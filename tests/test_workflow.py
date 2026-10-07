"""Create tiny committed source repositories and copied Just recipes, exercise
preparation and its failures, and verify clean submodules, reproducible output,
actionable missing-source diagnostics, and strict patch-conflict handling.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class SourceProjectFixture:
    def setUp(self):
        self.project = Path(__file__).resolve().parents[1]
        self.tmp = tempfile.TemporaryDirectory(prefix="awg-prep-", dir="/private/tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assertTrue((self.project / "justfile").exists(), "The public Just entrypoint is missing")
        shutil.copyfile(self.project / "justfile", self.root / "justfile")
        shutil.copytree(self.project / "patches", self.root / "patches")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for name in ("amneziawg-go", "amneziawg-tools"):
            repo = self.root / "src" / name
            repo.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            if name == "amneziawg-go":
                (repo / "version.go").write_text('package main\nconst Version = "old"\n')
            else:
                target = repo / "src/wg-quick/darwin.bash"
                target.parent.mkdir(parents=True)
                source = self.project / "src/amneziawg-tools/src/wg-quick/darwin.bash"
                shutil.copyfile(source, target)
            self.git(repo, "add", ".")
            self.git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "commit", "-qm", "Source fixture")

    def git(self, repo, *args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


class PreparationTests(SourceProjectFixture, unittest.TestCase):
    def prepare(self, **variables):
        return subprocess.run(["just", "--justfile", str(self.root / "justfile"), "prepare"],
                              env=dict(os.environ, **variables), text=True, capture_output=True)

    def test_missing_submodule_reports_checkout_command(self):
        """Remove one fixture checkout, invoke preparation, and check failure
        explains how to initialize the missing submodule.
        """
        (self.root / "src/amneziawg-tools").rename(self.root / "hidden-tools")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git submodule update --init --recursive", result.stderr)

    def test_repeated_preparation_keeps_sources_clean(self):
        """Prepare twice from committed sources, compare generated outputs,
        execute CLI help, and check neither source checkout was modified.
        """
        first = self.prepare()
        self.assertEqual(first.returncode, 0, first.stderr)
        script = self.root / "build/awg-quick"
        content = script.read_bytes()
        second = self.prepare()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(script.read_bytes(), content)
        for name in ("amneziawg-go", "amneziawg-tools"):
            self.assertEqual(self.git(self.root / "src" / name, "status", "--porcelain"), "")
        result = subprocess.run([str(script), "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        help_text = result.stdout + result.stderr
        self.assertIn("ExcludeIPs", help_text)
        self.assertIn("up | down | save | strip", help_text)

    def test_patch_conflict_stops_without_replacing_previous_output(self):
        """Prepare successfully, append a conflicting patch, prepare again,
        and check failure leaves the previously generated script intact.
        """
        first = self.prepare()
        self.assertEqual(first.returncode, 0, first.stderr)
        script = self.root / "build/awg-quick"
        content = script.read_bytes()
        (self.root / "patches/conflict.patch").write_text(
            "--- a/src/wg-quick/darwin.bash\n+++ b/src/wg-quick/darwin.bash\n"
            "@@ -1 +1 @@\n-THIS_LINE_DOES_NOT_EXIST\n+replacement\n")
        with (self.root / "patches/series").open("a") as f:
            f.write("conflict.patch\n")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("patch", result.stderr)
        self.assertEqual(script.read_bytes(), content)

    def test_dirty_source_is_rejected_instead_of_silently_ignored(self):
        """Edit a tracked fixture file, prepare, and check the build rejects
        uncommitted source changes instead of silently exporting older content.
        """
        (self.root / "src/amneziawg-go/version.go").write_text("uncommitted changes\n")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tracked local edits", result.stderr)

    def test_old_bash_override_is_rejected(self):
        """Select macOS Bash 3.2 explicitly, prepare, and check it fails with
        a Bash 4+ prerequisite diagnostic before producing an unusable script.
        """
        result = self.prepare(BASH_BIN="/bin/bash")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Bash 4+ required", result.stderr)


if __name__ == "__main__":
    unittest.main()

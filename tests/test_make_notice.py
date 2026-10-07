"""Copy the root Makefile into a temporary project, invoke each legacy target,
and check it prints the Just replacement without touching generated files.
"""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class MakeNoticeTests(unittest.TestCase):
    def test_legacy_targets_only_print_just_references(self):
        """Create protected build markers, run every old target plus an unknown
        target, and check migration notices are returned without executing tasks.
        """
        targets = ["all", "build", "prepare", "check-patches", "test", "test-upstream",
                   "install", "uninstall", "dev-install", "clean", "init-submodules",
                   "update-upstreams", "print-upstreams", "unknown-task"]
        project = Path(__file__).resolve().parents[1]
        for target in targets:
            with self.subTest(target=target), tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
                root = Path(tmp)
                shutil.copyfile(project / "Makefile", root / "Makefile")
                for directory in ["bin", "build"]:
                    (root / directory).mkdir()
                    (root / directory / "marker").write_text("preserve me")
                result = subprocess.run(["/usr/bin/make", "-C", str(root), target],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = "just --list" if target == "unknown-task" else "just " + target
                self.assertIn(expected, result.stdout)
                for directory in ["bin", "build"]:
                    self.assertTrue((root / directory / "marker").exists())
                    self.assertEqual((root / directory / "marker").read_text(), "preserve me")

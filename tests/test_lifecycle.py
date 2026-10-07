"""Run the real Just installation recipes against temporary source projects,
with compiler and privileged OS operations isolated to fixtures. Check copied
executables, config protection, explicit purge, argument safety, and dev symlinks.
"""

import json
import os
import shutil
import stat
import subprocess
import unittest

import test_workflow


class LifecycleTests(test_workflow.SourceProjectFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        for name in ["install.sh", "uninstall.sh"]:
            if (self.project / name).exists():
                shutil.copy2(self.project / name, self.root / name)
        (self.root / "conf").mkdir()
        shutil.copyfile(self.project / "conf/awg0.conf.example",
                        self.root / "conf/awg0.conf.example")
        self.prefix = self.root / "prefix with spaces"
        (self.prefix / "bin").mkdir(parents=True)
        self.config_dir = self.root / "system-config"
        self.config_dir.mkdir()
        self.config = self.config_dir / "awg0.conf"
        self.config.write_text("private fixture configuration\n")
        self.log = self.root / "privileged.jsonl"
        self.commands = self.root / "fixture-commands"
        self.commands.mkdir()
        self.write_command("go", '''#!/bin/bash
set -euo pipefail
if [[ $1 == version ]]; then
    echo 'go version go1.25.0 darwin/arm64'
else
    [[ $# == 4 && $1 == build && $2 == -trimpath && $3 == -o ]] || exit 91
    printf '#!/bin/sh\nexit 0\n' > "$4"
    chmod 755 "$4"
fi
''')
        self.write_command("make", '''#!/bin/bash
set -euo pipefail
[[ $# == 3 && $1 == -C && $2 == "$ROOT/build/amneziawg-tools/src" && $3 == all ]] || exit 92
printf 'C configuration tool fixture\n' > "$2/wg"
chmod 755 "$2/wg"
''')
        # Execute real file operations in a mapped temporary config directory.
        # chown is intercepted because tests must not change host ownership.
        self.write_command("sudo", '''#!/usr/bin/env python3
import json, os, shutil, subprocess, sys
args = sys.argv[1:]
if not args or args[0] not in {"mkdir", "chown", "chmod", "install", "rm"}:
    raise SystemExit("Unexpected privileged operation")
with open(os.environ["TEST_PRIVILEGED_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[0] == "chown":
    raise SystemExit(0)
original = "/etc/amnezia/amneziawg"
args = [os.environ["TEST_SYSTEM_CONFIG"] + a[len(original):]
        if a == original or a.startswith(original + "/") else a for a in args]
raise SystemExit(subprocess.run([shutil.which(args[0]), *args[1:]]).returncode)
''')

    def write_command(self, name, body):
        path = self.commands / name
        path.write_text(body)
        path.chmod(0o755)

    def run_task(self, task, *args):
        env = dict(os.environ, PREFIX=str(self.prefix),
                   PATH=str(self.commands) + os.pathsep + os.environ["PATH"],
                   TEST_SYSTEM_CONFIG=str(self.config_dir), TEST_PRIVILEGED_LOG=str(self.log))
        return subprocess.run(["just", "--justfile", str(self.root / "justfile"), task, *args],
                              env=env, text=True, capture_output=True)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_install_copies_executables_and_preserves_existing_configs(self):
        """Create a writable prefix and an existing private config, install
        through Just, then check executable copies, modes, and config preservation.
        """
        self.assert_ok(self.run_task("install"))
        for name in ["amneziawg-go", "awg", "awg-quick"]:
            installed = self.prefix / "bin" / name
            self.assertFalse(installed.is_symlink())
            self.assertEqual(installed.read_bytes(), (self.root / "bin" / name).read_bytes())
            self.assertEqual(stat.S_IMODE(installed.stat().st_mode), 0o755)
        self.assertEqual(self.config.read_text(), "private fixture configuration\n")
        self.assertEqual(stat.S_IMODE(self.config_dir.stat().st_mode), 0o700)
        example = self.config_dir / "awg0.conf.example"
        self.assertEqual(example.read_bytes(), (self.root / "conf/awg0.conf.example").read_bytes())
        self.assertEqual(stat.S_IMODE(example.stat().st_mode), 0o600)

    def test_uninstall_preserves_configs_until_explicit_purge(self):
        """Create installed files and configs, reject an unsafe argument,
        uninstall normally, then purge and check only requested files are removed.
        """
        for name in ["amneziawg-go", "awg", "awg-quick", "unrelated"]:
            (self.prefix / "bin" / name).write_text("fixture\n")
        marker = self.root / "argument-was-executed"
        bad = self.run_task("uninstall", "--purge; touch " + str(marker))
        self.assertNotEqual(bad.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertTrue((self.prefix / "bin/awg").exists())
        self.assert_ok(self.run_task("uninstall"))
        for name in ["amneziawg-go", "awg", "awg-quick"]:
            self.assertFalse((self.prefix / "bin" / name).exists())
        self.assertTrue(self.config.exists())
        self.assertTrue((self.prefix / "bin/unrelated").exists())
        self.assert_ok(self.run_task("uninstall", "--purge"))
        self.assertFalse(self.config_dir.exists())
        operations = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(operations, [["rm", "-rf", "/etc/amnezia/amneziawg"]])

    def test_dev_install_links_outputs_and_uninstall_keeps_sources(self):
        """Build fixture executables, install dev symlinks, remove them through
        uninstall, and check the underlying build outputs and configs remain.
        """
        self.assert_ok(self.run_task("dev-install"))
        for name in ["amneziawg-go", "awg", "awg-quick"]:
            installed = self.prefix / "bin" / name
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), self.root / "bin" / name)
        self.assert_ok(self.run_task("uninstall"))
        for name in ["amneziawg-go", "awg", "awg-quick"]:
            self.assertFalse((self.prefix / "bin" / name).is_symlink())
            self.assertTrue((self.root / "bin" / name).exists())
        self.assertTrue(self.config.exists())

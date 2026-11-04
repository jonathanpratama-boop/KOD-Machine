"""Exercise the guard against real git trees, including unusual path names."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "append_guard", Path(__file__).resolve().parents[1] / "check_append_only.py"
)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class AppendOnlyGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture.invalid")
        self.original_git = guard.git
        self.mock = patch.object(guard, "git", self.git)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def git(self, *args, check=True):
        proc = subprocess.run(["git", *args], cwd=self.root, capture_output=True)
        if check and proc.returncode:
            raise SystemExit(proc.stderr.decode())
        return proc.stdout

    def write(self, name, data):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def baseline(self, name, data=b"old\n"):
        self.write(name, data)
        self.git("add", "--", name)
        self.git("commit", "-qm", "fixture")

    def staged(self, name, data):
        self.write(name, data)
        self.git("add", "--", name)
        return guard.check("HEAD", None)

    def test_new_registry_subdirectory_is_frozen(self):
        name = "kod-machine/registry/new-kind/original.json"
        self.baseline(name)
        self.assertTrue(self.staged(name, b"changed\n"))

    def test_versioned_timing_contracts_require_new_paths(self):
        names = (
            "handoff/astra/protocols/EXAMPLE_v1/PROTOCOL.md",
            "costs/example_v1.json",
            "docs/schemas/example_v1.json",
            "schemas/example_v1.json",
        )
        for name in names:
            self.baseline(name)
        for name in names:
            with self.subTest(path=name):
                self.assertTrue(self.staged(name, b"changed\n"))
                self.git("reset", "--hard", "HEAD")
                self.write(name.replace("v1", "v2"), b"new version\n")
                self.git("add", ".")
                self.assertEqual(guard.check("HEAD", None), [])
                self.git("reset", "--hard", "HEAD")

    def test_newline_path_cannot_escape_protection(self):
        name = "idx-signals/research/a\nb.json"
        self.baseline(name)
        self.assertTrue(self.staged(name, b"changed\n"))

    def test_id_alias_map_is_append_only(self):
        name = "registry/ids/ID_MAP.jsonl"
        self.baseline(name)
        self.assertEqual(self.staged(name, b"old\nnew\n"), [])
        self.assertTrue(self.staged(name, b"rewritten\n"))

    def test_registry_logs_still_allow_exact_prefix_append(self):
        name = "kod-machine/registry/opens.jsonl"
        self.baseline(name)
        self.assertEqual(self.staged(name, b"old\nnew\n"), [])
        self.assertTrue(self.staged(name, b"rewritten\n"))

    def test_missing_blob_is_error_instead_of_empty_history(self):
        with self.assertRaises(SystemExit):
            guard.blob("not-a-commit", "registry/ids/ID_MAP.jsonl")

    def test_frozen_rename_and_delete_are_rejected(self):
        name = "idx-signals/research/original.json"
        self.baseline(name)
        self.git("mv", name, "idx-signals/research/renamed.json")
        self.assertTrue(guard.check("HEAD", None))
        self.git("reset", "--hard", "HEAD")
        self.git("rm", name)
        self.assertTrue(guard.check("HEAD", None))


if __name__ == "__main__":
    unittest.main()

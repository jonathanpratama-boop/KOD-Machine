"""Exercise the public command boundary across the integrated components."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from idxsig.runtime.__main__ import main
from idxsig.runtime.demo import demo
from idxsig.runtime.storage import atomic_json


class ComponentEntrypoints(unittest.TestCase):
    def invoke(self, arguments):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = main(arguments)
        return code, json.loads(output.getvalue() or errors.getvalue())

    def test_existing_recorded_account_validates_through_public_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            demo(root)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            code, result = self.invoke(["--root", str(root), "validate"])
            self.assertEqual(code, 0, result)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["checks"]["restart_idempotency"]["status"], "PASS")
            self.assertEqual(
                before,
                {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()},
            )

    def test_absent_decisions_are_inconclusive_and_do_not_create_an_account(self):
        with tempfile.TemporaryDirectory() as directory:
            code, result = self.invoke(["--root", directory, "validate"])
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_strategy_evaluation_and_checks_share_the_same_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            request = {
                "strategy": {
                    "id": "SMA_CROSS_SHADOW_V1",
                    "version": "1",
                    "parameters": {"fast": 2, "slow": 3},
                },
                "observations": [
                    {
                        "observed_at": f"2026-01-01T00:0{i}:00Z",
                        "symbol": "BTCUSDT",
                        "close": str(100 + i),
                    }
                    for i in range(6)
                ],
            }
            path = Path(directory) / "request.json"
            atomic_json(path, request)
            code, evaluated = self.invoke(["strategy-evaluate", "--input", str(path)])
            self.assertEqual(code, 0)
            self.assertFalse(evaluated["entry_enabled"])
            code, checked = self.invoke(
                ["strategy-check", "--input", str(path), "--warmup-lengths", "3", "5"]
            )
            self.assertEqual(code, 0, checked)
            self.assertEqual(checked["input_sha256"], evaluated["input_sha256"])
            self.assertEqual(checked["status"], "PASS")
            request["as_of"] = "2025-12-31T00:00:00Z"
            atomic_json(path, request)
            code, failure = self.invoke(["strategy-check", "--input", str(path)])
            self.assertEqual(code, 1)
            self.assertFalse(failure["ok"])

    def test_duplicate_json_keys_are_rejected_at_the_command_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text('{"strategy": {}, "strategy": {}}')
            code, result = self.invoke(["strategy-evaluate", "--input", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("duplicate", result["error"])


if __name__ == "__main__":
    unittest.main()

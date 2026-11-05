"""The operational watcher preserves evidence and distinguishes gaps from corruption."""

import copy
import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("watch_llm_arm", ROOT / "tools/watch_llm_arm.py")
watcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watcher)


class LlmArmWatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.output = Path(self.temp.name) / "watch"
        self.calls = self.repo / "idx-signals/research/LLM_ARM_v1/calls.jsonl"
        self.register = self.repo / "idx-signals/paper/speculations.jsonl"
        self.calls.parent.mkdir(parents=True)
        self.register.parent.mkdir(parents=True)
        self.call = {
            "call_id": "L1",
            "set": "S1",
            "ticker": "TEST",
            "market": "US",
            "signal_session": "2026-11-04",
            "called_at": "2026-11-04T23:00Z",
            "call": "ABSTAIN",
            "p": {key: 0.5 for key in ("RUN30_5", "FADE10_5", "BEATS_TWINS_5")},
            "sources": [],
            "reasons": ["Evidence insufficient"],
            "agrees_with_kod": True,
            "kod_numeric": "Forecast not sealed",
        }
        self.candidate = {
            "type": "SPECULATION_SET",
            "set_id": "S1",
            "ticker": "TEST",
            "market": "US",
            "signal_session": "2026-11-04",
            "sealed_at": "2026-11-04T22:00Z",
            "entry_cutoff": "2026-11-05T14:30Z",
            "cone": [{"id": key, "prior": 0.5, "resolves_with": "BASE5"} for key in self.call["p"]],
        }
        self.write_calls([self.call])
        self.write_register([self.candidate])

    def write_calls(self, rows):
        self.calls.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def write_register(self, rows):
        previous, records = None, []
        for row in rows:
            body = dict(row, prev_hash=previous)
            previous = watcher.digest(body)
            records.append(dict(body, record_hash=previous))
        self.register.write_text("".join(json.dumps(row) + "\n" for row in records))

    def test_quality_gaps_are_visible_without_failing_workflow(self):
        with redirect_stdout(io.StringIO()):
            code = watcher.main(["--repository", str(self.repo), "--output", str(self.output)])
        self.assertEqual(code, 0)
        result = watcher.watch(self.repo, self.output)
        self.assertEqual(result["status"], "ISSUES")
        self.assertEqual(result["audit"]["counts"]["all_call_rows"], 1)
        self.assertIn("CALLS_WITHOUT_SOURCE_URLS", [issue["code"] for issue in result["issues"]])
        self.assertEqual(result["register_chain"], "LOCAL_BYTES_CHECKED")
        self.assertFalse(result["notifications_delivered"])
        self.assertFalse(result["profitability_validated"])

    def test_unchanged_inputs_do_not_duplicate_snapshot_or_journal(self):
        before = (self.calls.read_bytes(), self.register.read_bytes())
        first = watcher.watch(self.repo, self.output, clock=lambda: "2026-11-05T00:00Z")
        second = watcher.watch(self.repo, self.output, clock=lambda: "2026-11-06T00:00Z")
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertEqual(len(watcher.read_receipts(self.output)), 1)
        self.assertEqual(len(list((self.output / "snapshots").glob("*.json"))), 1)
        self.assertEqual((self.calls.read_bytes(), self.register.read_bytes()), before)

    def test_whole_file_changes_have_distinct_receipts_even_if_rows_identical(self):
        first = watcher.watch(self.repo, self.output)
        self.calls.write_text(json.dumps(self.call, separators=(",", ":")) + "\n")
        second = watcher.watch(self.repo, self.output)
        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertEqual(len(watcher.read_receipts(self.output)), 2)
        info = second["inputs"]["idx-signals/research/LLM_ARM_v1/calls.jsonl"]
        self.assertEqual(info["sha256"], watcher._sha(self.calls.read_bytes()))

    def test_all_call_files_are_read_and_duplicates_fail(self):
        other = self.calls.with_name("calls_US_20261104.jsonl")
        other.write_bytes(self.calls.read_bytes())
        result = watcher.watch(self.repo, self.output)
        self.assertEqual(result["audit"]["counts"]["all_call_rows"], 2)
        self.assertEqual(result["audit"]["counts"]["duplicate_call_rows"], 2)
        self.assertEqual(result["status"], "BLOCKED")

    def test_malformed_json_is_logged_without_discarding_failure(self):
        self.calls.write_text('{"call_id":"L1","call_id":"duplicate"}\n')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(
                watcher.main(["--repository", str(self.repo), "--output", str(self.output)]), 1
            )
        result = watcher.watch(self.repo, self.output)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["errors"][0]["code"], "INPUT_UNREADABLE")
        self.assertEqual(len(watcher.read_receipts(self.output)), 1)

    def test_register_hash_tampering_is_a_failure(self):
        rows = watcher.load_jsonl(self.register)
        rows[0]["ticker"] = "ALTERED"
        self.register.write_text(json.dumps(rows[0]) + "\n")
        result = watcher.watch(self.repo, self.output)
        self.assertIn("REGISTER_CHAIN_INVALID", [error["code"] for error in result["errors"]])
        self.assertEqual(result["register_chain"], "INVALID_OR_MISSING")

    def test_missing_sources_retain_failure_snapshot(self):
        self.calls.unlink()
        self.register.unlink()
        result = watcher.watch(self.repo, self.output)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(Path(result["snapshot_path"]).exists())

    def test_corrupt_old_snapshot_or_journal_cannot_be_overwritten(self):
        result = watcher.watch(self.repo, self.output)
        path = Path(result["snapshot_path"])
        record = copy.deepcopy(watcher.read_json(path))
        record["status"] = "OK"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            watcher.watch(self.repo, self.output)
        path.write_text(
            json.dumps(
                {
                    key: value
                    for key, value in result.items()
                    if key not in {"snapshot_sha256", "snapshot_path"}
                }
            )
        )
        (self.output / "runs.jsonl").write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "integrity"):
            watcher.watch(self.repo, self.output)

    def test_output_symlink_and_unrelated_directory_are_rejected(self):
        self.output.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic"):
            watcher.watch(self.repo, self.output)
        self.output.unlink()
        self.output.mkdir()
        (self.output / "unrelated.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "dedicated"):
            watcher.watch(self.repo, self.output)

    def test_errors_are_json_escaped_in_cli(self):
        self.output.mkdir()
        (self.output / "unexpected").write_text("keep")
        stream = io.StringIO()
        with redirect_stderr(stream):
            self.assertEqual(
                watcher.main(["--repository", str(self.repo), "--output", str(self.output)]), 1
            )
        self.assertEqual(json.loads(stream.getvalue())["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

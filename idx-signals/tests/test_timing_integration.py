"""The timing organs must work together without changing historical economics."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from idxsig.runtime import coordinator
from idxsig.runtime.backup import backup, restore
from idxsig.runtime.demo import fixtures, T0
from idxsig.runtime.intraday import PublicResponse
from idxsig.runtime.storage import atomic_json, read_json
from idxsig.runtime.timing import (
    Attempt,
    capture_intraday,
    publish_board,
    retain_context,
    timing_status,
)
from idxsig.runtime.timing_demo import timing_demo, DEMO_TIME
from idxsig.runtime.data import utc_text
from idxsig.timing_capture import read_attempts
from idxsig.timing_context import context_fixture


class TimingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "runtime"
        self.clock_patch = patch("idxsig.runtime.timing.shutil.which", return_value=None)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)

    def test_synthetic_body_runs_offline_replays_and_restores(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            result = timing_demo(self.root)
            first = (self.root / "snapshot.json").read_bytes()
            journal = (self.root / "timing/attempts.jsonl").read_bytes()
            self.assertEqual(result, timing_demo(self.root))
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["entry_permission"])
        self.assertEqual(first, (self.root / "snapshot.json").read_bytes())
        self.assertEqual(journal, (self.root / "timing/attempts.jsonl").read_bytes())
        rows = read_attempts(self.root)
        requests = [r for r in rows if r["detector_version"] == "SOURCE_REQUEST_V1"]
        self.assertTrue(requests)
        self.assertTrue(all(r["status"] == "COMPLETED" for r in requests))
        self.assertTrue(all(r["source_time"] is None for r in requests))
        bundle = Path(self.tmp.name) / "backup.zip"
        backup(self.root, bundle)
        recovered = Path(self.tmp.name) / "restored"
        restore(bundle, recovered)
        self.assertEqual(
            timing_status(self.root)["integrity"], timing_status(recovered)["integrity"]
        )
        self.assertTrue(coordinator.verify(recovered)["ok"])

    def test_provider_block_retains_parent_and_failed_request_no_fake_market(self):
        fetcher = Mock(return_value=PublicResponse(451, b"unavailable"))
        result = capture_intraday(
            self.root,
            scheduled_at=utc_text(DEMO_TIME),
            symbols=["BTCUSDT"],
            bars=2,
            clock=lambda: utc_text(DEMO_TIME),
            fetcher=fetcher,
            evidence_kind="synthetic",
        )
        self.assertEqual(fetcher.call_count, 1)
        self.assertEqual(result["capture"]["status"], "BLOCKED")
        rows = read_attempts(self.root)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["status"] == "BLOCKED" for r in rows))
        self.assertFalse((self.root / "account").exists())

    def test_invalid_runtime_input_still_records_failed_attempt(self):
        self.root.mkdir()
        snapshot = self.root / "bad.json"
        snapshot.write_text("{}")
        with self.assertRaises((KeyError, ValueError, FileNotFoundError)):
            coordinator.run_once(self.root, snapshot, self.root / "missing.json", T0)
        rows = read_attempts(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "FAILED")
        self.assertIsNone(rows[0]["decision_at"])

    def test_processing_retry_keeps_original_economic_snapshot(self):
        profile, snapshots = fixtures()
        p, s = self.root / "source_profile.json", self.root / "source_snapshot.json"
        atomic_json(p, profile)
        atomic_json(s, snapshots[0])
        first = coordinator.run_once(self.root, s, p, T0)
        second = coordinator.run_once(self.root, s, p, T0)
        self.assertEqual(first, second)
        rows = read_attempts(self.root)
        rows = [r for r in rows if r["detector_version"] == "KOD_RUNTIME_PROCESSING_V1"]
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["id"], rows[1]["id"])
        self.assertEqual(rows[0]["links"]["run_id"], rows[1]["links"]["run_id"])
        self.assertIsNone(rows[1]["decision_at"])

    def test_finish_retry_recovers_projection_failure_without_duplicate_append(self):
        attempt = Attempt(
            self.root, detector="TEST", source="synthetic", kind="synthetic", members=[]
        )
        with patch("idxsig.runtime.timing.publish_board", side_effect=OSError("projection failed")):
            with self.assertRaises(OSError):
                attempt.finish("NO_TRIGGER")
        before = (self.root / "timing/attempts.jsonl").read_bytes()
        attempt.finish("NO_TRIGGER")
        self.assertEqual(before, (self.root / "timing/attempts.jsonl").read_bytes())
        with self.assertRaisesRegex(ValueError, "conflicting"):
            attempt.finish("COMPLETED")

    def test_context_only_root_and_historical_report_preserve_latest(self):
        fixture = context_fixture()
        retain_context(self.root, fixture, as_of=fixture["as_of"])
        latest = (self.root / "timing/report.json").read_bytes()
        historical = publish_board(self.root, as_of=fixture["as_of"])
        self.assertEqual(historical["payload"]["contexts"], [])
        self.assertEqual(latest, (self.root / "timing/report.json").read_bytes())
        board = read_json(self.root / "timing/report.json")
        self.assertEqual(board["payload"]["clock"]["status"], "UNKNOWN")
        self.assertEqual(len(board["payload"]["shadow"]), 2)


if __name__ == "__main__":
    unittest.main()

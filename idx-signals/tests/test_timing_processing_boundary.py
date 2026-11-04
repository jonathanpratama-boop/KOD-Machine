"""Read boundaries include setup delays without inventing successful coverage."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idxsig.runtime import coordinator
from idxsig.runtime.coordinator import run_once
from idxsig.runtime.demo import fixtures, T0
from idxsig.runtime.storage import atomic_json, read_json
from idxsig.runtime.timing import processing_attempt
from idxsig.timing_capture import read_attempts


class ProcessingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "runtime"
        self.profile, self.snapshots = fixtures()
        self.profile_path = self.base / "profile.json"
        atomic_json(self.profile_path, self.profile)
        self.clock_patch = patch("idxsig.runtime.timing.shutil.which", return_value=None)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)

    def test_read_receipt_precedes_membership_and_clock_probe_completion(self):
        source = self.base / "source.json"
        atomic_json(source, self.snapshots[0])
        values = iter(
            [
                "2026-11-04T00:00:00Z",
                "2026-11-04T00:00:01Z",
                "2026-11-04T00:00:05Z",
                "2026-11-04T00:00:06Z",
            ]
        )
        ticks = iter([100, 160])
        trace = processing_attempt(
            self.root, source, clock=lambda: next(values), monotonic_ns=lambda: next(ticks)
        )
        self.assertEqual(trace.record["started_at"], "2026-11-04T00:00:00Z")
        self.assertEqual(trace.record["received_at"], "2026-11-04T00:00:01Z")
        self.assertEqual(trace.record["clock"]["observed_at"], "2026-11-04T00:00:05Z")
        member = read_json(next((self.root / "timing/memberships").glob("*.json")))
        self.assertEqual(member["recorded_at"], trace.record["started_at"])
        trace.finish("COMPLETED")
        self.assertEqual(read_attempts(self.root)[0]["durations_ns"]["invocation"], 60)

    def test_nonobject_snapshots_retain_failed_attempts(self):
        for index, value in enumerate(([], None)):
            with self.subTest(value=value):
                source = self.base / f"bad-{index}.json"
                root = self.base / f"bad-runtime-{index}"
                atomic_json(source, value)
                with self.assertRaisesRegex(ValueError, "schema"):
                    run_once(root, source, self.profile_path, T0)
                rows = read_attempts(root)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["status"], "FAILED")
                member = read_json(next((root / "timing/memberships").glob("*.json")))
                self.assertEqual(member["members"], [])
                self.assertFalse((root / "account/account.jsonl").exists())

    def test_failed_read_has_no_received_timestamp(self):
        trace = processing_attempt(self.root, self.base / "missing.json")
        self.assertIsNone(trace.record["received_at"])
        trace.finish("FAILED")
        self.assertEqual(read_attempts(self.root)[0]["status"], "FAILED")

    def test_changed_input_between_read_and_processing_fails_before_account_write(self):
        source = self.base / "source.json"
        atomic_json(source, self.snapshots[0])
        original_run = coordinator._run_once

        def mutate_then_run(*args, **kwargs):
            atomic_json(source, self.snapshots[1])
            return original_run(*args, **kwargs)

        with patch("idxsig.runtime.coordinator._run_once", side_effect=mutate_then_run):
            with self.assertRaisesRegex(ValueError, "input changed"):
                run_once(self.root, source, self.profile_path, T0)
        rows = read_attempts(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "FAILED")
        self.assertFalse((self.root / "account/account.jsonl").exists())
        self.assertFalse((self.root / "pending.json").exists())


if __name__ == "__main__":
    unittest.main()

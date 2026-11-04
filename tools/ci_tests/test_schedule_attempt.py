import importlib.util
import io
import json
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "record_schedule_attempt", ROOT / "tools/record_schedule_attempt.py"
)
schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule)

ENV = {
    "GITHUB_RUN_ID": "123456",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_SHA": "a" * 40,
    "GITHUB_TOKEN": "secret-not-for-receipts",
    "KOD_SEC_CONTACT": "private-not-for-receipts",
}
T0 = "2026-11-04T02:41:00Z"
T1 = "2026-11-04T02:42:00Z"


class ScheduleAttemptTests(unittest.TestCase):
    def record(self, output, phase="begin", at=T0, **kwargs):
        values = dict(
            event="schedule", reference_utc="02:41", phase=phase, environment=ENV, clock=lambda: at
        )
        values.update(kwargs)
        return schedule.record_attempt(output, **values)

    def test_daily_reference_rollover_never_points_to_future(self):
        result = schedule.infer_slot(
            "2026-11-04T01:00:00Z", event="schedule", reference_utc="02:41"
        )
        self.assertEqual(result["inferred_slot_at"], "2026-11-03T02:41:00Z")
        self.assertEqual(result["delay_from_inferred_slot_seconds"], 80340)
        self.assertIsNone(result["platform_scheduled_at"])
        self.assertEqual(result["slot_basis"], "MOST_RECENT_UTC_CRON_SLOT")

    def test_manual_dispatch_has_no_guessed_slot_or_delay(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.record(directory, event="workflow_dispatch")
            self.assertIsNone(row["inferred_slot_at"])
            self.assertIsNone(row["delay_from_inferred_slot_seconds"])
            self.assertIsNone(row["overdue"])
            self.assertEqual(row["slot_basis"], "UNKNOWN")

    def test_delayed_start_is_flagged_without_claiming_actual_scheduled_time(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.record(directory, at="2026-11-04T09:41:00Z")
            self.assertEqual(row["delay_from_inferred_slot_seconds"], 7 * 3600)
            self.assertTrue(row["overdue"])
            self.assertIsNone(row["platform_scheduled_at"])
            self.assertFalse(row["forward_trial"])
            self.assertFalse(row["entry_permission"])

    def test_exact_begin_retry_reuses_first_observation_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.record(directory)
            path = next(Path(directory).glob("*.begin.json"))
            before = path.read_bytes()
            self.assertEqual(self.record(directory, at=T1), first)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 1)

    def test_completion_keeps_failure_and_links_original_begin(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.record(directory)
            last = self.record(directory, phase="complete", at=T1, status="failure")
            self.assertEqual(last["status"], "FAILURE")
            self.assertEqual(last["wall_elapsed_seconds"], 60)
            self.assertEqual(last["begin_sha256"], first["sha256"])
            self.assertEqual(
                self.record(
                    directory, phase="complete", at="2026-11-04T02:43:00Z", status="FAILURE"
                ),
                last,
            )
            with self.assertRaisesRegex(ValueError, "conflicting"):
                self.record(directory, phase="complete", at=T1, status="success")

    def test_missing_begin_retains_completion_with_unknown_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.record(directory, phase="complete", status="cancelled")
            self.assertEqual(row["status"], "CANCELLED")
            self.assertIsNone(row["started_at"])
            self.assertIsNone(row["wall_elapsed_seconds"])
            self.assertIsNone(row["inferred_slot_at"])
            self.assertTrue(any("BEGIN_RECEIPT_UNAVAILABLE" in s for s in row["warnings"]))

    def test_clock_reversal_preserved_as_conflict_not_negative_elapsed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.record(directory, at=T1)
            row = self.record(directory, phase="complete", at=T0, status="failure")
            self.assertEqual(row["clock_status"], "WALL_CLOCK_REVERSED")
            self.assertEqual(row["signed_wall_elapsed_seconds"], -60)
            self.assertIsNone(row["wall_elapsed_seconds"])

    def test_future_existing_receipt_and_naive_clock_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.record(directory, at=T1)
            with self.assertRaisesRegex(ValueError, "after the current"):
                self.record(directory, at=T0)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.record(directory, at=datetime(2026, 11, 4))

    def test_missing_or_malformed_run_identity_rejected_before_writing(self):
        for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                env = dict(ENV)
                env.pop(key)
                with self.assertRaises(ValueError):
                    self.record(directory, environment=env)
                self.assertEqual(list(Path(directory).iterdir()), [])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.record(directory, environment={**ENV, "GITHUB_RUN_ID": "../escape"})

    def test_run_attempts_are_distinct_and_identity_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.record(directory)
            second = self.record(directory, environment={**ENV, "GITHUB_RUN_ATTEMPT": "2"})
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertEqual(len(list(Path(directory).glob("*.begin.json"))), 2)
            with self.assertRaisesRegex(ValueError, "conflicting"):
                self.record(directory, environment={**ENV, "GITHUB_SHA": "b" * 40})

    def test_corrupted_or_symlink_receipt_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            self.record(directory)
            path = next(Path(directory).glob("*.begin.json"))
            path.write_bytes(path.read_bytes().replace(b'"STARTED"', b'"SUCCESS"'))
            with self.assertRaisesRegex(ValueError, "integrity"):
                self.record(directory)
        with tempfile.TemporaryDirectory() as directory:
            self.record(directory)
            path = next(Path(directory).glob("*.begin.json"))
            target = Path(directory) / "original"
            path.rename(target)
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.record(directory)

    def test_no_secret_or_contact_environment_fields_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            row = self.record(directory)
            serialized = json.dumps(row)
            self.assertNotIn(ENV["GITHUB_TOKEN"], serialized)
            self.assertNotIn(ENV["KOD_SEC_CONTACT"], serialized)
            self.assertNotIn("GITHUB_TOKEN", serialized)

    def test_invalid_reference_and_repository_output_are_rejected(self):
        for reference in ("25:00", "2:41", "02:60", "tomorrow"):
            with self.subTest(reference=reference), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    self.record(directory, reference_utc=reference)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.record(ROOT / "schedule-receipts-not-created")

    def test_cli_errors_do_not_echo_malformed_environment_values(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(schedule.os.environ, {**ENV, "GITHUB_SHA": "sensitive-invalid"}),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = schedule.main(
                [
                    "--output",
                    directory,
                    "--event",
                    "schedule",
                    "--reference-utc",
                    "02:41",
                    "--phase",
                    "begin",
                ]
            )
        self.assertEqual(code, 1)
        self.assertNotIn("sensitive-invalid", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["status"], "RECEIPT_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()

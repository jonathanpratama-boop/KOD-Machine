"""Replay diagnostics preserve source evidence and never manufacture forward runs."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig.runtime import coordinator
from idxsig.runtime.demo import demo, fixtures, T0, T1
from idxsig.runtime.storage import atomic_json, read_json
from idxsig.runtime.validation import validate_recorded_run


def bytes_by_path(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class RecordedValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.source.mkdir()
        clock = patch("idxsig.runtime.timing.shutil.which", return_value=None)
        clock.start()
        self.addCleanup(clock.stop)

    def test_demo_replays_each_decision_and_retry_without_source_mutation(self):
        demo(self.source)
        before = bytes_by_path(self.source)
        output = self.base / "validation"
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            report = validate_recorded_run(self.source, output_root=output)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["restart_idempotency"]["cycles_retried"], 2)
        self.assertEqual(len(report["checks"]["decision_replay"]["cycles"]), 2)
        self.assertEqual(before, bytes_by_path(self.source))
        self.assertEqual(report, read_json(output / "report.json"))
        self.assertEqual(report["forward_trial_days"], 0)
        self.assertFalse(report["entry_permission"])
        self.assertNotEqual(report["source_profile_sha256"], report["replay_profile_sha256"])

    def test_forward_profile_is_demoted_only_in_isolated_replay(self):
        profile, snapshots = fixtures()
        profile["execution_mode"] = "FORWARD_PAPER_CAPTURE"
        path = self.base / "input-profile.json"
        atomic_json(path, profile)
        for index, cutoff in enumerate((T0, T1)):
            snapshot = self.base / f"source-{index}.json"
            atomic_json(snapshot, snapshots[index])
            coordinator.run_once(self.source, snapshot, path, cutoff, _captured=True)
        before = bytes_by_path(self.source)
        output = self.base / "validation"
        report = validate_recorded_run(self.source, output_root=output)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(
            read_json(output / "replay-profile.json")["execution_mode"],
            "RECORDED_REPLAY_VALIDATION",
        )
        self.assertEqual(before, bytes_by_path(self.source))

    def test_empty_source_is_unknown_and_does_not_gain_a_lockfile(self):
        report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(bytes_by_path(self.source), {})

    def test_timing_only_observation_cannot_pass_as_decision_replay(self):
        from idxsig.runtime.timing import record_missed

        record_missed(
            self.source, scheduled_at=T0, members=["BTCUSDT"], reason="provider unavailable"
        )
        before = bytes_by_path(self.source)
        report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertNotIn("decision_replay", report["checks"])
        self.assertEqual(before, bytes_by_path(self.source))

    def test_tampered_input_is_failed_without_repairing_source(self):
        result = demo(self.source)
        path = self.source / "inputs" / (result["payload"]["run"]["input_sha256"] + ".json")
        data = read_json(path)
        data["quotes"][0]["bid"] = "147"
        atomic_json(path, data)
        before = bytes_by_path(self.source)
        report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("hash mismatch", report["checks"]["validation_error"]["error"])
        self.assertEqual(before, bytes_by_path(self.source))

    def test_missing_account_file_is_corruption_not_empty_coverage(self):
        demo(self.source)
        (self.source / "profile.json").unlink()
        report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("incomplete", report["checks"]["validation_error"]["error"])

    def test_pending_operation_requires_recovery(self):
        demo(self.source)
        atomic_json(self.source / "pending.json", {"run_id": "uncommitted"})
        report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("pending", report["checks"]["validation_error"]["error"])

    def test_recomputed_economic_divergence_fails(self):
        demo(self.source)
        original = coordinator.run_once

        def divergent(*args, **kwargs):
            result = copy.deepcopy(original(*args, **kwargs))
            result["payload"]["account"]["cash"] = "999999"
            return result

        with patch.object(coordinator, "run_once", side_effect=divergent):
            report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["decision_replay"]["status"], "FAIL")

    def test_source_changes_after_checkpoint_are_unknown(self):
        demo(self.source)
        original = coordinator.verify

        def mutate_source(root):
            report = original(root)
            (self.source / "new-observation.json").write_text("{}")
            return report

        with patch.object(coordinator, "verify", side_effect=mutate_source):
            report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["checks"]["source_unchanged"]["status"], "UNKNOWN")

    def test_output_must_be_new_and_outside_source(self):
        for output in (self.source, self.source / "validation", self.base):
            with self.subTest(output=output), self.assertRaises(ValueError):
                validate_recorded_run(self.source, output_root=output)
        output = self.base / "existing"
        output.mkdir()
        with self.assertRaises(ValueError):
            validate_recorded_run(self.source, output_root=output)

    def test_source_symlink_is_rejected(self):
        (self.source / "unexpected").symlink_to(self.base)
        report = validate_recorded_run(self.source)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("symbolic", report["checks"]["validation_error"]["error"])


if __name__ == "__main__":
    unittest.main()

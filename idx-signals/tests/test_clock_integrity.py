"""Real chrony layout, historical compatibility and immutable derived correction."""

import copy
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from idxsig.runtime.clock import PARSER_VERSION, assess_clock, parse_tracking
from idxsig.runtime.storage import atomic_json, digest, read_json
from idxsig.runtime.timing import clock_observation
from idxsig.runtime.timing_evidence import assess_retained_clock, verify_linked_evidence
from idxsig.timing_capture import append_attempt, make_attempt, read_attempts


NOW = "2026-11-04T17:30:52Z"
TRACKING = (
    "334FA8DC,51.79.168.220,3,1793813391.074799414,0.001704435,"
    "0.000812492,0.010271930,-182.658,54.013,48.161,"
    "0.008213954,0.029829502,65.2,Normal"
)


def raw_clock(*, versioned=True, stdout=TRACKING, returncode=0):
    value = {
        "observed_at": NOW,
        "command": "chronyc -c tracking",
        "returncode": returncode,
        "stdout": stdout,
        "stderr": "",
    }
    if versioned:
        value["parser_version"] = PARSER_VERSION
    return value


def claim(offset="0.001704435"):
    return {
        "status": "MEASURED_EXTERNAL",
        "offset_seconds": offset,
        "observed_at": NOW,
        "evidence_id": "set-by-test",
    }


class ChronyParserTests(unittest.TestCase):
    def test_real_csv_separates_reference_epoch_from_system_offset(self):
        parsed = parse_tracking(TRACKING + "\n")
        self.assertEqual(parsed["reference_epoch_seconds"], "1793813391.074799414")
        self.assertEqual(parsed["system_time_offset_seconds"], "0.001704435")
        self.assertEqual(parsed["conditional_error_bound_seconds"], "0.035640914")
        self.assertEqual(parsed["stratum"], 3)

    def test_signed_system_offset_survives_and_bound_stays_nonnegative(self):
        parsed = parse_tracking(TRACKING.replace(",0.001704435,", ",-0.001704435,"))
        self.assertEqual(parsed["system_time_offset_seconds"], "-0.001704435")
        self.assertEqual(parsed["conditional_error_bound_seconds"], "0.035640914")

    def test_rejects_failed_unsynchronized_local_and_unknown_formats(self):
        for raw, code in (
            (TRACKING, 1),
            (TRACKING, False),
            (TRACKING.replace("Normal", "Not synchronised"), 0),
            (TRACKING.replace("334FA8DC", "7F7F0101"), 0),
            (TRACKING.replace("334FA8DC", "00000000"), 0),
            (TRACKING.replace(",3,", ",16,", 1), 0),
            (TRACKING.replace(",0.001704435,", ",NaN,"), 0),
            (TRACKING.replace(",0.001704435,", ",1e999999999,"), 0),
            (TRACKING.replace(",0.029829502,", ",-1,"), 0),
            (TRACKING + "\n" + TRACKING, 0),
            ("ref,2,0,0.001,0,0,0,0,0,0,0,0,Normal", 0),
        ):
            with self.subTest(raw=raw, code=code), self.assertRaises(ValueError):
                parse_tracking(raw, code)

    def test_new_claim_must_match_correct_column_and_parser(self):
        self.assertTrue(assess_clock(raw_clock(), claim())["original_claim_valid"])
        with self.assertRaises(ValueError):
            assess_clock(raw_clock(), claim("1793813391.074799414"))
        invalid = raw_clock()
        invalid["parser_version"] = "future-unknown-parser"
        with self.assertRaises(ValueError):
            assess_clock(invalid, claim())

    def test_legacy_reference_epoch_claim_is_preserved_but_never_trusted(self):
        raw = raw_clock(versioned=False)
        original = claim("1793813391.074799414")
        before = copy.deepcopy((raw, original))
        result = assess_clock(raw, original)
        self.assertEqual(result["status"], "DERIVED_FROM_RETAINED_RAW")
        self.assertFalse(result["original_claim_valid"])
        self.assertEqual(result["system_time_offset_seconds"], "0.001704435")
        self.assertEqual((raw, original), before)

    def test_legacy_synthetic_thirteen_fields_remain_unknown(self):
        raw = raw_clock(versioned=False, stdout="ref,2,0,0.001,0,0,0,0,0,0,0,0,Normal")
        result = assess_clock(raw, claim("0.001"))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["system_time_offset_seconds"])
        with self.assertRaises(ValueError):
            assess_clock(raw, claim("0.002"))


class RetainedClockTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def retained(self, raw, offset):
        identity = "clock_" + digest(raw)
        path = self.root / "timing/clocks" / (identity + ".json")
        atomic_json(path, raw)
        measured = claim(offset)
        measured["evidence_id"] = identity
        row = make_attempt(
            "clock-test",
            detector_version="CLOCK_TEST_V1",
            universe_snapshot_id="declared-universe",
            evidence_id="clock-test",
            evidence_kind="synthetic",
            recorded_at=NOW,
            status="STARTED",
            source="test",
            clock=measured,
        )
        return path, row

    def test_collector_retains_versioned_raw_and_correct_offset(self):
        process = SimpleNamespace(returncode=0, stdout=TRACKING + "\n", stderr="")
        with patch("idxsig.runtime.timing.shutil.which", return_value="/usr/bin/chronyc"):
            result = clock_observation(self.root, clock=lambda: NOW, runner=lambda *a, **k: process)
        self.assertEqual(result["offset_seconds"], "0.001704435")
        path = self.root / "timing/clocks" / (result["evidence_id"] + ".json")
        self.assertEqual(read_json(path)["parser_version"], PARSER_VERSION)
        self.assertEqual(read_json(path)["stdout"], TRACKING + "\n")

    def test_collector_canonicalizes_clock_before_linking_retained_evidence(self):
        for timestamp in ("2026-11-04T17:30:52+00:00", "2026-11-04T23:00:52+05:30"):
            for returncode in (0, 1):
                with self.subTest(timestamp=timestamp, returncode=returncode):
                    process = SimpleNamespace(returncode=returncode, stdout=TRACKING, stderr="")
                    with patch(
                        "idxsig.runtime.timing.shutil.which", return_value="/usr/bin/chronyc"
                    ):
                        result = clock_observation(
                            self.root, clock=lambda: timestamp, runner=lambda *a, **k: process
                        )
                    self.assertEqual(result["observed_at"], NOW)
                    path = self.root / "timing/clocks" / (result["evidence_id"] + ".json")
                    before = path.read_bytes()
                    self.assertEqual(read_json(path)["observed_at"], NOW)
                    row = make_attempt(
                        "canonical-clock-" + str(returncode),
                        detector_version="CLOCK_TEST_V1",
                        universe_snapshot_id="declared-universe",
                        evidence_id="clock-test",
                        evidence_kind="synthetic",
                        recorded_at=timestamp,
                        status="STARTED",
                        source="test",
                        clock=result,
                    )
                    append_attempt(self.root, row)
                    retained = next(
                        item for item in read_attempts(self.root) if item["id"] == row["id"]
                    )
                    self.assertTrue(verify_linked_evidence(self.root, [retained])["ok"])
                    self.assertEqual(path.read_bytes(), before)

    def test_unavailable_clock_paths_also_canonicalize_observation_time(self):
        timestamp = "2026-11-04T17:30:52+00:00"
        with patch("idxsig.runtime.timing.shutil.which", return_value=None):
            result = clock_observation(self.root, clock=lambda: timestamp)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["observed_at"], NOW)
        with patch("idxsig.runtime.timing.shutil.which", return_value="/usr/bin/chronyc"):
            with patch(
                "subprocess.run", side_effect=subprocess.TimeoutExpired("chronyc", 2)
            ) as run:
                result = clock_observation(self.root, clock=lambda: timestamp, runner=run)
        self.assertEqual(result["status"], "MEASUREMENT_FAILED")
        self.assertEqual(result["observed_at"], NOW)
        self.assertIsNone(result["evidence_id"])
        self.assertFalse((self.root / "timing").exists())

    def test_retained_clock_still_rejects_a_different_observation_instant(self):
        path, row = self.retained(raw_clock(), "0.001704435")
        before = path.read_bytes()
        row["clock"]["observed_at"] = "2026-11-04T17:30:51.999999Z"
        with self.assertRaisesRegex(ValueError, "observation time mismatch"):
            assess_retained_clock(self.root, row)
        self.assertEqual(path.read_bytes(), before)

    def test_failed_measurement_keeps_original_raw_evidence(self):
        process = SimpleNamespace(returncode=1, stdout=TRACKING, stderr="unavailable")
        with patch("idxsig.runtime.timing.shutil.which", return_value="/usr/bin/chronyc"):
            result = clock_observation(self.root, clock=lambda: NOW, runner=lambda *a, **k: process)
        self.assertEqual(result["status"], "MEASUREMENT_FAILED")
        self.assertIsNone(result["offset_seconds"])
        self.assertTrue((self.root / "timing/clocks" / (result["evidence_id"] + ".json")).exists())

    def test_missing_chrony_is_unknown_and_does_not_probe(self):
        with patch("idxsig.runtime.timing.shutil.which", return_value=None):
            result = clock_observation(self.root, clock=lambda: NOW)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["offset_seconds"])
        self.assertFalse((self.root / "timing").exists())

    def test_legacy_integrity_and_corrected_measurement_are_separate(self):
        path, row = self.retained(raw_clock(versioned=False), "1793813391.074799414")
        before = path.read_bytes()
        evidence = verify_linked_evidence(self.root, [row])
        self.assertTrue(evidence["ok"])
        self.assertFalse(evidence["complete"])
        checks = [item for item in evidence["checks"] if item["kind"] == "clock_measurement"]
        self.assertEqual(checks[0]["status"], "DECLARED")
        self.assertFalse(checks[0]["assessment"]["original_claim_valid"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(row["clock"]["offset_seconds"], "1793813391.074799414")

    def test_new_measurement_verified_but_tamper_and_symlink_fail(self):
        path, row = self.retained(raw_clock(), "0.001704435")
        self.assertEqual(assess_retained_clock(self.root, row)["status"], "VERIFIED")
        row["clock"]["offset_seconds"] = "0.009"
        self.assertFalse(verify_linked_evidence(self.root, [row])["ok"])
        row["clock"]["offset_seconds"] = "0.001704435"
        target = self.root / "moved.json"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            assess_retained_clock(self.root, row)


if __name__ == "__main__":
    unittest.main()

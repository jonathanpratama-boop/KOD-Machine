"""chronyc -c tracking is read under an explicit layout, checked against a real capture.

The fixture in fixtures/real/ is the exact stdout the production observer retained on
2026-11-04 (see fixtures/real/README.md). Every other sample is the real line with one
stated edit, or the invented 13-field line the first parser's test used. Expected
values are literals: this file is the specification, not a mirror of the parser.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from idxsig.runtime.storage import atomic_json, digest, read_json
from idxsig.runtime.timing import clock_observation
from idxsig.runtime.timing_evidence import verify_linked_evidence
from idxsig.timing_capture import make_attempt

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "real"
REAL_STDOUT = (FIXTURE / "chronyc_tracking_20261104T123000Z.txt").read_bytes().decode("utf-8")
REAL_LINE = REAL_STDOUT.rstrip("\n")
REAL_OBSERVED_AT = "2026-11-04T12:30:00.034011Z"
REAL_RECORDED_AT = "2026-11-04T12:30:04.123087Z"
REAL_ATTEMPT_ID = "attempt_961e650bb6504be698974b104301dd7b"
# Identity and stored offset of the production v1 clock record (journal sequence 10).
REAL_CLOCK_ID = "clock_44499b11c6b067fc2239684750462ec5b9140169be0e71a34c4b56c6fda019c0"
REAL_V1_OFFSET = "1793795343.592268319"
REAL_SYSTEM_OFFSET = "0.002434953"
INVENTED_13_FIELDS = "ref,2,0,0.001,0,0,0,0,0,0,0,0,Normal"


def edited(index, value):
    fields = REAL_LINE.split(",")
    fields[index] = value
    return ",".join(fields) + "\n"


def observe(root, stdout, *, returncode=0):
    """Run the production clock probe against a fake installed chronyc."""

    def runner(command, **options):
        if command != ["/usr/bin/chronyc", "-c", "tracking"]:
            raise AssertionError(f"unexpected clock command: {command!r}")
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")

    with patch("idxsig.runtime.timing.shutil.which", return_value="/usr/bin/chronyc"):
        return clock_observation(root, clock=lambda: REAL_OBSERVED_AT, runner=runner)


class ClockObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def retained(self, observation):
        return read_json(self.root / "timing" / "clocks" / (observation["evidence_id"] + ".json"))

    def test_real_server_sample_reads_system_offset_field(self):
        observation = observe(self.root, REAL_STDOUT)
        self.assertEqual(observation["status"], "MEASURED_EXTERNAL")
        self.assertEqual(observation["offset_seconds"], REAL_SYSTEM_OFFSET)
        evidence = self.retained(observation)
        self.assertEqual(evidence["stdout"], REAL_STDOUT)
        self.assertEqual(evidence["parser_version"], "CHRONY_TRACKING_CSV_V2")

    def test_invented_thirteen_field_shape_is_measurement_failed(self):
        observation = observe(self.root, INVENTED_13_FIELDS)
        self.assertEqual(observation["status"], "MEASUREMENT_FAILED")
        self.assertIsNone(observation["offset_seconds"])
        self.assertEqual(self.retained(observation)["stdout"], INVENTED_13_FIELDS)

    def test_any_other_layout_is_measurement_failed_never_guessed(self):
        cases = {
            "fifteen fields": REAL_LINE + ",0.0\n",
            "leap status not Normal": edited(13, "Not synchronised"),
            "offset not a number": edited(4, "fast"),
            "offset not finite": edited(4, "NaN"),
            "reference ID not hexadecimal": edited(0, "ref"),
            "stratum not an integer": edited(2, "3.0"),
            "two lines": REAL_STDOUT * 2,
            "empty output": "",
        }
        for name, stdout in cases.items():
            with self.subTest(name):
                observation = observe(self.root, stdout)
                self.assertEqual(observation["status"], "MEASUREMENT_FAILED")
                self.assertIsNone(observation["offset_seconds"])
        observation = observe(self.root, REAL_STDOUT, returncode=1)
        self.assertEqual(observation["status"], "MEASUREMENT_FAILED")


class ClockVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def retain(self, evidence):
        identity = "clock_" + digest(evidence)
        atomic_json(self.root / "timing" / "clocks" / (identity + ".json"), evidence)
        return identity

    def verify(self, clock):
        row = make_attempt(
            REAL_ATTEMPT_ID,
            detector_version="INTRADAY_OBSERVATION_V1",
            universe_snapshot_id="legacy:universe",
            evidence_id=REAL_ATTEMPT_ID,
            evidence_kind="prospective",
            recorded_at=REAL_RECORDED_AT,
            status="COMPLETED",
            source="BINANCE_SPOT_PUBLIC",
            times={"started_at": "2026-11-04T12:30:00.020716Z"},
            clock=clock,
        )
        result = verify_linked_evidence(self.root, [row])
        (check,) = [c for c in result["checks"] if c["kind"] == "clock"]
        return result, check

    def legacy(self, stdout, offset, *, status="MEASURED_EXTERNAL"):
        # The exact object the unversioned parser wrote: it has no parser_version key.
        evidence = {
            "observed_at": REAL_OBSERVED_AT,
            "command": "chronyc -c tracking",
            "returncode": 0,
            "stdout": stdout,
            "stderr": "",
        }
        return {
            "status": status,
            "offset_seconds": offset,
            "observed_at": REAL_OBSERVED_AT,
            "evidence_id": self.retain(evidence),
        }

    def test_v2_record_verifies_against_system_offset_field(self):
        result, check = self.verify(observe(self.root, REAL_STDOUT))
        self.assertTrue(result["ok"])
        self.assertEqual(check["status"], "VERIFIED")
        self.assertEqual(result["diagnostics"], [])

    def test_v2_failed_record_verifies_only_when_raw_output_also_fails(self):
        result, check = self.verify(observe(self.root, INVENTED_13_FIELDS))
        self.assertTrue(result["ok"])
        self.assertEqual(check["status"], "VERIFIED")
        measured = observe(self.root, REAL_STDOUT)
        result, check = self.verify(
            {**measured, "status": "MEASUREMENT_FAILED", "offset_seconds": None}
        )
        self.assertFalse(result["ok"])
        self.assertIn("CHRONY_TRACKING_CSV_V2", check["reason"])

    def test_v2_record_with_changed_offset_or_raw_output_fails(self):
        clock = observe(self.root, REAL_STDOUT)
        result, check = self.verify({**clock, "offset_seconds": "0.002434954"})
        self.assertEqual(check["status"], "FAIL")
        # Edited output retained under its own new identity: only the re-read catches it.
        evidence = {
            "observed_at": REAL_OBSERVED_AT,
            "command": "chronyc -c tracking",
            "parser_version": "CHRONY_TRACKING_CSV_V2",
            "returncode": 0,
            "stdout": edited(4, "0.000000001"),
            "stderr": "",
        }
        result, check = self.verify({**clock, "evidence_id": self.retain(evidence)})
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("CHRONY_TRACKING_CSV_V2", check["reason"])
        path = self.root / "timing" / "clocks" / (clock["evidence_id"] + ".json")
        path.write_bytes(path.read_bytes().replace(b"0.002434953", b"0.002434954"))
        result, check = self.verify(clock)
        self.assertEqual(check["status"], "FAIL")
        path.unlink()
        result, check = self.verify(clock)
        self.assertFalse(result["ok"])
        self.assertEqual(check["status"], "UNAVAILABLE")

    def test_unsupported_parser_version_fails(self):
        evidence = {
            "observed_at": REAL_OBSERVED_AT,
            "command": "chronyc -c tracking",
            "parser_version": "CHRONY_TRACKING_CSV_V3",
            "returncode": 0,
            "stdout": REAL_STDOUT,
            "stderr": "",
        }
        clock = {
            "status": "MEASURED_EXTERNAL",
            "offset_seconds": REAL_SYSTEM_OFFSET,
            "observed_at": REAL_OBSERVED_AT,
            "evidence_id": self.retain(evidence),
        }
        result, check = self.verify(clock)
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("CHRONY_TRACKING_CSV_V3", check["reason"])

    def test_production_v1_record_verifies_as_written_and_reports_offset_defect(self):
        clock = self.legacy(REAL_STDOUT, REAL_V1_OFFSET)
        self.assertEqual(clock["evidence_id"], REAL_CLOCK_ID)  # fixture bytes are the original
        result, check = self.verify(clock)
        self.assertTrue(result["ok"])
        self.assertEqual(check["status"], "VERIFIED")
        (diagnostic,) = result["diagnostics"]
        reason = diagnostic.pop("reason")
        self.assertEqual(
            diagnostic,
            {
                "code": "OFFSET_FIELD_DEFECT_V1",
                "kind": "clock",
                "id": REAL_CLOCK_ID,
                "attempt_id": REAL_ATTEMPT_ID,
                "recorded_offset_seconds": REAL_V1_OFFSET,
                "recorded_field": "reference_time",
                "corrected_offset_seconds": REAL_SYSTEM_OFFSET,
                "corrected_by": "CHRONY_TRACKING_CSV_V2",
            },
        )
        self.assertIn("field index 3", reason)

    def test_v1_record_without_fourteen_fields_reports_defect_without_correction(self):
        result, check = self.verify(self.legacy(INVENTED_13_FIELDS, "0.001"))
        self.assertTrue(result["ok"])
        self.assertEqual(check["status"], "VERIFIED")
        (diagnostic,) = result["diagnostics"]
        self.assertEqual(diagnostic["code"], "OFFSET_FIELD_DEFECT_V1")
        self.assertIsNone(diagnostic["corrected_offset_seconds"])
        self.assertIn("found 13", diagnostic["reason"])

    def test_v1_failed_record_verifies_without_offset_defect(self):
        # The unversioned parser stored no offset for an unsynchronised clock: none is defective.
        clock = self.legacy(edited(13, "Not synchronised"), None, status="MEASUREMENT_FAILED")
        result, check = self.verify(clock)
        self.assertTrue(result["ok"])
        self.assertEqual(check["status"], "VERIFIED")
        self.assertEqual(result["diagnostics"], [])

    def test_v1_record_with_tampered_raw_output_fails(self):
        clock = self.legacy(edited(3, "1793795343.000000000"), REAL_V1_OFFSET)
        result, check = self.verify(clock)
        self.assertFalse(result["ok"])
        self.assertEqual(check["reason"], "clock measurement differs from retained raw output")
        self.assertEqual(result["diagnostics"], [])
        clock = self.legacy(REAL_STDOUT, REAL_V1_OFFSET)
        path = self.root / "timing" / "clocks" / (REAL_CLOCK_ID + ".json")
        path.write_bytes(path.read_bytes().replace(b"Normal", b"Unsync"))
        result, check = self.verify(clock)
        self.assertFalse(result["ok"])
        self.assertEqual(check["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

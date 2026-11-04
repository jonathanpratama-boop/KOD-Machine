"""The production server's real chronyc capture, read by idxsig.runtime.clock.

The fixture in fixtures/real/ is the exact stdout the production observer retained on
2026-11-04 (see fixtures/real/README.md). Expected values are literals copied from that
capture: this file checks the parser against reality, not against itself.
"""

from __future__ import annotations

from pathlib import Path
import unittest

from idxsig.runtime.clock import PARSER_VERSION, assess_clock, parse_tracking
from idxsig.runtime.storage import digest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "real"
REAL_STDOUT = (FIXTURE / "chronyc_tracking_20261104T123000Z.txt").read_bytes().decode("utf-8")
REAL_OBSERVED_AT = "2026-11-04T12:30:00.034011Z"
# Identity and stored offset of the production unversioned clock record (journal sequence 10).
REAL_CLOCK_ID = "clock_44499b11c6b067fc2239684750462ec5b9140169be0e71a34c4b56c6fda019c0"
REAL_STORED_OFFSET = "1793795343.592268319"
REAL_SYSTEM_OFFSET = "0.002434953"


def production_evidence():
    """The clock evidence object exactly as the unversioned observer wrote it."""
    return {
        "observed_at": REAL_OBSERVED_AT,
        "command": "chronyc -c tracking",
        "returncode": 0,
        "stdout": REAL_STDOUT,
        "stderr": "",
    }


class RealChronySampleTests(unittest.TestCase):
    def test_fixture_bytes_are_the_production_capture(self):
        self.assertEqual("clock_" + digest(production_evidence()), REAL_CLOCK_ID)

    def test_parser_reads_the_system_offset_field(self):
        parsed = parse_tracking(REAL_STDOUT)
        self.assertEqual(parsed["parser_version"], PARSER_VERSION)
        self.assertEqual(parsed["system_time_offset_seconds"], REAL_SYSTEM_OFFSET)
        self.assertEqual(parsed["reference_epoch_seconds"], REAL_STORED_OFFSET)

    def test_stored_legacy_value_is_the_reference_time_not_an_offset(self):
        claim = {
            "status": "MEASURED_EXTERNAL",
            "offset_seconds": REAL_STORED_OFFSET,
            "observed_at": REAL_OBSERVED_AT,
            "evidence_id": REAL_CLOCK_ID,
        }
        assessment = assess_clock(production_evidence(), claim)
        self.assertEqual(assessment["status"], "DERIVED_FROM_RETAINED_RAW")
        self.assertFalse(assessment["original_claim_valid"])
        self.assertEqual(assessment["original_offset_seconds"], REAL_STORED_OFFSET)
        self.assertEqual(assessment["system_time_offset_seconds"], REAL_SYSTEM_OFFSET)

    def test_invented_thirteen_field_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_tracking("ref,2,0,0.001,0,0,0,0,0,0,0,0,Normal")


if __name__ == "__main__":
    unittest.main()

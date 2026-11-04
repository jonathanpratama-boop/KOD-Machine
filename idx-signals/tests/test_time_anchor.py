"""External stamps preserve original decisions and actual retry times."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from idxsig.runtime.time_anchor import anchor_batch, verify_anchor


@dataclass
class Stamp:
    authority: str
    token: bytes


class FixtureStamper:
    authorities = {"fixture": None}
    last_errors = []

    def __init__(self, *, fail=False, late=False):
        self.calls = 0
        self.fail = fail
        self.late = late

    def stamp(self, data):
        self.calls += 1
        if self.fail:
            raise OSError("unreachable")
        return [Stamp("fixture", b"signed:" + data)]

    def verify(self, authority, token, data):
        if authority != "fixture" or token != b"signed:" + data:
            raise ValueError("signature mismatch")
        return datetime(2026, 11, 4, 1 if self.late else 0, 1, tzinfo=timezone.utc)


class TimeAnchorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "runtime"
        self.payload = {"decision_at": "2026-11-04T00:00:00Z", "candidates": ["synthetic"],
                        "outcome_window_start": "2026-11-04T00:30:00Z"}

    def test_disabled_does_not_create_files_or_call_authority(self):
        stamper = FixtureStamper()
        self.assertEqual(anchor_batch(self.root, self.payload, stamper=stamper)["status"], "DISABLED")
        self.assertFalse(self.root.exists())
        self.assertEqual(stamper.calls, 0)

    def test_round_trip_and_retry_keep_original_bytes(self):
        stamper = FixtureStamper()
        result = anchor_batch(self.root, self.payload, enabled=True, stamper=stamper)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["before_outcome_window"])
        folder = self.root / "timing" / "anchors" / result["anchor_id"]
        before = {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
        again = anchor_batch(self.root, self.payload, enabled=True, stamper=stamper)
        self.assertEqual(again["anchor_id"], result["anchor_id"])
        self.assertEqual(stamper.calls, 1)
        self.assertEqual(before, {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()})

    def test_failed_attempt_retains_payload_and_late_retry_stays_late(self):
        first = anchor_batch(self.root, self.payload, enabled=True, stamper=FixtureStamper(fail=True))
        self.assertEqual(first["status"], "UNAVAILABLE")
        result = anchor_batch(self.root, self.payload, enabled=True, stamper=FixtureStamper(late=True))
        self.assertEqual(result["anchor_id"], first["anchor_id"])
        self.assertFalse(result["before_outcome_window"])
        self.assertEqual(result["timestamp_minus_decision_seconds"], 3660)
        folder = self.root / "timing" / "anchors" / result["anchor_id"]
        self.assertEqual(len(list((folder / "attempts").glob("*.json"))), 2)

    def test_tampered_payload_is_fail_not_a_new_timestamp(self):
        stamper = FixtureStamper()
        result = anchor_batch(self.root, self.payload, enabled=True, stamper=stamper)
        path = self.root / "timing" / "anchors" / result["anchor_id"] / "payload.json"
        path.write_bytes(b"changed")
        self.assertEqual(verify_anchor(self.root, result["anchor_id"], verifier=stamper)["status"], "FAIL")
        with self.assertRaises(ValueError):
            anchor_batch(self.root, self.payload, enabled=True, stamper=stamper)
        self.assertEqual(stamper.calls, 1)

    def test_missing_dependency_is_unavailable_with_payload_retained(self):
        with patch("idxsig.runtime.time_anchor._checker", return_value=None):
            result = anchor_batch(self.root, self.payload, enabled=True)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertTrue((self.root / "timing" / "anchors" / result["anchor_id"] / "payload.json").is_file())

    def test_missing_anchor_and_unsafe_ids(self):
        self.assertEqual(verify_anchor(self.root, "a" * 64)["status"], "UNAVAILABLE")
        with self.assertRaises(ValueError):
            verify_anchor(self.root, "../outside")

    def test_invalid_times_and_nonfinite_values_are_rejected(self):
        for payload in ({"decision_at": "2026-11-04"}, {"value": float("nan")}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                anchor_batch(self.root, payload)

    def test_original_invalid_token_rejected_by_real_offline_verifier(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        fixture = FixtureStamper()
        result = anchor_batch(self.root, self.payload, enabled=True, stamper=fixture)
        folder = self.root / "timing" / "anchors" / result["anchor_id"]
        (folder / "fixture.tsr").unlink()
        (folder / "freetsa.tsr").write_bytes(b"not a valid RFC3161 token")
        checked = verify_anchor(self.root, result["anchor_id"], verifier=RFC3161Timestamper())
        self.assertEqual(checked["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

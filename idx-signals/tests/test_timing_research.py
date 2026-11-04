import copy
import hashlib
import json
from pathlib import Path
import unittest
from idxsig.timing_research import diagnose


def record():
    return {
        "id": "a",
        "detector_version": "v1",
        "evidence_kind": "synthetic",
        "universe_snapshot_id": "u1",
        "evidence_id": "e1",
        "published_at": "2026-11-01T00:00:00Z",
        "received_at": "2026-11-01T00:00:02Z",
        "detected_at": "2026-11-01T00:00:10Z",
        "decision_at": "2026-11-01T00:00:20Z",
    }


class TimingTests(unittest.TestCase):
    def test_preserved_report_bytes_match_observed_git_blobs(self):
        root = Path(__file__).resolve().parents[2] / "docs/research_sources/hermes_20261104"
        manifest = json.loads((root / "manifest.json").read_text())
        for row in manifest["sources"]:
            raw = (root / row["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
            header = b"blob " + str(len(raw)).encode() + b"\0"
            self.assertEqual(hashlib.sha1(header + raw).hexdigest(), row["git_blob_sha1"])

    def test_missing_fill_is_unknown_not_zero(self):
        out = diagnose([record()], as_of="2026-11-02T00:00:00Z")
        stages = out["cohorts"][0]["stages"]
        self.assertEqual(stages["received_at_to_detected_at"]["median_seconds"], 8)
        self.assertEqual(stages["executable_at_to_fill_at"]["unknown"], 1)
        self.assertIsNone(stages["executable_at_to_fill_at"]["median_seconds"])
        self.assertFalse(out["entry_permission"])

    def test_future_outcomes_never_change_diagnostic(self):
        r = record()
        expected = diagnose([r], as_of="2026-11-02T00:00:00Z")
        r["outcome"] = {"net_return": 900, "observed_at": "2030-01-01T00:00:00Z"}
        self.assertEqual(diagnose([r], as_of="2026-11-02T00:00:00Z"), expected)

    def test_future_reversed_duplicate_and_unproven_identity_rejected(self):
        for field, value in [
            ("detected_at", "2030-01-01T00:00:00Z"),
            ("received_at", "2026-11-01T00:00:15Z"),
            ("universe_snapshot_id", None),
        ]:
            r = record()
            r[field] = value
            with self.assertRaises(ValueError):
                diagnose([r], as_of="2026-11-02T00:00:00Z")
        with self.assertRaises(ValueError):
            diagnose([record(), record()], as_of="2026-11-02T00:00:00Z")

    def test_cohorts_and_synthetic_never_pooled(self):
        r = record()
        p = copy.deepcopy(r)
        p.update(id="b", evidence_kind="prospective")
        t = copy.deepcopy(r)
        t.update(id="c", detector_version="v2")
        out = diagnose([r, p, t], as_of="2026-11-02T00:00:00Z")
        self.assertEqual(len(out["cohorts"]), 3)
        self.assertTrue(all(c["attempts"] == 1 for c in out["cohorts"]))

    def test_tape_can_lack_publication_time(self):
        r = record()
        r.pop("published_at")
        out = diagnose([r], as_of="2026-11-02T00:00:00Z")
        self.assertEqual(out["missing_stages"]["published_at"], 1)
        self.assertIsNone(
            out["cohorts"][0]["stages"]["published_at_to_received_at"]["median_seconds"]
        )


if __name__ == "__main__":
    unittest.main()

"""Deleting linked evidence cannot leave a timing integrity report green."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from idxsig.runtime.intraday import PublicResponse, collect_intraday
from idxsig.runtime.storage import atomic_json, digest
from idxsig.runtime.timing_evidence import verify_linked_evidence
from idxsig.timing_capture import make_attempt
from idxsig.timing_context import build_timing_context, context_fixture

NOW = "2026-11-04T00:30:00Z"


class LinkedTimingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.membership = {
            "schema_version": "KOD_TIMING_MEMBERSHIP_V1",
            "id": "attempt_fixture",
            "recorded_at": NOW,
            "members": ["BTCUSDT"],
            "coverage": "REQUESTED_MEMBERSHIP_ONLY",
            "entry_permission": False,
        }
        self.member_id = "membership_" + digest(self.membership)
        self.member_path = self.root / "timing" / "memberships" / (self.member_id + ".json")
        atomic_json(self.member_path, self.membership)
        self.row = make_attempt(
            "attempt_fixture",
            detector_version="fixture",
            universe_snapshot_id=self.member_id,
            evidence_id="fixture",
            evidence_kind="synthetic",
            recorded_at=NOW,
            status="COMPLETED",
            source="fixture",
            times={"started_at": NOW},
        )

    def verify(self, rows=None):
        return verify_linked_evidence(self.root, [self.row] if rows is None else rows)

    def test_original_membership_verified_and_deletion_blocks_integrity(self):
        self.assertTrue(self.verify()["ok"])
        self.member_path.unlink()
        result = self.verify()
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"]["unavailable"], 1)

    def test_membership_tamper_and_reserialization_fail(self):
        self.member_path.write_text(json.dumps(self.membership))
        self.assertFalse(self.verify()["ok"])
        atomic_json(self.member_path, {**self.membership, "members": []})
        self.assertFalse(self.verify()["ok"])

    def test_membership_cannot_be_reused_for_another_owner(self):
        self.row["id"] = "other-attempt"
        self.assertFalse(self.verify()["ok"])

    def test_request_child_may_share_retained_parent_membership(self):
        child = copy.deepcopy(self.row)
        child["id"] += ":request:0"
        child["links"] = {"parent_attempt_id": self.row["id"]}
        self.assertTrue(self.verify([self.row, child])["ok"])
        self.assertFalse(self.verify([child])["ok"])

    def test_external_legacy_universe_remains_declared_unverified(self):
        self.row["universe_snapshot_id"] = "legacy:universe"
        result = self.verify()
        self.assertTrue(result["ok"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["counts"]["declared"], 1)

    def test_symlink_membership_is_rejected_even_inside_root(self):
        original = self.root / "copy.json"
        self.member_path.rename(original)
        self.member_path.symlink_to(original)
        self.assertFalse(self.verify()["ok"])

    def test_capture_link_checks_nested_raw_bytes(self):
        path = self.root / "timing" / "captures" / (self.row["id"] + ".json")

        def clock():
            return datetime(2026, 11, 4, 0, 30, tzinfo=timezone.utc)

        # A blocked response still has a retained denominator and original bytes.
        value = collect_intraday(
            path,
            self.root / "evidence",
            ["BTCUSDT"],
            scheduled_at=NOW,
            bars=2,
            fetcher=lambda *a, **kw: PublicResponse(451, b"blocked fixture"),
            clock=clock,
            evidence_kind="synthetic",
        )
        self.row["links"] = {
            "capture_path": path.relative_to(self.root).as_posix(),
            "capture_sha256": value["capture_sha256"],
            "capture_membership_id": value["membership_snapshot_id"],
        }
        self.assertTrue(self.verify()["ok"])
        raw = self.root / "evidence" / value["evidence"][0]["path"]
        raw.write_bytes(b"changed")
        self.assertFalse(self.verify()["ok"])

    def test_unsafe_capture_link_is_rejected(self):
        self.row["links"] = {"capture_path": "../outside.json", "capture_sha256": "a" * 64}
        self.assertFalse(self.verify()["ok"])

    def test_context_rebuild_retains_input_costs_and_requires_linked_file(self):
        payload = context_fixture()
        body = {
            "recorded_at": NOW,
            "as_of": NOW,
            "input": payload,
            "input_sha256": digest(payload),
            "context": build_timing_context(payload, as_of=NOW),
        }
        identity = digest(body)
        path = self.root / "timing" / "contexts" / (identity + ".json")
        atomic_json(
            path,
            {"schema_version": "KOD_TIMING_CONTEXT_RECORD_V1", "payload": body, "sha256": identity},
        )
        self.row["links"]["context_id"] = identity
        self.assertTrue(self.verify()["ok"])
        path.unlink()
        self.assertFalse(self.verify()["ok"])

    def test_changed_derived_context_fails_even_with_new_outer_hash(self):
        payload = context_fixture()
        body = {
            "recorded_at": NOW,
            "as_of": NOW,
            "input": payload,
            "input_sha256": digest(payload),
            "context": build_timing_context(payload, as_of=NOW),
        }
        body["context"]["shadow"][0]["cost_profile_sha256"] = "a" * 64
        identity = digest(body)
        atomic_json(
            self.root / "timing" / "contexts" / (identity + ".json"),
            {"schema_version": "KOD_TIMING_CONTEXT_RECORD_V1", "payload": body, "sha256": identity},
        )
        self.assertFalse(self.verify()["ok"])

    def test_optional_anchor_missing_payload_is_required_failure(self):
        self.row["links"]["anchor_id"] = "a" * 64
        self.assertFalse(self.verify()["ok"])


if __name__ == "__main__":
    unittest.main()

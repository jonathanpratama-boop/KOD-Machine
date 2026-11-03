"""Candidate chronology, persistence and permission boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from idxsig.runtime.candidates import assessments, project, record_assessment, verify_assessments
from idxsig.runtime.storage import read_snapshot, write_snapshot

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-01T01:00:00Z"
T2 = "2026-01-01T02:00:00Z"
T3 = "2026-01-01T03:00:00Z"


def request(**changes):
    value = {"candidate_id": "TAPE:TEST:BTCUSDT:2026-01-01", "state": "RESEARCHED",
             "as_of": T1, "owner": "analyst", "reason": "Study peer participation",
             "mechanism": "Possible group repricing", "counterarguments": ["Common beta may explain the move"],
             "blockers": ["No independently validated entry policy"], "clearing_evidence": ["Out-of-sample evidence"],
             "expires_at": T3, "recheck_at": T2,
             "evidence": [{"id": "source-1", "source": "retained://fixture",
                           "available_at": T0, "observed_at": T0, "statement": "Peers rose in the observed sample"}]}
    value.update(changes)
    return value


class CandidateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidate = {"id": request()["candidate_id"], "state": "DETECTED", "as_of": T0,
                          "detected_at": T0, "instrument_id": "TEST:BTCUSDT", "reasons": ["Original detection"]}
        self.payload = {"run": {"id": "r1", "as_of": T2}, "candidates": [self.candidate]}
        self.original = write_snapshot(self.root, self.payload)

    def test_assessment_retry_and_projection_preserve_original_observation(self):
        first = record_assessment(self.root, request())
        before = (self.root / "candidate_assessments.jsonl").read_bytes()
        self.assertEqual(record_assessment(self.root, request()), first)
        self.assertEqual((self.root / "candidate_assessments.jsonl").read_bytes(), before)
        self.assertEqual(verify_assessments(self.root)["assessments"], 1)
        payload = read_snapshot(self.root)["payload"]
        row = payload["candidates"][0]
        self.assertEqual(row["state"], "RESEARCHED")
        self.assertEqual(row["detector_state"], "DETECTED")
        self.assertEqual(row["reasons"], ["Original detection"])
        self.assertEqual(row["as_of"], T0)
        self.assertFalse(row["entry_permission"])
        self.assertEqual(payload["assessment_projection"]["base_snapshot_sha256"], self.original["sha256"])
        self.assertEqual(payload["run"], self.payload["run"])

    def test_revision_requires_latest_parent_and_keeps_both_versions(self):
        first = record_assessment(self.root, request())
        with self.assertRaisesRegex(ValueError, "superseded"):
            record_assessment(self.root, request(reason="Updated reason"))
        second = record_assessment(self.root, request(reason="Updated reason", supersedes=first["id"], as_of=T2,
                                                      recheck_at=None))
        self.assertEqual(second["version"], 2)
        self.assertEqual(assessments(self.root)[0], first)
        self.assertEqual(second["supersedes"], first["id"])
        self.assertEqual(read_snapshot(self.root)["payload"]["assessment_projection"]["base_snapshot_sha256"], self.original["sha256"])

    def test_future_evidence_unknown_candidate_and_backdating_fail_before_write(self):
        future = request()
        future["evidence"][0]["observed_at"] = T3
        for value in (future, request(candidate_id="invented"), request(as_of="2025-12-31T00:00:00Z"), request(as_of=T3, expires_at="2026-01-02T00:00:00Z", recheck_at=None)):
            with self.assertRaises(ValueError):
                record_assessment(self.root, value)
        self.assertFalse((self.root / "candidate_assessments.jsonl").exists())

    def test_entry_eligibility_cannot_be_granted_by_plan_or_narrative(self):
        with self.assertRaisesRegex(ValueError, "no approved"):
            record_assessment(self.root, request(state="ENTRY_ELIGIBLE", blockers=[]))
        with self.assertRaises(ValueError):
            record_assessment(self.root, request(state="CONDITIONAL_READY", blockers=[], plan={"status": "approved"}))
        with self.assertRaises(ValueError):
            record_assessment(self.root, request(entry_permission=True))

    def test_conditional_readiness_requires_full_declared_plan_and_still_grants_no_entry(self):
        first = record_assessment(self.root, request())
        plan = {"side": "LONG", "entry_lower": "100", "entry_upper": "101", "protective_price": "97",
                "loss_budget": "10", "ordinary_loss": "8", "stress_loss": "12", "gap_loss": "20",
                "round_trip_cost_fraction": ".02", "trigger": "Named future result exceeds frozen threshold",
                "invalidation": "Mechanism fails", "protection_basis": "Sourced structural level",
                "target_action": "Review target touch", "cancellation": "Cancel at expiry", "horizon": "1 session",
                "essential_evidence": {key: "source-1" for key in (
                    "identity", "broker_product_access", "risk_budget", "economics", "structural_protection",
                    "depth_spread_costs", "broker_orders", "monitoring", "cash_alternatives")},
                "pending_conditions": [{"kind": "FUTURE_RESULT", "condition": "Named result announcement"}]}
        value = request(state="CONDITIONAL_READY", supersedes=first["id"], blockers=[], plan=plan)
        invalid = deepcopy(value)
        invalid["plan"]["protective_price"] = "94"
        with self.assertRaisesRegex(ValueError, "within 5%"):
            record_assessment(self.root, invalid)
        accepted = record_assessment(self.root, value)
        self.assertEqual(accepted["state"], "CONDITIONAL_READY")
        self.assertFalse(accepted["entry_permission"])
        self.assertEqual(accepted["evidence_verification"], "ANALYST_DECLARATION")

    def test_expiry_projects_without_rewriting_assessment_and_cannot_reopen(self):
        first = record_assessment(self.root, request())
        old = (self.root / "candidate_assessments.jsonl").read_bytes()
        projected = project(self.root, [self.candidate], T3)[0]
        self.assertEqual(projected["state"], "EXPIRED")
        self.assertEqual(projected["assessment"]["state"], "RESEARCHED")
        self.assertEqual((self.root / "candidate_assessments.jsonl").read_bytes(), old)
        self.assertEqual(project(self.root, [self.candidate], T0)[0]["state"], "DETECTED")
        self.assertEqual(project(self.root, [projected], T0)[0]["state"], "DETECTED")
        self.assertNotIn("assessment", project(self.root, [projected], T0)[0])
        advanced = deepcopy(self.payload)
        advanced["run"]["as_of"] = T3
        write_snapshot(self.root, advanced)
        with self.assertRaisesRegex(ValueError, "transition"):
            record_assessment(self.root, request(as_of=T3, recheck_at=None, expires_at="2026-01-02T00:00:00Z", supersedes=first["id"]))

    def test_rejected_research_requires_changed_evidence_to_reopen(self):
        first = record_assessment(self.root, request(state="REJECTED"))
        with self.assertRaisesRegex(ValueError, "changed evidence"):
            record_assessment(self.root, request(supersedes=first["id"]))
        updated = request(supersedes=first["id"], change_kind="CORRECTED_INPUT")
        updated["evidence"][0]["statement"] = "Corrected peer sample"
        self.assertEqual(record_assessment(self.root, updated)["state"], "RESEARCHED")

    def test_tampered_or_torn_journal_fails_closed(self):
        record_assessment(self.root, request())
        path = self.root / "candidate_assessments.jsonl"
        old = path.read_bytes()
        path.write_bytes(old[:-1])
        with self.assertRaisesRegex(ValueError, "torn"):
            verify_assessments(self.root)
        row = json.loads(old)
        row["state"] = "ENTRY_ELIGIBLE"
        path.write_text(json.dumps(row) + "\n")
        with self.assertRaisesRegex(ValueError, "integrity"):
            project(self.root, [self.candidate], T2)

    def test_pending_cycle_blocks_assessment(self):
        (self.root / "pending.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "pending"):
            record_assessment(self.root, request())

    def test_real_demo_assessment_verifies_and_rerun_keeps_original_archives(self):
        from idxsig.runtime.coordinator import verify
        from idxsig.runtime.demo import demo
        directory = self.root / "integrated"
        demo(directory)
        payload = read_snapshot(directory)["payload"]
        candidate = payload["candidates"][0]
        cutoff = payload["run"]["as_of"]
        archived = {p.name: p.read_bytes() for p in (directory / "cycles").glob("*.json")}
        value = request(candidate_id=candidate["id"], as_of=cutoff,
                        expires_at="2026-11-03T00:00:00Z", recheck_at=None)
        value["evidence"][0]["available_at"] = candidate["detected_at"]
        value["evidence"][0]["observed_at"] = candidate["detected_at"]
        record_assessment(directory, value)
        self.assertTrue(verify(directory)["ok"])
        demo(directory)
        self.assertTrue(verify(directory)["ok"])
        self.assertEqual({p.name: p.read_bytes() for p in (directory / "cycles").glob("*.json")}, archived)
        self.assertEqual(read_snapshot(directory)["payload"]["candidates"][0]["state"], "RESEARCHED")


if __name__ == "__main__":
    unittest.main()

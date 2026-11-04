"""Per-intent processing observations never borrow another decision's clock."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from idxsig.runtime.timing_paper import observe_paper_timing
from idxsig.timing_capture import read_attempts


def fixture():
    order = {"id": "decision:2026-11-03:BTCUSDT", "symbol": "BTCUSDT", "side": "BUY",
             "made_at": "2026-11-04T00:00:10Z", "expires_at": "2026-11-04T01:00:10Z",
             "status": "PENDING"}
    payload = {"run": {"id": "cycle1", "as_of": "2026-11-04T00:00:10Z",
                       "profile_sha256": "a" * 64},
               "account": {"profile": "PAPER_TEST", "currency": "USDT",
                           "simulation_only": True, "orders": [order], "fills": []}}
    trace = {"id": "processing1", "evidence_kind": "synthetic",
             "universe_snapshot_id": "membership:test", "decision_at": "2026-11-04T00:00:11Z",
             "links": {"paper_new_intents_json": json.dumps([order["id"]]),
                       "paper_new_fills_json": "[]"}}
    return payload, trace


def fill(order):
    return {"id": "fill:" + order["id"], "intent_id": order["id"], "symbol": "BTCUSDT",
            "side": "BUY", "price": "100", "quantity": "1", "simulation_only": True,
            "fill_recorded_at": "2026-11-04T00:00:20Z", "observed_at": "2026-11-04T00:00:20Z",
            "received_at": "2026-11-04T00:00:20Z", "source_evidence_id": "quote:test",
            "observation_id": "observation:2"}


class PaperTimingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def observe(self, payload, trace, done="2026-11-04T00:00:12Z", quote=None):
        return observe_paper_timing(self.root, payload=payload, trace_record=trace,
                                   process_quote_at=quote, processed_at=done)

    def test_same_intent_links_later_fill_to_original_actual_decision(self):
        payload, trace = fixture()
        self.observe(payload, trace)
        later = copy.deepcopy(payload)
        later["run"].update(id="cycle2", as_of="2026-11-04T00:00:21Z")
        item = fill(later["account"]["orders"][0])
        later["account"]["fills"] = [item]
        later["account"]["orders"][0]["status"] = "IOC_COMPLETE"
        trace.update(id="processing2", decision_at="2026-11-04T00:00:22Z",
                     links={"paper_new_intents_json": "[]", "paper_new_fills_json": json.dumps([item["id"]])})
        self.observe(later, trace, "2026-11-04T00:00:23Z", "2026-11-04T00:00:21Z")
        row = read_attempts(self.root)[0]
        self.assertEqual(row["decision_at"], "2026-11-04T00:00:11Z")
        self.assertEqual(row["executable_at"], "2026-11-04T00:00:21Z")
        self.assertEqual(row["fill_at"], "2026-11-04T00:00:23Z")
        self.assertEqual(row["links"]["logical_fill_recorded_at"], item["fill_recorded_at"])
        self.assertIn("UPPER_BOUND", row["links"]["fill_clock_basis"])
        self.assertEqual(row["status"], "FILLED")
        self.assertEqual(row["links"]["parent_attempt_id"], "processing1")

    def test_replay_is_byte_idempotent_even_with_later_processing_clock(self):
        payload, trace = fixture()
        self.observe(payload, trace)
        before = (self.root / "timing/attempts.jsonl").read_bytes()
        trace.update(id="retry", decision_at=None, links={})
        self.observe(payload, trace, "2026-11-04T00:01:00Z")
        self.assertEqual(before, (self.root / "timing/attempts.jsonl").read_bytes())

    def test_existing_fill_without_original_observation_does_not_backdate(self):
        payload, trace = fixture()
        payload["account"]["fills"] = [fill(payload["account"]["orders"][0])]
        payload["account"]["orders"][0]["status"] = "IOC_COMPLETE"
        trace.update(evidence_kind="recorded", decision_at="2026-11-05T00:00:01Z", links={})
        self.observe(payload, trace, "2026-11-05T00:00:02Z", "2026-11-05T00:00:00Z")
        row = read_attempts(self.root)[0]
        self.assertIsNone(row["decision_at"])
        self.assertIsNone(row["executable_at"])
        self.assertIsNone(row["fill_at"])
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertEqual(row["links"]["paper_observed_fill_status"], "FILLED")
        self.assertEqual(row["evidence_kind"], "recorded")

    def test_saved_prospective_snapshot_replay_preserves_original_kind(self):
        payload, trace = fixture()
        trace["evidence_kind"] = "prospective"
        self.observe(payload, trace)
        before = (self.root / "timing/attempts.jsonl").read_bytes()
        trace.update(id="replay", evidence_kind="recorded", decision_at=None, links={})
        self.observe(payload, trace, "2026-11-04T00:01:00Z")
        self.assertEqual(before, (self.root / "timing/attempts.jsonl").read_bytes())
        self.assertEqual(read_attempts(self.root)[0]["evidence_kind"], "prospective")

    def test_other_intent_does_not_receive_current_decision_time(self):
        payload, trace = fixture()
        old = {**payload["account"]["orders"][0], "id": "old", "made_at": "2026-11-03T00:00:00Z"}
        payload["account"]["orders"].append(old)
        self.observe(payload, trace)
        rows = {r["links"]["intent_id"]: r for r in read_attempts(self.root)}
        self.assertIsNone(rows["old"]["decision_at"])
        self.assertIsNotNone(rows[payload["account"]["orders"][0]["id"]]["decision_at"])

    def test_orphan_fill_or_changed_identity_is_rejected(self):
        payload, trace = fixture()
        self.observe(payload, trace)
        broken = copy.deepcopy(payload)
        broken["account"]["orders"][0]["symbol"] = "ETHUSDT"
        with self.assertRaises(ValueError):
            self.observe(broken, trace)
        broken = copy.deepcopy(payload)
        broken["account"]["fills"] = [{**fill(broken["account"]["orders"][0]), "intent_id": "missing"}]
        with self.assertRaises(ValueError):
            self.observe(broken, trace)

    def test_older_snapshot_cannot_unfill_intent(self):
        payload, trace = fixture()
        original = copy.deepcopy(payload)
        self.observe(payload, trace)
        item = fill(payload["account"]["orders"][0])
        payload["account"]["fills"] = [item]
        payload["account"]["orders"][0]["status"] = "IOC_COMPLETE"
        trace.update(decision_at=None, links={"paper_new_fills_json": json.dumps([item["id"]])})
        self.observe(payload, trace, "2026-11-04T00:00:23Z", "2026-11-04T00:00:21Z")
        before = (self.root / "timing/attempts.jsonl").read_bytes()
        trace["links"] = {}
        self.observe(original, trace, "2026-11-04T00:01:00Z")
        self.assertEqual(before, (self.root / "timing/attempts.jsonl").read_bytes())

    def test_stale_order_label_cannot_rewrite_retained_terminal_state(self):
        payload, trace = fixture()
        payload["account"]["orders"][0]["status"] = "CANCELLED"
        trace.update(decision_at=None, links={})
        self.observe(payload, trace)
        before = (self.root / "timing/attempts.jsonl").read_bytes()
        payload["account"]["orders"][0]["status"] = "EXPIRED"
        self.observe(payload, trace, "2026-11-04T00:01:00Z")
        self.assertEqual(before, (self.root / "timing/attempts.jsonl").read_bytes())

    def test_delayed_original_decision_observation_can_complete_unknown_clock(self):
        original, original_trace = fixture()
        later, trace = copy.deepcopy(original), copy.deepcopy(original_trace)
        later["run"].update(id="cycle2", as_of="2026-11-04T00:00:21Z")
        item = fill(later["account"]["orders"][0])
        later["account"]["fills"] = [item]
        later["account"]["orders"][0]["status"] = "IOC_COMPLETE"
        trace.update(id="processing2", decision_at=None,
                     links={"paper_new_fills_json": json.dumps([item["id"]])})
        self.observe(later, trace, "2026-11-04T00:00:23Z", "2026-11-04T00:00:21Z")
        self.assertIsNone(read_attempts(self.root)[0]["decision_at"])
        self.observe(original, original_trace, "2026-11-04T00:00:24Z")
        row = read_attempts(self.root)[0]
        self.assertEqual(row["decision_at"], "2026-11-04T00:00:11Z")
        self.assertEqual(row["fill_at"], "2026-11-04T00:00:23Z")
        self.assertEqual(row["status"], "FILLED")
        self.assertEqual(row["links"]["decision_processing_attempt_id"], "processing1")


if __name__ == "__main__":
    unittest.main()

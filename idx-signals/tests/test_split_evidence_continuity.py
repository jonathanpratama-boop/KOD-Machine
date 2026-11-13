"""Independent regression cases for loss of the specific supporting split event.

These test the evidence rule, not the implementation proposed to enforce it.
No network, provider archives, live ledgers or timestamp services are used.
"""

from copy import deepcopy
from datetime import datetime
import unittest

from idxsig import split_assessments as sa


def unix(day):
    return int(datetime.fromisoformat(day + "T21:00:00+00:00").timestamp())


def chart(bars, splits):
    events = {
        str(i): {"date": unix(day), "numerator": numerator, "denominator": denominator,
                 "splitRatio": f"{numerator}:{denominator}"}
        for i, (day, numerator, denominator) in enumerate(splits)
    }
    return {"chart": {"result": [{
        "timestamp": [unix(day) for day, _ in bars],
        "indicators": {"quote": [{"close": [close for _, close in bars]}]},
        "events": {"splits": events},
    }]}}


class SplitEvidenceContinuity(unittest.TestCase):
    def setUp(self):
        self.spec = {"set_id": "CONTINUITY", "ticker": "CONTINUITY", "market": "US",
                     "signal_session": "2026-11-11", "signal": {"close": 24., "previous": 1.},
                     "decision": {}}
        self.bars = [("2026-11-10", 24.), ("2026-11-11", 24.)]
        self.supporting_split = ("2026-11-11", 1, 24)
        self.older_split = ("2026-01-02", 1, 2)
        payload = chart(self.bars, [self.supporting_split, self.older_split])
        self.first = sa.assessment_record(self.spec, payload, "initial response", "2026-11-12T01:00:00Z",
                                          pull_role="seal", retrieved_on="2026-11-12")
        self.first["record_hash"] = "initial-record"
        self.assertEqual(self.first["assessment"], "ARTIFACT_CONFIRMED")

    def reassess(self, payload, records=None, day="2026-11-13", spec=None):
        spec = spec or self.spec
        records = [self.first] if records is None else records
        return sa.propose_reassessments([spec], records, {spec["ticker"]: payload}, "later response",
                                        day + "T01:00:00Z", today=day, retrieved_on=day)

    def assert_stays_excluded(self, records):
        self.assertEqual(sa.removed_set_ids("corrected", records, []), {self.spec["set_id"]})
        self.assertEqual(sa.verify(records, [self.spec]), [])

    def test_unrelated_older_event_does_not_replace_missing_supporting_event(self):
        # Removing only Nov 11 leaves the old Jan 2 split readable and all prices identical.
        refreshed = chart(self.bars, [self.older_split])
        self.assertEqual(sa.split_event_coverage(refreshed), "LISTED")
        new = self.reassess(refreshed)
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["assessment"], "NOT_ASSESSABLE")
        self.assertEqual(new[0]["evidence_gap"], "SPLIT_EVENT_MISSING")
        self.assert_stays_excluded([self.first, new[0]])

    def test_unrelated_recent_event_does_not_replace_missing_supporting_event(self):
        # A split inside the general lookback also cannot explain the unchanged 24-to-1 unit discrepancy.
        refreshed = chart(self.bars, [("2026-11-05", 1, 2)])
        new = self.reassess(refreshed)
        self.assertEqual(new[0]["assessment"], "NOT_ASSESSABLE")
        self.assertEqual(new[0]["evidence_gap"], "SPLIT_EVENT_MISSING")
        self.assert_stays_excluded([self.first, new[0]])

    def test_same_event_date_with_corrected_ratio_can_change_the_finding(self):
        # Revised 1:12 ratio and reference close 12 agree. 24 / 12 - 1 = +100%, a real contaminated move.
        refreshed = chart([("2026-11-10", 12.), ("2026-11-11", 24.)], [("2026-11-11", 1, 12)])
        new = self.reassess(refreshed)
        self.assertEqual(new[0]["assessment"], "REAL_MOVE_UNITS_CONTAMINATED")
        self.assertEqual(new[0]["split_adjusted_ret1"], 1.)
        self.assertIsNone(new[0]["evidence_gap"])
        self.assertEqual(sa.removed_set_ids("corrected", [self.first, new[0]], []), set())
        self.assertEqual(sa.verify([self.first, new[0]], [self.spec]), [])

    def test_smx_kind_same_event_with_post_split_previous_close_can_reverse(self):
        spec = {"set_id": "POST_SPLIT", "ticker": "POST_SPLIT", "market": "US",
                "signal_session": "2026-11-10", "signal": {"close": 5.15, "previous": 2.50},
                "decision": {}}
        split = ("2026-11-09", 1, 2.8)
        first_payload = chart([("2026-11-06", 7.), ("2026-11-10", 5.15)], [split])
        first = sa.assessment_record(spec, first_payload, "initial response", "2026-11-11T01:00:00Z",
                                     pull_role="later", retrieved_on="2026-11-11")
        first["record_hash"] = "initial-smx-kind"
        self.assertEqual(first["assessment"], "ARTIFACT_CONFIRMED")
        # The added Nov 9 close establishes that the recorded previous price was already post-split.
        refreshed = chart([("2026-11-06", 7.), ("2026-11-09", 2.50), ("2026-11-10", 5.15)], [split])
        new = self.reassess(refreshed, [first], spec=spec)
        self.assertEqual(new[0]["assessment"], "REAL_MOVE_AFTER_SPLIT")
        self.assertIsNone(new[0]["evidence_gap"])
        self.assertEqual(sa.removed_set_ids("corrected", [first, new[0]], []), set())
        self.assertEqual(sa.verify([first, new[0]], [spec]), [])

    def test_repeated_gap_and_restoration_keep_a_consistent_history(self):
        missing = chart(self.bars, [self.older_split])
        gap = self.reassess(missing)[0]
        gap["record_hash"] = "gap-record"
        records = [self.first, gap]
        self.assert_stays_excluded(records)
        self.assertEqual(self.reassess(missing, records, day="2026-11-14"), [])
        restored = chart(self.bars, [self.supporting_split, self.older_split])
        new = self.reassess(restored, records, day="2026-11-15")
        self.assertEqual(new[0]["assessment"], "ARTIFACT_CONFIRMED")
        self.assertEqual(new[0]["supersedes"], "gap-record")
        self.assert_stays_excluded(records + new)

    def test_pre_revision_records_without_gap_field_remain_valid(self):
        old = deepcopy(self.first)
        old.pop("evidence_gap")
        self.assertEqual(sa.verify([old], [self.spec]), [])
        missing = chart(self.bars, [self.older_split])
        new = self.reassess(missing, [old])
        self.assertEqual(new[0]["assessment"], "NOT_ASSESSABLE")
        self.assert_stays_excluded([old] + new)


if __name__ == "__main__":
    unittest.main()

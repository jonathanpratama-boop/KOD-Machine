"""Independent tests for the US_SPLIT_ARTIFACTS_v1 function contract (RULE.md)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify import classify, window_events  # noqa: E402

SPLIT = {"numerator": 1, "denominator": 10, "effective_session": "2026-10-29"}
SPLIT2 = {"numerator": 1, "denominator": 20, "effective_session": "2026-10-29"}
NON_VERIFIED = ["RATIO_CONFIRMED", "MENTION_ONLY", "NO_EVIDENCE", "NO_CIK", "NOT_A_SPLIT"]


class TestClassifyClasses(unittest.TestCase):
    def test_unknown_on_fetch_failure(self):
        """Guards against classifying a set whose provider request failed."""
        self.assertEqual(classify([], 0.5, [], False), "UNKNOWN")

    def test_artifact_confirmed(self):
        """Guards against missing an SEC-verified split artifact."""
        self.assertEqual(classify([SPLIT], 0.01, ["VERIFIED"], True), "ARTIFACT_CONFIRMED")

    def test_artifact_provider_only(self):
        """Guards against treating an unverified split artifact as confirmed."""
        self.assertEqual(classify([SPLIT], 0.01, ["NO_EVIDENCE"], True), "ARTIFACT_PROVIDER_ONLY")

    def test_split_real_move(self):
        """Guards against calling a real +30% move on a split day an artifact."""
        self.assertEqual(classify([SPLIT], 0.45, ["VERIFIED"], True), "SPLIT_REAL_MOVE")

    def test_unexplained_gap(self):
        """Guards against misclassifying a small adjusted move with no split."""
        self.assertEqual(classify([], 0.05, [], True), "UNEXPLAINED_GAP")

    def test_clean(self):
        """Guards against flagging a genuine move with no split."""
        self.assertEqual(classify([], 0.45, [], True), "CLEAN")


class TestClassifyPrecedence(unittest.TestCase):
    def test_fetch_failure_beats_everything(self):
        """Guards against fetch_ok=False being overridden by split or return data."""
        self.assertEqual(classify([SPLIT], 0.01, ["VERIFIED"], False), "UNKNOWN")
        self.assertEqual(classify([SPLIT], 0.9, ["VERIFIED"], False), "UNKNOWN")
        self.assertEqual(classify([], 0.9, [], False), "UNKNOWN")

    def test_missing_adj_ret1_is_unknown(self):
        """Guards against a missing signal/prev bar falling through to another class."""
        self.assertEqual(classify([SPLIT], None, ["VERIFIED"], True), "UNKNOWN")
        self.assertEqual(classify([], None, [], True), "UNKNOWN")

    def test_split_at_exact_threshold_is_real_move(self):
        """Guards against an off-by-one threshold making adj_ret1 == 0.30 an artifact."""
        self.assertEqual(classify([SPLIT], 0.30, ["VERIFIED"], True), "SPLIT_REAL_MOVE")
        self.assertEqual(classify([SPLIT], 0.30, ["NO_EVIDENCE"], True), "SPLIT_REAL_MOVE")

    def test_no_split_at_exact_threshold_is_clean(self):
        """Guards against an off-by-one threshold making adj_ret1 == 0.30 a gap."""
        self.assertEqual(classify([], 0.30, [], True), "CLEAN")

    def test_just_below_threshold(self):
        """Guards against a threshold implemented as <= or with the wrong value."""
        self.assertEqual(classify([SPLIT], 0.2999, ["VERIFIED"], True), "ARTIFACT_CONFIRMED")
        self.assertEqual(classify([], 0.2999, [], True), "UNEXPLAINED_GAP")

    def test_negative_adj_ret1_with_split(self):
        """Guards against negative adjusted returns being treated specially."""
        self.assertEqual(classify([SPLIT], -0.2, ["VERIFIED"], True), "ARTIFACT_CONFIRMED")


class TestClassifySecStatus(unittest.TestCase):
    def test_non_verified_statuses_do_not_confirm(self):
        """Guards against any status other than exactly VERIFIED confirming an artifact."""
        for status in NON_VERIFIED:
            with self.subTest(status=status):
                self.assertEqual(classify([SPLIT], 0.01, [status], True), "ARTIFACT_PROVIDER_ONLY")

    def test_verified_must_match_exactly(self):
        """Guards against case-insensitive or substring matching of VERIFIED."""
        for status in ["verified", "Verified", "UNVERIFIED", "VERIFIED "]:
            with self.subTest(status=status):
                self.assertEqual(classify([SPLIT], 0.01, [status], True), "ARTIFACT_PROVIDER_ONLY")

    def test_one_of_many_verified_confirms(self):
        """Guards against requiring every window split to be VERIFIED."""
        self.assertEqual(
            classify([SPLIT, SPLIT2], 0.01, ["NO_EVIDENCE", "VERIFIED"], True), "ARTIFACT_CONFIRMED"
        )
        self.assertEqual(
            classify([SPLIT, SPLIT2], 0.01, ["VERIFIED", "MENTION_ONLY"], True),
            "ARTIFACT_CONFIRMED",
        )

    def test_many_splits_none_verified(self):
        """Guards against multiple unverified splits being counted as confirmation."""
        self.assertEqual(
            classify([SPLIT, SPLIT2], 0.01, ["RATIO_CONFIRMED", "NO_CIK"], True),
            "ARTIFACT_PROVIDER_ONLY",
        )


class TestWindowEvents(unittest.TestCase):
    PREV, SIG = "2026-10-28", "2026-10-29"

    @staticmethod
    def ev(day, **extra):
        return dict({"numerator": 1, "denominator": 10, "effective_session": day}, **extra)

    def test_event_on_prev_day_excluded(self):
        """Guards against an inclusive lower bound on the window."""
        self.assertEqual(window_events([self.ev(self.PREV)], self.PREV, self.SIG), [])

    def test_event_on_signal_day_included(self):
        """Guards against an exclusive upper bound on the window."""
        e = self.ev(self.SIG)
        self.assertEqual(window_events([e], self.PREV, self.SIG), [e])

    def test_event_after_signal_day_excluded(self):
        """Guards against later splits leaking into the window."""
        self.assertEqual(window_events([self.ev("2026-10-30")], self.PREV, self.SIG), [])

    def test_events_before_prev_day_excluded(self):
        """Guards against older splits leaking into the window."""
        evs = [self.ev("2026-10-27"), self.ev("2026-09-01")]
        self.assertEqual(window_events(evs, self.PREV, self.SIG), [])

    def test_empty_list(self):
        """Guards against failure on an input with no events."""
        self.assertEqual(window_events([], self.PREV, self.SIG), [])

    def test_multi_day_gap_and_mixed(self):
        """Guards against wrong filtering when prev_day is several days before signal_day."""
        inside = [self.ev("2026-10-24"), self.ev("2026-10-27")]
        evs = [self.ev("2026-10-23")] + inside + [self.ev("2026-10-28")]
        self.assertEqual(window_events(evs, "2026-10-23", "2026-10-27"), inside)

    def test_returns_event_dicts_unchanged(self):
        """Guards against window_events mutating, reshaping or dropping keys of events."""
        e = self.ev(self.SIG, ratio="1:10", source="yahoo", date=1761744600)
        before = copy.deepcopy(e)
        out = window_events([e], self.PREV, self.SIG)
        self.assertEqual(out, [before])
        self.assertEqual(e, before)


if __name__ == "__main__":
    unittest.main()

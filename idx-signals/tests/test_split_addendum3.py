"""SPLIT_REVISIONS_v1, contract addendum 3: an incomplete refresh never displaces an event-based finding.

Written by the independent test author from CONTRACT.md (part A, part B2), CONTRACT_ADDENDUM_1.md,
CONTRACT_ADDENDUM_2.md and CONTRACT_ADDENDUM_3.md alone, without reading the implementation. Every expected value is
derived from those texts; the arithmetic is in the comments.

Constants (contract, part A): T = 0.30, extreme ratio 4.0, previous-bar gap 5 days, event window 10 days, reference
window 30 days, unchanged tolerance ln(1.01), re-based tolerance ln(1.03), smallest split factor 1.05.
k = denominator / numerator: a 1-for-24 reverse split has numerator 1, denominator 24, k = 24.

Tickers CEX, RVX and NAF are invented. SMX and its pulls are those of PROTOCOL.md (as in test_split_assessments.py).
"""

import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from idxsig import split_assessments, split_flags, paper

sa = split_assessments

GROUP_OF = {  # contract, part B1
    "ARTIFACT_CONFIRMED": "ARTIFACT",
    "ARTIFACT_PROBABLE": "ARTIFACT",
    "REAL_MOVE_UNITS_CONTAMINATED": "CONTAMINATED",
    "REAL_MOVE_AFTER_SPLIT": "REAL",
    "NO_ACTION_FOUND": "REAL",
    "NOT_ASSESSABLE": "UNRESOLVED",
    "UNITS_INCONSISTENT": "UNRESOLVED",
    "SPLIT_IN_WINDOW_UNRESOLVED": "UNRESOLVED",
    "REAL_MOVE_UNITS_UNVERIFIED": "UNRESOLVED",
    "UNEXPLAINED_EXTREME_MOVE": "UNRESOLVED",
    "STALE_PREVIOUS": "UNRESOLVED",
}
EVENT_BASED = {"ARTIFACT_CONFIRMED", "ARTIFACT_PROBABLE", "REAL_MOVE_UNITS_CONTAMINATED",
               "SPLIT_IN_WINDOW_UNRESOLVED", "REAL_MOVE_UNITS_UNVERIFIED", "REAL_MOVE_AFTER_SPLIT"}
NOT_EVENT_BASED = set(GROUP_OF) - EVENT_BASED
RECORD_KEYS = {"type", "rule", "set_id", "ticker", "market", "signal_session", "recorded_ret1", "assessment", "group",
               "split", "split_adjusted_ret1", "previous_session", "previous_session_source", "units", "later_factor",
               "evidence_gap", "pull_role", "supersedes", "basis", "sources", "assessed_at"}
ABSENT, MALFORMED, LISTED = "ABSENT", "MALFORMED", "LISTED"
GAP_ABSENT, GAP_MALFORMED = "SPLIT_EVENTS_ABSENT", "SPLIT_EVENTS_MALFORMED"

S = "2026-11-10"  # Tuesday; E takes splits effective 2026-11-01 .. 2026-11-10, reference bars 2026-10-11 .. 2026-11-09
N1, N2, N3, N4, N5, N6 = ("2026-11-10T22:10:05Z", "2026-11-11T22:05:00Z", "2026-11-12T22:05:00Z",
                          "2026-11-13T22:05:00Z", "2026-11-14T22:05:00Z", "2026-11-15T22:05:00Z")


# ---- payloads ----------------------------------------------------------------------------------------------------

def unix(day):
    """14:30 UTC on an ISO date: 09:30 in New York in November, so the New York date is `day`."""
    y, m, d = (int(x) for x in day.split("-"))
    return int(datetime(y, m, d, 14, 30, tzinfo=timezone.utc).timestamp())


def split_entry(day, n, d):
    return {"date": unix(day), "numerator": n, "denominator": d, "splitRatio": f"{n}:{d}"}


def splits_dict(*splits):
    return {str(unix(day)): split_entry(day, n, d) for day, n, d in splits}


_NOTHING = object()


def chart(bars, events=_NOTHING):
    """A provider chart payload. `events` is put at chart.result[0].events verbatim; omitted, there is no `events`."""
    result = {
        "meta": {"currency": "USD", "exchangeTimezoneName": "America/New_York"},
        "timestamp": [unix(day) for day, _ in bars],
        "indicators": {"quote": [{"close": [close for _, close in bars]}]},
    }
    if events is not _NOTHING:
        result["events"] = events
    return {"chart": {"result": [result], "error": None}}


def listed(bars, *splits):
    return chart(bars, {"splits": splits_dict(*splits)})


# The reviewer's counterexample (CONTRACT_ADDENDUM_3.md, "The fault"): recorded previous close 1, close 24, signal
# 2026-11-10; the provider's later bars show the previous session 2026-11-09 at 24, and a 1-for-24 split is listed
# on the signal session.
CEX_LATER_BARS = [("2026-11-04", 26.0), ("2026-11-05", 25.5), ("2026-11-06", 25.0), ("2026-11-09", 24.0),
                  ("2026-11-10", 24.0), ("2026-11-11", 23.0)]
CEX_SPLIT = ("2026-11-10", 1, 24)


def cex():
    return {"set_id": "US-CEX-20261110", "ticker": "CEX", "market": "US", "signal_session": S,
            "signal": {"close": 24.0, "previous": 1.0}, "decision": {}}


def cex_own_pull():
    # The scan's pull on 2026-11-10: no split listed, history in pre-split units (2026-11-09 at 1.00 = p).
    # Case B: Xu = 2026-11-09, UNCHANGED. E is empty. r = 24 >= 4: UNEXPLAINED_EXTREME_MOVE.
    return chart([("2026-11-04", 1.08), ("2026-11-05", 1.06), ("2026-11-06", 1.04), ("2026-11-09", 1.00),
                  ("2026-11-10", 24.0)])


def cex_listed():
    # Case A at the seal's previous session 2026-11-09: q = 24; |ln(24 / 1)| > ln 1.01, not UNCHANGED;
    # 24 / (1 * 24) = 1: PRE_SPLIT_CONFIRMED (event 2026-11-10 > P). r / k - 1 = 24 / 24 - 1 = 0 < 0.30:
    # ARTIFACT_CONFIRMED, adjusted 0.0.
    # Without a seal (Case B): no bar within 1% of 1; for the event 2026-11-10, the latest reference session before it
    # matching 1 * 24 within 3% is 2026-11-09: PRE_SPLIT_CONFIRMED, the same class.
    return listed(CEX_LATER_BARS, CEX_SPLIT)


def absent_variants(bars):
    """Every form of ABSENT coverage a payload with chart.result[0] can take (addendum 3)."""
    return {
        "no events": chart(bars),
        "events without splits": chart(bars, {}),
        "events with dividends only": chart(bars, {"dividends": {str(unix("2026-11-05")): {
            "amount": 0.1, "date": unix("2026-11-05")}}}),
        "splits None": chart(bars, {"splits": None}),
        "splits empty dict": chart(bars, {"splits": {}}),
    }


def bad_numerator(day, n, d):
    e = split_entry(day, n, d)
    e["numerator"] = "one"
    return {str(e["date"]): e}


def bad_date(day, n, d):
    e = split_entry(day, n, d)
    e["date"] = "not a date"
    return {"x": e}


def malformed_variants(bars, split=CEX_SPLIT):
    """Every form of MALFORMED coverage (addendum 3), each still carrying the split in some unreadable form."""
    good = splits_dict(split)
    return {
        "events a list": chart(bars, [{"splits": good}]),
        "events a string": chart(bars, "splits"),
        "splits a list": chart(bars, {"splits": list(good.values())}),
        "splits a string": chart(bars, {"splits": "1:24"}),
        "non-numeric numerator": chart(bars, {"splits": bad_numerator(*split)}),
        "bad date": chart(bars, {"splits": bad_date(*split)}),
        "one readable and one unreadable entry": chart(bars, {"splits": {
            **splits_dict(("2026-11-03", 1, 2)), **bad_numerator(*split)}}),
        "entry not a dict": chart(bars, {"splits": {**good, "junk": "1:24"}}),
    }


# ---- hand-written records ----------------------------------------------------------------------------------------

def arec(spec, assessment, assessed_at, *, pull_role="later", supersedes=None, split="", adjusted=None,
         previous_session=None, source=None, units="UNKNOWN", basis="provider pull", evidence_gap=None):
    s = spec["signal"]
    return {"type": "SPLIT_ASSESSMENT", "rule": "SPLIT_UNITS_V1", "set_id": spec["set_id"], "ticker": spec["ticker"],
            "market": spec["market"], "signal_session": spec["signal_session"],
            "recorded_ret1": round(s["close"] / s["previous"] - 1, 4), "assessment": assessment,
            "group": GROUP_OF[assessment], "split": split, "split_adjusted_ret1": adjusted,
            "previous_session": previous_session, "previous_session_source": source, "units": units,
            "later_factor": None, "evidence_gap": evidence_gap, "pull_role": pull_role, "supersedes": supersedes,
            "basis": basis, "sources": [], "assessed_at": assessed_at}


class LedgerCase(unittest.TestCase):
    """Both ledgers point at temporary paths, so nothing here touches the repository's paper/ directory."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.path = self.dir / "split_assessments.jsonl"
        self.flags_path = self.dir / "split_flags.jsonl"
        for target, name, val in ((split_assessments, "LEDGER", self.path),
                                  (split_flags, "FLAGS_LEDGER", self.flags_path)):
            p = mock.patch.object(target, name, val)
            p.start()
            self.addCleanup(p.stop)
        self._n = 0

    def write(self, *recs):
        paper.append(list(recs), path=self.path)
        return paper.ledger_lines(self.path)

    def fork(self, *recs):
        """Seal records onto a copy of the current ledger; the main ledger is not touched."""
        self._n += 1
        path = self.dir / f"fork{self._n}.jsonl"
        if self.path.exists():
            shutil.copy(self.path, path)
        if recs:
            paper.append(list(recs), path=path)
        return paper.ledger_lines(path)

    def assertGap(self, rec, gap):
        self.assertEqual(set(rec), RECORD_KEYS)
        self.assertEqual((rec["assessment"], rec["group"]), ("NOT_ASSESSABLE", "UNRESOLVED"))
        self.assertEqual(rec["evidence_gap"], gap)
        # The fields addendum 1 gives: no previous session, units UNKNOWN, empty split, no adjusted move/factor.
        self.assertEqual((rec["previous_session"], rec["units"], rec["split"]), (None, "UNKNOWN", ""))
        self.assertEqual((rec["split_adjusted_ret1"], rec["later_factor"]), (None, None))


# ==================================================================================================================
# split_event_coverage
# ==================================================================================================================

class SplitEventCoverage(unittest.TestCase):
    BARS = CEX_LATER_BARS

    def test_listed(self):
        self.assertEqual(sa.split_event_coverage(cex_listed()), LISTED)
        two = listed(self.BARS, ("2026-11-03", 1, 2), ("2026-11-10", 1, 24))
        self.assertEqual(len(split_flags.provider_splits(two)), 2)
        self.assertEqual(sa.split_event_coverage(two), LISTED)
        # Coverage describes the split-event block only: a listed block without any bar is still LISTED.
        self.assertEqual(sa.split_event_coverage(listed([], CEX_SPLIT)), LISTED)

    def test_absent(self):
        for name, p in absent_variants(self.BARS).items():
            with self.subTest(name):
                self.assertEqual(sa.split_event_coverage(p), ABSENT)
        no_result = {
            "result empty list": {"chart": {"result": [], "error": None}},
            "result None (an error response)": {"chart": {"result": None, "error": {"code": "Not Found"}}},
            "no result key": {"chart": {"error": None}},
            "no chart": {},
        }
        for name, p in no_result.items():
            with self.subTest(name):
                self.assertEqual(sa.split_event_coverage(p), ABSENT)

    def test_malformed(self):
        for name, p in malformed_variants(self.BARS).items():
            with self.subTest(name):
                self.assertEqual(sa.split_event_coverage(p), MALFORMED)

    def test_unreadable_entries_are_unreadable_to_provider_splits(self):
        # Precondition of the definition: for a non-empty splits dict, MALFORMED means provider_splits returns fewer
        # events than the dict has entries. Check that the entries used above are indeed unreadable to it.
        for name in ("non-numeric numerator", "bad date", "one readable and one unreadable entry",
                     "entry not a dict"):
            with self.subTest(name):
                p = malformed_variants(self.BARS)[name]
                entries = p["chart"]["result"][0]["events"]["splits"]
                self.assertLess(len(split_flags.provider_splits(p)), len(entries))

    def test_never_raises(self):
        junk = [None, "", "chart", 0, 3.5, True, [], [1, 2], {}, {"chart": None}, {"chart": "x"}, {"chart": []},
                {"chart": {"result": "x"}}, {"chart": {"result": [None]}}, {"chart": {"result": ["x"]}},
                {"chart": {"result": [[]]}}, {"chart": {"result": [{"events": None}]}},
                {"chart": {"result": [{"events": {"splits": {"a": None}}}]}},
                {"chart": {"result": [{"events": {"splits": {"a": {"date": None, "numerator": None}}}}]}},
                {"chart": {"result": [{"events": {"splits": {"a": {"date": [], "numerator": {}, "denominator": "x"}}}}]}},
                {"chart": {"result": [{"events": {"splits": {1: {"date": float("nan"), "numerator": 1,
                                                                 "denominator": 0}}}}]}},
                {"chart": {"result": [{"events": {"splits": {"a": {"date": 10 ** 30, "numerator": 1,
                                                                   "denominator": 2}}}}]}},
                {"chart": {"result": [{"events": {"splits": {"a": [1, 2, 3]}}}]}}]
        for i, p in enumerate(junk):
            with self.subTest(i=i, payload=repr(p)[:80]):
                self.assertIn(sa.split_event_coverage(p), {LISTED, ABSENT, MALFORMED})
        # The obviously empty ones are ABSENT: there is no chart.result[0].
        for p in (None, "", 0, [], {}, {"chart": None}, {"chart": {"result": []}}):
            with self.subTest(empty=repr(p)):
                self.assertEqual(sa.split_event_coverage(p), ABSENT)

    def test_event_based_constant(self):
        self.assertEqual(set(sa.EVENT_BASED), EVENT_BASED)
        self.assertIn("evidence_gap", sa.CHANGE_FIELDS)


# ==================================================================================================================
# assessment_record(finding=...)
# ==================================================================================================================

class AssessmentRecordFinding(unittest.TestCase):

    def test_reviewer_counterexample_without_a_finding_is_units_inconsistent(self):
        # The fault as described: with the split-event block removed and no finding passed, Case B finds no bar
        # within 1% of 1 and E is empty: INCONSISTENT, UNITS_INCONSISTENT. A first assessment stays exactly that.
        for name, p in {**absent_variants(CEX_LATER_BARS), **malformed_variants(CEX_LATER_BARS)}.items():
            with self.subTest(name):
                r = sa.assessment_record(cex(), p, "b", "t")
                self.assertEqual(set(r), RECORD_KEYS)
                self.assertEqual(r["assessment"], "UNITS_INCONSISTENT")
                self.assertIsNone(r["evidence_gap"])

    def test_event_based_finding_and_absent_block(self):
        for cls in sorted(EVENT_BASED):
            finding = arec(cex(), cls, N2)
            for name, p in absent_variants(CEX_LATER_BARS).items():
                with self.subTest(finding=cls, payload=name):
                    r = sa.assessment_record(cex(), p, "b", "t", finding=finding)
                    self.assertEqual(set(r), RECORD_KEYS)
                    self.assertEqual(r["assessment"], "NOT_ASSESSABLE")
                    self.assertEqual(r["evidence_gap"], GAP_ABSENT)
                    self.assertEqual((r["previous_session"], r["units"], r["split"]), (None, "UNKNOWN", ""))
                    self.assertEqual((r["split_adjusted_ret1"], r["later_factor"]), (None, None))
                    self.assertEqual(r["recorded_ret1"], 23.0)  # 24 / 1 - 1

    def test_event_based_finding_and_malformed_block(self):
        for cls in sorted(EVENT_BASED):
            finding = arec(cex(), cls, N2)
            for name, p in malformed_variants(CEX_LATER_BARS).items():
                with self.subTest(finding=cls, payload=name):
                    r = sa.assessment_record(cex(), p, "b", "t", finding=finding)
                    self.assertEqual(r["assessment"], "NOT_ASSESSABLE")
                    self.assertEqual(r["evidence_gap"], GAP_MALFORMED)
                    self.assertEqual((r["previous_session"], r["units"], r["split"]), (None, "UNKNOWN", ""))

    def test_event_based_finding_and_listed_block_is_classified_as_usual(self):
        finding = arec(cex(), "ARTIFACT_CONFIRMED", N2)
        for f in (None, finding):
            with self.subTest(finding=f is not None):
                r = sa.assessment_record(cex(), cex_listed(), "b", "t", finding=f)
                self.assertEqual((r["assessment"], r["group"]), ("ARTIFACT_CONFIRMED", "ARTIFACT"))
                self.assertEqual((r["split"], r["split_adjusted_ret1"]), ("2026-11-10 1:24", 0.0))
                self.assertIsNone(r["evidence_gap"])

    def test_no_priced_bar_stays_as_addendum_1_gives_it(self):
        # Addendum 3: "A payload with no priced bar stays as addendum 1 gives it, with evidence_gap None."
        finding = arec(cex(), "ARTIFACT_CONFIRMED", N2)
        empty = {"chart": {"result": [{"meta": {"currency": "USD"}, "indicators": {"quote": [{}]}}], "error": None}}
        no_price = chart([("2026-11-09", None), ("2026-11-10", 0)])
        for name, p in {"None": None, "empty": empty, "no price": no_price,
                        "no price, malformed events": chart([("2026-11-10", None)], {"splits": "x"}),
                        "error": {"chart": {"result": None, "error": {"code": "Not Found"}}}}.items():
            with self.subTest(name):
                r = sa.assessment_record(cex(), p, "b", "t", finding=finding)
                self.assertEqual(r["assessment"], "NOT_ASSESSABLE")
                self.assertIsNone(r["evidence_gap"])

    def test_no_protection_when_the_finding_is_not_event_based(self):
        for cls in sorted(NOT_EVENT_BASED):
            finding = arec(cex(), cls, N2)
            for name, p in {**absent_variants(CEX_LATER_BARS), **malformed_variants(CEX_LATER_BARS)}.items():
                with self.subTest(finding=cls, payload=name):
                    r = sa.assessment_record(cex(), p, "b", "t", finding=finding)
                    self.assertEqual(r["assessment"], "UNITS_INCONSISTENT")
                    self.assertIsNone(r["evidence_gap"])

    def test_evidence_gap_key_follows_later_factor(self):
        for p in (cex_listed(), chart(CEX_LATER_BARS), None):
            for f in (None, arec(cex(), "ARTIFACT_CONFIRMED", N2)):
                r = sa.assessment_record(cex(), p, "b", "t", finding=f)
                keys = list(r)
                self.assertEqual(keys.index("evidence_gap"), keys.index("later_factor") + 1)

    def test_smx_reversal_with_a_listed_split(self):
        # Addendum 3 names SMX 2026-11-10: the response lists the 1-for-2.8 split of 2026-11-09, the previous bar is
        # 2026-11-09 at 2.50 = p (Case B, UNCHANGED, P = 2026-11-09 >= the split: straddle NO), r = 2.06 < 4, gap 1
        # day, E not empty: REAL_MOVE_AFTER_SPLIT, whatever the standing finding.
        smx = {"set_id": "US-SMX-20261110", "ticker": "SMX", "market": "US", "signal_session": S,
               "signal": {"close": 5.15, "previous": 2.50}, "decision": {}}
        pull = listed([("2026-11-04", 3.08), ("2026-11-05", 2.91), ("2026-11-06", 2.80), ("2026-11-09", 2.50),
                       ("2026-11-10", 5.15), ("2026-11-11", 4.70)], ("2026-11-09", 1, 2.8))
        self.assertEqual(sa.split_event_coverage(pull), LISTED)
        r = sa.assessment_record(smx, pull, "b", "t", finding=arec(smx, "ARTIFACT_PROBABLE", N2))
        self.assertEqual((r["assessment"], r["group"]), ("REAL_MOVE_AFTER_SPLIT", "REAL"))
        self.assertIsNone(r["evidence_gap"])


# ==================================================================================================================
# The reviewer's counterexample, end to end
# ==================================================================================================================

class ReviewerCounterexample(LedgerCase):

    def setUp(self):
        super().setUp()
        self.spec = cex()
        self.sid = self.spec["set_id"]
        self.specs = [self.spec]

    def removed(self, records):
        return sa.removed_set_ids("corrected", records=records, v11_flags=[])

    def seal_and_confirm(self):
        """Night 1: the seal assessment. Night 2: the split is listed: ARTIFACT_CONFIRMED."""
        first = sa.propose_assessments(self.specs, [], {"CEX": cex_own_pull()}, "pull 2026-11-10", N1,
                                       seal_session=S)
        self.assertEqual(len(first), 1)
        seal = first[0]
        self.assertEqual((seal["assessment"], seal["pull_role"]), ("UNEXPLAINED_EXTREME_MOVE", "seal"))
        self.assertEqual((seal["previous_session"], seal["units"]), ("2026-11-09", "UNCHANGED"))
        self.assertIsNone(seal["evidence_gap"])
        records = self.write(*first)

        second = sa.propose_reassessments(self.specs, records, {"CEX": cex_listed()}, "pull 2026-11-11", N2,
                                          retrieved_on="2026-11-11")
        self.assertEqual(len(second), 1)
        conf = second[0]
        self.assertEqual((conf["assessment"], conf["group"]), ("ARTIFACT_CONFIRMED", "ARTIFACT"))
        self.assertEqual((conf["split"], conf["split_adjusted_ret1"]), ("2026-11-10 1:24", 0.0))
        self.assertEqual((conf["previous_session"], conf["previous_session_source"], conf["units"]),
                         ("2026-11-09", "recorded", "PRE_SPLIT_CONFIRMED"))
        self.assertIsNone(conf["evidence_gap"])
        self.assertEqual(conf["supersedes"], records[0]["record_hash"])
        records = self.write(*second)
        self.assertEqual(sa.verify(records=records, specs=self.specs), [])
        self.assertEqual(self.removed(records), {self.sid})
        return records

    def check_gap_night(self, records, p, gap):
        out = sa.propose_reassessments(self.specs, records, {"CEX": p}, "pull", N3, retrieved_on="2026-11-12")
        self.assertEqual(len(out), 1)
        rec = out[0]
        self.assertGap(rec, gap)
        self.assertEqual(rec["pull_role"], "later")
        # It supersedes the set's last record.
        self.assertEqual(rec["supersedes"], records[-1]["record_hash"])
        return rec

    def check_still_excluded(self, records):
        self.assertEqual(sa.latest(records)[self.sid]["assessment"], "NOT_ASSESSABLE")
        self.assertEqual(sa.standing(records)[self.sid]["assessment"], "ARTIFACT_CONFIRMED")
        self.assertEqual(self.removed(records), {self.sid})
        self.assertEqual(sa.unresolved_set_ids(records), set())
        self.assertEqual(sa.verify(records=records, specs=self.specs), [])

    def test_absent_block_keeps_the_artifact(self):
        records = self.seal_and_confirm()
        for name, p in absent_variants(CEX_LATER_BARS).items():
            with self.subTest(name):
                rec = self.check_gap_night(records, p, GAP_ABSENT)
                self.check_still_excluded(self.fork(rec))

    def test_malformed_block_keeps_the_artifact(self):
        records = self.seal_and_confirm()
        for name, p in malformed_variants(CEX_LATER_BARS).items():
            with self.subTest(name):
                rec = self.check_gap_night(records, p, GAP_MALFORMED)
                self.check_still_excluded(self.fork(rec))

    def test_full_sequence_of_nights(self):
        records = self.seal_and_confirm()
        absent = chart(CEX_LATER_BARS)
        bad = chart(CEX_LATER_BARS, {"splits": bad_numerator(*CEX_SPLIT)})

        # Night 3: the block is absent.
        rec = self.check_gap_night(records, absent, GAP_ABSENT)
        records = self.write(rec)
        self.check_still_excluded(records)
        self.assertEqual(sa.verify(specs=self.specs), [])  # from disk, with the hash chain

        # Night 4: the same gap again appends nothing.
        self.assertEqual(sa.propose_reassessments(self.specs, records, {"CEX": absent}, "pull", N4,
                                                  retrieved_on="2026-11-13"), [])

        # Night 5: the block is malformed instead: only the kind of gap changes, and that is recorded.
        out = sa.propose_reassessments(self.specs, records, {"CEX": bad}, "pull", N5, retrieved_on="2026-11-14")
        self.assertEqual(len(out), 1)
        self.assertGap(out[0], GAP_MALFORMED)
        self.assertEqual(out[0]["supersedes"], records[-1]["record_hash"])
        records = self.write(*out)
        self.check_still_excluded(records)
        self.assertEqual(sa.propose_reassessments(self.specs, records, {"CEX": bad}, "pull", N5,
                                                  retrieved_on="2026-11-14"), [])

        # Night 6: the split is listed again: ARTIFACT_CONFIRMED supersedes the gap record.
        out = sa.propose_reassessments(self.specs, records, {"CEX": cex_listed()}, "pull", N6,
                                       retrieved_on="2026-11-15")
        self.assertEqual(len(out), 1)
        back = out[0]
        self.assertEqual((back["assessment"], back["evidence_gap"]), ("ARTIFACT_CONFIRMED", None))
        self.assertEqual(back["supersedes"], records[-1]["record_hash"])
        records = self.write(*out)
        self.assertEqual(len(records), 5)
        self.assertEqual(sa.latest(records)[self.sid]["assessment"], "ARTIFACT_CONFIRMED")
        self.assertEqual(sa.standing(records)[self.sid]["record_hash"], records[-1]["record_hash"])
        self.assertEqual(self.removed(records), {self.sid})
        self.assertEqual(sa.verify(records=records, specs=self.specs), [])
        self.assertEqual(sa.verify(specs=self.specs), [])
        for r in records:
            self.assertIn("evidence_gap", r)

    def test_first_assessment_artifact_then_gap(self):
        # The same counterexample without a seal: the first assessment (pull_role later, Case B) is already
        # ARTIFACT_CONFIRMED; the gap night is protected all the same.
        first = sa.propose_assessments(self.specs, [], {"CEX": cex_listed()}, "pull", N2)
        self.assertEqual((first[0]["assessment"], first[0]["pull_role"]), ("ARTIFACT_CONFIRMED", "later"))
        self.assertIsNone(first[0]["evidence_gap"])
        records = self.write(*first)
        for name, (p, gap) in {"absent": (chart(CEX_LATER_BARS), GAP_ABSENT),
                               "malformed": (chart(CEX_LATER_BARS, {"splits": []}), GAP_MALFORMED)}.items():
            with self.subTest(name):
                rec = self.check_gap_night(records, p, gap)
                self.check_still_excluded(self.fork(rec))

    def test_listed_response_with_post_split_closes_displaces_the_artifact(self):
        # A later response lists the 1-for-24 split on 2026-11-09 instead, and shows 2026-11-09 at 1.00: Case A at
        # the seal's previous session 2026-11-09, q = 1 = p: UNCHANGED. Straddle: P = 2026-11-09 >= 2026-11-09: NO.
        # CA-4 and CA-5 need a straddle not NO. r = 24 >= 4: CA-6, UNEXPLAINED_EXTREME_MOVE. Not NOT_ASSESSABLE, so
        # it becomes the standing assessment and the set is no longer removed.
        records = self.seal_and_confirm()
        gap = self.check_gap_night(records, chart(CEX_LATER_BARS), GAP_ABSENT)
        records = self.write(gap)
        pull = listed([("2026-11-05", 1.06), ("2026-11-06", 1.04), ("2026-11-09", 1.00), ("2026-11-10", 24.0)],
                      ("2026-11-09", 1, 24))
        out = sa.propose_reassessments(self.specs, records, {"CEX": pull}, "pull", N4, retrieved_on="2026-11-13")
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["assessment"], out[0]["evidence_gap"]), ("UNEXPLAINED_EXTREME_MOVE", None))
        self.assertEqual(out[0]["supersedes"], records[-1]["record_hash"])
        records = self.write(*out)
        self.assertEqual(sa.standing(records)[self.sid]["assessment"], "UNEXPLAINED_EXTREME_MOVE")
        self.assertEqual(self.removed(records), set())
        self.assertEqual(sa.verify(records=records, specs=self.specs), [])


# ==================================================================================================================
# An evidence-backed reversal is still possible
# ==================================================================================================================

def rvx():
    # Signal 2026-11-10: 5.15 / 2.50 = 2.06, recorded +106%.
    return {"set_id": "US-RVX-20261110", "ticker": "RVX", "market": "US", "signal_session": S,
            "signal": {"close": 5.15, "previous": 2.50}, "decision": {}}


RVX_PRE = [("2026-11-04", 7.30), ("2026-11-05", 7.20), ("2026-11-06", 7.10)]


def rvx_artifact_pull():
    # A 1-for-2.8 split listed on the signal session 2026-11-10 and 2026-11-09 at 7.00 = 2.50 * 2.8.
    # Case B (no seal): no bar within 1% of 2.50; for the event 2026-11-10, the latest reference session before it
    # with a close within 3% of 7.00 is 2026-11-09: PRE_SPLIT_CONFIRMED. 2.06 / 2.8 - 1 = -0.2643 < 0.30:
    # ARTIFACT_CONFIRMED.
    return listed(RVX_PRE + [("2026-11-09", 7.00), ("2026-11-10", 5.15)], ("2026-11-10", 1, 2.8))


def rvx_real_pull():
    # The provider now lists the split effective 2026-11-09 and shows 2026-11-09 at 2.50: the previous close was
    # recorded on the split's effective session, so both closes are post-split. Case B: Xu = 2026-11-09 (2.50 = p),
    # UNCHANGED, P = 2026-11-09. E = {2026-11-09} (S - 10 < 2026-11-09 <= S). Straddle: P >= effective: NO.
    # CA-2/3 no; CA-4, CA-5 need straddle not NO; CA-6: 2.06 < 4; CA-7: 1 day; CA-8: E not empty:
    # REAL_MOVE_AFTER_SPLIT, group REAL.
    return listed(RVX_PRE + [("2026-11-09", 2.50), ("2026-11-10", 5.15)], ("2026-11-09", 1, 2.8))


class EvidenceBackedReversal(LedgerCase):

    def setUp(self):
        super().setUp()
        self.spec, self.specs = rvx(), [rvx()]
        self.sid = self.spec["set_id"]
        first = sa.propose_assessments(self.specs, [], {"RVX": rvx_artifact_pull()}, "pull", N1)
        self.assertEqual((first[0]["assessment"], first[0]["split_adjusted_ret1"]), ("ARTIFACT_CONFIRMED", -0.2643))
        self.records = self.write(*first)
        self.assertEqual(sa.removed_set_ids("corrected", records=self.records, v11_flags=[]), {self.sid})

    def check_reversal(self, records, at):
        self.assertEqual(sa.split_event_coverage(rvx_real_pull()), LISTED)
        out = sa.propose_reassessments(self.specs, records, {"RVX": rvx_real_pull()}, "pull", at,
                                       retrieved_on="2026-11-14")
        self.assertEqual(len(out), 1)
        rec = out[0]
        self.assertEqual((rec["assessment"], rec["group"]), ("REAL_MOVE_AFTER_SPLIT", "REAL"))
        self.assertIsNone(rec["evidence_gap"])
        self.assertEqual((rec["previous_session"], rec["units"]), ("2026-11-09", "UNCHANGED"))
        self.assertEqual(rec["supersedes"], records[-1]["record_hash"])
        records = self.write(rec)
        self.assertEqual(sa.standing(records)[self.sid]["assessment"], "REAL_MOVE_AFTER_SPLIT")
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[]), set())
        self.assertEqual(sa.verify(records=records, specs=self.specs), [])
        self.assertEqual(sa.verify(specs=self.specs), [])

    def test_reversal_directly(self):
        self.check_reversal(self.records, N2)

    def test_reversal_after_a_gap_night(self):
        gap = sa.propose_reassessments(self.specs, self.records, {"RVX": chart(RVX_PRE + [("2026-11-09", 7.00),
                                                                                         ("2026-11-10", 5.15)])},
                                       "pull", N2, retrieved_on="2026-11-11")
        self.assertEqual(len(gap), 1)
        self.assertGap(gap[0], GAP_ABSENT)
        records = self.write(*gap)
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[]), {self.sid})
        self.check_reversal(records, N3)


# ==================================================================================================================
# No protection when the finding is not event-based; first assessments unchanged
# ==================================================================================================================

def naf():
    # Signal 2026-11-10: 1.40 / 1.00, recorded +40%.
    return {"set_id": "US-NAF-20261110", "ticker": "NAF", "market": "US", "signal_session": S,
            "signal": {"close": 1.40, "previous": 1.00}, "decision": {}}


class NotEventBased(LedgerCase):

    def test_no_action_found_then_refresh_without_events(self):
        spec, specs = naf(), [naf()]
        # Case B: Xu = 2026-11-09 (1.00 = p), E empty, r = 1.4 < 4, gap 1 day, NO_ACTION_FOUND; a reference bar
        # exists, so addendum 2 point 1 does not apply.
        own = chart([("2026-11-05", 1.02), ("2026-11-06", 1.01), ("2026-11-09", 1.00), ("2026-11-10", 1.40)])
        first = sa.propose_assessments(specs, [], {"NAF": own}, "pull", N1)
        self.assertEqual((first[0]["assessment"], first[0]["evidence_gap"]), ("NO_ACTION_FOUND", None))
        records = self.write(*first)
        # The refresh shows every earlier close at about 2.00 and lists no split: Case B, nothing within 1% of
        # 1.00, E empty: INCONSISTENT, UNITS_INCONSISTENT, classified as before.
        refresh = chart([("2026-11-05", 2.04), ("2026-11-06", 2.02), ("2026-11-09", 2.00), ("2026-11-10", 1.40)])
        for name, p in {"no events": refresh, "splits empty": chart(
                [("2026-11-05", 2.04), ("2026-11-06", 2.02), ("2026-11-09", 2.00), ("2026-11-10", 1.40)],
                {"splits": {}}), "splits malformed": chart(
                [("2026-11-05", 2.04), ("2026-11-06", 2.02), ("2026-11-09", 2.00), ("2026-11-10", 1.40)],
                {"splits": "?"})}.items():
            with self.subTest(name):
                out = sa.propose_reassessments(specs, records, {"NAF": p}, "pull", N2, retrieved_on="2026-11-11")
                self.assertEqual(len(out), 1)
                self.assertEqual((out[0]["assessment"], out[0]["evidence_gap"]), ("UNITS_INCONSISTENT", None))
                forked = self.fork(*out)
                self.assertEqual(sa.standing(forked)[spec["set_id"]]["assessment"], "UNITS_INCONSISTENT")
                self.assertEqual(sa.verify(records=forked, specs=specs), [])

    def test_unexplained_extreme_move_then_refresh_without_events(self):
        spec, specs = cex(), [cex()]
        first = sa.propose_assessments(specs, [], {"CEX": cex_own_pull()}, "pull", N1, seal_session=S)
        self.assertEqual((first[0]["assessment"], first[0]["evidence_gap"]), ("UNEXPLAINED_EXTREME_MOVE", None))
        records = self.write(*first)
        # Case A at 2026-11-09: q = 24, not 1; no event: INCONSISTENT, UNITS_INCONSISTENT. Not protected.
        for name, p in {"absent": chart(CEX_LATER_BARS),
                        "malformed": chart(CEX_LATER_BARS, {"splits": bad_numerator(*CEX_SPLIT)})}.items():
            with self.subTest(name):
                out = sa.propose_reassessments(specs, records, {"CEX": p}, "pull", N2, retrieved_on="2026-11-11")
                self.assertEqual(len(out), 1)
                self.assertEqual((out[0]["assessment"], out[0]["evidence_gap"]), ("UNITS_INCONSISTENT", None))
                self.assertEqual(sa.verify(records=self.fork(*out), specs=specs), [])

    def test_standing_not_assessable_is_not_protected(self):
        # A set whose records are all NOT_ASSESSABLE (no priced bar): its standing finding is not event-based.
        spec, specs = cex(), [cex()]
        first = sa.propose_assessments(specs, [], {"CEX": None}, "pull", N1)
        self.assertEqual((first[0]["assessment"], first[0]["evidence_gap"]), ("NOT_ASSESSABLE", None))
        records = self.write(*first)
        out = sa.propose_reassessments(specs, records, {"CEX": chart(CEX_LATER_BARS)}, "pull", N2,
                                       retrieved_on="2026-11-11")
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["assessment"], out[0]["evidence_gap"]), ("UNITS_INCONSISTENT", None))


class FirstAssessmentsUnchanged(unittest.TestCase):

    def test_propose_assessments_never_sets_evidence_gap(self):
        specs = [cex(), rvx(), naf()]
        for name, p in {**absent_variants(CEX_LATER_BARS), **malformed_variants(CEX_LATER_BARS),
                        "listed": cex_listed(), "none": None}.items():
            with self.subTest(name):
                payloads = {"CEX": p, "RVX": p, "NAF": p}
                for seal_session in (None, S):
                    out = sa.propose_assessments(specs, [], payloads, "pull", N1, seal_session=seal_session)
                    self.assertEqual(len(out), 3)
                    for r in out:
                        self.assertEqual(set(r), RECORD_KEYS)
                        self.assertIsNone(r["evidence_gap"])
        # The counterexample's absent block, as a first assessment, is the rule's UNITS_INCONSISTENT.
        out = sa.propose_assessments([cex()], [], {"CEX": chart(CEX_LATER_BARS)}, "pull", N1)
        self.assertEqual(out[0]["assessment"], "UNITS_INCONSISTENT")


# ==================================================================================================================
# changed() and verify()
# ==================================================================================================================

class ChangedAndVerify(LedgerCase):

    def test_changed_sees_the_kind_of_gap(self):
        a = arec(cex(), "NOT_ASSESSABLE", N2, evidence_gap=GAP_ABSENT)
        self.assertFalse(sa.changed(dict(a), a))
        self.assertTrue(sa.changed(dict(a, evidence_gap=GAP_MALFORMED), a))
        self.assertTrue(sa.changed(dict(a, evidence_gap=None), a))

    def ledger(self, **over):
        """A sound two-record ledger for CEX: ARTIFACT_CONFIRMED, then a gap record (fields overridable)."""
        spec = cex()
        r1 = arec(spec, "ARTIFACT_CONFIRMED", N2, split="2026-11-10 1:24", adjusted=0.0,
                  previous_session="2026-11-09", source="matched", units="PRE_SPLIT_CONFIRMED")
        sealed = self.fork(r1)
        r2 = arec(spec, "NOT_ASSESSABLE", N3, supersedes=sealed[0]["record_hash"], evidence_gap=GAP_ABSENT)
        r2.update(over)
        if "assessment" in over:
            r2["group"] = GROUP_OF[over["assessment"]]
        return self.fork(r1, r2)

    def test_sound_gap_records(self):
        for gap in (GAP_ABSENT, GAP_MALFORMED):
            with self.subTest(gap):
                self.assertEqual(sa.verify(records=self.ledger(evidence_gap=gap), specs=[cex()]), [])

    def test_unknown_evidence_gap_value(self):
        for bad in ("SPLIT_EVENTS_MISSING", "", "ABSENT", 1, ["SPLIT_EVENTS_ABSENT"]):
            with self.subTest(bad=bad):
                self.assertNotEqual(sa.verify(records=self.ledger(evidence_gap=bad), specs=[cex()]), [])

    def test_evidence_gap_on_a_record_that_is_not_not_assessable(self):
        for cls in ("UNITS_INCONSISTENT", "ARTIFACT_PROBABLE", "NO_ACTION_FOUND"):
            for gap in (GAP_ABSENT, GAP_MALFORMED):
                with self.subTest(cls=cls, gap=gap):
                    records = self.ledger(assessment=cls, evidence_gap=gap)
                    self.assertNotEqual(sa.verify(records=records, specs=[cex()]), [])
                    # Control: the same record with evidence_gap None is sound.
                    ok = self.ledger(assessment=cls, evidence_gap=None)
                    self.assertEqual(sa.verify(records=ok, specs=[cex()]), [])

    def test_first_record_with_a_bad_gap(self):
        spec = cex()
        good = self.fork(arec(spec, "NOT_ASSESSABLE", N1, evidence_gap=GAP_MALFORMED))
        self.assertEqual(sa.verify(records=good, specs=[spec]), [])
        bad = self.fork(arec(spec, "ARTIFACT_CONFIRMED", N1, evidence_gap=GAP_MALFORMED, units="PRE_SPLIT_CONFIRMED"))
        self.assertNotEqual(sa.verify(records=bad, specs=[spec]), [])


if __name__ == "__main__":
    unittest.main()

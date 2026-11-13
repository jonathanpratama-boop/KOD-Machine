"""SPLIT_UNITS_V1 and the split-assessment ledger (SPLIT_REVISIONS_v1).

Written by the independent test author from the frozen CONTRACT.md and its addenda (CONTRACT_ADDENDUM_1.md,
CONTRACT_ADDENDUM_2.md) alone, without seeing the implementation (house rule 5). Every expected value is derived
from those texts; the arithmetic is in the comments. The readings chosen where the texts are silent or ambiguous are
in CONTRACT_QUESTIONS.md.

Constants used in the comments (contract, part A):
    T = 0.30, extreme ratio 4.0, previous-bar gap 5 days, event window 10 days, reference window 30 days,
    ln(1.01) = 0.009950 (unchanged), ln(1.03) = 0.029559 (re-based), ln(1.05) = 0.048790 (smallest split factor).
    k = denominator / numerator, as in the V11 rule: a 1-for-10 reverse split has numerator 1, denominator 10, k = 10.

Prices are illustrative US microcap prices. Only the dates, the split ratios and the +106% move of SMX, and the
1-for-24 split of GOVX, come from PROTOCOL.md; GNTA and its signal session come from CONTRACT_ADDENDUM_1.md; ADIL, its
signal session, its +36.12% and its one-bar response come from CONTRACT_ADDENDUM_2.md. Tickers XONE, XTWO, XTRI, RSPL,
AAA, BBB, CCC, DDD are invented.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from idxsig import split_units, split_assessments, split_flags, paper_book as book, paper_book_report, paper

sa = split_assessments

CLASSIFY_KEYS = {"class", "group", "previous_session", "previous_session_source", "units", "event", "adjusted_ret1",
                 "later_factor"}
RECORD_KEYS = {"type", "rule", "set_id", "ticker", "market", "signal_session", "recorded_ret1", "assessment", "group",
               "split", "split_adjusted_ret1", "previous_session", "previous_session_source", "units", "later_factor",
               "pull_role", "supersedes", "basis", "sources", "assessed_at"}
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
UNITS = {"UNCHANGED", "PRE_SPLIT_CONFIRMED", "INCONSISTENT", "UNKNOWN"}
NEW_HEADING = "## Secondary view: split-unit assessments (display only, the frozen verdict above is unchanged)"
LEGACY_HEADING = (
    "## Secondary view: sets tagged SPLIT_ARTIFACT_V11 excluded "
    "(display only, the frozen verdict above is unchanged)"
)

S = "2026-11-10"  # Tuesday. E takes events effective 2026-11-01 .. 2026-11-10; reference bars 2026-10-11 .. 2026-11-09
P = "2026-11-09"  # the Monday before it
S5, P5 = "2026-11-05", "2026-11-04"  # Thursday and Wednesday: S5 - 10, S5 - 9, S5 - 30 and S5 - 31 are all weekdays
S20, P20 = "2026-10-20", "2026-10-19"  # Tuesday and Monday; a split on 2026-11-02 is a later split for this signal


def ev(day, n=1, d=10):
    return {"effective_session": day, "numerator": n, "denominator": d, "provider_ratio": f"{n}:{d}"}


# A split far outside every window: it is not in E and not a later split, but a pull that lists it was consulted.
OLD = [ev("2026-06-12", 1, 20)]


def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())


def unix(day):
    """14:30 UTC on an ISO date: 09:30 in New York in November, 10:30 in October. The New York date is `day`."""
    y, m, d = (int(x) for x in day.split("-"))
    return ts(y, m, d, 14, 30)


def payload(bars=(), splits=()):
    """A provider chart payload in the shape of tests/test_split_flags.py, with the bars the contract adds.
    bars: (session, close). splits: (session, numerator, denominator[, ratio string or None for no string])."""
    result = {
        "meta": {"currency": "USD", "exchangeTimezoneName": "America/New_York"},
        "timestamp": [unix(day) for day, _ in bars],
        "indicators": {"quote": [{"close": [close for _, close in bars]}]},
    }
    if splits:
        events = {}
        for day, n, d, *ratio in splits:
            e = {"date": unix(day), "numerator": n, "denominator": d}
            text = ratio[0] if ratio else f"{n}:{d}"
            if text is not None:
                e["splitRatio"] = text
            events[str(e["date"])] = e
        result["events"] = {"splits": events}
    return {"chart": {"result": [result], "error": None}}


def set_rec(sid="US-1", ticker="RSPL", close=9.84, prev=1.0, session=S):
    return {"set_id": sid, "ticker": ticker, "market": "US", "signal_session": session,
            "signal": {"close": close, "previous": prev}, "decision": {}}


def classify(close, previous, session, events, bars, **kw):
    return split_units.classify(close, previous, session, events, bars, **kw)


# ---- sets and pulls of part C ------------------------------------------------------------------------------------

def smx():
    # Signal 2026-11-10, +106%: 5.15 / 2.50 - 1 = 1.06. The previous bar, 2026-11-09, is the first post-split session.
    return set_rec("US-SMX-20261110", "SMX", 5.15, 2.50, "2026-11-10")


def smx_own_pull():
    # The scan's pull on the evening of 2026-11-10: the 1-for-2.8 split of 2026-11-09 is listed, history is re-based.
    return payload(bars=[("2026-11-04", 3.08), ("2026-11-05", 2.91), ("2026-11-06", 2.80), ("2026-11-09", 2.50),
                         ("2026-11-10", 5.15)], splits=[("2026-11-09", 1, 2.8)])


def smx_later_pull():
    return payload(bars=[("2026-11-04", 3.08), ("2026-11-05", 2.91), ("2026-11-06", 2.80), ("2026-11-09", 2.50),
                         ("2026-11-10", 5.15), ("2026-11-11", 4.70), ("2026-11-12", 4.41)],
                   splits=[("2026-11-09", 1, 2.8)])


def govx():
    # Signal 2026-11-11: 5.52 / 0.25 = 22.08, recorded +2108%. 0.25 is the pre-split close of 2026-11-10.
    return set_rec("US-GOVX-20261111", "GOVX", 5.52, 0.25, "2026-11-11")


def govx_own_pull():
    # The scan's pull on the evening of 2026-11-11: no split listed, the history still in pre-split units.
    return payload(bars=[("2026-11-05", 0.31), ("2026-11-06", 0.29), ("2026-11-09", 0.27), ("2026-11-10", 0.25),
                         ("2026-11-11", 5.52)])


def govx_later_pull():
    # 2026-11-12: the 1-for-24 split is listed on 2026-11-11 and the history is re-based (0.25 * 24 = 6.00).
    return payload(bars=[("2026-11-05", 7.44), ("2026-11-06", 6.96), ("2026-11-09", 6.48), ("2026-11-10", 6.00),
                         ("2026-11-11", 5.52), ("2026-11-12", 5.10)], splits=[("2026-11-11", 1, 24)])


def vcig():
    # Signal 2026-11-02: 2.70 / 0.60 = 4.5, recorded +350%.
    return set_rec("US-VCIG-20261102", "VCIG", 2.70, 0.60, "2026-11-02")


def vcig_later_pull(extra=()):
    # Nothing in this pull is within 1% of 0.60, and the 1-for-3 split of 2026-10-29 does not reconcile it either:
    # 0.60 * 3 = 1.80, while the bars before the split are 1.42 and 1.31.
    return payload(bars=[("2026-10-27", 1.42), ("2026-10-28", 1.31), ("2026-10-29", 1.22), ("2026-10-30", 1.15),
                         ("2026-11-02", 2.70), ("2026-11-03", 2.31), *extra], splits=[("2026-10-29", 1, 3)])


def tops():
    return set_rec("US-TOPS-20261109", "TOPS", 9.84, 1.00, "2026-11-09")


def xtri():
    # Signal 2026-11-03: 6.30 / 2.00 = 3.15. A 1-for-3 split is effective on the signal session.
    return set_rec("US-XTRI-20261103", "XTRI", 6.30, 2.00, "2026-11-03")


def gnta():
    # One of the four sets of CONTRACT_ADDENDUM_1.md, signal 2026-11-02. 4.03 / 3.00 - 1 = 0.3433: not extreme.
    return set_rec("US-GNTA-20261102", "GNTA", 4.03, 3.00, "2026-11-02")


def empty_response(ticker="GNTA"):
    """The provider's response for those four sets: metadata, an empty quote, no timestamps and no events."""
    return {"chart": {"result": [{
        "meta": {"currency": "USD", "symbol": ticker, "exchangeTimezoneName": "America/New_York",
                 "dataGranularity": "1d"},
        "indicators": {"quote": [{}], "adjclose": [{}]}}], "error": None}}


def error_response():
    """A response that carries an error instead of data."""
    return {"chart": {"result": None,
                      "error": {"code": "Not Found", "description": "No data found, symbol may be delisted"}}}


def adil():
    # The set of CONTRACT_ADDENDUM_2.md: signal 2026-10-28, recorded +36.12%. 3.403 / 2.50 - 1 = 0.3612.
    return set_rec("US-ADIL-20261028", "ADIL", 3.403, 2.50, "2026-10-28")


def adil_response():
    """The provider's response for ADIL: exactly one bar, on the signal session, and no events."""
    return payload(bars=[("2026-10-28", 3.403)])


def v11(spec, flag, assessed_at, split="", adjusted=None):
    """A complete record of the V11 ledger (the keys of tests/test_split_flags.py)."""
    s = spec["signal"]
    return {"type": "SPLIT_FLAG", "rule": "SPLIT_ARTIFACT_V11", "set_id": spec["set_id"], "ticker": spec["ticker"],
            "market": spec["market"], "signal_session": spec["signal_session"],
            "recorded_ret1": round(s["close"] / s["previous"] - 1, 4), "flag": flag, "split": split,
            "split_adjusted_ret1": adjusted, "basis": "provider events in the pull of the night",
            "assessed_at": assessed_at}


def arec(spec, assessment, assessed_at, *, pull_role="later", supersedes=None, split="", adjusted=None,
         previous_session=None, source=None, units="UNKNOWN", basis="provider pull", later_factor=None):
    """A complete, unsealed SPLIT_ASSESSMENT record written by hand: the twenty keys of the contract."""
    s = spec["signal"]
    return {"type": "SPLIT_ASSESSMENT", "rule": "SPLIT_UNITS_V1", "set_id": spec["set_id"], "ticker": spec["ticker"],
            "market": spec["market"], "signal_session": spec["signal_session"],
            "recorded_ret1": round(s["close"] / s["previous"] - 1, 4), "assessment": assessment,
            "group": GROUP_OF[assessment], "split": split, "split_adjusted_ret1": adjusted,
            "previous_session": previous_session, "previous_session_source": source, "units": units,
            "later_factor": later_factor, "pull_role": pull_role, "supersedes": supersedes, "basis": basis,
            "sources": [], "assessed_at": assessed_at}


def govx_seal(at="2026-11-11T22:10:05Z"):
    """What the scan's own pull gives for GOVX (see ContractCases.test_case_2): no split listed, an extreme move."""
    return arec(govx(), "UNEXPLAINED_EXTREME_MOVE", at, pull_role="seal", previous_session="2026-11-10",
                source="matched", units="UNCHANGED", basis="pull us_2026-11-11")


def govx_confirmed(supersedes, at="2026-11-12T22:05:00Z", **over):
    """What the later pull gives for GOVX: the previous close re-based by 24, 22.08 / 24 - 1 = -0.08."""
    rec = arec(govx(), "ARTIFACT_CONFIRMED", at, supersedes=supersedes, split="2026-11-11 1:24", adjusted=-0.08,
               previous_session="2026-11-10", source="recorded", units="PRE_SPLIT_CONFIRMED",
               basis="pull us_2026-11-12")
    return dict(rec, **over)


def smx_real(at="2026-11-12T10:06:00Z", pull_role="later"):
    return arec(smx(), "REAL_MOVE_AFTER_SPLIT", at, pull_role=pull_role, previous_session="2026-11-09",
                source="matched", units="UNCHANGED", basis="pull us_2026-11-12")


def row(spec, verdict="BUY_OK", owner=None, status="TRADED", net=None, dump=0.31):
    """One row of the paper book, in the format of paper_book.trades()."""
    return dict(set_id=spec["set_id"], ticker=spec["ticker"], session=spec["signal_session"], dump_tomorrow=dump,
                verdict=verdict, owner=owner, status=status, net=net)


def last_hash(records, sid):
    return [r for r in records if r.get("set_id") == sid][-1]["record_hash"]


class Base(unittest.TestCase):
    def check(self, res, cls, **expect):
        self.assertEqual(res["class"], cls)
        self.assertEqual(res["group"], GROUP_OF[cls])
        for key, value in expect.items():
            self.assertEqual(res[key], value, key)

    def check_event(self, res, day, k, adjusted):
        e = res["event"]
        self.assertIsNotNone(e)
        self.assertEqual(e["effective_session"], day)
        self.assertAlmostEqual(e["k"], k)
        self.assertAlmostEqual(e["denominator"] / e["numerator"], k)
        self.assertEqual(res["adjusted_ret1"], adjusted)

    def check_no_event(self, res):
        self.assertIsNone(res["event"])
        self.assertIsNone(res["adjusted_ret1"])


class LedgerCase(Base):
    """Both ledgers point at temporary paths, so nothing here reads or writes the repository's paper/ directory."""

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

    def write(self, *recs):
        """Seal records into the temporary assessment ledger; returns every sealed line, with real hashes."""
        paper.append(list(recs), path=self.path)
        return paper.ledger_lines(self.path)

    def write_flags(self, *recs):
        paper.append(list(recs), path=self.flags_path)
        return paper.ledger_lines(self.flags_path)


# ==================================================================================================================
# Part B1 constants
# ==================================================================================================================

class Constants(unittest.TestCase):
    def test_rule_id_and_the_eleven_classes(self):
        self.assertEqual(split_units.RULE_ID, "SPLIT_UNITS_V1")
        self.assertIsInstance(split_units.CLASSES, tuple)
        self.assertEqual(len(split_units.CLASSES), 11)
        self.assertEqual(set(split_units.CLASSES), set(GROUP_OF))

    def test_group_of_every_class(self):
        self.assertEqual(set(split_units.GROUP), set(GROUP_OF))
        self.assertEqual({c: split_units.GROUP[c] for c in GROUP_OF}, GROUP_OF)


# ==================================================================================================================
# Part A, step 5: each class once
# ==================================================================================================================

class ElevenClasses(Base):
    def test_no_action_found(self):
        # r = 1.50 / 1.00 = 1.5. No recorded previous session and reference bars exist: Case B. The latest
        # reference bar, 2026-11-09 at 1.00, equals p: units UNCHANGED, P = 2026-11-09. E is empty, r < 4,
        # S - P = 1 day: CA-9.
        res = classify(1.50, 1.00, S, [], [("2026-11-06", 0.97), (P, 1.00)])
        self.check(res, "NO_ACTION_FOUND", previous_session=P, previous_session_source="matched",
                   units="UNCHANGED", later_factor=None)
        self.check_no_event(res)

    def test_real_move_after_split(self):
        # 1-for-2.8 effective 2026-11-09 (k = 2.8), inside E. p = 2.50 is the close of 2026-11-09, c = 5.15, r = 2.06.
        # Case B: the latest reference bar within 1% of p is 2026-11-09 (2.50); 2026-11-06 at 2.80 is 12% away.
        # Units UNCHANGED, P = 2026-11-09. Straddle: P >= the effective session, NO. CA-4 and CA-5 need a straddle
        # that is not NO; r < 4; S - P = 1; E is not empty: CA-8.
        res = classify(5.15, 2.50, S, [ev(P, 1, 2.8)], [("2026-11-06", 2.80), (P, 2.50)])
        self.check(res, "REAL_MOVE_AFTER_SPLIT", previous_session=P, previous_session_source="matched",
                   units="UNCHANGED", later_factor=None)
        self.check_no_event(res)

    def test_real_move_after_split_when_the_split_moves_away_from_no_move(self):
        # r = 1.5, k = 10, straddle YES (bar at P unchanged, split on S). r / k - 1 = -0.85 < 0.30, but
        # |ln 0.15| = 1.897 is not < |ln 1.5| = 0.405: the event neither explains (CA-4) nor improves (CA-5).
        # r < 4, gap 1 day, E not empty: CA-8.
        res = classify(1.50, 1.00, S, [ev(S)], [(P, 1.00)], previous_session=P)
        self.check(res, "REAL_MOVE_AFTER_SPLIT", units="UNCHANGED")
        self.check_no_event(res)

    def test_artifact_confirmed(self):
        # Case A, P = 2026-11-09. The later pull shows 10.00 there: |ln(10.00 / 1.00)| = 2.30 > ln 1.01, not
        # unchanged. The 1-for-10 of 2026-11-10 is after P and |ln(10.00 / (1.00 * 10))| = 0 <= ln 1.03:
        # PRE_SPLIT_CONFIRMED. r / k - 1 = 9.84 / 10 - 1 = -0.016 < 0.30: CA-3, artifact.
        res = classify(9.84, 1.00, S, [ev(S)], [("2026-11-06", 10.40), (P, 10.00)], previous_session=P)
        self.check(res, "ARTIFACT_CONFIRMED", previous_session=P, previous_session_source="recorded",
                   units="PRE_SPLIT_CONFIRMED", later_factor=None)
        self.check_event(res, S, 10, -0.016)

    def test_real_move_units_contaminated(self):
        # The same confirmed units, but c = 15.00: r / k - 1 = 15 / 10 - 1 = 0.50 >= 0.30. CA-3, second row.
        res = classify(15.00, 1.00, S, [ev(S)], [(P, 10.00)], previous_session=P)
        self.check(res, "REAL_MOVE_UNITS_CONTAMINATED", units="PRE_SPLIT_CONFIRMED")
        self.assertEqual(res["group"], "CONTAMINATED")
        self.check_event(res, S, 10, 0.5)

    def test_artifact_probable_when_the_previous_bar_precedes_the_split(self):
        # Case A, the bar at P still shows 1.00: units UNCHANGED, so CA-3 does not apply. The split on S is after P:
        # straddle YES. It explains the move: 9.84 / 10 - 1 = -0.016 < 0.30 and |ln 0.984| = 0.016 < |ln 9.84| = 2.286.
        res = classify(9.84, 1.00, S, [ev(S)], [(P, 1.00)], previous_session=P)
        self.check(res, "ARTIFACT_PROBABLE", previous_session=P, previous_session_source="recorded",
                   units="UNCHANGED")
        self.check_event(res, S, 10, -0.016)

    def test_artifact_probable_below_the_extreme_ratio_when_the_straddle_is_yes(self):
        # Case A with no reference bar at P: units UNKNOWN, but P is known and precedes the split: straddle YES.
        # r = 3.15 < 4; the 1-for-3 explains it (3.15 / 3 - 1 = 0.05). A YES straddle is enough for CA-4, first row.
        res = classify(3.15, 1.00, S, [ev(S, 1, 3)], [], previous_session=P)
        self.check(res, "ARTIFACT_PROBABLE", previous_session=P, previous_session_source="recorded", units="UNKNOWN")
        self.check_event(res, S, 3, 0.05)

    def test_artifact_probable_when_the_straddle_is_unknown_and_the_move_extreme(self):
        # Case C: no recorded previous session, no reference bar. P unknown, straddle UNKNOWN. The split explains
        # the move and r = 9.84 >= 4: CA-4, first row.
        res = classify(9.84, 1.00, S, [ev(S)], [])
        self.check(res, "ARTIFACT_PROBABLE", previous_session=None, previous_session_source=None, units="UNKNOWN")
        self.check_event(res, S, 10, -0.016)

    def test_split_in_window_unresolved(self):
        # Case C again, r = 6.30 / 2.00 = 3.15 < 4. The 1-for-3 explains it: 3.15 / 3 - 1 = 0.05 < 0.30 and
        # |ln 1.05| = 0.049 < |ln 3.15| = 1.147. Straddle UNKNOWN and the move is not extreme: CA-4, second row.
        res = classify(6.30, 2.00, S, [ev(S, 1, 3)], [])
        self.check(res, "SPLIT_IN_WINDOW_UNRESOLVED", previous_session=None, previous_session_source=None,
                   units="UNKNOWN", later_factor=None)
        self.check_event(res, S, 3, 0.05)

    def test_real_move_units_unverified(self):
        # r = 3, k = 2: r / k - 1 = 0.50 >= 0.30, so the split does not explain the move, but
        # |ln 1.5| = 0.405 < |ln 3| = 1.099: CA-5. Once with the straddle UNKNOWN (Case C), once with it YES
        # (Case A, bar at P unchanged). The event of CA-5 is not "the event used by CA-3 or CA-4": event is None.
        for bars, kw in (([], {}), ([(P, 1.00)], {"previous_session": P})):
            with self.subTest(bars=bars):
                res = classify(3.00, 1.00, S, [ev(S, 1, 2)], bars, **kw)
                self.check(res, "REAL_MOVE_UNITS_UNVERIFIED")
                self.check_no_event(res)

    def test_unexplained_extreme_move(self):
        # 5.52 / 0.25 = 22.08 >= 4. Case B finds the unchanged bar of 2026-11-10; the pull lists no split: CA-6.
        res = classify(5.52, 0.25, "2026-11-11", [], [("2026-11-09", 0.27), ("2026-11-10", 0.25)])
        self.check(res, "UNEXPLAINED_EXTREME_MOVE", previous_session="2026-11-10", previous_session_source="matched",
                   units="UNCHANGED", later_factor=None)
        self.check_no_event(res)

    def test_stale_previous(self):
        # The recorded previous bar is 2026-11-04, unchanged in the pull. S - P = 6 days > 5; r = 1.5, no event: CA-7.
        res = classify(1.50, 1.00, S, [], [("2026-11-04", 1.00)], previous_session="2026-11-04")
        self.check(res, "STALE_PREVIOUS", previous_session="2026-11-04", previous_session_source="recorded",
                   units="UNCHANGED")
        self.check_no_event(res)

    def test_units_inconsistent(self):
        # Case A: the bar at P is 1.20, |ln 1.2| = 0.182 > ln 1.01, and there is no event to re-base by: CA-2.
        res = classify(1.50, 1.00, S, [], [(P, 1.20)], previous_session=P)
        self.check(res, "UNITS_INCONSISTENT", previous_session=P, previous_session_source="recorded",
                   units="INCONSISTENT", later_factor=None)
        self.check_no_event(res)

    def test_not_assessable(self):
        # Step 1 and "a close, previous close or session that is missing or invalid gives NOT_ASSESSABLE".
        good = {"close": 9.84, "previous": 1.00, "session": S}
        nan = float("nan")
        bad = [("close", None), ("close", 0), ("close", -9.84), ("close", nan), ("close", "abc"),
               ("previous", None), ("previous", 0), ("previous", -1.0), ("previous", nan), ("previous", "abc"),
               ("session", None), ("session", ""), ("session", "not-a-date"), ("session", "2026-11-31")]
        for name, value in bad:
            with self.subTest(name=name, value=value):
                a = dict(good, **{name: value})
                res = classify(a["close"], a["previous"], a["session"], [ev(S)], [(P, 10.00)])
                self.check(res, "NOT_ASSESSABLE", later_factor=None)
                self.check_no_event(res)


# ==================================================================================================================
# Part A, step 5: bounds and the order of the rules
# ==================================================================================================================

class FirstMatchingRule(Base):
    def test_threshold_is_met_at_exactly_30_percent(self):
        # Confirmed units, k = 10. c = 13.00: r / k - 1 = 0.30, which is not < T, so the move is real. In binary
        # floating point 13.0 / 10.0 - 1 = 0.30000000000000004, also >= 0.30; round(.., 4) = 0.3.
        at = classify(13.00, 1.00, S, [ev(S)], [(P, 10.00)], previous_session=P)
        self.check(at, "REAL_MOVE_UNITS_CONTAMINATED")
        self.check_event(at, S, 10, 0.3)
        # c = 12.99: r / k - 1 = 0.299 < 0.30.
        below = classify(12.99, 1.00, S, [ev(S)], [(P, 10.00)], previous_session=P)
        self.check(below, "ARTIFACT_CONFIRMED")
        self.check_event(below, S, 10, 0.299)

    def test_extreme_ratio_bound_without_a_split(self):
        # 2.00 / 0.50 = 4.0 exactly (both are binary fractions): r >= 4, CA-6. 1.99 / 0.50 = 3.98: CA-9.
        bars = [(P, 0.50)]
        self.check(classify(2.00, 0.50, S, [], bars), "UNEXPLAINED_EXTREME_MOVE")
        self.check(classify(1.99, 0.50, S, [], bars), "NO_ACTION_FOUND")

    def test_extreme_ratio_bound_with_an_unlocated_split(self):
        # Case C, 1-for-4 on S. r = 4.0: r / k - 1 = 0.0, explained, straddle UNKNOWN, r >= 4: ARTIFACT_PROBABLE.
        at = classify(2.00, 0.50, S, [ev(S, 1, 4)], [])
        self.check(at, "ARTIFACT_PROBABLE")
        self.check_event(at, S, 4, 0.0)
        # r = 3.98: r / k - 1 = -0.005, explained, straddle UNKNOWN, r < 4: unresolved.
        below = classify(1.99, 0.50, S, [ev(S, 1, 4)], [])
        self.check(below, "SPLIT_IN_WINDOW_UNRESOLVED")
        self.check_event(below, S, 4, -0.005)

    def test_previous_gap_bound(self):
        # S - P > 5 days is stale. 2026-11-05 is 5 days before S: not stale. 2026-11-04 is 6 days: stale.
        five = classify(1.50, 1.00, S, [], [("2026-11-05", 1.00)], previous_session="2026-11-05")
        self.check(five, "NO_ACTION_FOUND", previous_session="2026-11-05")
        # Case B finds its own previous bar; the gap is measured from the session it matched.
        six = classify(1.50, 1.00, S, [], [("2026-11-04", 1.00)])
        self.check(six, "STALE_PREVIOUS", previous_session="2026-11-04", previous_session_source="matched")

    def test_the_first_matching_rule_decides(self):
        stale = "2026-11-03"  # 7 days before S
        cases = {
            # r = 9.84 is extreme, but the bar at P (1.20) matches neither p nor a re-based value.
            "CA-2 before CA-6": (9.84, [], [(P, 1.20)], P, "UNITS_INCONSISTENT"),
            # P is 7 days old, but its bar (10.00) is p * 10 and 9.84 / 10 - 1 = -0.016.
            "CA-3 before CA-7": (9.84, [ev(S)], [(stale, 10.00)], stale, "ARTIFACT_CONFIRMED"),
            # The same stale P with an unchanged bar (1.00): the split after P explains the move.
            "CA-4 before CA-7": (9.84, [ev(S)], [(stale, 1.00)], stale, "ARTIFACT_PROBABLE"),
            # r = 8, k = 2: r / k - 1 = 3.0, not explained, but |ln 4| = 1.386 < |ln 8| = 2.079.
            "CA-5 before CA-6": (8.00, [ev(S, 1, 2)], [], None, "REAL_MOVE_UNITS_UNVERIFIED"),
            # r = 5 with no event; P unchanged but 7 days old.
            "CA-6 before CA-7": (5.00, [], [(stale, 1.00)], stale, "UNEXPLAINED_EXTREME_MOVE"),
            # 1-for-5 effective on P itself (straddle NO) and r = 5: the split cannot explain, the move is extreme.
            "CA-6 before CA-8": (5.00, [ev(P, 1, 5)], [(P, 1.00)], P, "UNEXPLAINED_EXTREME_MOVE"),
            # Split on 2026-11-03, P = 2026-11-04 (straddle NO) is 6 days old, r = 1.5.
            "CA-7 before CA-8": (1.50, [ev("2026-11-03")], [("2026-11-04", 1.00)], "2026-11-04", "STALE_PREVIOUS"),
        }
        for name, (close, events, bars, previous_session, cls) in cases.items():
            with self.subTest(name):
                self.check(classify(close, 1.00, S, events, bars, previous_session=previous_session), cls)

    def test_latest_explaining_event_is_used(self):
        # r = 9.84, Case C. 1-for-10 (2026-11-03) gives 0.984; 1-for-8 (2026-11-06) gives 1.23, +23% < 30% and
        # |ln 1.23| = 0.207 < 2.286: both explain the move. The later one is used, whatever the order of the list.
        a, b = ev("2026-11-03", 1, 10), ev("2026-11-06", 1, 8)
        for events in ([a, b], [b, a]):
            res = classify(9.84, 1.00, S, events, [])
            self.check(res, "ARTIFACT_PROBABLE")
            self.check_event(res, "2026-11-06", 8, 0.23)

    def test_split_on_the_previous_session_cannot_explain_the_move(self):
        # r = 3.15 and a 1-for-3 would explain it (3.15 / 3 - 1 = 0.05). The bar at P is unchanged.
        # Split effective on P: P >= effective session, straddle NO; CA-4 and CA-5 skip it; CA-8.
        on_p = classify(3.15, 1.00, S, [ev(P, 1, 3)], [(P, 1.00)], previous_session=P)
        self.check(on_p, "REAL_MOVE_AFTER_SPLIT", units="UNCHANGED")
        self.check_no_event(on_p)
        # The same split one session later, on S: straddle YES, CA-4.
        on_s = classify(3.15, 1.00, S, [ev(S, 1, 3)], [(P, 1.00)], previous_session=P)
        self.check(on_s, "ARTIFACT_PROBABLE")
        self.check_event(on_s, S, 3, 0.05)

    def test_adjusted_ret1_is_rounded_to_4_decimals(self):
        # 6.53 / 6 - 1 = 0.088333..., rounded 0.0883. Units confirmed: the bar at P is 1.00 * 6.
        res = classify(6.53, 1.00, S, [ev(S, 1, 6)], [(P, 6.00)], previous_session=P)
        self.check(res, "ARTIFACT_CONFIRMED")
        self.check_event(res, S, 6, 0.0883)


# ==================================================================================================================
# Part A, step 3: the previous bar and its units
# ==================================================================================================================

class PreviousBar(Base):
    def test_case_a_uses_the_recorded_session_only(self):
        # The bar at P is within 1% of p (|ln 1.004| = 0.0040): UNCHANGED.
        ok = classify(1.50, 1.00, S, [], [("2026-11-06", 1.20), (P, 1.004)], previous_session=P)
        self.check(ok, "NO_ACTION_FOUND", previous_session=P, previous_session_source="recorded", units="UNCHANGED")
        # The bar at P is 1.20. Another session matches p, but Case A looks at P alone: INCONSISTENT.
        bad = classify(1.50, 1.00, S, [], [("2026-11-06", 1.00), (P, 1.20)], previous_session=P)
        self.check(bad, "UNITS_INCONSISTENT", previous_session=P, previous_session_source="recorded",
                   units="INCONSISTENT")

    def test_case_a_without_a_reference_bar_at_p_is_unknown(self):
        # No bar at P, or a bar without a price (None or not greater than zero): units UNKNOWN, P still known.
        # r = 1.5, no event, gap 1 day: CA-9.
        for bars in ([("2026-11-06", 1.00)], [("2026-11-06", 1.00), (P, None)], [("2026-11-06", 1.00), (P, 0.0)],
                     [("2026-11-06", 1.00), (P, -1.00)]):
            with self.subTest(bars=bars):
                res = classify(1.50, 1.00, S, [], bars, previous_session=P)
                self.check(res, "NO_ACTION_FOUND", previous_session=P, previous_session_source="recorded",
                           units="UNKNOWN")

    def test_case_a_previous_session_outside_the_reference_window(self):
        # P = 2026-10-05 is S5 - 31: the bar there is not a reference bar, so the units are UNKNOWN. P is known
        # and 31 days old: CA-7.
        res = classify(1.50, 1.00, S5, OLD, [("2026-10-05", 1.00)], previous_session="2026-10-05")
        self.check(res, "STALE_PREVIOUS", previous_session="2026-10-05", previous_session_source="recorded",
                   units="UNKNOWN")

    def test_case_a_split_must_be_after_the_previous_session(self):
        # The bar at P shows 10.00 = p * 10, but the 1-for-10 is effective on P itself. PRE_SPLIT_CONFIRMED needs
        # P < effective session: no event qualifies, the units are INCONSISTENT.
        res = classify(9.84, 1.00, S, [ev(P)], [(P, 10.00)], previous_session=P)
        self.check(res, "UNITS_INCONSISTENT", units="INCONSISTENT")
        self.check_no_event(res)

    def test_case_b_takes_the_latest_unchanged_match(self):
        # 2026-11-09 is 20% away; of the two sessions within 1% of p the later is 2026-11-06. The list is unsorted
        # on purpose. S - P = 4 days: not stale.
        res = classify(1.50, 1.00, S, [], [("2026-11-05", 1.00), (P, 1.20), ("2026-11-06", 1.004)])
        self.check(res, "NO_ACTION_FOUND", previous_session="2026-11-06", previous_session_source="matched",
                   units="UNCHANGED")

    def test_case_b_unchanged_match_comes_before_any_rebased_match(self):
        # 2026-11-06 matches p as recorded, so Xu exists and the units are UNCHANGED, although the later bar of
        # 2026-11-09 equals p * 10. P = 2026-11-06 precedes the split: straddle YES, explained: CA-4, not CA-3.
        res = classify(9.84, 1.00, S, [ev(S)], [("2026-11-06", 1.00), (P, 10.00)])
        self.check(res, "ARTIFACT_PROBABLE", previous_session="2026-11-06", previous_session_source="matched",
                   units="UNCHANGED")

    def test_case_b_rebased_match(self):
        # Nothing is within 1% of p = 1.00. For the 1-for-10 of S: the latest reference bar before S within 3% of
        # p * k = 10.00 is 2026-11-09 (10.00); 10.40 is 4% away (|ln 1.04| = 0.039 > 0.0296).
        res = classify(9.84, 1.00, S, [ev(S)], [("2026-11-06", 10.40), (P, 10.00)])
        self.check(res, "ARTIFACT_CONFIRMED", previous_session=P, previous_session_source="rebased_match",
                   units="PRE_SPLIT_CONFIRMED", later_factor=None)
        self.check_event(res, S, 10, -0.016)

    def test_case_b_rebased_match_must_precede_the_split(self):
        # 1-for-5 effective 2026-11-04; p * k = 5.00. Bars on or after the effective session do not count.
        events = [ev("2026-11-04", 1, 5)]
        bars = [("2026-11-04", 5.00), ("2026-11-05", 5.00), (P, 5.00)]
        none = classify(5.20, 1.00, S, events, bars)
        self.check(none, "UNITS_INCONSISTENT", previous_session=None, previous_session_source=None,
                   units="INCONSISTENT")
        # With a bar on 2026-11-03 at 5.05 (|ln 1.01| = 0.00995 <= 0.0296): P = 2026-11-03, confirmed.
        # 5.20 / 5 - 1 = 0.04 < 0.30. P is 7 days old, but CA-3 comes before CA-7.
        found = classify(5.20, 1.00, S, events, bars + [("2026-11-03", 5.05)])
        self.check(found, "ARTIFACT_CONFIRMED", previous_session="2026-11-03",
                   previous_session_source="rebased_match", units="PRE_SPLIT_CONFIRMED")
        self.check_event(found, "2026-11-04", 5, 0.04)

    def test_case_b_tries_the_latest_event_first(self):
        # Two events in E. The later one (1-for-2 on S) has a match before it: 2026-11-09 at 2.00 = p * 2. The
        # earlier one (1-for-5 on 2026-11-04) would match 2026-11-03 at 5.00, but it is never reached.
        # 2.10 / 2 - 1 = 0.05.
        a, b = ev("2026-11-04", 1, 5), ev(S, 1, 2)
        for events in ([a, b], [b, a]):
            res = classify(2.10, 1.00, S, events, [("2026-11-03", 5.00), (P, 2.00)])
            self.check(res, "ARTIFACT_CONFIRMED", previous_session=P, previous_session_source="rebased_match")
            self.check_event(res, S, 2, 0.05)

    def test_case_b_nothing_matches(self):
        # No bar within 1% of p and no event: INCONSISTENT, P unknown.
        res = classify(1.50, 1.00, S, [], [("2026-11-06", 1.25), (P, 1.20)])
        self.check(res, "UNITS_INCONSISTENT", previous_session=None, previous_session_source=None,
                   units="INCONSISTENT")
        # An event whose re-based value does not match either: 7.00 against p * 10 = 10.00.
        res = classify(9.84, 1.00, S, [ev(S)], [(P, 7.00)])
        self.check(res, "UNITS_INCONSISTENT", previous_session=None, previous_session_source=None,
                   units="INCONSISTENT")
        self.check_no_event(res)

    def test_reference_window_bounds(self):
        # Reference bars have S - 30 <= X < S. For S5 = 2026-11-05: 2026-10-06 is in, 2026-10-05 is out, S5 itself
        # and anything after it are out. The pull lists an old split, so a source was consulted.
        inside = classify(1.50, 1.00, S5, OLD, [("2026-10-06", 1.00)])
        self.check(inside, "STALE_PREVIOUS", previous_session="2026-10-06", previous_session_source="matched",
                   units="UNCHANGED")
        for day in ("2026-10-05", S5, "2026-11-06"):
            with self.subTest(day=day):
                # No reference bar: Case C. P unknown, r = 1.5, E empty: CA-9.
                res = classify(1.50, 1.00, S5, OLD, [(day, 1.00)])
                self.check(res, "NO_ACTION_FOUND", previous_session=None, previous_session_source=None,
                           units="UNKNOWN")

    def test_a_bar_after_the_signal_is_not_a_previous_bar(self):
        # The day after the spike the price is back at 1.00 = p. That bar is not a reference bar; the only one,
        # 2026-11-09 at 1.20, does not match.
        res = classify(1.50, 1.00, S, [], [(P, 1.20), ("2026-11-11", 1.00)])
        self.check(res, "UNITS_INCONSISTENT", previous_session=None, units="INCONSISTENT")

    def test_unchanged_tolerance_is_one_percent_of_the_log_ratio(self):
        # |ln(q / p)| <= ln 1.01 = 0.009950.
        # 1.009: 0.008960, in. 0.991: 0.009041, in.
        # 1.011: 0.010940, out. 0.989: 0.011061, out. 0.99: |ln 0.99| = 0.010050 > 0.009950, out (the bound is on
        # the logarithm, so the lower edge is 1 / 1.01 = 0.990099, not 0.99).
        for q, cls in ((1.009, "NO_ACTION_FOUND"), (0.991, "NO_ACTION_FOUND"), (1.011, "UNITS_INCONSISTENT"),
                       (0.989, "UNITS_INCONSISTENT"), (0.99, "UNITS_INCONSISTENT")):
            with self.subTest(q=q):
                self.check(classify(1.50, 1.00, S, [], [(P, q)], previous_session=P), cls)

    def test_rebased_tolerance_is_three_percent_of_the_log_ratio(self):
        # |ln(q / (p * k))| <= ln 1.03 = 0.029559, with p * k = 10.00.
        # 10.29: 0.028587, in. 9.75: 0.025318, in. 10.31: 0.030529, out. 9.70: 0.030459, out.
        for q, cls in ((10.29, "ARTIFACT_CONFIRMED"), (9.75, "ARTIFACT_CONFIRMED"), (10.31, "UNITS_INCONSISTENT"),
                       (9.70, "UNITS_INCONSISTENT")):
            with self.subTest(q=q):
                self.check(classify(9.84, 1.00, S, [ev(S)], [(P, q)], previous_session=P), cls)


# ==================================================================================================================
# Part A, step 2: candidate events
# ==================================================================================================================

class CandidateEvents(Base):
    def test_window_bounds(self):
        # S5 = 2026-11-05, P5 = 2026-11-04 with an unchanged bar (2.00). r = 6.30 / 2.00 = 3.15; a 1-for-3 would
        # explain it. E takes S - 10 < effective session <= S.
        def c(day):
            return classify(6.30, 2.00, S5, [ev(day, 1, 3)], [(P5, 2.00)], previous_session=P5)

        self.check(c("2026-10-23"), "NO_ACTION_FOUND")  # 13 days before
        self.check(c("2026-10-26"), "NO_ACTION_FOUND")  # exactly 10 days: exclusive lower bound
        self.check(c("2026-10-27"), "REAL_MOVE_AFTER_SPLIT")  # 9 days: in E, before P, straddle NO, CA-8
        self.check(c(P5), "REAL_MOVE_AFTER_SPLIT")  # on P: in E, straddle NO
        self.check(c(S5), "ARTIFACT_PROBABLE")  # on the signal session: in E, straddle YES, explains
        after = c("2026-11-06")  # after the signal session: not in E; the bar matches p as written
        self.check(after, "NO_ACTION_FOUND", units="UNCHANGED", later_factor=None)

    def test_factor_too_close_to_one_is_ignored(self):
        # r = 1.5, bar at P unchanged, split on S. E needs |ln k| > ln 1.05.
        def c(n, d):
            return classify(1.50, 1.00, S, [ev(S, n, d)], [(P, 1.00)], previous_session=P)

        self.check(c(1, 1.04), "NO_ACTION_FOUND")  # ln 1.04 = 0.0392 < 0.0488
        self.check(c(1, 1.05), "NO_ACTION_FOUND")  # equal, and the comparison is strict
        self.check(c(1.04, 1), "NO_ACTION_FOUND")  # k = 1 / 1.04: |ln k| = 0.0392
        # k = 1.06 is an event (0.0583 > 0.0488), straddle YES. 1.5 / 1.06 - 1 = 0.415 >= 0.30: not explained;
        # |ln 1.415| = 0.347 < |ln 1.5| = 0.405: CA-5.
        self.check(c(1, 1.06), "REAL_MOVE_UNITS_UNVERIFIED")

    def test_forward_split_is_a_candidate_event(self):
        # 2-for-1: numerator 2, denominator 1, k = 0.5, |ln 0.5| = 0.693 > ln 1.05. It is in E with straddle YES.
        # r / k - 1 = 1.5 / 0.5 - 1 = 2.0, not explained; |ln 3| = 1.099 is not < |ln 1.5| = 0.405, not CA-5.
        # r < 4, gap 1 day, E not empty: CA-8 (CA-9 if forward splits were dropped).
        res = classify(1.50, 1.00, S, [ev(S, 2, 1)], [(P, 1.00)], previous_session=P)
        self.check(res, "REAL_MOVE_AFTER_SPLIT")
        self.check_no_event(res)

    def test_forward_split_artifact(self):
        # The rule is symmetric. 2-for-1 on S, recorded 5.00 / 10.00 (r = 0.5). The later pull shows 5.00 at P =
        # p * 0.5: PRE_SPLIT_CONFIRMED; r / k - 1 = 0.5 / 0.5 - 1 = 0.0 < 0.30: CA-3.
        res = classify(5.00, 10.00, S, [ev(S, 2, 1)], [(P, 5.00)], previous_session=P)
        self.check(res, "ARTIFACT_CONFIRMED", units="PRE_SPLIT_CONFIRMED")
        self.check_event(res, S, 0.5, 0.0)

    def test_event_with_a_bad_numerator_or_denominator_is_ignored(self):
        # With the 1-for-10 counted this is ARTIFACT_PROBABLE (ElevenClasses). With the event ignored E is empty
        # and r = 9.84 >= 4: CA-6.
        bad = [ev(S, 0, 10), ev(S, -1, 10), ev(S, 1, 0), ev(S, 1, -10), ev(S, -1, -10),
               {"effective_session": S, "denominator": 10}, {"effective_session": S, "numerator": 1},
               {"effective_session": S, "numerator": None, "denominator": 10},
               {"effective_session": S, "numerator": 1, "denominator": None}]
        for e in bad:
            with self.subTest(event=e):
                res = classify(9.84, 1.00, S, [e], [(P, 1.00)], previous_session=P)
                self.check(res, "UNEXPLAINED_EXTREME_MOVE", units="UNCHANGED")
                self.check_no_event(res)


# ==================================================================================================================
# Part A, addendum 1: re-basing by a later split
# ==================================================================================================================

class LaterSplits(Base):
    """Signal 2026-10-20: 1.56 / 1.20 = 1.3. A 1-for-10 on 2026-11-02 re-based the history of a later pull: the
    close of 2026-10-19 reads 12.00 = 1.20 * 10. E takes 2026-10-11 .. 2026-10-20, so that split is not in E."""

    LATER = [ev("2026-11-02", 1, 10)]
    BARS = [("2026-10-16", 11.50), (P20, 12.00)]

    def test_case_a_matches_the_rebased_previous_close(self):
        # F = 10 and |ln 10| > ln 1.05. 12.00 against p = 1.20 fails; against p * F = 12.00 it matches: UNCHANGED.
        # Nothing else changes: r = 1.3 < 4, gap 1 day, E empty: CA-9. The factor is recorded.
        for retrieved_on in ("2026-11-05", None):
            with self.subTest(retrieved_on=retrieved_on):
                res = classify(1.56, 1.20, S20, self.LATER, self.BARS, previous_session=P20,
                               retrieved_on=retrieved_on)
                self.check(res, "NO_ACTION_FOUND", previous_session=P20, previous_session_source="recorded",
                           units="UNCHANGED")
                self.assertAlmostEqual(res["later_factor"], 10.0)
                self.check_no_event(res)

    def test_split_after_the_pull_does_not_count(self):
        # A pull retrieved on 2026-10-30 cannot have been re-based by a split of 2026-11-02: F is the empty
        # product, 12.00 matches nothing, and no event is in E: INCONSISTENT.
        res = classify(1.56, 1.20, S20, self.LATER, self.BARS, previous_session=P20, retrieved_on="2026-10-30")
        self.check(res, "UNITS_INCONSISTENT", units="INCONSISTENT", later_factor=None)

    def test_retrieved_on_bound_is_inclusive(self):
        # effective session <= the UTC date of the pull.
        on = classify(1.56, 1.20, S20, self.LATER, self.BARS, previous_session=P20, retrieved_on="2026-11-02")
        self.check(on, "NO_ACTION_FOUND", units="UNCHANGED")
        self.assertAlmostEqual(on["later_factor"], 10.0)
        before = classify(1.56, 1.20, S20, self.LATER, self.BARS, previous_session=P20, retrieved_on="2026-11-01")
        self.check(before, "UNITS_INCONSISTENT", later_factor=None)

    def test_case_b_matches_the_rebased_previous_close(self):
        # No bar within 1% of 1.20. Within 1% of p * F = 12.00: 2026-10-19 (11.50 is 4% away). Still "matched".
        res = classify(1.56, 1.20, S20, self.LATER, self.BARS, retrieved_on="2026-11-05")
        self.check(res, "NO_ACTION_FOUND", previous_session=P20, previous_session_source="matched",
                   units="UNCHANGED")
        self.assertAlmostEqual(res["later_factor"], 10.0)

    def test_match_as_written_records_no_factor(self):
        # The comparison as written is tried first. Case A: the bar at P equals p.
        res = classify(1.56, 1.20, S20, self.LATER, [(P20, 1.20)], previous_session=P20, retrieved_on="2026-11-05")
        self.check(res, "NO_ACTION_FOUND", units="UNCHANGED", later_factor=None)
        # Case B: "Xu is the latest reference session matching p; if there is none, the latest matching p * F".
        # 2026-10-16 matches p, so it is taken although the later bar of 2026-10-19 matches p * F.
        res = classify(1.56, 1.20, S20, self.LATER, [("2026-10-16", 1.20), (P20, 12.00)], retrieved_on="2026-11-05")
        self.check(res, "NO_ACTION_FOUND", previous_session="2026-10-16", previous_session_source="matched",
                   units="UNCHANGED", later_factor=None)

    def test_pre_split_confirmed_through_a_later_factor(self):
        # Recorded 5.10 / 0.50 (r = 10.2). 1-for-10 on the signal session (in E), then 1-for-4 on 2026-11-02 (F = 4).
        # The pull shows 20.00 on 2026-10-19: not 0.50, not 0.50 * 4 = 2.00, not 0.50 * 10 = 5.00, but
        # 0.50 * 10 * 4 = 20.00. PRE_SPLIT_CONFIRMED by the event of the signal session. The later split does not
        # alter the recorded pair: r / k - 1 = 10.2 / 10 - 1 = 0.02 < 0.30, CA-3.
        events = [ev(S20, 1, 10), ev("2026-11-02", 1, 4)]
        bars = [(P20, 20.00)]
        a = classify(5.10, 0.50, S20, events, bars, previous_session=P20, retrieved_on="2026-11-05")
        self.check(a, "ARTIFACT_CONFIRMED", previous_session=P20, previous_session_source="recorded",
                   units="PRE_SPLIT_CONFIRMED")
        self.check_event(a, S20, 10, 0.02)
        self.assertAlmostEqual(a["later_factor"], 4.0)
        b = classify(5.10, 0.50, S20, events, bars, retrieved_on="2026-11-05")
        self.check(b, "ARTIFACT_CONFIRMED", previous_session=P20, previous_session_source="rebased_match",
                   units="PRE_SPLIT_CONFIRMED")
        self.check_event(b, S20, 10, 0.02)
        self.assertAlmostEqual(b["later_factor"], 4.0)
        # Retrieved before the later split: 20.00 matches neither 0.50 nor 5.00.
        c = classify(5.10, 0.50, S20, events, bars, previous_session=P20, retrieved_on="2026-10-30")
        self.check(c, "UNITS_INCONSISTENT", later_factor=None)

    def test_later_factor_is_the_product_of_the_later_splits(self):
        # 1-for-2 on 2026-10-27 and 1-for-5 on 2026-11-03: F = 10 for a pull of 2026-11-05, F = 2 for a pull of
        # 2026-10-30 (1.20 * 2 = 2.40 does not match 12.00).
        events = [ev("2026-10-27", 1, 2), ev("2026-11-03", 1, 5)]
        both = classify(1.56, 1.20, S20, events, [(P20, 12.00)], previous_session=P20, retrieved_on="2026-11-05")
        self.check(both, "NO_ACTION_FOUND", units="UNCHANGED")
        self.assertAlmostEqual(both["later_factor"], 10.0)
        first = classify(1.56, 1.20, S20, events, [(P20, 12.00)], previous_session=P20, retrieved_on="2026-10-30")
        self.check(first, "UNITS_INCONSISTENT", later_factor=None)

    def test_later_forward_split(self):
        # 2-for-1 on 2026-11-02: F = 0.5, |ln 0.5| > ln 1.05. The pull shows 0.60 = 1.20 * 0.5.
        res = classify(1.56, 1.20, S20, [ev("2026-11-02", 2, 1)], [(P20, 0.60)], previous_session=P20,
                       retrieved_on="2026-11-05")
        self.check(res, "NO_ACTION_FOUND", units="UNCHANGED")
        self.assertAlmostEqual(res["later_factor"], 0.5)

    def test_later_factor_too_close_to_one_is_not_tried(self):
        # F = 1.04: |ln F| = 0.0392 is not > ln 1.05 = 0.0488, so p * F is never tried. 1.248 = 1.20 * 1.04 is 4%
        # from p: INCONSISTENT.
        res = classify(1.56, 1.20, S20, [ev("2026-11-02", 1, 1.04)], [(P20, 1.248)], previous_session=P20,
                       retrieved_on="2026-11-05")
        self.check(res, "UNITS_INCONSISTENT", units="INCONSISTENT", later_factor=None)

    def test_rebased_comparison_keeps_the_tolerance_of_the_comparison(self):
        # 12.30 against p * F = 12.00: |ln 1.025| = 0.0247. That is inside 3% but outside the 1% of the unchanged
        # comparison, and no event is in E: INCONSISTENT.
        res = classify(1.56, 1.20, S20, self.LATER, [(P20, 12.30)], previous_session=P20, retrieved_on="2026-11-05")
        self.check(res, "UNITS_INCONSISTENT", units="INCONSISTENT", later_factor=None)


# ==================================================================================================================
# Part B1: the returned dict, bad input, payload_bars
# ==================================================================================================================

class ClassifyShape(Base):
    def test_exact_keys(self):
        calls = [
            classify(1.50, 1.00, S, [], [(P, 1.00)]),
            classify(9.84, 1.00, S, [ev(S)], [(P, 10.00)], previous_session=P),
            # every argument positional, in the order of the contract's signature
            split_units.classify(9.84, 1.00, S, [ev(S)], [(P, 10.00)], P, "2026-11-12"),
            classify(6.30, 2.00, S, [ev(S, 1, 3)], []),
            classify(1.50, 1.00, S, [], [(P, 1.20)]),
            classify(None, 1.00, S, [], []),
            classify(1.56, 1.20, S20, [ev("2026-11-02", 1, 10)], [(P20, 12.00)], previous_session=P20),
        ]
        for res in calls:
            self.assertIsInstance(res, dict)
            self.assertEqual(set(res), CLASSIFY_KEYS)
            self.assertIn(res["class"], GROUP_OF)
            self.assertEqual(res["group"], GROUP_OF[res["class"]])
            self.assertIn(res["units"], UNITS)

    def test_never_raises_on_bad_input(self):
        good = dict(close=9.84, previous=1.00, signal_session=S, events=[ev(S)], bars=[(P, 10.00)],
                    previous_session=None, retrieved_on=None)
        nan = float("nan")
        bad = [
            dict(events=None), dict(bars=None), dict(events="oops"), dict(bars="oops"), dict(events=7), dict(bars=7),
            dict(events=[None, "x", 7, {}, {"effective_session": None, "numerator": 1, "denominator": 10},
                         {"effective_session": "soon", "numerator": 1, "denominator": 10},
                         {"effective_session": S, "numerator": "one", "denominator": 10},
                         {"effective_session": S, "numerator": nan, "denominator": 10}]),
            dict(bars=[None, (), (P,), ("yesterday", 1.0), (P, "abc"), (P, nan), (None, 1.0), 7]),
            dict(previous_session="yesterday"), dict(previous_session=20261109), dict(previous_session=""),
            dict(retrieved_on="later"), dict(retrieved_on=20261112),
            dict(close="abc", previous=[], signal_session=20261110),
            dict(close=None, previous=None, signal_session=None, events=None, bars=None),
        ]
        for change in bad:
            with self.subTest(change=change):
                res = split_units.classify(**dict(good, **change))
                self.assertEqual(set(res), CLASSIFY_KEYS)
                self.assertIn(res["class"], GROUP_OF)
                self.assertEqual(res["group"], GROUP_OF[res["class"]])
                self.assertIn(res["units"], UNITS)

    def test_empty_pull_counts_as_a_consulted_source(self):
        # CONTRACT_QUESTIONS.md, question 2. The classifier is given the events of a pull, so a source was
        # consulted even when the pull lists no split and no bar. Case C: units UNKNOWN, P unknown.
        # CONTRACT_ADDENDUM_1.md states this reading of CONTRACT.md ("falls through to NO_ACTION_FOUND") and leaves
        # classify unchanged; the correction for a response without bars sits in assessment_record.
        small = classify(1.50, 1.00, S, [], [])
        self.check(small, "NO_ACTION_FOUND", previous_session=None, previous_session_source=None, units="UNKNOWN")
        extreme = classify(9.84, 1.00, S, [], [])
        self.check(extreme, "UNEXPLAINED_EXTREME_MOVE", previous_session=None, units="UNKNOWN")


class PayloadBars(unittest.TestCase):
    def test_pairs_of_session_and_close(self):
        p = payload(bars=[("2026-11-06", 1.07), (P, 1.00), (S, 9.84)], splits=[(S, 1, 10)])
        self.assertEqual([tuple(b) for b in split_units.payload_bars(p)],
                         [("2026-11-06", 1.07), (P, 1.00), (S, 9.84)])

    def test_new_york_date_not_utc_date(self):
        # 2026-10-21 03:30 UTC is 2026-10-20 23:30 in New York (EDT, UTC-4).
        # 2026-11-07 02:00 UTC is 2026-11-06 21:00 (EST, UTC-5). 2026-11-10 04:59 UTC is 2026-11-09 23:59.
        # 2026-11-10 05:00 UTC is midnight of 2026-11-10 in New York.
        raw = {"chart": {"result": [{
            "timestamp": [ts(2026, 10, 21, 3, 30), ts(2026, 11, 7, 2, 0), ts(2026, 11, 10, 4, 59),
                          ts(2026, 11, 10, 5, 0)],
            "indicators": {"quote": [{"close": [1.11, 1.07, 1.00, 9.84]}]}}]}}
        self.assertEqual([tuple(b) for b in split_units.payload_bars(raw)],
                         [("2026-10-20", 1.11), ("2026-11-06", 1.07), ("2026-11-09", 1.00), ("2026-11-10", 9.84)])

    def test_malformed_payloads(self):
        stamps = [unix(P)]
        closes = {"quote": [{"close": [1.0]}]}
        for bad in (None, {}, "oops", 7, [], {"chart": None}, {"chart": {"result": None}}, {"chart": {"result": []}},
                    {"chart": {"result": [{}]}},
                    {"chart": {"result": [{"timestamp": stamps}]}},
                    {"chart": {"result": [{"timestamp": stamps, "indicators": None}]}},
                    {"chart": {"result": [{"timestamp": stamps, "indicators": {"quote": []}}]}},
                    {"chart": {"result": [{"timestamp": stamps, "indicators": {"quote": [{}]}}]}},
                    {"chart": {"result": [{"timestamp": stamps, "indicators": {"quote": [{"close": None}]}}]}},
                    {"chart": {"result": [{"timestamp": None, "indicators": closes}]}},
                    {"chart": {"result": [{"indicators": closes}]}},
                    {"chart": {"result": [{"timestamp": ["yesterday"], "indicators": closes}]}},
                    {"chart": {"result": None, "error": {"code": "Not Found"}}},
                    {"finance": {"error": "Too Many Requests"}}):
            with self.subTest(payload=bad):
                self.assertEqual(split_units.payload_bars(bad), [])

    def test_a_session_without_a_price_is_not_a_reference_bar(self):
        # The provider leaves None for a session without a trade. Whether payload_bars keeps or drops that entry,
        # the priced sessions are intact and the classifier finds no reference bar on 2026-11-09.
        bars = split_units.payload_bars(payload(bars=[("2026-11-06", 1.07), (P, None), (S, 9.84)]))
        self.assertEqual({s: c for s, c in bars if c is not None}, {"2026-11-06": 1.07, S: 9.84})
        res = classify(9.84, 1.07, S, [], bars, previous_session=P)
        self.assertEqual((res["previous_session"], res["units"]), (P, "UNKNOWN"))


# ==================================================================================================================
# Part B2: assessment_record
# ==================================================================================================================

def rspl_pull(*split):
    """A later pull of RSPL (set_rec()): 1-for-10 on the signal session, history re-based (1.00 * 10 = 10.00)."""
    return payload(bars=[("2026-11-06", 10.40), (P, 10.00), (S, 9.84)], splits=[split or (S, 1, 10)])


class AssessmentRecord(unittest.TestCase):
    def test_ledger_path(self):
        self.assertEqual(sa.LEDGER, paper.PAPER / "split_assessments.jsonl")

    def test_keys_and_values(self):
        # No seal assessment is given, so no previous session is passed: Case B. Nothing is within 1% of 0.25; for
        # the 1-for-24 of 2026-11-11 the latest bar before it within 3% of 0.25 * 24 = 6.00 is 2026-11-10 (6.00;
        # 6.48 is 8% away). 22.08 / 24 - 1 = -0.08 < 0.30: ARTIFACT_CONFIRMED. recorded_ret1 = 22.08 - 1 = 21.08.
        r = sa.assessment_record(govx(), govx_later_pull(), "pull us_2026-11-12", "2026-11-12T22:05:00Z")
        self.assertEqual(set(r), RECORD_KEYS)
        self.assertNotIn("prev_hash", r)
        self.assertNotIn("record_hash", r)
        self.assertEqual((r["type"], r["rule"]), ("SPLIT_ASSESSMENT", "SPLIT_UNITS_V1"))
        self.assertEqual((r["set_id"], r["ticker"], r["market"], r["signal_session"]),
                         ("US-GOVX-20261111", "GOVX", "US", "2026-11-11"))
        self.assertEqual(r["recorded_ret1"], 21.08)
        self.assertEqual((r["assessment"], r["group"]), ("ARTIFACT_CONFIRMED", "ARTIFACT"))
        self.assertEqual((r["split"], r["split_adjusted_ret1"]), ("2026-11-11 1:24", -0.08))
        self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"], r["later_factor"]),
                         ("2026-11-10", "rebased_match", "PRE_SPLIT_CONFIRMED", None))
        self.assertEqual((r["pull_role"], r["supersedes"], r["sources"]), ("later", None, []))
        self.assertEqual((r["basis"], r["assessed_at"]), ("pull us_2026-11-12", "2026-11-12T22:05:00Z"))

    def test_recorded_ret1(self):
        # 9.84 / 1.00 - 1 = 8.84; 5.15 / 2.50 - 1 = 1.06; 2.70 / 0.60 - 1 = 3.5.
        self.assertEqual(sa.assessment_record(set_rec(), rspl_pull(), "b", "t")["recorded_ret1"], 8.84)
        self.assertEqual(sa.assessment_record(smx(), smx_own_pull(), "b", "t")["recorded_ret1"], 1.06)
        self.assertEqual(sa.assessment_record(vcig(), vcig_later_pull(), "b", "t")["recorded_ret1"], 3.5)

    def test_recorded_ret1_is_none_without_two_positive_closes(self):
        for signal in ({"close": 9.84}, {"previous": 1.0}, {}, {"close": 9.84, "previous": 0},
                       {"close": 9.84, "previous": None}, {"close": None, "previous": 1.0},
                       {"close": -9.84, "previous": 1.0}):
            with self.subTest(signal=signal):
                r = sa.assessment_record(dict(set_rec(), signal=signal), rspl_pull(), "b", "t")
                self.assertEqual(set(r), RECORD_KEYS)
                self.assertIsNone(r["recorded_ret1"])
                self.assertEqual((r["assessment"], r["group"]), ("NOT_ASSESSABLE", "UNRESOLVED"))

    def test_no_payload_is_not_assessable(self):
        r = sa.assessment_record(set_rec(), None, "b", "t")
        self.assertEqual(set(r), RECORD_KEYS)
        self.assertEqual((r["assessment"], r["group"]), ("NOT_ASSESSABLE", "UNRESOLVED"))
        self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]), (None, None, "UNKNOWN"))
        self.assertEqual((r["split"], r["split_adjusted_ret1"], r["later_factor"]), ("", None, None))
        self.assertEqual(r["recorded_ret1"], 8.84)  # the recorded move does not depend on the payload

    # A payload that holds no bar with a price: see ResponseWithoutAPricedBar (CONTRACT_ADDENDUM_1.md).

    def test_split_is_empty_when_no_event_is_used(self):
        # SMX from the scan's own pull is REAL_MOVE_AFTER_SPLIT (ContractCases.test_case_1). The split in the
        # window is not "the event used" by CA-3 or CA-4: split is "" and there is no adjusted move.
        r = sa.assessment_record(smx(), smx_own_pull(), "b", "t")
        self.assertEqual(r["assessment"], "REAL_MOVE_AFTER_SPLIT")
        self.assertEqual((r["split"], r["split_adjusted_ret1"]), ("", None))

    def test_split_format(self):
        # RSPL from rspl_pull(): Case B re-based match on 2026-11-09, 9.84 / 10 - 1 = -0.016, ARTIFACT_CONFIRMED.
        cases = {
            "provider string": ((S, 1, 10), "2026-11-10 1:10"),
            # The provider's own string is used as given, not rebuilt from numerator and denominator.
            "provider string verbatim": ((S, 5, 50, "1:10"), "2026-11-10 1:10"),
            # No provider string: the V11 form, numerator:denominator.
            "no provider string": ((S, 1, 10, None), "2026-11-10 1:10"),
        }
        for name, (split, expected) in cases.items():
            with self.subTest(name):
                r = sa.assessment_record(set_rec(), rspl_pull(*split), "b", "t")
                self.assertEqual(r["assessment"], "ARTIFACT_CONFIRMED")
                self.assertEqual((r["split"], r["split_adjusted_ret1"]), (expected, -0.016))

    def test_seal_previous_session_goes_to_the_classifier(self):
        # With the seal assessment's previous session the classifier runs Case A on that session.
        r = sa.assessment_record(govx(), govx_later_pull(), "b", "t", seal=govx_seal())
        self.assertEqual((r["assessment"], r["previous_session"], r["previous_session_source"]),
                         ("ARTIFACT_CONFIRMED", "2026-11-10", "recorded"))
        # Had the seal recorded 2026-11-09, Case A would look at that bar alone: 6.48 against 0.25 * 24 = 6.00 is
        # |ln 1.08| = 0.077 > ln 1.03, and 6.48 is not 0.25 either: INCONSISTENT. (Case B would find 2026-11-10.)
        other = dict(govx_seal(), previous_session="2026-11-09")
        r = sa.assessment_record(govx(), govx_later_pull(), "b", "t", seal=other)
        self.assertEqual((r["assessment"], r["previous_session"], r["previous_session_source"], r["units"]),
                         ("UNITS_INCONSISTENT", "2026-11-09", "recorded", "INCONSISTENT"))

    def test_seal_is_used_only_when_it_is_a_seal_record_with_a_previous_session(self):
        # A first record with pull_role "later", or a seal record without a previous session, passes nothing:
        # Case B, which finds 2026-11-10 by its re-based close.
        not_a_seal = dict(govx_seal(), pull_role="later", previous_session="2026-11-09")
        no_session = dict(govx_seal(), previous_session=None, previous_session_source=None, units="UNKNOWN")
        for seal in (not_a_seal, no_session, None):
            with self.subTest(seal=seal):
                r = sa.assessment_record(govx(), govx_later_pull(), "b", "t", seal=seal)
                self.assertEqual((r["assessment"], r["previous_session"], r["previous_session_source"]),
                                 ("ARTIFACT_CONFIRMED", "2026-11-10", "rebased_match"))

    def test_supersedes_is_the_hash_of_the_prior_record(self):
        prior = dict(govx_seal(), prev_hash="0" * 64, record_hash="9f" * 32)
        r = sa.assessment_record(govx(), govx_later_pull(), "b", "t", prior=prior, seal=prior)
        self.assertEqual(r["supersedes"], "9f" * 32)
        self.assertEqual(set(r), RECORD_KEYS)
        self.assertIsNone(sa.assessment_record(govx(), govx_later_pull(), "b", "t")["supersedes"])

    def test_pull_role_and_sources(self):
        r = sa.assessment_record(govx(), govx_own_pull(), "b", "t", pull_role="seal",
                                 sources=("issuer notice of the 1-for-24 reverse split", "exchange daily list"))
        self.assertEqual(r["pull_role"], "seal")
        self.assertEqual(r["sources"], ["issuer notice of the 1-for-24 reverse split", "exchange daily list"])
        self.assertIsInstance(r["sources"], list)
        default = sa.assessment_record(govx(), govx_own_pull(), "b", "t")
        self.assertEqual((default["pull_role"], default["sources"]), ("later", []))

    def test_retrieved_on_bounds_the_later_splits(self):
        # LaterSplits through the record: signal 2026-10-20, 1.56 / 1.20, a 1-for-10 on 2026-11-02 that re-based
        # the pull (2026-10-19 reads 12.00). recorded_ret1 = 1.3 - 1 = 0.3.
        spec = set_rec("US-XONE-20261020", "XONE", 1.56, 1.20, S20)
        pull = payload(bars=[("2026-10-16", 11.50), (P20, 12.00), (S20, 15.60), ("2026-11-02", 14.10),
                             ("2026-11-03", 13.80)], splits=[("2026-11-02", 1, 10)])
        after = sa.assessment_record(spec, pull, "b", "t", retrieved_on="2026-11-05")
        self.assertEqual((after["assessment"], after["group"]), ("NO_ACTION_FOUND", "REAL"))
        self.assertEqual((after["previous_session"], after["previous_session_source"], after["units"]),
                         (P20, "matched", "UNCHANGED"))
        self.assertAlmostEqual(after["later_factor"], 10.0)
        self.assertEqual((after["recorded_ret1"], after["split"]), (0.3, ""))
        before = sa.assessment_record(spec, pull, "b", "t", retrieved_on="2026-10-30")
        self.assertEqual((before["assessment"], before["group"], before["later_factor"]),
                         ("UNITS_INCONSISTENT", "UNRESOLVED", None))


# ==================================================================================================================
# Part B2: readers of the record list
# ==================================================================================================================

class Readers(unittest.TestCase):
    def test_latest_is_the_last_assessment_of_each_set_in_ledger_order(self):
        g1, g2, s1 = govx_seal(), govx_confirmed("ab" * 32), smx_real()
        foreign = {"type": "SPLIT_FLAG", "set_id": govx()["set_id"], "flag": "INDETERMINATE"}
        out = sa.latest([g1, s1, g2, foreign])
        self.assertEqual(set(out), {govx()["set_id"], smx()["set_id"]})
        self.assertEqual(out[govx()["set_id"]], g2)
        self.assertEqual(out[smx()["set_id"]], s1)
        self.assertEqual(sa.latest([]), {})

    def test_seal_assessments_are_first_records_with_the_seal_role(self):
        g1, g2 = govx_seal(), govx_confirmed("ab" * 32)
        s1 = smx_real()  # first record of SMX, made from a later pull
        s2 = dict(smx_real("2026-11-13T10:00:00Z"), assessment="STALE_PREVIOUS", group="UNRESOLVED")
        out = sa.seal_assessments([g1, s1, g2, s2])
        self.assertEqual(set(out), {govx()["set_id"]})
        self.assertEqual(out[govx()["set_id"]], g1)

    def test_pending_is_sealed_us_sets_without_an_assessment_in_spec_order(self):
        a, b, c = set_rec("US-A"), set_rec("US-B"), set_rec("US-C")
        idx = dict(set_rec("IDX-1"), market="IDX")
        crypto = dict(set_rec("CR-1"), market="CRYPTO")
        resolution = {"type": "RESOLUTION", "set_id": "US-R", "market": "US"}
        records = [
            arec(b, "NO_ACTION_FOUND", "2026-11-10T22:10:05Z"),
            # A record of another type about US-A is not an assessment of US-A.
            {"type": "SPLIT_FLAG", "rule": "SPLIT_ARTIFACT_V11", "set_id": "US-A", "flag": "NOT_FLAGGED"},
        ]
        out = sa.pending([c, idx, a, crypto, resolution, b], records)
        self.assertEqual([s["set_id"] for s in out], ["US-C", "US-A"])
        self.assertEqual([s["set_id"] for s in sa.pending([c, idx, a, crypto, resolution, b], [])],
                         ["US-C", "US-A", "US-B"])

    def test_changed_compares_assessment_split_previous_session_and_units(self):
        old = govx_seal()
        self.assertFalse(sa.changed(dict(old), old))
        for key, value in (("assessment", "NO_ACTION_FOUND"), ("split", "2026-11-11 1:24"),
                           ("previous_session", "2026-11-09"), ("previous_session", None), ("units", "UNKNOWN")):
            with self.subTest(key=key, value=value):
                self.assertTrue(sa.changed(dict(old, **{key: value}), old))
                self.assertTrue(sa.changed(old, dict(old, **{key: value})))

    def test_changed_ignores_every_other_field(self):
        old = dict(govx_seal(), prev_hash="0" * 64, record_hash="cd" * 32)
        new = dict(old, basis="pull us_2026-11-12", assessed_at="2026-11-12T22:05:00Z", pull_role="later",
                   supersedes="cd" * 32, sources=["exchange daily list"], previous_session_source="recorded",
                   later_factor=10.0, split_adjusted_ret1=-0.08, prev_hash="cd" * 32, record_hash="ef" * 32)
        self.assertFalse(sa.changed(new, old))


# ==================================================================================================================
# Part B2: propose_assessments and propose_reassessments
# ==================================================================================================================

class Propose(LedgerCase):
    def test_assessments_one_unsealed_record_per_pending_set(self):
        a = set_rec("US-A", "AAA", 1.50, 1.00, "2026-11-10")
        b = set_rec("US-B", "BBB", 1.50, 1.00, "2026-11-09")
        c = set_rec("US-C", "CCC", 1.50, 1.00, "2026-11-10")  # its ticker is not in the pull
        d = set_rec("US-D", "DDD", 1.50, 1.00, "2026-11-10")  # its payload is None
        idx = dict(set_rec("IDX-1", "BBCA"), market="IDX")
        payloads = {
            # AAA: the bar of 2026-11-09 equals p, r = 1.5, no split: NO_ACTION_FOUND.
            "AAA": payload(bars=[("2026-11-09", 1.00), ("2026-11-10", 1.50)]),
            # BBB: signal Monday 2026-11-09, previous bar Friday 2026-11-06 (3 days): NO_ACTION_FOUND.
            "BBB": payload(bars=[("2026-11-06", 1.00), ("2026-11-09", 1.50)]),
            "DDD": None,
            "BBCA": payload(bars=[("2026-11-09", 1.00)]),
        }
        out = sa.propose_assessments([a, idx, b, c, d], [], payloads, "pull us_2026-11-10", "2026-11-10T22:10:05Z",
                                     seal_session="2026-11-10")
        self.assertEqual(len(out), 4)
        by = {r["set_id"]: r for r in out}
        self.assertEqual(set(by), {"US-A", "US-B", "US-C", "US-D"})
        for r in out:
            self.assertEqual(set(r), RECORD_KEYS)
            self.assertIsNone(r["supersedes"])
            self.assertEqual((r["basis"], r["assessed_at"]), ("pull us_2026-11-10", "2026-11-10T22:10:05Z"))
        self.assertEqual({sid: r["assessment"] for sid, r in by.items()},
                         {"US-A": "NO_ACTION_FOUND", "US-B": "NO_ACTION_FOUND", "US-C": "NOT_ASSESSABLE",
                          "US-D": "NOT_ASSESSABLE"})
        # "seal" for the sets whose signal session is the session of the pull, "later" for the others.
        self.assertEqual({sid: r["pull_role"] for sid, r in by.items()},
                         {"US-A": "seal", "US-B": "later", "US-C": "seal", "US-D": "seal"})
        self.assertEqual((by["US-A"]["previous_session"], by["US-A"]["previous_session_source"]),
                         ("2026-11-09", "matched"))

    def test_assessments_skip_sets_that_have_a_record(self):
        a = set_rec("US-A", "AAA", 1.50, 1.00, "2026-11-10")
        b = set_rec("US-B", "BBB", 1.50, 1.00, "2026-11-09")
        payloads = {"AAA": payload(bars=[("2026-11-09", 1.00), ("2026-11-10", 1.50)]),
                    "BBB": payload(bars=[("2026-11-06", 1.00), ("2026-11-09", 1.50)])}
        records = self.write(arec(b, "NOT_ASSESSABLE", "2026-11-09T22:10:05Z", pull_role="seal"))
        out = sa.propose_assessments([a, b], records, payloads, "pull us_2026-11-10", "2026-11-10T22:10:05Z")
        self.assertEqual([r["set_id"] for r in out], ["US-A"])
        self.assertEqual(out[0]["pull_role"], "later")  # no seal_session given
        self.assertEqual(sa.propose_assessments([b], records, payloads, "b", "t", seal_session="2026-11-09"), [])

    def test_assessments_pass_retrieved_on_to_the_classifier(self):
        # See AssessmentRecord.test_retrieved_on_bounds_the_later_splits.
        spec = set_rec("US-XONE-20261020", "XONE", 1.56, 1.20, S20)
        pull = {"XONE": payload(bars=[("2026-10-16", 11.50), (P20, 12.00), (S20, 15.60), ("2026-11-02", 14.10)],
                                splits=[("2026-11-02", 1, 10)])}
        after = sa.propose_assessments([spec], [], pull, "b", "t", retrieved_on="2026-11-05")
        self.assertEqual([r["assessment"] for r in after], ["NO_ACTION_FOUND"])
        before = sa.propose_assessments([spec], [], pull, "b", "t", retrieved_on="2026-10-30")
        self.assertEqual([r["assessment"] for r in before], ["UNITS_INCONSISTENT"])

    def test_reassessments_return_changed_records_only(self):
        specs = [smx(), govx()]
        records = self.write(smx_real("2026-11-10T22:10:05Z", pull_role="seal"), govx_seal())
        payloads = {"SMX": smx_later_pull(), "GOVX": govx_later_pull()}
        out = sa.propose_reassessments(specs, records, payloads, "pull us_2026-11-12", "2026-11-12T22:05:00Z",
                                       retrieved_on="2026-11-12")
        # SMX is REAL_MOVE_AFTER_SPLIT again, with the same previous session, units and split: no record.
        # GOVX turns from UNEXPLAINED_EXTREME_MOVE into ARTIFACT_CONFIRMED.
        self.assertEqual([r["set_id"] for r in out], [govx()["set_id"]])
        r = out[0]
        self.assertEqual(set(r), RECORD_KEYS)
        self.assertEqual((r["assessment"], r["group"], r["split"], r["split_adjusted_ret1"]),
                         ("ARTIFACT_CONFIRMED", "ARTIFACT", "2026-11-11 1:24", -0.08))
        self.assertEqual((r["pull_role"], r["supersedes"]), ("later", last_hash(records, govx()["set_id"])))
        # The seal assessment's previous session was passed: Case A.
        self.assertEqual((r["previous_session"], r["previous_session_source"]), ("2026-11-10", "recorded"))
        self.assertEqual((r["basis"], r["assessed_at"]), ("pull us_2026-11-12", "2026-11-12T22:05:00Z"))

    def test_reassessments_skip_a_set_whose_ticker_is_not_in_the_pull(self):
        records = self.write(govx_seal())
        for payloads in ({}, {"SMX": smx_later_pull()}):
            self.assertEqual(sa.propose_reassessments([govx()], records, payloads, "b", "2026-11-12T22:05:00Z"), [])

    def test_reassessments_skip_a_set_whose_payload_is_none(self):
        # CONTRACT_QUESTIONS.md, question 12: a None payload is "no payload", so the set keeps its assessment.
        # (A payload that is there but holds no bar is different: ResponseWithoutAPricedBar.)
        records = self.write(govx_seal())
        self.assertEqual(sa.propose_reassessments([govx()], records, {"GOVX": None}, "b", "2026-11-12T22:05:00Z"), [])

    def test_reassessments_leave_pending_sets_to_propose_assessments(self):
        records = self.write(govx_seal())
        payloads = {"SMX": smx_later_pull(), "GOVX": govx_later_pull()}
        out = sa.propose_reassessments([smx(), govx()], records, payloads, "b", "2026-11-12T22:05:00Z")
        self.assertEqual([r["set_id"] for r in out], [govx()["set_id"]])

    def test_reassessments_window(self):
        # Both sets were NOT_ASSESSABLE and both pulls now give NO_ACTION_FOUND. today - signal session:
        # 2026-11-12 - 2026-11-03 = 9 days, 2026-11-12 - 2026-11-02 = 10 days.
        one = set_rec("US-XONE-20261103", "XONE", 1.50, 1.00, "2026-11-03")
        two = set_rec("US-XTWO-20261102", "XTWO", 1.50, 1.00, "2026-11-02")
        records = self.write(arec(two, "NOT_ASSESSABLE", "2026-11-02T22:10:05Z", pull_role="seal"),
                             arec(one, "NOT_ASSESSABLE", "2026-11-03T22:10:05Z", pull_role="seal"))
        payloads = {"XONE": payload(bars=[("2026-11-02", 1.00), ("2026-11-03", 1.50)]),
                    "XTWO": payload(bars=[("2026-10-30", 1.00), ("2026-11-02", 1.50)])}

        def ids(**kw):
            out = sa.propose_reassessments([two, one], records, payloads, "b", "2026-11-12T22:05:00Z", **kw)
            return {r["set_id"] for r in out}

        self.assertEqual(ids(), {one["set_id"], two["set_id"]})
        self.assertEqual(ids(window_days=9, today="2026-11-12"), {one["set_id"]})  # at most 9 days: 10 is out
        self.assertEqual(ids(window_days=10, today="2026-11-12"), {one["set_id"], two["set_id"]})
        self.assertEqual(ids(window_days=8, today="2026-11-12"), set())

    def test_reassessments_sources(self):
        records = self.write(govx_seal(), arec(xtri(), "NOT_ASSESSABLE", "2026-11-03T22:10:05Z", pull_role="seal"))
        payloads = {"GOVX": govx_later_pull(),
                    # XTRI: bars from the signal session only, 1-for-3 on it: SPLIT_IN_WINDOW_UNRESOLVED.
                    "XTRI": payload(bars=[("2026-11-03", 6.30), ("2026-11-04", 6.10)], splits=[("2026-11-03", 1, 3)])}
        note = ["issuer notice of the 1-for-24 reverse split, 2026-11-10"]
        out = sa.propose_reassessments([govx(), xtri()], records, payloads, "b", "2026-11-12T22:05:00Z",
                                       sources={govx()["set_id"]: note})
        by = {r["set_id"]: r for r in out}
        self.assertEqual(set(by), {govx()["set_id"], xtri()["set_id"]})
        self.assertEqual(by[govx()["set_id"]]["sources"], note)
        self.assertEqual(by[xtri()["set_id"]]["sources"], [])

    def test_reassessment_supersedes_the_latest_record_of_a_chain(self):
        spec, sid = xtri(), xtri()["set_id"]
        # Night 1, the scan's own pull has no payload for the ticker: NOT_ASSESSABLE, role "seal".
        n1 = sa.propose_assessments([spec], [], {}, "pull us_2026-11-03", "2026-11-03T22:10:05Z",
                                    seal_session="2026-11-03")
        self.assertEqual([(r["assessment"], r["pull_role"]) for r in n1], [("NOT_ASSESSABLE", "seal")])
        records = self.write(*n1)
        # Night 2: bars from the signal session only (no reference bar) and a 1-for-3 on it. The seal record has no
        # previous session, so Case C: the split explains 3.15 (3.15 / 3 - 1 = 0.05), straddle UNKNOWN, r < 4.
        pull2 = {"XTRI": payload(bars=[("2026-11-03", 6.30), ("2026-11-04", 6.10)], splits=[("2026-11-03", 1, 3)])}
        n2 = sa.propose_reassessments([spec], records, pull2, "pull us_2026-11-04", "2026-11-04T22:10:05Z")
        self.assertEqual([(r["assessment"], r["split"], r["split_adjusted_ret1"]) for r in n2],
                         [("SPLIT_IN_WINDOW_UNRESOLVED", "2026-11-03 1:3", 0.05)])
        self.assertEqual(n2[0]["supersedes"], records[0]["record_hash"])
        records = self.write(*n2)
        # Night 3: the history is there and re-based. Case B: nothing within 1% of 2.00; the latest bar before the
        # split within 3% of 2.00 * 3 = 6.00 is 2026-11-02 (6.00). ARTIFACT_CONFIRMED.
        pull3 = {"XTRI": payload(bars=[("2026-10-30", 6.15), ("2026-11-02", 6.00), ("2026-11-03", 6.30),
                                       ("2026-11-04", 6.10), ("2026-11-05", 5.90)], splits=[("2026-11-03", 1, 3)])}
        n3 = sa.propose_reassessments([spec], records, pull3, "pull us_2026-11-05", "2026-11-05T22:10:05Z")
        self.assertEqual([(r["assessment"], r["previous_session"], r["previous_session_source"], r["units"])
                          for r in n3], [("ARTIFACT_CONFIRMED", "2026-11-02", "rebased_match", "PRE_SPLIT_CONFIRMED")])
        self.assertEqual(n3[0]["supersedes"], records[1]["record_hash"])  # the latest record, not the first
        records = self.write(*n3)
        self.assertEqual(len(records), 3)
        self.assertEqual(sa.verify(records=records, specs=[spec]), [])
        self.assertEqual(sa.verify(specs=[spec]), [])
        self.assertEqual(sa.latest(records)[sid]["record_hash"], records[2]["record_hash"])
        self.assertEqual(sa.seal_assessments(records)[sid]["record_hash"], records[0]["record_hash"])
        # The same pull again changes nothing.
        self.assertEqual(sa.propose_reassessments([spec], records, pull3, "b", "2026-11-06T22:10:05Z"), [])


# ==================================================================================================================
# Part B2: removed_set_ids and unresolved_set_ids
# ==================================================================================================================

T1 = "2026-11-11T22:10:00Z"  # the V11 hook on the night of the signal
T2 = "2026-11-11T22:10:05Z"  # the seal assessment, a few seconds later
T3 = "2026-11-12T03:00:00Z"  # still before the cutoff
CUT = "2026-11-12T14:30:00Z"  # GOVX's entry cutoff: the next open, 09:30 in New York
T4 = "2026-11-12T22:05:00Z"  # the night after


class RemovedSets(LedgerCase):
    def setUp(self):
        super().setUp()
        self.g = govx()
        self.sid = self.g["set_id"]

    def at_the_time(self, records, flags, cutoffs=None):
        cutoffs = {self.sid: CUT} if cutoffs is None else cutoffs
        return sa.removed_set_ids("at_the_time", records=records, v11_flags=flags, cutoffs=cutoffs)

    def real(self, at):
        return arec(self.g, "NO_ACTION_FOUND", at, previous_session="2026-11-10", source="matched", units="UNCHANGED")

    def probable(self, at):
        return arec(self.g, "ARTIFACT_PROBABLE", at, split="2026-11-11 1:24", adjusted=-0.08)

    def test_corrected_is_the_latest_assessment_with_group_artifact(self):
        x = xtri()
        records = [
            govx_seal(), smx_real(), govx_confirmed("ab" * 32),  # GOVX: unresolved, then a confirmed artifact
            arec(vcig(), "UNITS_INCONSISTENT", T4, units="INCONSISTENT"),
            arec(x, "ARTIFACT_PROBABLE", "2026-11-04T22:10:05Z", split="2026-11-03 1:3", adjusted=0.05),
            arec(tops(), "ARTIFACT_PROBABLE", T4, split="2026-11-06 1:10", adjusted=-0.016),
            # XTRI: probable artifact first, then found to be real: not removed.
            arec(x, "REAL_MOVE_AFTER_SPLIT", "2026-11-05T22:10:05Z", supersedes="cd" * 32,
                 previous_session="2026-11-03", source="matched", units="UNCHANGED"),
        ]
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[]),
                         {self.sid, tops()["set_id"]})
        self.assertEqual(sa.removed_set_ids("corrected", records, []), {self.sid, tops()["set_id"]})  # positional

    def test_corrected_uses_the_v11_flag_for_a_set_without_a_finding(self):
        # Changed for CONTRACT_ADDENDUM_2.md, point 2 (it was ..._only_for_a_set_without_an_assessment and expected
        # TOPS alone): the V11 tag also counts for a set whose standing assessment is NOT_ASSESSABLE, here XTRI.
        flags = [
            v11(tops(), "ARTIFACT_V11", "2026-11-09T22:10:00Z", "2026-11-06 1:10", -0.016),  # no assessment
            v11(smx(), "ARTIFACT_V11", "2026-11-10T22:10:00Z", "2026-11-09 1:2.8", -0.2643),  # assessed REAL
            v11(vcig(), "INDETERMINATE", "2026-11-02T22:10:00Z"),  # no assessment, not an artifact tag
            v11(xtri(), "ARTIFACT_V11", "2026-11-03T22:10:00Z", "2026-11-03 1:3", 0.05),  # only NOT_ASSESSABLE
        ]
        records = [smx_real(), arec(xtri(), "NOT_ASSESSABLE", "2026-11-12T10:06:00Z")]
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=flags),
                         {tops()["set_id"], xtri()["set_id"]})
        self.assertEqual(sa.removed_set_ids("corrected", records=[], v11_flags=flags),
                         {tops()["set_id"], smx()["set_id"], xtri()["set_id"]})

    def test_at_the_time_v11_tag_before_the_cutoff(self):
        self.assertEqual(self.at_the_time([], [v11(self.g, "ARTIFACT_V11", T1)]), {self.sid})
        for flag in ("INDETERMINATE", "NOT_FLAGGED", "NOT_ASSESSED"):
            with self.subTest(flag=flag):
                self.assertEqual(self.at_the_time([], [v11(self.g, flag, T1)]), set())

    def test_at_the_time_cutoff_is_strict(self):
        # Only records assessed strictly before the cutoff count.
        self.assertEqual(self.at_the_time([], [v11(self.g, "ARTIFACT_V11", "2026-11-12T14:29:59Z")]), {self.sid})
        self.assertEqual(self.at_the_time([], [v11(self.g, "ARTIFACT_V11", CUT)]), set())
        self.assertEqual(self.at_the_time([], [v11(self.g, "ARTIFACT_V11", T4)]), set())
        self.assertEqual(self.at_the_time([self.probable("2026-11-12T14:29:59Z")], []), {self.sid})
        self.assertEqual(self.at_the_time([self.probable(CUT)], []), set())
        self.assertEqual(self.at_the_time([self.probable(T4)], []), set())

    def test_at_the_time_ignores_what_was_learned_after_the_cutoff(self):
        # A correction found later is not a filter that was available before the trade.
        records = [govx_seal(T2), govx_confirmed("ab" * 32, T4)]
        self.assertEqual(self.at_the_time(records, [v11(self.g, "INDETERMINATE", T1)]), set())
        # And a tag that was there before the trade stays one, whatever is found later.
        self.assertEqual(self.at_the_time([self.real(T4)], [v11(self.g, "ARTIFACT_V11", T1)]), {self.sid})

    def test_at_the_time_latest_record_before_the_cutoff_decides(self):
        artifact, plain = v11(self.g, "ARTIFACT_V11", T1), v11(self.g, "NOT_FLAGGED", T1)
        # V11 tag at T1, then an assessment at T2, both before the cutoff: the assessment is the latest.
        self.assertEqual(self.at_the_time([self.real(T2)], [artifact]), set())
        self.assertEqual(self.at_the_time([self.probable(T2)], [plain]), {self.sid})
        # Two assessments before the cutoff: the later one.
        self.assertEqual(self.at_the_time([govx_seal(T2), govx_confirmed("ab" * 32, T3)], [plain]), {self.sid})
        self.assertEqual(self.at_the_time([self.probable(T2), self.real(T3)], [plain]), set())
        # An assessment at T2 and a V11 tag at T3: the V11 record is the latest by assessed_at.
        self.assertEqual(self.at_the_time([self.real(T2)], [v11(self.g, "ARTIFACT_V11", T3)]), {self.sid})

    def test_at_the_time_tie_goes_to_the_assessment(self):
        self.assertEqual(self.at_the_time([self.real(T1)], [v11(self.g, "ARTIFACT_V11", T1)]), set())
        self.assertEqual(self.at_the_time([self.probable(T1)], [v11(self.g, "NOT_FLAGGED", T1)]), {self.sid})

    def test_at_the_time_needs_a_cutoff(self):
        flags = [v11(self.g, "ARTIFACT_V11", T1)]
        records = [self.probable(T2)]
        self.assertEqual(self.at_the_time(records, flags, cutoffs={}), set())
        self.assertEqual(self.at_the_time(records, flags, cutoffs={smx()["set_id"]: CUT}), set())
        self.assertEqual(sa.removed_set_ids("at_the_time", records=records, v11_flags=flags), set())  # default None

    def test_at_the_time_each_set_has_its_own_cutoff(self):
        s = smx()
        flags = [v11(self.g, "ARTIFACT_V11", T1), v11(s, "ARTIFACT_V11", "2026-11-10T22:10:00Z")]
        # SMX's own cutoff is 2026-11-11T14:30:00Z; its tag of the evening before precedes it. If GOVX is given
        # that cutoff too, GOVX's tag (T1, the evening of 2026-11-11) is not before it and GOVX is not included.
        cutoffs = {self.sid: "2026-11-11T14:30:00Z", s["set_id"]: "2026-11-11T14:30:00Z"}
        self.assertEqual(sa.removed_set_ids("at_the_time", [], flags, cutoffs), {s["set_id"]})
        # With its own cutoff, the open of 2026-11-12, GOVX's tag precedes it.
        cutoffs[self.sid] = CUT
        self.assertEqual(sa.removed_set_ids("at_the_time", [], flags, cutoffs), {s["set_id"], self.sid})

    def test_unknown_view_raises(self):
        for view in ("as_frozen", "frozen", "CORRECTED", ""):
            with self.subTest(view=view):
                with self.assertRaises(ValueError):
                    sa.removed_set_ids(view, records=[], v11_flags=[], cutoffs={})

    def test_missing_ledgers_remove_nothing(self):
        self.assertEqual(sa.removed_set_ids("corrected"), set())
        self.assertEqual(sa.removed_set_ids("at_the_time", cutoffs={self.sid: CUT}), set())
        self.assertEqual(sa.unresolved_set_ids(), set())

    def test_defaults_read_the_two_ledgers_on_disk(self):
        records = self.write(govx_seal(T2), smx_real())
        records = self.write(govx_confirmed(records[0]["record_hash"], T4))
        self.write_flags(v11(tops(), "ARTIFACT_V11", "2026-11-09T22:10:00Z", "2026-11-06 1:10", -0.016),
                         v11(smx(), "ARTIFACT_V11", "2026-11-10T22:10:00Z", "2026-11-09 1:2.8", -0.2643),
                         v11(self.g, "INDETERMINATE", T1))
        # Corrected: GOVX by its latest assessment, TOPS by its V11 tag (no assessment); SMX was assessed REAL.
        self.assertEqual(sa.removed_set_ids("corrected"), {self.sid, tops()["set_id"]})
        # At the time: TOPS and SMX carried the V11 tag before their cutoffs; GOVX's artifact came after its own.
        cutoffs = {tops()["set_id"]: "2026-11-10T14:30:00Z", smx()["set_id"]: "2026-11-11T14:30:00Z", self.sid: CUT}
        self.assertEqual(sa.removed_set_ids("at_the_time", cutoffs=cutoffs), {tops()["set_id"], smx()["set_id"]})
        self.assertEqual(sa.unresolved_set_ids(), set())

    def test_unresolved_set_ids_is_the_latest_assessment_with_group_unresolved(self):
        records = [
            govx_seal(), smx_real(),
            arec(vcig(), "UNITS_INCONSISTENT", T4, units="INCONSISTENT"),
            arec(xtri(), "NOT_ASSESSABLE", "2026-11-03T22:10:05Z", pull_role="seal"),
            arec(tops(), "REAL_MOVE_UNITS_CONTAMINATED", T4, split="2026-11-06 1:10", adjusted=0.5),
        ]
        self.assertEqual(sa.unresolved_set_ids(records), {self.sid, vcig()["set_id"], xtri()["set_id"]})
        # GOVX is resolved by its second record; the others stay.
        records.append(govx_confirmed("ab" * 32))
        self.assertEqual(sa.unresolved_set_ids(records), {vcig()["set_id"], xtri()["set_id"]})
        self.assertEqual(sa.unresolved_set_ids([]), set())


# ==================================================================================================================
# Part B2: verify
# ==================================================================================================================

class Verify(LedgerCase):
    def setUp(self):
        super().setUp()
        self.specs = [govx(), smx(), xtri(), dict(set_rec("IDX-BBCA-20261111", "BBCA"), market="IDX"),
                      {"type": "RESOLUTION", "set_id": "US-R", "market": "US"}]

    def problems(self):
        """Problems from the lines read back, and from the ledger on disk (which also checks the hash chain)."""
        return sa.verify(records=paper.ledger_lines(self.path), specs=self.specs), sa.verify(specs=self.specs)

    def assert_sound(self):
        self.assertEqual(self.problems(), ([], []))

    def assert_problem(self):
        explicit, on_disk = self.problems()
        self.assertTrue(explicit)
        self.assertTrue(on_disk)

    def test_missing_ledger_is_sound(self):
        self.assertEqual(sa.verify(specs=self.specs), [])
        self.assertEqual(sa.verify(records=[], specs=self.specs), [])

    def test_sound_ledger_with_several_records_per_set(self):
        x = xtri()
        records = self.write(govx_seal(), arec(x, "NOT_ASSESSABLE", "2026-11-03T22:10:05Z", pull_role="seal"),
                             smx_real())
        g1, x1 = last_hash(records[:1], govx()["set_id"]), last_hash(records, x["set_id"])
        records = self.write(arec(x, "SPLIT_IN_WINDOW_UNRESOLVED", "2026-11-04T22:10:05Z", supersedes=x1,
                                  split="2026-11-03 1:3", adjusted=0.05))
        x2 = last_hash(records, x["set_id"])
        records = self.write(govx_confirmed(g1))
        records = self.write(arec(x, "ARTIFACT_CONFIRMED", "2026-11-05T22:10:05Z", supersedes=x2,
                                  split="2026-11-03 1:3", adjusted=0.05, previous_session="2026-11-02",
                                  source="rebased_match", units="PRE_SPLIT_CONFIRMED"))
        self.assertEqual(len(records), 6)
        self.assertEqual([r["set_id"] for r in records],
                         [govx()["set_id"], x["set_id"], smx()["set_id"], x["set_id"], govx()["set_id"], x["set_id"]])
        self.assert_sound()

    def test_problems_of_a_single_record(self):
        idx, resolution = self.specs[3], self.specs[4]
        cases = {
            "type is not SPLIT_ASSESSMENT": dict(govx_seal(), type="SPLIT_FLAG"),
            "rule is not SPLIT_UNITS_V1": dict(govx_seal(), rule="SPLIT_ARTIFACT_V11"),
            "pull_role is neither seal nor later": dict(govx_seal(), pull_role="nightly"),
            "pull_role missing": dict(govx_seal(), pull_role=None),
            "set of another market": arec(idx, "NO_ACTION_FOUND", T2),
            "US record that is not a sealed set": dict(govx_seal(), set_id=resolution["set_id"]),
            "first record that supersedes something": dict(govx_seal(), supersedes="ab" * 32),
        }
        for name, rec in cases.items():
            with self.subTest(name):
                self.path.unlink(missing_ok=True)
                self.write(rec)
                self.assert_problem()

    def test_the_same_single_record_is_sound_without_the_defect(self):
        self.write(govx_seal())
        self.assert_sound()

    def test_supersedes_must_be_the_hash_of_the_previous_record_of_the_set(self):
        def none(g1, s1):
            return [govx_confirmed(None)]

        def other_set(g1, s1):
            return [govx_confirmed(s1)]

        def skips_one(g1, s1):  # the third record names the first, not the second
            return [govx_confirmed(g1), "third"]

        for build in (none, other_set, skips_one):
            with self.subTest(build.__name__):
                self.path.unlink(missing_ok=True)
                records = self.write(govx_seal(), smx_real())
                g1, s1 = records[0]["record_hash"], records[1]["record_hash"]
                for rec in build(g1, s1):
                    if rec == "third":
                        rec = arec(govx(), "ARTIFACT_PROBABLE", "2026-11-13T22:05:00Z", supersedes=g1,
                                   split="2026-11-11 1:24", adjusted=-0.08, previous_session="2026-11-10",
                                   source="recorded", units="UNKNOWN")
                    self.write(rec)
                self.assert_problem()

    def test_seal_role_on_a_later_record_of_a_set_whose_first_record_is_later(self):
        records = self.write(smx_real())
        second = dict(smx_real("2026-11-13T10:06:00Z", pull_role="seal"), assessment="STALE_PREVIOUS",
                      group="UNRESOLVED", supersedes=records[0]["record_hash"])
        self.write(second)
        self.assert_problem()
        # The same second record with the role "later" is a legitimate reassessment.
        self.path.unlink(missing_ok=True)
        records = self.write(smx_real())
        self.write(dict(second, pull_role="later", supersedes=records[0]["record_hash"]))
        self.assert_sound()

    def test_tampered_line_fails_the_chain_check_of_the_ledger_on_disk(self):
        records = self.write(govx_seal())
        self.write(govx_confirmed(records[0]["record_hash"]))
        self.assert_sound()
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("pull us_2026-11-11", text)
        # The basis of the first record is rewritten in place. No rule about the records is broken (the second
        # still names the stored hash of the first); only the hash chain can tell.
        self.path.write_text(text.replace("pull us_2026-11-11", "pull us_2026-11-10"), encoding="utf-8")
        self.assertTrue(sa.verify(specs=self.specs))


# ==================================================================================================================
# CONTRACT_ADDENDUM_1.md: a response that holds no bar with a price is not evidence
# ==================================================================================================================

class ResponseWithoutAPricedBar(LedgerCase):
    """assessment_record gives NOT_ASSESSABLE when payload is None or payload_bars(payload) has no pair whose close
    is a number greater than zero: no previous session, units UNKNOWN, an empty split, no adjusted move and no later
    factor. The split events of such a response are not used. classify itself is unchanged."""

    def assert_not_assessable(self, r):
        self.assertEqual(set(r), RECORD_KEYS)
        self.assertEqual((r["assessment"], r["group"]), ("NOT_ASSESSABLE", "UNRESOLVED"))
        self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]), (None, None, "UNKNOWN"))
        self.assertEqual((r["split"], r["split_adjusted_ret1"], r["later_factor"]), ("", None, None))

    def test_metadata_and_an_empty_quote(self):
        # GNTA: r = 4.03 / 3.00 = 1.3433. Under CONTRACT.md alone this response was a consulted source that lists
        # no split, with no reference bar, and the set fell through to NO_ACTION_FOUND, group REAL.
        response = empty_response()
        self.assertEqual(split_units.payload_bars(response), [])
        r = sa.assessment_record(gnta(), response, "pull us_2026-11-12", "2026-11-12T10:06:00Z")
        self.assert_not_assessable(r)
        # The recorded move and the bookkeeping fields are those of any other record.
        self.assertEqual(r["recorded_ret1"], 0.3433)
        self.assertEqual((r["set_id"], r["ticker"], r["signal_session"]), ("US-GNTA-20261102", "GNTA", "2026-11-02"))
        self.assertEqual((r["pull_role"], r["supersedes"], r["sources"]), ("later", None, []))
        self.assertEqual((r["basis"], r["assessed_at"]), ("pull us_2026-11-12", "2026-11-12T10:06:00Z"))
        # The same with empty lists where the provider left the keys out.
        self.assert_not_assessable(sa.assessment_record(gnta(), payload(), "b", "t"))

    def test_classify_is_unchanged(self):
        # "split_units.classify is unchanged: it is a pure function of what it is given." With no event and no bar
        # it still answers as CONTRACT.md says; the correction sits where a response becomes evidence.
        self.check(classify(4.03, 3.00, "2026-11-02", [], []), "NO_ACTION_FOUND", previous_session=None,
                   units="UNKNOWN")

    def test_bars_whose_closes_are_all_none(self):
        # The sessions are listed but none has a price. Whether payload_bars keeps such entries or drops them, it
        # holds no pair whose close is a number greater than zero. A close of 0.0 is not greater than zero either.
        days = ("2026-10-29", "2026-10-30", "2026-11-02")
        for close in (None, 0.0):
            with self.subTest(close=close):
                response = payload(bars=[(day, close) for day in days])
                self.assert_not_assessable(sa.assessment_record(gnta(), response, "b", "t"))

    def test_error_body_or_no_data(self):
        # "The same holds for a response that carries an error instead of data."
        for response in (error_response(), {"finance": {"error": "Too Many Requests"}},
                         {"chart": {"result": [{}]}}, {}):
            with self.subTest(response=response):
                self.assertEqual(split_units.payload_bars(response), [])
                self.assert_not_assessable(sa.assessment_record(gnta(), response, "b", "t"))

    def test_split_events_without_a_priced_bar_are_not_used(self):
        # RSPL: r = 9.84 and a 1-for-10 on the signal session, in a response without any bar. The event is there.
        response = payload(splits=[(S, 1, 10)])
        events = split_flags.provider_splits(response)
        self.assertEqual([(e["effective_session"], e["denominator"] / e["numerator"]) for e in events], [(S, 10)])
        # Given that event and no bars the classifier, which is unchanged, says ARTIFACT_PROBABLE (Case C, the
        # split explains the move, r >= 4)...
        self.check(classify(9.84, 1.00, S, events, split_units.payload_bars(response)), "ARTIFACT_PROBABLE")
        # ...but the record does not use the events of a response that holds no bar with a price.
        self.assert_not_assessable(sa.assessment_record(set_rec(), response, "b", "t"))
        # The same when the sessions are listed without prices.
        unpriced = payload(bars=[("2026-11-06", None), (P, None), (S, None)], splits=[(S, 1, 10)])
        self.assert_not_assessable(sa.assessment_record(set_rec(), unpriced, "b", "t"))

    def test_one_priced_bar_is_evidence(self):
        # GNTA with a single bar, Friday 2026-10-30 at p = 3.00: Case B matches it, 3 days before the signal.
        # r = 1.3433 < 4 and no split: NO_ACTION_FOUND, this time on evidence.
        r = sa.assessment_record(gnta(), payload(bars=[("2026-10-30", 3.00)]), "b", "t")
        self.assertEqual((r["assessment"], r["group"]), ("NO_ACTION_FOUND", "REAL"))
        self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]),
                         ("2026-10-30", "matched", "UNCHANGED"))
        # RSPL with one priced bar, the signal session itself, next to an unpriced one. payload_bars now holds a
        # pair with a price, so the response is evidence and its events are used. There is still no reference bar
        # (2026-11-09 has no price, 2026-11-10 is not before the signal): Case C, the 1-for-10 explains the move
        # (9.84 / 10 - 1 = -0.016), straddle UNKNOWN, r = 9.84 >= 4: ARTIFACT_PROBABLE.
        one = payload(bars=[(P, None), (S, 9.84)], splits=[(S, 1, 10)])
        r = sa.assessment_record(set_rec(), one, "b", "t")
        self.assertEqual((r["assessment"], r["group"]), ("ARTIFACT_PROBABLE", "ARTIFACT"))
        self.assertEqual((r["split"], r["split_adjusted_ret1"]), ("2026-11-10 1:10", -0.016))
        self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]), (None, None, "UNKNOWN"))

    def test_seal_previous_session_is_not_carried_into_the_record(self):
        # "With no previous session", also when the set's seal assessment recorded one.
        sealed = dict(govx_seal(), prev_hash="0" * 64, record_hash="9f" * 32)
        r = sa.assessment_record(govx(), empty_response("GOVX"), "b", "t", prior=sealed, seal=sealed)
        self.assert_not_assessable(r)
        self.assertEqual((r["supersedes"], r["recorded_ret1"]), ("9f" * 32, 21.08))

    def test_pending_set_without_bars_is_unresolved_and_stays_in_every_view(self):
        spec, sid = gnta(), gnta()["set_id"]
        new = sa.propose_assessments([spec], [], {"GNTA": empty_response()}, "pull us_2026-11-12",
                                     "2026-11-12T10:06:00Z", retrieved_on="2026-11-12")
        self.assertEqual(len(new), 1)
        self.assert_not_assessable(new[0])
        self.assertEqual(new[0]["pull_role"], "later")
        records = self.write(*new)
        self.assertEqual(sa.verify(records=records, specs=[spec]), [])
        # "They stay in every view, as every unresolved set does, and are counted as unresolved."
        self.assertEqual(sa.unresolved_set_ids(records), {sid})
        flag = v11(spec, "NOT_FLAGGED", "2026-11-02T22:10:00Z")
        cutoffs = {sid: "2026-11-03T14:30:00Z"}
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), set())
        self.assertEqual(sa.removed_set_ids("at_the_time", records=records, v11_flags=[flag], cutoffs=cutoffs),
                         set())
        rows = [row(aaa(), net=0.05), row(spec, net=0.08)]
        v = paper_book_report.views(rows, records, [flag], cutoffs)
        for name in ("as_frozen", "at_the_time", "corrected"):
            self.assertEqual([r["ticker"] for r in v[name]], ["AAA", "GNTA"], name)

    def test_reassessment_proposes_not_assessable_when_the_history_is_lost(self):
        specs = [smx(), govx(), gnta()]
        records = self.write(smx_real("2026-11-10T22:10:05Z", pull_role="seal"), govx_seal(),
                             arec(gnta(), "NOT_ASSESSABLE", "2026-11-12T10:06:00Z"))
        # SMX was assessed REAL; tonight the provider returns no bar for it: not skipped, proposed NOT_ASSESSABLE.
        # GOVX: its ticker has no payload in the pull: skipped.
        # GNTA is NOT_ASSESSABLE already and its response still holds no bar: no difference, nothing proposed.
        payloads = {"SMX": empty_response("SMX"), "GNTA": empty_response("GNTA")}
        out = sa.propose_reassessments(specs, records, payloads, "pull us_2026-11-13", "2026-11-13T22:05:00Z",
                                       retrieved_on="2026-11-13")
        self.assertEqual([r["set_id"] for r in out], [smx()["set_id"]])
        r = out[0]
        self.assert_not_assessable(r)
        self.assertEqual((r["pull_role"], r["supersedes"]), ("later", records[0]["record_hash"]))
        self.assertEqual((r["basis"], r["assessed_at"]), ("pull us_2026-11-13", "2026-11-13T22:05:00Z"))
        self.assertTrue(sa.changed(r, records[0]))
        # "A visible reassessment, not silence": it goes into the ledger and the validator accepts it.
        records = self.write(r)
        self.assertEqual(len(records), 4)
        self.assertEqual(sa.verify(records=records, specs=specs), [])
        self.assertEqual(sa.verify(specs=specs), [])
        self.assertEqual(sa.latest(records)[smx()["set_id"]]["assessment"], "NOT_ASSESSABLE")
        # Changed for CONTRACT_ADDENDUM_2.md, point 2 (SMX was expected here too): SMX's standing assessment is
        # still REAL_MOVE_AFTER_SPLIT, so it is not unresolved. GOVX (UNEXPLAINED_EXTREME_MOVE) and GNTA (only
        # NOT_ASSESSABLE) are.
        self.assertEqual(sa.unresolved_set_ids(records), {govx()["set_id"], gnta()["set_id"]})
        # The next night returns the same: nothing differs any more.
        self.assertEqual(sa.propose_reassessments(specs, records, payloads, "pull us_2026-11-14",
                                                  "2026-11-14T22:05:00Z"), [])

    def test_reassessment_of_an_artifact_whose_history_is_lost(self):
        # The addendum makes no exception for the group of the latest assessment: a set whose payload holds no bar
        # "is proposed as NOT_ASSESSABLE when that differs from its latest assessment" (CONTRACT_QUESTIONS.md,
        # question 20). Here the latest assessment is ARTIFACT_CONFIRMED and the response is an error body.
        records = self.write(govx_seal())
        records = self.write(govx_confirmed(records[0]["record_hash"]))
        out = sa.propose_reassessments([govx()], records, {"GOVX": error_response()}, "pull us_2026-11-13",
                                       "2026-11-13T22:05:00Z")
        self.assertEqual(len(out), 1)
        self.assert_not_assessable(out[0])
        self.assertEqual((out[0]["pull_role"], out[0]["supersedes"]), ("later", records[1]["record_hash"]))
        # A ticker that is not in the pull at all is skipped, as before.
        self.assertEqual(sa.propose_reassessments([govx()], records, {}, "pull us_2026-11-13",
                                                  "2026-11-13T22:05:00Z"), [])


# ==================================================================================================================
# CONTRACT_ADDENDUM_2.md: an absence shows nothing without a reference bar; NOT_ASSESSABLE never displaces a finding
# ==================================================================================================================

class AddendumTwo(LedgerCase):
    """Point 1: in assessment_record the rule's class NO_ACTION_FOUND becomes NOT_ASSESSABLE when the response holds
    no reference bar (a priced bar with S - 30 days <= X < S); every other class is kept as the rule returns it.
    Point 2: standing(records) is a set's last record that is not NOT_ASSESSABLE (its last record when all are), and
    removed_set_ids, unresolved_set_ids and the book report conclude from it. latest, changed, propose_reassessments,
    the supersedes chain and verify are unchanged."""

    def assert_not_assessable(self, r):
        # "With the fields addendum 1 gives."
        self.assertEqual(set(r), RECORD_KEYS)
        self.assertEqual((r["assessment"], r["group"]), ("NOT_ASSESSABLE", "UNRESOLVED"))
        self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]), (None, None, "UNKNOWN"))
        self.assertEqual((r["split"], r["split_adjusted_ret1"], r["later_factor"]), ("", None, None))

    def na(self, spec, at, **kw):
        return arec(spec, "NOT_ASSESSABLE", at, basis="pull of a night without bars", **kw)

    # ---- point 1 -------------------------------------------------------------------------------------------------

    def test_only_the_signal_session_bar_and_no_events(self):
        # ADIL: 3.403 / 2.50 = 1.3612. The response holds one bar, on the signal session, and no events. The rule,
        # unchanged: no reference bar and no recorded previous session, Case C; E empty, r < 4, P unknown: CA-9.
        response = adil_response()
        bars = split_units.payload_bars(response)
        self.assertEqual([tuple(b) for b in bars], [("2026-10-28", 3.403)])
        self.check(classify(3.403, 2.50, "2026-10-28", split_flags.provider_splits(response), bars),
                   "NO_ACTION_FOUND", previous_session=None, units="UNKNOWN")
        # In the record that absence is not a finding: the response does not reach back before the signal session.
        r = sa.assessment_record(adil(), response, "pull us_2026-11-12", "2026-11-12T10:06:00Z")
        self.assert_not_assessable(r)
        self.assertEqual(r["recorded_ret1"], 0.3612)
        self.assertEqual((r["pull_role"], r["supersedes"], r["basis"], r["assessed_at"]),
                         ("later", None, "pull us_2026-11-12", "2026-11-12T10:06:00Z"))

    def test_priced_bars_only_on_or_after_the_signal_session_and_no_events(self):
        # No priced bar with 2026-09-28 <= X < 2026-10-28 in any of these; r = 1.3612 and no event: the rule says
        # NO_ACTION_FOUND, the record NOT_ASSESSABLE.
        for bars in ([("2026-10-29", 3.10), ("2026-10-30", 2.95)],
                     [("2026-10-28", 3.403), ("2026-10-29", 3.10), ("2026-10-30", 2.95)],
                     # earlier sessions are listed, but without a price
                     [("2026-10-26", None), ("2026-10-27", None), ("2026-10-28", 3.403), ("2026-10-29", 3.10)],
                     [("2026-10-27", 0.0), ("2026-10-28", 3.403)]):
            with self.subTest(bars=bars):
                self.assert_not_assessable(sa.assessment_record(adil(), payload(bars=bars), "b", "t"))

    def test_earlier_bar_older_than_thirty_days_and_no_events(self):
        # GNTA, signal 2026-11-02: reference bars have 2026-10-03 <= X < 2026-11-02. The only earlier bar is of
        # Friday 2026-10-02, 31 days before: not a reference bar. r = 1.3433, no event: NOT_ASSESSABLE.
        r = sa.assessment_record(gnta(), payload(bars=[("2026-10-02", 2.95), ("2026-11-02", 4.03)]), "b", "t")
        self.assert_not_assessable(r)
        # The bound, on a signal of Thursday 2026-11-05 (1.50 / 1.00). A bar on 2026-10-05, S - 31: none.
        spec = set_rec("US-XONE-20261105", "XONE", 1.50, 1.00, S5)
        outside = sa.assessment_record(spec, payload(bars=[("2026-10-05", 1.00), (S5, 1.50)]), "b", "t")
        self.assert_not_assessable(outside)
        # A bar on 2026-10-06, S - 30, is a reference bar. It equals p, so Case B takes it as the previous bar,
        # 30 days old: the rule says STALE_PREVIOUS, and a class other than NO_ACTION_FOUND is kept.
        inside = sa.assessment_record(spec, payload(bars=[("2026-10-06", 1.00), (S5, 1.50)]), "b", "t")
        self.assertEqual((inside["assessment"], inside["group"]), ("STALE_PREVIOUS", "UNRESOLVED"))
        self.assertEqual((inside["previous_session"], inside["previous_session_source"], inside["units"]),
                         ("2026-10-06", "matched", "UNCHANGED"))

    def test_one_reference_bar_and_no_events_is_assessed_normally(self):
        # ADIL with the bar of Tuesday 2026-10-27 at p = 2.50, with or without the signal-session bar: Case B
        # matches it, one day back; r = 1.3612 < 4, no split: NO_ACTION_FOUND with its previous session identified.
        for bars in ([("2026-10-27", 2.50)], [("2026-10-27", 2.50), ("2026-10-28", 3.403)]):
            with self.subTest(bars=bars):
                r = sa.assessment_record(adil(), payload(bars=bars), "b", "t")
                self.assertEqual((r["assessment"], r["group"]), ("NO_ACTION_FOUND", "REAL"))
                self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]),
                                 ("2026-10-27", "matched", "UNCHANGED"))
        # A reference bar that does not match is a finding too: 2.90 against 2.50 is 16% away, no event.
        r = sa.assessment_record(adil(), payload(bars=[("2026-10-27", 2.90), ("2026-10-28", 3.403)]), "b", "t")
        self.assertEqual((r["assessment"], r["units"]), ("UNITS_INCONSISTENT", "INCONSISTENT"))

    def test_listed_split_keeps_its_class_without_a_reference_bar(self):
        # One priced bar, on the signal session, and a split listed on it. No reference bar: Case C, straddle
        # UNKNOWN. These classes "rest on a split the response does list" and are kept.
        cases = {
            # r = 9.84 >= 4; the 1-for-10 explains it: 9.84 / 10 - 1 = -0.016.
            "ARTIFACT_PROBABLE": (set_rec(), payload(bars=[(S, 9.84)], splits=[(S, 1, 10)]),
                                  "2026-11-10 1:10", -0.016),
            # r = 3.15 < 4; the 1-for-3 explains it: 3.15 / 3 - 1 = 0.05.
            "SPLIT_IN_WINDOW_UNRESOLVED": (xtri(), payload(bars=[("2026-11-03", 6.30), ("2026-11-04", 6.10)],
                                                           splits=[("2026-11-03", 1, 3)]), "2026-11-03 1:3", 0.05),
            # r = 3, 1-for-2: 3 / 2 - 1 = 0.50, not explained, but |ln 1.5| = 0.405 < |ln 3| = 1.099: CA-5.
            "REAL_MOVE_UNITS_UNVERIFIED": (set_rec(close=3.00), payload(bars=[(S, 3.00)], splits=[(S, 1, 2)]),
                                           "", None),
            # r = 1.5, 1-for-10: 0.15 is further from no move than 1.5; r < 4, P unknown, E not empty: CA-8.
            "REAL_MOVE_AFTER_SPLIT": (set_rec(close=1.50), payload(bars=[(S, 1.50)], splits=[(S, 1, 10)]),
                                      "", None),
        }
        for cls, (spec, response, split, adjusted) in cases.items():
            with self.subTest(cls):
                r = sa.assessment_record(spec, response, "b", "t")
                self.assertEqual((r["assessment"], r["group"]), (cls, GROUP_OF[cls]))
                self.assertEqual((r["split"], r["split_adjusted_ret1"]), (split, adjusted))
                self.assertEqual((r["previous_session"], r["previous_session_source"], r["units"]),
                                 (None, None, "UNKNOWN"))

    def test_extreme_move_keeps_its_class_without_a_reference_bar(self):
        # GOVX with the signal-session bar only and no events: Case C, E empty, 22.08 >= 4: CA-6. The class "rests
        # on the size of the move" and is kept.
        r = sa.assessment_record(govx(), payload(bars=[("2026-11-11", 5.52)]), "b", "t")
        self.assertEqual((r["assessment"], r["group"]), ("UNEXPLAINED_EXTREME_MOVE", "UNRESOLVED"))
        self.assertEqual((r["previous_session"], r["units"], r["split"]), (None, "UNKNOWN", ""))
        # At the bound: 2.00 / 0.50 = 4.0 exactly is extreme and kept; 1.99 / 0.50 = 3.98 is NO_ACTION_FOUND by the
        # rule and therefore NOT_ASSESSABLE in the record.
        at = sa.assessment_record(set_rec(close=2.00, prev=0.50), payload(bars=[(S, 2.00)]), "b", "t")
        self.assertEqual(at["assessment"], "UNEXPLAINED_EXTREME_MOVE")
        below = sa.assessment_record(set_rec(close=1.99, prev=0.50), payload(bars=[(S, 1.99)]), "b", "t")
        self.assert_not_assessable(below)

    def test_response_that_no_longer_reaches_back_after_a_real_assessment(self):
        # ADIL was NO_ACTION_FOUND at sealing, with its previous session 2026-10-27. A later response holds the
        # signal-session bar only. The rule, Case A on the seal's session: no reference bar there, units UNKNOWN;
        # r < 4, no event, gap 1 day: NO_ACTION_FOUND. No reference bar in the response: NOT_ASSESSABLE, with no
        # previous session. It differs from the last record, so it is proposed (point 1 meets addendum 1).
        spec, sid = adil(), adil()["set_id"]
        records = self.write(arec(spec, "NO_ACTION_FOUND", "2026-10-28T22:10:05Z", pull_role="seal",
                                  previous_session="2026-10-27", source="matched", units="UNCHANGED"))
        out = sa.propose_reassessments([spec], records, {"ADIL": adil_response()}, "pull us_2026-11-12",
                                       "2026-11-12T10:06:00Z")
        self.assertEqual(len(out), 1)
        self.assert_not_assessable(out[0])
        self.assertEqual((out[0]["pull_role"], out[0]["supersedes"]), ("later", records[0]["record_hash"]))
        records = self.write(*out)
        self.assertEqual(sa.verify(records=records, specs=[spec]), [])
        # Point 2: the record exists, the finding stands.
        self.assertEqual(sa.latest(records)[sid]["assessment"], "NOT_ASSESSABLE")
        self.assertEqual(sa.standing(records)[sid]["assessment"], "NO_ACTION_FOUND")
        self.assertEqual(sa.unresolved_set_ids(records), set())

    # ---- point 2: standing ---------------------------------------------------------------------------------------

    def test_standing_keeps_a_finding_over_a_later_not_assessable(self):
        sid = govx()["set_id"]
        g1, g2 = govx_seal(T2), govx_confirmed("ab" * 32, T4)
        g3 = self.na(govx(), "2026-11-13T22:05:00Z", supersedes="cd" * 32)
        out = sa.standing([g1, g2, g3])
        self.assertEqual(set(out), {sid})
        self.assertEqual(out[sid], g2)
        # A finding of an unresolved class stands in the same way: only NOT_ASSESSABLE is passed over.
        v1 = arec(vcig(), "UNITS_INCONSISTENT", "2026-11-12T10:06:00Z", units="INCONSISTENT")
        v2 = self.na(vcig(), "2026-11-13T22:05:00Z", supersedes="ef" * 32)
        self.assertEqual(sa.standing([v1, v2])[vcig()["set_id"]], v1)

    def test_standing_of_a_set_with_only_not_assessable_records(self):
        sid = gnta()["set_id"]
        n1 = self.na(gnta(), "2026-11-12T10:06:00Z")
        self.assertEqual(sa.standing([n1]), {sid: n1})
        # "For a set whose records are all NOT_ASSESSABLE, its last record."
        n2 = dict(self.na(gnta(), "2026-11-13T22:05:00Z", supersedes="ab" * 32), basis="second request")
        self.assertEqual(sa.standing([n1, n2])[sid], n2)
        self.assertEqual(sa.standing([]), {})

    def test_standing_after_not_assessable_then_a_class(self):
        xid = xtri()["set_id"]
        x1 = self.na(xtri(), "2026-11-03T22:10:05Z", pull_role="seal")
        x2 = arec(xtri(), "NO_ACTION_FOUND", "2026-11-04T22:10:05Z", supersedes="a1" * 32,
                  previous_session="2026-11-02", source="matched", units="UNCHANGED")
        self.assertEqual(sa.standing([x1, x2])[xid], x2)
        # Through a second gap, with a newer finding and another night without bars: the last finding.
        x3 = self.na(xtri(), "2026-11-05T22:10:05Z", supersedes="a2" * 32)
        x4 = arec(xtri(), "ARTIFACT_CONFIRMED", "2026-11-06T22:10:05Z", supersedes="a3" * 32,
                  split="2026-11-03 1:3", adjusted=0.05, previous_session="2026-11-02", source="rebased_match",
                  units="PRE_SPLIT_CONFIRMED")
        x5 = self.na(xtri(), "2026-11-09T22:10:05Z", supersedes="a4" * 32)
        self.assertEqual(sa.standing([x1, x2, x3])[xid], x2)
        self.assertEqual(sa.standing([x1, x2, x3, x4, x5])[xid], x4)
        # Several sets, interleaved in the ledger.
        g1, g2 = govx_seal(T2), govx_confirmed("ab" * 32, T4)
        g3 = self.na(govx(), "2026-11-13T22:05:00Z", supersedes="cd" * 32)
        n1 = self.na(gnta(), "2026-11-12T10:06:00Z")
        self.assertEqual(sa.standing([x1, g1, x2, g2, n1, g3]),
                         {xid: x2, govx()["set_id"]: g2, gnta()["set_id"]: n1})

    # ---- point 2: the readers ------------------------------------------------------------------------------------

    def test_corrected_still_removes_a_confirmed_artifact_after_not_assessable(self):
        sid = govx()["set_id"]
        records = [govx_seal(T2), govx_confirmed("ab" * 32, T4),
                   self.na(govx(), "2026-11-13T22:05:00Z", supersedes="cd" * 32)]
        flags = [v11(govx(), "INDETERMINATE", T1)]
        self.assertEqual(sa.latest(records)[sid]["assessment"], "NOT_ASSESSABLE")
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=flags), {sid})
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[]), {sid})

    def test_corrected_still_removes_a_v11_artifact_whose_first_assessment_is_not_assessable(self):
        flags = [v11(tops(), "ARTIFACT_V11", "2026-11-09T22:10:00Z", "2026-11-06 1:10", -0.016),
                 v11(gnta(), "NOT_FLAGGED", "2026-11-02T22:10:00Z"),
                 v11(vcig(), "INDETERMINATE", "2026-11-02T22:10:00Z")]
        records = [self.na(tops(), "2026-11-12T10:06:00Z"), self.na(gnta(), "2026-11-12T10:06:00Z"),
                   self.na(vcig(), "2026-11-12T10:06:00Z")]
        # TOPS keeps its ARTIFACT_V11 tag in force. GNTA and VCIG carry no artifact tag and are not removed.
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=flags), {tops()["set_id"]})

    def test_corrected_v11_artifact_with_a_finding_of_another_class_is_not_removed(self):
        flags = [v11(s, "ARTIFACT_V11", "2026-11-10T22:10:00Z") for s in (tops(), smx(), xtri(), aaa())]
        records = [
            # another unresolved class
            arec(tops(), "UNITS_INCONSISTENT", "2026-11-12T10:06:00Z", units="INCONSISTENT"),
            # a REAL class (part C, case 4)
            smx_real(),
            # NOT_ASSESSABLE first, then a finding of another unresolved class: that finding stands
            self.na(xtri(), "2026-11-03T22:10:05Z", pull_role="seal"),
            arec(xtri(), "SPLIT_IN_WINDOW_UNRESOLVED", "2026-11-04T22:10:05Z", supersedes="a1" * 32,
                 split="2026-11-03 1:3", adjusted=0.05),
            # a REAL class, then a night without bars: the REAL finding stands
            arec(aaa(), "NO_ACTION_FOUND", "2026-11-12T10:06:00Z", previous_session="2026-10-28", source="matched",
                 units="UNCHANGED"),
            self.na(aaa(), "2026-11-13T22:05:00Z", supersedes="b1" * 32),
        ]
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=flags), set())

    def test_at_the_time_ignores_not_assessable_records(self):
        g, sid = govx(), govx()["set_id"]

        def at_the_time(records, flags):
            return sa.removed_set_ids("at_the_time", records=records, v11_flags=flags, cutoffs={sid: CUT})

        probable = arec(g, "ARTIFACT_PROBABLE", T2, split="2026-11-11 1:24", adjusted=-0.08)
        real = arec(g, "NO_ACTION_FOUND", T2, previous_session="2026-11-10", source="matched", units="UNCHANGED")
        tag = v11(g, "ARTIFACT_V11", T1)
        # A V11 artifact tag at T1 and a NOT_ASSESSABLE assessment at T2, both before the cutoff. The assessment is
        # the later record, but it is ignored: the tag decides.
        self.assertEqual(at_the_time([self.na(g, T2)], [tag]), {sid})
        # The same at one and the same time: the tie rule would let the assessment decide, but it is ignored.
        self.assertEqual(at_the_time([self.na(g, T1)], [tag]), {sid})
        # An artifact assessment at T2, then NOT_ASSESSABLE at T3, both before the cutoff: the artifact decides.
        self.assertEqual(at_the_time([probable, self.na(g, T3)], [v11(g, "NOT_FLAGGED", T1)]), {sid})
        # Tag at T1, a REAL assessment at T2, NOT_ASSESSABLE at T3: the REAL assessment is the latest that counts.
        self.assertEqual(at_the_time([real, self.na(g, T3)], [tag]), set())
        # NOT_ASSESSABLE alone removes nothing, with a plain V11 record or with none.
        self.assertEqual(at_the_time([self.na(g, T2)], [v11(g, "INDETERMINATE", T1)]), set())
        self.assertEqual(at_the_time([self.na(g, T2)], []), set())
        # After the cutoff it did not count before either.
        self.assertEqual(at_the_time([self.na(g, T4)], [tag]), {sid})

    def test_unresolved_set_ids_uses_the_standing_assessment(self):
        records = [
            # SMX: REAL, then a night without bars: not unresolved
            smx_real("2026-11-10T22:10:05Z", pull_role="seal"),
            self.na(smx(), "2026-11-13T22:05:00Z", supersedes="a1" * 32),
            # GOVX: unresolved, then a confirmed artifact, then a night without bars: not unresolved
            govx_seal(T2), govx_confirmed("ab" * 32, T4),
            self.na(govx(), "2026-11-13T22:05:00Z", supersedes="cd" * 32),
            # VCIG: an unresolved finding, then a night without bars: still unresolved
            arec(vcig(), "UNITS_INCONSISTENT", "2026-11-12T10:06:00Z", units="INCONSISTENT"),
            self.na(vcig(), "2026-11-13T22:05:00Z", supersedes="a2" * 32),
            # GNTA: only NOT_ASSESSABLE: unresolved
            self.na(gnta(), "2026-11-12T10:06:00Z"),
            # XTRI: NOT_ASSESSABLE at sealing, then a REAL class: not unresolved
            self.na(xtri(), "2026-11-03T22:10:05Z", pull_role="seal"),
            arec(xtri(), "NO_ACTION_FOUND", "2026-11-04T22:10:05Z", supersedes="a3" * 32,
                 previous_session="2026-11-02", source="matched", units="UNCHANGED"),
        ]
        self.assertEqual(sa.unresolved_set_ids(records), {vcig()["set_id"], gnta()["set_id"]})

    def test_views_use_the_standing_assessment(self):
        rows = [row(aaa(), net=0.05), row(tops(), verdict="DONT_BUY", net=-0.02), row(govx(), status="OPEN")]
        flags = [v11(tops(), "ARTIFACT_V11", "2026-11-09T22:10:00Z", "2026-11-06 1:10", -0.016),
                 v11(govx(), "INDETERMINATE", T1)]
        records = [
            self.na(tops(), "2026-11-09T22:10:05Z", pull_role="seal"),  # before TOPS's cutoff
            govx_seal(T2), govx_confirmed("ab" * 32, T4),
            self.na(govx(), "2026-11-13T22:05:00Z", supersedes="cd" * 32),
        ]
        cutoffs = {aaa()["set_id"]: "2026-10-30T13:30:00Z", tops()["set_id"]: "2026-11-10T14:30:00Z",
                   govx()["set_id"]: CUT}
        v = paper_book_report.views(rows, records, flags, cutoffs)
        self.assertEqual([r["ticker"] for r in v["as_frozen"]], ["AAA", "TOPS", "GOVX"])
        # At the time: TOPS carried its V11 tag before the cutoff and the NOT_ASSESSABLE record is ignored. GOVX
        # was unresolved before its cutoff.
        self.assertEqual([r["ticker"] for r in v["at_the_time"]], ["AAA", "GOVX"])
        # Corrected: TOPS by its tag (standing assessment NOT_ASSESSABLE), GOVX by its standing ARTIFACT_CONFIRMED.
        self.assertEqual([r["ticker"] for r in v["corrected"]], ["AAA"])

    # ---- point 2: what does not change ---------------------------------------------------------------------------

    def test_latest_and_changed_are_unchanged(self):
        sid = govx()["set_id"]
        g1, g2 = govx_seal(T2), govx_confirmed("ab" * 32, T4)
        g3 = self.na(govx(), "2026-11-13T22:05:00Z", supersedes="cd" * 32)
        # latest is still the last record, whatever its class; standing is the reader that passes it over.
        self.assertEqual(sa.latest([g1, g2, g3])[sid], g3)
        self.assertEqual(sa.standing([g1, g2, g3])[sid], g2)
        # changed still compares assessment, split, previous_session and units, in both directions.
        self.assertTrue(sa.changed(g3, g2))
        self.assertTrue(sa.changed(g2, g3))
        self.assertFalse(sa.changed(dict(g3, basis="another night", assessed_at="2026-11-14T22:05:00Z"), g3))

    def test_ledger_through_a_night_without_bars(self):
        spec, sid = govx(), govx()["set_id"]
        specs, flag, cutoffs = [spec], v11(govx(), "INDETERMINATE", T1), {sid: CUT}
        records = self.write(govx_seal(T2))
        records = self.write(govx_confirmed(records[0]["record_hash"], T4))

        # Friday 2026-11-13: the provider returns no bar. The proposal is still made (addendum 1) and supersedes
        # the set's last record, the confirmed artifact.
        lost = sa.propose_reassessments(specs, records, {"GOVX": empty_response("GOVX")}, "pull us_2026-11-13",
                                        "2026-11-13T22:05:00Z")
        self.assertEqual(len(lost), 1)
        self.assert_not_assessable(lost[0])
        self.assertEqual((lost[0]["pull_role"], lost[0]["supersedes"]), ("later", records[1]["record_hash"]))
        records = self.write(*lost)
        self.assertEqual(len(records), 3)
        self.assertEqual(sa.verify(records=records, specs=specs), [])
        self.assertEqual(sa.verify(specs=specs), [])
        # The ledger records the night; the readers keep the finding.
        self.assertEqual(sa.latest(records)[sid]["record_hash"], records[2]["record_hash"])
        self.assertEqual(sa.standing(records)[sid]["record_hash"], records[1]["record_hash"])
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), {sid})
        self.assertEqual(sa.removed_set_ids("at_the_time", records=records, v11_flags=[flag], cutoffs=cutoffs),
                         set())
        self.assertEqual(sa.unresolved_set_ids(records), set())
        # A second night without bars (Monday 2026-11-16) is compared with the last record and differs in nothing.
        self.assertEqual(sa.propose_reassessments(specs, records, {"GOVX": error_response()}, "pull us_2026-11-16",
                                                  "2026-11-16T22:05:00Z"), [])

        # Tuesday 2026-11-17: the data is back. The pull is compared with the last record, the NOT_ASSESSABLE one,
        # so the artifact is recorded again, and the new record supersedes the NOT_ASSESSABLE record. The seal
        # assessment still supplies the previous session (Case A, "recorded").
        back = sa.propose_reassessments(specs, records, {"GOVX": govx_later_pull()}, "pull us_2026-11-17",
                                        "2026-11-17T22:05:00Z", retrieved_on="2026-11-17")
        self.assertEqual(len(back), 1)
        self.assertEqual((back[0]["assessment"], back[0]["split"], back[0]["split_adjusted_ret1"]),
                         ("ARTIFACT_CONFIRMED", "2026-11-11 1:24", -0.08))
        self.assertEqual((back[0]["previous_session"], back[0]["previous_session_source"]),
                         ("2026-11-10", "recorded"))
        self.assertEqual((back[0]["pull_role"], back[0]["supersedes"]), ("later", records[2]["record_hash"]))
        records = self.write(*back)
        self.assertEqual(len(records), 4)
        self.assertEqual([r["supersedes"] for r in records],
                         [None, records[0]["record_hash"], records[1]["record_hash"], records[2]["record_hash"]])
        self.assertEqual(sa.verify(records=records, specs=specs), [])
        self.assertEqual(sa.verify(specs=specs), [])
        self.assertEqual(sa.latest(records)[sid]["record_hash"], records[3]["record_hash"])
        self.assertEqual(sa.standing(records)[sid]["record_hash"], records[3]["record_hash"])
        self.assertEqual(sa.seal_assessments(records)[sid]["record_hash"], records[0]["record_hash"])
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), {sid})
        # The same pull again proposes nothing.
        self.assertEqual(sa.propose_reassessments(specs, records, {"GOVX": govx_later_pull()}, "pull us_2026-11-18",
                                                  "2026-11-18T22:05:00Z", retrieved_on="2026-11-18"), [])


# ==================================================================================================================
# Part B3: the paper book report
# ==================================================================================================================

def aaa():
    return set_rec("US-AAA-20261029", "AAA", 1.45, 1.00, "2026-10-29")


class BookViews(LedgerCase):
    def setUp(self):
        super().setUp()
        self.rows = [
            row(aaa(), net=0.05),  # never tagged, never assessed
            row(vcig(), verdict="DONT_BUY", net=-0.12),  # unresolved
            row(tops(), verdict="DONT_BUY", owner="SKIP", net=-0.02),  # V11 artifact before its cutoff, no assessment
            row(smx(), owner="BUY", net=0.21),  # V11 artifact before its cutoff, assessed REAL afterwards
            row(govx(), status="OPEN"),  # unresolved before its cutoff, a confirmed artifact afterwards
        ]
        self.flags = [
            v11(vcig(), "INDETERMINATE", "2026-11-02T22:10:00Z"),
            v11(tops(), "ARTIFACT_V11", "2026-11-09T22:10:00Z", "2026-11-06 1:10", -0.016),
            v11(smx(), "ARTIFACT_V11", "2026-11-10T22:10:00Z", "2026-11-09 1:2.8", -0.2643),
            v11(govx(), "INDETERMINATE", T1),
        ]
        self.records = [
            govx_seal(T2),
            arec(vcig(), "UNITS_INCONSISTENT", "2026-11-12T10:06:00Z", units="INCONSISTENT"),
            smx_real("2026-11-12T10:06:00Z"),
            govx_confirmed("ab" * 32, T4),
        ]
        self.cutoffs = {
            aaa()["set_id"]: "2026-10-30T13:30:00Z",  # 09:30 in New York, still on daylight time
            vcig()["set_id"]: "2026-11-03T14:30:00Z",
            tops()["set_id"]: "2026-11-10T14:30:00Z",
            smx()["set_id"]: "2026-11-11T14:30:00Z",
            govx()["set_id"]: CUT,
        }

    def tickers(self, rows):
        return [r["ticker"] for r in rows]

    def test_three_views(self):
        v = paper_book_report.views(self.rows, self.records, self.flags, self.cutoffs)
        self.assertEqual(set(v), {"as_frozen", "at_the_time", "corrected"})
        self.assertEqual(v["as_frozen"], self.rows)
        # At the time: TOPS and SMX carried ARTIFACT_V11 before their cutoffs. GOVX was unresolved then.
        self.assertEqual(self.tickers(v["at_the_time"]), ["AAA", "VCIG", "GOVX"])
        # Corrected: TOPS (V11 tag, no assessment) and GOVX (confirmed artifact) are out; SMX is back.
        self.assertEqual(self.tickers(v["corrected"]), ["AAA", "VCIG", "SMX"])
        for name in ("at_the_time", "corrected"):
            for r in v[name]:
                self.assertIn(r, self.rows)

    def test_rows_keep_their_order(self):
        rows = list(reversed(self.rows))
        v = paper_book_report.views(rows, self.records, self.flags, self.cutoffs)
        self.assertEqual(self.tickers(v["as_frozen"]), ["GOVX", "SMX", "TOPS", "VCIG", "AAA"])
        self.assertEqual(self.tickers(v["at_the_time"]), ["GOVX", "VCIG", "AAA"])
        self.assertEqual(self.tickers(v["corrected"]), ["SMX", "VCIG", "AAA"])

    def test_without_records_every_view_is_the_frozen_book(self):
        v = paper_book_report.views(self.rows, [], [], {})
        self.assertEqual((v["as_frozen"], v["at_the_time"], v["corrected"]), (self.rows, self.rows, self.rows))
        self.assertEqual(paper_book_report.views([], self.records, self.flags, self.cutoffs),
                         {"as_frozen": [], "at_the_time": [], "corrected": []})


def legacy_section(rows, tagged):
    """The secondary section exactly as paper_book_report.secondary_view wrote it before this change."""
    hit = [r for r in rows if r["set_id"] in tagged]
    kept = [r for r in rows if r["set_id"] not in tagged]
    names = ", ".join(f"{r['ticker']} ({r['session']})" for r in hit)
    out = [
        LEGACY_HEADING,
        "",
        f"{len(hit)} of {len(rows)} planned spikes were recorded as +30% days only because a reverse split "
        "left the last pre-split close in the provider's data (`paper/split_flags.jsonl`, rule "
        f"`{split_flags.RULE_ID}`, research/US_SPLIT_ARTIFACTS_v1). Tagged: {names}.",
        "",
        "The same books without them. This is a disclosure, not a second verdict: the planned look and "
        "the bounds above are computed on every planned spike, as frozen.",
        "",
        "| Book | Positions | Closed | Wins | P&L | Average trade |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for b in book.BOOKS:
        s = book.book_summary(kept, b)
        avg = "-" if s["average"] is None else f"{s['average']:+.2%}"
        out.append(f"| {b} | {s['positions']} | {s['closed']} | {s['wins']} | ${s['pnl']:+,.0f} | {avg} |")
    return "\n\n" + "\n".join(out) + "\n"


class SecondaryView(LedgerCase):
    """secondary_view(rows) reads the two ledgers on disk. The contract does not say where it takes the entry
    cutoffs from (CONTRACT_QUESTIONS.md, question 17); the plans of the rows are written to a temporary paper book
    ledger in case it reads them there, and nothing asserted here depends on a cutoff."""

    def setUp(self):
        super().setUp()
        self.book_path = self.dir / "paper_book.jsonl"
        p = mock.patch.object(book, "LEDGER", self.book_path)
        p.start()
        self.addCleanup(p.stop)
        self.rows = [row(aaa(), net=0.05), row(tops(), verdict="DONT_BUY", owner="SKIP", net=-0.02),
                     row(govx(), status="OPEN")]
        cutoffs = ("2026-10-30T13:30:00Z", "2026-11-10T14:30:00Z", CUT)
        made = ("2026-10-29T22:20:00Z", "2026-11-09T22:20:00Z", "2026-11-11T22:20:00Z")
        paper.append([{"type": book.PLAN, "book": book.BOOK_ID, "set_id": r["set_id"], "ticker": r["ticker"],
                       "signal_session": r["session"], "entry_cutoff": cutoff, "dump_tomorrow": r["dump_tomorrow"],
                       "cutoff": book.CUTOFF, "verdict": r["verdict"], "forecast_record_hash": f"{i:064x}",
                       "made_at": at}
                      for i, (r, cutoff, at) in enumerate(zip(self.rows, cutoffs, made), 1)], path=self.book_path)
        self.tagged = [v11(tops(), "ARTIFACT_V11", "2026-11-09T22:10:00Z", "2026-11-06 1:10", -0.016),
                       v11(govx(), "INDETERMINATE", T1)]

    def test_no_tag_and_no_assessment_gives_nothing(self):
        self.assertEqual(paper_book_report.secondary_view(self.rows), "")

    def test_v11_tag_without_an_assessment_gives_the_legacy_section(self):
        self.write_flags(*self.tagged)
        out = paper_book_report.secondary_view(self.rows)
        self.assertEqual(out, legacy_section(self.rows, {tops()["set_id"]}))
        self.assertNotIn(NEW_HEADING, out)

    def test_assessments_of_sets_outside_the_book_change_nothing(self):
        # SMX has an assessment but is not a row of this book.
        self.write(smx_real())
        self.assertEqual(paper_book_report.secondary_view(self.rows), "")
        self.write_flags(*self.tagged)
        self.assertEqual(paper_book_report.secondary_view(self.rows),
                         legacy_section(self.rows, {tops()["set_id"]}))

    def test_an_assessed_row_gives_the_new_section(self):
        self.write_flags(*self.tagged)
        records = self.write(govx_seal(T2))
        self.write(govx_confirmed(records[0]["record_hash"], T4))
        out = paper_book_report.secondary_view(self.rows)
        self.assertIn(NEW_HEADING, out)
        # "A section headed": the heading is its first line.
        self.assertEqual(out.strip().splitlines()[0], NEW_HEADING)
        # It lists each affected set and gives every book.
        self.assertTrue("GOVX" in out or govx()["set_id"] in out)
        for b in book.BOOKS:
            self.assertIn(b, out)


# ==================================================================================================================
# Part C: the cases the independent tests must include
# ==================================================================================================================

class ContractCases(LedgerCase):
    def test_case_1_genuine_move_after_a_split(self):
        spec, sid = smx(), smx()["set_id"]
        own, later = smx_own_pull(), smx_later_pull()
        # The V11 rule: 2.06 / 2.8 - 1 = -0.264 < 0.30 and |ln 0.7357| = 0.307 < |ln 2.06| = 0.723, the split is
        # within ten days before the signal: tagged an artifact.
        flag = split_flags.flag_record(spec, own, "provider events in pull us_2026-11-10", "2026-11-10T22:10:00Z")
        self.assertEqual(flag["flag"], "ARTIFACT_V11")

        # SPLIT_UNITS_V1 from the scan's own pull. Case B: the latest reference bar within 1% of p = 2.50 is
        # 2026-11-09, the split session itself. P >= effective session: straddle NO. r = 2.06 < 4, gap 1 day,
        # E not empty: REAL_MOVE_AFTER_SPLIT.
        direct = split_units.classify(5.15, 2.50, "2026-11-10", split_flags.provider_splits(own),
                                      split_units.payload_bars(own))
        self.check(direct, "REAL_MOVE_AFTER_SPLIT", previous_session="2026-11-09",
                   previous_session_source="matched", units="UNCHANGED")
        seal = sa.assessment_record(spec, own, "pull us_2026-11-10", "2026-11-10T22:10:05Z", pull_role="seal")
        self.assertEqual((seal["assessment"], seal["group"]), ("REAL_MOVE_AFTER_SPLIT", "REAL"))
        self.assertEqual((seal["previous_session"], seal["previous_session_source"], seal["units"]),
                         ("2026-11-09", "matched", "UNCHANGED"))
        self.assertEqual(seal["recorded_ret1"], 1.06)
        records = self.write(seal)

        # From a later pull, with the seal assessment (Case A on 2026-11-09, bar 2.50 unchanged) and without it.
        with_seal = sa.assessment_record(spec, later, "pull us_2026-11-12", "2026-11-12T22:05:00Z",
                                         prior=records[0], seal=records[0], retrieved_on="2026-11-12")
        self.assertEqual((with_seal["assessment"], with_seal["group"]), ("REAL_MOVE_AFTER_SPLIT", "REAL"))
        self.assertEqual((with_seal["previous_session"], with_seal["previous_session_source"]),
                         ("2026-11-09", "recorded"))
        alone = sa.assessment_record(spec, later, "pull us_2026-11-12", "2026-11-12T22:05:00Z",
                                     retrieved_on="2026-11-12")
        self.assertEqual((alone["assessment"], alone["group"]), ("REAL_MOVE_AFTER_SPLIT", "REAL"))

        # Nothing changed, so nothing is appended; the set is not removed and not unresolved.
        self.assertFalse(sa.changed(with_seal, records[0]))
        self.assertEqual(sa.propose_reassessments([spec], records, {"SMX": later}, "pull us_2026-11-12",
                                                  "2026-11-12T22:05:00Z", retrieved_on="2026-11-12"), [])
        self.assertEqual(sa.verify(records=records, specs=[spec]), [])
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), set())
        self.assertEqual(sa.unresolved_set_ids(records), set())
        self.assertNotIn(sid, sa.removed_set_ids("corrected", records=records, v11_flags=[flag]))

    def test_case_2_split_reported_late(self):
        spec, sid = govx(), govx()["set_id"]
        specs = [spec]
        own, later = govx_own_pull(), govx_later_pull()
        cutoffs = {sid: CUT}  # the open of 2026-11-12
        # At the time the V11 rule finds no split and an extreme ratio (22.08 >= 4): INDETERMINATE.
        flag = split_flags.flag_record(spec, own, "provider events in pull us_2026-11-11", T1)
        self.assertEqual(flag["flag"], "INDETERMINATE")

        # The seal assessment, from the scan's own pull. Case B: 2026-11-10 at 0.25 equals p. E is empty and
        # r = 22.08 >= 4: UNEXPLAINED_EXTREME_MOVE.
        first = sa.propose_assessments(specs, [], {"GOVX": own}, "pull us_2026-11-11", T2,
                                       seal_session="2026-11-11")
        self.assertEqual(len(first), 1)
        seal = first[0]
        self.assertEqual((seal["assessment"], seal["group"]), ("UNEXPLAINED_EXTREME_MOVE", "UNRESOLVED"))
        self.assertEqual((seal["pull_role"], seal["supersedes"]), ("seal", None))
        self.assertEqual((seal["previous_session"], seal["previous_session_source"], seal["units"]),
                         ("2026-11-10", "matched", "UNCHANGED"))
        self.assertEqual((seal["split"], seal["split_adjusted_ret1"], seal["recorded_ret1"]), ("", None, 21.08))
        records = self.write(*first)
        self.assertEqual(sa.verify(records=records, specs=specs), [])
        self.assertEqual(sa.unresolved_set_ids(records), {sid})
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), set())

        # The next night's pull lists the 1-for-24 on the signal session and shows 2026-11-10 at 6.00. Case A on
        # the seal's previous session: 6.00 is not 0.25; 6.00 / (0.25 * 24) = 1: PRE_SPLIT_CONFIRMED;
        # 22.08 / 24 - 1 = -0.08 < 0.30: ARTIFACT_CONFIRMED.
        second = sa.propose_reassessments(specs, records, {"GOVX": later}, "pull us_2026-11-12", T4,
                                          retrieved_on="2026-11-12")
        self.assertEqual(len(second), 1)
        re = second[0]
        self.assertEqual((re["assessment"], re["group"]), ("ARTIFACT_CONFIRMED", "ARTIFACT"))
        self.assertEqual((re["split"], re["split_adjusted_ret1"]), ("2026-11-11 1:24", -0.08))
        self.assertEqual((re["previous_session"], re["previous_session_source"], re["units"], re["later_factor"]),
                         ("2026-11-10", "recorded", "PRE_SPLIT_CONFIRMED", None))
        self.assertEqual((re["pull_role"], re["supersedes"]), ("later", records[0]["record_hash"]))
        records = self.write(*second)

        # Both records are in the ledger, the second supersedes the first, and the validator accepts them.
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["supersedes"], records[0]["record_hash"])
        self.assertEqual(sa.verify(records=records, specs=specs), [])
        self.assertEqual(sa.verify(specs=specs), [])
        self.assertEqual(sa.latest(records)[sid]["assessment"], "ARTIFACT_CONFIRMED")
        self.assertEqual(sa.seal_assessments(records)[sid]["record_hash"], records[0]["record_hash"])
        self.assertEqual(sa.unresolved_set_ids(records), set())

        # The corrected view removes the set. The at-the-time view does not: before the cutoff the latest record
        # about it was the seal assessment (T2), unresolved; the artifact was found at T4, after the cutoff.
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), {sid})
        self.assertEqual(sa.removed_set_ids("at_the_time", records=records, v11_flags=[flag], cutoffs=cutoffs),
                         set())
        rows = [row(aaa(), net=0.05), row(spec, status="OPEN")]
        v = paper_book_report.views(rows, records, [flag], cutoffs)
        self.assertEqual([r["ticker"] for r in v["as_frozen"]], ["AAA", "GOVX"])
        self.assertEqual([r["ticker"] for r in v["at_the_time"]], ["AAA", "GOVX"])
        self.assertEqual([r["ticker"] for r in v["corrected"]], ["AAA"])

        # The same pull again proposes nothing.
        self.assertEqual(sa.propose_reassessments(specs, records, {"GOVX": later}, "pull us_2026-11-13",
                                                  "2026-11-13T22:05:00Z", retrieved_on="2026-11-13"), [])

    def test_case_3_unresolved_evidence_stays_unresolved(self):
        spec, sid = vcig(), vcig()["set_id"]
        specs = [spec]
        later = vcig_later_pull()
        cutoffs = {sid: "2026-11-03T14:30:00Z"}
        # V11 at the time: 4.5 / 3 - 1 = 0.50 is not < 0.30, so the split does not explain it; r >= 4: INDETERMINATE.
        flag = split_flags.flag_record(spec, later, "provider events in pull us_2026-11-02", "2026-11-02T22:10:00Z")
        self.assertEqual(flag["flag"], "INDETERMINATE")

        # Case B. Reference bars 1.42, 1.31, 1.22, 1.15: none within 1% of 0.60. The 1-for-3 of 2026-10-29 is in E
        # (2026-10-23 < 2026-10-29 <= 2026-11-02); before it 1.42 and 1.31 against 0.60 * 3 = 1.80 are 21% and 27%
        # away. Nothing matches: UNITS_INCONSISTENT.
        first = sa.propose_assessments(specs, [], {"VCIG": later}, "pull us_2026-11-12", "2026-11-12T10:06:00Z",
                                       retrieved_on="2026-11-12")
        self.assertEqual(len(first), 1)
        rec = first[0]
        self.assertEqual((rec["assessment"], rec["group"]), ("UNITS_INCONSISTENT", "UNRESOLVED"))
        self.assertEqual((rec["previous_session"], rec["previous_session_source"], rec["units"], rec["split"]),
                         (None, None, "INCONSISTENT", ""))
        self.assertEqual((rec["pull_role"], rec["recorded_ret1"]), ("later", 3.5))
        records = self.write(*first)
        self.assertEqual(sa.verify(records=records, specs=specs), [])

        # It is listed as unresolved and stays in every view.
        self.assertEqual(sa.unresolved_set_ids(records), {sid})
        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), set())
        self.assertEqual(sa.removed_set_ids("at_the_time", records=records, v11_flags=[flag], cutoffs=cutoffs),
                         set())
        rows = [row(aaa(), net=0.05), row(spec, verdict="DONT_BUY", net=-0.12)]
        v = paper_book_report.views(rows, records, [flag], cutoffs)
        for name in ("as_frozen", "at_the_time", "corrected"):
            self.assertEqual([r["ticker"] for r in v[name]], ["AAA", "VCIG"], name)

        # Without new evidence it is not reassessed: the same pull, and a newer pull that only adds sessions after
        # the signal, propose nothing. The ledger keeps its single record and the set stays unresolved.
        newer = vcig_later_pull(extra=[("2026-11-04", 2.05), ("2026-11-05", 1.98)])
        for pull, at in ((later, "2026-11-12T22:05:00Z"), (newer, "2026-11-13T22:05:00Z")):
            again = sa.propose_reassessments(specs, records, {"VCIG": pull}, "pull of the night", at)
            self.assertEqual(again, [])
        fresh = sa.assessment_record(spec, newer, "pull us_2026-11-13", "2026-11-13T22:05:00Z", prior=records[0])
        self.assertEqual((fresh["assessment"], fresh["group"]), ("UNITS_INCONSISTENT", "UNRESOLVED"))
        self.assertFalse(sa.changed(fresh, records[0]))
        self.assertEqual(sa.unresolved_set_ids(paper.ledger_lines(self.path)), {sid})

    def test_case_4_earlier_artifact_tag_that_current_evidence_does_not_support(self):
        spec, sid = smx(), smx()["set_id"]
        cutoffs = {sid: "2026-11-11T14:30:00Z", aaa()["set_id"]: "2026-10-30T13:30:00Z"}
        # Tagged ARTIFACT_V11 on the night of the signal, before the entry cutoff of 2026-11-11.
        flag = split_flags.flag_record(spec, smx_own_pull(), "provider events in pull us_2026-11-10",
                                       "2026-11-10T22:10:00Z")
        self.assertEqual(flag["flag"], "ARTIFACT_V11")
        self.assertLess(flag["assessed_at"], cutoffs[sid])
        # Assessed on 2026-11-12, after the cutoff, from a later pull: REAL (case 1).
        new = sa.propose_assessments([spec], [], {"SMX": smx_later_pull()}, "pull us_2026-11-12",
                                     "2026-11-12T10:06:00Z", retrieved_on="2026-11-12")
        self.assertEqual([(r["assessment"], r["group"], r["pull_role"]) for r in new],
                         [("REAL_MOVE_AFTER_SPLIT", "REAL", "later")])
        records = self.write(*new)
        self.assertEqual(sa.verify(records=records, specs=[spec]), [])

        self.assertEqual(sa.removed_set_ids("corrected", records=records, v11_flags=[flag]), set())
        self.assertEqual(sa.removed_set_ids("at_the_time", records=records, v11_flags=[flag], cutoffs=cutoffs), {sid})

        rows = [row(aaa(), net=0.05), row(spec, owner="BUY", net=0.21)]
        v = paper_book_report.views(rows, records, [flag], cutoffs)
        self.assertEqual([r["ticker"] for r in v["as_frozen"]], ["AAA", "SMX"])
        self.assertEqual([r["ticker"] for r in v["corrected"]], ["AAA", "SMX"])
        self.assertEqual([r["ticker"] for r in v["at_the_time"]], ["AAA"])
        # In the corrected view's books, out of the at-the-time view's books. SMX is BUY_OK and confirmed BUY:
        # it belongs to KOD, ALL and OWNER. P&L at $1,000 a position: 50 + 210 = 260 with it, 50 without.
        for b, with_smx, without in (("KOD", 2, 1), ("ALL", 2, 1), ("OWNER", 1, 0), ("AVOIDED", 0, 0)):
            self.assertEqual(book.book_summary(v["corrected"], b)["positions"], with_smx, b)
            self.assertEqual(book.book_summary(v["at_the_time"], b)["positions"], without, b)
        self.assertAlmostEqual(book.book_summary(v["corrected"], "KOD")["pnl"], 260.0)
        self.assertAlmostEqual(book.book_summary(v["at_the_time"], "KOD")["pnl"], 50.0)

    def test_case_5_validation(self):
        spec, sid = govx(), govx()["set_id"]
        specs = [spec, smx()]
        # Two assessments for one set with a correct supersedes, both built by the module itself.
        first = sa.propose_assessments([spec], [], {"GOVX": govx_own_pull()}, "pull us_2026-11-11", T2,
                                       seal_session="2026-11-11")
        records = self.write(*first)
        second = sa.propose_reassessments([spec], records, {"GOVX": govx_later_pull()}, "pull us_2026-11-12", T4)
        self.assertEqual(len(second), 1)
        records = self.write(*second)
        self.assertEqual([r["set_id"] for r in records], [sid, sid])
        self.assertEqual(sa.verify(records=records, specs=specs), [])
        self.assertEqual(sa.verify(specs=specs), [])

        one, two = first[0], second[0]  # the unsealed records
        self.assertEqual(two["supersedes"], records[0]["record_hash"])
        # Each problem is one defect in a fresh ledger: a first record, and where needed a second record built
        # from the hash that the first record received in that ledger.
        problems = {
            "wrong supersedes": (one, lambda h: dict(two, supersedes="0" * 64)),
            "second seal record": (one, lambda h: dict(two, supersedes=h, pull_role="seal")),
            "unchanged reassessment": (one, lambda h: dict(one, pull_role="later", supersedes=h,
                                                           basis="pull us_2026-11-12", assessed_at=T4)),
            "unknown class": (dict(one, assessment="ARTIFACT_V11", group="ARTIFACT"), None),
            "wrong group": (dict(one, group="REAL"), None),
            "unknown set": (dict(one, set_id="US-NOPE-20261111"), None),
        }
        for name, (head, then) in problems.items():
            with self.subTest(name):
                self.path.unlink(missing_ok=True)
                lines = self.write(head)
                if then is not None:
                    lines = self.write(then(lines[0]["record_hash"]))
                self.assertTrue(sa.verify(records=lines, specs=specs), name)
                self.assertTrue(sa.verify(specs=specs), name)
        # The same rebuild without a defect is sound, so each failure above is the defect and not the rebuild.
        self.path.unlink(missing_ok=True)
        lines = self.write(one)
        lines = self.write(dict(two, supersedes=lines[0]["record_hash"]))
        self.assertEqual(sa.verify(records=lines, specs=specs), [])
        self.assertEqual(sa.verify(specs=specs), [])


if __name__ == "__main__":
    unittest.main()

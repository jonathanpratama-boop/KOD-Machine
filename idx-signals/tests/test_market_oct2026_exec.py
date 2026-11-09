"""Behaviour-level tests for the October 2026 IDX auto-rejection correction.

Scope (CONTRACT.md section 8): item 7 (exhaustive exact-rational oracle), item 10 (market-level lock
flips and the execution examples), item 8 (vector semantics, 2-D shapes), the property and
mixed-date parts of item 6 (the unconfirmed period) and an optional paper-ledger example.

Independence. Every expected value comes from SPEC_FINAL.md (market facts) or CONTRACT.md (the
interface). The oracle re-implements SPEC_FINAL section 5 with fractions.Fraction. Nothing here
imports tick_size, floor_tick, ceil_tick, band_pct, BANDS or TICK_BANDS from the code under test,
so the oracle is free to disagree with it.

Grades (SPEC_FINAL section 0). CONFIRMED and REPORTED facts live in separate classes. A cell of the
exhaustive comparison is REPORTED when its value rests on a reading the spec grades REPORTED: the
tick of the limit price's own band (U3: the cell would change if the tick of the reference's band
were used instead) or the ARB of a Rp1 reference (U4). Everything for dates after 2026-12-31 is a
modelling CONVENTION (CONTRACT section 3), not a rule, and lives in a class that says so.

Never asserted (CONTRACT section 6): any exchange rule for a date after 2026-12-31, any symmetric
lower limit, any ARB on 2026-10-19 for a reference of Rp11 to Rp14 (SPEC_FINAL U5), ETF, REIT, IPO,
rights or warrant limits, a last-session date, a holiday fact, or the order-volume rule together
with price limits. No raw price data, no network, and no test depends on another.

Periods used below: P1 = 2026-09-28 to 2026-10-18 (ARB 15% above Rp10), P2 = 2026-10-19 (ARB 7%),
P3 = 2026-10-20 to 2026-12-31 (ARB 7%, and a nominal Rp1 for references Rp11 to Rp14). The ARA is
the same in all three. Weekend dates are legal inputs: the rule follows the calendar date.
"""

import functools
import math
import unittest
import warnings
from fractions import Fraction

import numpy as np

from idxsig import market, paper
from idxsig.execution import STATUS, ExecConfig, Market, execute
from tests.support import flat_market, rebuild

OCT16, OCT19, OCT20, DEC31 = "2026-10-16", "2026-10-19", "2026-10-20", "2026-12-31"
THREE_DATES = (OCT16, OCT19, OCT20)

# ---------------------------------------------------------------------------------------------
# The oracle: SPEC_FINAL sections 2.1, 4 and 5, written out again with exact fractions.
# ---------------------------------------------------------------------------------------------

# (first price of the band, first price of the next band, tick): SPEC_FINAL section 4.
_TICK_TABLE = ((1, 200, 1), (200, 500, 2), (500, 2000, 5), (2000, 5000, 10), (5000, None, 25))
_TOP_REFERENCE = 600_000


def _tick_of(price):
    for _first, nxt, tick in _TICK_TABLE:
        if nxt is None or price < nxt:
            return tick
    raise AssertionError("the top band is open")


@functools.lru_cache(maxsize=None)
def _valid_references():
    """Every valid reference price from Rp1 to Rp600,000: a whole rupiah, a multiple of the tick of
    its own band (1..199 step 1, 200..498 step 2, 500..1995 step 5, 2000..4990 step 10, then 25)."""
    out = []
    for first, nxt, tick in _TICK_TABLE:
        top = _TOP_REFERENCE if nxt is None else nxt - tick
        out.extend(range(first, top + 1, tick))
    return tuple(out)


def _floor_to_grid(x):
    """The largest valid price at or below x (SPEC_FINAL section 5: how the ARA is rounded)."""
    x = Fraction(x)
    for first, _nxt, tick in reversed(_TICK_TABLE):
        if x >= first:
            return math.floor(x / tick) * tick
    raise ValueError(f"no valid price at or below {x}")


def _ceil_to_grid(x):
    """The smallest valid price at or above x (SPEC_FINAL section 5: how the ARB is rounded)."""
    x = Fraction(x)
    for first, nxt, tick in _TICK_TABLE:
        if nxt is None or x <= nxt - tick:
            return math.ceil(max(x, first) / tick) * tick
    raise AssertionError("the top band is open")


def _pct_up(ref):
    """ARA percentage by the band of the reference (section 2.1; Rp11-14 is inside the 35% band)."""
    if ref <= 200:
        return Fraction(35, 100)
    if ref <= 5000:
        return Fraction(25, 100)
    return Fraction(20, 100)


def _raw_limits(ref, period):
    """Unrounded (ARA, ARB) of an integer reference for one period (SPEC_FINAL section 2.1).

    Rp1-10 is a nominal Rp1 either way in every period. From P3 the ARB of Rp11-14 is also a
    nominal Rp1. For P2 and Rp11-14 the 7% formula is returned, but those cells are never judged
    (SPEC_FINAL U5): see _Oracle.unspecified_arb.
    """
    if ref <= 10:
        return Fraction(ref + 1), Fraction(ref - 1)
    ara_raw = ref * (1 + _pct_up(ref))
    if period == "P3" and ref <= 14:
        return ara_raw, Fraction(ref - 1)
    down = Fraction(15, 100) if period == "P1" else Fraction(7, 100)
    return ara_raw, ref * (1 - down)


def _oracle_pair(ref, period):
    """(ARA, ARB) of an integer reference: floor / ceil onto the valid-price grid, minimum Rp1."""
    ara_raw, arb_raw = _raw_limits(ref, period)
    return _floor_to_grid(ara_raw), max(1, _ceil_to_grid(arb_raw))


def _limit_from_pct(side, ref, pct):
    """One limit for a percentage row (used for the observed anchors of SPEC_FINAL section 8)."""
    pct = Fraction(pct, 100)
    if side == "ara":
        return _floor_to_grid(ref * (1 + pct))
    return max(1, _ceil_to_grid(ref * (1 - pct)))


class _Oracle:
    """Exact limits of every valid reference for one period, and the grade of every cell.

    A cell (reference, side) is REPORTED when rounding with the tick of the reference's own band,
    instead of the tick of the limit's band, would give a different number (U3), or when it is the
    ARB of Rp1 (U4). Otherwise it is CONFIRMED. The ARB cells of Rp11-14 in P2 are in neither
    group (U5): nothing is asserted about them.
    """

    def __init__(self, period):
        refs = _valid_references()
        size = len(refs)
        self.period = period
        self.refs = np.array(refs, dtype=float)
        self.ara = np.empty(size)
        self.arb = np.empty(size)
        ara_reading = np.zeros(size, dtype=bool)
        arb_reading = np.zeros(size, dtype=bool)
        for i, ref in enumerate(refs):
            ara_raw, arb_raw = _raw_limits(ref, period)
            self.ara[i] = _floor_to_grid(ara_raw)
            self.arb[i] = max(1, _ceil_to_grid(arb_raw))
            tick = _tick_of(ref)  # the rejected reading: the reference's own tick
            ara_reading[i] = self.ara[i] != math.floor(ara_raw / tick) * tick
            arb_reading[i] = self.arb[i] != max(1, math.ceil(arb_raw / tick) * tick)
        is_one = self.refs == 1
        self.unspecified_arb = np.zeros(size, dtype=bool)
        if period == "P2":
            self.unspecified_arb = (self.refs >= 11) & (self.refs <= 14)
        keep = ~self.unspecified_arb
        self._cells = {
            ("confirmed", "ara"): ~ara_reading,
            ("confirmed", "arb"): ~arb_reading & ~is_one & keep,
            ("reported", "ara"): ara_reading,
            ("reported", "arb"): (arb_reading | is_one) & keep,
        }

    def cells(self, grade, side):
        return self._cells[(grade, side)]

    def index(self, ref):
        i = int(np.searchsorted(self.refs, ref))
        if i >= len(self.refs) or self.refs[i] != ref:
            raise KeyError(f"{ref} is not a valid reference price")
        return i


@functools.lru_cache(maxsize=None)
def _oracle(period):
    return _Oracle(period)


def _period_of(day):
    """The period of a calendar day for the dates this file uses (CONTRACT section 1), else None."""
    d = np.datetime64(day, "D")
    if np.datetime64("2026-09-28") <= d <= np.datetime64("2026-10-18"):
        return "P1"
    if d == np.datetime64("2026-10-19"):
        return "P2"
    if np.datetime64("2026-10-20") <= d <= np.datetime64("2026-12-31"):
        return "P3"
    return None


def _step_up(price):
    """The next valid price above a valid price."""
    return price + _tick_of(price)


def _step_down(price):
    """The next valid price below a valid price (0 below Rp1)."""
    return price - _tick_of(price - 1)


def _limits_quiet(ref, days):
    """limits() with warnings silenced: callers that compare values do not care about them."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ara, arb = market.limits(ref, days)
    return np.asarray(ara), np.asarray(arb)


def _code_limits(day, refs):
    """limits() for every reference of `refs` on one calendar day (same-shape date array)."""
    return _limits_quiet(refs, np.full(refs.shape, np.datetime64(day, "D")))


def _examples(refs, got, want, bad, limit=5, want_label="oracle"):
    """The first few disagreements, spelled out."""
    return "; ".join(
        f"ref {refs[i]:,.0f}: limits() {got[i]:,.0f}, {want_label} {want[i]:,.0f}"
        for i in np.flatnonzero(bad)[:limit]
    )


def _no_problems(case, problems, what):
    """Fail with a short, readable message (not a long list diff) when `problems` is not empty."""
    if problems:
        case.fail(f"{len(problems)} {what}. First: " + "; ".join(problems[:5]))


# ---------------------------------------------------------------------------------------------
# Synthetic markets
# ---------------------------------------------------------------------------------------------


def _market_from_cases(
    cases,
    days,
    *,
    one_price=False,
    volume=1_000_000.0,
    present=True,
    price_limits=True,
    quiet=True,
):
    """A Market of len(cases) tickers over `days`; each ticker repeats its (reference, close) pair
    in every session. The default bars are regular (high above low), so only the regular-board
    limit applies; one_price=True makes high == low == close, the case the thin-bar rule is about.
    quiet=False lets warnings through, for the tests that look for them."""
    n_days = len(days)
    ref = np.repeat(np.array([[c[0]] for c in cases], dtype=float), n_days, axis=1)
    close = np.repeat(np.array([[c[1]] for c in cases], dtype=float), n_days, axis=1)
    if one_price:
        high, low = close.copy(), close.copy()
    else:
        high, low = np.maximum(ref, close) + 1.0, np.minimum(ref, close)
    traded = np.full(close.shape, float(volume))
    with warnings.catch_warnings():
        if quiet:
            warnings.simplefilter("ignore")
        return Market.build(
            np.array([f"T{i:03d}" for i in range(len(cases))]),
            np.array(days, dtype="datetime64[D]"),
            close,
            ref,
            high,
            low,
            traded,
            traded * close,
            np.full(close.shape, bool(present)),
            price_limits=price_limits,
        )


def _flags(ref, close, day, **kwargs):
    """(lock_up, lock_down) of one bar on one day, exactly as Market.build derives them."""
    m = _market_from_cases([(ref, close)], [day], **kwargs)
    return bool(m.lock_up[0, 0]), bool(m.lock_down[0, 0])


def _up(ref, close, day, **kwargs):
    return _flags(ref, close, day, **kwargs)[0]


def _down(ref, close, day, **kwargs):
    return _flags(ref, close, day, **kwargs)[1]


class _FlagAssertions:
    """Readable assertions on the lock flags of one bar. Not a test case itself."""

    def _check_flag(self, side, expected, ref, close, day, label, kwargs):
        if (_up if side == "up" else _down)(ref, close, day, **kwargs) == expected:
            return
        bar = "".join(f", {key}={value}" for key, value in kwargs.items())
        prefix = f"{label}: " if label else ""
        self.fail(
            f"{prefix}a close of {close} from a reference of {ref} on {day}{bar} should "
            f"{'be' if expected else 'not be'} locked {side}"
        )

    def assert_locked_down(self, ref, close, day, label="", **kwargs):
        self._check_flag("down", True, ref, close, day, label, kwargs)

    def assert_not_locked_down(self, ref, close, day, label="", **kwargs):
        self._check_flag("down", False, ref, close, day, label, kwargs)

    def assert_locked_up(self, ref, close, day, label="", **kwargs):
        self._check_flag("up", True, ref, close, day, label, kwargs)

    def assert_not_locked_up(self, ref, close, day, label="", **kwargs):
        self._check_flag("up", False, ref, close, day, label, kwargs)


def _synthetic_market(start, price, closes, step, volume=1_000_000.0):
    """One ticker, one session per entry of `closes`, on consecutive weekdays from `start`. Each
    session's reference is the previous close and every bar is regular (high above low)."""
    tickers, dates, arrays = flat_market(
        n_tickers=1, n_sessions=len(closes), price=price, volume=volume, start=start
    )
    prev = [closes[0], *closes[:-1]]
    for j, close in enumerate(closes):
        arrays["close"][0, j] = close
        arrays["prev"][0, j] = prev[j]
        arrays["high"][0, j] = max(prev[j], close) + step
        arrays["low"][0, j] = min(prev[j], close)
    return rebuild(tickers, dates, arrays)


def _exit_example(start, price, closes, step, holding=3, volume=1_000_000.0):
    """One long trade through execute(): signal on session 0, entry at the close of session 1,
    sale due at the close of session 1 + holding."""
    m = _synthetic_market(start, price, closes, step, volume)
    out = execute(m, np.array([0]), np.array([0]), ExecConfig(holding_days=holding))
    return m, {key: value[0] for key, value in out.items()}


def _net(entry, exit_price):
    """Net return of a flat-fee round trip: 0.15% to buy, 0.25% to sell (the default Fees)."""
    return exit_price * (1 - 0.0025) / (entry * (1 + 0.0015)) - 1


def _ledger_decision(signal_session, close):
    """A paper decision of the v3 shape that paper.score() reads: BUY ON TRIGGER on the next
    close, a stop 15% below the signal close, no more than 10% chase."""
    return {
        "decision_id": "synthetic-1",
        "decision": "BUY ON TRIGGER",
        "market": "IDX",
        "instrument": {"ticker": "T000"},
        "signal_session": signal_session,
        "verified_price": {"close": close},
        "plan": {"invalidation": 850.0, "max_chase_price": 1100.0},
    }


# ---------------------------------------------------------------------------------------------
# Item 7: the exhaustive exact oracle
# ---------------------------------------------------------------------------------------------


# SPEC_FINAL section 7.2: (reference, ARA, ARB in P1, ARB in P2, ARB in P3). None marks the cells
# the spec does not assert (U5). 201 and 5001 are the spec's daggered references (not valid prices).
_SPEC_ROWS = (
    (1, 2, 1, 1, 1),
    (2, 3, 1, 1, 1),
    (10, 11, 9, 9, 9),
    (11, 14, 10, None, 10),
    (12, 16, 11, None, 11),
    (13, 17, 12, None, 12),
    (14, 18, 12, None, 13),
    (15, 20, 13, 14, 14),
    (16, 21, 14, 15, 15),
    (17, 22, 15, 16, 16),
    (20, 27, 17, 19, 19),
    (25, 33, 22, 24, 24),
    (50, 67, 43, 47, 47),
    (100, 135, 85, 93, 93),
    (199, 268, 170, 186, 186),
    (200, 270, 170, 186, 186),
    (201, 250, 171, 187, 187),
    (202, 252, 172, 188, 188),
    (500, 625, 426, 466, 466),
    (505, 630, 430, 470, 470),
    (1000, 1250, 850, 930, 930),
    (1995, 2490, 1700, 1860, 1860),
    (2000, 2500, 1700, 1860, 1860),
    (4990, 6225, 4250, 4650, 4650),
    (5000, 6250, 4250, 4650, 4650),
    (5001, 6000, 4260, 4660, 4660),
    (5025, 6025, 4280, 4680, 4680),
    (10000, 12000, 8500, 9300, 9300),
)

# The cells of those rows that the spec itself grades REPORTED: the own-band tick rows (U3, named in
# the text under section 7.2) and the ARB of Rp1 (U4). Every other cell is CONFIRMED.
_SPEC_REPORTED = frozenset({(1, "arb"), (500, "arb"), (4990, "ara"), (5001, "arb"), (5025, "arb")})

# SPEC_FINAL section 8: (label, side, reference, percentage row, observed limit price).
_ANCHORS = (
    ("GOTO/PADI/RBMS 2026-09-28", "arb", 50, 15, 43),
    ("GOTO 2026-10-19", "arb", 25, 7, 24),
    ("TLKM 2026-10-19", "arb", 1900, 7, 1770),
    ("BBCA 2026-10-19", "arb", 5175, 7, 4820),
    ("AMMN 2026-10-19", "arb", 3740, 7, 3480),
    ("MORA 2026-10-19", "arb", 3910, 7, 3640),
    ("BYAN 2026-10-19", "arb", 11150, 7, 10375),
    ("BBCA 2026-10-16", "arb", 6075, 15, 5175),
    ("AKSI 2025-10-21", "ara", 302, 25, 376),
    ("FITT 2025-10-21", "ara", 835, 25, 1040),
    ("COCO 2025-10-21", "ara", 246, 25, 306),
    ("WAPO 2025-10-21", "ara", 234, 25, 292),
    ("BABY 2025-10-21", "ara", 430, 25, 535),
    ("COCO 2025-10-22", "ara", 306, 25, 382),
    ("TEBE 2025-10-22", "ara", 1930, 25, 2410),
    ("NIRO 2025-10-22", "ara", 163, 35, 220),
    ("AYLS 2025-10-22", "ara", 175, 35, 236),
    ("PPRE 2025-10-22", "ara", 86, 35, 116),
    ("PGUN 2025-10-22", "ara", 12525, 20, 15025),
    ("RISE 2025-10-22", "ara", 7300, 20, 8750),
)
# The one anchor whose observed price tells the own-band tick from the reference-band tick (U3).
_OWN_BAND_ANCHOR = "BBCA 2026-10-19"


def _spec_cells(reported):
    """(reference, side, period, expected) for the spec's section 7.2 cells of one grade."""
    out = []
    for ref, ara, arb1, arb2, arb3 in _SPEC_ROWS:
        for side, period, want in (
            ("ara", "P1", ara),
            ("ara", "P2", ara),
            ("ara", "P3", ara),
            ("arb", "P1", arb1),
            ("arb", "P2", arb2),
            ("arb", "P3", arb3),
        ):
            if want is not None and ((ref, side) in _SPEC_REPORTED) == reported:
                out.append((ref, side, period, want))
    return out


def _spec_cell_problems(reported):
    """Disagreements between the oracle and the spec's section 7.2 cells of one grade."""
    problems = []
    for ref, side, period, want in _spec_cells(reported):
        got = _oracle_pair(ref, period)[0 if side == "ara" else 1]
        if got != want:
            problems.append(f"{period} ref {ref} {side.upper()}: oracle {got}, spec {want}")
    return problems


def _grade_problems(reported):
    """Spec cells (valid references only) that the oracle's cell partition files under the wrong
    grade: a CONFIRMED spec cell must be judged in the CONFIRMED class, a REPORTED one in the
    REPORTED class."""
    grade = "reported" if reported else "confirmed"
    problems = []
    valid = set(_valid_references())
    for ref, side, period, _want in _spec_cells(reported):
        if ref in valid:
            oracle = _oracle(period)
            if not oracle.cells(grade, side)[oracle.index(ref)]:
                problems.append(f"{period} ref {ref} {side.upper()} is not in the {grade} class")
    return problems


def _anchor_problems(anchors):
    problems = []
    for label, side, ref, pct, observed in anchors:
        got = _limit_from_pct(side, ref, pct)
        if got != observed:
            problems.append(f"{label}: oracle {got}, observed {observed}")
    return problems


class OracleReproducesTheSpecTables(unittest.TestCase):
    """CONFIRMED: the oracle against SPEC_FINAL's own printed numbers. The code under test is not
    involved. Section 7.2 cells the spec grades REPORTED, and the one anchor that tells the two
    tick readings apart, are in the next class.

    Guards against: a faulty oracle. When this class passes and an exhaustive comparison fails,
    the fault is in the code under test (or in the spec), not in the oracle that judged it.
    """

    def test_oracle_reproduces_the_confirmed_cells_of_spec_section_7_2(self):
        """Guards against: an oracle that disagrees with the spec's own worked arithmetic, for
        every cell of the table except the REPORTED ones (U3, U4) and the P2 cells of U5."""
        _no_problems(
            self, _spec_cell_problems(reported=False), "oracle values differ from SPEC_FINAL 7.2"
        )

    def test_the_confirmed_cells_of_spec_section_7_2_are_judged_in_the_confirmed_class(self):
        """Guards against: the oracle's cell partition demoting a cell the spec calls CONFIRMED
        to REPORTED, which would take it out of the CONFIRMED comparison."""
        _no_problems(self, _grade_problems(reported=False), "cells filed under the wrong grade")

    def test_oracle_reproduces_the_observed_anchors_of_spec_section_8(self):
        """Guards against: an oracle whose rounding direction contradicts the observed limit
        prices (floor for the ARA, ceil for the ARB). 19 of the 20 anchors; the 20th is in the
        REPORTED class because it is the one that discriminates the tick reading."""
        anchors = [row for row in _ANCHORS if row[0] != _OWN_BAND_ANCHOR]
        self.assertEqual(len(anchors), 19)
        _no_problems(self, _anchor_problems(anchors), "oracle values differ from observed prices")

    def test_enumeration_is_the_tick_grid_from_rp1_to_rp600000(self):
        """Guards against: an enumeration that skips valid references or includes invalid ones."""
        refs = _valid_references()
        self.assertEqual(len(refs), 199 + 150 + 300 + 300 + 23_801)
        self.assertEqual((refs[0], refs[-1]), (1, 600_000))
        for price in (199, 200, 202, 498, 500, 505, 1995, 2000, 4990, 5000, 5025, 600_000):
            self.assertIn(price, refs)
        for price in (201, 499, 501, 1996, 4995, 5001, 5010, 600_001):
            self.assertNotIn(price, refs)

    def test_every_cell_is_judged_exactly_once(self):
        """Guards against: a cell dropped from both the CONFIRMED and the REPORTED comparison, or
        judged twice, which would make the two classes below prove less than they say."""
        for period in ("P1", "P2", "P3"):
            oracle = _oracle(period)
            for side in ("ara", "arb"):
                confirmed = oracle.cells("confirmed", side)
                reported = oracle.cells("reported", side)
                skipped = oracle.unspecified_arb if side == "arb" else np.zeros_like(confirmed)
                self.assertFalse((confirmed & reported).any(), f"{period} {side}")
                self.assertFalse(((confirmed | reported) & skipped).any(), f"{period} {side}")
                self.assertTrue((confirmed | reported | skipped).all(), f"{period} {side}")
        self.assertEqual(int(_oracle("P2").unspecified_arb.sum()), 4)  # Rp11, 12, 13, 14


class OracleReproducesTheReportedSpecRows(unittest.TestCase):
    """REPORTED: the oracle against the numbers the spec grades REPORTED: the own-band tick rows
    of section 7.2 (reference 500, 4,990, 5,001 and 5,025; U3), the ARB of Rp1 (U4), and the BBCA
    anchor of 2026-10-19 (reference 5,175, observed ARB 4,820, not 4,825), the observation that
    supports the own-band tick choice. The code under test is not involved.

    Guards against: a faulty oracle on exactly the cells where the two readings of U3 differ.
    """

    def test_oracle_reproduces_the_reported_cells_of_spec_section_7_2(self):
        """Guards against: an oracle that rounds with the reference's own tick, or that does not
        floor the ARB of Rp1 at the Rp1 minimum price."""
        _no_problems(
            self, _spec_cell_problems(reported=True), "oracle values differ from SPEC_FINAL 7.2"
        )

    def test_the_reported_cells_of_spec_section_7_2_are_judged_in_the_reported_class(self):
        """Guards against: the oracle's cell partition missing a cell the spec calls REPORTED,
        which would leave it in the CONFIRMED comparison."""
        _no_problems(self, _grade_problems(reported=True), "cells filed under the wrong grade")

    def test_oracle_reproduces_the_bbca_anchor_that_tells_the_two_tick_readings_apart(self):
        """Guards against: an oracle that returns Rp4,825 (the reference's tick, 25) where the
        exchange closed BBCA at Rp4,820 (the limit's own tick, 10) on 2026-10-19."""
        anchors = [row for row in _ANCHORS if row[0] == _OWN_BAND_ANCHOR]
        self.assertEqual(len(anchors), 1)
        _no_problems(self, _anchor_problems(anchors), "oracle values differ from observed prices")


class _OracleComparison:
    """Shared by the two exhaustive comparison classes. Not a test case itself."""

    grade = ""

    def compare(self, day, side):
        oracle = _oracle(_period_of(day))
        ara, arb = _code_limits(day, oracle.refs)
        got, want = (ara, oracle.ara) if side == "ara" else (arb, oracle.arb)
        judged = oracle.cells(self.grade, side)
        bad = judged & (got != want)
        if bad.any():
            self.fail(
                f"{int(bad.sum())} of {int(judged.sum())} {self.grade} {side.upper()} cells "
                f"disagree with the exact oracle on {day}. First: "
                + _examples(oracle.refs, got, want, bad)
            )


class ExactOracleConfirmedCells(_OracleComparison, unittest.TestCase):
    """CONFIRMED cells: limits() against the exact oracle for every valid reference from Rp1 to
    Rp600,000, 24,750 prices. A cell is CONFIRMED unless it depends on the own-band tick reading
    (U3), on the ARB of Rp1 (U4), or is the P2 ARB of Rp11-14 (U5, never judged).

    Guards against: any reference price, in any band, on any edge, whose limit differs from the
    rule the exchange published, while the hand-picked cases of the other tests pass.
    """

    grade = "confirmed"

    def test_ara_on_2026_10_16(self):
        """Guards against: the regime before the correction (P1) losing its ARA."""
        self.compare(OCT16, "ara")

    def test_arb_on_2026_10_16(self):
        """Guards against: the 15% ARB of the regime before the correction (P1) changing."""
        self.compare(OCT16, "arb")

    def test_ara_on_2026_10_19(self):
        """Guards against: the correction touching the ARA on its first day (P2)."""
        self.compare(OCT19, "ara")

    def test_arb_on_2026_10_19(self):
        """Guards against: the 7% ARB of 2026-10-19 (P2) missing, for any reference above Rp10
        except Rp11-14 (U5)."""
        self.compare(OCT19, "arb")

    def test_ara_on_2026_10_20(self):
        """Guards against: the correction touching the ARA from 2026-10-20 (P3)."""
        self.compare(OCT20, "ara")

    def test_arb_on_2026_10_20(self):
        """Guards against: the P3 ARB: 7% above Rp14 and a nominal Rp1 for Rp11-14."""
        self.compare(OCT20, "arb")

    def test_ara_on_2026_12_31(self):
        """Guards against: the last confirmed calendar date (P3) losing its ARA."""
        self.compare(DEC31, "ara")

    def test_arb_on_2026_12_31(self):
        """Guards against: the P3 rule ending one day early, so 2026-12-31 gets another ARB."""
        self.compare(DEC31, "arb")


class ExactOracleReportedCells(_OracleComparison, unittest.TestCase):
    """REPORTED cells: the cells of the same exhaustive comparison whose value rests on a reading
    the spec grades REPORTED. These are the cells where rounding with the tick of the reference's
    band would differ from rounding with the tick of the limit's own band (U3; for example
    reference 500 under 7%: ARB 466, not 465; reference 4,990: ARA 6,225, not 6,230), and the ARB
    of a Rp1 reference, which the Rp1 minimum price turns from 0 into 1 (U4).

    Guards against: a rounding that uses the tick of the reference's band, which returns prices
    that are not valid prices on the tick table (SPEC_FINAL section 5, U3).
    """

    grade = "reported"

    def test_ara_on_2026_10_16(self):
        """Guards against: the own-band tick choice breaking for the ARA before the correction."""
        self.compare(OCT16, "ara")

    def test_arb_on_2026_10_16(self):
        """Guards against: the own-band tick choice (and the Rp1 floor) breaking in P1."""
        self.compare(OCT16, "arb")

    def test_ara_on_2026_10_19(self):
        """Guards against: the own-band tick choice breaking for the ARA in P2."""
        self.compare(OCT19, "ara")

    def test_arb_on_2026_10_19(self):
        """Guards against: a reference-band tick used for the 7% ARB of P2."""
        self.compare(OCT19, "arb")

    def test_ara_on_2026_10_20(self):
        """Guards against: the own-band tick choice breaking for the ARA in P3."""
        self.compare(OCT20, "ara")

    def test_arb_on_2026_10_20(self):
        """Guards against: a reference-band tick used for the 7% ARB of P3."""
        self.compare(OCT20, "arb")

    def test_ara_on_2026_12_31(self):
        """Guards against: the own-band tick choice breaking for the ARA on the last date."""
        self.compare(DEC31, "ara")

    def test_arb_on_2026_12_31(self):
        """Guards against: a reference-band tick used for the ARB on the last date."""
        self.compare(DEC31, "arb")


# ---------------------------------------------------------------------------------------------
# Item 10: market-level flips, observed closes, the thin-bar rule
# ---------------------------------------------------------------------------------------------


class LowerLimitFlipsAtMarketLevel(_FlagAssertions, unittest.TestCase):
    """CONFIRMED: which closes Market.build flags as locked at the lower limit, with regular
    (not one-price) bars so that only the regular-board limit decides. 2026-10-16 is under the
    15% regime; 2026-10-19 and 2026-10-20 are under the 7% regime, and from the 20th Rp11-14 moves
    by one rupiah. SPEC_FINAL U5 is respected: no test here asserts a Rp11-14 lower limit on
    2026-10-19.

    Guards against: a correction that changes the limit table but not the lock flags the execution
    model reads, or that changes more flags than the table does.
    """

    def test_1000_to_930_is_not_locked_on_2026_10_16(self):
        """Guards against: the old 15% limit (Rp850) being replaced before 2026-10-19. A fall of
        7% from a reference of Rp1,000 is Rp930, well above Rp850."""
        self.assert_not_locked_down(1000, 930, OCT16)

    def test_1000_to_930_is_locked_on_2026_10_19(self):
        """Guards against: the 7% limit missing on its first day. 1,000 x 0.93 = 930, so a close
        of Rp930 sits exactly on the lower limit and counts as locked."""
        self.assert_locked_down(1000, 930, OCT19)

    def test_1000_to_930_is_locked_on_2026_10_20(self):
        """Guards against: the 7% limit being lost when the Rp11-14 amendment takes effect."""
        self.assert_locked_down(1000, 930, OCT20)

    def test_1000_to_931_is_not_locked_on_any_of_the_three_dates(self):
        """Guards against: a lower limit set too high, so a close just above Rp930 locks. Rp931 is
        the contract's example (it is not a valid price: Rp935 is the next one, tested too)."""
        for day in THREE_DATES:
            self.assert_not_locked_down(1000, 931, day)
            self.assert_not_locked_down(1000, 935, day)

    def test_1000_to_900_is_not_locked_on_2026_10_16(self):
        """Guards against: a close 10% below the reference locking a regular bar in the 15%
        regime. The lower limit is Rp850; only a one-price bar locks at Rp900 (thin-bar rule)."""
        self.assert_not_locked_down(1000, 900, OCT16)

    def test_1000_to_900_is_locked_on_2026_10_19_and_2026_10_20(self):
        """Guards against: a close 10% below the reference escaping the 7% limit (Rp930)."""
        self.assert_locked_down(1000, 900, OCT19)
        self.assert_locked_down(1000, 900, OCT20)

    def test_1000_to_850_is_locked_on_2026_10_16(self):
        """Guards against: the 15% limit of the old regime no longer locking on 2026-10-16."""
        self.assert_locked_down(1000, 850, OCT16)
        self.assert_not_locked_down(1000, 855, OCT16)

    def test_14_to_13_is_not_locked_on_2026_10_16(self):
        """Guards against: the Rp1 rule for Rp11-14 applying before 2026-10-20. Under the 15% limit
        14 x 0.85 = 11.9 rounds up to Rp12, so a close of Rp13 can still be sold."""
        self.assert_not_locked_down(14, 13, OCT16)

    def test_14_to_13_is_locked_on_2026_10_20(self):
        """Guards against: the Rp1 rule for Rp11-14 missing. From 2026-10-20 the lower limit of a
        Rp14 reference is Rp14 - 1 = Rp13, so a close of Rp13 is locked."""
        self.assert_locked_down(14, 13, OCT20)

    def test_12_to_11_is_locked_on_both_2026_10_16_and_2026_10_20(self):
        """Guards against: the Rp11-14 amendment changing a case where both rules agree. For a
        reference of Rp12 the 15% rule gives Rp11 (10.2 rounds up) and the Rp1 rule gives
        Rp12 - 1 = Rp11, so Rp11 is locked either way (2026-10-19 is left out: SPEC_FINAL U5)."""
        self.assert_locked_down(12, 11, OCT16)
        self.assert_locked_down(12, 11, OCT20)

    def test_rp11_to_rp14_closes_follow_the_oracle_on_oct16_oct20_and_dec31(self):
        """Guards against: any Rp11-14 reference, at any close up to four rupiah below it,
        flagged differently from the oracle on the 15% date (2026-10-16) and the Rp1 dates
        (2026-10-20, 2026-12-31). 2026-10-19 is left out on purpose (SPEC_FINAL U5)."""
        problems = []
        for day in (OCT16, OCT20, DEC31):
            for ref in (11, 12, 13, 14):
                _ara, arb = _oracle_pair(ref, _period_of(day))
                for close in range(max(1, ref - 4), ref + 1):
                    want = close < ref and close <= arb
                    if _down(ref, close, day) != want:
                        problems.append(f"{day} ref {ref} close {close}: expected locked={want}")
        _no_problems(self, problems, "Rp11-14 lock flags disagree with the oracle")

    def test_flips_hold_through_2026_12_31(self):
        """Guards against: the correction ending before its last confirmed calendar date. On
        2026-12-31 a close of Rp930 from Rp1,000 and Rp13 from Rp14 are locked, Rp935 is not."""
        self.assert_locked_down(1000, 930, DEC31)
        self.assert_not_locked_down(1000, 935, DEC31)
        self.assert_locked_down(14, 13, DEC31)
        self.assert_locked_down(12, 11, DEC31)

    def test_rp1_to_rp10_band_does_not_change_between_the_dates(self):
        """Guards against: the nominal Rp1 band (references Rp2 to Rp10) being moved by the
        percentage change: the limit stays reference - 1 on every date, so a fall of one rupiah
        locks and an unchanged close does not. Reference 1 is left to the REPORTED classes (U4)."""
        for day in (OCT16, OCT19, OCT20, DEC31):
            for ref in range(2, 11):
                self.assert_locked_down(ref, ref - 1, day)
                self.assert_not_locked_down(ref, ref, day)

    def test_a_bar_that_did_not_trade_is_not_locked(self):
        """Guards against: lock flags set on a bar that never traded (no volume, or not present).
        The traded twin of each bar is locked, so a missing lock cannot hide behind the old rule."""
        for day, ref, close in ((OCT19, 1000, 930), (OCT20, 1000, 930), (OCT20, 14, 13)):
            self.assert_locked_down(ref, close, day)
            self.assert_not_locked_down(ref, close, day, volume=0.0)
            self.assert_not_locked_down(ref, close, day, present=False)


class UnchangedBehaviourAtMarketLevel(_FlagAssertions, unittest.TestCase):
    """CONFIRMED regression guards: what the correction must leave alone. The upper limit on every
    date, and the 15% rule through 2026-10-18 including the weekend dates.

    Guards against: a correction that spills over into the ARA side or into the days before it.
    """

    def test_1000_to_1250_is_locked_up_on_every_date(self):
        """Guards against: the ARA (1,000 x 1.25 = 1,250) moving. A close on it is locked up."""
        for day in (*THREE_DATES, DEC31):
            self.assert_locked_up(1000, 1250, day)

    def test_1000_to_1245_is_not_locked_up_on_any_date(self):
        """Guards against: the ARA being lowered, so a close just under it locks."""
        for day in (*THREE_DATES, DEC31):
            self.assert_not_locked_up(1000, 1245, day)

    def test_14_to_18_is_locked_up_and_17_is_not(self):
        """Guards against: the Rp11-14 amendment touching the ARA of that band: 14 x 1.35 = 18.9
        floors to Rp18 on every date."""
        for day in (*THREE_DATES, DEC31):
            self.assert_locked_up(14, 18, day)
            self.assert_not_locked_up(14, 17, day)

    def test_one_price_bar_at_the_special_board_upper_limit_is_locked_up(self):
        """Guards against: the thin-bar rule losing its upper side. A one-price bar 10% above the
        reference is locked up on every date (the special-board limit), a regular bar is not."""
        for day in (*THREE_DATES, DEC31):
            self.assert_locked_up(1000, 1100, day, one_price=True)
            self.assert_not_locked_up(1000, 1100, day)

    def test_15_percent_rule_holds_from_2026_09_28_through_2026_10_18(self):
        """Guards against: the 7% rule starting early, on 2026-10-17 or 2026-10-18 (weekend dates
        are legal inputs and still belong to the old rule) or on any date before the 19th."""
        for day in ("2026-09-28", "2026-10-15", OCT16, "2026-10-17", "2026-10-18"):
            self.assert_not_locked_down(1000, 930, day)
            self.assert_not_locked_down(1000, 855, day)
            self.assert_locked_down(1000, 850, day)
            self.assert_not_locked_down(14, 13, day)
            self.assert_locked_down(14, 12, day)


# Closes sampled around the limits of each sweep reference. The references are valid prices from
# every band and every edge of the tick table; those with a REPORTED-grade cell are filtered out.
_SWEEP_CANDIDATES = (
    2, 3, 9, 10, 15, 16, 17, 20, 25, 50, 99, 100, 101, 150, 199, 200, 202, 250, 400, 498, 500, 505,
    1000, 1005, 1600, 1995, 2000, 2010, 4000, 4990, 5000, 5025, 10_000, 100_000, 600_000,
)  # fmt: skip
_GRID_DAYS = (OCT16, OCT19, OCT20, DEC31)


def _clean_sweep_references():
    """Sweep references whose ARA and ARB are CONFIRMED-grade in P1, P2 and P3."""
    chosen = []
    for ref in _SWEEP_CANDIDATES:
        clean = True
        for period in ("P1", "P2", "P3"):
            oracle = _oracle(period)
            i = oracle.index(ref)
            clean &= bool(oracle.cells("confirmed", "ara")[i])
            clean &= bool(oracle.cells("confirmed", "arb")[i])
        if clean:
            chosen.append(ref)
    return chosen


def _closes_around(ref):
    """Valid closes one step below, on and one step above the reference and each of its limits."""
    old_arb = _oracle_pair(ref, "P1")[1]
    new_ara, new_arb = _oracle_pair(ref, "P3")
    limits = {ref, old_arb, new_arb, new_ara}
    closes = set()
    for price in limits:
        closes.update({_step_down(price), price, _step_up(price)})
    return sorted(close for close in closes if close >= 1)


class MarketFlagsAgainstTheOracle(unittest.TestCase):
    """CONFIRMED cells: every lock flag of a 2-D (tickers, sessions) market against the oracle.

    Each ticker is one (reference, close) pair repeated over four dates (2026-10-16, 10-19,
    10-20, 12-31); the closes sit one valid step below, on and above the reference and each limit.
    A regular bar is locked up when close >= ARA, and locked down when close < reference and
    close <= ARB (CONTRACT section 4). References with a REPORTED-grade cell, and Rp11-14, are not
    in the sweep (Rp11-14 has its own test above).

    Guards against: a lock flag that disagrees with the limit table at any band edge, in either
    direction, on any of the dates, in the 2-D layout Market.build uses.
    """

    @classmethod
    def setUpClass(cls):
        cls.refs = _clean_sweep_references()
        cls.cases = [(ref, close) for ref in cls.refs for close in _closes_around(ref)]
        cls.market = _market_from_cases(cls.cases, _GRID_DAYS)

    def _expected(self, side):
        want = np.zeros((len(self.cases), len(_GRID_DAYS)), dtype=bool)
        for j, day in enumerate(_GRID_DAYS):
            period = _period_of(day)
            pairs = {ref: _oracle_pair(ref, period) for ref in self.refs}
            for i, (ref, close) in enumerate(self.cases):
                ara, arb = pairs[ref]
                want[i, j] = close >= ara if side == "up" else (close < ref and close <= arb)
        return want

    def _check(self, side, got):
        want = self._expected(side)
        bad = np.argwhere(got != want)
        if len(bad):
            shown = "; ".join(
                f"ref {self.cases[i][0]} close {self.cases[i][1]} on {_GRID_DAYS[j]}: "
                f"expected {bool(want[i, j])}"
                for i, j in bad[:5]
            )
            self.fail(
                f"{len(bad)} of {want.size} lock_{side} flags disagree with the oracle: {shown}"
            )

    def test_the_sweep_covers_every_band_and_both_sides_of_each_limit(self):
        """Guards against: a sweep that quietly shrinks to a few easy references."""
        self.assertGreaterEqual(len(self.refs), 25)
        for low, high in ((1, 199), (200, 499), (500, 1999), (2000, 4999), (5000, 10**9)):
            self.assertTrue(any(low <= ref <= high for ref in self.refs), (low, high))
        self.assertEqual(self.market.lock_down.shape, (len(self.cases), len(_GRID_DAYS)))
        self.assertEqual(self.market.lock_down.dtype, np.dtype(bool))
        self.assertTrue(self.market.tradeable.all())

    def test_lock_down_matches_the_oracle_arb_on_every_date(self):
        """Guards against: a wrong lower-limit lock for any sampled close, on the 15% date, the
        2026-10-19 date, the 2026-10-20 date or 2026-12-31."""
        self._check("down", self.market.lock_down)

    def test_lock_up_matches_the_oracle_ara_on_every_date(self):
        """Guards against: the upper-limit lock changing on any date. It must not: the ARA side is
        unchanged by the correction."""
        self._check("up", self.market.lock_up)


class ObservedLimitClosesAtMarketLevel(_FlagAssertions, unittest.TestCase):
    """CONFIRMED: closes observed on the exchange at the lower limit (SPEC_FINAL section 8, from
    CNBC Indonesia, Katadata and investortrust.id) must be locked bars in a synthetic market that
    reproduces the reference price and the close. The one-step-higher control is a prediction of
    the rule, not an observation. These hold whichever tick reading is used (U3): BBCA's 4,820 is
    at or below both candidate limits (4,820 with the limit's own tick, 4,825 with the reference's
    tick) and 4,830 is above both.

    Guards against: a correction that sets limits no real stock reached, or locks too much.
    """

    ARB_2026_10_19 = (  # (label, reference, observed close at the 7% ARB)
        ("GOTO", 25, 24),
        ("TLKM", 1900, 1770),
        ("BBCA", 5175, 4820),
        ("AMMN", 3740, 3480),
        ("MORA", 3910, 3640),
        ("BYAN", 11150, 10375),
    )
    ARB_15_PERCENT = (  # (label, day, reference, observed close at the 15% ARB)
        ("GOTO/PADI/RBMS", "2026-09-28", 50, 43),
        ("BBCA", OCT16, 6075, 5175),
    )

    def test_observed_arb_closes_of_2026_10_19_are_locked(self):
        """Guards against: the 7% limit missing on 2026-10-19. Each of these closes was the
        lower limit that day (BBCA 5,175 -> 4,820 was -6.86%, BYAN -6.95%), so each is locked."""
        for label, ref, close in self.ARB_2026_10_19:
            self.assert_locked_down(ref, close, OCT19, label=label)

    def test_the_next_valid_price_above_each_observed_close_is_not_locked(self):
        """Guards against: a lower limit set above what was observed, which would lock a close
        that could still be sold."""
        for label, ref, close in self.ARB_2026_10_19:
            self.assert_not_locked_down(ref, _step_up(close), OCT19, label=label)

    def test_observed_15_percent_arb_closes_before_2026_10_19_are_locked(self):
        """Guards against: the 15% regime changing before the correction date. GOTO, PADI and RBMS
        closed at Rp43 from Rp50 on 2026-09-28; BBCA closed at Rp5,175 from Rp6,075 on 2026-10-16.
        One valid price higher is not locked."""
        for label, day, ref, close in self.ARB_15_PERCENT:
            self.assert_locked_down(ref, close, day, label=label)
            self.assert_not_locked_down(ref, _step_up(close), day, label=label)


class ThinBarRuleAtMarketLevel(_FlagAssertions, unittest.TestCase):
    """CONFIRMED: a one-price bar (high == low == close) is also locked at the 10% special-board
    limit, because the data has no board field (CONTRACT section 4). Before the correction this
    made one-price bars lock 10% down while regular bars needed 15%. From 2026-10-19 the regular
    7% limit is the tighter one, so the thin-bar rule adds no locks.

    Guards against: the thin-bar rule being lost, or changed, by the lower-limit correction.
    """

    def test_one_price_bar_10_percent_below_the_reference_is_locked_on_2026_10_16(self):
        """Guards against: the special-board limit no longer reaching one-price bars in the 15%
        regime. A one-price bar at Rp900 or Rp880 from Rp1,000 is locked on 2026-10-16."""
        self.assert_locked_down(1000, 900, OCT16, one_price=True)
        self.assert_locked_down(1000, 880, OCT16, one_price=True)

    def test_regular_bar_between_the_two_limits_is_not_locked_on_2026_10_16(self):
        """Guards against: the thin-bar rule applying to regular bars. The same prices on a bar
        that traded over a range (high above low) are above the 15% limit (Rp850), so not locked."""
        self.assert_not_locked_down(1000, 900, OCT16)
        self.assert_not_locked_down(1000, 880, OCT16)

    def test_one_price_bar_just_above_every_limit_is_not_locked(self):
        """Guards against: the thin-bar rule locking one-price bars above both limits. Rp935 is
        above the 10% limit (Rp900), the 7% limit (Rp930) and the 15% limit (Rp850)."""
        for day in THREE_DATES:
            self.assert_not_locked_down(1000, 935, day, one_price=True)

    def test_one_price_bar_at_930_is_locked_from_2026_10_19_but_not_on_2026_10_16(self):
        """Guards against: the regular 7% limit not reaching one-price bars. A one-price bar at
        Rp930 is on the 7% limit (locked on 10-19 and 10-20) but above the 10% special limit
        (Rp900) and the 15% limit, so it is not locked on 10-16."""
        self.assert_not_locked_down(1000, 930, OCT16, one_price=True)
        self.assert_locked_down(1000, 930, OCT19, one_price=True)
        self.assert_locked_down(1000, 930, OCT20, one_price=True)

    def test_from_2026_10_19_a_one_price_bar_adds_no_lock_over_a_regular_bar(self):
        """Guards against: the two kinds of bar disagreeing once the regular limit is tighter than
        the special one. For references from Rp10 up to Rp10,000 and every valid close from 15%
        below the reference to just under it, a one-price bar and a regular bar get the same
        lock_down flag on 2026-10-19, 2026-10-20 and 2026-12-31. References Rp11 to Rp14 are
        included for 2026-10-20 and 2026-12-31 only (SPEC_FINAL U5 for the 19th); for them every
        close from four rupiah below the reference to just under it is used."""
        groups = []
        cases = []
        for ref in (10, 15, 16, 20, 25, 50, 100, 200, 500, 1000, 2000, 5000, 10_000):
            close = _ceil_to_grid(Fraction(85, 100) * ref)
            while close < ref:
                cases.append((ref, close))
                close = _step_up(close)
        groups.append((cases, (OCT19, OCT20, DEC31)))
        low_cases = [(ref, c) for ref in (11, 12, 13, 14) for c in range(max(1, ref - 4), ref)]
        groups.append((low_cases, (OCT20, DEC31)))
        for number, (group, days) in enumerate(groups):
            regular = _market_from_cases(group, days).lock_down
            one_price = _market_from_cases(group, days, one_price=True).lock_down
            bad = np.argwhere(regular != one_price)
            shown = "; ".join(f"{group[i]} on {days[j]}" for i, j in bad[:5])
            self.assertEqual(len(bad), 0, f"{len(bad)} of {regular.size} flags differ: {shown}")
            # The sweep must not be vacuous. The first group straddles the 7% limit, so it mixes
            # locked and open flags. In the Rp11-14 group every close below the reference is at or
            # below the limit (reference minus Rp1), so there every flag is locked.
            self.assertTrue(regular.any())
            if number == 0:
                self.assertFalse(regular.all())


class PriceLimitsOffAndUnconfirmedBars(unittest.TestCase):
    """CONFIRMED (CONTRACT section 4): markets without daily limits (US, crypto) are never locked,
    on any date, and building a market never raises because of a date. Whether a warning is
    emitted for those markets is not specified, so warnings are ignored here.

    Guards against: the correction breaking the price_limits=False path, or making Market.build
    raise on bars dated after the last confirmed date.
    """

    DAYS = (OCT16, OCT19, OCT20, DEC31)
    CASES = ((1000, 930), (1000, 900), (1000, 750), (1000, 1250), (1000, 1500), (14, 13), (14, 8))

    def test_price_limits_false_locks_nothing_on_2027_bars(self):
        """Guards against: a lock flag appearing for a market without limits, or an exception, on
        bars dated 2027 (closes at, below and above every limit, regular and one-price)."""
        for one_price in (False, True):
            m = _market_from_cases(
                self.CASES, ("2027-01-04", "2027-06-30"), one_price=one_price, price_limits=False
            )
            self.assertFalse(m.lock_up.any())
            self.assertFalse(m.lock_down.any())
            self.assertEqual(m.lock_down.shape, (len(self.CASES), 2))

    def test_price_limits_false_locks_nothing_on_the_october_to_december_2026_bars(self):
        """Guards against: the new limits leaking into markets without limits on the dates the
        correction is about."""
        for one_price in (False, True):
            m = _market_from_cases(self.CASES, self.DAYS, one_price=one_price, price_limits=False)
            self.assertFalse(m.lock_up.any())
            self.assertFalse(m.lock_down.any())

    def test_price_limits_true_builds_2027_bars_without_raising(self):
        """Guards against: an exception for bars dated after 2026-12-31 when limits are on (a
        daily job would stop). Only the absence of an exception is asserted here."""
        m = _market_from_cases(self.CASES, ("2027-01-04", "2027-06-30"))
        self.assertEqual(m.lock_down.shape, (len(self.CASES), 2))
        self.assertEqual(m.lock_up.dtype, np.dtype(bool))


# ---------------------------------------------------------------------------------------------
# Item 10: the execution examples (CONTRACT section 5)
# ---------------------------------------------------------------------------------------------


class ExitLockExamples(unittest.TestCase):
    """How a lower-limit lock changes the exit. Worked examples for a human reader.

    execute() buys at the close of the session after the signal and sells at the close
    `holding_days` sessions later. If the stock is locked at its lower limit on that day, nobody
    could be assumed to buy, so the sale rolls forward to the next session in which the stock
    trades and is not locked. rolled_sessions counts the sessions lost, and the return is earned on
    the close of the session in which the sale really happens.

    Every example buys either 100 lots (10,000 shares) of a Rp1,000 stock or 714,200 shares of a
    Rp14 stock, with the default Rp10,000,000 budget, 10% participation cap and fees of 0.15% to
    buy and 0.25% to sell. Volumes are large enough that neither the lot rule nor the
    participation rule skips the trade, so each example ends with status EXITED.

    Guards against: a lower limit that does not reach the exit model, so locked positions are
    sold on days they could not be sold and the realised returns are too good.
    """

    #: Closes by session. Session 0 is the signal, session 1 the entry (a close of Rp1,000), and
    #: session 4 the scheduled exit, where the stock closes at Rp930 from a reference of Rp1,000.
    FALL_TO_930 = (1000, 1000, 1000, 1000, 930, 950, 950, 950)

    def test_exit_at_the_7_percent_limit_on_2026_10_19_rolls_to_the_next_session(self):
        """Worked example: a 7% fall on Monday 2026-10-19 now locks the sale, so the exit rolls.

        The position is bought at the close of Wednesday 2026-10-14 at Rp1,000 (100 lots, 10,000
        shares) and is due to be sold at the close of Monday 2026-10-19. That Monday the reference
        price (the previous close) is Rp1,000 and the stock closes at Rp930. The lower limit is 7%
        below the reference, 1,000 x 0.93 = 930, so Rp930 is exactly on the limit. A close on the
        lower limit counts as locked: there were no buyers above it, so the sale cannot be assumed.
        It rolls to the next session in which the stock trades and is not locked: Tuesday
        2026-10-20, with a reference of Rp930, a close of Rp950 and a lower limit of Rp865. The
        exit therefore moves from session 4 to session 5 (rolled_sessions = 1) and the return is
        earned on Rp950, not Rp930: 950 x (1 - 0.0025) / (1,000 x (1 + 0.0015)) - 1 = -5.38%.

        Guards against: the 15% limit (Rp850) still deciding on 2026-10-19, which would sell at
        Rp930 that same day and overstate how cleanly a fall of this size can be exited.
        """
        m, r = _exit_example("2026-10-13", 1000.0, self.FALL_TO_930, step=10)
        self.assertEqual(str(m.dates[4]), "2026-10-19")  # the scheduled exit session
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["entry_idx"], 1)
        self.assertEqual(r["shares"], 10_000)
        self.assertEqual(r["rolled_sessions"], 1, "a close at the 7% limit must lock the exit")
        self.assertEqual(r["exit_idx"], 5)
        self.assertEqual(str(m.dates[r["exit_idx"]]), "2026-10-20")
        self.assertEqual(r["exit_price"], 950)
        self.assertAlmostEqual(r["net_return"], _net(1000, 950))
        self.assertAlmostEqual(r["net_return"], -0.0538, places=4)

    def test_same_prices_with_the_exit_on_2026_10_16_do_not_roll(self):
        """Worked example: the identical price pattern, one session earlier, is not locked.

        Same closes as the previous example, with the calendar moved so that the scheduled exit is
        Friday 2026-10-16. That day the lower limit is still 15% below the reference: 1,000 x 0.85
        = 850. A close of Rp930 is only 7% down, well above Rp850, so the sale goes through at the
        close of that session: exit_idx stays at session 4, rolled_sessions is 0 and the return is
        earned on Rp930: 930 x (1 - 0.0025) / (1,000 x (1 + 0.0015)) - 1 = -7.37%.

        Guards against: the 7% limit being applied before 2026-10-19, which would lock this exit.
        """
        m, r = _exit_example("2026-10-12", 1000.0, self.FALL_TO_930, step=10)
        self.assertEqual(str(m.dates[4]), "2026-10-16")
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["entry_idx"], 1)
        self.assertEqual(r["shares"], 10_000)
        self.assertEqual(r["rolled_sessions"], 0)
        self.assertEqual(r["exit_idx"], 4)
        self.assertEqual(r["exit_price"], 930)
        self.assertAlmostEqual(r["net_return"], _net(1000, 930))
        self.assertAlmostEqual(r["net_return"], -0.0737, places=4)

    def test_15_percent_limit_still_locks_the_exit_on_2026_10_16(self):
        """Worked example: before the correction a fall has to reach 15% to lock the exit.

        On Friday 2026-10-16, with the stock bought at Rp1,000 and due for sale that day, the close
        has to reach Rp850 (1,000 x 0.85) for the sale to be locked. Here it does: the exit rolls
        to Monday 2026-10-19 (reference Rp850, close Rp950, a rise, so not locked) and the return
        is earned on Rp950: -5.38%. Compare the first example, where only a 7% fall (Rp930) locks.

        Guards against: the old regime losing its own lock while the new one is added.
        """
        closes = (1000, 1000, 1000, 1000, 850, 950, 950, 950)
        m, r = _exit_example("2026-10-12", 1000.0, closes, step=10)
        self.assertEqual(str(m.dates[4]), "2026-10-16")
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["rolled_sessions"], 1)
        self.assertEqual(r["exit_idx"], 5)
        self.assertEqual(str(m.dates[5]), "2026-10-19")
        self.assertAlmostEqual(r["net_return"], _net(1000, 950))

    def test_close_just_above_the_7_percent_limit_on_2026_10_19_does_not_roll(self):
        """Worked example: the lock is at the limit, not for every fall.

        On Monday 2026-10-19 a close of Rp935 from a reference of Rp1,000 is 6.5% down, one tick
        (Rp5) above the Rp930 limit. It is not locked, so the position is sold that day at Rp935:
        rolled_sessions is 0 and the return is 935 x (1 - 0.0025) / (1,000 x (1 + 0.0015)) - 1.

        Guards against: a lower limit set too high, which would lock exits that could be made and
        understate the returns of falling stocks.
        """
        closes = (1000, 1000, 1000, 1000, 935, 950, 950, 950)
        m, r = _exit_example("2026-10-13", 1000.0, closes, step=10)
        self.assertEqual(str(m.dates[4]), "2026-10-19")
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["rolled_sessions"], 0)
        self.assertEqual(r["exit_idx"], 4)
        self.assertAlmostEqual(r["net_return"], _net(1000, 935))

    def test_rp14_exit_one_rupiah_down_on_2026_10_20_rolls_to_the_next_session(self):
        """Worked example: in the Rp11-14 band the lower limit from 2026-10-20 is one rupiah down.

        A Rp14 stock is bought at the close of Thursday 2026-10-15. Rp10,000,000 buys 7,142 lots,
        714,200 shares (1,400 per lot fits 7,142 times), which is 1.4% of the 50,000,000 shares
        traded each session, far inside the 10% participation cap. The sale is due at the close of
        Tuesday 2026-10-20: reference Rp14, close Rp13. From that day the lower limit of a Rp11-14
        reference is the reference minus Rp1, 14 - 1 = 13, so Rp13 is locked and the sale rolls to
        Wednesday 2026-10-21 (reference Rp13, close Rp15), where it is sold. rolled_sessions is 1
        and the return is earned on Rp15: 15 x (1 - 0.0025) / (14 x (1 + 0.0015)) - 1 = +6.71%.
        Monday 2026-10-19 is a flat day at Rp14 here, so nothing about that day's Rp11-14 lower
        limit is involved (SPEC_FINAL U5).

        Guards against: the Rp1 rule for Rp11-14 missing, which leaves the 15% limit (Rp12) in
        force and lets this stock be sold at Rp13 when the exchange would not have allowed it.
        """
        closes = (14, 14, 14, 14, 13, 15, 15, 15)
        m, r = _exit_example("2026-10-14", 14.0, closes, step=1, volume=50_000_000.0)
        self.assertEqual(str(m.dates[4]), "2026-10-20")
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["entry_idx"], 1)
        self.assertEqual(r["shares"], 714_200)
        self.assertEqual(r["rolled_sessions"], 1, "Rp14 closing at Rp13 must be locked")
        self.assertEqual(r["exit_idx"], 5)
        self.assertEqual(str(m.dates[5]), "2026-10-21")
        self.assertEqual(r["exit_price"], 15)
        self.assertAlmostEqual(r["net_return"], _net(14, 15))

    def test_same_rp14_prices_with_the_exit_on_2026_10_16_do_not_roll(self):
        """Worked example: the same Rp14 pattern with the exit on Friday 2026-10-16 is not locked.

        Same closes and size as the previous example, calendar moved so that the sale is due on
        2026-10-16. The lower limit that day is 15% below the reference: 14 x 0.85 = 11.9, rounded
        up to the next valid price, Rp12. A close of Rp13 is above it, so the stock is sold that
        session at Rp13: rolled_sessions is 0 and the return is 13 x (1 - 0.0025) / (14 x (1 +
        0.0015)) - 1 = -7.51%.

        Guards against: the Rp1 rule for Rp11-14 being applied before its start date of 2026-10-20.
        """
        closes = (14, 14, 14, 14, 13, 15, 15, 15)
        m, r = _exit_example("2026-10-12", 14.0, closes, step=1, volume=50_000_000.0)
        self.assertEqual(str(m.dates[4]), "2026-10-16")
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["shares"], 714_200)
        self.assertEqual(r["rolled_sessions"], 0)
        self.assertEqual(r["exit_idx"], 4)
        self.assertEqual(r["exit_price"], 13)
        self.assertAlmostEqual(r["net_return"], _net(14, 13))


# ---------------------------------------------------------------------------------------------
# Item 4 (optional): a ledger-level example through paper.score
# ---------------------------------------------------------------------------------------------


class LedgerOutcomeExamples(unittest.TestCase):
    """How a lower-limit lock changes the paper ledger. Worked examples for a human reader.

    paper.score() closes a plain IDX decision at the close of the fifth session after its entry
    (the horizon), provided the stock can be sold that day. A close on the lower limit cannot be
    sold, so the position stays open and the ledger records no outcome. Both examples use data
    that end on the horizon session: the first session is the signal (a close of Rp1,000), the
    entry is the close of the next session at Rp1,000, and the horizon is session 6.

    Guards against: a lower limit that does not reach the ledger, which would record an exit and a
    return for a position that could not have been sold.
    """

    @staticmethod
    def _market(start, last_close):
        closes = (1000, 1000, 1000, 1000, 1000, 1000, last_close)
        return _synthetic_market(start, 1000.0, closes, step=10)

    def test_horizon_exit_locked_at_the_lower_limit_gets_no_outcome(self):
        """Worked example: a horizon close at the 7% limit leaves the decision without an outcome.

        Signal on Friday 2026-10-09, entry at the close of Monday 2026-10-12 at Rp1,000, horizon
        Monday 2026-10-19. That Monday the reference is Rp1,000 and the close is Rp930, exactly on
        the 7% limit (1,000 x 0.93), so the stock cannot be sold and score() returns None: the
        window is not finished. As a control, a close of Rp935 on the same session is above the
        limit, the position is sold and an outcome exists, so the None is caused by the lock.
        (This branch of score() never looks past the horizon session, so it would return None
        with later sessions in the data too; only the case without later sessions is asserted.)

        Guards against: the ledger recording an exit at Rp930 for a session that was locked.
        """
        control = self._market("2026-10-09", 935)
        self.assertEqual(str(control.dates[6]), "2026-10-19")
        self.assertIsNotNone(paper.score(_ledger_decision(str(control.dates[0]), 1000.0), control))

        m = self._market("2026-10-09", 930)
        self.assertEqual(str(m.dates[6]), "2026-10-19")
        outcome = paper.score(_ledger_decision(str(m.dates[0]), 1000.0), m)
        if outcome is not None:
            trade = outcome["execution"].get("paper_trade") or {}
            self.fail(
                "a horizon close on the 7% lower limit cannot be sold, yet score() recorded an "
                f"outcome (exit on {trade.get('exit_session')}, net {trade.get('net_return')})"
            )

    def test_same_price_path_with_the_horizon_exit_on_2026_10_16_gets_an_outcome(self):
        """Worked example: the identical path, one session earlier, is sold and scored.

        Signal on Thursday 2026-10-08, entry at the close of Friday 2026-10-09 at Rp1,000, horizon
        Friday 2026-10-16. The close of Rp930 is 7% down, but the lower limit that day is 15%
        (Rp850), so the position is sold at the horizon and the ledger records an outcome: the
        exit session is 2026-10-16, the reason is the horizon, and the net return is 930 x (1 -
        0.0025) / (1,000 x (1 + 0.0015)) - 1 = -7.37%, a LOSS for a BUY ON TRIGGER decision.

        Guards against: the 7% limit being applied before 2026-10-19, which would hold this
        position open.
        """
        m = self._market("2026-10-08", 930)
        self.assertEqual(str(m.dates[6]), "2026-10-16")
        outcome = paper.score(_ledger_decision(str(m.dates[0]), 1000.0), m)
        self.assertIsNotNone(outcome, "a close at 7% down is sellable on 2026-10-16")
        trade = outcome["execution"]["paper_trade"]
        self.assertEqual(trade["entry_session"], "2026-10-09")
        self.assertEqual(trade["exit_session"], "2026-10-16")
        self.assertEqual(trade["exit_reason"], "horizon")
        self.assertAlmostEqual(trade["net_return"], _net(1000, 930))
        self.assertEqual(outcome["decision_verdict"], "LOSS")


# ---------------------------------------------------------------------------------------------
# Item 8: vector semantics
# ---------------------------------------------------------------------------------------------

# One date per regime start and per date this file cares about; includes the two weekend dates.
_VECTOR_DAYS = (
    "2019-07-29", "2020-03-10", "2020-03-13", "2023-06-05", "2023-09-04", "2025-04-08",
    "2026-09-28", "2026-10-16", "2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20", DEC31,
)  # fmt: skip
_VECTOR_REFS = (8.0, 12.0, 14.0, 25.0, 100.0, 1000.0, 2000.0, 10_000.0)
_AFTER_DAYS = ("2027-01-01", "2027-01-04", "2031-07-15")
# A fixed permutation of the 13 columns of _VECTOR_DAYS (no random numbers: deterministic).
_PERMUTATION = (9, 3, 12, 0, 7, 10, 5, 1, 11, 4, 8, 2, 6)


def _vector_grid(extra=(), writable=True):
    """(references, dates) of shape (len(_VECTOR_REFS), len(days)): every reference on every
    date, the dates a broadcast of one row (a read-only view, as Market.build passes them)."""
    days = np.array(_VECTOR_DAYS + tuple(extra), dtype="datetime64[D]")
    refs = np.repeat(np.array(_VECTOR_REFS)[:, None], len(days), axis=1)
    grid = np.broadcast_to(days, refs.shape)
    return refs, (grid.copy() if writable else grid)


class LimitsVectorSemantics(unittest.TestCase):
    """CONFIRMED (CONTRACT section 2): limits() takes array-likes that broadcast against each
    other, preserves the broadcast shape, and treats every element on its own, so one call can mix
    regimes. Market.build calls it with two 2-D arrays of shape (tickers, sessions), the dates
    being a read-only broadcast of one row.

    Where a test compares one layout with another, or a grid with single calls, it asserts
    agreement only, never a value for a Rp11-14 reference on 2026-10-19 (SPEC_FINAL U5).

    Guards against: a correction that handles one date at a time, assumes sorted or 1-D dates,
    writes into its inputs, drops the shape, or lets one element's regime leak into another's.
    """

    def test_two_dimensional_call_preserves_shape_and_returns_floats(self):
        """Guards against: a result flattened, transposed or cast to integers or booleans."""
        refs, days = _vector_grid()
        ara, arb = _limits_quiet(refs, days)
        self.assertEqual(ara.shape, refs.shape)
        self.assertEqual(arb.shape, refs.shape)
        self.assertEqual(ara.dtype.kind, "f")
        self.assertEqual(arb.dtype.kind, "f")

    def test_mixed_regime_grid_equals_element_by_element_calls(self):
        """Guards against: one element's regime leaking into another's. The 13 dates run
        through every regime start from 2019 to 2026-12-31 (and both weekend dates); each cell must
        equal the call made for that one reference and date alone."""
        refs, days = _vector_grid()
        ara, arb = _limits_quiet(refs, days)
        for i in range(refs.shape[0]):
            for j in range(refs.shape[1]):
                one_ara, one_arb = _limits_quiet(refs[i : i + 1, j], days[i : i + 1, j])
                self.assertEqual((ara[i, j], arb[i, j]), (one_ara[0], one_arb[0]), (i, j))

    def test_mixed_regime_grid_matches_the_oracle_where_it_is_defined(self):
        """Guards against: the 2-D call getting the October columns wrong while single calls are
        right. Cells in 2026-09-28..2026-12-31 are compared with the oracle when they are
        CONFIRMED-grade (not U3, U4 or U5); the earlier columns are covered by the test above."""
        refs, days = _vector_grid()
        ara, arb = _limits_quiet(refs, days)
        problems, judged = [], 0
        for j, day in enumerate(_VECTOR_DAYS):
            period = _period_of(day)
            if period is None:
                continue
            oracle = _oracle(period)
            for i, ref in enumerate(_VECTOR_REFS):
                k = oracle.index(ref)
                for side, got, want in (("ARA", ara, oracle.ara), ("ARB", arb, oracle.arb)):
                    if oracle.cells("confirmed", side.lower())[k]:
                        judged += 1
                        if got[i, j] != want[k]:
                            problems.append(
                                f"{day} ref {ref:g} {side}: {got[i, j]:g}, oracle {want[k]:g}"
                            )
        self.assertGreater(judged, 100)
        _no_problems(self, problems, "cells of the 2-D grid disagree with the oracle")

    def test_column_order_does_not_matter(self):
        """Guards against: a result that depends on the order of the dates (an implementation that
        sorts, or searches, assuming ascending dates). The columns are permuted with a fixed
        derangement and each output column must follow its date."""
        refs, days = _vector_grid()
        ara, arb = _limits_quiet(refs, days)
        order = list(_PERMUTATION)
        shuffled_ara, shuffled_arb = _limits_quiet(refs[:, order], days[:, order])
        np.testing.assert_array_equal(shuffled_ara, ara[:, order])
        np.testing.assert_array_equal(shuffled_arb, arb[:, order])

    def test_column_of_references_against_row_of_dates_broadcasts(self):
        """Guards against: a result of the wrong shape when the inputs only broadcast: (8, 1)
        references against (1, 13) dates must give (8, 13) and the same numbers as the full grid."""
        refs, days = _vector_grid()
        ara, arb = _limits_quiet(refs, days)
        column = np.array(_VECTOR_REFS)[:, None]
        row = np.array(_VECTOR_DAYS, dtype="datetime64[D]")[None, :]
        b_ara, b_arb = _limits_quiet(column, row)
        self.assertEqual(b_ara.shape, (len(_VECTOR_REFS), len(_VECTOR_DAYS)))
        np.testing.assert_array_equal(b_ara, ara)
        np.testing.assert_array_equal(b_arb, arb)

    def test_read_only_broadcast_inputs_as_market_build_passes_them(self):
        """Guards against: an implementation that writes into its inputs. Market.build passes the
        dates as a read-only broadcast view; here the references are read-only too."""
        refs, days = _vector_grid(writable=False)
        refs.flags.writeable = False
        self.assertFalse(days.flags.writeable)
        ara, arb = _limits_quiet(refs, days)
        w_refs, w_days = _vector_grid()
        w_ara, w_arb = _limits_quiet(w_refs, w_days)
        np.testing.assert_array_equal(ara, w_ara)
        np.testing.assert_array_equal(arb, w_arb)

    def test_scalar_and_list_inputs(self):
        """Guards against: array-likes other than arrays being refused, or a scalar call returning
        something with a shape. Scalars give shape (), lists give shape (n,) (2026-10-16: ARA 1,250
        and ARB 850 for Rp1,000, ARA 9 and ARB 7 for Rp8)."""
        ara, arb = _limits_quiet(1000.0, OCT16)
        self.assertEqual((np.shape(ara), np.shape(arb)), ((), ()))
        self.assertEqual((float(ara), float(arb)), (1250.0, 850.0))
        ara, arb = _limits_quiet([1000.0, 8.0], [OCT16, OCT16])
        self.assertEqual((ara.tolist(), arb.tolist()), ([1250.0, 9.0], [850.0, 7.0]))

    def test_a_pre_2019_element_anywhere_in_a_two_dimensional_call_still_raises(self):
        """Guards against: the ValueError for dates before 2019-07-29 being lost in a vector call,
        or swallowed when the same call also holds a date after 2026-12-31."""
        refs = np.full((2, 2), 1000.0)
        for days in (
            [[OCT19, "2019-07-26"], [OCT20, OCT16]],
            [["2019-07-26", "2027-01-04"], [OCT19, OCT20]],
        ):
            with self.assertRaises(ValueError), warnings.catch_warnings():
                warnings.simplefilter("ignore")
                market.limits(refs, np.array(days, dtype="datetime64[D]"))

    def test_regime_index_preserves_two_dimensional_shape(self):
        """Guards against: regime_index() flattening a 2-D date array, or giving a different index
        to a date inside a grid than to the same date alone (up to 2026-12-31)."""
        _refs, days = _vector_grid()
        index = market.regime_index(days)
        self.assertEqual(index.shape, days.shape)
        for j in range(days.shape[1]):
            self.assertTrue((index[:, j] == market.regime_index(days[:1, j])[0]).all(), j)


# ---------------------------------------------------------------------------------------------
# Item 6, property and mixed-date parts: the unconfirmed period (a convention, not a rule)
# ---------------------------------------------------------------------------------------------


class UnconfirmedPeriodConvention(unittest.TestCase):
    """CONVENTION, not an exchange rule (CONTRACT section 3, SPEC_FINAL section 9). Nothing is
    confirmed for any date after 2026-12-31. The code adopts a labelled modelling convention
    for those dates: carry the rule of 2026-12-31 forward, and say so with a warning. These tests
    check that convention; they do not claim the exchange will do this, and they assert no
    symmetric (35/25/20) lower limit for those dates.

    Guards against: an unconfirmed rule being presented as fact, a daily job stopping on a date
    after the last confirmed one, a warning that goes missing, and results that depend on the
    mix of dates in one call.
    """

    AFTER = ("2027-01-01", "2027-01-04", "2027-12-31", "2031-07-15")

    def _warning_class(self):
        category = getattr(market, "RulesUnconfirmedWarning", None)
        if category is None:
            self.fail("idxsig.market.RulesUnconfirmedWarning is missing (CONTRACT section 3)")
        return category

    def test_the_warning_category_exists_and_is_a_user_warning(self):
        """Guards against: a missing or mis-based warning class, which callers cannot filter."""
        category = self._warning_class()
        self.assertTrue(issubclass(category, UserWarning))

    def test_regime_index_puts_every_unconfirmed_cell_in_the_dedicated_last_regime(self):
        """Convention, regime label (CONTRACT section 3d), 2-D: every date after 2026-12-31 in a
        grid maps to the last entry of REGIMES, which starts on 2027-01-01 and whose label says
        UNCONFIRMED; no date on or before 2026-12-31 maps to it.

        Guards against: unconfirmed dates sharing a regime with confirmed ones, so that reports
        keyed by regime would mix them."""
        _refs, days = _vector_grid(extra=_AFTER_DAYS)
        index = market.regime_index(days)
        after = days > np.datetime64(DEC31)
        last = len(market.REGIMES) - 1
        self.assertTrue((index[after] == last).all())
        self.assertTrue((index[~after] < last).all())
        self.assertEqual(market.REGIMES[last].start.isoformat(), "2027-01-01")
        self.assertIn("UNCONFIRMED", market.REGIMES[last].label)

    def test_unconfirmed_flags_a_two_dimensional_grid_cell_by_cell(self):
        """Convention, vector: unconfirmed() flags exactly the dates after 2026-12-31, cell by
        cell, for what limits() accepts: a read-only broadcast 2-D grid and a plain list of strings.

        Guards against: unconfirmed() refusing those inputs, or returning one flag per call
        instead of one per date."""
        unconfirmed = getattr(market, "unconfirmed", None)
        if unconfirmed is None:
            self.fail("idxsig.market.unconfirmed is missing (CONTRACT section 3)")
        _refs, days = _vector_grid(extra=_AFTER_DAYS, writable=False)
        flags = np.asarray(unconfirmed(days))
        self.assertEqual(flags.shape, days.shape)
        self.assertEqual(flags.dtype, np.dtype(bool))
        np.testing.assert_array_equal(flags, days > np.datetime64(DEC31))
        self.assertEqual(
            np.asarray(unconfirmed(["2026-12-30", DEC31, "2027-01-01", "2027-01-04"])).tolist(),
            [False, False, True, True],
        )

    def test_every_valid_reference_gets_its_2026_12_31_limits_after_that_date(self):
        """Convention, property: for all 24,750 valid references and each date after 2026-12-31,
        ARA and ARB equal the values of the same reference on 2026-12-31 (the last confirmed rule
        carried forward, CONTRACT section 3c).

        Guards against: a date after expiry that reverts to another table in any band or at any
        tick edge, for some references only."""
        refs = _oracle("P3").refs
        ara_last, arb_last = _code_limits(DEC31, refs)
        problems = []
        for day in self.AFTER:
            ara, arb = _code_limits(day, refs)
            for side, got, want in (("ARA", ara, ara_last), ("ARB", arb, arb_last)):
                bad = got != want
                if bad.any():
                    problems.append(
                        f"{day} {side}: {int(bad.sum())} of {len(refs)} references differ; first: "
                        + _examples(refs, got, want, bad, limit=3, want_label="2026-12-31")
                    )
        _no_problems(self, problems, "date/side combinations differ from 2026-12-31")

    def test_contract_example_reference_1000_on_2027_01_04(self):
        """Convention, the contract's example: limits(1000, '2027-01-04') is ARA 1,250 and ARB 930,
        the 2026-12-31 values. (An announced plan for a different lower limit is NOT applied.)

        Guards against: the announced plan for 2027 being applied as if it were a confirmed rule."""
        ara, arb = _limits_quiet(1000.0, "2027-01-04")
        self.assertEqual((float(ara), float(arb)), (1250.0, 930.0))

    def test_a_mixed_date_call_gives_each_element_its_own_regime(self):
        """Convention, mixed dates: one call with dates from the 15% regime, both October dates,
        the last confirmed days and three dates after expiry. For a reference of Rp1,000 the ARA is
        1,250 throughout and the ARB is 850 on 2026-10-16 and 930 on every later date.

        Guards against: the unconfirmed dates in a call changing the answer for the confirmed ones,
        or the other way round."""
        days = np.array(
            [OCT16, OCT19, OCT20, "2026-12-30", DEC31, "2027-01-01", "2027-01-04"],
            dtype="datetime64[D]",
        )
        ara, arb = _limits_quiet(np.full(days.shape, 1000.0), days)
        want_arb = [850.0, 930.0, 930.0, 930.0, 930.0, 930.0, 930.0]
        problems = [
            f"{day}: ARA {a:g} and ARB {b:g}, expected 1250 and {w:g}"
            for day, a, b, w in zip(days, ara, arb, want_arb)
            if (a, b) != (1250.0, w)
        ]
        _no_problems(self, problems, "elements of the mixed-date call have the wrong limits")

    def test_a_mixed_date_call_warns_every_time_it_is_made(self):
        """Convention, warning: with warnings set to 'always', a call in which at least one date is
        after 2026-12-31 records a RulesUnconfirmedWarning, every time it is made.

        Guards against: a warning shown once and then hidden, or tied to the first call only."""
        category = self._warning_class()
        refs = np.array([1000.0, 1000.0, 1000.0])
        days = np.array(["2026-12-30", DEC31, "2027-01-04"], dtype="datetime64[D]")
        for attempt in (1, 2):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                market.limits(refs, days)
            self.assertTrue(
                any(issubclass(w.category, category) for w in caught), f"call {attempt}"
            )

    def test_a_call_with_only_confirmed_dates_does_not_warn(self):
        """Convention, warning: a call whose dates are all on or before 2026-12-31 records no
        RulesUnconfirmedWarning, including the call that ends on 2026-12-31 itself.

        Guards against: a warning on every call, which trains users to ignore it."""
        category = self._warning_class()
        for days in (
            ["2019-07-29", OCT16, OCT19, OCT20],
            ["2026-12-30", DEC31],
            [DEC31],
        ):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                market.limits(np.full(len(days), 1000.0), np.array(days, dtype="datetime64[D]"))
            ours = [w for w in caught if issubclass(w.category, category)]
            self.assertEqual(ours, [], days)

    def test_a_two_dimensional_mixed_call_warns_and_keeps_its_shape(self):
        """Convention, vector: a (2, 4) grid of references Rp1,000 and Rp14 over four dates
        (2026-10-16, 2026-10-20, 2026-12-31, 2027-01-04) warns, keeps its shape, and carries the
        2026-12-31 limits forward: 1,000 -> ARB 930 and 14 -> ARB 13 (the Rp1 move), ARA 1,250 and
        18. (2026-10-19 is not used for Rp14: SPEC_FINAL U5.)

        Guards against: the warning, the shape or the values being lost in the 2-D layout."""
        category = self._warning_class()
        refs = np.array([[1000.0] * 4, [14.0] * 4])
        row = np.array([OCT16, OCT20, DEC31, "2027-01-04"], dtype="datetime64[D]")
        days = np.broadcast_to(row, refs.shape)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ara, arb = market.limits(refs, days)
        self.assertTrue(any(issubclass(w.category, category) for w in caught))
        self.assertEqual(ara.shape, (2, 4))
        self.assertEqual(ara.tolist(), [[1250.0] * 4, [18.0] * 4])
        self.assertEqual(arb.tolist(), [[850.0, 930.0, 930.0, 930.0], [12.0, 13.0, 13.0, 13.0]])

    def test_market_flags_of_2027_bars_equal_those_of_2026_12_31(self):
        """Convention, market level: bars dated after 2026-12-31 get the lock flags the same bars
        get on 2026-12-31. On that date, from a reference of Rp1,000, closes of 800, 900 and 930
        are locked down and 935 is not; from Rp14, closes of 13 and 12 are locked down; from Rp12,
        a close of 11 is; a close of 1,250 from Rp1,000 is locked up and 1,245 is not.

        Guards against: Market.build giving 2027 bars a different lower limit from the carried
        rule, which would unlock positions the convention says are locked."""
        cases = [
            (1000, 800), (1000, 900), (1000, 930), (1000, 935),
            (14, 13), (14, 12), (12, 11), (1000, 1250), (1000, 1245),
        ]  # fmt: skip
        days = ("2026-12-30", DEC31, "2027-01-04", "2027-01-05", "2027-06-30")
        m = _market_from_cases(cases, days)
        down = [True, True, True, False, True, True, True, False, False]
        up = [False] * 7 + [True, False]
        for j in (2, 3, 4):  # the convention: the same flags as 2026-12-31, column 1
            self.assertEqual(m.lock_down[:, j].tolist(), m.lock_down[:, 1].tolist(), days[j])
            self.assertEqual(m.lock_up[:, j].tolist(), m.lock_up[:, 1].tolist(), days[j])
        for j in (0, 1):  # and the confirmed rule they are carried from
            self.assertEqual(m.lock_down[:, j].tolist(), down, days[j])
            self.assertEqual(m.lock_up[:, j].tolist(), up, days[j])

    def test_building_a_market_with_2027_bars_and_price_limits_warns(self):
        """Convention, warning at market level: Market.build with price_limits=True calls limits()
        on bars dated after 2026-12-31 and so records a RulesUnconfirmedWarning, without raising.
        (With price_limits=False the contract allows either outcome; nothing is asserted there.)

        Guards against: a market of unconfirmed dates being built silently with limits on."""
        category = self._warning_class()
        with self.assertWarns(category):
            _market_from_cases([(1000, 930)], ["2027-01-04"], quiet=False)


if __name__ == "__main__":
    unittest.main()

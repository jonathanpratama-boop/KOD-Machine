r"""October 2026 correction of the IDX auto-rejection limits: tests of idxsig.market.limits().

Written from two documents only, SPEC_FINAL.md (the market facts, reconciled 2026-11-09) and CONTRACT.md
(the interface of the correction), before the code change existed. Every expected number is transcribed
from SPEC_FINAL sections 7.1, 7.2, 7.3 and 8, or derived by hand in the comment next to it; for the
regimes before 2026-09-28, which SPEC_FINAL does not cover, the few explicit numbers come from the schedule
in the idxsig/market.py docstring and the existing tests/test_market.py, and the rest from the golden
master. None is computed by the code under test.

Evidence grade of each class, so that a failure carries the weight of its class:

  Confirmed*                    CONFIRMED market facts: the dated rule table, the 20 observed anchors, the
                                helper functions the contract keeps, properties of every valid reference, and
                                the 10% / Rp1 rule of special_limits where no rounding is involved.
  Reported*                     REPORTED facts, flagged as such (SPEC_FINAL U3, U4, section 7.3): the own-band
                                tick at band crossings, the ARB of a Rp1 reference, and the rounded cells of
                                special_limits.
  UnconfirmedPeriodConvention*  The CONVENTION of CONTRACT section 3 for dates after 2026-12-31 (the last
                                confirmed rule is carried forward). A modelling choice, not an exchange rule.
  EarlierRegimesGoldenMaster    Regression guard: every output for 2019-07-29 .. 2026-10-18 equals what the
                                module returned before the correction.
  BoardDistinction*             The thin-bar rule in Market.build: a one-price bar is judged at the 10% limit.

Not asserted, on purpose (SPEC_FINAL U5, section 9, section 12; CONTRACT section 6): the ARB on 2026-10-19
for references Rp11-14; any exchange rule for a date after 2026-12-31 (only the labelled convention);
ETF, REIT, IPO, rights and warrant limits; a last-session date or a holiday; the order-volume rule.
Dates are calendar dates: limits() consults no session calendar. 2026-12-31 is used only as the last
calendar date of the confirmed period; SPEC_FINAL U11 says it may be a holiday.

Golden master. tests/fixtures/market_limits_golden_20261109.json holds the (ARA, ARB) pairs that the
unmodified idxsig/market.py (sha256 e9e9328a...) returned for 74 reference prices (every band edge and tick
edge of SPEC_FINAL section 4, and others) and 5 off-grid references, on 40 calendar dates from 2019-07-29 to
2026-10-18: every regime start date and the day before it, interior dates and weekend dates. It also holds
the regime index of each date, special_limits for the same references, and the regime labels that start on
or before 2026-09-28. It was captured by the script below, run from idx-signals/ on the unmodified module
before anything was changed; the script refuses to run against any other version of market.py. The script
is documentation only: it is not part of the tests and nothing imports it.

    # Capture script for tests/fixtures/market_limits_golden_20261109.json.
    # Run from idx-signals/ against the UNMODIFIED idxsig/market.py (the base of the October 2026
    # correction); it refuses to run against any other version of that file:
    #   python3 capture_golden.py > tests/fixtures/market_limits_golden_20261109.json

    import hashlib
    import json
    import sys

    import numpy as np

    sys.path.insert(0, ".")
    from idxsig import market  # noqa: E402

    BASE_SHA256 = "e9e9328af46a871d6a8bc929ab10889f071bcdbef4be6d85f6fe1d26bd2f9cbc"
    REFS = [
        1, 2, 3, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 20, 25, 30, 40, 49, 50, 51, 55, 58, 59,
        60, 75, 100, 150, 198, 199, 200, 201, 202, 203, 250, 300, 400, 498, 499, 500, 501, 502, 505,
        510, 750, 1000, 1500, 1990, 1995, 1999, 2000, 2005, 2010, 2500, 3000, 4000, 4980, 4990, 4995,
        4999, 5000, 5001, 5010, 5025, 5050, 6000, 7500, 10000, 12525, 20000, 30000, 50000, 100000,
        600000,
    ]  # fmt: skip
    OFF_GRID_REFS = [10.5, 14.5, 200.5, 4999.5, 5000.5]  # not valid prices; "unchanged" still holds
    DATES = [
        "2019-07-29", "2019-07-30", "2019-08-01", "2020-03-09", "2020-03-10", "2020-03-11",
        "2020-03-12", "2020-03-13", "2020-03-16", "2021-06-15", "2022-12-30", "2023-06-02",
        "2023-06-04", "2023-06-05", "2023-06-06", "2023-09-01", "2023-09-03", "2023-09-04",
        "2023-09-05", "2024-01-02", "2024-12-31", "2025-04-07", "2025-04-08", "2025-04-09",
        "2025-10-21", "2025-10-22", "2026-01-02", "2026-06-30", "2026-09-24", "2026-09-25",
        "2026-09-26", "2026-09-27", "2026-09-28", "2026-09-29", "2026-10-01", "2026-10-14",
        "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18",
    ]  # fmt: skip


    def num(x):
        x = float(x)
        return int(x) if x.is_integer() else x


    def row(values):
        return "[" + ", ".join(json.dumps(num(v)) for v in values) + "]"


    def main():
        digest = hashlib.sha256(open("idxsig/market.py", "rb").read()).hexdigest()
        if digest != BASE_SHA256:
            sys.exit("refusing to capture: idxsig/market.py is not the unmodified base module")
        refs = np.array(REFS + OFF_GRID_REFS, dtype=float)
        n = len(REFS)
        out = ["{"]
        out.append('  "captured_from": {"module": "idx-signals/idxsig/market.py", "sha256": "%s"},' % digest)
        out.append('  "references": %s,' % row(REFS))
        out.append('  "off_grid_references": %s,' % row(OFF_GRID_REFS))
        out.append('  "dates": %s,' % json.dumps(DATES))
        out.append('  "limits": {')
        for i, d in enumerate(DATES):
            day = np.full(refs.shape, np.datetime64(d, "D"))
            ara, arb = market.limits(refs, day)
            idx = int(market.regime_index(np.datetime64(d, "D")))
            out.append('    "%s": {"regime_index": %d,' % (d, idx))
            out.append('      "ara": %s, "arb": %s,' % (row(ara[:n]), row(arb[:n])))
            out.append('      "off_grid_ara": %s, "off_grid_arb": %s}%s'
                       % (row(ara[n:]), row(arb[n:]), "," if i < len(DATES) - 1 else ""))
        out.append("  },")
        sp_ara, sp_arb = market.special_limits(refs)
        out.append('  "special_limits": {"ara": %s, "arb": %s,' % (row(sp_ara[:n]), row(sp_arb[:n])))
        out.append('    "off_grid_ara": %s, "off_grid_arb": %s},' % (row(sp_ara[n:]), row(sp_arb[n:])))
        labels = [r for r in market.regime_labels() if r["start"] <= "2026-09-28"]
        out.append('  "regime_labels_through_2026_09_28": [')
        for i, r in enumerate(labels):
            out.append("    %s%s" % (json.dumps(r), "," if i < len(labels) - 1 else ""))
        out.append("  ]")
        out.append("}")
        print("\n".join(out))


    main()
"""

import dataclasses
import datetime
import inspect
import json
import unittest
import warnings
from fractions import Fraction
from pathlib import Path

import numpy as np

from idxsig import market
from tests.support import flat_market, rebuild

GOLDEN_PATH = Path(__file__).resolve().parent / "fixtures" / "market_limits_golden_20261109.json"

# Calendar dates standing for each period of SPEC_FINAL section 1. limits() selects its rule by the
# calendar date (CONTRACT section 1), so none of them has to be a session.
P0_DATES = ("2026-09-24", "2026-09-25")  # Kep-00003/BEI/04-2025; minimum price Rp50
P1_DATES = ("2026-09-28", "2026-10-16")  # Kep-00136/BEI/09-2026; ARB 15%; minimum price Rp1
P2_DATES = ("2026-10-19",)  # Kep-00157/BEI/10-2026; ARB 7%
P3_DATES = ("2026-10-20", "2026-11-09", "2026-12-30", "2026-12-31")  # Kep-00158/BEI/10-2026
P1_TO_P3_DATES = P1_DATES + P2_DATES + P3_DATES
# One call per (period, date) for the properties over every valid reference price.
PERIOD_DAYS = (
    ("P0", "2026-09-25"),
    ("P1", "2026-09-28"),
    ("P1", "2026-10-16"),
    ("P2", "2026-10-19"),
    ("P3", "2026-10-20"),
    ("P3", "2026-12-31"),
)
MINIMUM_PRICE = {"P0": 50, "P1": 1, "P2": 1, "P3": 1}
AFTER_LAST_CONFIRMED_DATE = ("2027-01-01", "2027-01-04", "2027-06-30", "2030-01-01")

# SPEC_FINAL 7.2, "Full arithmetic". One row per reference:
#   (reference, ARA in P1 = P2 = P3, ARB P0, ARB P1, ARB P2, ARB P3).
# None means "not asserted in the Confirmed* classes", for one of four reasons:
#   - P0 below Rp50 is "n/a (below Rp50 minimum)";
#   - P2 with a reference of Rp11-14 is SPEC_FINAL U5 and is not asserted anywhere;
#   - the ARB of R = 1 is SPEC_FINAL U4 (REPORTED);
#   - the cell depends on the own-band tick choice, SPEC_FINAL U3 (REPORTED): R = 500 ARB, R = 4990 ARA,
#     R = 5001 ARB and R = 5025 ARB as listed in SPEC_FINAL 7.2, plus R = 201 ARB, which the same
#     criterion selects (raw 170.85 and 186.93 lie in the tick-1 band, R in the tick-2 band; the
#     reference-band tick would give 172 and 188). Those cells are in ReportedOwnBandTickTests.
SECTION_7_2 = (
    (1, 2, None, None, None, None),
    (2, 3, None, 1, 1, 1),
    (10, 11, None, 9, 9, 9),
    (11, 14, None, 10, None, 10),
    (12, 16, None, 11, None, 11),
    (13, 17, None, 12, None, 12),
    (14, 18, None, 12, None, 13),
    (15, 20, None, 13, 14, 14),
    (16, 21, None, 14, 15, 15),
    (17, 22, None, 15, 16, 16),
    (20, 27, None, 17, 19, 19),
    (25, 33, None, 22, 24, 24),
    (50, 67, 50, 43, 47, 47),
    (100, 135, 85, 85, 93, 93),
    (199, 268, 170, 170, 186, 186),
    (200, 270, 170, 170, 186, 186),
    (201, 250, None, None, None, None),
    (202, 252, 172, 172, 188, 188),
    (500, 625, None, None, None, None),
    (505, 630, 430, 430, 470, 470),
    (1000, 1250, 850, 850, 930, 930),
    (1995, 2490, 1700, 1700, 1860, 1860),
    (2000, 2500, 1700, 1700, 1860, 1860),
    (4990, None, 4250, 4250, 4650, 4650),
    (5000, 6250, 4250, 4250, 4650, 4650),
    (5001, 6000, None, None, None, None),
    (5025, 6025, None, None, None, None),
    (10000, 12000, 8500, 8500, 9300, 9300),
)

# SPEC_FINAL 7.1, "Per-date quick reference". One row per reference; one cell per date of
# SECTION_7_1_DATES, each (ARA, ARB) or None for "n/a" (P0 below Rp50). An ARB of None inside a cell is
# not asserted, for the reasons listed above (U4 for R = 1; U5 for R = 11 and 14 on 2026-10-19; U3 for the
# daggered rows 201 and 5001).
SECTION_7_1_DATES = (
    "2026-09-25",
    "2026-09-28",
    "2026-10-16",
    "2026-10-19",
    "2026-10-20",
    "2026-12-31",
)
# fmt: off
SECTION_7_1 = (
    # ref   2026-09-25     2026-09-28     2026-10-16     2026-10-19     2026-10-20     2026-12-31
    (1,     None,          (2, None),     (2, None),     (2, None),     (2, None),     (2, None)),
    (10,    None,          (11, 9),       (11, 9),       (11, 9),       (11, 9),       (11, 9)),
    (11,    None,          (14, 10),      (14, 10),      (14, None),    (14, 10),      (14, 10)),
    (14,    None,          (18, 12),      (18, 12),      (18, None),    (18, 13),      (18, 13)),
    (15,    None,          (20, 13),      (20, 13),      (20, 14),      (20, 14),      (20, 14)),
    (16,    None,          (21, 14),      (21, 14),      (21, 15),      (21, 15),      (21, 15)),
    (50,    (67, 50),      (67, 43),      (67, 43),      (67, 47),      (67, 47),      (67, 47)),
    (100,   (135, 85),     (135, 85),     (135, 85),     (135, 93),     (135, 93),     (135, 93)),
    (200,   (270, 170),    (270, 170),    (270, 170),    (270, 186),    (270, 186),    (270, 186)),
    (201,   (250, None),   (250, None),   (250, None),   (250, None),   (250, None),   (250, None)),
    (5000,  (6250, 4250),  (6250, 4250),  (6250, 4250),  (6250, 4650),  (6250, 4650),  (6250, 4650)),
    (5001,  (6000, None),  (6000, None),  (6000, None),  (6000, None),  (6000, None),  (6000, None)),
    (10000, (12000, 8500), (12000, 8500), (12000, 8500), (12000, 9300), (12000, 9300), (12000, 9300)),
)
# fmt: on

# SPEC_FINAL section 8: the 20 observed limit prices. (name, date, reference, side, observed price).
# "derived" references in the source were backed out from the printed percentage change. The raw limit
# and what round-to-nearest would give are in the comment; the rule is floor for ARA, ceil for ARB.
# fmt: off
ANCHORS = (
    ("GOTO/PADI/RBMS",  "2026-09-28", 50,     "ARB", 43),     # 15%: raw 42.5; nearest 43
    ("GOTO",            "2026-10-19", 25,     "ARB", 24),     # 7%: raw 23.25; nearest would give 23
    ("TLKM",            "2026-10-19", 1900,   "ARB", 1770),   # raw 1767; nearest would give 1765
    ("BBCA",            "2026-10-19", 5175,   "ARB", 4820),   # raw 4812.75; nearest would give 4810; 4825 is off-grid
    ("AMMN",            "2026-10-19", 3740,   "ARB", 3480),   # raw 3478.2
    ("MORA",            "2026-10-19", 3910,   "ARB", 3640),   # raw 3636.3
    ("BYAN",            "2026-10-19", 11150,  "ARB", 10375),  # raw 10369.5
    ("BBCA",            "2026-10-16", 6075,   "ARB", 5175),   # 15%: raw 5163.75
    ("AKSI",            "2025-10-21", 302,    "ARA", 376),    # 25%: raw 377.5; nearest would give 378
    ("FITT",            "2025-10-21", 835,    "ARA", 1040),   # raw 1043.75; nearest would give 1045
    ("COCO",            "2025-10-21", 246,    "ARA", 306),    # raw 307.5; nearest would give 308
    ("WAPO",            "2025-10-21", 234,    "ARA", 292),    # raw 292.5
    ("BABY",            "2025-10-21", 430,    "ARA", 535),    # raw 537.5 in tick 5; the reference is in tick 2
    ("COCO",            "2025-10-22", 306,    "ARA", 382),    # raw 382.5
    ("TEBE",            "2025-10-22", 1930,   "ARA", 2410),   # raw 2412.5
    ("NIRO",            "2025-10-22", 163,    "ARA", 220),    # 35%: raw 220.05
    ("AYLS",            "2025-10-22", 175,    "ARA", 236),    # raw 236.25
    ("PPRE",            "2025-10-22", 86,     "ARA", 116),    # raw 116.1
    ("PGUN",            "2025-10-22", 12525,  "ARA", 15025),  # 20%: raw 15030
    ("RISE",            "2025-10-22", 7300,   "ARA", 8750),   # raw 8760
)
# fmt: on

# SPEC_FINAL 7.3 (REPORTED): special_limits, 10% / 10% above Rp10, +/- Rp1 in the Rp1-10 band.
# (reference, ARA, ARB)
SECTION_7_3 = (
    (1, 2, 1),  # 1 - 1 = 0, below the minimum price Rp1
    (2, 3, 1),
    (10, 11, 9),
    (11, 12, 10),  # 12.1 floors to 12; 9.9 ceils to 10
    (12, 13, 11),
    (14, 15, 13),
    (15, 16, 14),
    (16, 17, 15),
    (100, 110, 90),
    (200, 220, 180),
    (201, 220, 181),  # 221.1 floors to 220 (tick 2); 180.9 ceils to 181 (tick 1)
    (1000, 1100, 900),
    (5000, 5500, 4500),
    (5001, 5500, 4510),  # 5501.1 floors to 5500; 4500.9 ceils to 4510
    (10000, 11000, 9000),
)

# REPORTED (SPEC_FINAL U3): cells whose value depends on the tick being that of the limit's own band.
# (reference, side, value in P0, P1, P2, P3). The value under the reference-band tick is in the comment.
# fmt: off
OWN_BAND_CELLS = (
    # ref  side   P0    P1    P2    P3
    (201,  "ARB", 171,  171,  187,  187),   # raw 170.85 / 186.93 in tick 1; reference-band tick: 172 / 188
    (500,  "ARB", 426,  426,  466,  466),   # raw 425 / 465 in tick 2; reference-band tick: 425 / 465
    (4990, "ARA", 6225, 6225, 6225, 6225),  # raw 6237.5 in tick 25; reference-band tick: 6230
    (5001, "ARB", 4260, 4260, 4660, 4660),  # raw 4250.85 / 4650.93 in tick 10; reference-band: 4275 / 4675
    (5025, "ARB", 4280, 4280, 4680, 4680),  # raw 4271.25 / 4673.25 in tick 10; reference-band: 4275 / 4675
)
# fmt: on


def spec_tick(price):
    """Tick of the band a price lies in, SPEC_FINAL section 4 (a separate copy of market.TICK_BANDS)."""
    if price < 200:
        return 1
    if price < 500:
        return 2
    if price < 2000:
        return 5
    if price < 5000:
        return 10
    return 25


def is_valid_price(price, minimum=1):
    """SPEC_FINAL section 5: a whole rupiah, at least the minimum price, a multiple of its own tick."""
    return price == int(price) and price >= minimum and int(price) % spec_tick(price) == 0


def valid_references(top=30000):
    """Every valid price (SPEC_FINAL section 4) from Rp1 to `top`: the possible reference prices."""
    refs = list(range(1, 200))
    refs += list(range(200, 500, 2))
    refs += list(range(500, 2000, 5))
    refs += list(range(2000, 5000, 10))
    refs += list(range(5000, top + 1, 25))
    return refs


VALID_REFERENCES = tuple(valid_references())


def raw_limits(ref, period):
    """Unrounded (ARA, ARB) for a Main/Development/New Economy reference, SPEC_FINAL 2.1 and 5.

    Exact Fractions. The ARB is None where nothing is asserted: P2 for Rp11-14 (SPEC_FINAL U5).
    """
    r = Fraction(ref)
    if r <= 10:  # Rp1-10: a nominal Rp1, in every period that has the band
        return r + 1, r - 1
    if r <= 200:
        up = Fraction(35, 100)
    elif r <= 5000:
        up = Fraction(25, 100)
    else:
        up = Fraction(20, 100)
    if period in ("P0", "P1"):
        down = r * Fraction(85, 100)
    elif r <= 14:
        down = r - 1 if period == "P3" else None
    else:
        down = r * Fraction(93, 100)
    return r * (1 + up), down


def lim(ref, day):
    """(ARA, ARB) of one reference price on one calendar date, as floats."""
    ara, arb = market.limits(np.array([float(ref)]), np.array([np.datetime64(day, "D")]))
    return float(ara[0]), float(arb[0])


def lim_quiet(ref, day):
    """lim() with every warning ignored: for dates after the last confirmed date."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return lim(ref, day)


def limit_arrays(refs, day):
    """limits() for many references on one calendar date, warnings ignored."""
    refs = np.array(refs, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return market.limits(refs, np.full(refs.shape, np.datetime64(day, "D")))


def grid_results(period, day):
    """[(reference, ARA, ARB)] from limits() for every valid reference that exists in `period`."""
    refs = [ref for ref in VALID_REFERENCES if ref >= MINIMUM_PRICE[period]]
    ara, arb = limit_arrays(refs, day)
    return list(zip(refs, ara.tolist(), arb.tolist()))


def unconfirmed_warnings(call):
    """Run call() with every warning shown; return (its result, the RulesUnconfirmedWarning records)."""
    category = market.RulesUnconfirmedWarning
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = call()
    return result, [w for w in caught if issubclass(w.category, category)]


def load_golden():
    with open(GOLDEN_PATH, encoding="utf-8") as handle:
        return json.load(handle)


class LimitsCase(unittest.TestCase):
    def assert_cell(self, ref, day, ara=None, arb=None):
        """Assert the asserted parts of one (ARA, ARB) cell; None leaves a side unasserted."""
        got_ara, got_arb = lim(ref, day)
        if ara is not None:
            self.assertEqual(got_ara, ara, f"ARA of reference {ref} on {day}")
        if arb is not None:
            self.assertEqual(got_arb, arb, f"ARB of reference {ref} on {day}")


class ConfirmedPeriodTableTests(LimitsCase):
    """CONFIRMED (SPEC_FINAL sections 1, 2.1, 5, 6, 7.1, 7.2): the dated rule table of the decisions.

    Table-driven: a failing subTest names the reference and the date. The cells that SECTION_7_2 and
    SECTION_7_1 leave as None are not asserted here: P0 below Rp50 (n/a), P2 for Rp11-14 (U5, not asserted
    anywhere), the ARB of R = 1 (U4) and the own-band crossing cells (U3) live in the Reported* classes.
    """

    def check_section_7_1(self, days):
        for ref, *cells in SECTION_7_1:
            for day, cell in zip(SECTION_7_1_DATES, cells):
                if day in days and cell is not None:
                    with self.subTest(ref=ref, day=day):
                        self.assert_cell(ref, day, *cell)

    def check_section_7_2_arb(self, column, days):
        for row in SECTION_7_2:
            ref, arb = row[0], row[column]
            if arb is None:
                continue
            for day in days:
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, arb=arb)

    def test_section_7_1_and_7_2_agree_where_both_assert(self):
        """Guards against: a transcription slip in one of the two copies of the same SPEC_FINAL numbers."""
        column = {  # the SECTION_7_2 column that each SECTION_7_1 date reads
            "2026-09-25": 2,
            "2026-09-28": 3,
            "2026-10-16": 3,
            "2026-10-19": 4,
            "2026-10-20": 5,
            "2026-12-31": 5,
        }
        rows = {row[0]: row for row in SECTION_7_2}
        for ref, *cells in SECTION_7_1:
            for day, cell in zip(SECTION_7_1_DATES, cells):
                if cell is None:
                    continue
                with self.subTest(ref=ref, day=day):
                    ara, arb = cell
                    self.assertEqual(ara, rows[ref][1])
                    if arb is not None and rows[ref][column[day]] is not None:
                        self.assertEqual(arb, rows[ref][column[day]])

    def test_section_7_1_columns_before_the_october_decisions(self):
        """Guards against: a change to the P0 and P1 columns (2026-09-25, 09-28, 10-16) of the per-date table."""
        self.check_section_7_1({"2026-09-25", "2026-09-28", "2026-10-16"})

    def test_section_7_1_columns_from_2026_10_19(self):
        """Guards against: the 7% ARB missing on 2026-10-19, the nominal Rp1 ARB for Rp11-14 missing from
        2026-10-20, or either rule ending before the last confirmed date 2026-12-31."""
        self.check_section_7_1({"2026-10-19", "2026-10-20", "2026-12-31"})

    def test_section_7_2_ara_is_identical_in_every_period(self):
        """Guards against: the October decisions changing the ARA; SPEC_FINAL 7.2 gives one ARA column for
        P1, P2 and P3, and the same values hold in P0 for references of Rp50 and above."""
        for ref, ara, *_ in SECTION_7_2:
            if ara is None:
                continue
            for day in P1_TO_P3_DATES + (P0_DATES if ref >= 50 else ()):
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, ara=ara)

    def test_section_7_2_arb_in_p0(self):
        """Guards against: the old regime (15% ARB, minimum price Rp50) changing; references below Rp50 are
        n/a in P0."""
        self.check_section_7_2_arb(2, P0_DATES)

    def test_section_7_2_arb_in_p1(self):
        """Guards against: the Rp1-reform regime (15% ARB above Rp10, floor Rp1) changing."""
        self.check_section_7_2_arb(3, P1_DATES)

    def test_section_7_2_arb_in_p2(self):
        """Guards against: the 7% ARB not applying on 2026-10-19 (Rp11-14 is not asserted: U5)."""
        self.check_section_7_2_arb(4, P2_DATES)

    def test_section_7_2_arb_in_p3(self):
        """Guards against: the 7% ARB, or the nominal Rp1 ARB for Rp11-14, not applying from 2026-10-20."""
        self.check_section_7_2_arb(5, P3_DATES)

    def test_rp1_10_band_moves_a_nominal_rupiah_from_2026_09_28(self):
        """Guards against: the Rp1-10 band turning into a percentage band, or the October decisions changing
        it (SPEC_FINAL section 6: ARA = R + 1, ARB = R - 1, the same in P1, P2 and P3). The ARB of R = 1
        (floored at the minimum price) is REPORTED and is in ReportedRp1ReferenceArbTests."""
        for ref in range(1, 11):
            for day in P1_TO_P3_DATES:
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, ara=ref + 1, arb=None if ref == 1 else ref - 1)

    def test_rp11_14_ara_is_35_percent_on_every_date_from_2026_09_28(self):
        """Guards against: the ARA of the Rp11-14 references changing; it stays 35% in P1, P2 and P3
        (SPEC_FINAL U5 and section 2.1: the ARA is asserted even on 2026-10-19). 11 * 1.35 = 14.85,
        12 * 1.35 = 16.2, 13 * 1.35 = 17.55, 14 * 1.35 = 18.9, each floored on the Rp1 tick."""
        for ref, ara in ((11, 14), (12, 16), (13, 17), (14, 18)):
            for day in P1_TO_P3_DATES:
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, ara=ara)

    def test_rp11_14_arb_is_15_percent_up_to_2026_10_18(self):
        """Guards against: the Rp11-14 rule starting early; 15% gives 10, 11, 12 and 12 (SPEC_FINAL 7.2),
        and 2026-10-17 and 2026-10-18 are weekend calendar dates that still follow it (CONTRACT section 1)."""
        for ref, arb in ((11, 10), (12, 11), (13, 12), (14, 12)):
            for day in P1_DATES + ("2026-10-17", "2026-10-18"):
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, arb=arb)

    def test_rp11_14_arb_is_a_nominal_rupiah_from_2026_10_20(self):
        """Guards against: the Rp11-14 ARB staying a percentage; from 2026-10-20 it is R - 1 (SPEC_FINAL
        section 6 and U14), with the ARA unchanged at 35%."""
        for ref, ara, arb in ((11, 14, 10), (12, 16, 11), (13, 17, 12), (14, 18, 13)):
            for day in P3_DATES:
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, ara=ara, arb=arb)

    def test_minimum_price_changes_from_rp50_to_rp1_on_2026_09_28(self):
        """Guards against: the Rp1 floor starting early or late. 55 * 0.85 = 46.75 ceils to 47, which the
        Rp50 minimum price lifts to 50 in P0 only; the ARA is 55 * 1.35 = 74.25, floored to 74."""
        for day, arb in (
            ("2026-09-24", 50),
            ("2026-09-25", 50),
            ("2026-09-28", 47),
            ("2026-09-29", 47),
        ):
            with self.subTest(day=day):
                self.assert_cell(55, day, ara=74, arb=arb)

    def test_old_floor_pins_the_arb_at_rp50_for_references_50_to_58(self):
        """Guards against: the P0 floor ceasing to bind; with a 15% ARB at the Rp50 floor, R = 50 to 58
        gives ARB = 50 (no downside) and R = 59 gives 50.15, ceiled to 51 (SPEC_FINAL section 5)."""
        for ref in range(50, 60):
            for day in P0_DATES:
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, arb=51 if ref == 59 else 50)

    def test_rules_are_unchanged_through_calendar_date_2026_10_18(self):
        """Guards against: the October rules starting before 2026-10-19. limits() selects by calendar date,
        so Saturday 2026-10-17 and Sunday 2026-10-18 follow the P1 rule (CONTRACT section 1)."""
        cells = ((1000, 1250, 850), (55, 74, 47), (14, 18, 12), (15, 20, 13), (8, 9, 7))
        for day in ("2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18"):
            for ref, ara, arb in cells:
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, ara, arb)

    def test_seven_percent_arb_starts_on_2026_10_19(self):
        """Guards against: the 7% ARB not starting on 2026-10-19. 55 * 0.93 = 51.15 ceils to 52."""
        for ref, ara, arb in ((1000, 1250, 930), (55, 74, 52), (15, 20, 14), (100, 135, 93)):
            with self.subTest(ref=ref):
                self.assert_cell(ref, "2026-10-19", ara, arb)

    def test_nominal_rp11_14_arb_starts_on_2026_10_20(self):
        """Guards against: the nominal Rp1 ARB for Rp11-14 starting on the wrong date. 2026-10-19 itself is
        not asserted for these references (SPEC_FINAL U5)."""
        for day, arb in (("2026-10-16", 12), ("2026-10-18", 12), ("2026-10-20", 13)):
            with self.subTest(day=day):
                self.assert_cell(14, day, ara=18, arb=arb)

    def test_p3_rule_holds_through_2026_12_31(self):
        """Guards against: the P3 rule ending before the last confirmed date; interior dates and
        2026-12-31 give the same 7% and nominal Rp1 results as 2026-10-20."""
        for day in ("2026-11-02", "2026-11-09", "2026-12-01", "2026-12-30", "2026-12-31"):
            for ref, ara, arb in ((1000, 1250, 930), (14, 18, 13), (55, 74, 52)):
                with self.subTest(ref=ref, day=day):
                    self.assert_cell(ref, day, ara, arb)


class ConfirmedObservedAnchorTests(LimitsCase):
    """CONFIRMED by observation (SPEC_FINAL section 8): the 20 observed limit prices, and the worked
    examples of section 8's last bullet. Only the observed side (ARA or ARB) of each anchor is asserted.

    BBCA 2026-10-19 (reference 5,175, observed 4,820, not the 4,825 of the reference-band tick) is the
    anchor that supports the own-band tick choice; the other crossing cells are in ReportedOwnBandTickTests.
    """

    def assert_anchors(self, rows):
        for name, day, ref, side, observed in rows:
            with self.subTest(anchor=name, day=day, ref=ref, side=side):
                if side == "ARA":
                    self.assert_cell(ref, day, ara=observed)
                else:
                    self.assert_cell(ref, day, arb=observed)

    def test_anchor_table_has_the_twenty_rows_of_section_8(self):
        """Guards against: an anchor silently dropped from the table (SPEC_FINAL section 8 lists 20)."""
        self.assertEqual(len(ANCHORS), 20)
        self.assertEqual(len({(name, day) for name, day, *_ in ANCHORS}), 20)

    def test_observed_arb_on_2026_10_19(self):
        """Guards against: the 7% ARB missing on its first day: GOTO, TLKM, BBCA, AMMN, MORA, BYAN
        (CNBC Indonesia, 351 stocks at the 7% ARB), each on the previous close set under the old regime."""
        self.assert_anchors([row for row in ANCHORS if row[1] == "2026-10-19"])

    def test_observed_arb_before_2026_10_19(self):
        """Guards against: the 15% ARB changing: GOTO, PADI, RBMS on 2026-09-28 (50 to 43) and BBCA on
        2026-10-16 (6,075 to 5,175)."""
        self.assert_anchors([row for row in ANCHORS if row[3] == "ARB" and row[1] < "2026-10-19"])

    def test_observed_ara_on_2025_10_21_and_22(self):
        """Guards against: the ARA floor rounding changing (35% / 25% / 20% bands). Six of these twelve
        differ clearly from round-to-nearest."""
        self.assert_anchors([row for row in ANCHORS if row[3] == "ARA"])

    def test_maybank_worked_examples_for_the_7_percent_arb_on_2026_10_20(self):
        """Guards against: the 7% ARB missing on 2026-10-20: Rp100 gives Rp93, Rp1,000 gives Rp930 and
        Rp10,000 gives Rp9,300 (Maybank Trade, 2026-10-20)."""
        for ref, arb in ((100, 93), (1000, 930), (10000, 9300)):
            with self.subTest(ref=ref):
                self.assert_cell(ref, "2026-10-20", arb=arb)


class ConfirmedLimitInvariantTests(LimitsCase):
    """CONFIRMED (SPEC_FINAL sections 5 and 7.2): properties that hold for every valid reference price from
    Rp1 to Rp30,000, not only for the table rows. The ARB on 2026-10-19 for references Rp11-14 is skipped
    (U5); references below Rp50 do not exist in P0."""

    def test_ara_is_not_changed_by_the_october_decisions(self):
        """Guards against: the October decisions touching the ARA: for every valid reference the ARA is the
        same on 2026-09-28, 2026-10-16, 2026-10-19, 2026-10-20 and 2026-12-31 (SPEC_FINAL 7.2)."""
        refs = list(VALID_REFERENCES)
        reference_ara = limit_arrays(refs, "2026-09-28")[0]
        for day in ("2026-10-16", "2026-10-19", "2026-10-20", "2026-11-09", "2026-12-31"):
            with self.subTest(day=day):
                ara = limit_arrays(refs, day)[0]
                moved = [(ref, a, b) for ref, a, b in zip(refs, reference_ara, ara) if a != b]
                self.assertEqual(moved[:10], [], f"{len(moved)} references differ")

    def test_limits_bracket_the_reference_price(self):
        """Guards against: a limit on the wrong side of the reference: ARB <= R <= ARA in every period."""
        for period, day in PERIOD_DAYS:
            with self.subTest(period=period, day=day):
                bad = []
                for ref, ara, arb in grid_results(period, day):
                    skip_arb = period == "P2" and 11 <= ref <= 14
                    if ara < ref or (not skip_arb and arb > ref):
                        bad.append((ref, ara, arb))
                self.assertEqual(bad[:10], [], f"{len(bad)} references")

    def check_direction(self, periods):
        for period, day in PERIOD_DAYS:
            if period not in periods:
                continue
            with self.subTest(period=period, day=day):
                bad = []
                for ref, ara, arb in grid_results(period, day):
                    raw_ara, raw_arb = raw_limits(ref, period)
                    if Fraction(ara) > raw_ara:
                        bad.append((ref, "ARA", ara, float(raw_ara)))
                    if raw_arb is not None and Fraction(arb) < raw_arb:
                        bad.append((ref, "ARB", arb, float(raw_arb)))
                self.assertEqual(bad[:10], [], f"{len(bad)} breaches of the raw limit")

    def test_direction_of_the_rounding_before_the_october_decisions(self):
        """Guards against: rounding the wrong way in P0 and P1. An order priced beyond the limit is
        rejected, so ARA <= R * (1 + a) and ARB >= R * (1 - b), exactly (SPEC_FINAL section 5)."""
        self.check_direction({"P0", "P1"})

    def test_direction_of_the_rounding_from_2026_10_19(self):
        """Guards against: the 7% ARB (and the nominal Rp1 ARB for Rp11-14 from 2026-10-20) being rounded
        past the raw limit, or not applied: ARB >= R * 0.93, ARB >= R - 1 for Rp11-14, in exact arithmetic."""
        self.check_direction({"P2", "P3"})


# SPEC_FINAL 7.2, the "raw -> floor / ceil on the valid-price grid" steps, for the rows whose raw limit
# lies in the same tick band as the reference or where both tick readings agree (so no U3 dependence).
FLOOR_STEPS = (
    (14.85, 14), (16.2, 16), (17.55, 17), (18.9, 18), (20.25, 20), (21.6, 21), (22.95, 22),
    (27.0, 27), (33.75, 33), (67.5, 67), (135.0, 135), (268.65, 268), (270.0, 270), (251.25, 250),
    (252.5, 252), (625.0, 625), (631.25, 630), (1250.0, 1250), (2493.75, 2490), (2500.0, 2500),
    (6250.0, 6250), (6001.2, 6000), (6030.0, 6025), (12000.0, 12000),
)  # fmt: skip
CEIL_STEPS = (
    (9.35, 10), (10.2, 11), (11.05, 12), (11.9, 12), (12.75, 13), (13.6, 14), (14.45, 15), (17.0, 17),
    (21.25, 22), (42.5, 43), (85.0, 85), (169.15, 170), (170.0, 170), (171.7, 172), (429.25, 430),
    (850.0, 850), (1695.75, 1700), (1700.0, 1700), (4241.5, 4250), (4250.0, 4250), (8500.0, 8500),
    (13.95, 14), (14.88, 15), (15.81, 16), (18.6, 19), (23.25, 24), (46.5, 47), (93.0, 93),
    (185.07, 186), (186.0, 186), (187.86, 188), (469.65, 470), (930.0, 930), (1855.35, 1860),
    (1860.0, 1860), (4640.7, 4650), (4650.0, 4650), (9300.0, 9300),
)  # fmt: skip
# The U3 steps: the raw limit lies in a different tick band than the reference, and the reference-band
# tick would give another result (in the comment of OWN_BAND_CELLS).
CROSSING_FLOOR_STEPS = ((6237.5, 6225),)
CROSSING_CEIL_STEPS = (
    (170.85, 171), (186.93, 187), (425.0, 426), (465.0, 466),
    (4250.85, 4260), (4650.93, 4660), (4271.25, 4280), (4673.25, 4680),
)  # fmt: skip


class ConfirmedUnchangedHelpersTests(unittest.TestCase):
    """CONFIRMED (SPEC_FINAL sections 2.1, 4, 5; CONTRACT section 2): the helpers, constants and
    signatures that the correction must keep. They pass on the module before the correction and are
    guards: the new limits are built on them."""

    # SPEC_FINAL section 4. tick_size() works on the band of the value it is given.
    TICK_EDGES = (
        (1, 1), (49, 1), (50, 1), (199, 1), (200, 2), (201, 2), (498, 2), (499, 2), (500, 5),
        (501, 5), (1995, 5), (1999, 5), (2000, 10), (2001, 10), (4990, 10), (4999, 10), (5000, 25),
        (5001, 25), (600000, 25),
    )  # fmt: skip
    # SPEC_FINAL section 3: Rp200 is in the 35% band, Rp5,000 in the 25% band, Rp5,001 in the 20% band.
    BAND_EDGES = ((1, 0.35), (200, 0.35), (201, 0.25), (5000, 0.25), (5001, 0.20), (10000, 0.20))

    def test_tick_table_edges(self):
        """Guards against: a change to the tick table of SPEC_FINAL section 4 (Rp1 / Rp2 / Rp5 / Rp10 / Rp25)."""
        for price, tick in self.TICK_EDGES:
            with self.subTest(price=price):
                self.assertEqual(float(market.tick_size(np.array([float(price)]))[0]), tick)

    def test_band_percentages_at_the_band_edges(self):
        """Guards against: a change to the ARA band edges of SPEC_FINAL section 2.1 (35% to Rp200, 25% to
        Rp5,000, 20% above)."""
        for ref, pct in self.BAND_EDGES:
            with self.subTest(ref=ref):
                self.assertEqual(float(market.band_pct(np.array([float(ref)]))[0]), pct)

    def test_floor_and_ceil_land_on_the_valid_price_grid(self):
        """Guards against: a change to floor_tick / ceil_tick, which round on the grid of valid prices
        (SPEC_FINAL 7.2 raw -> result steps whose result does not depend on U3)."""
        for raw, expected in FLOOR_STEPS:
            with self.subTest(step="floor", raw=raw):
                self.assertEqual(float(market.floor_tick(np.array([raw]))[0]), expected)
        for raw, expected in CEIL_STEPS:
            with self.subTest(step="ceil", raw=raw):
                self.assertEqual(float(market.ceil_tick(np.array([raw]))[0]), expected)

    def test_constants_and_signatures_the_contract_keeps(self):
        """Guards against: a changed constant, signature or Regime field that CONTRACT section 2 lists as
        unchanged (Market.build, panel.py and the frozen reports depend on them)."""
        self.assertEqual(market.TICK_BANDS, ((200, 1), (500, 2), (2000, 5), (5000, 10)))
        self.assertEqual(market.TICK_TOP, 25)
        self.assertEqual(market.BANDS, ((200, 0.35), (5000, 0.25), (float("inf"), 0.20)))
        self.assertEqual(market.SPECIAL_BOARD_PCT, 0.10)
        self.assertEqual(market.LOT_SIZE, 100)
        self.assertEqual(market.RULES_START, datetime.date(2019, 7, 29))
        self.assertEqual(market.Fees(), market.Fees(buy=0.0015, sell=0.0025))
        names = [field.name for field in dataclasses.fields(market.Regime)]
        self.assertEqual(names[:5], ["start", "arb_flat", "floor", "small_abs", "label"])
        regime = market.Regime(datetime.date(2026, 9, 28), 0.15, 1, True, "label")
        self.assertEqual(
            (regime.start, regime.arb_flat, regime.floor, regime.small_abs, regime.label),
            (datetime.date(2026, 9, 28), 0.15, 1, True, "label"),
        )
        for name, required in (
            ("limits", ["ref", "days"]),
            ("special_limits", ["ref"]),
            ("regime_index", ["days"]),
            ("regime_labels", []),
        ):
            with self.subTest(function=name):
                params = list(inspect.signature(getattr(market, name)).parameters.values())
                # positional-compatible: the same leading parameters; anything added must be optional
                self.assertEqual([p.name for p in params[: len(required)]], required)
                self.assertTrue(all(p.default is not p.empty for p in params[len(required) :]))

    def test_dates_before_the_schedule_are_still_refused(self):
        """Guards against: limits() or regime_index() accepting a date before 2019-07-29 (CONTRACT section
        2 and 1: ValueError, unchanged), including one element of a mixed call."""
        for day in ("2019-07-28", "2019-07-26", "2000-01-03"):
            with self.subTest(day=day):
                with self.assertRaises(ValueError):
                    lim(1000, day)
                with self.assertRaises(ValueError):
                    market.regime_index(np.array([day], dtype="datetime64[D]"))
        with self.assertRaises(ValueError):
            market.limits(
                np.array([1000.0, 1000.0]),
                np.array(["2026-10-16", "2019-07-28"], dtype="datetime64[D]"),
            )
        # The first scheduled date itself is accepted.
        self.assertEqual(lim(1000, "2019-07-29"), (1250, 750))


class ConfirmedVectorSemanticsTests(LimitsCase):
    """CONTRACT section 2 and item 8: limits() is vectorised and element-wise. A (tickers, sessions) call
    mixes regimes, whatever the order of the dates, and keeps the broadcast shape. The expected cells are
    CONFIRMED cells of SPEC_FINAL 7.1 (None: n/a in P0 below Rp50, or U5) or regime facts that the
    existing tests of tests/test_market.py already state."""

    MIXED_DAYS = (
        "2026-09-25",
        "2026-09-28",
        "2026-10-16",
        "2026-10-19",
        "2026-10-20",
        "2026-12-31",
    )
    MIXED_ROWS = (  # (reference, ARA per date, ARB per date)
        (14, (None, 18, 18, 18, 18, 18), (None, 12, 12, None, 13, 13)),
        (15, (None, 20, 20, 20, 20, 20), (None, 13, 13, 14, 14, 14)),
        (50, (67,) * 6, (50, 43, 43, 47, 47, 47)),
        (100, (135,) * 6, (85, 85, 85, 93, 93, 93)),
        (1000, (1250,) * 6, (850, 850, 850, 930, 930, 930)),
        (5000, (6250,) * 6, (4250, 4250, 4250, 4650, 4650, 4650)),
        (10000, (12000,) * 6, (8500, 8500, 8500, 9300, 9300, 9300)),
    )
    # Reference 1000 across the older regimes, in a deliberately unsorted order:
    # 2019 symmetric, COVID 10% and 7%, stage I 15%, stage II symmetric, April 2025 15%, Rp1 reform 15%.
    OLD_REGIME_DAYS = (
        "2026-10-16",
        "2019-08-01",
        "2023-09-04",
        "2020-03-13",
        "2025-04-08",
        "2020-03-10",
        "2023-06-05",
        "2026-09-28",
    )
    OLD_REGIME_ARB = (850, 750, 750, 930, 850, 900, 850, 850)

    def expected(self):
        refs = np.array([row[0] for row in self.MIXED_ROWS], dtype=float)
        days = np.array(self.MIXED_DAYS, dtype="datetime64[D]")
        ara = np.array([[np.nan if v is None else v for v in row[1]] for row in self.MIXED_ROWS])
        arb = np.array([[np.nan if v is None else v for v in row[2]] for row in self.MIXED_ROWS])
        return refs, days, ara, arb

    def assert_matches(self, got, want, label):
        for side, got_side, want_side in (("ARA", got[0], want[0]), ("ARB", got[1], want[1])):
            self.assertEqual(got_side.shape, want_side.shape, f"{label}: {side} shape")
            asserted = ~np.isnan(want_side)
            wrong = [
                (int(i), int(j), float(got_side[i, j]), float(want_side[i, j]))
                for i, j in np.argwhere(asserted & (got_side != want_side))
            ]
            self.assertEqual(wrong, [], f"{label}: {side} cells (row, column, got, expected)")

    def test_two_dimensional_call_mixing_regimes_keeps_shape_and_values(self):
        """Guards against: a vectorised call applying one regime to the whole array, or flattening it. Two
        (tickers, sessions) arrays, as Market.build passes them, with P0, P1, P2 and P3 dates in one call."""
        refs, days, want_ara, want_arb = self.expected()
        ref_grid = np.repeat(refs[:, None], len(days), axis=1)
        day_grid = np.repeat(days[None, :], len(refs), axis=0)
        got = market.limits(ref_grid, day_grid)
        self.assert_matches(got, (want_ara, want_arb), "2-D x 2-D")
        for side, out in zip(("ARA", "ARB"), got):
            self.assertEqual(out.dtype.kind, "f", f"{side} is a float array")

    def test_broadcast_forms_and_date_order_give_the_same_matrix(self):
        """Guards against: a result that depends on the broadcast form or on the order of the dates: the
        sessions row broadcast over tickers, a (tickers, 1) column against a (1, sessions) row, and
        both with the sessions reversed (unsorted dates)."""
        refs, days, want_ara, want_arb = self.expected()
        for order_name, order in (("sorted", slice(None)), ("reversed", slice(None, None, -1))):
            ref_grid = np.repeat(refs[:, None], len(days), axis=1)[:, order]
            forms = {
                "(T, S) x (S,)": (ref_grid, days[order]),
                "(T, 1) x (1, S)": (refs[:, None], days[order][None, :]),
            }
            want = (want_ara[:, order], want_arb[:, order])
            for name, (ref_arg, day_arg) in forms.items():
                with self.subTest(form=name, sessions=order_name):
                    self.assert_matches(market.limits(ref_arg, day_arg), want, name)

    def test_inputs_are_left_untouched_and_shapes_follow_the_broadcast(self):
        """Guards against: limits() writing into its arguments, or returning a shape other than the
        broadcast shape (dates up to 2026-10-16 only, so it holds before and after the correction)."""
        refs = np.array([[1000.0, 100.0, 55.0], [5000.0, 10000.0, 200.0]])
        days = np.array(["2026-09-25", "2026-09-28", "2026-10-16"], dtype="datetime64[D]")
        refs_before, days_before = refs.copy(), days.copy()
        ara, arb = market.limits(refs, days)
        np.testing.assert_array_equal(refs, refs_before)
        np.testing.assert_array_equal(days, days_before)
        self.assertEqual((ara.shape, arb.shape), ((2, 3), (2, 3)))
        # Cell (i, j) is reference refs[i, j] on days[j]: 1000 and 5000 on 2026-09-25 (P0), 100 and 10000
        # on 2026-09-28 (P1), 55 and 200 on 2026-10-16 (P1; 55 * 0.85 = 46.75 ceils to 47).
        np.testing.assert_array_equal(ara, [[1250, 135, 74], [6250, 12000, 270]])
        np.testing.assert_array_equal(arb, [[850, 85, 47], [4250, 8500, 170]])

    def test_every_accepted_date_form_gives_the_same_limits(self):
        """Guards against: limits() accepting fewer input forms than before: ISO strings, datetime.date
        objects, datetime64[D] and datetime64[ns] arrays for the dates, and lists, int arrays and float
        arrays for the references (CONTRACT section 2: array-likes), mixing the older regimes in one
        unsorted call (dates up to 2026-10-16)."""
        refs = np.full(len(self.OLD_REGIME_DAYS), 1000.0)
        forms = {
            "ISO strings": list(self.OLD_REGIME_DAYS),
            "datetime.date": [datetime.date.fromisoformat(d) for d in self.OLD_REGIME_DAYS],
            "datetime64[D]": np.array(self.OLD_REGIME_DAYS, dtype="datetime64[D]"),
            "datetime64[ns]": np.array(self.OLD_REGIME_DAYS, dtype="datetime64[ns]"),
        }
        for name, days in forms.items():
            with self.subTest(form=name):
                ara, arb = market.limits(refs, days)
                self.assertEqual(ara.tolist(), [1250] * len(refs))
                self.assertEqual(arb.tolist(), list(self.OLD_REGIME_ARB))
        ref_forms = {
            "list of ints": [1000] * len(refs),
            "int array": np.full(len(refs), 1000),
            "float array": refs,
        }
        for name, ref_arg in ref_forms.items():
            with self.subTest(reference_form=name):
                ara, arb = market.limits(ref_arg, list(self.OLD_REGIME_DAYS))
                self.assertEqual(ara.tolist(), [1250] * len(refs))
                self.assertEqual(arb.tolist(), list(self.OLD_REGIME_ARB))


class ReportedRp1ReferenceArbTests(LimitsCase):
    """REPORTED (SPEC_FINAL U4, section 6): the ARB for a reference of Rp1. The computed ARB is 0; the
    result 1 follows from the minimum price Rp1 and was not observed directly."""

    def test_arb_of_a_rp1_reference_is_floored_at_the_minimum_price(self):
        """Guards against: an ARB of 0 (a limit below the minimum price) in P1, P2 and P3; ARA = 2."""
        for day in P1_TO_P3_DATES:
            with self.subTest(day=day):
                self.assert_cell(1, day, ara=2, arb=1)


class ReportedOwnBandTickTests(LimitsCase):
    """REPORTED, with added support (SPEC_FINAL U3, section 5, last bullet of 7.2): at a band crossing the
    limit is rounded on the valid-price grid of the limit's own band, not with the tick of the reference
    price. Supported by BBCA 2026-10-19 (4,820, not 4,825; in ConfirmedObservedAnchorTests) and, not noted
    in SPEC_FINAL, by BABY 2025-10-21 (reference 430 in tick 2, ARA 535 in tick 5; the reference-band tick
    would give the off-grid 536). The cells are flagged REPORTED; a failure here is a failure of the
    own-band reading, not of a confirmed rule."""

    def check_cells(self, side, column, days):
        for ref, cell_side, *values in OWN_BAND_CELLS:
            if cell_side != side:
                continue
            for day in days:
                with self.subTest(ref=ref, side=side, day=day):
                    if side == "ARA":
                        self.assert_cell(ref, day, ara=values[column])
                    else:
                        self.assert_cell(ref, day, arb=values[column])

    def check_tightness(self, periods):
        for period, day in PERIOD_DAYS:
            if period not in periods:
                continue
            with self.subTest(period=period, day=day):
                bad = []
                minimum = MINIMUM_PRICE[period]
                for ref, ara, arb in grid_results(period, day):
                    raw_ara, raw_arb = raw_limits(ref, period)
                    # The ARA is the largest valid price not above the raw ARA ...
                    top = int(ara)
                    if not top <= raw_ara < top + spec_tick(top):
                        bad.append((ref, "ARA", ara, float(raw_ara)))
                    # ... and the ARB the smallest valid price not below the raw ARB, or the minimum.
                    if raw_arb is not None:
                        bottom = int(arb)
                        tight = bottom == minimum or bottom - spec_tick(bottom - 1) < raw_arb
                        if not (raw_arb <= bottom and tight):
                            bad.append((ref, "ARB", arb, float(raw_arb)))
                self.assertEqual(
                    bad[:10], [], f"{len(bad)} limits are not the tightest valid price"
                )

    def test_ara_that_crosses_into_a_coarser_tick_band(self):
        """Guards against: the ARA of 4,990 (raw 6,237.5, in the tick-25 band) rounding with the tick 10 of
        the reference: 6,225, not 6,230."""
        self.check_cells("ARA", 0, P0_DATES + P1_TO_P3_DATES)

    def test_arb_that_crosses_into_a_finer_tick_band_before_2026_10_19(self):
        """Guards against: the 15% ARB of 201 (raw 170.85), 500 (425), 5,001 (4,250.85) and 5,025 (4,271.25)
        rounding with the tick of the reference instead of that of the limit's own band."""
        self.check_cells("ARB", 0, P0_DATES)
        self.check_cells("ARB", 1, P1_DATES)

    def test_arb_that_crosses_into_a_finer_tick_band_from_2026_10_19(self):
        """Guards against: the 7% ARB of 201 (raw 186.93), 500 (465), 5,001 (4,650.93) and 5,025
        (4,673.25) rounding with the tick of the reference: 187, 466, 4,660 and 4,680."""
        self.check_cells("ARB", 2, P2_DATES)
        self.check_cells("ARB", 3, P3_DATES)

    def test_floor_and_ceil_tick_use_the_tick_of_the_raw_value(self):
        """Guards against: floor_tick / ceil_tick taking the tick of anything but the value they round
        (the raw steps of the crossing rows of SPEC_FINAL 7.2)."""
        for raw, expected in CROSSING_FLOOR_STEPS:
            with self.subTest(step="floor", raw=raw):
                self.assertEqual(float(market.floor_tick(np.array([raw]))[0]), expected)
        for raw, expected in CROSSING_CEIL_STEPS:
            with self.subTest(step="ceil", raw=raw):
                self.assertEqual(float(market.ceil_tick(np.array([raw]))[0]), expected)

    def test_every_limit_is_a_valid_price_on_the_tick_table(self):
        """Guards against: a limit that is not a valid price (a whole rupiah, a multiple of the tick of its
        own band), for every valid reference from Rp1 to Rp30,000. Not asserted for the ARB on 2026-10-19
        with a reference of Rp11-14 (U5)."""
        for period, day in PERIOD_DAYS:
            with self.subTest(period=period, day=day):
                bad = []
                for ref, ara, arb in grid_results(period, day):
                    if not is_valid_price(ara):
                        bad.append((ref, "ARA", ara))
                    skip_arb = period == "P2" and 11 <= ref <= 14
                    if not skip_arb and not is_valid_price(arb, MINIMUM_PRICE[period]):
                        bad.append((ref, "ARB", arb))
                self.assertEqual(bad[:10], [], f"{len(bad)} limits are not valid prices")

    def test_limits_are_the_tightest_valid_prices_before_the_october_decisions(self):
        """Guards against: rounding to a price other than the tightest one in P0 and P1: the ARA is the
        largest valid price not above the raw limit and the ARB the smallest not below it (or the minimum
        price), in exact arithmetic."""
        self.check_tightness({"P0", "P1"})

    def test_limits_are_the_tightest_valid_prices_from_2026_10_19(self):
        """Guards against: a wrong raw limit, or rounding to anything but the tightest valid price, under
        the 7% ARB and the nominal Rp1 ARB for Rp11-14 (P2 for Rp11-14 is not asserted: U5)."""
        self.check_tightness({"P2", "P3"})


class ConfirmedSpecialBoardPercentageTests(unittest.TestCase):
    """CONFIRMED (SPEC_FINAL sections 2.2, 2.4 and 12): the special-monitoring board, whose rule the
    Acceleration board and DINFRA share: 10% / 10% above Rp10, +/- Rp1 in the Rp1-10 band. Only cells
    where no rounding is involved are asserted here, so that the rounding convention of section 7.3
    (REPORTED, in ReportedSpecialBoardLimitsTests) plays no part. special_limits() takes no date: the
    same values hold in P1, P2 and P3, and the correction leaves it unchanged."""

    # (reference, ARA, ARB): R * 1.1 and R * 0.9 are whole rupiah and valid prices, derived by hand.
    EXACT_ROWS = (
        (20, 22, 18),
        (50, 55, 45),
        (100, 110, 90),
        (200, 220, 180),
        (500, 550, 450),
        (1000, 1100, 900),
        (2000, 2200, 1800),
        (5000, 5500, 4500),
        (10000, 11000, 9000),
        (20000, 22000, 18000),
    )

    def test_ten_percent_both_ways_where_no_rounding_is_involved(self):
        """Guards against: the special-monitoring board ceasing to be 10% / 10% above Rp10."""
        for ref, ara, arb in self.EXACT_ROWS:
            with self.subTest(ref=ref):
                got_ara, got_arb = market.special_limits(np.array([float(ref)]))
                self.assertEqual((float(got_ara[0]), float(got_arb[0])), (ara, arb))

    def test_rp1_10_band_moves_a_nominal_rupiah(self):
        """Guards against: the Rp1-10 band turning into a percentage band: ARA = R + 1 for R = 1 to 10
        and ARB = R - 1 for R = 2 to 10. The ARB of R = 1 is floored at the minimum price and is REPORTED
        (ReportedSpecialBoardLimitsTests)."""
        for ref in range(1, 11):
            with self.subTest(ref=ref):
                got_ara, got_arb = market.special_limits(np.array([float(ref)]))
                self.assertEqual(float(got_ara[0]), ref + 1)
                if ref > 1:
                    self.assertEqual(float(got_arb[0]), ref - 1)


class ReportedSpecialBoardLimitsTests(unittest.TestCase):
    """REPORTED (SPEC_FINAL section 7.3, section 12): special_limits() on the cells whose value depends on
    the rounding convention (ARA floored, ARB ceiled on the valid-price grid), which SPEC_FINAL assumes
    carries over from the regular board, and the floor of the Rp1 reference at the minimum price. The
    function takes no date; the correction leaves it unchanged."""

    def test_section_7_3_rows(self):
        """Guards against: a change to special_limits(): the rows of SPEC_FINAL 7.3, one reference per call."""
        for ref, ara, arb in SECTION_7_3:
            with self.subTest(ref=ref):
                got_ara, got_arb = market.special_limits(np.array([float(ref)]))
                self.assertEqual((float(got_ara[0]), float(got_arb[0])), (ara, arb))

    def test_section_7_3_rows_in_one_vector_call(self):
        """Guards against: a vector call of special_limits() differing from its element-wise results, or
        losing the shape of a 2-D input."""
        refs = np.array([float(row[0]) for row in SECTION_7_3])
        ara, arb = market.special_limits(refs)
        self.assertEqual(ara.tolist(), [row[1] for row in SECTION_7_3])
        self.assertEqual(arb.tolist(), [row[2] for row in SECTION_7_3])
        ara2, arb2 = market.special_limits(refs[:12].reshape(3, 4))
        self.assertEqual((ara2.shape, arb2.shape), ((3, 4), (3, 4)))
        self.assertEqual(ara2.ravel().tolist(), ara.tolist()[:12])

    def test_arb_of_a_rp1_reference_is_floored_at_the_minimum_price(self):
        """Guards against: an ARB of 0 for a reference of Rp1 on the special board (1 - 1 = 0 is below the
        minimum price Rp1); ARA = 2."""
        ara, arb = market.special_limits(np.array([1.0]))
        self.assertEqual((float(ara[0]), float(arb[0])), (2, 1))


class BoardDistinctionTests(unittest.TestCase):
    """CONTRACT sections 0, 4 and item 5: the data has no board field, so Market.build treats a bar as
    thin, and so possibly on the 10% special board, when it is one-price (high == low == close). A thin bar
    at the special-board limit is a lock; a regular bar at the same price is judged against the regular
    limit. Every case uses a regular reference of Rp1,000; dates are weekdays. Market.build and
    special_limits() are unchanged by the correction."""

    @staticmethod
    def session_market(day, cases):
        """A Market whose last session is `day` (a weekday); every name was flat at Rp1,000 before it.

        cases: one (close, low, high) per name for the last session; the reference (prev) stays Rp1,000.
        """
        start = np.busday_offset(np.datetime64(day, "D"), -4, roll="backward")
        tickers, dates, arrays = flat_market(
            n_tickers=len(cases), n_sessions=5, price=1000.0, start=str(start)
        )
        if str(dates[-1]) != day:
            raise AssertionError(f"test setup: the last session is {dates[-1]}, not {day}")
        for i, (close, low, high) in enumerate(cases):
            arrays["close"][i, -1] = close
            arrays["low"][i, -1] = low
            arrays["high"][i, -1] = high
        return rebuild(tickers, dates, arrays)

    def test_thin_bar_at_the_special_board_lower_limit_is_locked_on_2026_10_16(self):
        """Guards against: a one-price bar 10% below the reference not counting as locked down, or a
        regular bar at the same price counting as locked. On 2026-10-16 the regular ARB of Rp1,000 is
        850 (15%); the special-board lower limit is 900 (10%)."""
        cases = {
            "one-price bar at 900 (the special-board limit)": ((900.0, 900.0, 900.0), True),
            "regular bar closing at 900": ((900.0, 900.0, 1000.0), False),
            "regular bar closing at 850 (the regular ARB)": ((850.0, 850.0, 1000.0), True),
            "one-price bar at 901": ((901.0, 901.0, 901.0), False),
        }
        market_ = self.session_market("2026-10-16", [bar for bar, _ in cases.values()])
        for i, (name, (_, locked)) in enumerate(cases.items()):
            with self.subTest(case=name):
                self.assertEqual(bool(market_.lock_down[i, -1]), locked)
                self.assertFalse(market_.lock_up[i, -1])

    def test_lock_up_side_is_the_same_before_and_after_the_october_decisions(self):
        """Guards against: the correction touching the ARA side: on 2026-10-16, 2026-10-19 and 2026-10-20 a
        one-price bar at 1,100 (the special-board ARA) and a regular bar at the ARA 1,250 are locked up; a
        regular bar at 1,100 or 1,249 and a one-price bar at 1,099 are not."""
        cases = {
            "one-price bar at 1100 (the special-board limit)": ((1100.0, 1100.0, 1100.0), True),
            "regular bar closing at 1100": ((1100.0, 1000.0, 1100.0), False),
            "regular bar closing at 1250 (the ARA)": ((1250.0, 1000.0, 1250.0), True),
            "regular bar closing at 1249": ((1249.0, 1000.0, 1250.0), False),
            "one-price bar at 1099": ((1099.0, 1099.0, 1099.0), False),
        }
        for day in ("2026-10-16", "2026-10-19", "2026-10-20"):
            market_ = self.session_market(day, [bar for bar, _ in cases.values()])
            for i, (name, (_, locked)) in enumerate(cases.items()):
                with self.subTest(day=day, case=name):
                    self.assertEqual(bool(market_.lock_up[i, -1]), locked)
                    self.assertFalse(market_.lock_down[i, -1])


class EarlierRegimesGoldenMasterTests(unittest.TestCase):
    """Regression guard (CONTRACT section 1 and item 9): from 2019-07-29 through 2026-10-18 every output
    of limits(), regime_index() and special_limits() is identical to what the module returned before the
    correction, read from tests/fixtures/market_limits_golden_20261109.json (see the module docstring
    for how it was captured). These tests pass on the module before the correction by construction; a
    failure means the correction changed a regime it must not touch."""

    REGIME_STARTS = (
        "2019-07-29",
        "2020-03-10",
        "2020-03-13",
        "2023-06-05",
        "2023-09-04",
        "2025-04-08",
        "2026-09-28",
    )
    # Reference prices that the fixture must contain: band edges and tick edges of SPEC_FINAL section 4.
    REQUIRED_REFERENCES = (
        1, 2, 9, 10, 11, 14, 15, 16, 49, 50, 51, 199, 200, 201, 202, 499, 500, 505, 1000, 1995, 2000,
        4990, 5000, 5001, 5025, 10000, 30000,
    )  # fmt: skip

    @classmethod
    def setUpClass(cls):
        cls.golden = load_golden()

    def mismatches(self, day, refs, want_ara, want_arb):
        got_ara, got_arb = market.limits(
            np.array(refs, dtype=float), np.full(len(refs), np.datetime64(day, "D"))
        )
        out = []
        for ref, ga, gb, wa, wb in zip(
            refs, got_ara.tolist(), got_arb.tolist(), want_ara, want_arb
        ):
            if ga != wa or gb != wb:
                out.append((ref, (ga, gb), (wa, wb)))
        return out

    def test_fixture_covers_every_regime_and_the_required_references(self):
        """Guards against: a golden master that is too thin to guard anything: every regime start date
        and the day before it, interior and weekend dates, nothing after 2026-10-18, and every band edge
        and tick edge reference."""
        g = self.golden
        self.assertRegex(g["captured_from"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(g["dates"], sorted(g["dates"]))
        self.assertEqual(set(g["dates"]), set(g["limits"]))
        self.assertGreaterEqual(len(g["dates"]), 35)
        self.assertEqual((g["dates"][0], g["dates"][-1]), ("2019-07-29", "2026-10-18"))
        for start in self.REGIME_STARTS:
            day_before = (
                datetime.date.fromisoformat(start) - datetime.timedelta(days=1)
            ).isoformat()
            self.assertIn(start, g["dates"])
            if start != "2019-07-29":
                self.assertIn(day_before, g["dates"], f"the day before {start}")
        self.assertTrue(set(self.REQUIRED_REFERENCES) <= set(g["references"]))
        for day in g["dates"]:
            entry = g["limits"][day]
            self.assertEqual(len(entry["ara"]), len(g["references"]), day)
            self.assertEqual(len(entry["arb"]), len(g["references"]), day)
            self.assertEqual(len(entry["off_grid_ara"]), len(g["off_grid_references"]), day)
            self.assertEqual(len(entry["off_grid_arb"]), len(g["off_grid_references"]), day)

    def test_limits_equal_the_captured_values_on_every_date(self):
        """Guards against: any change of ARA or ARB for a valid-price reference on a date from 2019-07-29
        through 2026-10-18, one subTest per date."""
        g = self.golden
        for day in g["dates"]:
            with self.subTest(day=day):
                entry = g["limits"][day]
                bad = self.mismatches(day, g["references"], entry["ara"], entry["arb"])
                self.assertEqual(
                    bad[:10], [], f"{len(bad)} references changed (ref, got, captured)"
                )

    def test_off_grid_references_are_unchanged_through_2026_10_18(self):
        """Guards against: a change for references that are not valid prices (10.5, 14.5, 200.5, 4,999.5,
        5,000.5): CONTRACT section 1 keeps every output through 2026-10-18 identical, valid price or not."""
        g = self.golden
        for day in g["dates"]:
            with self.subTest(day=day):
                entry = g["limits"][day]
                bad = self.mismatches(
                    day, g["off_grid_references"], entry["off_grid_ara"], entry["off_grid_arb"]
                )
                self.assertEqual(bad, [])

    def test_one_matrix_call_over_every_captured_regime(self):
        """Guards against: the vectorised path differing from the one-date calls: one call with a
        (references, dates) matrix mixing every regime, the dates in an unsorted order."""
        g = self.golden
        refs = g["references"] + g["off_grid_references"]
        dates = g["dates"]
        order = list(range(0, len(dates), 2)) + list(range(1, len(dates), 2))[::-1]
        days = np.array([dates[i] for i in order], dtype="datetime64[D]")
        columns = [g["limits"][dates[i]] for i in order]
        want_ara = np.array([c["ara"] + c["off_grid_ara"] for c in columns]).T
        want_arb = np.array([c["arb"] + c["off_grid_arb"] for c in columns]).T
        ara, arb = market.limits(np.array(refs, dtype=float)[:, None], days[None, :])
        self.assertEqual(ara.shape, (len(refs), len(dates)))
        np.testing.assert_array_equal(ara, want_ara)
        np.testing.assert_array_equal(arb, want_arb)

    def test_regime_index_is_unchanged_through_2026_10_18(self):
        """Guards against: a shifted or inserted regime before 2026-09-28: the index of every captured
        date, in one call (the indexes into REGIMES that panel.py and e5.py key their reports on)."""
        g = self.golden
        got = market.regime_index(np.array(g["dates"], dtype="datetime64[D]"))
        self.assertEqual(got.tolist(), [g["limits"][day]["regime_index"] for day in g["dates"]])

    def test_regime_labels_that_start_by_2026_09_28_are_unchanged(self):
        """Guards against: a renamed or altered regime: frozen reports are keyed by these label strings
        (CONTRACT section 2). Entries that start later are not asserted here."""
        got = [entry for entry in market.regime_labels() if entry["start"] <= "2026-09-28"]
        self.assertEqual(got, self.golden["regime_labels_through_2026_09_28"])

    def test_special_limits_equal_the_captured_values(self):
        """Guards against: any change of special_limits() (the 10% special-monitoring board), for the same
        references, valid and off-grid."""
        g = self.golden
        for name, refs in (("on-grid", g["references"]), ("off-grid", g["off_grid_references"])):
            with self.subTest(references=name):
                ara, arb = market.special_limits(np.array(refs, dtype=float))
                key = "" if name == "on-grid" else "off_grid_"
                self.assertEqual(ara.tolist(), g["special_limits"][key + "ara"])
                self.assertEqual(arb.tolist(), g["special_limits"][key + "arb"])


class UnconfirmedPeriodConventionValuesTests(LimitsCase):
    """A CONVENTION, not an exchange rule (CONTRACT section 3; SPEC_FINAL section 9): no rule is confirmed
    for any date after 2026-12-31, so limits() carries the last confirmed rule (the 2026-12-31 values:
    ARB 7%, nominal Rp1 for Rp11-14, ARA unchanged) forward. It is the cautious choice for exits and a
    modelling choice only. These tests assert that convention and nothing about what the exchange does or
    will do after 2026-12-31. Warnings are ignored here; they are tested in
    UnconfirmedPeriodConventionMechanismTests."""

    def test_the_contract_example_carries_the_last_confirmed_rule_forward(self):
        """Guards against: the announced symmetric lower limit being applied after the last confirmed date.
        By the convention limits(1000, "2027-01-04") is ARA 1250 and ARB 930 (the 2026-12-31 values), not
        the symmetric 750; this is how the model treats an unconfirmed period, not what the exchange does."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ara, arb = market.limits(1000, "2027-01-04")
        self.assertEqual(np.asarray(ara).item(), 1250)
        self.assertEqual(np.asarray(arb).item(), 930)
        self.assertNotEqual(
            np.asarray(arb).item(), 750, "the announced symmetric limit is not applied (convention)"
        )

    def test_confirmed_table_cells_are_carried_forward(self):
        """Guards against: a rule other than the 2026-12-31 one after that date: every cell that
        SECTION_7_2 asserts for P3 (ARA, and ARB including the nominal Rp1 rule for Rp11-14) is the result
        on 2027-01-01, 2027-01-04, 2027-06-30 and 2030-01-01 by the convention."""
        for ref, ara, *_, arb in SECTION_7_2:
            for day in AFTER_LAST_CONFIRMED_DATE:
                with self.subTest(ref=ref, day=day):
                    got_ara, got_arb = lim_quiet(ref, day)
                    if ara is not None:
                        self.assertEqual(got_ara, ara)
                    if arb is not None:
                        self.assertEqual(got_arb, arb)

    def test_every_valid_reference_gets_its_2026_12_31_limits(self):
        """Guards against: any reference price whose limits after 2026-12-31 differ from its 2026-12-31
        limits (the convention in full, for every valid price from Rp1 to Rp30,000)."""
        refs = list(VALID_REFERENCES)
        want_ara, want_arb = limit_arrays(refs, "2026-12-31")
        for day in AFTER_LAST_CONFIRMED_DATE:
            with self.subTest(day=day):
                ara, arb = limit_arrays(refs, day)
                moved = [
                    (ref, (a, b), (wa, wb))
                    for ref, a, b, wa, wb in zip(refs, ara, arb, want_ara, want_arb)
                    if a != wa or b != wb
                ]
                self.assertEqual(moved[:10], [], f"{len(moved)} references differ from 2026-12-31")

    def test_mixed_date_call_carries_forward_only_the_late_elements(self):
        """Guards against: the convention leaking into confirmed dates, or the late dates being treated as
        confirmed ones, within one call that mixes dates around 2026-12-31 and 2027-01-04 (and a P1 date)."""
        refs = np.array([1000.0, 100.0, 5000.0, 10000.0, 1000.0, 14.0, 11.0, 1000.0])
        days = np.array(
            [
                "2026-12-30",  # confirmed, P3
                "2026-12-31",  # the last confirmed date
                "2027-01-01",  # by the convention
                "2027-01-04",  # by the convention
                "2026-10-16",  # P1: 15%, unaffected
                "2026-12-31",
                "2027-01-01",
                "2030-01-01",
            ],
            dtype="datetime64[D]",
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ara, arb = market.limits(refs, days)
        self.assertEqual(ara.tolist(), [1250, 135, 6250, 12000, 1250, 18, 14, 1250])
        self.assertEqual(arb.tolist(), [930, 93, 4650, 9300, 850, 13, 10, 930])


class UnconfirmedPeriodConventionMechanismTests(LimitsCase):
    """The machinery of the CONVENTION of CONTRACT section 3 (a: no raise; b: the warning; d: the
    dedicated UNCONFIRMED regime entry): how the model marks the period after 2026-12-31 as unconfirmed.
    Not claims about the exchange."""

    ISO_DAYS = (
        "2019-07-29",
        "2026-10-16",
        "2026-12-30",
        "2026-12-31",
        "2027-01-01",
        "2027-01-04",
        "2030-01-01",
    )
    LATE = (False, False, False, False, True, True, True)

    def test_the_last_confirmed_date_is_2026_12_31(self):
        """Guards against: the boundary of the confirmed period moving (CONTRACT section 3)."""
        self.assertEqual(market.RULES_CONFIRMED_THROUGH, datetime.date(2026, 12, 31))

    def test_the_warning_category_is_a_user_warning(self):
        """Guards against: a warning class that the warnings machinery or a caller cannot filter as a
        UserWarning."""
        self.assertTrue(issubclass(market.RulesUnconfirmedWarning, UserWarning))

    def test_unconfirmed_flags_dates_after_the_last_confirmed_date(self):
        """Guards against: unconfirmed() flagging 2026-12-31 or missing 2027-01-01, for every date form
        that limits() accepts (ISO strings, datetime.date, datetime64[D], datetime64[ns])."""
        forms = {
            "ISO strings": list(self.ISO_DAYS),
            "datetime.date": [datetime.date.fromisoformat(d) for d in self.ISO_DAYS],
            "datetime64[D]": np.array(self.ISO_DAYS, dtype="datetime64[D]"),
            "datetime64[ns]": np.array(self.ISO_DAYS, dtype="datetime64[ns]"),
        }
        for name, days in forms.items():
            with self.subTest(form=name):
                flags = np.asarray(market.unconfirmed(days))
                self.assertEqual(flags.dtype, np.dtype(bool))
                self.assertEqual(flags.tolist(), list(self.LATE))

    def test_unconfirmed_keeps_the_shape_of_a_two_dimensional_input_and_takes_a_scalar(self):
        """Guards against: unconfirmed() flattening a (tickers, sessions) array, or refusing the scalar date
        that limits() accepts (CONTRACT section 3 uses limits(1000, "2027-01-04"))."""
        days = np.array(
            [["2026-10-16", "2027-01-04"], ["2026-12-31", "2027-01-01"]], dtype="datetime64[D]"
        )
        flags = np.asarray(market.unconfirmed(days))
        self.assertEqual(flags.shape, (2, 2))
        self.assertEqual(flags.tolist(), [[False, True], [False, True]])
        self.assertEqual(np.asarray(market.unconfirmed("2027-01-04")).item(), True)
        self.assertEqual(np.asarray(market.unconfirmed("2026-12-31")).item(), False)

    def test_limits_does_not_raise_because_of_the_date(self):
        """Guards against: the daily jobs stopping after 2026-12-31: limits() returns two arrays of the
        broadcast shape for dates after the last confirmed date, in every accepted form."""
        refs = np.array([1000.0, 14.0, 5000.0, 55.0])
        forms = {
            "ISO strings": ["2027-01-01", "2027-01-04", "2027-06-30", "2030-01-01"],
            "datetime64[D]": np.array(
                ["2027-01-01", "2027-01-04", "2027-06-30", "2030-01-01"], dtype="datetime64[D]"
            ),
        }
        for name, days in forms.items():
            with self.subTest(form=name):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    ara, arb = market.limits(refs, days)
                self.assertEqual((ara.shape, arb.shape), ((4,), (4,)))

    def test_limits_warns_in_every_call_with_a_date_after_the_last_confirmed_date(self):
        """Guards against: a silent unconfirmed period, or a warning only on the first call: with every
        warning shown, each call that has at least one date after 2026-12-31 records a
        RulesUnconfirmedWarning."""
        cases = {
            "scalars": (1000, "2027-01-04"),
            "one element": (np.array([1000.0]), np.array(["2027-01-01"], dtype="datetime64[D]")),
            "far future": (np.array([14.0]), ["2030-01-01"]),
            "2-D with one late date": (
                np.array([[1000.0, 1000.0], [100.0, 100.0]]),
                np.array(["2026-12-31", "2027-06-30"], dtype="datetime64[D]"),
            ),
        }
        for name, (ref, days) in cases.items():
            for call in (1, 2, 3):
                with self.subTest(case=name, call=call):
                    _, caught = unconfirmed_warnings(lambda: market.limits(ref, days))
                    self.assertGreaterEqual(len(caught), 1)

    def test_limits_is_silent_on_or_before_the_last_confirmed_date(self):
        """Guards against: a spurious RulesUnconfirmedWarning on confirmed dates, 2026-12-31 included: a
        call whose every date is on or before 2026-12-31 emits none of that category."""
        for days in (
            ["2026-12-31"],
            ["2026-10-16", "2026-10-19", "2026-10-20", "2026-12-30", "2026-12-31"],
            ["2019-07-29", "2023-09-04", "2026-09-28"],
        ):
            with self.subTest(days=days):
                refs = np.full(len(days), 1000.0)
                _, caught = unconfirmed_warnings(lambda: market.limits(refs, days))
                self.assertEqual(caught, [])

    def test_mixed_date_call_warns_but_its_confirmed_part_does_not(self):
        """Guards against: the warning depending on the first or last element only: one call mixing dates
        around 2026-12-31 and 2027-01-04 warns; the same call restricted to its confirmed elements is
        silent."""
        refs = np.array([1000.0, 100.0, 5000.0, 10000.0, 1000.0])
        days = np.array(
            ["2026-12-30", "2026-12-31", "2027-01-01", "2027-01-04", "2026-10-16"],
            dtype="datetime64[D]",
        )
        _, caught = unconfirmed_warnings(lambda: market.limits(refs, days))
        self.assertGreaterEqual(len(caught), 1)
        late = np.asarray(market.unconfirmed(days))
        self.assertEqual(late.tolist(), [False, False, True, True, False])
        _, caught_confirmed = unconfirmed_warnings(lambda: market.limits(refs[~late], days[~late]))
        self.assertEqual(caught_confirmed, [])

    def test_regime_index_after_the_last_confirmed_date_is_the_dedicated_last_entry(self):
        """Guards against: reports keyed by regime mixing the unconfirmed period with a confirmed one:
        every date after 2026-12-31 maps to the last REGIMES entry, which starts on 2027-01-01 and is
        labelled UNCONFIRMED; 2026-12-31 does not map to it."""
        days = np.array(AFTER_LAST_CONFIRMED_DATE, dtype="datetime64[D]")
        last = len(market.REGIMES) - 1
        self.assertEqual(market.regime_index(days).tolist(), [last] * len(days))
        self.assertEqual(market.REGIMES[last].start, datetime.date(2027, 1, 1))
        self.assertIn("UNCONFIRMED", market.REGIMES[last].label)
        confirmed = market.regime_index(np.array(["2026-12-31"], dtype="datetime64[D]"))
        self.assertNotEqual(int(confirmed[0]), last)

    def test_regime_labels_list_the_unconfirmed_entry_last(self):
        """Guards against: a report label list without the unconfirmed period, an unordered list, or a
        dict that lost or gained a key (CONTRACT sections 2 and 3d)."""
        labels = market.regime_labels()
        self.assertEqual(labels[-1]["start"], "2027-01-01")
        self.assertIn("UNCONFIRMED", labels[-1]["label"])
        starts = [entry["start"] for entry in labels]
        self.assertEqual(starts, sorted(starts))
        for entry in labels:
            self.assertEqual(set(entry), {"start", "arb_flat", "floor", "small_abs", "label"})


if __name__ == "__main__":
    unittest.main()

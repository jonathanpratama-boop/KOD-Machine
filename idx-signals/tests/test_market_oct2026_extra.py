r"""Gap-filling tests for the October 2026 IDX auto-rejection correction (idxsig.market).

Written by the mutation tester after the two independent test files (tests/test_market_oct2026.py
and tests/test_market_oct2026_exec.py, with tests/test_market.py) had been run against 422
one-defect mutants of idxsig/market.py: 171 written from the contract and 251 generated from the
code (one operator or literal changed per mutant). They killed 368; 54 survived. Thirty-one of the
survivors are equivalent, that is, they change nothing the contract lets a test observe: the Rp11-14
bound anywhere from Rp14 to Rp28 (a nominal Rp1 and 7% give the same ARB for every whole-rupiah
price from Rp15 to Rp28); the ARB of Rp11-14 on 2026-10-19, which CONTRACT section 6 forbids
asserting; floors and tolerances that no reference reaches; the text and the stack level of the
warning; the label text of the two new regimes; constants held as numpy dates that still compare
equal to the contract's datetime.date. The other 23 were real gaps, in four families. Three
families are tested below; the fourth (the float tolerance inside the pre-existing floor_tick and
ceil_tick, mutants M-E05 and M-E06) was left out of this change as unrelated to it. Each test below
was written to kill the gaps of its family (ids such as M-A03 are mutant ids of the table in
mutants.md of that run; M-X181 is a round-2 mutant):

  RegimeTableOfTheOctoberRulesTests            M-A03, M-A12,  A rule change is a regime of its
                                               M-X181         own, starting on its own date (the
                                                              reports of panel and e5 key on it).
  RegimeLabelFieldsForReportsTests             M-F07, M-F08,  The regime dicts that go into the
                                               M-F14..F18,    frozen manifests: values and types
                                               M-I09, M-I10   of the new regimes, exact JSON text
                                                              of the old ones.
  UnconfirmedPeriodConventionConsistencyTests  M-H22,         unconfirmed() and the warning of
                                               M-F07, M-F08   limits() agree for timestamps (the
                                                              calendar date decides); the last
                                                              regime reports the carried rule.

Nothing here asserts an exchange rule for a date after 2026-12-31 or the ARB of Rp11-14 on
2026-10-19 (CONTRACT section 6). What is asserted for the period after 2026-12-31 is the labelled
convention of CONTRACT section 3, in a class that says so. No test depends on another, nothing reads
the network or raw data, and the whole file runs in well under a second.
"""

import datetime
import json
import unittest
import warnings

import numpy as np

from idxsig import market

OCT18, OCT19, OCT20 = "2026-10-18", "2026-10-19", "2026-10-20"
DEC31, JAN01 = "2026-12-31", "2027-01-01"
ONE_DAY = np.timedelta64(1, "D")

# The regime dicts that start on or before 2026-09-28, as the module returned them before the
# correction. They are written to the frozen manifests (panel.py: json.dumps(manifest,
# sort_keys=True)), so the TYPE of every value matters, not only equality: 50 is not 50.0 and true
# is not 1 in the JSON text. Provenance: the same seven dicts are in
# tests/fixtures/market_limits_golden_20261109.json (key regime_labels_through_2026_09_28),
# captured from the unmodified module.
FROZEN_LABELS = [
    {"start": "2019-07-29", "arb_flat": None, "floor": 50, "small_abs": False,
     "label": "symmetric 35/25/20 (in force at panel start)"},
    {"start": "2020-03-10", "arb_flat": 0.1, "floor": 50, "small_abs": False,
     "label": "COVID ARB 10%"},
    {"start": "2020-03-13", "arb_flat": 0.07, "floor": 50, "small_abs": False,
     "label": "COVID ARB 7%"},
    {"start": "2023-06-05", "arb_flat": 0.15, "floor": 50, "small_abs": False,
     "label": "ARB 15% (stage I)"},
    {"start": "2023-09-04", "arb_flat": None, "floor": 50, "small_abs": False,
     "label": "symmetric 35/25/20 (stage II)"},
    {"start": "2025-04-08", "arb_flat": 0.15, "floor": 50, "small_abs": False,
     "label": "ARB 15% (April 2025)"},
    {"start": "2026-09-28", "arb_flat": 0.15, "floor": 1, "small_abs": True,
     "label": "ARB 15%, floor Rp1"},
]  # fmt: skip


def day(text):
    return datetime.date.fromisoformat(text)


def day_array(*texts):
    return np.array(texts, dtype="datetime64[D]")


def label_for(start):
    """The regime_labels() entry whose start date is `start` (an ISO string), or fail the lookup."""
    found = [entry for entry in market.regime_labels() if entry["start"] == start]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} regime_labels() entries start on {start}, expected one")
    return found[0]


class RegimeTableOfTheOctoberRulesTests(unittest.TestCase):
    """CONFIRMED dates (SPEC_FINAL section 1, CONTRACT section 1): the two October decisions change
    the rule on 2026-10-19 (ARB 7%) and on 2026-10-20 (a nominal Rp1 for Rp11-14). Reports are keyed
    by regime (panel._limit_qa groups its violations by regime_index, e5 by REGIMES[...].label), so
    each rule change has to be a regime of its own that starts on its own date: 2026-10-19 is the
    one session under Kep-00157 and must not be counted with the sessions that follow it, which
    have another rule for Rp11-14."""

    def test_each_regime_is_selected_on_its_own_start_date_and_not_the_day_before(self):
        """Guards against: a regime that can never be selected, or one that starts on another date
        than it says (M-A03: the 2026-10-20 row starting on 2026-10-19 hides the 2026-10-19 row;
        M-A02: the 2026-10-19 row starting on 2026-10-20). For every REGIMES entry k, regime_index()
        of its start date is k and of the day before is k - 1, and the start dates strictly
        increase."""
        starts = [regime.start for regime in market.REGIMES]
        self.assertEqual(starts, sorted(set(starts)), "start dates must be unique and increasing")
        for k, start in enumerate(starts):
            with self.subTest(regime=k, start=start.isoformat()):
                here = market.regime_index(np.array([np.datetime64(start, "D")]))
                self.assertEqual(int(here[0]), k)
                if k > 0:
                    before = market.regime_index(np.array([np.datetime64(start, "D") - ONE_DAY]))
                    self.assertEqual(int(before[0]), k - 1)

    def test_2026_10_19_and_2026_10_20_start_two_distinct_regimes(self):
        """Guards against: the 2026-10-19 session sharing a regime with the sessions from 2026-10-20
        (M-A12: one merged row from 2026-10-19; M-A03), which would put the one Kep-00157 session,
        and the Rp11-14 violations seen on it (BTEK, TAXI), into the report of the Rp1 rule. The
        dates 2026-10-18, 2026-10-19 and 2026-10-20 map to three increasing regimes that start on
        those dates (2026-10-18 is still the 15% regime), and 2026-10-20, interior dates and
        2026-12-31 share the last of them."""
        index = market.regime_index(
            day_array(OCT18, OCT19, OCT20, "2026-11-09", "2026-12-30", DEC31)
        ).tolist()
        before, first, second, interior, last_but_one, dec31 = index
        self.assertLess(before, first)
        self.assertLess(first, second)
        self.assertEqual(second, interior)
        self.assertEqual(second, last_but_one)
        self.assertEqual(second, dec31)
        self.assertEqual(market.REGIMES[before].start, day("2026-09-28"))
        self.assertEqual(market.REGIMES[first].start, day(OCT19))
        self.assertEqual(market.REGIMES[second].start, day(OCT20))

    def test_regime_labels_list_the_regimes_that_regime_index_selects(self):
        """Guards against: regime_labels() and regime_index() describing different tables (the
        report label list is keyed by the same index): for the dates around the changes, the start
        date of the selected regime is the start date at position `index` of regime_labels()."""
        labels = market.regime_labels()
        dates = ("2026-09-28", OCT18, OCT19, OCT20, DEC31)
        expected_start = ("2026-09-28", "2026-09-28", OCT19, OCT20, OCT20)
        index = market.regime_index(day_array(*dates)).tolist()
        self.assertEqual([labels[i]["start"] for i in index], list(expected_start))


class RegimeLabelFieldsForReportsTests(unittest.TestCase):
    """CONFIRMED (CONTRACT sections 1 and 2): regime_labels() is written into the frozen panel
    manifests as JSON text. The dicts of the regimes up to 2026-09-28 must be identical to what they
    were, value and type; the dicts of the two October regimes must say what the rule is (ARB 7%,
    minimum price Rp1, Rp1-10 band at +/- Rp1). The label text of the new regimes is not fixed by
    the contract and is not asserted."""

    def test_the_old_regime_dicts_serialise_to_the_frozen_json_text(self):
        """Guards against: a changed type that compares equal but changes the manifest bytes (M-I09:
        floor 50 written 50.0; M-I10: small_abs true written 1). json.dumps(sort_keys=True) of the
        dicts that start on or before 2026-09-28 equals the text of the frozen list."""
        got = [entry for entry in market.regime_labels() if entry["start"] <= "2026-09-28"]
        self.assertEqual(json.dumps(got, sort_keys=True), json.dumps(FROZEN_LABELS, sort_keys=True))

    def test_every_regime_dict_holds_plain_json_types(self):
        """Guards against: a numpy scalar, a date object or a bool-as-int in a regime dict, which
        makes json.dumps fail or changes the text of a manifest: start and label are strings,
        arb_flat is None or a float, floor an int, small_abs a bool, for every entry including the
        new ones."""
        for entry in market.regime_labels():
            with self.subTest(start=entry["start"]):
                self.assertIs(type(entry["start"]), str)
                self.assertIs(type(entry["label"]), str)
                self.assertTrue(entry["arb_flat"] is None or type(entry["arb_flat"]) is float)
                self.assertIs(type(entry["floor"]), int)
                self.assertIs(type(entry["small_abs"]), bool)
                self.assertEqual(json.loads(json.dumps(entry)), entry)

    def test_the_two_october_regimes_report_arb_7_percent_floor_rp1_and_the_rp1_band(self):
        """Guards against: wrong regime metadata that no limit value shows (M-F07: floor 0 in the
        new rows; M-F08: floor 2): from 2026-10-19 the minimum price is still Rp1 (floor 1), the
        lower limit above the nominal band is 7% (arb_flat 0.07) and the Rp1-10 band still moves a
        nominal rupiah (small_abs true), on the 2026-10-19 and on the 2026-10-20 regime."""
        for start in (OCT19, OCT20):
            with self.subTest(regime=start):
                entry = label_for(start)
                self.assertEqual(entry["arb_flat"], 0.07)
                self.assertEqual(entry["floor"], 1)
                self.assertIs(entry["small_abs"], True)


class UnconfirmedPeriodConventionConsistencyTests(unittest.TestCase):
    """A CONVENTION, not an exchange rule (CONTRACT section 3; SPEC_FINAL section 9). After
    2026-12-31 no rule is confirmed and limits() carries the last confirmed rule forward. A caller
    learns about that period from the mask unconfirmed(days) and from the RulesUnconfirmedWarning
    of limits(); they must agree, and the calendar date decides (CONTRACT section 0: limits()
    selects its rule by the calendar date), so a timestamp on 2026-12-31 is a confirmed date
    whatever the time of day. The dedicated last regime of the report labels must carry the rule
    that limits() carries. Nothing is asserted about the exchange."""

    STAMPS = (  # (timestamp, is it after 2026-12-31 by calendar date)
        ("2026-12-30T12:00:00", False),
        ("2026-12-31T00:00:00", False),
        ("2026-12-31T15:30:00", False),
        ("2026-12-31T23:59:59", False),
        ("2027-01-01T00:00:00", True),
        ("2027-01-01T09:00:00", True),
        ("2027-01-04T00:00:00", True),
    )

    @staticmethod
    def warnings_of(call):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            call()
        return [w for w in caught if issubclass(w.category, market.RulesUnconfirmedWarning)]

    def test_the_mask_of_a_timestamp_is_the_mask_of_its_calendar_date(self):
        """Guards against: unconfirmed() comparing the time of day (M-H22: dates cast to
        nanoseconds, so 2026-12-31T15:30 counts as after 2026-12-31) while limits() truncates to the
        calendar date. For every timestamp unconfirmed() equals the comparison of its calendar date
        with 2026-12-31."""
        for stamp, late in self.STAMPS:
            with self.subTest(stamp=stamp):
                flag = np.asarray(market.unconfirmed(np.array([stamp], dtype="datetime64[s]")))
                self.assertEqual(flag.tolist(), [late])
                self.assertEqual(bool(np.asarray(market.unconfirmed(np.datetime64(stamp)))), late)

    def test_the_warning_of_limits_follows_the_calendar_date_of_a_timestamp(self):
        """Guards against: limits() warning on a timestamp of 2026-12-31 (a confirmed date) or
        staying silent on one of 2027-01-01, and a mask that disagrees with the warning: limits()
        records a RulesUnconfirmedWarning exactly for the timestamps that unconfirmed() flags."""
        for stamp, late in self.STAMPS:
            with self.subTest(stamp=stamp):
                days = np.array([stamp], dtype="datetime64[s]")
                caught = self.warnings_of(lambda: market.limits(np.array([1000.0]), days))
                self.assertEqual(len(caught) >= 1, late)
                self.assertEqual(len(caught) >= 1, bool(market.unconfirmed(days).any()))

    def test_the_unconfirmed_regime_dict_carries_the_last_confirmed_rule_forward(self):
        """Guards against: the label dict of the unconfirmed regime reporting another rule than the
        one limits() carries forward (the convention: the 2026-12-31 rule, ARB 7%, minimum price
        Rp1, the Rp1-10 band): the regime that starts on 2027-01-01 reports arb_flat 0.07, floor 1
        and small_abs true, like the 2026-10-20 regime it continues."""
        entry = label_for(JAN01)
        carried = label_for(OCT20)
        for key in ("arb_flat", "floor", "small_abs"):
            with self.subTest(key=key):
                self.assertEqual(entry[key], carried[key])
        self.assertEqual((entry["arb_flat"], entry["floor"], entry["small_abs"]), (0.07, 1, True))


if __name__ == "__main__":
    unittest.main()

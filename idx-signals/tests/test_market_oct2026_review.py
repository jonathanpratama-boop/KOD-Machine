"""Review additions to the October 2026 IDX auto-rejection tests: the mechanics of the "unconfirmed"
convention in idxsig/market.py that tests/test_market_oct2026.py and
tests/test_market_oct2026_exec.py leave unpinned.

After 2026-12-31 limits() carries the last confirmed rule forward and warns (CONTRACT section 3).
The two files above assert that at least one RulesUnconfirmedWarning is recorded and which values
come back. Review found five behaviours that no test pins; each has a class here:

  RulesUnconfirmedWarningIsAttributedToTheCallerTests
      stacklevel 2: the warning names the caller of limits(), not market.py or the job runner.
  RulesUnconfirmedWarningIsEmittedOncePerCallTests
      one warning per call: not one per element or row, not none, not only on the first call.
  RulesConfirmedThroughMatchesTheLastRegimeTests
      RULES_CONFIRMED_THROUGH and the last (UNCONFIRMED) entry of REGIMES move together.
  UnconfirmedReturnsAnArrayForAScalarDateTests
      unconfirmed(scalar) is a 0-d numpy.ndarray, as annotated, not a numpy scalar.
  RulesUnconfirmedWarningIsFilterableByClassTests
      a UserWarning subclass that the warnings filters select, and silence, by class.

These tests assert how the model marks the period after 2026-12-31 as unconfirmed. None asserts a
limit value or any exchange rule for a date after 2026-12-31 (CONTRACT section 6, SPEC_FINAL section
9), and none asserts the ARB of 2026-10-19 for references Rp11-14 (SPEC_FINAL U5). Dates are
calendar dates; no session calendar is consulted.

The warning tests use literal dates on either side of 2026-12-31. The class that ties the two
constants together is written relative to them, so it holds unedited after the update procedure in
the idxsig/market.py docstring: replace the UNCONFIRMED entry by the confirmed regime(s), append a
new UNCONFIRMED entry that starts the day after the new RULES_CONFIRMED_THROUGH, then move that
constant.
"""

import datetime
import inspect
import os
import unittest
import warnings

import numpy as np

from idxsig import market

THIS_FILE = os.path.realpath(__file__)
MARKET_FILE = os.path.realpath(market.__file__)
ONE_DAY = datetime.timedelta(days=1)
NP_DAY = np.timedelta64(1, "D")

# Calendar dates after 2026-12-31 (late) and on or before it (confirmed).
LATE_DAYS = ("2027-01-01", "2027-01-04", "2027-06-30", "2030-01-01")
CONFIRMED_DAYS = (
    "2019-07-29",
    "2026-10-16",
    "2026-10-19",
    "2026-10-20",
    "2026-12-30",
    "2026-12-31",
)


def unconfirmed_records(caught):
    """The RulesUnconfirmedWarning records among what a catch_warnings(record=True) block saw."""
    return [w for w in caught if issubclass(w.category, market.RulesUnconfirmedWarning)]


def late_warning_count(refs, days):
    """How many RulesUnconfirmedWarning one limits() call records with every warning shown."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        market.limits(refs, days)
    return len(unconfirmed_records(caught))


def limits_from_a_helper():
    """A job-like caller of limits(), defined in this module. It also returns the line of its call:
    the call and inspect.currentframe() share one line, so f_lineno is the line limits() was called
    from."""
    return market.limits(1000, "2027-01-04"), inspect.currentframe().f_lineno


def days_where(mask, days):
    """The first few days of `days` where `mask` is True, as ISO strings (for readable failures)."""
    return [str(day) for day in days[np.asarray(mask)][:5]]


class RulesUnconfirmedWarningIsAttributedToTheCallerTests(unittest.TestCase):
    """Guards against: the unconfirmed-rules warning naming the wrong place. limits() raises it
    with stacklevel 2, so its file and line are those of the caller of limits(); an operator reads
    them to find which job asked for limits after 2026-12-31. Both tests call limits() from this
    module, and the first calls it straight from the test method, so that a stacklevel that is too
    high lands in unittest's frames, not in this file. Only direct callers are pinned: through
    Market.build the caller of limits() is idxsig/execution.py, and that is where the warning then
    points."""

    def test_a_direct_call_is_attributed_to_the_calling_module(self):
        """Guards against: the warning pointing at idxsig/market.py (stacklevel 1) or at the code
        that called the caller (stacklevel 3 or more, here unittest) instead of at the caller. With
        every warning shown, limits() called from this module for a date after 2026-12-31 records
        one RulesUnconfirmedWarning whose file is this test file and not market.py; the operator
        otherwise cannot tell which job triggered it."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            market.limits(1000, "2027-01-04")
        records = unconfirmed_records(caught)
        self.assertEqual(len(records), 1)
        filename = os.path.realpath(records[0].filename)
        self.assertEqual(filename, THIS_FILE)
        self.assertNotEqual(filename, MARKET_FILE)

    def test_a_call_from_a_helper_is_attributed_to_the_helper(self):
        """Guards against: the attribution stopping one frame too high when limits() is called by a
        helper, as a job's own code calls it. The warning's file is this module and not market.py,
        and its line is the helper's call line, not the line that called the helper (stacklevel 3
        would still name this file, so the line is what tells them apart)."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _, call_line = limits_from_a_helper()
        records = unconfirmed_records(caught)
        self.assertEqual(len(records), 1)
        filename = os.path.realpath(records[0].filename)
        self.assertEqual(filename, THIS_FILE)
        self.assertNotEqual(filename, MARKET_FILE)
        self.assertEqual(records[0].lineno, call_line)


class RulesUnconfirmedWarningIsEmittedOncePerCallTests(unittest.TestCase):
    """Guards against: the wrong number of warnings per limits() call. CONTRACT section 3b says
    every call with a date after 2026-12-31 warns, and the sibling tests check "at least one". A
    warning per element or per row would put thousands of lines in the log of a (tickers, sessions)
    call and train readers to ignore it; none would hide the convention. These tests count
    exactly."""

    def test_three_late_calls_record_three_warnings(self):
        """Guards against: a warning per element (each call has four late dates), a warning on the
        first call only, or none: three consecutive calls with dates after 2026-12-31, under
        simplefilter("always"), record exactly three RulesUnconfirmedWarning, one more after each
        call."""
        refs = np.array([1000.0, 14.0, 5000.0, 55.0])
        days = np.array(LATE_DAYS, dtype="datetime64[D]")
        totals = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for _ in range(3):
                market.limits(refs, days)
                totals.append(len(unconfirmed_records(caught)))
        self.assertEqual(totals, [1, 2, 3])

    def test_one_call_with_many_late_dates_records_one_warning(self):
        """Guards against: a warning per late element, per distinct late date or per row of a
        (tickers, sessions) call: five distinct late dates, one late date repeated five times and a
        3 x 4 grid of late dates each record exactly one warning."""
        cases = {
            "five distinct late dates": (
                np.full(5, 1000.0),
                np.array(LATE_DAYS + ("2027-12-31",), dtype="datetime64[D]"),
            ),
            "one late date five times": (
                np.full(5, 1000.0),
                np.array(["2027-01-04"] * 5, dtype="datetime64[D]"),
            ),
            "3 x 4 grid": (
                np.full((3, 4), 1000.0),
                np.tile(np.array(LATE_DAYS, dtype="datetime64[D]"), (3, 1)),
            ),
        }
        for name, (refs, days) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(late_warning_count(refs, days), 1)

    def test_a_mixed_call_records_one_warning_wherever_the_late_dates_are(self):
        """Guards against: a warning per late element, or one that depends on where the late date
        sits (the first or last element only) or on all of them being late: calls that mix confirmed
        dates with late ones record exactly one warning, with the late dates first, last, in the
        middle and in the majority."""
        patterns = {
            "late first": ["2027-01-04", "2026-10-16", "2026-12-31"],
            "late last": ["2026-10-16", "2026-12-31", "2027-01-04"],
            "late in the middle": ["2026-12-30", "2027-01-04", "2026-12-31"],
            "late in the majority": ["2026-12-31", "2027-01-01", "2027-01-04", "2030-01-01"],
            "confirmed and late alternating": [
                "2026-12-31",
                "2027-01-01",
                "2026-12-30",
                "2027-01-04",
                "2026-10-16",
                "2030-01-01",
            ],
        }
        for name, days in patterns.items():
            with self.subTest(pattern=name):
                self.assertEqual(late_warning_count(np.full(len(days), 1000.0), days), 1)

    def test_calls_with_only_confirmed_dates_record_none(self):
        """Guards against: a warning on confirmed dates, which trains readers to ignore it: calls
        whose dates are all on or before 2026-12-31, the last confirmed date itself included,
        record no RulesUnconfirmedWarning."""
        for days in (["2026-12-31"], list(CONFIRMED_DAYS[-2:]), list(CONFIRMED_DAYS)):
            with self.subTest(days=days):
                self.assertEqual(late_warning_count(np.full(len(days), 1000.0), days), 0)

    def test_a_confirmed_call_between_late_calls_adds_nothing(self):
        """Guards against: a warning decided by earlier calls (a module-level flag, a once-only
        filter) and not by the dates of the call itself: in one recording, a late call, a confirmed
        call, a late call and a confirmed call bring the count to 1, 1, 2, 2."""
        calls = (["2027-01-04"], ["2026-12-31"], ["2027-01-01", "2026-12-31"], ["2026-10-16"])
        totals = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for days in calls:
                market.limits(np.full(len(days), 1000.0), days)
                totals.append(len(unconfirmed_records(caught)))
        self.assertEqual(totals, [1, 1, 2, 2])


class RulesConfirmedThroughMatchesTheLastRegimeTests(unittest.TestCase):
    """Guards against: RULES_CONFIRMED_THROUGH and the last entry of REGIMES drifting apart. The
    constant drives unconfirmed() and the warning; the entry keys reports by regime. The update
    procedure moves them together: replace the UNCONFIRMED entry by the confirmed regime(s),
    append a new UNCONFIRMED entry that starts the day after the new RULES_CONFIRMED_THROUGH, then
    move the constant. Everything here is relative to the two, so it needs no edit when they
    move."""

    def test_the_last_regime_starts_the_day_after_the_last_confirmed_date(self):
        """Guards against: a gap or an overlap between the confirmed schedule and the UNCONFIRMED
        regime: the last REGIMES entry starts the day after RULES_CONFIRMED_THROUGH, so the last
        confirmed date still belongs to a confirmed regime and the next day to the unconfirmed
        one."""
        self.assertEqual(market.REGIMES[-1].start, market.RULES_CONFIRMED_THROUGH + ONE_DAY)

    def test_only_the_last_regime_is_labelled_unconfirmed(self):
        """Guards against: reports keyed by regime mixing the unconfirmed period with a confirmed
        one: the last REGIMES label contains UNCONFIRMED and no earlier label does (a leftover entry
        after the update procedure, or the marker lost from the last one)."""
        self.assertIn("UNCONFIRMED", market.REGIMES[-1].label)
        for regime in market.REGIMES[:-1]:
            with self.subTest(start=regime.start):
                self.assertNotIn("UNCONFIRMED", regime.label)

    def test_regime_labels_end_with_the_unconfirmed_entry_of_the_same_start(self):
        """Guards against: the report-facing list disagreeing with REGIMES: regime_labels() ends
        with the entry that starts the day after RULES_CONFIRMED_THROUGH and is labelled
        UNCONFIRMED, and no earlier entry is."""
        labels = market.regime_labels()
        self.assertEqual(
            labels[-1]["start"], (market.RULES_CONFIRMED_THROUGH + ONE_DAY).isoformat()
        )
        self.assertIn("UNCONFIRMED", labels[-1]["label"])
        for entry in labels[:-1]:
            with self.subTest(start=entry["start"]):
                self.assertNotIn("UNCONFIRMED", entry["label"])

    def test_unconfirmed_is_true_exactly_from_the_start_of_the_last_regime(self):
        """Guards against: unconfirmed() and the last REGIMES entry disagreeing about the first late
        day, in either direction: for every calendar day from the start of the rules to 400 days
        after the last regime starts, unconfirmed(day) is True exactly when the day is on or after
        that start (an off-by-one in the constant, in the comparison or in the entry)."""
        last_start = np.datetime64(market.REGIMES[-1].start, "D")
        days = np.arange(np.datetime64(market.RULES_START, "D"), last_start + 400 * NP_DAY)
        flags = np.asarray(market.unconfirmed(days))
        want = days >= last_start
        self.assertEqual(flags.shape, days.shape)
        self.assertEqual(days_where(flags & ~want, days), [], "flagged but before the last regime")
        self.assertEqual(days_where(~flags & want, days), [], "in the last regime but not flagged")

    def test_regime_index_and_unconfirmed_pick_out_the_same_days(self):
        """Guards against: the mask and the regime lookup describing different periods (CONTRACT
        section 3d): a day maps to the last REGIMES entry exactly when unconfirmed() flags it, from
        60 days before the last regime starts to 60 days after, and for two far-away days."""
        last_start = np.datetime64(market.REGIMES[-1].start, "D")
        days = np.concatenate(
            [
                np.arange(last_start - 60 * NP_DAY, last_start + 60 * NP_DAY),
                np.array([market.RULES_START.isoformat(), "2100-01-01"], dtype="datetime64[D]"),
            ]
        )
        in_last_regime = np.asarray(market.regime_index(days)) == len(market.REGIMES) - 1
        flags = np.asarray(market.unconfirmed(days))
        self.assertEqual(days_where(in_last_regime & ~flags, days), [], "regime but not flagged")
        self.assertEqual(days_where(~in_last_regime & flags, days), [], "flagged but not regime")


class UnconfirmedReturnsAnArrayForAScalarDateTests(unittest.TestCase):
    """Guards against: unconfirmed() returning a numpy scalar for a scalar date. Its annotation and
    CONTRACT section 3 say numpy.ndarray. Comparing a 0-d array with a datetime64 scalar gives a
    numpy scalar (numpy.bool), not an array, so the function has to wrap its result; without that a
    caller that treats the result as an array (isinstance, in-place use, out=) gets a different
    type for one date than for many."""

    SCALAR_FORMS = (
        ("ISO string", lambda text: text),
        ("datetime.date", datetime.date.fromisoformat),
        ("numpy.datetime64", np.datetime64),
    )

    def assert_zero_d_flag(self, flag, expected):
        """Assert `flag` is a 0-d bool numpy.ndarray (not a numpy scalar) holding `expected`."""
        self.assertIsInstance(flag, np.ndarray)
        self.assertNotIsInstance(flag, np.generic)
        self.assertEqual(flag.ndim, 0)
        self.assertEqual(flag.shape, ())
        self.assertEqual(flag.dtype, np.dtype(bool))
        self.assertIs(flag.item(), expected)

    def test_a_scalar_date_after_the_last_confirmed_date_gives_a_zero_d_true_array(self):
        """Guards against: a numpy scalar for a late scalar date: unconfirmed("2027-01-04") is a
        0-d numpy.ndarray of dtype bool holding True, for an ISO string, a datetime.date and a
        numpy.datetime64."""
        for name, make in self.SCALAR_FORMS:
            with self.subTest(form=name):
                self.assert_zero_d_flag(market.unconfirmed(make("2027-01-04")), True)

    def test_the_last_confirmed_date_gives_a_zero_d_false_array(self):
        """Guards against: a numpy scalar, or a True, for the last confirmed date:
        unconfirmed("2026-12-31") is a 0-d numpy.ndarray of dtype bool holding False, for an ISO
        string, a datetime.date and a numpy.datetime64."""
        for name, make in self.SCALAR_FORMS:
            with self.subTest(form=name):
                self.assert_zero_d_flag(market.unconfirmed(make("2026-12-31")), False)

    def test_a_two_dimensional_date_array_keeps_its_shape(self):
        """Guards against: wrapping or reducing the result so that a (tickers, sessions) array of
        dates loses its shape: a 2 x 3 array of dates gives a 2 x 3 boolean numpy.ndarray with True
        exactly where the date is after 2026-12-31."""
        days = np.array(
            [
                ["2026-10-16", "2026-12-31", "2027-01-01"],
                ["2027-01-04", "2030-01-01", "2026-12-30"],
            ],
            dtype="datetime64[D]",
        )
        flags = market.unconfirmed(days)
        self.assertIsInstance(flags, np.ndarray)
        self.assertEqual(flags.shape, (2, 3))
        self.assertEqual(flags.dtype, np.dtype(bool))
        self.assertEqual(flags.tolist(), [[False, False, True], [True, True, False]])


class RulesUnconfirmedWarningIsFilterableByClassTests(unittest.TestCase):
    """Guards against: a warning that callers cannot control by its class.
    RulesUnconfirmedWarning is a UserWarning subclass (CONTRACT section 3), so a job can promote it
    to an error, or silence it, with warnings.filterwarnings(category=...), and silencing numpy's
    RuntimeWarnings does not hide it. Every test sets its own filters inside catch_warnings, so
    none depends on the global ones."""

    def test_an_error_filter_on_the_category_raises_it_for_a_late_date(self):
        """Guards against: a category that the error action cannot select, or a warning raised under
        another class: with filterwarnings("error", category=RulesUnconfirmedWarning), limits() for
        a date after 2026-12-31 raises RulesUnconfirmedWarning."""
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=market.RulesUnconfirmedWarning)
            with self.assertRaises(market.RulesUnconfirmedWarning):
                market.limits(1000, "2027-01-04")

    def test_an_error_filter_on_the_category_leaves_confirmed_dates_alone(self):
        """Guards against: a job that promotes the warning to an error also failing on confirmed
        dates: with the same error filter, limits() for dates on or before 2026-12-31 returns two
        arrays and raises nothing."""
        refs = np.full(len(CONFIRMED_DAYS), 1000.0)
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=market.RulesUnconfirmedWarning)
            ara, arb = market.limits(refs, list(CONFIRMED_DAYS))
        self.assertEqual((ara.shape, arb.shape), (refs.shape, refs.shape))

    def test_an_ignore_filter_on_the_category_returns_normally_and_records_nothing(self):
        """Guards against: the warning surviving an ignore filter on its own class, or the filter
        changing what limits() returns: with every warning shown and then filterwarnings("ignore",
        category=RulesUnconfirmedWarning), limits() for dates after 2026-12-31 returns two arrays of
        the broadcast shape, equal to the unfiltered result, and records no warning of that
        category."""
        refs = np.array([1000.0, 14.0, 5000.0])
        days = np.array(LATE_DAYS[:3], dtype="datetime64[D]")
        with warnings.catch_warnings(record=True) as shown:
            warnings.simplefilter("always")
            want_ara, want_arb = market.limits(refs, days)
        self.assertEqual(len(unconfirmed_records(shown)), 1)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warnings.filterwarnings("ignore", category=market.RulesUnconfirmedWarning)
            ara, arb = market.limits(refs, days)
        self.assertEqual(unconfirmed_records(caught), [])
        self.assertEqual((ara.shape, arb.shape), (refs.shape, refs.shape))
        self.assertEqual(ara.tolist(), want_ara.tolist())
        self.assertEqual(arb.tolist(), want_arb.tolist())

    def test_the_category_is_a_user_warning_subclass(self):
        """Guards against: a category outside the UserWarning family. CONTRACT section 3 gives
        class RulesUnconfirmedWarning(UserWarning); callers and the default filters treat other
        families differently."""
        self.assertTrue(issubclass(market.RulesUnconfirmedWarning, UserWarning))

    def test_an_error_filter_on_user_warning_raises_it(self):
        """Guards against: the category not being selectable through its base class: with
        filterwarnings("error", category=UserWarning), as in a job run with -W error::UserWarning,
        limits() for a date after 2026-12-31 raises RulesUnconfirmedWarning."""
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=UserWarning)
            with self.assertRaises(market.RulesUnconfirmedWarning):
                market.limits(1000, "2027-01-04")

    def test_an_ignore_filter_on_runtime_warning_does_not_hide_it(self):
        """Guards against: the category being a RuntimeWarning, which a job that silences numpy's
        RuntimeWarnings would then hide with them: with every warning shown and then
        filterwarnings("ignore", category=RuntimeWarning), limits() for a date after 2026-12-31
        still records one RulesUnconfirmedWarning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            market.limits(1000, "2027-01-04")
        self.assertEqual(len(unconfirmed_records(caught)), 1)


if __name__ == "__main__":
    unittest.main()

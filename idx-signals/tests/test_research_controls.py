"""Causality checks for the opt-in control-pool helper; no market outcomes."""

from datetime import timedelta
import unittest

from idxsig.research_controls import past_only_control_pool


class PastOnlyControlsTest(unittest.TestCase):
    def test_future_trigger_does_not_remove_control(self):
        events = [{"symbol": "A", "observed_at": "2026-11-04T11:00:00Z"}]
        self.assertEqual(
            past_only_control_pool(["A", "B"], events,
                                   at="2026-11-04T10:00:00Z", lookback=timedelta(hours=72)),
            ("A", "B"),
        )

    def test_exact_bounds_and_timezone(self):
        events = [
            {"symbol": "OLD", "observed_at": "2026-11-01T10:00:00Z"},
            {"symbol": "RECENT", "observed_at": "2026-11-01T10:00:01Z"},
            {"symbol": "NOW", "observed_at": "2026-11-04T17:00:00+07:00"},
        ]
        self.assertEqual(
            past_only_control_pool(["NOW", "OLD", "RECENT", "QUIET"], events,
                                   at="2026-11-04T10:00:00Z", lookback=timedelta(hours=72)),
            ("OLD", "QUIET"),
        )

    def test_future_outcome_columns_do_not_affect_pool(self):
        before = [{"symbol": "A", "observed_at": "2026-11-04T09:00:00Z"}]
        with_outcomes = [{**before[0], "forward_return": 900},
                         {"symbol": "B", "observed_at": "2026-11-05T00:00:00Z"}]
        args = dict(at="2026-11-04T10:00:00Z", lookback=timedelta(hours=72))
        self.assertEqual(past_only_control_pool(["A", "B"], before, **args),
                         past_only_control_pool(["A", "B"], with_outcomes, **args))

    def test_naive_time_and_invalid_lookback_rejected(self):
        for at, lookback in [("2026-11-04T10:00:00", timedelta(hours=72)),
                             ("2026-11-04T10:00:00Z", timedelta(0)),
                             ("2026-11-04T10:00:00Z", -1)]:
            with self.subTest(at=at, lookback=lookback), self.assertRaises(ValueError):
                past_only_control_pool(["A"], [], at=at, lookback=lookback)

    def test_invalid_symbols_and_naive_observation_rejected(self):
        args = dict(at="2026-11-04T10:00:00Z", lookback=timedelta(hours=72))
        for symbols in [["A", "A"], [""], [1]]:
            with self.subTest(symbols=symbols), self.assertRaises(ValueError):
                past_only_control_pool(symbols, [], **args)
        with self.assertRaises(ValueError):
            past_only_control_pool(["A"], [{"symbol": "A", "observed_at": "2026-11-04"}], **args)

    def test_no_self_fallback_when_all_controls_excluded(self):
        self.assertEqual(past_only_control_pool(
            ["A"], [{"symbol": "A", "observed_at": "2026-11-04T09:00:00Z"}],
            at="2026-11-04T10:00:00Z", lookback=timedelta(hours=72)), ())


if __name__ == "__main__":
    unittest.main()

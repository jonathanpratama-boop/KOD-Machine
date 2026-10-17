import importlib.util
import unittest
from pathlib import Path

import numpy as np

SPEC = importlib.util.spec_from_file_location(
    "e10_run", Path(__file__).resolve().parents[1] / "research" / "E10" / "run_test.py")
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)

DATES = np.array(["2021-03-01", "2021-03-02", "2021-03-03", "2021-03-04", "2021-03-05"])


class EntryTests(unittest.TestCase):
    def test_premarket_release_trades_same_session(self):
        self.assertEqual(run.entry_session("2021-03-02T08:00:00", DATES), 1)
        self.assertEqual(run.entry_session("2021-03-02T09:15:00", DATES), 1)

    def test_after_open_or_after_close_trades_next_session(self):
        self.assertEqual(run.entry_session("2021-03-02T09:16:00", DATES), 2)
        self.assertEqual(run.entry_session("2021-03-02T16:05:00", DATES), 2)

    def test_weekend_release_trades_next_session(self):
        self.assertEqual(run.entry_session("2021-02-27T12:00:00", DATES), 0)

    def test_no_session_left(self):
        self.assertIsNone(run.entry_session("2021-03-05T17:00:00", DATES))


class TradeTests(unittest.TestCase):
    def setUp(self):
        n = 5
        self.m = {"open": np.array([[10.0], [10.2], [10.1], [9.0], [9.5]]),
                  "high": np.full((n, 1), 11.0),
                  "low": np.array([[9.8], [9.9], [9.7], [8.8], [9.2]]),
                  "close": np.array([[10.1], [10.0], [9.9], [9.1], [9.6]]),
                  "value": np.full((n, 1), 1e6), "unit_factor": np.ones((n, 1))}

    def test_hold_exits_at_close(self):
        a, b, ta, tb, x = run.trade(self.m, 0, 0, 5)
        self.assertEqual((a, b, x), (10.0, 9.6, 4))

    def test_stop_gap_fills_at_open(self):
        a, b, ta, tb, x = run.trade(self.m, 0, 0, 5, stop=0.05)  # level 9.5; day 3 opens at 9.0
        self.assertEqual((b, x), (9.0, 3))

    def test_stop_intraday_fills_at_level(self):
        m = dict(self.m)
        m["low"] = np.array([[9.8], [9.4], [9.7], [9.6], [9.6]])
        a, b, ta, tb, x = run.trade(m, 0, 0, 5, stop=0.05)
        self.assertEqual((b, x), (9.5, 1))

    def test_costs_by_as_traded_tier(self):
        net = run.net_returns(np.array(10.0), np.array(10.0), np.array(10.0), np.array(10.0))
        self.assertAlmostEqual(float(net), (1 - 0.0015) * (1 - 0.0015 - 0.0000278) - 1)
        net = run.net_returns(np.array(10.0), np.array(10.0), np.array(3.0), np.array(3.0))
        self.assertAlmostEqual(float(net), (1 - 0.005) * (1 - 0.005 - 0.0000278) - 1)


class StatTests(unittest.TestCase):
    def test_boot_positive_mean(self):
        rng = np.random.default_rng(1)
        x = rng.normal(0.02, 0.01, 400)
        weeks = np.repeat(np.arange(40), 10)
        b = run.boot(x, weeks, 7)
        self.assertGreater(b["ci95"][0], 0)
        self.assertLess(b["p_one_sided"], 0.01)

    def test_boot_diff_sign(self):
        a, b = np.full(50, 0.03), np.full(50, 0.01)
        wa, wb = np.repeat(np.arange(10), 5), np.repeat(np.arange(10), 5)
        d = run.boot_diff(a, wa, b, wb, 3)
        self.assertAlmostEqual(d["diff"], 0.02)

    def test_wilson(self):
        lo, hi = run.wilson(50, 100)
        self.assertTrue(0.39 < lo < 0.41 and 0.59 < hi < 0.61)


if __name__ == "__main__":
    unittest.main()

"""Synthetic tests for the helpers in research/E9/run_test.py (no data, no network)."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np

from idxsig import execution
from idxsig.market import Fees
from idxsig.profiles import PROFILES

spec = importlib.util.spec_from_file_location("e9_run_test", Path(__file__).resolve().parents[1] / "research" / "E9" / "run_test.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
TIERS = PROFILES["US"].cost_tiers


class Costs(unittest.TestCase):
    def test_tiers_match_the_harness(self):
        p = np.array([0.2, 0.999, 1.0, 4.99, 5.0, 19.99, 20.0, 400.0])
        self.assertTrue(np.array_equal(R.tier_cost(p, TIERS), execution._tier_costs(p, TIERS)))
        self.assertEqual(list(R.tier_cost(p, TIERS)), [0.015, 0.015, 0.005, 0.005, 0.0015, 0.0015, 0.0005, 0.0005])

    def test_net_formula(self):
        f = Fees(0.0, 2.78e-05)
        got = R.net_return(np.array([0.10]), np.array([0.5]), np.array([30.0]), f, TIERS)
        self.assertAlmostEqual(got[0], 1.10 * (1 - 2.78e-05 - 0.0005) / 1.015 - 1, places=15)
        got = R.net_return(np.array([0.10]), np.array([0.5]), np.array([30.0]), f, TIERS, extra=0.005)
        self.assertAlmostEqual(got[0], 1.10 * (1 - 2.78e-05 - 0.0005 - 0.005) / 1.02 - 1, places=15)
        got = R.net_return(np.array([0.10, 0.10]), np.array([30.0, 30.0]), np.array([30.0, 30.0]), f, TIERS,
                           flat=(np.array([True, False]), 0.015))
        self.assertAlmostEqual(got[0], 1.10 * (1 - 2.78e-05 - 0.015) / 1.015 - 1, places=15)
        self.assertAlmostEqual(got[1], 1.10 * (1 - 2.78e-05 - 0.0005) / 1.0005 - 1, places=15)


class Overlap(unittest.TestCase):
    def test_a_signal_while_held_is_skipped(self):
        ex = execution.STATUS.index("EXITED")
        tr = {"exit_idx": np.array([5, 7, 15, 6]), "status": np.array([ex] * 4)}
        got = R.overlap_skips(tr, np.array([0, 0, 0, 1]), np.array([0, 2, 10, 1]), 1)
        self.assertEqual(got.tolist(), [False, True, False, False])

    def test_an_incomplete_trade_holds_to_the_end(self):
        inc = execution.STATUS.index("INCOMPLETE")
        tr = {"exit_idx": np.array([-1, 9]), "status": np.array([inc, 0])}
        self.assertEqual(R.overlap_skips(tr, np.array([0, 0]), np.array([3, 40]), 1).tolist(), [False, True])


class Statistics(unittest.TestCase):
    def test_bootstrap(self):
        w = np.repeat([202101, 202102, 202103, 202104], 5)
        b = R.Boot(w, 500, 1)
        flat = b.mean(np.full(20, 0.02), w)
        self.assertAlmostEqual(flat["ci95"][0], 0.02)
        self.assertAlmostEqual(flat["ci95"][1], 0.02)
        v = np.arange(20) / 100
        d = b.diff(v, w, v, w)
        self.assertEqual((d["diff"], d["ci95"]), (0.0, [0.0, 0.0]))
        m = b.mean(v, w)
        self.assertLess(m["ci95"][0], m["mean"])
        self.assertGreater(m["ci95"][1], m["mean"])
        self.assertEqual(m["weeks"], 4)
        self.assertEqual(R.Boot(w, 500, 1).mean(v, w), m)  # the seed fixes the resampled weeks
        self.assertRaises(ValueError, b.mean, [0.1], [202150])
        self.assertIsNone(b.mean([], []))

    def test_wilson_and_describe(self):
        lo, hi = R.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=4)
        self.assertAlmostEqual(hi, 0.7634, places=4)
        d = R.describe([0.3, -0.1, 0.05, np.nan, -0.2])
        self.assertEqual((d["n"], d["win_rate"], d["share_net_at_least_20pct"]), (4, 0.5, 0.25))
        self.assertAlmostEqual(d["avg_loss"], -0.15)
        self.assertEqual(R.describe([np.nan]), {"n": 0})

    def test_exposure(self):
        x = R.exposure([0, 2, 10], [5, 6, 12], [0.10, -0.20, 0.05], 5000.0, 100000.0)
        self.assertEqual(x["max_concurrent_positions"], 2)
        self.assertAlmostEqual(x["total_pnl_usd"], 5000 * (0.10 - 0.20 + 0.05))
        self.assertAlmostEqual(x["max_drawdown_usd"], -1000.0)   # +500, then -1000 at the second exit
        self.assertEqual(x["sessions_with_a_position"], 10)       # sessions 0-6 and 10-12


if __name__ == "__main__":
    unittest.main()

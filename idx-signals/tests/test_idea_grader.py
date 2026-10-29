import unittest

import numpy as np

from idxsig import idea_grader as ig


class Mechanics(unittest.TestCase):
    def test_signals_fire_on_the_first_day_only(self):
        lv = np.r_[np.linspace(1, 2, 60), np.linspace(2, 1, 30), np.linspace(1, 2, 60)]
        sig = ig.signals(lv, {"type": "rsi_below", "n": 14, "level": 30})
        self.assertTrue(sig.any())
        self.assertFalse((sig[1:] & sig[:-1]).any())

    def test_tp_sl_exit(self):
        lv = np.array([1.0, 1.02, 1.11, 1.2, 1.0])
        self.assertEqual(ig.exit_index(lv, 0, {"tp": 0.10, "sl": 0.05, "max_hold": 3}), 2)
        lv = np.array([1.0, 0.94, 1.3])
        self.assertEqual(ig.exit_index(lv, 0, {"tp": 0.10, "sl": 0.05, "max_hold": 3}), 1)

    def test_unknown_type_is_refused(self):
        with self.assertRaises(ValueError):
            ig.signals(np.ones(50), {"type": "__import__('os')"})


class Honesty(unittest.TestCase):
    def test_noise_is_rarely_a_survivor(self):
        rng = np.random.default_rng(3)
        ps = []
        for k in range(6):
            d = rng.normal(0, 0.01, size=(400, 30))
            ps.append(ig.spa(d, seed=k)["p"])
        self.assertGreater(np.median(ps), 0.1)

    def test_a_real_edge_is_found(self):
        rng = np.random.default_rng(4)
        d = rng.normal(0, 0.01, size=(600, 30))
        d[:, 7] += 0.004
        self.assertLess(ig.spa(d)["p"], 0.05)

    def test_grade_on_synthetic_noise(self):
        rng = np.random.default_rng(5)
        n = 1500
        dates = np.array([f"2018-{1 + i // 28 % 12:02d}-{1 + i % 28:02d}" for i in range(n)])
        s = ig.Series(dates, np.exp(np.cumsum(rng.normal(0, 0.02, n))))
        g = ig.grade({"name": "noise", "market": "US", "ticker": "X", "entry": {"type": "rsi_below", "n": 14, "level": 30},
                      "exit": {"hold": 10}}, s)
        self.assertIn(g["verdict"], ("NOT DISTINGUISHABLE FROM LUCK", "IN-SAMPLE ONLY"))
        self.assertIn("Paper only", ig.words(g))


if __name__ == "__main__":
    unittest.main()

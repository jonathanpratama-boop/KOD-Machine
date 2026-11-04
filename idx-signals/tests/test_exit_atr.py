"""Focused tests for idxsig/exit_atr.py (EXIT-ATR-v1). Synthetic bars only."""

import unittest

import numpy as np

from idxsig import exit_atr as X


def bars(n, o=100.0):
    """Flat bars: open = high = o, low = o - 0.5, so the highest price since entry stays at the entry."""
    o = np.full(n, float(o))
    return o.copy(), o.copy(), o - 0.5, np.ones(n, dtype=bool)


class ATR(unittest.TestCase):
    def test_true_range_uses_the_previous_close(self):
        tr = X.true_ranges([10, 12, 9], [9, 11, 8], [10, 11.5, 8.5])
        np.testing.assert_allclose(tr, [max(1, 2, 1), max(1, abs(9 - 11.5), abs(8 - 11.5))])

    def test_atr_is_the_mean_of_14_true_ranges_from_15_bars(self):
        hi = np.arange(15) + 10.0
        lo = hi - 2
        cl = hi - 1
        a = X.atr_at_signal(hi, lo, cl, consecutive=True)
        self.assertAlmostEqual(a, float(np.mean(X.true_ranges(hi, lo, cl))))
        self.assertAlmostEqual(
            a, 2.0
        )  # each day: high - low = 2, |high - prev close| = 2, |low - prev close| = 0

    def test_invalid_warmups(self):
        hi, lo, cl = np.full(15, 11.0), np.full(15, 9.0), np.full(15, 10.0)
        self.assertIsNone(
            X.atr_at_signal(hi[:14], lo[:14], cl[:14], True)
        )  # 14 bars, no previous close
        self.assertIsNone(X.atr_at_signal(hi, lo, cl, False))  # a missing day inside
        bad = lo.copy()
        bad[3] = 0
        self.assertIsNone(X.atr_at_signal(hi, bad, cl, True))
        bad = hi.copy()
        bad[5] = 8
        self.assertIsNone(X.atr_at_signal(bad, lo, cl, True))  # high < low
        bad = cl.copy()
        bad[7] = np.nan
        self.assertIsNone(X.atr_at_signal(hi, lo, bad, True))
        flat = np.full(15, 10.0)
        self.assertIsNone(X.atr_at_signal(flat, flat, flat, True))  # ATR 0


class Trail(unittest.TestCase):
    def test_initial_stop_and_touch_fill(self):
        o, h, l, p = bars(10)
        l[4] = 93.0  # 100 - 3 x 2 = 94 is touched in bar 4
        r = X.trail(o, h, l, p, 100.0, 2.0)
        self.assertEqual((r["reason"], r["exit_bar"]), ("STOP", 4))
        self.assertAlmostEqual(r["initial_stop"], 94.0)
        self.assertAlmostEqual(r["exit_price"], 94.0)

    def test_gap_below_the_stop_fills_at_the_open(self):
        o, h, l, p = bars(10)
        o[3], h[3], l[3] = 90.0, 91.0, 89.0
        r = X.trail(o, h, l, p, 100.0, 2.0)
        self.assertEqual((r["reason"], r["exit_price"], r["exit_bar"]), ("STOP_GAP", 90.0, 3))

    def test_ratchet_activates_only_from_the_next_bar(self):
        o, h, l, p = bars(10)
        h[2], l[2] = 120.0, 99.0  # bar 2 makes a new high; within bar 2 the old stop (94) applies
        o[3:], h[3:], l[3:] = 116.0, 116.0, 115.0
        r_same = X.trail(o, h, l, p, 100.0, 2.0)
        self.assertEqual(
            r_same["reason"], "NOT_STOPPED"
        )  # bar 2's low 99 is above 94; 114 is not active yet
        self.assertAlmostEqual(r_same["final_stop"], 114.0)
        l2 = l.copy()
        l2[3] = 113.0  # bar 3 low under the raised stop 120 - 6 = 114
        r = X.trail(o, h, l2, p, 100.0, 2.0)
        self.assertEqual((r["reason"], r["exit_bar"]), ("STOP", 3))
        self.assertAlmostEqual(r["exit_price"], 114.0)

    def test_stop_never_moves_down(self):
        o, h, l, p = bars(8)
        h[1] = 110.0  # stop 104 from bar 2
        o[2], h[2], l[2] = 106.0, 106.0, 105.0  # lower high: stop stays 104
        o[3], h[3], l[3] = 105.0, 105.5, 103.5
        r = X.trail(o, h, l, p, 100.0, 2.0)
        self.assertEqual((r["reason"], r["exit_bar"]), ("STOP", 3))
        self.assertAlmostEqual(r["exit_price"], 104.0)
        self.assertEqual(r["raises"], 1)

    def test_no_take_profit_and_not_stopped(self):
        p = np.ones(6, dtype=bool)
        h = np.linspace(101, 200, 6)  # straight up +100%: there is no profit target to sell into
        r = X.trail(np.full(6, 100.0), h, np.full(6, 99.9), p, 100.0, 50.0)
        self.assertEqual(r["reason"], "NOT_STOPPED")
        self.assertIsNone(r["exit_price"])

    def test_missing_bars_skip_and_do_not_move_the_stop(self):
        o, h, l, p = bars(8)
        p[2:5] = False
        h[3] = 500.0  # inside missing bars: must be ignored
        o[5], h[5], l[5] = 95.0, 96.0, 93.5
        r = X.trail(o, h, l, p, 100.0, 2.0)
        self.assertEqual((r["reason"], r["exit_bar"]), ("STOP", 5))
        self.assertAlmostEqual(r["exit_price"], 94.0)
        c = X.trail(o, h, l, p, 100.0, 2.0, conservative_gaps=True)
        self.assertEqual((c["reason"], c["exit_price"]), ("STOP_GAP_WORST", 93.5))
        o[5] = 92.0
        l[5] = 91.0
        g = X.trail(o, h, l, p, 100.0, 2.0)
        self.assertEqual((g["reason"], g["exit_price"]), ("STOP_GAP", 92.0))

    def test_conservative_mode_changes_nothing_without_a_gap(self):
        o, h, l, p = bars(10)
        l[6] = 93.0
        self.assertEqual(
            X.trail(o, h, l, p, 100.0, 2.0), X.trail(o, h, l, p, 100.0, 2.0, conservative_gaps=True)
        )

    def test_deadline_bars_beyond_the_window_are_never_read(self):
        o, h, l, p = bars(10)
        a = X.trail(o[:6], h[:6], l[:6], p[:6], 100.0, 2.0)
        l[7] = 1.0  # a crash after the deadline
        b = X.trail(o[:6], h[:6], l[:6], p[:6], 100.0, 2.0)
        self.assertEqual(a, b)
        self.assertEqual(a["reason"], "NOT_STOPPED")

    def test_future_bars_cannot_change_an_earlier_exit(self):
        rng = np.random.default_rng(5)
        for _ in range(200):
            n = 60
            c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
            o = np.concatenate([[100.0], c[:-1]])
            h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, n))
            l = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, n))
            p = rng.uniform(size=n) > 0.05
            p[0] = True
            r = X.trail(o, h, l, p, 100.0, 1.0)
            if r["exit_bar"] is None:
                continue
            k = r["exit_bar"]
            o2, h2, l2 = o.copy(), h.copy(), l.copy()
            o2[k + 1 :] *= 3
            h2[k + 1 :] *= 0.1
            l2[k + 1 :] *= 0.01
            self.assertEqual(r, X.trail(o2, h2, l2, p, 100.0, 1.0))
            # and the decision path up to bar j never depends on bars after j
            j = int(rng.integers(0, n))
            pre = X.trail(o[: j + 1], h[: j + 1], l[: j + 1], p[: j + 1], 100.0, 1.0)
            if pre["exit_bar"] is not None:
                self.assertEqual(pre["exit_bar"], r["exit_bar"])
                self.assertEqual(pre["exit_price"], r["exit_price"])


class Deadline(unittest.TestCase):
    def test_unstopped_trade_leaves_with_the_original_exit(self):
        o, h, l, p = bars(120)
        r = X.trailing_exit(o, h, l, p, 100.0, 2.0, original_exit_price=101.25)
        self.assertEqual(
            (r["reason"], r["exit_price"], r["held_bars"]), ("NOT_STOPPED", 101.25, 120)
        )

    def test_stopped_trade_ignores_the_original_exit(self):
        o, h, l, p = bars(120)
        l[30] = 90.0
        r = X.trailing_exit(o, h, l, p, 100.0, 2.0, original_exit_price=150.0)
        self.assertEqual((r["reason"], r["exit_price"], r["held_bars"]), ("STOP", 94.0, 31))

    def test_truncated_data_checks_stops_until_the_data_ends(self):
        o, h, l, p = bars(120)
        p[50:] = False  # hourly data ends early (delisting)
        l[60] = 1.0  # never seen
        r = X.trailing_exit(o, h, l, p, 100.0, 2.0, original_exit_price=99.0)
        self.assertEqual(
            (r["reason"], r["exit_price"], r["last_present_bar"]), ("NOT_STOPPED", 99.0, 49)
        )


class Costs(unittest.TestCase):
    def test_net_return_matches_e2_formula(self):
        # E2 harness: proceeds / cost - 1 with cost = value (1 + fee + tier), proceeds = value' (1 - fee - tier)
        self.assertAlmostEqual(
            float(X.net_return(100, 110, 0.002)), 110 * 0.998 / (100 * 1.002) - 1
        )
        self.assertAlmostEqual(float(X.net_return(100, 100, 0.003)), 0.997 / 1.003 - 1)
        self.assertLess(float(X.net_return(100, 100, 0.004)), float(X.net_return(100, 100, 0.003)))


if __name__ == "__main__":
    unittest.main()

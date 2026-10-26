"""FLOW_IDX_v1 features, on tiny hand-checkable arrays."""

import unittest

import numpy as np

from idxsig import flow_features as fx


def raw(n=1, s=30, **over):
    base = {k: np.full((n, s), 1000.0) for k in fx.RAW_COLS}
    base["foreign_buy"], base["foreign_sell"] = np.full((n, s), 300.0), np.full((n, s), 100.0)
    base["bid_volume"], base["offer_volume"] = np.full((n, s), 300.0), np.full((n, s), 100.0)
    base["non_regular_value"] = np.zeros((n, s))
    base.update(over)
    return base


class FlowFeatureTests(unittest.TestCase):
    def test_values_on_constant_flows(self):
        f = fx.features(raw(), np.ones((1, 30), dtype=bool))
        self.assertAlmostEqual(f["fnet5"][0, 10], 0.2)            # (300-100)/1000
        self.assertAlmostEqual(f["fnet20"][0, 25], 0.2)
        self.assertAlmostEqual(f["fpart20"][0, 25], 0.2)          # (300+100)/(2*1000)
        self.assertAlmostEqual(f["bidq1"][0, 3], 0.75)
        self.assertAlmostEqual(f["bidq5"][0, 10], 0.75)
        self.assertAlmostEqual(f["bidx1"][0, 25], np.log10(301 / 1001))
        self.assertAlmostEqual(f["blk5"][0, 10], 0.0)

    def test_block_share_and_minimum_sessions(self):
        r = raw(non_regular_value=np.full((1, 30), 1000.0))
        f = fx.features(r, np.ones((1, 30), dtype=bool))
        self.assertAlmostEqual(f["blk5"][0, 10], 0.5)             # 1000 / (1000 + 1000)
        self.assertTrue(np.isnan(f["fnet5"][0, 2]))               # fewer than 4 sessions
        self.assertTrue(np.isfinite(f["fnet5"][0, 3]))
        self.assertTrue(np.isnan(f["fnet20"][0, 13]))             # fewer than 15
        self.assertTrue(np.isfinite(f["fnet20"][0, 14]))

    def test_untradeable_sessions_are_nan_and_future_is_never_read(self):
        tr = np.ones((1, 30), dtype=bool)
        tr[0, 12] = False
        f = fx.features(raw(), tr)
        self.assertTrue(np.isnan(f["bidq1"][0, 12]))
        self.assertTrue(np.isfinite(f["fnet5"][0, 13]))           # the gap does not poison later windows
        r2 = raw()
        for k in r2:
            r2[k] = r2[k].copy()
            r2[k][0, 20:] = np.random.default_rng(1).uniform(1, 9e6, 10)
        f2 = fx.features(r2, np.ones((1, 30), dtype=bool))
        f1 = fx.features(raw(), np.ones((1, 30), dtype=bool))
        for name in fx.NAMES:
            np.testing.assert_allclose(f1[name][0, :20], f2[name][0, :20])

    def test_queue_is_nan_when_both_sides_empty(self):
        z = np.zeros((1, 30))
        f = fx.features(raw(bid_volume=z, offer_volume=z), np.ones((1, 30), dtype=bool))
        self.assertTrue(np.isnan(f["bidq1"][0, 5]))

    def test_hot_mask_is_a_per_session_cross_sectional_quantile(self):
        v = np.tile(np.arange(100, dtype=float)[:, None], (1, 3))
        ok = np.ones_like(v, dtype=bool)
        ok[99, 1] = False                                          # an excluded name does not set the threshold
        hot = fx.hot_mask(v, ok, 0.80)
        self.assertEqual(int(hot[:, 0].sum()), 20)                 # 80th percentile of 0..99 is 79.2 -> 80..99
        self.assertTrue(hot[99, 1])                                # still hot itself if above the threshold
        self.assertEqual(int(fx.hot_mask(v[:10], ok[:10], 0.8).sum()), 0)   # fewer than 20 names: none


if __name__ == "__main__":
    unittest.main()

import unittest

import numpy as np

from idxsig import quant as q


def planted(T=80, N=300, strength=0.15, seed=2):
    rng = np.random.default_rng(seed)
    sig = rng.normal(size=(T, N))
    fwd = strength * sig + rng.normal(size=(T, N))
    return [
        sig + 0.5 * rng.normal(size=(T, N)),
        rng.normal(size=(T, N)),
        rng.normal(size=(T, N)),
    ], fwd


class RankTests(unittest.TestCase):
    def test_rank_normalize(self):
        r = q.rank_normalize(np.array([3.0, np.nan, 1.0, 2.0]))
        self.assertTrue(np.isnan(r[1]))
        self.assertEqual([int(i) for i in np.argsort(r[[0, 2, 3]])], [1, 2, 0])
        self.assertAlmostEqual(np.nansum(r), 0.0)

    def test_ic_extremes(self):
        x = np.random.default_rng(1).normal(size=500)
        self.assertAlmostEqual(q.rank_ic(x, x * 3 + 1), 1.0)
        self.assertAlmostEqual(q.rank_ic(x, -x), -1.0)
        self.assertLess(abs(q.rank_ic(x, np.random.default_rng(9).normal(size=500))), 0.15)
        self.assertTrue(np.isnan(q.rank_ic(x[:10], x[:10])))


class WalkForwardTests(unittest.TestCase):
    def test_finds_planted_signal_and_weights_it(self):
        feats, fwd = planted()
        sc, b = q.walk_forward_scores(feats, fwd, first=30, lam=10.0)
        ics = np.array([q.rank_ic(sc[t], fwd[t]) for t in range(30, 80)])
        self.assertGreater(ics.mean(), 0.05)
        self.assertGreater(np.nanmean(b[30:, 0]), 5 * abs(np.nanmean(b[30:, 1])))

    def test_pure_noise_has_no_ic(self):
        feats, _ = planted()
        fwd = np.random.default_rng(5).normal(size=feats[0].shape)
        sc, _ = q.walk_forward_scores(feats, fwd, first=30, lam=10.0)
        ics = np.array([q.rank_ic(sc[t], fwd[t]) for t in range(30, 80)])
        self.assertLess(abs(q.series_stats(ics)["t_nw"]), 3.0)

    def test_no_lookahead(self):
        feats, fwd = planted()
        t = 50
        a, _ = q.walk_forward_scores(feats, fwd, first=30, lam=10.0, embargo=1)
        fwd2 = fwd.copy()
        fwd2[t - 1 :] = (
            np.random.default_rng(7).normal(size=fwd[t - 1 :].shape) * 100
        )  # everything not yet realised
        b, _ = q.walk_forward_scores(feats, fwd2, first=30, lam=10.0, embargo=1)
        np.testing.assert_allclose(a[t], b[t])
        self.assertFalse(
            np.allclose(a[t + 5], b[t + 5], equal_nan=True)
        )  # later months do see the change


class StatsTests(unittest.TestCase):
    def test_hac_recovers_known_model(self):
        rng = np.random.default_rng(3)
        f = rng.normal(size=(400, 2))
        y = 0.02 + f @ np.array([1.5, -0.7]) + rng.normal(0, 0.05, 400)
        r = q.ols_hac(y, f, lags=6)
        self.assertAlmostEqual(r["alpha"], 0.02, delta=0.01)
        self.assertAlmostEqual(r["betas"][0], 1.5, delta=0.02)
        self.assertGreater(r["alpha_t"], 3)
        self.assertGreater(r["r2"], 0.99)

    def test_nw_exceeds_iid_se_when_autocorrelated(self):
        rng = np.random.default_rng(4)
        e = rng.normal(size=600)
        x = np.zeros(600)
        for i in range(1, 600):
            x[i] = 0.7 * x[i - 1] + e[i]
        self.assertGreater(q.newey_west_se_mean(x, 6), 1.5 * x.std(ddof=1) / np.sqrt(600))

    def test_quintiles(self):
        s = np.arange(100.0)
        self.assertEqual(list(q.quintile_means(s, s)), [9.5, 29.5, 49.5, 69.5, 89.5])
        self.assertEqual(len(q.quintile_members(s)[0]), 20)


class CostTests(unittest.TestCase):
    def test_impact_monotone_and_floor(self):
        self.assertAlmostEqual(float(q.impact_cost_per_side(0.0, 1e6, 0.03)), 0.0005)
        self.assertGreater(
            float(q.impact_cost_per_side(1e5, 1e6, 0.03)),
            float(q.impact_cost_per_side(1e4, 1e6, 0.03)),
        )

    def test_net_spread_falls_with_aum_and_breakeven(self):
        m = 60
        args = dict(
            gross=np.full(m, 0.01),
            turnover_long=np.full(m, 0.5),
            turnover_short=np.full(m, 0.5),
            adv_long=np.full(m, 5e6),
            adv_short=np.full(m, 5e6),
            vol_long=np.full(m, 0.03),
            vol_short=np.full(m, 0.03),
            n_leg=np.full(m, 100.0),
        )
        means = {
            a: float(q.net_spread_at_aum(aum=a, **args).mean())
            for a in (1e4, 1e5, 1e6, 1e7, 1e8, 1e9)
        }
        vals = [means[a] for a in sorted(means)]
        self.assertTrue(all(x >= y for x, y in zip(vals, vals[1:])))
        be = q.breakeven_aum(means)
        self.assertIsNotNone(be)
        self.assertGreater(be, 1e6)
        self.assertEqual(q.breakeven_aum({1e4: -0.001, 1e5: -0.002}), 0.0)
        self.assertIsNone(q.breakeven_aum({1e4: 0.01, 1e5: 0.009}))


if __name__ == "__main__":
    unittest.main()

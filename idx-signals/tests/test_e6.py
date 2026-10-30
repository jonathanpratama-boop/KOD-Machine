"""Synthetic tests for idxsig/e6.py (research/E6, KOD-CRYPTO-E6-v1). No real data."""

import unittest

import numpy as np
import pandas as pd

from idxsig import e6


def synth(n=12, days=150, seed=1, gaps=True):
    rng = np.random.default_rng(seed)
    hours = days * 24
    r = rng.normal(0, 0.01, (n, hours))
    close = 10 * np.exp(np.cumsum(r, axis=1))
    opn = np.concatenate([close[:, :1], close[:, :-1]], axis=1)
    high = np.maximum(close, opn) * (1 + np.abs(rng.normal(0, 0.003, (n, hours))))
    low = np.minimum(close, opn) * (1 - np.abs(rng.normal(0, 0.003, (n, hours))))
    quote = np.exp(rng.normal(np.log(2e4), 0.5, (n, hours)))
    tb = quote * np.clip(0.5 + 20 * r, 0.01, 0.99)  # buying moves price up: same-hour relation only
    present = np.ones((n, hours), dtype=bool)
    if gaps:
        present[0, 500:520] = False
        present[1, : 24 * 40] = False  # lists on day 40
    nan = lambda a: np.where(present, a, np.nan)
    return e6.Hourly(
        [f"C{i:02d}USDT" for i in range(n)],
        pd.Timestamp("2020-04-01", tz="UTC"),
        present,
        nan(opn),
        nan(high),
        nan(low),
        nan(close),
        nan(quote),
        nan(tb),
    )


def index(h):
    return {s: i for i, s in enumerate(h.symbols)}


def perturb_after(h, hour):
    later = np.arange(h.present.shape[1])[None, :] > hour
    g = lambda a, m=1.7: np.where(later, a * m + 0.3, a)
    present = h.present.copy()
    present[2, hour + 1 :] = False  # a delisting after the cut
    return e6.Hourly(
        h.symbols,
        h.start,
        present,
        g(h.open),
        g(h.high, 1.9),
        g(h.low, 1.5),
        g(h.close),
        g(h.quote, 3.0),
        g(h.tb, 2.0),
    )


class Causality(unittest.TestCase):
    def test_features_and_flags_of_day_d_ignore_every_later_bar(self):
        h = synth()
        k = 110
        f1, f2 = e6.features(h, index(h)), e6.features(perturb_after(h, 24 * k + 23), index(h))
        for name in (
            "A",
            "A_pl",
            "P",
            "liq",
            "hist",
            "hi30",
            "ret7",
            "vol30",
            "close",
            "high",
            "qd",
        ):
            np.testing.assert_array_equal(
                np.nan_to_num(f1[name][:, : k + 1], nan=-9),
                np.nan_to_num(f2[name][:, : k + 1], nan=-9),
                name,
            )
        np.testing.assert_array_equal(f1["bad37"][:, : k + 1], f2["bad37"][:, : k + 1])
        day_ok = np.ones(h.n_days, dtype=bool)
        a1, _, _ = e6.arms(f1, day_ok)
        a2, _, _ = e6.arms(f2, day_ok)
        for arm in e6.ARMS:
            np.testing.assert_array_equal(a1[arm][:, : k + 1], a2[arm][:, : k + 1], arm)
        self.assertTrue(np.isfinite(f1["A"][:, k]).any())

    def test_outcome_starts_at_the_0100_open_after_the_decision(self):
        h = synth(gaps=False)
        k = 60
        e0 = 24 * (k + 1) + 1
        o1 = e6.outcomes(h)
        g = lambda a: np.where(
            np.arange(a.shape[1])[None, :] < e0, a * 2.0, a
        )  # every bar up to 00:00 of d+1
        h2 = e6.Hourly(
            h.symbols, h.start, h.present, g(h.open), g(h.high), g(h.low), g(h.close), h.quote, h.tb
        )
        o2 = e6.outcomes(h2)
        np.testing.assert_array_equal(o1["R120"][:, k], o2["R120"][:, k])
        np.testing.assert_array_equal(o1["E30"][:, k], o2["E30"][:, k])
        self.assertAlmostEqual(o1["R120"][3, k], h.close[3, e0 + 119] / h.open[3, e0] - 1)
        h3 = e6.Hourly(
            h.symbols,
            h.start,
            h.present,
            h.open * np.where(np.arange(h.open.shape[1]) == e0, 1.1, 1.0),
            h.high,
            h.low,
            h.close,
            h.quote,
            h.tb,
        )
        self.assertNotEqual(e6.outcomes(h3)["R120"][3, k], o1["R120"][3, k])

    def test_no_outcome_when_the_window_is_not_loaded_and_days_are_excluded(self):
        h = synth(days=80, gaps=False)
        o = e6.outcomes(h)
        last_ok = (h.present.shape[1] - 1 - 1 - (e6.H - 1)) // 24 - 1
        self.assertTrue(np.isfinite(o["R120"][:, last_ok]).all())
        self.assertTrue(np.isnan(o["R120"][:, last_ok + 1 :]).all())

    def test_barrier_order_and_unresolved(self):
        h = synth(n=3, days=60, gaps=False)
        k = 40
        e0 = 24 * (k + 1) + 1
        hi, lo = h.high.copy(), h.low.copy()
        hi[0, e0 + 5] = h.open[0, e0] * 1.31  # win first
        hi[1, e0 + 5] = h.open[1, e0] * 1.31
        lo[1, e0 + 5] = h.open[1, e0] * 0.94  # same bar
        lo[2, e0 + 2] = h.open[2, e0] * 0.94
        hi[2, e0 + 9] = h.open[2, e0] * 1.31  # loss first
        o = e6.outcomes(
            e6.Hourly(h.symbols, h.start, h.present, h.open, hi, lo, h.close, h.quote, h.tb)
        )
        self.assertEqual(list(o["barrier"][:, k]), ["WIN", "UNRESOLVED", "LOSS"])


class Measurement(unittest.TestCase):
    def test_planted_absorption_is_seen_and_the_placebo_does_not_see_it(self):
        rng = np.random.default_rng(3)
        n, days = 1, 80
        hours = days * 24
        net_sign = rng.choice([-1.0, 1.0], size=hours)
        size = np.exp(rng.normal(0, 0.3, hours))
        k = 70
        recent = np.arange(hours) > 24 * k + 23 - e6.RECENT
        # baseline: selling moves price 3x as much as buying; recent: buying moves it 3x as much
        imp = np.where(net_sign > 0, np.where(recent, 0.003, 0.001), np.where(recent, 0.001, 0.003))
        r = net_sign * size * imp + rng.normal(0, 1e-5, hours)
        close = 10 * np.exp(np.cumsum(r))[None, :]
        quote = np.full((1, hours), 1e5)
        tb = quote * (0.5 + 0.2 * net_sign * size / size.max())
        h = e6.Hourly(
            ["X"],
            pd.Timestamp("2020-04-01", tz="UTC"),
            np.ones((1, hours), dtype=bool),
            close,
            close * 1.001,
            close * 0.999,
            close,
            quote,
            tb,
        )
        f = e6.features(h, {"X": 0})
        self.assertGreater(f["A"][0, k], np.log(9) * 0.8)  # ln(3/1) - ln(1/3) = ln 9
        pl = f["A_pl"][0, k]
        self.assertFalse(
            np.isfinite(pl) and pl > 1.0
        )  # scrambled signs: undefined or small, never the planted value

    def test_scale_free_in_m_d(self):
        h = synth(gaps=False)
        a = e6.features(h, index(h))["A"]
        h2 = e6.Hourly(
            h.symbols, h.start, h.present, h.open, h.high, h.low, h.close, h.quote * 7, h.tb * 7
        )
        np.testing.assert_allclose(
            np.nan_to_num(a), np.nan_to_num(e6.features(h2, index(h2))["A"]), rtol=1e-9
        )


class Guards(unittest.TestCase):
    def test_holdout_is_never_loaded(self):
        with self.assertRaises(e6.HoldoutError):
            e6.build_hourly({}, pd.Timestamp("2024-01-01 00:00", tz="UTC"))

    def test_loader_drops_bars_after_the_last_hour(self):
        t = pd.date_range("2022-12-30", periods=72, freq="1h", tz="UTC")
        df = pd.DataFrame(
            {"t": t, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "quote": 1.0, "tb": 0.5}
        )
        h = e6.build_hourly(
            {"X": df}, e6.DISCOVERY_LAST_HOUR, start=pd.Timestamp("2022-12-30", tz="UTC")
        )
        self.assertEqual(h.present.shape[1], 48)
        self.assertTrue(h.present.all())

    def test_debounce(self):
        raw = np.zeros((1, 20), dtype=bool)
        raw[0, [2, 3, 7, 8, 14]] = True
        self.assertEqual(list(np.flatnonzero(e6.debounce(raw)[0])), [2, 8, 14])


class Statistics(unittest.TestCase):
    def frame(self, mean, seed):
        rng = np.random.default_rng(seed)
        d = pd.date_range("2021-01-01", periods=300, freq="1D")
        return pd.DataFrame({"week": e6._weeks(d), "excess": rng.normal(mean, 0.05, 300)})

    def test_bootstrap_separates_signal_from_noise(self):
        self.assertLess(
            e6.week_bootstrap({"a": self.frame(0.03, 1)}, {"a": 1.0}, resamples=2000)[
                "p_one_sided"
            ],
            0.01,
        )
        self.assertGreater(
            e6.week_bootstrap({"a": self.frame(0.0, 2)}, {"a": 1.0}, resamples=2000)["p_one_sided"],
            0.05,
        )
        diff = e6.week_bootstrap(
            {"a": self.frame(0.03, 3), "b": self.frame(0.03, 4)},
            {"a": 1.0, "b": -1.0},
            resamples=2000,
        )
        self.assertGreater(diff["p_one_sided"], 0.05)

    def test_end_to_end_stage1_runs_on_synthetic_data(self):
        h = synth(n=40, days=200, gaps=True)
        meta = {"symbol_index": index(h)}
        summary, table = e6.run_stage1(h, meta, period=("2020-06-10", "2020-10-10"))
        self.assertEqual(set(summary["gates"]), set(e6.PRIMARIES))
        self.assertEqual(set(summary["arms"]), set(e6.ARMS))
        self.assertTrue(set(table["arm"]) <= set(e6.ARMS))
        last = pd.Timestamp(summary["decision_days"][1])
        self.assertLessEqual(
            last + pd.Timedelta(hours=24 + 1 + e6.H),
            pd.Timestamp("2020-04-01") + pd.Timedelta(days=200),
        )


if __name__ == "__main__":
    unittest.main()

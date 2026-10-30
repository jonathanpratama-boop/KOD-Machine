"""Matched controls v3 (E5 protocol draft, matched_controls.trading_stage): the volatility
control as a quintile, ahead of market cap, with v2 kept byte-for-byte for the recorded runs.

Each test names the failure it guards against. Synthetic markets only."""

import unittest

import numpy as np
import pandas as pd

from idxsig import controls
from idxsig.backtest import RunConfig
from idxsig.execution import Market
from idxsig.profiles import PROFILES
from tests.support import random_walk_panel
from tests.support import run_synthetic as run

US = PROFILES["US"]
V3 = ("price_band", "liquidity", "volatility", "market_cap", "momentum", "drawdown", "listing_age")
V2 = ("price_band", "liquidity", "market_cap", "volatility", "momentum", "drawdown", "listing_age")
V1 = ("price_band", "liquidity", "volatility", "momentum")


# ---------------------------------------------------------------------------------------------
# A frozen copy of controls.features / controls._bucket / controls._rolling as they stood at the
# merge commit ae2cbee (base + PR #7), before v3 was added. The recorded v2 runs were produced
# by this text; the live module must reproduce it exactly for version="v1" and "v2".
# ---------------------------------------------------------------------------------------------
_LOOKBACK = 20
_DRAWDOWN_LOOKBACK = 60


def _frozen_bucket(values, n):
    pct = pd.DataFrame(values).rank(axis=0, pct=True).to_numpy()
    out = np.where(np.isfinite(pct), np.minimum(np.ceil(pct * n) - 1, n - 1), -1)
    return out.astype(np.int8)


def _frozen_rolling(arr, how, window):
    frame = pd.DataFrame(arr.T).rolling(window, min_periods=window)
    return getattr(frame, how)().to_numpy().T


def frozen_features_pre_v3(m, version="v2", band_edges=(200, 5000), as_traded=False):
    close = np.where(m.present, m.close, np.nan)
    level = close * m.unit_factor if as_traded else close
    band = np.searchsorted(
        np.array(band_edges, dtype=float), np.nan_to_num(level, nan=0.0), side="left"
    )
    band = np.where(np.isfinite(close), band, -1).astype(np.int8)
    value = np.where(m.present, np.where(m.tradeable, np.nan_to_num(m.value), 0.0), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(m.tradeable & (m.prev > 0), np.log(m.close / m.prev), 0.0)
    logret = np.where(m.present, logret, np.nan)
    out = {
        "price_band": band,
        "liquidity": _frozen_bucket(
            np.where(m.present, _frozen_rolling(value, "median", _LOOKBACK), np.nan), 5
        ),
        "volatility": _frozen_bucket(
            np.where(m.present, _frozen_rolling(logret, "std", _LOOKBACK), np.nan), 3
        ),
        "momentum": _frozen_bucket(
            np.where(m.present, _frozen_rolling(logret, "sum", _LOOKBACK), np.nan), 3
        ),
    }
    if version == "v1":
        return out
    level = np.exp(np.nancumsum(np.nan_to_num(logret), axis=1))
    level = np.where(m.present, level, np.nan)
    high = _frozen_rolling(level, "max", _DRAWDOWN_LOOKBACK)
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdown = np.where(m.present, level / high - 1, np.nan)
        mcap = np.where(m.present & np.isfinite(m.listed_shares), close * m.listed_shares, np.nan)
    n_sessions = m.shape[1]
    first = np.where(m.present.any(axis=1), m.present.argmax(axis=1), n_sessions)
    age = np.arange(n_sessions)[None, :] - first[:, None]
    censored = (first == 0)[:, None]
    age_bucket = np.select([censored | (age >= 250), age >= 60], [2, 1], 0).astype(np.int8)
    out.update(
        {
            "market_cap": _frozen_bucket(mcap, 5),
            "drawdown": _frozen_bucket(drawdown, 3),
            "listing_age": np.where(m.present, age_bucket, -1).astype(np.int8),
        }
    )
    return out


def _market(**kw):
    df, meta = random_walk_panel(**kw)
    return Market.from_panel(df), df, meta


def _assert_same_features(a, b):
    assert set(a) == set(b), (sorted(a), sorted(b))
    for name in a:
        assert a[name].dtype == b[name].dtype, name
        np.testing.assert_array_equal(a[name], b[name], err_msg=name)


class ControlsV3Buckets(unittest.TestCase):
    def test_v3_feature_order_is_the_protocol_draft_order(self):
        """Guards against: v3 registered with a different feature list or priority than the E5
        draft (volatility quintile ahead of market_cap), which would relax in the wrong order."""
        self.assertEqual(controls.VERSIONS["v3"], V3)
        self.assertEqual(controls.levels("v3"), tuple(V3[:i] for i in range(7, -1, -1)))
        names = controls.level_names("v3")
        self.assertEqual(names[0], "+".join(V3))
        self.assertEqual(names[-1], "same session only")
        self.assertEqual(len(names), 8)

    def test_v3_volatility_is_a_quintile_refining_the_v2_tercile(self):
        """Guards against: v3 keeping the tercile, or re-ranking volatility differently from v2 so
        the two versions are not comparable on the same session."""
        m, _, _ = _market(n_tickers=40, n_sessions=120)
        v3 = controls.features(m, "v3")["volatility"]
        v2 = controls.features(m, "v2")["volatility"]
        known = v3 >= 0
        np.testing.assert_array_equal(known, v2 >= 0)
        self.assertEqual(sorted(np.unique(v3[known]).tolist()), [0, 1, 2, 3, 4])
        self.assertEqual(sorted(np.unique(v2[known]).tolist()), [0, 1, 2])
        # same cross-sectional rank: a name in a higher tercile is never in a lower quintile
        checked = 0
        for s in range(m.shape[1]):
            rows = np.flatnonzero(known[:, s])
            for t in (0, 1):
                lower, upper = rows[v2[rows, s] == t], rows[v2[rows, s] == t + 1]
                if len(lower) and len(upper):
                    self.assertLessEqual(
                        int(v3[lower, s].max()), int(v3[upper, s].min()), f"session {s}"
                    )
                    checked += 1
        self.assertGreater(checked, 0)
        # within a session the quintile has at most the expected share of names per bucket
        s = m.shape[1] - 1
        counts = np.bincount(v3[known[:, s], s], minlength=5)
        self.assertEqual(counts.sum(), int(known[:, s].sum()))
        self.assertTrue((counts >= 1).all())

    def test_v3_bucket_counts_per_feature(self):
        """Guards against: a feature bucketed with the wrong count (e.g. liquidity as a tercile or
        market cap as a tercile) under v3, and the FEATURES table disagreeing with the arrays."""
        m, _, _ = _market(n_tickers=60, n_sessions=320, ipo={2: 10, 5: 100}, shares_until=200)
        f = controls.features(m, "v3")
        self.assertEqual(set(f), set(V3))
        expected = {
            "price_band": 3,
            "liquidity": 5,
            "volatility": 5,
            "market_cap": 5,
            "momentum": 3,
            "drawdown": 3,
            "listing_age": 3,
        }
        for name, n in expected.items():
            arr = f[name]
            self.assertEqual(arr.dtype, np.int8, name)
            known = arr[arr >= 0]
            self.assertEqual(int(known.max()), n - 1, name)
            self.assertEqual(int(known.min()), 0, name)
            self.assertEqual(controls.feature(name, "v3").buckets, n, name)
            self.assertGreaterEqual(len(np.unique(known)), n, name)
        present = m.present
        self.assertTrue((f["market_cap"][:, :201][present[:, :201]] >= 0).all())
        self.assertTrue(
            (f["market_cap"][:, 201:] == -1).all()
        )  # no share counts: unknown, as in v2
        self.assertTrue((f["market_cap"][~present] == -1).all())
        self.assertTrue((f["listing_age"][2, :10] == -1).all())
        self.assertEqual(int(f["listing_age"][2, 10]), 0)

    def test_v3_matches_v2_on_every_feature_but_volatility(self):
        """Guards against: v3 silently changing a feature other than the one the protocol names."""
        m, _, _ = _market(n_tickers=30, n_sessions=200, ipo={3: 40}, shares_until=150)
        v2 = controls.features(m, "v2")
        v3 = controls.features(m, "v3")
        for name in V2:
            if name == "volatility":
                self.assertFalse(np.array_equal(v2[name], v3[name]))
            else:
                np.testing.assert_array_equal(v2[name], v3[name], err_msg=name)

    def test_v3_features_use_only_past_data(self):
        """Guards against: the quintile (or any v3 feature) computed with data after the session."""
        m, _, _ = _market(n_tickers=15, n_sessions=120, ipo={2: 30, 9: 90}, shares_until=80)
        full = controls.features(m, "v3")
        for cut in (25, 61, 95):
            part = controls.features(m.truncate(cut), "v3")
            for name in V3:
                np.testing.assert_array_equal(full[name][:, : cut + 1], part[name], err_msg=name)

    def test_v3_coverage_reports_the_quintile_and_the_version(self):
        """Guards against: the report describing v3's volatility control as a tercile."""
        m, _, _ = _market(n_tickers=20, n_sessions=90)
        f = controls.features(m, "v3")
        a_tick, a_sig = np.array([0, 4]), np.array([50, 70])
        _, lv = controls.matched_draws(
            m.tradeable.copy(), f, a_tick, a_sig, 10, np.random.default_rng(0), "v3"
        )
        cov = controls.coverage(f, a_tick, a_sig, lv, "v3")
        self.assertEqual(cov["version"], "v3")
        self.assertEqual(list(cov["features"]), list(V3))
        self.assertIn("quintile", cov["features"]["volatility"]["description"])
        self.assertNotIn("tercile", cov["features"]["volatility"]["description"])
        self.assertEqual(cov["features"]["volatility"]["priority"], 3)
        self.assertEqual(cov["features"]["market_cap"]["priority"], 4)
        self.assertEqual(cov["min_pool"], controls.MIN_POOL)
        self.assertEqual(cov["not_available"], controls.UNAVAILABLE)
        us = controls.coverage(f, a_tick, a_sig, lv, "v3", US.band_names)
        self.assertTrue(us["features"]["price_band"]["description"].startswith("close in "))


class ControlsV3Relaxation(unittest.TestCase):
    def test_relaxed_from_the_last_feature_down_to_min_pool(self):
        """Guards against: v3 relaxing in another order, stopping before MIN_POOL names match, or
        relaxing further than needed. Checked against the feature arrays for every attempt."""
        m, _, _ = _market(n_tickers=45, n_sessions=130, seed=11, shares_until=100)
        f = controls.features(m, "v3")
        evaluable = m.tradeable.copy()
        rng = np.random.default_rng(3)
        a_sig = rng.integers(70, 125, size=60)
        a_tick = rng.integers(0, m.shape[0], size=60)
        drawn, lv = controls.matched_draws(
            evaluable, f, a_tick, a_sig, 40, np.random.default_rng(1), "v3"
        )
        lvls = controls.levels("v3")
        self.assertEqual(drawn.shape, (40, 60))
        seen = set()
        for col, (n, s) in enumerate(zip(a_tick, a_sig)):
            k = int(lv[col])
            seen.add(k)
            others = np.flatnonzero(evaluable[:, s])
            others = others[others != n]

            def pool(names):
                keep = np.ones(len(others), dtype=bool)
                for name in names:
                    keep &= f[name][others, s] == f[name][n, s]
                return others[keep]

            used = pool(lvls[k])
            self.assertNotIn(n, drawn[:, col])
            self.assertTrue(
                np.isin(drawn[:, col], used).all(), f"attempt {col}: a control outside its pool"
            )
            if k < len(lvls) - 1:
                self.assertGreaterEqual(
                    len(used), controls.MIN_POOL, f"attempt {col}: stopped short of MIN_POOL"
                )
            if k > 0:
                self.assertLess(
                    len(pool(lvls[k - 1])),
                    controls.MIN_POOL,
                    f"attempt {col}: relaxed although the stricter level had a pool",
                )
        self.assertGreater(
            len(seen), 1, "the synthetic market never needed relaxing; test is vacuous"
        )

    def test_v3_relaxes_volatility_after_market_cap(self):
        """Guards against: v3's priority putting the quintile below market cap, i.e. dropping it
        first, which is what v2 did (28% of recorded IDX attempts were never matched on it)."""
        lv = controls.levels("v3")  # lv[0] is the full match, lv[-1] the empty one
        self.assertEqual(lv[4], ("price_band", "liquidity", "volatility"))
        self.assertEqual(lv[3], ("price_band", "liquidity", "volatility", "market_cap"))
        self.assertEqual(controls.level_names("v3")[4], "price_band+liquidity+volatility")
        v2 = controls.levels("v2")
        self.assertEqual(
            v2[4], ("price_band", "liquidity", "market_cap")
        )  # v2 drops volatility first

    def test_run_records_v3_in_the_summary(self):
        """Guards against: a v3 run whose summary.json still says v2 (the method text, the harness
        key, the controls block), or whose match levels are not v3's."""
        df, meta = random_walk_panel(n_tickers=20, n_sessions=80)
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=10, controls_version="v3"), df, meta)[
            "summary"
        ]
        self.assertEqual(s["harness"]["controls"], "v3")
        rm = s["random_matched"]
        self.assertEqual(rm["controls"]["version"], "v3")
        self.assertIn(" / ".join(V3), rm["method"])
        self.assertIn("quintile", rm["controls"]["features"]["volatility"]["description"])
        self.assertTrue(set(rm["match_level_used"]) <= set(controls.level_names("v3")))
        self.assertEqual(sum(rm["match_level_used"].values()), s["signals"]["attempted"])
        self.assertGreater(s["signals"]["attempted"], 0)
        self.assertIn("uniform", s["random"]["method"])


class ControlsV2Unchanged(unittest.TestCase):
    def test_v1_and_v2_features_equal_the_frozen_pre_v3_copy(self):
        """Guards against: adding v3 changing any v1/v2 array (the recorded runs must reproduce)."""
        cases = (
            dict(n_tickers=40, n_sessions=160),
            dict(
                n_tickers=30, n_sessions=300, ipo={2: 30, 9: 90}, delist={4: 120}, shares_until=200
            ),
            dict(n_tickers=6, n_sessions=90, shares_until=50),
        )
        for kw in cases:
            m, _, _ = _market(**kw)
            for version in ("v1", "v2"):
                _assert_same_features(
                    controls.features(m, version), frozen_features_pre_v3(m, version)
                )
                _assert_same_features(
                    controls.features(m, version, US.band_edges),
                    frozen_features_pre_v3(m, version, US.band_edges),
                )
            mu = m.with_units(np.full(m.shape, 0.5))
            _assert_same_features(
                controls.features(mu, "v2", US.band_edges, as_traded=True),
                frozen_features_pre_v3(mu, "v2", US.band_edges, as_traded=True),
            )
        # the default version is still v2
        m, _, _ = _market(n_tickers=12, n_sessions=70)
        _assert_same_features(controls.features(m), frozen_features_pre_v3(m, "v2"))

    def test_v2_literals_and_report_fields_are_unchanged(self):
        """Guards against: v3 editing v2's feature list, priorities, bucket counts or wording."""
        self.assertEqual(controls.VERSIONS["v1"], V1)
        self.assertEqual(controls.VERSIONS["v2"], V2)
        self.assertEqual(
            controls.level_names("v2"),
            [
                "price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age",
                "price_band+liquidity+market_cap+volatility+momentum+drawdown",
                "price_band+liquidity+market_cap+volatility+momentum",
                "price_band+liquidity+market_cap+volatility",
                "price_band+liquidity+market_cap",
                "price_band+liquidity",
                "price_band",
                "same session only",
            ],
        )
        self.assertEqual(controls.MIN_POOL, 5)
        self.assertEqual(controls.FEATURES["volatility"].buckets, 3)
        self.assertEqual(
            controls.FEATURES["volatility"].description,
            "tercile of 20-session std of daily log returns",
        )
        for version in ("v1", "v2"):
            for name in controls.VERSIONS[version]:
                self.assertIs(controls.feature(name, version), controls.FEATURES[name])
        m, _, _ = _market(n_tickers=20, n_sessions=90)
        f = controls.features(m, "v2")
        a_tick, a_sig = np.array([0, 4]), np.array([50, 70])
        _, lv = controls.matched_draws(
            m.tradeable.copy(), f, a_tick, a_sig, 10, np.random.default_rng(0), "v2"
        )
        cov = controls.coverage(f, a_tick, a_sig, lv, "v2")
        self.assertEqual(cov["version"], "v2")
        self.assertEqual(list(cov["features"]), list(V2))
        self.assertEqual(
            cov["features"]["volatility"]["description"],
            controls.FEATURES["volatility"].description,
        )
        self.assertEqual(cov["features"]["volatility"]["priority"], 4)
        self.assertEqual(cov["features"]["market_cap"]["priority"], 3)

    def test_v2_draws_equal_the_frozen_copy_under_the_same_seed(self):
        """Guards against: v3 changing the code path matched_draws takes for v2 (same features,
        same rng, same pools, same level used)."""
        m, _, _ = _market(n_tickers=25, n_sessions=100, shares_until=60)
        a_tick, a_sig = np.array([0, 3, 5, 1, 2]), np.array([40, 40, 60, 80, 80])
        live = controls.matched_draws(
            m.tradeable.copy(),
            controls.features(m, "v2"),
            a_tick,
            a_sig,
            50,
            np.random.default_rng(0),
            "v2",
        )
        frozen = controls.matched_draws(
            m.tradeable.copy(),
            frozen_features_pre_v3(m, "v2"),
            a_tick,
            a_sig,
            50,
            np.random.default_rng(0),
            "v2",
        )
        np.testing.assert_array_equal(live[0], frozen[0])
        np.testing.assert_array_equal(live[1], frozen[1])

    def test_default_run_still_records_v2(self):
        """Guards against: the harness default moving to v3 (every recorded run is v2 or v1)."""
        self.assertEqual(RunConfig("PLACEBO_COINFLIP").controls_version, "v2")
        df, meta = random_walk_panel(n_tickers=20, n_sessions=80)
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=10), df, meta)["summary"]
        self.assertEqual(s["harness"]["controls"], "v2")
        self.assertEqual(s["random_matched"]["controls"]["version"], "v2")
        self.assertIn(" / ".join(V2), s["random_matched"]["method"])
        self.assertIn(
            "tercile", s["random_matched"]["controls"]["features"]["volatility"]["description"]
        )


class ControlsV3AsTraded(unittest.TestCase):
    def test_v3_price_band_uses_the_traded_price_and_the_rest_is_unit_free(self):
        """Guards against: the as_traded band path not reaching v3, or a unit factor leaking into
        the return-based quintile."""
        m, _, _ = _market(n_tickers=20, n_sessions=90)
        factor = np.full(m.shape, 0.01)  # every adjusted price traded 100x higher
        mu = m.with_units(factor)
        panel_units = controls.features(mu, "v3", US.band_edges)
        as_traded = controls.features(mu, "v3", US.band_edges, as_traded=True)
        self.assertEqual(set(as_traded), set(V3))
        self.assertFalse(np.array_equal(panel_units["price_band"], as_traded["price_band"]))
        np.testing.assert_array_equal(
            as_traded["price_band"][m.present],
            controls.features(m, "v3", tuple(e * 100 for e in US.band_edges))["price_band"][
                m.present
            ],
        )
        for name in V3:
            if name != "price_band":
                np.testing.assert_array_equal(panel_units[name], as_traded[name], err_msg=name)
        # the pre-existing single-bar check, on v3
        self.assertEqual(
            int(controls.features(m, "v3", US.band_edges)["price_band"][0, 5]),
            int(controls.features(m, "v2", US.band_edges)["price_band"][0, 5]),
        )


if __name__ == "__main__":
    unittest.main()

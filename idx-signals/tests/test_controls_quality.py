"""Matched controls v2 (audit v2, section 6) and data-quality tiers (section 8).

Each test names the failure it guards against."""

import unittest

import numpy as np

from idxsig import controls, quality
from idxsig.backtest import RunConfig
from idxsig.execution import Market
from idxsig.results import render_report
from idxsig.sources.idx_mirror import FIRST_SNAPSHOT
from tests.support import random_walk_panel
from tests.support import run_synthetic as run


class ControlFeatures(unittest.TestCase):
    def test_every_feature_uses_only_past_data(self):
        """Guards against: a control feature (market cap, drawdown, listing age ...) computed with
        data after the signal session, which would pick controls with hindsight."""
        df, _ = random_walk_panel(n_tickers=15, n_sessions=120, ipo={2: 30, 9: 90}, shares_until=80)
        m = Market.from_panel(df)
        full = controls.features(m)
        for cut in (25, 61, 95):
            part = controls.features(m.truncate(cut))
            for name in controls.VERSIONS["v2"]:
                np.testing.assert_array_equal(full[name][:, : cut + 1], part[name], err_msg=name)

    def test_listing_age_counts_from_first_session_and_censors_the_start(self):
        """Guards against: treating names present at the data's start as new listings, or
        a new listing as established."""
        df, _ = random_walk_panel(n_tickers=6, n_sessions=320, ipo={2: 10})
        m = Market.from_panel(df)
        age = controls.features(m)["listing_age"]
        self.assertEqual(age[0, 0], 2)       # present from session 0: age unknown, treated as established
        self.assertEqual(age[2, 9], -1)      # not listed yet
        self.assertEqual(age[2, 10], 0)      # first session
        self.assertEqual(age[2, 10 + 60], 1)
        self.assertEqual(age[2, 10 + 250], 2)

    def test_market_cap_is_unknown_without_share_counts_and_reported(self):
        """Guards against: inventing market cap where the data has no share counts (Yahoo era)
        and hiding how often the control was actually available."""
        df, meta = random_walk_panel(n_tickers=30, n_sessions=150, shares_until=99)
        m = Market.from_panel(df)
        mcap = controls.features(m)["market_cap"]
        self.assertTrue((mcap[:, :100] >= 0).all())
        self.assertTrue((mcap[:, 100:] == -1).all())
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=20, start="2023-01-02"), df, meta)["summary"]
        cov = s["random_matched"]["controls"]
        known = cov["features"]["market_cap"]["known_share"]
        self.assertTrue(0 < known < 1)
        self.assertEqual(cov["features"]["price_band"]["known_share"], 1.0)

    def test_unavailable_features_are_declared_not_invented(self):
        """Guards against: matching on sector, board or free float from a present-day snapshot."""
        for name in ("sector", "board", "free_float"):
            self.assertIn(name, controls.UNAVAILABLE)
            self.assertNotIn(name, controls.FEATURES)
            for version in controls.VERSIONS.values():
                self.assertNotIn(name, version)

    def test_same_session_baseline_is_kept_beside_matched(self):
        """Guards against: replacing the plain same-session baseline instead of adding to it."""
        df, meta = random_walk_panel(n_tickers=20, n_sessions=80)
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=10), df, meta)["summary"]
        self.assertIn("uniform", s["random"]["method"])
        self.assertIn("market_cap", s["random_matched"]["method"])
        self.assertEqual(s["random_matched"]["controls"]["version"], "v2")

    def test_controls_v1_reproduces_older_runs(self):
        """Guards against: losing the ability to re-run the configuration older runs used."""
        df, meta = random_walk_panel(n_tickers=20, n_sessions=80)
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=10, controls_version="v1"), df, meta)["summary"]
        self.assertIn("price_band+liquidity+volatility+momentum", controls.level_names("v1"))
        self.assertEqual(s["random_matched"]["controls"]["version"], "v1")


class QualityTiers(unittest.TestCase):
    def test_default_window_is_tier_1_only(self):
        """Guards against: the default run silently mixing in survivor-biased or Yahoo-era sessions."""
        df, meta = random_walk_panel(n_tickers=8, n_sessions=500, start="2019-08-01")
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=5), df, meta)["summary"]
        self.assertEqual(list(s["data_quality"]["sessions_by_tier"]), ["TIER_1"])
        self.assertFalse(any("TIER_" in w for w in s["warnings"]))

    def test_extended_window_states_its_tiers(self):
        """Guards against: an extended window whose weaker segments are not labelled."""
        df, meta = random_walk_panel(n_tickers=8, n_sessions=500, start="2019-08-01")
        meta = {**meta, "source_boundary": "2020-12-31"}  # pretend the exchange data ended here
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=5, start="2019-08-01", end="2021-06-30",
                          ca_mode="exclude"), df, meta)["summary"]
        tiers = s["data_quality"]["sessions_by_tier"]
        self.assertEqual(set(tiers), {"TIER_2", "TIER_3"})
        self.assertTrue(any("TIER_2 data" in w for w in s["warnings"]))
        self.assertTrue(any("TIER_3 data" in w for w in s["warnings"]))
        report = render_report("t", {**s, "code": {"commit": "x", "dirty": False}})
        self.assertIn("## Data quality", report)
        self.assertIn("Known limitations", report)

    def test_tier_boundaries(self):
        """Guards against: an off-by-one at the first snapshot or the source boundary."""
        self.assertEqual(quality.tier_of("2021-01-21", "2025-02-21"), "TIER_2")
        self.assertEqual(quality.tier_of(FIRST_SNAPSHOT, "2025-02-21"), "TIER_1")
        self.assertEqual(quality.tier_of("2025-02-21", "2025-02-21"), "TIER_1")
        self.assertEqual(quality.tier_of("2025-02-24", "2025-02-21"), "TIER_3")


if __name__ == "__main__":
    unittest.main()

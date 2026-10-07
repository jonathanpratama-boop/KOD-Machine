"""IDX harness fixes for the external review (Ace).

#5 a rights issue is not a split: only integer splits scale shares; trades held across any
   other reference reset are excluded (or valued explicitly with ca_mode=value_preserving).
   These are now the legacy modes; the default registry mode is tested in
   test_corporate_actions.py.
#6 a matched random baseline (price band, liquidity, volatility, momentum) so exposure to a
   kind of name is not mistaken for a signal
#7 the default window starts where the universe is survivorship-complete
#8 the lookahead check recomputes the rule on every prefix, not three (now prefix-first:
   test_lookahead.py)
"""

import unittest

import numpy as np
import pandas as pd

from idxsig import controls, rules
from idxsig.backtest import LookaheadError, RunConfig
from idxsig.execution import STATUS, ExecConfig, execute
from idxsig.sources.idx_mirror import FIRST_SNAPSHOT
from tests.rulekit import module_rule, with_rule
from tests.support import flat_market, random_walk_panel, rebuild
from tests.support import run_synthetic as run

FLAT_NET = (1 - 0.0025) / (1 + 0.0015) - 1


def one(m, **cfg):
    out = execute(m, np.array([0]), np.array([2]), ExecConfig(holding_days=3, **cfg))
    return {k: v[0] for k, v in out.items()}


def reset_at(price_before, price_after, session=5, price_scale=None):
    t, d, a = flat_market(price=price_before)
    a["prev"][0, session] = price_after
    for k in ("close", "prev", "high", "low"):
        a[k][0, session + (1 if k == "prev" else 0):] = price_after
    return rebuild(t, d, a)


class Ace5RightsIssueIsNotASplit(unittest.TestCase):
    def test_split_scales_shares(self):
        r = one(reset_at(5000.0, 1000.0))
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["share_factor"], 5.0)
        self.assertAlmostEqual(r["net_return"], FLAT_NET)

    def test_reverse_split_scales_shares(self):
        r = one(reset_at(100.0, 500.0))
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["share_factor"], 0.2)

    def test_rights_issue_reset_is_excluded_not_scaled(self):
        # Reference falls from 1100 to 1000 on the ex-date: a theoretical ex-rights price.
        m = reset_at(1100.0, 1000.0)
        self.assertFalse(m.is_split[0, 5])
        r = one(m)
        self.assertEqual(STATUS[r["status"]], "EXCLUDED_CORP_ACTION")
        self.assertTrue(np.isnan(r["net_return"]))
        self.assertEqual(r["exit_idx"], 6)  # still held to its exit, so overlap logic sees it

    def test_value_preserving_mode_is_explicit(self):
        r = one(reset_at(1100.0, 1000.0), ca_mode="value_preserving")
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertAlmostEqual(r["share_factor"], 1.1)

    def test_reset_before_entry_does_not_exclude(self):
        r = one(reset_at(1100.0, 1000.0, session=3))  # ex-date is the entry session itself
        self.assertEqual(STATUS[r["status"]], "EXITED")


def exposure_panel(n=40, sessions=150, seed=11):
    """Half the names are cheap (from Rp60) and drift up 0.4% a day; half are Rp1,000 and flat."""
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(np.busday_offset(np.datetime64("2022-01-03", "D"), np.arange(sessions), roll="forward"))
    rows = []
    for i in range(n):
        cheap = i < n // 2
        price = 60.0 if cheap else 1000.0
        for d in range(sessions):
            prev = price
            step = np.clip(rng.normal(0.004 if cheap else 0.0, 0.02), -0.06, 0.06)
            tick = 1 if price < 200 else 5
            price = max(round(prev * (1 + step) / tick) * tick, 51.0)
            vol = int(rng.integers(5_000_000, 50_000_000))
            rows.append({"date": dates[d], "ticker": f"S{i:03d}", "source": "synthetic", "previous": int(prev),
                         "open": pd.NA, "high": int(max(prev, price)), "low": int(min(prev, price)),
                         "close": int(price), "volume": vol, "value": int(vol * price), "frequency": 100})
    df = pd.DataFrame(rows)
    for col in ("previous", "open", "high", "low", "close", "volume", "value", "frequency"):
        df[col] = df[col].astype("Int64")
    return df, {"sha256": "synthetic", "panel": "synthetic", "source_boundary": str(dates[-1].date())}


class Ace6MatchedControls(unittest.TestCase):
    def test_features_are_causal(self):
        df, meta = random_walk_panel(n_tickers=12, n_sessions=80)
        from idxsig.execution import Market

        m = Market.from_panel(df)
        full = controls.features(m)
        cut = 50
        part = controls.features(m.truncate(cut))
        for name in controls.FEATURES:
            np.testing.assert_array_equal(full[name][:, : cut + 1], part[name])

    def test_controls_never_include_the_signalled_name(self):
        df, meta = random_walk_panel(n_tickers=12, n_sessions=60)
        from idxsig.execution import Market

        m = Market.from_panel(df)
        evaluable = m.tradeable.copy()
        a_tick = np.array([0, 3, 7])
        a_sig = np.array([30, 30, 45])
        drawn, levels = controls.matched_draws(evaluable, controls.features(m), a_tick, a_sig, 50,
                                               np.random.default_rng(0))
        for col, n in enumerate(a_tick):
            self.assertNotIn(n, drawn[:, col])
        self.assertEqual(len(levels), 3)

    def test_matched_baseline_is_not_fooled_by_exposure(self):
        df, meta = exposure_panel()

        cheap_names = module_rule("CHEAP", """
            def compute(m):
                out = np.zeros(m.shape)
                out[:, ::5] = 1.0
                out = np.where(m.close <= 200, out, 0.0)
                return np.where(m.tradeable, out, np.nan)
        """)
        with with_rule(cheap_names):
            s = run(RunConfig("CHEAP", random_draws=200), df, meta)["summary"]
        same, matched = s["random"]["avg_net_return"], s["random_matched"]["avg_net_return"]
        # Against all names, picking cheap ones looks like an edge...
        self.assertLess(same["p_value_one_sided"], 0.01)
        # ...against names of the same kind it is not.
        self.assertGreater(matched["p_value_one_sided"], 0.05)
        self.assertLess(abs(matched["difference"]), abs(same["difference"]) / 4)
        self.assertTrue(any(k.startswith("price_band+liquidity") for k in s["random_matched"]["match_level_used"]))


class Ace7SurvivorshipSafeDefault(unittest.TestCase):
    def test_default_start_is_first_snapshot_and_earlier_start_warns(self):
        df, meta = random_walk_panel(n_tickers=8, n_sessions=500, start="2019-08-01")
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=5), df, meta)["summary"]
        self.assertEqual(s["universe"]["first_session"] >= FIRST_SNAPSHOT, True)
        self.assertFalse(any("survivor-biased" in w for w in s["warnings"]))
        early = run(RunConfig("PLACEBO_COINFLIP", random_draws=5, start="2019-08-01"), df, meta)["summary"]
        self.assertTrue(any("survivor-biased" in w for w in early["warnings"]))


class Ace8ExhaustiveLookahead(unittest.TestCase):
    def test_sparse_leak_is_caught_only_by_the_exhaustive_check(self):
        df, meta = random_walk_panel(n_tickers=10, n_sessions=120)

        leaks_once = module_rule("LEAK", """
            def compute(m):
                out = np.zeros(m.shape)
                k = 17  # one session, far from the sampled cut points
                if m.shape[1] > k + 1:
                    out[:, k] = (m.close[:, k + 1] > m.close[:, k]).astype(float)
                return np.where(m.tradeable, out, np.nan)
        """)
        with with_rule(leaks_once):
            sampled = run(RunConfig("LEAK", random_draws=5, lookahead_cuts=3), df, meta)["summary"]
            self.assertEqual(sampled["lookahead_check"]["mode"], "sampled")
            self.assertTrue(any("not causal by construction" in w for w in sampled["warnings"]))
            with self.assertRaisesRegex(LookaheadError, "reads data from after the close"):
                run(RunConfig("LEAK", random_draws=5), df, meta)


if __name__ == "__main__":
    unittest.main()

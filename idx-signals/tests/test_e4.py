"""Experiment E4: protocol, candidate rules, selection rule, harness wiring. Synthetic data only."""

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import e3, e4, rules
from idxsig.execution import ENTRY_RULES, SHORT_EXITS, Market
from idxsig.profiles import PROFILES
from idxsig.rules import moonshot_e4, moonshot_g
from idxsig.rules.audit import audit_module
from tests.support import random_walk_panel

ROOT = Path(__file__).resolve().parents[1]
PROTO = json.loads((ROOT / "research" / "E4" / "protocol.json").read_text(encoding="utf-8"))
E2 = json.loads((ROOT / "research" / "E2" / "protocol.json").read_text(encoding="utf-8"))
YEARS = e3.years_of(PROTO["periods"]["discovery"])


def row(**kw):
    base = {"plan_id": "x", "detector": "G2_RET30", "entry_rule": "fixed", "entry_window": 1, "exit_rule": "fixed",
            "holding_days": 5, "scored": 500, "avg_net_return": 0.02, "p_one_sided_vs_matched": 0.005,
            "hit_rate": 0.62, "p1_net_return": -0.3,
            "scored_2020": 100, "avg_net_return_2020": 0.01, "scored_2021": 300, "avg_net_return_2021": 0.03,
            "scored_2022": 200, "avg_net_return_2022": 0.01}
    base.update(kw)
    return base


class ProtocolTests(unittest.TestCase):
    def test_frozen_and_consistent_with_e2(self):
        self.assertTrue(PROTO["frozen_before_analysis"])
        self.assertEqual(PROTO["side"], "short")
        self.assertEqual(PROTO["periods"]["discovery"], E2["periods"]["discovery"])
        self.assertEqual(PROTO["periods"]["validation"], E2["periods"]["validation"])
        self.assertEqual(tuple(PROTO["detectors"]["candidates"]), moonshot_e4.CANDIDATES)
        self.assertEqual(YEARS, [2020, 2021, 2022])
        for market, spec in PROTO["markets"].items():
            prof = PROFILES[market]
            self.assertEqual((spec["notional"], spec["fee_buy"], spec["fee_sell"]), (prof.notional, prof.fee_buy, prof.fee_sell))
            self.assertIsNotNone(prof.short_carry_per_session)
        self.assertIsNone(PROFILES["IDX"].short_carry_per_session)

    def test_plan_grid_is_the_declared_family(self):
        grid = e3.plan_grid(PROTO)
        self.assertEqual(len(grid), PROTO["plans"]["count"])
        for p in grid:
            self.assertIn(p["entry_rule"], ENTRY_RULES)
            self.assertNotEqual(p["entry_rule"], "unlock")
            self.assertIn(p["exit_rule"], SHORT_EXITS)
        ref = PROTO["selection"]["reference_plan"]
        self.assertIn(e3.plan_id(ref["detector"], ref), {e3.plan_id(ref["detector"], p) for p in grid})

    def test_harness_config_follows_the_protocol(self):
        plan = {"entry_rule": "confirm", "entry_window": 3, "exit_rule": "stop_high", "holding_days": 3}
        cfg = e4.harness_config(PROTO, "CRYPTO", "E4_CAND_G2_RET30", "discovery", plan, side="short")
        self.assertEqual((cfg.market, cfg.side, cfg.exit_rule, cfg.holding_days), ("CRYPTO", "short", "stop_high", 3))
        self.assertEqual((cfg.start, cfg.end), tuple(PROTO["periods"]["discovery"]))
        self.assertEqual((cfg.ca_mode, cfg.fill_model, cfg.notional), ("adjusted", "A", 5000.0))
        self.assertLess(cfg.end, PROTO["periods"]["holdout"][0])
        bare = e4.harness_config(PROTO, "CRYPTO", "MOONSHOT_E4_D1", "validation")
        self.assertIsNone(bare.side)  # the frozen rule's plan carries the side


class CandidateRuleTests(unittest.TestCase):
    def test_candidates_are_registered_and_pass_the_source_audit(self):
        reg = rules.registry()
        for name in moonshot_e4.CANDIDATES:
            self.assertIn(moonshot_e4.candidate_rule_id(name), reg)
            self.assertIsNone(reg[moonshot_e4.candidate_rule_id(name)].plan)
        self.assertEqual("MOONSHOT_E4_D1" in reg, moonshot_e4.SELECTED is not None)
        self.assertEqual(audit_module(moonshot_e4), [])

    def test_copied_flags_match_the_e2_family(self):
        df, _ = random_walk_panel(n_tickers=30, n_sessions=120, seed=5)
        df["open"] = df["previous"]  # an opening price (the G family reads it for the gap)
        m = Market.from_panel(df, price_limits=False)
        args = (m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
        ours = moonshot_e4.family_flags(moonshot_e4.features(*args))
        theirs = moonshot_g.family_flags(moonshot_g.features(*args))
        for name in moonshot_e4.CANDIDATES:
            np.testing.assert_array_equal(ours[name], theirs[name])

    def test_frozen_plan_carries_the_short_side(self):
        self.assertIsNone(moonshot_e4.selected_plan())
        saved = moonshot_e4.SELECTED
        try:
            moonshot_e4.SELECTED = ("G2_RET30", "confirm", 3, "stop_high", 3)
            self.assertEqual(moonshot_e4.selected_plan(), {"entry_rule": "confirm", "entry_window": 3,
                                                           "exit_rule": "stop_high", "side": "short"})
            found = {r.rule_id: r for r in moonshot_e4.rules()}
            self.assertEqual(found["MOONSHOT_E4_D1"].plan["side"], "short")
            self.assertEqual(found["MOONSHOT_E4_D1"].holding_days, 3)
        finally:
            moonshot_e4.SELECTED = saved


class SelectionTests(unittest.TestCase):
    def test_admissibility_adds_hit_rate_and_tail(self):
        self.assertEqual(e4.admissibility(row(), PROTO, YEARS), [])
        self.assertTrue(any("hit rate" in r for r in e4.admissibility(row(hit_rate=0.49), PROTO, YEARS)))
        self.assertTrue(any("tail" in r for r in e4.admissibility(row(p1_net_return=-0.51), PROTO, YEARS)))
        self.assertTrue(any("2021" in r for r in e4.admissibility(row(avg_net_return_2021=-0.01), PROTO, YEARS)))
        self.assertEqual(e4.admissibility(row(scored_2020=49, avg_net_return_2020=-0.01), PROTO, YEARS), [])

    def test_select_takes_the_best_admissible(self):
        table = pd.DataFrame([row(plan_id="a", avg_net_return=0.05, hit_rate=0.4),
                              row(plan_id="b", avg_net_return=0.03),
                              row(plan_id="c", avg_net_return=0.04, p1_net_return=-0.8)])
        self.assertEqual(e4.select(table, PROTO, YEARS)["plan_id"], "b")
        self.assertIsNone(e4.select(pd.DataFrame([row(avg_net_return=-0.01)]), PROTO, YEARS))

    def test_tail_stats(self):
        trades = pd.DataFrame({"status": ["EXITED"] * 5 + ["SKIP_LOT"], "net_return": [0.1, 0.05, -0.02, -0.6, 0.0, np.nan]})
        t = e4.tail_stats(trades)
        self.assertEqual(t["worst_net_return"], -0.6)
        self.assertEqual(t["share_below_minus_20pct"], 0.2)
        self.assertIsNone(e4.tail_stats(trades.iloc[5:])["worst_net_return"])


class V2Tests(unittest.TestCase):
    PROTO2 = json.loads((ROOT / "research" / "E4" / "v2" / "protocol.json").read_text(encoding="utf-8"))

    def test_v2_protocol_is_v1_plus_the_declared_changes(self):
        p2 = self.PROTO2
        self.assertEqual(p2["protocol_id"], "KOD-GLOBAL-E4-v2")
        for k in ("discovery", "validation", "holdout"):
            self.assertEqual(p2["periods"][k], PROTO["periods"][k])
        self.assertEqual(p2["plans"]["entries"], PROTO["plans"]["entries"])
        self.assertEqual(p2["harness"]["liquidation"], 1.0)
        self.assertEqual(p2["harness"]["jump_ratio"], 10.0)
        self.assertEqual(tuple(p2["detectors"]["candidates"]), moonshot_e4.CANDIDATES + moonshot_e4.REGIME_CANDIDATES)
        self.assertNotIn("max_p1_loss", p2["selection"])
        self.assertEqual(p2["markets"]["CRYPTO"]["panel_manifest"], PROTO["markets"]["CRYPTO"]["panel_manifest"])
        self.assertEqual(e4.protocol(version="v2")[0]["protocol_id"], "KOD-GLOBAL-E4-v2")
        self.assertEqual(e4.market_dir("CRYPTO", "v2"), ROOT / "research" / "E4" / "v2" / "CRYPTO")
        cfg = e4.harness_config(p2, "CRYPTO", "E4_CAND_G2_RET30_BEAR", "discovery",
                                {"entry_rule": "fixed", "entry_window": 1, "exit_rule": "fixed", "holding_days": 1},
                                side="short")
        self.assertEqual((cfg.liquidation, cfg.jump_ratio), (1.0, 10.0))
        self.assertIsNone(e4.harness_config(PROTO, "CRYPTO", "E4_CAND_G2_RET30", "discovery").liquidation)

    def test_v2_tail_criteria(self):
        r = row(p5_net_return=-0.3, share_liquidated=0.01)
        self.assertEqual(e4.admissibility(r, self.PROTO2, YEARS), [])
        self.assertTrue(any("5th" in x for x in e4.admissibility(row(p5_net_return=-0.6, share_liquidated=0.0), self.PROTO2, YEARS)))
        self.assertTrue(any("liquidated" in x for x in e4.admissibility(row(p5_net_return=-0.1, share_liquidated=0.03), self.PROTO2, YEARS)))
        self.assertTrue(e4.admissibility(row(p5_net_return=None), self.PROTO2, YEARS))  # unknown tail: not admitted

    def test_bear_regime_reads_btc_only_and_is_causal(self):
        df, _ = random_walk_panel(n_tickers=12, n_sessions=130, seed=3)
        df["open"] = df["previous"]
        df.loc[df["ticker"] == "S000", "ticker"] = "BTC"
        m = Market.from_panel(df, price_limits=False)
        bear = moonshot_e4.bear_regime(m.tickers, m.close)
        btc = m.close[list(m.tickers).index("BTC")]
        mean = pd.Series(btc).rolling(50, min_periods=50).mean().to_numpy()
        np.testing.assert_array_equal(bear, np.isfinite(mean) & (btc < mean))
        self.assertFalse(bear[:49].any())
        without = moonshot_e4.bear_regime(np.array(["ETH", "SOL"]), m.close[:2])
        self.assertFalse(without.any())
        reg = rules.registry()
        for name in moonshot_e4.REGIME_CANDIDATES:
            self.assertIn(moonshot_e4.candidate_rule_id(name), reg)
        flags = moonshot_e4.all_flags(m, moonshot_e4.features(m.close, m.prev, m.high, m.low, m.volume, m.present,
                                                              m.tradeable, m.open))
        np.testing.assert_array_equal(flags["G2_RET30_BEAR"], flags["G2_RET30"] & bear[None, :])
        self.assertEqual(audit_module(moonshot_e4), [])


class HoldoutTests(unittest.TestCase):
    def test_global_holdout_is_refused_for_us_and_crypto_detectors(self):
        from idxsig.backtest import GLOBAL_HOLDOUT, HoldoutSealed, RunConfig, run
        from tests.rulekit import module_rule, with_rule

        self.assertEqual(GLOBAL_HOLDOUT[0], PROTO["periods"]["holdout"][0])
        df, meta = random_walk_panel(start="2023-10-02", n_sessions=120)
        df["open"] = df["previous"]
        meta = {**meta, "default_start": "2023-10-02", "quality_tiers": [], "known_limitations": []}
        rule = module_rule("EDGEG", """
def compute(m):
    out = np.zeros(m.shape)
    out[0, ::7] = 1.0
    return np.where(m.tradeable, out, np.nan)
""")
        with with_rule(rule):
            with self.assertRaises(HoldoutSealed):
                run(RunConfig("EDGEG", market="CRYPTO", ca_mode="adjusted", random_draws=5), df, meta)
            out = run(RunConfig("EDGEG", market="CRYPTO", ca_mode="adjusted", random_draws=5, end="2023-12-29"),
                      df, meta)
            self.assertEqual(out["summary"]["universe"]["last_session"], "2023-12-29")


if __name__ == "__main__":
    unittest.main()

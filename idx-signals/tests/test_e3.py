"""Experiment E3: protocol, candidate rules, selection rule, harness wiring. Synthetic data only."""

import dataclasses
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import e3, rules
from idxsig.backtest import RunConfig
from idxsig.execution import ENTRY_RULES, EXIT_RULES, Market
from idxsig.rules import moonshot_e1, moonshot_e3
from idxsig.rules.audit import audit_module
from tests.rulekit import module_rule, with_rule
from tests.support import random_walk_panel, run_synthetic

ROOT = Path(__file__).resolve().parents[1]
PROTO = json.loads((ROOT / "research" / "E3" / "protocol.json").read_text(encoding="utf-8"))
E1 = json.loads((ROOT / "research" / "E1" / "protocol.json").read_text(encoding="utf-8"))
YEARS = e3.years_of(PROTO["periods"]["discovery"])


def row(**kw):
    base = {
        "plan_id": "x",
        "detector": "F1_ARA",
        "entry_rule": "fixed",
        "entry_window": 1,
        "exit_rule": "fixed",
        "holding_days": 5,
        "scored": 500,
        "avg_net_return": 0.02,
        "p_one_sided_vs_matched": 0.005,
        "scored_2021": 300,
        "avg_net_return_2021": 0.03,
        "scored_2022": 200,
        "avg_net_return_2022": 0.01,
    }
    base.update(kw)
    return base


class ProtocolTests(unittest.TestCase):
    def test_frozen_and_consistent_with_e1(self):
        self.assertTrue(PROTO["frozen_before_analysis"])
        self.assertEqual(PROTO["periods"]["discovery"], E1["periods"]["discovery"])
        self.assertEqual(PROTO["periods"]["validation"], E1["periods"]["validation"])
        self.assertEqual(PROTO["periods"]["holdout"], E1["periods"]["holdout"])
        self.assertEqual(tuple(PROTO["detectors"]["candidates"]), moonshot_e3.CANDIDATES)
        self.assertEqual(PROTO["harness"]["fill_model"], "C")
        self.assertEqual(PROTO["harness"]["ca_mode"], "registry")

    def test_plan_grid_is_the_declared_family(self):
        grid = e3.plan_grid(PROTO)
        self.assertEqual(len(grid), PROTO["plans"]["count"])
        self.assertEqual(len({e3.plan_id("D", p) for p in grid}), len(grid))
        for p in grid:
            self.assertIn(p["entry_rule"], ENTRY_RULES)
            self.assertIn(p["exit_rule"], EXIT_RULES)
            self.assertGreaterEqual(
                p["holding_days"], 2
            )  # with 1 every exit rule is the fixed exit
        ref = PROTO["selection"]["reference_plan"]
        self.assertIn(
            e3.plan_id(ref["detector"], ref), {e3.plan_id(ref["detector"], p) for p in grid}
        )

    def test_harness_config_follows_the_protocol(self):
        plan = {
            "entry_rule": "confirm",
            "entry_window": 3,
            "exit_rule": "stop_ref",
            "holding_days": 3,
        }
        cfg = e3.harness_config(PROTO, "E3_CAND_F1_ARA", "discovery", plan)
        self.assertEqual((cfg.start, cfg.end), tuple(PROTO["periods"]["discovery"]))
        self.assertEqual(
            (cfg.entry_rule, cfg.entry_window, cfg.exit_rule, cfg.holding_days),
            ("confirm", 3, "stop_ref", 3),
        )
        self.assertEqual((cfg.fill_model, cfg.ca_mode, cfg.units), ("C", "registry", "panel"))
        self.assertEqual(cfg.notional, PROTO["harness"]["notional_idr"])
        bare = e3.harness_config(PROTO, "MOONSHOT_E3_D1", "validation")
        self.assertIsNone(bare.entry_rule)  # the frozen rule's own plan applies
        self.assertIsNone(bare.holding_days)


class CandidateRuleTests(unittest.TestCase):
    def test_candidates_are_registered_and_pass_the_source_audit(self):
        reg = rules.registry()
        for name in moonshot_e3.CANDIDATES:
            self.assertIn(moonshot_e3.candidate_rule_id(name), reg)
            self.assertEqual(reg[moonshot_e3.candidate_rule_id(name)].kind, "DETECTOR")
        self.assertEqual("MOONSHOT_E3_D1" in reg, moonshot_e3.SELECTED is not None)
        self.assertEqual(audit_module(moonshot_e3), [])

    def test_copied_flags_match_the_e1_family(self):
        df, _ = random_walk_panel(n_tickers=30, n_sessions=120, seed=11)
        m = Market.from_panel(df)
        args = (m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
        ours = moonshot_e3.family_flags(moonshot_e3.features(*args))
        theirs = moonshot_e1.family_flags(moonshot_e1.features(*args))
        for name in moonshot_e3.CANDIDATES:
            np.testing.assert_array_equal(ours[name], theirs[name])
        reg = rules.registry()
        for name in moonshot_e3.CANDIDATES:
            sig = reg[moonshot_e3.candidate_rule_id(name)].compute(m)
            np.testing.assert_array_equal(
                np.nan_to_num(sig, nan=-1), np.where(m.tradeable, theirs[name], -1)
            )

    def test_selected_tuple_round_trips_into_a_plan(self):
        chosen = row(
            detector="F8_ARA_EARLY",
            entry_rule="confirm",
            entry_window=3,
            exit_rule="stop_ref",
            holding_days=3,
        )
        self.assertEqual(e3.selected_tuple(chosen), ("F8_ARA_EARLY", "confirm", 3, "stop_ref", 3))


class SelectionTests(unittest.TestCase):
    def test_admissibility_reasons(self):
        self.assertEqual(e3.admissibility(row(), PROTO, YEARS), [])
        self.assertTrue(any("scored" in r for r in e3.admissibility(row(scored=199), PROTO, YEARS)))
        self.assertTrue(
            any(
                "not positive" in r for r in e3.admissibility(row(avg_net_return=0.0), PROTO, YEARS)
            )
        )
        self.assertTrue(
            any(
                "p vs matched" in r
                for r in e3.admissibility(row(p_one_sided_vs_matched=0.05), PROTO, YEARS)
            )
        )
        self.assertTrue(
            any("2022" in r for r in e3.admissibility(row(avg_net_return_2022=-0.01), PROTO, YEARS))
        )
        self.assertEqual(
            e3.admissibility(row(scored_2022=49, avg_net_return_2022=-0.01), PROTO, YEARS), []
        )
        self.assertTrue(e3.admissibility(row(p_one_sided_vs_matched=None), PROTO, YEARS))

    def test_select_takes_the_best_admissible_plan(self):
        table = pd.DataFrame(
            [
                row(plan_id="a", avg_net_return=0.05, p_one_sided_vs_matched=0.2),  # not admissible
                row(plan_id="b", avg_net_return=0.03, scored=400),
                row(plan_id="c", avg_net_return=0.03, scored=600),  # tie: more trades
                row(plan_id="d", avg_net_return=0.01),
            ]
        )
        self.assertEqual(e3.select(table, PROTO, YEARS)["plan_id"], "c")
        none = pd.DataFrame([row(plan_id="a", avg_net_return=-0.01)])
        self.assertIsNone(e3.select(none, PROTO, YEARS))


EDGE_BODY = """
def compute(m):
    out = np.zeros(m.shape)
    out[0, ::7] = 1.0
    out[1, 3::11] = 1.0
    return np.where(m.tradeable, out, np.nan)
"""


class HarnessCacheTests(unittest.TestCase):
    def test_signal_cache_reuses_signals_and_changes_nothing(self):
        df, meta = random_walk_panel()
        rule = module_rule("CACHED", EDGE_BODY)
        cache = {}
        with with_rule(rule):
            a = run_synthetic(RunConfig("CACHED", random_draws=10), df, meta)["summary"]
            from idxsig.backtest import run
            from tests.support import synthetic_registry

            reg = synthetic_registry(df, meta)
            b = run(
                RunConfig("CACHED", random_draws=10), df, meta, ca_registry=reg, signal_cache=cache
            )["summary"]
            c = run(
                RunConfig("CACHED", random_draws=10, holding_days=2, exit_rule="first_down"),
                df,
                meta,
                ca_registry=reg,
                signal_cache=cache,
            )["summary"]
        self.assertEqual(len(cache), 1)
        self.assertEqual(a["rule_trades"], b["rule_trades"])
        self.assertEqual(a["signals"], b["signals"])
        self.assertEqual(c["signals"]["total"], a["signals"]["total"])
        self.assertEqual(c["execution"]["plan"]["exit_rule"], "first_down")

    def test_plan_row_reads_a_summary(self):
        df, meta = random_walk_panel()
        rule = dataclasses.replace(
            module_rule("ROWED", EDGE_BODY),
            plan={"entry_rule": "unlock", "entry_window": 2, "exit_rule": "fixed"},
        )
        with with_rule(rule):
            s = run_synthetic(RunConfig("ROWED", random_draws=10), df, meta)["summary"]
        plan = {"entry_rule": "unlock", "entry_window": 2, "exit_rule": "fixed", "holding_days": 5}
        r = e3.plan_row(s, "F1_ARA", plan, [2023])
        self.assertEqual(r["plan_id"], "F1_ARA|unlock2|fixed|h5")
        self.assertEqual(r["scored"], s["rule_trades"]["scored"])
        self.assertEqual(r["scored_2023"], s["rule_trades"]["scored"])
        self.assertIn("p_one_sided_vs_matched", r)


if __name__ == "__main__":
    unittest.main()

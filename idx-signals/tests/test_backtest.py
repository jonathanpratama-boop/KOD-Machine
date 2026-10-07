import sys
import unittest
from unittest import mock

import numpy as np

from idxsig import rules
from idxsig.backtest import LookaheadError, RunConfig, run
from tests.support import random_walk_panel


def make_rule(rule_id, compute, holding=5):
    return rules.Rule(rule_id, "test", f"test rule {rule_id}", holding, compute, sys.modules[__name__])


def with_rule(rule):
    real = rules.registry

    def patched():
        out = real()
        out[rule.rule_id] = rule
        return out

    return mock.patch.object(rules, "registry", patched)


class BacktestTests(unittest.TestCase):
    def test_placebo_runs_over_the_full_universe(self):
        df, meta = random_walk_panel(delist={3: 80})
        out = run(RunConfig("PLACEBO_COINFLIP", random_draws=50), df, meta)
        s = out["summary"]
        self.assertEqual(s["universe"]["tickers_in_window"], 40)
        self.assertEqual(s["universe"]["tickers_ending_inside_window"], 1)
        self.assertEqual(s["signals"]["total"], len(out["trades"]))
        self.assertEqual(len(out["draws"]), 100)  # 50 matched + 50 same-session
        self.assertEqual(sorted(out["draws"]["baseline"].unique()), ["random", "random_matched"])
        self.assertEqual(s["lookahead_check"]["mode"], "exhaustive")
        self.assertEqual(s["lookahead_check"]["sessions_checked"], s["universe"]["sessions"])
        self.assertIn("PLACEBO", " ".join(s["warnings"]))

    def test_runs_are_deterministic(self):
        df, meta = random_walk_panel()
        a = run(RunConfig("PLACEBO_COINFLIP", random_draws=20), df, meta)["summary"]
        b = run(RunConfig("PLACEBO_COINFLIP", random_draws=20), df, meta)["summary"]
        self.assertEqual(a["random"], b["random"])
        self.assertEqual(a["rule_trades"], b["rule_trades"])

    def test_rule_that_reads_ahead_is_refused(self):
        def peek(m):
            tomorrow = np.roll(m.close, -1, axis=1)
            out = (tomorrow > m.close).astype(float)
            out[:, -1] = np.nan
            return np.where(m.tradeable, out, np.nan)

        df, meta = random_walk_panel()
        with with_rule(make_rule("PEEK", peek)):
            with self.assertRaises(LookaheadError):
                run(RunConfig("PEEK", random_draws=5), df, meta)

    def test_real_edge_beats_random_and_noise_does_not(self):
        df, meta = random_walk_panel(drift={0: 0.01})

        def first_name(m):
            out = np.zeros(m.shape)
            out[0, ::7] = 1.0
            return np.where(m.tradeable, out, np.nan)

        with with_rule(make_rule("EDGE", first_name)):
            s = run(RunConfig("EDGE", random_draws=200), df, meta)["summary"]
        self.assertGreater(s["rule_trades"]["avg_net_return"], s["random"]["avg_net_return"]["random_p97_5"])
        self.assertLess(s["random"]["avg_net_return"]["p_value_one_sided"], 0.01)

    def test_overlapping_signals_are_skipped_while_held(self):
        df, meta = random_walk_panel()

        def every_day_first_name(m):
            out = np.zeros(m.shape)
            out[0, :] = 1.0
            return np.where(m.tradeable, out, np.nan)

        with with_rule(make_rule("DAILY", every_day_first_name, holding=5)):
            out = run(RunConfig("DAILY", random_draws=5), df, meta)
        sig = out["summary"]["signals"]
        self.assertGreater(sig["skipped_overlap"], 0)
        trades = out["trades"]
        held = trades[trades["status"] == "EXITED"]
        self.assertTrue((held["entry_date"].to_numpy()[1:] > held["exit_date"].to_numpy()[:-1]).all())

    def test_user_rule_is_pending_not_guessed(self):
        self.assertIn("USER_RULE", rules.pending())
        with self.assertRaises(rules.RuleNotProvided):
            rules.get("USER_RULE")


if __name__ == "__main__":
    unittest.main()

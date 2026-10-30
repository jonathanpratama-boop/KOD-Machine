"""Per-trade control means on the trades frame and the paired-excess statistic (E5 protocol draft,
matched_controls.paired_statistic). Synthetic markets only; the draws are made deterministic by
construction (clone names) or by patching controls.matched_draws."""

import json
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import backtest, controls
from idxsig.backtest import RunConfig, paired_excess, per_signal_excess
from tests.rulekit import module_rule, with_rule
from tests.support import random_walk_panel
from tests.support import run_synthetic as run

ORIGINAL_TRADE_COLUMNS = [
    "ticker",
    "signal_date",
    "status",
    "entry_date",
    "exit_date",
    "entry_price",
    "shares",
    "exit_price",
    "share_factor",
    "rolled_sessions",
    "gross_return",
    "net_return",
]
NEW_COLUMNS = ["matched_mean_net_return", "same_session_mean_net_return"]
DRAW_COLUMNS = [
    "draw",
    "scored",
    "fill_rate",
    "hit_rate",
    "avg_net_return",
    "median_net_return",
    "baseline",
]


def every_seventh(row: int, evaluable_rows: int | None = None) -> str:
    """A rule signalling name `row` every 7th session; evaluable on the first `evaluable_rows` names only."""
    mask = f"\n            out[{evaluable_rows}:, :] = np.nan" if evaluable_rows is not None else ""
    return f"""
        def compute(m):
            out = np.zeros(m.shape)
            out[{row}, ::7] = 1.0
            out = np.where(m.tradeable, out, np.nan){mask}
            return out
    """


def clone_panel():
    """S001 is a byte-for-byte clone of S000, so a control drawn from either earns what S000 earns."""
    df, meta = random_walk_panel(n_tickers=12, n_sessions=90, seed=11)
    df = df[df["ticker"] != "S001"]
    df = pd.concat([df, df[df["ticker"] == "S000"].assign(ticker="S001")], ignore_index=True)
    return df, meta


def alternating(ticker_a: int, ticker_b: int):
    """A stand-in for controls.matched_draws: even draws take ticker_a, odd draws ticker_b."""

    def fake(evaluable, feats, a_tick, a_sig, draws, rng, version="v2"):
        col = np.where(np.arange(draws) % 2 == 0, ticker_a, ticker_b).astype(np.int64)
        return np.repeat(col[:, None], len(a_sig), axis=1), np.zeros(len(a_sig), dtype=np.int8)

    return fake


class PairedColumnTests(unittest.TestCase):
    def test_columns_equal_the_control_outcome_when_every_control_is_a_clone(self):
        df, meta = clone_panel()
        rule = module_rule("PAIR0", every_seventh(0, evaluable_rows=2))
        with with_rule(rule):
            out = run(RunConfig("PAIR0", random_draws=6), df, meta)
        trades = out["trades"]
        self.assertEqual(list(trades.columns), ORIGINAL_TRADE_COLUMNS + NEW_COLUMNS)
        self.assertGreater(int(trades["status"].eq("EXITED").sum()), 5)
        # same-session draws come from {S000, S001}, matched draws from {S001}: both are S000's own path
        net = trades["net_return"].to_numpy(dtype=float)
        np.testing.assert_array_equal(
            trades["same_session_mean_net_return"].to_numpy(dtype=float), net
        )
        np.testing.assert_array_equal(trades["matched_mean_net_return"].to_numpy(dtype=float), net)
        self.assertAlmostEqual(
            out["summary"]["random_matched"]["avg_net_return"]["random_mean"],
            out["summary"]["rule_trades"]["avg_net_return"],
            places=12,
        )

    def test_matched_mean_averages_the_scored_draws(self):
        df, meta = clone_panel()
        signal = module_rule("PAIRS", every_seventh(0))
        with with_rule(signal), mock.patch.object(controls, "matched_draws", alternating(3, 4)):
            out = run(RunConfig("PAIRS", random_draws=4), df, meta)
        expected = {}
        for k in (3, 4):
            ctrl = module_rule(f"CTRL{k}", every_seventh(k))
            with with_rule(ctrl):
                t = run(RunConfig(f"CTRL{k}", random_draws=2, overlap="allow"), df, meta)["trades"]
            expected[k] = t.set_index("signal_date")["net_return"]
        trades = out["trades"].set_index("signal_date")
        self.assertEqual(list(trades.index), list(expected[3].index))
        both = pd.concat([expected[3], expected[4]], axis=1).to_numpy(dtype=float)
        with np.errstate(invalid="ignore"):
            want = np.where(
                np.isfinite(both).any(axis=1),
                np.nansum(both, axis=1) / np.isfinite(both).sum(axis=1),
                np.nan,
            )
        np.testing.assert_allclose(
            trades["matched_mean_net_return"].to_numpy(dtype=float), want, rtol=0, atol=1e-15
        )
        self.assertTrue(np.isfinite(want).any())
        self.assertTrue(np.isnan(want).any())  # the last signals run past the data on every name

    def test_no_control_is_drawn_for_an_overlap_skipped_signal(self):
        df, meta = random_walk_panel(n_tickers=12, n_sessions=90, seed=11)
        daily = module_rule(
            "PAIRD",
            """
            def compute(m):
                out = np.zeros(m.shape)
                out[0, :] = 1.0
                return np.where(m.tradeable, out, np.nan)
        """,
        )
        with with_rule(daily):
            trades = run(RunConfig("PAIRD", random_draws=50), df, meta)["trades"]
        skipped = trades["status"] == "SKIP_OVERLAP"
        self.assertGreater(int(skipped.sum()), 0)
        for col in NEW_COLUMNS:
            self.assertTrue(trades.loc[skipped, col].isna().all(), col)
            self.assertTrue(trades.loc[trades["status"] == "EXITED", col].notna().all(), col)

    def test_columns_are_present_when_no_signal_is_attempted(self):
        df, meta = random_walk_panel(n_tickers=8, n_sessions=60, seed=3)
        silent = module_rule(
            "PAIRN",
            """
            def compute(m):
                return np.where(m.tradeable, 0.0, np.nan)
        """,
        )
        with with_rule(silent):
            out = run(RunConfig("PAIRN", random_draws=5), df, meta)
        self.assertEqual(len(out["trades"]), 0)
        self.assertEqual(list(out["trades"].columns), ORIGINAL_TRADE_COLUMNS + NEW_COLUMNS)
        self.assertEqual(len(out["draws"]), 0)
        self.assertEqual(paired_excess(out["trades"], resamples=10)["n"], 0)

    def test_summary_and_draws_are_unchanged(self):
        df, meta = random_walk_panel(n_tickers=12, n_sessions=90, seed=11)
        out = run(RunConfig("PLACEBO_COINFLIP", random_draws=20), df, meta)
        text = json.dumps(out["summary"], default=str)
        for col in NEW_COLUMNS:
            self.assertNotIn(col, text)
        self.assertEqual(list(out["draws"].columns), DRAW_COLUMNS)
        self.assertEqual(len(out["draws"]), 40)


class PairedExcessTests(unittest.TestCase):
    TOY = pd.DataFrame(
        {
            "signal_date": [
                "2023-01-02",
                "2023-01-02",
                "2023-01-03",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
            ],
            "net_return": [0.05, 0.06, 0.02, 0.00, np.nan, 0.10],
            "matched_mean_net_return": [0.03, 0.02, 0.01, 0.01, 0.01, np.nan],
        }
    )

    def test_per_signal_excess(self):
        ex = per_signal_excess(self.TOY)
        np.testing.assert_allclose(ex.to_numpy()[:4], [0.02, 0.04, 0.01, -0.01], atol=1e-15)
        self.assertTrue(ex.iloc[4:].isna().all())  # no rule outcome, no control mean

    def test_toy_frame_has_the_known_answer(self):
        r = paired_excess(self.TOY, resamples=10000, seed=1)
        self.assertEqual((r["n"], r["n_clusters"], r["resamples"], r["seed"]), (4, 2, 10000, 1))
        self.assertAlmostEqual(r["mean_excess"], 0.015, places=15)
        # two clusters, means +0.03 (A,A), +0.015 (A,B / B,A), 0.0 (B,B): a quarter of the resamples are <= 0
        self.assertGreater(r["p_one_sided"], 0.22)
        self.assertLess(r["p_one_sided"], 0.28)
        self.assertAlmostEqual(r["ci95"][0], 0.0, places=15)
        self.assertAlmostEqual(r["ci95"][1], 0.03, places=15)
        self.assertEqual(r["cluster"], "signal_date")

    def test_every_cluster_positive_gives_the_floor_p(self):
        frame = pd.DataFrame(
            {
                "signal_date": ["a", "a", "b", "c"],
                "net_return": [0.1, 0.2, 0.3, 0.4],
                "matched_mean_net_return": [0.0, 0.0, 0.0, 0.0],
            }
        )
        r = paired_excess(frame, resamples=999, seed=5)
        self.assertAlmostEqual(r["p_one_sided"], 1 / 1000, places=15)
        self.assertEqual(r["n_clusters"], 3)
        negative = frame.assign(matched_mean_net_return=1.0)
        self.assertEqual(paired_excess(negative, resamples=999, seed=5)["p_one_sided"], 1.0)

    def test_empty_frame(self):
        r = paired_excess(self.TOY.iloc[4:], resamples=10)
        self.assertEqual((r["n"], r["n_clusters"]), (0, 0))
        self.assertIsNone(r["mean_excess"])
        self.assertIsNone(r["p_one_sided"])
        self.assertIsNone(r["ci95"])

    def test_bootstrap_is_reproducible_under_the_seed(self):
        a = paired_excess(self.TOY, resamples=2000, seed=20261015)
        b = paired_excess(self.TOY, resamples=2000, seed=20261015)
        self.assertEqual(a, b)
        default = paired_excess(self.TOY)
        self.assertEqual((default["resamples"], default["seed"]), (10000, 20261015))
        self.assertEqual(default, paired_excess(self.TOY, resamples=10000, seed=20261015))
        with self.assertRaises(ValueError):
            paired_excess(self.TOY, resamples=0)

    def test_overlap_skipped_rows_do_not_enter_the_statistic(self):
        frame = pd.DataFrame(
            {
                "signal_date": ["a", "a"],
                "status": ["EXITED", "SKIP_OVERLAP"],
                "net_return": [0.1, 0.5],
                "matched_mean_net_return": [0.0, np.nan],
            }
        )
        self.assertEqual(paired_excess(frame, resamples=10)["n"], 1)

    def test_runs_on_a_harness_trades_frame(self):
        df, meta = random_walk_panel(n_tickers=12, n_sessions=90, seed=11)
        rule = module_rule("PAIRH", every_seventh(2))
        with with_rule(rule):
            trades = run(RunConfig("PAIRH", random_draws=30), df, meta)["trades"]
        r = paired_excess(trades, resamples=200)
        self.assertEqual(r["n"], int(np.isfinite(per_signal_excess(trades)).sum()))
        self.assertEqual(
            r["n_clusters"], trades.loc[per_signal_excess(trades).notna(), "signal_date"].nunique()
        )
        self.assertGreater(r["n"], 0)
        self.assertTrue(0 < r["p_one_sided"] <= 1)
        self.assertEqual(backtest.paired_excess, paired_excess)


if __name__ == "__main__":
    unittest.main()

# Phase 2 integration TODO (collected from builder reports; apply when merging e5/* into claude/e5-ceiling)

## from build:h1-controls (commit c537606 on e5/h1-controls)
- `idx-signals/idxsig/cli.py` ~line 91: add "v3" to `--controls-version` choices (default stays "v2").
- `idx-signals/idxsig/e1.py` line 151: `Study` hard-codes `controls.features(m, "v2", ...)`; the E5 detection stage needs the h3-e1 opt-in (`pool_version='v3'`) to pass "v3" there — check h3's branch covers it, else do it at integration.
- Docstring figure "28% of IDX attempts never matched on volatility under v2" is quoted from the synthesis, not recomputed; verify at Stage 0 or soften the wording.

## from build:h2-backtest (commit 0d2da5d on e5/h2-backtest)
- New trades columns `matched_mean_net_return`, `same_session_mean_net_return` (mean over SCORED draws only; unscored SKIP_*/INCOMPLETE draws excluded — note this definition in protocol.json). Helpers `backtest.per_signal_excess()` and `backtest.paired_excess(trades_df, resamples=10000, seed=20261015, column=..., cluster='signal_date')` → n, n_clusters, mean_excess, p_one_sided ((1+count)/(1+resamples), floor ≈1e-4), ci95. summary.json unchanged by design.
- `e5.py` must call `backtest.paired_excess(output['trades'])` after each `backtest.run` and record the dict in plans.csv / result.json; the Stage-2 gate reads `p_one_sided` from it.
- Cluster key compares `signal_date` as strings (exact for harness frames); consumers select the new columns by name, not position (they are last in every configuration).
- Optional further column (count of scored draws per signal) not added; decide at protocol freeze.

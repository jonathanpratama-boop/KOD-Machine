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

## from build:h4-profiles (commit 963a57d on e5/h4-profiles)
- `profiles.CRYPTO_CLOSE` = CRYPTO with entry="close"; `PROFILES["CRYPTO_CLOSE"]`; `.market` stays "CRYPTO". 6 tests; 250 tests OK.
- `cli.py:73` `run --market` choices need "CRYPTO_CLOSE"; `cli.py:293` must load the panel via `global_panel.latest(PROFILES[args.market].market)` (no CRYPTO_CLOSE panel exists). Do NOT touch the e4-* choices (`cli.py:141`); the e5-* subcommands get their own list.
- `e5.py` (clone of e4.harness_config/market_dir): key the protocol `markets` block and the output dir by the RunConfig market name, but map `PROFILES[market].market` → panel. Protocol needs a "CRYPTO_CLOSE" markets entry pointing at the CRYPTO panel/precondition.
- Fill-model constraint: with entry "close", `execution.py` refuses fill B (open-only) and refuses C unless units=panel & ca_mode=registry; crypto runs use ca_mode "adjusted" → CRYPTO_CLOSE sensitivity must use fill A (the protocol draft says A; keep it).
- Never pass CRYPTO_CLOSE into the paper path (`paper.py` literal {IDX,US,CRYPTO} dicts would KeyError); it is a research sensitivity only.

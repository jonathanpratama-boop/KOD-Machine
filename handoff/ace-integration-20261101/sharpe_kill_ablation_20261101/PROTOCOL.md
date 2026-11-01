# Sharpe-kill ablation — protocol (frozen before any challenger result)

**Classification: reused-data diagnostic, not independent validation.** It reuses the BTC/ETH daily history that the
published replay (and FRESH_EYES before it) already used. It can describe what the permanent negative-90-day-Sharpe
kill did on this history. It cannot show that removing the rule would improve future returns.

## Question

In the published shared-account trend replay, did the permanent negative-trailing-90-day-Sharpe kill materially
suppress returns, materially protect capital, or both?

## Prior work check (done before this protocol)

No existing KOD result isolates this rule. The published replay ran four fixed policies: shared trend (both kills),
buy-once 50/50 with the same kills, conventional buy-and-hold with no kills, and cash. The only no-kill case removes
both kills from a buy-and-hold account, so it does not isolate the Sharpe rule.

## Baseline (reproduced exactly, 2026-11-01)

The published run `historical_shared_account_results_20261101T1134` was reproduced with its canonical command and
clearance, under the offline guard. Inputs: the 220 Binance archive URLs in `input_allowlist.json`, re-downloaded and
each checked against its pinned size and SHA256 (465,071 bytes in total). Result: all 8 journals byte-identical to the
hash-pinned archive copy; all 8 summaries and `INPUT_VALIDATION.json` byte-identical; `RESULTS.json` identical except its
two wall-clock fields (`started_at`, `finished_at`), which record when a run happened and so cannot match on a re-run.
Log: `logs/baseline_reproduction_check.log`.

## Challenger (the only change)

`challenger_engine/` is a copy of the published engine directory. Exactly one line differs (`CHALLENGER.diff`):
`daily_core.py` line 445, the negative-trailing-90-day-Sharpe trigger, is disabled. Everything else is byte-identical
(hashes in `FREEZE.json`):

- same data, partitions (development 2017-09-26 → 2023-01-01 opening; validation 2023-01-01 → 2026-09-30 opening),
  each a separate 10,000 USDT account;
- same signal (SMA10 > SMA40), sizing (min(1, 0.015/σ20) per coin, scaled down only if the sum exceeds 1), shared cash,
  fee 0.1% and slippage 0.05% per side, synthetic 0.1%-of-known-volume capacity, decision on prior-day closes with fill
  at the following open, intent expiry, terminal exit and journal checks;
- the 25% drawdown kill is unchanged and stays permanent; no restart logic is added;
- the trailing Sharpe status is still computed and recorded every day, so the report can show when the removed rule
  would have fired.

Only `TREND_V2_SHARED` is run. Benchmarks come from the published run, unchanged.

## Harness

`run_challenger.py` calls the engine's own `replay.run_case()` exactly as `replay.main()` does, for this one policy.
Equivalence check before the freeze: run with the unmodified published engine, it reproduced the published trend
journals and summaries byte for byte (`logs/harness_check_comparison.log`). `compare.py` was also run baseline-vs-baseline
before the freeze and reported no divergence (`logs/compare_selftest.log`).

## Reported (fixed now)

Per partition: first divergence (operation and date); additional fills; ending NAV, total and annualised growth;
sampled maximum drawdown; whole-partition volatility and Sharpe; time invested, and volatility while invested; fees and
turnover; whether and when the 25% drawdown kill fires in the challenger, with the intents it cancelled, the liquidation
fills and the drawdown actually reached; the days on which the removed Sharpe rule would have fired; year-end NAVs;
an annotated timeline separating recorded baseline events from the diagnostic challenger run. Benchmarks: cash,
passive 50/50 with the same kills (capacity-limited to 45.31% exposure in development), and conventional buy-and-hold
with no kills, all from the published run, with their different risk policies stated.

## Reading rule (fixed now; descriptive, one historical path per partition, not a significance test)

- **Suppressed returns** in a partition: challenger ending NAV ≥ baseline ending NAV + 1,000 USDT (10% of starting cash).
- **Protected capital** in a partition: challenger sampled max drawdown ≥ baseline's + 5 percentage points, or
  challenger ending NAV ≤ baseline − 1,000 USDT.
- Both can hold. Neither: no material effect. Each partition is reported separately, also if they disagree; no pooling.

## Not allowed after results

No change to thresholds, dates, costs, sizing, the drawdown level, or the engine; no restart logic; no further variants
or reruns. A disappointing answer is recorded as it is. The operational paper protocol is not touched.

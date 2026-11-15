# MAJORS_TREND_v1: the frozen 10/40 trend rule on eight majors it was not chosen on

Written 2026-11-15 (UTC), before any price of the eight coins below was fetched or read for this test. Paper research
only: spot coin and cash, no leverage, no orders. Requested by the owner on 2026-11-15 ("do them in order").

## Why

ETH_TREND_REPRO_v1 found that the 10/40 rule beat holding ETH's own average exposure since 2023 by about 29 points a
year (Binance costs), but that this is not significant once the choice among four rules is allowed for (p 0.091). The
rule was chosen on ETH (and read on BTC, where it did not beat holding). This test asks, once, whether the same rule
beats exposure-matched holding on eight major coins on which it was never chosen.

## What is fixed now

- **Coins:** SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, LTCUSDT: the eight other coins of
  FRESH_EYES_v1's `majors.txt`, Binance spot daily klines, the monthly archives pinned by sha256 in
  `handoff/fresh-eyes-2026-11-01/backtests/manifests/manifest_spot_klines_1d.jsonl`. No coin is added or dropped.
- **Rule:** FRESH_EYES_v1 T1c unchanged: at each daily close, hold the coin from the next open when the 10-day simple
  average of the close is above the 40-day one, otherwise cash. Engine: `lib.py` and `run_t1_t5.sma_cross_positions`,
  imported unchanged. No parameter is varied.
- **Costs:** Binance 0.15% a side (decisive); eToro-style 1.00% a side (reported, not decisive).
- **Benchmark:** holding the rule's own average exposure in the window all the time, rebalanced at every open, each
  rebalancing trade paying the same cost (`matched_constant` of ETH_TREND_REPRO_v1, unchanged).
- **Primary window:** 2023-01-01 to 2026-09-29 (the pinned data end). Secondary, reported only: each coin's whole
  pinned history from its first day with 40 closes.
- **Per-coin statistic:** the annualised mean of the daily excess (rule net minus benchmark net), with a circular block
  bootstrap (20-day blocks, 10,000 resamples) for its 90% interval.
- **Pooled statistic:** the equal-weight average across the eight coins of their daily excess series on the primary
  window; one-sided p = share of 10,000 circular block-bootstrap resamples (20-day blocks, seed 20261115) whose
  annualised mean is at or below zero.

## The pass mark (decides the result)

At Binance costs, on the primary window:

- **SUPPORTED** if at least 6 of the 8 coins have a positive annualised excess AND the pooled p is at most 0.05.
- **NOT SUPPORTED** if 4 or fewer coins have a positive excess, OR the pooled annualised excess is at or below zero.
- **INCONCLUSIVE** otherwise.

What follows from each, fixed now: SUPPORTED makes slow trend-following on majors KOD's lead research line (next step:
a pre-registered prospective paper basket). NOT SUPPORTED closes trend research apart from the existing ETH paper log,
which runs to its own kill rule. INCONCLUSIVE: keep the ETH paper log only; no new trend work.

## Disclosed before running

- The person running this knows the broad history of crypto prices in 2023 to 2026 from general knowledge; no per-coin
  result of this rule was computed or read. The pass mark is fixed and simple so that knowledge cannot steer it.
- FRESH_EYES_v1 used these coins' perpetual-futures data for other rules (T3 cross-sectional momentum, T4 hourly mean
  reversion). The T1 rules were run on BTC and ETH only.
- One look: the result is reported as it comes out; no variant, window or coin change follows from it.

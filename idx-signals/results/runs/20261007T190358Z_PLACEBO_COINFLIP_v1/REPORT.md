# Run 20261007T190358Z_PLACEBO_COINFLIP_v1

Rule: **PLACEBO_COINFLIP v1** (PLACEBO), holding 5 sessions
Rule SHA-256: `b774201b08e6da68c54c7083a85d31830ca5a8342a6d0932f92a02d74fe27b68`
Code: `d2ce9fe86032a4909fb1190cf7071586f132d989`
Panel: `06b4ffcfa625fd15c0fbc195537fe18b945640fbe6d033887cea9e4d9e26d98b`
Window: 2021-01-22 .. 2025-02-21 (990 sessions, 958 tickers, 3 stop trading inside the window)

> Signal on session d for ticker t when splitmix64(crc32(t) * 2^20 + days_since_epoch(d)) / 2^64 < 0.01, for every ticker that traded on session d. Hold 5 sessions. No price input.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 7326 (rate 1.0% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 7120 | 200 draws × 7120 | 200 draws × 7120 |
| Filled | 4143 (58.2%) | 59.0% | 58.9% |
| Scored trades | 4114 | 834331 | 832842 |
| Hit rate (net return > 0) | 39.6% | 39.7% (95% of draws 38.6% .. 40.9%) | 39.7% (95% of draws 38.3% .. 41.5%) |
| Average net return | -0.57% | -0.52% (95% of draws -0.81% .. -0.28%) | -0.44% (95% of draws -0.74% .. -0.17%) |
| Median net return | -0.74% | -0.76% | -0.80% |

Average return vs matched random: -0.04% (rule at percentile 36.0 of draws, one-sided p = 0.642).
Hit rate vs matched random: -0.03% (rule at percentile 52.0 of draws, one-sided p = 0.483).
Average return vs same-session random: -0.13% (rule at percentile 18.5 of draws, one-sided p = 0.816).
Hit rate vs same-session random: -0.12% (rule at percentile 45.5 of draws, one-sided p = 0.547).

Matched controls found at: price_band+liquidity+volatility+momentum 5803, price_band+liquidity+volatility 972, price_band+liquidity 256, price_band 89

Status counts (rule): EXITED 4114, INCOMPLETE 22, EXCLUDED_CORP_ACTION 7, SKIP_NO_ENTRY_SESSION 11, SKIP_NOT_TRADED 124, SKIP_ARA_LOCK 96, SKIP_LIQUIDITY 2746

Status counts (matched random, pooled): EXITED 834295, EXIT_DATA_END 36, INCOMPLETE 4208, EXCLUDED_CORP_ACTION 1076, SKIP_NO_ENTRY_SESSION 2200, SKIP_NOT_TRADED 21987, SKIP_ARA_LOCK 18459, SKIP_LOT 49, SKIP_LIQUIDITY 541690

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 1460 | 874 | 42.7% | +0.36% | 40.9% | +0.12% | +0.07% |
| 2022 | 1687 | 1085 | 35.0% | -0.79% | 38.2% | -0.85% | -0.64% |
| 2023 | 1845 | 1071 | 40.1% | -0.94% | 40.2% | -0.78% | -0.66% |
| 2024 | 1849 | 964 | 41.6% | -0.73% | 39.4% | -0.55% | -0.48% |
| 2025 | 279 | 120 | 39.2% | -0.80% | 39.4% | +0.23% | -0.11% |

## Execution

- official close; signal at close of s, entry at close of s + entry_lag, entry lag 1
- 100-share lots, notional Rp 10,000,000 per trade, at most 10% of session volume
- Fees: buy 0.15%, sell 0.25%
- entry refused when the entry close is locked at ARA; exit rolls while locked at ARB or untraded; regular-board schedule by date, plus 10% special-board limits on one-price or sub-Rp50 bars
- Corporate actions: splits and reverse splits scale shares; a trade held across any other reference reset (rights issue, bonus, stock dividend) is excluded
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: exhaustive: the rule was recomputed on all 990 prefixes; 0 signals changed

## Warnings

- 7 trades were held across a rights issue or other non-split corporate action and are not scored (ca_mode=exclude); the baselines apply the same rule
- PLACEBO rule: harness self-check, not a trading rule; any lift here is a harness bias

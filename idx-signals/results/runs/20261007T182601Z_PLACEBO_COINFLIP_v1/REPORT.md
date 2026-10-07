# Run 20261007T182601Z_PLACEBO_COINFLIP_v1

Rule: **PLACEBO_COINFLIP v1** (PLACEBO), holding 5 sessions
Rule SHA-256: `b774201b08e6da68c54c7083a85d31830ca5a8342a6d0932f92a02d74fe27b68`
Code: `b6061395b066ac2b49fd677d51a878ed16f2a101`
Panel: `06b4ffcfa625fd15c0fbc195537fe18b945640fbe6d033887cea9e4d9e26d98b`
Window: 2019-07-29 .. 2025-02-21 (1355 sessions, 958 tickers, 3 stop trading inside the window)

> Signal on session d for ticker t when splitmix64(crc32(t) * 2^20 + days_since_epoch(d)) / 2^64 < 0.01, for every ticker that traded on session d. Hold 5 sessions. No price input.

## Result

| | Rule | Random (same sessions, same execution) |
|---|---:|---:|
| Signals | 9389 (rate 1.0% of evaluable ticker-sessions) | — |
| Attempted (after overlap skip) | 9135 | 200 draws × 9135 |
| Filled | 5122 (56.1%) | 56.7% |
| Scored trades | 5100 | 1031115 |
| Hit rate (net return > 0) | 39.6% | 40.0% (95% of draws 38.7% .. 41.5%) |
| Average net return | -0.62% | -0.46% (95% of draws -0.68% .. -0.18%) |
| Median net return | -0.79% | -0.80% |

Average return vs random: -0.16% (rule at percentile 9.0 of draws, one-sided p = 0.910).
Hit rate vs random: -0.41% (percentile 26.0, one-sided p = 0.741).

Status counts (rule): EXITED 5100, INCOMPLETE 22, SKIP_NO_ENTRY_SESSION 11, SKIP_NOT_TRADED 221, SKIP_ARA_LOCK 107, SKIP_LIQUIDITY 3674

Status counts (random, pooled): EXITED 1031106, EXIT_DATA_END 9, INCOMPLETE 4274, SKIP_NO_ENTRY_SESSION 2200, SKIP_NOT_TRADED 45766, SKIP_ARA_LOCK 19816, SKIP_LOT 139, SKIP_LIQUIDITY 723690

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Random hit rate | Random avg net |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | 584 | 312 | 35.3% | -1.58% | 38.1% | -1.05% |
| 2020 | 1344 | 626 | 41.2% | -0.38% | 43.3% | -0.11% |
| 2021 | 1547 | 918 | 42.6% | +0.19% | 40.3% | -0.09% |
| 2022 | 1687 | 1086 | 35.0% | -0.80% | 39.0% | -0.63% |
| 2023 | 1845 | 1072 | 40.0% | -0.94% | 39.9% | -0.65% |
| 2024 | 1849 | 966 | 41.7% | -0.64% | 39.5% | -0.46% |
| 2025 | 279 | 120 | 39.2% | -0.80% | 39.3% | -0.29% |

## Execution

- official close; signal at close of s, entry at close of s + entry_lag, entry lag 1
- 100-share lots, notional Rp 10,000,000 per trade, at most 10% of session volume
- Fees: buy 0.15%, sell 0.25%
- entry refused when the entry close is locked at ARA; exit rolls while locked at ARB or untraded; regular-board schedule by date, plus 10% special-board limits on one-price or sub-Rp50 bars
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: truncated after 2021-03-24: identical, truncated after 2022-11-16: identical, truncated after 2024-08-02: identical

## Warnings

- PLACEBO rule: harness self-check, not a trading rule; any lift here is a harness bias

# Run 20261007T231344Z_PLACEBO_COINFLIP_v1

Rule: **PLACEBO_COINFLIP v1** (PLACEBO), holding 5 sessions
Rule SHA-256: `b774201b08e6da68c54c7083a85d31830ca5a8342a6d0932f92a02d74fe27b68`
Code: `e82d62136a505d6732c8fce75a82c03db46fd66f`
Panel: `9d3a0718c95f9e885c4f8310cf68bf5e75021c366c454f73389d7fae75c02877`
Window: 2021-01-22 .. 2025-02-21 (989 sessions, 958 tickers, 3 stop trading inside the window)

> Signal on session d for ticker t when splitmix64(crc32(t) * 2^20 + days_since_epoch(d)) / 2^64 < 0.01, for every ticker that traded on session d. Hold 5 sessions. No price input.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 7325 (rate 1.0% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 7119 | 200 draws × 7119 | 200 draws × 7119 |
| Filled | 4143 (58.2%) | 58.9% | 58.9% |
| Scored trades | 4117 | 834153 | 833942 |
| Hit rate (net return > 0) | 39.6% | 39.8% (95% of draws 38.5% .. 41.2%) | 39.8% (95% of draws 38.4% .. 41.2%) |
| Average net return | -0.56% | -0.43% (95% of draws -0.67% .. -0.17%) | -0.43% (95% of draws -0.72% .. -0.16%) |
| Median net return | -0.74% | -0.80% | -0.78% |

Average return vs matched random: -0.13% (rule at percentile 16.5 of draws, one-sided p = 0.836).
Hit rate vs matched random: -0.19% (rule at percentile 40.0 of draws, one-sided p = 0.602).
Average return vs same-session random: -0.13% (rule at percentile 18.5 of draws, one-sided p = 0.816).
Hit rate vs same-session random: -0.17% (rule at percentile 42.0 of draws, one-sided p = 0.582).

Matched controls found at: price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age 1009, price_band+liquidity+market_cap+volatility+momentum+drawdown 142, price_band+liquidity+market_cap+volatility+momentum 1284, price_band+liquidity+market_cap+volatility 2673, price_band+liquidity+market_cap 1504, price_band+liquidity 415, price_band 92

Status counts (rule): EXITED 4117, INCOMPLETE 22, CORP_ACTION_UNRESOLVED 4, SKIP_NO_ENTRY_SESSION 11, SKIP_NOT_TRADED 119, SKIP_ARA_LOCK 96, SKIP_LIQUIDITY 2750

Status counts (matched random, pooled): EXITED 834153, INCOMPLETE 4077, CORP_ACTION_UNRESOLVED 821, SKIP_NO_ENTRY_SESSION 2200, SKIP_NOT_TRADED 21248, SKIP_ARA_LOCK 20590, SKIP_LOT 53, SKIP_LIQUIDITY 540658

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 1459 | 877 | 42.6% | +0.39% | 41.1% | +0.04% | +0.08% |
| 2022 | 1687 | 1085 | 35.0% | -0.79% | 38.5% | -0.58% | -0.65% |
| 2023 | 1845 | 1071 | 40.1% | -0.94% | 40.3% | -0.76% | -0.65% |
| 2024 | 1849 | 964 | 41.6% | -0.73% | 40.0% | -0.37% | -0.46% |
| 2025 | 279 | 120 | 39.2% | -0.80% | 36.8% | -0.22% | -0.10% |

## Data quality

Sessions by tier: TIER_1 989 (panel format panel-v2)

- TIER_2 2019-07-29 .. 2021-01-21: idx_mirror, survivorship survivor-biased (pre-snapshot delistings absent), corporate actions from exchange reference + share counts
- TIER_1 2021-01-22 .. 2025-02-21: idx_mirror, survivorship complete, corporate actions from exchange reference + share counts + Yahoo
- TIER_3 2025-02-22 .. 2026-10-06: yahoo, survivorship survivor-only, corporate actions from Yahoo split events only (single source)

Known limitations:

- TIER_2 sessions (before 2021-01-22) miss names that delisted before then: survivor-biased.
- TIER_3 sessions (after the mirror ends) are survivor-only Yahoo data; corporate actions there are single-source and trades held across them are excluded.
- Prices are daily closes; there is no intraday path, so a stop or limit inside the session is not modelled.
- Cash dividends are not added back: returns are price returns.
- Sector, board membership and free float are not available point-in-time; controls do not match on them.
- Trades held across a reference reset that is not a verified split, reverse split or stock dividend are excluded from scoring (rule and baselines alike), so names with rights issues are under-represented.
- Suspensions longer than the data are exited at the last traded close (EXIT_DATA_END), not marked to zero, unless data_end_exit='zero'.

## Corporate actions

Registry `ca_registry-20261007T230210Z.json` (ca-registry-v1), file SHA-256 `659da375e4586deab958e22dc242d7be6966ebc226bfefe8ce7ce85eb51f1e6c`.
Reference resets in the window: 160; share-scaled (verified split / reverse split / stock dividend) 72; verified rights issues 0; unresolved 88 (of which missing from the registry 0).

## Matched controls

Controls v2; full match (every feature) for 14.2% of attempts; pool minimum 5.

| Priority | Feature | Known for signalled name | Matched on | Availability |
|---:|---|---:|---:|---|
| 1 | price_band: close <= Rp200 / <= Rp5,000 / above | 100.0% | 100.0% | every tier |
| 2 | liquidity: quintile of 20-session median traded value | 99.3% | 98.7% | every tier |
| 3 | market_cap: quintile of close x IDX listed shares | 100.0% | 92.9% | TIER_1, TIER_2 (no share counts after the mirror ends) |
| 4 | volatility: tercile of 20-session std of daily log returns | 99.3% | 71.8% | every tier |
| 5 | momentum: tercile of 20-session cumulative log return | 99.3% | 34.2% | every tier |
| 6 | drawdown: tercile of close / 60-session high close - 1 | 97.8% | 16.2% | every tier |
| 7 | listing_age: sessions since first panel session: <60 / <250 / older or censored at the panel start | 100.0% | 14.2% | every tier |

Not matched on (no point-in-time data): sector: only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used; board: listing board known only as of the 2025-02 snapshot; not point-in-time, so not used; free_float: IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used

## Execution

- official close; signal at close of s, entry at close of s + entry_lag, entry lag 1
- 100-share lots, notional Rp 10,000,000 per trade, at most 10% of session volume
- Fees: buy 0.15%, sell 0.25%
- entry refused when the entry close is locked at ARA; exit rolls while locked at ARB or untraded; regular-board schedule by date, plus 10% special-board limits on one-price or sub-Rp50 bars
- Corporate actions: shares scaled only through registry-verified splits, reverse splits and stock dividends; trades held across a verified rights issue or any unverified reset are not scored (CORP_ACTION_RIGHTS_ISSUE / CORP_ACTION_UNRESOLVED)
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: prefix-first-v1: causal by construction. Each signal is column d of a call given only sessions 0..d and the names listed by d (989 calls); source audit passed; file, network, process, frame and heap access blocked during compute; a full-window call matched every prefix-built signal

## Warnings

- 4 trades were held across a corporate action the model does not share-scale and are not scored (ca_mode=registry); the baselines apply the same rule
- PLACEBO rule: harness self-check, not a trading rule; any lift here is a harness bias

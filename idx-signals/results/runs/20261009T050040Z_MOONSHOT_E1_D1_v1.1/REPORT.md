# Run 20261009T050040Z_MOONSHOT_E1_D1_v1.1

Rule: **MOONSHOT_E1_D1 v1.1** (DETECTOR), holding 5 sessions
Rule SHA-256: `648a06e1079f43303bffbc6e16ab814ebe06c148695c1fa782af6d1225523dbc`
Code: `d57e4b886900895bd1ab7b00d8a57854e1d8e2a2`
Panel: `9d3a0718c95f9e885c4f8310cf68bf5e75021c366c454f73389d7fae75c02877`
Window: 2023-01-02 .. 2023-12-29 (239 sessions, 905 tickers, 1 stop trading inside the window)

> Experiment E1 detector D1: the single rule from FAMILY selected on the discovery period defined in research/E1/PROTOCOL.md, by the rule pre-registered there. Signal at the close of session d when that rule holds; hold 5 sessions. Selected: F1_ARA.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 1109 (rate 0.6% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 1073 | 200 draws × 1073 | 200 draws × 1073 |
| Filled | 262 (24.4%) | 33.4% | 56.9% |
| Scored trades | 251 | 69307 | 117010 |
| Hit rate (net return > 0) | 31.1% | 39.7% (95% of draws 34.6% .. 44.3%) | 38.9% (95% of draws 35.1% .. 42.9%) |
| Average net return | -3.64% | -0.44% (95% of draws -1.65% .. +0.79%) | -0.64% (95% of draws -1.33% .. +0.00%) |
| Median net return | -5.93% | -1.00% | -0.75% |

Average return vs matched random: -3.20% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs matched random: -8.67% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Average return vs same-session random: -3.00% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs same-session random: -7.83% (rule at percentile 0.0 of draws, one-sided p = 1.000).

Matched controls found at: price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age 120, price_band+liquidity+market_cap+volatility+momentum+drawdown 90, price_band+liquidity+market_cap+volatility+momentum 229, price_band+liquidity+market_cap+volatility 337, price_band+liquidity+market_cap 181, price_band+liquidity 53, price_band 63

Status counts (rule): EXITED 251, INCOMPLETE 11, SKIP_NO_ENTRY_SESSION 15, SKIP_NOT_TRADED 21, SKIP_ARA_LOCK 350, SKIP_LIQUIDITY 423, SKIP_CAPACITY_UNKNOWN 2

Status counts (matched random, pooled): EXITED 69307, INCOMPLETE 2308, CORP_ACTION_UNRESOLVED 3, SKIP_NO_ENTRY_SESSION 3000, SKIP_NOT_TRADED 3910, SKIP_ARA_LOCK 6657, SKIP_LIQUIDITY 129363, SKIP_CAPACITY_UNKNOWN 52

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 1073 | 251 | 31.1% | -3.64% | 39.7% | -0.44% | -0.64% |

## Data quality

Sessions by tier: TIER_1 239 (panel format panel-v2)

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
Reference resets in the window: 29; share-scaled (verified split / reverse split / stock dividend) 19; verified rights issues 0; unresolved 10 (of which missing from the registry 0).

## Matched controls

Controls v2; full match (every feature) for 11.2% of attempts; pool minimum 5.

| Priority | Feature | Known for signalled name | Matched on | Availability |
|---:|---|---:|---:|---|
| 1 | price_band: close <= Rp200 / <= Rp5,000 / above | 100.0% | 100.0% | every tier |
| 2 | liquidity: quintile of 20-session median traded value | 93.1% | 94.1% | every tier |
| 3 | market_cap: quintile of close x IDX listed shares | 100.0% | 89.2% | TIER_1, TIER_2 (no share counts after the mirror ends) |
| 4 | volatility: tercile of 20-session std of daily log returns | 93.1% | 72.3% | every tier |
| 5 | momentum: tercile of 20-session cumulative log return | 93.1% | 40.9% | every tier |
| 6 | drawdown: tercile of close / 60-session high close - 1 | 89.6% | 19.6% | every tier |
| 7 | listing_age: sessions since first panel session: <60 / <250 / older or censored at the panel start | 100.0% | 11.2% | every tier |

Not matched on (no point-in-time data): sector: only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used; board: listing board known only as of the 2025-02 snapshot; not point-in-time, so not used; free_float: IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used

## Execution

- official close; signal at close of s, entry at close of s + entry_lag, entry lag 1
- 100-share lots, notional Rp 10,000,000 per trade, at most 10% of session volume
- Fees: buy 0.15%, sell 0.25%
- entry refused when the entry close is locked at ARA; exit rolls while locked at ARB or untraded; regular-board schedule by date, plus 10% special-board limits on one-price or sub-Rp50 bars
- Corporate actions: shares scaled only through registry-verified splits, reverse splits and stock dividends; trades held across a verified rights issue or any unverified reset are not scored (CORP_ACTION_RIGHTS_ISSUE / CORP_ACTION_UNRESOLVED)
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: prefix-first-v1: causal by construction. Each signal is column d of a call given only sessions 0..d and the names listed by d (239 calls); source audit passed; file, network, process, frame and heap access blocked during compute; a full-window call matched every prefix-built signal

## Warnings

- none

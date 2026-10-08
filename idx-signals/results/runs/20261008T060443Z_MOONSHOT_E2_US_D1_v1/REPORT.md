# Run 20261008T060443Z_MOONSHOT_E2_US_D1_v1

Rule: **MOONSHOT_E2_US_D1 v1** (DETECTOR), holding 5 sessions
Rule SHA-256: `c21126d8ba9db77b06c186401220850b36c4e1b539d77d4f9da4dcc571e6753f`
Code: `826ec76da52b3c1d65abaac5f7502afb16772d63`
Panel: `e5b5267438667a136f4a4cb42c52d6bc98bc80cde6a88c02a27751a4902c9b92`
Window: 2023-01-03 .. 2023-12-29 (250 sessions, 4878 tickers, 0 stop trading inside the window)

> Experiment E2 detector: the single rule from FAMILY selected on the market's discovery period defined in research/E2/protocol.json, by the rule pre-registered there. Signal at the close of session d when that rule holds; hold 5 sessions. Market: US. Selected: G2_RET30.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 1676 (rate 0.1% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 1496 | 200 draws × 1496 | 200 draws × 1496 |
| Filled | 1148 (76.7%) | 70.3% | 87.8% |
| Scored trades | 1099 | 201254 | 252505 |
| Hit rate (net return > 0) | 36.2% | 43.0% (95% of draws 39.9% .. 45.7%) | 48.1% (95% of draws 45.6% .. 50.3%) |
| Average net return | -3.65% | -0.60% (95% of draws -1.74% .. +0.70%) | +0.16% (95% of draws -0.40% .. +0.95%) |
| Median net return | -7.74% | -1.69% | -0.20% |

Average return vs matched random: -3.05% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs matched random: -6.76% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Average return vs same-session random: -3.81% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs same-session random: -11.84% (rule at percentile 0.0 of draws, one-sided p = 1.000).

Matched controls found at: price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age 1224, price_band+liquidity+market_cap+volatility+momentum+drawdown 116, price_band+liquidity+market_cap+volatility+momentum 116, price_band+liquidity+market_cap+volatility 11, price_band+liquidity+market_cap 2, price_band 27

Status counts (rule): EXITED 1099, INCOMPLETE 49, SKIP_NO_ENTRY_SESSION 9, SKIP_NOT_TRADED 53, SKIP_LOT 154, SKIP_LIQUIDITY 132

Status counts (matched random, pooled): EXITED 201254, INCOMPLETE 9006, SKIP_NO_ENTRY_SESSION 1800, SKIP_NOT_TRADED 3126, SKIP_LOT 12061, SKIP_LIQUIDITY 71953

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 1496 | 1099 | 36.2% | -3.65% | 43.0% | -0.60% | +0.16% |

## Data quality

Sessions by tier: US_SURVIVOR 250 (panel format panel-global-v1)

- US_SURVIVOR 2020-01-02 .. 2026-10-07: yahoo, survivorship survivor-only: the universe is the Nasdaq Trader listing snapshot of the download day; names delisted earlier are absent, corporate actions from split-adjusted by the source

Known limitations:

- survivor-only: the universe is the Nasdaq Trader listing snapshot of the download day; names delisted earlier are absent
- prices are split-adjusted by the source, not dividend-adjusted
- daily bars only: no intraday path, no halts (US LULD) or order-book depth
- costs are assumed per price tier (profiles.py), not measured spreads

## Matched controls

Controls v2; full match (every feature) for 81.8% of attempts; pool minimum 5.

| Priority | Feature | Known for signalled name | Matched on | Availability |
|---:|---|---:|---:|---|
| 1 | price_band: close <= Rp200 / <= Rp5,000 / above | 100.0% | 100.0% | every tier |
| 2 | liquidity: quintile of 20-session median traded value | 97.7% | 98.2% | every tier |
| 3 | market_cap: quintile of close x IDX listed shares | 0.0% | 98.2% | TIER_1, TIER_2 (no share counts after the mirror ends) |
| 4 | volatility: tercile of 20-session std of daily log returns | 97.7% | 98.1% | every tier |
| 5 | momentum: tercile of 20-session cumulative log return | 97.7% | 97.3% | every tier |
| 6 | drawdown: tercile of close / 60-session high close - 1 | 94.4% | 89.6% | every tier |
| 7 | listing_age: sessions since first panel session: <60 / <250 / older or censored at the panel start | 100.0% | 81.8% | every tier |

Not matched on (no point-in-time data): sector: only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used; board: listing board known only as of the 2025-02 snapshot; not point-in-time, so not used; free_float: IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used

## Execution

- signal at close of s, entry at the open of s + entry_lag, exit at a close, entry lag 1
- 100-share lots, notional Rp 5,000 per trade, at most 10% of session volume
- Fees: buy 0.00%, sell 0.00%
- none (no daily price limits)
- Corporate actions: source prices are split-adjusted; no reference resets are expected or scaled
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: prefix-first-v1: causal by construction. Each signal is column d of a call given only sessions 0..d and the names listed by d (250 calls); source audit passed; file, network, process, frame and heap access blocked during compute; a full-window call matched every prefix-built signal

## Warnings

- US: survivor-only: the universe is the Nasdaq Trader listing snapshot of the download day; names delisted earlier are absent
- costs assumed: per side 1.5% under $1, 0.5% $1-5, 0.15% $5-20, 0.05% above, plus the SEC fee on sales

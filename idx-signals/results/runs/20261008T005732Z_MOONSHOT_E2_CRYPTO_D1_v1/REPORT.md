# Run 20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1

Rule: **MOONSHOT_E2_CRYPTO_D1 v1** (DETECTOR), holding 5 sessions
Rule SHA-256: `d8218f2e9c9b95169ccee01330b5e1be1b11bec85ad33b181eaa644ed1ddd89d`
Code: `21345b1202456b2a0a6b22a7028d338942d0f1fc`
Panel: `3dc12749c7cce635a68ef4f152ec21c3b3d24eb6b02665c799aa24e513963d7d`
Window: 2023-01-01 .. 2023-12-31 (365 sessions, 371 tickers, 14 stop trading inside the window)

> Experiment E2 detector: the single rule from FAMILY selected on the market's discovery period defined in research/E2/protocol.json, by the rule pre-registered there. Signal at the close of session d when that rule holds; hold 5 sessions. Market: CRYPTO. Selected: G2_RET30.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 312 (rate 0.3% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 270 | 200 draws × 270 | 200 draws × 270 |
| Filled | 269 (99.6%) | 99.2% | 98.7% |
| Scored trades | 264 | 52559 | 52327 |
| Hit rate (net return > 0) | 31.4% | 48.1% (95% of draws 43.4% .. 53.1%) | 51.1% (95% of draws 46.6% .. 55.9%) |
| Average net return | -1.90% | +1.42% (95% of draws -0.10% .. +3.15%) | +1.66% (95% of draws +0.33% .. +3.26%) |
| Median net return | -10.46% | -0.44% | +0.20% |

Average return vs matched random: -3.32% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs matched random: -16.62% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Average return vs same-session random: -3.57% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs same-session random: -19.64% (rule at percentile 0.0 of draws, one-sided p = 1.000).

Matched controls found at: price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age 30, price_band+liquidity+market_cap+volatility+momentum+drawdown 8, price_band+liquidity+market_cap+volatility+momentum 96, price_band+liquidity+market_cap+volatility 46, price_band+liquidity+market_cap 74, price_band 16

Status counts (rule): EXITED 263, EXIT_DATA_END 1, INCOMPLETE 5, SKIP_NO_ENTRY_SESSION 1

Status counts (matched random, pooled): EXITED 52509, EXIT_DATA_END 50, INCOMPLETE 1000, SKIP_NO_ENTRY_SESSION 200, SKIP_NOT_TRADED 65, SKIP_LOT 110, SKIP_LIQUIDITY 66

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 270 | 264 | 31.4% | -1.90% | 48.1% | +1.42% | +1.66% |

## Data quality

Sessions by tier: CRYPTO_BINANCE 365 (panel format panel-global-v1)

- CRYPTO_BINANCE 2020-01-01 .. 2026-10-07: binance, survivorship Binance USDT pairs including delisted ones still described by exchangeInfo (190 delisted/halted bases); pairs Binance dropped from exchangeInfo entirely are absent, corporate actions from split-adjusted by the source

Known limitations:

- Binance USDT pairs including delisted ones still described by exchangeInfo (190 delisted/halted bases); pairs Binance dropped from exchangeInfo entirely are absent
- prices are split-adjusted by the source, not dividend-adjusted
- daily bars only: no intraday path, no halts (US LULD) or order-book depth
- costs are assumed per price tier (profiles.py), not measured spreads
- sessions are UTC days; the asset trades 24/7

## Matched controls

Controls v2; full match (every feature) for 11.1% of attempts; pool minimum 5.

| Priority | Feature | Known for signalled name | Matched on | Availability |
|---:|---|---:|---:|---|
| 1 | price_band: close <= Rp200 / <= Rp5,000 / above | 100.0% | 100.0% | every tier |
| 2 | liquidity: quintile of 20-session median traded value | 95.9% | 94.1% | every tier |
| 3 | market_cap: quintile of close x IDX listed shares | 0.0% | 94.1% | TIER_1, TIER_2 (no share counts after the mirror ends) |
| 4 | volatility: tercile of 20-session std of daily log returns | 95.9% | 66.7% | every tier |
| 5 | momentum: tercile of 20-session cumulative log return | 95.9% | 49.6% | every tier |
| 6 | drawdown: tercile of close / 60-session high close - 1 | 92.2% | 14.1% | every tier |
| 7 | listing_age: sessions since first panel session: <60 / <250 / older or censored at the panel start | 100.0% | 11.1% | every tier |

Not matched on (no point-in-time data): sector: only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used; board: listing board known only as of the 2025-02 snapshot; not point-in-time, so not used; free_float: IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used

## Execution

- signal at close of s, entry at the open of s + entry_lag, exit at a close, entry lag 1
- 100-share lots, notional Rp 5,000 per trade, at most 10% of session volume
- Fees: buy 0.10%, sell 0.10%
- none (no daily price limits)
- Corporate actions: source prices are split-adjusted; no reference resets are expected or scaled
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: prefix-first-v1: causal by construction. Each signal is column d of a call given only sessions 0..d and the names listed by d (365 calls); source audit passed; file, network, process, frame and heap access blocked during compute; a full-window call matched every prefix-built signal

## Warnings

- CRYPTO: Binance USDT pairs including delisted ones still described by exchangeInfo (190 delisted/halted bases); pairs Binance dropped from exchangeInfo entirely are absent
- costs assumed: 0.1% taker fee + 0.1% slippage per side; sessions are UTC days
- 1 trades exited at a last traded close because the name stopped trading (data_end_exit=last_close)

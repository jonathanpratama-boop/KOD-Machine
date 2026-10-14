# Run 20261013T212610Z_MOONSHOT_E4_D1_v1

Rule: **MOONSHOT_E4_D1 v1** (DETECTOR), holding 2 sessions
Rule SHA-256: `f5585be5d967dfabd98d24f02eef1857362457e23f22ff0e4b25b7208fde9d67`
Code: `8bad7926e317ff22d722da495365f25a9b4e645d`
Panel: `1fec989bc929268f290d73ae60e4216f37de866ec30e00fba645b665dc2b6e14`
Window: 2023-01-01 .. 2023-12-31 (365 sessions, 371 tickers, 14 stop trading inside the window)

> Experiment E4 (the fade): one of the E2 family's already-ran detectors G2_RET30, G1_RET20_CLOSEHIGH, G10_RET15_CLOSEHIGH, G7_MOMENTUM5_30 (research/E2/protocol.json) traded on the SHORT side with one execution plan from the family in research/E4/protocol.json, the pair selected on the discovery period by the rule pre-registered there. Signal at the close of session d when the detector holds; the short entry and its cover as the plan says. Selected under KOD-GLOBAL-E4-v2: G2_RET30_BEAR; side short; plan: entry pullback within 3 session(s), exit first_up, hold 2.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 57 (rate 0.0% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 53 | 200 draws × 53 | 200 draws × 53 |
| Filled | 34 (64.2%) | 76.6% | 77.1% |
| Scored trades | 34 | 8122 | 8170 |
| Hit rate (net return > 0) | 67.6% | 50.7% (95% of draws 38.1% .. 64.5%) | 43.8% (95% of draws 32.4% .. 57.2%) |
| Average net return | -1.50% | -0.22% (95% of draws -3.64% .. +2.88%) | -0.17% (95% of draws -2.12% .. +1.54%) |
| Median net return | +9.30% | +0.04% | -0.50% |

Average return vs matched random: -1.28% (rule at percentile 22.0 of draws, one-sided p = 0.781).
Hit rate vs matched random: +16.94% (rule at percentile 98.0 of draws, one-sided p = 0.025).
Average return vs same-session random: -1.33% (rule at percentile 10.5 of draws, one-sided p = 0.896).
Hit rate vs same-session random: +23.84% (rule at percentile 100.0 of draws, one-sided p = 0.005).

Matched controls found at: price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age 3, price_band+liquidity+market_cap+volatility+momentum+drawdown 2, price_band+liquidity+market_cap+volatility+momentum 21, price_band+liquidity+market_cap+volatility 9, price_band+liquidity+market_cap 13, price_band 5

Status counts (rule): EXITED 34, SKIP_NO_TRIGGER 19

Status counts (matched random, pooled): EXITED 8122, SKIP_LIQUIDITY 25, SKIP_NO_TRIGGER 2453

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 53 | 34 | 67.6% | -1.50% | 50.7% | -0.19% | -0.16% |

## Data quality

Sessions by tier: CRYPTO_BINANCE 365 (panel format panel-global-v2)

- CRYPTO_BINANCE 2020-01-01 .. 2026-10-12: binance, survivorship Binance USDT pairs including delisted ones still described by exchangeInfo (190 delisted/halted bases); pairs Binance dropped from exchangeInfo entirely are absent, corporate actions from split-adjusted by the source

Known limitations:

- Binance USDT pairs including delisted ones still described by exchangeInfo (190 delisted/halted bases); pairs Binance dropped from exchangeInfo entirely are absent
- prices are split-adjusted by the source, not dividend-adjusted
- daily bars only: no intraday path, no halts (US LULD) or order-book depth
- costs are assumed per price tier (profiles.py), not measured spreads
- sessions are UTC days; the asset trades 24/7

## Matched controls

Controls v2; full match (every feature) for 5.7% of attempts; pool minimum 5.

| Priority | Feature | Known for signalled name | Matched on | Availability |
|---:|---|---:|---:|---|
| 1 | price_band: close in <0.01 / 0.01-1 / 1-100 / >100 | 100.0% | 100.0% | every tier |
| 2 | liquidity: quintile of 20-session median traded value | 90.6% | 90.6% | every tier |
| 3 | market_cap: quintile of close x IDX listed shares | 0.0% | 90.6% | TIER_1, TIER_2 (no share counts after the mirror ends) |
| 4 | volatility: tercile of 20-session std of daily log returns | 90.6% | 66.0% | every tier |
| 5 | momentum: tercile of 20-session cumulative log return | 90.6% | 49.1% | every tier |
| 6 | drawdown: tercile of close / 60-session high close - 1 | 90.6% | 9.4% | every tier |
| 7 | listing_age: sessions since first panel session: <60 / <250 / older or censored at the panel start | 100.0% | 5.7% | every tier |

Not matched on (no point-in-time data): sector: only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used; board: listing board known only as of the 2025-02 snapshot; not point-in-time, so not used; free_float: IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used

## Execution

- signal at close of s, entry at the open of s + entry_lag, exit at a close, entry lag 1
- Plan: sell short at the first open in s+1..s+3 that is above the signal close (into a bounce); buy back at the first close above its own reference price (an up day), else at the close of the 2th session after entry; carry charged per session held
- 100-share lots, notional Rp 5,000 per trade, at most 10% of session volume
- Fees: buy 0.10%, sell 0.10%
- none (no daily price limits)
- Corporate actions: source prices are split-adjusted; no reference resets are expected or scaled
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: prefix-first-v1: causal by construction. Each signal is column d of a call given only sessions 0..d and the names listed by d (365 calls); source audit passed; file, network, process, frame and heap access blocked during compute; a full-window call matched every prefix-built signal

## Warnings

- CRYPTO: Binance USDT pairs including delisted ones still described by exchangeInfo (190 delisted/halted bases); pairs Binance dropped from exchangeInfo entirely are absent
- costs assumed: 0.1% taker fee + 0.1% slippage per side; sessions are UTC days

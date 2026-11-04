# Independent audit of the FRESH_EYES_v1 engine and runs (2026-11-01)

Performed by a separate agent that did not write the code, with read-only access to this folder and the raw data. Scratch
scripts were kept outside the repository. No repository file was modified by the audit.

## Summary table

| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | Engine shift and open-to-open attribution (`lib.run_positions`) | PASS | Synthetic 6-bar test: a target set at the close of day 0 earns open(day 1) to open(day 2) only; entry cost on day 1, exit cost on day 2. |
| 1b | Planted look-ahead series | PASS (engine not at fault) | A target equal to sign(open t+1 to open t+2) scores Sharpe 16.9 (the engine credits exactly that return, so a cheating input cheats); honest signals known at close t score about zero; without the shift the planted series would score -1.31, confirming the shift is present. |
| 1c | T1 signals use only data through bar t | PASS | Positions through bar 2000 are identical when all later data is deleted, for every T1 and T5 variant. |
| 1d | TSMOM re-evaluation | PASS, robustness caveat | Causal; the 5-day grid is anchored to the first bar (see issue 3). |
| 1e | T3 Sunday/Monday indexing | PASS | All 351 Mondays read signals at the preceding Sunday close; hold Monday open to next Monday open. |
| 1f | T4 z-score | PASS | Trailing std uses 180 non-overlapping same-phase 4h windows ending at i-4 (current window excluded), verified to 1e-12. |
| 2a | Per-side costs | PASS (minor) | Initial entry charged; a position still open on the last bar is never charged its exit (one side, 0.15%, once in nine years). |
| 2b | Funding sign | PASS | Long pays positive funding; short receives; T4 window handles millisecond jitter. |
| 2c | T3 turnover | PASS | Sum of absolute weight changes per side; mean weekly turnover 2.61 of a maximum 4.0; mean weekly cost 0.26%. |
| 3 | T3 delisted-symbol handling | ISSUE | Binance Vision keeps publishing zero-volume frozen-price daily bars for years after delisting (median 297 days); 157 symbols stopped trading before 2026-09 but only 28 end in the panel. See issue 1. |
| 4a-b | Sharpe, CAGR, MaxDD | PASS | 365 daily / 52 weekly; formulas verified; buy-and-hold drawdowns match 2018. |
| 4c | T6 drift and bootstrap | PASS | Daily mean S*vol/365 reproduces annual Sharpe 0.995 for S = 1; block bootstrap correct. Deviations from protocol: 365 days instead of 252; Sharpe 3.0 and 10x leverage added. |
| 5a-d | Data integrity | PASS with notes | Mixed ms/us timestamps handled; BTC/ETH spot 2017-08-17 to 2026-09-30, no gaps or duplicates; UM 1h starts 2020-01 (not 2019-09); SOL/XRP/LTC miss 120 archive hours in 2022, no trade straddles them; klines end 2026-09-30, so validation effectively ends 2026-09-29. |
| 6a | No-signal placebo | PASS | Random long/flat on BTC earns half the buy-and-hold drift (Sharpe 0.59, sd 0.23); random long/short earns zero gross and negative net. |
| 6b | T4a sample construction | ISSUE | T4a is reported as the |z| >= 3 subset of the |z| >= 2 run, whose 5-hour blocking suppresses later signals. See issue 2. |

## Issues ranked by impact

1. **T3 frozen post-delisting bars.** A symbol can stay eligible for about 15 days after its last trade, and 100 of about 13,000 position-weeks held a symbol with a zero-volume day. Re-running T3 with zero-volume bars masked to NaN: dev Sharpe T3a 0.575 (reported 0.600), T3b 1.103 (1.105); val T3a 0.318 (0.322), T3b 0.462 (0.483). Verdicts unchanged (FAIL, FAIL). The protocol's description of delisting handling is inaccurate and the panel should define a symbol's last bar as its last traded bar.
2. **T4a derived from the T4b run.** A standalone |z| >= 3 run: dev long-after-drop 1,123 trades, mean net +0.563%, t 3.69 (reported 691, +0.779%, t 3.66); val long-after-drop 1,410 trades, -0.015%, t -0.21 (reported 824, -0.020%, t -0.19). Verdicts unchanged (all FAIL). Also, 37% of trade hours have more than one symbol trading at once, so the independence assumption behind the t-statistics is violated and reported |t| values are overstated.
3. **ETH T1b (TSMOM) PASS depends on the re-evaluation phase.** Across the five possible phases, ETH validation Sharpe is 1.121, 0.530, 0.608, 1.034, 1.069 against buy-and-hold 0.653; three of five phases pass, and the reported phase is the best. BTC validation Sharpe ranges 0.883 to 1.347. Not look-ahead, but the ETH T1b PASS is fragile. The ETH T1c (SMA 10/40) PASS has no such phase dependence.
4. **Protocol deviations to disclose.** T6: 365 days, extra Sharpe and leverage cells. Validation ends 2026-09-29 (October 2026 monthly archives not yet published). UM 1h begins 2020-01. T3 development effectively begins 2020-05-25 (first week with 20 eligible candidates), 134 weeks.
5. **Minor accounting.** Last-bar exit not charged; `trades_per_year` counts sides (8.2 sides is about 4 round trips); T5iii's fixed stop references the signal-bar close rather than the next open; one T3 week has a NaN universe benchmark; buy-and-hold pays no entry cost.
6. **Context.** For a long-flat strategy on an asset with strong positive drift the relevant null is not zero: random long/flat positions earn Sharpe about 0.59 (sd 0.23) on BTC. The T1 development Sharpes of 1.1 to 1.24 are about 2 to 3 standard deviations above that null.

## Verdict

Usable with corrections. Engine timing, cost, funding and statistical mechanics are correct; the planted look-ahead test confirms the engine credits exactly the open(t+1) to open(t+2) return of a decision taken at the close of t. The two substantive issues were re-computed and change no PASS/FAIL verdict. Corrections to carry into the result: report the corrected T3 and standalone T4a figures beside the originals; attach the TSMOM phase table to the ETH T1b PASS; amend the stated data ranges.

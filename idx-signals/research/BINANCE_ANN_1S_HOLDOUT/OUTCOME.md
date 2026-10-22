# BINANCE_ANN_1S_HOLDOUT: outcome (2026-10-22): the run was not made

## What was done
With the owner's authorization (`AUTHORIZATION.md`) the event rule of tests 21/22 was applied, unchanged, to the 292 "Binance Futures Will Launch ... Perpetual" articles released
2024-01-01 .. 2026-09-30. First pass (`feasibility/`): 9 eligible events. That pass mis-parsed the tokens (Binance now names the contract symbol, e.g. NIGHTUSDT); the parser was corrected
under `ADDENDUM_1.md`, committed before it was run. Corrected pass (`feasibility_v2/`): **29 eligible events**. GO rule 1 needs 40, and the addendum fixed in advance that a shortfall means no run.

## The funnel, then and now (token rows)
| | 2020-2023 (test 21) | 2024-2026 (this window) |
|---|---|---|
| launch articles | 260 | 292 |
| token rows | 293 | 338 |
| with a USDT spot pair in the panel | 275 | 140 |
| perpetual's first day 0-7 days after the article | 215 | 112 |
| and spot history of at least 30 days | 141 | 50 |
| and median daily quote volume of at least USD 1M (eligible) | 115 | **29** |
| eligible by year | 2020: 35, 2021: 26, 2022: 14, 2023: 40 | **2024: 25, 2025: 4, 2026: 0** |

The event the 2 s result lived on (a futures launch for a token that already has a liquid spot market) was about 29 a year in 2020-2023. It was 25 in 2024, 4 in 2025 and none in 2026 through
September: Binance now launches perpetuals mostly for brand-new tokens with no spot history, or pre-market.

## What was and was not opened
Opened: titles and release times already stored, the daily quote volumes of the tokens' spot pairs, and the futures archive's file names. **No trade and no return of the 2024+ window was read**;
`ticks/` and `results/` do not exist. The crypto 2024+ holdout is therefore unspent at the trade level.

## What follows
- Test 22's PASS (2020-2023) is neither confirmed nor refuted: there are too few events left to test it, and at the pace of 2025-2026 there will be almost none to trade. For practical purposes the
  opportunity it described has largely disappeared.
- Running on the 29 events anyway would be relaxing a threshold after seeing the count; it would need an owner decision and its own addendum, and would still leave a result with about 60% power at best.
- A different event definition (for example launches for tokens listed on spot within the last 30 days, or spot-listing announcements) is a new hypothesis with its own discovery and protocol.

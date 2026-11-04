# FRESH_EYES_v1: results (run once on the frozen protocol, 2026-11-01; audited, see AUDIT.md)

Historical research only; never a forecast; no order was placed. All figures are net of the protocol's Binance costs
unless marked. Data end for kline-based tests is 2026-09-29 (the October 2026 monthly archives were not yet published).
Protocol sha256 `177e7ccd…a170173`, pinned in commit `5b3d7c2` before any return was computed.

## T1. Trend following, BTC and ETH spot, long-flat (Sharpe / MaxDD; buy-and-hold in brackets)

| Coin | Variant | Dev 2017-08..2022 | Val 2023..2026-09 | Verdict |
|---|---|---|---|---|
| BTC | T1a Donchian 20/10 | 1.24 / -54% (0.72 / -83%) | 0.88 / -38% (1.16 / -53%) | WEAK |
| BTC | T1b TSMOM 28, re-eval 5d | 1.16 / -68% | 0.99 / -40% | WEAK |
| BTC | T1c SMA 10/40 | 1.24 / -62% | 1.12 / -37% | WEAK (Sharpe 1.12 vs 1.16) |
| BTC | T1d close > SMA200 | 0.55 / -64% | 1.07 / -32% | FAIL |
| ETH | T1a Donchian 20/10 | 1.14 / -68% (0.76 / -94%) | -0.03 / -62% (0.65 / -68%) | WEAK |
| ETH | T1b TSMOM 28, re-eval 5d | 1.02 / -71% | 1.12 / -42% | PASS, fragile (3 of 5 phases pass; see AUDIT issue 3) |
| ETH | T1c SMA 10/40 | 1.24 / -66% | 1.15 / -37% | PASS |
| ETH | T1d close > SMA200 | 0.75 / -74% | 0.78 / -38% | WEAK |

ETH T1c net return by year: 2017 +107%, 2018 -26%, 2019 +26%, 2020 +508%, 2021 +283%, 2022 -32%, 2023 +41%, 2024 +36%, 2025 +80%,
2026 (to Sep) +33%; in the market 49-52% of days; about 5 round trips a year. At eToro costs (1% a side) the SMA 10/40 validation Sharpe
falls from 1.15 to 0.93 (ETH) and from 1.12 to 0.85 (BTC); the strategy survives eToro costs because it trades about five round
trips a year, but it then no longer beats buy-and-hold on Sharpe for either coin. Read: trend following on majors keeps roughly the market's return with about
half the drawdown; it did not beat BTC buy-and-hold on Sharpe in 2023-2026 because BTC itself had Sharpe 1.16 in that window.

Placebo context (AUDIT 6a): random long/flat positions on BTC earn Sharpe about 0.59 (sd 0.23) because of the asset's drift;
the development Sharpes of 1.1-1.24 are 2-3 standard deviations above that null. This is a single frozen test, not a
confirmation.

## T2. Funding carry, BTC and ETH perpetuals (annualised funding received by a short)

| Year | BTC | ETH | Share of 8h periods negative (BTC) |
|---|---|---|---|
| 2020 | 17.2% | 27.4% | 14% |
| 2021 | 30.6% | 37.5% | 7% |
| 2022 | 4.2% | 0.8% | 22% |
| 2023 | 7.9% | 8.3% | 10% |
| 2024 | 11.9% | 13.0% | 8% |
| 2025 | 5.1% | 4.9% | 13% |
| 2026 (to Oct) | 3.1% | 2.1% | 25% |

Dev (2020-2022): 17.3% / 21.9% gross, PASS the 8% bar. Val (2023-2026): 7.2% / 7.3% gross, 6.7% / 6.8% net of one round trip
per leg, FAIL the 8% bar. Carry is real but compressed to roughly stablecoin-lending levels, with basis and liquidation risk
on top. Contrarian signal (report only): the trailing 30-day mean BTC funding turned negative five times (2020-03-28,
2021-07-08, 2022-11-14, 2024-09-08, 2026-02-27); the forward 90-day BTC return was +47%, +68%, +31%, +82%, +12%, against an
unconditional mean of +16% and median of +6% (57% positive). Five events; suggestive, not tested.

## T3. Cross-sectional 14-day momentum, Binance USDT perpetuals, weekly (775-symbol panel incl. delisted)

| | Dev 2020-05..2022 | Val 2023..2026-09 | Share of years positive | Verdict |
|---|---|---|---|---|
| T3a long top decile / short bottom decile | Sharpe 0.60, MaxDD -79% | Sharpe 0.32, CAGR +1%, MaxDD -64% | 29% | FAIL |
| T3b long top decile only | Sharpe 1.11, MaxDD -94% | Sharpe 0.48, CAGR +8%, MaxDD -82% | 43% | FAIL |
| Equal-weight eligible universe (benchmark) | Sharpe 0.90 | Sharpe 0.24, CAGR -10% | | |

Audit correction (zero-volume post-delisting bars masked): dev 0.575 / 1.103, val 0.318 / 0.462; verdicts unchanged. By
year, long-short: 2020 +513%, 2021 -8%, 2022 -75%, 2023 -30%, 2024 -32%, 2025 +9%, 2026 +103%. The altcoin universe itself
lost 69% in 2025. Altcoin momentum worked in one year (2020) and has not been a reliable edge since.

## T4. Hourly mean reversion after extreme 4-hour moves, ten major perpetuals

| Side, threshold | Dev 2020..2022 | Val 2023..2026-09 | Verdict |
|---|---|---|---|
| Long after a <= -3 sigma drop | 691 trades, +0.78% net per trade, t 3.66, win 58% | 824 trades, -0.02%, t -0.19, win 55% | FAIL |
| Short after a >= +3 sigma spike | 643, -0.39%, t -1.4 | 883, -0.60%, t -5.7 | FAIL |
| Long after <= -2 sigma | 2,999, +0.24%, t 3.3 | 3,982, -0.08%, t -2.2 | FAIL |
| Short after >= +2 sigma | 3,025, -0.29%, t -3.5 | 4,092, -0.36%, t -9.4 | FAIL |

Audit correction (standalone |z| >= 3 run): dev long +0.56%, t 3.69 (1,123 trades); val long -0.015%, t -0.21 (1,410).
Simultaneous trades across symbols overstate |t|. The 2020-2022 liquidity-provision edge after forced selling (the
mechanism in the literature) is gone in 2023-2026 at taker costs. The short side never worked.

## T5. Exit logic on the Donchian entry (Sharpe dev / val)

| Exit | BTC | ETH |
|---|---|---|
| (i) 10-day channel exit | 1.24 / 0.88 | 1.14 / -0.03 |
| (ii) 2 x ATR(20) trailing stop | 1.13 / 0.86 | 1.29 / 0.29 |
| (iii) fixed 5% stop plus channel exit | 1.41 / 0.96 | 1.00 / 0.49 |
| (iv) 10-day time exit | 1.01 / 0.80 | 1.04 / -0.02 |

The trailing stop was not the best exit in three of four coin-periods. No exit rescues the ETH Donchian entry in 2023-2026;
the entry, not the exit, decided the result. A wide signal-based exit or a fixed initial stop performed as well or better.

## T6. What USD 1,000 to USD 10,000 within one year requires (20,000 paths, 365 days)

Parametric, daily rebalanced, unlevered volatility 20%:

| Strategy quality | Leverage | P(reach 10x within a year) | P(50% drawdown within a year) | P(10x before any 50% drawdown) | Median end |
|---|---|---|---|---|---|
| Sharpe 1.0 | 1x | 0.0% | 0.0% | 0.0% | 1.20x |
| Sharpe 1.0 | 5x | 5.7% | 76% | 4.9% | 1.64x |
| Sharpe 1.0 | 10x | 24% | 99.9% | 5.6% | 0.99x |
| Sharpe 1.5 | 5x | 14% | 63% | 12% | 2.73x |
| Sharpe 2.0 | 5x | 27% | 50% | 24% | 4.46x |
| Sharpe 3.0 | 3x | 15% | 1.6% | 15% | 5.08x |
| Sharpe 3.0 | 5x | 64% | 26% | 59% | 12.2x |

Bootstrapped from the realised ETH T1c (SMA 10/40) daily net returns (full-sample Sharpe 1.18, volatility 62%):
1x: P(10x) 0.8%, P(50% drawdown) 19%, median 1.67x. 2x: P(10x) 15%, P(50% drawdown) 79%, median 1.95x. 3x: P(10x) 27%,
P(50% drawdown) 97%, median 1.50x, 29% of paths end below half the starting capital. 5x: P(10x) 31%, P(50% drawdown) 99.9%,
median 0.10x, 65% of paths end below half.

Reading: a ten-fold gain in one year with better-than-even odds and without a 50% drawdown needs a strategy of Sharpe about
3 run at about 5x leverage. The strategies that pass or nearly pass here have Sharpe about 1.1-1.2 after costs, which the
literature calls the practical ceiling for crypto trend following. At that quality, the ten-fold target in one year is a
roughly 1-in-7 to 1-in-4 lottery bought with a near-certain halving of the account along the way. Over four to five years at
1x-2x, the same strategy's median path reaches roughly 8-25x, with 50%+ drawdowns expected on the way.

## Multiplicity

Twelve strategy variants were pre-registered; two passed (both ETH trend, both correlated with each other and with the WEAK
BTC trend results). With twelve correlated variants, two passes at this margin are consistent with a real but modest trend
effect on majors and are not evidence of anything else. No parameter was changed after results. Any follow-up is a new
protocol.

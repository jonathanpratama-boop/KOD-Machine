# ALERT_ATTRIBUTION_v1: every 2023 alert as one isolated trade

Ran 2026-10-31T15:40:49Z at commit `efc5ac3d23e9402ad85a97be2d9745c4b78a2145`. attribution study on 2023 (already-studied data), simulation only; not investable, not a strategy, no permission to buy; 2024 data never read

Each of the 1,825 early-population top-five alerts per arm was traded on its own with CRYPTO_REPLAY_v1's frozen BASE rules (entry next open, 0.1% fee + 0.1% slippage per side, 5% stop, 10% target, bar-5 close exit), no account limits, and labelled by what the BASE account did with it. Net returns are per trade; they do not add up to a portfolio.

## Verdicts (fixed rules, from the numbers)

- Q1 score -> trade outcome: MIXED. Spearman rho summary +0.012, sequence -0.018; top-minus-bottom quintile mean net return summary +0.25 pts, sequence +0.26 pts.
- Q2 crowding out: NOT CROWDED OUT. summary: skipped minus admitted +0.21 pts (95% -0.52 to +0.94); sequence: skipped minus admitted +0.38 pts (95% -0.32 to +1.06).
- Q3 forecast -> trade: summary: P(10% target before 5% stop | model hit) = 83%; sequence: P(10% target before 5% stop | model hit) = 92%. The trade matches the forecast.

## Ace's figures, reproduced from the account ledgers

| Arm | Model hits | Hits the account entered | Entry-day stops (account) | Closed P&L before costs | After costs |
|---|---:|---:|---:|---:|---:|
| summary | 60 | 6 | 28 | 1,290.88 | 208.93 |
| sequence | 76 | 13 | 55 | 1,548.84 | 323.95 |
| shuffled | 75 | 13 | 48 | 2,306.33 | 1,050.60 |

## summary

**A. All 1825 alerts in isolation:** 1808 closed, statuses {'CLOSED': 1808, 'UNRESOLVED': 12, 'UNFILLED_AFTER_DATA': 5}; exits {'TIME_EXIT': 940, 'STOP': 549, 'TARGET': 319}; entry-day stops 179; ambiguous bars 16. Mean net return +0.27% (median -0.67%), win rate 42.5%; mean gross +0.68% minus cost 0.40% per trade (3.80 USDT at the account's size).

**B. Score versus outcome**

| Rank | Alerts | Mean net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|
| 1 | 365 | -0.27% | 38.0% | 1.6% |
| 2 | 365 | +0.40% | 43.3% | 3.6% |
| 3 | 365 | +0.21% | 42.5% | 2.5% |
| 4 | 365 | +0.47% | 43.1% | 4.7% |
| 5 | 365 | +0.58% | 45.5% | 4.1% |

| Score quintile (5 = highest) | Alerts | Mean net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|
| 1 | 365 | +0.24% | 42.7% | 2.7% |
| 2 | 365 | +0.20% | 39.1% | 2.7% |
| 3 | 365 | +0.41% | 43.5% | 3.3% |
| 4 | 365 | +0.03% | 40.3% | 3.0% |
| 5 | 365 | +0.49% | 46.7% | 4.7% |

Spearman rho(score, net return) +0.012; top minus bottom quintile +0.25%.

**C. Admitted versus skipped**

| Group | Alerts | Closed | Mean net | Median net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|---:|---:|
| admitted | 291 | 288 | +0.10% | -0.83% | 41.0% | 2.1% |
| skipped (all) | 1534 | 1520 | +0.31% | -0.66% | 42.8% | 3.5% |
| skipped: SKIP_DAILY_LIMIT | 28 | 28 | +0.94% | +1.01% | 50.0% | 10.7% |
| skipped: SKIP_DUPLICATE_SYMBOL | 579 | 571 | -0.34% | -0.80% | 36.4% | 2.1% |
| skipped: SKIP_RISK_LIMIT | 927 | 921 | +0.69% | -0.50% | 46.5% | 4.2% |

Skipped minus admitted: +0.21% (95% -0.52% to +0.94%). Model hits admitted: 6 of 60. First alert of each run only (608 runs): admitted mean net +0.80% (95), skipped +0.49% (513); difference -0.32% (95% -1.75% to +1.01%).

**D. The model's event versus our trade**

| Model label | OTHER | STOP | TARGET | TIME_LOSS | TIME_WIN |
|---|---:|---:|---:|---:|---:|
| censored | 17 | 5 | 4 | 0 | 0 |
| hit | 0 | 10 | 50 | 0 | 0 |
| non-hit | 0 | 534 | 265 | 491 | 449 |

P(target before stop | model hit) 83.3%; P(stop | hit) 16.7%; P(model hit | target) 15.7%; entry-day stop rate 9.9%; mean net on hits +7.18%, on non-hits +0.03%.

**E. Volatility**

| vol20 tercile | Median daily vol | Alerts | Mean net | Stop rate | Entry-day stop rate | Model hit rate |
|---|---:|---:|---:|---:|---:|---:|
| low | 0.9% | 609 | -0.16% | 14.4% | 3.0% | 1.5% |
| mid | 1.8% | 608 | +0.35% | 33.3% | 8.8% | 4.4% |
| high | 2.6% | 608 | +0.63% | 43.4% | 18.0% | 3.9% |

The model's barrier exceeds our 10% target in 69% of alerts (median barrier 13%); the 5% stop is a median 2.84 daily standard deviations away.

## sequence

**A. All 1825 alerts in isolation:** 1811 closed, statuses {'CLOSED': 1811, 'UNRESOLVED': 9, 'UNFILLED_AFTER_DATA': 5}; exits {'TIME_EXIT': 763, 'STOP': 640, 'TARGET': 408}; entry-day stops 221; ambiguous bars 20. Mean net return +0.44% (median -0.82%), win rate 42.7%; mean gross +0.84% minus cost 0.40% per trade (3.81 USDT at the account's size).

**B. Score versus outcome**

| Rank | Alerts | Mean net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|
| 1 | 365 | +0.17% | 40.7% | 2.5% |
| 2 | 365 | +0.33% | 43.6% | 3.6% |
| 3 | 365 | +0.10% | 40.1% | 4.1% |
| 4 | 365 | +0.74% | 44.1% | 5.2% |
| 5 | 365 | +0.87% | 44.9% | 5.5% |

| Score quintile (5 = highest) | Alerts | Mean net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|
| 1 | 365 | +0.43% | 43.0% | 3.6% |
| 2 | 365 | +0.09% | 38.6% | 3.0% |
| 3 | 365 | +0.65% | 44.1% | 4.9% |
| 4 | 365 | +0.34% | 41.8% | 2.5% |
| 5 | 365 | +0.69% | 46.0% | 6.8% |

Spearman rho(score, net return) -0.018; top minus bottom quintile +0.26%.

**C. Admitted versus skipped**

| Group | Alerts | Closed | Mean net | Median net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|---:|---:|
| admitted | 328 | 325 | +0.13% | -1.55% | 39.7% | 4.0% |
| skipped (all) | 1497 | 1486 | +0.51% | -0.73% | 43.3% | 4.2% |
| skipped: SKIP_DAILY_LIMIT | 58 | 58 | +0.32% | -2.23% | 39.7% | 5.2% |
| skipped: SKIP_DUPLICATE_SYMBOL | 523 | 516 | -0.32% | -0.95% | 38.0% | 2.1% |
| skipped: SKIP_RISK_LIMIT | 916 | 912 | +0.99% | -0.41% | 46.6% | 5.3% |

Skipped minus admitted: +0.38% (95% -0.32% to +1.06%). Model hits admitted: 13 of 76. First alert of each run only (737 runs): admitted mean net +0.45% (109), skipped +0.84% (628); difference +0.39% (95% -0.88% to +1.60%).

**D. The model's event versus our trade**

| Model label | OTHER | STOP | TARGET | TIME_LOSS | TIME_WIN |
|---|---:|---:|---:|---:|---:|
| censored | 14 | 8 | 5 | 0 | 0 |
| hit | 0 | 6 | 70 | 0 | 0 |
| non-hit | 0 | 626 | 333 | 398 | 365 |

P(target before stop | model hit) 92.1%; P(stop | hit) 7.9%; P(model hit | target) 17.2%; entry-day stop rate 12.2%; mean net on hits +8.49%, on non-hits +0.09%.

**E. Volatility**

| vol20 tercile | Median daily vol | Alerts | Mean net | Stop rate | Entry-day stop rate | Model hit rate |
|---|---:|---:|---:|---:|---:|---:|
| low | 1.2% | 609 | +0.00% | 21.7% | 4.6% | 4.1% |
| mid | 2.0% | 608 | +0.13% | 38.7% | 10.1% | 3.5% |
| high | 2.8% | 608 | +1.21% | 45.8% | 22.1% | 4.9% |

The model's barrier exceeds our 10% target in 77% of alerts (median barrier 14%); the 5% stop is a median 2.53 daily standard deviations away.

## shuffled

**A. All 1825 alerts in isolation:** 1811 closed, statuses {'CLOSED': 1811, 'UNRESOLVED': 9, 'UNFILLED_AFTER_DATA': 5}; exits {'TIME_EXIT': 834, 'STOP': 613, 'TARGET': 364}; entry-day stops 214; ambiguous bars 22. Mean net return +0.29% (median -0.75%), win rate 42.6%; mean gross +0.70% minus cost 0.40% per trade (3.80 USDT at the account's size).

**B. Score versus outcome**

| Rank | Alerts | Mean net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|
| 1 | 365 | -0.11% | 39.4% | 2.2% |
| 2 | 365 | +0.18% | 40.3% | 3.6% |
| 3 | 365 | +0.58% | 43.9% | 4.4% |
| 4 | 365 | +0.09% | 40.8% | 5.5% |
| 5 | 365 | +0.73% | 48.8% | 4.9% |

| Score quintile (5 = highest) | Alerts | Mean net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|
| 1 | 365 | +0.04% | 40.8% | 3.8% |
| 2 | 365 | -0.06% | 39.9% | 3.6% |
| 3 | 365 | +0.46% | 43.5% | 3.6% |
| 4 | 365 | +0.33% | 42.2% | 4.9% |
| 5 | 365 | +0.70% | 46.7% | 4.7% |

Spearman rho(score, net return) +0.018; top minus bottom quintile +0.66%.

**C. Admitted versus skipped**

| Group | Alerts | Closed | Mean net | Median net | Win rate | Model hit rate |
|---|---:|---:|---:|---:|---:|---:|
| admitted | 323 | 320 | +0.36% | -0.98% | 41.2% | 4.0% |
| skipped (all) | 1502 | 1491 | +0.28% | -0.72% | 42.9% | 4.1% |
| skipped: SKIP_DAILY_LIMIT | 56 | 55 | +2.02% | +0.62% | 54.5% | 7.1% |
| skipped: SKIP_DUPLICATE_SYMBOL | 543 | 540 | -0.31% | -0.90% | 37.2% | 2.9% |
| skipped: SKIP_RISK_LIMIT | 903 | 896 | +0.53% | -0.66% | 45.6% | 4.7% |

Skipped minus admitted: -0.08% (95% -0.80% to +0.58%). Model hits admitted: 13 of 75. First alert of each run only (745 runs): admitted mean net +0.76% (118), skipped +0.51% (627); difference -0.24% (95% -1.52% to +1.02%).

**D. The model's event versus our trade**

| Model label | OTHER | STOP | TARGET | TIME_LOSS | TIME_WIN |
|---|---:|---:|---:|---:|---:|
| censored | 14 | 8 | 4 | 0 | 0 |
| hit | 0 | 12 | 63 | 0 | 0 |
| non-hit | 0 | 593 | 297 | 426 | 408 |

P(target before stop | model hit) 84.0%; P(stop | hit) 16.0%; P(model hit | target) 17.3%; entry-day stop rate 11.8%; mean net on hits +7.28%, on non-hits -0.01%.

**E. Volatility**

| vol20 tercile | Median daily vol | Alerts | Mean net | Stop rate | Entry-day stop rate | Model hit rate |
|---|---:|---:|---:|---:|---:|---:|
| low | 1.1% | 609 | -0.16% | 18.3% | 4.1% | 2.6% |
| mid | 1.9% | 608 | +0.28% | 37.9% | 9.4% | 4.1% |
| high | 2.7% | 608 | +0.76% | 45.5% | 22.0% | 5.6% |

The model's barrier exceeds our 10% target in 73% of alerts (median barrier 14%); the 5% stop is a median 2.65 daily standard deviations away.

## Limits

- The same coin alerted on consecutive days counts once per alert (runs over-weighted; section C also collapses runs).
- Isolated trades ignore cash and risk limits by design.
- Daily bars, modelled costs, one already-studied year; descriptive, no statistical certainty.

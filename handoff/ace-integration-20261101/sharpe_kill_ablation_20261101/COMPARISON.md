# Sharpe-kill ablation: comparison

Classification: **REUSED_DATA_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION**. Reused historical data; describes what the negative-90-day-Sharpe kill did on this history. It cannot show that removing it would improve future returns.

## development

| | Baseline (both kills) | Challenger (drawdown kill only) |
|---|---:|---:|
| Ending NAV (USDT, from 10,000) | 20,592.77 | 17,716.06 |
| Total growth | +105.93% | +77.16% |
| Annualised growth | +14.70% | +11.47% |
| Sampled max drawdown | +15.42% | +27.12% |
| Annualised vol, whole partition | +12.63% | +14.65% |
| Daily Sharpe (annualised) | 1.15 | 0.81 |
| Time invested | 144 of 1923 days | 199 of 1923 days |
| Annualised vol while invested | +45.27% | +45.29% |
| Fills / fees (USDT) | 228 / 88.69 | 321 / 193.29 |
| Kill | 2018-03-15 NEGATIVE_TRAILING_90_DAY_SHARPE | 2018-08-08 DRAWDOWN_AT_LEAST_25_PERCENT |

First divergence: {'index': 0, 'baseline_op': 'init:TREND_V2_SHARED:2017-09-26', 'challenger_op': 'init:TREND_V2_SHARED:2017-09-26', 'date': '2017-09-26T00:00:00Z'}. First daily NAV difference: 2018-04-21.
Additional fills in challenger: 93.
Days the removed Sharpe rule would have fired (challenger): 224 in 5 separate runs, first 2018-03-15.
Reading (pre-declared): **PROTECTED_CAPITAL** (end NAV difference -2,876.71 USDT; max drawdown difference +11.70 pp).

Year-end NAV (last daily open mark of each year):

| Year | Baseline | Challenger |
|---|---:|---:|
| 2017 | 20,113.71 | 20,113.71 |
| 2018 | 20,592.77 | 17,716.06 |
| 2019 | 20,592.77 | 17,716.06 |
| 2020 | 20,592.77 | 17,716.06 |
| 2021 | 20,592.77 | 17,716.06 |
| 2022 | 20,592.77 | 17,716.06 |
| 2023 | 20,592.77 | 17,716.06 |

Benchmarks from the published run (different risk policies; see notes):

| Policy | Ending NAV | Growth | Sampled max drawdown | Mean exposure | Kill |
|---|---:|---:|---:|---:|---|
| CASH | 10,000.00 | +0.00% | +0.00% | 0.0% | none |
| PASSIVE_50_50_RISK_MATCHED | 17,844.13 | +78.44% | +27.60% | 4.3% | 2018-02-03 DRAWDOWN_AT_LEAST_25_PERCENT |
| CONVENTIONAL_50_50_BUY_HOLD_NO_KILL | 24,500.54 | +145.01% | +71.69% | 68.8% | none |

## validation

| | Baseline (both kills) | Challenger (drawdown kill only) |
|---|---:|---:|
| Ending NAV (USDT, from 10,000) | 12,377.20 | 19,340.00 |
| Total growth | +23.77% | +93.40% |
| Annualised growth | +5.86% | +19.24% |
| Sampled max drawdown | +11.55% | +30.20% |
| Annualised vol, whole partition | +12.42% | +23.70% |
| Daily Sharpe (annualised) | 0.52 | 0.86 |
| Time invested | 89 of 1368 days | 388 of 1368 days |
| Annualised vol while invested | +48.69% | +44.42% |
| Fills / fees (USDT) | 180 / 76.78 | 693 / 482.69 |
| Kill | 2023-04-22 NEGATIVE_TRAILING_90_DAY_SHARPE | 2024-08-03 DRAWDOWN_AT_LEAST_25_PERCENT |

First divergence: {'index': 0, 'baseline_op': 'init:TREND_V2_SHARED:2023-01-01', 'challenger_op': 'init:TREND_V2_SHARED:2023-01-01', 'date': '2023-01-01T00:00:00Z'}. First daily NAV difference: 2023-04-23.
Additional fills in challenger: 513.
Days the removed Sharpe rule would have fired (challenger): 294 in 10 separate runs, first 2023-04-22.
Reading (pre-declared): **BOTH** (end NAV difference +6,962.80 USDT; max drawdown difference +18.65 pp).

Year-end NAV (last daily open mark of each year):

| Year | Baseline | Challenger |
|---|---:|---:|
| 2023 | 12,377.20 | 17,404.18 |
| 2024 | 12,377.20 | 19,340.00 |
| 2025 | 12,377.20 | 19,340.00 |
| 2026 | 12,377.20 | 19,340.00 |

Benchmarks from the published run (different risk policies; see notes):

| Policy | Ending NAV | Growth | Sampled max drawdown | Mean exposure | Kill |
|---|---:|---:|---:|---:|---|
| CASH | 10,000.00 | +0.00% | +0.00% | 0.0% | none |
| PASSIVE_50_50_RISK_MATCHED | 15,037.86 | +50.38% | +19.54% | 12.1% | 2023-06-16 NEGATIVE_TRAILING_90_DAY_SHARPE |
| CONVENTIONAL_50_50_BUY_HOLD_NO_KILL | 36,220.21 | +262.20% | +57.58% | 99.9% | none |


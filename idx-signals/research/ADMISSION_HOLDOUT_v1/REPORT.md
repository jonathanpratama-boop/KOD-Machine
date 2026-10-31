# ADMISSION_HOLDOUT_v1: the fresh 10-15% rule on 2024-01-01..2026-10-29

Ran 2026-10-31T18:44:15Z at commit `5eae447c1c16dcff3daf02da6bd6ee836069eaae`. Owner-authorised, one run, frozen before any 2024+ bar was collected. Panel f63a227ff91e..., 479,113 bars, 638 pairs (1 failed requests).

## Verdict: NOT CONFIRMED

- summary/BASE: WORSE
- summary/DOUBLE_COSTS: IMPROVES
- sequence/BASE: IMPROVES
- sequence/DOUBLE_COSTS: IMPROVES

## summary

5165 alerts over 1033 days; eligibility {'NOT_FRESH': 3703, 'BELOW_BAND': 807, 'ELIGIBLE': 588, 'AT_OR_ABOVE_BAND': 67}; days with an eligible alert 342.

### BASE: WORSE

| Policy | End equity | Net return | Max drawdown | Fills | Closed | Mean exposure | Return / exposure | Fees + slippage | Realized | Unrealized | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 8,017.08 | -19.83% | -30.54% | 842 | 839 | 20.8% | -0.95 | 3,049.96 | -1,990.68 | 7.76 | +6.17% | -16.03% | -10.07% |
| challenger | 7,933.22 | -20.67% | -25.01% | 310 | 308 | 7.2% | -2.88 | 1,053.57 | -2,057.74 | -9.04 | -0.01% | -9.66% | -12.17% |

Challenger minus baseline: -83.86 USDT; drawdown +5.53%; ahead in 19 of 34 months; summed daily return difference -1.87% (95% -33.99% to +28.95%). Without its 5 largest winners the challenger realized -2,522.44 (baseline -2,499.62). Skips: challenger {'SKIP_DAILY_LIMIT': 2, 'SKIP_DUPLICATE_SYMBOL': 37, 'SKIP_RISK_LIMIT': 238, 'ambiguous_bar': 5, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}.

### DOUBLE_COSTS: IMPROVES

| Policy | End equity | Net return | Max drawdown | Fills | Closed | Mean exposure | Return / exposure | Fees + slippage | Realized | Unrealized | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 5,992.95 | -40.07% | -44.85% | 850 | 847 | 19.6% | -2.04 | 5,033.13 | -4,009.32 | 2.27 | -6.45% | -24.18% | -15.50% |
| challenger | 7,240.92 | -27.59% | -30.35% | 311 | 309 | 6.7% | -4.10 | 1,914.01 | -2,748.66 | -10.42 | -2.21% | -11.72% | -16.12% |

Challenger minus baseline: +1,247.97 USDT; drawdown +14.50%; ahead in 19 of 34 months; summed daily return difference +18.13% (95% -12.75% to +48.45%). Without its 5 largest winners the challenger realized -3,170.71 (baseline -4,456.86). Skips: challenger {'SKIP_DAILY_LIMIT': 2, 'SKIP_DUPLICATE_SYMBOL': 36, 'SKIP_RISK_LIMIT': 238, 'ambiguous_bar': 5, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}.

## sequence

5165 alerts over 1033 days; eligibility {'NOT_FRESH': 3348, 'BELOW_BAND': 1101, 'ELIGIBLE': 644, 'AT_OR_ABOVE_BAND': 72}; days with an eligible alert 352.

### BASE: IMPROVES

| Policy | End equity | Net return | Max drawdown | Fills | Closed | Mean exposure | Return / exposure | Fees + slippage | Realized | Unrealized | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 6,449.24 | -35.51% | -41.87% | 931 | 929 | 19.9% | -1.79 | 3,144.81 | -3,519.53 | -31.23 | -1.51% | -18.32% | -19.83% |
| challenger | 10,086.01 | +0.86% | -13.90% | 348 | 347 | 6.4% | +0.13 | 1,320.70 | 101.74 | -15.73 | +4.24% | -3.85% | +0.63% |

Challenger minus baseline: +3,636.77 USDT; drawdown +27.97%; ahead in 22 of 34 months; summed daily return difference +43.62% (95% +6.53% to +80.62%). Without its 5 largest winners the challenger realized -383.15 (baseline -4,012.47). Skips: challenger {'SKIP_DAILY_LIMIT': 2, 'SKIP_DUPLICATE_SYMBOL': 34, 'SKIP_RISK_LIMIT': 258, 'ambiguous_bar': 10, 'unfilled_end_of_data': 2, 'unresolved_end_of_data': 1}.

### DOUBLE_COSTS: IMPROVES

| Policy | End equity | Net return | Max drawdown | Fills | Closed | Mean exposure | Return / exposure | Fees + slippage | Realized | Unrealized | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 4,921.53 | -50.78% | -53.89% | 941 | 939 | 18.8% | -2.71 | 5,268.18 | -5,054.05 | -24.42 | -13.51% | -24.95% | -24.19% |
| challenger | 9,143.74 | -8.56% | -18.05% | 348 | 347 | 6.1% | -1.41 | 2,361.32 | -841.10 | -15.16 | +1.60% | -6.80% | -3.43% |

Challenger minus baseline: +4,222.21 USDT; drawdown +35.83%; ahead in 21 of 34 months; summed daily return difference +60.92% (95% +25.01% to +96.66%). Without its 5 largest winners the challenger realized -1,270.96 (baseline -5,490.05). Skips: challenger {'SKIP_DAILY_LIMIT': 2, 'SKIP_DUPLICATE_SYMBOL': 35, 'SKIP_RISK_LIMIT': 257, 'ambiguous_bar': 10, 'unfilled_end_of_data': 2, 'unresolved_end_of_data': 1}.

## Limits

- Survivorship: today's archive catalogue. Daily bars, modelled costs.
- The 2024+ bars were read before by CRYPTO_TUNE_v1 (spike days) and BINANCE_ANN_1S_HOLDOUT (announcement windows); this question had not been asked of them.

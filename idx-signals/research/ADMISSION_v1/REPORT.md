# ADMISSION_v1: original admission versus fresh alerts at 0.10 <= p < 0.15 (2023, cash-constrained)

Ran 2026-10-31T18:25:40Z at commit `48a4d8dcb09b75755ee44bb3ceb9d0e13284f6c0`. retrospective development evidence on 2023 (already studied, including by SCORE_VALUE_v1, which suggested this rule); not validation; simulation only, no orders; 2024+ not opened

Both policies use the audited CRYPTO_REPLAY_v1 account engine unchanged; the challenger only removes alerts from the same daily top five (never adds). Its risk convention is the audited one: at most three pending or open positions at 0.5% planned risk each.

## Verdict (fixed rules)

- The challenger did not improve the 2023 account in every model and cost case: summary/BASE WORSE, summary/DOUBLE_COSTS WORSE, sequence/BASE IMPROVES, sequence/DOUBLE_COSTS IMPROVES.

## summary

Alerts 1825; eligibility of the original top five: {'NOT_FRESH': 1217, 'ELIGIBLE': 393, 'BELOW_BAND': 124, 'AT_OR_ABOVE_BAND': 86, 'FRESHNESS_UNKNOWN': 5}; days with an eligible alert: 224.

### BASE: verdict WORSE

| Policy | End equity | Net return | Max drawdown | Realized | Unrealized | Fees | Slippage | Turnover | Mean exposure | Return / exposure | Orders | Fills | Closed | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 10,152.19 | +1.52% | -13.35% (2023-09-12) | 208.93 | -56.73 | 543.87 | 543.86 | 54.94 | 20.9% | 0.07 | 291 | 291 | 288 | +41.0% |
| challenger | 9,614.93 | -3.85% | -13.97% (2023-10-19) | -331.49 | -53.58 | 355.25 | 355.25 | 37.35 | 13.2% | -0.29 | 200 | 199 | 197 | +40.1% |

Paired (challenger minus baseline): end equity -537.26 USDT; net return -5.37%; max drawdown -0.61%; mean exposure -7.7%; summed daily return difference -5.60% (95% -23.44% to +12.88%).

Skips and rejections: baseline {'SKIP_DAILY_LIMIT': 28, 'SKIP_DUPLICATE_SYMBOL': 579, 'SKIP_RISK_LIMIT': 927, 'ambiguous_bar': 2, 'unresolved_end_of_data': 3}; challenger {'SKIP_DAILY_LIMIT': 2, 'SKIP_DUPLICATE_SYMBOL': 30, 'SKIP_RISK_LIMIT': 161, 'ambiguous_bar': 4, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}. Exit reasons: baseline {'TIME_EXIT': 145, 'TARGET': 50, 'STOP': 93}; challenger {'STOP': 77, 'TIME_EXIT': 85, 'TARGET': 35}.

Concentration: baseline realized 208.93, without its 5 largest winners -274.56; challenger realized -331.49, without its 5 largest winners -796.35; challenger's largest winners [93.46, 93.41, 92.91, 92.56, 92.52].

| Month | Baseline | Challenger | Difference |
|---|---:|---:|---:|
| 2023-01 | +5.03% | +2.27% | -2.76% |
| 2023-02 | -1.38% | -2.31% | -0.93% |
| 2023-03 | -1.22% | -0.92% | +0.30% |
| 2023-04 | -2.37% | -0.95% | +1.42% |
| 2023-05 | -1.25% | -2.91% | -1.66% |
| 2023-06 | -4.25% | -2.89% | +1.35% |
| 2023-07 | +2.22% | +1.89% | -0.34% |
| 2023-08 | -2.41% | -2.74% | -0.33% |
| 2023-09 | -0.51% | +0.12% | +0.64% |
| 2023-10 | +4.72% | -1.25% | -5.97% |
| 2023-11 | +1.69% | -0.25% | -1.94% |
| 2023-12 | +1.70% | +6.43% | +4.73% |

### DOUBLE_COSTS: verdict WORSE

| Policy | End equity | Net return | Max drawdown | Realized | Unrealized | Fees | Slippage | Turnover | Mean exposure | Return / exposure | Orders | Fills | Closed | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 8,952.49 | -10.48% | -19.41% (2023-10-12) | -995.26 | -52.25 | 978.58 | 978.58 | 52.25 | 19.8% | -0.53 | 292 | 292 | 289 | +37.0% |
| challenger | 8,771.14 | -12.29% | -19.50% (2023-10-19) | -1,179.39 | -49.47 | 639.47 | 639.46 | 34.84 | 12.5% | -0.99 | 198 | 197 | 195 | +35.4% |

Paired (challenger minus baseline): end equity -181.36 USDT; net return -1.81%; max drawdown -0.09%; mean exposure -7.3%; summed daily return difference -2.22% (95% -19.35% to +15.39%).

Skips and rejections: baseline {'SKIP_DAILY_LIMIT': 24, 'SKIP_DUPLICATE_SYMBOL': 585, 'SKIP_RISK_LIMIT': 924, 'ambiguous_bar': 2, 'unresolved_end_of_data': 3}; challenger {'SKIP_DAILY_LIMIT': 2, 'SKIP_DUPLICATE_SYMBOL': 29, 'SKIP_RISK_LIMIT': 164, 'ambiguous_bar': 4, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}. Exit reasons: baseline {'TIME_EXIT': 147, 'TARGET': 47, 'STOP': 95}; challenger {'STOP': 79, 'TIME_EXIT': 84, 'TARGET': 32}.

Concentration: baseline realized -995.26, without its 5 largest winners -1,433.43; challenger realized -1,179.39, without its 5 largest winners -1,603.83; challenger's largest winners [85.29, 85.27, 84.67, 84.62, 84.59].

| Month | Baseline | Challenger | Difference |
|---|---:|---:|---:|
| 2023-01 | +3.93% | +1.62% | -2.31% |
| 2023-02 | -2.15% | -2.52% | -0.36% |
| 2023-03 | -2.19% | -1.01% | +1.18% |
| 2023-04 | -2.93% | -1.44% | +1.50% |
| 2023-05 | -1.89% | -3.30% | -1.42% |
| 2023-06 | -4.68% | -2.93% | +1.74% |
| 2023-07 | +0.86% | -0.56% | -1.42% |
| 2023-08 | -3.04% | -3.69% | -0.65% |
| 2023-09 | -2.75% | -1.58% | +1.17% |
| 2023-10 | +2.57% | -1.87% | -4.44% |
| 2023-11 | +0.93% | -0.61% | -1.54% |
| 2023-12 | +0.72% | +5.19% | +4.47% |

## sequence

Alerts 1825; eligibility of the original top five: {'NOT_FRESH': 1088, 'ELIGIBLE': 453, 'BELOW_BAND': 189, 'AT_OR_ABOVE_BAND': 90, 'FRESHNESS_UNKNOWN': 5}; days with an eligible alert: 232.

### BASE: verdict IMPROVES

| Policy | End equity | Net return | Max drawdown | Realized | Unrealized | Fees | Slippage | Turnover | Mean exposure | Return / exposure | Orders | Fills | Closed | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 10,232.58 | +2.33% | -18.21% (2023-09-14) | 323.95 | -91.37 | 615.37 | 615.37 | 62.11 | 19.9% | 0.12 | 328 | 328 | 325 | +39.7% |
| challenger | 10,755.44 | +7.55% | -6.97% (2023-09-21) | 815.73 | -60.29 | 444.25 | 444.25 | 42.90 | 13.0% | 0.58 | 228 | 227 | 225 | +40.0% |

Paired (challenger minus baseline): end equity +522.86 USDT; net return +5.23%; max drawdown +11.24%; mean exposure -7.0%; summed daily return difference +4.79% (95% -13.50% to +22.79%).

Skips and rejections: baseline {'SKIP_DAILY_LIMIT': 58, 'SKIP_DUPLICATE_SYMBOL': 523, 'SKIP_RISK_LIMIT': 916, 'ambiguous_bar': 8, 'unresolved_end_of_data': 3}; challenger {'SKIP_DAILY_LIMIT': 3, 'SKIP_DUPLICATE_SYMBOL': 21, 'SKIP_RISK_LIMIT': 201, 'ambiguous_bar': 5, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}. Exit reasons: baseline {'STOP': 128, 'TIME_EXIT': 124, 'TARGET': 73}; challenger {'TIME_EXIT': 77, 'TARGET': 59, 'STOP': 89}.

Concentration: baseline realized 323.95, without its 5 largest winners -170.44; challenger realized 815.73, without its 5 largest winners 322.49; challenger's largest winners [99.18, 98.76, 98.61, 98.52, 98.18].

| Month | Baseline | Challenger | Difference |
|---|---:|---:|---:|
| 2023-01 | +5.18% | +3.05% | -2.13% |
| 2023-02 | +2.29% | +1.09% | -1.20% |
| 2023-03 | -2.75% | -0.30% | +2.45% |
| 2023-04 | -2.48% | -1.92% | +0.56% |
| 2023-05 | -3.16% | -0.51% | +2.65% |
| 2023-06 | -5.38% | -0.24% | +5.13% |
| 2023-07 | +1.59% | +3.39% | +1.80% |
| 2023-08 | -2.18% | -2.32% | -0.13% |
| 2023-09 | -1.30% | -0.26% | +1.04% |
| 2023-10 | +6.75% | +5.53% | -1.22% |
| 2023-11 | +0.83% | +0.74% | -0.09% |
| 2023-12 | +3.68% | -0.65% | -4.33% |

### DOUBLE_COSTS: verdict IMPROVES

| Policy | End equity | Net return | Max drawdown | Realized | Unrealized | Fees | Slippage | Turnover | Mean exposure | Return / exposure | Orders | Fills | Closed | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 8,937.46 | -10.63% | -23.61% (2023-09-16) | -982.10 | -80.44 | 1,088.20 | 1,088.20 | 58.76 | 18.9% | -0.56 | 327 | 327 | 324 | +36.4% |
| challenger | 10,039.95 | +0.40% | -7.99% (2023-07-20) | 96.90 | -56.95 | 806.08 | 806.08 | 40.05 | 12.4% | 0.03 | 225 | 224 | 222 | +38.7% |

Paired (challenger minus baseline): end equity +1,102.50 USDT; net return +11.02%; max drawdown +15.63%; mean exposure -6.6%; summed daily return difference +11.45% (95% -8.45% to +31.30%).

Skips and rejections: baseline {'SKIP_DAILY_LIMIT': 58, 'SKIP_DUPLICATE_SYMBOL': 524, 'SKIP_RISK_LIMIT': 916, 'ambiguous_bar': 8, 'unresolved_end_of_data': 3}; challenger {'SKIP_DAILY_LIMIT': 4, 'SKIP_DUPLICATE_SYMBOL': 21, 'SKIP_RISK_LIMIT': 203, 'ambiguous_bar': 6, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}. Exit reasons: baseline {'STOP': 130, 'TIME_EXIT': 125, 'TARGET': 69}; challenger {'TIME_EXIT': 75, 'TARGET': 58, 'STOP': 89}.

Concentration: baseline realized -982.10, without its 5 largest winners -1,424.03; challenger realized 96.90, without its 5 largest winners -338.56; challenger's largest winners [87.5, 87.11, 87.03, 86.94, 86.89].

| Month | Baseline | Challenger | Difference |
|---|---:|---:|---:|
| 2023-01 | +4.07% | +2.42% | -1.65% |
| 2023-02 | +0.54% | +0.50% | -0.05% |
| 2023-03 | -3.41% | -0.47% | +2.95% |
| 2023-04 | -3.10% | -2.44% | +0.66% |
| 2023-05 | -4.12% | -1.01% | +3.10% |
| 2023-06 | -6.38% | -0.53% | +5.85% |
| 2023-07 | -0.98% | +3.75% | +4.73% |
| 2023-08 | -2.68% | -2.94% | -0.27% |
| 2023-09 | -1.97% | -0.60% | +1.36% |
| 2023-10 | +3.82% | +3.10% | -0.72% |
| 2023-11 | +0.34% | +0.37% | +0.04% |
| 2023-12 | +3.32% | -1.51% | -4.83% |

## Reading this

- Holding fewer positions lowers exposure and usually drawdown whatever the selection; 'return per unit of mean exposure' and the paired daily differences are shown so a smaller account is not mistaken for a better one.
- 2023 was already studied and this rule was suggested by SCORE_VALUE_v1 on the same year: any improvement is retrospective development evidence, not a proven edge.
- This tests freshness and the band together, not priority alone.

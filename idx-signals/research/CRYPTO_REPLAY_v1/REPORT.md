# CRYPTO_REPLAY_v1: 2023 historical crypto paper-account replay

Ran 2026-10-31T15:07:53Z at commit `e1fac0753750e55c6348311330e7c1c2cf730c6e`. a separate hypothetical test of the frozen PREMOVE_SEQUENCE_v1 rankings: every day's frozen top-five early-population shortlist is offered to the account in rank order and the account limits decide which names enter. It is not a replay of the live crypto paper policy (which decides PASS) and grants no permission to activate buys. Retrospective development evidence on 2023, a year KOD has studied before; NOT untouched validation. Simulation only: no orders. 2024 data is never opened, not even to finish year-end trades: positions open at the end of 2023-12-31 stay unresolved, valued at their last 2023 close.

## Verdict (fixed rules, from the numbers)

- In the primary scenario summary, sequence, shuffled ended above cash.
- No model arm stayed above cash in all four scenarios (delay and doubled costs included).
- Sequence ended above summary in 2 of 4 scenarios (BASE, ENTRY_DELAY_1).
- The sequence-minus-summary interval includes zero in every scenario: no clear executable difference.
- The fewest closed trades in any model arm (primary scenario) is 288: too few for certainty.

## What was traded

Every day's frozen top-five early-population shortlist (ret1 < 10%, ret5 < 20%) was offered to the account in rank order; the account limits decided which names entered. Arms: summary and sequence (frozen PREMOVE_SEQUENCE_v1 models, rankings rebuilt and verified against its summary.json), shuffled (the frozen shuffled-sequence control from PREMOVE_SHADOW_v1/control_model.json, fitted on 2020-2022, not part of the PR #19 run) and cash. A hypothetical test of the rankings: not the live PASS-only policy and no permission to buy.

## Ranking quality (prediction) versus account result (execution)

Each arm put 1825 names on its 2023 early-population shortlist (5 a day). Up hits (barrier reached first on a daily close within 5 days): summary 60, sequence 76, shuffled 75 (published: summary 60, sequence 76). an up hit = the price reached its volatility-scaled barrier (at least +10%) on a daily close within 5 days before falling as far; it ignores costs, stops and whether the account could take the trade.

## Scenario BASE: entry delay 0 bar(s), fee 0.1% + slippage 0.1% per side

| Arm | End equity | Net return | Realized | Unrealized | Max drawdown | Closed trades | Win rate | Avg win | Avg loss | Expectancy | Profit factor | Fees | Slippage | Mean exposure | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| summary | 10,152.19 | +1.52% | 208.93 | -56.73 | -13.35% (2023-09-12) | 288 | +41.0% | 50.58 | -33.88 | 0.73 | 1.04 | 543.87 | 543.86 | +20.9% | 54.94 |
| sequence | 10,232.58 | +2.33% | 323.95 | -91.37 | -18.21% (2023-09-14) | 325 | +39.7% | 60.57 | -38.21 | 1.00 | 1.04 | 615.37 | 615.37 | +19.9% | 62.11 |
| shuffled | 11,029.67 | +10.30% | 1,050.60 | -20.93 | -15.34% (2023-07-06) | 320 | +41.2% | 62.95 | -38.61 | 3.28 | 1.14 | 628.92 | 628.92 | +20.1% | 60.96 |
| cash | 10,000.00 | +0.00% | 0.00 | 0.00 | +0.00% (2023-01-01) | 0 | - | - | - | - | - | 0.00 | 0.00 | +0.0% | 0.00 |

Exit reasons, skips, rejections and data gaps:

- **summary**: orders 291, fills 291; exits {'TIME_EXIT': 145, 'TARGET': 50, 'STOP': 93}; counters {'SKIP_DAILY_LIMIT': 28, 'SKIP_DUPLICATE_SYMBOL': 579, 'SKIP_RISK_LIMIT': 927, 'ambiguous_bar': 2, 'unresolved_end_of_data': 3}; unresolved at the data end: WNXMUSDT valued 929.53 at the close of 2023-12-31 (unrealized -32.87, deadline 2024-01-01); SUNUSDT valued 944.56 at the close of 2023-12-31 (unrealized -19.10, deadline 2024-01-03); PAXGUSDT valued 958.89 at the close of 2023-12-31 (unrealized -4.76, deadline 2024-01-03); unfilled at the data end: none.
- **sequence**: orders 328, fills 328; exits {'STOP': 128, 'TIME_EXIT': 124, 'TARGET': 73}; counters {'SKIP_DAILY_LIMIT': 58, 'SKIP_DUPLICATE_SYMBOL': 523, 'SKIP_RISK_LIMIT': 916, 'ambiguous_bar': 8, 'unresolved_end_of_data': 3}; unresolved at the data end: WNXMUSDT valued 946.83 at the close of 2023-12-31 (unrealized -33.49, deadline 2024-01-01); SUNUSDT valued 953.65 at the close of 2023-12-31 (unrealized -19.28, deadline 2024-01-03); WANUSDT valued 934.70 at the close of 2023-12-31 (unrealized -38.60, deadline 2024-01-04); unfilled at the data end: none.
- **shuffled**: orders 323, fills 321; exits {'TIME_EXIT': 130, 'TARGET': 72, 'STOP': 118}; counters {'SKIP_DAILY_LIMIT': 56, 'SKIP_DUPLICATE_SYMBOL': 543, 'SKIP_RISK_LIMIT': 903, 'ambiguous_bar': 5, 'unfilled_end_of_data': 2, 'unresolved_end_of_data': 1}; unresolved at the data end: SUNUSDT valued 1,035.17 at the close of 2023-12-31 (unrealized -20.93, deadline 2024-01-03); unfilled at the data end: PAXGUSDT (entry 2024-01-01), WNXMUSDT (entry 2024-01-01).

Paired comparisons (moving-block bootstrap of daily return differences, descriptive):

- sequence_minus_summary: end equity +80.39 USDT; summed daily return difference +1.00% (95% interval -14.42% to +16.79%)
- sequence_minus_shuffled: end equity -797.08 USDT; summed daily return difference -7.48% (95% interval -21.34% to +6.61%)
- summary_minus_shuffled: end equity -877.47 USDT; summed daily return difference -8.48% (95% interval -23.69% to +5.86%)
- sequence_minus_cash: end equity +232.58 USDT; summed daily return difference +3.05% (95% interval -20.88% to +27.48%)
- summary_minus_cash: end equity +152.19 USDT; summed daily return difference +2.05% (95% interval -18.13% to +22.47%)
- shuffled_minus_cash: end equity +1,029.67 USDT; summed daily return difference +10.53% (95% interval -14.87% to +36.44%)

## Scenario ENTRY_DELAY_1: entry delay 1 bar(s), fee 0.1% + slippage 0.1% per side

| Arm | End equity | Net return | Realized | Unrealized | Max drawdown | Closed trades | Win rate | Avg win | Avg loss | Expectancy | Profit factor | Fees | Slippage | Mean exposure | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| summary | 10,456.67 | +4.57% | 470.52 | -13.85 | -7.81% (2023-10-12) | 230 | +42.2% | 54.45 | -36.17 | 2.05 | 1.10 | 460.32 | 460.32 | +16.3% | 43.67 |
| sequence | 10,706.73 | +7.07% | 752.91 | -46.18 | -10.39% (2023-06-14) | 245 | +40.4% | 64.60 | -38.65 | 3.07 | 1.13 | 489.54 | 489.54 | +15.6% | 46.68 |
| shuffled | 10,512.53 | +5.13% | 566.00 | -53.47 | -11.24% (2023-12-19) | 239 | +41.0% | 60.67 | -38.16 | 2.37 | 1.11 | 495.14 | 495.14 | +15.9% | 45.40 |
| cash | 10,000.00 | +0.00% | 0.00 | 0.00 | +0.00% (2023-01-01) | 0 | - | - | - | - | - | 0.00 | 0.00 | +0.0% | 0.00 |

Exit reasons, skips, rejections and data gaps:

- **summary**: orders 233, fills 231; exits {'TIME_EXIT': 113, 'TARGET': 45, 'STOP': 72}; counters {'SKIP_DAILY_LIMIT': 20, 'SKIP_DUPLICATE_SYMBOL': 587, 'SKIP_RISK_LIMIT': 985, 'ambiguous_bar': 2, 'unfilled_end_of_data': 2, 'unresolved_end_of_data': 1}; unresolved at the data end: SUNUSDT valued 979.03 at the close of 2023-12-31 (unrealized -13.85, deadline 2024-01-04); unfilled at the data end: PAXGUSDT (entry 2024-01-01), JUVUSDT (entry 2024-01-01).
- **sequence**: orders 248, fills 247; exits {'STOP': 91, 'TIME_EXIT': 98, 'TARGET': 56}; counters {'SKIP_DAILY_LIMIT': 32, 'SKIP_DUPLICATE_SYMBOL': 526, 'SKIP_RISK_LIMIT': 1019, 'ambiguous_bar': 5, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}; unresolved at the data end: WNXMUSDT valued 990.51 at the close of 2023-12-31 (unrealized -26.20, deadline 2024-01-02); SUNUSDT valued 988.17 at the close of 2023-12-31 (unrealized -19.98, deadline 2024-01-03); unfilled at the data end: PAXGUSDT (entry 2024-01-02).
- **shuffled**: orders 242, fills 241; exits {'TIME_EXIT': 107, 'TARGET': 51, 'STOP': 81}; counters {'SKIP_DAILY_LIMIT': 30, 'SKIP_DUPLICATE_SYMBOL': 544, 'SKIP_RISK_LIMIT': 1009, 'ambiguous_bar': 3, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}; unresolved at the data end: SUNUSDT valued 983.35 at the close of 2023-12-31 (unrealized -19.88, deadline 2024-01-03); UTKUSDT valued 966.57 at the close of 2023-12-31 (unrealized -33.59, deadline 2024-01-04); unfilled at the data end: PAXGUSDT (entry 2024-01-01).

Paired comparisons (moving-block bootstrap of daily return differences, descriptive):

- sequence_minus_summary: end equity +250.05 USDT; summed daily return difference +2.51% (95% interval -12.65% to +16.99%)
- sequence_minus_shuffled: end equity +194.20 USDT; summed daily return difference +1.91% (95% interval -14.84% to +19.36%)
- summary_minus_shuffled: end equity -55.85 USDT; summed daily return difference -0.60% (95% interval -13.97% to +12.49%)
- sequence_minus_cash: end equity +706.73 USDT; summed daily return difference +7.36% (95% interval -12.43% to +26.86%)
- summary_minus_cash: end equity +456.67 USDT; summed daily return difference +4.85% (95% interval -14.05% to +23.04%)
- shuffled_minus_cash: end equity +512.53 USDT; summed daily return difference +5.45% (95% interval -18.49% to +28.69%)

## Scenario DOUBLE_COSTS: entry delay 0 bar(s), fee 0.2% + slippage 0.2% per side

| Arm | End equity | Net return | Realized | Unrealized | Max drawdown | Closed trades | Win rate | Avg win | Avg loss | Expectancy | Profit factor | Fees | Slippage | Mean exposure | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| summary | 8,952.49 | -10.48% | -995.26 | -52.25 | -19.41% (2023-10-12) | 289 | +37.0% | 44.87 | -31.85 | -3.44 | 0.83 | 978.58 | 978.58 | +19.8% | 52.25 |
| sequence | 8,937.46 | -10.63% | -982.10 | -80.44 | -23.61% (2023-09-16) | 324 | +36.4% | 52.91 | -35.08 | -3.03 | 0.86 | 1,088.20 | 1,088.20 | +18.9% | 58.76 |
| shuffled | 9,423.13 | -5.77% | -558.22 | -18.65 | -19.93% (2023-09-16) | 326 | +37.1% | 54.95 | -35.16 | -1.71 | 0.92 | 1,124.82 | 1,124.83 | +18.9% | 58.95 |
| cash | 10,000.00 | +0.00% | 0.00 | 0.00 | +0.00% (2023-01-01) | 0 | - | - | - | - | - | 0.00 | 0.00 | +0.0% | 0.00 |

Exit reasons, skips, rejections and data gaps:

- **summary**: orders 292, fills 292; exits {'TIME_EXIT': 147, 'TARGET': 47, 'STOP': 95}; counters {'SKIP_DAILY_LIMIT': 24, 'SKIP_DUPLICATE_SYMBOL': 585, 'SKIP_RISK_LIMIT': 924, 'ambiguous_bar': 2, 'unresolved_end_of_data': 3}; unresolved at the data end: WNXMUSDT valued 777.25 at the close of 2023-12-31 (unrealized -29.10, deadline 2024-01-01); SUNUSDT valued 789.05 at the close of 2023-12-31 (unrealized -17.56, deadline 2024-01-03); PAXGUSDT valued 801.02 at the close of 2023-12-31 (unrealized -5.59, deadline 2024-01-03); unfilled at the data end: none.
- **sequence**: orders 327, fills 327; exits {'STOP': 130, 'TIME_EXIT': 125, 'TARGET': 69}; counters {'SKIP_DAILY_LIMIT': 58, 'SKIP_DUPLICATE_SYMBOL': 524, 'SKIP_RISK_LIMIT': 916, 'ambiguous_bar': 8, 'unresolved_end_of_data': 3}; unresolved at the data end: WNXMUSDT valued 783.68 at the close of 2023-12-31 (unrealized -29.34, deadline 2024-01-01); SUNUSDT valued 789.07 at the close of 2023-12-31 (unrealized -17.56, deadline 2024-01-03); WANUSDT valued 773.16 at the close of 2023-12-31 (unrealized -33.54, deadline 2024-01-04); unfilled at the data end: none.
- **shuffled**: orders 329, fills 327; exits {'TIME_EXIT': 134, 'TARGET': 69, 'STOP': 123}; counters {'SKIP_DAILY_LIMIT': 52, 'SKIP_DUPLICATE_SYMBOL': 526, 'SKIP_RISK_LIMIT': 918, 'ambiguous_bar': 5, 'unfilled_end_of_data': 2, 'unresolved_end_of_data': 1}; unresolved at the data end: SUNUSDT valued 837.70 at the close of 2023-12-31 (unrealized -18.65, deadline 2024-01-03); unfilled at the data end: PAXGUSDT (entry 2024-01-01), WNXMUSDT (entry 2024-01-01).

Paired comparisons (moving-block bootstrap of daily return differences, descriptive):

- sequence_minus_summary: end equity -15.03 USDT; summed daily return difference +0.01% (95% interval -13.89% to +15.02%)
- sequence_minus_shuffled: end equity -485.67 USDT; summed daily return difference -5.28% (95% interval -16.50% to +6.57%)
- summary_minus_shuffled: end equity -470.64 USDT; summed daily return difference -5.29% (95% interval -18.21% to +6.76%)
- sequence_minus_cash: end equity -1,062.54 USDT; summed daily return difference -10.56% (95% interval -33.29% to +12.43%)
- summary_minus_cash: end equity -1,047.51 USDT; summed daily return difference -10.57% (95% interval -29.49% to +8.86%)
- shuffled_minus_cash: end equity -576.87 USDT; summed daily return difference -5.28% (95% interval -26.97% to +16.20%)

## Scenario DELAY_AND_DOUBLE: entry delay 1 bar(s), fee 0.2% + slippage 0.2% per side

| Arm | End equity | Net return | Realized | Unrealized | Max drawdown | Closed trades | Win rate | Avg win | Avg loss | Expectancy | Profit factor | Fees | Slippage | Mean exposure | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| summary | 9,825.75 | -1.74% | -160.15 | -14.10 | -10.61% (2023-12-19) | 230 | +37.8% | 52.61 | -33.13 | -0.70 | 0.97 | 844.73 | 844.73 | +15.5% | 41.41 |
| sequence | 9,751.86 | -2.48% | -204.77 | -43.37 | -13.49% (2023-12-19) | 245 | +38.0% | 58.41 | -37.09 | -0.84 | 0.96 | 891.43 | 891.43 | +14.8% | 44.22 |
| shuffled | 9,881.98 | -1.18% | -66.83 | -51.19 | -13.52% (2023-12-19) | 242 | +37.2% | 59.38 | -35.60 | -0.28 | 0.99 | 908.54 | 908.54 | +14.9% | 43.59 |
| cash | 10,000.00 | +0.00% | 0.00 | 0.00 | +0.00% (2023-01-01) | 0 | - | - | - | - | - | 0.00 | 0.00 | +0.0% | 0.00 |

Exit reasons, skips, rejections and data gaps:

- **summary**: orders 233, fills 231; exits {'TIME_EXIT': 116, 'TARGET': 44, 'STOP': 70}; counters {'SKIP_DAILY_LIMIT': 20, 'SKIP_DUPLICATE_SYMBOL': 592, 'SKIP_RISK_LIMIT': 980, 'ambiguous_bar': 2, 'unfilled_end_of_data': 2, 'unresolved_end_of_data': 1}; unresolved at the data end: SUNUSDT valued 871.62 at the close of 2023-12-31 (unrealized -14.10, deadline 2024-01-04); unfilled at the data end: PAXGUSDT (entry 2024-01-01), JUVUSDT (entry 2024-01-01).
- **sequence**: orders 248, fills 247; exits {'STOP': 92, 'TIME_EXIT': 99, 'TARGET': 54}; counters {'SKIP_DAILY_LIMIT': 34, 'SKIP_DUPLICATE_SYMBOL': 530, 'SKIP_RISK_LIMIT': 1013, 'ambiguous_bar': 5, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}; unresolved at the data end: WNXMUSDT valued 855.16 at the close of 2023-12-31 (unrealized -24.38, deadline 2024-01-02); SUNUSDT valued 853.22 at the close of 2023-12-31 (unrealized -18.99, deadline 2024-01-03); unfilled at the data end: PAXGUSDT (entry 2024-01-02).
- **shuffled**: orders 245, fills 244; exits {'TIME_EXIT': 106, 'TARGET': 54, 'STOP': 82}; counters {'SKIP_DAILY_LIMIT': 26, 'SKIP_DUPLICATE_SYMBOL': 544, 'SKIP_RISK_LIMIT': 1010, 'ambiguous_bar': 2, 'unfilled_end_of_data': 1, 'unresolved_end_of_data': 2}; unresolved at the data end: SUNUSDT valued 875.69 at the close of 2023-12-31 (unrealized -19.49, deadline 2024-01-03); UTKUSDT valued 860.81 at the close of 2023-12-31 (unrealized -31.70, deadline 2024-01-04); unfilled at the data end: PAXGUSDT (entry 2024-01-02).

Paired comparisons (moving-block bootstrap of daily return differences, descriptive):

- sequence_minus_summary: end equity -73.89 USDT; summed daily return difference -0.64% (95% interval -15.39% to +13.24%)
- sequence_minus_shuffled: end equity -130.12 USDT; summed daily return difference -1.28% (95% interval -17.09% to +14.50%)
- summary_minus_shuffled: end equity -56.23 USDT; summed daily return difference -0.65% (95% interval -12.92% to +11.60%)
- sequence_minus_cash: end equity -248.14 USDT; summed daily return difference -2.05% (95% interval -20.55% to +16.26%)
- summary_minus_cash: end equity -174.25 USDT; summed daily return difference -1.41% (95% interval -19.26% to +15.97%)
- shuffled_minus_cash: end equity -118.02 USDT; summed daily return difference -0.76% (95% interval -21.71% to +20.77%)

## Checks on every arm and scenario

Invariants (no fill on or before its decision, exits after fills, no overspending, equity = start + realized + unrealized every day), the cross-check of cash, reservations and realized P&L against the US paper account's tested accounting, and a repeat run with an identical fingerprint: all passed, or the run would have stopped.

## Limits

- 2023 was studied before: development evidence, not validation. The 2024+ holdout was not read.
- Daily bars: a touched price is not a guaranteed fill; intraday order is unknown (stop-first when both levels are touched); no depth or queue position.
- Costs are assumptions. The universe is today's archive catalogue, so delisted coins are missing.
- One year and a few hundred decisions at most: no statistical certainty.

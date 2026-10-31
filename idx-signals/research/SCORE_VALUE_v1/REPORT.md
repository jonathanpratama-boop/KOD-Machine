# SCORE_VALUE_v1: what a score is worth, and whether the top-five order picks the wrong alerts

Ran 2026-10-31T15:52:09Z at commit `b319134f3b608af5292ededa907ea3a85478a8e9`. attribution study on 2023 (already-studied data), simulation only; not investable, not a strategy, no permission to buy; 2024 data never read; any threshold or priority rule the curves suggest is a hypothesis for a fresh period, not a result

113,365 early-population coin-days in 2023; 52,615 traded in isolation (predicted probability >= 5% under any arm, or shortlisted) with the frozen BASE rules.

## Verdicts (fixed rules, from the numbers)

- Calibration: overconfident at the top in neither arm. summary: shortlist predicted 12.0% vs realized 3.3%; sequence: shortlist predicted 12.0% vs realized 4.2%.
- Threshold curve: no threshold level reaches 1% mean net with 100 candidates in both arms.
- Timing: no consistent bad-timing effect (neither arm below zero). summary: admission days minus other days -0.30 pts (95% -1.02 to +0.41); sequence: admission days minus other days +0.01 pts (95% -0.77 to +0.77).
- Value: summary: EV +0.27% per alert = hit rate 3.3% x +7.2% + non-hits +0.03%; the predicted probabilities implied +0.89%; 1% per trade needs a hit rate of 13.6%; sequence: EV +0.44% per alert = hit rate 4.2% x +8.5% + non-hits +0.09%; the predicted probabilities implied +1.09%; 1% per trade needs a hit rate of 10.9%.

## summary

**A. Calibration on all candidates**

| Predicted p bin | Candidates | Mean predicted | Realized hit rate | Of which shortlisted | Isolated trades | Mean net |
|---|---:|---:|---:|---:|---:|---:|
| [0.0, 0.01) | 4806 | 0.6% | 0.3% | 0 | 0 | - |
| [0.01, 0.02) | 10745 | 1.5% | 0.7% | 0 | 3 | -1.04% |
| [0.02, 0.03) | 14749 | 2.5% | 1.0% | 0 | 14 | +0.24% |
| [0.03, 0.05) | 32643 | 4.0% | 1.6% | 13 | 2138 | +0.11% |
| [0.05, 0.075) | 29345 | 6.1% | 2.9% | 275 | 29079 | +0.31% |
| [0.075, 0.1) | 14041 | 8.6% | 5.3% | 598 | 13941 | +0.82% |
| [0.1, 0.15) | 6733 | 11.6% | 6.9% | 1700 | 6699 | +0.87% |
| [0.15, 0.2) | 296 | 16.0% | 4.7% | 247 | 295 | +0.27% |
| [0.2, 0.3) | 7 | 22.5% | 0.0% | 7 | 7 | +3.97% |

Shortlist: predicted 12.0%, realized 3.29% (3.34% of known). All candidates: predicted 5.03%, realized 2.50%.

**B. Global threshold curve (no daily budget)**

| p >= | Candidates | Days | Max/day | Hit rate | Closed | Mean net | Median net | Win rate | First-of-run n | First-of-run mean net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5.0% | 50422 | 365 | 274 | 4.1% | 50021 | +0.52% | -1.38% | 44.0% | 5350 | +0.61% |
| 7.5% | 21077 | 362 | 209 | 5.8% | 20942 | +0.83% | -0.75% | 46.3% | 3714 | +0.80% |
| 10.0% | 7036 | 345 | 126 | 6.8% | 7001 | +0.84% | -0.62% | 46.6% | 1762 | +0.77% |
| 15.0% | 303 | 113 | 14 | 4.6% | 302 | +0.35% | -0.90% | 45.0% | 157 | +1.23% |
| 20.0% | 7 | 7 | 1 | 0.0% | 7 | +3.97% | +9.67% | 57.1% | 7 | +3.97% |
| 30.0% | 0 | 0 | 0 | - | 0 | - | - | - | - | - |

**C. Admission timing**

Days the account admitted something: 209; days it admitted nothing: 156. All five alerts on admission days: mean net +0.15% (n 1045); on other days +0.45% (n 780); difference -0.30% (95% -1.02% to +0.41%). On admission days, admitted +0.10% vs skipped +0.17%.

**D. Rank anatomy**

| Rank | Mean predicted | Repeat share | Median vol20 | Median 20-day value | Admitted share | Hit rate | Mean net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 13.9% | 86% | 1.2% | 627,825 | 32% | 1.6% | -0.27% |
| 2 | 12.4% | 78% | 1.7% | 344,584 | 28% | 3.6% | +0.40% |
| 3 | 11.7% | 67% | 1.9% | 367,442 | 20% | 2.5% | +0.21% |
| 4 | 11.2% | 58% | 2.0% | 430,689 | 0% | 4.7% | +0.47% |
| 5 | 10.9% | 45% | 1.9% | 388,311 | 0% | 4.1% | +0.58% |

**E. Value accounting**

EV per alert +0.27% = 3.3% x +7.2% + 96.7% x +0.03%. The predicted probabilities implied +0.89%. A 1% net per trade needs a hit rate of 13.6%. At the account's size and this many alerts: 4,704 USDT a year.

## sequence

**A. Calibration on all candidates**

| Predicted p bin | Candidates | Mean predicted | Realized hit rate | Of which shortlisted | Isolated trades | Mean net |
|---|---:|---:|---:|---:|---:|---:|
| [0.0, 0.01) | 7063 | 0.6% | 0.3% | 0 | 14 | -0.45% |
| [0.01, 0.02) | 13843 | 1.5% | 0.6% | 0 | 18 | +1.83% |
| [0.02, 0.03) | 17321 | 2.5% | 1.2% | 0 | 65 | +0.94% |
| [0.03, 0.05) | 33463 | 4.0% | 1.7% | 21 | 10790 | +0.07% |
| [0.05, 0.075) | 25049 | 6.1% | 3.5% | 260 | 24790 | +0.43% |
| [0.075, 0.1) | 10966 | 8.6% | 5.8% | 729 | 10875 | +0.91% |
| [0.1, 0.15) | 5312 | 11.6% | 7.4% | 1538 | 5279 | +0.98% |
| [0.15, 0.2) | 337 | 16.3% | 4.7% | 281 | 334 | +0.14% |
| [0.2, 0.3) | 11 | 22.6% | 0.0% | 11 | 11 | -0.01% |

Shortlist: predicted 12.0%, realized 4.16% (4.23% of known). All candidates: predicted 4.54%, realized 2.50%.

**B. Global threshold curve (no daily budget)**

| p >= | Candidates | Days | Max/day | Hit rate | Closed | Mean net | Median net | Win rate | First-of-run n | First-of-run mean net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5.0% | 41675 | 365 | 265 | 4.6% | 41289 | +0.62% | -1.26% | 44.6% | 6021 | +0.51% |
| 7.5% | 16626 | 362 | 198 | 6.3% | 16499 | +0.92% | -0.73% | 46.6% | 3669 | +0.89% |
| 10.0% | 5660 | 339 | 129 | 7.2% | 5624 | +0.93% | -0.62% | 47.0% | 1734 | +0.75% |
| 15.0% | 348 | 129 | 24 | 4.6% | 345 | +0.13% | -2.73% | 42.6% | 186 | +0.59% |
| 20.0% | 11 | 11 | 1 | 0.0% | 11 | -0.01% | -5.28% | 45.5% | 8 | +1.12% |
| 30.0% | 0 | 0 | 0 | - | 0 | - | - | - | - | - |

**C. Admission timing**

Days the account admitted something: 217; days it admitted nothing: 148. All five alerts on admission days: mean net +0.45% (n 1085); on other days +0.44% (n 740); difference +0.01% (95% -0.77% to +0.77%). On admission days, admitted +0.13% vs skipped +0.58%.

**D. Rank anatomy**

| Rank | Mean predicted | Repeat share | Median vol20 | Median 20-day value | Admitted share | Hit rate | Mean net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 14.0% | 83% | 1.8% | 433,677 | 40% | 2.5% | +0.17% |
| 2 | 12.4% | 71% | 2.0% | 454,759 | 32% | 3.6% | +0.33% |
| 3 | 11.7% | 60% | 2.0% | 446,753 | 18% | 4.1% | +0.10% |
| 4 | 11.1% | 46% | 2.0% | 450,544 | 0% | 5.2% | +0.74% |
| 5 | 10.7% | 38% | 2.0% | 488,595 | 0% | 5.5% | +0.87% |

**E. Value accounting**

EV per alert +0.44% = 4.2% x +8.5% + 95.8% x +0.09%. The predicted probabilities implied +1.09%. A 1% net per trade needs a hit rate of 10.9%. At the account's size and this many alerts: 7,576 USDT a year.

## shuffled

**A. Calibration on all candidates**

| Predicted p bin | Candidates | Mean predicted | Realized hit rate | Of which shortlisted | Isolated trades | Mean net |
|---|---:|---:|---:|---:|---:|---:|
| [0.0, 0.01) | 6333 | 0.6% | 0.3% | 0 | 0 | - |
| [0.01, 0.02) | 12394 | 1.5% | 0.6% | 0 | 0 | - |
| [0.02, 0.03) | 16109 | 2.5% | 1.2% | 0 | 5 | +1.71% |
| [0.03, 0.05) | 33769 | 4.0% | 1.7% | 9 | 7814 | +0.17% |
| [0.05, 0.075) | 27481 | 6.1% | 3.4% | 241 | 27213 | +0.42% |
| [0.075, 0.1) | 11886 | 8.5% | 5.7% | 729 | 11781 | +0.75% |
| [0.1, 0.15) | 5213 | 11.5% | 7.2% | 1694 | 5183 | +0.96% |
| [0.15, 0.2) | 172 | 16.0% | 3.5% | 159 | 172 | +0.40% |
| [0.2, 0.3) | 8 | 22.9% | 0.0% | 8 | 8 | +0.95% |

Shortlist: predicted 11.6%, realized 4.11% (4.17% of known). All candidates: predicted 4.68%, realized 2.50%.

**B. Global threshold curve (no daily budget)**

| p >= | Candidates | Days | Max/day | Hit rate | Closed | Mean net | Median net | Win rate | First-of-run n | First-of-run mean net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5.0% | 44760 | 365 | 269 | 4.5% | 44357 | +0.57% | -1.33% | 44.2% | 5902 | +0.48% |
| 7.5% | 17279 | 364 | 189 | 6.1% | 17144 | +0.81% | -0.85% | 45.7% | 3724 | +0.81% |
| 10.0% | 5393 | 343 | 114 | 7.0% | 5363 | +0.94% | -0.55% | 47.2% | 1625 | +0.86% |
| 15.0% | 180 | 73 | 11 | 3.3% | 180 | +0.42% | -1.35% | 43.9% | 129 | +1.30% |
| 20.0% | 8 | 8 | 1 | 0.0% | 8 | +0.95% | -2.79% | 37.5% | 8 | +0.95% |
| 30.0% | 0 | 0 | 0 | - | 0 | - | - | - | - | - |

**C. Admission timing**

Days the account admitted something: 211; days it admitted nothing: 154. All five alerts on admission days: mean net +0.28% (n 1055); on other days +0.31% (n 770); difference -0.03% (95% -0.78% to +0.74%). On admission days, admitted +0.36% vs skipped +0.25%.

**D. Rank anatomy**

| Rank | Mean predicted | Repeat share | Median vol20 | Median 20-day value | Admitted share | Hit rate | Mean net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 13.4% | 83% | 1.5% | 454,762 | 35% | 2.2% | -0.11% |
| 2 | 12.0% | 71% | 1.9% | 451,344 | 34% | 3.6% | +0.18% |
| 3 | 11.4% | 61% | 1.9% | 458,858 | 19% | 4.4% | +0.58% |
| 4 | 10.9% | 44% | 2.1% | 444,967 | 0% | 5.5% | +0.09% |
| 5 | 10.5% | 37% | 2.0% | 437,753 | 0% | 4.9% | +0.73% |

**E. Value accounting**

EV per alert +0.29% = 4.1% x +7.3% + 95.9% x -0.01%. The predicted probabilities implied +0.84%. A 1% net per trade needs a hit rate of 13.8%. At the account's size and this many alerts: 5,033 USDT a year.

## Limits

- 2023 only, already studied; descriptive; the threshold curve is in-sample and selects nothing.
- Isolated trades overlap and ignore cash; their sums are not portfolio results.
- Daily bars and modelled costs.

# MSCI_DELETION_OPT_v1: holding-period study of the MSCI Indonesia deletion trade (EXPLORATORY)

Ran 2026-11-01T09:02:37Z at commit `4a73fe0a6170eec89edea8e85deb75ed3b95adc3` on the frozen protocol (`protocol.json`, sha256 `dd0c6a02b8b114c9...`). One run. Simulation only. **Exploratory:** every review here was inspected before; the sealed 2024 reviews were not computed. The two frozen studies' trade files reproduce: True.

## Verdict: EXPLORATORY_REJECT

| Gate | Result |
|---|---|
| W0_sample | PASS |
| W1_account | PASS |
| W2_net | FAIL |
| W3_vs_baseline | PASS |
| W4_blocks | FAIL |
| W5_winners | FAIL |
| W6_stress | FAIL |
| W7_incremental | PASS |
| W8_not_brittle | FAIL |

## Walk-forward choices (hold chosen on earlier reviews only; None = cash)

| Outer review | Training reviews | Chosen hold |
|---|---|---|
| Nov20 | 4 | 20 |
| Feb21 | 5 | 20 |
| May21 | 6 | 20 |
| Aug21 | 7 | 20 |
| Nov21 | 8 | 20 |
| Feb22 | 9 | 20 |
| May22 | 10 | 20 |
| Aug22 | 11 | 20 |
| Nov22 | 12 | 20 |
| Feb23 | 13 | 20 |
| May23 | 14 | 20 |
| Aug23 | 15 | 20 |
| Feb25 | 16 | 20 |
| May25 | 17 | 10 |
| Aug25 | 18 | 10 |
| Nov25 | 19 | 10 |
| Feb26 | 20 | 10 |
| May26 | 21 | 10 |
| Aug26 | 22 | 20 |

Most selected (reviews with a deletion; a tie with cash counts as cash): 20; counts {'20': 11, '10': 5}. Outer sample (W0, scored at every hold): 74 trades in 16 reviews. The hold the same procedure picks on all 23 reviews (in-sample; for a prospective protocol only): 5.

## Walk-forward against the baseline, cash and the market (19 outer reviews; Nov23 excluded)

| Rule | Trades | Mean net | Median | Win | Avg win | Avg loss | Payoff | Excess vs controls | Over liquid market | Account (IDR 160m start) | Max DD (review exits) | Exposure | Turnover/yr | Fees/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Walk-forward (base plan) | 74 | +1.49% | -1.27% | +43% | +14.66% | -8.54% | 1.72 | +3.95% | +4.92% | 191.7m (+19.8%) | -13.8% | +16.4% | 4.76 | +0.95% |
| Baseline: hold 20 (v1 rule) | 74 | -0.62% | -2.54% | +34% | +15.12% | -8.66% | 1.75 | +4.32% | +5.06% | 173.4m (+8.4%) | -18.3% | +19.6% | 4.80 | +0.96% |
| Walk-forward, S1_entry_next_session | 73 | -2.91% | -4.12% | +32% | +11.89% | -9.71% | 1.22 | +0.16% | +1.07% | 130.9m (-18.2%) | -31.0% | +17.3% | 5.10 | +1.02% |
| Walk-forward, S2_tick_cost | 74 | +0.43% | -2.06% | +38% | +15.68% | -8.85% | 1.77 | +3.99% | +4.97% | 172.0m (+7.5%) | -15.2% | +16.8% | 4.89 | +0.98% |
| Walk-forward, S3_double_fees | 74 | +1.08% | -1.67% | +39% | +15.70% | -8.34% | 1.88 | +3.93% | +4.90% | 183.9m (+14.9%) | -14.2% | +16.6% | 4.81 | +1.92% |
| Walk-forward, block dev_outer | 28 | +5.23% | -1.15% | +43% | +18.96% | -5.07% | 3.74 | +3.99% | +4.93% | 212.2m (+32.7%) | -6.0% | +15.2% | 3.73 | +0.75% |
| Walk-forward, block oot | 46 | -0.79% | -1.71% | +43% | +12.08% | -10.68% | 1.13 | +3.93% | +4.91% | 144.2m (-9.8%) | -13.8% | +20.8% | 7.77 | +1.55% |

W3 accounts (outer reviews): walk-forward 191.7m, baseline 173.4m. Walk-forward without its best review (Nov20): 162.0m. P&L without the 3 largest winners: -33.8m. W2's review-cluster bootstrap one-sided 95% lower bound of the mean net trade return: -3.77% (16 clusters).

Benchmarks: cash 0%. Equal-weight liquid IDX market held through each block (rebalanced every 20 sessions, costs once in and out): development outer -13.0% (2020-11-30 .. 2023-11-30), out of time +18.5% (2025-02-28 .. 2026-10-06), fully invested throughout.

## Every fixed hold as a rule (base plan), on all 23 reviews, the 19 outer reviews and per block

| scope | hold | scored | mean_net | median_net | win_rate | mean_excess_vs_controls | mean_mkt_adj | account_return | max_dd_at_review_exits |
|---|---|---|---|---|---|---|---|---|---|
| all_23 | 1 | 93 | +3.32% | +2.67% | +75.27% | +3.06% | +3.12% | +39.43% | -1.52% |
| all_23 | 2 | 93 | +3.87% | +3.46% | +67.74% | +4.19% | +4.45% | +41.16% | -5.46% |
| all_23 | 3 | 93 | +4.88% | +3.96% | +69.89% | +5.47% | +5.65% | +56.25% | -4.35% |
| all_23 | 5 | 93 | +7.27% | +3.50% | +64.52% | +7.96% | +8.16% | +75.72% | -6.43% |
| all_23 | 10 | 93 | +7.84% | +3.39% | +64.52% | +7.90% | +8.37% | +80.86% | -6.59% |
| all_23 | 20 | 93 | +4.63% | -0.69% | +46.24% | +7.67% | +8.37% | +48.01% | -17.70% |
| dev_outer | 1 | 28 | +2.44% | +1.52% | +71.43% | +2.54% | +2.53% | +15.28% | -0.55% |
| dev_outer | 2 | 28 | +3.44% | +2.63% | +67.86% | +3.08% | +2.89% | +21.85% | -1.07% |
| dev_outer | 3 | 28 | +4.23% | +2.76% | +75.00% | +3.33% | +3.58% | +27.03% | -0.83% |
| dev_outer | 5 | 28 | +4.23% | +2.05% | +67.86% | +3.43% | +3.35% | +27.43% | -1.73% |
| dev_outer | 10 | 28 | +2.87% | +1.32% | +53.57% | +2.41% | +1.95% | +18.48% | -8.11% |
| dev_outer | 20 | 28 | +5.23% | -1.15% | +42.86% | +3.99% | +4.93% | +32.66% | -6.03% |
| oot | 1 | 46 | +3.54% | +3.74% | +76.09% | +3.40% | +3.64% | +17.95% | -1.57% |
| oot | 2 | 46 | +1.64% | +1.74% | +63.04% | +3.94% | +4.44% | +10.66% | -1.72% |
| oot | 3 | 46 | +2.44% | +2.79% | +63.04% | +5.52% | +5.86% | +14.99% | -2.84% |
| oot | 5 | 46 | +0.98% | +1.82% | +54.35% | +6.67% | +6.93% | +12.43% | -6.79% |
| oot | 10 | 46 | +4.16% | +1.40% | +60.87% | +5.29% | +6.59% | +14.57% | -3.75% |
| oot | 20 | 46 | -4.19% | -5.05% | +28.26% | +4.53% | +5.14% | -19.05% | -19.05% |
| outer_19 | 1 | 74 | +3.12% | +2.45% | +74.32% | +3.08% | +3.22% | +35.38% | -1.37% |
| outer_19 | 2 | 74 | +2.32% | +2.31% | +64.86% | +3.61% | +3.85% | +34.02% | -1.52% |
| outer_19 | 3 | 74 | +3.12% | +2.76% | +67.57% | +4.69% | +5.00% | +45.01% | -2.38% |
| outer_19 | 5 | 74 | +2.21% | +2.05% | +59.46% | +5.44% | +5.58% | +42.53% | -6.58% |
| outer_19 | 10 | 74 | +3.67% | +1.40% | +58.11% | +4.20% | +4.83% | +35.83% | -8.11% |
| outer_19 | 20 | 74 | -0.62% | -2.54% | +33.78% | +4.32% | +5.06% | +8.38% | -18.30% |

The full trial log (every plan x hold x scope, and the walk-forward under every plan) is `run/TRIALS.csv`.

## What this does and does not show

- Exploratory: the holding-period lever was suggested by data already seen; the walk-forward only disciplines the choice, it does not validate it.
- Closing-auction fills are modelled; prices after 2025-02-21 are Yahoo-sourced; drawdown is at review exits.
- Trade statistics use trades with matched controls; exposure (nominal hold), turnover and fees use every trade the account held; fees exclude the S2 tick; capital per review averages over reviews that traded; 'over liquid market' is the return relative to an equal-weight liquid basket that cannot be shorted, not a hedged return.
- No stop; no result here is a guaranteed maximum loss or a forecast. No live promotion follows from it.

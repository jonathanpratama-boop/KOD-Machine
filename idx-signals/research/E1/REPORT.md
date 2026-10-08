# E1 results (protocol KOD-IDX-E1-v1)

Historical research on IDX TIER_1 data. Nothing here is prospective performance, and the
100-event pilot does not establish predictive power. The holdout (2024-01-02 .. 2025-02-21)
has not been touched.

Order of events, each a pushed commit (so GitHub's own run records date them):
`1f997f7` protocol and code → `29e32e4` discovery results + D1 frozen →
`a78ce92` validation results (+ D1 v1.1, a crash fix with identical flags) →
`573e98b` trading run on the validation window.

## Base rates (eligible ticker-days, non-winners included)

| Period | Ticker-days | +30% in 5 sessions | +50% | +100% | Episodes 30 / 50 / 100 |
|---|---:|---:|---:|---:|---|
| Discovery 2021-01-22..2022-12-22 | 323,324 | 1.88% | 0.63% | 0.098% | 1,511 / 577 / 114 |
| Validation 2023 | 179,617 | 1.16% | 0.35% | 0.030% | 569 / 198 / 23 |

By price band, +30% rates fall with price (discovery: 2.6% for ≤Rp200, 1.6% for ≤Rp5,000,
1.0% above; validation 1.5%, 1.0%, 0.4%). 2021 (2.5%) was twice as active as 2022 (1.3%).
Files: `discovery/base_rates.csv`, `validation/base_rates.csv`, `*/episodes_E*.csv`.

## The first 100 events and their matched controls

`discovery/first100_events.csv`: the first 100 +30% episodes, 2021-01-22 .. 2021-02-24,
88 names (51 priced ≤Rp200), every value as of the decision close. 11 went on to +50%,
none to +100%; 97 had an executable entry the next session. `first100_controls.csv`: five
same-session non-events each from the same price band, liquidity and market-cap quintile
(460 exact, 40 with market cap relaxed). `all_E30_controls.csv` does the same for all 1,511
discovery episodes.

## Weak signals at the episode start (`discovery/signal_stats.csv`)

Matched-set AUC (0.5 = no information), all 1,511 discovery episodes:

| Signal | AUC (95%) | Reading |
|---|---|---|
| 20-session volatility | 0.68 (0.66-0.70) | moonshots come from names that were already moving a lot |
| turnover, traded value | 0.53-0.54 | slightly more active names |
| volume / value / trade-count surge that day | 0.50 | no information on the start day |
| ARA lock, 60-session breakout, IGNITION daily analogue | 0.49-0.50 | almost never on the start day |
| day return, close location, 60-session drawdown | 0.37-0.42 | starts tend to be down closes (partly the definition: a lower base makes the forward ratio bigger) |

The first-100 sample agrees (volatility 0.67) with wider intervals. On the day before a
repricing begins, the tape mostly looks ordinary.

## Detector D1 (pre-registered selection on discovery)

All ten family rules were admissible; F1_ARA (close locked at ARA) had the highest lift:
1,673 flags, +30% precision 23.6% (Wilson lower bound 21.6%), 12.5x the base rate
(`discovery/detector_selection.csv`). It is a continuation detector: ARA closes fall inside
repricings that have started, not before them.

## Validation 2023 (`validation/result.json`, `validation/flags.csv`)

**Discovery skill: yes.** 972 flags. Precision at +30%: 18.3% (16.0-20.9%) vs a 1.16% base
rate (15.8x) and vs 1.96% for matched random names on the same sessions (9.3x, one-sided
p = 0.005, the floor at 200 draws). +50%: 7.3% (11.7x matched). +100%: 0.9% (12x).

**Coverage: low.** It caught 9.8% of the 569 +30% episodes before their peak (16.7% of +50%,
35% of +100%), a median 2 sessions ahead. 794 of 972 flags (82%) were false alerts.

**Execution: no.** 66% of flags had an executable entry at the next close; the median gain
still capturable from that entry was 0.0%, and only 4.7% of executable flags still had +30%
left. Through the harness (`results/runs/20261008T000401Z_MOONSHOT_E1_D1_v1.1`: lots, fees,
ARA/ARB, corporate-action registry), buying at the next close and holding 5 sessions averaged
**-4.06% net per trade vs -0.53% for matched random entries** (hit rate 28% vs 39%; worse than
every one of 200 draws). 339 of 1,042 attempts could not be filled because the name was still
locked at ARA: those are the continuations that run. The fills that do happen are mostly the
moves that are fading.

## What this means for decisions

D1 sees repricings in progress better than chance, but the obvious way to act on it loses
money. The paper policy therefore passes on D1 candidates (`paper/`), recording each one with
its plan so the counterfactual is scored. Any new execution variant (earlier entry, a
pullback trigger, a different exit) must be designed on discovery data only and then judged
prospectively, because validation has been used and the holdout is reserved for one final test.

# PATH_HISTORY_v1: result (one look, 2026-10-29)

Protocol `protocol.json` with addenda 1-3, all written before this result was read. Built by `build2.py`, scored once
by `evaluate2.py`; every number below is in `results/RESULT.json`. Counted trial `PATH_HISTORY_v1_result.json`
(the result of the PENDING registration `PATH_HISTORY_v1.json`: one trial).

**Question.** Among the Speculation Register's own spiking stocks, does a model fitted on earlier years tell apart, on
later years, the ones that make the move on their own (a *twin-filtered path*: the stock crossed the barrier and
fewer than half of its twins did)? Which free feature blocks add discrimination?

**Events.** 14,561: US 6,225 (+30% days, 2020-2023), crypto 1,720 (2020-2023), IDX 6,616 (ARA closes at Rp50 or more:
3,136 in 2019-07..2023 and 3,480 in 2025-02-24..2026-10). Fitted on 8,925 events up to 2022-12-31, scored on 5,636
from 2023 on. The sealed periods were cut out before any market was built.

## Decision (block P1, Holm over the four primary statements, AUC within each market)

| Primary statement | Test n | AUC [95%] | Brier gain over the base rate [95%] | Verdict |
|---|---:|---|---|---|
| DUMP10_5: the 5-session plan loses 10% or more, on its own | 3,918 | 0.578 [0.558, 0.597] | +0.0013 [-0.0025, +0.0051] | LEARNABLE (ranking clear; the Brier gain's interval includes zero) |
| PUMP30_5: a close 30% higher within 5 sessions, on its own | 5,636 | 0.560 [0.539, 0.581] | -0.0009 [-0.0047, +0.0034] | NOT LEARNABLE with these features (ranks, but the base rate shifted and the Brier gain is negative) |
| NEXT_DUMP10: the next session closes 10% lower, on its own | 5,636 | 0.567 [0.537, 0.599] | +0.0034 [+0.0016, +0.0051] | LEARNABLE |
| NEXT_LOSES: the next session does worse than the twins' median | 5,636 | 0.626 [0.606, 0.644] | +0.0119 [+0.0081, +0.0155] | LEARNABLE |

Holm-adjusted p for AUC <= 0.5 is 0.002 for all four (cluster bootstrap over signal weeks, 2,000 resamples). AUC and
the Brier gain are reported apart on purpose: for PUMP30_5 the model ranks (AUC 0.56) but the base rate rose from
training to test (IDX 0.21 to 0.28), so the anchor is miscalibrated and the Brier gain is negative.

## By market (block P1 unless stated; crypto has only 268 test events)

| Statement | US | IDX 2023 + 2025-26 | IDX 2025-26 alone | Crypto |
|---|---|---|---|---|
| DUMP10_5 | 0.591 (E_US 0.600 [0.566, 0.632]) | 0.571 | 0.570 | 0.623 |
| NEXT_DUMP10 | 0.611 (E_US 0.627 [0.590, 0.661]) | 0.550 | 0.583 | 0.675 |
| NEXT_LOSES | 0.535 (E_US 0.555) | 0.639 | 0.636 | 0.657 |
| PUMP30_5 | 0.551 (E_US 0.560) | 0.560 | 0.557 | 0.661 |
| NEXT_RUN10 (secondary): the next session closes 10% higher, on its own | 0.558 | 0.705 | 0.705 | 0.632 |

The 2025-26 IDX segment is a different regime (far more ARA days, price limits restored in stages) and the model
holds there: the best news for robustness in this study.

## What each block adds (paired delta AUC over P0, 95% interval)

| Block | DUMP10_5 | PUMP30_5 | NEXT_DUMP10 | NEXT_LOSES | NEXT_RUN10 |
|---|---|---|---|---|---|
| P1 (more price features) | +0.031 [+0.013, +0.048] | +0.068 [+0.045, +0.090] | -0.094 [-0.133, -0.050] | -0.016 [-0.029, -0.004] | +0.019 [+0.009, +0.030] |
| CONTEXT (P1 plus the context prior) | +0.036 [+0.017, +0.054] | +0.067 [+0.045, +0.089] | -0.094 [-0.135, -0.048] | -0.014 [-0.027, -0.002] | +0.019 [+0.009, +0.029] |
| E_US over P1, US rows only | +0.009 [-0.006, +0.024] | +0.009 [-0.020, +0.039] | +0.015 [+0.001, +0.029] | +0.020 [+0.002, +0.038] | -0.023 [-0.050, +0.007] |

- **The context prior (the keyboard's next-letter idea) adds nothing beyond P1.** Its delta equals P1's within
  0.005 everywhere. In this coarse form the dictionary knows nothing the logistic model does not.
- **P1 is not uniformly better.** It helps the 5-session statements and hurts NEXT_DUMP10, where the damage is on
  IDX: that label was almost impossible in training (2.6%, a -7% lower limit for most of 2020-2023) and 9.8% in
  the test years, and 17 features with market deviations overfit the 150 training positives; P0's seven did not.
- **EDGAR and FINRA (E_US) add a little, on the next-day statements only**: +0.015 and +0.020 AUC, just significant;
  nothing on the 5-session pump or on NEXT_RUN10. Coverage: filings read for 96% of US events, short-sale volume
  for 64%, share counts for 68%; an 8-K on the previous session or the spike day for 27%; an offering filing in
  the previous 90 days for 30%; a 424B5 in the previous year for 25%; a reverse split in the previous year for 11%.

## What drives a US dump (standardised coefficients, E_US model)

| | DUMP10_5 | NEXT_DUMP10 |
|---|---|---|
| volatility before the spike | +0.25 | +0.24 |
| spike in units of that volatility | +0.09 | +0.22 |
| opening gap (the move came at the open) | -0.20 | -0.25 |
| an 8-K that day or the day before | -0.12 | -0.12 |
| had already run over 5 sessions | +0.21 | - |
| shares outstanding (log) | +0.14 | +0.18 |
| abnormal short-sale share that day | +0.12 | - |
| the market's own move that day | - | -0.24 |
| spikes on the market that day | - | +0.15 |

The picture is coherent and in the direction the literature on information-less price shocks predicts: a spike that
came during the day rather than at the open, with no filing behind it, in a stock that was already volatile and
already running, on a day when many stocks spiked, tends to give it back. A gap with a filing behind it tends to
hold.

## Speed, descriptive (gate simulations in `sims/`, idealised learner)

- NEXT_DUMP10 in the US at AUC about 0.63 and 7-10 forecasts a session: the daily-block gate opens at its 30-session
  floor in most runs at AUC 0.66, and in a median of about 66 sessions at AUC 0.61 (`daily_gate.py`, 10 a day). Read:
  **about 2-3 months of live data**, if the live skill matches history, with 6 weeks as the floor.
- DUMP10_5 in the US at AUC about 0.60 and 35-50 forecasts a week: the weekly gate at AUC 0.61 and 50 a week opens
  in 68% of runs by week 30 and 98% by week 52 (`gate_power2.py`). Read: **about 7 months**.
- A pump headline would be slower: PUMP30_5's US AUC is 0.55-0.56 and its Brier gain negative.

## What this does not show

- Any live skill. It is history, fitted on one period and scored on another; it licenses one challenger, not a claim.
- Money. No return beyond the twins was tested here; a dump forecast is not a short trade.
- The worst dumps. US prices are survivor-only; delisted names are absent, so the true dump rate is higher and the
  signal may differ.
- Stability of the Brier gains: the base rates moved between the periods, and the anchor is the training rate.
- Crypto: 268 test events; the intervals are wide.
- The feature flags are what they say: an 8-K is an 8-K, a 424B5 is a 424B5, FINRA's short share includes market
  makers.

## Use

The headline for the one live challenger (LEARNER v2.3), decided here before any live outcome exists: **US +30%
stocks, NEXT_DUMP10** (the fastest clock and the best-discriminated dump statement), with DUMP10_5 as its companion.
The challenger carries blocks P1 and E_US; the context prior is not carried. IDX next-session continuation
(NEXT_RUN10, AUC 0.705, regime-robust) is the strongest discrimination in the study and is recorded as the next
candidate, not opened now. Nothing here changes a live ledger, prior, twin draw, family rule or frozen protocol.

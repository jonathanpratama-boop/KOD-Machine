# TA_HISTORY_v1: result (one look, 2026-10-29)

Protocol `protocol.json`, run once by `run.py`; every number below is in `results/RESULT.json`. Counted trial
`TA_HISTORY_v1_result.json`, the result of the PENDING registration `TA_HISTORY_v1.json` (one trial).

**Question.** On US stocks that just closed 30% or more higher (6,225 events, 2020-2023), do the indicators with
the best published evidence (RESEARCH) or the popular chart indicators (CHART) add out-of-time discrimination to
LEARNER v2.3's own 29 features? Fit 2020-21 and score 2022; fit 2020-22 and score 2023.

## Decision (Holm over four, paired AUC gain over v2.3's features, Brier gain beside it)

| Block | Statement | AUC: v2.3 features -> with the block | Gain [95%] | 2022 | 2023 | Brier gain | Verdict |
|---|---|---|---|---|---|---|---|
| CHART | next session closes 10% lower, on its own | 0.605 -> 0.623 | +0.018 [+0.011, +0.026] | +0.013 | +0.022 | +0.0027 | **ADDS** (Holm p 0.002) |
| CHART | 5-session plan ends 10% down, on its own | 0.604 -> 0.614 | +0.010 [+0.002, +0.018] | +0.020 | +0.004 | +0.0011 | **ADDS** (Holm p 0.021) |
| RESEARCH | next session | 0.605 -> 0.602 | -0.003 [-0.007, +0.001] | -0.004 | -0.002 | -0.0003 | does not add |
| RESEARCH | 5 sessions | 0.604 -> 0.603 | -0.001 [-0.003, +0.001] | -0.001 | -0.001 | +0.0000 | does not add |

## What carries it

Stochastic %K(14) carries the CHART block. Its standardised coefficient is -0.20 to -0.28 in every fold and for both
statements; Bollinger %B, MACD and RSI are small and change sign. On a +30% day the 14-session high is usually that
day's own high, so %K measures how far below the top of its recent range the stock closed after the spike. A spike
that closes well off its high, or one that only climbs back into a range it fell from, tends to be given back. The
v2.3 features already hold the close's place in the day's own range and the distance from the 120-session high;
%K adds on top of them.

The research indicators are built for other horizons and populations: monthly returns of ordinary stocks across a
cross-section. For a spiking stock the next day, they carry nothing that v2.3 does not already have. The 12-month
pair also exists for only 54-56% of events (the panel starts in 2020). The lottery effect is already in the
population itself: every one of these stocks just had its MAX day.

## What it does not show

- **Live skill.** This is history.
- **A large edge.** The gain is +0.010 to +0.018 AUC.
- **A clean second year.** 2023 already chose v2.3's features. 2022 chose nothing, and the gain holds there.
- **Survivor-free prices.** US prices are survivor-only, as in every US history study here.
- **That Stochastic "works" in general.** It is one input that helps this one question.

## Use

Per the protocol, CHART is a candidate for a separately frozen challenger; RESEARCH stays out. v2.3 had sealed no
forecast when this result was read. The decision on how CHART enters is recorded separately.

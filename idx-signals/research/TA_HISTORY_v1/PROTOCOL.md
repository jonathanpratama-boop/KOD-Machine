# TA_HISTORY_v1: do the indicators with the best published evidence, or the popular chart ones, add anything?

Frozen 2026-10-29, before any indicator was computed for any event. `protocol.json` is normative; `run.py` is the one
run, committed with the protocol.

**Question.** On US stocks that just closed 30% or more higher (the 6,225 events of 2020-2023 that are LEARNER v2.3's
warm start), do two blocks of indicators add out-of-time discrimination to v2.3's own 29 features?

- **RESEARCH**, the price indicators with the strongest published evidence:
  - the largest single-day return in the previous 20 sessions (the lottery effect, Bali, Cakici & Whitelaw 2011);
  - nearness to the 52-week high (George & Hwang 2004);
  - 12-month momentum skipping the last month (Jegadeesh & Titman 1993).
- **CHART**, the popular ones: RSI(14), the MACD histogram, Stochastic %K(14), Bollinger %B(20, 2).

The question is asked for v2.3's headline statement (the next session closes 10% lower, on its own) and its
companion (the 5-session plan ends 10% down, on its own).

**Out of time, twice.** Fit on 2020-2021 and score 2022; fit on 2020-2022 and score 2023. 2023 already chose
v2.3's features in PATH_HISTORY_v1, which can only favour the baseline. 2022 chose nothing.

**Decision.** A block adds for a statement when its paired AUC gain over the baseline survives Holm over the four
tests at 5% (bootstrap over signal weeks) and its Brier score improves too. Otherwise it does not add. A block that
adds becomes a candidate for a separately frozen v2.4; v2.3 is not touched either way.

# LEARNER_v2, addendum 4: v2.4, the challenger with the chart block

Written 2026-10-29 at about 15:45 UTC, before any set the challenger can forecast existed and before KOD-LEARNER-v2.3
sealed any forecast: `paper/learner_v3.jsonl` does not exist. `protocol_v2_4.json` (KOD-LEARNER-v2.4) supersedes
`protocol_v2_3.json` for the one live challenger. v2.2 is untouched and keeps running as monitoring.

**Why.** The owner asked whether technical-analysis indicators are worth including. `research/TA_HISTORY_v1` put
two blocks to one pre-registered look, rolling origin, scored on 2022 and 2023:

- **The chart block adds** to both of the challenger's statements:
  - next-session own dump: AUC 0.605 -> 0.623, Holm p 0.002, positive in both years;
  - 5-session own dump: +0.010, Holm p 0.021.

  Stochastic %K carries it: a spike that closes well below the top of its 14-session range tends to be given back.
- **The research-backed block adds nothing** (the lottery MAX, nearness to the 52-week high, 12-1 momentum), so it
  stays out.

By that study's rule, a block that adds is a candidate for a separately frozen challenger. v2.3 had sealed nothing,
so one challenger with the block replaces it, rather than two competing claims on the same question.

**What changes.**
- Four features, computed inside v2.3's 120-session window and on one frozen scale (`protocol_v2_4.json`
  `features.CHART`): RSI(14), the MACD histogram, Stochastic %K(14) and Bollinger %B.
- The warm start: `warmstart_v4`, the same 6,225 events with the four columns added. Its 29 v2.3 columns are
  identical, checked to 0.0.
- The registration: v2.3's is recorded as superseded (`LEARNER_v2_3_NEXT_DUMP_superseded.json`) and v2.4's is
  `LEARNER_v2_4_NEXT_DUMP_registered.json`.

**What does not change.** The question, the statements, the population, the other 29 features, the benchmark, the
model and its penalties, the anchor, the gate, the claim and its looks, verify, the ledger
(`paper/learner_v3.jsonl`), the routine step and everything v2.3 never does.

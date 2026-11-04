# PATH_HISTORY_v1: can the machine tell, from history, which spiking stocks pump, dump or fade on their own?

Frozen 2026-10-29, before any outcome of any event in it was computed. The normative details are in `protocol.json`.

**Why.** The owner asked for a speedrun: "we cannot afford to make it that long". The live learner can earn
confidence only as fast as live outcomes arrive. History can answer the first question now, in days: is there anything
to learn, and which free data helps? This study does not replace the live record, and it changes nothing live.

## What is tested

- **Events.** Every past stock the Speculation Register's own detectors would have flagged:
  - US and crypto: a day of +30% or more;
  - IDX: a close locked at the upper limit (ARA), at Rp50 or more.

  The feasibility count, which reads no outcome: US 6,225 events (2020-2023), crypto 1,720 (2020-2023), IDX 3,136
  (2019-07 to 2023) and 3,480 (2025-02-24 to 2026-10).
- **Sealed data.** The sealed periods (US and crypto 2024 onward, IDX 2024-01-02 to 2025-02-21) are cut out of the
  panels before anything is computed.
- **Twins.** Five per event, drawn exactly as the live register draws them.
- **Statements.** "On its own" means fewer than half of the twins did the same.
  - Primary:
    - DUMP10_5: the 5-session plan loses at least 10%, on its own;
    - PUMP30_5: a close at least 30% higher within 5 sessions, on its own;
    - NEXT_DUMP10: the next session closes at least 10% lower, on its own;
    - NEXT_LOSES: the next session does worse than the twins' median.
  - Secondary: PUMP_AND_DUMP_5, PUMP30_20, PUMP100_20, NEXT_RUN10, BEATS_TWINS_5.
- **Out of time.** Fitted on events up to 2022, scored once on 2023, and for IDX also on 2025-2026.
- **Model.** The learner's own form: penalised logistic regression with shared slopes, market deviations and the
  learner's penalties. Nothing is tuned.

## Feature blocks

| Block | What it adds |
|---|---|
| P0 | the learner's current price features |
| P1 | gap, volatility, price level, earlier spikes, up-streak, distance from the 52-week high, listing age, how many stocks spiked that day, the market's move; IDX: consecutive ARA days |
| E_US | EDGAR and FINRA, all published before the entry open: news (an 8-K that day), a recent offering, a shelf, an at-the-market program, a reverse split, short volume, turnover against shares outstanding |
| CONTEXT | the keyboard idea: what followed the same context in training (earlier spikes, streak, gap, news, offering), as a smoothed frequency, the way a phone keyboard guesses the next letter from the letters before it |

## Decision

A primary statement is **LEARNABLE** when the P1 model's out-of-time AUC is above 0.5 after Holm over the four,
and its Brier score beats the anchor (the base rate). Otherwise it is **not learnable with these features**. That is a
statement about these features, not about the goal. A block adds when its paired AUC gain is above zero with 95%
confidence. Each learnable statement's AUC is translated into the time the live learner would need to earn
confidence, using the gate simulations committed with this study.

## What it is for

The design of LEARNER v2.3: which feature blocks enter, and a warm start for the pump and dump statements from these
events. v2.3 is frozen separately and judged on its own prospective record. Nothing here changes a ledger, prior,
twin draw, family rule or frozen protocol.

## What it cannot show

That anything makes money, and that the history holds without survivorship. US prices are survivor-only, and the
worst dumps are among the delisted names. The full list of limitations is in `protocol.json`.

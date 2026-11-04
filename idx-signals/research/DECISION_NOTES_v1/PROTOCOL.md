# DECISION_NOTES_v1: a source-cited judgment beside a sealed prediction

Frozen 2026-10-29. Owner instruction: the Harry-lens review of 2026-10-29 (the owner's paste; its bounded
recommendation: "use one already registered event to demonstrate the six-step reasoning above in a source-cited
decision note. Choose by a rule established before looking at its subsequent return, disclose the actual analysis
time, and keep the note separate from the original sealed prediction. Do not rewrite the existing cohort using the new
judgment.").

## What a note is

A `NOTE.md` in `research/DECISION_NOTES_v1/<date>_<set_id>/`, written about one set that the Speculation or Catalyst
Register has already sealed. It answers six questions from sources it names, states what is unknown, and records its
own predictions so they can be scored. `research/` is append-only, so a committed note cannot be edited; a correction
is a new file. The note never becomes an input to any family, rule, prior, twin draw or resolution: the sealed set stays
independently scoreable exactly as sealed.

## Selection rule

Every note names the rule that chose its set, written before any outcome of that set could be seen. The first note's
rule, fixed in this file: **the first FIRE set of the first counted US family in `paper/catalysts.jsonl`**, which is
`CAT-SEC13D-0000921895-26-002864` (BKU). Later rules are written into this directory before the note they govern.

## The six questions (from the owner's paste, kept verbatim in spirit)

1. What changed, who can act on it, and when was it knowable? Completed transactions are separated from possible
   future actions and from descriptive filing language.
2. What economic consequence could follow for the security we can buy, and what could prevent it? Enterprise value,
   claims, dilution, minority value and temporary flows are kept apart. Missing quantities stay unknown.
3. What does the available price already appear to assume? Observable reactions and stated ratios only; no invented
   consensus.
4. What remains for us after feasible entry, costs and adverse scenarios, on the register's own plan?
5. Does the trade fit the mandate (the owner's 1 to 5 session horizon with a planned stop at most 5% from entry,
   PAPER-POLICY-v5's constraint in `idxsig/paper.py`)? A research yardstick that succeeds does not satisfy the mandate
   by itself; that would be a new, deliberate mandate decision.
6. What observable development would prove the explanation wrong, by what date, from what source?

## Timing disclosure

The note records the UTC time its analysis started and ended, whether the set's entry had already happened, the last
price it could see, and each source with its retrieval time. A fact the author could not read from a source it names is
marked unverified or unknown, never filled.

## Predictions and scoring

- **Actor predictions**: statements about what the actor or issuer will do, each with a probability, a resolution date
  and the public source that resolves it (EDGAR forms, the issuer's 8-Ks). Scored by that date from that source,
  in a new file `SCORE.md` in the same directory, by the Brier score.
- **Price view**: the note's own probability for each of the sealed set's cone statements. Scored when the register
  resolves the set, against the register's outcome, beside the family prior the set carries. The sealed set's prior and
  outcome are not changed by the note.
- **Mandate view**: the note's probability that a 1 to 5 session trade under the mandate would have made money, scored
  from the same bars the register uses, in `SCORE.md`.

No note is a counted trial. Whether this judgment adds anything is a later question, answered only by at least 20
scored notes compared with their sets' family priors on the same statements, pre-registered before that reading.

## Forbidden

Editing a sealed record or a committed note; choosing a set after seeing any of its outcomes; using a note's content in
any register, family, prior or twin draw; placing or simulating an order; filling a missing number.

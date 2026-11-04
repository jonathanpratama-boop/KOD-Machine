# LEARNER_v2, addendum 1: v2.1, graded on its thesis, pump and dump included

Written 2026-10-29, before any outcome and before any LEARNER_v2 forecast. No RESOLUTION record exists in
`paper/catalysts.jsonl` or `paper/speculations.jsonl`, and `paper/learner_v2.jsonl` does not exist yet. `protocol.json`
(KOD-LEARNER-v2) was committed in 8b4ba63 and sealed nothing. `protocol_v2_1.json` (KOD-LEARNER-v2.1) supersedes it
and is now normative. `PROTOCOL.md` still explains everything v2.1 keeps.

Owner, after v2 was frozen:

> "I dont care if its gonna be a pump and dump. I just care if it gets it right, and its thesis on even a pump and dump
> or whatnot is right."

## What changes

1. **Pumps and dumps become skill statements (a fourth kind, PATH).** v2 treated every raw move (RUN30, FADE10,
   DOUBLE, GAIN0) as market-driven: anchor only, never learned. v2.1 keeps that for the raw moves and adds each move's
   **own** version. Each counts only when fewer than half of the stock's matched twins made the same move; the
   register records that rate at every resolution.
   - `PUMP30_k`: it closed at least 30% above the signal close within k sessions.
   - `PUMP100_k`: it doubled.
   - `DUMP10_k`: its plan lost at least 10%.
   - `PUMP_AND_DUMP_k`: it spiked at least 30%, its plan still ended at least 10% down, and each move was its own.

   A rising market cannot make these true, so the original requirement still holds: no credit for being lucky that
   it's going up. A pump the stock made on its own is now something the machine can call and be credited for.
2. **Every call states its thesis.** The thesis is the statement in words, for example "a pump and dump: it closes at
   least 30% above the signal close within 5 sessions and its plan still ends at least 10% down, each when most of its
   twins do not". The thesis is sealed with the call. A BACK is graded:
   - **RIGHT** only when the whole thesis came true;
   - **PARTLY** when some part did, for example it pumped but never dumped;
   - **MARKET_MADE_IT** when the move happened but most twins made it too (no credit);
   - **WRONG** otherwise.
3. **The Speculation Register's sets are read too**, as families SPEC_IDX, SPEC_US and SPEC_CRYPTO. These are the
   scanner's daily +30% movers, where pumps and dumps happen. Their priors are the speculation protocol's frozen
   per-market numbers, and they add many outcomes a week to learn from.
4. **The claim pools the four kinds.** It is registered as `research/QUANT_GRADE/trials/LEARNER_v2_1_BRIER_registered.json`.
   v2's registration is recorded as superseded and was never looked at.

## What does not change

The anchor (a climatology twin), the centring on the live population, the hierarchical model and its priors, the warm
start (file, hash, cap), the time-uniform confidence gate, the call rule, verify, and everything the learner never
does.

Two details of the move statements:

- **Shared models.** A pump model is shared across families and horizons (PUMP for PUMP30 and PUMP100). DUMP and
  PUMP_AND_DUMP each have their own, plus a deviation per statement.
- **Short calls.** For a short call (the dilution family), the price features of a move statement are read on the
  price, not in the call's direction.

The move statements start from live outcomes only: history records no twins' moves.

## Why this is legitimate

It is a change of what is graded, made before anything was graded or sealed under either version. Like the v1
withdrawal, it hides no result because none exists.

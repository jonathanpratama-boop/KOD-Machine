# LEARNER_v1, addendum 1: the claim is withdrawn before any outcome existed

Written 2026-10-29, before any RESOLUTION record exists in `paper/catalysts.jsonl` (the first H20 window ends
2026-11-27): no forecast of this learner has been scored, and no look has been taken. Owner instruction of the same day:
"Make sure you engineer the self learning properly and make it fool proof. I want you to understand what safeguard is
hindering us and what is not."

`protocol.json` and `PROTOCOL.md` stay as they were frozen. This addendum withdraws the claim and the registered trial
(`research/QUANT_GRADE/trials/LEARNER_v1_BRIER_withdrawn.json`). The successor is `research/LEARNER_v2`.

## What stays

The two forecasts sealed at 2026-10-29T08:36:21Z (`CAT-SEC13D-0000921895-26-002864`, BankUnited, and
`CAT-SEC13D-0001493152-26-049116`, Smith & Wesson) stay in `paper/learner.jsonl`. `paper-verify` keeps checking them.
Both published the sealed priors unchanged (alpha 0, no training rows), so withdrawing the claim hides no result. No
new LEARNER_v1 forecast is sealed: `learner-forecast` now runs LEARNER_v2.

## Why: six defects found in an audit of the code against the owner's goal

The goal is a machine that becomes confident only when its predictions are accurate, "not being lucky that its going
up". v1 could have reported success without meeting it.

1. **The comparator rewards base rates (a fake pass).** v1 is judged against the sealed priors. For RUN30, FADE10 and
   every mechanism statement the sealed prior is a 0.5 placeholder ("running" below 20 outcomes). A learner that only
   learns how often a statement comes true beats a 0.5 placeholder by a wide margin without telling any two sets apart.
   Measured on a synthetic register where a mechanism statement is true 10% of the time and no feature carries
   information: the v1 skill statistic (1 - Brier(learner) / Brier(sealed prior)) is **0.63**. LEARNER_v2 scores the
   same world at zero: its comparator learns the base rate too, and its forecast moved by at most 0.003 in logit
   (`tests/test_learner2.py`, `test_learning_a_base_rate_earns_no_skill`).
2. **Confidence is pooled across statements.** One alpha for everything: a fake pass on RUN30 base rates would have
   unlocked confidence for BEATS_TWINS, where nothing was learned.
3. **The claim counts statements a rising market makes true.** GAIN0, RUN30 and FADE10 are absolute. A model whose
   intercept tracks the last month's outcomes learns the market's direction and is credited for it: the luck the owner
   ruled out.
4. **The offset drifts.** A running prior changes from one set to the next, so the same features meet a different
   baseline in training and at forecast time. The model's coefficients absorb that drift.
5. **One filing counts twice.** A child family (SEC13D_V2, FORM4_SHARP) seals the same filing as its parent. v1 trains on
   both sets as independent rows and counts both toward its 300-forecast confidence target.
6. **The gate is not luck-proof, and the check can raise false alarms.** alpha = min(1, n / 300) x clip(skill / 0.05)
   uses a point estimate checked every day. A lucky run lifts it, and the chance grows with every look. Separately,
   `verify` compares a sha256 of weights rounded to 8 decimals. A different floating-point library can flip one digit
   and report "possible peeking" on an honest forecast.

v1 also learned only from live outcomes. The first resolves 2026-11-27, and the 300-forecast target sits more than a
year out.

## What LEARNER_v2 does instead (research/LEARNER_v2/PROTOCOL.md)

| v1 defect | LEARNER_v2 |
|---|---|
| sealed-prior comparator | a climatology twin: the same fit with an intercept only; the learner's forecast is the anchor moved by centred slopes, so its only possible gain is discrimination |
| pooled confidence | one alpha per kind (relative, mechanism, triangulated) |
| absolute statements in the claim | skill statements only; absolute ones get the anchor and are never scored as skill |
| drifting offset | a fixed offset (the frozen base prior) and the base rate learned as an intercept, identically in the learner and its anchor |
| double counting | each underlying event weighs once per statement |
| luck-prone gate, brittle check | a time-uniform confidence sequence (valid however often it is checked) plus a recent-record kill switch; verify reproduces numbers within 1e-6, not a hash |
| no data for a year | a pinned warm start of 5,587 events from 2020-2023, with its own intercepts and capped at 300 outcomes' weight per kind |

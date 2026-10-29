# LEARNER_v2, addendum 2: v2.2, the independent review's findings fixed before anything was sealed

Written 2026-10-29, before any outcome and before any LEARNER_v2 forecast: `paper/learner_v2.jsonl` does not exist.
`protocol_v2_2.json` (KOD-LEARNER-v2.2) supersedes `protocol_v2_1.json` (committed in e88f13b, which sealed nothing) and
is now normative.

An independent reviewer (a separate agent) was given the code, the protocol and the tests of KOD-LEARNER-v2, with the
brief to break the owner's guarantees: credit only for accurate predictions, never for base rates, the market or luck.
It reproduced seven defects. Six concern how the machine earns confidence and how its record is checked; one concerns
the schedule. Every one is fixed here, and each fix has a test that names it
(`tests/test_learner2.py`).

| Review finding | Measured | v2.2 |
|---|---|---|
| The gate never closed once open: the running maximum pinned the proof, and the only exit was a plain recent average, a coin flip at zero skill | after skill fell to zero, still open in 40-52% of runs, alpha 1 in 14-24% | the last 52 weeks must still show skill: the gate opens when their one-sided 95% lower bound is above zero and stays open while their 80% bound is; after skill fell to zero it was open in about 14% of the following weeks at the heaviest overlap tested |
| Observations were keyed by the second of resolution, so one market day became dozens of observations; overlapping 20/60-session windows were treated as independent | zero-skill gains with overlapping windows opened the gate in 55% / 68% of runs; the claim's t >= 3 came up 10-19% of the time against 0.2% nominal | one observation per block of resolution weeks (1 week for 5- and 20-session statements, 4 weeks for 60-session ones), a gate per kind and horizon class, and a truncated, small-sample corrected long-run standard deviation; zero-skill noise with the worst overlap of each class opened the gate in 0-7% of runs; the claim uses 4-week blocks with the same standard deviation |
| A parent and child set of one filing shared a weight only if they resolved in the same second | double counted | each underlying event counts once per statement over the whole sequence, where it first resolved |
| verify did not compare the fields scoring reads (kind, window, family, session, event key, prior) | a losing statement relabelled ABSOLUTE passed; a renamed family passed and then crashed every later run | the whole record is recomputed and compared, every field but the chain's |
| verify trusted the clocks in the records and nothing checked that every set got a forecast | a false alarm on an honest forecast when a resolution stamped before it was appended after it; forecasts written after the outcomes, for the winners only, passed | each forecast records the ledger state it was computed from (line count and last hash of both registers) and verify retrains on exactly that state; an RFC 3161 token's time must be before the set's cutoff; the report lists every due set without a forecast |
| IDX sets were never forecast on the documented schedule | 14 IDX sets on 10-29, none forecast | the IDX and crypto routines run the learner after their own seals (routine prompts, 2026-10-29) |
| Lower: a revised resolution left a stale outcome; the tolerance equalled the rounding step; undamped Newton could stall; rejected forecasts were still scored; "earlier" ignored the register order | reproduced | latest revision per (set, window) replaces; tolerance 2e-6; step-halving with an error on non-convergence; only valid forecasts are scored; triangulation counts order by sealed_at |

## What did not change

The statements and theses of v2.1 are unchanged. So are the anchor (the climatology twin), the centring on the live
population, the model and its priors, the warm start, the call rule, and everything the learner never does.

## What it costs

Confidence is slower and more honest. A gate needs 30 observations: 30 weeks for 5- and 20-session statements, and
about two years for 60-session ones, whose windows overlap so much that a week adds little new evidence. The fast
gates are the ones the owner cares most about: the Speculation Register's 5- and 20-session pumps and dumps, which
resolve every week.

## The review's checks that held up

- **No base-rate credit.** In worlds where nothing predicts the outcome, using the real warm start, the learner's mean
  deviation was about zero and its expected Brier gain negative. In this addendum's own end-to-end simulation the gain
  was -0.0005 over six seeds, against +0.0100 with a real edge.
- **No peeking.** Training uses only resolutions before the forecast, and pairs need an outcome after it.
- **Clean inputs.** The triangulation counts see only earlier sets, and the warm start is pinned.
- **No crash on the real ledger.** Missing fields, partial cones and child families are all handled.

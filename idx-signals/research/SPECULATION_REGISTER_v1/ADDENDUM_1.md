# Speculation Register, addendum 1: v1.1, the next session's close

Written 2026-10-29. `protocol_v1_1.json` (KOD-SPEC-REGISTER-v1.1) supersedes `protocol.json` (KOD-SPEC-REGISTER-v1)
for every set sealed from now on. Sets sealed under v1 keep their cone and their two windows and are never
re-sealed; v1.1's third window is never opened on them.

## Why

The owner's instruction is to reach a measured answer in weeks, not months. `research/PATH_HISTORY_v1` (one
pre-registered look at 14,561 past spikes) found that whether a spiking stock closes 10% lower the next session, on
its own, is the best-discriminated dump statement out of time (US AUC 0.627 with free EDGAR and FINRA data) and the
fastest to resolve. The learner can only be scored on outcomes the register records, so the register now records the
next session's close.

## What changes

- **One window, `NEXT1`**: the next session's close of the candidate and its twins, on the reference chain, no
  plan. It resolves one session after the signal (crypto: the next UTC day).
- **Three statements**, all for every market:
  - `DOWN10_1`: the close of s+1 is at most 0.90 times the signal close (running prior);
  - `UP10_1`: the close of s+1 is at least 1.10 times the signal close (running prior);
  - `BEATS_TWINS_1`: the s+1 return over the signal close exceeds the median of the twins' (prior 0.5, the null).
    A name without a bar at s+1 is ungraded; a twin without one is left out, and the statement needs at least
    three twins with a bar.
- The resolver id becomes `spec-resolve-v1.1`; the two existing windows resolve exactly as before.
- The register version recorded on new sets becomes `spec-register-v1.1`, and each set records its own protocol's
  hash, which `paper-verify` checks against that version's file.

## What does not change

BASE5, PATH20, the plan, the twins and their seed, the v1 statements and priors, the tag, the decision rule and its
looks, the sealing cutoffs, and every line already in `paper/speculations.jsonl`. The learner versions already sealed
(v2.2) forecast only the windows their protocol names; the new statements are for the next learner version.

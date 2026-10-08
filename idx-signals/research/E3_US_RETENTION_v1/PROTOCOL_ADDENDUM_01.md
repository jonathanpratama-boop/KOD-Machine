# E3-US-RETENTION-v1 protocol addendum 01 (added before any E3 return evaluation)

`PROTOCOL.md` is append-only, so these two clarifications are recorded here. They bind with it
and change no rule, threshold, gate or sample.

1. **In-sample screening window.** The screening period 2020-07-01..2022-12-31 is exactly the
   E2 discovery period on which G2_RET30 was selected (`research/E2/protocol.json`, `periods`),
   so G2 flags in this window are in-sample for the detector and an E3 pass there is not
   out-of-sample evidence: it can only justify the independent confirmation described in
   `PROTOCOL.md`.
2. **Unverified split units in the screening window.** SEC-corroborated split schedules cover
   only provider events effective after 2023-01-03 (`effective_after` in the
   `us_splits-*.json` manifests), so price units for names with provider splits effective in
   2020-2022 are unverified; the results must report the number of such names, and of
   affected origins per arm, alongside the cost-envelope bounds, rather than leave them
   implicit.

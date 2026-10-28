# LEAD_LADDER_INTL_v1 addendum 2 (2026-10-26, after the placebo rehearsal, before the recorded run)

The rehearsal (random eligible names in place of the up episodes) gives primary lifts of P1 1.11, P2 1.56 and
P3 1.15. P2's null is not 1: the matched pools exclude names with a same-kind move in u..t, and that exclusion shifts
the pool's distribution of a few features. LEAD_LADDER_v1's own rehearsal shows the same for two of its passing
cells (IDX up5 bottom 1.80, CRYPTO ret20 bottom 1.44; see LEAD_LADDER_v1/ERRATA_1.md).

So a primary cell now also needs **G6 placebo: lift >= 1.5 x its rehearsal lift** (the same cell in
`rehearsal/summary.json`). A cell passes only with G1 to G6. The runner (`run_v2.py`) is unchanged; `placebo_gate.py`,
pinned before the run, reads `results/summary.json` and `rehearsal/summary.json` and writes the final verdict to
`results/placebo_gate.json` with the same reading rules. The secondary ladder reports its placebo lift beside each
passing cell. No result of the real episodes has been computed.

# CRYPTO_REPLAY_v1 — reviews and audits

## Before the freeze (adversarial review, four lenses, skeptic verification)

No real-data result existed during the review; reviewers worked on synthetic fixtures only.

- **Causality lens:** no findings.
- **Execution lens:** one minor: a missing bar-5 close keeps the position open, stop and target still resting, until the
  next valid bar. Kept and documented (counted as rolled exits).
- **Accounting lens:** the aggregate-risk cap measured open positions by their distance to the stop, so an open gain
  could block entries; a skeptic called it deliberate, but it did not match the owner's "1.5% aggregate *planned* risk".
  Fixed: the cap sums planned risk fractions (at most three pending or open). Also fixed: an independent re-derivation of
  every trade from the raw bars (`audit_trades`), a circular block bootstrap, and valuation bounds for year-end positions.
- **Spec lens:** fixed: rankings re-verified on the final `rankings.py`; the run refuses unless every pinned file is
  committed and unchanged; `report.py` and the tests pinned; outputs written only after every arm passes its checks;
  population and control provenance worded correctly.
- Two remaining skeptic checks were stopped once their findings were already fixed.

## After the run (three independent auditors, read-only)

| Audit | Verdict | What was checked |
|---|---|---|
| Clean-room re-simulation | CONFIRMED | A simulator written from the policy text alone, without the engine, reproduced BASE summary and sequence exactly: 1,825 decisions per arm, every fill, exit and P&L, the 365 daily rows, end equity difference 0.0. |
| Report and ledger consistency | CONFIRMED | Every figure in RESULT.json and all 57 figure-bearing lines of REPORT.md recomputed from the trade and daily ledgers for all 16 scenario-arm pairs; daily identities on every day; the bootstrap reproduced to 1e-12; `report.render` reproduces REPORT.md byte for byte. |
| Causality, no-2024, reproduction | CONFIRMED | Every entry after its decision, every exit after its entry, nothing dated after 2023-12-31, entry opens equal the panel, no label column reaches the engine; all 16 runs re-executed in memory reproduce the recorded fingerprints; protocol and pins committed (e1fac07) before the run (15:07:37Z frozen, 15:07:53Z ran). |

Notes recorded by the auditors (none changes a number):

1. The trade ledgers leave `entry_day` blank for the 12 orders that stayed unfilled because their entry day fell in
   2024 (`trades_table` copies the entry day only from fills). Their planned entry days are in RESULT.json and
   REPORT.md (signal day + 1 + delay).
2. A fill requires that day's whole bar to be valid (complete, positive prices and volume): a mild same-bar condition
   specified by the frozen protocol. No entry was rejected in any arm, so it changed nothing.
3. Git proves the code and protocol were committed before the recorded run; it cannot prove the absence of an
   uncommitted earlier run. None was made: before the freeze the only 2023 computation was the ranking rebuild, whose
   hit counts were already published in PREMOVE_SEQUENCE_v1's summary.json.
4. The gap, rolled-exit and rejected-entry branches never occurred in this data; they are covered by the fixture tests
   only.

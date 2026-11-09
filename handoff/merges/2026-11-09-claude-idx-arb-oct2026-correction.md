# Merge: October 2026 IDX lower-limit correction

PR #29 corrects the missing October 19 and 20 rules. Reviewed implementation: `558fe7daa265f8189857db715bf61c462e143e0f`. Architect approval and the narrowly scoped pin exception are in `handoff/decisions/2026-11-09_idx_arb_correction_approval.md`.

## Q1. Were the tests written by a different agent than the code?
Answer: yes
Evidence: The PR records independent test authors working from the spec and interface contract, plus a blind second implementation. The implementer's two test repairs are disclosed in the draft note. This review independently ran the five market test modules: 197 passed on Python 3.12.15 with the repository's NumPy/pandas versions.

## Q2. Does every parser of outside data have a real-sample test?
Answer: n.a.
Evidence: No outside-data parser is added or changed. Production code changes only idxsig/market.py; the replay harnesses are review artifacts.

## Q3. Does every study pass the look-ahead check?
Answer: n.a.
Evidence: No study or trading hypothesis is added or changed. The impact report is a retrospective correction analysis, with original scoring-pull and final-bar replay differences disclosed.

## Q4. Did the architect approve it?
Answer: yes
Architect: Astra, acting through Codex in Jonathan's KOD review chat
Evidence: handoff/decisions/2026-11-09_idx_arb_correction_approval.md approves the exact reviewed rules change, its pin exception and the unconfirmed January convention; GitHub CI on 558fe7daa passed and two read-only reviews found no blocker.

## Q5. Could the owner actually trade this, and could the result change what the owner does?
Answer: n.a.
Evidence: This repairs paper-model correctness and creates no trade permission. The reported effect is 14/93 hypothetical ledger outcomes (including 3 becoming unscorable), 9/14 catalyst rows and 1/23 speculation rows; original records remain intact and these are not evidence of a profitable strategy.

## Q6. Does it alert the owner when it breaks?
Answer: no
Evidence: The correction adds a post-2026 log warning, not an owner-delivered exchange-rule alert. That limitation is accepted for this narrow repair and recorded in the decision; no new schedule or alert-delivery claim is made.

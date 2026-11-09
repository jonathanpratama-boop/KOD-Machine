# Draft merge note and waiver request, for the architect

The architect writes and signs the final merge note at merge (`handoff/KOD_RULES.md` rules 10 and 11; `tools/check_merge_notes.py` checks it on a push to the default branch). This draft gives the answers and the evidence. Copy it to `handoff/merges/2026-11-09-claude-idx-arb-oct2026-correction.md` (use the UTC date of the merge), edit freely, and fill in Q4. Nothing here is an approval.

## Q1. Were the tests written by a different agent than the code?
Answer: yes
Evidence: the code (`market.py`) was written by the implementer agent; the tests were written by three other agents in isolated workspaces from a spec pack and an interface contract (`spec_pack/`), before any of them saw the code: `tests/test_market_oct2026.py` and `tests/test_market_oct2026_exec.py` (commit 7f44ca239), `tests/test_market_oct2026_extra.py` after mutation testing (commit 927efb8bf), and `tests/test_market_oct2026_review.py`. Two repairs were made by the implementer and are named in their commit messages: one over-strict vacuity guard in the thin-bar sweep, and the removal of two float-tolerance tests as unrelated. A second implementation, written blind by a fourth agent from the contract alone, passes the same tests.

## Q2. Does every parser of outside data have a real-sample test?
Answer: n.a.
Evidence: no parser of outside data changed. The change is confined to `idxsig/market.py`, the README and tests.

## Q3. Does every study pass the look-ahead check?
Answer: n.a.
Evidence: no study changed or was added. The impact report replays existing ledger records on frozen prices and is not a study.

## Q4. Did the architect approve it?
Answer: yes
Architect: <name of the architect who approved and performed this merge>
Evidence: <where the approval is recorded; it needs the waiver below>

## Q5. Could the owner actually trade this, and could the result change what the owner does?
Answer: n.a.
Evidence: it corrects the lower-limit rule of a paper simulator. No trade, no new decision. It does change which hypothetical outcomes the ledger records (14 of 93 replayed records, section 3 of the report).

## Q6. Does it alert the owner when it breaks?
Answer: no
Evidence: nothing alerts if BEI changes the rule again, as it did three times in four weeks. After 2026-12-31 the only signal is `RulesUnconfirmedWarning` in job logs. Suggested follow-ups, none built: scheduled re-checks of the rule sources (after MSCI's review on 2026-11-12, mid-December, 2026-12-29 and 2027-01-04) and a nightly count of closes more than 10% below the previous close (the drift canary, `DESIGN_NOTES.md` option 3).

## Waiver request: editing the byte-pinned file `idx-signals/idxsig/market.py`

- **Why.** The defect is in this file. `handoff/claude/LINT_CLEANUP_20261104.md` says pinned files "must still not be edited without a new protocol version".
- **What is pinned.** `research/MSCI_DELETION_v1`, `MSCI_DELETION_OPT_v1` and `MSCI_DELETION_OOT_v1` (`protocol.json`) pin the old sha256 `e9e9328a...`. Their runners now stop with "idxsig/market.py changed since the freeze". All three already have a completed run whose stored results are untouched, and their whole-tree pin was already stale since 2026-11-04. Seven other studies pin an older hash (`b956576f`) and were already stale.
- **Not touched.** `execution.py` and `paper.py` (pinned by seven and five frozen records). The recorded ledger, registers and frozen research files are byte-identical.
- **What the architect decides.** Whether to record the waiver as a dated file under `handoff/decisions/` and add an addendum to `handoff/claude/LINT_CLEANUP_20261104.md` and the `ruff.toml` comment, both of which still describe the `market.py` pin as intact. This branch does not edit those files: they are existing records.
- **Suggested wording.** "2026-11-09: `idxsig/market.py` is edited to add the 2026-10-19 and 2026-10-20 lower-limit rules and to stop treating the unconfirmed 2027 rule as fact. MSCI_DELETION_v1, _OPT_v1 and _OOT_v1 can no longer be re-run; their stored results stand. No other pinned file changes."

## Decisions that remain with the architect or the owner

1. **Today's scoring.** Merge before the IDX run at about 10:20 UTC, or pause `paper-score --market IDX` (report section 6 and 9).
2. **After 2026-12-31.** Keep the carry-forward convention, or move to fail-closed (`DESIGN_NOTES.md` option 1: needs a waiver for `execution.py`, an alert and a runbook).
3. **Locked horizon bars.** Leave the legacy scorer as it is, or give it a rolling horizon in a new policy version (needs `paper.py`).
4. **Open the decree.** The in-force Rule II-A PDF is in the IDX register; the owner can open it in a browser. It would settle the rounding wording, the Rp11-14 reading, the board scope and any 2027 clause.
5. **Re-check the sources** after MSCI's review on 2026-11-12 if the merge is later than that.

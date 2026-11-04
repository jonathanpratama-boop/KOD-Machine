# KOD house rules

Adopted 2026-11-04 (`handoff/decisions/2026-11-04_rules_and_architect.md`). They apply to every agent (Claude, Ace,
Astra, Codex, Hermes) and override any prompt that conflicts with them. Background: `handoff/KOD_FIX_PLAN.md`.

## Safety (unchanged, restated)
1. Paper only. No broker credentials, no leverage, no real order without the owner's approval of that specific trade.
2. Frozen records are never edited; corrections are new files (`tools/check_append_only.py`, enforced by `.githooks`).
3. A protocol is committed before its data is read, and runs once (`docs/PROTOCOL_TEMPLATE.md`).
4. No bot-check or block circumvention. No secrets in the repository.

## Building
5. **Different authors.** The tests for new code are written by a different agent than the code, from the protocol or
   specification, before the implementation is seen.
6. **Real samples.** Every parser of outside data has at least one test on a real captured sample
   (`handoff/claude/REAL_SAMPLE_INVENTORY.md` lists the gaps).
7. **Look-ahead check.** Every new study passes `tools/check_no_lookahead.py` before its outcome run
   (`docs/LOOKAHEAD_CHECK.md`).
8. **Shared data.** New studies load data through shared, as-of-aware loaders; CI warns on direct raw-file reads in new
   study scripts (`tools/check_shared_data.py`).
9. **Feasibility first.** Every protocol opens with the feasibility gate; a NO-GO is recorded and not run.

## Structure
10. **One architect** (see `handoff/AGENTS.md`). Only the architect merges into the default branch, except the daily
    paper bots' own log paths. One builder works on default-branch code at a time.
11. **Merge notes.** Every code merge into the default branch adds `handoff/merges/<date>-<slug>.md` answering the six
    questions below (`tools/check_merge_notes.py` blocks merges without one).
12. **Branches.** At most five open working branches; merge or archive within seven days. `moonshot-tools` is untouched
    by owner instruction.

## Operations
13. **Alerts.** Anything that runs on a schedule reports success and failure to the owner (`ops/kod-watch/`).
14. **Off-server copies.** Evidence that exists on only one machine is not yet evidence.

## The six questions (owner's checklist before any merge)
1. Were the tests written by a different agent than the code?
2. Does every parser of outside data have a real-sample test?
3. Does every study pass the look-ahead check?
4. Did the architect approve it?
5. Could the owner actually trade this, and could the result change what the owner does?
6. Does it alert the owner when it breaks?

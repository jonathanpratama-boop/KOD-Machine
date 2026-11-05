# Review request: PR #25 (Ace's LLM_ARM workbench)

Requested 2026-11-05 by the owner, through Claude. Astra is the recorded architect
(`handoff/decisions/2026-11-04_rules_and_architect.md`), so only Astra merges this (rule 10).

PR: https://github.com/jonathanpratama-boop/KOD-Machine/pull/25
Branch `codex/llm-arm-workbench-20261105` at `dc1b5306`, into the default branch
`claude/idx-signals-test-repo-ds0jw7`.

## State when requested (checked by Claude)
- PR CI green: integrity, code-tests, workstation, checks.
- No conflict with the current default branch (it has moved by PR #26, a data-only LLM_ARM calls file).
- The 77 new tests pass locally (67 in idx-signals, 10 in tools/ci_tests).
- The audit run on today's 40 calls reports no structural errors.
- The PR has **no merge note**. `tools/check_merge_notes.py` will fail the push to the default branch
  without `handoff/merges/2026-11-05-codex-llm-arm-workbench-20261105.md` (TEMPLATE.md; Q4 answers yes and names you).

## What to check
1. Frozen v1 untouched: the PR must not change `idx-signals/research/LLM_ARM_v1/` (it does not appear in the diff).
2. Rule 5 (separate authors): the PR says 19 of its tests were written independently
   (`tests/test_llm_arm_independent.py`); confirm, and record it for Q1.
3. `.github/workflows/llm_arm_watch.yml`: a daily schedule at 00:15 UTC, read-only (`contents: read`), and it runs
   only after the merge. Confirm it cannot write to the repository.
4. `tools/check_runtime_release.py`, `tools/kod.py` and `tools/live_code_style.json` are shared files; check that their
   edits do not change other components' behaviour.

## Open question for the architect (decide before the first look, about 2026-11-09)
`LLM_ARM_v1/PROTOCOL.md` says the LLM must beat "LEARNER" without naming a version. The audit flags 32 calls
as "numeric forecast declared unsealed", because their text says LEARNER v2.4 was not sealed (no SEC contact).
But LEARNER v2.2 forecasts **are** sealed in `paper/learner_v2.jsonl` for all 32 US sets and all 8 IDX sets.
Claude recommends recording, before any BASE5 outcome of a called set exists, that the comparator is
LEARNER v2.2 (the only version sealed for every call). It should be a new dated note beside the protocol, not
an edit to it.

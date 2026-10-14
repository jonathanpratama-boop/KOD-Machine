# Exact next steps for whoever continues

## 0. Re-orient (5 minutes)

```sh
cd /home/user/KOD-Machine && git status --short && git log --oneline -3
cat handoff/kod-next-move/HANDOFF.md
python3 handoff/kod-next-move/scripts/sync_outputs.py        # refresh outputs/ from the journal
ls handoff/kod-next-move/outputs/*/                            # see which agents have finished
```
If the container was reclaimed, the journal path in `sync_outputs.py` will not exist; the
`outputs/` directory already holds everything that had finished at the last sync, and the
workflow must be re-run from `workflow/kod-next-move.js` (see §2).

## 1. Phase 1 — DONE (2026-10-14 07:23 UTC)

All 25 outputs are in `outputs/`; the recommendation is `synthesis/RECOMMENDATION.md` and the
draft protocol `synthesis/E5_CEILING_protocol_draft.json`. The synthesis was checked against the
refuters' demands (`03_proposals_and_evidence.md` §Recommendation lists what was and was not
incorporated). Nothing further is needed from the workflow; `workflow/wf_1f360293-1fd.result.json`
holds the complete return value if the journal is ever lost.

## 2. Phase 2 (implementation) — IN PROGRESS (the owner said "execute now"; local branch only)

State: Phase 2a done and merged (`claude/e5-ceiling` `be99fec`, worktree `scratchpad/e5`); Phase 2b workflow `wf_c9b7db07-d56` running in worktree `scratchpad/e5-s-study` (branch `e5/s-study`). When it finishes: sync outputs to `outputs_phase2b/`, read the review verdicts, merge `e5/s-study` into `claude/e5-ceiling`, run the four checks, then (orchestrator, not an agent) freeze `research/E5/protocol.json` in its own commit and record the sha, then Stage 0 reproduce → Stage 1 information gate → Stage 2 execution, one recorded run each, reporting a null honestly. The steps below are the original plan and still apply.

Owner inputs needed first (see `04_decisions.md`): merge PR #7 or not; push the PR #3 merge or not;
accept 2023 reuse; name of the new branch to push (default `claude/e5-<slug>`).

Then, on a new branch from the base (`git checkout -b claude/e5-<slug> origin/claude/idx-signals-test-repo-ds0jw7`):
1. Write `idx-signals/research/E5/PROTOCOL.md` + `protocol.json` from the synthesis draft; commit with its sha; **before any number**. Follow the E3/E4 pattern (`research/E3/protocol.json`, `idxsig/e3.py`, and on PR #7 `idxsig/e4.py`): precondition reproduce → discovery → freeze SELECTED → validation (one run, recorded via `results.write_run`).
2. Every US/crypto `RunConfig` must set `end` explicitly (HEAD has no code holdout guard for US/crypto; PR #7 adds `backtest.GLOBAL_HOLDOUT`). Never load 2024+.
3. Rules go in `idx-signals/idxsig/rules/moonshot_e5.py`, registered in `rules/__init__.py`, passing `rules/audit.py` and the prefix-first lookahead check (`python3 -m idxsig rules`).
4. Tests synthetic only (`tests/test_e5.py`), run `python3 -m unittest` in `idx-signals/` (expect ≥273 on the PR #3 merge base, ≥222 on base) and in `kod-machine/` (96).
5. `python3 -m idxsig verify-runs`, `python3 ../tools/check_append_only.py --all` must stay OK; `write_run` refuses a dirty tree, so commit before each run.
6. Report the result including a null; never describe discovery numbers as performance.

## 3. Pending non-experiment items

- **PR #3 merge** (`0ce21f0`): to restore it anywhere, `git bundle verify bundles/pr3-merge-0ce21f0.bundle && git fetch bundles/pr3-merge-0ce21f0.bundle claude/pr3-merge-v5-local:claude/pr3-merge-v5-local` (prerequisite commits `bd352b2` and `e952482` must be present, i.e. fetch origin first). Human-readable: `bundles/pr3-merge-resolution.patch`. Push only with the owner's permission; if PR #7 lands first, redo the merge onto the new base.
- **Breakout branch**: `git fetch bundles/us-breakout-v1.bundle claude/us-breakout-v1:claude/us-breakout-v1` (prerequisite = merge-base with `origin/claude/us-pipeline-v1`, present after `git fetch origin`). Not pushed; owner's call.
- **Daily routines** will fire into this session; run them exactly as their prompt says (`02_session_log.md` has the last three runs as examples) and never start one while another paper-scan is running.
- **G3 provenance** (Hermes steps 1–3): wait for the owner's audit report from `scripts/g3_provenance_audit.sh`, then write the execution timeline; do not reschedule anything.
- **PR #3 review**: a GitHub event from Ace wakes this session; address review comments on the merge commit, not on `bd352b2`.

## 4. Things another agent must not do

- `handoff/` IS committed and pushed on the base branch (the owner's stop hook asked for it); keep every sync a small commit. Never push `claude/e5-ceiling` or `e5/*`, or open a PR, without the owner's say-so.
- Do not `git worktree remove` the scratch worktrees before the bundles are confirmed restorable somewhere durable.
- Do not run any harness run that reads 2024+ rows, re-tune a frozen detector, or describe discovery statistics as performance.

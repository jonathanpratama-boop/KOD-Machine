# HANDOFF — kod-next-move (resumable checkpoint)

**Status line (update at every phase boundary):**
Phase 1 and Phase 2a COMPLETE (recommendation E5-CEILING; harness extensions merged). **Phase 2b COMPLETE 2026-10-14 16:00 UTC under a budget constraint** (owner: 24 % usage left — no more subagents): the study module, `e5-*` CLI, tests and protocol were built by the workflow builder (commit `30a442f`, 356 tests OK, verify-runs OK) and reviewed by the orchestrator only; the reviewer workflow was stopped. **Protocol FROZEN: commit `e1e57af`** on local branch `claude/e5-ceiling` (head `f101023`). **Stage 0 (reproduce) RUNNING** since 16:00 UTC (`scratchpad/e5_stage0.log`). Next: Stage 1 information gate and Stage 2 execution via `e5-discovery`, then `e5-freeze`, then `e5-validation` (2023, PROVISIONAL), one recorded run each; report a null honestly. Not pushed; no PR. Checkpoint commits are pushed to the base branch.

**Where:** `/home/user/KOD-Machine`, branch `claude/idx-signals-test-repo-ds0jw7`. This directory is committed and pushed on that branch (the owner's stop hook asked for it); every sync is a small commit. Phase-2 code lives in the worktrees listed in `02_session_log.md` §Phase 2, on local branches `claude/e5-ceiling` and `e5/*`.

| Need | File |
|---|---|
| Objective, scope, environment, directives, prior results, branch/PR state | `01_context.md` |
| Commands run, code changes, actual test results, workflow run ids and transcript paths | `02_session_log.md` |
| The six proposals, judge scores, refutations, reader evidence (digest) | `03_proposals_and_evidence.md` |
| Decisions made vs open questions (owner's vs technical) | `04_decisions.md` |
| Exact next steps, how to resume the workflow, how to restore the unpushed commits, what not to do | `05_next_steps.md` |
| Full agent outputs, one file per agent (`.json` raw, `.md` readable) | `outputs/<Understand|Propose|Judge|Refute|Synthesize>/` |
| Judge aggregate ranking | `outputs/ranking.json` |
| The workflow script (copy) | `workflow/kod-next-move.js` |
| Unpushed commits: PR #3↔base merge (`0ce21f0`, policy v5) and `claude/us-breakout-v1` | `bundles/*.bundle`, `bundles/pr3-merge-resolution.patch` |
| Tooling: output sync; G3 Mac audit script | `scripts/sync_outputs.py`, `scripts/g3_provenance_audit.sh` |

**One-paragraph state.** E1–E4 and the breakout baseline all found real repricing detection but no plan that makes money after costs (fade, fat tails, liquidations; see `01_context.md` table). The owner asked for the next move and to execute. A read-only panel produced six proposals; the judges rank (1) a pre-registered T-0 predictability ceiling / directional-ranker kill test (#4, 47.0/60), (2) a pre-spike tape family built around the KOD volume-creep definition (#1, 45.7), (3) a delayed-entry grid on the frozen G2_RET30 (#2, 43.3). All three refuters of #4 found serious but fixable flaws (verdict conflates information with executability; anti-conservative matched test; IDX down-label regime mismatch; serial dependence; unrepaired US panel). The synthesis is pending. Owner decisions pending: merge PR #7; push the local PR #3 merge; accept 2023 reuse; branch for Phase 2.

**Resume in one line:** read `05_next_steps.md` §0 and §2, sync the Phase-2b journal into `outputs_phase2b/` with `scripts/sync_outputs.py`, read `06_phase2_integration_todo.md` for every API decision, then continue from the last entry of `02_session_log.md`.

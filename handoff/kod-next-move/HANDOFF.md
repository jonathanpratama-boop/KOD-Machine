# HANDOFF — kod-next-move (resumable checkpoint)

**Status line (update at every phase boundary):**
Phase 1 `wf_1f360293-1fd` COMPLETE (recommendation E5-CEILING, `synthesis/RECOMMENDATION.md`). **Phase 2a COMPLETE** 2026-10-14: workflow `wf_a885f29d-0ec` (15 agents, 0 errors after the 09:30 UTC resume) — five harness/rule builds accepted (h3-e1's last fix inspected by the orchestrator, see `06_phase2_integration_todo.md`); all merged into local branch `claude/e5-ceiling` head **`be99fec`** (321 tests OK, rules audit, verify-runs, append-only OK). **Phase 2b RUNNING**: workflow `wf_c9b7db07-d56` builds `idxsig/e5.py` + `e5-*` CLI + tests + DRAFT `research/E5` protocol in worktree `e5-s-study` (branch `e5/s-study`), then three-lens review and fix rounds — see `02_session_log.md` §Phase 2b for the journal path and how to resume. Nothing frozen, no real-data run yet; not pushed; no PR. Checkpoint commits are pushed to the base branch.

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

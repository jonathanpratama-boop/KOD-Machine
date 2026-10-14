# Context: objective, scope, environment

Written 2026-10-14 ~07:00 UTC by the cloud session `session_01SrR7rsdNDD1Fqye2K6MDSw`
(Claude Code on claude.ai; container `/home/user/KOD-Machine`). Everything here is taken from
files on disk or from commands whose output is recorded in `02_session_log.md`.

## Objective

The owner (Jonathan) asked, with ultracode on: *"what do you think is the next move? … make this
work and explore new ideas … execute now."* The immediate task is to choose and then run the
next pre-registered experiment (or infrastructure step) for KOD-Machine, after four experiments
and a baseline found no tradeable edge. Phase 1 (this checkpoint) is a read-only multi-agent
workflow that maps the project, generates six proposals, judges them, refutes the top three, and
synthesizes one recommendation with a protocol draft. Phase 2 (not started) is implementation.

## Working directory, branch, repositories

| Item | Value |
|---|---|
| Primary checkout | `/home/user/KOD-Machine`, branch `claude/idx-signals-test-repo-ds0jw7` (the base branch; the scheduled paper scans commit here) |
| HEAD at checkpoint | `e635e22` paper score CRYPTO (2026-10-14 00:27 UTC) |
| Remote | `origin` = `jonathanpratama-boop/KOD-Machine` (GitHub) |
| Scratch worktree A | `/tmp/claude-0/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/scratchpad/m` on local branch `claude/us-breakout-v1` (head `0ef056b`, **not pushed**) |
| Scratch worktree B | `/tmp/claude-0/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/scratchpad/mw` detached at `0ce21f0` = merge of base (PR #6) into PR #3, policy renamed v5 (**not pushed**; also local branch `claude/pr3-merge-v5-local`) |
| Bundles of both unpushed commits | `handoff/kod-next-move/bundles/` (see `05_next_steps.md` for how to apply) |
| Python | 3.13, pandas/numpy installed; tests run with `python3 -m unittest` inside `idx-signals/` and `kod-machine/` |

## Standing directives (from the owner and Ace; all still in force)

- No real-money orders, no funds moved, no ASTRA/production change, no production detector promoted.
- Historical experiments are never presented as prospective performance. No manufactured probabilities, recommendations, candidates or results.
- Preserve historical records, frozen research dirs, the committed DB and append-only guarantees. Never rewrite history, never force-push. `tools/check_append_only.py --all` must stay OK.
- Do not tune the old IDX strategy; do not inspect the reserved holdout (IDX 2024-01-02..2025-02-21; US/crypto 2024 onward).
- Do not inspect git credentials or gcloud config.
- Ace (reviewer): "finish trustworthy execution accounting first; strategy selection remains parked" — the owner has since asked explicitly to explore new ideas (this task), so strategy selection is now authorised by the owner; Ace's review of PR #3 is still pending.
- Pushing: only to `claude/idx-signals-test-repo-ds0jw7` without asking; any other branch or any PR merge needs the owner's say-so.

## What has been established (numbers from the repo; readers' detail in `outputs/Understand/`)

| Experiment | Market / family | Result | Why it failed |
|---|---|---|---|
| E1 (`research/E1`) | IDX, F1_ARA | detection validated (precision ≈9x matched); trading −4.06% vs −0.53% matched (run `20261008T000401Z`) | entry at next close inside the move; median 5-session path ≈ −10% |
| E2 (`research/E2`, repairs) | US/crypto, G2_RET30 | detection 15.4% vs 2.8% (US), 18.5% vs 4.0% (crypto); trading US −0.97% vs −0.75% (fill B), crypto −1.90% vs +1.42% | same fade; US panel/split repairs did not change the sign |
| IDX_CAUSAL_CAPACITY_v1 | IDX FILL-C | −3.64% vs −4.06%, p=1.0 | capacity model not material |
| US_BREAKOUT_v1 (local branch only) | US 60-day-high breakout | D = −0.04pp, p=0.86; NO EDGE | plain breakout has nothing |
| E3 (PR #6, merged) | IDX, 3 detectors × 36 plans | 0/108 admissible; all 108 lost in 2022 | no entry/exit rule rescues the fade |
| E4 v1/v2 (PR #7, open, green) | crypto short side | v1 0/144; v2 31/288 on discovery (bear regime), validation 2023 FAILED: 34 trades, 68% hit, avg −1.5%, 3 liquidations | fat left tail; selling insurance |
| KOD lab | 5 detectors KOD-DET-v0 | 0 prospective cases vs floor 30; calibration NOT_STARTED | nothing feeds it |

Prospective paper ledger (`idx-signals/paper/ledger.jsonl` at `e635e22`): 16 scans, 86 decisions, all PASS (APPROVAL-v2 cannot approve because every pinned run has negative average net), 2 outcomes scored (both CORRECT REJECTION). First US outcomes due 2026-10-15.

## Branch / PR state at checkpoint (`outputs/Understand/read_prs.md` has the conflict analysis)

| Ref | Head | State |
|---|---|---|
| base `claude/idx-signals-test-repo-ds0jw7` | `e635e22` | includes PR #6 merge `e952482` (execution plans, E3, PAPER-POLICY-v4 IDX/E3 rule) |
| PR #3 `claude/us-pipeline-v1` | `bd352b2` | open, awaiting Ace; conflicts with base in `cli.py`, `execution.py`, `paper.py` (policy name clash v4/v4) — resolved locally as `0ce21f0` (v5), not pushed |
| PR #7 `claude/e4-fade-short-side` | `2b26197` | open, CI green, mergeable_state clean; owner's merge decision pending |
| PR #5 `codex/e3-us-retention-protocol-v1` | `8b61fb8` | draft; E3-US retention idea, not run |
| `moonshot-tools` | `c664ea8` | Fable's `msx.py` 3.0.2 toolkit; read-only w.r.t. this repo; selftest passes |
| `claude/us-breakout-v1` | `0ef056b` | local only (worktree A) |

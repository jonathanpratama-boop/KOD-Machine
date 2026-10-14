# Session log: commands executed, code changes, actual results

All times UTC. Only things that were actually run are listed; results are copied from the
command output at the time.

## Scheduled paper routines (committed and pushed to the base branch)

| When | Command (in `idx-signals/`) | Result |
|---|---|---|
| 2026-10-13 22:48 | `python3 -W ignore -m idxsig paper-scan --market US --commit` | `SCAN-US-2026-10-13-G2_RET30`: 15 candidates, all PASS; commit `bc05443`, pushed |
| 2026-10-13 23:15 | `python3 -W ignore -m idxsig paper-score --market US --commit` | "no US decision can have completed its window yet; nothing recorded" |
| 2026-10-13 23:15 | `python3 -m idxsig paper-verify`; `python3 ../tools/check_append_only.py --all` | OK / OK |
| 2026-10-14 00:24 | `python3 -W ignore -m idxsig paper-scan --market CRYPTO --commit` | `SCAN-CRYPTO-2026-10-13-G2_RET30`: 1 candidate (GNS) PASS; commit `96f1fd1`, pushed |
| 2026-10-14 00:27 | `python3 -W ignore -m idxsig paper-score --market CRYPTO --commit` | scored 1: `SCAN-CRYPTO-2026-10-07-G2_RET30-MET` → CORRECT REJECTION (r5max −0.74%); commit `e635e22`, pushed |
| 2026-10-14 00:27 | `paper-verify`; `check_append_only --all` | OK / OK |

Routines still scheduled on this account (they wake this session): IDX scan (daily after IDX close), US scan (weekdays after US close, trigger `trig_01J9ByPru7Yu1HX7oeuWMy93`), crypto scan (daily 00:23 UTC, `trig_01SjYKTaUQ48evByHj3ajPwe`). Each must not start while another paper-scan runs (single hash chain).

## PR #3 ↔ base merge, done in scratch worktree B (local only)

```
git worktree add --detach <scratch>/mw origin/claude/us-pipeline-v1   # bd352b2
git merge --no-ff --no-commit origin/claude/idx-signals-test-repo-ds0jw7   # e952482 (PR #6 merged)
# conflicts: idxsig/cli.py (1 hunk), idxsig/execution.py (1 hunk), idxsig/paper.py (4 hunks)
```
Resolution (full diff: `bundles/pr3-merge-resolution.patch`; commit message in the bundle):
- `cli.py`, `execution.py`: union of both sides (fill models A/B/B2/C + PR #6 plan options/fields).
- `paper.py`: three policy records. v3 unchanged (sha `fdc5b488…`, matches the 81 recorded v3 decisions). v4 = PR #6's (v3 + E3 rule), sha `86ff27d3…` identical to base. PR #3's policy renamed **PAPER-POLICY-v5** (sha `237a66a8…`), with an added `e3_rule` field: while a validated E3 pair exists the IDX scan raises instead of deciding (v5 does not define how a no-chase plan meets the 5% stop rule).
- Silent-merge hazard found and fixed: git had merged PR #6's `e3_plan_rule` field into the v3 dataclass without a conflict marker; left alone it would have changed v3's hash to `19c43ab6…` and orphaned 81 decisions. Pinned by new `tests/test_policy_versions.py`.
- PR #6's `tests/test_paper_v4.py` now passes `policy=paper.POLICY_ID_V4`; PR #3's `test_us_pipeline.py` expects v5. `exec_us.py`, `contract.py` docstrings say v5. `paper/README.md` updated; `research/EXEC_US_v2_1/POLICY_RENAMED_v5.md` added (frozen research files untouched).

Checks on the merge commit `0ce21f0` (all run in worktree B):

| Check | Result |
|---|---|
| `idx-signals`: `python3 -m unittest` | 273 tests OK |
| `kod-machine`: `python3 -m unittest` | 96 OK |
| `python3 -m idxsig rules` / `verify-runs` / `paper-verify` | source audit passed / OK / OK |
| `python3 tools/check_append_only.py --all` | OK |
| `python3 -m kod --db var/kod.db verify` | OK with the two pre-existing timestamp WARNs (SMCI, PIPELINE-001) |
| policy hashes | v3 `fdc5b488…` = ledger; v4 `86ff27d3…` = base |

Not pushed. GitHub still has PR #3 at `bd352b2`.

## Other read-only work this session

- Fable's `moonshot-tools` branch: three commits (`de44e14`, `49b3a59`, `c664ea8`), 2 files (`msx.py`, `README.md`); `python3 -I msx.py selftest` in a scratch dir → `SELFTEST PASS`, self-hash OK. It reads our ledger via `git fetch`/`git show`, writes nothing into this repo.
- PR #7 (E4) inspected: `paper.py` diff is 2 lines (`FIRST_SKIP`→`NEVER_ENTERED`); policy unchanged.
- G3 provenance audit script written for the owner's Mac (`scripts/g3_provenance_audit.sh`); not run here (G3 code is not in any branch).

## Phase-1 workflow (running at checkpoint)

- Launched 2026-10-14 ~05:05 UTC: `kod-next-move`, run id `wf_1f360293-1fd`.
- Script: `workflow/kod-next-move.js` (copy; live file at `/root/.claude/projects/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/workflows/scripts/kod-next-move-wf_1f360293-1fd.js`).
- Journal / per-agent transcripts: `/root/.claude/projects/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/subagents/workflows/wf_1f360293-1fd/{journal.jsonl,agent-*.jsonl}`.
- `scripts/sync_outputs.py` copies every completed agent result into `outputs/<phase>/<label>.{json,md}`; re-run it any time.
- Agents are read-only by instruction; no repo file was modified by the workflow. Judge 1 re-ran one scratch counting script (no outcomes); the data reader made ≤6 FMP MCP probe calls.

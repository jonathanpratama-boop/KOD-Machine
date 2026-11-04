# Lint cleanup: 183 ruff errors to 0, and the real bug behind them

Branch `claude/hopeful-hypatia-ktzpog`, 2026-11-04. Owner: "There are still errors. I need you to fix them for me."

## What the errors were
`ruff check .` under the repository's `ruff.toml` (rules E4, E7, E9, F) reported **183 errors in 46 files**, identical on
the default branch and on this branch (all pre-existing). By rule: E702 55, F401 43, E701 43, E741 19, E731 11,
F841 8, F811 2, F541 1, F821 1.

## Result: `ruff check .` prints "All checks passed!"

| Batch | Branch | Errors | Review |
|---|---|---|---|
| Workstation tests | `lint/1-workstation-tests` | 41 to 0 | accepted (nits only) |
| kod-machine library and tests | `lint/2-kod-machine` | 33 to 0 | accepted (nits only) |
| `tools/ci_tests/test_ci_scope.py` | `lint/3-ci-scope-tests` | 23 to 0 | accepted (nits only) |
| idx-signals tests | `lint/4-idx-signals-tests` | 68 to 1 (the 1 resolved below) | accepted (nits only) |
| idx-signals library bugs | `lint/5-idxsig-bugs` | 7 to 2 (paper.py, pinned, below) | accepted (nits only) |
| Pinned files excluded in `ruff.toml` | (direct commits) | 11 + 2 | - |

Method: each batch in its own worktree; one-line-statement splits proved by identical ASTs (`ast.dump(ast.parse(old)) ==
ast.dump(ast.parse(new))`) in separate commits; every removed import checked for re-exports and mock patch targets;
renames local only; no public name or signature changed; touched tests run before and after; one adversarial
reviewer per batch, which reran the AST checks and tests.

## Real bugs found
1. **`idxsig/cli.py`, `sensors pull --commit` crashed after a successful pull.** It read `os.environ` but `os` was
   only imported locally in other branches of `main()`, so `os` was an unbound local there (UnboundLocalError) and the
   commit step never ran. A separate test author wrote `idx-signals/tests/test_cli_sensors_commit.py` first; it failed
   on the old code and passes after the fix (`lint/5-idxsig-bugs`).
2. **`tests/test_event_study.py` did not test what its name says.** The entry-session index `j` was computed and never
   checked. Added the intended assertion (entry is the first session after the public date); it passes.

Investigated and harmless: `event_study.py` unused `a_tick` (removed; no side effect), `paper.py` unused `sel` (left;
file pinned), `kod/workstation/store.py` F811 (the unused module import of `source_url` was shadowed by method
parameters; import removed, public parameter names unchanged).

## Pinned files: why some code is excluded rather than edited
Frozen research records store the exact sha256 of some live code files as the code that produced their results (for
example `REPLAY_UNITS_v2/replay.py` refuses to run when a pinned file changed). Editing such a file, even for lint,
breaks that proof. 45 live Python files are pinned this way. The 11 that are excluded in `ruff.toml` (6 of them added
in this pass because they had lint errors) are never edited for lint; the other 34 are lint-clean and stay checked, and
must still not be edited without a new protocol version.

| Status | File | Pinned by (first records found) |
|---|---|---|
| CHECKED | `idx-signals/idxsig/__init__.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/calendar_us.py` | idx-signals/research/PAPER_ACCOUNT_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/call_cert.py` | idx-signals/research/REPLAY_UNITS_v2/protocol_A.json, idx-signals/research/REPLAY_UNITS_v2/protocol_B.json |
| CHECKED | `idx-signals/idxsig/controls.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/corporate_actions.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/crypto_account.py` | idx-signals/research/CRYPTO_ACCOUNT_v1/protocol_v1_4.json |
| CHECKED | `idx-signals/idxsig/crypto_replay.py` | idx-signals/research/ADMISSION_HOLDOUT_v1/protocol.json, idx-signals/research/ADMISSION_v1/protocol.json, idx-signals/research/ALERT_ATTRIBUTION_v1/protocol.json, idx-signals/research/CRYPTO_REPLAY_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/exec_us.py` | idx-signals/research/PAPER_ACCOUNT_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/execution.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json, idx-signals/research/REPLAY_UNITS_v2/data/events_A_BUILD.json |
| EXCLUDED | `idx-signals/idxsig/global_panel.py` | idx-signals/research/REPLAY_UNITS_v2/data/events_A_BUILD.json, idx-signals/research/REPLAY_UNITS_v2/data/events_B_BUILD.json, idx-signals/research/REPLAY_UNITS_v2/protocol_A.json, idx-signals/research/REPLAY_UNITS_v2/protocol_B.json |
| EXCLUDED | `idx-signals/idxsig/idx_events.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/learner2.py` | idx-signals/research/CRYPTO_TUNE_v1/protocol.json, idx-signals/research/FRESH_SHORT_v1/data/events_BUILD.json, idx-signals/research/FRESH_SHORT_v1/protocol.json, idx-signals/research/RECENT_REPLAY_v1/data/events_BUILD.json |
| EXCLUDED | `idx-signals/idxsig/learner3.py` | idx-signals/research/FRESH_SHORT_v1/data/events_BUILD.json, idx-signals/research/FRESH_SHORT_v1/protocol.json, idx-signals/research/RECENT_REPLAY_v1/data/events_BUILD.json, idx-signals/research/RECENT_REPLAY_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/market.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/panel.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/paper.py` | idx-signals/research/CRYPTO_ACCOUNT_v1/protocol_v1_4.json, idx-signals/research/REPLAY_UNITS_v2/data/events_A_BUILD.json, idx-signals/research/REPLAY_UNITS_v2/data/events_B_BUILD.json, idx-signals/research/REPLAY_UNITS_v2/protocol_A.json |
| EXCLUDED | `idx-signals/idxsig/paper_account.py` | idx-signals/research/CRYPTO_ACCOUNT_v1/protocol.json, idx-signals/research/CRYPTO_ACCOUNT_v1/protocol_v1_1.json, idx-signals/research/CRYPTO_ACCOUNT_v1/protocol_v1_2.json, idx-signals/research/CRYPTO_ACCOUNT_v1/protocol_v1_3.json |
| CHECKED | `idx-signals/idxsig/paper_book.py` | idx-signals/research/PAPER_ACCOUNT_v1/protocol.json, idx-signals/research/PAPER_BOOK_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/premove.py` | idx-signals/research/ADMISSION_HOLDOUT_v1/protocol.json, idx-signals/research/CRYPTO_REPLAY_v1/rankings/VERIFY.json, idx-signals/research/PREMOVE_SHADOW_v1/protocol.json, idx-signals/research/SCORE_VALUE_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/premove_core.py` | idx-signals/research/ADMISSION_HOLDOUT_v1/protocol.json, idx-signals/research/CRYPTO_REPLAY_v1/rankings/VERIFY.json, idx-signals/research/PREMOVE_SHADOW_v1/protocol.json, idx-signals/research/SCORE_VALUE_v1/protocol.json |
| EXCLUDED | `idx-signals/idxsig/premove_shadow.py` | idx-signals/research/ADMISSION_HOLDOUT_v1/protocol.json, idx-signals/research/CRYPTO_REPLAY_v1/rankings/VERIFY.json, idx-signals/research/PREMOVE_SHADOW_v1/protocol.json, idx-signals/research/SCORE_VALUE_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/provenance.py` | idx-signals/research/LIQ_REBOUND_v1/protocol.json, idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/quality.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/research_evaluation.py` | idx-signals/research/RESEARCH_CORRECTIONS_20261104/NEIGHBOURS_v1/RESULT.json, idx-signals/research/RESEARCH_CORRECTIONS_20261104/PRESSURE_v1/RESULT.json, idx-signals/research/RESEARCH_CORRECTIONS_20261104/README.md, idx-signals/research/RESEARCH_CORRECTIONS_20261104/RUN_NOTES.txt |
| CHECKED | `idx-signals/idxsig/risk_control.py` | idx-signals/research/REPLAY_UNITS_v2/protocol_A.json, idx-signals/research/REPLAY_UNITS_v2/protocol_B.json |
| CHECKED | `idx-signals/idxsig/rules/audit.py` | idx-signals/research/E9/protocol.json |
| CHECKED | `idx-signals/idxsig/rules/moonshot_e1.py` | idx-signals/research/E1/d1_v1_1/equivalence.json, idx-signals/research/FLOW_IDX_v1/PINS.json, idx-signals/research/LEAD_LADDER_v1/PINS.json, idx-signals/research/PATH_HISTORY_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/rules/moonshot_e3.py` | idx-signals/research/E3/discovery/summary.json, idx-signals/research/E3/reproduce/result.json |
| CHECKED | `idx-signals/idxsig/rules/moonshot_e4.py` | idx-signals/research/E4/v2/CRYPTO/validation/result.json |
| CHECKED | `idx-signals/idxsig/rules/moonshot_e5.py` | idx-signals/research/E5/v1.1/CRYPTO/discovery/summary.json, idx-signals/research/E5/v1.1/CRYPTO/reproduce/result.json, idx-signals/research/E5/v1.1/IDX/discovery/summary.json, idx-signals/research/E5/v1.1/IDX/reproduce/result.json |
| CHECKED | `idx-signals/idxsig/rules/moonshot_g.py` | idx-signals/research/CRYPTO_TUNE_v1/protocol.json, idx-signals/research/E2/CRYPTO/validation/result.json, idx-signals/research/E2/US/validation/result.json, idx-signals/research/E9/protocol.json |
| CHECKED | `idx-signals/idxsig/rules/sandbox.py` | idx-signals/research/E9/protocol.json |
| CHECKED | `idx-signals/idxsig/sources/__init__.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/sources/idx_mirror.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/idxsig/speculation.py` | idx-signals/research/REPLAY_UNITS_v2/data/events_A_BUILD.json, idx-signals/research/REPLAY_UNITS_v2/data/events_B_BUILD.json, idx-signals/research/REPLAY_UNITS_v2/protocol_A.json, idx-signals/research/REPLAY_UNITS_v2/protocol_B.json |
| CHECKED | `idx-signals/tests/test_admission.py` | idx-signals/research/ADMISSION_v1/protocol.json |
| CHECKED | `idx-signals/tests/test_admission_holdout.py` | idx-signals/research/ADMISSION_HOLDOUT_v1/protocol.json |
| CHECKED | `idx-signals/tests/test_crypto_replay.py` | idx-signals/research/CRYPTO_REPLAY_v1/protocol.json, idx-signals/research/CRYPTO_REPLAY_v1/run/RESULT.json |
| CHECKED | `idx-signals/tests/test_liq_rebound.py` | idx-signals/research/LIQ_REBOUND_v1/protocol.json |
| CHECKED | `idx-signals/tests/test_msci_deletion.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json, idx-signals/research/MSCI_DELETION_v1/protocol.json |
| CHECKED | `idx-signals/tests/test_msci_deletion_oot.py` | idx-signals/research/MSCI_DELETION_OOT_v1/protocol.json, idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json |
| CHECKED | `idx-signals/tests/test_msci_deletion_opt.py` | idx-signals/research/MSCI_DELETION_OPT_v1/protocol.json |
| CHECKED | `idx-signals/tests/test_vix_basis.py` | idx-signals/research/VIX_BASIS_v1/protocol.json |
| CHECKED | `kod-machine/kod/detectors.py` | kod-machine/registry/cards/KOD-R-ZEAL-20250312.json, kod-machine/research/ZEALAND_PILOT_v1/01_protocol/protocol.json |
| CHECKED | `tools/collect_premove_crypto.py` | idx-signals/research/ADMISSION_HOLDOUT_v1/protocol.json |

## Guard against regressions
The `workstation` CI job now runs `python3 -m ruff check .` after the style check, so a new lint error fails CI.

## Not in scope
Line length (E501) and other rule families are not selected in `ruff.toml`. Whole-file formatting of unmanaged files
was not run.

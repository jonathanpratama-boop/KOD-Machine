# review:h1-controls:r1 (Review; agent a943c6cf64312277e)

## verdict
accept
## findings
#### severity
minor
#### file
idx-signals/idxsig/controls.py
#### line
29
#### claim
Module docstring misstates v2's relaxation order: volatility is the fourth feature dropped under v2, not 'the second'.
#### evidence
VERSIONS['v2'] = (price_band, liquidity, market_cap, volatility, momentum, drawdown, listing_age) and levels() drops from the end, so the drop order is listing_age, drawdown, momentum, then volatility. test_controls_v3.py line 228-229 repeats the inaccuracy ('dropping it first, which is what v2 did'). Documentation only; no executable effect.
#### fix
Reword to 'it is dropped before market_cap (fourth feature dropped, after listing_age, drawdown and momentum)' in the module docstring and in the test docstring of test_v3_relaxes_volatility_after_market_cap.
#### severity
minor
#### file
idx-signals/idxsig/controls.py
#### line
30
#### claim
The '28% of attempted signals were never matched on volatility under v2' figure is asserted in the module docstring as a fact about the recorded IDX run but was not recomputed in this branch (builder acknowledges it is quoted from RECOMMENDATION.md).
#### evidence
Builder's open_concerns item 1; no code or test in the diff derives it. It is a coverage share, not performance, but a source-level docstring stating a measured number that the branch cannot verify invites later misquotation.
#### fix
Attribute it explicitly in the docstring ('per handoff/kod-next-move/synthesis/RECOMMENDATION.md, not recomputed here') or drop the figure and keep the qualitative rationale.
#### severity
minor
#### file
idx-signals/idxsig/cli.py
#### line
91
#### claim
`--controls-version` choices are ('v2','v1'), so the `run` subcommand cannot select v3 from the command line; only programmatic callers (RunConfig, e3/e4-style harness_config) can.
#### evidence
cli.py:91 `p_run.add_argument("--controls-version", choices=("v2", "v1"), default="v2", ...)`. Not an owned file; builder reported it under needs_other_file. E5's own stages are to go through e5.py harness_config, so this does not block the protocol's use of v3.
#### fix
In cli.py (its owner): add "v3" to choices, keep default "v2"; extend the help text.
## test_rerun_tail
$ cd <worktree>/idx-signals && python3 -m unittest
..................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 258 tests in 41.830s

OK

$ python3 -m idxsig rules (tail)
E4_CAND_G2_RET30 v1 DETECTOR hold=5 sha=362a9207a418 source-audit=passed
E4_CAND_G2_RET30_BEAR v1 DETECTOR hold=5 sha=5d4665925e15 source-audit=passed
E4_CAND_G7_MOMENTUM5_30 v1 DETECTOR hold=5 sha=0378c8b43d27 source-audit=passed
E4_CAND_G7_MOMENTUM5_30_BEAR v1 DETECTOR hold=5 sha=816abcb4a2a2 source-audit=passed
MOONSHOT_E1_D1 v1.1 DETECTOR hold=5 sha=648a06e1079f source-audit=passed
MOONSHOT_E2_CRYPTO_D1 v1 DETECTOR hold=5 sha=d8218f2e9c9b source-audit=passed
MOONSHOT_E2_US_D1 v1 DETECTOR hold=5 sha=c21126d8ba9d source-audit=passed
MOONSHOT_E4_D1 v1 DETECTOR hold=2 sha=f5585be5d967 source-audit=passed
PLACEBO_COINFLIP v1 PLACEBO hold=5 sha=b774201b08e6 source-audit=passed
USER_RULE PENDING: rule text not supplied
rules exit=0

$ python3 -m idxsig verify-runs
verify-runs: OK

$ cd <worktree> && python3 tools/check_append_only.py --all
append-only: OK

$ git diff ae2cbee --name-only
idx-signals/idxsig/controls.py
idx-signals/tests/test_controls_v3.py

Reviewer mutation check (scratch copy of idxsig+tests outside the repo, tests.test_controls_v3 only; 14 tests each):
  v3 volatility override set back to 3 buckets/'tercile'      -> FAILED (failures=5)
  VERSIONS['v3'] set to v2's order                            -> FAILED (failures=4)
  features() volatility bucket count hard-coded to 3          -> FAILED (failures=3)
  coverage() uses FEATURES[name] instead of feature(name, v)  -> FAILED (failures=2)
Reviewer notes: rule sha (rules/__init__.py:55-57) hashes the rule body only, so the controls.py change does not move any rule sha; rules/audit.py lists 'controls' only as a forbidden attribute for rules. backtest.run already routes cfg.controls_version into features/matched_draws/VERSIONS/level_names/coverage and summary['harness']['controls'] (backtest.py:372-396, 546); e3.py:71 and e4.py:76 pass h['controls_version'] through. v3 path in features() differs from v2 only by the bucket count argument; masking by m.present precedes every cross-sectional rank, and the truncation test covers v3. _codes packs base 8 with max digit 6, within range.

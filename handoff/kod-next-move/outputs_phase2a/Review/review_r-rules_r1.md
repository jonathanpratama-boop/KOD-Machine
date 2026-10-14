# review:r-rules:r1 (Review; agent a5816484999e4401a)

## verdict
fix_required
## findings
#### severity
serious
#### file
idx-signals/idxsig/rules/moonshot_e5.py
#### line
282
#### claim
flags()/debounce() treat a session with no score (NaN, i.e. the WARMUP columns) as 'outside the set', so at the first evaluable column of every view (WARMUP = 60) every name currently in the top set fires at once, and the five sessions after that over-flag too. Flags are therefore not window-invariant: the same session gets different flags depending on where the run window starts, which defeats the protocol's reason for the 60-session lead-in ('features warm at period start') and deviates from the protocol text 'first session a name enters the top 0.5% after >= 5 sessions outside it' (a NaN session is not a session outside the set). The same applies to the debounced A0/A1 rules.
#### evidence
Probe on open_panel(n_tickers=30, n_sessions=200, seed=5) with the test fixture frozen_us_a(threshold=1.9): full window flags at session 80 = 2 (names in the set at 80 = 9); the same session as column 60 of m.slice(20, 200) = 9 flags. Flags per session 60..64 of the shifted window [9, 7, 3, 5, 2] vs the same sessions in the full window [2, 1, 1, 2, 2]; total flags over the common range 193 vs 175 (+10%). tests/test_e5_rules.py::test_debounce_flags_the_first_session_above_after_five_below freezes this semantics (s[2, :5] = nan -> flag at 5). Under the protocol's harness contract (window starts 60 sessions before the period, compute NaN there) the burst lands on the first period session of every discovery/validation run and inflates stage-1 flag counts/precision there.
#### fix
Make the debounce require DEBOUNCE sessions of known state: compute ranks/scores on the unmasked raw features, build state = isfinite(score) & (score >= thr), and require the trailing DEBOUNCE sessions to be finite AND outside (e.g. known = _lagb(isfinite(score), k) for k in 1..5; ok &= known & ~_lagb(state, k)); then apply _warm only to compute()'s output. Because brk60/dd60/vol60 are only window-invariant from column 60, either mask compute() for the first WARMUP + DEBOUNCE columns (and have e5.py start the window WARMUP + DEBOUNCE sessions early) or set WARMUP = 65 for the flags; update the docstring (line 32) and the test row s[2] accordingly. Any choice is fine as long as the first flag a window can emit has five real out-of-set sessions behind it and the lead-in covers it.
#### severity
minor
#### file
idx-signals/idxsig/rules/moonshot_e5.py
#### line
39
#### claim
The docstring (and the builder's report) says family_flags() returning all-False for unfrozen arms lets 'a feature table or a study' be built, but e1.Study(family_module=moonshot_e5) crashes: e1.Study._signals does flags[next(k for k in flags if 'IGNITION' in k)] and no E5 candidate name contains IGNITION.
#### evidence
python3: e1.Study(df, {**meta, 'format': 'panel-v2'}, family_module=moonshot_e5) on random_walk_panel(30, 160, seed=11) -> StopIteration. RECOMMENDATION.md line 112 already plans the fix in idxsig/e1.py ('guard sig["ign"] when the family has no IGNITION member') and line 115 plans e5.py build_dataset 'via Study'.
#### fix
needs_other_file: idx-signals/idxsig/e1.py (guard the IGNITION lookup, e.g. sig['ign'] = NaN/0 array when no member matches) must land before e5.py builds a Study on this family; until then reword the docstring at line 39 to say a feature table can be built from features()/family_flags() directly, not via e1.Study.
#### severity
minor
#### file
idx-signals/idxsig/rules/moonshot_e5.py
#### line
243
#### claim
compute() is roughly 12x the cost of moonshot_g.features at panel scale, and rules.causal_signals calls it once per session, so a full-window IDX run of one E5 candidate is hours of CPU; rank_features alone spends ~6 s per call on DataFrame.rank(axis=0) over a names x sessions frame, which is 3x slower than ranking the transpose along axis=1.
#### evidence
900 names x 1500 sessions synthetic: moonshot_g.features 1.76 s; e5.raw_features 11.53 s (of which _rebase 1.18 s); e5.rank_features 5.73 s; e5.features total 20.96 s. One DataFrame.rank(axis=0) on (names x sessions) 0.49 s vs rank(axis=1) on the transpose 0.16 s. A ~540-session IDX discovery window (480 + 60 lead-in) means ~540 prefix calls of average half length: on the order of 45-90 min per candidate run on IDX, more on crypto; unit tests went 33 s -> 49-53 s.
#### fix
Rank on the transpose (pd.DataFrame(np.where(pool, f[name], nan).T).rank(axis=1, method='average').to_numpy().T) and compute the count from the same frame; consider hoisting the seven rolling medians through one DataFrame per source series. Semantics unchanged (same ranks), so no test needs to move; document the expected run time in e5.py so signal_cache is used across plans and sensitivities.
#### severity
minor
#### file
idx-signals/idxsig/rules/moonshot_e5.py
#### line
228
#### claim
Binary features with an undefined input collapse silently to 0: not_repriced = ret20 < 0.30 is 0 (i.e. 'repriced') when ret20 is NaN (name listed < 20 sessions ago), and quiet is 0 whenever rngr5/ret5/vol20 are NaN. The logistic fit sees 'repriced'/'not quiet' for 'unknown', and A1 = A0 & not_repriced is suppressed for young names even when A0 holds; this is not stated in the docstring or the protocol's feature definitions.
#### evidence
raw_features: not_repriced = ret20 < NOT_REPRICED_MAX with ret20 NaN -> False; quiet = (rngr5 <= 1.0) & (|ret5| <= 2 vol20 sqrt 5) with any NaN -> False; detector_states uses f['not_repriced'] == 1.0. No test covers the NaN-input case for the binaries.
#### fix
Either document the convention (unknown -> 0) in the docstring and the protocol's binary_unranked text, or make not_repriced NaN-safe the way F8_ARA_EARLY does (np.nan_to_num(ret20, nan=9.0) < 0.30 treats unknown as repriced, explicitly) and add a one-line test for a name listed fewer than 20 sessions before t.
#### severity
minor
#### file
idx-signals/tests/test_e5_rules.py
#### line
21
#### claim
The idx-signals test suite now depends on a file outside the package (kod-machine/research/ZEALAND_PILOT_v1/03_card/price_facts.py, loaded by path and exec'd); no other idx-signals test does this, so the suite breaks if idx-signals is run outside the monorepo layout.
#### evidence
grep -ln 'kod-machine' idx-signals/tests/*.py -> only tests/test_e5_rules.py; PRICE_FACTS = ROOT / 'kod-machine' / 'research' / ... with ROOT = parents[2]. The file is read only (exec defines functions; main() is not called), so the append-only rule is respected.
#### fix
Keep the cross-check (it is the best test in the file) but guard it with unittest.skipUnless(PRICE_FACTS.exists(), ...) and keep a pure in-file reference for the creep/quiet arithmetic so the pre-spike block stays tested without the sibling package.
## test_rerun_tail
$ cd <worktree>/idx-signals && python3 -m unittest
......................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 262 tests in 48.779s

OK

$ python3 -m idxsig rules   (tail)
E5_CAND_A0_CREEP_QUIET v1 DETECTOR hold=5 sha=710bb3f81baf source-audit=passed
E5_CAND_A1_CREEP_QUIET_NR v1 DETECTOR hold=5 sha=9340180f3e82 source-audit=passed
E5_CAND_CRYPTO_A v1 DETECTOR hold=5 sha=d53a52617429 source-audit=passed
E5_CAND_CRYPTO_B v1 DETECTOR hold=5 sha=e24cb3823f24 source-audit=passed
E5_CAND_IDX_A v1 DETECTOR hold=5 sha=1e9e6b8e0efe source-audit=passed
E5_CAND_IDX_B v1 DETECTOR hold=5 sha=5261fa817413 source-audit=passed
E5_CAND_US_A v1 DETECTOR hold=5 sha=3b8c33e7e965 source-audit=passed
E5_CAND_US_B v1 DETECTOR hold=5 sha=3c1980aca606 source-audit=passed
MOONSHOT_E1_D1 v1.1 DETECTOR hold=5 sha=648a06e1079f source-audit=passed
MOONSHOT_E2_CRYPTO_D1 v1 DETECTOR hold=5 sha=d8218f2e9c9b source-audit=passed
MOONSHOT_E2_US_D1 v1 DETECTOR hold=5 sha=c21126d8ba9d source-audit=passed
MOONSHOT_E4_D1 v1 DETECTOR hold=2 sha=f5585be5d967 source-audit=passed
PLACEBO_COINFLIP v1 PLACEBO hold=5 sha=b774201b08e6 source-audit=passed
USER_RULE PENDING: rule text not supplied

$ python3 -m idxsig verify-runs
verify-runs: OK

$ cd <worktree> && python3 tools/check_append_only.py --all
append-only: OK

Review notes (READ-ONLY, nothing edited or committed): git diff ae2cbee --stat = rules/__init__.py (+2/-2, additive registry entry), rules/moonshot_e5.py (new, 373), tests/test_e5_rules.py (new, 423); no other file touched; untracked .githooks/post-* are git-lfs hooks created at worktree setup (07:30, before the commit), not part of the change. Defaults: no existing module source, argument, column, key or threshold changed; pre-existing rule shas unchanged by construction (their module sources are untouched) and verify-runs OK. Look-ahead: every window is trailing (_roll/_lag/_lagb, _rebase peak/min5/pre, debounce), ranks are masked by present & tradeable before ranking, the cross-sectional median is the moonshot_g one, and test_ranks_are_prefix_first plus causal_signals on a frozen arm and on A0/A1 pass with 0 mismatches. API: compute(view) reads only RULE_FIELDS (open, value, lock_up included), FEATURE_ARGS works with getattr(view, a) as paper.py/e1.Study do, Rule(kind DETECTOR, plan None) resolves to the original plan in backtest.resolve_plan; audit passes. Pre-spike block equals kod-machine price_facts.measures() for every t in 60..89 on the designed episode (checked by the test; the A0 conjunction matches kod/detectors.py _volume_creep). needs_other_file: idx-signals/idxsig/e1.py (IGNITION guard, already in RECOMMENDATION.md line 112) before e5.py uses Study on this family.

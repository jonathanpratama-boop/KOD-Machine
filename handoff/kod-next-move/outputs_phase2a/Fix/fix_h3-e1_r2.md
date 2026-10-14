# fix:h3-e1:r2 (Fix; agent a174d48d16c173909)

## branch
e5/h3-e1
## commit
8fbd4474d03d89bb25846f7754b28d704836b102
## files_changed
- idx-signals/idxsig/e1.py
- idx-signals/tests/test_e1_study_opts.py
## api_added
- Study.study_options(self) -> dict | None  # {"panel_format": str, "pool_units": str, "pool_version": str, "pool_keys": list[str]} when any E5 option is on; None on the recorded E1/E2 path
- Study.legacy_panel_format: str  # "panel-v2" on IDX, "panel-global-v1" elsewhere (the format the recorded E1/E2 studies expected)
- summary.json key "study_options" (run_discovery) and result.json key "study_options" (run_validation), emitted only when Study.study_options() is not None
## behaviour_summary
Round 2 fix for the serious finding at e1.py run_discovery/run_validation. Study now exposes study_options(): None when (pool_units, pool_version, panel_format) == ("panel", "v1", legacy_panel_format), otherwise {panel_format, pool_units, pool_version, pool_keys}. run_discovery adds summary["study_options"] and run_validation adds result["study_options"] only when that is not None, so a result directory produced with the v3 pool, as-traded bands, or a non-legacy panel format (e.g. the US repair panel panel-global-v2-units) self-describes which detection pool its controls were matched on, mirroring how e3/e4 record their config. I went slightly beyond the reviewer's suggested trigger: a non-legacy panel_format alone also triggers the block (a default-pool study on panel-global-v2-units would otherwise look identical in its outputs to the recorded E2 run on panel-global-v1). On E1 (IDX, panel-v2) and E2 (US/CRYPTO, panel-global-v1) the legacy format is what the protocol resolves to, so their key sets are unchanged. _declared_panel_format now reads self.legacy_panel_format instead of recomputing it (same value). The Study docstring notes the self-description.
## tests_added
- tests/test_e1_study_opts.py::StudyOptionsRecorded::test_the_default_path_writes_no_study_options_key (IDX bare, IDX with explicit legacy keywords, E2 US on panel-global-v1: study_options() is None and the key is absent from the returned dicts and from summary.json / result.json on disk; asserts the exact recorded E1 summary key set)
- tests/test_e1_study_opts.py::StudyOptionsRecorded::test_v3_pool_is_recorded (pool_version="v3": block present in both stage outputs with pool_keys [price_band, liquidity, volatility, market_cap], pool_units panel, panel_format panel-v2)
- tests/test_e1_study_opts.py::StudyOptionsRecorded::test_as_traded_bands_are_recorded (pool_units="as_traded" on the US units panel: block present with pool_units as_traded, pool_version v1, panel_format panel-global-v2-units)
- tests/test_e1_study_opts.py::StudyOptionsRecorded::test_a_non_legacy_panel_format_alone_is_recorded (US study on panel-global-v2-units with the default pool: block present; legacy_panel_format is panel-global-v1 on US and panel-v2 on IDX)
## test_output_tail
$ python3 -m unittest   (from <worktree>/idx-signals)
..............................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 270 tests in 68.266s

OK

$ python3 -m idxsig rules   (tail)
E4_CAND_G7_MOMENTUM5_30 v1 DETECTOR hold=5 sha=0378c8b43d27 source-audit=passed
E4_CAND_G7_MOMENTUM5_30_BEAR v1 DETECTOR hold=5 sha=816abcb4a2a2 source-audit=passed
MOONSHOT_E1_D1 v1.1 DETECTOR hold=5 sha=648a06e1079f source-audit=passed
MOONSHOT_E2_CRYPTO_D1 v1 DETECTOR hold=5 sha=d8218f2e9c9b source-audit=passed
MOONSHOT_E2_US_D1 v1 DETECTOR hold=5 sha=c21126d8ba9d source-audit=passed
MOONSHOT_E4_D1 v1 DETECTOR hold=2 sha=f5585be5d967 source-audit=passed
PLACEBO_COINFLIP v1 PLACEBO hold=5 sha=b774201b08e6 source-audit=passed
USER_RULE PENDING: rule text not supplied

$ python3 -m idxsig verify-runs
verify-runs: OK

$ python3 tools/check_append_only.py --all   (from <worktree>)
append-only: OK

Sanity check that the new tests catch the defect (e1.Study.study_options stubbed to always return None, i.e. the pre-fix behaviour, then StudyOptionsRecorded run alone):
Ran 4 tests in 10.393s
FAILED (failures=3)
failures: ['test_a_non_legacy_panel_format_alone_is_recorded', 'test_as_traded_bands_are_recorded', 'test_v3_pool_is_recorded']
## defaults_unchanged_evidence
The new key is guarded by study_options() returning None whenever pool_units == "panel", pool_version == "v1" and panel_format equals the legacy expectation; E1's protocol resolves to panel-v2 on IDX and E2's to panel-global-v1 on US/CRYPTO, so every recorded E1/E2 configuration hits the None branch and summary.json / result.json keep exactly their previous key sets. test_the_default_path_writes_no_study_options_key asserts the key is absent on disk for the bare IDX study, the IDX study with explicit legacy keywords, and the E2 US study on its legacy panel, and asserts the exact 12-key recorded summary key set. The pre-existing DefaultsUnchanged class (bare call equals explicit legacy keywords across detector_table, episodes, matched_controls, signal_stats and evaluate) still passes; the full suite is 270 = 244 base + 26 in test_e1_study_opts.py, 0 failures; verify-runs OK confirms the recorded run directories still verify. No existing argument, column, key or default changed meaning; the only computational change in e1.py is that _declared_panel_format reads the same legacy string from an attribute instead of recomputing it.
## needs_other_file

## open_concerns
- Trigger is slightly wider than the reviewer's suggested (pool_units, pool_version) != ("panel", "v1"): a non-legacy panel_format alone also emits study_options. This is deliberate (a default-pool study on the US repair panel should not be indistinguishable from the recorded E2 run) and does not affect E1/E2 re-runs, whose panel formats are the legacy ones. If the orchestrator wants the narrower trigger, it is a one-line change in Study.study_options plus dropping test_a_non_legacy_panel_format_alone_is_recorded.
- Untracked .githooks/post-checkout, post-commit, post-merge, pre-push were present in the worktree before this round and were left untouched and uncommitted (not mine, not owned).

# fix:h3-e1:r1 (Fix; agent a149312f2dc7e1bf5)

## branch
e5/h3-e1
## commit
45d98364fc9010b4c2f42d7a5cf1d9d1f945eae6
## files_changed
- idx-signals/idxsig/e1.py
- idx-signals/tests/test_e1_study_opts.py
## api_added
- e1.Study(panel_df, panel_meta, protocol_path=PROTOCOL, profile=None, family_module=None, pool_units="panel", pool_version="v1", panel_format: str | None = None)  # new keyword; validated against e1.PANEL_FORMATS, overrides the protocol's declaration
- protocol["markets"][<profile.market>]["panel_format"]  # new optional protocol key read by e1.Study when that markets entry is a dict; takes precedence over protocol["data"]["panel_format"]
- e1.Study._declared_panel_format(proto: dict, override: str | None) -> str  # resolution order: keyword > markets.<market>.panel_format > data.panel_format > legacy (panel-v2 on IDX, panel-global-v1 elsewhere)
## behaviour_summary
Fixes the reviewer's serious finding: one frozen E5 protocol file can now serve IDX (panel-v2), US (panel-global-v2-units) and CRYPTO (panel-global-v1) studies with a single protocol_sha256. e1.Study resolves the panel format it needs in this order: the new Study(panel_format=...) keyword; protocol["markets"][<profile.market>]["panel_format"] when that entry is a dict carrying the key; the existing global protocol["data"]["panel_format"]; then the legacy expectation. Every named format (keyword, per-market or global) must be in PANEL_FORMATS, and panel_meta["format"] is still held to the resolved value, so a mismatched panel is still refused. Error messages name the source of the declaration (panel_format=, <id> markets.<market>.panel_format, <id> data.panel_format). No other line of Study changed; the global-key behaviour from the previous commit is kept.
## tests_added
- tests/test_e1_study_opts.py::PerMarketPanelFormat::test_one_protocol_builds_the_idx_and_the_us_study (the reviewer's scenario: one protocol with markets.IDX=panel-v2 and markets.US=panel-global-v2-units builds an IDX study on jumpy_panel and a US study on us_panel with equal protocol_sha == sha256_file(protocol); mismatched panels refused for both markets)
- tests/test_e1_study_opts.py::PerMarketPanelFormat::test_the_market_entry_wins_over_the_global_key (per-market beats data.panel_format; a market without an entry falls back to the global key)
- tests/test_e1_study_opts.py::PerMarketPanelFormat::test_the_keyword_overrides_the_protocol (keyword accepted on a protocol with no declaration or a different one; keyword held against the panel; unknown keyword refused; keyword on the default E1 study refused when mismatched)
- tests/test_e1_study_opts.py::PerMarketPanelFormat::test_draft_style_string_entries_and_entries_without_a_format_fall_through (E5-draft string entries and E2's dict entries without panel_format resolve to the legacy/global expectation; asserts E1 protocol has no markets block, E2 has no data block and no panel_format in any market entry)
- tests/test_e1_study_opts.py::PerMarketPanelFormat::test_unknown_per_market_formats_are_refused (typo in markets.IDX.panel_format refused; an unknown name under another market does not affect this study)
- protocol_with() helper gained a markets= parameter to write a markets block into a temp copy of E1/E2's protocol (9 new test assertions-sets across 5 test methods; file now 22 tests, up from 13)
## test_output_tail
=== python3 -m unittest (from idx-signals) ===
----------------------------------------------------------------------
Ran 266 tests in 61.248s

OK
=== python3 -m idxsig rules ===
E4_CAND_G7_MOMENTUM5_30 v1 DETECTOR hold=5 sha=0378c8b43d27 source-audit=passed
E4_CAND_G7_MOMENTUM5_30_BEAR v1 DETECTOR hold=5 sha=816abcb4a2a2 source-audit=passed
MOONSHOT_E1_D1 v1.1 DETECTOR hold=5 sha=648a06e1079f source-audit=passed
MOONSHOT_E2_CRYPTO_D1 v1 DETECTOR hold=5 sha=d8218f2e9c9b source-audit=passed
MOONSHOT_E2_US_D1 v1 DETECTOR hold=5 sha=c21126d8ba9d source-audit=passed
MOONSHOT_E4_D1 v1 DETECTOR hold=2 sha=f5585be5d967 source-audit=passed
PLACEBO_COINFLIP v1 PLACEBO hold=5 sha=b774201b08e6 source-audit=passed
USER_RULE PENDING: rule text not supplied
=== python3 -m idxsig verify-runs ===
verify-runs: OK
=== python3 tools/check_append_only.py --all (from worktree root) ===
append-only: OK
## defaults_unchanged_evidence
(1) The only code path touched is the panel-format resolution; the diff to e1.py is 45 changed lines (docstring/comment, one new keyword with default None, one new method, two lines in __init__ replaced by a call to it). (2) On the real protocols the resolver returns exactly the previous expectations: E1 protocol.json + IDX -> panel-v2; E2 protocol.json + US -> panel-global-v1; E2 + CRYPTO -> panel-global-v1 (printed from Study._declared_panel_format with override=None). (3) The structural facts that make the new keys inert on recorded protocols are asserted in tests: E1's protocol has no "markets" key; E2's protocol has no "data" key and every markets entry is a dict without "panel_format"; the E5 draft's markets entries are plain strings (reproduced in the test, which proves string entries are ignored). (4) The pre-existing DefaultsUnchanged class (bare Study == explicit legacy options on detector_table, episodes, matched_controls, signal_stats, evaluate; unit_factor column alone changes nothing; E1 protocol still refuses a panel-v1 panel) still passes. (5) verify-runs OK confirms every recorded run still re-verifies.
## needs_other_file
- idx-signals/research/E5/protocol.json (when frozen by the Phase 2b owner): to use the per-market path, give each entry of its markets block a dict with a panel_format key (IDX: panel-v2, US: panel-global-v2-units, CRYPTO: panel-global-v1); the draft's string entries fall through to the legacy expectation, which would wrongly expect panel-global-v1 for the US repair panel. Alternatively e5.py can pass Study(panel_format=...) per market without touching the protocol.
## open_concerns
- The reviewer's probe (E1 protocol copy with a global data.panel_format=panel-global-v2-units run on an IDX panel-v2 panel) still raises by design: a global declaration that contradicts the panel is a mismatch. The fix is the per-market entry or the keyword, both now available and tested.
- The previous round's needs_other_file note ('use a protocol whose data.panel_format names panel-global-v2-units') is superseded by this change; no per-market protocol files are needed.

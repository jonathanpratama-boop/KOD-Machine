# US repair status

Base GitHub commit: 1420ee68ac1da2f063bfaf96a1bd374701f23a05 (download ZIP comment independently read by director; source audit itself lacked .git). Remote review branch hermes/us-data-repair-v1 created and read back. Source snapshot local, not authenticated Git clone.

Completed locally: frozen US_DATA_REPAIR_PROTOCOL_v1.md; independent source audit; reproduce_source_findings.py executed actual _finish and paper.score on synthetic 2020 fixtures. Confirmed future-bar deletion of past input, and split-between-signal-and-entry cost-unit error. No raw market panel or holdout opened. Third issue (final-volume opening fills) source-reviewed, not yet function-level reproduced.

New opt-in idxsig/price_units.py with split-only adjustment/coverage contract, distinct contemporaneous price conversion and explicit volume convention. 5 new tests failed before implementation; full IDX suite now 123 tests passing (7.010s). No existing strategy/panel/scorer replaced or production behavior changed. This is a primitive, not integrated repair or real-source adjustment validation.

Outstanding: integrate versioned causal preprocessing and correct date-specific execution units, reproduce final-volume fill issue, full price/volume provider convention validation, raw-manifest completeness scan, originals access, corrected detector+baseline rerun, SEC fetcher, independent repair audit, remote code publication/PR. Original data missing from Git per audit brief. Do not substitute fresh Yahoo pulls for original dataset. No completed repaired result or quantified historical impact.

Completed additional local repair: global_panel._finish no longer deletes earlier observations based on later reversal. Old algorithm remains explicit _finish_legacy_v1; new panel format panel-global-v2. Three regression tests failed before fix; full suite now 126 tests passing (6.926s), saved CAUSAL_PANEL_REPAIR_TEST_RESULT.json. Existing E1 admission expects v1 and must receive an explicit versioned compatibility review before repaired-panel reruns; no historical result recomputed. Original reproduction script intentionally demonstrates the old behavior and needs version-aware adjustment before rerun. Manifest completeness check still outstanding.

Latest checkpoint: REPAIR_CHECKPOINT_v2.md and REPAIR_CHECKPOINT_v2.json. US paper scorer has opt-in effective-session units; full suite 130 tests passing (6.712s). Opening-volume defect functionally reproduced, preserved as ex-post model under protocol. Input audit confirms all 5,705 original raw payloads and original panel absent locally. Manifest QA unexpectedly exposed 2024+ illustrative prices; deviation documented in checkpoint, not used for tuning. No complete repaired rerun or independent repair certification.

Remote has branch only; new code/report/protocol remain local. No background task remains. Overall: PARTIALLY REPAIRED — SPECIFIED LIMITATIONS.

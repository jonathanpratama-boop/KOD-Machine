# Repair checkpoint v2 — partial, local only

## Executed
- Original raw manifest matches the hash in the panel manifest. Exactly 5,705 unique payload records are declared; all 5,705 payload files are absent in this repair tree. The original compressed panel is absent too. Presence audit lists every missing path in ORIGINAL_INPUT_PRESENCE_v1.json. No raw/panel payload was opened.
- Reproduced final-volume dependence in actual execute(): identical $10 opening prices with different final daily volume yield SKIP_LIQUIDITY versus EXITED. Kept unchanged per frozen repair protocol: this is an ex-post capacity model, not causal opening execution.
- Added explicit opt-in paper.score(..., price_units=...) for US split-only units. Reconciles recorded signal price against declared complete action schedule; entry and exit cost tiers use their respective effective-session prices. Stop/chase comparisons remain in the common adjusted coordinate system. Unsupported convention, incomplete coverage and unreconciled signal units are rejected.
- Legacy scorer remains default for comparison; no production scorer or ledger was run. New outcome version labels distinguish paths. Metadata assertions are upstream audit prerequisites, NOT independent verification of Yahoo conventions.
- New scoring test failed before implementation. Expanded regression coverage: entry-boundary split, exit-boundary split, action after window, incomplete/unknown metadata, reconciliation and immutable decision input. Full suite: 130 tests in 6.712s, OK. Synthetic verification is not historical validation.

## Information-exposure deviation
Reading the panel manifest without filtering its QA fields exposed several illustrative 2024+ price rows embedded in metadata. No raw panel, holdout evaluation or holdout outcome file was opened, and those examples were not used for implementation/tuning. Nevertheless the claim of zero exposure to any 2024+ prices cannot be maintained. Preserve this deviation; future manifest inspection must project only filenames, hashes and counts before returning output. Strict untouched-holdout certification requires independent review of this exposure.

## Still required
- Verified provider OHLC/volume conventions and complete corporate-action coverage; evidence-backed input adapter, ticker/source bindings and provenance for scoring metadata.
- Execution sizing and price-band/control integration; E1 explicit v2 compatibility; full corrected strategy AND baseline rerun after original inputs are supplied.
- Fix/re-version old reproduction harness to explicitly call legacy preprocessing without overwriting the original evidence.
- SEC retrieval deliverable, independent repair review, publish review branch changes/PR. GitHub has branch only; no local changes published.

No detector optimization, new market retrieval, historical performance estimate or production deployment occurred. Files hashed in REPAIR_CHECKPOINT_v2.json. Verdict: PARTIALLY REPAIRED — SPECIFIED LIMITATIONS.

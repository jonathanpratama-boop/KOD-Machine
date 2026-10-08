# US_DATA_REPAIR_PROTOCOL v1

Status: frozen repair specification, not a completed experiment. Base snapshot: GitHub 1420ee68ac1da2f063bfaf96a1bd374701f23a05, archive SHA256 51177c7adbf7545c7664b10f200e6f2b6847370d0214f1bf3b2e86f96ca96543. Remote review branch: hermes/us-data-repair-v1. Local snapshot lacks Git history; original KOD workspace untouched.

## Fixed experimental scope
Reproduce E2 US 2023 validation only. Preserve frozen detector, thresholds, notional, entry lag, holding period and cost schedule. No holdout or 2024+ outcome inspection. No live scans, money movement, ASTRA change or secret extraction. Keep original results and ledgers immutable. Reruns and corrections receive new versions. Do not infer matched lift from detector-only re-costing.

## Input gate
Original run: results/runs/20261008T060443Z_MOONSHOT_E2_US_D1_v1. Raw manifest yahoo_us-20261008T001812Z.jsonl and panel manifest panel_us-20261008T004105Z.json. Original raw/panel payloads are absent from archive per audit brief; verify paths/hashes before any rerun. New retrieval is a new dataset, not exact reproduction. Corporate-action reconstruction may use later split records only as measurement metadata, never predictive covariates.

## Representation contract
Keep provider prices unchanged. Add explicit as-traded prices from a verified complete action schedule and independently established provider adjustment convention. For split-adjusted-to-reference prices, as-traded price on session d equals adjusted price times the product of new-shares/old-shares for actions effective strictly after d through adjustment reference. Volume convention must be explicitly declared; do not assume Yahoo adjusts volume identically to OHLC. Preserve both price coordinate systems; determine entry and exit units separately. Unknown action history, unsupported rights/mergers, invalid ratios, or missing coverage blocks reconstruction. Action effectiveness is exchange-session dated; same-session action is already in that session's units. Cash-in-lieu/fractional share conventions require separate treatment.

## Additional source findings to reproduce
1. _finish uses future reversion to remove past rows; verify prefix invariance failure on synthetic input. A causal replacement must preserve raw past observations and record retrospective QA separately, versioning panel semantics.
2. Opening entry checks final same-session volume; classify as ex-post capacity model, not causal execution. Preserve original strategy for mechanical repair, disclose limitation; replacing fill model needs its own comparison, not hidden optimization.
3. Paper cost tiers restore signal-date units rather than entry-date units if action occurs in between; reproduce without writing real ledger.

## Required tests
Forward/reverse/multiple splits, actions on signal/entry/exit boundaries, post-window actions, unchanged securities, unknown action/volume conventions, coverage failure, raw hashes, price-band and share-sizing effects, stops/chase conversions, distinct entry/exit cost tiers, session counts and open/close timing. Synthetic tests do not prove provider conventions on real data.

## Outcome gate
Rebuild eligibility, controls, flags, attempts, skips, fills, costs and outcomes on both strategy and matched baseline. Reconcile all denominator discrepancies. Preserve diagnostic vs full-rerun distinction. Pin dependencies and freeze inputs. Independent review required before calling repaired. Report REPAIRED AND REPRODUCIBLE, PARTIALLY REPAIRED — SPECIFIED LIMITATIONS, or BLOCKED — SPECIFIC MISSING CAPABILITY. Until raw coverage and causal defects are resolved, no validated detection/execution claim.

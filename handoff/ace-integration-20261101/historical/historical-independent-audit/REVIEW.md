# Independent pre-outcome daily shared-account replay review

2026-11-01 UTC. Reviewer: audit_account_concurrency. Review uses invented tapes only. No historical archive rows, historical account returns, external request or outcome-guided variant was used in this review.

## Scope and decision
Technically clear for one canonical already-selected exploratory replay on the pinned existing local inputs, subject to parent go and exact final source pins. Not live execution, quote/depth parity, profitability validation, or a new holdout. Existing data were already exposed in prior research. No arbitrary extra scenarios or tuning authorized.

Protocol_v1 plus its explicit pre-outcome addendum define two independently initialized 10,000-USDT accounts per fixed policy: development baseline/decision 2017-09-26 through 2023-01-01 opening; reused validation baseline/decision 2023-01-01 through 2026-09-30 opening. The original development start Aug17 is NOT preserved as a scored date: Aug17–Sep25 provide the first40 earlier closes. This is a material window/account-design difference from the prior per-asset study and must accompany any comparison. No account restarts within either partition after a kill. Four fixed labels include trend, risk-matched passive buy-once, cash, and clearly differently risked conventional no-kill buy-and-hold.

## Evidence
27 tests = 13 author + 14 independent pass normal Python and optimized `-O`, with socket connect functions blocked. See combined-normal.txt, combined-optimized.txt; run `python historical-independent-audit/run_combined.py` (or `python -O ...`). Independent fixtures are test_independent.py. prefinal.txt preserves the discovered availability failure before repair, superseded by final combined results.

Verified source-only loader scope: exact allowlist and manifest SHA checks,220 approved archive byte hashes/sizes, contained paths, expected sole CSV member, daily column counts/timestamp units/UTC boundaries/OHLC sanity,3332 unique consecutive aligned days per symbol. Validation exceptions are explicit, not assert-only. No loader invocation or archive inspection occurred in this review; actual data validity remains to be established by the approved run before returns.

Original v2 file hash remains dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3; accounting core hash29688797f6738e4aa02ca87403a5a90d60dec0bca54cffab36a4a4a7e266f8a6. Independent synthetic comparison confirms exact original signal/raw-normalized target results; reserve/cancel_pending/sharpe_status ASTs match. Reused mechanics are not claimed identical where the daily profile explicitly changes observation/fill timing, marks, capacity and lifetime.

## Causality and accounting
- Assumed close/volume availability is precisely next day00:01, never claimed actual historical receipt/publication. Decisions at00:01 use40 strictly earlier consecutive closes. Fill uses a genuinely later opening, never the just-passed same-date open. No invented subsecond receipt, BBO or observed depth.
- Frozen per-intent capacity is0.1% of the latest volume already available at intent creation: T-2 at midnight, T-1 at00:01. This is a synthetic capacity assumption, not evidence of executable liquidity. New kill/residual intents cannot fill at creation time.
- Atomic pair of opening reference marks precedes risk/fills; per-symbol observations cannot replace a batch price. Sells precede buys. Shared cash/reserves, frozen buy budgets with future-price affordable quantities, and frozen sell quantities were tested under price gaps. Fees are separately half-up cents; modeled slippage is adverse. Independent fill arithmetic reconciles exact cash, holdings and commissions with no negative cash or gross exposure over1.
- Persistent drawdown/90-return kill,91-clean-mark warmup, unknown held marks and zero-variance handling checked. Initial capital enters the peak. Controls share execution/cost/date assumptions; no-kill control explicitly differs in risk policy, so it is not evidence of strategy-only alpha.
- Terminal flat target is preplanned; final opening may leave capacity-limited residuals, which stay marked. Synthetic tests show terminal close/volume changes cannot alter journals/results. Final cash is not equated with NAV while holdings remain.
- Journal duplicate retry/conflict, deterministic rerun equality, independent core replay, torn-tail and hash tampering rejection exercised. Offline writer is explicitly new-file/linear, not a production multiwriter service or power-loss-resumable execution engine.

## Corrections before outcome computation
Review identified stale capacity on renewal before updated batch metadata and a same-time atomic-price overwrite seam; author corrected both before final review. Independently reproduced a model-availability loophole: core signals accepted a final close relabeled available at midnight, contrary to declared00:01. Final validation requires exact modeled availability, current00:01 decision and yesterday signal date for every policy/terminal/killed decision. Tests now reject the pre-fix fixture.

## Reporting limitations
This is a newly shared-cash/daily-rebalanced strategy contract, not direct replication of old independent0/1 asset returns. Delayed opening fills, assumed fees0.1%, slippage0.05%, capacity, no min-notional/product-rule constraint and sampled opening-only risk are explicit departures/unsupported facts. No intraday stop or guaranteed25% liquidation. Local hashes establish deterministic byte consistency, not immutable preregistration or trusted historical availability. Report source validation failures rather than selecting substitutes; preserve failed attempts and any already-created output. No optimization or policy rerun justified by resulting returns.

Final reporting seam also tested: kill fills cannot be relabeled preplanned terminal fills merely because their intent creation time equals the terminal decision. Exposure summary and kill-to-first-liquidation timing are explicit modeled fields. Final27-test evidence covers the exact pinned candidate.

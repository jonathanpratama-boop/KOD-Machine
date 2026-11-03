# Independent completed-run verification

All eight canonical accounts PASS independent read-only verification. No new scenario, strategy run, market download or historical row parsing was performed by this reviewer. The single author's approved run completed2026-11-01 11:38:47.897493Z after starting11:34:27.503333Z.

## What the numbers support

Each account starts10,000 USDT. Ending NAV (no residual holdings in these actual outputs):

| Fixed policy | Development NAV / growth | Reused-validation NAV / growth |
|---|---:|---:|
| Trend v2 shared |20,592.77 / +105.93%|12,377.20 / +23.77%|
| Risk-matched passive buy-once |17,844.13 / +78.44%|15,037.86 / +50.38%|
| No-kill intended50/50 buy-once |24,500.54 / +145.01%|36,220.21 / +262.20%|
| Cash |10,000 /0%|10,000 /0%|

The arithmetic supports positive modeled trend returns, NOT superiority across controls: trend trails both passive controls in reused validation and trails the no-kill control in development. No profitability/production-readiness conclusion follows from this exploratory replay.

Trend permanently killed2018-03-15 in development and2023-04-22 in reused validation, both on negative trailing90-return Sharpe. First modeled liquidation is the following opening,2018-03-16 /2023-04-23. No re-entry or reset follows. These are not years of continued trend trading: capital sits in cash after those early kills. Risk-matched passive killed2018-02-03 (drawdown) /2023-06-16 (Sharpe), liquidating the following openings. No-kill control has intentionally different risk policy.

## Comparator limitation that must accompany results
Development controls' initial intended budgets are5,000 per coin, but both synthetic volume caps bind. Actual cash debits are2,830.580711 BTC and1,704.461914 ETH, leaving5,464.957375 cash. Initial opening-mark exposure is45.313271% of NAV, not fully invested50/50; the coin weights also differ. Both passive controls hold this unfilled cash without topping up, by the predeclared buy-once IOC rule. Validation controls are nearly fully invested (0.020160 cash;99.999798% gross exposure). Thus the development no-kill label must be described as intended50/50 under common modeled capacity, not conventional fully invested benchmark performance. This is disclosed rather than repaired with an outcome-driven alternate run.

## Independent checks
- All220 existing approved ZIP bytes independently rehashed against the pinned allowlist and recorded input-validation receipts; original manifest and allowlist match. No extra input source used. See INPUT_BYTES_VERIFIED.json.
- Current implementation/protocol hashes match the pre-run clearance and START_PIN; report hash matches. Combined RESULTS agrees exactly with eight individual summaries.
- Every operation's hash-chain link/hash, unique operation ID, provenance and evidence hash checked. Journal bytes match recorded final hashes. Final state-hash receipts match summaries; the author's full deterministic core replay separately passed every account.
- Every fill independently recomputed from quantity, modeled price, fee and side; exact cash, holdings, fees and NAV reconcile at every journal event. Reservations stay within cash, cash/spot holdings nonnegative. Capacity, adverse slippage, fee rounding, decision-before-fill, source availability and terminal cutoff checked. Zero actual terminal residuals are verified, not assumed.
- Independently recomputed daily return series, CAGR, volatility, Sharpe, observed drawdown, notional/normalized turnover and exposure summaries; all agree. Persistent kills never reset; negative-Sharpe reasons have91 marks and negative trailing-return means. No same-trigger opening liquidation.

Artifacts: verify_results.py (read-only checker), POSTRUN_VERIFICATION.json (all8PASS), INPUT_BYTES_VERIFIED.json, INITIAL_PASSIVE_EXPOSURE.json. Output directory: historical_shared_account_results_20261101T1134. RESULTS.json SHA256142c1074cf4c861e800304fee5752746cd510bbeb8ecb407d413ea83affd324f. Input snapshot SHA2566b6a0e9324819da0bf709c58df3effae596ba92001cc88151e028ff86c72a511.

Scope limits remain those of the pre-outcome REVIEW.md: reused exploratory inputs, changed Sep26 development start for warmup, separate initialized partitions, assumed daily availability/delayed opening/capacity/costs, no actual BBO/depth/receipt times, no live execution validation. Frozen policy and outputs remain unchanged.

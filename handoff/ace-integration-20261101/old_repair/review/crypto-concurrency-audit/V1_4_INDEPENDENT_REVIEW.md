# Independent v1.4 candidate review — clear with limits

Reviewed isolated archive of `b40e0e6bb6e106d2d8871f86f8eaf2b4f7d567f5`, not an editable repair working tree. No active files changed, network access, receipt service calls, remote writes, or real orders.

## Verification

- Independently ran **all 100 repository tests**, with socket connect/create_connection prohibited: PASS.
- Reused original deterministic stale-snapshot fixture with only callback keyword forwarding, fixed-source selection and expected outcome changes (`reproduce_fixed.py`). Frozen earlier A clock now fails closed on B's later business event after the stale-head rejection. Only three orders commit; planned risk 149.99999988/150, reservations 2887.49999772, free cash nonnegative, unique decisions and valid chain/account verification.
- Repeated that fixture with A's evaluation clock advanced past B (`reproduce_fixed_clock_advanced.py`). Both duplicate and disjoint cases complete normally with the same safe three-order bounds. Duplicate recomputation creates no duplicate orders; disjoint recomputation cannot double available capacity.
- Reused exact earlier future-valuation fixture (`reproduce_future_valuation_fixed.py`). Mark and decision remain identical before/after the future quote: equity 9998.10, eligible candidate ORDER; position valuation time is no later than mark time. Settlement still ignores the future quote at the earlier time.
- Reviewed and ran the lifecycle stale-fill test: only one entry per order. All tested cash/risk/decision/chain invariants pass.
- Reviewed and ran retry exhaustion test: exactly three attempted proposals, each rejected with unchanged ledger bytes; no stale order/reservation committed.
- Reviewed and ran receipt tests: already-committed receipt failures do not replay business proposals. The actual append writer's receipt callback successfully takes the same ledger lock nonblockingly, proving release before receipt handling. Checked lock path matches provenance.exclusive_lock.
- Reviewed and ran extracted real CLI callback test: expected_head keyword is forwarded and ReceiptPendingError remains committed-success handling.
- Additional independent adapter probe confirms both an unrelated RuntimeError and a RuntimeError subclass carrying the stale-head text propagate as the original exception object; only the frozen writer's exact RuntimeError/message pair is translated.
- `paper.py`, `paper_account.py`, `provenance.py`, and protocol files v1 through v1.3 are byte-identical to the commit parent. Only listed crypto implementation/CLI callback/test/new-protocol/correction files changed.
- Supplied `crypto-phase-cas-v1.4.patch` and commit diff have identical stable patch-id `3033bad7fa0fa4740e7fadc4e778e4950fa9b715`; differing raw hashes are expected format-patch metadata.

## Assessment and limits

No blocking defect found within the requested bounded audit. Snapshot/head capture is coherent, successful commits are not retried for receipt failures, retries reload both state and clock, and state-derived phases are covered. The as-of boundary fixes the demonstrated quote leak and explicitly refuses future business events instead of pretending to reconstruct history.

This is offline deterministic interleaving coverage, not multiprocess stress, production evidence, remote CI, or proof that every external writer honors the callback contract. A frozen/backward clock can fail closed rather than complete; that is intentional and preserved in the evidence. Exact RuntimeError-text matching is a narrow dependency on the unchanged writer interface, not a broad exception catch. Whole-ledger reporting remains latest-known rather than historical replay. The old verifier blind spot for externally injected disjoint over-budget orders remains explicitly out of scope; guarded cycle prevention is not a comprehensive historical risk audit.

Outputs: `fixed-results.jsonl`, `fixed-clock-advanced-results.jsonl`, `future-valuation-fixed-results.json` beside this note. Original pre-fix repros/results remain unchanged.

## Multiprocess addendum

Subsequently ran two targeted actual spawned-process races with real locks/CAS, temporary ledgers, pipe synchronization, blocked network and fake local receipts. Both final cases passed the same safety invariants; see `MULTIPROCESS_REVIEW.md` and `multiprocess-results.jsonl`. An initial harness attempt exposed the expected bounded-retry liveness limit (explicit fail-closed exhaustion possible with two cycles), documented transparently in that addendum. This is no longer a deterministic-single-process-only validation; it is still not stress/load or production testing.

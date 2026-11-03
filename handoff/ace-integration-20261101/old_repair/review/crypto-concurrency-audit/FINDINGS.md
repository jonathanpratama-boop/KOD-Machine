# Offline crypto account concurrency audit

Source: isolated archive of commit `36bc7c5` from `kod-crypto-repair`, not its in-progress working tree. No active repair files modified. No network, receipts, real orders, or production ledger access.

Run: `python crypto-concurrency-audit/reproduce.py` from the task workspace. Output: `results.jsonl`.

## Controlled interleaving

Real `crypto_account.cycle` A computes three order proposals, then its append callback pauses before publication. Cycle B completes against the still-unreserved prefix. A resumes and appends its stale proposals. Both cycles use finite bid 105 / ask 106 and reference 100; asks exceed the limit 101, so all orders remain pending. A and B decision times differ by one second, avoiding exact-payload idempotency suppression.

- Same three candidates: six orders, three duplicate decisions, planned risk 299.99999976 USDT versus 150 cap; reserved 5774.99999544 USDT. Hash chain valid. Account verifier reports three duplicate decisions only.
- Three disjoint candidates per cycle: six distinct orders, same risk/reservation breach, daily order count six versus cap three. Hash chain valid **and account verifier returns no problems**.
- Existing `paper.append(expected_head=...)` control rejects a changed head and leaves ledger bytes unchanged.

## Cause and existing guards

`crypto_account.py:502+` calls `decide(lines(), ...)` then passes computed records to `append`; the read/compute/write sequence has no enclosing lock or head comparison. CLI `crypto-account-sync` (`cli.py:1283-1295`) forwards records to `paper.append` without `expected_head`. `paper.py:441+` serializes physical writes and validates the hash chain, but its default `_ANY_HEAD` allows stale proposals. Exact-payload deduplication is not semantic decision idempotency; different `made_at` values produce different payloads.

No enclosing cycle lock was found in the supplied repository/CLI or local shell/Python/YAML wrappers matching this command. This is not evidence about an unseen deployed scheduler wrapper. A scheduler that serializes every invocation could avoid this specific overlap, but the CLI itself does not enforce that guarantee, and any bypass/direct caller remains exposed.

## Narrow recommendation (not implemented)

Capture the ledger prefix once per state-derived phase, compute from that exact snapshot, then commit using its last hash as `expected_head`. On stale-head failure, reload and recompute rather than resend the stale records. Apply to settlement/cancellation/marks as appropriate, not just order decisions. Thread the keyword through the CLI callback; preserve separate receipt-pending handling because that error means commit already happened. An alternative is a dedicated account-cycle lock acquired before the first state read, honored by every account-state writer; do not recursively acquire the append lock. Keep network receipt collection outside the append critical section.

Regression coverage should include the controlled interleaving here (duplicate and disjoint candidates) and assert that the second stale attempt cannot exceed decision, daily-order, or risk limits. Add independent verifier checks for prefix-based daily/risk/cash bounds as defense in depth; verification is not a substitute for prevention.

Limits: deterministic single-process interleaving demonstrates an allowed overlapping execution schedule, not a probabilistic multiprocessing stress test or production incident. No claim about existing ledger corruption or actual live use. Numeric-validation edits after the archived commit were intentionally not examined or modified.

## Caller coverage / proposed contract

Repository search at this commit finds exactly one production `cycle` caller: `idxsig/cli.py:1290`. Test caller `tests/test_crypto_account.py:82` goes through `Base.append` (line 77); `tests/test_crypto_quote_validation.py:42` also uses that inherited callback. Change callbacks from `append(recs)` to `append(recs, **kwargs)` (or an explicit keyword-only expected-head sentinel), forwarding `**kwargs` to `paper.append`. Existing unguarded quote-observation appends must retain default `_ANY_HEAD` semantics; do not accidentally make their default `None`, which means “require empty ledger.” No production cancel writer was found; the one cancellation append is a lifecycle test using the pure `ca.cancel` proposal helper.

Within `cycle`, replace each state-derived read/compute/put at lines 519, 520, 524, and 525 with one helper: read snapshot; capture snapshot last hash (or None); evaluate settlement/decision/mark at the attempt's clock; `append(proposal, expected_head=captured_head)`. A stale-head rejection retries from a new snapshot for a small bounded count, then fails closed explicitly without appending the stale proposal. Never catch all RuntimeErrors as contention: chain corruption and other errors must propagate. A narrow `StaleHeadError(RuntimeError)` in `paper.append` would avoid message matching while preserving callers that expect RuntimeError. Only track events after confirmed commit; an empty recomputation should not falsely report the initial stale order as placed. New observations do not need a compare-and-swap because they are facts rather than reservations; they can cause a harmless recomputation.

The existing CLI `ReceiptPendingError` catch must remain distinct and mean success for the committed state transition plus receipt warning. Do not retry the business proposal merely because receipts failed. `paper.append` already releases its lock before obtaining receipts; expected-head checking uses its current critical section and introduces no long-lived network lock. The bounded retry helper must not replay the full cycle or refetch quotes merely to resolve contention.

Useful repair regression: seed two existing pending orders and interleave one proposed order from A with one distinct order from B. After successful recomputation, only one may become an order; the other must decline because daily/risk capacity is consumed. Also cover stale settlements, duplicate candidates, empty recomputation, retry exhaustion, and receipt-pending-after-commit behavior.

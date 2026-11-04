# CRYPTO_ACCOUNT_v1 — Correction 4 (rules v1.4)

Local successor candidate, not remotely published or activated. Preserves v1.2
and v1.3 protocol/patch history. No production ledger, strategy, shared US account
engine or frozen `paper.py` implementation is changed.

## A. Stale-prefix concurrency

The supplied offline audit was reproduced: cycle A computed three orders and
paused before appending; cycle B committed three orders on the same unreserved
prefix. A then appended stale proposals. Six orders reserved 5,774.99999544 USDT,
with planned risk 299.99999976 against a 150 cap. The hash chain remained valid;
disjoint candidates also passed the existing account verifier. This is a
controlled allowed interleaving, not a claim about an actual production incident.

Each settlement, decision and mark phase now reads a single prefix, computes
against that snapshot and sends its exact last hash as `expected_head` to the
existing atomic writer. On the writer's exact stale-head RuntimeError, a narrow
local adapter raises `StaleHeadConflict`; the phase reloads/recomputes at most
three total attempts. Exhaustion fails closed without committing stale records.
Unrelated errors propagate, never masquerading as contention.

Quote observations remain unguarded facts. An empty recomputation produces no
phantom order/event or follow-on fetch. Only committed proposals are tracked.
ReceiptPendingError means an already-committed write: its records and warning are
kept, and the business phase is NOT retried. The existing CLI receipt warning
behavior is retained. No ledger lock encloses network receipt operations.
Only the crypto CLI callback and test Base.append forward the added keyword;
the frozen shared writer itself is unchanged.

Scope: this protects state phases using `cycle` and its callback contract; it
does not claim to constrain an external writer that deliberately bypasses CAS.
It does not retroactively repair records or add a complete historical risk audit.

## B. Separate as-of valuation guard

The separate artificial future-row fixture was reproduced: a future quote for
an existing position changed today's mark equity from 9,998.10 to 10,951.07 and
changed another candidate from ORDER to risk-limit DECLINE, even though settlement
and fresh_quote ignored that future quote. No normal forward contamination is
asserted; this tests an inconsistent future-row/stale-clock input.

`decide` and `mark` now pass their clock to `account`. Only recorded quotes at or
before that clock value positions. The ordinary whole-ledger `account(recs)`
view remains unchanged for historical reporting. Future business events cannot
be safely reconstructed by dropping just quote rows: if an order/decline/cancel/
entry/exit/mark has a future made/recorded/filled/exited time, as-of valuation
raises FutureLedgerStateError. Planned future validity and holding deadlines are
not mistaken for executed future events. No history is rewritten.

## C. Separate policy-reference input boundary

With a valid 99/100 book, a policy `verified_price.quote` of positive infinity or
non-numeric text could crash after the observation had already appended. Boolean
True could coerce to 1.0 and create an unintended 1.01 limit. The successor requires
a positive finite non-Boolean reference and catches conversion failures. Invalid
or malformed policy references produce DECLINE/NO_DECISION_PRICE and processing
continues for unrelated valid candidates. Legitimate numeric strings remain
supported. No policy threshold or strategy decision is changed.

## Verification

100 combined offline tests pass with socket connections prohibited: 11 new CAS
tests, 5 separate as-of tests and 3 policy-reference tests, plus all 81 prior focused tests. Controlled
duplicate/disjoint candidates, one remaining slot, stale fill and mark, empty
recomputation, retry exhaustion, unchanged bytes on rejected CAS, cash/risk/daily
bounds, hash chains, CLI forwarding and receipt-pending are covered. A real writer
receipt-failure fixture obtains the ledger lock nonblockingly during receipt
handling, proving the append lock was already released. No receipt service called.

Three selected duplicate/disjoint/future-valuation regressions fail against the
unchanged v1.3 source and pass the successor. No remote CI, orders or publication.

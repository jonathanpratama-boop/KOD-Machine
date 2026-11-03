# Candidate protocol addendum 1 — 2026-11-01, during synthetic acceptance

The original candidate protocol remains byte-identical. This is a pre-deployment
implementation correction, NOT a historical profitability optimization.

Independent review and author review found that a pending BUY could fill after
another held instrument's mark expired, leaving aggregate NAV/drawdown unknowable.
Correction: every increased-risk BUY fill additionally requires complete, fresh
aggregate NAV at fill-processing time. Otherwise retain its pending reservation and
record UNKNOWN_AGGREGATE_NAV_AT_FILL until eligible evidence arrives or the intent
expires. Risk-reducing SELL intents remain eligible with their own causal quote and
quantity evidence. Unknown NAV still propagates; no stale mark is carried forward.

The executable code, this addendum and the unchanged original candidate protocol
are all bound into each account's provenance. Old synthetic journals created before
the correction are not silently replayed under the new code. No published v1 record
or live account was changed.

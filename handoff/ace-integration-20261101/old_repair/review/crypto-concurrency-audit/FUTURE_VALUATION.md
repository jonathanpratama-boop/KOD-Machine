# Separate causal valuation finding (not part of CAS patch)

Source: isolated committed `36bc7c5` archive. Run `python crypto-concurrency-audit/reproduce_future_valuation.py`. Exact output: `future-valuation-results.json`. No active files edited, network calls, receipts, or real orders.

## Minimal bounded fixture

1. Use the real cycle and test finite quote feed to open one AAA position at 100 from two recorded quotes. This produces legitimate ORDER/ENTRY records and cash/stop state.
2. At `now=2026-11-01T00:31:00Z`, record an unrelated eligible BBB quote (bid 99.9 / ask 100), with a valid BBB buy candidate. Its proposal is an ORDER; mark equity is 9998.10.
3. Append one finite AAA quote bid 200 / ask 200.1 with observed_at `2026-11-07T00:30:00Z`.
4. Evaluate the same BBB decision and mark at the unchanged earlier `now`.

Results: mark equity rises to 10951.07; the mark made on Nov 1 contains a position valued on Nov 7. BBB now declines: `LIMIT_PLANNED_RISK: 1000.52 + 54.76 would exceed 1.5% of equity 10951.07`. In contrast, `fresh_quote(AAA, now)` still selects the Nov 1 quote, `fresh_quote(BBB, now)` accepts the current BBB quote, and `settle(rows, now)` returns no event (it only emits the time exit when evaluated at the future time). Both `paper.verify_chain` and `ca.verify` return `[]`.

Cause: `account(recs)` has no as-of clock and selects the latest quote from all rows (`crypto_account.py:214+`). Both `decide(recs, cands, now)` and `mark(recs, now)` invoke that timeless valuation. Their explicit `now` therefore does not bound inputs used to calculate equity and planned risk.

## Scope / interpretation

This fixture deliberately injects a future observation relative to the evaluation clock. It is not evidence of a future quote being collected in normal sequential execution. With accurate monotonic clocks and `now` taken after each fetch, normal forward-only runs naturally have no future observation and do not encounter this case. The history could also represent a valid later ledger evaluated at an earlier replay time; the pure API currently lacks causal valuation in that scenario. Overlap with a cached earlier `now` or clock skew can make the mismatch less artificial. This audit did not test those external mechanisms or claim a production incident.

## Narrow recommendation

Add optional as-of valuation to `account(recs, now=...)` (or equivalent helper), excluding quote observations later than that time. Pass the decision clock from `decide` and mark clock from `mark`; keep latest-known reporting behavior explicit where intended. For this fixture the position lifecycle is entirely before `now`, so bounding the valuation quotes alone corrects the result. General historical replay also requires an as-of event prefix for orders/entries/exits/cancellations/cash; a quote-only filter must not be advertised as full historical-account reconstruction. Add a focused regression that the future quote does not alter current mark/decision and that the chosen valuation timestamp never exceeds the mark/decision timestamp. Keep this work separate from the concurrent-write repair.

# One bounded public execution-metadata capture

2026-10-31, 18:50:25–18:51:10 UTC. Four unauthenticated GET requests only:
one `data-api.binance.vision/api/v3/exchangeInfo` for BTCUSDT, ETHUSDT and
BEAMXUSDT together, then one `/api/v3/depth?symbol=...&limit=100` per pair.
All returned HTTP 200; all three symbols reported TRADING and LIMIT support.
Each book contained 100 bid and 100 ask levels. No order/account endpoint,
credentials, alternate hosts, retry loop, production ledger or strategy change.

## Honest result

| Pair | 100 USDT target | 1,000 USDT target |
|---|---|---|
| BTCUSDT | REJECTED | REJECTED |
| ETHUSDT | REJECTED | REJECTED |
| BEAMXUSDT | REJECTED | REJECTED |

After sizing synthetic base quantities downward to the **observed** lot step,
all six fail closed on `UNSUPPORTED_FILTER:ICEBERG_PARTS`. Every observed filter
was passed intact, with no pruning or fabricated averages. This is the first
unsupported filter in source order, not the only remaining restriction.

- **Inapplicable to these plain standalone LIMIT/IOC fixtures, but not yet
  explicitly handled by the module:** ICEBERG_PARTS, MARKET_LOT_SIZE,
  TRAILING_DELTA, MAX_NUM_ORDER_LISTS, MAX_NUM_ALGO_ORDERS, MAX_NUM_ORDER_AMENDS.
- **Still requires evidence not collected:** PERCENT_PRICE_BY_SIDE needs its
  documented reference/average price; MAX_NUM_ORDERS requires account open-order
  state. Neither is assumed to pass. No authenticated account access was attempted.
- PRICE_FILTER, LOT_SIZE and NOTIONAL are present, but rejection prevents an
  overall eligibility or fill claim. No estimated P&L or buy recommendation.

The synthetic buy limit is the captured best ask; targets are converted to base
quantity and floored to the observed lot step. The fixture's intent time is set
to request-start, purely for controlled temporal evaluation: it is **not** an
actual order placement record. Evaluation uses receive-time as its clock, with
a 10-second book-age bound, 10-minute filter-age bound and hypothetical 0.1%
quote-notional fee (not an account-specific fee). These were offline calculations
on one snapshot, not attempts to execute or track liquidity.

## Evidence and adapter correction

Raw responses are `exchangeInfo.json` and `*-depth.json`. `provenance.json` and
`*-provenance.json` record complete request URLs, start/receive UTC times, HTTP
status, byte counts and SHA-256 hashes. All four raw hashes were reverified.
`outcomes-sized.json` contains final sized requests, complete results and filter
classifications. `evaluate_saved.py` reproduces that evaluation without networking.

The initial capture adapter passed an unrounded repeating Decimal quotient, which
the module correctly rejected as NUMBER_PRECISION_UNSUPPORTED. That first result
is retained in `outcomes.json`. The adapter was corrected **offline**, using the
same raw capture and observed lot step; no additional requests were made and no
estimator code was changed. `capture_depth.py` records the initial capture logic
and refuses to repeat once outcomes exist.

## Conclusion

Public market data access worked. The prototype honestly declines these real
metadata samples rather than pretending complete exchange parity. A future
separate amendment could classify provably inapplicable filters while retaining
explicit blockers for applicable unknown constraints. It must not silently drop
filters or infer missing account/reference-price evidence. Existing fixture tests
remain the only positive fill-feasibility verification; live acceptance/fill claims
are unsupported by this capture.

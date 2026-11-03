# Filter evidence extension — local candidate, not integrated

This additive amendment supersedes only the applicability/evidence portion of
SPEC.md. The earlier local prototype commit and first public rejection artifacts
remain available unchanged. No quote-account module, strategy or ledger changed.

## Explicit request scope and evidence

Intent now names LIMIT, IOC, zero iceberg quantity, no trailing parameter, no
order list and no amendment. Any other shape is rejected, so inapplicability is
not inferred for an unsupported order type. Every supplied filter is inspected;
`Estimate.filter_checks` records the interpretation even on later rejection.
Unknown or duplicate filters remain rejections.

Verified against [Binance filters](https://developers.binance.com/en/docs/products/spot/filters):
iceberg-parts, market-lot and trailing-delta constraints do not apply to this plain
limit intent. A new standalone intent also creates no order list or amendment.
These five filters are marked INAPPLICABLE, never silently removed. Open-order
limits count the new normal order; an algo count receives no increment because
this request is not conditional.

`SimulatedCounts` must provide symbol-specific total/algo open counts and as-of
time. Missing, negative, Boolean, stale, future or inconsistent counts reject.
Even for the non-algo request, supplied MAX_NUM_ALGO_ORDERS requires counts; this
is deliberately conservative. A total at its maximum blocks the additional
order; an algo count above its maximum also rejects. Every use emits
`SIMULATED_ACCOUNT_COUNTS_ONLY:NOT_ACTUAL_ACCOUNT_VERIFICATION`. This is not
evidence of actual holdings, balances or exchange account eligibility.

## Percentage-price evidence

PERCENT_PRICE_BY_SIDE checks the side-specific multiplier bounds against a fresh
`AverageReference` with the exact required minute interval. Missing/mismatched
evidence rejects. Its observation, last-trade and overriding-reference-state
times must be timezone-aware, no later than intent time and within the caller's
reference age limit. A trade later than the average observation also rejects.

Current [official documentation](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)
provides average interval, price and last-trade time via avgPrice. It separately
defines referencePrice, including null or error -2043 for absence. The current
filter specification gives a non-null overriding reference precedence over the
average. Therefore this bounded implementation accepts averages only with fresh
observed ABSENT override state and its provenance. PRESENT/UNKNOWN rejects;
support for non-null overriding references is intentionally not added here.
An inaccessible endpoint is not evidence that a reference is absent.

This remains a partial **feasibility model**, not full exchange parity. Price-range
execution rules, account/exchange/asset constraints outside the supplied subset,
actual fee asset/rate and liquidity persistence are still not verified. COMPLETE
is only the displayed-depth estimate under the declared simulated assumptions.

## Verification and public observation

`python -m unittest tests.test_paper_execution_filter_evidence tests.test_paper_execution_feasibility tests.test_crypto_account tests.test_paper_account tests.test_paper_book tests.test_paper_account_report`

73 offline tests pass (10 new applicability/evidence fixtures). Socket connections
were prohibited. Includes inapplicable-filter audit trails, unsupported request
shapes, missing/mismatched/stale/future references, side bounds, reference override
states, absent/invalid/stale counts, total/algo caps and simulated-state labeling.

The initial bounded public observation used **two** of the six allowed GETs:
BTCUSDT avgPrice succeeded, reporting a 5-minute average. The data-only host's
referencePrice endpoint returned HTTP 404 HTML. Capture stopped immediately:
no retry, alternative host, refreshed book or BEAMX request. No absence assertion
or fill estimate was manufactured from that error. Raw response hashes and
request/receive times are retained in the separate capture directory.

After separate authorization for one documented public-host fallback (404 was
endpoint unavailability), `api.binance.com/api/v3/referencePrice?symbol=BTCUSDT`
returned HTTP 451 with a restricted-location eligibility message. All further
network requests stopped immediately. Total extension GETs: **three**, not six.
There was no further host switch, retry or bypass. Reference state remains UNKNOWN;
no real-metadata eligibility or fill result is claimed.

# Bounded public-book observation

Purpose: measure public spread, displayed depth and hypothetical 100/1,000-USDT
sweep costs for BTCUSDT, ETHUSDT and BEAMXUSDT. This is not a strategy, signal,
filter-eligibility check, P&L experiment or guaranteed execution estimate.

Frozen run: 60 scheduled sample sets, 120 seconds apart, maximum 180 depth GETs;
only the previously successful data-api.binance.vision `/api/v3/depth`, 100 levels.
No api.binance.com/referencePrice, credentials, account or order endpoints.
No redirects, host switches, retries or historical backfill. HTTP 429 respects
Retry-After by marking intervening samples missing; invalid/missing Retry-After
stops. Redirects, source-unavailable 4xx or access denials stop the entire run.
An outer process timeout bounds lifetime as well as the internal two-hour deadline.

Raw snapshots, errors, request/receive UTC times, hashes and attempted requests
are retained. All missing/failed slots are explicit. `status.json` gives progress
and `summary.json` the terminal result. `protocol.json` is written before the
first GET and pins collector and reused microstructure source hashes.

The existing microstructure book_metrics/book_fill functions supply descriptive
walks after malformed/crossed/nonfinite book rejection. BUY spends the hypothetical
quote amount; SELL sells quantity equal to that amount divided by the observed
mid. Incomplete depth remains incomplete; partial VWAP can understate the cost
of filling the entire request. Fee assumption is 0.1% per side, hypothetical and
not account-specific. No liquidity is reserved across observations.

Verification: 10 offline tests for exact request bounds/timing, 451 and other source
failures, rate limits, missing slots, malformed books and overwrite prevention.
Run: `python -m unittest test_collect` from this folder.
Start exactly once with a fresh output path. Existing run folders are never reused.

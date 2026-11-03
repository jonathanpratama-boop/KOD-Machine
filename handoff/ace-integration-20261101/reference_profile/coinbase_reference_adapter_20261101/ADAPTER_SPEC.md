# COINBASE_EXCHANGE_USD_REFERENCE_v1 — bounded prospective adapter specification

Written 2026-11-01 before implementation and before any selected public API request.
Simulation only; separate BTC-USD/ETH-USD/USD reference profile. NOT Binance/USDT,
NOT eToro executable prices, NOT venue access/eligibility advice or validated alpha.
Original TREND_CORE v1 and v2 synthetic bytes/journals/default remain unchanged.

## Bounded source and exposure

Official documentation reviewed:
- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-book
- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-single-product
- https://docs.cdp.coinbase.com/exchange/rest-api/requests
- https://docs.cdp.coinbase.com/exchange/rest-api/rate-limits

Only unauthenticated GETs to api.exchange.coinbase.com, products BTC-USD/ETH-USD:
product metadata; daily candles with explicit 40-day UTC start/end and granularity
86400; level1 book. At most eight requests in one manually authorized cycle (two of
metadata/candles/pre-decision book/post-decision book); no recurring poll, retry,
redirect, alternate hostname or account/order endpoint. Any source/access refusal
stops the route. Original response bytes and request/receipt timestamps/hashes are
saved before parsing. A separate exposure receipt records exactly the dates read.
This is current warm-up exposure for a prospective decision, not a sealed-data test.
No stored market datasets or raw prior sealed history are opened.

## Timing and data quality

Use process UTC wall clock plus monotonic elapsed clock; reject backward/jumping
clock, RTT>2 seconds, missing/invalid HTTP Date, response clock difference>5 seconds,
or Age>0. Actual local first receipt is authoritative for this run. It is NOT
immutable external timestamp attestation. Candle first-publication times are absent
from documentation: retain first_public_at=null and availability_at=actual receipt;
never fabricate publication times or use candles for a historical decision/fill.
Select exactly40 distinct consecutive completed UTC-day buckets ending yesterday,
validate finite positive OHLC, consistency, nonnegative volume, UTC boundaries and
source hashes. Reject gaps/conflicting duplicates/future selected buckets. Ignore
returned earlier/out-of-range buckets only with recorded counts (docs allow extras).
The signal, normalization and account rules are inherited unchanged from v2.

Book source time/sequence are required; source time cannot be future or older than
5 seconds at receipt. Preserve source time separately; account observation time is
actual local receipt. Require local quote request to begin after a fill's intent,
and source book time also after intent. Post-decision capture starts after a6-second
buffer, bounded to one pair of book reads. First-public availability remains unknown.
A public snapshot is reference evidence, not guaranteed executable liquidity.

## Product and simulation eligibility

Require exact product ID/base/quote identity, status online, known false post_only,
limit_only,cancel_only,auction_mode,trading_disabled. Unknown status/flags/rules
block fills. Require positive base_increment/quote_increment/min_market_funds;
base increment must be a supported decimal power-of-ten matching account precision.
Metadata must be received within300 seconds of use. Book prices must lie on declared
quote grid and not cross; book auction flag must be explicitly false. Sizes are
aggregated quantities (do not multiply by order count). Missing size blocks fills.
Use only10% of displayed side quantity as a declared conservative reference cap;
partial remainder cancels. This fraction is a modeling assumption, not fill proof.
Reject prospective fills below min_market_funds or off quantity grid. Tiny residual
holdings remain held/marked; no fictitious dust liquidation.

Costs are fixed named research assumptions: fee1% per side, adverse slippage0.1%,
transaction tax0%. NOT asserted Coinbase/Binance/eToro applicable fees or taxes.
Round slipped price adversely to observed quote increment, quantity down to base
increment and fees with existing Decimal half-up cents. Tax0% is unverified; this
reference scenario cannot support a real net-return/venue recommendation.

## Core reuse and activation gate

Reuse the reviewed v2 event/account implementation and Decimal primitives via a
minimal separately versioned profile seam; record an exact diff from the immutable
original. No second portfolio/backtest engine, no real-order code. New journals
bind adapter/source/core/protocol hashes and preserve USD identity throughout.
Synthetic-only original remains unchanged and rejects real evidence.

Before any public response is requested: mocked-response tests and an independent
review must pass. Then one bounded local cash1000 USD initialization/decision cycle
may run. CASH is valid; no trade forced. If data/status/clock/access is inadequate,
record a blocked cycle and stop, without inventing a signal or fill. No schedule,
workflow/Mac integration, remote publication or financial trade is authorized.

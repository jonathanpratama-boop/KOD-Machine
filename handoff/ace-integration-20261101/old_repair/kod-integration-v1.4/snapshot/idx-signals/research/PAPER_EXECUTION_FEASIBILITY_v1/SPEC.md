# Paper execution feasibility v1 — local, disconnected prototype

## Scope and API

`idxsig.paper_execution_feasibility.estimate(intent, book, filters, *, now,
max_book_age, max_filter_age, fee_rate) -> Estimate` is a pure function for a
single plain LIMIT/IOC-style base-quantity intent. All prices and quantities are
Decimal, never float. It accepts timestamped `BookSnapshot` and `FilterSnapshot`
objects supplied by the caller. It does not fetch anything, route orders, reserve
cash/liquidity, update a strategy, or write any ledger. No credentials exist here.

The caller must retain the original inputs and public-data provenance together
with each estimate. Filter and book timestamps mean **when locally observed**,
not an inferred exchange event time. Required ordering is
`filters.observed_at <= intent.placed_at <= book.observed_at <= now`.
Book and filter maximum ages are caller-supplied, independent, nonnegative values.
Unknown age, missing data, future data and timezone-naive timestamps fail closed.

Outputs include normalized quantity/limit, per-level assumed fills, unfilled
quantity, gross quote notional and quote-currency fee under the supplied rate.
States are REJECTED, UNFILLED, PARTIAL or COMPLETE; every state has a reason.
COMPLETE means only that this snapshot displayed sufficient eligible depth.
It is **not** exchange acceptance or a guaranteed execution.

## Filter subset (not complete Binance parity)

Rules checked against official Binance spot documentation on 2026-10-31:
https://github.com/binance/binance-spot-api-docs/blob/master/filters.md

- PRICE_FILTER: enabled minimum/maximum and tick multiples. An explicitly zero
  price bound or tick disables that component; missing fields are not zero.
- LOT_SIZE: quantity minimum/maximum and step multiples. Missing or zero lot
  steps are unsupported and rejected, not guessed.
- MIN_NOTIONAL / NOTIONAL: limit price times normalized order quantity against
  applicable minimum/maximum. At least one notional filter must be present.
  Market-order flags do not apply because this estimator supports only limits.
- Unsupported or duplicate filter types fail closed. Do **not** strip observed
  filters to force a result. Most real symbols may remain unsupported until
  percentage-price, account/exchange/asset limits and their required evidence are
  implemented. Even supported symbol filters do not prove account eligibility.

Quantity rounds downward; BUY limits downward and SELL limits upward to the
observed increments. Bounds and notional are checked **after** rounding. This is
a disclosed intent normalization, not a claim that the exchange rounds requests.
Decimals are constrained to 28 significant digits and exponent magnitude <=18;
unsupported precision and nonfinite/negative values are explicitly rejected.

## Depth and reuse decision

Inspected existing `microstructure.book_fill` and retained its best-first,
consume-only-displayed-depth algorithm. Its float arithmetic, buy quote-budget
semantics and lack of limit/filter validation make direct reuse unsafe for exact
base-quantity filter checks. The new narrow Decimal walker is cross-checked
against that existing utility on an equivalent complete-fill fixture. Existing
microstructure code is byte-identical; no second collector is introduced.

Books must be strictly ordered with no duplicate price levels, positive prices,
nonnegative quantities, both sides present and no locked/crossed top-of-book.
Consumption is capped by each displayed quantity and the normalized limit.
Each level's usable quantity rounds down to a lot; dust is not combined across
levels (intentionally conservative). Residual IOC quantity is explicitly unfilled,
not silently booked later. A valid order can have a partial execution worth less
than order-level minimum notional; that is not retroactively rejected.

Fee rate is mandatory, finite and in [0,1); fees are assumed paid in quote
currency on consumed notional, with no discount or actual account-tier claim.
No queue priority, latency, cancellation races, hidden liquidity, market impact,
funding availability, exchange balance, fee rounding or actual fee asset is
modelled. The snapshot is an optimistic upper bound on available displayed
liquidity, not evidence it will remain there. Repeated independent estimates on
the same snapshot **must not be summed**: this function does not share consumption
across orders. Testnet depth is not evidence of production liquidity.

## Verification

`python -m unittest tests.test_paper_execution_feasibility`

20 synthetic adversarial tests cover min/max notional, quantity and price rounding,
missing/zero increments, unsupported filters, partial and absent fills, insufficient
depth, dust, fee accounting, stale/missing/future inputs, timestamp ordering,
malformed books, nonfinite numbers, disabled price constraints and bounded fills.
The combined 63-test suite includes the separately reviewed v1.2 repair and frozen
US account preservation tests. All run with socket connections prohibited.

No strategy, account, historical protocol, production ledger or research dataset
is modified; this prototype is not integrated, activated or remotely published.

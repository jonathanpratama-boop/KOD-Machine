"""Pure, paper-only LIMIT/IOC displayed-depth feasibility estimator.

No network, authentication, broker, persistence or strategy integration. Not an
exchange acceptance check or a promise of fills. See the companion SPEC.md.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from typing import Literal, Mapping

D = Decimal
ZERO = D("0")


@dataclass(frozen=True)
class FilterSnapshot:
    symbol: str
    observed_at: datetime
    source: str
    filters: tuple[Mapping[str, str | int | bool], ...]


@dataclass(frozen=True)
class BookSnapshot:
    symbol: str
    observed_at: datetime
    source: str
    bids: tuple[tuple[Decimal, Decimal], ...]
    asks: tuple[tuple[Decimal, Decimal], ...]


@dataclass(frozen=True)
class Intent:
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    limit_price: Decimal
    placed_at: datetime
    order_type: str = "LIMIT"
    time_in_force: str = "IOC"
    iceberg_quantity: Decimal = ZERO
    trailing_delta: int | None = None
    is_order_list: bool = False
    is_amendment: bool = False


@dataclass(frozen=True)
class AverageReference:
    symbol: str
    price: Decimal
    minutes: int
    observed_at: datetime
    last_trade_at: datetime
    source: str
    override_state: Literal["ABSENT", "PRESENT", "UNKNOWN"]
    override_observed_at: datetime
    override_source: str


@dataclass(frozen=True)
class SimulatedCounts:
    """Hypothetical state, never evidence about a real exchange account."""
    symbol: str
    as_of: datetime
    open_orders: int
    open_algo_orders: int


@dataclass(frozen=True)
class Estimate:
    status: str
    reason: str
    quantity: Decimal = ZERO
    limit_price: Decimal = ZERO
    filled: Decimal = ZERO
    unfilled: Decimal = ZERO
    notional: Decimal = ZERO
    fee_quote: Decimal = ZERO
    fee_rate: Decimal = ZERO
    fills: tuple[tuple[Decimal, Decimal], ...] = ()
    filter_checks: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


class Invalid(ValueError):
    pass


def _number(value, *, string=False):
    if string:
        if not isinstance(value, str):
            raise Invalid("FILTER_NUMBER_MUST_BE_STRING")
        try:
            value = D(value)
        except Exception as exc:
            raise Invalid("INVALID_NUMBER") from exc
    if not isinstance(value, Decimal) or not value.is_finite():
        raise Invalid("INVALID_NUMBER")
    if len(value.as_tuple().digits) > 28 or abs(value.as_tuple().exponent) > 18:
        raise Invalid("NUMBER_PRECISION_UNSUPPORTED")
    if value < ZERO:
        raise Invalid("NEGATIVE_NUMBER")
    return value


def _aware(t):
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise Invalid("TIMEZONE_REQUIRED")


def _recent(t, now, age, name):
    _aware(t)
    if not isinstance(age, timedelta) or age < timedelta(0):
        raise Invalid("INVALID_MAX_AGE")
    if t > now:
        raise Invalid(f"FUTURE_{name}")
    if now - t > age:
        raise Invalid(f"STALE_{name}")


def _integer(value):
    if type(value) is not int or value < 0:
        raise Invalid("NONNEGATIVE_INTEGER_REQUIRED")
    return value


def _filters(snapshot, checks):
    required = {"PRICE_FILTER": ("minPrice", "maxPrice", "tickSize"),
                "LOT_SIZE": ("minQty", "maxQty", "stepSize"),
                "MIN_NOTIONAL": ("minNotional",),
                "NOTIONAL": ("minNotional", "maxNotional"),
                "PERCENT_PRICE_BY_SIDE": ("bidMultiplierUp", "bidMultiplierDown", "askMultiplierUp", "askMultiplierDown", "avgPriceMins"),
                "MAX_NUM_ORDERS": ("maxNumOrders",),
                "MAX_NUM_ALGO_ORDERS": ("maxNumAlgoOrders",),
                "ICEBERG_PARTS": ("limit",),
                "MARKET_LOT_SIZE": ("minQty", "maxQty", "stepSize"),
                "TRAILING_DELTA": ("minTrailingAboveDelta", "maxTrailingAboveDelta", "minTrailingBelowDelta", "maxTrailingBelowDelta"),
                "MAX_NUM_ORDER_AMENDS": ("maxNumOrderAmends",),
                "MAX_NUM_ORDER_LISTS": ("maxNumOrderLists",)}
    integers = {"avgPriceMins", "maxNumOrders", "maxNumAlgoOrders", "limit", "maxNumOrderAmends", "maxNumOrderLists",
                "minTrailingAboveDelta", "maxTrailingAboveDelta", "minTrailingBelowDelta", "maxTrailingBelowDelta"}
    inapplicable = {"ICEBERG_PARTS": "no iceberg quantity", "MARKET_LOT_SIZE": "LIMIT not MARKET",
                   "TRAILING_DELTA": "no trailing parameter", "MAX_NUM_ORDER_AMENDS": "new intent not amendment",
                   "MAX_NUM_ORDER_LISTS": "standalone not order list"}
    found = {}
    for row in snapshot.filters:
        name = row.get("filterType")
        if name not in required:
            raise Invalid(f"UNSUPPORTED_FILTER:{name}")
        if name in found:
            raise Invalid(f"DUPLICATE_FILTER:{name}")
        if any(k not in row for k in required[name]):
            raise Invalid(f"MISSING_FILTER_FIELD:{name}")
        found[name] = {k: _integer(row[k]) if k in integers else _number(row[k], string=True) for k in required[name]}
        if name in inapplicable:
            checks.append(f"{name}:INAPPLICABLE:{inapplicable[name]}")
    if not {"PRICE_FILTER", "LOT_SIZE"} <= found.keys():
        raise Invalid("MISSING_PRICE_OR_LOT_FILTER")
    if not ({"MIN_NOTIONAL", "NOTIONAL"} & found.keys()):
        raise Invalid("MISSING_NOTIONAL_FILTER")
    lot = found["LOT_SIZE"]
    if lot["stepSize"] <= 0 or lot["maxQty"] <= 0 or lot["minQty"] > lot["maxQty"]:
        raise Invalid("UNSUPPORTED_OR_INVALID_LOT_FILTER")
    price = found["PRICE_FILTER"]
    if price["maxPrice"] and price["minPrice"] > price["maxPrice"]:
        raise Invalid("INVALID_PRICE_BOUNDS")
    n = found.get("NOTIONAL")
    if n and (n["maxNotional"] <= 0 or n["minNotional"] > n["maxNotional"]):
        raise Invalid("INVALID_NOTIONAL_BOUNDS")
    return found


def _levels(levels, descending):
    if len(levels) > 10000:
        raise Invalid("TOO_MANY_LEVELS")
    prior = None
    for price, qty in levels:
        _number(price)
        _number(qty)
        if price <= 0:
            raise Invalid("INVALID_BOOK_PRICE")
        if prior is not None and (price >= prior if descending else price <= prior):
            raise Invalid("UNSORTED_OR_DUPLICATE_LEVEL")
        prior = price


def estimate(intent: Intent, book: BookSnapshot | None, filters: FilterSnapshot | None,
             *, now: datetime, max_book_age: timedelta, max_filter_age: timedelta,
             fee_rate: Decimal, average: AverageReference | None = None,
             simulated_counts: SimulatedCounts | None = None,
             max_reference_age: timedelta | None = None,
             max_count_age: timedelta | None = None) -> Estimate:
    """Round quantity down; buy limit down / sell limit up. Walk one snapshot once.

    Caller supplies observed filters and an explicit quote-currency fee assumption.
    Unconsumed IOC quantity does not rest in this model. Never reuse the same book
    independently for multiple orders and then add fills: liquidity is not reserved.
    """
    checks, assumptions = [], []
    try:
        with localcontext() as ctx:
            ctx.prec = 160
            return _estimate(intent, book, filters, now, max_book_age, max_filter_age, fee_rate,
                             average, simulated_counts, max_reference_age, max_count_age, checks, assumptions)
    except Invalid as exc:
        return Estimate("REJECTED", str(exc), filter_checks=tuple(checks), assumptions=tuple(assumptions))


def _estimate(intent, book, filters, now, book_age, filter_age, fee,
              average, counts, ref_age, count_age, checks, assumptions):
    _aware(now)
    _aware(intent.placed_at)
    if intent.placed_at > now:
        raise Invalid("FUTURE_INTENT")
    if (intent.order_type != "LIMIT" or intent.time_in_force != "IOC"
            or _number(intent.iceberg_quantity) != ZERO or intent.trailing_delta is not None
            or intent.is_order_list is not False or intent.is_amendment is not False):
        raise Invalid("ONLY_PLAIN_NEW_STANDALONE_LIMIT_IOC_SUPPORTED")
    if book is None or filters is None:
        raise Invalid("MISSING_BOOK_OR_FILTERS")
    if not intent.symbol or intent.symbol != book.symbol or intent.symbol != filters.symbol:
        raise Invalid("SYMBOL_MISMATCH")
    if not book.source or not filters.source:
        raise Invalid("MISSING_PROVENANCE")
    _recent(book.observed_at, now, book_age, "BOOK")
    _recent(filters.observed_at, now, filter_age, "FILTERS")
    if book.observed_at < intent.placed_at:
        raise Invalid("BOOK_BEFORE_INTENT")
    if filters.observed_at > intent.placed_at:
        raise Invalid("FILTERS_AFTER_INTENT")
    if intent.side not in ("BUY", "SELL"):
        raise Invalid("UNSUPPORTED_SIDE")
    qty, price, fee = _number(intent.quantity), _number(intent.limit_price), _number(fee)
    if not qty or not price or fee >= 1:
        raise Invalid("INVALID_INTENT_OR_FEE")
    fs = _filters(filters, checks)
    pf, lot = fs["PRICE_FILTER"], fs["LOT_SIZE"]
    step, tick = lot["stepSize"], pf["tickSize"]
    qty = (qty / step).to_integral_value(rounding=ROUND_FLOOR) * step
    if tick:  # Binance explicitly allows zero tickSize to disable this rule.
        rounding = ROUND_FLOOR if intent.side == "BUY" else ROUND_CEILING
        price = (price / tick).to_integral_value(rounding=rounding) * tick
    if qty <= 0 or not lot["minQty"] <= qty <= lot["maxQty"]:
        raise Invalid("LOT_SIZE")
    if price <= 0 or (pf["minPrice"] and price < pf["minPrice"]) or (pf["maxPrice"] and price > pf["maxPrice"]):
        raise Invalid("PRICE_FILTER")
    order_notional = price * qty
    for name in ("MIN_NOTIONAL", "NOTIONAL"):
        if name in fs and order_notional < fs[name]["minNotional"]:
            raise Invalid("MIN_NOTIONAL")
    if "NOTIONAL" in fs and order_notional > fs["NOTIONAL"]["maxNotional"]:
        raise Invalid("MAX_NOTIONAL")
    checks.extend(f"{f}:PASS_OBSERVED_FILTER" for f in ("PRICE_FILTER", "LOT_SIZE", "MIN_NOTIONAL", "NOTIONAL") if f in fs)
    if "PERCENT_PRICE_BY_SIDE" in fs:
        rule = fs["PERCENT_PRICE_BY_SIDE"]
        if average is None:
            raise Invalid("MISSING_AVERAGE_REFERENCE")
        if average.symbol != intent.symbol or not average.source or not average.override_source:
            raise Invalid("REFERENCE_IDENTITY_OR_PROVENANCE")
        for t, name in ((average.observed_at, "AVERAGE"), (average.last_trade_at, "AVERAGE_TRADE"),
                        (average.override_observed_at, "REFERENCE_STATE")):
            _recent(t, now, ref_age, name)
            if t > intent.placed_at:
                raise Invalid("REFERENCE_AFTER_INTENT")
        if average.last_trade_at > average.observed_at:
            raise Invalid("TRADE_AFTER_AVERAGE_OBSERVATION")
        if average.override_state != "ABSENT":
            raise Invalid("ACTIVE_OR_UNKNOWN_OVERRIDE_REFERENCE")
        if _integer(average.minutes) != rule["avgPriceMins"]:
            raise Invalid("AVERAGE_INTERVAL_MISMATCH")
        ref = _number(average.price)
        prefix = "bid" if intent.side == "BUY" else "ask"
        lo, hi = rule[prefix + "MultiplierDown"], rule[prefix + "MultiplierUp"]
        if ref <= 0 or lo <= 0 or hi < lo:
            raise Invalid("INVALID_PERCENT_PRICE_BOUNDS")
        if not ref * lo <= price <= ref * hi:
            raise Invalid("PERCENT_PRICE_BY_SIDE")
        checks.append("PERCENT_PRICE_BY_SIDE:PASS_OBSERVED_AVERAGE_AND_ABSENT_OVERRIDE")
    if {"MAX_NUM_ORDERS", "MAX_NUM_ALGO_ORDERS"} & fs.keys():
        if counts is None:
            raise Invalid("MISSING_SIMULATED_ACCOUNT_COUNTS")
        if counts.symbol != intent.symbol:
            raise Invalid("COUNT_SYMBOL_MISMATCH")
        _recent(counts.as_of, now, count_age, "SIMULATED_COUNTS")
        if counts.as_of > intent.placed_at:
            raise Invalid("COUNTS_AFTER_INTENT")
        ordinary, algo = _integer(counts.open_orders), _integer(counts.open_algo_orders)
        if algo > ordinary:
            raise Invalid("ALGO_COUNT_EXCEEDS_TOTAL")
        assumptions.append("SIMULATED_ACCOUNT_COUNTS_ONLY:NOT_ACTUAL_ACCOUNT_VERIFICATION")
        if "MAX_NUM_ORDERS" in fs:
            if ordinary + 1 > fs["MAX_NUM_ORDERS"]["maxNumOrders"]:
                raise Invalid("MAX_NUM_ORDERS")
            checks.append("MAX_NUM_ORDERS:PASS_SIMULATED_COUNT_PLUS_ONE")
        if "MAX_NUM_ALGO_ORDERS" in fs:
            if algo > fs["MAX_NUM_ALGO_ORDERS"]["maxNumAlgoOrders"]:
                raise Invalid("MAX_NUM_ALGO_ORDERS")
            checks.append("MAX_NUM_ALGO_ORDERS:PASS_SIMULATED_COUNT_PLUS_ZERO_NON_ALGO")
    _levels(book.bids, True)
    _levels(book.asks, False)
    if not book.bids or not book.asks:
        raise Invalid("MISSING_BOOK_SIDE")
    if book.bids[0][0] >= book.asks[0][0]:
        raise Invalid("CROSSED_OR_LOCKED_BOOK")
    remaining, notional, fills = qty, ZERO, []
    reason = "INSUFFICIENT_DISPLAYED_DEPTH"
    for p, available in (book.asks if intent.side == "BUY" else book.bids):
        if (p > price if intent.side == "BUY" else p < price):
            reason = "LIMIT_PRICE"
            break
        # Conservative: do not assume odd-lot dust can be combined across levels.
        take = (min(remaining, available) / step).to_integral_value(rounding=ROUND_FLOOR) * step
        if take:
            fills.append((p, take))
            notional += p * take
            remaining -= take
        if remaining == 0:
            break
    filled = qty - remaining
    status = "COMPLETE" if remaining == 0 else "PARTIAL" if filled else "UNFILLED"
    return Estimate(status, "DISPLAYED_DEPTH_ONLY" if not remaining else reason,
                    qty, price, filled, remaining, notional, notional * fee, fee, tuple(fills),
                    tuple(checks), tuple(assumptions))

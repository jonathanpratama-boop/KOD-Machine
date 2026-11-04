"""Compose signal, allocation and risk into a traceable shadow simulation intent.

This is an opt-in, single-instrument diagnostic contract. It never writes to the
active trend account and never promotes a research strategy into that account.
The quote is an indicative sizing reference, not a fill. Execution requires a
separately retained later observation through the simulation executor.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from ..runtime.data import parse_time, utc_text
from ..runtime.storage import digest
from .costs import CostModel, decimal
from .strategy import assess_risk, evaluate_batch, portfolio_targets

VERSION = "KOD_SHADOW_PLAN_V1"


def _fields(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(f"{name}: explicit fields required: {fields}")


def evaluate_plan(request):
    """Return a risk-gated submit event for an isolated paper diagnostic.

    The fixed SHADOW_SIMULATION scope admits only the allowlisted research
    templates to this diagnostic; it grants no legacy account or live entry.
    Every result retains the request hash. Invalid input fails before an event
    exists; valid but stale/over-limit/insufficient-warmup input returns blockers.
    """
    _fields(
        request,
        "schema_version evidence_type strategy observations as_of portfolio quote "
        "allocation risk costs expires_at",
        "shadow plan",
    )
    if (
        request["schema_version"] != VERSION
        or not isinstance(request["evidence_type"], str)
        or request["evidence_type"] not in {"synthetic", "recorded"}
    ):
        raise ValueError("explicit synthetic or recorded shadow plan required")
    at = parse_time(request["as_of"])
    expires = parse_time(request["expires_at"])
    if expires <= at:
        raise ValueError("intent must expire after the decision")
    _fields(request["portfolio"], "cash quantity quote_currency", "portfolio")
    _fields(request["quote"], "symbol bid ask observed_at evidence_id quote_currency", "quote")
    _fields(request["allocation"], "gross_weight symbol_limit", "allocation")
    _fields(request["risk"], "max_gross max_symbol max_age_seconds", "risk")
    evaluation = evaluate_batch(
        {key: request[key] for key in ("strategy", "observations", "as_of")}
    )
    if not evaluation["decisions"]:
        raise ValueError("a shadow plan requires at least one observation")
    last = evaluation["decisions"][-1]
    quote = request["quote"]
    currency = request["portfolio"]["quote_currency"]
    if not isinstance(currency, str) or not currency.strip() or quote["quote_currency"] != currency:
        raise ValueError("cash and quote must have the same explicit quote currency")
    if last["symbol"] == "UNSPECIFIED" or quote["symbol"] != last["symbol"]:
        raise ValueError("quote and signal require one matching explicit symbol")
    if not isinstance(quote["evidence_id"], str) or not quote["evidence_id"].strip():
        raise ValueError("retained quote evidence reference required")
    quote_at = parse_time(quote["observed_at"])
    if quote_at > at:
        raise ValueError("quote was unavailable at the decision cutoff")
    bid = decimal(quote["bid"], "bid", positive=True)
    ask = decimal(quote["ask"], "ask", positive=True)
    if bid > ask:
        raise ValueError("crossed quote")
    cash = decimal(request["portfolio"]["cash"], "cash")
    holding = decimal(request["portfolio"]["quantity"], "quantity")
    model = CostModel.from_dict(request["costs"])
    if model.price_basis != "EXECUTABLE":
        raise ValueError("bid/ask sizing requires EXECUTABLE cost basis")
    age_limit = request["risk"]["max_age_seconds"]
    if isinstance(age_limit, bool) or not isinstance(age_limit, int) or age_limit < 0:
        raise ValueError("max_age_seconds: nonnegative integer required")
    fresh = (
        max(
            (at - quote_at).total_seconds(),
            (at - parse_time(last["observed_at"])).total_seconds(),
        )
        <= age_limit
    )
    known = last["status"] == "READY"
    targets = portfolio_targets(
        {last["symbol"]: last["signal"] if known else 0}, **request["allocation"]
    )
    risk = assess_risk(
        targets,
        admitted=True,  # The allowlist admits evaluation to this shadow scope only.
        fresh=fresh,
        max_gross=request["risk"]["max_gross"],
        max_symbol=request["risk"]["max_symbol"],
    )
    if not known:
        risk["allowed"] = False
        risk["reasons"].append("SIGNAL_WARMUP_UNKNOWN")
    identity = digest(request)
    plan_id = "shadow-plan:" + identity
    event = None
    sizing_estimate = None
    if risk["allowed"]:
        equity = cash + holding * bid
        weight = Decimal(targets[last["symbol"]])
        target_value = equity * weight
        delta = target_value - holding * bid
        buy, sell = model.prices(ask, bid)
        if delta > 0:
            side, limit = "BUY", buy
            quantity = min(delta, cash) / (limit * (1 + model.fee_rate))
            quantity = quantity.quantize(Decimal("1e-18"), rounding=ROUND_FLOOR)
        else:
            side, limit = "SELL", sell
            # Selling reduces both inventory and NAV through costs. Solve for
            # the target against that smaller NAV, rather than pre-cost equity.
            loss_per_unit = bid - sell * (1 - model.fee_rate)
            quantity = -delta / (bid - weight * loss_per_unit)
            quantity = min(holding, quantity.quantize(Decimal("1e-18"), rounding=ROUND_CEILING))
        # These are conservative simulation precisions, not venue lot sizes.
        if quantity > 0:
            expense = quantity * limit
            after_cash = (
                cash - expense * (1 + model.fee_rate)
                if side == "BUY"
                else cash + expense * (1 - model.fee_rate)
            )
            after_quantity = holding + quantity if side == "BUY" else holding - quantity
            after_nav = after_cash + after_quantity * bid
            after_weight = after_quantity * bid / after_nav if after_nav > 0 else Decimal(0)
            post_cost = assess_risk(
                {last["symbol"]: str(after_weight)},
                admitted=True,
                fresh=fresh,
                max_gross=request["risk"]["max_gross"],
                max_symbol=request["risk"]["max_symbol"],
            )
            sizing_estimate = {
                "cash": str(after_cash),
                "quantity": str(after_quantity),
                "nav_at_current_bid": str(after_nav),
                "weight_at_current_bid": str(after_weight),
                "basis": "ASSUMED_LIMIT_FILL_AND_CURRENT_BID_NOT_AN_OBSERVED_FILL",
                "risk": post_cost,
            }
            if not post_cost["allowed"]:
                risk["allowed"] = False
                risk["reasons"].extend("POST_COST_" + r for r in post_cost["reasons"])
            else:
                event = {
                    "event_id": "submit:" + identity,
                    "kind": "submit",
                    "at": utc_text(at),
                    "order_id": plan_id,
                    "symbol": last["symbol"],
                    "side": side,
                    "quantity": str(quantity),
                    "limit_price": str(limit),
                    "expires_at": utc_text(expires),
                    "decision": {
                        "plan_id": plan_id,
                        "input_sha256": identity,
                        "strategy_id": evaluation["strategy"]["id"],
                        "strategy_version": evaluation["strategy"]["version"],
                        "scope": "SHADOW_SIMULATION",
                    },
                }
    return {
        "schema_version": VERSION,
        "plan_id": plan_id,
        "input_sha256": identity,
        "scope": "SHADOW_SIMULATION",
        "evidence_type": request["evidence_type"],
        "evaluation": evaluation,
        "proposed_targets": targets if known else None,
        "risk": risk,
        "quote_evidence_id": quote["evidence_id"],
        "costs": model.as_dict(),
        "quote_currency": currency,
        "quantity_precision_basis": "SIMULATION_BUY_FLOOR_SELL_CEILING_18_PLACES_NOT_VENUE_FILTERS",
        "sizing_estimate": sizing_estimate,
        "submit_event": event,
        "legacy_account_entry_enabled": False,
        "live_enabled": False,
    }

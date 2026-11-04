"""Preparation and executable-price observations for timing research.

Pure, offline adapters. They never submit orders, change candidate eligibility,
rewrite the catalyst register, or replace a frozen account's cost assumptions.
Calendar times are declarations backed by caller-retained evidence; the adapter
validates chronology, not the truth of a source. A quote is not a guaranteed fill.
"""

from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .runtime.data import number, parse_time, utc_text
from .runtime.storage import digest

CALENDAR_SCHEMA = "KOD_CATALYST_CALENDAR_V1"
PREPARATION_SCHEMA = "KOD_CATALYST_PREPARATION_V1"
COST_SCHEMA = "KOD_COST_PROFILE_V1"
SHADOW_SCHEMA = "KOD_SHADOW_EXECUTABILITY_V1"
AVOID_SCHEMA = "KOD_AVOID_OBSERVATION_V1"
FAMILIES = {
    "EARNINGS",
    "TOKEN_UNLOCK",
    "GOVERNANCE",
    "INDEX_REBALANCE",
    "EXCHANGE_NOTICE",
    "OTHER_DATED",
}
AVOID_CHECKS = {
    "wild_volatility",
    "lone_spike",
    "recent_30pct_spike",
    "share_issuance",
    "crowded_short",
}
FRACTIONS = (
    "buy_fee_fraction",
    "sell_fee_fraction",
    "buy_slippage_fraction",
    "sell_slippage_fraction",
    "fx_cost_fraction",
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty text required")
    return value.strip()


def _stamp(value: Any, field: str) -> str:
    return utc_text(parse_time(value, field))


def _observed_time(value: Any, field: str, cutoff: str) -> str:
    stamp = _stamp(value, field)
    if parse_time(stamp) > parse_time(cutoff):
        raise ValueError(f"{field}: future information")
    return stamp


def validate_calendar_event(event: dict, *, as_of: str) -> dict:
    """Normalize a new calendar version; original records must remain untouched."""
    if not isinstance(event, dict):
        raise ValueError("calendar event object required")
    value = copy.deepcopy(event)
    cutoff = _stamp(as_of, "as_of")
    if value.get("schema_version") != CALENDAR_SCHEMA:
        raise ValueError("unsupported catalyst calendar schema")
    for key in ("id", "instrument_id", "evidence_id", "source_timezone"):
        value[key] = _text(value.get(key), key)
    version = value.get("version")
    if type(version) is not int or version < 1:
        raise ValueError("positive calendar version required")
    if version == 1 and value.get("supersedes") is not None:
        raise ValueError("first event version cannot supersede a record")
    if version > 1:
        _text(value.get("supersedes"), "supersedes")
    if value.get("family") not in FAMILIES:
        raise ValueError("unsupported catalyst family")
    if value.get("evidence_kind") not in {"synthetic", "recorded", "prospective"}:
        raise ValueError("explicit calendar evidence kind required")
    source = urlparse(_text(value.get("source_url"), "source_url"))
    synthetic = value["evidence_kind"] == "synthetic"
    if (
        source.username
        or source.password
        or (
            source.scheme != "https"
            and not (synthetic and source.scheme == "synthetic")
        )
    ):
        raise ValueError("credential-free source URL required")
    if not source.netloc:
        raise ValueError("source host required")
    try:
        ZoneInfo(value["source_timezone"])
    except ZoneInfoNotFoundError as exc:
        raise ValueError("unknown source timezone") from exc
    value["received_at"] = _observed_time(
        value.get("received_at"), "received_at", cutoff
    )
    if value.get("published_at") is not None:
        value["published_at"] = _observed_time(
            value["published_at"], "published_at", value["received_at"]
        )
    precision = value.get("time_precision")
    if precision not in {"EXACT", "WINDOW", "DATE_ONLY", "UNKNOWN"}:
        raise ValueError("explicit calendar time precision required")
    if precision in {"EXACT", "WINDOW"}:
        value["event_at"] = _stamp(value.get("event_at"), "event_at")
        if precision == "WINDOW":
            value["window_end"] = _stamp(value.get("window_end"), "window_end")
            if parse_time(value["window_end"]) <= parse_time(value["event_at"]):
                raise ValueError("calendar window must end after its start")
        elif value.get("window_end") is not None:
            raise ValueError("exact calendar time cannot also specify a window")
    else:
        if value.get("event_at") is not None or value.get("window_end") is not None:
            raise ValueError("unknown/date-only event must not invent an exact time")
        if precision == "DATE_ONLY":
            date.fromisoformat(_text(value.get("event_date"), "event_date"))
    if value.get("status") not in {"SCHEDULED", "CANCELLED"}:
        raise ValueError("calendar status must be SCHEDULED or CANCELLED")
    value.update(
        record_id=f"{value['id']}:v{version}",
        simulation_only=True,
        entry_permission=False,
    )
    return value


def prepare_event(event: dict, branches: list[dict], *, prepared_at: str) -> dict:
    """Freeze research branches before a known event; cannot prepare retroactively."""
    prepared_at = _stamp(prepared_at, "prepared_at")
    event = validate_calendar_event(event, as_of=prepared_at)
    if (
        event["time_precision"] not in {"EXACT", "WINDOW"}
        or event["status"] != "SCHEDULED"
    ):
        raise ValueError(
            "known scheduled time required to establish preparation before event"
        )
    if parse_time(prepared_at) >= parse_time(event["event_at"]):
        raise ValueError("preparation must be before the event/window starts")
    if not isinstance(branches, list) or not branches:
        raise ValueError("at least one explicit research branch required")
    normalized, ids = [], set()
    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError("research branch object required")
        branch = copy.deepcopy(branch)
        for key in ("id", "condition", "mechanism"):
            branch[key] = _text(branch.get(key), "branch." + key)
        if branch["id"] in ids:
            raise ValueError("duplicate branch id")
        ids.add(branch["id"])
        if branch.get("action") not in {"RESEARCH", "NO_ACTION", "RECHECK"}:
            raise ValueError("branches support research actions only")
        normalized.append(branch)
    value = {
        "schema_version": PREPARATION_SCHEMA,
        "event_id": event["id"],
        "event_record_id": event["record_id"],
        "event_sha256": digest(event),
        "evidence_id": event["evidence_id"],
        "prepared_at": prepared_at,
        "event_at": event["event_at"],
        "branches": normalized,
        "simulation_only": True,
        "entry_permission": False,
        "source_verification": "CALLER_RETAINED_DECLARATION",
    }
    return {"id": "preparation_" + digest(value)[:32], **value}


def calendar_board(
    events: list[dict], *, as_of: str, horizon_seconds: int = 86400
) -> dict:
    """Project latest declared versions. Date-only events never imply an exact due time."""
    cutoff = parse_time(as_of)
    if type(horizon_seconds) is not int or horizon_seconds <= 0:
        raise ValueError("positive horizon_seconds required")
    versions: dict[tuple[str, int], dict] = {}
    for raw in events:
        event = validate_calendar_event(raw, as_of=as_of)
        key = (event["id"], event["version"])
        if key in versions and versions[key] != event:
            raise ValueError("conflicting calendar version")
        versions[key] = event
    latest = {}
    for (_, _), value in sorted(versions.items()):
        previous = latest.get(value["id"])
        if previous is not None and value["supersedes"] != previous["record_id"]:
            raise ValueError("calendar revision must name previous retained version")
        latest[value["id"]] = value
    rows = []
    for value in latest.values():
        value = copy.deepcopy(value)
        seconds = None
        if value["status"] == "CANCELLED":
            state = "CANCELLED"
        elif value["time_precision"] in {"DATE_ONLY", "UNKNOWN"}:
            state = "UNKNOWN_TIME"
        else:
            seconds = (parse_time(value["event_at"]) - cutoff).total_seconds()
            end = parse_time(value.get("window_end") or value["event_at"])
            state = (
                "ELAPSED"
                if end < cutoff
                else "DUE"
                if seconds <= horizon_seconds
                else "SCHEDULED"
            )
        value.update(timing_state=state, seconds_until_event=seconds)
        rows.append(value)
    rows.sort(key=lambda x: (x.get("event_at") or "9999", x["id"]))
    return {
        "as_of": utc_text(cutoff),
        "events": rows,
        "due_count": sum(r["timing_state"] == "DUE" for r in rows),
        "entry_permission": False,
    }


def validate_cost_profile(profile: dict, *, as_of: str) -> dict:
    """Validate named assumptions as of a cutoff, preserving unknown fee components."""
    if not isinstance(profile, dict):
        raise ValueError("cost profile object required")
    value = copy.deepcopy(profile)
    if value.get("schema_version") != COST_SCHEMA:
        raise ValueError("unsupported cost profile schema")
    for key in ("id", "venue", "quote_currency"):
        value[key] = _text(value.get(key), key)
    if type(value.get("version")) is not int or value["version"] < 1:
        raise ValueError("positive cost profile version required")
    value["valid_from"] = _observed_time(value.get("valid_from"), "valid_from", as_of)
    if value.get("valid_until") is not None:
        value["valid_until"] = _stamp(value["valid_until"], "valid_until")
        if parse_time(value["valid_until"]) <= parse_time(value["valid_from"]):
            raise ValueError("cost profile has invalid effective interval")
        if parse_time(as_of) >= parse_time(value["valid_until"]):
            raise ValueError("cost profile expired")
    if value.get("verification_status") not in {
        "OWNER_REPORTED_ASSUMPTION",
        "SIMULATION_ASSUMPTION",
        "HISTORICAL_STUDY_ASSUMPTION",
        "VERIFIED_ACCOUNT_QUOTE",
    }:
        raise ValueError("explicit cost verification status required")
    if value.get("account_applicability") not in {
        "UNKNOWN",
        "SYNTHETIC_ONLY",
        "VERIFIED",
    }:
        raise ValueError("explicit account applicability required")
    if value["verification_status"] == "VERIFIED_ACCOUNT_QUOTE":
        _text(value.get("account_quote_evidence_id"), "account_quote_evidence_id")
        _observed_time(value.get("verified_at"), "verified_at", as_of)
        if value["account_applicability"] != "VERIFIED":
            raise ValueError("verified account quote requires verified applicability")
    for field in FRACTIONS:
        value[field] = number(value.get(field), field, nullable=True)
        if value[field] is not None and Decimal(value[field]) >= 1:
            raise ValueError("cost fraction must be below one")
    if value.get("spread_convention") != "OBSERVED_BID_ASK":
        raise ValueError("spread must be counted once through observed bid/ask")
    if (
        type(value.get("max_quote_age_seconds")) is not int
        or value["max_quote_age_seconds"] <= 0
    ):
        raise ValueError("positive quote age bound required")
    if not isinstance(value.get("sources"), list) or not value["sources"]:
        raise ValueError("cost profile needs source/assumption references")
    value.update(simulation_only=True, entry_permission=False)
    return value


def account_cost_profile(account_profile: dict, *, as_of: str) -> dict:
    """Name an existing simulation's costs without changing that account's bytes/hash."""
    if not isinstance(account_profile, dict):
        raise ValueError("account profile object required")
    synthetic = account_profile.get("evidence_type") == "synthetic"
    result = {
        "schema_version": COST_SCHEMA,
        "id": _text(account_profile.get("id"), "account profile id") + ":costs-v1",
        "version": 1,
        "legacy_profile_id": account_profile["id"],
        "legacy_profile_sha256": digest(account_profile),
        "venue": account_profile["venue"],
        "quote_currency": account_profile["quote_currency"],
        "valid_from": _stamp(as_of, "as_of"),
        "valid_until": None,
        "buy_fee_fraction": account_profile.get("fee_rate"),
        "sell_fee_fraction": account_profile.get("fee_rate"),
        "buy_slippage_fraction": account_profile.get("slippage"),
        "sell_slippage_fraction": account_profile.get("slippage"),
        "fx_cost_fraction": None,
        "spread_convention": "OBSERVED_BID_ASK",
        "verification_status": "SIMULATION_ASSUMPTION",
        "account_applicability": "SYNTHETIC_ONLY" if synthetic else "UNKNOWN",
        "max_quote_age_seconds": account_profile.get("max_quote_age", 30),
        "sources": [
            {
                "kind": "immutable_account_profile",
                "id": account_profile["id"],
                "sha256": digest(account_profile),
            }
        ],
        "limitations": [
            "No verified owner brokerage cost or FX conversion.",
            "Existing account rounding/fill rules remain authoritative for its ledger.",
        ],
    }
    return validate_cost_profile(result, as_of=as_of)


def shadow_executability(
    decision: dict,
    quote: dict | None,
    cost_profile: dict,
    *,
    as_of: str,
    owner_venue: str | None = None,
    requested_quantity: str | None = None,
) -> dict:
    """Evaluate a retained post-availability quote, never manufacture a fill.

    OBSERVED means a fresh, structurally usable quote at the recorded venue.
    It grants no entry permission and does not establish owner account access.
    Historical outcome-label opens and pre-decision requests cannot qualify.
    """
    if not isinstance(decision, dict) or (
        quote is not None and not isinstance(quote, dict)
    ):
        raise ValueError("decision and optional quote objects required")
    cutoff = parse_time(as_of)
    did = _text(decision.get("id"), "decision.id")
    for key in ("symbol", "venue"):
        _text(decision.get(key), "decision." + key)
    when = parse_time(decision.get("decision_at"), "decision_at")
    available = parse_time(
        decision.get("available_at") or decision["decision_at"], "available_at"
    )
    expiry = parse_time(decision.get("expires_at"), "expires_at")
    if when > available or available > cutoff or expiry <= available:
        raise ValueError("invalid decision availability/expiry chronology")
    profile = validate_cost_profile(cost_profile, as_of=as_of)
    result = {
        "schema_version": SHADOW_SCHEMA,
        "decision_id": did,
        "as_of": utc_text(cutoff),
        "available_at": utc_text(available),
        "quote_evidence_id": None,
        "quote_received_at": None,
        "cost_profile_id": profile["id"],
        "cost_profile_sha256": digest(profile),
        "status": "UNKNOWN",
        "reasons": [],
        "simulation_only": True,
        "entry_permission": False,
        "owner_venue": owner_venue,
        "owner_venue_executable": False,
        "fill_at": None,
        "executable_at": None,
        "spread_fraction": None,
        "spread_basis": "(ask-bid)/mid; already included in bid/ask economics",
        "instant_round_trip_return": None,
        "return_basis": "hypothetical same-quote liquidation, quote currency, excludes FX; not a forecast/fill",
        "fx_cost_fraction": profile["fx_cost_fraction"],
        "unknown_costs": [k for k in FRACTIONS if profile[k] is None],
        "depth_scope": "UNKNOWN",
        "capacity_status": "UNKNOWN",
        "cost_scope": "QUOTE_VENUE_ONLY",
        "quote_currency": profile["quote_currency"],
        "currency_basis": "PROFILE_DECLARATION",
    }
    if cutoff >= expiry:
        result.update(status="EXPIRED", reasons=["DECISION_EXPIRED"])
        return result
    if quote is None:
        result["reasons"].append("MISSING_QUOTE")
        return result
    for key in ("symbol", "venue"):
        _text(quote.get(key), "quote." + key)
        _text(decision.get(key), "decision." + key)
    received = parse_time(quote.get("received_at"), "quote.received_at")
    result.update(
        quote_evidence_id=_text(quote.get("evidence_id"), "quote.evidence_id"),
        quote_received_at=utc_text(received),
        quote_venue=quote["venue"],
        symbol=quote["symbol"],
    )
    reasons = result["reasons"]
    if quote["symbol"] != decision["symbol"] or quote["venue"] != decision["venue"]:
        reasons.append("INSTRUMENT_MISMATCH")
    if profile["venue"] != quote["venue"]:
        reasons.append("COST_VENUE_MISMATCH")
    if (
        quote.get("quote_currency") is not None
        and quote["quote_currency"] != profile["quote_currency"]
    ):
        reasons.append("COST_CURRENCY_MISMATCH")
    if received < available:
        reasons.append("QUOTE_PRECEDES_AVAILABILITY")
    if received > cutoff:
        reasons.append("FUTURE_QUOTE")
    if (cutoff - received).total_seconds() > profile["max_quote_age_seconds"]:
        reasons.append("STALE_QUOTE")
    request = quote.get("request_started_at")
    if request is not None:
        request = parse_time(request, "request_started_at")
        if request < available:
            reasons.append("REQUEST_PRECEDES_AVAILABILITY")
        if request > received:
            reasons.append("REVERSED_REQUEST_CHRONOLOGY")
    source = quote.get("source_time")
    if source is not None:
        source = parse_time(source, "quote.source_time")
        if source < available:
            reasons.append("QUOTE_SOURCE_PRECEDES_AVAILABILITY")
        if source > received:
            reasons.append("SOURCE_CLOCK_CONFLICT")
        if (cutoff - source).total_seconds() > profile["max_quote_age_seconds"]:
            reasons.append("STALE_SOURCE_QUOTE")
    bid = Decimal(number(quote.get("bid"), "bid", positive=True))
    ask = Decimal(number(quote.get("ask"), "ask", positive=True))
    if bid > ask:
        reasons.append("CROSSED_QUOTE")
    result["spread_fraction"] = str((ask - bid) / ((ask + bid) / 2))
    result["depth_scope"] = "TOP_OF_BOOK_ONLY"
    ask_size = number(quote.get("ask_size"), "ask_size", nullable=True)
    bid_size = number(quote.get("bid_size"), "bid_size", nullable=True)
    if ask_size is not None and Decimal(ask_size) == 0:
        reasons.append("NO_DISPLAYED_ASK_LIQUIDITY")
    result.update(bid=str(bid), ask=str(ask), bid_size=bid_size, ask_size=ask_size)
    if requested_quantity is not None:
        quantity = Decimal(
            number(requested_quantity, "requested_quantity", positive=True)
        )
        result["requested_quantity"] = str(quantity)
        if ask_size is None:
            reasons.append("MISSING_DISPLAYED_SIZE")
        elif quantity > Decimal(ask_size):
            reasons.append("INSUFFICIENT_DISPLAYED_SIZE")
            result["capacity_status"] = "INSUFFICIENT_DISPLAYED_SIZE"
        else:
            result["capacity_status"] = "DISPLAYED_SIZE_SUFFICIENT"
    known = all(profile[k] is not None for k in FRACTIONS if k != "fx_cost_fraction")
    if (
        known
        and not {"COST_VENUE_MISMATCH", "COST_CURRENCY_MISMATCH"}.intersection(reasons)
        and bid <= ask
    ):
        entry = (
            ask
            * (1 + Decimal(profile["buy_slippage_fraction"]))
            * (1 + Decimal(profile["buy_fee_fraction"]))
        )
        liquidation = (
            bid
            * (1 - Decimal(profile["sell_slippage_fraction"]))
            * (1 - Decimal(profile["sell_fee_fraction"]))
        )
        result["instant_round_trip_return"] = str(liquidation / entry - 1)
    if reasons:
        result["status"] = "REJECTED"
    elif owner_venue is not None and owner_venue != quote["venue"]:
        result.update(status="PROXY_ONLY", reasons=["OWNER_VENUE_QUOTE_UNAVAILABLE"])
    else:
        result["status"] = "OBSERVED"
    # Neither a venue match nor a displayed size guarantees fill/access. A valid
    # observation can be linked to timing, while actual fill_at remains unknown.
    if result["status"] in {"OBSERVED", "PROXY_ONLY"}:
        result["executable_at"] = utc_text(received)
        result["execution_basis"] = (
            "INDICATIVE_PROXY_QUOTE"
            if result["status"] == "PROXY_ONLY"
            else "INDICATIVE_QUOTE_ONLY"
        )
    return result


def validate_avoid_observation(record: dict, *, as_of: str) -> dict:
    """Retain hypotheses and unknowns; no checklist item is a universal veto."""
    if not isinstance(record, dict):
        raise ValueError("avoid observation object required")
    value = copy.deepcopy(record)
    if value.get("schema_version") != AVOID_SCHEMA:
        raise ValueError("unsupported avoid observation schema")
    for key in ("id", "decision_id"):
        value[key] = _text(value.get(key), key)
    value["as_of"] = _observed_time(value.get("as_of"), "as_of", as_of)
    raw_checks = value.get("checks")
    if not isinstance(raw_checks, dict) or set(raw_checks) - AVOID_CHECKS:
        raise ValueError("unsupported avoid check")
    checks = {}
    for key in sorted(AVOID_CHECKS):
        item = copy.deepcopy(
            raw_checks.get(
                key, {"status": "UNKNOWN", "evidence_id": None, "available_at": None}
            )
        )
        if not isinstance(item, dict):
            raise ValueError("avoid check object required")
        if item.get("status") not in {"PRESENT", "ABSENT", "UNKNOWN"}:
            raise ValueError("avoid status must be PRESENT, ABSENT, or UNKNOWN")
        if item.get("available_at") is not None:
            item["available_at"] = _observed_time(
                item["available_at"], "check.available_at", value["as_of"]
            )
        if item["status"] != "UNKNOWN":
            _text(item.get("evidence_id"), "check.evidence_id")
            item["available_at"] = _observed_time(
                item.get("available_at"), "check.available_at", value["as_of"]
            )
        checks[key] = item
    regime = value.get("regime", {"label": "UNKNOWN", "evidence_id": None})
    if not isinstance(regime, dict):
        raise ValueError("regime object required")
    _text(regime.get("label"), "regime.label")
    if regime["label"] != "UNKNOWN":
        _text(regime.get("evidence_id"), "regime.evidence_id")
        regime["available_at"] = _observed_time(
            regime.get("available_at"), "regime.available_at", value["as_of"]
        )
    value.update(
        checks=checks,
        regime=regime,
        simulation_only=True,
        entry_permission=False,
        veto=False,
        interpretation="UNVALIDATED_OBSERVATIONS_ONLY",
    )
    return value


def premove_shadow_decision(
    forecast: dict,
    symbol: str,
    *,
    observed_at: str,
    availability_evidence_id: str,
    expires_at: str,
    venue: str = "BINANCE_SPOT",
    sealed_at: str | None = None,
) -> dict:
    """Attach an execution clock to an original PREMOVE forecast without relabeling it.

    The original record hash is checked. Chain membership and external timestamp
    signatures need their existing independent verifiers. ``observed_at`` is the
    caller-retained availability receipt, never inferred from a daily open or the
    timestamp at which the forecasting function began. No outcome fields are read.
    """
    if (
        not isinstance(forecast, dict)
        or forecast.get("type") != "PREMOVE_SHADOW_FORECAST"
        or forecast.get("trial") != "PREMOVE_SHADOW_v1"
    ):
        raise ValueError("original PREMOVE_SHADOW_v1 forecast required")
    original_hash = _text(forecast.get("record_hash"), "forecast.record_hash")
    if (
        digest({k: v for k, v in forecast.items() if k != "record_hash"})
        != original_hash
    ):
        raise ValueError("forecast record hash mismatch")
    if symbol not in forecast.get("candidates", {}):
        raise ValueError("instrument was not in the frozen forecast universe")
    observed = parse_time(observed_at, "observed_at")
    made = parse_time(forecast.get("made_at"), "forecast.made_at")
    expiry = parse_time(expires_at, "expires_at")
    if observed < made or expiry <= observed:
        raise ValueError("invalid forecast availability/expiry chronology")
    if sealed_at is not None:
        sealed = parse_time(sealed_at, "sealed_at")
        if sealed < made or observed < sealed:
            raise ValueError("forecast availability must follow seal time")
    evidence = _text(availability_evidence_id, "availability_evidence_id")
    return {
        "id": "premove_execution_"
        + digest(
            {
                "forecast": original_hash,
                "symbol": symbol,
                "availability_evidence_id": evidence,
            }
        )[:32],
        "decision_at": utc_text(observed),
        "available_at": utc_text(observed),
        "expires_at": utc_text(expiry),
        "symbol": _text(symbol, "symbol"),
        "venue": _text(venue, "venue"),
        "forecast_record_hash": original_hash,
        "forecast_made_at": utc_text(made),
        "availability_evidence_id": evidence,
        "sealed_at": None if sealed_at is None else _stamp(sealed_at, "sealed_at"),
        "original_label_reference": copy.deepcopy(forecast.get("entry")),
        "decision_clock_basis": "RETAINED_FORECAST_AVAILABILITY_RECEIPT",
        "forecast_chain_verification": "REQUIRES_EXISTING_LEDGER_VERIFIER",
        "external_timestamp_verification": "NOT_ESTABLISHED_BY_THIS_ADAPTER",
        "simulation_only": True,
        "entry_permission": False,
    }


def build_timing_context(payload: dict, *, as_of: str) -> dict:
    """Validate a supplied context pack for the runtime's immutable evidence store."""
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != "KOD_TIMING_CONTEXT_V1"
    ):
        raise ValueError("unsupported timing context schema")
    _stamp(as_of, "as_of")
    if payload.get("as_of") is not None and parse_time(payload["as_of"]) != parse_time(
        as_of
    ):
        raise ValueError("context cutoff differs from supplied as_of")
    collections = (
        "calendar_events",
        "preparations",
        "avoid_observations",
        "shadow_checks",
    )
    for key in collections:
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key}: list required")
    events = [
        validate_calendar_event(e, as_of=as_of)
        for e in payload.get("calendar_events", [])
    ]
    by_record = {e["record_id"]: e for e in events}
    preparations = []
    for item in payload.get("preparations", []):
        if not isinstance(item, dict):
            raise ValueError("preparation object required")
        event_id = _text(item.get("event_record_id"), "event_record_id")
        if event_id not in by_record:
            raise ValueError("preparation references missing calendar event version")
        prepared_at = _observed_time(item.get("prepared_at"), "prepared_at", as_of)
        preparations.append(
            prepare_event(
                by_record[event_id], item.get("branches"), prepared_at=prepared_at
            )
        )
    shadow = []
    for item in payload.get("shadow_checks", []):
        if not isinstance(item, dict):
            raise ValueError("shadow check object required")
        decision = item.get("decision")
        if item.get("premove_forecast") is not None:
            if decision is not None:
                raise ValueError("shadow check chooses one decision source")
            args = item.get("premove_availability")
            if not isinstance(args, dict):
                raise ValueError("premove availability receipt required")
            decision = premove_shadow_decision(item["premove_forecast"], **args)
        shadow.append(
            shadow_executability(
                decision,
                item.get("quote"),
                item.get("cost_profile"),
                as_of=as_of,
                owner_venue=item.get("owner_venue"),
                requested_quantity=item.get("requested_quantity"),
            )
        )
    avoid = [
        validate_avoid_observation(r, as_of=as_of)
        for r in payload.get("avoid_observations", [])
    ]
    return {
        "schema_version": "KOD_TIMING_CONTEXT_V1",
        "as_of": _stamp(as_of, "as_of"),
        "input_sha256": digest(payload),
        "calendar": calendar_board(events, as_of=as_of),
        "preparations": preparations,
        "shadow": shadow,
        "avoid": avoid,
        "source_validation": "DECLARATIONS_AND_CHRONOLOGY_ONLY; raw source verification remains required",
        "simulation_only": True,
        "entry_permission": False,
    }


def context_fixture() -> dict:
    """Deterministic synthetic context input; creates no market or paper-trade result."""
    cutoff = "2026-11-04T00:30:00Z"
    event = {
        "schema_version": CALENDAR_SCHEMA,
        "id": "synthetic:event:1",
        "version": 1,
        "supersedes": None,
        "family": "EARNINGS",
        "instrument_id": "SYNTHETIC_SPOT:AAA",
        "time_precision": "EXACT",
        "event_at": "2026-11-04T01:00:00Z",
        "window_end": None,
        "source_timezone": "UTC",
        "published_at": "2026-11-03T12:00:00Z",
        "received_at": "2026-11-03T12:01:00Z",
        "evidence_id": "synthetic:calendar:1",
        "source_url": "synthetic://calendar-fixture",
        "evidence_kind": "synthetic",
        "status": "SCHEDULED",
    }
    profile = account_cost_profile(
        {
            "id": "synthetic:context-costs",
            "venue": "SYNTHETIC_SPOT",
            "quote_currency": "USDT",
            "fee_rate": "0.01",
            "slippage": "0",
            "evidence_type": "synthetic",
        },
        as_of=cutoff,
    )
    decision = {
        "id": "synthetic:context-decision",
        "decision_at": "2026-11-04T00:25:00Z",
        "available_at": "2026-11-04T00:25:01Z",
        "expires_at": "2026-11-04T00:31:00Z",
        "symbol": "AAA",
        "venue": "SYNTHETIC_SPOT",
    }
    quote = {
        "symbol": "AAA",
        "venue": "SYNTHETIC_SPOT",
        "evidence_id": "synthetic:quote:1",
        "received_at": "2026-11-04T00:29:59Z",
        "source_time": None,
        "request_started_at": "2026-11-04T00:29:58Z",
        "bid": "100",
        "ask": "101",
        "bid_size": "10",
        "ask_size": "10",
    }
    old_quote = {
        **quote,
        "evidence_id": "synthetic:old-label-open",
        "received_at": "2026-11-04T00:00:00Z",
        "request_started_at": "2026-11-03T23:59:59Z",
    }
    return {
        "schema_version": "KOD_TIMING_CONTEXT_V1",
        "as_of": cutoff,
        "calendar_events": [event],
        "preparations": [
            {
                "event_record_id": "synthetic:event:1:v1",
                "prepared_at": cutoff,
                "branches": [
                    {
                        "id": "result-branch",
                        "condition": "Result changes the stated economics",
                        "mechanism": "Unvalidated repricing hypothesis",
                        "action": "RESEARCH",
                    }
                ],
            }
        ],
        "shadow_checks": [
            {
                "decision": decision,
                "quote": quote,
                "cost_profile": profile,
                "owner_venue": "ETORO",
                "requested_quantity": "2",
            },
            {
                "decision": {**decision, "id": "synthetic:context-early-quote"},
                "quote": old_quote,
                "cost_profile": profile,
            },
        ],
        "avoid_observations": [
            {
                "schema_version": AVOID_SCHEMA,
                "id": "synthetic:avoid:1",
                "decision_id": decision["id"],
                "as_of": cutoff,
                "regime": {"label": "UNKNOWN", "evidence_id": None},
                "checks": {},
            }
        ],
    }

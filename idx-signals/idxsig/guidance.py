"""GUIDANCE-REVISION-v1: source-bound features and local shadow-paper decisions.

No order API, performance search, historical outcome loader or scheduler.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import hashlib
import html
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
KEYS = ("issuer_cik", "fiscal_year", "metric", "representation", "currency", "units", "scope", "base_period")


def moment(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return result.astimezone(UTC)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def verify_freeze(root):
    root = Path(root)
    freeze = json.loads((root / "FREEZE.json").read_text())
    for name, expected in freeze["files"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen file changed: " + name)
    moment(freeze["frozen_at_utc"])
    return json.loads((root / "protocol.json").read_text()), freeze


def plain(value):
    # Same extraction convention as the existing ten-announcement source checker.
    value = re.sub(r"<(script|style)\b.*?</\1>", "", value, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value))).strip()


def submission(raw, expected_cik, expected_accession):
    text = raw.decode("utf-8", errors="replace")
    if not text.startswith("<SEC-DOCUMENT>"):
        raise ValueError("not an SEC submission")
    if not re.search(r"ACCESSION NUMBER:\s*" + re.escape(expected_accession), text):
        raise ValueError("accession mismatch")
    if not re.search(r"CENTRAL INDEX KEY:\s*0*" + str(int(expected_cik)) + r"\b", text):
        raise ValueError("CIK mismatch")
    header = re.search(r"<ACCEPTANCE-DATETIME>\s*(\d{14})", text)
    if not header:
        raise ValueError("missing SGML acceptance")
    accepted = datetime.strptime(header[1], "%Y%m%d%H%M%S").replace(tzinfo=NY).astimezone(UTC)
    docs = {}
    for block in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", text, re.I | re.S):
        kind = re.search(r"<TYPE>([^\r\n<]+)", block)
        name = re.search(r"<FILENAME>([^\r\n<]+)", block)
        body = re.search(r"<TEXT>(.*?)</TEXT>", block, re.I | re.S)
        if kind and name and body and (kind[1].strip() == "8-K" or kind[1].startswith("EX-99")):
            docs[name[1].strip()] = plain(body[1])
    if not docs:
        raise ValueError("no earnings documents")
    return {"issuer_cik": int(expected_cik), "accession": expected_accession,
            "accepted_at_utc": accepted.isoformat(), "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "documents": docs}


def bind_guidance(package, review):
    """Validate an explicit document review. Semantic correctness still needs review.

    Unsupported/ambiguous disclosures remain a classification, never default to zero.
    """
    if review.get("classification") != "NUMERIC_ANNUAL_REVENUE":
        return {"classification": review.get("classification", "REVIEW_REQUIRED"),
                "reason": review.get("reason", "No admitted comparable guidance"),
                "accession": package["accession"]}
    result = dict(review)
    if result.get("issuer_cik") != package["issuer_cik"]:
        raise ValueError("review issuer mismatch")
    for key in KEYS:
        if key not in result or result[key] in (None, ""):
            raise ValueError("missing comparability field: " + key)
    if result["metric"] != "full_year_revenue" or result["representation"] not in ("level", "growth_percent") or result["scope"] != "consolidated":
        raise ValueError("unsupported guidance metric/representation")
    if not re.fullmatch(r"20\d{2}", str(result["fiscal_year"])):
        raise ValueError("invalid fiscal year")
    if result["representation"] == "growth_percent" and not re.fullmatch(r"20\d{2}", str(result["base_period"])):
        raise ValueError("growth base year required")
    source = package["documents"].get(result["document"])
    quote = result.get("quote", "")
    if source is None or not quote or quote not in source:
        raise ValueError("guidance quote not in source document")
    start = source.index(quote)
    lower, upper = Decimal(str(result["lower"])), Decimal(str(result["upper"]))
    if not lower.is_finite() or not upper.is_finite() or lower > upper:
        raise ValueError("invalid guidance bounds")
    numbers = {Decimal(x.replace(",", "")) for x in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", quote)}
    if lower not in numbers or upper not in numbers:
        raise ValueError("guidance numbers unsupported by quotation")
    level = (lower + upper) / 2
    if result["representation"] == "growth_percent":
        level = 1 + level / 100
    if level <= 0:
        raise ValueError("nonpositive forecast level")
    result.update(lower=str(lower), upper=str(upper), forecast_level=str(level),
                  accession=package["accession"], accepted_at_utc=package["accepted_at_utc"],
                  raw_sha256=package["raw_sha256"], source_span=[start, start + len(quote)],
                  text_sha256=hashlib.sha256(source.encode()).hexdigest())
    return result


def revision(prior, current, *, latest_prior_confirmed):
    if not latest_prior_confirmed:
        return {"classification": "REVIEW_REQUIRED", "reason": "Latest comparable prior not verified"}
    if prior.get("classification") != "NUMERIC_ANNUAL_REVENUE" or current.get("classification") != "NUMERIC_ANNUAL_REVENUE":
        return {"classification": "NO_COMPARABLE_GUIDANCE", "reason": "Absent or different metric/horizon"}
    mismatch = [key for key in KEYS if prior[key] != current[key]]
    if mismatch:
        return {"classification": "INCOMPARABLE", "mismatched_fields": mismatch}
    if moment(prior["accepted_at_utc"]) >= moment(current["accepted_at_utc"]):
        raise ValueError("prior was not available before current guidance")
    change = Decimal(current["forecast_level"]) / Decimal(prior["forecast_level"]) - 1
    label = "RAISED" if change > 0 else "LOWERED" if change < 0 else "UNCHANGED"
    return {"classification": label, "forecast_level_change_fraction": str(change),
            "prior_accession": prior["accession"], "current_accession": current["accession"],
            "issuer_cik": current["issuer_cik"], "fiscal_year": current["fiscal_year"],
            "latest_prior_confirmed": True}


def session_schedule(ready_at, source_at, policy):
    """Use exchange sessions, including holidays and DST; never infer weekdays only."""
    import exchange_calendars as xc
    import pandas as pd
    ready, source = moment(ready_at), moment(source_at)
    if ready < source:
        raise ValueError("decision ready before source")
    cal = xc.get_calendar("XNYS")
    start = (source - timedelta(days=1)).date().isoformat()
    end = (ready + timedelta(days=90)).date().isoformat()
    sessions = cal.sessions_in_range(start, end)
    entries = []
    source_session_count = 0
    first = None
    hour, minute = map(int, policy["entry_time_et"].split(":"))
    for day in sessions:
        opening = cal.session_open(day).to_pydatetime()
        planned = datetime.combine(day.date(), datetime.min.time(), NY).replace(hour=hour, minute=minute).astimezone(UTC)
        if opening > source:
            source_session_count += 1
        if planned > ready and first is None:
            first = (day, planned, source_session_count)
        if first:
            entries.append(day)
    if first is None or len(entries) < policy["hold_sessions"]:
        raise ValueError("calendar does not cover holding period")
    _, planned, age = first
    exit_day = entries[policy["hold_sessions"] - 1]
    return {"entry_at_utc": planned.isoformat(),
            "entry_deadline_utc": (planned + timedelta(minutes=1)).isoformat(),
            "entry_session": first[0].date().isoformat(),
            "time_exit_at_utc": cal.session_close(exit_day).to_pydatetime().isoformat(),
            "time_exit_session": exit_day.date().isoformat(),
            "source_age_sessions": age,
            "source_fresh": age <= policy["max_source_to_entry_sessions"],
            "calendar": "XNYS", "calendar_version": xc.__version__}


def risk_size(entry_price, policy, *, cash, equity, open_positions=0, whole_units=False):
    price = Decimal(str(entry_price))
    cash, equity = Decimal(str(cash)), Decimal(str(equity))
    if not all(x.is_finite() and x > 0 for x in (price, cash, equity)):
        raise ValueError("positive finite price, cash and equity required")
    if open_positions >= policy["max_positions"]:
        return {"units": "0", "reason": "POSITION_CAP"}
    stop = Decimal(str(policy["stop_fraction"]))
    commission = Decimal(str(policy["commission_per_side_usd"]))
    slip = Decimal(str(policy["slippage_per_side_fraction"]))
    budget = equity * Decimal(str(policy["risk_fraction"]))
    # Entry price already includes buy stress. Sell stress is counted once here.
    loss_fraction = 1 - (1 - stop) * (1 - slip)
    max_loss_notional = max(Decimal(0), (budget - 2 * commission) / loss_fraction)
    notional = min(equity * Decimal(str(policy["max_notional_fraction"])), cash - commission, max_loss_notional)
    units = max(Decimal(0), notional / price)
    units = units.quantize(Decimal("1") if whole_units else Decimal("0.000001"), rounding=ROUND_DOWN)
    exposure = units * price
    return {"units": str(units), "entry_price": str(price), "notional_usd": str(exposure),
            "cash_required_usd": str(exposure + commission), "stop_price": str(price * (1 - stop)),
            "planned_stop_loss_usd": str(exposure * loss_fraction + 2 * commission),
            "risk_budget_usd": str(budget), "full_notional_gap_exposure_usd": str(exposure + commission),
            "modeled_round_trip_commission_usd": str(2 * commission), "reason": "SIZED" if units > 0 else "RISK_BUDGET_TOO_SMALL"}


def validate_quote(quote, at, policy, *, check_spread=True):
    at = moment(at)
    ask, bid = Decimal(str(quote["ask"])), Decimal(str(quote["bid"]))
    if not ask.is_finite() or not bid.is_finite() or not 0 < bid <= ask:
        return "INVALID_QUOTE"
    age = (at - moment(quote["asOf"])).total_seconds()
    if age < 0 or age > policy["quote_max_age_seconds"]:
        return "STALE_QUOTE"
    if check_spread and (ask - bid) / ((ask + bid) / 2) > Decimal(str(policy["max_spread_fraction"])):
        return "SPREAD_TOO_WIDE"
    return None


def decide(feature, *, policy, created_at, source_at=None, retrieved_at=None, reviewed_at=None,
           execution=None, cash=None, equity=None, open_positions=0):
    """No fill is ever inferred from a decision or a closing-market reference."""
    created = moment(created_at)
    out = {"created_at_utc": created.isoformat(), "protocol_id": policy["protocol_id"],
           "research_status": "UNVALIDATED", "real_trade_permission": False,
           "feature": feature, "filled_units": "0", "filled_exposure_usd": "0", "outcome": "NOT_DUE"}
    label = feature["classification"]
    if label != "RAISED":
        out.update(action="DATA_BLOCKED" if label in ("REVIEW_REQUIRED", "SOURCE_UNAVAILABLE") else "NO_SIGNAL",
                   reason=label)
        return out
    if not all((source_at, retrieved_at, reviewed_at)):
        raise ValueError("signal requires source, retrieval and review clocks")
    clocks = [moment(x) for x in (source_at, retrieved_at, reviewed_at)]
    if max(clocks) > created:
        raise ValueError("future information in decision")
    ready = max(clocks) + timedelta(minutes=policy["processing_delay_minutes"])
    schedule = session_schedule(max(ready, created).isoformat(), source_at, policy)
    out.update(information_available_at_utc=max(clocks).isoformat(), decision_ready_at_utc=ready.isoformat(),
               entry=schedule, exit={"stop_fraction": policy["stop_fraction"], "take_profit": None,
               "trailing_stop": False, "time_exit_at_utc": schedule["time_exit_at_utc"]},
               capital_assumption_usd=policy["capital_usd"],
               costs={k:policy[k] for k in ("commission_per_side_usd", "slippage_per_side_fraction", "extra_stress_per_side_fraction")})
    if not schedule["source_fresh"]:
        out.update(action="NO_SIGNAL", reason="STALE_DISCLOSURE")
        return out
    blockers = []
    if execution is None:
        blockers.append("BROKER_AND_QUOTE_UNVERIFIED")
    else:
        identity = execution.get("identity_verified") is True
        if not identity or execution.get("issuer_cik") != feature.get("issuer_cik"):
            blockers.append("SECURITY_IDENTITY_UNVERIFIED")
        if execution.get("underlying_stock_1x_verified") is not True:
            blockers.append("BROKER_PRODUCT_UNVERIFIED")
        if execution.get("stop_supported_verified") is not True:
            blockers.append("STOP_SUPPORT_UNVERIFIED")
        if execution.get("allow_open") is not True:
            blockers.append("BROKER_OPEN_UNAVAILABLE")
    # A complete wait decision can carry the exact missing conditions; it cannot be a fill.
    out.update(action="PAPER_WAIT", reason="AWAITING_ENTRY_WINDOW", blockers=blockers,
               next_action="At entry time obtain a fresh eligible broker bid/ask, verify protection and record a new append-only evaluation.",
               entry_price=None, stop_price=None,
               entry_price_rule="Observed ask * (1 + execution stress); fresh quote and spread gate required",
               expiry=schedule["entry_deadline_utc"])
    return out


def paper_fill(decision, execution, at, policy, *, cash, equity, open_positions=0):
    """Separate state transition. Does not submit any broker request."""
    now = moment(at)
    if decision.get("action") != "PAPER_WAIT" or decision.get("filled_units") != "0":
        raise ValueError("only an unfilled wait decision can fill")
    scheduled = moment(decision["entry"]["entry_at_utc"])
    if now < scheduled:
        raise ValueError("entry is not due")
    if now > moment(decision["entry"]["entry_deadline_utc"]):
        return {"action": "MISSED_ENTRY", "reason": "ENTRY_WINDOW_EXPIRED", "filled_units": "0"}
    expected = decision["feature"]["issuer_cik"]
    if execution.get("identity_verified") is not True or execution.get("issuer_cik") != expected or not isinstance(execution.get("instrument_id"),int):
        raise ValueError("security identity not verified")
    required = ("underlying_stock_1x_verified", "stop_supported_verified", "allow_open")
    if any(execution.get(k) is not True for k in required):
        return {"action": "EXECUTION_BLOCKED", "reason": "PRODUCT_OR_PROTECTION_UNVERIFIED", "filled_units": "0"}
    problem = validate_quote(execution["quote"], at, policy)
    if problem:
        return {"action": "EXECUTION_BLOCKED", "reason": problem, "filled_units": "0"}
    entry = Decimal(str(execution["quote"]["ask"])) * (1 + Decimal(str(policy["slippage_per_side_fraction"])))
    size = risk_size(entry, policy, cash=cash, equity=equity, open_positions=open_positions,
                     whole_units=execution.get("whole_units", False))
    if Decimal(size["units"]) <= 0:
        return {"action": "EXECUTION_BLOCKED", "reason": size["reason"], "filled_units": "0"}
    if execution.get("min_exposure_usd") is None or execution.get("max_units_per_order") is None:
        return {"action":"EXECUTION_BLOCKED","reason":"ORDER_LIMITS_UNVERIFIED","filled_units":"0"}
    if Decimal(size["notional_usd"]) < Decimal(str(execution["min_exposure_usd"])) or Decimal(size["units"]) > Decimal(str(execution["max_units_per_order"])):
        return {"action":"EXECUTION_BLOCKED","reason":"BROKER_ORDER_LIMIT","filled_units":"0"}
    return {"action": "PAPER_FILLED", "filled_at_utc": now.isoformat(), "size": size,
            "cash_after_usd": str(Decimal(str(cash)) - Decimal(size["cash_required_usd"])),
            "security":{"issuer_cik":expected,"instrument_id":execution["instrument_id"]},
            "quote": execution["quote"], "real_trade_permission": False}


def mark_position(fill, quote, at, policy, *, time_exit_at, corporate_action_clear):
    """Observed-quote valuation/exit, never an assumed intrabar stop fill.

    Caller retains every observation; gaps between observations are a monitoring gap.
    """
    if fill.get("action") != "PAPER_FILLED":
        raise ValueError("position has no observed paper fill")
    if moment(at) < moment(fill["filled_at_utc"]):
        raise ValueError("valuation before fill")
    if not corporate_action_clear:
        return {"action": "VALUATION_BLOCKED", "reason": "CORPORATE_ACTION_REVIEW_REQUIRED"}
    if quote.get("instrument_id") != fill["security"]["instrument_id"]:
        return {"action":"VALUATION_BLOCKED","reason":"QUOTE_SECURITY_MISMATCH"}
    # An adverse spread must not prevent recording a losing exit at the observed bid.
    problem = validate_quote(quote, at, policy, check_spread=False)
    if problem:
        return {"action": "VALUATION_BLOCKED", "reason": problem}
    size = fill["size"]
    units = Decimal(size["units"])
    bid = Decimal(str(quote["bid"]))
    mark_value = units * bid
    liquidation = mark_value * (1 - Decimal(str(policy["slippage_per_side_fraction"])))
    commission = Decimal(str(policy["commission_per_side_usd"]))
    entry_cost = Decimal(size["cash_required_usd"])
    net_proceeds = liquidation - commission
    pnl = net_proceeds - entry_cost
    stop = bid <= Decimal(size["stop_price"])
    due = moment(at) >= moment(time_exit_at)
    result = {"action": "PAPER_EXITED" if stop or due else "PAPER_MARK",
              "reason": "STOP_OBSERVED" if stop else "TIME_EXIT" if due else "HOLD",
              "at_utc": moment(at).isoformat(), "bid": str(bid),
              "marked_equity_usd": str(Decimal(fill["cash_after_usd"]) + mark_value),
              "modeled_net_liquidation_pnl_usd": str(pnl),
              "net_return_on_entry_cash_fraction": str(pnl / entry_cost),
              "realized": bool(stop or due), "monitoring_continuity_proven": False,
              "cost_stress_pnl_usd": str(pnl -
                  (Decimal(size["notional_usd"]) + liquidation) * Decimal(str(policy["extra_stress_per_side_fraction"])))}
    if stop or due:
        result.update(filled_exit_price=str(liquidation / units),
                      cash_after_usd=str(Decimal(fill["cash_after_usd"]) + net_proceeds))
    return result


def append_once(record, path):
    """Reuse KOD's chain, with exclusive single-writer lock and stable IDs."""
    import fcntl
    from .paper import append, ledger_lines, verify_chain
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if verify_chain(path):
            raise ValueError("existing ledger is corrupt")
        rows = ledger_lines(path)
        old = [r for r in rows if r.get("id") == record["id"]]
        if old:
            body = {k:v for k,v in old[0].items() if k not in ("record_hash", "prev_hash")}
            if canonical(body) != canonical(record):
                raise ValueError("record ID already exists with different content")
            return old[0]
        append([record], path=path)
        if verify_chain(path):
            raise ValueError("ledger read-back failed")
        return ledger_lines(path)[-1]

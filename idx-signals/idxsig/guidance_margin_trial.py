"""Prospective, supervised guidance comparison. Local paper records; no order API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from .guidance_margin_facts import _Review, _document
from .guidance_revision import canonical, digest, moment, session_schedule
from .paper import _canonical, _chain_problems
from .provenance import exclusive_lock, publish_bytes

SCHEMA = "guidance-margin-prospective/v1"
POLICY = {
    "capital_per_arm_usd": "10000",
    "slot_usd": "1000",
    "max_positions": 10,
    "entry_time_et": "09:30",
    "hold_sessions": 20,
    "max_source_to_entry_sessions": 6,
    "initial_disclosure_lookback_days": 7,
    "revenue_raise_pct": "1",
    "cost_per_side_fraction": "0.0025",
    "minimum_entry_price": "2",
    "descriptive_sessions": [1, 3, 5],
}


def _clock():
    return datetime.now(timezone.utc)


def records(path):
    """Read a complete atomic snapshot and reject damage rather than repair it."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("trial journal cannot be a symbolic link")
    raw = path.read_bytes() if path.exists() else b""
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    if (raw and not raw.endswith(b"\n")) or _chain_problems(rows):
        raise ValueError("trial journal is corrupt")
    if rows and rows[0].get("kind") != "START":
        raise ValueError("trial journal has no initialization")
    return rows


def _write(path, build):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("trial journal cannot be a symbolic link")
    with exclusive_lock(path):
        rows = records(path)
        now = _clock()
        if rows and now < moment(rows[-1]["recorded_at"]):
            raise ValueError("system clock precedes journal tail")
        body = build(rows, now)
        if "record_hash" in body:
            return body
        body = {
            **body,
            "recorded_at": now.isoformat(),
            "prev_hash": rows[-1]["record_hash"] if rows else None,
        }
        body["record_hash"] = hashlib.sha256(_canonical(body).encode()).hexdigest()
        serialized = b"".join((_canonical(row) + "\n").encode() for row in [*rows, body])
        publish_bytes(path, serialized, replace=bool(rows))
        if path.read_bytes() != serialized:
            raise ValueError("trial journal read-back differs")
        return body


def initialize(path):
    """Freeze this implementation's policy at the actual start time; idempotent."""

    def build(rows, now):
        if rows:
            if rows[0]["policy"] != POLICY:
                raise ValueError("existing trial policy differs")
            return rows[0]
        return {
            "kind": "START",
            "id": "start",
            "schema": SCHEMA,
            "policy": POLICY,
            "policy_sha256": digest(POLICY),
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "real_trade_permission": False,
            "execution_assumption": "Scheduled next-session daily open with fixed costs; modeled paper fills, not executable quotes",
        }

    return _write(path, build)


def qualify_prospective(pair):
    """Reuse source/token validators under an explicit prospective contract.

    This does not relabel the development contract or treat its fixtures as live.
    External review still establishes authenticity, semantics and latest prior.
    """
    if (
        not isinstance(pair, dict)
        or pair.get("schema_version") != SCHEMA
        or pair.get("purpose") != "prospective"
    ):
        raise ValueError("explicit prospective fact schema and purpose required")
    canonical(pair)
    review = _Review()
    review.text(pair, "event_id", "pair")
    current = _document(pair.get("current"), "current", review)
    prior = _document(pair.get("prior"), "prior", review)
    for key in ("identity", "basis", "definition", "perimeter", "periods"):
        if current[key] is not None and prior[key] is not None and current[key] != prior[key]:
            review.add("INCOMPARABLE", f"current/prior {key} differ")
    external = pair.get("external") or {}
    if not isinstance(external, dict):
        raise ValueError("external review must be an object")
    for key in ("attestor", "evidence_notes"):
        review.text(external, key, "external")
    for key in (
        "source_authenticity",
        "metric_binding",
        "prior_completeness",
        "basis_comparable",
        "perimeter_comparable",
    ):
        value = review.required(external, key, "external")
        if value is not None and value not in ("VERIFIED", "UNKNOWN", "FAILED"):
            raise ValueError("unknown external attestation")
        if value in ("UNKNOWN", "FAILED"):
            review.add("UNVERIFIED", f"external.{key}: {value}")
    latest = review.text(external, "latest_prior_source_id", "external")
    if latest is not None and prior["source_id"] is not None and latest != prior["source_id"]:
        review.add("INCOMPARABLE", "prior is not the reviewed latest prior")
    clocks = pair.get("clocks") or {}
    if not isinstance(clocks, dict):
        raise ValueError("clocks must be an object")
    extracted = review.clock(clocks, "extracted_at", "clocks")
    decision = review.clock(clocks, "decision_at", "clocks")
    if (
        prior["published"] is not None
        and current["published"] is not None
        and prior["published"] >= current["published"]
    ):
        raise ValueError("prior publication must precede current")
    for doc in (current, prior):
        if doc["received"] is not None and extracted is not None and doc["received"] > extracted:
            raise ValueError("extraction precedes receipt")
    if extracted is not None and decision is not None and extracted > decision:
        raise ValueError("decision precedes extraction")
    state = next(
        (s for s in ("INCOMPARABLE", "MISSING", "UNVERIFIED") if review.issues[s]), "FACTS_READY"
    )
    result = {
        "status": state,
        "reasons": [r for items in review.issues.values() for r in items],
        "derived": None,
    }
    if state == "FACTS_READY":
        result["derived"] = {
            "revenue_revision_pct": str(100 * (current["revenue"] / prior["revenue"] - 1)),
            "margin_revision_pp": str(current["margin"] - prior["margin"]),
        }
    return result


def _require_started(rows):
    if not rows:
        raise ValueError("initialize trial before admitting facts")
    return rows[0]["policy"]


def admit(path, fact_pair, *, ticker, reviewer):
    """Seal a reviewed event now, before its scheduled open and any outcome."""
    if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", ticker):
        raise ValueError("valid ticker required")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("named reviewer required")
    qualification = qualify_prospective(fact_pair)
    event_id = fact_pair["event_id"]
    input_hash = digest({"pair": fact_pair, "ticker": ticker, "reviewer": reviewer})

    def build(rows, now):
        policy = _require_started(rows)
        previous = [r for r in rows if r.get("kind") == "ADMISSION" and r["event_id"] == event_id]
        if previous:
            if previous[0]["input_sha256"] != input_hash:
                raise ValueError("event already sealed with different facts")
            return previous[0]
        start = moment(rows[0]["recorded_at"])
        reasons = list(qualification["reasons"])
        source = (fact_pair.get("current") or {}).get("source") or {}
        for key in ("published_at", "received_at"):
            if source.get(key) is not None:
                stamp = moment(source[key])
                if stamp > now:
                    raise ValueError("source clock is in the future")
                boundary = (
                    start - timedelta(days=policy["initial_disclosure_lookback_days"])
                    if key == "published_at"
                    else start
                )
                if stamp < boundary:
                    reasons.append(f"current {key} precedes allowed prospective window")
        for value in (fact_pair.get("clocks") or {}).values():
            if value is not None and moment(value) > now:
                raise ValueError("review clock is in the future")
            if value is not None and moment(value) < start:
                reasons.append("extraction or review precedes trial start")
        schedule = None
        if not reasons and qualification["status"] == "FACTS_READY":
            schedule = session_schedule(now.isoformat(), source["published_at"], policy)
            if not schedule["source_fresh"]:
                reasons.append("source too old for next-session admission")
        derived = qualification["derived"]
        revenue = bool(
            derived
            and Decimal(derived["revenue_revision_pct"]) >= Decimal(policy["revenue_raise_pct"])
        )
        margin = bool(revenue and Decimal(derived["margin_revision_pp"]) > 0)
        if not reasons and not revenue:
            reasons.append("revenue increase below 1 percent")
        active = [
            r
            for r in rows
            if r.get("kind") == "ADMISSION"
            and r["status"] == "ADMITTED"
            and not any(
                x.get("kind") in ("CLOSE", "MISSED_ENTRY") and x.get("event_id") == r["event_id"]
                for x in rows
            )
        ]
        if not reasons and len(active) >= policy["max_positions"]:
            reasons.append("all paired slots are occupied")
        if not reasons:
            for arm in ("revenue", "revenue_and_margin"):
                realized = sum(
                    (Decimal(r["pnl_usd"][arm]) for r in rows if r.get("kind") == "CLOSE"),
                    Decimal(0),
                )
                available = (
                    Decimal(policy["capital_per_arm_usd"])
                    + realized
                    - len(active) * Decimal(policy["slot_usd"])
                )
                if available < Decimal(policy["slot_usd"]):
                    reasons.append("insufficient shared paper cash for another paired slot")
                    break
        issuer = (fact_pair.get("current") or {}).get("issuer_cik")
        if not reasons and any(r["issuer_cik"].lstrip("0") == issuer.lstrip("0") for r in active):
            reasons.append("issuer already has an active paired slot")
        return {
            "kind": "ADMISSION",
            "id": "event:" + event_id,
            "event_id": event_id,
            "ticker": ticker,
            "issuer_cik": issuer,
            "reviewer": reviewer,
            "input_sha256": input_hash,
            "fact_pair": fact_pair,
            "qualification": qualification,
            "status": "EXCLUDED" if reasons else "ADMITTED",
            "reasons": reasons,
            "cohort": "INITIAL_RECENT"
            if source.get("published_at") and moment(source["published_at"]) < start
            else "NEW_RELEASE",
            "schedule": schedule,
            "arms": {"revenue": revenue, "revenue_and_margin": margin},
            "real_trade_permission": False,
        }

    return _write(path, build)


def _sessions(entry, end):
    import exchange_calendars as xc

    cal = xc.get_calendar("XNYS", start=entry, end=end)
    return cal, [day for day in cal.sessions if day.date().isoformat() >= entry]


def observe_bar(path, *, event_id, bar):
    """Retain a newly fetched completed daily bar; never admit at its old open.

    The admission must precede the scheduled opening. The first bar must be that
    exact session, and must arrive before the next session opens. Missing an entry
    is recorded rather than retrospectively selecting a later entry.
    """
    canonical(bar)

    def build(rows, now):
        policy = _require_started(rows)
        events = [r for r in rows if r.get("kind") == "ADMISSION" and r["event_id"] == event_id]
        if len(events) != 1 or events[0]["status"] != "ADMITTED":
            raise ValueError("event is not admitted")
        event = events[0]
        if bar.get("ticker") != event["ticker"] or str(bar.get("issuer_cik", "")).lstrip(
            "0"
        ) != event["issuer_cik"].lstrip("0"):
            raise ValueError("bar security identity differs")
        if not isinstance(bar.get("provider"), str) or not bar["provider"].strip():
            raise ValueError("bar provider required")
        fetched = moment(bar["fetched_at"])
        if (
            fetched > now
            or fetched < moment(event["recorded_at"])
            or now - fetched > timedelta(hours=1)
        ):
            raise ValueError("bar fetch must be current and after admission")
        session = bar["session"]
        entry_session = event["schedule"]["entry_session"]
        if session < entry_session:
            raise ValueError("bar precedes planned entry")
        cal, sessions = _sessions(entry_session, (now + timedelta(days=10)).date().isoformat())
        labels = [day.date().isoformat() for day in sessions]
        if session not in labels:
            raise ValueError("bar date is not a covered exchange session")
        day = sessions[labels.index(session)]
        closed = cal.session_close(day).to_pydatetime()
        if closed > fetched or closed > now:
            raise ValueError("daily bar is incomplete or from the future")
        completed = [
            d.date().isoformat()
            for d in sessions
            if cal.session_close(d).to_pydatetime() <= fetched
        ]
        if session != completed[-1]:
            raise ValueError("only the latest completed session may be observed; no backfill")
        prices = {key: Decimal(str(bar[key])) for key in ("open", "high", "low", "close", "volume")}
        if (
            not all(value.is_finite() and value > 0 for value in prices.values())
            or not prices["low"]
            <= min(prices["open"], prices["close"])
            <= max(prices["open"], prices["close"])
            <= prices["high"]
        ):
            raise ValueError("invalid OHLCV bar")
        if bar.get("corporate_action_clear") is not True:
            raise ValueError("corporate actions require review before valuation")
        previous = [
            r
            for r in rows
            if r.get("event_id") == event_id and r.get("kind") in ("BAR", "CLOSE", "MISSED_ENTRY")
        ]
        duplicate = [r for r in previous if r.get("session") == session]
        if duplicate:
            stable = {key: value for key, value in bar.items() if key != "fetched_at"}
            old = {
                key: value
                for key, value in duplicate[0].get("bar", {}).items()
                if key != "fetched_at"
            }
            if stable != old:
                raise ValueError("session already recorded with different bar")
            return duplicate[0]
        if any(r["kind"] in ("CLOSE", "MISSED_ENTRY") for r in previous):
            raise ValueError("paired slot is already closed")
        if previous and session <= previous[-1]["session"]:
            raise ValueError("cannot backfill an outcome after later outcomes")
        base = {
            "event_id": event_id,
            "id": f"bar:{event_id}:{session}",
            "session": session,
            "bar": bar,
        }
        if not previous:
            next_open = cal.session_open(sessions[1]).to_pydatetime()
            if session != entry_session or now >= next_open:
                return {
                    **base,
                    "kind": "MISSED_ENTRY",
                    "reason": "planned entry bar not captured before next open",
                }
            if prices["open"] < Decimal(policy["minimum_entry_price"]):
                return {**base, "kind": "MISSED_ENTRY", "reason": "entry price below minimum"}
            entry_open = prices["open"]
        else:
            entry_open = Decimal(previous[0]["entry_open"])
        elapsed = labels.index(session) + 1
        cost = Decimal(policy["cost_per_side_fraction"])
        budget = Decimal(policy["slot_usd"])
        units = budget / (entry_open * (1 + cost))
        net = units * prices["close"] * (1 - cost) - budget
        terminal = elapsed >= policy["hold_sessions"]
        expected_horizon = (
            elapsed in policy["descriptive_sessions"] or elapsed == policy["hold_sessions"]
        )
        return {
            **base,
            "kind": "CLOSE" if terminal else "BAR",
            "entry_open": str(entry_open),
            "modeled_entry_at": event["schedule"]["entry_at_utc"],
            "modeled_units": str(units),
            "held_sessions": elapsed,
            "descriptive_horizon": elapsed if expected_horizon else None,
            "missed_terminal_close": elapsed > policy["hold_sessions"],
            "pnl_usd": {
                "revenue": str(net),
                "revenue_and_margin": str(
                    net if event["arms"]["revenue_and_margin"] else Decimal(0)
                ),
            },
            "real_trade_permission": False,
        }

    return _write(path, build)


def status(path):
    rows = records(path)
    policy = _require_started(rows)
    admitted = [r for r in rows if r.get("kind") == "ADMISSION"]
    latest = {}
    horizons = {str(day): [] for day in [*policy["descriptive_sessions"], policy["hold_sessions"]]}
    for row in rows:
        if row.get("kind") in ("BAR", "CLOSE"):
            latest[row["event_id"]] = row
            if row["descriptive_horizon"] is not None:
                horizons[str(row["descriptive_horizon"])].append(row)

    def totals(observations):
        observations = list(observations)
        return {
            arm: str(sum((Decimal(row["pnl_usd"][arm]) for row in observations), Decimal(0)))
            for arm in ("revenue", "revenue_and_margin")
        }

    cohorts = {}
    for cohort in ("INITIAL_RECENT", "NEW_RELEASE"):
        cohort_events = {r["event_id"] for r in admitted if r["cohort"] == cohort}
        cohorts[cohort] = {
            "admitted": sum(r["status"] == "ADMITTED" and r["cohort"] == cohort for r in admitted),
            "filled_pairs": sum(key in cohort_events for key in latest),
            "horizons": {
                day: {
                    "paired_events": sum(r["event_id"] in cohort_events for r in group),
                    "net_pnl_usd": totals(r for r in group if r["event_id"] in cohort_events),
                }
                for day, group in horizons.items()
            },
        }
    return {
        "started_at": rows[0]["recorded_at"],
        "last_record_at": rows[-1]["recorded_at"],
        "status": "COLLECTING_REVIEWED_EVENTS",
        "candidates": len(admitted),
        "admitted": sum(r["status"] == "ADMITTED" for r in admitted),
        "excluded": sum(r["status"] == "EXCLUDED" for r in admitted),
        "filled_pairs": len(latest),
        "closed_pairs": sum(r["kind"] == "CLOSE" for r in latest.values()),
        "missing_terminal_outcomes": sum(
            r.get("missed_terminal_close", False) for r in latest.values()
        ),
        "missed_entries": sum(r["kind"] == "MISSED_ENTRY" for r in rows),
        "modeled_net_pnl_usd": totals(latest.values()),
        "horizons": {
            day: {"paired_events": len(group), "net_pnl_usd": totals(group)}
            for day, group in horizons.items()
        },
        "cohorts": cohorts,
        "conclusion": "Descriptive paper observations only; no edge verdict or real orders",
        "policy": policy,
        "real_trade_permission": False,
    }

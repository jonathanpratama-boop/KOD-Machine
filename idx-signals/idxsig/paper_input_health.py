"""Read-only US paper-input status; no forecast, plan, account or protocol changes.

Configuration is assessed only when an execution caller supplies a boolean. An
offline report's environment says nothing about the scheduled cloud job. All
times below describe retained records, not a new successful execution.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import calendar_us


def _time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def expected_session(now):
    """Conservative freshness bound: a session is due by the next regular open.

This uses the existing NYSE calendar, including its documented limitation for
one-off closures. It does not invent a nightly job completion timestamp.
"""
    day = now.astimezone(calendar_us.NEW_YORK).date()
    for _ in range(370):
        day -= timedelta(days=1)
        if calendar_us.is_session(day) and calendar_us.open_utc(calendar_us.next_session(day)) <= now:
            return day.isoformat()
    raise ValueError("cannot resolve expected US input session")


def sec_configured(environment):
    """Presence only, following sec_client's override priority. Never return values."""
    from .us_actions import DEFAULT_USER_AGENT

    override = environment.get("IDXSIG_SEC_USER_AGENT", "")
    if override:
        return bool(override.strip()) and override != DEFAULT_USER_AGENT
    return bool(environment.get("KOD_SEC_CONTACT", "").strip())


def unassessed():
    """Deterministic status for pure render calls without execution evidence."""
    return {"state": "NOT_ASSESSED", "reason": "Input health was not supplied to this rendering; current input flow is not established.",
            "assessed_at": "not assessed", "last_us_scan_session": None,
            "latest_forecast_at": None, "latest_forecast_session": None,
            "pending_forecast_count": "unavailable", "missed_forecast_count": "unavailable",
            "sec_contact_configured": None, "read_errors": []}


def summarize(*, scans, sets, forecasts, now, sec_contact_configured=None, read_errors=()):
    if now.tzinfo is None:
        raise ValueError("input-health clock must include a timezone")
    now = now.astimezone(timezone.utc)
    if sec_contact_configured is not None and type(sec_contact_configured) is not bool:
        raise ValueError("configuration evidence must be a boolean, never a contact value")
    compatible = [f for f in forecasts if f.get("type") == "LEARNER3_FORECAST"
                  and f.get("learner") == "LEARNER-v2.4" and f.get("market") == "US"
                  and f.get("family") == "SPEC_US"
                  and (f.get("protocol") or {}).get("id") == "KOD-LEARNER-v2.4"
                  and _time(f.get("made_at")) is not None and _time(f["made_at"]) <= now
                  and _time(f.get("entry_cutoff")) is not None
                  and _time(f["made_at"]) < _time(f["entry_cutoff"])]
    latest = max(compatible, key=lambda f: _time(f["made_at"]), default=None)
    us_sets = [s for s in sets if (s.get("type") == "SPECULATION_SET" and s.get("market") == "US"
               or s.get("type") == "CATALYST_SET" and s.get("family") == "SPEC_US")
               and (s.get("protocol") or {}).get("id") == "KOD-SPEC-REGISTER-v1.1"
               and s.get("signal_session", "") >= "2026-10-30"
               and _time(s.get("sealed_at")) is not None and _time(s["sealed_at"]) <= now]
    seen = {s["set_id"] for s in us_sets for f in compatible
            if s.get("set_id") == f.get("set_id") and s.get("record_hash")
            and f.get("set_record_hash") == s["record_hash"]
            and f.get("entry_cutoff") == s.get("entry_cutoff")}
    missing = [s for s in us_sets if s.get("set_id") not in seen]
    overdue = [s for s in missing if _time(s.get("entry_cutoff")) is not None
               and _time(s["entry_cutoff"]) <= now]
    pending = [s for s in missing if _time(s.get("entry_cutoff")) is not None
               and _time(s["entry_cutoff"]) > now]
    us_scans = [s for s in scans if s.get("type") == "SCAN" and s.get("market") == "US"
                and s.get("session") and _time(s.get("discovered_at")) is not None
                and _time(s["discovered_at"]) <= now]
    scan = max(us_scans, key=lambda s: (s["session"], _time(s["discovered_at"])), default=None)
    required = expected_session(now)
    last_session = scan["session"] if scan else None
    current_sets = [s for s in us_sets if s.get("signal_session") == last_session]
    current_missing = [s for s in missing if s.get("signal_session") == last_session]
    current_overdue = [s for s in overdue if s.get("signal_session") == last_session]
    current_bad_cutoffs = [s for s in current_missing if _time(s.get("entry_cutoff")) is None]
    candidate_names = set(scan.get("candidates_ranked", [])) if scan else set()
    missing_register = candidate_names - {s.get("ticker") for s in current_sets}
    if sec_contact_configured is False:
        state, reason = "BLOCKED_CONFIGURATION", "US forecast execution is blocked: KOD_SEC_CONTACT is not configured in this execution context."
    elif read_errors:
        state, reason = "UNAVAILABLE", "One or more input ledgers could not be read; coverage is unavailable."
    elif scan is None:
        state, reason = "UNAVAILABLE", "No dated US scan is available; current US input coverage cannot be established."
    elif last_session < required:
        state, reason = "STALE_INPUT", f"US scan input is stale: latest session {last_session}; expected at least {required}."
    elif current_bad_cutoffs:
        state, reason = "UNAVAILABLE", "An eligible US set has an invalid or missing entry cutoff; its timing status is unavailable."
    elif current_sets and missing_register:
        state, reason = "PARTIAL_INPUT", f"{len(missing_register)} latest-scan candidate(s) lack compatible eligible-set evidence; the register is incomplete."
    elif current_overdue:
        state, reason = "STALE_INPUT", f"{len(current_overdue)} eligible US set(s) from the latest scan passed their cutoff without a compatible v2.4 forecast."
    elif current_missing:
        state, reason = "WAITING_FORECAST", f"{len(current_missing)} eligible US set(s) still await a compatible v2.4 forecast before their cutoff."
    elif scan.get("data", {}).get("not_scanned", 0) > 0:
        state, reason = "PARTIAL_INPUT", "The latest US scan has unscanned names; full input coverage cannot be claimed."
    elif not current_sets and scan.get("result") == "NO SIGNAL" and scan.get("candidates_ranked") == []:
        state, reason = "CURRENT_NO_OPPORTUNITY", "The latest recorded US scan found no qualifying candidates; no new forecast or paper plan is expected from that scan."
    elif not current_sets:
        state, reason = "NO_FORECAST", "The latest US scan has no compatible eligible-set/forecast evidence; this is not proof of no opportunity."
    else:
        state, reason = "CURRENT", "Every eligible US set recorded for the latest scan has a compatible v2.4 forecast. This does not certify planner/account execution."
    return {
        "state": state, "reason": reason, "assessed_at": now.isoformat().replace("+00:00", "Z"),
        "expected_scan_session": required, "last_us_scan_session": last_session,
        "last_us_scan_received_at": scan.get("discovered_at") if scan else None,
        "latest_forecast_at": latest.get("made_at") if latest else None,
        "latest_forecast_session": latest.get("signal_session") if latest else None,
        "forecast_age_days": (now - _time(latest["made_at"])).total_seconds() / 86400 if latest else None,
        "compatible_forecast_count": len(compatible), "pending_forecast_count": len(pending),
        "missed_forecast_count": len(overdue), "current_missing_count": len(current_missing),
        "candidates_without_eligible_set_count": len(missing_register),
        "sec_contact_configured": sec_contact_configured,
        "read_errors": list(read_errors),
    }


def load(*, now=None, sec_contact_configured=None):
    """Read local retained ledgers only. No environment values, requests or writes."""
    from . import learner3, paper, speculation

    errors = []

    def read(path):
        if not path.exists():
            errors.append(path.name + ": missing")
            return []
        try:
            return paper.ledger_lines(path)
        except (OSError, ValueError, TypeError, KeyError):
            errors.append(path.name + ": unreadable")
            return []

    scans = read(paper.LEDGER)
    sets = read(speculation.SPEC_LEDGER)
    forecasts = read(learner3.LEDGER)
    return summarize(scans=scans, sets=sets, forecasts=forecasts,
                     now=now or datetime.now(timezone.utc),
                     sec_contact_configured=sec_contact_configured, read_errors=errors)


def banner(status):
    latest = status["latest_forecast_at"] or "none recorded"
    session = status["latest_forecast_session"] or "none"
    scan = status["last_us_scan_session"] or "unavailable"
    out = ["## US forecast input health", "", f"**{status['state']} — {status['reason']}**", "",
           f"- Assessed {status['assessed_at']}; latest US scan session: {scan}.",
           f"- Latest compatible LEARNER v2.4 forecast: {latest} (signal session {session}).",
           f"- Eligible sets awaiting forecasts: {status['pending_forecast_count']}; "
           f"historical sets missed before cutoff: {status['missed_forecast_count']}.",
           "- Existing plan and account totals below are historical records, not proof that new input is flowing."]
    if status["sec_contact_configured"] is None:
        out.append("- SEC configuration was not assessed by this offline report; check the environment running the US forecast job.")
    elif status["sec_contact_configured"] is True:
        out.append("- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.")
    if status["read_errors"]:
        out.append("- Input read status: " + "; ".join(status["read_errors"]) + ".")
    return "\n".join(out) + "\n\n"


def add_banner(report, status):
    title, remainder = report.split("\n", 1)
    return title + "\n\n" + banner(status) + remainder.lstrip("\n")

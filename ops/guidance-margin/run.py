#!/usr/bin/env python3
"""One unattended paper-research cycle. No broker or real-order interface."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "idx-signals"))
from idxsig import guidance_margin_trial as trial  # noqa: E402
from idxsig.provenance import publish_bytes  # noqa: E402


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    publish_bytes(
        Path(path),
        (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode(),
        replace=Path(path).exists(),
    )


def latest_closed_session(now):
    import exchange_calendars as xc

    cal = xc.get_calendar(
        "XNYS",
        start=(now - timedelta(days=15)).date().isoformat(),
        end=(now + timedelta(days=2)).date().isoformat(),
    )
    completed = [day for day in cal.sessions if cal.session_close(day).to_pydatetime() <= now]
    if (
        not completed
        or cal.session_close(completed[-1]).to_pydatetime() + timedelta(minutes=20) > now
    ):
        return None
    return completed[-1].date().isoformat()


def fetch_bar(state, event, session):
    """Retain the provider response before parsing a daily modeled-paper mark."""
    ticker = event["ticker"]
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(ticker, safe="")
        + "?range=6mo&interval=1d&events=div%2Csplits"
    )
    started = stamp()
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 KOD-paper-research"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError("price response is unexpectedly large")
    fetched = stamp()
    digest = hashlib.sha256(raw).hexdigest()
    folder = state / "prices" / ticker
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (fetched.replace(":", "-") + ".json")
    publish_bytes(target, raw)
    data = json.loads(raw)
    if data.get("chart", {}).get("error"):
        raise ValueError("price provider returned an error")
    result = data["chart"]["result"][0]
    if result["meta"].get("symbol", "").upper().replace("-", ".") != ticker.upper().replace(
        "-", "."
    ):
        raise ValueError("price provider symbol differs")
    if result["meta"].get("currency") != "USD":
        raise ValueError("only USD paper instruments are supported")
    if (
        result["meta"].get("instrumentType") != "EQUITY"
        or result["meta"].get("exchangeTimezoneName") != "America/New_York"
    ):
        raise ValueError("only identified US-session equities are supported")
    ny = ZoneInfo("America/New_York")
    sessions = [
        datetime.fromtimestamp(t, timezone.utc).astimezone(ny).date().isoformat()
        for t in result["timestamp"]
    ]
    if sessions.count(session) != 1:
        raise ValueError("planned daily price is unavailable or duplicated")
    index = sessions.index(session)
    quote = result["indicators"]["quote"][0]
    actions = []
    for kind, values in result.get("events", {}).items():
        for action in values.values():
            day = (
                datetime.fromtimestamp(action["date"], timezone.utc)
                .astimezone(ny)
                .date()
                .isoformat()
            )
            if event["schedule"]["entry_session"] <= day <= session:
                actions.append({"type": kind, "session": day, "details": action})
    return {
        "session": session,
        **{field: quote[field][index] for field in ("open", "high", "low", "close", "volume")},
        "ticker": ticker,
        "issuer_cik": event["issuer_cik"],
        "provider": "Yahoo daily chart; unadjusted OHLC; modeled fills",
        "fetched_at": fetched,
        "request_started_at": started,
        "source_url": url,
        "source_sha256": digest,
        "corporate_action_clear": not actions,
        "reported_corporate_actions": actions,
        "corporate_action_scope": "No split or dividend reported by this provider between entry and mark; not an independent corporate-action audit",
    }


def update_prices(state, journal):
    rows = trial.records(journal)
    closed = latest_closed_session(datetime.now(timezone.utc))
    if closed is None:
        return []
    errors = []
    for event in rows:
        if event.get("kind") != "ADMISSION" or event["status"] != "ADMITTED":
            continue
        event_rows = [r for r in rows if r.get("event_id") == event["event_id"]]
        if any(r["kind"] in ("CLOSE", "MISSED_ENTRY") for r in event_rows):
            continue
        if closed < event["schedule"]["entry_session"] or any(
            r.get("session") == closed for r in event_rows
        ):
            continue
        try:
            bar = fetch_bar(state, event, closed)
            trial.observe_bar(journal, event_id=event["event_id"], bar=bar)
        except Exception as exc:
            errors.append(
                {
                    "event_id": event["event_id"],
                    "session": closed,
                    "reason": f"{type(exc).__name__}: {exc}"[:350],
                }
            )
    return errors


def import_reviews(state, journal):
    errors = []
    known = {
        row.get("event_id") for row in trial.records(journal) if row.get("kind") == "ADMISSION"
    }
    for path in sorted((state / "approved").glob("*.json")):
        try:
            packet = json.loads(path.read_text())
            if packet["fact_pair"]["event_id"] in known:
                continue
            trial.admit(
                journal, packet["fact_pair"], ticker=packet["ticker"], reviewer=packet["reviewer"]
            )
        except Exception as exc:
            errors.append({"file": path.name, "reason": f"{type(exc).__name__}: {exc}"[:350]})
    return errors


def cycle(state, cik_map, *, skip_feed=False):
    state.mkdir(parents=True, exist_ok=True)
    journal = state / "trial.jsonl"
    launch = trial.initialize(journal)
    feed = {}
    errors = []
    if not skip_feed:
        try:
            from idxsig import guidance_margin_feed

            guidance_margin_feed.initialize(
                state, cik_map, started_at=launch["recorded_at"], budget=55.0, prior_spend=0.47
            )
            feed = guidance_margin_feed.cycle(state, live=True)
        except Exception as exc:
            # Never include HTTP request headers or environment in this record.
            errors.append({"stage": "feed", "reason": f"{type(exc).__name__}: {exc}"[:350]})
    if not feed:
        feed_path = state / "FEED_STATUS.json"
        if feed_path.exists():
            feed = json.loads(feed_path.read_text())
    errors.extend(update_prices(state, journal))
    errors.extend(import_reviews(state, journal))
    result = {
        "schema": "guidance-margin-status/v1",
        "as_of": stamp(),
        "state": "NEEDS_ATTENTION" if errors or feed.get("state") == "DEGRADED" else "RUNNING",
        "trial": trial.status(journal),
        "feed": feed,
        "errors": errors,
        "real_trade_permission": False,
        "notes": "Early 1/3/5-session observations are descriptive. The primary hold is 20 exchange sessions. Model review and daily-bar execution can be wrong; there is no proven trading edge.",
    }
    save(state / "STATUS.json", result)
    print(
        json.dumps(
            {
                "state": result["state"],
                "as_of": result["as_of"],
                "candidates": result["trial"]["candidates"],
                "admitted": result["trial"]["admitted"],
                "errors": errors,
            }
        )
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--cik-map", type=Path, required=True)
    parser.add_argument("--skip-feed", action="store_true")
    parser.add_argument("--initialize-only", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    args.state.mkdir(parents=True, exist_ok=True)
    with (args.state / "cycle.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.initialize_only:
            row = trial.initialize(args.state / "trial.jsonl")
            print(
                json.dumps(
                    {"started_at": row["recorded_at"], "policy_sha256": row["policy_sha256"]}
                )
            )
        else:
            cycle(args.state, args.cik_map, skip_feed=args.skip_feed)


if __name__ == "__main__":
    main()

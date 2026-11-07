#!/usr/bin/env python3
"""Export recorded R2 outcomes using a read-only, consistent SQLite snapshot.

Only COMPLETE 24-hour endpoints count as results. Returns use the engine's
recorded midpoint-minus-two-percentage-point model; they are not real fills.
No engine code is imported and no research state is changed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sqlite3
import statistics

UTC = dt.timezone.utc
ARMS = (1, 5, 30, 240)


def iso(value):
    return dt.datetime.fromtimestamp(value, UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def stamp(value):
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return float(value)
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def mean(values):
    return statistics.mean(values) if values else None


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def comparison_readiness(db, symbols, watermark):
    """Match ResearchEngine._features() at the committed receipt watermark."""
    last = math.floor(watermark / 3600) * 3600 - 3600
    day = math.floor(watermark / 86400) * 86400
    eligible = 0
    for symbol in symbols:
        hours = {r["opened"]: r["close"] for r in db.execute(
            "SELECT opened,close FROM hours WHERE symbol=? AND opened IN (?,?) AND available<=?",
            (symbol, last, last - 24 * 3600, watermark),
        )}
        daily = db.execute(
            "SELECT volume FROM daily WHERE symbol=? AND opened>=? AND opened<? AND available<=?",
            (symbol, day - 30 * 86400, day, watermark),
        ).fetchall()
        momentum = (hours[last] / hours[last - 24 * 3600] - 1
                    if last in hours and last - 24 * 3600 in hours else None)
        median = statistics.median(r[0] for r in daily) if len(daily) == 30 else None
        if number(momentum) is not None and number(median) is not None:
            eligible += 1
    status = "READY" if eligible == len(symbols) and eligible >= 2 else "PARTIAL" if eligible >= 2 else "UNAVAILABLE"
    return {"status": status, "as_of": iso(watermark),
            "eligible_symbols": eligible, "total_symbols": len(symbols)}


def export_results(state):
    state = Path(state)
    config = read_json(state / "research.json")
    heartbeat = read_json(state / "RESEARCH_ENGINE_HEALTH.json", {})
    capture = read_json(state / "RESEARCH_CAPTURE_HEARTBEAT.json", {})
    collector = read_json(state / "HEALTH.json", {}).get("collector", {})
    db_path = state / "engine" / "research.sqlite"
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        watermark_row = db.execute("SELECT value FROM meta WHERE key='watermark'").fetchone()
        watermark = float(json.loads(watermark_row[0]))
        snapshot_at = dt.datetime.now(UTC).timestamp()
        events = [dict(r) for r in db.execute("SELECT * FROM events ORDER BY reference,id")]
        positions = [dict(r) for r in db.execute("SELECT * FROM positions ORDER BY event_id,arm,role,symbol")]
        endpoints = {r["position_id"]: dict(r) for r in db.execute("SELECT * FROM endpoints WHERE horizon=24")}
        readiness = comparison_readiness(db, [r["symbol"] for r in config["primary"]], watermark)
    finally:
        db.close()

    by_key = {(p["event_id"], p["arm"], p["role"], p["symbol"]): p for p in positions}
    output_events = []
    stats = {arm: {"minutes": arm, "event_entries": 0, "completed_24h": 0,
                   "censored_24h": 0, "awaiting_24h": 0, "net": [], "benchmark": [], "control": []}
             for arm in ARMS}
    due = []
    completed_event_ids = set()
    unavailable_controls = 0

    def recorded_returns(position):
        endpoint = endpoints.get(position["id"]) if position else None
        if not endpoint or endpoint["status"] != "COMPLETE":
            return None
        payload = json.loads(endpoint["payload"])
        return payload["returns"]

    for event in events:
        payload = json.loads(event["payload"])
        controls = payload.get("controls", [])
        if not controls or payload.get("controls_status") != "AVAILABLE":
            unavailable_controls += 1
        event_out = {"event_id": event["id"], "symbol": event["symbol"],
                     "reference_at": iso(event["reference"]),
                     "controls_status": payload.get("controls_status", "UNKNOWN"),
                     "primary_deadline_at": iso(event["reference"] + 24 * 3600), "arms": []}
        for arm in ARMS:
            item = stats[arm]
            p = by_key.get((event["id"], arm, "EVENT", event["symbol"]))
            endpoint = endpoints.get(p["id"]) if p else None
            primary_status = endpoint["status"] if endpoint else p["status"] if p else "NO_ENTRY_RECORDED"
            entry = json.loads(p["entry"]) if p and p["entry"] else None
            if p and p["status"] == "ENTERED":
                item["event_entries"] += 1
            if primary_status == "AWAIT_EXIT":
                item["awaiting_24h"] += 1
                due.append(endpoint["deadline"])
            elif primary_status == "CENSORED":
                item["censored_24h"] += 1
            result = recorded_returns(p)
            net = benchmark = control_excess = None
            if result is not None:
                item["completed_24h"] += 1
                completed_event_ids.add(event["id"])
                net = number(result.get("modeled_net_token_return"))
                benchmark = number(result.get("net_excess"))
                if net is not None:
                    item["net"].append(net)
                if benchmark is not None:
                    item["benchmark"].append(benchmark)
                control_nets = []
                for control in controls:
                    c = by_key.get((event["id"], arm, "CONTROL", control["symbol"]))
                    c_result = recorded_returns(c)
                    c_net = number(c_result.get("modeled_net_token_return")) if c_result else None
                    if c_net is not None:
                        control_nets.append(c_net)
                if net is not None and controls and len(control_nets) == len(controls):
                    control_excess = net - statistics.mean(control_nets)
                    item["control"].append(control_excess)
            event_out["arms"].append({"minutes": arm,
                "entry_at": entry.get("received_at") if entry else None,
                "primary_status": primary_status, "net_return": net,
                "benchmark_excess": benchmark, "control_excess": control_excess})
        output_events.append(event_out)

    output_arms = []
    for arm in ARMS:
        item = stats[arm]
        net, benchmark, controls = item.pop("net"), item.pop("benchmark"), item.pop("control")
        item.update(mean_net_return=mean(net), median_net_return=statistics.median(net) if net else None,
                    mean_benchmark_excess=mean(benchmark) if len(benchmark) == item["completed_24h"] else None,
                    mean_control_excess=mean(controls), completed_control_pairs=len(controls))
        output_arms.append(item)
    health_at = heartbeat.get("epoch")
    if health_at is None and heartbeat.get("as_of"):
        health_at = stamp(heartbeat["as_of"])
    status = heartbeat.get("status", "UNKNOWN")
    if health_at is None or snapshot_at - health_at > 120 or health_at - snapshot_at > 5:
        status = "STALE" if health_at is not None else "UNKNOWN"
    if capture.get("phase") in {"PROVIDER_STOPPED", "PAUSED", "FAILED"}:
        status = capture["phase"]
    return {"schema": "KOD_R2_RESULTS_V1", "as_of": iso(snapshot_at),
        "study_id": config["study_id"], "status": status,
        "independent_events": len(events), "events_with_completed_24h": len(completed_event_ids),
        "events_without_controls": unavailable_controls, "comparison_inputs": readiness,
        "coverage": {"on_time_fraction": number(collector.get("coverage", {}).get("pooled_on_time_coverage"))},
        "next_primary_due_at": iso(min(due)) if due else None,
        "arms": output_arms, "events": output_events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = export_results(args.state)
    encoded = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_name(args.out.name + ".tmp")
    temporary.write_text(encoded)
    temporary.replace(args.out)
    print(json.dumps({"out": str(args.out), "as_of": result["as_of"],
                      "events": result["independent_events"], "completed_24h": result["events_with_completed_24h"]}))


if __name__ == "__main__":
    main()

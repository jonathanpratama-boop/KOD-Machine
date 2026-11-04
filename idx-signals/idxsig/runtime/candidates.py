"""Versioned analyst assessments for retained detections; never an order adapter.

Assessment evidence is an analyst declaration, not provider verification. The
detector record and earlier assessments remain intact. Entry eligibility cannot
be granted by this research-only workflow.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path

from .data import parse_time, utc_text
from .storage import canonical, digest, locked, read_snapshot, write_snapshot

SCHEMA = "KOD_CANDIDATE_ASSESSMENT_V1"
STATES = {"DETECTED", "RESEARCHED", "CONDITIONAL_READY", "ENTRY_ELIGIBLE", "REJECTED", "EXPIRED"}
CHANGES = {"NEW_EVENT", "PRICE_OR_CONDITION_CHANGE", "CORRECTED_INPUT",
           "NEWLY_FOUND_OLD_INFORMATION", "CHANGED_INFERENCE"}
TRANSITIONS = {
    "DETECTED": {"DETECTED", "RESEARCHED", "REJECTED", "EXPIRED"},
    "RESEARCHED": {"RESEARCHED", "CONDITIONAL_READY", "REJECTED", "EXPIRED"},
    "CONDITIONAL_READY": {"CONDITIONAL_READY", "RESEARCHED", "REJECTED", "EXPIRED"},
    "REJECTED": {"REJECTED", "RESEARCHED"},
    "EXPIRED": {"EXPIRED"},
}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} requires nonempty text")
    return value.strip()


def _strings(value, name):
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [_text(x, name) for x in value]


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate assessment JSON key")
        out[key] = value
    return out


def _conditional_plan(plan, evidence_ids):
    """Check complete declared prerequisites; their truth remains analyst-attested."""
    if not isinstance(plan, dict) or plan.get("side") != "LONG":
        raise ValueError("conditional plan requires explicit LONG side")
    required = ("entry_lower", "entry_upper", "protective_price", "loss_budget",
                "ordinary_loss", "stress_loss", "gap_loss", "round_trip_cost_fraction")
    numbers = {}
    for key in required:
        try:
            value = Decimal(str(plan[key]))
        except (KeyError, InvalidOperation, ValueError):
            raise ValueError("conditional plan requires finite " + key) from None
        if not value.is_finite() or value < 0:
            raise ValueError("invalid conditional plan " + key)
        numbers[key] = value
    low, high, protection = (numbers[k] for k in ("entry_lower", "entry_upper", "protective_price"))
    if not 0 < protection < low <= high or (high - protection) / high > Decimal("0.05"):
        raise ValueError("conditional entry bounds require structural protection within 5% at upper bound")
    if numbers["loss_budget"] <= 0 or numbers["ordinary_loss"] > numbers["loss_budget"]:
        raise ValueError("ordinary loss must fit a positive confirmed budget")
    if not numbers["ordinary_loss"] <= numbers["stress_loss"] <= numbers["gap_loss"]:
        raise ValueError("stress and gap loss assumptions must not understate ordinary loss")
    if numbers["round_trip_cost_fraction"] >= 1:
        raise ValueError("invalid cost assumption")
    for key in ("trigger", "invalidation", "protection_basis", "target_action", "cancellation", "horizon"):
        _text(plan.get(key), "plan." + key)
    checks = plan.get("essential_evidence")
    names = {"identity", "broker_product_access", "risk_budget", "economics", "structural_protection",
             "depth_spread_costs", "broker_orders", "monitoring", "cash_alternatives"}
    if not isinstance(checks, dict) or set(checks) != names or any(v not in evidence_ids for v in checks.values()):
        raise ValueError("every essential prerequisite needs a retained evidence id")
    waiting = plan.get("pending_conditions")
    if not isinstance(waiting, list) or not waiting:
        raise ValueError("conditional readiness needs a named future event, quote or trigger")
    for item in waiting:
        if not isinstance(item, dict) or item.get("kind") not in {"FUTURE_RESULT", "QUOTE", "TRIGGER"}:
            raise ValueError("only future results, quotes and triggers may remain unresolved")
        _text(item.get("condition"), "pending condition")


def assessments(root):
    """Read the entire verified journal. Missing journal means no assessments."""
    path = Path(root) / "candidate_assessments.jsonl"
    if not path.exists():
        return []
    if path.is_symlink():
        raise ValueError("assessment journal must not be a symlink")
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("torn assessment journal; restore verified backup")
    rows, previous, latest, ids = [], None, {}, set()
    for line in raw.splitlines():
        row = json.loads(line, object_pairs_hook=_pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite assessment JSON")))
        if not isinstance(row, dict):
            raise ValueError("invalid assessment journal record")
        body = {k: v for k, v in row.items() if k != "record_hash"}
        if row.get("schema_version") != SCHEMA or row.get("sequence") != len(rows) + 1 or row.get("prev_hash") != previous or digest(body) != row.get("record_hash"):
            raise ValueError("assessment journal integrity failure")
        identifier = row["candidate_id"]
        prior = latest.get(identifier)
        if row.get("version") != (prior["version"] + 1 if prior else 1) or row.get("supersedes") != (prior["id"] if prior else None):
            raise ValueError("assessment version chain failure")
        if row["id"] in ids:
            raise ValueError("duplicate assessment identity")
        ids.add(row["id"])
        latest[identifier], previous = row, row["record_hash"]
        rows.append(row)
    return rows


def verify_assessments(root):
    rows = assessments(root)
    return {"ok": True, "assessments": len(rows),
            "head_hash": rows[-1]["record_hash"] if rows else None,
            "entry_permission": False}


def _normalize(value):
    if not isinstance(value, dict):
        raise ValueError("assessment must be an object")
    allowed = {"candidate_id", "state", "as_of", "owner", "reason", "mechanism", "counterarguments",
               "evidence", "blockers", "clearing_evidence", "expires_at", "recheck_at", "plan",
               "supersedes", "change_kind", "strategy_id"}
    if set(value) - allowed:
        raise ValueError("unknown assessment fields: " + ", ".join(sorted(set(value) - allowed)))
    out = copy.deepcopy(value)
    for key in ("candidate_id", "owner", "reason", "state"):
        out[key] = _text(out.get(key), key)
    if out["state"] not in STATES:
        raise ValueError("unknown candidate state")
    if out["state"] == "ENTRY_ELIGIBLE":
        raise ValueError("no approved selective-repricing entry policy; assessment cannot grant entry eligibility")
    cutoff = parse_time(out.get("as_of"), "assessment.as_of")
    out["as_of"] = utc_text(cutoff)
    out["strategy_id"] = out.get("strategy_id", "SELECTIVE_REPRICING")
    if out["strategy_id"] != "SELECTIVE_REPRICING":
        raise ValueError("candidate assessments belong to SELECTIVE_REPRICING research")
    for name in ("counterarguments", "blockers", "clearing_evidence"):
        out[name] = _strings(out.get(name, []), name)
    out["mechanism"] = _text(out.get("mechanism", "UNKNOWN"), "mechanism")
    evidence = out.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")
    seen = set()
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"id", "source", "available_at", "observed_at", "statement"}:
            raise ValueError("evidence requires id, source, available_at, observed_at and statement")
        for key in ("id", "source", "statement"):
            item[key] = _text(item[key], "evidence." + key)
        if item["id"] in seen:
            raise ValueError("duplicate evidence id")
        seen.add(item["id"])
        available = parse_time(item["available_at"])
        observed = parse_time(item["observed_at"])
        if not available <= observed <= cutoff:
            raise ValueError("evidence is unavailable or observed after assessment cutoff")
        item["available_at"], item["observed_at"] = utc_text(available), utc_text(observed)
    out["evidence"] = evidence
    if out["state"] in {"RESEARCHED", "CONDITIONAL_READY"} and (not evidence or not out["counterarguments"]):
        raise ValueError("research requires evidence and a competing explanation")
    out["expires_at"] = out.get("expires_at")
    if out["expires_at"] is not None:
        expiry = parse_time(out["expires_at"])
        out["expires_at"] = utc_text(expiry)
        if out["state"] not in {"EXPIRED", "REJECTED"} and expiry <= cutoff:
            raise ValueError("active assessment requires a future exact expiry")
        if out["state"] == "EXPIRED" and expiry > cutoff:
            raise ValueError("cannot expire an assessment before its deadline")
    elif out["state"] in {"RESEARCHED", "CONDITIONAL_READY", "EXPIRED"}:
        raise ValueError("this state requires an exact expires_at")
    out["recheck_at"] = out.get("recheck_at")
    if out["recheck_at"] is not None:
        recheck = parse_time(out["recheck_at"])
        if recheck <= cutoff or (out["expires_at"] and recheck > parse_time(out["expires_at"])):
            raise ValueError("recheck must be after cutoff and no later than expiry")
        out["recheck_at"] = utc_text(recheck)
    out["plan"] = out.get("plan")
    if out["plan"] is not None and not isinstance(out["plan"], dict):
        raise ValueError("plan must be an object or null")
    if out["state"] == "CONDITIONAL_READY":
        if out["blockers"] or out["mechanism"] == "UNKNOWN":
            raise ValueError("essential unknowns require RESEARCHED with blockers")
        _conditional_plan(out["plan"], seen)
    out["supersedes"] = out.get("supersedes")
    out["change_kind"] = out.get("change_kind", "CHANGED_INFERENCE")
    if out["change_kind"] not in CHANGES:
        raise ValueError("unknown assessment change_kind")
    canonical(out)  # Refuse nonfinite plan values before touching the journal.
    return out


def project(root, candidate_rows, as_of):
    """Overlay assessments by analytical cutoff, preserving original records.

    ``as_of`` selects the market/evidence cutoff used in an assessment. Its
    actual recording time is the separate ``recorded_at`` field; this view is
    not a reconstruction of which assessments existed at a historical time.
    """
    cutoff = parse_time(as_of)
    latest = {}
    for row in assessments(root):
        if parse_time(row["as_of"]) <= cutoff:
            latest[row["candidate_id"]] = row
    out = []
    for raw in candidate_rows:
        # A later cutoff may carry an already projected row. Always rebuild from
        # its preserved detection so projecting an earlier cutoff cannot retain
        # later analyst fields or an expired-state projection.
        item = copy.deepcopy(raw.get("detector_record", raw))
        identifier = item.get("id", item.get("candidate_id"))
        record = latest.get(identifier)
        if record:
            item["detector_record"] = copy.deepcopy(item)
            item.setdefault("detector_state", item.get("state", "DETECTED"))
            item["state"] = record["state"]
            item["assessment"] = copy.deepcopy(record)
            item["assessment_id"] = record["id"]
            item["assessment_version"] = record["version"]
            for key in ("owner", "mechanism", "counterarguments", "blockers", "clearing_evidence", "expires_at", "recheck_at", "plan"):
                item[key] = copy.deepcopy(record[key])
            item["assessment_reason"] = record["reason"]
            expiry = record.get("expires_at")
            if expiry and cutoff >= parse_time(expiry) and item["state"] not in {"REJECTED", "EXPIRED"}:
                item["state"] = "EXPIRED"
                item["expiry_projection"] = {"expires_at": expiry, "evaluated_at": utc_text(cutoff),
                                             "original_assessment_state": record["state"]}
        item["entry_permission"] = False
        out.append(item)
    return out


def record_assessment(root, assessment):
    """Append one revision for a retained candidate and refresh its read-only view.

Retrying the same normalized request returns the first record unchanged. A
revision names its preceding assessment ID in ``supersedes``. Snapshot cutoff
must cover all assessment evidence; run a new explicit cycle for newer evidence.
    """
    request = _normalize(assessment)
    request_hash = digest(request)
    root = Path(root)
    with locked(root):
        if (root / "pending.json").exists():
            raise ValueError("finish the pending runtime cycle before assessing a candidate")
        snapshot = read_snapshot(root)
        payload = snapshot["payload"]
        cutoff = parse_time(payload["run"]["as_of"])
        if parse_time(request["as_of"]) > cutoff or parse_time(request["as_of"]) > datetime.now(timezone.utc):
            raise ValueError("assessment cutoff exceeds the recorded market view or current clock")
        candidates = payload["candidates"]
        candidate = next((c for c in candidates if c.get("id", c.get("candidate_id")) == request["candidate_id"]), None)
        if candidate is None:
            raise ValueError("candidate is not in the retained verified queue")
        if parse_time(request["as_of"]) < parse_time(candidate.get("detected_at", candidate["as_of"])):
            raise ValueError("assessment precedes detection")
        rows = assessments(root)
        record = next((r for r in rows if r["request_hash"] == request_hash), None)
        if record is None:
            history = [r for r in rows if r["candidate_id"] == request["candidate_id"]]
            prior = history[-1] if history else None
            if request["supersedes"] != (prior["id"] if prior else None):
                raise ValueError("revision must name the latest superseded assessment")
            previous_state = prior["state"] if prior else candidate.get("detector_state", "DETECTED")
            if prior and parse_time(request["as_of"]) < parse_time(prior["as_of"]):
                raise ValueError("assessment revision cannot move cutoff backwards")
            if prior and prior.get("expires_at") and parse_time(request["as_of"]) >= parse_time(prior["expires_at"]) and previous_state != "REJECTED":
                previous_state = "EXPIRED"
            if request["state"] not in TRANSITIONS.get(previous_state, set()):
                raise ValueError("forbidden candidate state transition")
            if previous_state == "REJECTED" and request["state"] == "RESEARCHED" and (request["change_kind"] == "CHANGED_INFERENCE" or request["evidence"] == prior["evidence"]):
                raise ValueError("reopening rejected research requires changed evidence, not another opinion")
            record = {**request, "id": "ASSESSMENT:" + request_hash, "request_hash": request_hash,
                      "schema_version": SCHEMA, "sequence": len(rows) + 1,
                      "version": prior["version"] + 1 if prior else 1,
                      "recorded_at": utc_text(datetime.now(timezone.utc)),
                      "entry_permission": False, "evidence_verification": "ANALYST_DECLARATION",
                      "prev_hash": rows[-1]["record_hash"] if rows else None}
            record["record_hash"] = digest(record)
            with (root / "candidate_assessments.jsonl").open("ab") as stream:
                stream.write(canonical(record) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        payload["candidates"] = project(root, candidates, payload["run"]["as_of"])
        payload["assessment_projection"] = {**verify_assessments(root),
            "base_snapshot_sha256": payload.get("assessment_projection", {}).get("base_snapshot_sha256", snapshot["sha256"])}
        write_snapshot(root, payload)
        from ..timing_capture import make_attempt, append_attempt
        observation = make_attempt("assessment_timing:" + record["id"],
            detector_version="CANDIDATE_ASSESSMENT_TIMING_V1",
            universe_snapshot_id=payload["run"].get("input_sha256") or payload["assessment_projection"]["base_snapshot_sha256"], evidence_id=record["id"],
            evidence_kind="synthetic" if payload["run"].get("synthetic") else "recorded",
            recorded_at=record["recorded_at"], status="REJECTED" if record["state"] == "REJECTED" else "DECIDED",
            source="ANALYST_DECLARATION", times={"decision_at": record["recorded_at"]},
            links={"candidate_id": record["candidate_id"], "assessment_id": record["id"],
                   "run_id": payload["run"]["id"], "analytical_cutoff": record["as_of"]},
            reason="Actual assessment recording time; first detection and source publication remain separate.")
        append_attempt(root, observation, _locked=True)
    from .timing import publish_board
    publish_board(root)
    return record

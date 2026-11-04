"""Explicit, restartable paper cycles. No scheduler, broker, or network activity."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from .account import PaperAccount, SYMBOLS, _bars, signals, _quote, operation_id, apply, initial, _scenario
from .data import load_recorded_snapshot, parse_time, utc_text, capture_raw_evidence
from .storage import (locked, digest, read_json, atomic_json, immutable_json,
                      read_receipts, append_receipt, read_snapshot)
from .strategy import require_paper_profile, registry
from ..market_context import build_context, discover_candidates
from ..experiment_catalog import load_catalog
from .candidates import project, verify_assessments

REPO_ROOT = Path(__file__).resolve().parents[3]
VERSION = "KOD_EXPLICIT_CYCLE_V1"
META_KEYS = ("tick_size", "lot_step", "min_notional", "min_qty", "max_qty", "max_notional", "trading_status")


def now():
    return utc_text(datetime.now(timezone.utc))


def _envelope(payload):
    return {"schema_version": "KOD_RUNTIME_SNAPSHOT_V1", "payload": payload, "sha256": digest(payload)}


def _read_cycle(root, identifier):
    value = read_json(root / "cycles" / (identifier + ".json"))
    if value.get("schema_version") != "KOD_RUNTIME_SNAPSHOT_V1" or value.get("sha256") != digest(value.get("payload")):
        raise ValueError("cycle snapshot hash/schema mismatch")
    return value


def _metadata(profile, snapshot):
    supplied = {i["symbol"]: i for i in snapshot["instruments"] if i["venue"] == profile["venue"]}
    for symbol in SYMBOLS:
        item = supplied.get(symbol)
        if item is None or item["quote_asset"] != profile["quote_currency"]:
            raise ValueError("MISSING_ACCOUNT_INSTRUMENT: " + symbol)
        for key in META_KEYS:
            before, after = profile["instruments"][symbol].get(key), item.get(key)
            same = before == after if key == "trading_status" or before is None or after is None else Decimal(str(before)) == Decimal(str(after))
            if not same:
                raise ValueError("METADATA_CHANGED: " + symbol + ":" + key + "; explicit profile migration required")


def _history(account):
    account.verify()
    path = account.ledger.path
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def account_projection(raw, profile):
    view = raw.get("account")
    result = {"profile": profile["id"], "currency": profile["quote_currency"],
              "evidence_type": profile["evidence_type"], "simulation_only": True,
              "status": raw["status"], "cash": None, "reserved_cash": None,
              "free_cash": None, "equity": None, "nav_status": "UNAVAILABLE",
              "positions": None, "orders": raw.get("intents", []),
              "fills": [dict(f, filled_at=f["fill_recorded_at"]) for f in raw.get("fills", [])],
              "realized_pnl": None, "unrealized_pnl": None, "raw": raw}
    if view is not None:
        result.update(cash=view["cash_total"], reserved_cash=view["cash_reserved"],
                      free_cash=view["cash_available"], equity=view["nav"],
                      nav_status="MARKED" if view["nav"] is not None else "UNKNOWN_MARKS",
                      positions=[{"symbol": s, "quantity": q,
                                  "status": "UNMARKED" if s in view["missing_marks"] else "HELD",
                                  "average_entry_price": None, "mark_price": None,
                                  "market_value": None, "unrealized_pnl": None}
                                 for s, q in view["holdings"].items() if Decimal(q) != 0])
    return result


def _projected(root, envelope):
    evidence = verify_assessments(root)
    if not evidence["assessments"]:
        return envelope
    payload = copy.deepcopy(envelope["payload"])
    payload["candidates"] = project(root, payload["candidates"], payload["run"]["as_of"])
    payload["assessment_projection"] = {**evidence, "base_snapshot_sha256": envelope["sha256"]}
    return _envelope(payload)


def _commit(root, envelope, receipts):
    run = envelope["payload"]["run"]
    done = next((r for r in receipts if r.get("run_id") == run["id"] and r.get("status") == "COMPLETED"), None)
    if done and done["snapshot_sha256"] != envelope["sha256"]:
        raise ValueError("completed run snapshot differs from receipt")
    if done is None:
        append_receipt(root, {"runtime_version": VERSION, "run_id": run["id"], "status": "COMPLETED",
                              "as_of": run["as_of"], "input_sha256": run["input_sha256"],
                              "profile_sha256": run["profile_sha256"], "snapshot_sha256": envelope["sha256"],
                              "completed_at": now(), "mode": run["mode"]})
    # A retry of an old finished cycle must never roll the dashboard backwards.
    latest = read_snapshot(root) if (root / "snapshot.json").exists() else None
    if latest is None or parse_time(latest["payload"]["run"]["as_of"]) <= parse_time(run["as_of"]):
        atomic_json(root / "snapshot.json", _projected(root, envelope))
    pending = root / "pending.json"
    if pending.exists() and read_json(pending)["run_id"] == run["id"]:
        pending.unlink()
    atomic_json(root / "last_attempt.json", {"status": "COMPLETED", "run_id": run["id"], "as_of": run["as_of"], "recorded_at": now()})
    return _projected(root, envelope)


def _run_once(root, snapshot_path, profile_path, as_of, evidence_root=None, *, _captured=False, _trace=None):
    """Replay one explicit recorded cutoff. A replay never counts as forward proof.

    Crashes after individual account writes are resumed only with the same cycle.
    Ledger operations are idempotent, so retried observations cannot double fill.
    """
    root = Path(root)
    as_of = utc_text(parse_time(as_of))
    with locked(root):
        receipts = read_receipts(root)
        original = read_json(snapshot_path)
        profile = require_paper_profile(read_json(profile_path))
        forward = profile.get("execution_mode") == "FORWARD_PAPER_CAPTURE"
        if forward != _captured:
            raise ValueError("forward capture and recorded replay must use separate profiles and runtime roots")
        input_hash, profile_hash = digest(original), digest(profile)
        if _trace is not None and _trace.record["links"].get("input_sha256") != input_hash:
            raise ValueError("processing input changed after its observed read")
        identifier = "run_" + digest({"version": VERSION, "input": input_hash, "profile": profile_hash, "as_of": as_of})[:32]
        pending_path = root / "pending.json"
        if pending_path.exists() and read_json(pending_path)["run_id"] != identifier:
            raise ValueError("RECOVERY_REQUIRED: retry the preserved pending cycle before a new one")
        saved = root / "cycles" / (identifier + ".json")
        if saved.exists():
            return _commit(root, _read_cycle(root, identifier), receipts)
        if (root / "snapshot.json").exists():
            previous = read_snapshot(root)["payload"]
            if parse_time(as_of) < parse_time(previous["run"]["as_of"]):
                raise ValueError("new cycles cannot move the cutoff backwards")
        else:
            previous = None
        input_path = root / "inputs" / (input_hash + ".json")
        immutable_json(input_path, original)
        snapshot = load_recorded_snapshot(input_path, as_of, evidence_root)
        if snapshot["evidence_type"] != profile["evidence_type"]:
            raise ValueError("cross-profile snapshot evidence forbidden")
        # Construct validates profile without inventing initialization or cash.
        account = PaperAccount(root / "account", profile)
        _metadata(account.profile, snapshot)
        context = build_context(snapshot, as_of)
        if _trace is not None:
            _trace.mark("features_ready_at")
        discovered = discover_candidates(snapshot, context, as_of)
        if _trace is not None:
            _trace.extras["discovered"] = len(discovered)
            if discovered:
                _trace.mark("detected_at")
        experiments = load_catalog(REPO_ROOT)
        history = _history(account)
        before_account = account.ledger.state() or {}
        before_fills = {r["id"] for r in before_account.get("fills", [])}
        before_intents = {r["id"] for r in before_account.get("intents", [])}
        # Simulate all account-specific validation before the first durable write.
        # Invalid ticks, conflicting retries and backwards clocks must not strand a cycle.
        known = {row["id"]: row["command"] for row in history}
        probe = account.ledger.state()
        for row in snapshot["quotes"]:
            if row["venue"] != profile["venue"] or row["symbol"] not in SYMBOLS:
                continue
            evidence, observed_at = _quote(dict(row, evidence_type=snapshot["evidence_type"], at=row["received_at"]), account.profile)
            command = {"op": "observe", "at": observed_at, "evidence": evidence}
            oid = operation_id(command)
            if oid in known:
                if known[oid] != command:
                    raise ValueError("conflicting observation retry")
                continue
            if probe is None:
                epoch = account.profile.get("initialized_at", observed_at)
                if parse_time(epoch) > parse_time(observed_at):
                    raise ValueError("future account initialization")
                probe = initial({"op": "init", "at": epoch, "mode": "paper_only", "account_id": account.profile["id"],
                                 "profile": account.profile, "initial_cash": account.profile["initial_cash"], "scenario": _scenario(account.profile)})
            probe, _ = apply(probe, command)
            known[oid] = command
        signal_day = (parse_time(as_of).date() - timedelta(days=1)).isoformat()
        bars = {s: [dict(r, evidence_type=snapshot["evidence_type"]) for r in snapshot["bars"]
                    if r["symbol"] == s and r["venue"] == profile["venue"]][-40:] for s in SYMBOLS}
        decision_blocker = None
        try:
            signals(_bars(bars, signal_day, as_of, account.profile), signal_day, as_of)
        except ValueError as exc:
            decision_blocker = "INSUFFICIENT_SIGNAL_DATA: " + str(exc)
        immutable_json(root / "profile.json", profile)
        immutable_json(root / "inputs" / (input_hash + ".json"), original)
        # Copy and verify public raw evidence into the self-contained runtime root.
        if snapshot["evidence_type"] == "public_market":
            for entry in original.get("evidence", []):
                raw = (Path(evidence_root) / entry["path"]).read_bytes()
                copied = capture_raw_evidence(raw, root / "evidence", source_url=entry["source_url"],
                                             received_at=entry["received_at"], kind=entry["kind"], request=entry.get("request"))
                if copied != entry:
                    raise ValueError("evidence copy differs from original receipt")
            load_recorded_snapshot(root / "inputs" / (input_hash + ".json"), as_of, root / "evidence")
        immutable_json(pending_path, {"run_id": identifier, "as_of": as_of,
                                     "input_sha256": input_hash, "profile_sha256": profile_hash})
        for row in snapshot["quotes"]:
            if row["venue"] == profile["venue"] and row["symbol"] in SYMBOLS:
                account.observe(dict(row, evidence_type=snapshot["evidence_type"], at=row["received_at"]), run_id=identifier)
        decision_exists = any(r["id"] == "decision:" + signal_day for r in history)
        if decision_exists:
            decision_status = "ORIGINAL_DECISION_RETAINED"
        elif decision_blocker:
            decision_status = "BLOCKED"
        else:
            decision_status = account.decide(signal_day, bars, as_of, run_id=identifier)["status"]
            if _trace is not None:
                _trace.mark("decision_at")
        account.mark(as_of)
        if account.verify()["initialized"] and not any(r["id"] == "daily:" + as_of[:10] for r in history):
            account.daily_mark(as_of[:10], as_of)
        raw_account = account.snapshot(as_of)
        if _trace is not None:
            _trace.record["links"]["paper_new_fills_json"] = json.dumps(
                [r["id"] for r in raw_account.get("fills", []) if r["id"] not in before_fills])
            _trace.record["links"]["paper_new_intents_json"] = json.dumps(
                [r["id"] for r in raw_account.get("intents", []) if r["id"] not in before_intents])
        candidates = {c["id"]: c for c in (previous or {}).get("candidates", [])}
        for c in discovered:
            c = dict(c, id=c["candidate_id"], detected_at=as_of, reasons=[c["detection_reason"]],
                     plan=None, policy_id="DESCRIPTIVE_RADAR_V1", owner="KOD", version=1)
            candidates[c["id"]] = c
        for group in context["groups"]:
            coverage = group["coverage"]
            group["coverage_counts"] = coverage
            group["coverage"] = coverage["return_observations"] / coverage["members"] if coverage["members"] else None
        warnings = list(context["warnings"])
        if decision_blocker:
            warnings.append(decision_blocker)
        mode = "SYNTHETIC_DEMO" if profile["evidence_type"] == "synthetic" else "FORWARD_PAPER_CAPTURE" if forward else "RECORDED_PAPER_REPLAY"
        payload = {"run": {"id": identifier, "status": "COMPLETED_WITH_BLOCKERS" if decision_blocker else "COMPLETED",
                           "as_of": as_of, "generated_at": now(), "input_sha256": input_hash,
                           "profile_sha256": profile_hash, "mode": mode,
                           "evidence_type": profile["evidence_type"], "synthetic": profile["evidence_type"] == "synthetic",
                           "forward_trial_days": 0, "decision_status": decision_status, "warnings": warnings},
                   "health": {"sources": [{"name": "Recorded snapshot", "status": "PARTIAL",
                                            "as_of": as_of, "message": "Only retained supplied membership was scanned; broader market and primary-disclosure coverage are unverified."}],
                              "validation": snapshot["validation"], "queue_retrieval": "RETRIEVAL_VERIFIED" if previous else "NEW_RUNTIME_NO_PRIOR_QUEUE",
                              "membership": [r["instrument_id"] for r in snapshot["instruments"]],
                              "run_receipt": "LOCAL_HASH_CHAIN_NOT_EXTERNAL_TIMESTAMP"},
                   "market_context": context, "candidates": list(candidates.values()),
                   "account": account_projection(raw_account, profile),
                   "experiments": [dict(e, evidence_status=e["evidence_level"]) for e in experiments],
                   "strategies": registry()}
        envelope = _envelope(payload)
        immutable_json(saved, envelope)
        return _commit(root, envelope, receipts)


def run_once(root, snapshot_path, profile_path, as_of, evidence_root=None, *, _captured=False, scheduled_at=None):
    from .timing import processing_attempt

    trace = processing_attempt(root, snapshot_path, scheduled_at=scheduled_at, captured=_captured)
    try:
        result = _run_once(root, snapshot_path, profile_path, as_of, evidence_root,
                           _captured=_captured, _trace=trace)
        run = result["payload"]["run"]
        from .timing_paper import observe_paper_timing
        observe_paper_timing(root, payload=result["payload"], trace_record=trace.record,
                            process_quote_at=trace.record["received_at"], processed_at=trace.clock())
        state = "BLOCKED" if run["decision_status"] == "BLOCKED" else "COMPLETED"
        if trace.extras.get("discovered") == 0 and trace.record["decision_at"] is None:
            state = "NO_TRIGGER"
        trace.finish(state, links={"run_id": run["id"], "economic_cutoff": run["as_of"],
                     "decision_status": run["decision_status"]},
                     reason="Actual processing clock; economic references and historical fills remain unchanged.")
        return result
    except (ValueError, OSError, KeyError) as exc:
        if trace.record["status"] == "STARTED":
            trace.finish("FAILED", reason=type(exc).__name__)
        with locked(root):
            atomic_json(Path(root) / "last_attempt.json", {"status": "FAILED", "as_of": as_of,
                        "recorded_at": now(), "error": str(exc), "account_may_have_partial_cycle": (Path(root) / "pending.json").exists()})
        raise


def verify(root):
    root = Path(root)
    with locked(root):
        receipts = read_receipts(root)
        profile = read_json(root / "profile.json")
        require_paper_profile(profile)
        account = PaperAccount(root / "account", profile)
        report = account.verify()
        snapshot = read_snapshot(root)
        for receipt in receipts:
            if receipt.get("status") != "COMPLETED":
                continue
            envelope = _read_cycle(root, receipt["run_id"])
            if envelope["sha256"] != receipt["snapshot_sha256"]:
                raise ValueError("run receipt snapshot mismatch")
            source = root / "inputs" / (receipt["input_sha256"] + ".json")
            if digest(read_json(source)) != receipt["input_sha256"] or digest(profile) != receipt["profile_sha256"]:
                raise ValueError("profile or input hash mismatch")
            load_recorded_snapshot(source, receipt["as_of"], root / "evidence" if profile["evidence_type"] == "public_market" else None)
        base = _read_cycle(root, snapshot["payload"]["run"]["id"])
        if snapshot != _projected(root, base):
            raise ValueError("current snapshot differs from the archived cycle and verified assessments")
        matching = [r for r in receipts if r.get("snapshot_sha256") == base["sha256"]]
        if not matching:
            raise ValueError("current snapshot has no completed run receipt")
        from .timing import verify_timing
        timing = verify_timing(root)
        return {**report, "runs": len(receipts), "snapshot_sha256": snapshot["sha256"],
                "timing": timing,
                "recovery_required": (root / "pending.json").exists(),
                "evidence_type": profile["evidence_type"], "forward_trial_days": 0,
                "run": snapshot["payload"]["run"],
                "last_attempt": read_json(root / "last_attempt.json") if (root / "last_attempt.json").exists() else None}


def status(root):
    return verify(root)

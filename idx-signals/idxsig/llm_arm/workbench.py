"""Model-independent reasoning, complete failure memory and operator alerts.

No provider calls, arbitrary code execution, live orders or strategy promotion.
The model receives a packet and returns a proposal; this module owns its record.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

from ..runtime.storage import _pairs, canonical, digest, immutable_json, locked, read_json
from .contracts import (
    PROMPT,
    STATEMENTS,
    VERSION,
    now,
    timestamp,
    source_hash,
    validate_context,
    validate_response,
    validate_spec,
    finite,
)
from .journal import append, checkpoint, events, safe_root, verify_checkpoint


def implementation_hash():
    root = Path(__file__).parent
    return digest(
        {
            name: source_hash((root / name).read_text())
            for name in (
                "contracts.py",
                "journal.py",
                "workbench.py",
            )
        }
    )


def _load(root, *, recover=False, writing=False):
    manifest = read_json(root / "manifest.json")
    if manifest.get("schema_version") != VERSION or manifest.get("entry_permission") is not False:
        raise ValueError("invalid LLM manifest")
    validate_spec(manifest["spec"])
    rows = events(root, recover=recover)
    if (
        not rows
        or rows[0]["kind"] != "INITIALIZED"
        or rows[0]["payload"] != {"manifest_sha256": digest(manifest)}
    ):
        raise ValueError("manifest differs from initialization journal")
    if writing and manifest["implementation_sha256"] != implementation_hash():
        raise ValueError("implementation changed; start a separate cohort")
    return manifest, rows


def initialize(root, spec, *, memory_root=None, clock=now):
    """Freeze all expected candidates before accepting any response."""
    root = safe_root(root)
    validate_spec(spec)
    at = clock()
    if any(timestamp(c["set"]["entry_cutoff"]) <= timestamp(at) for c in spec["candidates"]):
        raise ValueError("new cohort cannot enroll candidates after entry cutoff")
    for candidate in spec["candidates"]:
        if timestamp(candidate["set"]["sealed_at"]) > timestamp(at):
            raise ValueError("candidate was not sealed at cohort initialization")
        if candidate["learner"] is not None and timestamp(
            candidate["learner"]["made_at"]
        ) > timestamp(at):
            raise ValueError("learner forecast was unavailable at cohort initialization")
    memory = None
    if memory_root is not None:
        if Path(memory_root).resolve() == root.resolve():
            raise ValueError("memory must come from a different completed cohort")
        memory = learning_memory(memory_root, clock=clock)
    manifest = {
        "schema_version": VERSION,
        "spec": spec,
        "created_at": at,
        "prompt": PROMPT,
        "memory": memory,
        "implementation_sha256": implementation_hash(),
        "entry_permission": False,
        "purpose": "ENGINEERING_DEVELOPMENT_ONLY",
    }
    with locked(root):
        if (root / "manifest.json").exists():
            existing = read_json(root / "manifest.json")
            if existing["spec"] != spec or existing["memory"] != memory:
                raise ValueError("cohort is frozen; cannot replace roster, model or memory")
            # Recover only the narrow manifest-before-first-event crash window.
            if not (root / "events").exists() and not (root / "runs.jsonl").exists():
                append(root, "INITIALIZED", {"manifest_sha256": digest(existing)}, at)
            _load(root)
            return existing
        if any(p.name != ".runtime.lock" for p in root.iterdir()):
            raise ValueError("initialize requires a dedicated empty directory")
        immutable_json(root / "manifest.json", manifest)
        append(root, "INITIALIZED", {"manifest_sha256": digest(manifest)}, at)
    return manifest


def _candidate(manifest, identifier):
    found = [c for c in manifest["spec"]["candidates"] if c["set"]["set_id"] == identifier]
    if len(found) != 1:
        raise ValueError("candidate is not in frozen roster")
    return found[0]


def _for(rows, kind, identifier):
    return [r for r in rows if r["kind"] == kind and r["payload"].get("set_id") == identifier]


def prepare(root, identifier, context, *, clock=now):
    root = safe_root(root)
    with locked(root):
        manifest, rows = _load(root, recover=True, writing=True)
        candidate = _candidate(manifest, identifier)
        prior = _for(rows, "PACKET", identifier)
        if prior:
            if prior[0]["payload"]["context"] != context:
                raise ValueError("candidate packet already frozen")
            return prior[0]["payload"]
        at = clock()
        validate_context(context, at, candidate)
        packet = {
            "set_id": identifier,
            "model": manifest["spec"]["model"],
            "candidate": candidate,
            "context": copy.deepcopy(context),
            "prepared_at": at,
            "system_instructions": manifest["prompt"],
            "memory": manifest["memory"],
            "source_receipts": [
                {"id": s["id"], "sha256": source_hash(s["content"])} for s in context["sources"]
            ],
            "provenance": "SUPPLIED_RECEIPTS_NOT_INDEPENDENTLY_VERIFIED",
            "entry_permission": False,
        }
        packet["packet_sha256"] = digest(packet)
        append(root, "PACKET", packet, at)
        return packet


def record_response(root, identifier, response, *, clock=now):
    """Retain every attempt. Only the first valid, timely response can be admitted."""
    root = safe_root(root)
    with locked(root):
        manifest, rows = _load(root, recover=True, writing=True)
        candidate = _candidate(manifest, identifier)
        packets = _for(rows, "PACKET", identifier)
        attempts = _for(rows, "RESPONSE", identifier)
        at = clock()
        state, error = "ADMITTED", None
        elapsed = None
        # Invalid JSON-compatible values must still consume the first submission.
        # The CLI passes malformed raw text in an explicit rejection envelope.
        encoding_error = None
        try:
            raw = canonical(response)
            if len(raw) > 100000:
                encoding_error = "response exceeds 100000 bytes"
                response = {"rejected_sha256": source_hash(raw.decode()), "bytes": len(raw)}
        except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
            encoding_error = "response is not finite JSON"
            response = {"rejected_representation": repr(response)[:100000]}
        try:
            if encoding_error:
                raise ValueError(encoding_error)
            if attempts:
                raise ValueError("first attempt is final; retries cannot replace it")
            if not packets:
                raise ValueError("no reserved reasoning packet")
            packet = packets[0]["payload"]
            elapsed = (timestamp(at) - timestamp(packet["prepared_at"])).total_seconds()
            if elapsed < 0:
                raise ValueError("clock moved backwards")
            validate_response(response, packet)
            if timestamp(at) >= timestamp(candidate["set"]["entry_cutoff"]):
                state, error = "LATE", "response arrived at or after entry cutoff"
            elif elapsed > manifest["spec"]["latency_budget_seconds"]:
                state, error = "SLOW", "response exceeded frozen latency budget"
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            state, error = "REJECTED", str(exc)
        payload = {
            "set_id": identifier,
            "attempt": len(attempts) + 1,
            "status": state,
            "error": error,
            "response": response,
            "wall_elapsed_seconds": elapsed,
            "duration_quality": "LOCAL_WALL_CLOCK_NOT_PROVIDER_LATENCY",
            "entry_permission": False,
        }
        append(root, "RESPONSE", payload, at)
        return payload


def record_file(root, identifier, path, *, clock=now):
    raw_bytes = Path(path).read_bytes()
    try:
        raw = raw_bytes.decode("utf-8")
        response = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: float("nan"))
    except (ValueError, json.JSONDecodeError, RecursionError, UnicodeError):
        import hashlib

        response = {
            "invalid_json_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "raw_prefix": raw_bytes[:100000].decode("utf-8", errors="backslashreplace"),
        }
    return record_response(root, identifier, response, clock=clock)


def resolve(root, register, *, clock=now):
    """Import exact BASE5 outcomes from the independent speculation register.

    Never accept outcome fields from model responses. Register receipt/authority
    verification remains the existing paper verifier's responsibility.
    """
    root = safe_root(root)
    with locked(root):
        manifest, rows = _load(root, recover=True, writing=True)
        at = clock()
        pending = []
        for candidate in manifest["spec"]["candidates"]:
            source = candidate["set"]
            identifier = source["set_id"]
            sets = [
                r
                for r in register
                if r.get("type") == "SPECULATION_SET" and r.get("set_id") == identifier
            ]
            if len(sets) != 1 or sets[0] != source:
                raise ValueError("outcome source does not contain the exact frozen set")
            matches = [
                r
                for r in register
                if r.get("type") == "RESOLUTION"
                and r.get("set_id") == identifier
                and r.get("window") == "BASE5"
            ]
            if not matches:
                continue
            if len(matches) != 1:
                raise ValueError("ambiguous BASE5 outcome; preserve and review corrections")
            resolution = matches[0]
            if resolution.get("status") != "RESOLVED":
                continue
            if any(
                resolution.get(k) != source.get(k)
                for k in ("market", "ticker", "signal_session", "protocol")
            ):
                raise ValueError("resolution identity differs from frozen set")
            if (
                not timestamp(source["entry_cutoff"])
                < timestamp(resolution["resolved_at"])
                <= timestamp(at)
            ):
                raise ValueError("resolution time is invalid")
            cone = [r for r in resolution["cone"] if r.get("id") in STATEMENTS]
            if len(cone) != 3 or {r["id"] for r in cone} != set(STATEMENTS):
                raise ValueError("resolution statements are incomplete or ambiguous")
            if any(
                type(r.get("outcome")) is not bool and r.get("outcome") is not None for r in cone
            ):
                raise ValueError("outcome must be boolean or unknown")
            net = resolution.get("candidate", {}).get("trade", {}).get("net_return")
            if net is not None:
                finite(net, "net return")
            retained = _for(rows, "OUTCOME", identifier)
            payload = {
                "set_id": identifier,
                "resolution": resolution,
                "source_sha256": digest(resolution),
                "net_return": net,
                "outcomes": {r["id"]: r["outcome"] for r in cone},
                "provenance": "REGISTER_BYTES_BOUND_AUTHORITY_NOT_VERIFIED_HERE",
            }
            if retained:
                if retained[0]["payload"] != payload:
                    raise ValueError("retained outcome differs; cannot rewrite a loss")
            else:
                pending.append(payload)
        for payload in pending:
            append(root, "OUTCOME", payload, at)
        return {"imported": len(pending), "entry_permission": False}


def _report(root, manifest, rows, at):
    cases, alerts = [], []
    for candidate in manifest["spec"]["candidates"]:
        identifier = candidate["set"]["set_id"]
        packets = _for(rows, "PACKET", identifier)
        responses = _for(rows, "RESPONSE", identifier)
        outcomes = _for(rows, "OUTCOME", identifier)
        first = responses[0]["payload"] if responses else None
        outcome = outcomes[0]["payload"] if outcomes else None
        state = (
            first["status"]
            if first
            else (
                "MISSING_RESPONSE"
                if timestamp(at) >= timestamp(candidate["set"]["entry_cutoff"])
                else "PENDING"
            )
        )
        response = first["response"] if first and first["status"] == "ADMITTED" else None
        case = {
            "set_id": identifier,
            "status": state,
            "attempts": len(responses),
            "call": response["call"] if response else None,
            "net_return": outcome["net_return"] if outcome else None,
            "outcome_status": "RESOLVED" if outcome else "PENDING",
            "unknown_statements": [
                s for s in STATEMENTS if not outcome or outcome["outcomes"][s] is None
            ],
            "probability_scores": {},
            "proposal": response["proposal"] if response else None,
            "wall_elapsed_seconds": first["wall_elapsed_seconds"] if first else None,
        }
        if packets:
            packet = packets[0]["payload"]
            case["timing"] = {
                "context_age_at_prepare_seconds": (
                    timestamp(packet["prepared_at"]) - timestamp(packet["context"]["as_of"])
                ).total_seconds(),
                "set_seal_to_prepare_seconds": (
                    timestamp(packet["prepared_at"]) - timestamp(candidate["set"]["sealed_at"])
                ).total_seconds(),
                "prepare_to_response_seconds": case["wall_elapsed_seconds"],
                "measurement": "LOCAL_WALL_CLOCK_INCLUDES_TRANSPORT_AND_OPERATOR_TIME",
                "provider_latency_seconds": None,
            }
        if response and outcome:
            priors = {s["id"]: s["prior"] for s in candidate["set"]["cone"]}
            for statement, value in outcome["outcomes"].items():
                if value is not None:
                    case["probability_scores"][statement] = {
                        "llm_brier": (response["p"][statement] - value) ** 2,
                        "prior_brier": (priors[statement] - value) ** 2,
                        "learner_brier": None
                        if candidate["learner"] is None
                        else (candidate["learner"]["p"][statement] - value) ** 2,
                    }
        codes = []
        if state not in ("ADMITTED", "PENDING"):
            codes.append(state)
        if len(responses) > 1:
            codes.append("RETRIES_RETAINED")
        if candidate["learner"] is None:
            codes.append("MISSING_COMPARATOR")
        if packets and not packets[0]["payload"]["context"]["sources"]:
            codes.append("NO_SOURCE_RECEIPTS")
        if not outcome and timestamp(at) >= timestamp(candidate["resolution_due_at"]):
            codes.append("OUTCOME_OVERDUE")
        if case["net_return"] is not None and case["net_return"] < 0:
            codes.append("NEGATIVE_BASE5_OUTCOME")
        alerts.extend({"set_id": identifier, "code": code} for code in codes)
        cases.append(case)
    resolved = [r for r in cases if r["outcome_status"] == "RESOLVED"]
    complete = len(resolved) == len(cases) and all(r["status"] != "PENDING" for r in cases)
    # Performance is visible only after this engineering cohort closes. It is
    # descriptive development feedback, never a significance or promotion test.
    if not complete:
        for case in cases:
            case.pop("probability_scores")
    return {
        "schema_version": VERSION,
        "cohort": manifest["spec"]["cohort"],
        "as_of": at,
        "expected_candidates": len(cases),
        "counts": dict(Counter(r["status"] for r in cases)),
        "resolved_candidates": len(resolved),
        "complete": complete,
        "cases": cases,
        "alerts": alerts,
        "checkpoint": checkpoint(root, rows),
        "integrity": "LOCAL_HASH_CHAIN_AND_INTENTS_ONLY",
        "external_timestamp_verified": False,
        "notifications_delivered": False,
        "model_service_running": False,
        "entry_permission": False,
        "learning": "COMPLETED_COHORT_MEMORY_ONLY",
        "learner_provenance": "SUPPLIED_NOT_INDEPENDENTLY_VERIFIED",
        "fact_validation": "CITATION_IDS_ONLY_NOT_TRUTH_OR_ENTAILMENT",
        "submission_coverage": "FIRST_SUBMITTED_RESPONSE_NOT_ALL_EXTERNAL_GENERATIONS",
        "evaluation": "DESCRIPTIVE_DEVELOPMENT_ONLY" if complete else "PROBABILITY_SCORES_WITHHELD",
        "implementation_matches": manifest["implementation_sha256"] == implementation_hash(),
    }


def status(root, *, clock=now, expected_checkpoint=None):
    root = safe_root(root)
    with locked(root):
        manifest, rows = _load(root)
        if expected_checkpoint is not None:
            verify_checkpoint(root, rows, expected_checkpoint)
        return _report(root, manifest, rows, clock())


def learning_memory(root, *, clock=now):
    report = status(root, clock=clock)
    if not report["complete"]:
        raise ValueError("memory blocked until every expected candidate has an outcome")
    return {
        "source_cohort": report["cohort"],
        "checkpoint": report["checkpoint"],
        "cases": report["cases"],
        "alerts": report["alerts"],
        "lesson_policy": "ALL_CASES_WITHIN_SELECTED_COHORT",
        "validated_edge": False,
        "cohort_selection": "OPERATOR_SELECTED_NOT_GLOBAL_EXPERIMENT_REGISTRY",
    }


def watch(root, *, clock=now):
    """Write each observed local alert once; stdout/exit code are scheduler inputs."""
    root = safe_root(root)
    with locked(root):
        manifest, rows = _load(root, recover=True)
        at = clock()
        report = _report(root, manifest, rows, at)
        old = {r["payload"]["alert_sha256"] for r in rows if r["kind"] == "ALERT"}
        for alert in report["alerts"]:
            sha = digest(alert)
            if sha not in old:
                append(root, "ALERT", {**alert, "alert_sha256": sha}, at)
                old.add(sha)
        return report


def recover(root):
    root = safe_root(root)
    with locked(root):
        _, rows = _load(root, recover=True)
        return checkpoint(root, rows)

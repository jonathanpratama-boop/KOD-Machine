"""Finite research worker with immutable inputs and restart-safe attempt accounting.

Proposals may be written by a person or an AI. This worker executes only registered
strategy templates; it neither calls a language model nor executes supplied code.
A reservation consumes budget before evaluation, including an interrupted attempt.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ..runtime.storage import (
    append_receipt,
    digest,
    immutable_json,
    locked,
    read_json,
    read_receipts,
)
from .evaluator import EvaluationBlocked, evaluate
from .spec import (
    hash_text,
    hypothesis_hash,
    validate_dataset,
    validate_proposal,
    validate_protocol,
)

VERSION = "KOD_RESEARCH_WORKER_V1"


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def implementation_hash():
    """Bind the cohort to the actual evaluator, strategy, costs, checks and worker."""
    package = Path(__file__).resolve().parent
    names = [
        "spec.py",
        "evaluator.py",
        "worker.py",
        "../components/strategy.py",
        "../components/costs.py",
        "../strategy_checks.py",
    ]
    return digest(
        {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in names}
    )


def _root(path):
    root = Path(path)
    if root.is_symlink():
        raise ValueError("research cohort root must not be a symbolic link")
    for name in (
        "manifest.json",
        "inputs",
        "proposals",
        "results",
        "reservations",
        "runs.jsonl",
        ".runtime.lock",
    ):
        if (root / name).is_symlink():
            raise ValueError("research artifacts must not be symbolic links")
    return root


def _artifact(root, folder, sha):
    hash_text(sha, "artifact hash")
    path = root / folder / f"{sha}.json"
    if path.is_symlink():
        raise ValueError("research artifact must not be a symbolic link")
    value = read_json(path)
    if digest(value) != sha:
        raise ValueError(f"research artifact hash mismatch: {folder}/{sha}")
    return value


def _initialize(root, protocol, dataset):
    manifest = {
        "schema_version": VERSION,
        "protocol_sha256": digest(protocol),
        "dataset_sha256": digest(dataset),
        "evidence_kind": dataset["kind"],
        "implementation_sha256": implementation_hash(),
        "live_eligible": False,
    }
    path = root / "manifest.json"
    if not path.exists():
        allowed = {".runtime.lock", "inputs"}
        if any(item.name not in allowed for item in root.iterdir()):
            raise ValueError("a research cohort requires a dedicated root")
        inputs = root / "inputs"
        expected = {f"{digest(protocol)}.json": protocol, f"{digest(dataset)}.json": dataset}
        if inputs.exists():
            if not inputs.is_dir():
                raise ValueError("research initialization inputs must be a directory")
            for item in inputs.iterdir():
                if item.is_symlink() or item.name not in expected or not item.is_file():
                    raise ValueError("unexpected artifact in unfinished research initialization")
                if read_json(item) != expected[item.name]:
                    raise ValueError("unfinished research input differs from frozen specification")
    # Check the frozen manifest before writing any new input into an existing cohort.
    if path.exists() and read_json(path) != manifest:
        raise ValueError("cohort protocol, dataset or evaluator changed; existing cohort is frozen")
    immutable_json(root / "inputs" / f"{digest(protocol)}.json", protocol)
    immutable_json(root / "inputs" / f"{digest(dataset)}.json", dataset)
    immutable_json(path, manifest)
    return manifest


def _state(root):
    manifest = read_json(root / "manifest.json")
    if manifest.get("schema_version") != VERSION or manifest.get("live_eligible") is not False:
        raise ValueError("invalid research manifest")
    protocol = _artifact(root, "inputs", manifest["protocol_sha256"])
    dataset = _artifact(root, "inputs", manifest["dataset_sha256"])
    validate_protocol(protocol)
    validate_dataset(dataset, protocol)
    if manifest.get("evidence_kind") != dataset["kind"]:
        raise ValueError("manifest evidence kind differs from dataset")
    reservations, results, histories = {}, {}, []
    for row in read_receipts(root):
        kind = row.get("kind")
        if kind in {"RESERVED", "DUPLICATE", "BUDGET_EXHAUSTED"}:
            proposal = _artifact(root, "proposals", row["proposal_sha256"])
            if hypothesis_hash(proposal) != row["hypothesis_sha256"]:
                raise ValueError("research hypothesis identity changed")
        if kind == "RESERVED":
            key = row["hypothesis_sha256"]
            if key in reservations or row["attempt"] != len(reservations) + 1:
                raise ValueError("duplicate or unordered research reservation")
            reservations[key] = {
                k: v for k, v in row.items() if k not in {"prev_hash", "record_hash"}
            }
            if len(reservations) > protocol["max_attempts"]:
                raise ValueError("retained research budget exceeded")
        elif kind == "COMPLETED":
            key = row["hypothesis_sha256"]
            if key not in reservations or key in results:
                raise ValueError("orphan or duplicate research completion")
            result = _artifact(root, "results", row["result_sha256"])
            reserved = reservations[key]
            if any(
                result.get(name) != reserved[name]
                for name in (
                    "attempt",
                    "hypothesis_sha256",
                    "proposal_sha256",
                )
            ):
                raise ValueError("result is not bound to its reserved proposal")
            if result.get("status") not in {"COMPLETED", "FAILED", "INTERRUPTED"}:
                raise ValueError("invalid research outcome status")
            if (
                result.get("entry_permission") is not False
                or result.get("live_eligible") is not False
            ):
                raise ValueError("research result cannot grant entry permission")
            results[key] = result
        elif kind == "DUPLICATE":
            if row["hypothesis_sha256"] not in reservations:
                raise ValueError("duplicate has no prior hypothesis")
        elif kind == "BUDGET_EXHAUSTED":
            if len(reservations) < protocol["max_attempts"]:
                raise ValueError("premature budget exhaustion record")
        else:
            raise ValueError("unknown research receipt kind")
        histories.append(row)
    retained = root / "reservations"
    expected = {f"attempt-{row['attempt']}.json": row for row in reservations.values()}
    actual = {item.name: item for item in retained.iterdir()} if retained.exists() else {}
    if actual.keys() != expected.keys():
        raise ValueError(
            "research reservation journal is incomplete; preserve artifacts and recover"
        )
    for name, reservation in expected.items():
        item = actual[name]
        if item.is_symlink() or not item.is_file() or read_json(item) != reservation:
            raise ValueError("immutable research reservation differs from journal")
    # Completion intents can precede their receipt, but never their reservation.
    for item in (root / "results").glob("attempt-*.json"):
        if item.name not in expected or item.is_symlink():
            raise ValueError("orphan research completion intent")
        result = read_json(item)
        if any(
            result.get(name) != expected[item.name][name]
            for name in (
                "attempt",
                "hypothesis_sha256",
                "proposal_sha256",
            )
        ):
            raise ValueError("completion intent differs from its reservation")
    return manifest, protocol, dataset, reservations, results, histories


def _complete(root, reservation, result):
    sha = digest(result)
    immutable_json(root / "results" / f"{sha}.json", result)
    append_receipt(
        root,
        {
            "kind": "COMPLETED",
            "hypothesis_sha256": reservation["hypothesis_sha256"],
            "result_sha256": sha,
            "recorded_at": _now(),
        },
    )
    return result


def _base_result(reservation):
    return {
        name: reservation[name]
        for name in ("attempt", "hypothesis_sha256", "proposal_sha256", "started_at")
    } | {"entry_permission": False, "live_eligible": False}


def _recover(root, reservations, results):
    """An incomplete reservation stays spent; never silently rerun it after a crash."""
    for key, reservation in reservations.items():
        if key in results:
            continue
        # An immutable completion intent bridges a crash between result write and journal append.
        pending = root / "results" / f"attempt-{reservation['attempt']}.json"
        if pending.exists():
            if pending.is_symlink():
                raise ValueError("research completion intent must not be a symbolic link")
            result = read_json(pending)
            if any(
                result.get(name) != reservation[name]
                for name in ("attempt", "hypothesis_sha256", "proposal_sha256")
            ):
                raise ValueError("pending result differs from reservation")
        else:
            result = _base_result(reservation) | {
                "status": "INTERRUPTED",
                "finished_at": _now(),
                "error": "Reserved attempt did not complete; budget remains consumed",
            }
            immutable_json(pending, result)
        results[key] = _complete(root, reservation, result)


def _summary(manifest, protocol, reservations, results):
    counts = {
        name: sum(row["status"] == name for row in results.values())
        for name in ("COMPLETED", "FAILED", "INTERRUPTED")
    }
    return {
        "schema_version": VERSION,
        "protocol_id": protocol["id"],
        "protocol_sha256": manifest["protocol_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "evidence_kind": manifest["evidence_kind"],
        "evaluation_basis": "CLOSE_PRICE_PROXY",
        "source_evidence_status": "SYNTHETIC"
        if manifest["evidence_kind"] == "synthetic"
        else "DECLARED_NOT_RECONCILED",
        "profitability_validated": False,
        "implementation_matches": manifest["implementation_sha256"] == implementation_hash(),
        "attempts_used": len(reservations),
        "attempts_remaining": protocol["max_attempts"] - len(reservations),
        "pending_attempts": len(reservations) - len(results),
        "counts": counts,
        "results": list(results.values()),
        "entry_permission": False,
        "live_eligible": False,
        "integrity_scope": "Retained-byte consistency; no independent historical timestamp proof",
    }


def status(root):
    """Read and verify a retained cohort. This does not resume work or consume budget."""
    root = _root(root)
    if not (root / "manifest.json").exists():
        return {"schema_version": VERSION, "status": "NOT_INITIALIZED", "entry_permission": False}
    with locked(root):
        manifest, protocol, _, reservations, results, _ = _state(root)
        return _summary(manifest, protocol, reservations, results)


def run_batch(root, protocol, dataset, proposals):
    """Process a finite list of strict JSON proposals under one frozen cohort budget."""
    protocol = validate_protocol(protocol)
    dataset = validate_dataset(dataset, protocol)
    if not isinstance(proposals, list) or not 1 <= len(proposals) <= 100:
        raise ValueError("supply one to one hundred proposals per explicit batch")
    root = _root(root)
    submitted = []
    with locked(root):
        manifest = _initialize(root, protocol, dataset)
        _, _, _, reservations, results, _ = _state(root)
        _recover(root, reservations, results)
        for proposal in proposals:
            if implementation_hash() != manifest["implementation_sha256"]:
                raise ValueError("evaluator implementation changed during the batch")
            proposal_sha = digest(proposal)
            key = hypothesis_hash(proposal)
            immutable_json(root / "proposals" / f"{proposal_sha}.json", proposal)
            reference = {"proposal_sha256": proposal_sha, "hypothesis_sha256": key}
            if key in reservations:
                append_receipt(root, reference | {"kind": "DUPLICATE", "recorded_at": _now()})
                submitted.append(
                    reference | {"status": "DUPLICATE", "attempt": reservations[key]["attempt"]}
                )
                continue
            if len(reservations) >= protocol["max_attempts"]:
                append_receipt(
                    root, reference | {"kind": "BUDGET_EXHAUSTED", "recorded_at": _now()}
                )
                submitted.append(reference | {"status": "BUDGET_EXHAUSTED"})
                continue
            reservation = reference | {
                "kind": "RESERVED",
                "attempt": len(reservations) + 1,
                "started_at": _now(),
            }
            immutable_json(
                root / "reservations" / f"attempt-{reservation['attempt']}.json", reservation
            )
            append_receipt(root, reservation)
            reservations[key] = reservation
            result = _base_result(reservation)
            try:
                validated = validate_proposal(proposal)
                evaluation = evaluate(protocol, dataset, validated)
                if implementation_hash() != manifest["implementation_sha256"]:
                    raise ValueError("evaluator implementation changed during the attempt")
                result.update(status="COMPLETED", evaluation=evaluation)
            except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                result.update(status="FAILED", error=str(exc), error_type=type(exc).__name__)
                if isinstance(exc, EvaluationBlocked):
                    result["strategy_checks"] = exc.checks
            result["finished_at"] = _now()
            immutable_json(root / "results" / f"attempt-{reservation['attempt']}.json", result)
            results[key] = _complete(root, reservation, result)
            submitted.append(
                reference | {"status": result["status"], "attempt": reservation["attempt"]}
            )
        summary = _summary(manifest, protocol, reservations, results)
        summary["submissions"] = submitted
        return summary

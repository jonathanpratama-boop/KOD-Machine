#!/usr/bin/env python3
"""Audit frozen LLM_ARM v1 records and retain local readiness snapshots.

This reads repository records; it does not call a model, collect new forecasts,
evaluate profitability, modify source evidence or send notifications.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "idx-signals"))

from idxsig.llm_arm.audit import audit, load_jsonl  # noqa: E402
from idxsig.runtime.storage import (  # noqa: E402
    append_receipt,
    digest,
    immutable_json,
    locked,
    read_json,
    read_receipts,
)


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _output(path):
    root = Path(path).absolute()
    if any(parent.is_symlink() for parent in (root, *root.parents)):
        raise ValueError("watch output cannot use symbolic links")
    if root.exists():
        if any(item.is_symlink() for item in root.rglob("*")):
            raise ValueError("watch artifacts cannot use symbolic links")
        if any(
            item.name not in {".runtime.lock", "runs.jsonl", "snapshots"} for item in root.iterdir()
        ):
            raise ValueError("watch output requires a dedicated directory")
    return root


def _read(path, repository, inputs, errors):
    relative = path.relative_to(repository).as_posix()
    try:
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError("source must not be a symbolic link")
        raw = path.read_bytes()
        inputs[relative] = {"sha256": _sha(raw), "bytes": len(raw)}
        rows = load_jsonl(path)
        digest(rows)  # Reject overflowing numeric literals such as 1e999 before processing.
        if path.read_bytes() != raw:
            raise ValueError("source changed during audit")
        inputs[relative]["rows"] = len(rows)
        return rows
    except (OSError, ValueError, UnicodeError) as exc:
        inputs.setdefault(relative, {"sha256": None, "bytes": None})
        errors.append({"code": "INPUT_UNREADABLE", "path": relative, "detail": str(exc)})
        return []


def _chain_errors(register):
    errors, previous = [], None
    for number, row in enumerate(register, 1):
        if not isinstance(row, dict):
            errors.append({"code": "REGISTER_CHAIN_INVALID", "row": number})
            continue
        body = {key: value for key, value in row.items() if key != "record_hash"}
        if row.get("prev_hash") != previous or row.get("record_hash") != digest(body):
            errors.append({"code": "REGISTER_CHAIN_INVALID", "row": number})
        previous = row.get("record_hash")
    return errors


def inspect(repository):
    """Build a deterministic report from whole-file hashes and strict record reads."""
    repository = Path(repository).absolute()
    inputs, errors, issues, calls = {}, [], [], []
    call_paths = sorted((repository / "idx-signals/research/LLM_ARM_v1").glob("calls*.jsonl"))
    if not call_paths:
        errors.append({"code": "NO_CALL_FILES"})
    for path in call_paths:
        calls.extend(_read(path, repository, inputs, errors))
    register = _read(
        repository / "idx-signals/paper/speculations.jsonl", repository, inputs, errors
    )
    if not calls:
        errors.append({"code": "NO_CALL_ROWS"})
    if not register:
        errors.append({"code": "NO_REGISTER_ROWS"})
    chain_errors = _chain_errors(register)
    errors.extend(chain_errors)
    result = audit(calls, register)
    for row in result["calls"]:
        if row["issues"]:
            errors.append(
                {"code": "CALL_STRUCTURAL_ISSUES", "row": row["row"], "issues": row["issues"]}
            )
    if result["counts"]["malformed_register_rows"]:
        errors.append(
            {
                "code": "MALFORMED_REGISTER_ROWS",
                "count": result["counts"]["malformed_register_rows"],
            }
        )
    set_ids = Counter(
        row["set_id"]
        for row in register
        if isinstance(row, dict)
        and row.get("type") == "SPECULATION_SET"
        and isinstance(row.get("set_id"), str)
    )
    if any(count > 1 for count in set_ids.values()):
        errors.append({"code": "DUPLICATE_REGISTER_SET_IDS"})
    for field, code in (
        ("without_source_urls", "CALLS_WITHOUT_SOURCE_URLS"),
        ("missing_numeric_context", "MISSING_NUMERIC_CONTEXT"),
        ("numeric_forecast_declared_unsealed", "NUMERIC_FORECASTS_DECLARED_UNSEALED"),
        ("missing_register_priors", "MISSING_REGISTER_PRIORS"),
    ):
        if result["counts"][field]:
            issues.append({"code": code, "count": result["counts"][field]})
    issues.append({"code": "LEARNER_COMPARISON_NOT_VERIFIED", "count": len(calls)})
    issues.append(
        {"code": result["first_look"]["status"], "remaining": result["first_look"]["remaining"]}
    )
    return {
        "schema_version": "KOD_LLM_ARM_WATCH_V1",
        "status": "BLOCKED" if errors else "ISSUES" if issues else "OK",
        "inputs": inputs,
        "implementation": {
            "watcher_sha256": _sha(Path(__file__).read_bytes()),
            "audit_sha256": _sha((ROOT / "idx-signals/idxsig/llm_arm/audit.py").read_bytes()),
        },
        "audit": result,
        "errors": errors,
        "issues": issues,
        "register_chain": "LOCAL_BYTES_CHECKED"
        if register and not chain_errors
        else "INVALID_OR_MISSING",
        "source_calls_timestamp_verified": False,
        "notifications_delivered": False,
        "notification_note": "GitHub workflow notifications depend on account settings; artifact creation is not delivery.",
        "continuity_scope": "Journal covers this output directory only; CI artifacts are separate per workflow run.",
        "entry_permission": False,
        "profitability_validated": False,
    }


def watch(repository, output, *, clock=_now):
    """Retain one immutable snapshot and receipt per distinct report in this directory."""
    root = _output(output)
    report = inspect(repository)
    sha = digest(report)
    with locked(root):
        rows = read_receipts(root)
        for row in rows:
            recorded = row.get("snapshot_sha256")
            if (
                not isinstance(recorded, str)
                or len(recorded) != 64
                or any(c not in "0123456789abcdef" for c in recorded)
            ):
                raise ValueError("invalid retained watch snapshot identity")
            retained = read_json(root / "snapshots" / f"{recorded}.json")
            if digest(retained) != recorded:
                raise ValueError("retained watch snapshot hash mismatch")
        immutable_json(root / "snapshots" / f"{sha}.json", report)
        if not any(row["snapshot_sha256"] == sha for row in rows):
            append_receipt(
                root,
                {
                    "kind": "LLM_ARM_AUDIT",
                    "snapshot_sha256": sha,
                    "recorded_at": clock(),
                    "status": report["status"],
                },
            )
    return {
        "snapshot_sha256": sha,
        "snapshot_path": str(root / "snapshots" / f"{sha}.json"),
        **report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = watch(args.repository, args.output)
        # JSON escaping keeps untrusted source strings out of workflow-command syntax.
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 1 if result["errors"] else 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print(
            json.dumps({"status": "BLOCKED", "error": str(exc), "notifications_delivered": False}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

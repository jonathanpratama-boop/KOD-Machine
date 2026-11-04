"""Validate retained paper operations in an isolated, explicitly recorded replay.

Source files are only read. A copied checkpoint is verified before fresh cycles
are reconstructed in receipt order. Local execution clocks and derived catalog
text are not compared as economics. No capture, provider request, or order route
is available through this module.
"""

from __future__ import annotations

import contextlib
import copy
import fcntl
import hashlib
from pathlib import Path
import tempfile

from . import coordinator
from .storage import atomic_json, digest, read_json, read_receipts

VERSION = "KOD_RECORDED_VALIDATION_V1"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024


def _files(root):
    """Enumerate ordinary files only; lock contents are not retained evidence."""
    paths, total = [], 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("validation source cannot contain symbolic links")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("validation source must contain ordinary files")
        if path.name.endswith(".lock"):
            continue
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError("validation source exceeds bounded archive size")
        paths.append(path)
    return paths


def _manifest(root, *, destination=None):
    manifest = []
    for path in _files(root):
        body = path.read_bytes()
        if len(body) > MAX_FILE_BYTES:
            raise ValueError("validation source changed beyond size limit")
        relative = path.relative_to(root)
        manifest.append(
            {
                "path": relative.as_posix(),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
        if destination is not None:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    return manifest


@contextlib.contextmanager
def _source_lock(root):
    """Share an existing writer lock without creating or modifying source files."""
    path = root / ".runtime.lock"
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid runtime source lock")
        with path.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    else:
        yield


def _economics(envelope):
    payload = envelope["payload"]
    account = copy.deepcopy(payload["account"])
    # Only execution_mode changes in the replay profile. Preserve its semantic
    # ID so quote, order and scenario identities can be compared exactly.
    account["raw"].pop("profile_sha256", None)
    return {
        "as_of": payload["run"]["as_of"],
        "decision_status": payload["run"]["decision_status"],
        "account": account,
        "candidates": payload["candidates"],
        "market_context": payload["market_context"],
    }


def _validate_checkpoint(checkpoint, replay, report):
    required = ("profile.json", "snapshot.json", "runs.jsonl")
    if not all((checkpoint / name).is_file() for name in required):
        if (
            any((checkpoint / name).exists() for name in required)
            or (checkpoint / "account").exists()
        ):
            raise ValueError("retained account checkpoint is incomplete")
        from .timing import verify_timing

        timing = verify_timing(checkpoint) if (checkpoint / "timing").exists() else None
        report["checks"]["recorded_cycles"] = {
            "status": "UNKNOWN",
            "reason": "No complete retained paper-account capture; timing observations alone contain no replayable strategy decision",
            "timing_integrity": timing,
        }
        return
    integrity = coordinator.verify(checkpoint)
    if integrity["recovery_required"]:
        raise ValueError(
            "source has a pending operation; preserve and recover it before validation"
        )
    report["checks"]["source_integrity"] = {"status": "PASS"}
    linked = integrity["timing"]["linked_evidence"]
    report["checks"]["timing_evidence"] = {
        "status": "PASS" if linked["complete"] else "UNKNOWN",
        "counts": linked["counts"],
        "reason": None if linked["complete"] else "Some timing claims remain unverified",
    }
    source_profile = read_json(checkpoint / "profile.json")
    replay_profile = dict(source_profile)
    replay_profile["execution_mode"] = "RECORDED_REPLAY_VALIDATION"
    profile_path = replay.parent / "replay-profile.json"
    atomic_json(profile_path, replay_profile)
    report["source_profile_sha256"] = digest(source_profile)
    report["replay_profile_sha256"] = digest(replay_profile)
    report["replay_profile_id"] = replay_profile["id"]
    receipts = [r for r in read_receipts(checkpoint) if r.get("status") == "COMPLETED"]
    if not receipts:
        report["checks"]["recorded_cycles"] = {
            "status": "UNKNOWN",
            "reason": "No completed run receipts",
        }
        return
    compared = []
    evidence = (
        checkpoint / "evidence" if source_profile["evidence_type"] == "public_market" else None
    )
    for receipt in receipts:
        original = coordinator._read_cycle(checkpoint, receipt["run_id"])
        source = checkpoint / "inputs" / (receipt["input_sha256"] + ".json")
        result = coordinator.run_once(replay, source, profile_path, receipt["as_of"], evidence)
        before, after = _economics(original), _economics(result)
        compared.append(
            {
                "source_run_id": receipt["run_id"],
                "replay_run_id": result["payload"]["run"]["id"],
                "as_of": receipt["as_of"],
                "status": "PASS" if before == after else "FAIL",
                "expected_sha256": digest(before),
                "actual_sha256": digest(after),
                "differing_sections": [key for key in before if before[key] != after[key]],
            }
        )
    report["checks"]["decision_replay"] = {
        "status": "PASS" if all(r["status"] == "PASS" for r in compared) else "FAIL",
        "ordering": "COMPLETED_RECEIPT_ORDER_WITH_RETAINED_INPUT_QUOTE_ORDER",
        "cycles": compared,
    }
    ledger = replay / "account" / "account.jsonl"
    before = ledger.read_bytes() if ledger.exists() else b""
    snapshot_before = (replay / "snapshot.json").read_bytes()
    # Reload from disk and retry every operation, including an older cycle after
    # the newest one. Account/receipt IDs must prevent additional economic writes.
    for receipt in reversed(receipts):
        coordinator.run_once(
            replay,
            checkpoint / "inputs" / (receipt["input_sha256"] + ".json"),
            profile_path,
            receipt["as_of"],
            evidence,
        )
    unchanged = before == (ledger.read_bytes() if ledger.exists() else b"")
    unchanged &= snapshot_before == (replay / "snapshot.json").read_bytes()
    coordinator.verify(replay)
    report["checks"]["restart_idempotency"] = {
        "status": "PASS" if unchanged else "FAIL",
        "cycles_retried": len(receipts),
        "account_journal_unchanged": unchanged,
    }
    report["source_evidence_type"] = source_profile["evidence_type"]


def validate_recorded_run(source_root, *, output_root=None):
    """Return PASS/FAIL/UNKNOWN; persist diagnostic copies only in a new root.

    A timing-only or empty collection returns UNKNOWN. An interrupted, corrupted
    or nonreproducible account returns FAIL. Concurrent source changes return
    UNKNOWN unless a failing check was already found. Synthetic inputs remain
    synthetic, and all replays accrue zero prospective trial days.
    """
    supplied = Path(source_root)
    if supplied.is_symlink() or not supplied.is_dir():
        raise ValueError("an existing ordinary source directory is required")
    source = supplied.resolve()
    if output_root is not None:
        output = Path(output_root).absolute()
        if output.exists() or output.is_symlink():
            raise ValueError("validation output must be a new directory")
        resolved = output.resolve()
        if resolved == source or source in resolved.parents or resolved in source.parents:
            raise ValueError("validation output must be outside the source tree")
        output.mkdir(parents=True, exist_ok=False)
        workspace = contextlib.nullcontext(str(output))
    else:
        workspace = tempfile.TemporaryDirectory(prefix="kod-recorded-validation-")
    report = {
        "schema_version": VERSION,
        "status": "UNKNOWN",
        "checks": {},
        "forward_trial_days": 0,
        "entry_permission": False,
        "network": False,
        "scope": "Retained evidence integrity, decision/economic replay, and restart idempotency; no profitability or real-fill validation",
    }
    with workspace as directory:
        destination = Path(directory)
        checkpoint, replay = destination / "checkpoint", destination / "replay"
        try:
            with _source_lock(source):
                before = _manifest(source, destination=checkpoint)
                if before != _manifest(source):
                    raise ValueError("source changed while copying the checkpoint")
            report["source_manifest_sha256"] = digest(before)
            report["source_files"] = len(before)
            checkpoint.mkdir(exist_ok=True)
            _validate_checkpoint(checkpoint, replay, report)
            with _source_lock(source):
                unchanged = before == _manifest(source)
            report["checks"]["source_unchanged"] = {
                "status": "PASS" if unchanged else "UNKNOWN",
                "reason": None
                if unchanged
                else "Source changed concurrently after the checkpoint was copied",
            }
        except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as exc:
            report["checks"]["validation_error"] = {
                "status": "FAIL",
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        statuses = [item["status"] for item in report["checks"].values()]
        report["status"] = (
            "FAIL"
            if "FAIL" in statuses
            else ("UNKNOWN" if not statuses or "UNKNOWN" in statuses else "PASS")
        )
        if output_root is not None:
            atomic_json(destination / "report.json", report)
    return report

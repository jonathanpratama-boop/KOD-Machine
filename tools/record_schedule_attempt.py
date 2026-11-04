#!/usr/bin/env python3
"""Record existing GitHub job timing into runner-temporary immutable receipts.

No scheduler, market request, credential access or trading operation is started.
A cron reference is an explicitly inferred daily slot, never GitHub's actual
scheduled timestamp. Only run ID, attempt and commit SHA are copied from the
environment. Wall-clock durations do not establish NTP accuracy or market timing.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = "KOD_SCHEDULE_RECEIPT_V1"
REPO = Path(__file__).resolve().parents[1]
EVENTS = {"schedule", "workflow_dispatch"}
COMPLETION_STATUSES = {"SUCCESS", "FAILURE", "CANCELLED", "SKIPPED", "TIMED_OUT", "UNKNOWN"}
MAX_BYTES = 65536


def now() -> datetime:
    return datetime.now(timezone.utc)


def _time(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-qualified actual observation required")
    return value.astimezone(timezone.utc)


def _stamp(value) -> str:
    return _time(value).isoformat().replace("+00:00", "Z")


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _identity(environment) -> dict:
    # Deliberate allowlist: never serialize the environment or exception values.
    run_id = environment.get("GITHUB_RUN_ID", "")
    attempt = environment.get("GITHUB_RUN_ATTEMPT", "")
    sha = environment.get("GITHUB_SHA", "")
    for name, value in (("GITHUB_RUN_ID", run_id), ("GITHUB_RUN_ATTEMPT", attempt)):
        if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", value):
            raise ValueError(name + " must be a positive numeric identifier")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("GITHUB_SHA must be a full commit hash")
    return {"run_id": run_id, "run_attempt": attempt, "commit_sha": sha.lower()}


def infer_slot(started_at, *, event: str, reference_utc: str) -> dict:
    """Infer the most recent daily reference only; multi-day delays are ambiguous."""
    if event not in EVENTS:
        raise ValueError("supported event is schedule or workflow_dispatch")
    if not isinstance(reference_utc, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", reference_utc):
        raise ValueError("reference UTC must be HH:MM")
    result = {"platform_scheduled_at": None, "reference_utc": reference_utc,
              "inferred_slot_at": None, "slot_basis": "UNKNOWN",
              "delay_from_inferred_slot_seconds": None}
    if event == "schedule":
        started = _time(started_at)
        hour, minute = (int(part) for part in reference_utc.split(":"))
        slot = started.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if slot > started:
            slot -= timedelta(days=1)
        result.update(inferred_slot_at=_stamp(slot), slot_basis="MOST_RECENT_UTC_CRON_SLOT",
                      delay_from_inferred_slot_seconds=(started - slot).total_seconds())
    return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate receipt JSON key")
        result[key] = value
    return result


def _read(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("schedule receipt must not be a symlink")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("schedule receipt exceeds size limit")
    value = json.loads(raw, object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite receipt JSON")))
    if not isinstance(value, dict):
        raise ValueError("invalid schedule receipt")
    body = {key: item for key, item in value.items() if key != "sha256"}
    if value.get("schema_version") != SCHEMA or _digest(body) != value.get("sha256"):
        raise ValueError("schedule receipt integrity failure")
    if raw != _canonical(value) + b"\n":
        raise ValueError("schedule receipt bytes changed")
    return value


def _publish(path: Path, body: dict) -> dict:
    value = dict(body, sha256=_digest(body))
    raw = _canonical(value) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".schedule-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic creation without replacing any existing receipt, including a
        # concurrently published one. The enclosing lock serializes our callers.
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)
    return value


def record_attempt(output, *, event: str, reference_utc: str, phase: str,
                   status: str | None = None, late_after_seconds: int = 300,
                   environment=None, clock=now) -> dict:
    """Freeze begin/completion independently; an exact retry retains its first clock."""
    identity = _identity(os.environ if environment is None else environment)
    observed = _time(clock())
    slot = infer_slot(observed, event=event, reference_utc=reference_utc)
    if phase not in {"begin", "complete"}:
        raise ValueError("phase must be begin or complete")
    status = (status or ("STARTED" if phase == "begin" else "UNKNOWN")).upper()
    if (phase == "begin" and status != "STARTED") or (phase == "complete" and status not in COMPLETION_STATUSES):
        raise ValueError("status is incompatible with the receipt phase")
    if type(late_after_seconds) is not int or late_after_seconds < 0:
        raise ValueError("late threshold must be nonnegative integer seconds")
    folder = Path(output).absolute()
    if folder.is_symlink() or folder.resolve().is_relative_to(REPO.resolve()):
        raise ValueError("schedule receipts belong outside the repository in runner temporary storage")
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"run-{identity['run_id']}-attempt-{identity['run_attempt']}"
    destination = folder / f"{stem}.{phase}.json"
    start_path = folder / f"{stem}.begin.json"
    lock_path = folder / ".schedule.lock"
    if lock_path.is_symlink():
        raise ValueError("schedule lock must not be a symlink")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        expected = {**identity, "event": event, "reference_utc": reference_utc,
                    "late_after_seconds": late_after_seconds, "phase": phase, "status": status}
        if destination.exists() or destination.is_symlink():
            saved = _read(destination)
            if any(saved.get(key) != value for key, value in expected.items()):
                raise ValueError("conflicting reuse of immutable schedule receipt")
            if _time(saved["recorded_at"]) > observed:
                raise ValueError("existing receipt is after the current observation clock")
            return saved
        warnings = ["UTC clock offset is unmeasured; local receipts are not independent timestamp proof."]
        body = {"schema_version": SCHEMA, **expected, "recorded_at": _stamp(observed),
                "started_at": None, "completed_at": None, "begin_sha256": None,
                "wall_elapsed_seconds": None, "signed_wall_elapsed_seconds": None,
                "clock_status": "OFFSET_UNKNOWN", "entry_permission": False,
                "market_coverage": "NOT_ESTABLISHED_BY_WORKFLOW_RECEIPT",
                "forward_trial": False, "warnings": warnings}
        if phase == "begin":
            body.update(slot, started_at=_stamp(observed))
            if event == "schedule":
                warnings.append("The most recent daily cron slot is inferred; delays spanning previous days cannot be identified here.")
            else:
                warnings.append("Manual dispatch has no inferred scheduled slot.")
        else:
            body["completed_at"] = _stamp(observed)
            if start_path.exists() or start_path.is_symlink():
                start = _read(start_path)
                for key in (*identity, "event", "reference_utc", "late_after_seconds"):
                    if start.get(key) != expected[key]:
                        raise ValueError("completion does not match its original begin receipt")
                body.update({key: start[key] for key in slot})
                body.update(started_at=start["started_at"], begin_sha256=start["sha256"])
                elapsed = (observed - _time(start["started_at"])).total_seconds()
                body["signed_wall_elapsed_seconds"] = elapsed
                if elapsed < 0:
                    body["clock_status"] = "WALL_CLOCK_REVERSED"
                    warnings.append("Completion clock precedes start; elapsed duration remains unknown.")
                else:
                    body["wall_elapsed_seconds"] = elapsed
                warnings.extend(item for item in start["warnings"] if item not in warnings)
            else:
                body.update(platform_scheduled_at=None, reference_utc=reference_utc,
                            inferred_slot_at=None, slot_basis="UNKNOWN",
                            delay_from_inferred_slot_seconds=None)
                warnings.append("BEGIN_RECEIPT_UNAVAILABLE: start, delay and duration are unknown.")
        lag = body["delay_from_inferred_slot_seconds"]
        body["overdue"] = None if lag is None else lag > late_after_seconds
        body["late_threshold_basis"] = "EXPLICIT_OPERATIONAL_THRESHOLD_NOT_PLATFORM_SLA"
        return _publish(destination, body)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="directory under runner temporary storage")
    parser.add_argument("--event", required=True, choices=sorted(EVENTS))
    parser.add_argument("--reference-utc", required=True, help="existing daily cron reference, HH:MM UTC")
    parser.add_argument("--phase", required=True, choices=("begin", "complete"))
    parser.add_argument("--status")
    parser.add_argument("--late-after-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        value = record_attempt(args.output, event=args.event, reference_utc=args.reference_utc,
                               phase=args.phase, status=args.status,
                               late_after_seconds=args.late_after_seconds)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Exception values can contain arbitrary environment/file text. Emit a
        # stable diagnostic class without copying credentials or raw payloads.
        print(json.dumps({"ok": False, "status": "RECEIPT_UNAVAILABLE", "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

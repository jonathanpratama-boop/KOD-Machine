"""Connect timing evidence to explicit operations without changing economic records.

The timing store is a sidecar: existing account IDs, frozen labels and cycle
hashes retain their meaning. A processing observation is not a historical fill.
No import, report read, or context preparation performs a network request.
"""

from __future__ import annotations

import copy
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..timing_capture import append_attempt, make_attempt, read_attempts, summarize
from ..timing_capture import verify as verify_attempts
from .chrony import CHRONY_COMMAND, CHRONY_TRACKING_CSV_V2, read_tracking_v2
from .data import parse_time, utc_text
from .storage import atomic_json, digest, immutable_json, locked, read_json

BOARD_SCHEMA = "KOD_TIMING_BOARD_V1"
CONTEXT_SCHEMA = "KOD_TIMING_CONTEXT_RECORD_V1"


def now():
    return utc_text(datetime.now(timezone.utc))


def clock_observation(root, *, clock=now, runner=subprocess.run):
    """Read an installed chrony clock measurement; never start a time service.

    Absence of chrony is UNKNOWN, not a zero offset. The raw local observation is
    retained with the parser version that reads it (CHRONY_TRACKING_CSV_V2); the
    attempt keeps the four-field clock shape of the frozen v1 attempt schema.
    Exchange server time is a different clock and is never called NTP.
    """
    at = clock()
    result = {"status": "UNKNOWN", "offset_seconds": None, "observed_at": at, "evidence_id": None}
    executable = shutil.which("chronyc")
    if executable is None:
        return result
    try:
        process = runner(
            [executable, "-c", "tracking"], capture_output=True, text=True, timeout=2, check=False
        )
        evidence = {
            "observed_at": clock(),
            "command": CHRONY_COMMAND,
            "parser_version": CHRONY_TRACKING_CSV_V2,
            "returncode": process.returncode,
            "stdout": process.stdout[:16384],
            "stderr": process.stderr[:16384],
        }
        identity = "clock_" + digest(evidence)
        with locked(root):
            immutable_json(Path(root) / "timing" / "clocks" / (identity + ".json"), evidence)
    except (OSError, subprocess.SubprocessError, ValueError):
        result.update(status="MEASUREMENT_FAILED", observed_at=clock())
        return result
    # The retained (bounded) text is parsed, so verification can repeat this exactly.
    reading = read_tracking_v2(evidence["returncode"], evidence["stdout"])
    return {
        "status": reading["status"],
        "offset_seconds": reading["offset_seconds"],
        "observed_at": evidence["observed_at"],
        "evidence_id": identity,
    }


class Attempt:
    """One invocation, including retries and interruptions, with measured stages."""

    def __init__(
        self,
        root,
        *,
        detector,
        source,
        kind,
        members,
        scheduled_at=None,
        links=None,
        clock=now,
        monotonic_ns=time.monotonic_ns,
        started_at=None,
        started_ns=None,
    ):
        self.root = Path(root)
        self.clock = clock
        self.monotonic_ns = monotonic_ns
        self.tick = monotonic_ns() if started_ns is None else started_ns
        started = clock() if started_at is None else utc_text(parse_time(started_at))
        if scheduled_at is not None:
            scheduled_at = utc_text(parse_time(scheduled_at))
            if parse_time(scheduled_at) > parse_time(started):
                raise ValueError("scheduled attempt cannot begin before its declared time")
        identifier = "attempt_" + uuid4().hex
        membership = {
            "schema_version": "KOD_TIMING_MEMBERSHIP_V1",
            "id": identifier,
            "recorded_at": started,
            "members": list(members),
            "coverage": "REQUESTED_MEMBERSHIP_ONLY",
            "entry_permission": False,
        }
        member_id = "membership_" + digest(membership)
        with locked(root):
            immutable_json(self.root / "timing" / "memberships" / (member_id + ".json"), membership)
        self.record = make_attempt(
            identifier,
            detector_version=detector,
            universe_snapshot_id=member_id,
            evidence_id=identifier,
            evidence_kind=kind,
            recorded_at=started,
            status="STARTED",
            source=source,
            times={"scheduled_at": scheduled_at, "started_at": started},
            links=links,
        )
        append_attempt(root, self.record)
        # Record STARTED first so a clock probe crash cannot erase the attempt.
        self.record["clock"] = clock_observation(root, clock=clock)
        self.extras = {}
        self._finished = None
        self._finish_request = None

    def mark(self, stage, *, at=None):
        value = at or self.clock()
        if self.record.get(stage) is not None and self.record[stage] != value:
            raise ValueError("timing stage already observed: " + stage)
        self.record[stage] = value
        return value

    def finish(self, status, *, reason=None, links=None):
        request = {"status": status, "reason": reason, "links": links or {}}
        if self._finished is not None:
            if request != self._finish_request:
                raise ValueError("conflicting timing completion retry")
            publish_board(self.root)
            return self._finished
        completed = copy.deepcopy(self.record)
        completed["recorded_at"] = self.clock()
        completed["status"] = status
        completed["reason"] = reason
        completed["links"].update(links or {})
        completed["durations_ns"]["invocation"] = self.monotonic_ns() - self.tick
        result = append_attempt(self.root, completed)
        self.record, self._finished, self._finish_request = completed, result, request
        publish_board(self.root)
        return result


def processing_attempt(
    root,
    snapshot_path,
    *,
    scheduled_at=None,
    captured=False,
    clock=now,
    monotonic_ns=time.monotonic_ns,
):
    """Observe reading a retained input now, preserving its old source cutoff."""
    started_ns, started_at = monotonic_ns(), clock()
    members, kind, links = [], "recorded", {}
    received_at = None
    try:
        snapshot = read_json(snapshot_path)
        received_at = clock()
        links = {"input_sha256": digest(snapshot)}
        if not isinstance(snapshot, dict):
            raise ValueError("recorded snapshot must be an object")
        members = [
            r.get("venue", "UNKNOWN") + ":" + r["symbol"]
            for r in snapshot.get("instruments", [])
            if isinstance(r, dict) and isinstance(r.get("symbol"), str)
        ]
        kind = (
            "synthetic"
            if snapshot.get("evidence_kind") == "synthetic"
            else "prospective"
            if captured
            else "recorded"
        )
        links["original_capture_at"] = snapshot.get("captured_at")
    except (OSError, ValueError, KeyError, TypeError):
        # The normal runtime validator still raises its original precise error.
        pass
    attempt = Attempt(
        root,
        detector="KOD_RUNTIME_PROCESSING_V1",
        source="RETAINED_INPUT_READ",
        kind=kind,
        members=members,
        scheduled_at=scheduled_at,
        links=links,
        clock=clock,
        monotonic_ns=monotonic_ns,
        started_at=started_at,
        started_ns=started_ns,
    )
    if received_at is not None:
        attempt.mark("received_at", at=received_at)
    return attempt


def _context_records(root, as_of):
    records = []
    directory = Path(root) / "timing" / "contexts"
    for path in sorted(directory.glob("*.json")):
        envelope = read_json(path)
        if (
            envelope.get("schema_version") != CONTEXT_SCHEMA
            or digest(envelope.get("payload")) != envelope.get("sha256")
            or path.stem != envelope["sha256"]
        ):
            raise ValueError("timing context integrity failure")
        if parse_time(envelope["payload"]["recorded_at"]) <= parse_time(as_of):
            records.append(envelope["payload"])
    return records


def publish_board(root, *, as_of=None):
    """Rebuild a replaceable view from verified immutable observations."""
    root = Path(root)
    with locked(root):
        cutoff = as_of or now()
        rows = read_attempts(root, as_of=cutoff)
        integrity = verify_timing(root, rows=rows)
        contexts = _context_records(root, cutoff)
        payload = {
            "as_of": cutoff,
            "summary": summarize(rows, as_of=cutoff),
            "attempts": rows,
            "integrity": integrity,
            "calendar": [r["context"].get("calendar", {}) for r in contexts],
            "shadow": [s for r in contexts for s in r["context"].get("shadow", [])],
            "contexts": contexts,
            "entry_permission": False,
            "clock": rows[-1]["clock"]
            if rows
            else {
                "status": "UNKNOWN",
                "offset_seconds": None,
                "observed_at": None,
                "evidence_id": None,
            },
        }
        envelope = {"schema_version": BOARD_SCHEMA, "payload": payload, "sha256": digest(payload)}
        existing = root / "timing" / "report.json"
        if existing.exists() and parse_time(read_json(existing)["payload"]["as_of"]) > parse_time(
            cutoff
        ):
            return envelope  # Historical projection cannot replace the latest board.
        atomic_json(existing, envelope)
        return envelope


def timing_status(root, *, as_of=None):
    """Read originals; never write a projection or perform collection."""
    cutoff = as_of or now()
    rows = read_attempts(root, as_of=cutoff)
    return {
        "integrity": verify_timing(root, rows=rows),
        "summary": summarize(rows, as_of=cutoff),
        "contexts": _context_records(root, cutoff),
        "entry_permission": False,
    }


def verify_timing(root, *, rows=None):
    from .timing_evidence import verify_linked_evidence

    chain = verify_attempts(root)
    evidence = verify_linked_evidence(root, read_attempts(root) if rows is None else rows)
    if not evidence["ok"]:
        raise ValueError(
            "timing linked evidence failed: "
            + "; ".join(p["reason"] for p in evidence["problems"][:3])
        )
    return {**chain, "linked_evidence": evidence}


def retain_context(root, payload, *, as_of, clock=now, evidence_kind="recorded"):
    from ..timing_context import build_timing_context

    recorded = clock()
    if parse_time(as_of) > parse_time(recorded):
        raise ValueError("context cutoff is in the future")
    context = build_timing_context(payload, as_of=as_of)
    if evidence_kind not in {"recorded", "synthetic"}:
        raise ValueError("imported context cannot self-certify prospective availability")
    attempt = Attempt(
        root,
        detector="CONTEXT_PREPARATION_V1",
        source="RETAINED_CONTEXT_INPUT",
        kind=evidence_kind,
        members=[e["id"] for e in payload.get("calendar_events", [])],
        clock=clock,
    )
    body = {
        "recorded_at": recorded,
        "as_of": utc_text(parse_time(as_of)),
        "input": copy.deepcopy(payload),
        "input_sha256": digest(payload),
        "context": context,
    }
    identifier = digest(body)
    with locked(root):
        immutable_json(
            Path(root) / "timing" / "contexts" / (identifier + ".json"),
            {"schema_version": CONTEXT_SCHEMA, "payload": body, "sha256": identifier},
        )
    attempt.finish(
        "COMPLETED",
        links={"context_id": identifier},
        reason="Context declarations validated; original source verification remains separate.",
    )
    return {
        "id": identifier,
        "context": context,
        "recorded_at": recorded,
        "entry_permission": False,
    }


def capture_intraday(
    root,
    *,
    scheduled_at,
    symbols,
    interval="1m",
    bars=60,
    fetcher=None,
    clock=now,
    monotonic_ns=time.monotonic_ns,
    evidence_kind="public_market",
):
    from .intraday import collect_intraday

    attempt = Attempt(
        root,
        detector="INTRADAY_OBSERVATION_V1",
        source="BINANCE_SPOT_PUBLIC",
        kind="synthetic" if evidence_kind == "synthetic" else "prospective",
        members=symbols,
        scheduled_at=scheduled_at,
        clock=clock,
        monotonic_ns=monotonic_ns,
    )
    output = Path(root) / "timing" / "captures" / (attempt.record["id"] + ".json")
    try:
        captured = collect_intraday(
            output,
            Path(root) / "evidence",
            symbols,
            scheduled_at=scheduled_at,
            interval=interval,
            bars=bars,
            fetcher=fetcher,
            clock=clock,
            monotonic_ns=monotonic_ns,
            evidence_kind=evidence_kind,
        )
        requests = captured.get("requests", [])
        receipts = [r["received_at"] for r in requests if r.get("received_at")]
        if receipts:
            attempt.mark("received_at", at=max(receipts, key=parse_time))
        attempt.mark("features_ready_at", at=captured["completed_at"])
        links = {
            "capture_sha256": captured["capture_sha256"],
            "capture_path": str(output.relative_to(Path(root))),
            "capture_membership_id": captured["membership_snapshot_id"],
        }
        status = {"COLLECTED": "COMPLETED", "PARTIAL": "PARTIAL", "BLOCKED": "BLOCKED"}[
            captured["status"]
        ]
        # Separate request-level cohorts make source lag and failed requests visible.
        for index, request in enumerate(requests):
            request_id = attempt.record["id"] + ":request:" + str(index)
            row = make_attempt(
                request_id,
                detector_version="SOURCE_REQUEST_V1",
                universe_snapshot_id=attempt.record["universe_snapshot_id"],
                evidence_id=request.get("evidence_id") or request_id,
                evidence_kind=attempt.record["evidence_kind"],
                recorded_at=captured["completed_at"],
                status=(
                    "COMPLETED"
                    if request.get("status") == "RECEIVED" and not request.get("validation_status")
                    else "BLOCKED"
                    if request.get("status") == "BLOCKED"
                    else "FAILED"
                ),
                source=request.get("endpoint", "BINANCE_SPOT_PUBLIC"),
                times={
                    "started_at": request.get("request_started_at"),
                    "received_at": request.get("received_at"),
                },
                source_time=None
                if request.get("source_time_status") == "EXCHANGE_CLOCK_SAMPLE"
                else request.get("source_time"),
                links={
                    "parent_attempt_id": attempt.record["id"],
                    "source_clock_basis": request.get("source_time_status"),
                },
                durations_ns={"request": request.get("elapsed_ns")},
            )
            append_attempt(root, row)
        attempt.finish(
            status,
            links=links,
            reason="Observation only; no detector was run and no entry permission was granted.",
        )
        publish_board(root, as_of=clock())
        return {"attempt_id": attempt.record["id"], "capture": captured, "entry_permission": False}
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        if attempt.record["status"] == "STARTED":
            attempt.finish("FAILED", reason=type(exc).__name__)
        raise


def record_missed(root, *, scheduled_at, members, reason):
    """An explicit missed slot remains visible; no missing market scan is invented."""
    attempt = Attempt(
        root,
        detector="SCHEDULED_OBSERVATION_V1",
        source="SCHEDULE_RECEIPT",
        kind="prospective",
        members=members,
        scheduled_at=scheduled_at,
    )
    attempt.finish("FAILED", reason=reason)
    return attempt.record

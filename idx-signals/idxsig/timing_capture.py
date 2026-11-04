"""Linked, append-only timing observations for explicit paper research runs.

This module performs no network request, places no order and grants no entry
permission. Wall-clock timestamps, process-local durations, source clocks and
external timestamp evidence remain separate. Missing observations stay unknown.
"""

from __future__ import annotations

import copy
import json
import math
import os
import statistics
from collections import Counter
from contextlib import nullcontext
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .runtime.data import parse_time, utc_text
from .runtime.storage import canonical, digest, immutable_json, locked

SCHEMA = "KOD_TIMING_ATTEMPT_V1"
JOURNAL_SCHEMA = "KOD_TIMING_JOURNAL_V1"
REPORT_SCHEMA = "KOD_TIMING_CAPTURE_REPORT_V1"
TIME_FIELDS = (
    "scheduled_at",
    "started_at",
    "published_at",
    "received_at",
    "features_ready_at",
    "detected_at",
    "decision_at",
    "executable_at",
    "fill_at",
)
LOCAL_STAGES = (
    "started_at",
    "received_at",
    "features_ready_at",
    "detected_at",
    "decision_at",
    "executable_at",
    "fill_at",
)
STATUSES = {
    "STARTED",
    "COMPLETED",
    "PARTIAL",
    "FAILED",
    "BLOCKED",
    "NO_TRIGGER",
    "DETECTED",
    "DECIDED",
    "NO_ACTION",
    "REJECTED",
    "EXPIRED",
    "FILLED",
    "UNKNOWN",
}
KINDS = {"synthetic", "recorded", "prospective"}
IDENTITY_FIELDS = (
    "schema_version",
    "id",
    "detector_version",
    "universe_snapshot_id",
    "evidence_id",
    "evidence_kind",
    "source",
    "entry_permission",
)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n\0"):
        raise ValueError(f"{name}: nonempty single-line text required")
    return value


def _finite(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name}: finite number required")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name}: finite number required") from None
    if not number.is_finite() or (positive and number <= 0):
        raise ValueError(f"{name}: invalid number")
    return number


def _utc(value: Any, name: str) -> str | None:
    return None if value is None else utc_text(parse_time(value, name))


def make_attempt(
    identifier: str,
    *,
    detector_version: str,
    universe_snapshot_id: str,
    evidence_id: str,
    evidence_kind: str,
    recorded_at: str,
    status: str,
    source: str,
    times: dict | None = None,
    threshold: dict | None = None,
    clock: dict | None = None,
    links: dict | None = None,
    prices: dict | None = None,
    durations_ns: dict | None = None,
    external_timestamp: dict | None = None,
    source_time: str | None = None,
    reason: str | None = None,
) -> dict:
    """Create a normalized version-one record without observing or inventing time.

    ``recorded_at`` is the explicit observation cutoff. Monotonic measurements
    are durations only: absolute monotonic values cannot be compared across runs.
    A source timestamp may disagree with the local clock; the report exposes the
    disagreement instead of interpreting a negative lag as early information.
    """
    supplied = {} if times is None else times
    if not isinstance(supplied, dict) or set(supplied) - set(TIME_FIELDS):
        raise ValueError("unknown timing stage")
    return validate_attempt(
        {
            "schema_version": SCHEMA,
            "id": identifier,
            "detector_version": detector_version,
            "universe_snapshot_id": universe_snapshot_id,
            "evidence_id": evidence_id,
            "evidence_kind": evidence_kind,
            "recorded_at": recorded_at,
            "status": status,
            "source": source,
            "entry_permission": False,
            **{key: supplied.get(key) for key in TIME_FIELDS},
            "source_time": source_time,
            "threshold": threshold
            if threshold is not None
            else {"at": None, "basis": "UNKNOWN", "evidence_id": None, "reference_at": None},
            "clock": clock
            if clock is not None
            else {
                "status": "UNKNOWN",
                "offset_seconds": None,
                "observed_at": None,
                "evidence_id": None,
            },
            "durations_ns": {} if durations_ns is None else durations_ns,
            "links": {} if links is None else links,
            "prices": {} if prices is None else prices,
            "external_timestamp": external_timestamp
            if external_timestamp is not None
            else {"status": "NOT_REQUESTED"},
            "reason": reason,
        }
    )


def validate_attempt(value: dict) -> dict:
    """Validate and copy a record. Existing records are never modified in place."""
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA:
        raise ValueError("unsupported timing attempt schema")
    row = copy.deepcopy(value)
    expected = (
        set(IDENTITY_FIELDS)
        | set(TIME_FIELDS)
        | {
            "recorded_at",
            "status",
            "source_time",
            "threshold",
            "clock",
            "durations_ns",
            "links",
            "prices",
            "external_timestamp",
            "reason",
        }
    )
    if set(row) != expected:
        raise ValueError("timing attempt fields differ from version-one schema")
    for key in IDENTITY_FIELDS:
        if key != "entry_permission":
            _text(row.get(key), key)
    if row["entry_permission"] is not False:
        raise ValueError("timing observations cannot grant entry permission")
    if row["evidence_kind"] not in KINDS or row["status"] not in STATUSES:
        raise ValueError("unsupported timing kind or status")
    cutoff = parse_time(row["recorded_at"], "recorded_at")
    row["recorded_at"] = utc_text(cutoff)
    for key in TIME_FIELDS:
        row[key] = _utc(row[key], key)
        if row[key] is not None and parse_time(row[key]) > cutoff:
            raise ValueError(f"{key}: observation is after recorded_at")
    required_stage = {"FILLED": "fill_at", "DECIDED": "decision_at", "DETECTED": "detected_at"}.get(
        row["status"]
    )
    if required_stage is not None and row[required_stage] is None:
        raise ValueError(f"{row['status']} requires an observed {required_stage}")
    # Publication and schedule are distinct clocks. Their signed lag is reported
    # separately; known local processing stages must remain causally ordered.
    # Recorded evidence can predate the start of a replay. Processing after
    # receipt remains causal, while run start must precede processing stages.
    local = [parse_time(row[key]) for key in LOCAL_STAGES[1:] if row[key] is not None]
    if local != sorted(local):
        raise ValueError("reversed local timing chronology")
    if row["started_at"] and any(
        row[key] and parse_time(row[key]) < parse_time(row["started_at"])
        for key in LOCAL_STAGES[2:]
    ):
        raise ValueError("processing stage precedes attempt start")
    row["source_time"] = _utc(row["source_time"], "source_time")
    threshold = row["threshold"]
    if not isinstance(threshold, dict) or set(threshold) != {
        "at",
        "basis",
        "evidence_id",
        "reference_at",
    }:
        raise ValueError("threshold requires at, basis, evidence_id and reference_at")
    if threshold["basis"] not in {"UNKNOWN", "COMPLETED_BAR", "QUOTE"}:
        raise ValueError("unsupported threshold observation basis")
    for key in ("at", "reference_at"):
        threshold[key] = _utc(threshold[key], "threshold." + key)
        if threshold[key] and parse_time(threshold[key]) > cutoff:
            raise ValueError("future threshold evidence")
    if threshold["at"] is None:
        if threshold["basis"] != "UNKNOWN" or threshold["evidence_id"] is not None:
            raise ValueError("unknown threshold must not claim an observation")
    else:
        if threshold["basis"] == "UNKNOWN":
            raise ValueError("observed threshold requires a basis")
        _text(threshold["evidence_id"], "threshold.evidence_id")
        at = parse_time(threshold["at"])
        if threshold["reference_at"] and parse_time(threshold["reference_at"]) > at:
            raise ValueError("threshold precedes its reference")
        if row["detected_at"] and at > parse_time(row["detected_at"]):
            raise ValueError("threshold evidence is after detection")
    clock = row["clock"]
    if not isinstance(clock, dict) or set(clock) != {
        "status",
        "offset_seconds",
        "observed_at",
        "evidence_id",
    }:
        raise ValueError("clock requires explicit status, offset, time and evidence")
    if clock["status"] not in {"UNKNOWN", "MEASURED_EXTERNAL", "MEASUREMENT_FAILED"}:
        raise ValueError("unsupported clock status")
    clock["observed_at"] = _utc(clock["observed_at"], "clock.observed_at")
    if clock["evidence_id"] is not None:
        _text(clock["evidence_id"], "clock.evidence_id")
    if clock["observed_at"] and parse_time(clock["observed_at"]) > cutoff:
        raise ValueError("future clock measurement")
    if clock["status"] == "MEASURED_EXTERNAL":
        clock["offset_seconds"] = str(_finite(clock["offset_seconds"], "clock.offset_seconds"))
        _text(clock["evidence_id"], "clock.evidence_id")
        if clock["observed_at"] is None:
            raise ValueError("measured clock requires measurement time")
    elif clock["offset_seconds"] is not None:
        raise ValueError("unknown clock offset must remain null")
    durations = row["durations_ns"]
    if not isinstance(durations, dict):
        raise ValueError("durations_ns must be an object")
    for name, duration in durations.items():
        _text(name, "duration name")
        if duration is not None and (type(duration) is not int or duration < 0):
            raise ValueError("monotonic durations must be nonnegative integer nanoseconds")
    if not isinstance(row["links"], dict):
        raise ValueError("links must be an object")
    for name, identity in row["links"].items():
        _text(name, "link name")
        if identity is not None:
            _text(identity, "linked identity")
    if not isinstance(row["prices"], dict):
        raise ValueError("prices must be an object")
    for stage, quote in row["prices"].items():
        if (
            stage not in TIME_FIELDS
            or not isinstance(quote, dict)
            or set(quote)
            != {
                "price",
                "venue",
                "symbol",
                "currency",
                "evidence_id",
                "observed_at",
            }
        ):
            raise ValueError(
                "stage price requires exact price, identity, evidence and observation fields"
            )
        quote["price"] = str(_finite(quote["price"], "price", positive=True))
        for key in ("venue", "symbol", "currency", "evidence_id"):
            _text(quote[key], "price." + key)
        quote["observed_at"] = _utc(quote["observed_at"], "price.observed_at")
        if row[stage] is None or quote["observed_at"] is None:
            raise ValueError("price requires its observed stage time")
        if parse_time(quote["observed_at"]) > parse_time(row[stage]):
            raise ValueError("price was unavailable at its stage")
    stamp = row["external_timestamp"]
    if not isinstance(stamp, dict) or stamp.get("status") not in {
        "NOT_REQUESTED",
        "UNAVAILABLE",
        "PRESENT_UNVERIFIED",
    }:
        raise ValueError("external timestamp requires a truthful supported evidence status")
    if set(stamp) - {"status", "evidence_id", "token_sha256", "reason"}:
        raise ValueError("unknown external timestamp field")
    if stamp["status"] == "PRESENT_UNVERIFIED":
        _text(stamp.get("evidence_id"), "external_timestamp.evidence_id")
        sha = stamp.get("token_sha256")
        if (
            not isinstance(sha, str)
            or len(sha) != 64
            or any(c not in "0123456789abcdef" for c in sha)
        ):
            raise ValueError("external timestamp token sha256 required")
    elif stamp.get("token_sha256") is not None or stamp.get("evidence_id") is not None:
        raise ValueError("unavailable external timestamp cannot claim a token")
    if stamp.get("reason") is not None:
        _text(stamp["reason"], "external_timestamp.reason")
    if row["reason"] is not None:
        _text(row["reason"], "reason")
    canonical(row)
    return row


def _preserves(previous: Any, current: Any, path: str) -> None:
    """A revision may fill an unknown or add metadata, never change known facts."""
    if previous is None:
        return
    if isinstance(previous, dict) and isinstance(current, dict):
        for key, value in previous.items():
            if key not in current:
                raise ValueError(f"timing revision removes {path}.{key}")
            _preserves(value, current[key], f"{path}.{key}")
    elif previous != current:
        raise ValueError(f"timing revision rewrites {path}")


def _revision(previous: dict, current: dict) -> None:
    for key in IDENTITY_FIELDS:
        if previous[key] != current[key]:
            raise ValueError("timing attempt identity cannot change")
    if parse_time(current["recorded_at"]) < parse_time(previous["recorded_at"]):
        raise ValueError("timing revision backdates observation")
    for key in TIME_FIELDS + ("source_time", "links", "prices", "durations_ns"):
        _preserves(previous[key], current[key], key)
    for key in ("threshold", "clock", "external_timestamp"):
        initial = previous[key]
        unknown = {
            "threshold": initial.get("basis") == "UNKNOWN",
            "clock": initial.get("status") in {"UNKNOWN", "MEASUREMENT_FAILED"},
            "external_timestamp": initial.get("status") in {"NOT_REQUESTED", "UNAVAILABLE"},
        }[key]
        if unknown:
            marker = "basis" if key == "threshold" else "status"
            _preserves(
                {name: value for name, value in initial.items() if name != marker},
                current[key],
                key,
            )
        else:
            _preserves(initial, current[key], key)
    if (
        previous["status"] in {"FAILED", "REJECTED", "EXPIRED", "FILLED", "NO_TRIGGER"}
        and previous["status"] != current["status"]
    ):
        raise ValueError("terminal timing attempt requires a new attempt identity")
    if previous["status"] != "STARTED" and current["status"] == "STARTED":
        raise ValueError("timing attempt cannot regress to started")
    if previous["status"] != "UNKNOWN" and current["status"] == "UNKNOWN":
        raise ValueError("timing attempt cannot erase its known status")
    if previous["status"] in {"COMPLETED", "NO_ACTION", "BLOCKED"} and current["status"] not in {
        previous["status"],
        "FILLED",
    }:
        raise ValueError("completed timing attempt requires a new attempt identity")


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate timing journal key")
        result[key] = value
    return result


def _journal(root: str | Path) -> list[dict]:
    path = Path(root) / "timing" / "attempts.jsonl"
    if path.parent.is_symlink() or (path.parent / "records").is_symlink() or path.is_symlink():
        raise ValueError("timing journal must not be a symlink")
    if not path.exists():
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("torn timing journal; preserve and restore verified backup")
    records, latest, previous = [], {}, None
    for line in raw.splitlines():
        envelope = json.loads(
            line,
            object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite timing JSON")),
        )
        if not isinstance(envelope, dict):
            raise ValueError("invalid timing journal envelope")
        body = {key: value for key, value in envelope.items() if key != "record_hash"}
        if (
            envelope.get("schema_version") != JOURNAL_SCHEMA
            or type(envelope.get("sequence")) is not int
            or envelope.get("sequence") != len(records) + 1
            or envelope.get("prev_hash") != previous
            or digest(body) != envelope.get("record_hash")
        ):
            raise ValueError("timing journal integrity failure")
        row = validate_attempt(envelope.get("attempt"))
        prior = latest.get(row["id"])
        if type(envelope.get("version")) is not int or envelope.get("version") != (
            prior["version"] + 1 if prior else 1
        ):
            raise ValueError("timing revision sequence failure")
        if envelope.get("supersedes") != (prior["record_hash"] if prior else None):
            raise ValueError("timing revision parent failure")
        if prior:
            _revision(prior["attempt"], row)
        artifact = path.parent / "records" / (envelope["record_hash"] + ".json")
        if (
            artifact.is_symlink()
            or not artifact.exists()
            or artifact.read_bytes() != canonical(envelope) + b"\n"
        ):
            raise ValueError("timing immutable artifact missing or changed")
        latest[row["id"]] = envelope
        previous = envelope["record_hash"]
        records.append(envelope)
    return records


def append_attempt(root: str | Path, record: dict, *, _locked: bool = False) -> dict:
    """Append an immutable observation or an additive revision; retry is safe.

    Pass ``_locked=True`` only while already holding runtime.storage.locked(root).
    The immutable artifact is written first. A crash before journal publication
    leaves a harmless orphan that an identical retry reuses.
    """
    row = validate_attempt(record)
    root = Path(root)
    with nullcontext() if _locked else locked(root):
        records = _journal(root)
        prior = next((r for r in reversed(records) if r["attempt"]["id"] == row["id"]), None)
        if prior and canonical(prior["attempt"]) == canonical(row):
            return prior
        if prior:
            _revision(prior["attempt"], row)
        body = {
            "schema_version": JOURNAL_SCHEMA,
            "sequence": len(records) + 1,
            "version": prior["version"] + 1 if prior else 1,
            "supersedes": prior["record_hash"] if prior else None,
            "prev_hash": records[-1]["record_hash"] if records else None,
            "attempt": row,
        }
        envelope = dict(body, record_hash=digest(body))
        folder = root / "timing"
        artifact = folder / "records" / (envelope["record_hash"] + ".json")
        if artifact.is_symlink():
            raise ValueError("timing artifact must not be a symlink")
        if artifact.exists() and artifact.read_bytes() != canonical(envelope) + b"\n":
            raise ValueError("timing orphan artifact bytes changed")
        immutable_json(artifact, envelope)
        with (folder / "attempts.jsonl").open("ab") as stream:
            stream.write(canonical(envelope) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return envelope


def read_attempts(root: str | Path, *, as_of: str | None = None) -> list[dict]:
    """Read latest revisions available at cutoff; never expose later revisions."""
    cutoff = parse_time(as_of) if as_of is not None else None
    latest = {}
    for envelope in _journal(root):
        row = envelope["attempt"]
        if cutoff is None or parse_time(row["recorded_at"]) <= cutoff:
            latest[row["id"]] = row
    return list(latest.values())


def verify(root: str | Path) -> dict:
    records = _journal(root)
    return {
        "ok": True,
        "schema_version": JOURNAL_SCHEMA,
        "attempts": len({r["attempt"]["id"] for r in records}),
        "revisions": len(records),
        "head_hash": records[-1]["record_hash"] if records else None,
        "entry_permission": False,
        "external_verification": "LOCAL_HASH_CHAIN_ONLY",
    }


def _seconds(start: str | None, end: str | None) -> float | None:
    return (parse_time(end) - parse_time(start)).total_seconds() if start and end else None


def _statistics(values: list[float | None]) -> dict:
    known = sorted(v for v in values if v is not None)
    return {
        "known": len(known),
        "unknown": len(values) - len(known),
        "median_seconds": statistics.median(known) if known else None,
        "p95_seconds": known[max(0, math.ceil(len(known) * 0.95) - 1)] if known else None,
        "max_seconds": max(known) if known else None,
    }


def _details(row: dict) -> dict:
    threshold = row["threshold"]
    pairs = {
        "schedule_start": (row["scheduled_at"], row["started_at"]),
        "threshold": (threshold["reference_at"], threshold["at"]),
        "collection_after_threshold": (threshold["at"], row["received_at"]),
        "receipt_to_features": (row["received_at"], row["features_ready_at"]),
        "detection_processing": (row["received_at"], row["detected_at"]),
        "analyst": (row["detected_at"], row["decision_at"]),
        "execution_quote": (row["decision_at"], row["executable_at"]),
        "fill_after_quote": (row["executable_at"], row["fill_at"]),
        "source_to_receipt": (row["published_at"] or row["source_time"], row["received_at"]),
    }
    signed = {name: _seconds(*pair) for name, pair in pairs.items()}
    conflicts = [name for name, value in signed.items() if value is not None and value < 0]
    seconds = {
        name: (value if value is None or value >= 0 else None) for name, value in signed.items()
    }
    price_drift = {}
    for before, after in zip(LOCAL_STAGES, LOCAL_STAGES[1:]):
        first, second = row["prices"].get(before), row["prices"].get(after)
        comparable = (
            first and second and all(first[k] == second[k] for k in ("venue", "symbol", "currency"))
        )
        price_drift[f"{before}_to_{after}"] = (
            str(Decimal(second["price"]) / Decimal(first["price"]) - 1) if comparable else None
        )
    return {
        "id": row["id"],
        "status": row["status"],
        "seconds": seconds,
        "signed_clock_differences_seconds": signed,
        "clock_conflicts": conflicts,
        "monotonic_seconds": {
            k: value / 1_000_000_000 if value is not None else None
            for k, value in row["durations_ns"].items()
        },
        "price_drift_fraction": price_drift,
    }


def summarize(records: list[dict], *, as_of: str) -> dict:
    """Describe latest complete attempt records, separating evidence/detector cohorts.

    Coverage remains the producer's explicit retained scope. An event-to-receipt
    lag includes vendor delay and clock error; it is not a measured NTP offset.
    """
    cutoff = parse_time(as_of)
    if not isinstance(records, list):
        raise ValueError("timing records must be a list")
    rows = [validate_attempt(r) for r in records]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("summarize requires latest unique attempt records")
    if any(parse_time(r["recorded_at"]) > cutoff for r in rows):
        raise ValueError("timing record is after report cutoff")
    details = {r["id"]: _details(r) for r in rows}
    cohorts = []
    for kind, detector in sorted({(r["evidence_kind"], r["detector_version"]) for r in rows}):
        subset = [
            r for r in rows if (r["evidence_kind"], r["detector_version"]) == (kind, detector)
        ]
        keys = list(details[subset[0]["id"]]["seconds"])
        cohorts.append(
            {
                "evidence_kind": kind,
                "detector_version": detector,
                "attempts": len(subset),
                "statuses": dict(Counter(r["status"] for r in subset)),
                "stages": {
                    key: _statistics([details[r["id"]]["seconds"][key] for r in subset])
                    for key in keys
                },
            }
        )
    board = []
    for kind, source in sorted({(r["evidence_kind"], r["source"]) for r in rows}):
        subset = [r for r in rows if (r["evidence_kind"], r["source"]) == (kind, source)]
        values = [details[r["id"]]["seconds"]["source_to_receipt"] for r in subset]
        board.append(
            {
                "source": source,
                "evidence_kind": kind,
                "attempts": len(subset),
                "lag": _statistics(values),
                "clock_conflicts": sum(
                    "source_to_receipt" in details[r["id"]]["clock_conflicts"] for r in subset
                ),
                "failures": sum(r["status"] in {"FAILED", "BLOCKED"} for r in subset),
            }
        )
    return {
        "schema_version": REPORT_SCHEMA,
        "as_of": utc_text(cutoff),
        "status": "DESCRIPTIVE_ONLY",
        "entry_permission": False,
        "attempts": len(rows),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "missing_stages": {k: sum(r[k] is None for r in rows) for k in TIME_FIELDS},
        "clock_statuses": dict(Counter(r["clock"]["status"] for r in rows)),
        "external_timestamp_statuses": dict(
            Counter(r["external_timestamp"]["status"] for r in rows)
        ),
        "cohorts": cohorts,
        "source_latency": board,
        "records": list(details.values()),
        "limitations": [
            "All retained attempts are counted; collection scope must be established by producer receipts.",
            "Unknown timestamps remain null; negative cross-clock differences are conflicts, not lead time.",
            "Stage durations overlap and must not be summed as independent causes.",
            "Monotonic durations are process-local measurements, independent of wall-clock offset.",
            "Local hashes and supplied timestamp metadata do not independently prove prospective availability.",
            "Descriptive latency and price drift do not establish executable returns or a trading edge.",
        ],
    }


def from_legacy(record: dict, *, recorded_at: str, source: str = "LEGACY_TIMING_INPUT") -> dict:
    """Adapt a legacy diagnostic row in memory; retain its original bytes elsewhere."""
    return make_attempt(
        record["id"],
        detector_version=record["detector_version"],
        universe_snapshot_id=record["universe_snapshot_id"],
        evidence_id=record["evidence_id"],
        evidence_kind=record["evidence_kind"],
        recorded_at=recorded_at,
        status="UNKNOWN",
        source=source,
        times={k: record.get(k) for k in TIME_FIELDS},
        reason="Legacy diagnostic import; no missing status or threshold was inferred.",
    )


def legacy_records(records: list[dict]) -> list[dict]:
    """Export only original diagnostic fields for callers that retain its API."""
    from .timing_research import STAGES

    return [
        {
            key: row[key]
            for key in (
                "id",
                "detector_version",
                "universe_snapshot_id",
                "evidence_id",
                "evidence_kind",
                *STAGES,
            )
        }
        for row in (validate_attempt(r) for r in records)
    ]

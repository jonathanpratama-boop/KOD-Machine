"""Read-only operational views over the runtime's atomic snapshot.

The runner owns collection, candidate decisions and the paper account.  This
adapter only validates and presents its output; viewing a page never runs a
scanner, places an order, changes a policy or writes into an account ledger.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "KOD_RUNTIME_SNAPSHOT_V1"
MAX_BYTES = 16 * 1024 * 1024
DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "kod"
SECTIONS = ("run", "health", "candidates", "market_context", "account", "experiments")
TIMING_SCHEMA = "KOD_TIMING_BOARD_V1"
TIMING_STAGES = (
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


class OperationsUnavailable(ValueError):
    """The current runtime cannot support a reliable operational view."""


def canonical(payload: dict) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise OperationsUnavailable("The runtime snapshot contains a duplicate JSON key.")
        result[key] = value
    return result


def _nonfinite(value):
    raise OperationsUnavailable("The runtime snapshot contains a non-finite number.")


def _records(value, section, *, identities=False):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise OperationsUnavailable(f"The runtime {section} must be a list of records.")
    if identities:
        ids = [row.get("id") for row in value]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise OperationsUnavailable(f"The runtime {section} needs unique non-empty record IDs.")


def _validate(payload):
    if not isinstance(payload, dict) or any(key not in payload for key in SECTIONS):
        raise OperationsUnavailable("The runtime snapshot is missing a required section.")
    for key in ("run", "market_context", "account"):
        if not isinstance(payload[key], dict):
            raise OperationsUnavailable(f"The runtime {key} must be an object.")
    if not isinstance(payload["health"], (dict, list)):
        raise OperationsUnavailable("The runtime health must be an object or a list of records.")
    if isinstance(payload["health"], list):
        _records(payload["health"], "health")
    _records(payload["candidates"], "candidates", identities=True)
    _records(payload["experiments"], "experiments", identities=True)
    for row in payload["candidates"]:
        for key in ("reasons", "blockers"):
            if row.get(key) is not None and not isinstance(row[key], list):
                raise OperationsUnavailable(f"Candidate {key} must be a list.")
        if row.get("plan") is not None and not isinstance(row["plan"], dict):
            raise OperationsUnavailable("A candidate plan must be an object or null.")
    groups = payload["market_context"].get("groups", [])
    _records(groups, "market groups", identities=True)
    for group in groups:
        if group.get("member_ids") is not None and not isinstance(group["member_ids"], list):
            raise OperationsUnavailable("Market group members must be a list.")
    for key in ("positions", "orders", "fills"):
        if payload["account"].get(key) is not None:
            _records(payload["account"][key], f"account {key}")


class OperationsArchive:
    """Read and verify a fresh immutable projection for each request."""

    def __init__(self, root: Path | str | None = None):
        configured = root if root is not None else os.environ.get("KOD_RUNTIME_ROOT")
        self.root = Path(configured).expanduser() if configured else DEFAULT_ROOT

    def last_attempt(self):
        """Display operational failure separately from the last verified snapshot."""
        path = self.root / "last_attempt.json"
        if not path.exists():
            return None
        try:
            if path.is_symlink() or path.stat().st_size > 65536:
                raise ValueError("unsupported attempt record")
            value = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_pairs,
                parse_constant=_nonfinite,
            )
            if not isinstance(value, dict) or value.get("status") not in {"FAILED", "COMPLETED"}:
                raise ValueError("invalid attempt status")
            return value
        except (OSError, UnicodeError, ValueError, RecursionError):
            return {
                "status": "UNREADABLE",
                "error": "The latest attempt record could not be read; current run health is unknown.",
            }

    def snapshot(self) -> dict:
        path = self.root / "snapshot.json"
        try:
            if path.is_symlink() or not path.is_file():
                raise OperationsUnavailable(
                    "No runtime snapshot is available. Run an explicit KOD cycle to create one."
                )
            with path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise OperationsUnavailable("The runtime snapshot exceeds the supported size.")
            envelope = json.loads(
                raw.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_nonfinite
            )
        except OperationsUnavailable:
            raise
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            raise OperationsUnavailable("The runtime snapshot is unreadable or malformed.") from exc
        if not isinstance(envelope, dict) or envelope.get("schema_version") != SCHEMA:
            raise OperationsUnavailable("The runtime snapshot uses an unsupported schema.")
        payload = envelope.get("payload")
        digest = envelope.get("sha256")
        try:
            computed = hashlib.sha256(canonical(payload)).hexdigest()
        except (TypeError, ValueError, RecursionError) as exc:
            raise OperationsUnavailable("The runtime snapshot payload cannot be verified.") from exc
        if not isinstance(digest, str) or not hmac.compare_digest(computed, digest):
            raise OperationsUnavailable("The runtime snapshot failed its integrity check.")
        _validate(payload)
        return {
            "payload": payload,
            "sha256": computed,
            "schema_version": SCHEMA,
            "last_attempt": self.last_attempt(),
        }


def _timing_time(value, name):
    if not isinstance(value, str):
        raise OperationsUnavailable(f"Timing {name} requires a timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise OperationsUnavailable(f"Timing {name} requires an explicit timezone.") from exc


def _timing_count(value, name):
    if type(value) is not int or value < 0:
        raise OperationsUnavailable(f"Timing {name} must be a nonnegative count.")


def _timing_stats(value):
    if not isinstance(value, dict):
        raise OperationsUnavailable("Timing stage statistics must be an object.")
    for key in ("known", "unknown"):
        _timing_count(value.get(key), key)
    for key in ("median_seconds", "p95_seconds", "max_seconds"):
        number = value.get(key)
        if number is not None and (
            isinstance(number, bool) or not isinstance(number, (int, float)) or number < 0
        ):
            raise OperationsUnavailable("Timing delays must be nonnegative numbers or unknown.")


def _validate_timing(payload):
    if not isinstance(payload, dict):
        raise OperationsUnavailable("The timing board payload must be an object.")
    cutoff = _timing_time(payload.get("as_of"), "cutoff")
    for key in ("summary", "clock", "integrity"):
        if not isinstance(payload.get(key), dict):
            raise OperationsUnavailable(f"The timing {key} must be an object.")
    for key in ("attempts", "calendar", "shadow"):
        _records(payload.get(key), "timing " + key, identities=key == "attempts")
    for row in payload["calendar"]:
        if "events" in row:
            _records(row["events"], "timing calendar events")
    if "entry_permission" in payload and payload["entry_permission"] is not False:
        raise OperationsUnavailable("The timing board cannot grant entry permission.")
    summary = payload["summary"]
    if (
        summary.get("schema_version") != "KOD_TIMING_CAPTURE_REPORT_V1"
        or summary.get("entry_permission") is not False
    ):
        raise OperationsUnavailable("The timing summary has an unsupported research schema.")
    if _timing_time(summary.get("as_of"), "summary cutoff") != cutoff:
        raise OperationsUnavailable("The timing board and summary cutoffs disagree.")
    _timing_count(summary.get("attempts"), "attempts")
    if summary["attempts"] != len(payload["attempts"]):
        raise OperationsUnavailable(
            "The timing attempt denominator disagrees with the retained records."
        )
    for key in ("statuses", "missing_stages", "clock_statuses", "external_timestamp_statuses"):
        if not isinstance(summary.get(key), dict):
            raise OperationsUnavailable(f"The timing {key} must be an object.")
        for count in summary[key].values():
            _timing_count(count, key)
    for key in ("cohorts", "source_latency", "records"):
        _records(summary.get(key), "timing " + key, identities=key == "records")
    if {r["id"] for r in summary["records"]} != {r["id"] for r in payload["attempts"]}:
        raise OperationsUnavailable("The timing summary and attempt identities disagree.")
    for row in summary["cohorts"]:
        _timing_count(row.get("attempts"), "cohort attempts")
        if not isinstance(row.get("stages"), dict):
            raise OperationsUnavailable("Timing cohort stages must be an object.")
        for stats in row["stages"].values():
            _timing_stats(stats)
            if stats["known"] + stats["unknown"] != row["attempts"]:
                raise OperationsUnavailable("Timing stage denominator disagrees with its cohort.")
    for row in summary["source_latency"]:
        _timing_count(row.get("attempts"), "source attempts")
        _timing_stats(row.get("lag"))
    for row in payload["attempts"]:
        if (
            row.get("schema_version") != "KOD_TIMING_ATTEMPT_V1"
            or row.get("entry_permission") is not False
        ):
            raise OperationsUnavailable("The timing attempt has an unsupported research schema.")
        observed = _timing_time(row.get("recorded_at"), "recorded_at")
        if observed > cutoff:
            raise OperationsUnavailable("A timing observation is after the report cutoff.")
        for key in TIMING_STAGES:
            if row.get(key) is not None and _timing_time(row[key], key) > observed:
                raise OperationsUnavailable("A timing stage is after its observation cutoff.")
        for key in ("links", "threshold", "clock", "external_timestamp"):
            if not isinstance(row.get(key), dict):
                raise OperationsUnavailable(f"Timing attempt {key} must be an object.")
        if any(value is not None and not isinstance(value, str) for value in row["links"].values()):
            raise OperationsUnavailable("Timing links must contain identifiers or unknown values.")
        if (
            row["threshold"].get("at") is not None
            and _timing_time(row["threshold"]["at"], "threshold") > observed
        ):
            raise OperationsUnavailable("A threshold observation is after its record cutoff.")
        if row.get("evidence_kind") not in {"synthetic", "recorded", "prospective"}:
            raise OperationsUnavailable("Unknown timing evidence kind.")
    if (
        payload["integrity"].get("ok") is not True
        or payload["integrity"].get("entry_permission") is not False
    ):
        raise OperationsUnavailable("The timing producer did not report verified local integrity.")
    if "contexts" in payload:
        _records(payload["contexts"], "timing contexts")
        for item in payload["contexts"]:
            recorded = _timing_time(item.get("recorded_at"), "context recorded_at")
            if recorded > cutoff or _timing_time(item.get("as_of"), "context cutoff") > recorded:
                raise OperationsUnavailable("Timing context chronology disagrees with its report.")
            context = item.get("context")
            if not isinstance(context, dict) or not isinstance(context.get("calendar"), dict):
                raise OperationsUnavailable("Timing context results and calendar must be objects.")
            _records(context["calendar"].get("events", []), "calendar events")
            for key in ("shadow", "preparations", "avoid"):
                _records(context.get(key, []), "context " + key)


class TimingArchive(OperationsArchive):
    """Independent read-only timing sidecar; an account snapshot is not required."""

    def snapshot(self) -> dict:
        path = self.root / "timing" / "report.json"
        try:
            if path.parent.is_symlink() or path.is_symlink() or not path.is_file():
                raise OperationsUnavailable(
                    "No timing report is available. Run an explicit instrumented attempt to create one."
                )
            with path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise OperationsUnavailable("The timing report exceeds the supported size.")
            envelope = json.loads(
                raw.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_nonfinite
            )
            if not isinstance(envelope, dict) or envelope.get("schema_version") != TIMING_SCHEMA:
                raise OperationsUnavailable("The timing report uses an unsupported schema.")
            payload = envelope.get("payload")
            computed = hashlib.sha256(canonical(payload)).hexdigest()
            if not isinstance(envelope.get("sha256"), str) or not hmac.compare_digest(
                computed, envelope["sha256"]
            ):
                raise OperationsUnavailable("The timing report failed its integrity check.")
            _validate_timing(payload)
        except OperationsUnavailable:
            raise
        except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
            raise OperationsUnavailable("The timing report is unreadable or malformed.") from exc
        return {"payload": payload, "sha256": computed, "schema_version": TIMING_SCHEMA}


def timing_timeline(attempt):
    """Sort observed timestamps only; keep unknown stages explicit at the end."""
    stages = [{"name": key.replace("_", " "), "at": attempt.get(key)} for key in TIMING_STAGES]
    threshold = attempt.get("threshold", {})
    stages.append(
        {
            "name": "observable threshold (" + str(threshold.get("basis", "UNKNOWN")) + ")",
            "at": threshold.get("at"),
        }
    )
    known = sorted(
        (row for row in stages if row["at"] is not None),
        key=lambda row: _timing_time(row["at"], row["name"]),
    )
    return known + [row for row in stages if row["at"] is None]


def timing_context_views(payload):
    """Join context results to their retained evidence cohort and recording clock.

    A legacy flattened report cannot establish these joins. Its results remain
    visible with unknown provenance instead of inheriting another row's cohort.
    """
    contexts = payload.get("contexts")
    if contexts is None:
        calendar = []
        for row in payload["calendar"]:
            calendar.extend(row.get("events", [row]))
        if not calendar and not payload["shadow"]:
            return []
        return [
            {
                "id": "LEGACY_FLATTENED_CONTEXT",
                "evidence_kind": "UNKNOWN",
                "recorded_at": None,
                "as_of": None,
                "calendar": calendar,
                "preparations": [],
                "shadow": payload["shadow"],
                "avoid": [],
                "source_validation": "Context provenance is unavailable in this older projection.",
            }
        ]
    views = []
    for item in contexts:
        identity = hashlib.sha256(canonical(item)).hexdigest()
        kinds = {
            row["evidence_kind"]
            for row in payload["attempts"]
            if row["links"].get("context_id") == identity
            and row.get("detector_version") == "CONTEXT_PREPARATION_V1"
        }
        context = item["context"]
        views.append(
            {
                "id": identity,
                "evidence_kind": next(iter(kinds)) if len(kinds) == 1 else "UNKNOWN",
                "recorded_at": item["recorded_at"],
                "as_of": item["as_of"],
                "calendar": context["calendar"].get("events", []),
                "preparations": context.get("preparations", []),
                "shadow": context.get("shadow", []),
                "avoid": context.get("avoid", []),
                "source_validation": context.get(
                    "source_validation", "Source verification unknown."
                ),
            }
        )
    return sorted(
        views, key=lambda row: _timing_time(row["recorded_at"], "context record"), reverse=True
    )


def health_rows(health) -> list[dict]:
    """Normalize display only; no missing value is replaced with success or zero."""
    if isinstance(health, list):
        return health
    if isinstance(health.get("sources"), list):
        return [row for row in health["sources"] if isinstance(row, dict)]
    if isinstance(health.get("sources"), dict):
        return [
            {"name": name, **(value if isinstance(value, dict) else {"status": value})}
            for name, value in health["sources"].items()
        ]
    return [
        {"name": name, **value} for name, value in health.items() if isinstance(value, dict)
    ] or ([health] if health else [])


def brief(value) -> str:
    """Readable structured values without rendering trusted HTML or evaluating code."""
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return str(value)

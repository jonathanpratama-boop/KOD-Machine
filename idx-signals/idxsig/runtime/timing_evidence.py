"""Verify timing sidecar references, without fetching data or changing records.

A valid journal hash does not prove that its membership, clock, capture or context
objects still exist. Generated local identifiers therefore require their original
objects. External legacy identifiers remain declarations with explicit coverage.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import hashlib
from pathlib import Path, PurePosixPath
import re

from .data import parse_time
from .storage import canonical, digest, read_json

SCHEMA = "KOD_TIMING_LINKED_EVIDENCE_V1"
HEX = re.compile(r"[0-9a-f]{64}")


def _safe(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("invalid relative evidence path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts:
        raise ValueError("evidence path escapes runtime root")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("evidence symlinks are not original retained files")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("evidence path escapes runtime root")
    return path


def _object(root: Path, relative: str) -> dict:
    path = _safe(root, relative)
    value = read_json(path)
    if not isinstance(value, dict) or path.read_bytes() != canonical(value) + b"\n":
        raise ValueError("retained object bytes differ from canonical immutable encoding")
    return value


def _generated(value, prefix: str) -> bool:
    if not isinstance(value, str) or not value.startswith(prefix):
        return False
    if not HEX.fullmatch(value[len(prefix) :]):
        raise ValueError("malformed generated evidence identifier")
    return True


def verify_linked_evidence(root, rows: list[dict]) -> dict:
    """Return integrity and coverage for linked local objects and context packs.

    Missing generated artifacts make ``ok`` false. Missing optional independent
    timestamp verification remains UNAVAILABLE and makes ``complete`` false.
    Caller-declared legacy identities do not pretend to verify local artifacts.
    """
    root = Path(root).resolve()
    checks = []
    by_id = {row.get("id"): row for row in rows}
    memberships = {}
    captures = {}
    context_links = {}

    def result(kind, identifier, status, reason, *, attempt_id=None, required=True, **extra):
        checks.append(
            {
                "kind": kind,
                "id": identifier,
                "attempt_id": attempt_id,
                "status": status,
                "required": required,
                "reason": reason,
                **extra,
            }
        )

    def check(kind, identifier, callback, attempt_id=None):
        try:
            value = callback()
            result(
                kind,
                identifier,
                "VERIFIED",
                "original linked object verified",
                attempt_id=attempt_id,
            )
            return value
        except FileNotFoundError:
            result(
                kind,
                identifier,
                "UNAVAILABLE",
                "required original linked artifact is missing",
                attempt_id=attempt_id,
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            ArithmeticError,
            AttributeError,
            IndexError,
        ) as exc:
            result(kind, identifier, "FAIL", str(exc), attempt_id=attempt_id)
        return None

    for row in rows:
        identity = row.get("id")
        member_id = row.get("universe_snapshot_id")

        def membership():
            if not _generated(member_id, "membership_"):
                return None
            value = _object(root, f"timing/memberships/{member_id}.json")
            if (
                "membership_" + digest(value) != member_id
                or value.get("schema_version") != "KOD_TIMING_MEMBERSHIP_V1"
            ):
                raise ValueError("membership hash or schema mismatch")
            parent = row.get("links", {}).get("parent_attempt_id")
            owner = parent or identity
            if value.get("id") != owner or value.get("entry_permission") is not False:
                raise ValueError("membership is not tied to its owning attempt")
            if parent and (
                parent not in by_id or by_id[parent].get("universe_snapshot_id") != member_id
            ):
                raise ValueError("child membership lacks matching retained parent attempt")
            if (
                not isinstance(value.get("members"), list)
                or value.get("coverage") != "REQUESTED_MEMBERSHIP_ONLY"
            ):
                raise ValueError("unsupported membership contents")
            owner_row = by_id.get(owner, row)
            if parse_time(value["recorded_at"]) != parse_time(owner_row["started_at"]):
                raise ValueError("membership was not frozen at the owning attempt start")
            return value

        if isinstance(member_id, str) and member_id.startswith("membership_"):
            memberships[identity] = check("membership", member_id, membership, identity)
        else:
            result(
                "membership",
                member_id,
                "DECLARED",
                "external universe identity; local retention not established",
                attempt_id=identity,
                required=False,
            )

        clock = row.get("clock", {})
        clock_id = clock.get("evidence_id")
        if isinstance(clock_id, str) and clock_id.startswith("clock_"):

            def clock_evidence():
                _generated(clock_id, "clock_")
                value = _object(root, f"timing/clocks/{clock_id}.json")
                if "clock_" + digest(value) != clock_id or value.get("observed_at") != clock.get(
                    "observed_at"
                ):
                    raise ValueError("clock hash or observation time mismatch")
                if parse_time(value["observed_at"]) > parse_time(row["recorded_at"]):
                    raise ValueError("clock observation is after retained attempt")
                if value.get("command") != "chronyc -c tracking":
                    raise ValueError("unsupported local clock measurement")
                if clock.get("status") == "MEASURED_EXTERNAL":
                    fields = value["stdout"].strip().split(",")
                    if (
                        value.get("returncode") != 0
                        or len(fields) < 13
                        or fields[-1].strip() != "Normal"
                        or not Decimal(fields[3]).is_finite()
                        or Decimal(fields[3]) != Decimal(clock["offset_seconds"])
                    ):
                        raise ValueError("clock measurement differs from retained raw output")
                return value

            check("clock", clock_id, clock_evidence, identity)
        elif clock_id is not None:
            result(
                "clock",
                clock_id,
                "DECLARED",
                "external clock evidence not locally verified",
                attempt_id=identity,
                required=False,
            )

        links = row.get("links", {})
        if links.get("context_id") is not None:
            context_links.setdefault(links["context_id"], []).append(identity)
        if any(key in links for key in ("capture_path", "capture_sha256", "capture_membership_id")):

            def capture():
                from .intraday import load_intraday

                expected = links.get("capture_sha256")
                if not isinstance(expected, str) or not HEX.fullmatch(expected):
                    raise ValueError("capture link requires its exact byte digest")
                path = _safe(root, links["capture_path"])
                if path.parent != root / "timing" / "captures":
                    raise ValueError("capture link is outside the retained capture directory")
                if path.name != identity + ".json":
                    raise ValueError("capture filename does not identify its owning attempt")
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise ValueError("linked capture bytes changed")
                raw = read_json(path)
                _safe(root, "evidence/" + raw["membership_path"])
                for evidence in raw["evidence"]:
                    _safe(root, "evidence/" + evidence["path"])
                    _safe(
                        root,
                        "evidence/receipts/"
                        + evidence["evidence_id"].removeprefix("ev_")
                        + ".json",
                    )
                value = load_intraday(path, _safe(root, "evidence"))
                if value["membership_snapshot_id"] != links.get("capture_membership_id"):
                    raise ValueError("capture membership link differs from original capture")
                if identity in memberships and memberships[identity] is not None:
                    if value["symbols_requested"] != memberships[identity]["members"]:
                        raise ValueError("capture universe differs from attempt membership")
                if parse_time(value["completed_at"]) > parse_time(row["recorded_at"]):
                    raise ValueError("capture completed after the attempt was retained")
                if row.get("started_at") and parse_time(value["started_at"]) < parse_time(
                    row["started_at"]
                ):
                    raise ValueError("capture started before its owning attempt")
                if row.get("scheduled_at") and parse_time(value["scheduled_at"]) != parse_time(
                    row["scheduled_at"]
                ):
                    raise ValueError("capture schedule differs from attempt")
                if (
                    row.get("evidence_kind") == "synthetic"
                    and value.get("evidence_kind") != "synthetic"
                ):
                    raise ValueError("synthetic attempt linked to nonsynthetic capture")
                if (
                    row.get("evidence_kind") == "prospective"
                    and value.get("evidence_kind") == "synthetic"
                ):
                    raise ValueError("prospective attempt linked to synthetic capture")
                return value

            captures[identity] = check("capture", links.get("capture_path"), capture, identity)

        anchor_id = links.get("anchor_id")
        if anchor_id is not None:

            def anchor():
                from .time_anchor import verify_anchor

                if not isinstance(anchor_id, str) or not HEX.fullmatch(anchor_id):
                    raise ValueError("invalid linked anchor identifier")
                folder = f"timing/anchors/{anchor_id}"
                manifest = _object(root, folder + "/manifest.json")
                payload_path = _safe(root, folder + "/payload.json")
                if (
                    hashlib.sha256(payload_path.read_bytes()).hexdigest() != anchor_id
                    or manifest.get("anchor_id") != anchor_id
                    or manifest.get("payload_sha256") != anchor_id
                ):
                    raise ValueError("anchor payload hash mismatch")
                payload = read_json(payload_path)
                # Legacy single-run batches used run_id. A two-observation capture
                # preserves its first decision separately from its final fill run.
                decision_run_id = links.get("decision_run_id", links.get("run_id"))
                if (
                    payload.get("attempt_id") != identity
                    or payload.get("decision_at") != row.get("decision_at")
                    or (decision_run_id is not None and payload.get("run_id") != decision_run_id)
                ):
                    raise ValueError("timestamp anchor does not bind the linked attempt decision")
                for token in _safe(root, folder).glob("*.tsr"):
                    _safe(root, token.relative_to(root).as_posix())
                verified = verify_anchor(root, anchor_id)
                if verified["status"] == "FAIL":
                    raise ValueError("independent timestamp anchor failed verification")
                if verified["status"] != "VERIFIED":
                    result(
                        "external_timestamp",
                        anchor_id,
                        "UNAVAILABLE",
                        "original payload retained; independent signature verification incomplete",
                        attempt_id=identity,
                        required=False,
                    )
                return verified

            check("anchor_payload", anchor_id, anchor, identity)

    # Request children use the same captured evidence as their retained parent.
    for row in rows:
        parent_id = row.get("links", {}).get("parent_attempt_id")
        if parent_id in captures and captures[parent_id] is not None:

            def request_link():
                capture = captures[parent_id]
                prefix = parent_id + ":request:"
                if not row["id"].startswith(prefix):
                    raise ValueError("request child identity does not name its parent")
                index = int(row["id"][len(prefix) :])
                if index < 0 or index >= len(capture["requests"]):
                    raise ValueError("request child index is outside original capture")
                request = capture["requests"][index]
                expected_id = request.get("evidence_id") or row["id"]
                if (
                    row.get("evidence_id") != expected_id
                    or row.get("received_at") != request.get("received_at")
                    or row.get("started_at") != request.get("request_started_at")
                ):
                    raise ValueError("request child differs from captured original request")
                return request

            check("request", row.get("evidence_id"), request_link, row.get("id"))

    try:
        context_dir = _safe(root, "timing/contexts")
        context_paths = set(context_dir.glob("*.json"))
    except ValueError as exc:
        result("context_directory", "timing/contexts", "FAIL", str(exc))
        context_paths = set()
    for identity, owners in context_links.items():
        if not isinstance(identity, str) or not HEX.fullmatch(identity):
            result(
                "context",
                identity,
                "FAIL",
                "invalid linked context identifier",
                attempt_id=owners[0],
            )
        else:
            context_paths.add(root / "timing" / "contexts" / (identity + ".json"))
    for path in sorted(context_paths):

        def context():
            from ..timing_context import build_timing_context

            envelope = _object(root, path.relative_to(root).as_posix())
            body = envelope["payload"]
            if (
                envelope.get("schema_version") != "KOD_TIMING_CONTEXT_RECORD_V1"
                or digest(body) != envelope.get("sha256")
                or path.stem != envelope["sha256"]
            ):
                raise ValueError("context envelope hash or identity mismatch")
            if digest(body["input"]) != body["input_sha256"]:
                raise ValueError("retained context input changed")
            if parse_time(body["as_of"]) > parse_time(body["recorded_at"]):
                raise ValueError("context cutoff is after its local observation")
            rebuilt = build_timing_context(body["input"], as_of=body["as_of"])
            if canonical(rebuilt) != canonical(body["context"]):
                raise ValueError(
                    "context outputs differ from original source and cost declarations"
                )
            result(
                "context_sources",
                path.stem,
                "DECLARED",
                "source and cost input bytes retained; upstream truth requires source-specific verification",
                required=False,
            )
            return body

        check("context", path.stem, context)

    counts = Counter(row["status"].lower() for row in checks)
    failures = [
        row
        for row in checks
        if row["status"] == "FAIL" or (row["status"] == "UNAVAILABLE" and row["required"])
    ]
    return {
        "schema_version": SCHEMA,
        "ok": not failures,
        "complete": bool(checks) and all(row["status"] == "VERIFIED" for row in checks),
        "counts": {
            key: counts.get(key, 0) for key in ("verified", "unavailable", "declared", "fail")
        },
        "checks": checks,
        "problems": failures,
        "entry_permission": False,
    }

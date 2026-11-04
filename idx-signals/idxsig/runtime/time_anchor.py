"""Opt-in external timestamps for immutable decision batches; no order routing.

Stored payload bytes never acquire timestamp fields. Authority tokens and attempt
receipts are separate immutable objects. Verification is offline and uses KOD's
pinned RFC3161 trust chain. A retry keeps the authority's actual later timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

from ..provenance import exclusive_lock, publish_bytes
from .storage import canonical, read_json

SCHEMA = "KOD_TIME_ANCHOR_V1"
IDENTIFIER = re.compile(r"[0-9a-f]{64}")
AUTHORITY = re.compile(r"[A-Za-z0-9_-]+")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _folder(root, identifier: str) -> Path:
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise ValueError("invalid anchor identifier")
    root = Path(root).resolve()
    result = root / "timing" / "anchors" / identifier
    if not result.resolve().is_relative_to(root):
        raise ValueError("anchor path escapes runtime root")
    return result


def _same_bytes(path: Path, data: bytes) -> None:
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError("immutable anchor artifact conflict")
    else:
        publish_bytes(path, data)


def _checker():
    try:
        from kod.timestamp import RFC3161Timestamper
    except ImportError:
        return None
    return RFC3161Timestamper()


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp requires an explicit timezone")
    return parsed.astimezone(timezone.utc)


def verify_anchor(root, identifier: str, *, verifier=None) -> dict:
    """Verify exact original payload and every available token without network IO."""
    folder = _folder(root, identifier)
    result = {
        "schema_version": SCHEMA,
        "anchor_id": identifier,
        "status": "UNAVAILABLE",
        "payload_sha256": identifier,
        "tokens": [],
        "errors": [],
        "earliest_verified_at": None,
        "before_outcome_window": None,
    }
    try:
        if (folder / "manifest.json").is_symlink():
            raise ValueError("manifest symlink is not an original file")
        manifest = read_json(folder / "manifest.json")
        payload_path = folder / "payload.json"
        if payload_path.is_symlink():
            raise ValueError("payload symlink is not an original file")
        payload = payload_path.read_bytes()
        if (
            manifest.get("schema_version") != SCHEMA
            or manifest.get("anchor_id") != identifier
            or manifest.get("payload_sha256") != identifier
            or manifest.get("payload_file") != "payload.json"
            or hashlib.sha256(payload).hexdigest() != identifier
        ):
            raise ValueError("anchor manifest or payload hash mismatch")
        decision = json.loads(payload)
        if not isinstance(decision, dict):
            raise ValueError("decision batch must be an object")
        for field in ("decision_at", "outcome_window_start"):
            if decision.get(field) is not None:
                _aware(decision[field])
    except FileNotFoundError:
        result["errors"].append("original payload or manifest unavailable")
        return result
    except (OSError, ValueError, TypeError):
        result.update(
            status="FAIL", errors=["original payload or manifest failed integrity checks"]
        )
        return result
    verifier = verifier if verifier is not None else _checker()
    tokens = sorted(folder.glob("*.tsr"))
    if not tokens:
        result["errors"].append("no external timestamp token")
        return result
    verified = []
    for token_path in tokens:
        name = token_path.stem
        token = {"authority": name, "status": "UNAVAILABLE", "timestamp": None}
        if not AUTHORITY.fullmatch(name) or token_path.is_symlink():
            token.update(status="FAIL", reason="invalid token path")
        elif verifier is None:
            token["reason"] = "offline timestamp verifier unavailable"
        else:
            try:
                stamp = verifier.verify(name, token_path.read_bytes(), payload)
                if stamp.tzinfo is None or stamp.utcoffset() is None:
                    raise ValueError("authority time lacks timezone")
                stamp = stamp.astimezone(timezone.utc)
                token.update(status="VERIFIED", timestamp=stamp.isoformat())
                verified.append(stamp)
            except FileNotFoundError:
                token["reason"] = "OpenSSL or pinned certificate unavailable"
            except Exception as exc:
                token.update(
                    status="FAIL", reason="timestamp verification failed: " + type(exc).__name__
                )
        result["tokens"].append(token)
    statuses = {row["status"] for row in result["tokens"]}
    result["status"] = (
        "FAIL"
        if "FAIL" in statuses
        else "VERIFIED"
        if statuses == {"VERIFIED"}
        else "PARTIAL"
        if verified
        else "UNAVAILABLE"
    )
    if verified:
        first = min(verified)
        result["earliest_verified_at"] = first.isoformat()
        if decision.get("decision_at") is not None:
            result["timestamp_minus_decision_seconds"] = (
                first - _aware(decision["decision_at"])
            ).total_seconds()
        if decision.get("outcome_window_start") is not None:
            result["before_outcome_window"] = first < _aware(decision["outcome_window_start"])
    return result


def anchor_batch(root, payload: dict, *, enabled: bool = False, stamper=None) -> dict:
    """Seal a batch only on an explicit prospective invocation, preserving retries.

    ``enabled=False`` performs no filesystem or network IO. The caller decides
    whether this is a prospective decision; demos and historical replay must keep
    it disabled. ``decision_at`` and an optional outcome window remain original
    caller facts, never replaced with a timestamp authority's later clock.
    """
    if not isinstance(payload, dict):
        raise ValueError("decision batch must be an object")
    for field in ("decision_at", "outcome_window_start"):
        if payload.get(field) is not None:
            _aware(payload[field])
    data = canonical(payload)
    identifier = hashlib.sha256(data).hexdigest()
    if not enabled:
        return {
            "schema_version": SCHEMA,
            "anchor_id": identifier,
            "status": "DISABLED",
            "payload_sha256": identifier,
            "tokens": [],
        }
    folder = _folder(root, identifier)
    checker = stamper if stamper is not None else _checker()
    manifest = {
        "schema_version": SCHEMA,
        "anchor_id": identifier,
        "payload_sha256": identifier,
        "payload_file": "payload.json",
    }
    with exclusive_lock(folder / "anchor"):
        _same_bytes(folder / "payload.json", data)
        _same_bytes(folder / "manifest.json", canonical(manifest) + b"\n")
        if checker is None:
            return {
                **manifest,
                "status": "UNAVAILABLE",
                "tokens": [],
                "errors": ["timestamp module unavailable; original payload retained"],
            }
        names = tuple(getattr(checker, "authorities", ()))
        if not names or any(
            not isinstance(name, str) or not AUTHORITY.fullmatch(name) for name in names
        ):
            raise ValueError("timestamper must declare safe authority names")
        existing = verify_anchor(root, identifier, verifier=checker)
        if existing["status"] == "FAIL":
            return existing
        if all((folder / f"{name}.tsr").is_file() for name in names):
            return existing
        started_at, start = _utc(), time.monotonic_ns()
        errors, written = [], []
        try:
            stamps = checker.stamp(data)
            for stamp in stamps:
                if stamp.authority not in names:
                    raise ValueError("timestamp authority was not declared")
                checker.verify(stamp.authority, stamp.token, data)
                target = folder / f"{stamp.authority}.tsr"
                # A later successful retry must never replace an earlier token.
                if not target.exists():
                    _same_bytes(target, stamp.token)
                    written.append(stamp.authority)
            errors.extend("authority request failed" for _ in getattr(checker, "last_errors", []))
        except Exception as exc:
            errors.append("timestamp attempt failed: " + type(exc).__name__)
        result = verify_anchor(root, identifier, verifier=checker)
        missing = [name for name in names if not (folder / f"{name}.tsr").is_file()]
        if missing and result["status"] == "VERIFIED":
            result["status"] = "PARTIAL"
        result["missing_authorities"] = missing
        receipt = {
            "schema_version": SCHEMA,
            "anchor_id": identifier,
            "attempted_at": started_at,
            "completed_at": _utc(),
            "duration_ns": time.monotonic_ns() - start,
            "requested_authorities": list(names),
            "written_authorities": written,
            "status": result["status"],
            "missing_authorities": missing,
            "errors": errors,
        }
        _same_bytes(folder / "attempts" / (uuid.uuid4().hex + ".json"), canonical(receipt) + b"\n")
        result["errors"].extend(errors)
        return result

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
from pathlib import Path

SCHEMA = "KOD_RUNTIME_SNAPSHOT_V1"
MAX_BYTES = 16 * 1024 * 1024
DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "kod"
SECTIONS = ("run", "health", "candidates", "market_context", "account", "experiments")


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
            value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
                               parse_constant=_nonfinite)
            if not isinstance(value, dict) or value.get("status") not in {"FAILED", "COMPLETED"}:
                raise ValueError("invalid attempt status")
            return value
        except (OSError, UnicodeError, ValueError, RecursionError):
            return {"status": "UNREADABLE", "error": "The latest attempt record could not be read; current run health is unknown."}

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
        return {"payload": payload, "sha256": computed, "schema_version": SCHEMA,
                "last_attempt": self.last_attempt()}


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
        {"name": name, **value}
        for name, value in health.items()
        if isinstance(value, dict)
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

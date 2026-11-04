"""Resolve dated aliases while preserving the original identifier and artifact bytes.

The ``old`` field is the historical canonical name; ``new`` is an additional alias.
An alias is never a request to move a file or rewrite a stored label. The map is
append-only. No existing experiment or import is renamed by this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re

from .hashing import parse_ts

DEFAULT_MAP = Path(__file__).resolve().parents[2] / "registry" / "ids" / "ID_MAP.jsonl"
KINDS = frozenset({"module", "function", "experiment", "detector", "profile", "path"})


def _name(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("identifier must be a nonempty string without outer whitespace")
    if any(ord(character) < 32 for character in value):
        raise ValueError("identifier contains a control character")
    return value


def _path_name(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("path aliases must remain relative to the repository")


def load_aliases(registry_path: Path | str = DEFAULT_MAP) -> list[dict]:
    """Read schema v1 (including legacy unversioned v1) without changing any bytes."""
    path = Path(registry_path)
    if not path.is_file():
        raise ValueError(f"identifier registry unavailable: {path}")
    rows: list[dict] = []
    aliases: dict[str, str] = {}
    canonical: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("schema_version", 1) != 1:
                raise ValueError("unsupported identifier-map schema")
            original, alias = _name(row["old"]), _name(row["new"])
            if original == alias or row["kind"] not in KINDS:
                raise ValueError("invalid alias or kind")
            if row["kind"] == "path":
                _path_name(original)
                _path_name(alias)
            since = parse_ts(row["since"])
            if datetime.fromisoformat(row["since"].replace("Z", "+00:00")).utcoffset().total_seconds() != 0:
                raise ValueError("alias effective time must be stored in UTC")
            if not re.fullmatch(r"[0-9a-f]{40}", row["commit"]):
                raise ValueError("alias commit must identify an existing full commit")
            _name(row["reason"])
            if alias in aliases or alias in canonical or original in aliases:
                raise ValueError("aliases cannot be rebound, chained or replace a canonical name")
            aliases[alias] = original
            canonical.add(original)
            rows.append({**row, "schema_version": 1, "effective_at": since})
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"invalid identifier-map line {line_number}: {exc}") from exc
    return rows


def resolve(
    name: str,
    at: str | datetime | None = None,
    *,
    registry_path: Path | str = DEFAULT_MAP,
    kind: str | None = None,
) -> str:
    """Return an original name; an unknown or not-yet-effective alias stays unchanged.

    ``at`` is the caller's information cutoff. Omitting it means the current UTC
    clock; historical readers should supply their own explicit cutoff. Unknown
    identifiers are preserved, not asserted to exist. Malformed registries fail.
    """
    name = _name(name)
    if kind is not None and kind not in KINDS:
        raise ValueError("unknown identifier kind")
    if at is None:
        cutoff = datetime.now(timezone.utc)
    elif isinstance(at, datetime):
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("alias cutoff requires an explicit timezone")
        cutoff = at.astimezone(timezone.utc)
    else:
        cutoff = parse_ts(at)
    for row in load_aliases(registry_path):
        if row["new"] == name and (kind is None or row["kind"] == kind):
            return row["old"] if row["effective_at"] <= cutoff else name
    return name

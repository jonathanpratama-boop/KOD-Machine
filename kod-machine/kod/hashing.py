"""Hashing, clocks, and canonical JSON. Software clock only."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt_ts(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now() -> str:
    return fmt_ts(utc_now_dt())


def parse_ts(text: str) -> datetime:
    """Parse an ISO-8601 timestamp. A timestamp without a timezone is refused, not guessed."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"timestamp missing: {text!r}")
    moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {text!r}")
    try:
        return moment.astimezone(timezone.utc)
    except OverflowError as exc:  # e.g. 0001-01-01T00:00:00+01:00 has no UTC representation
        raise ValueError(f"timestamp out of range: {text!r}") from exc


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_obj(obj) -> str:
    return sha256_text(canonical(obj))

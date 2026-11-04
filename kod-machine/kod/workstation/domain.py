"""Small value objects and input invariants for the local workstation.

The existing earnings/workbench engines remain the financial calculation core.
These records protect the IO boundary without duplicating their arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
import re
from urllib.parse import urlsplit

from ..hashing import fmt_ts, parse_ts

APP_VERSION = "KOD-WORKSTATION-v2"
ASSOCIATIONS = frozenset({"verified_from_filing_metadata", "user_asserted", "unresolved"})
MAX_DOCUMENT_BYTES = 12 * 1024 * 1024


def timestamp(value: str | None) -> str | None:
    """UTC ISO seconds or None. A date alone is deliberately not a timestamp."""
    return fmt_ts(parse_ts(value)) if value is not None else None


def publication(value: str | None) -> tuple[str | None, str | None]:
    if value is not None and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None, date.fromisoformat(value).isoformat()
    return timestamp(value), None


def canonical(value) -> str:
    def encode(item):
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError("non-finite decimal is not permitted")
            return str(item)
        raise TypeError(f"not a JSON domain value: {type(item).__name__}")

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=encode,
    )


def identity(prefix: str, *values) -> str:
    return prefix + "_" + hashlib.sha256(canonical(values).encode()).hexdigest()[:24]


def association(value: str) -> str:
    if value not in ASSOCIATIONS:
        raise ValueError(
            "association must be verified_from_filing_metadata, user_asserted or unresolved"
        )
    return value


def cik_value(value: str | int | None) -> str | None:
    if value in (None, ""):
        return None
    text = str(value)
    if not text.isdigit() or not 1 <= len(text) <= 10 or int(text) == 0:
        raise ValueError("CIK must contain 1–10 digits and be positive")
    return text.zfill(10)


def source_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 3000 or any(ord(c) < 32 for c in value):
        raise ValueError("source URL is invalid")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise ValueError("source URL is invalid") from exc
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError("source URL must be an http(s) citation without credentials")
    if port is not None and port not in (80, 443):
        raise ValueError("source URL uses an unsupported port")
    from ..earnings import has_dot_segments

    if has_dot_segments(parts.path):
        raise ValueError("source URL must not contain '.' or '..' path segments")
    return value


@dataclass(frozen=True, slots=True)
class Security:
    ticker: str
    name: str
    cik: str | None = None
    venue: str = "XNAS"
    currency: str = "USD"
    association: str = "user_asserted"

    def validated(self) -> "Security":
        ticker, venue, currency = (
            self.ticker.strip().upper(),
            self.venue.strip().upper(),
            self.currency.strip().upper(),
        )
        if not re.fullmatch(r"[A-Z0-9.^_\-]{1,32}", ticker):
            raise ValueError("ticker must contain 1–32 letters, digits or . ^ _ -")
        if not self.name.strip() or len(self.name) > 240:
            raise ValueError("company name must contain 1–240 characters")
        if not re.fullmatch(r"[A-Z0-9_\-]{1,20}", venue):
            raise ValueError("venue must contain 1–20 letters/digits")
        if not re.fullmatch(r"[A-Z]{3}|UNKNOWN", currency):
            raise ValueError("currency must be an ISO currency code or UNKNOWN")
        return Security(
            ticker,
            self.name.strip(),
            cik_value(self.cik),
            venue,
            currency,
            association(self.association),
        )


@dataclass(frozen=True, slots=True)
class SourceEnvelope:
    security_id: str
    raw: bytes
    filename: str
    source_url: str
    published_at: str | None
    published_basis: str
    observed_at: str
    role: str = "current"
    association: str = "user_asserted"
    provider: str = "local"
    external_id: str | None = None

    def validate(self) -> None:
        if not isinstance(self.raw, bytes) or not self.raw or len(self.raw) > MAX_DOCUMENT_BYTES:
            raise ValueError("document must contain 1 byte to 12 MiB")
        source_url(self.source_url)
        association(self.association)
        observed = timestamp(self.observed_at)
        published = timestamp(self.published_at)
        if published and observed < published:
            raise ValueError("observation must not precede publication")
        if self.role not in ("current", "comparison", "metadata", "other"):
            raise ValueError("unsupported source role")

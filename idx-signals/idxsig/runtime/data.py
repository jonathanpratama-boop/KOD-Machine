"""Strict, point-in-time recorded market snapshots and immutable evidence objects.

Synthetic fixtures are explicitly labelled. Public snapshots require verified raw
objects; a missing observation is never silently replaced by a zero or a later one.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..market_time import binance_datetime

SCHEMA_VERSION = "KOD_RECORDED_SNAPSHOT_V1"
VENUE = "BINANCE_SPOT"


class SnapshotError(ValueError):
    """A snapshot cannot support a trustworthy point-in-time observation."""


def parse_time(value: str, field: str = "timestamp") -> datetime:
    if not isinstance(value, str):
        raise SnapshotError(f"{field}: timezone-qualified ISO timestamp required")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError(f"{field}: invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SnapshotError(f"{field}: timezone required")
    return dt.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def number(
    value: Any,
    field: str,
    *,
    positive: bool = False,
    nonnegative: bool = True,
    nullable: bool = False,
) -> str | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or value is None:
        raise SnapshotError(f"{field}: finite number required")
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SnapshotError(f"{field}: invalid number") from exc
    if not n.is_finite() or (positive and n <= 0) or (nonnegative and n < 0):
        raise SnapshotError(f"{field}: invalid range or non-finite number")
    return format(n, "f")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _write_immutable(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(body)
    except FileExistsError:
        if path.read_bytes() != body:
            raise SnapshotError(f"immutable evidence conflict: {path.name}")


def capture_raw_evidence(
    raw: bytes,
    evidence_root: str | Path,
    *,
    source_url: str,
    received_at: str,
    kind: str,
    request: dict | None = None,
) -> dict:
    """Persist the exact response bytes and a receipt. Repeated content is safe.

    Different retrievals of identical bytes have distinct evidence IDs so their
    actual availability times cannot be confused.
    """
    received_at = utc_text(parse_time(received_at, "received_at"))
    if not isinstance(raw, bytes):
        raise SnapshotError("raw evidence must be bytes")
    digest = hashlib.sha256(raw).hexdigest()
    relative = f"objects/{digest[:2]}/{digest}.json"
    metadata = {
        "sha256": digest,
        "path": relative,
        "received_at": received_at,
        "source_url": source_url,
        "kind": kind,
        "request": request or {},
        "size_bytes": len(raw),
    }
    identity = hashlib.sha256(_canonical(metadata)).hexdigest()
    record = {"evidence_id": "ev_" + identity, **metadata}
    root = Path(evidence_root)
    _write_immutable(root / relative, raw)
    _write_immutable(root / "receipts" / f"{identity}.json", _canonical(record))
    return record


# Compatibility spelling for callers that use the short name.
capture_evidence = capture_raw_evidence


def _identity(row: dict) -> str:
    venue, symbol = row.get("venue"), row.get("symbol")
    if not isinstance(venue, str) or not venue or not isinstance(symbol, str) or not symbol:
        raise SnapshotError("venue and symbol are required")
    if any(c in venue + symbol for c in "\n\r/\\"):
        raise SnapshotError("invalid instrument identity")
    return f"{venue}:{symbol}"


def _json(raw: bytes | str) -> Any:
    def reject(value):
        raise SnapshotError(f"non-finite JSON constant: {value}")

    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SnapshotError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(raw, parse_constant=reject, object_pairs_hook=unique)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SnapshotError("invalid JSON snapshot/evidence") from exc


def _evidence(
    snapshot: dict, root: Path | None, cutoff: datetime, required: bool
) -> tuple[dict, dict]:
    records, payloads = {}, {}
    if required and root is None:
        raise SnapshotError("public_market snapshot requires evidence_root")
    for entry in snapshot.get("evidence", []):
        entry = dict(entry)
        eid = entry.get("evidence_id")
        if not isinstance(eid, str) or not eid or eid in records:
            raise SnapshotError("missing or duplicate evidence_id")
        if parse_time(entry.get("received_at"), "evidence.received_at") > cutoff:
            raise SnapshotError("future evidence receipt")
        records[eid] = entry
        if root is None:
            continue
        rel = Path(entry.get("path", ""))
        resolved = (root / rel).resolve()
        if rel.is_absolute() or root.resolve() not in resolved.parents:
            raise SnapshotError("evidence path escapes evidence_root")
        try:
            raw = resolved.read_bytes()
        except OSError as exc:
            raise SnapshotError(f"missing raw evidence: {eid}") from exc
        if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
            raise SnapshotError(f"raw evidence hash mismatch: {eid}")
        if entry.get("size_bytes") != len(raw):
            raise SnapshotError(f"raw evidence length mismatch: {eid}")
        receipt_identity = hashlib.sha256(
            _canonical({k: v for k, v in entry.items() if k != "evidence_id"})
        ).hexdigest()
        if eid != "ev_" + receipt_identity:
            raise SnapshotError(f"evidence receipt hash mismatch: {eid}")
        receipt = root / "receipts" / f"{receipt_identity}.json"
        if not receipt.exists() or receipt.read_bytes() != _canonical(entry):
            raise SnapshotError(f"missing or changed evidence receipt: {eid}")
        payloads[eid] = _json(raw)
    return records, payloads


def _milliseconds(value: Any) -> str:
    # Retain the historical helper name while normalizing ms/us per observation.
    try:
        return utc_text(binance_datetime(value))
    except ValueError as exc:
        raise SnapshotError(str(exc)) from exc


def _same_numbers(row: dict, expected: dict) -> None:
    for key, value in expected.items():
        if row.get(key) is None or Decimal(str(row[key])) != Decimal(str(value)):
            raise SnapshotError(f"normalized {key} differs from raw evidence")


def _verify_public_row(row: dict, row_type: str, evidence: dict, payloads: dict) -> None:
    eid = row.get("evidence_id")
    if eid not in evidence or eid not in payloads:
        raise SnapshotError(f"{row_type}: missing verified raw evidence")
    meta, raw = evidence[eid], payloads[eid]
    source_url = urlparse(meta.get("source_url", ""))
    if (
        source_url.scheme != "https"
        or source_url.hostname != "api.binance.com"
        or source_url.username
        or source_url.password
        or source_url.port not in (None, 443)
    ):
        raise SnapshotError("public evidence is not from the fixed supported Binance host")
    stamp = row.get("metadata_received_at") if row_type == "instrument" else row.get("received_at")
    if parse_time(stamp) != parse_time(meta["received_at"]):
        raise SnapshotError("normalized availability timestamp differs from evidence receipt")
    if row["venue"] != VENUE:
        raise SnapshotError("no raw reconciliation adapter for this public venue")
    if row_type == "bar":
        if (
            meta.get("kind") != "binance_klines"
            or meta.get("request", {}).get("symbol") != row["symbol"]
        ):
            raise SnapshotError("bar raw source identity mismatch")
        match = [r for r in raw if _milliseconds(r[0]) == row["open_time"]]
        if len(match) != 1 or _milliseconds(match[0][6]) != row["close_time"]:
            raise SnapshotError("bar time differs from raw evidence")
        r = match[0]
        _same_numbers(
            row,
            dict(
                zip(
                    ("open", "high", "low", "close", "base_volume", "quote_volume"),
                    (r[1], r[2], r[3], r[4], r[5], r[7]),
                )
            ),
        )
    elif row_type == "quote":
        if meta.get("kind") != "binance_book_ticker" or raw.get("symbol") != row["symbol"]:
            raise SnapshotError("quote raw source identity mismatch")
        _same_numbers(
            row,
            {
                "bid": raw["bidPrice"],
                "ask": raw["askPrice"],
                "bid_size": raw["bidQty"],
                "ask_size": raw["askQty"],
            },
        )
        if row.get("source_time") is not None:
            raise SnapshotError("Binance bookTicker has no source timestamp; do not invent one")
        raw_start = meta.get("request", {}).get("request_started_at")
        if raw_start is not None and row.get("request_started_at") != raw_start:
            raise SnapshotError("quote request start differs from evidence receipt")
    else:
        if meta.get("kind") != "binance_exchange_info":
            raise SnapshotError("instrument raw source mismatch")
        match = [r for r in raw.get("symbols", []) if r.get("symbol") == row["symbol"]]
        if len(match) != 1:
            raise SnapshotError("instrument not present in raw exchange metadata")
        r = match[0]
        for key, source_key in (
            ("base_asset", "baseAsset"),
            ("quote_asset", "quoteAsset"),
            ("trading_status", "status"),
        ):
            if row[key] != r[source_key]:
                raise SnapshotError("instrument identity/status differs from raw metadata")
        filters = {x["filterType"]: x for x in r.get("filters", [])}
        expected = {
            "tick_size": filters.get("PRICE_FILTER", {}).get("tickSize"),
            "lot_step": filters.get("LOT_SIZE", {}).get("stepSize"),
            "min_notional": filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {})).get(
                "minNotional"
            ),
        }
        expected.update(
            {
                key: filters.get(source_filter, {}).get(source_key)
                for key, source_filter, source_key in (
                    ("min_qty", "LOT_SIZE", "minQty"),
                    ("max_qty", "LOT_SIZE", "maxQty"),
                    ("max_notional", "NOTIONAL", "maxNotional"),
                )
            }
        )
        for key, value in expected.items():
            if value is None:
                if row.get(key) is not None:
                    raise SnapshotError(f"invented instrument constraint: {key}")
            else:
                _same_numbers(row, {key: value})


def load_recorded_snapshot(
    path: str | Path, as_of: str | datetime, evidence_root: str | Path | None = None
) -> dict:
    """Validate a snapshot at an explicit cutoff; never silently drop future data.

    The collector excludes a forming candle before publication. Any future row
    in an already recorded snapshot is an error, preventing accidental hindsight.
    Stale and missing observations remain visible in ``validation``.
    """
    cutoff = parse_time(as_of, "as_of") if isinstance(as_of, str) else as_of
    if not isinstance(cutoff, datetime) or cutoff.tzinfo is None:
        raise SnapshotError("as_of requires a timezone")
    cutoff = cutoff.astimezone(timezone.utc)
    # Parse and identify the same bytes even if another writer replaces the file.
    snapshot_bytes = Path(path).read_bytes()
    original = _json(snapshot_bytes)
    if not isinstance(original, dict) or original.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotError("unsupported recorded snapshot schema")
    kind = original.get("evidence_kind")
    if kind not in ("synthetic", "public_market"):
        raise SnapshotError("evidence_kind must be synthetic or public_market")
    captured = parse_time(original.get("captured_at"), "captured_at")
    if captured > cutoff:
        raise SnapshotError("snapshot was captured after as_of")
    for key in ("instruments", "bars", "quotes"):
        if not isinstance(original.get(key), list):
            raise SnapshotError(f"{key} must be a list")
    records, payloads = _evidence(
        original, Path(evidence_root) if evidence_root else None, cutoff, kind == "public_market"
    )
    instruments, bars, quotes = [], [], []
    identities = set()
    for raw in original["instruments"]:
        r = dict(raw)
        ident = _identity(r)
        if ident in identities:
            raise SnapshotError("duplicate instrument")
        identities.add(ident)
        r["instrument_id"] = ident
        for key in ("base_asset", "quote_asset", "asset_class", "trading_status"):
            if not isinstance(r.get(key), str) or not r[key]:
                raise SnapshotError(f"instrument.{key} required")
        for key in ("tick_size", "lot_step", "min_notional"):
            r[key] = number(r.get(key), key, positive=key != "min_notional", nullable=True)
        for key in ("min_qty", "max_qty", "max_notional"):
            if key in r:
                r[key] = number(r[key], key, nullable=True)
        if r.get("metadata_received_at"):
            stamp = parse_time(r["metadata_received_at"], "metadata_received_at")
            if stamp > cutoff:
                raise SnapshotError("future instrument metadata")
            r["metadata_received_at"] = utc_text(stamp)
        if kind == "public_market":
            _verify_public_row(r, "instrument", records, payloads)
        instruments.append(r)
    seen_bars, seen_quotes = {}, set()
    stale_quotes, unknown_quote_times, stale_bars = [], [], []
    for raw in original["bars"]:
        r = dict(raw)
        ident = _identity(r)
        if ident not in identities:
            raise SnapshotError("bar has unknown instrument")
        r["instrument_id"] = ident
        times = {
            k: parse_time(r.get(k), f"bar.{k}") for k in ("open_time", "close_time", "received_at")
        }
        if not times["open_time"] < times["close_time"] <= times["received_at"] <= cutoff:
            raise SnapshotError("bar is incomplete, future, or received before close")
        r.update({k: utc_text(v) for k, v in times.items()})
        for key in ("open", "high", "low", "close"):
            r[key] = number(r.get(key), key, positive=True)
        for key in ("base_volume", "quote_volume"):
            r[key] = number(r.get(key), key, nullable=True)
        if (
            Decimal(r["low"]) > min(Decimal(r["open"]), Decimal(r["close"]))
            or Decimal(r["high"]) < max(Decimal(r["open"]), Decimal(r["close"]))
            or Decimal(r["low"]) > Decimal(r["high"])
        ):
            raise SnapshotError("invalid OHLC bounds")
        key = (ident, r["open_time"])
        if key in seen_bars:
            label = "duplicate" if seen_bars[key] == r else "revised/conflicting"
            raise SnapshotError(f"{label} bar: {ident} {r['open_time']}")
        seen_bars[key] = r
        if not isinstance(r.get("evidence_id"), str) or not r["evidence_id"]:
            raise SnapshotError("bar evidence_id required")
        if kind == "public_market":
            _verify_public_row(r, "bar", records, payloads)
        bars.append(r)
    for raw in original["quotes"]:
        r = dict(raw)
        ident = _identity(r)
        if ident not in identities:
            raise SnapshotError("quote has unknown instrument")
        r["instrument_id"] = ident
        receipt = parse_time(r.get("received_at"), "quote.received_at")
        if r.get("at") is not None and parse_time(r["at"], "quote.at") != receipt:
            raise SnapshotError("recorded quote cannot override its observation processing clock")
        source = parse_time(r["source_time"], "quote.source_time") if r.get("source_time") else None
        if receipt > cutoff or (source is not None and source > receipt):
            raise SnapshotError("future quote/source timestamp")
        r["received_at"] = utc_text(receipt)
        r["source_time"] = utc_text(source) if source else None
        if r.get("request_started_at") is not None:
            started = parse_time(r["request_started_at"], "quote.request_started_at")
            if started > receipt:
                raise SnapshotError("quote request started after receipt")
            r["request_started_at"] = utc_text(started)
        for key in ("bid", "ask"):
            r[key] = number(r.get(key), key, positive=True)
        for key in ("bid_size", "ask_size"):
            r[key] = number(r.get(key), key, nullable=True)
        if Decimal(r["bid"]) > Decimal(r["ask"]):
            raise SnapshotError("crossed quote")
        observation = r.get("observation_id")
        if not isinstance(observation, str) or not observation or observation in seen_quotes:
            raise SnapshotError("missing or duplicate quote observation_id")
        seen_quotes.add(observation)
        if not isinstance(r.get("evidence_id"), str) or not r["evidence_id"]:
            raise SnapshotError("quote evidence_id required")
        if cutoff - (source or receipt) > timedelta(minutes=5):
            stale_quotes.append(observation)
        if source is None:
            unknown_quote_times.append(observation)
        if kind == "public_market":
            _verify_public_row(r, "quote", records, payloads)
        quotes.append(r)
    bars.sort(key=lambda x: (x["instrument_id"], x["open_time"]))
    quotes.sort(key=lambda x: (x["received_at"], x["observation_id"]))
    latest = {r["instrument_id"]: r for r in bars}
    for ident, bar in latest.items():
        if cutoff - parse_time(bar["close_time"]) > timedelta(hours=48):
            stale_bars.append(ident)
    missing_bars = sorted(identities - set(latest))
    quoted = {r["instrument_id"] for r in quotes}
    result = {
        **original,
        "as_of": utc_text(cutoff),
        "captured_at": utc_text(captured),
        "evidence_type": kind,
        "instruments": instruments,
        "bars": bars,
        "quotes": quotes,
        "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "validation": {
            "status": "VALIDATED",
            "evidence_verified": kind == "public_market",
            "missing_bar_instruments": missing_bars,
            "missing_quote_instruments": sorted(identities - quoted),
            "stale_bar_instruments": stale_bars,
            "stale_quote_observations": stale_quotes,
            "unknown_quote_source_times": unknown_quote_times,
            "future_rows_excluded": 0,
            "session_model": "24/7 UTC; no invented exchange session",
        },
    }
    return result

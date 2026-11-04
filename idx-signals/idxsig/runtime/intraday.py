"""Finite prospective intraday observations, separate from every trading rule.

No background loop, account endpoint, order, historical backfill, or invented
fill is provided. A run freezes its requested universe and window before GETs.
All successful and failed HTTP responses retain their exact bytes. A provider
block stops further requests; there is no alternate-host fallback.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

from ..market_time import binance_bar_end, binance_datetime
from .data import (
    SnapshotError,
    _canonical,
    _json,
    _write_immutable,
    capture_raw_evidence,
    number,
    parse_time,
    utc_text,
)

SCHEMA_VERSION = "KOD_INTRADAY_CAPTURE_V1"
HOST = "https://api.binance.com"
VENUE = "BINANCE_SPOT"
INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900}
PATHS = frozenset(
    {"/api/v3/time", "/api/v3/exchangeInfo", "/api/v3/klines",
     "/api/v3/ticker/bookTicker", "/api/v3/depth"}
)
MAX_RESPONSE = 8 * 1024 * 1024
STOP_STATUSES = frozenset({403, 418, 429, 451})


def _clock_time(clock: Callable) -> datetime:
    value = clock()
    return parse_time(value if isinstance(value, str) else value.isoformat(), "local clock")


@dataclass(frozen=True)
class PublicResponse:
    status: int
    raw: bytes
    headers: dict = field(default_factory=dict)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_public(path: str, params: dict, *, timeout: float) -> PublicResponse:
    """One fixed-host GET. Return error bytes without following redirects."""
    if path not in PATHS:
        raise ValueError("unsupported public endpoint")
    url = HOST + path + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url, headers={"User-Agent": "KOD-timing-research/1.0", "Accept": "application/json"}
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("public response exceeds capture byte limit")
        # Retain rate-limit advice, not arbitrary headers which may contain tokens.
        headers = {"retry_after": response.headers.get("Retry-After")}
        return PublicResponse(int(response.code), raw, headers)


def _config(symbols: list[str], interval: str, bars: int, timeout: float) -> None:
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 30:
        raise ValueError("request 1 to 30 explicit spot symbols")
    if any(not isinstance(s, str) or not re.fullmatch(r"[A-Z0-9]{1,26}USDT", s) for s in symbols):
        raise ValueError("explicit uppercase USDT symbols required")
    if len(set(symbols)) != len(symbols):
        raise ValueError("duplicate requested symbols")
    if interval not in INTERVAL_SECONDS:
        raise ValueError("supported intraday intervals are 1m, 5m and 15m")
    if isinstance(bars, bool) or not isinstance(bars, int) or not 2 <= bars <= 1000:
        raise ValueError("bars must be an integer from 2 to 1000")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError("timeout must be finite and at most 60 seconds")


def _bars(payload: object, symbol: str, interval: str, start: datetime,
          end: datetime, evidence: dict) -> tuple[list[dict], list[dict]]:
    if not isinstance(payload, list):
        raise ValueError("candle response is not a list")
    rows, excluded, seen = [], [], set()
    seconds = INTERVAL_SECONDS[interval]
    for candle in payload:
        if not isinstance(candle, list) or len(candle) < 8:
            raise ValueError("malformed candle")
        opened, closed = binance_datetime(candle[0]), binance_datetime(candle[6])
        finished = binance_bar_end(candle[6])
        if opened in seen:
            raise ValueError("duplicate candle timestamp")
        seen.add(opened)
        if finished - opened != timedelta(seconds=seconds) or opened.microsecond or int(opened.timestamp()) % seconds:
            raise ValueError("candle duration or alignment differs from requested interval")
        if opened < start or finished > end:
            excluded.append({"symbol": symbol, "open_time": utc_text(opened),
                             "reason": "OUTSIDE_FROZEN_COMPLETED_WINDOW"})
            continue
        row = {"venue": VENUE, "symbol": symbol, "interval": interval,
               "open_time": utc_text(opened), "close_time": utc_text(closed),
               "bar_end_at": utc_text(finished), "received_at": evidence["received_at"],
               "evidence_id": evidence["evidence_id"], "complete": True}
        for key, value in zip(("open", "high", "low", "close", "base_volume", "quote_volume"),
                              (candle[1], candle[2], candle[3], candle[4], candle[5], candle[7])):
            row[key] = number(value, key, positive=key in {"open", "high", "low", "close"})
        low, high = Decimal(row["low"]), Decimal(row["high"])
        if low > min(Decimal(row["open"]), Decimal(row["close"])) or high < max(Decimal(row["open"]), Decimal(row["close"])):
            raise ValueError("invalid OHLC bounds")
        rows.append(row)
    return sorted(rows, key=lambda row: row["open_time"]), excluded


def _quote(payload: object, symbol: str, evidence: dict, started: str) -> dict:
    if not isinstance(payload, dict) or payload.get("symbol") != symbol:
        raise ValueError("book ticker identity mismatch")
    row = {"venue": VENUE, "symbol": symbol, "source_time": None,
           "source_time_status": "UNAVAILABLE", "received_at": evidence["received_at"],
           "request_started_at": started, "evidence_id": evidence["evidence_id"],
           "observation_id": "quote_" + evidence["evidence_id"],
           "execution_venue_role": "PROXY_ONLY", "owner_venue_executability": "UNKNOWN"}
    for target, source in {"bid": "bidPrice", "ask": "askPrice", "bid_size": "bidQty", "ask_size": "askQty"}.items():
        row[target] = number(payload.get(source), target, positive=target in {"bid", "ask"})
    bid, ask = Decimal(row["bid"]), Decimal(row["ask"])
    if bid > ask:
        raise ValueError("crossed book ticker")
    row["spread_bps"] = str((ask - bid) / ((ask + bid) / 2) * 10000)
    return row


def _depth(payload: object, symbol: str, evidence: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("depth response is not an object")
    if type(payload.get("lastUpdateId")) is not int or payload["lastUpdateId"] < 0:
        raise ValueError("invalid depth update id")
    result = {"venue": VENUE, "symbol": symbol, "received_at": evidence["received_at"],
              "source_time": None, "source_time_status": "UNAVAILABLE",
              "evidence_id": evidence["evidence_id"], "execution_venue_role": "PROXY_ONLY",
              "update_id": payload.get("lastUpdateId")}
    for side in ("bids", "asks"):
        levels = payload.get(side)
        if not isinstance(levels, list) or not levels:
            raise ValueError("missing depth levels")
        normalized = []
        for level in levels:
            if not isinstance(level, list) or len(level) != 2:
                raise ValueError("invalid depth level")
            normalized.append([number(level[0], "price", positive=True), number(level[1], "quantity", positive=True)])
        prices = [Decimal(level[0]) for level in normalized]
        if len(set(prices)) != len(prices) or prices != sorted(prices, reverse=side == "bids"):
            raise ValueError("unordered or duplicate depth levels")
        result[side] = normalized
    if Decimal(result["bids"][0][0]) > Decimal(result["asks"][0][0]):
        raise ValueError("crossed depth")
    return result


def collect_intraday(
    output_path: str | Path,
    evidence_root: str | Path,
    symbols: list[str],
    *,
    scheduled_at: str,
    interval: str = "1m",
    bars: int = 60,
    timeout: float = 12.0,
    fetcher: Callable | None = None,
    clock: Callable | None = None,
    monotonic_ns: Callable | None = None,
    evidence_kind: str = "public_market",
    include_depth: bool = True,
) -> dict:
    """Capture one declared scheduled window and return an immutable receipt.

    Injected test transports must label their observations ``synthetic``. A
    repeated output path is read/verified without any new network requests.
    Publication time and earliest threshold crossing remain unknown: a candle
    collector cannot infer a detector's trigger or a news publication time.
    """
    _config(symbols, interval, bars, timeout)
    if type(include_depth) is not bool:
        raise ValueError("include_depth must be an explicit boolean")
    if evidence_kind not in {"public_market", "synthetic"}:
        raise ValueError("unsupported evidence kind")
    clock = clock or (lambda: datetime.now(timezone.utc))
    monotonic_ns = monotonic_ns or time.monotonic_ns
    fetcher = fetcher or fetch_public
    root, output = Path(evidence_root), Path(output_path)
    scheduled = parse_time(scheduled_at, "scheduled_at")
    started = _clock_time(clock)
    if scheduled > started:
        raise ValueError("scheduled time is in the future")
    if output.exists():
        existing = load_intraday(output, root)
        wanted = (utc_text(scheduled), symbols, interval, bars, evidence_kind, include_depth)
        actual = (existing["scheduled_at"], existing["symbols_requested"], existing["interval"],
                  existing["requested_bars"], existing["evidence_kind"], existing["include_depth"])
        if actual != wanted:
            raise ValueError("existing capture belongs to a different scheduled request")
        return existing
    step = INTERVAL_SECONDS[interval]
    end = datetime.fromtimestamp(int(started.timestamp()) // step * step, timezone.utc)
    start = end - timedelta(seconds=step * bars)
    membership = {"schema_version": "KOD_INTRADAY_MEMBERSHIP_V1", "scheduled_at": utc_text(scheduled),
                  "frozen_at": utc_text(started), "symbols": symbols, "venue": VENUE,
                  "window_start_at": utc_text(start), "window_end_at": utc_text(end),
                  "interval": interval, "requested_bars": bars, "evidence_kind": evidence_kind}
    member_id = "universe_" + hashlib.sha256(_canonical(membership)).hexdigest()
    member_path = "memberships/" + member_id + ".json"
    _write_immutable(root / member_path, _canonical(membership))
    result = {"schema_version": SCHEMA_VERSION, "scheduled_at": utc_text(scheduled),
              "started_at": utc_text(started), "symbols_requested": symbols,
              "membership_snapshot_id": member_id, "membership_path": member_path,
              "interval": interval, "requested_bars": bars, "include_depth": include_depth,
              "window_start_at": utc_text(start), "window_end_at": utc_text(end),
              "evidence_kind": evidence_kind, "requests": [], "evidence": [],
              "instruments": [], "bars": [], "quotes": [], "depth": [], "failures": [],
              "excluded_bars": [], "symbol_status": [], "entry_permission": False,
              "threshold_crossing_at": None, "threshold_status": "NO_DETECTOR_RUN",
              "clock_integrity": {"ntp_status": "UNVERIFIED", "ntp_offset_ms": None,
                                  "source_clock_status": "UNAVAILABLE", "source_offset_midpoint_ms": None}}
    blocked = False
    capture_start_ns = monotonic_ns()

    def request(path: str, params: dict, kind: str):
        nonlocal blocked
        stamp = utc_text(_clock_time(clock))
        begin = monotonic_ns()
        record = {"endpoint": path, "symbol": params.get("symbol"), "request_started_at": stamp,
                  "received_at": None, "source_time": None, "source_time_status": "UNAVAILABLE",
                  "elapsed_ns": None, "status": "FAILED", "http_status": None, "evidence_id": None}
        payload, evidence = None, None
        try:
            response = fetcher(path, params, timeout=timeout)
            if isinstance(response, tuple):
                response = PublicResponse(*response)
            if not isinstance(response, PublicResponse) or not isinstance(response.raw, bytes):
                raise ValueError("transport must return PublicResponse with exact bytes")
            if len(response.raw) > MAX_RESPONSE:
                raise ValueError("public response exceeds capture byte limit")
            received = utc_text(_clock_time(clock))
            record.update(received_at=received, http_status=response.status)
            url = HOST + path + "?" + urllib.parse.urlencode(params)
            evidence = capture_raw_evidence(response.raw, root, source_url=url,
                                           received_at=received, kind=kind,
                                           request={**params, "request_started_at": stamp, "http_status": response.status})
            result["evidence"].append(evidence)
            record["evidence_id"] = evidence["evidence_id"]
            if parse_time(received) < parse_time(stamp):
                raise ValueError("local wall clock moved backwards during request")
            if response.status in STOP_STATUSES or 300 <= response.status < 400:
                blocked = True
                record["retry_after"] = response.headers.get("retry_after")
                record["status"] = "BLOCKED"
                raise ValueError(f"provider request stopped at HTTP {response.status}")
            if response.status != 200:
                raise ValueError(f"provider returned HTTP {response.status}")
            try:
                payload = _json(response.raw)
            except ValueError:
                blocked = True
                record["status"] = "BLOCKED"
                raise ValueError("provider returned non-JSON data; further requests stopped") from None
            if isinstance(payload, dict) and "code" in payload and "msg" in payload:
                raise ValueError("provider returned an API error object")
            record["status"] = "RECEIVED"
        except (ValueError, OSError, urllib.error.URLError, TimeoutError) as exc:
            record["error"] = type(exc).__name__ + ": " + str(exc)[:240]
            result["failures"].append({"endpoint": path, "symbol": params.get("symbol"),
                                       "status": record["status"], "reason": record["error"]})
            payload = None
        finally:
            elapsed = monotonic_ns() - begin
            record["elapsed_ns"] = elapsed if elapsed >= 0 else None
            record["recorded_at"] = utc_text(_clock_time(clock))
            result["requests"].append(record)
        return payload, evidence, record

    server, _, server_request = request("/api/v3/time", {}, "binance_server_time")
    if server is not None:
        try:
            source = binance_datetime(server["serverTime"])
            first = parse_time(server_request["request_started_at"])
            last = parse_time(server_request["received_at"])
            server_request.update(source_time=utc_text(source), source_time_status="EXCHANGE_CLOCK_SAMPLE")
            result["clock_integrity"].update(
                source_clock_status="MIDPOINT_ESTIMATE_NOT_NTP",
                source_offset_midpoint_ms=(source - (first + (last - first) / 2)).total_seconds() * 1000,
            )
        except (KeyError, TypeError, ValueError):
            server_request["validation_status"] = "INVALID_CLOCK_RESPONSE"
    info, metadata, _ = (None, None, None) if blocked else request(
        "/api/v3/exchangeInfo", {"symbols": json.dumps(symbols, separators=(",", ":"))}, "binance_exchange_info"
    )
    indexed = {}
    if isinstance(info, dict) and isinstance(info.get("symbols"), list):
        try:
            indexed = {row["symbol"]: row for row in info["symbols"]}
            if len(indexed) != len(info["symbols"]):
                indexed = {}
        except (KeyError, TypeError):
            indexed = {}
    for symbol in symbols:
        status = {"symbol": symbol, "status": "NOT_ATTEMPTED", "missing_bar_open_times": []}
        result["symbol_status"].append(status)
        if blocked:
            status["reason"] = "PROVIDER_STOPPED"
            continue
        instrument = indexed.get(symbol)
        if (not instrument or instrument.get("quoteAsset") != "USDT"
                or not isinstance(instrument.get("baseAsset"), str)
                or instrument["baseAsset"] + "USDT" != symbol
                or instrument.get("status") != "TRADING"
                or instrument.get("isSpotTradingAllowed") is False):
            status.update(status="FAILED", reason="MISSING_OR_INELIGIBLE_AS_OF_SPOT_METADATA")
            continue
        result["instruments"].append({"venue": VENUE, "symbol": symbol,
                                      "base_asset": instrument.get("baseAsset"), "quote_asset": "USDT",
                                      "trading_status": instrument["status"],
                                      "evidence_id": metadata["evidence_id"],
                                      "metadata_received_at": metadata["received_at"]})
        candles, evidence, candle_request = request(
            "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": bars,
                               "startTime": int(start.timestamp()) * 1000,
                               "endTime": int(end.timestamp()) * 1000 - 1}, "binance_intraday_klines"
        )
        rows = []
        if candles is not None:
            try:
                rows, excluded = _bars(candles, symbol, interval, start, end, evidence)
                result["bars"].extend(rows)
                result["excluded_bars"].extend(excluded)
            except (ValueError, TypeError, KeyError) as exc:
                status["reason"] = str(exc)
                candle_request["validation_status"] = "INVALID_CANDLES"
        expected = {utc_text(start + timedelta(seconds=step * i)) for i in range(bars)}
        status["missing_bar_open_times"] = sorted(expected - {row["open_time"] for row in rows})
        quote_ok = False
        if not blocked:
            book, evidence, book_request = request("/api/v3/ticker/bookTicker", {"symbol": symbol}, "binance_book_ticker")
            if book is not None:
                try:
                    result["quotes"].append(_quote(book, symbol, evidence, book_request["request_started_at"]))
                    quote_ok = True
                except (ValueError, TypeError) as exc:
                    status["quote_reason"] = str(exc)
                    book_request["validation_status"] = "INVALID_QUOTE"
        depth_ok = not include_depth
        if include_depth and not blocked:
            book, evidence, depth_request = request("/api/v3/depth", {"symbol": symbol, "limit": 100}, "binance_depth")
            if book is not None:
                try:
                    result["depth"].append(_depth(book, symbol, evidence))
                    depth_ok = True
                except (ValueError, TypeError) as exc:
                    status["depth_reason"] = str(exc)
                    depth_request["validation_status"] = "INVALID_DEPTH"
        status["status"] = "COMPLETE" if not status["missing_bar_open_times"] and quote_ok and depth_ok else "PARTIAL" if rows or quote_ok else "FAILED"
    completed = utc_text(_clock_time(clock))
    capture_elapsed = monotonic_ns() - capture_start_ns
    result.update(as_of=completed, captured_at=completed, completed_at=completed,
                  elapsed_ns=capture_elapsed if capture_elapsed >= 0 else None)
    counts = {name.lower(): sum(row["status"] == name for row in result["symbol_status"])
              for name in ("COMPLETE", "PARTIAL", "FAILED", "NOT_ATTEMPTED")}
    result["coverage"] = {"requested": len(symbols), **counts,
                          "status": "COMPLETE_SELECTED_UNIVERSE" if counts["complete"] == len(symbols) else "PARTIAL"}
    result["status"] = "BLOCKED" if blocked else "COLLECTED" if counts["complete"] == len(symbols) else "PARTIAL"
    _write_immutable(output, _canonical(result))
    return load_intraday(output, root)


def load_intraday(path: str | Path, evidence_root: str | Path) -> dict:
    """Verify version, immutable raw bytes, membership and observation chronology."""
    raw = Path(path).read_bytes()
    value = _json(raw)
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotError("unsupported intraday capture schema")
    _config(value["symbols_requested"], value["interval"], value["requested_bars"], 12)
    if value.get("entry_permission") is not False or value.get("threshold_crossing_at") is not None:
        raise SnapshotError("collector observations cannot grant entry or invent a detector crossing")
    root = Path(evidence_root)
    cutoff = parse_time(value["as_of"])
    started = parse_time(value["started_at"])
    if not parse_time(value["scheduled_at"]) <= started <= cutoff:
        raise SnapshotError("invalid intraday capture chronology")
    membership_path = root / value["membership_path"]
    if root.resolve() not in membership_path.resolve().parents:
        raise SnapshotError("membership path escapes evidence root")
    membership_raw = membership_path.read_bytes()
    if "universe_" + hashlib.sha256(membership_raw).hexdigest() != value["membership_snapshot_id"]:
        raise SnapshotError("membership hash mismatch")
    membership = _json(membership_raw)
    if (membership["symbols"] != value["symbols_requested"]
            or membership["frozen_at"] != value["started_at"]
            or any(membership[key] != value[key] for key in
                   ("scheduled_at", "interval", "requested_bars", "evidence_kind", "window_start_at", "window_end_at"))):
        raise SnapshotError("membership does not match capture")
    # HTTP error bodies need not be JSON. Verify exact byte/receipt integrity,
    # then parse only successful responses when reconciling their output rows.
    evidence_by_id, raw_by_id = {}, {}
    for entry in value["evidence"]:
        if entry["evidence_id"] in evidence_by_id:
            raise SnapshotError("duplicate intraday evidence id")
        source = urllib.parse.urlparse(entry["source_url"])
        if (source.scheme != "https" or source.hostname != "api.binance.com"
                or source.path not in PATHS or source.username or source.password
                or source.port not in (None, 443)):
            raise SnapshotError("intraday evidence is not from the declared provider")
        evidence_path = root / entry["path"]
        if root.resolve() not in evidence_path.resolve().parents:
            raise SnapshotError("evidence path escapes root")
        body = evidence_path.read_bytes()
        if hashlib.sha256(body).hexdigest() != entry["sha256"] or len(body) != entry["size_bytes"]:
            raise SnapshotError("intraday evidence hash mismatch")
        identity = hashlib.sha256(_canonical({k: v for k, v in entry.items() if k != "evidence_id"})).hexdigest()
        if entry["evidence_id"] != "ev_" + identity or (root / "receipts" / f"{identity}.json").read_bytes() != _canonical(entry):
            raise SnapshotError("intraday evidence receipt mismatch")
        if not started <= parse_time(entry["received_at"]) <= cutoff:
            raise SnapshotError("future or pre-capture evidence receipt")
        evidence_by_id[entry["evidence_id"]] = entry
        if entry["request"].get("http_status") == 200:
            try:
                raw_by_id[entry["evidence_id"]] = _json(body)
            except SnapshotError:
                pass  # A recorded invalid response is a failed request, not evidence for rows.
    for request in value["requests"]:
        first = parse_time(request["request_started_at"])
        last = parse_time(request["received_at"]) if request["received_at"] else parse_time(request["recorded_at"])
        if not started <= first <= last <= cutoff:
            raise SnapshotError("reversed request chronology")
        if request["evidence_id"] is not None:
            entry = evidence_by_id.get(request["evidence_id"])
            if entry is None or entry["received_at"] != request["received_at"]:
                raise SnapshotError("request evidence receipt mismatch")
            if entry["request"]["request_started_at"] != request["request_started_at"]:
                raise SnapshotError("request start differs from evidence receipt")
    instrument_symbols = set()
    for instrument in value["instruments"]:
        symbol = instrument["symbol"]
        entry = evidence_by_id.get(instrument.get("evidence_id"))
        payload = raw_by_id.get(instrument.get("evidence_id"))
        if (entry is None or not isinstance(payload, dict)
                or entry["kind"] != "binance_exchange_info"
                or symbol not in value["symbols_requested"] or symbol in instrument_symbols):
            raise SnapshotError("instrument lacks unique requested exchange metadata")
        matches = [row for row in payload.get("symbols", []) if row.get("symbol") == symbol]
        if len(matches) != 1:
            raise SnapshotError("instrument identity absent from exchange metadata")
        original = matches[0]
        expected_instrument = {"venue": VENUE, "symbol": symbol, "base_asset": original.get("baseAsset"),
                               "quote_asset": original.get("quoteAsset"), "trading_status": original.get("status"),
                               "evidence_id": entry["evidence_id"], "metadata_received_at": entry["received_at"]}
        if instrument != expected_instrument:
            raise SnapshotError("instrument differs from raw exchange metadata")
        instrument_symbols.add(symbol)
    for kind in ("bars", "quotes", "depth"):
        for row in value[kind]:
            entry = evidence_by_id.get(row.get("evidence_id"))
            payload = raw_by_id.get(row.get("evidence_id"))
            if entry is None or payload is None or row["symbol"] not in instrument_symbols:
                raise SnapshotError("intraday row lacks verified source evidence")
            if entry["request"].get("symbol") != row["symbol"]:
                raise SnapshotError("intraday source symbol mismatch")
            if kind == "bars":
                normalized, _ = _bars(payload, row["symbol"], value["interval"],
                                      parse_time(value["window_start_at"]), parse_time(value["window_end_at"]), entry)
                matches = [item for item in normalized if item["open_time"] == row["open_time"]]
                if len(matches) != 1 or matches[0] != row:
                    raise SnapshotError("intraday bar differs from raw evidence")
            elif kind == "quotes":
                if _quote(payload, row["symbol"], entry, entry["request"]["request_started_at"]) != row:
                    raise SnapshotError("intraday quote differs from raw evidence")
            elif _depth(payload, row["symbol"], entry) != row:
                raise SnapshotError("intraday depth differs from raw evidence")
    # Verify completeness against successful source responses, not just rows
    # the normalized capture happened to retain. Removing a row cannot improve
    # coverage or silently erase an inconvenient observation.
    expected = {"bars": [], "quotes": [], "depth": []}
    for request in value["requests"]:
        if request["status"] != "RECEIVED" or request.get("validation_status"):
            continue
        entry = evidence_by_id[request["evidence_id"]]
        payload = raw_by_id[request["evidence_id"]]
        symbol = request["symbol"]
        if request["endpoint"] == "/api/v3/klines":
            rows, _ = _bars(payload, symbol, value["interval"], parse_time(value["window_start_at"]),
                            parse_time(value["window_end_at"]), entry)
            expected["bars"].extend(rows)
        elif request["endpoint"] == "/api/v3/ticker/bookTicker":
            expected["quotes"].append(_quote(payload, symbol, entry, request["request_started_at"]))
        elif request["endpoint"] == "/api/v3/depth":
            expected["depth"].append(_depth(payload, symbol, entry))
    if any(value[kind] != expected[kind] for kind in expected):
        raise SnapshotError("intraday normalized row membership differs from source responses")
    if [row["symbol"] for row in value["symbol_status"]] != value["symbols_requested"]:
        raise SnapshotError("intraday coverage omitted requested members")
    opens = {utc_text(parse_time(value["window_start_at"]) + timedelta(seconds=INTERVAL_SECONDS[value["interval"]] * i))
             for i in range(value["requested_bars"])}
    for status in value["symbol_status"]:
        symbol = status["symbol"]
        symbol_bars = [row for row in value["bars"] if row["symbol"] == symbol]
        missing = sorted(opens - {row["open_time"] for row in symbol_bars})
        if status["status"] not in {"NOT_ATTEMPTED", "FAILED"} or "reason" not in status:
            if status["missing_bar_open_times"] != missing:
                raise SnapshotError("intraday missing-bar coverage differs from observations")
        quote_ok = any(row["symbol"] == symbol for row in value["quotes"])
        depth_ok = not value["include_depth"] or any(row["symbol"] == symbol for row in value["depth"])
        if status["status"] == "COMPLETE" and (missing or not quote_ok or not depth_ok):
            raise SnapshotError("intraday complete coverage claim lacks observations")
    counts = {name.lower(): sum(row["status"] == name for row in value["symbol_status"])
              for name in ("COMPLETE", "PARTIAL", "FAILED", "NOT_ATTEMPTED")}
    if (sum(counts.values()) != len(value["symbols_requested"])
            or value["coverage"]["requested"] != len(value["symbols_requested"])
            or any(value["coverage"][name] != count for name, count in counts.items())):
        raise SnapshotError("intraday coverage denominator mismatch")
    complete = counts["complete"] == len(value["symbols_requested"])
    expected_status = ("BLOCKED" if any(row["status"] == "BLOCKED" for row in value["requests"])
                       else "COLLECTED" if complete else "PARTIAL")
    if (value["status"] != expected_status
            or value["coverage"]["status"] != ("COMPLETE_SELECTED_UNIVERSE" if complete else "PARTIAL")):
        raise SnapshotError("intraday overall status differs from coverage")
    for row in value["bars"]:
        if not parse_time(row["open_time"]) < parse_time(row["bar_end_at"]) <= parse_time(value["window_end_at"]) <= started:
            raise SnapshotError("incomplete or future intraday candle")
    value["capture_sha256"] = hashlib.sha256(raw).hexdigest()
    return value

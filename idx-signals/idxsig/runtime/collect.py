"""Explicit, read-only Binance spot snapshot collection. No account/order API.

The fixed-host public client records exact bytes and local receipt timestamps.
Network calls only occur when collect_binance_spot is explicitly invoked, or the
CLI receives --public-binance. Imports and synthetic demo paths are offline.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .data import (
    SCHEMA_VERSION,
    VENUE,
    SnapshotError,
    _milliseconds,
    _write_immutable,
    capture_raw_evidence,
    load_recorded_snapshot,
    utc_text,
)

HOST = "https://api.binance.com"
PATHS = {"/api/v3/exchangeInfo", "/api/v3/klines", "/api/v3/ticker/bookTicker"}
MAX_RESPONSE = 8 * 1024 * 1024


class PublicDataUnavailable(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PublicDataUnavailable("public provider redirected; request refused")


def _fetch(
    path: str, params: dict, evidence_root: Path, kind: str, *, timeout: float = 12.0
) -> tuple[object, dict, str]:
    if path not in PATHS:
        raise PublicDataUnavailable("unsupported public endpoint")
    query = urllib.parse.urlencode(params)
    url = HOST + path + ("?" + query if query else "")
    started = utc_text(datetime.now(timezone.utc))
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "KOD-recorded-research/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req, timeout=timeout) as response:
            if response.status != 200:
                raise PublicDataUnavailable(f"public provider returned HTTP {response.status}")
            raw = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as exc:
        raise PublicDataUnavailable(f"public provider unavailable: HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PublicDataUnavailable(f"public provider unavailable: {type(exc).__name__}") from None
    if len(raw) > MAX_RESPONSE:
        raise PublicDataUnavailable("public provider response too large")
    received = utc_text(datetime.now(timezone.utc))
    evidence = capture_raw_evidence(
        raw,
        evidence_root,
        source_url=url,
        received_at=received,
        kind=kind,
        request={**params, "request_started_at": started},
    )
    try:
        payload = json.loads(
            raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
        )
    except (ValueError, UnicodeDecodeError):
        raise PublicDataUnavailable("public provider returned invalid JSON") from None
    if isinstance(payload, dict) and "code" in payload and "msg" in payload:
        raise PublicDataUnavailable(f"public provider error code {payload['code']}")
    return payload, evidence, started


def collect_binance_spot(
    output_path: str | Path,
    evidence_root: str | Path,
    symbols: list[str],
    *,
    days: int = 120,
    timeout: float = 12.0,
) -> dict:
    """Collect a finite selected-symbol snapshot; does not claim whole-market coverage.

    Every completed bar is retrieved now; this is not a reconstruction of what
    the provider would have reported at a historical cutoff. Missing inputs stop
    collection, and an unavailable provider is never replaced with synthetic data.
    """
    if not symbols or len(symbols) > 30 or len(set(symbols)) != len(symbols):
        raise SnapshotError("provide 1 to 30 distinct explicit symbols")
    if any(not re.fullmatch(r"[A-Z0-9]{3,30}", s) or not s.endswith("USDT") for s in symbols):
        raise SnapshotError("only explicit uppercase USDT symbols are supported")
    if not 40 <= days <= 365:
        raise SnapshotError("days must be between 40 and 365")
    root = Path(evidence_root)
    info, info_evidence, _ = _fetch(
        "/api/v3/exchangeInfo",
        {"symbols": json.dumps(symbols, separators=(",", ":"))},
        root,
        "binance_exchange_info",
        timeout=timeout,
    )
    if not isinstance(info, dict) or not isinstance(info.get("symbols"), list):
        raise PublicDataUnavailable("invalid exchange metadata response")
    symbol_info = {r["symbol"]: r for r in info["symbols"]}
    instruments, bars, quotes = [], [], []
    evidence = [info_evidence]
    exclusions = []
    for symbol in symbols:
        if symbol not in symbol_info:
            raise PublicDataUnavailable(f"requested instrument missing: {symbol}")
        r = symbol_info[symbol]
        if r.get("quoteAsset") != "USDT" or r.get("isSpotTradingAllowed") is False:
            raise PublicDataUnavailable(f"instrument is not supported USDT spot: {symbol}")
        filters = {f["filterType"]: f for f in r.get("filters", [])}
        lot = filters.get("LOT_SIZE", {})
        notion = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
        instrument = {
            "venue": VENUE,
            "symbol": symbol,
            "base_asset": r["baseAsset"],
            "quote_asset": r["quoteAsset"],
            "asset_class": "crypto",
            "tick_size": filters.get("PRICE_FILTER", {}).get("tickSize"),
            "lot_step": lot.get("stepSize"),
            "min_qty": lot.get("minQty"),
            "max_qty": lot.get("maxQty"),
            "min_notional": notion.get("minNotional"),
            "max_notional": notion.get("maxNotional"),
            "trading_status": r["status"],
            "metadata_received_at": info_evidence["received_at"],
            "evidence_id": info_evidence["evidence_id"],
            "raw_filters": r.get("filters", []),
            "session_model": "24/7 UTC",
        }
        instruments.append(instrument)
        candles, candle_evidence, _ = _fetch(
            "/api/v3/klines",
            {"symbol": symbol, "interval": "1d", "limit": days + 1},
            root,
            "binance_klines",
            timeout=timeout,
        )
        evidence.append(candle_evidence)
        if not isinstance(candles, list):
            raise PublicDataUnavailable("invalid candle response")
        # No close or volume from the still-forming daily candle enters a snapshot.
        receipt = datetime.fromisoformat(candle_evidence["received_at"].replace("Z", "+00:00"))
        complete = []
        for candle in candles:
            if not isinstance(candle, list) or len(candle) < 8:
                raise PublicDataUnavailable("malformed candle response")
            close_time = _milliseconds(candle[6])
            if datetime.fromisoformat(close_time.replace("Z", "+00:00")) > receipt:
                exclusions.append(
                    {
                        "symbol": symbol,
                        "open_time": _milliseconds(candle[0]),
                        "reason": "FORMING_BAR",
                    }
                )
                continue
            complete.append(
                {
                    "venue": VENUE,
                    "symbol": symbol,
                    "open_time": _milliseconds(candle[0]),
                    "close_time": close_time,
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "base_volume": candle[5],
                    "quote_volume": candle[7],
                    "received_at": candle_evidence["received_at"],
                    "evidence_id": candle_evidence["evidence_id"],
                }
            )
        bars.extend(complete[-days:])
        book, book_evidence, started = _fetch(
            "/api/v3/ticker/bookTicker",
            {"symbol": symbol},
            root,
            "binance_book_ticker",
            timeout=timeout,
        )
        evidence.append(book_evidence)
        if not isinstance(book, dict) or book.get("symbol") != symbol:
            raise PublicDataUnavailable("invalid book-ticker identity")
        quotes.append(
            {
                "venue": VENUE,
                "symbol": symbol,
                "bid": book["bidPrice"],
                "ask": book["askPrice"],
                "bid_size": book["bidQty"],
                "ask_size": book["askQty"],
                "source_time": None,
                "source_time_basis": "UNAVAILABLE",
                "request_started_at": started,
                "received_at": book_evidence["received_at"],
                "evidence_id": book_evidence["evidence_id"],
                "observation_id": "book_" + book_evidence["evidence_id"],
            }
        )
    cutoff = utc_text(datetime.now(timezone.utc))
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": cutoff,
        "as_of": cutoff,
        "evidence_kind": "public_market",
        "instruments": instruments,
        "bars": bars,
        "quotes": quotes,
        "evidence": evidence,
        "collection": {
            "provider": "Binance spot public GET",
            "symbols_requested": symbols,
            "coverage_status": "SELECTED_SYMBOLS_ONLY",
            "requested_daily_bars_per_symbol": days,
            "excluded_bars": exclusions,
            "note": "Book ticker has no exchange source timestamp; local receipt is observed availability only.",
        },
    }
    encoded = (json.dumps(snapshot, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    _write_immutable(Path(output_path), encoded)
    return load_recorded_snapshot(output_path, cutoff, root)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public-binance",
        action="store_true",
        help="explicitly perform selected-symbol public GET requests",
    )
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--days", type=int, default=120)
    args = parser.parse_args(argv)
    if not args.public_binance:
        parser.error("collection is OFF; --public-binance is required")
    try:
        result = collect_binance_spot(args.output, args.evidence_root, args.symbols, days=args.days)
    except (PublicDataUnavailable, SnapshotError) as exc:
        print(json.dumps({"status": "UNAVAILABLE", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "COLLECTED",
                "as_of": result["as_of"],
                "snapshot_sha256": result["snapshot_sha256"],
                "instruments": len(result["instruments"]),
                "bars": len(result["bars"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

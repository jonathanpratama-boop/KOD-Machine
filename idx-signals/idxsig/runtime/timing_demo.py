"""Offline wiring example for timing, catalysts, quotes, account and recovery."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..timing_context import context_fixture
from .data import utc_text
from .demo import demo
from .intraday import PublicResponse
from .storage import immutable_json, locked, read_json
from .timing import capture_intraday, publish_board, retain_context, timing_status

DEMO_TIME = datetime(2026, 11, 2, 12, 3, tzinfo=timezone.utc)


def synthetic_fetcher(endpoint, params, *, timeout):
    """Invented public-response shapes; this function cannot make a request."""
    if endpoint.endswith("/time"):
        value = {"serverTime": int(DEMO_TIME.timestamp() * 1000)}
    elif endpoint.endswith("/exchangeInfo"):
        value = {"symbols": [{"symbol": symbol, "baseAsset": symbol[:-4],
            "quoteAsset": "USDT", "status": "TRADING", "isSpotTradingAllowed": True}
            for symbol in json.loads(params["symbols"])]}
    elif endpoint.endswith("/klines"):
        value = []
        for minutes in (2, 1):
            opened = DEMO_TIME - timedelta(minutes=minutes)
            value.append([int(opened.timestamp() * 1000), "100", "106", "99", "105",
                          "20", int((opened + timedelta(minutes=1)).timestamp() * 1000) - 1, "2000"])
    elif endpoint.endswith("/bookTicker"):
        value = {"symbol": params["symbol"], "bidPrice": "100", "askPrice": "101",
                 "bidQty": "10", "askQty": "10"}
    elif endpoint.endswith("/depth"):
        value = {"lastUpdateId": 1, "bids": [["100", "10"]], "asks": [["101", "10"]]}
    else:
        raise ValueError("unsupported synthetic endpoint")
    return PublicResponse(200, json.dumps(value, sort_keys=True).encode())


def timing_demo(root):
    root = Path(root)
    saved = root / "timing" / "synthetic_demo.json"
    if saved.exists():
        timing_status(root)
        return read_json(saved)
    # This existing demonstration retains its original policy, account and IDs.
    economic = demo(root)
    capture = capture_intraday(root, scheduled_at=utc_text(DEMO_TIME), symbols=["BTCUSDT", "ETHUSDT"],
        bars=2, fetcher=synthetic_fetcher, clock=lambda: utc_text(DEMO_TIME), evidence_kind="synthetic")
    context = context_fixture()
    retained = retain_context(root, context, as_of=context["as_of"], evidence_kind="synthetic")
    board = publish_board(root)
    result = {"schema_version": "KOD_TIMING_DEMO_V1", "synthetic": True, "network": False,
              "run_id": economic["payload"]["run"]["id"], "capture_attempt_id": capture["attempt_id"],
              "context_id": retained["id"], "board_sha256": board["sha256"],
              "attempts": board["payload"]["summary"]["attempts"],
              "entry_permission": False, "profitability_validated": False}
    with locked(root):
        immutable_json(saved, result)
    return result

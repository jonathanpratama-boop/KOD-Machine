"""Deterministic synthetic wiring demonstration; never a market result."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from .coordinator import run_once
from .data import SCHEMA_VERSION, utc_text
from .storage import immutable_json, locked

T0 = "2026-11-02T00:00:10Z"
T1 = "2026-11-02T00:00:20Z"


def fixtures():
    profile = {
        "id": "KOD_SYNTHETIC_DEMO_V1",
        "evidence_type": "synthetic",
        "venue": "SYNTHETIC_SPOT",
        "quote_currency": "USDT",
        "initial_cash": "1000",
        "fee_rate": "0.001",
        "slippage": "0.001",
        "max_quote_age": 120,
        "expiry": 3600,
        "initialized_at": T0,
        "instruments": {},
    }
    instruments, bars = [], []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        meta = {
            "tick_size": "0.01",
            "lot_step": "0.001",
            "min_notional": "5",
            "trading_status": "TRADING",
            "metadata_received_at": "2026-11-01T00:00:00Z",
            "evidence_id": "demo:metadata",
        }
        profile["instruments"][symbol] = meta.copy()
        instruments.append(
            dict(
                meta,
                symbol=symbol,
                venue="SYNTHETIC_SPOT",
                base_asset=symbol[:-4],
                quote_asset="USDT",
                asset_class="crypto",
            )
        )
        for i in range(40):
            opened = datetime(2026, 9, 23, tzinfo=timezone.utc) + timedelta(days=i)
            value = Decimal(100 + i) + Decimal(i % 3) / 3
            if i == 39:
                value += 10
            bars.append(
                {
                    "symbol": symbol,
                    "venue": "SYNTHETIC_SPOT",
                    "open_time": utc_text(opened),
                    "close_time": utc_text(opened + timedelta(days=1)),
                    "received_at": utc_text(opened + timedelta(days=1)),
                    "open": str(value),
                    "high": str(value + 1),
                    "low": str(value - 1),
                    "close": str(value),
                    "base_volume": "10000",
                    "quote_volume": "1000000",
                    "evidence_id": f"demo:bar:{symbol}:{i}",
                }
            )
    snapshots = []
    for at in (T0, T1):
        quotes = [
            {
                "symbol": s,
                "venue": "SYNTHETIC_SPOT",
                "bid": "149.00",
                "ask": "149.01",
                "bid_size": "1000",
                "ask_size": "1000",
                "source_time": at,
                "received_at": at,
                "evidence_id": f"demo:quote:{s}:{at}",
                "observation_id": f"demo:quote:{s}:{at}",
            }
            for s in ("BTCUSDT", "ETHUSDT")
        ]
        snapshots.append(
            {
                "schema_version": SCHEMA_VERSION,
                "evidence_kind": "synthetic",
                "captured_at": at,
                "instruments": instruments,
                "bars": bars,
                "quotes": quotes,
                "evidence": [],
            }
        )
    return profile, snapshots


def demo(root):
    root = Path(root)
    profile, snapshots = fixtures()
    source = root / "demo_inputs"
    with locked(root):
        immutable_json(source / "profile.json", profile)
        for i, snapshot in enumerate(snapshots):
            immutable_json(source / f"snapshot-{i}.json", snapshot)
    for i, at in enumerate((T0, T1)):
        result = run_once(root, source / f"snapshot-{i}.json", source / "profile.json", at)
    return result

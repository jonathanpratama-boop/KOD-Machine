#!/usr/bin/env python3
"""Append today's TREND_CORE_PAPER_v1 decision for BTC and ETH to ledger.jsonl (hash-chained, append-only).

Usage: log_decision.py [YYYY-MM-DD]   (signal date = last completed UTC daily bar; default yesterday UTC)
"""
import datetime as dt
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backtests"))
import lib  # noqa: E402
from signal_today import extend_with_daily  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ledger.jsonl")


def last_hash():
    if not os.path.exists(LEDGER):
        return "0" * 64
    with open(LEDGER, "rb") as f:
        lines = [l for l in f.read().split(b"\n") if l.strip()]
    return hashlib.sha256(lines[-1]).hexdigest() if lines else "0" * 64


def main():
    sig_date = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    prev = last_hash()
    for sym in ["BTCUSDT", "ETHUSDT"]:
        df = lib.load_klines("spot", sym, "1d")
        n_monthly = len(df)
        df = extend_with_daily(df, sym, sig_date)
        if df.index[-1].date() != sig_date:
            rec = {"protocol": "TREND_CORE_PAPER_v1", "symbol": sym, "signal_date": sig_date.isoformat(), "action": "MISSED",
                   "reason": f"last available bar {df.index[-1].date()}", "prev_sha256": prev}
        else:
            c = df["close"]
            sma10, sma40 = c.rolling(10).mean().iloc[-1], c.rolling(40).mean().iloc[-1]
            sigma20 = float(np.log(c).diff().iloc[-20:].std())
            long = bool(sma10 > sma40)
            frac = min(1.0, 0.015 / sigma20) if long else 0.0
            prev_long = bool(c.rolling(10).mean().iloc[-2] > c.rolling(40).mean().iloc[-2])
            action = "HOLD" if long == prev_long else ("BUY_NEXT_OPEN" if long else "SELL_TO_CASH_NEXT_OPEN")
            rec = {"protocol": "TREND_CORE_PAPER_v1", "symbol": sym, "signal_date": sig_date.isoformat(),
                   "close": round(float(c.iloc[-1]), 2), "sma10": round(float(sma10), 2), "sma40": round(float(sma40), 2),
                   "sigma20_daily": round(sigma20, 5), "state": "LONG" if long else "CASH",
                   "target_fraction": round(float(frac), 4), "action": action,
                   "data_source": "monthly_archive" if len(df) == n_monthly else "monthly_archive+daily_files",
                   "logged_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prev_sha256": prev}
        line = json.dumps(rec, sort_keys=True)
        with open(LEDGER, "a") as f:
            f.write(line + "\n")
        prev = hashlib.sha256(line.encode()).hexdigest()
        print(line)


if __name__ == "__main__":
    main()

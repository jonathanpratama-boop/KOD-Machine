#!/usr/bin/env python3
"""Daily state of the FRESH_EYES_v1 trend rules on BTC and ETH spot, for the paper ledger.

Pulls Binance Vision DAILY kline files (published the next UTC day) to extend the monthly archive, then prints the
position each frozen rule would hold from the next open, with the inputs that decided it. Nothing is ordered. The
output is meant to be appended, unchanged, to a paper log before the next session's open.

Usage: signal_today.py [YYYY-MM-DD]   (default: yesterday UTC, the last completed daily bar)
"""
import datetime as dt
import io
import os
import sys
import urllib.request
import zipfile

import numpy as np
import pandas as pd

import lib
from run_t1_t5 import donchian_positions, sma_cross_positions, tsmom_positions

DAILY = "https://data.binance.vision/data/spot/daily/klines/{sym}/1d/{sym}-1d-{d}.zip"


def extend_with_daily(df, sym, upto):
    last = df.index[-1].date()
    d = last + dt.timedelta(days=1)
    rows = []
    while d <= upto:
        url = DAILY.format(sym=sym, d=d.isoformat())
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                raw = r.read()
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                csv = z.read(z.namelist()[0])
            first = csv.split(b"\n", 1)[0]
            t = pd.read_csv(io.BytesIO(csv), header=0 if first[:1].isalpha() else None)
            t.columns = lib.KCOLS[: t.shape[1]]
            t["time"] = lib._to_dt(t["open_time"])
            rows.append(t.set_index("time")[["open", "high", "low", "close", "volume", "quote_volume"]].astype(float))
        except Exception as e:  # noqa: a missing day is reported, not invented
            print(f"  {sym} {d}: not available ({type(e).__name__})", file=sys.stderr)
        d += dt.timedelta(days=1)
    if rows:
        df = pd.concat([df] + rows).sort_index()
        df = df[~df.index.duplicated(keep="last")]
    return df


def main():
    upto = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    for sym in ["BTCUSDT", "ETHUSDT"]:
        df = lib.load_klines("spot", sym, "1d")
        df = extend_with_daily(df, sym, upto)
        c = df["close"]
        sma10, sma40 = c.rolling(10).mean(), c.rolling(40).mean()
        hh20, ll10 = df["high"].rolling(20).max().shift(1), df["low"].rolling(10).min().shift(1)
        r28 = c / c.shift(28) - 1
        rules = {
            "T1c_sma10_40 (PASS on ETH, WEAK on BTC)": sma_cross_positions(df, 10, 40),
            "T1a_donchian20_10 (WEAK)": donchian_positions(df, 20, 10, "channel"),
            "T1b_tsmom28_hold5 (PASS fragile on ETH)": tsmom_positions(df, 28, 5),
        }
        last = df.index[-1]
        print(f"\n{sym}  last completed bar {last.date()}  close {c.iloc[-1]:.2f}")
        print(f"  SMA10 {sma10.iloc[-1]:.2f}  SMA40 {sma40.iloc[-1]:.2f}  20d-high(prior) {hh20.iloc[-1]:.2f}  10d-low(prior) {ll10.iloc[-1]:.2f}  28d-return {r28.iloc[-1]:+.2%}")
        for name, pos in rules.items():
            now, prev = pos.iloc[-1], pos.iloc[-2]
            action = "HOLD" if now == prev else ("BUY at next open" if now > prev else "SELL to cash at next open")
            print(f"  {name:45s} position from next open: {'LONG' if now else 'CASH'}  ({action})")
        print(f"  Data through {last.date()}; a bar later than {upto} was not requested.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""T1 (trend, BTC/ETH spot, long-flat) and T5 (exit comparison) per PROTOCOL.md. Rules fixed in the protocol."""
import json
import sys

import numpy as np
import pandas as pd

import lib

SPOT_SIDE = 0.0015         # 0.10% fee + 0.05% slippage per side
ETORO_SIDE = 0.0100
PERIODS = {"dev": ("2017-08-17", "2022-12-31"), "val": ("2023-01-01", "2026-10-31")}


def donchian_positions(df, entry_n=20, exit_n=10, exit_mode="channel", atr_mult=2.0, stop_pct=0.05, time_n=10):
    """Long-flat state machine. Decision at close of bar t; returns target position for bar t (applied t+1 open)."""
    hh = df["high"].rolling(entry_n).max().shift(1)
    ll = df["low"].rolling(exit_n).min().shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - df["close"].shift(1)).abs(),
                    (df["low"] - df["close"].shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    close = df["close"].values
    pos = np.zeros(len(df))
    in_pos, entry_px, peak, bars = False, 0.0, 0.0, 0
    for i in range(len(df)):
        c = close[i]
        if in_pos:
            bars += 1
            peak = max(peak, c)
            exit_now = False
            if exit_mode == "channel":
                exit_now = c < ll.iloc[i]
            elif exit_mode == "atr_trail":
                exit_now = c < peak - atr_mult * atr.iloc[i]
            elif exit_mode == "fixed_stop_plus_channel":
                exit_now = (c < entry_px * (1 - stop_pct)) or (c < ll.iloc[i])
            elif exit_mode == "time":
                exit_now = bars >= time_n
            if exit_now:
                in_pos = False
        if not in_pos and not np.isnan(hh.iloc[i]) and c > hh.iloc[i]:
            in_pos, entry_px, peak, bars = True, c, c, 0
        pos[i] = 1.0 if in_pos else 0.0
    return pd.Series(pos, index=df.index)


def tsmom_positions(df, lookback=28, hold=5):
    r = df["close"] / df["close"].shift(lookback) - 1
    sig = (r > 0).astype(float)
    sig[r.isna()] = 0.0
    # re-evaluate every `hold` bars; hold the decision in between
    keep = pd.Series(np.arange(len(df)) % hold == 0, index=df.index)
    out = sig.where(keep).ffill().fillna(0.0)
    return out


def sma_cross_positions(df, fast=10, slow=40):
    f, s = df["close"].rolling(fast).mean(), df["close"].rolling(slow).mean()
    return (f > s).astype(float).where(s.notna(), 0.0)


def sma_filter_positions(df, n=200):
    s = df["close"].rolling(n).mean()
    return (df["close"] > s).astype(float).where(s.notna(), 0.0)


def evaluate(df, pos, side, label, results):
    for pname, (a, b) in PERIODS.items():
        out = lib.run_positions(df, pos, side, start=a, end=b)
        bh = lib.run_positions(df, pd.Series(1.0, index=df.index), 0.0, start=a, end=b)
        st = lib.stats(out["net"], 365, out["pos"])
        st["by_year"] = lib.by_year(out["net"])
        st["bh_Sharpe"] = lib.stats(bh["net"], 365)["Sharpe"]
        st["bh_MaxDD"] = lib.stats(bh["net"], 365)["MaxDD"]
        st["bh_CAGR"] = lib.stats(bh["net"], 365)["CAGR"]
        results[f"{label}|{pname}"] = st


def main():
    results = {}
    for sym in ["BTCUSDT", "ETHUSDT"]:
        df = lib.load_klines("spot", sym, "1d")
        variants = {
            "T1a_donchian20_10": donchian_positions(df, 20, 10, "channel"),
            "T1b_tsmom28_hold5": tsmom_positions(df, 28, 5),
            "T1c_sma10_40": sma_cross_positions(df, 10, 40),
            "T1d_sma200": sma_filter_positions(df, 200),
        }
        for name, pos in variants.items():
            evaluate(df, pos, SPOT_SIDE, f"{sym}|{name}|binance", results)
            evaluate(df, pos, ETORO_SIDE, f"{sym}|{name}|etoro", results)
        # T5 exits on the T1a entry
        exits = {
            "T5i_channel10": donchian_positions(df, 20, 10, "channel"),
            "T5ii_atr2_trail": donchian_positions(df, 20, 10, "atr_trail", atr_mult=2.0),
            "T5iii_fixed5pct_plus_channel": donchian_positions(df, 20, 10, "fixed_stop_plus_channel", stop_pct=0.05),
            "T5iv_time10": donchian_positions(df, 20, 10, "time", time_n=10),
        }
        for name, pos in exits.items():
            evaluate(df, pos, SPOT_SIDE, f"{sym}|{name}|binance", results)
    # verdicts for T1 per protocol
    verdict = {}
    for sym in ["BTCUSDT", "ETHUSDT"]:
        for v in ["T1a_donchian20_10", "T1b_tsmom28_hold5", "T1c_sma10_40", "T1d_sma200"]:
            ok = []
            for p in ["dev", "val"]:
                r = results[f"{sym}|{v}|binance|{p}"]
                ok.append(r["Sharpe"] > r["bh_Sharpe"] and r["MaxDD"] > r["bh_MaxDD"])
            verdict[f"{sym}|{v}"] = "PASS" if all(ok) else ("WEAK" if any(ok) else "FAIL")
    json.dump({"results": results, "T1_verdicts": verdict}, open("results_t1_t5.json", "w"), indent=1)
    # compact table
    rows = []
    for k, r in results.items():
        sym, v, cost, p = k.split("|")
        rows.append((sym, v, cost, p, r["CAGR"], r["Sharpe"], r["MaxDD"], r.get("trades_per_year"), r["bh_CAGR"], r["bh_Sharpe"], r["bh_MaxDD"]))
    t = pd.DataFrame(rows, columns=["sym", "variant", "cost", "period", "CAGR", "Sharpe", "MaxDD", "trades/yr", "BH_CAGR", "BH_Sharpe", "BH_MaxDD"])
    pd.set_option("display.width", 250)
    print(t.to_string(index=False))
    print(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()

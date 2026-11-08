#!/usr/bin/env python3
"""CRASH_BOUNCE_IDX_v1. See PROTOCOL.md.   python3 crash.py   -> results.json"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PANEL = HERE.parents[1] / "data/panel/panel-20261007T225823Z.csv.gz"
SEED, BOOT, MINVAL, MINCTRL = 20261108, 10000, 1e8, 20
COSTS = {"c1.5": 0.015, "c0.8": 0.008}


def load():
    df = pd.read_csv(PANEL, usecols=["date", "ticker", "previous", "high", "low", "close", "value"])
    for c in ("previous", "high", "low", "close", "value"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["previous", "high", "low", "close", "value"])
    df = df[(df.previous > 0) & (df.close > 0)]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"]).reset_index(drop=True)


def prep(df):
    g = df.groupby("ticker", sort=False)
    df["ret1"] = df.close / df.previous - 1
    df["cond"] = ((df.ret1 <= -0.07) & (df.close <= 1.001 * df.low) & (df.value >= MINVAL)).astype(float)
    prior = g.cond.transform(lambda x: x.shift(1).rolling(5, min_periods=1).max()).fillna(0)
    df["fresh"] = (df.cond == 1) & (prior == 0) & (g.cumcount() >= 20)
    df["recent_event"] = (df.cond == 1) | (prior == 1)       # event row, or an event in s-5..s-1
    c1, c2, c6 = g.close.shift(-1), g.close.shift(-2), g.close.shift(-6)
    d6 = g.date.shift(-6)
    df["ok"] = c6.notna() & ((d6 - df.date).dt.days <= 20)
    df["g5"] = c6 / c1 - 1
    df["g1"] = c2 / c1 - 1
    return df


def boot(vals, days, rng):
    d = pd.DataFrame({"v": vals, "d": days}).groupby("d").v.agg(["sum", "count"]).to_numpy()
    idx = rng.integers(0, len(d), (BOOT, len(d)))
    s = d[idx].sum(axis=1)
    m = s[:, 0] / s[:, 1]
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def trimmed(x):
    lo, hi = np.percentile(x, [1, 99]); return float(x[(x >= lo) & (x <= hi)].mean())


def summarise(ev, rng):
    out = {"n": len(ev), "n_dates": int(ev.date.nunique())}
    for cn, c in COSTS.items():
        net = ev.g5.to_numpy() - c
        out[cn] = dict(mean=float(net.mean()), ci95=boot(net, ev.date.to_numpy(), rng), median=float(np.median(net)),
                       trimmed_mean=trimmed(net), win_rate=float((net > 0).mean()))
    x = ev.dropna(subset=["ctrl5"])
    ex = x.g5.to_numpy() - x.ctrl5.to_numpy()
    out["excess"] = dict(n=len(x), mean=float(ex.mean()) if len(x) else None,
                         ci95=boot(ex, x.date.to_numpy(), rng) if len(x) else None,
                         control_mean_gross=float(x.ctrl5.mean()) if len(x) else None)
    out["gross_5"] = float(ev.g5.mean()); out["gross_1_session"] = float(ev.g1.mean())
    out["net_1_session_c1.5"] = float((ev.g1 - 0.015).mean())
    return out


def main():
    rng = np.random.default_rng(SEED)
    df = prep(load())
    ctrl_pool = df[(df.value >= MINVAL) & df.ok & ~df.recent_event]
    ctrl = ctrl_pool.groupby("date").g5.agg(["mean", "count"])
    ctrl = ctrl[ctrl["count"] >= MINCTRL]["mean"].rename("ctrl5")
    ev_all = df[df.fresh]
    unscorable = int((~ev_all.ok).sum())
    ev = ev_all[ev_all.ok].join(ctrl, on="date")
    ev["period"] = np.where(ev.date <= "2022-12-31", "A_2019_2022", "B_2023_2026")
    out = {"events_total": len(ev_all), "unscorable": unscorable, "periods": {}, "by_depth": {}, "by_liquidity": {}}
    for p, g in list(ev.groupby("period")) + [("pooled", ev)]:
        out["periods"][p] = summarise(g, rng)
    depth = pd.cut(ev.ret1, [-1.01, -0.15, -0.10, -0.07], labels=["below_-15", "-15_to_-10", "-10_to_-7"])
    for k, g in ev.groupby(depth, observed=True):
        out["by_depth"][str(k)] = dict(n=len(g), mean_net_c1_5=float((g.g5 - 0.015).mean()), median_net=float((g.g5 - 0.015).median()))
    liq = pd.qcut(ev.value, 3, labels=["low", "mid", "high"])
    for k, g in ev.groupby(liq, observed=True):
        out["by_liquidity"][str(k)] = dict(n=len(g), mean_net_c1_5=float((g.g5 - 0.015).mean()))
    P = out["periods"]
    passed = all(P[p]["c1.5"]["ci95"][0] > 0 and (P[p]["excess"]["ci95"] or [-1])[0] > 0 for p in ("A_2019_2022", "B_2023_2026"))
    out["verdict"] = "PASS" if passed else ("FIRM NO" if P["pooled"]["c0.8"]["ci95"][1] < 0 else "NOT PROVEN")
    (HERE / "results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

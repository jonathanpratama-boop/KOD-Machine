#!/usr/bin/env python3
"""BREADTH_v1: trade-count multiple vs dollar-volume multiple at ignition alerts. See PROTOCOL.md.

    python3 breadth.py          # writes results.json and prints it
"""
import glob
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPRO = HERE.parent / "HERMES_NOV3_REPRO_v1"
sys.path.insert(0, str(REPRO))
import lib  # noqa: E402

COST, THRESH, SEED, BOOT = 0.006, 2.0, 20261107, 10000


def trades_matrix(sg, name):
    cp = lib.CACHE / f"trades_{name}.pkl"
    if cp.exists():
        return pickle.load(open(cp, "rb"))
    cfg = lib.SEGMENTS[name]
    m = np.full((len(sg.syms), sg.T), np.nan)
    for fp in sorted(glob.glob(str(lib.RAW / "k1h" / "*.zip"))):
        b = os.path.basename(fp); s = b.split("-1h-")[0]; ym = b[-11:-4]
        if s not in sg.idx or not (cfg["months"][0] <= ym <= cfg["months"][1]):
            continue
        d = lib.read_zip(fp, [0, 8])
        ts = pd.to_datetime(d.iloc[:, 0].astype("int64"), unit="ms", utc=True)
        pos = sg.grid.get_indexer(ts)
        ok = pos >= 0
        m[sg.idx[s], pos[ok]] = d.iloc[:, 1].values[ok]
    pickle.dump(m, open(cp, "wb"), protocol=4)
    return m


def trade_multiple(N, T):
    """sum N over t-2..t / (3 x mean N over t-170..t-3), >= 150 of 168 present (same windows as lib.detect)."""
    n3 = N + lib.shift(N, 1) + lib.shift(N, 2)
    cs = np.concatenate([np.zeros((N.shape[0], 1)), np.nancumsum(np.nan_to_num(N), axis=1)], axis=1)
    cc = np.concatenate([np.zeros((N.shape[0], 1)), np.cumsum(np.isfinite(N).astype(float), axis=1)], axis=1)
    t = np.arange(T); lo = t - 170; hi = t - 2; valid = lo >= 0
    base = np.full_like(N, np.nan); nobs = np.full_like(N, np.nan)
    base[:, valid] = (cs[:, hi[valid]] - cs[:, lo[valid]]) / 168.0
    nobs[:, valid] = cc[:, hi[valid]] - cc[:, lo[valid]]
    base = np.where((nobs >= 150) & (base > 0), base, np.nan)
    return n3 / (3 * base)


def rows(name):
    sg = lib.Seg(name)
    det = lib.detect(sg)
    ev = pickle.load(open(lib.CACHE / f"alerts_{name}.pkl", "rb"))["ev_all"]
    N = trades_matrix(sg, name)
    tm = trade_multiple(N, sg.T)
    out, dropped = [], {"no_breadth": 0, "no_prices": 0}
    for i, t, status in ev:
        if status != "OK":
            continue
        B = tm[i, t] / det["vmult"][i, t]
        if not np.isfinite(B):
            dropped["no_breadth"] += 1; continue
        if t + 72 >= sg.T:
            dropped["no_prices"] += 1; continue
        ent, c24, c72 = sg.O[i, t + 1], sg.C[i, t + 24], sg.C[i, t + 72]
        if not (np.isfinite(ent) and ent > 0 and np.isfinite(c24)):
            dropped["no_prices"] += 1; continue
        hi24 = np.nanmax(sg.H[i, t + 1:t + 25])
        out.append(dict(sym=sg.syms[i], ts=sg.grid[t], day=sg.grid[t].date(), B=float(B),
                        tmult=float(tm[i, t]), vmult=float(det["vmult"][i, t]), base=float(det["base"][i, t]),
                        net24=c24 / ent - 1 - COST, hit30=float(hi24 >= 1.3 * ent),
                        net72=(c72 / ent - 1 - COST) if np.isfinite(c72) else np.nan))
    return pd.DataFrame(out), dropped


def day_boot(df, rng):
    days = df.day.unique()
    by = {d: g for d, g in df.groupby("day")}
    sums = {d: (g.net24[g.BROAD].sum(), g.BROAD.sum(), g.net24[~g.BROAD].sum(), (~g.BROAD).sum()) for d, g in by.items()}
    arr = np.array([sums[d] for d in days])
    diffs = np.empty(BOOT)
    for k in range(BOOT):
        s = arr[rng.integers(0, len(days), len(days))].sum(axis=0)
        diffs[k] = s[0] / s[1] - s[2] / s[3]
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def trimmed(x):
    lo, hi = np.percentile(x, [1, 99])
    return float(x[(x >= lo) & (x <= hi)].mean())


def summarise(df, dropped, rng):
    df["BROAD"] = df.B >= THRESH
    b, r = df[df.BROAD], df[~df.BROAD]
    lo, hi = day_boot(df, rng)
    res = dict(n=len(df), dropped=dropped, n_broad=len(b), share_broad=len(b) / len(df),
               B_median=float(df.B.median()),
               mean_net24_broad=float(b.net24.mean()), mean_net24_rest=float(r.net24.mean()),
               diff_mean_net24=float(b.net24.mean() - r.net24.mean()), ci95=[lo, hi], pass_period=lo > 0,
               median_net24_broad=float(b.net24.median()), median_net24_rest=float(r.net24.median()),
               trimmed_net24_broad=trimmed(b.net24.values), trimmed_net24_rest=trimmed(r.net24.values),
               hit30_broad=float(b.hit30.mean()), hit30_rest=float(r.hit30.mean()),
               mean_net72_broad=float(b.net72.mean()), mean_net72_rest=float(r.net72.mean()))
    df["liq3"] = pd.qcut(df.base, 3, labels=["low", "mid", "high"])
    res["by_liquidity"] = {str(k): dict(n_broad=int(g.BROAD.sum()), n_rest=int((~g.BROAD).sum()),
                                        diff_mean_net24=float(g.net24[g.BROAD].mean() - g.net24[~g.BROAD].mean()))
                           for k, g in df.groupby("liq3", observed=True)}
    df["Bq"] = pd.qcut(df.B, 5, labels=[f"Q{k}" for k in range(1, 6)])
    res["by_B_quintile"] = {str(k): dict(B_range=[float(g.B.min()), float(g.B.max())], n=len(g),
                                         mean_net24=float(g.net24.mean()), median_net24=float(g.net24.median()),
                                         hit30=float(g.hit30.mean()))
                            for k, g in df.groupby("Bq", observed=True)}
    return res


def one_live():
    """ONE's own B at the R2 trigger (hour 07:00-09:59Z, trigger t = 09:00 bar), from the live public kline file."""
    p = HERE / "one_klines_20261106.json"
    if not p.exists():
        return None
    k = json.loads(p.read_text())
    t = next(j for j, r in enumerate(k) if r[0] == 1793955600000)   # 2026-11-06 09:00Z bar
    N = np.array([float(r[8]) for r in k]); Q = np.array([float(r[7]) for r in k])
    nb, qb = N[t - 170:t - 2].mean(), Q[t - 170:t - 2].mean()
    tmult, vmult = N[t - 2:t + 1].sum() / (3 * nb), Q[t - 2:t + 1].sum() / (3 * qb)
    return dict(trade_multiple=tmult, dollar_multiple=vmult, B=tmult / vmult)


def main():
    rng = np.random.default_rng(SEED)
    out = {"protocol": "PROTOCOL.md", "threshold": THRESH, "periods": {}}
    for name in ("disc", "hold"):
        df, dropped = rows(name)
        out["periods"][name] = summarise(df, dropped, rng)
    out["pass"] = all(p["pass_period"] for p in out["periods"].values())
    out["one_live"] = one_live()
    (HERE / "results.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()

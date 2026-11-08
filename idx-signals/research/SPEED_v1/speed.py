#!/usr/bin/env python3
"""SPEED_v1: minute-level entry delay on crypto ignition alerts. See PROTOCOL.md.

    python3 speed.py sample   # draw the 2,000 events (no outcomes), write sample.json
    python3 speed.py fetch    # download the needed daily 1-minute kline archives into raw/
    python3 speed.py score    # compute results.json (run only after sample.json and the protocol are stamped)
"""
import concurrent.futures as cf
import datetime as dt
import json
import pickle
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPRO = HERE.parent / "HERMES_NOV3_REPRO_v1"
sys.path.insert(0, str(REPRO))
import lib  # noqa: E402

SEED, BOOT, PER_PERIOD = 20261108, 10000, 1000
ARMS = [0, 1, 5, 30, 240]
COSTS = {"cost_2.0": 0.02, "cost_0.6": 0.006}
RAW = HERE / "raw"
URL = "https://data.binance.vision/data/spot/daily/klines/{s}/1m/{s}-1m-{d}.zip"
MIN = dt.timedelta(minutes=1)


def sample():
    rng = np.random.default_rng(SEED)
    out = []
    for name in ("disc", "hold"):
        sg = lib.Seg(name)
        ev = [(i, t) for i, t, st in pickle.load(open(lib.CACHE / f"alerts_{name}.pkl", "rb"))["ev_all"] if st == "OK"]
        pick = sorted(rng.choice(len(ev), size=min(PER_PERIOD, len(ev)), replace=False))
        for k in pick:
            i, t = ev[k]
            S = sg.grid[t] + pd.Timedelta(hours=1)
            out.append(dict(period=name, sym=sg.syms[i], signal_at=S.isoformat(), close_3h_before=float(sg.C[i, t - 3])))
    (HERE / "sample.json").write_text(json.dumps(out, indent=0) + "\n")
    print(len(out), "events written")


def days_needed(ev):
    S = pd.Timestamp(ev["signal_at"])
    return {(ev["sym"], d.strftime("%Y-%m-%d")) for d in (S - MIN, S + pd.Timedelta(hours=24))} | {
        (ev["sym"], S.strftime("%Y-%m-%d"))}


def _get(pair):
    s, d = pair
    fp = RAW / f"{s}-1m-{d}.zip"
    if fp.exists():
        return "cached"
    try:
        with urllib.request.urlopen(URL.format(s=s, d=d), timeout=60) as r:
            fp.write_bytes(r.read())
        return "ok"
    except Exception as e:  # missing day = no trades or no archive; recorded as unavailable later
        return f"err {type(e).__name__}"


def fetch():
    RAW.mkdir(exist_ok=True)
    (RAW / ".gitignore").write_text("*\n")
    evs = json.loads((HERE / "sample.json").read_text())
    pairs = sorted(set().union(*(days_needed(e) for e in evs)))
    stats = {}
    with cf.ThreadPoolExecutor(16) as ex:
        for k, res in enumerate(ex.map(_get, pairs)):
            key = res.split()[0]
            stats[key] = stats.get(key, 0) + 1
            if k % 500 == 0:
                print(k, len(pairs), stats, flush=True)
    print("done", len(pairs), stats)


def bars(sym, days):
    fr = []
    for d in sorted(days):
        fp = RAW / f"{sym}-1m-{d}.zip"
        if fp.exists():
            df = lib.read_zip(fp, [0, 1, 4]); df.columns = ["t", "o", "c"]; fr.append(df)
    if not fr:
        return None
    df = pd.concat(fr).drop_duplicates("t")
    df.index = pd.to_datetime(df.t.astype("int64"), unit="ms", utc=True)
    return df.sort_index()


def boot_mean(vals, days, rng):
    df = pd.DataFrame({"v": vals, "d": days})
    g = df.groupby("d").v.agg(["sum", "count"]).to_numpy()
    idx = rng.integers(0, len(g), (BOOT, len(g)))
    s = g[idx].sum(axis=1)
    m = s[:, 0] / s[:, 1]
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def trimmed(x):
    lo, hi = np.percentile(x, [1, 99])
    return float(x[(x >= lo) & (x <= hi)].mean())


def score():
    evs = json.loads((HERE / "sample.json").read_text())
    rows = []
    for e in evs:
        S = pd.Timestamp(e["signal_at"])
        b = bars(e["sym"], {d for _, d in days_needed(e)})
        r = dict(period=e["period"], sym=e["sym"], day=S.date().isoformat())
        if b is None:
            rows.append(r); continue
        end = S + pd.Timedelta(hours=24)
        ex = b[(b.index + MIN <= end) & (b.index + MIN >= end - pd.Timedelta(minutes=30))]
        exit_px = float(ex.c.iloc[-1]) if len(ex) else np.nan
        for a in ARMS:
            tgt = S + a * MIN
            w = b[(b.index >= tgt) & (b.index <= tgt + 5 * MIN)]
            ent = float(w.o.iloc[0]) if len(w) else np.nan
            r[f"gross_{a}"] = exit_px / ent - 1 if ent > 0 and np.isfinite(exit_px) else np.nan
            if a == 1 and ent > 0:
                r["already_moved"] = ent / e["close_3h_before"] - 1
        rows.append(r)
    df = pd.DataFrame(rows)
    rng = np.random.default_rng(SEED)
    out = {"n_events": len(df), "arms": {}, "speed": {}, "by_period": {}}
    for a in ARMS:
        g = df.dropna(subset=[f"gross_{a}"])
        arm = {"available": len(g), "share_available": len(g) / len(df)}
        for cn, c in COSTS.items():
            net = g[f"gross_{a}"].to_numpy() - c
            arm[cn] = dict(mean=float(net.mean()), ci95=boot_mean(net, g.day.to_numpy(), rng),
                           median=float(np.median(net)), trimmed_mean=trimmed(net), win_rate=float((net > 0).mean()))
        out["arms"][str(a)] = arm
    for slow in (30, 240):
        g = df.dropna(subset=["gross_1", f"gross_{slow}"])
        diff = (g["gross_1"] - g[f"gross_{slow}"]).to_numpy()
        out["speed"][f"1_minus_{slow}"] = dict(n=len(g), mean=float(diff.mean()), median=float(np.median(diff)),
                                               ci95=boot_mean(diff, g.day.to_numpy(), rng))
    for p, g in df.groupby("period"):
        out["by_period"][p] = {str(a): dict(n=int(g[f"gross_{a}"].notna().sum()),
                                            mean_net_cost_2=float((g[f"gross_{a}"] - 0.02).mean()),
                                            mean_net_cost_06=float((g[f"gross_{a}"] - 0.006).mean())) for a in ARMS}
    out["already_moved_median"] = float(df.already_moved.median())
    one = out["arms"]["1"]
    out["verdict"] = ("PROFITABLE" if one["cost_2.0"]["ci95"][0] > 0
                      else "FIRM NO" if one["cost_0.6"]["ci95"][1] < 0 else "NOT PROVEN")
    (HERE / "results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"sample": sample, "fetch": fetch, "score": score}[sys.argv[1]]()

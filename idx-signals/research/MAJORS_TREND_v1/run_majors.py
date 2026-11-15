#!/usr/bin/env python3
"""MAJORS_TREND_v1: the frozen T1c 10/40 rule against exposure-matched holding on eight majors (see PROTOCOL.md).

Usage (from the repository root):
    BINANCE_RAW=<dir with the pinned archives> python3 idx-signals/research/MAJORS_TREND_v1/run_majors.py --out OUT.json
Reuses ETH_TREND_REPRO_v1 (matched_constant, block_bootstrap_diff, summary) and the original FRESH_EYES code unchanged.
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ETH_TREND_REPRO_v1"))
import repro_eth as R  # noqa: E402  (also imports lib and run_t1_t5 unchanged)

COINS = ["SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT"]
START, END = "2023-01-01", "2026-09-29"
SEED, BOOT, BLOCK = 20261115, 10_000, 20


def load(sym):
    return R.lib.load_klines("spot", sym, "1d")


def pooled_p(v, seed=SEED, block=BLOCK):
    v = np.asarray(v); n = len(v); rng = np.random.default_rng(seed); nb = math.ceil(n / block)
    means = []
    for _ in range(BOOT):
        starts = rng.integers(0, n, nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        means.append(v[idx].mean() * 365)
    means = np.array(means)
    return {"annual_mean": float(v.mean() * 365), "ci90": [float(np.percentile(means, 5)), float(np.percentile(means, 95))],
            "p_one_sided_le_0": float((means <= 0).mean()), "days": int(n)}


def one(df, side, start, end):
    pos = R.t1.sma_cross_positions(df, 10, 40)
    rule = R.lib.run_positions(df, pos, side, start=start, end=end)
    net = rule["net"]; w = float(rule["pos"].mean())
    cm = R.matched_constant(df, w, side, start, end).reindex(net.index)
    d = R.block_bootstrap_diff(net, cm)
    full = R.lib.run_positions(df, pd.Series(1.0, index=df.index), 0.0, start=start, end=end)["net"]
    return {"window": [str(net.index[0].date()), str(net.index[-1].date())], "exposure": round(w, 4),
            "changes_per_year": float(rule["pos"].diff().abs().sum() / len(net) * 365),
            "rule": {k: R.summary(net, rule["pos"]).get(k) for k in ("CAGR", "Sharpe", "MaxDD", "vol")},
            "matched": {k: R.summary(cm).get(k) for k in ("CAGR", "Sharpe", "MaxDD", "vol")},
            "hold_100pct_no_costs": {k: R.summary(full).get(k) for k in ("CAGR", "Sharpe", "MaxDD")},
            "excess": d}, (net - cm)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    out = {"protocol_sha256": __import__("hashlib").sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest(), "coins": {}, "pooled": {}}
    data = {s: load(s) for s in COINS}
    for cost, side in R.COSTS.items():
        ex = {}
        for s, df in data.items():
            prim, e = one(df, side, START, END)
            first = df.index[40].strftime("%Y-%m-%d")
            hist, _ = one(df, side, first, END)
            out["coins"].setdefault(s, {})[cost] = {"primary": prim, "whole_history": hist}
            ex[s] = e
        frame = pd.DataFrame(ex).dropna()
        pooled = pooled_p(frame.mean(axis=1).values)
        pos = sum(1 for s in COINS if out["coins"][s][cost]["primary"]["excess"]["annual_mean_diff"] > 0)
        out["pooled"][cost] = {**pooled, "coins_positive": pos}
    b = out["pooled"]["binance"]
    if b["coins_positive"] >= 6 and b["p_one_sided_le_0"] <= 0.05:
        v = "SUPPORTED"
    elif b["coins_positive"] <= 4 or b["annual_mean"] <= 0:
        v = "NOT SUPPORTED"
    else:
        v = "INCONCLUSIVE"
    out["verdict"] = v
    a.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print("verdict:", v, json.dumps(out["pooled"]))


if __name__ == "__main__":
    main()

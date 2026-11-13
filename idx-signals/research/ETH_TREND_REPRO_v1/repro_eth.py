#!/usr/bin/env python3
"""ETH_TREND_REPRO_v1: one reproduction pass of FRESH_EYES_v1 T1 on ETH, plus an exposure-matched benchmark.

Paper research only: spot ETH and cash, no leverage, no orders.

Usage (from the repository root):
    BINANCE_RAW=<dir with the pinned monthly archives> python3 idx-signals/research/ETH_TREND_REPRO_v1/repro_eth.py \
        --ext-raw <dir with pinned + later monthly archives> --out <output dir>

1. Re-runs the original code (handoff/fresh-eyes-2026-11-01/backtests/lib.py and run_t1_t5.py, imported unchanged) on
   the archives pinned by sha256 in its manifest, and compares every ETH T1 figure with the published results_t1_t5.json.
2. Compares the frozen rule (T1c, long when SMA10 > SMA40, else cash) with holding the rule's average ETH exposure, for
   2023-01-01 onward, at both of the original cost assumptions (Binance 0.15% a side; eToro 1.00% a side).
3. The same comparison for the other three ETH variants, a random-timing placebo, and a test that allows for the
   choice among the four variants (White's Reality Check on the four rules' excess returns, block bootstrap).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FE = ROOT / "handoff/fresh-eyes-2026-11-01/backtests"
sys.path.insert(0, str(FE))
import lib  # noqa: E402  (original, unchanged)
import run_t1_t5 as t1  # noqa: E402  (original, unchanged)

COSTS = {"binance": t1.SPOT_SIDE, "etoro": t1.ETORO_SIDE}
VARIANTS = {
    "T1a_donchian20_10": lambda df: t1.donchian_positions(df, 20, 10, "channel"),
    "T1b_tsmom28_hold5": lambda df: t1.tsmom_positions(df, 28, 5),
    "T1c_sma10_40": lambda df: t1.sma_cross_positions(df, 10, 40),
    "T1d_sma200": lambda df: t1.sma_filter_positions(df, 200),
}
VAL_START = "2023-01-01"
SEED = 20261113
BOOT = 10_000
BLOCK = 20
PLACEBOS = 2_000


def load(raw):
    old = lib.RAW
    lib.RAW = str(raw)
    try:
        return lib.load_klines("spot", "ETHUSDT", "1d")
    finally:
        lib.RAW = old


def matched_constant(df, w, side, start, end):
    """Hold a constant ETH weight w, rebalanced at every open (the drift trade pays `side`); initial buy pays `side`."""
    op = df["open"]
    r = (op.shift(-1) / op - 1.0)
    r = r[(r.index >= pd.Timestamp(start, tz="UTC")) & (r.index <= pd.Timestamp(end, tz="UTC"))].dropna()
    gross = w * r
    drift = (w * (1 + r) / (1 + w * r) - w).abs()           # trade needed at the next open to restore w
    cost = drift.shift(1).fillna(w) * side                 # first day: buying w
    net = gross - cost
    return net


def matched_buy_and_hold(df, w, side, start, end):
    """Buy w of ETH at the first open, never trade again (exposure drifts)."""
    op = df["open"]
    r = (op.shift(-1) / op - 1.0)
    r = r[(r.index >= pd.Timestamp(start, tz="UTC")) & (r.index <= pd.Timestamp(end, tz="UTC"))].dropna()
    eth = w * (1 - side) * (1 + r).cumprod()
    eq = eth + (1 - w)
    prev = pd.concat([pd.Series([1.0], index=[r.index[0] - pd.Timedelta(days=1)]), eq.iloc[:-1]])
    prev.index = r.index
    return eq / prev - 1.0


def summary(net, pos=None):
    s = lib.stats(net, 365, pos)
    s["by_year"] = lib.by_year(net)
    return s


def block_bootstrap_diff(a, b, seed=SEED, block=BLOCK):
    """Circular block bootstrap of (annualised mean of a-b, Sharpe(a)-Sharpe(b)); a and b share an index."""
    a, b = a.values, b.values
    n = len(a)
    rng = np.random.default_rng(seed)
    nb = math.ceil(n / block)
    mean_d, sharpe_d = [], []
    for _ in range(BOOT):
        starts = rng.integers(0, n, nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        x, y = a[idx], b[idx]
        mean_d.append((x - y).mean() * 365)
        sx, sy = x.std(ddof=1), y.std(ddof=1)
        sharpe_d.append((x.mean() / sx - y.mean() / sy) * math.sqrt(365) if sx > 0 and sy > 0 else np.nan)
    mean_d, sharpe_d = np.array(mean_d), np.array(sharpe_d)
    q = lambda v, p: float(np.nanpercentile(v, p))  # noqa: E731
    return {
        "annual_mean_diff": float((a - b).mean() * 365),
        "annual_mean_diff_ci90": [q(mean_d, 5), q(mean_d, 95)],
        "p_one_sided_mean_diff_le_0": float((mean_d <= 0).mean()),
        "sharpe_diff": float((a.mean() / a.std(ddof=1) - b.mean() / b.std(ddof=1)) * math.sqrt(365)),
        "sharpe_diff_ci90": [q(sharpe_d, 5), q(sharpe_d, 95)],
        "p_one_sided_sharpe_diff_le_0": float(np.nanmean(sharpe_d <= 0)),
    }


def excess_series(df, pos, side, start, end):
    """Daily net return of a rule minus that of holding its own average exposure over the window."""
    rule = lib.run_positions(df, pos, side, start=start, end=end)
    w = float(rule["pos"].mean())
    cm = matched_constant(df, w, side, start, end).reindex(rule.index)
    return rule["net"] - cm


def reality_check(excess, chosen, seed=SEED, block=BLOCK):
    """White's Reality Check on K rules' excess-return series (columns of `excess`): the chance that the best of the
    K looks as good as observed when none has a true advantage, with the rules' correlation kept by resampling the
    same blocks of days for all of them. Also the same probability at the chosen rule's own value."""
    x = excess.dropna().values
    n, k = x.shape
    means = x.mean(axis=0)
    rng = np.random.default_rng(seed)
    nb = math.ceil(n / block)
    stat = np.empty(BOOT)
    for i in range(BOOT):
        starts = rng.integers(0, n, nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        stat[i] = (x[idx].mean(axis=0) - means).max()
    j = list(excess.columns).index(chosen)
    return {
        "rules": list(excess.columns),
        "annual_excess": {c: float(m * 365) for c, m in zip(excess.columns, means)},
        "best_rule": str(excess.columns[int(means.argmax())]),
        "p_best_of_k": float((stat >= means.max()).mean()),
        "chosen": chosen,
        "p_chosen_allowing_for_k": float((stat >= means[j]).mean()),
        "p_chosen_alone": float(_single_p(x[:, j], seed, block)),
        "block_days": block,
    }


def _single_p(v, seed, block):
    n = len(v)
    rng = np.random.default_rng(seed)
    nb = math.ceil(n / block)
    m = v.mean()
    hits = 0
    for _ in range(BOOT):
        starts = rng.integers(0, n, nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        hits += (v[idx].mean() - m) >= m
    return hits / BOOT


def compare(df, pos, side, start, end):
    rule = lib.run_positions(df, pos, side, start=start, end=end)
    net = rule["net"]
    w = float(rule["pos"].mean())
    cm = matched_constant(df, w, side, start, end).reindex(net.index)
    bh_w = matched_buy_and_hold(df, w, side, start, end).reindex(net.index)
    full = lib.run_positions(df, pd.Series(1.0, index=df.index), 0.0, start=start, end=end)["net"]
    return {
        "window": [str(net.index[0].date()), str(net.index[-1].date())],
        "average_eth_exposure": round(w, 4),
        "rule": summary(net, rule["pos"]),
        "matched_constant_daily_rebalanced": summary(cm),
        "matched_buy_once_no_rebalance": summary(bh_w),
        "buy_and_hold_100pct_no_costs": summary(full),
        "rule_minus_matched_constant": block_bootstrap_diff(net, cm),
        "block_length_sensitivity": {
            str(b): {
                k: v
                for k, v in block_bootstrap_diff(net, cm, block=b).items()
                if k in ("annual_mean_diff_ci90", "p_one_sided_mean_diff_le_0", "sharpe_diff_ci90", "p_one_sided_sharpe_diff_le_0")
            }
            for b in (5, 60)
        },
    }, net, cm, rule["pos"]


def placebo(df, pos, side, start, end, seed=SEED):
    """Random long/flat timing with the rule's average in/out spell lengths; each scored against its own matched
    constant-exposure benchmark. Returns the distribution of annualised excess (placebo minus its matched benchmark)."""
    seg = pos[(pos.index >= pd.Timestamp(start, tz="UTC")) & (pos.index <= pd.Timestamp(end, tz="UTC"))]
    runs, cur, length = [], seg.iloc[0], 0
    for v in seg.values:
        if v == cur:
            length += 1
        else:
            runs.append((cur, length))
            cur, length = v, 1
    runs.append((cur, length))
    mean_in = np.mean([n for v, n in runs if v > 0]) if any(v > 0 for v, _ in runs) else 1.0
    mean_out = np.mean([n for v, n in runs if v == 0]) if any(v == 0 for v, _ in runs) else 1.0
    rng = np.random.default_rng(seed)
    out = []
    n = len(df)
    for _ in range(PLACEBOS):
        p, state = np.zeros(n), int(rng.random() < 0.5)
        i = 0
        while i < n:
            d = int(rng.geometric(1 / (mean_in if state else mean_out)))
            p[i : i + d] = state
            i += d
            state = 1 - state
        ps = pd.Series(p, index=df.index)
        res = lib.run_positions(df, ps, side, start=start, end=end)
        w = float(res["pos"].mean())
        cm = matched_constant(df, w, side, start, end).reindex(res.index)
        out.append(float((res["net"] - cm).mean() * 365))
    return np.array(out), float(mean_in), float(mean_out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext-raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    published = json.loads((FE / "results_t1_t5.json").read_text())["results"]

    df = load(os.environ.get("BINANCE_RAW", lib.RAW))
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    report = {
        "inputs": {
            "handoff/fresh-eyes-2026-11-01/backtests/lib.py": sha(FE / "lib.py"),
            "handoff/fresh-eyes-2026-11-01/backtests/run_t1_t5.py": sha(FE / "run_t1_t5.py"),
            "handoff/fresh-eyes-2026-11-01/backtests/results_t1_t5.json": sha(FE / "results_t1_t5.json"),
            "handoff/fresh-eyes-2026-11-01/backtests/manifests/manifest_spot_klines_1d.jsonl": sha(
                FE / "manifests/manifest_spot_klines_1d.jsonl"
            ),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "data_pinned": {"first": str(df.index[0].date()), "last": str(df.index[-1].date()), "bars": len(df)},
    }

    # 1. Reproduction of every published ETH T1 figure.
    repro, worst = {}, 0.0
    for name, fn in VARIANTS.items():
        pos = fn(df)
        for cost, side in COSTS.items():
            for pname, (s, e) in t1.PERIODS.items():
                out = lib.run_positions(df, pos, side, start=s, end=e)
                st = lib.stats(out["net"], 365, out["pos"])
                key = f"ETHUSDT|{name}|{cost}|{pname}"
                pub = published[key]
                diff = {k: round(st[k] - pub[k], 6) for k in ("CAGR", "vol", "Sharpe", "MaxDD", "total") if k in pub}
                worst = max(worst, max(abs(v) for v in diff.values()))
                repro[key] = {"reproduced": {k: st[k] for k in diff}, "published": {k: pub[k] for k in diff}, "diff": diff}
    report["reproduction"] = {"max_abs_diff": worst, "rows": repro}

    # 2. The frozen rule against its average exposure, 2023 onward, both costs, pinned data and the update.
    df_ext = load(a.ext_raw)
    report["data_update"] = {"first": str(df_ext.index[0].date()), "last": str(df_ext.index[-1].date()), "bars": len(df_ext)}
    main_rows, keep = {}, {}
    for label, frame, end in (("frozen_window_to_2026-09", df, t1.PERIODS["val"][1]), ("update_to_2026-10", df_ext, "2026-12-31")):
        pos = t1.sma_cross_positions(frame, 10, 40)
        for cost, side in COSTS.items():
            res, net, cm, p = compare(frame, pos, side, VAL_START, end)
            main_rows[f"{label}|{cost}"] = res
            keep[f"{label}|{cost}"] = (net, cm)
    report["T1c_vs_matched"] = main_rows

    # 2b. The whole pinned history (development and validation together), both costs.
    full_rows = {}
    pos_full = t1.sma_cross_positions(df, 10, 40)
    for cost, side in COSTS.items():
        res, *_ = compare(df, pos_full, side, t1.PERIODS["dev"][0], t1.PERIODS["val"][1])
        full_rows[cost] = res
    report["T1c_vs_matched_full_history"] = full_rows

    # 2c. Allowing for the choice among the four ETH rules (Reality Check), each window and cost.
    rc = {}
    for wname, (s, e) in {
        "since_2023": (VAL_START, t1.PERIODS["val"][1]),
        "2017_2022": t1.PERIODS["dev"],
        "full_history": (t1.PERIODS["dev"][0], t1.PERIODS["val"][1]),
    }.items():
        for cost, side in COSTS.items():
            ex = pd.DataFrame({name: excess_series(df, fn(df), side, s, e) for name, fn in VARIANTS.items()})
            rc[f"{wname}|{cost}"] = reality_check(ex, "T1c_sma10_40")
    report["selection_reality_check"] = rc

    # 3a. All four ETH variants against their own matched exposure (selection context), Binance costs, both periods.
    allv = {}
    for name, fn in VARIANTS.items():
        pos = fn(df)
        for pname, (s, e) in t1.PERIODS.items():
            res, *_ = compare(df, pos, COSTS["binance"], s, e)
            allv[f"{name}|{pname}"] = {
                "exposure": res["average_eth_exposure"],
                "rule_CAGR": res["rule"]["CAGR"],
                "rule_Sharpe": res["rule"]["Sharpe"],
                "rule_MaxDD": res["rule"]["MaxDD"],
                "matched_CAGR": res["matched_constant_daily_rebalanced"]["CAGR"],
                "matched_Sharpe": res["matched_constant_daily_rebalanced"]["Sharpe"],
                "matched_MaxDD": res["matched_constant_daily_rebalanced"]["MaxDD"],
                "excess_annual_mean": res["rule_minus_matched_constant"]["annual_mean_diff"],
                "excess_ci90": res["rule_minus_matched_constant"]["annual_mean_diff_ci90"],
            }
    report["all_four_variants_vs_matched_binance"] = allv

    # 3b. Random-timing placebo for the 2023-onward window, Binance costs, pinned data.
    pos = t1.sma_cross_positions(df, 10, 40)
    dist, mean_in, mean_out = placebo(df, pos, COSTS["binance"], VAL_START, t1.PERIODS["val"][1])
    obs = report["T1c_vs_matched"]["frozen_window_to_2026-09|binance"]["rule_minus_matched_constant"]["annual_mean_diff"]
    p1 = float((dist >= obs).mean())
    report["placebo"] = {
        "draws": PLACEBOS,
        "mean_in_spell_days": round(mean_in, 2),
        "mean_out_spell_days": round(mean_out, 2),
        "placebo_excess_mean": float(dist.mean()),
        "placebo_excess_sd": float(dist.std(ddof=1)),
        "placebo_excess_p95": float(np.percentile(dist, 95)),
        "observed_excess": obs,
        "p_single_rule": p1,
        "p_best_of_4_if_independent": 1 - (1 - p1) ** 4,
        "p_best_of_8_if_independent": 1 - (1 - p1) ** 8,
    }
    (a.out / "repro_eth.json").write_text(json.dumps(report, indent=1, default=float) + "\n")
    for k, (net, cm) in keep.items():
        pd.DataFrame({"rule_net": net, "matched_constant_net": cm}).to_csv(a.out / f"daily_{k.replace('|', '_')}.csv")
    print(json.dumps({"max_abs_diff": worst, "data": report["data_pinned"], "update": report["data_update"]}, indent=1))


if __name__ == "__main__":
    main()

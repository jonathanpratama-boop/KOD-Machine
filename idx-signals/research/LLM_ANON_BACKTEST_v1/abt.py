#!/usr/bin/env python3
"""LLM_ANON_BACKTEST_v1: build anonymised events, fit benchmarks, score the calls.

    python3 abt.py build   # events + features for judges, benchmarks fitted on the training window
    python3 abt.py score   # run only after the calls file is stamped; reads outcomes for test events

See PROTOCOL.md for every rule. Standard library plus numpy and pandas.
"""

import argparse
import gzip
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
PANELS = {
    "IDX": HERE.parents[1] / "data/panel/panel-20261007T225823Z.csv.gz",
    "CRYPTO": HERE.parents[1] / "data/panel/panel_crypto-20261008T003354Z.csv.gz",
}
TEST_START, TEST_END, TRAIN_END = "2026-07-01", "2026-09-22", "2026-06-30"
SEED, CAP, COST = 20261107, 150, 0.015
FEATURES = ["ret1", "ret5", "ret20", "log_volr", "cpos", "dd60", "adv20_log10"]
STATEMENTS = ["RUN30_5", "FADE10_5", "GAIN0_5"]
LAMBDA = 1.0
BOOT = 10000


def load(market: str) -> pd.DataFrame:
    cols = ["date", "ticker", "previous", "high", "low", "close", "value"]
    df = pd.read_csv(PANELS[market], usecols=cols)
    for c in ("previous", "high", "low", "close", "value"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["previous", "high", "low", "close", "value"])
    df = df[(df.previous > 0) & (df.close > 0)]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"]).reset_index(drop=True)


def prep(df: pd.DataFrame, market: str) -> pd.DataFrame:
    g = df.groupby("ticker", sort=False)
    df["ret1"] = df.close / df.previous - 1
    df["ret5"] = df.close / g.close.shift(5) - 1
    df["ret20"] = df.close / g.close.shift(20) - 1
    prev_mean = g.value.transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    df["volr"] = df.value / prev_mean
    df["log_volr"] = np.log(df.volr.clip(lower=0.01))
    span = df.high - df.low
    df["cpos"] = np.where(span > 0, (df.close - df.low) / span.where(span > 0, 1), 1.0)
    df["dd60"] = df.close / g.close.transform(lambda x: x.rolling(60, min_periods=20).max()) - 1
    adv = g.value.transform(lambda x: x.rolling(20, min_periods=20).mean())
    df["adv20_log10"] = np.log10(adv.clip(lower=1))
    if market == "IDX":
        cond = (df.ret1 >= 0.20) & (df.close >= 0.999 * df.high) & (df.value >= 1e8)
    else:
        cond = (df.ret1 >= 0.30) & (df.value >= 1e6)
    df["cond"] = cond.astype(float)
    recent = g.cond.transform(lambda x: x.shift(1).rolling(5, min_periods=1).max()).fillna(0)
    df["fresh"] = cond & (recent == 0)
    df["n_before"] = g.cumcount()
    return df


def add_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("ticker", sort=False)
    fwd = [g.close.shift(-k) for k in range(1, 7)]
    df["date6"] = g.date.shift(-6)
    ok = fwd[5].notna() & ((df.date6 - df.date).dt.days <= 20)
    mx = pd.concat(fwd[:5], axis=1).max(axis=1)
    net = fwd[5] / fwd[0] - 1 - COST
    df["scorable"] = ok
    df["RUN30_5"] = (mx >= 1.30 * df.close).astype(float)
    df["FADE10_5"] = (net <= -0.10).astype(float)
    df["GAIN0_5"] = (net > 0).astype(float)
    df["net5"] = net
    return df


def events(df: pd.DataFrame) -> pd.DataFrame:
    e = df[df.fresh & (df.n_before >= 20)].dropna(subset=FEATURES)
    return e.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)


def fit_logistic(x: np.ndarray, y: np.ndarray, lam: float = LAMBDA):
    mu, sd = x.mean(axis=0), x.std(axis=0)
    sd[sd == 0] = 1
    z = (x - mu) / sd
    a = np.hstack([np.ones((len(z), 1)), z])
    w = np.zeros(a.shape[1])
    reg = np.eye(a.shape[1]) * lam
    reg[0, 0] = 0
    for _ in range(50):
        p = 1 / (1 + np.exp(-(a @ w)))
        grad = a.T @ (p - y) + reg @ w
        hess = (a * (p * (1 - p))[:, None]).T @ a + reg + 1e-9 * np.eye(len(w))
        step = np.linalg.solve(hess, grad)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return {"w": w.tolist(), "mu": mu.tolist(), "sd": sd.tolist()}


def predict(model: dict, x: np.ndarray) -> np.ndarray:
    z = (x - np.array(model["mu"])) / np.array(model["sd"])
    return 1 / (1 + np.exp(-(model["w"][0] + z @ np.array(model["w"][1:]))))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> int:
    rng = random.Random(SEED)
    summary, test_rows, key = {}, [], {}
    for market in ("IDX", "CRYPTO"):
        df = add_outcomes(prep(load(market), market))
        # the build step never uses outcomes after the training window: blank them out
        df.loc[df.date > TRAIN_END, ["RUN30_5", "FADE10_5", "GAIN0_5", "net5"]] = np.nan
        df.loc[df.date > TRAIN_END, "scorable"] = False
        ev = events(df)
        train = ev[(ev.date <= TRAIN_END) & ev.scorable]
        summary[market] = {"n_train": int(len(train)), "base": {}, "models": {}, "train_end": TRAIN_END}
        for st in STATEMENTS:
            summary[market]["base"][st] = float(train[st].mean())
            summary[market]["models"][st] = fit_logistic(train[FEATURES].to_numpy(float), train[st].to_numpy(float))
        test = ev[(ev.date >= TEST_START) & (ev.date <= TEST_END)].sort_values(["ticker", "date"])
        idx = list(range(len(test)))
        summary[market]["n_test_events"] = len(idx)
        if len(idx) > CAP:
            idx = sorted(rng.sample(idx, CAP))
        summary[market]["n_test_drawn"] = len(idx)
        for i in idx:
            r = test.iloc[i]
            eid = "E" + "".join(rng.choice("0123456789abcdef") for _ in range(7))
            key[eid] = {"market": market, "ticker": r.ticker, "date": r.date.strftime("%Y-%m-%d")}
            test_rows.append({"id": eid, "market": market, **{f: round(float(r[f]), 4) for f in FEATURES}})
    rng.shuffle(test_rows)
    (HERE / "test_events_features.jsonl").write_text("\n".join(json.dumps(r) for r in test_rows) + "\n")
    (HERE / "key_private.json").write_text(json.dumps(key, indent=1, sort_keys=True) + "\n")
    (HERE / "train_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    for m, s in summary.items():
        print(m, "train", s["n_train"], "test events", s["n_test_events"], "drawn", s["n_test_drawn"],
              "base", {k: round(v, 3) for k, v in s["base"].items()})
    return 0


def brier(p, y):
    return (np.asarray(p) - np.asarray(y)) ** 2


def boot_ci(diff: np.ndarray, rng) -> tuple[float, float, float]:
    n = len(diff)
    means = np.array([diff[rng.integers(0, n, n)].mean() for _ in range(BOOT)])
    return float(diff.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 95))


def score() -> int:
    calls_path = HERE / "calls.jsonl"
    stamp = HERE / "timestamps" / "calls.jsonl.freetsa.tsr"
    if not calls_path.exists() or not stamp.exists():
        raise SystemExit("calls.jsonl and its timestamp must exist before scoring")
    calls = {c["id"]: c for c in map(json.loads, calls_path.read_text().splitlines() if calls_path.exists() else [])}
    key = json.loads((HERE / "key_private.json").read_text())
    summ = json.loads((HERE / "train_summary.json").read_text())
    feats = {r["id"]: r for r in map(json.loads, (HERE / "test_events_features.jsonl").read_text().splitlines())}
    rows = []
    for market in ("IDX", "CRYPTO"):
        df = add_outcomes(prep(load(market), market))
        df["datestr"] = df.date.dt.strftime("%Y-%m-%d")
        look = df.set_index(["ticker", "datestr"])
        for eid, k in key.items():
            if k["market"] != market or eid not in calls:
                continue
            r = look.loc[(k["ticker"], k["date"])]
            f = feats[eid]
            x = np.array([[f[c] for c in FEATURES]], dtype=float)
            row = {"id": eid, "market": market, "scorable": bool(r.scorable), "net5": float(r.net5) if r.scorable else None,
                   "call": calls[eid]["call"]}
            for st in STATEMENTS:
                row[st] = float(r[st]) if r.scorable else None
                row["judge_" + st] = float(calls[eid]["p"][st])
                row["base_" + st] = summ[market]["base"][st]
                row["logit_" + st] = float(predict(summ[market]["models"][st], x)[0])
            rows.append(row)
    df = pd.DataFrame(rows)
    out = {"calls_scored": len(df), "unscorable": int((~df.scorable).sum()), "markets": {}, "pooled": {}}
    sc = df[df.scorable]
    rng = np.random.default_rng(SEED)
    for scope, part in [("pooled", sc)] + [(m, sc[sc.market == m]) for m in ("IDX", "CRYPTO")]:
        res = {"n": int(len(part))}
        for st in STATEMENTS:
            if not len(part):
                continue
            y = part[st].to_numpy()
            jb, bb, lb = brier(part["judge_" + st], y), brier(part["base_" + st], y), brier(part["logit_" + st], y)
            res[st] = {
                "brier_judge": float(jb.mean()), "brier_base": float(bb.mean()), "brier_logit": float(lb.mean()),
                "vs_base": boot_ci(jb - bb, rng), "vs_logit": boot_ci(jb - lb, rng),
            }
        (out["pooled"] if scope == "pooled" else out["markets"])[scope if scope != "pooled" else "all"] = res
    pooled = out["pooled"].get("all", {})
    out["pass"] = bool(pooled) and all(
        pooled[st][cmp][2] < 0 for st in ("RUN30_5", "FADE10_5") for cmp in ("vs_base", "vs_logit")
    )
    back, avoid = sc[sc.call == "BACK"].net5.dropna().to_numpy(), sc[sc.call == "AVOID"].net5.dropna().to_numpy()
    out["call_counts"] = df.call.value_counts().to_dict()
    if len(back) >= 20 and len(avoid) >= 20:
        diffs = np.array([back[rng.integers(0, len(back), len(back))].mean() - avoid[rng.integers(0, len(avoid), len(avoid))].mean()
                          for _ in range(BOOT)])
        out["back_minus_avoid"] = {"mean": float(back.mean() - avoid.mean()), "lo95": float(np.percentile(diffs, 2.5)),
                                   "hi95": float(np.percentile(diffs, 97.5)), "n_back": len(back), "n_avoid": len(avoid)}
    else:
        out["back_minus_avoid"] = f"not evaluable: {len(back)} BACK calls (need 20)"
    (HERE / "results.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "score"])
    sys.exit(build() if ap.parse_args().cmd == "build" else score())

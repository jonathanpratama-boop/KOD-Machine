"""CRYPTO_TUNE_v1: the same fine-tune as TUNE_SWEEP_v1, for crypto: hundreds of model scenarios for the next-day dump
of Binance pairs that closed 30% or more higher, picked on one period, confirmed once on a period no dump study read.

Owner (2026-10-30): "whenever i ask something, its every damn market" (US and crypto; IDX is out: a no-trade zone).

    python3 tune.py --freeze     # protocol.json + scenarios.json, before anything is fitted or built
    python3 tune.py --sweep      # fit on TRAIN (2020-2022), rank on VALIDATE (2023): leaderboard
    python3 tune.py --confirm    # once: build the 2024-01-01..2026-10-06 events (PATH_HISTORY_v1's own builder build2.py, the one that made the stored history;
                                 # same detector, twins and label), refit the two candidates on 2020-2023, score

Label: S_NEXT_DUMP10 (the next daily close 10% or more below the signal close while fewer than half of the five
twins do), the crypto twin of v2.4's headline. Features: PATH_HISTORY_v1's price blocks (P0 and P1 without the IDX-only
ARA streak), the same columns in every period because the same builder makes them. There is no live crypto dump model,
so the comparison is the pre-declared volatility-and-context benchmark (vol20, s_ret1, mkt_ret, breadth) and chance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import sha256_file, utc_stamp  # noqa: E402

TS = importlib.util.spec_from_file_location("tune_us", ROOT / "research" / "TUNE_SWEEP_v1" / "tune.py")
US = importlib.util.module_from_spec(TS)
TS.loader.exec_module(US)  # the US harness's model families, metrics and bootstrap, unchanged

PROTO = HERE / "protocol.json"
RESULTS = HERE / "results"
LABEL = "S_NEXT_DUMP10"
HISTORY = "research/PATH_HISTORY_v1/results/events.csv.gz"
P0 = ["s_ret1", "s_ret5", "s_ret20", "s_dd60", "log_volr", "s_cpos", "log_adv"]
P1 = ["gap", "vol20_pre", "spike_z", "log_price", "spikes60", "streak", "dist_high252", "log_age", "breadth", "mkt_ret"]
BENCH = ["vol20_pre", "spike_z", "s_ret1", "mkt_ret", "breadth"]  # v2.4's benchmark block
FEATURES = P0 + P1
FEATURE_SETS = {"ALL": FEATURES, "P0": P0, "P0_P1": FEATURES, "BENCH": BENCH,
                "NO_LEVEL": [k for k in FEATURES if k not in ("log_price", "log_adv")]}
CONFIRM_RANGE = ["2024-01-01", "2026-10-06"]
BUILD_FROM = "2023-09-01"   # 60+ sessions of lookback before the confirm range; events before it are discarded
SEED = 20261030
CODE_PINS = ("research/CRYPTO_TUNE_v1/tune.py", "research/TUNE_SWEEP_v1/tune.py", "research/PATH_HISTORY_v1/build2.py",
             "idxsig/speculation.py", "idxsig/rules/moonshot_g.py", "idxsig/global_panel.py", "idxsig/learner2.py")


def scenarios() -> list[dict]:
    out = []
    for fs, lam in itertools.product(FEATURE_SETS, (0.01, 0.1, 0.3, 1, 3, 10, 30, 100)):
        out.append({"family": "logistic", "features": fs, "l2": lam})
    for fs, (leaves, lr, trees, mcs, ff, bag) in itertools.product(
            ("ALL", "NO_LEVEL"),
            itertools.product((7, 15, 31), (0.02, 0.05, 0.1), (100, 300, 600), (20, 50, 100), (0.6, 1.0), (0.7, 1.0))):
        out.append({"family": "lightgbm", "features": fs, "num_leaves": leaves, "learning_rate": lr, "n_estimators": trees,
                    "min_child_samples": mcs, "feature_fraction": ff, "bagging_fraction": bag})
    for fs, (depth, lr, it, l2) in itertools.product(("ALL", "NO_LEVEL"),
                                                     itertools.product((3, 5, None), (0.03, 0.1), (100, 300), (0.0, 1.0))):
        out.append({"family": "hist_gb", "features": fs, "max_depth": depth, "learning_rate": lr, "max_iter": it,
                    "l2_regularization": l2})
    for fs, (kind, trees, leaf, mf) in itertools.product(("ALL", "NO_LEVEL"),
                                                         itertools.product(("rf", "extra"), (300, 800), (5, 20, 50), (0.3, 0.6))):
        out.append({"family": kind, "features": fs, "n_estimators": trees, "min_samples_leaf": leaf, "max_features": mf})
    for fs, (hidden, alpha) in itertools.product(("ALL", "NO_LEVEL"), itertools.product(((16,), (32,), (32, 16)), (1e-3, 1e-2, 1e-1))):
        out.append({"family": "mlp", "features": fs, "hidden": list(hidden), "alpha": alpha})
    for fs, k in itertools.product(("ALL", "NO_LEVEL", "P0"), (25, 50, 100, 200)):
        out.append({"family": "knn", "features": fs, "k": k})
    for i, s in enumerate(out):
        s["id"] = f"C{i:04d}"
    return out


def fit_predict(s: dict, tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    """The US harness's fit_predict with this module's feature sets and label."""
    US.FEATURE_SETS, US.LABEL = FEATURE_SETS, LABEL
    return US.fit_predict(s, tr, te)


def history() -> pd.DataFrame:
    ev = pd.read_csv(ROOT / HISTORY, dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    ev = ev[(ev["market"] == "CRYPTO") & ev[LABEL].notna()].copy()
    ev[LABEL] = ev[LABEL].astype(float)
    return ev.reset_index(drop=True)


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    sc = scenarios()
    proto = {
        "study_id": "CRYPTO_TUNE_v1", "frozen_at": utc_stamp(), "label": LABEL, "features": FEATURES,
        "feature_sets": FEATURE_SETS, "split": {"TRAIN": ["2020-01-01", "2022-12-31"], "VALIDATE": ["2023-01-01", "2023-12-31"],
                                                "REFIT_FOR_CONFIRM": ["2020-01-01", "2023-12-31"], "CONFIRM": CONFIRM_RANGE},
        "confirm_build": f"PATH_HISTORY_v1/build2.py build_market('CRYPTO') on the pinned crypto panel rows {BUILD_FROM}.."
                         f"{CONFIRM_RANGE[1]}, events kept from {CONFIRM_RANGE[0]}; built only by --confirm",
        "n_scenarios": len(sc), "scenarios_sha256": hashlib.sha256(json.dumps(sc, sort_keys=True).encode()).hexdigest(),
        "selection": "BEST = highest VALIDATE AUC (ties: lower id); TOP10 = mean of the ten highest; both refit on 2020-2023",
        "baseline": "BENCH = logistic l2=1 on vol20_pre, spike_z, s_ret1, mkt_ret, breadth (v2.4's benchmark block), refit on 2020-2023",
        "bar": "a candidate IMPROVES on the benchmark when Holm over the two candidates rejects on the one-sided "
               "session-bootstrap p of AUC(candidate) - AUC(BENCH) <= 0 (2.5% then 5%); BEATS CHANCE when z >= 3",
        "bootstrap": {"unit": "signal session", "resamples": 2000, "seed": SEED},
        "honesty": ["VALIDATE is optimistic by construction; only CONFIRM is reported as skill",
                    "crypto 2024 onward is sealed; read once here, on the owner's instruction; nothing tuned on it",
                    "IDX is excluded on the owner's instruction (no-trade zone)",
                    "survivorship: the panel's pair list is the archive's, delisted pairs included where the archive kept them"],
        "environment": "pinned venv: scikit-learn 1.9.1, lightgbm 4.7.0, pandas 2.2.3, numpy 2.3.5",
        "inputs": {HISTORY: sha256_file(ROOT / HISTORY)}, "code": {p: sha256_file(ROOT / p) for p in CODE_PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    (HERE / "scenarios.json").write_text(json.dumps(sc, indent=0) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "n_scenarios", "split")}, indent=1))
    return 0


def check() -> dict:
    proto = json.loads(PROTO.read_text())
    for p, want in proto["code"].items():
        if sha256_file(ROOT / p) != want:
            raise RuntimeError(f"{p} changed since the freeze")
    if hashlib.sha256(json.dumps(scenarios(), sort_keys=True).encode()).hexdigest() != proto["scenarios_sha256"]:
        raise RuntimeError("the scenario grid changed")
    return proto


def sweep() -> int:
    check()
    out = RESULTS / "leaderboard.csv"
    if out.exists():
        sys.exit("error: the sweep runs once")
    ev = history()
    tr = ev[ev["session"] <= "2022-12-31"].reset_index(drop=True)
    va = ev[(ev["session"] >= "2023-01-01") & (ev["session"] <= "2023-12-31")].reset_index(drop=True)
    yv = va[LABEL].to_numpy(float)
    rows, t0 = [], time.time()
    for i, s in enumerate(scenarios()):
        try:
            m = US.metrics(fit_predict(s, tr, va), yv)
        except Exception as exc:  # noqa: BLE001
            m = {"error": f"{type(exc).__name__}: {exc}"}
        rows.append({"id": s["id"], "family": s["family"], "features": s["features"],
                     "params": json.dumps({k: v for k, v in s.items() if k not in ("id", "family", "features")}), **m})
        if i % 100 == 0:
            print(f"{i}/{len(scenarios())}, {time.time() - t0:.0f}s", flush=True)
    RESULTS.mkdir(exist_ok=True)
    lb = pd.DataFrame(rows).sort_values(["auc", "id"], ascending=[False, True])
    lb.to_csv(out, index=False)
    bench = lb[(lb.family == "logistic") & (lb.features == "BENCH") & (lb.params == json.dumps({"l2": 1}))]
    summary = {"ran_at": utc_stamp(), "train_n": len(tr), "validate_n": len(va), "scenarios": len(rows),
               "failed": int(lb["auc"].isna().sum()), "best": lb.iloc[0][["id", "family", "features", "params", "auc"]].to_dict(),
               "top10_ids": lb["id"].head(10).tolist(), "bench_validate_auc": float(bench["auc"].iloc[0]) if len(bench) else None,
               "auc_spread": {"max": float(lb["auc"].max()), "median": float(lb["auc"].median()), "min": float(lb["auc"].min())},
               "by_family_best": lb.groupby("family")["auc"].max().round(4).to_dict()}
    (RESULTS / "SWEEP.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


def build_confirm() -> pd.DataFrame:
    """PATH_HISTORY_v1's own builder on the confirm period: same detector, twins, features and labels."""
    spec_ = importlib.util.spec_from_file_location("path_build", ROOT / "research" / "PATH_HISTORY_v1" / "build2.py")
    pb = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(pb)
    pb.PROTO["data"]["CRYPTO"]["rows_read"] = [BUILD_FROM, CONFIRM_RANGE[1]]
    rows = pb.build_market("CRYPTO", log=lambda s: print(s, flush=True))
    df = pd.DataFrame(rows)
    st = pb.statements(df)
    df[LABEL] = [None if v is None else int(v) for v in st["NEXT_DUMP10"]]
    df = df[(df["session"] >= CONFIRM_RANGE[0]) & (df["session"] <= CONFIRM_RANGE[1]) & df[LABEL].notna()].copy()
    df[LABEL] = df[LABEL].astype(float)
    return df.reset_index(drop=True)


def confirm() -> int:
    check()
    out = RESULTS / "CONFIRM.json"
    if out.exists():
        sys.exit("error: confirm runs once")
    sw = json.loads((RESULTS / "SWEEP.json").read_text())
    lb = pd.read_csv(RESULTS / "leaderboard.csv").sort_values(["auc", "id"], ascending=[False, True])
    if lb["id"].head(10).tolist() != sw["top10_ids"] or lb.iloc[0]["id"] != sw["best"]["id"]:
        raise RuntimeError("SWEEP.json does not match the leaderboard")
    by_id = {s["id"]: s for s in scenarios()}
    ev = history()
    fit = ev[ev["session"] <= "2023-12-31"].reset_index(drop=True)
    cs = build_confirm()
    cs.to_csv(RESULTS / "confirm_events.csv.gz", index=False)
    y, sess = cs[LABEL].to_numpy(float), cs["session"].to_numpy()
    preds = {"BEST": fit_predict(by_id[sw["best"]["id"]], fit, cs),
             "TOP10": np.mean([fit_predict(by_id[i], fit, cs) for i in sw["top10_ids"]], axis=0),
             "BENCH": fit_predict({"family": "logistic", "features": "BENCH", "l2": 1}, fit, cs)}

    def z_vs_half(p):
        groups = [np.flatnonzero(sess == s) for s in np.unique(sess)]
        rng = np.random.default_rng(SEED)
        d = []
        for _ in range(2000):
            idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
            a = US.auc(p[idx], y[idx])
            if a is not None:
                d.append(a)
        se = float(np.std(d, ddof=1))
        return (US.auc(p, y) - 0.5) / se, se

    res = {"study": "CRYPTO_TUNE_v1", "ran_at": utc_stamp(), "range": CONFIRM_RANGE, "n": int(len(cs)),
           "sessions": int(len(np.unique(sess))), "selection": {"best_id": sw["best"]["id"], "top10_ids": sw["top10_ids"],
           "sweep_sha256": sha256_file(RESULTS / "SWEEP.json")}, "candidates": {}}
    for name, p in preds.items():
        z, se = z_vs_half(p)
        res["candidates"][name] = {**US.metrics(p, y), "z_vs_chance": z, "se": se}
    pb = {n: US.paired_boot(sess, y, preds[n], preds["BENCH"]) for n in ("BEST", "TOP10")}
    order = sorted(pb, key=lambda k: pb[k]["p_one_sided"])
    still = True
    for rank, n in enumerate(order):
        ok = still and pb[n]["p_one_sided"] <= 0.05 / (len(order) - rank)
        res["candidates"][n].update({"vs_bench": pb[n], "IMPROVES_ON_BENCH": bool(ok),
                                     "BEATS_CHANCE": bool(res["candidates"][n]["z_vs_chance"] >= 3)})
        still = ok
    pd.DataFrame({"ticker": cs["ticker"], "session": sess, "y": y, **{k.lower(): v for k, v in preds.items()}}).to_csv(
        RESULTS / "confirm_predictions.csv.gz", index=False)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--sweep", action="store_true")
    g.add_argument("--confirm", action="store_true")
    a = ap.parse_args()
    return freeze() if a.freeze else sweep() if a.sweep else confirm()


if __name__ == "__main__":
    sys.exit(main())

"""TUNE_SWEEP_v1: try hundreds of model scenarios for the next-day dump of US +30% spikes, pick on one period, confirm
once on periods the choice never saw.

Owner (2026-10-30): "do unlimited amount of scenarios ... fine tune this like a radio ... with historical results".

Stages (each refuses to run twice; protocol.json is frozen first):
    python3 tune.py --freeze     # writes protocol.json: data split, every scenario, the selection rule, the bar
    python3 tune.py --sweep      # fit each scenario on TRAIN (2020-2022), score on VALIDATE (2023): leaderboard
    python3 tune.py --confirm A  # once: refit the chosen candidates on 2020-2023, score CONFIRM_A (2026-04..10)
    python3 tune.py --confirm B  # once: the same on CONFIRM_B (2025-11..2026-03) when its labels exist

Label: y_NEXT_DUMP10_1 (the next session closes 10% or more below the signal close while fewer than half of the
five twins do), the statement LEARNER v2.4's registered claim is about. Features: v2.4's 33, computed by the same
functions in every period. The confirm sets are read only by --confirm, after the leaderboard is written.
"""
from __future__ import annotations

import argparse
import hashlib
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
from idxsig import learner3  # noqa: E402
from idxsig.provenance import sha256_file, utc_stamp  # noqa: E402

PROTO = HERE / "protocol.json"
RESULTS = HERE / "results"
LABEL = "y_NEXT_DUMP10_1"
# Five of v2.4's features are defined differently in the 2020-2023 warm start and in the replayed confirm sets
# (TUNE_SWEEP_v1 preflight review, 2026-10-30): has_edgar (history: filings dated after the session and a 2026
# ticker map), has_shares / log_shares / log_turnover (different share-count sources, coverage 0.69 vs 0.25) and
# has_short (a different population of names absent from FINRA's file). They are excluded from every scenario.
MISMATCHED = ("has_edgar", "has_shares", "log_shares", "log_turnover", "has_short")
FEATURES = [k for k in learner3.FEATURES if k not in MISMATCHED]
BLOCKS = {"P0": list(learner3.P0), "P1": list(learner3.P1), "E_US": [k for k in learner3.E_US if k not in MISMATCHED],
          "CHART": list(learner3.CHART), "BENCH": list(learner3.BENCH)}
# The warm start's panel begins 2020-01-02, so the 120-session bar/chart/age window is cut short before this session;
# those rows are left out of TRAIN and of the confirm refit (preflight review).
FULL_WINDOW_FROM = "2020-06-23"
CODE_PINS = ("idxsig/learner3.py", "idxsig/learner2.py", "research/TUNE_SWEEP_v1/tune.py")
FEATURE_SETS = {"ALL": FEATURES, "P0": BLOCKS["P0"], "P0_P1": BLOCKS["P0"] + BLOCKS["P1"],
                "P0_P1_E": BLOCKS["P0"] + BLOCKS["P1"] + BLOCKS["E_US"], "P0_P1_CHART": BLOCKS["P0"] + BLOCKS["P1"] + BLOCKS["CHART"],
                "BENCH": BLOCKS["BENCH"]}
WARM = "research/LEARNER_v2/warmstart_v4/events_us.csv.gz"
# Confirm sets: as-traded features (research/REPLAY_UNITS_v2, the corrected rebuild) and that study's v2.4 replay
CONFIRM = {"A": {"events": "research/REPLAY_UNITS_v2/data/events_A.csv.gz",
                 "build": "research/REPLAY_UNITS_v2/data/events_A_BUILD.json",
                 "labels": "research/REPLAY_UNITS_v2/results_A/forecasts.csv.gz", "range": ["2026-04-01", "2026-10-28"],
                 "v24_column": "NEXT_DUMP10_1_raw"},
           "B": {"events": "research/REPLAY_UNITS_v2/data/events_B.csv.gz",
                 "build": "research/REPLAY_UNITS_v2/data/events_B_BUILD.json",
                 "labels": "research/REPLAY_UNITS_v2/results_B/forecasts.csv.gz", "range": ["2025-11-03", "2026-03-31"],
                 "v24_column": "NEXT_DUMP10_1_raw"}}
SEED = 20261030


# ----------------------------------------------------------------------------------------------- scenarios
def scenarios() -> list[dict]:
    """Every scenario, in a fixed order. Fixed before any is fitted (hashed into protocol.json)."""
    out = []
    for fs, lam in itertools.product(FEATURE_SETS, (0.01, 0.1, 0.3, 1, 3, 10, 30, 100)):
        out.append({"family": "logistic", "features": fs, "l2": lam})
    for fs, (leaves, lr, trees, mcs, ff, bag) in itertools.product(
            ("ALL", "P0_P1_E", "P0_P1_CHART"),
            itertools.product((7, 15, 31, 63), (0.02, 0.05, 0.1), (100, 300, 600), (20, 50, 100), (0.6, 1.0), (0.7, 1.0))):
        out.append({"family": "lightgbm", "features": fs, "num_leaves": leaves, "learning_rate": lr, "n_estimators": trees,
                    "min_child_samples": mcs, "feature_fraction": ff, "bagging_fraction": bag})
    for fs, (depth, lr, it, l2) in itertools.product(("ALL", "P0_P1_E"),
                                                     itertools.product((3, 5, None), (0.03, 0.1), (100, 300), (0.0, 1.0))):
        out.append({"family": "hist_gb", "features": fs, "max_depth": depth, "learning_rate": lr, "max_iter": it,
                    "l2_regularization": l2})
    for fs, (kind, trees, leaf, mf) in itertools.product(("ALL", "P0_P1_E"),
                                                         itertools.product(("rf", "extra"), (300, 800), (5, 20, 50), (0.3, 0.6))):
        out.append({"family": kind, "features": fs, "n_estimators": trees, "min_samples_leaf": leaf, "max_features": mf})
    for fs, (hidden, alpha) in itertools.product(("ALL", "P0_P1_E"), itertools.product(((16,), (32,), (32, 16)), (1e-3, 1e-2, 1e-1))):
        out.append({"family": "mlp", "features": fs, "hidden": list(hidden), "alpha": alpha})
    for fs, k in itertools.product(("ALL", "P0_P1_E", "P0_P1"), (25, 50, 100, 200)):
        out.append({"family": "knn", "features": fs, "k": k})
    for i, s in enumerate(out):
        s["id"] = f"S{i:04d}"
    return out


def _standardise(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu, sd = np.nanmean(a, axis=0), np.nanstd(a, axis=0)
    mu, sd = np.where(np.isfinite(mu), mu, 0.0), np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
    return np.nan_to_num((a - mu) / sd), np.nan_to_num((b - mu) / sd)


def _logistic(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Ridge logistic by Newton steps (intercept unpenalised)."""
    Xi = np.c_[np.ones(len(X)), X]
    w = np.zeros(Xi.shape[1])
    pen = np.full(Xi.shape[1], lam)
    pen[0] = 0.0
    for _ in range(100):
        p = 1 / (1 + np.exp(-(Xi @ w)))
        g = Xi.T @ (y - p) - pen * w
        H = (Xi * (p * (1 - p))[:, None]).T @ Xi + np.diag(pen) + 1e-9 * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w += step
        if np.abs(step).max() < 1e-8:
            break
    return w


def fit_predict(s: dict, tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    cols = FEATURE_SETS[s["features"]]
    Xa, Xb = tr[cols].to_numpy(float), te[cols].to_numpy(float)
    y = tr[LABEL].to_numpy(float)
    f = s["family"]
    if f == "logistic":
        A, Bm = _standardise(Xa, Xb)
        w = _logistic(A, y, s["l2"])
        return 1 / (1 + np.exp(-(np.c_[np.ones(len(Bm)), Bm] @ w)))
    if f == "lightgbm":
        import lightgbm as lgb
        m = lgb.LGBMClassifier(num_leaves=s["num_leaves"], learning_rate=s["learning_rate"], n_estimators=s["n_estimators"],
                               min_child_samples=s["min_child_samples"], colsample_bytree=s["feature_fraction"],
                               subsample=s["bagging_fraction"], subsample_freq=1 if s["bagging_fraction"] < 1 else 0,
                               random_state=SEED, n_jobs=1, verbose=-1, deterministic=True, force_row_wise=True)
        m.fit(Xa, y)
        return m.predict_proba(Xb)[:, 1]
    if f == "hist_gb":
        from sklearn.ensemble import HistGradientBoostingClassifier
        m = HistGradientBoostingClassifier(max_depth=s["max_depth"], learning_rate=s["learning_rate"], max_iter=s["max_iter"],
                                           l2_regularization=s["l2_regularization"], random_state=SEED, early_stopping=False)
        m.fit(Xa, y)
        return m.predict_proba(Xb)[:, 1]
    if f in ("rf", "extra"):
        from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
        cls = RandomForestClassifier if f == "rf" else ExtraTreesClassifier
        m = cls(n_estimators=s["n_estimators"], min_samples_leaf=s["min_samples_leaf"], max_features=s["max_features"],
                random_state=SEED, n_jobs=4)
        m.fit(np.nan_to_num(Xa), y)
        return m.predict_proba(np.nan_to_num(Xb))[:, 1]
    if f == "mlp":
        from sklearn.neural_network import MLPClassifier
        A, Bm = _standardise(Xa, Xb)
        m = MLPClassifier(hidden_layer_sizes=tuple(s["hidden"]), alpha=s["alpha"], max_iter=500, early_stopping=True,
                          validation_fraction=0.15, random_state=SEED)
        m.fit(A, y)
        return m.predict_proba(Bm)[:, 1]
    if f == "knn":
        from sklearn.neighbors import KNeighborsClassifier
        A, Bm = _standardise(Xa, Xb)
        m = KNeighborsClassifier(n_neighbors=s["k"], weights="distance")
        m.fit(A, y)
        return m.predict_proba(Bm)[:, 1]
    raise ValueError(f)


# ----------------------------------------------------------------------------------------------- metrics
def auc(p: np.ndarray, y: np.ndarray) -> float | None:
    return learner3._auc(np.asarray(p, float), np.asarray(y, float))


def metrics(p: np.ndarray, y: np.ndarray) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    top = np.argsort(-p)[: max(1, len(p) // 10)]
    return {"auc": auc(p, y), "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "top10_dump_rate": float(y[top].mean()), "base_rate": float(y.mean()), "n": int(len(y))}


def paired_boot(sessions: np.ndarray, y: np.ndarray, a: np.ndarray, b: np.ndarray, resamples: int = 2000) -> dict:
    """AUC(a) - AUC(b) with a bootstrap over signal sessions: the difference, its 2.5%, 5% and 97.5% quantiles and
    the one-sided bootstrap p (share of resamples with a difference at or below zero)."""
    uniq = np.unique(sessions)
    groups = [np.flatnonzero(sessions == s) for s in uniq]
    rng = np.random.default_rng(SEED)
    d = []
    for _ in range(resamples):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        ua, ub = auc(a[idx], y[idx]), auc(b[idx], y[idx])
        if ua is not None and ub is not None:
            d.append(ua - ub)
    d = np.array(d)
    return {"diff": float(auc(a, y) - auc(b, y)), "q025": float(np.quantile(d, 0.025)), "q05": float(np.quantile(d, 0.05)),
            "q975": float(np.quantile(d, 0.975)), "p_one_sided": float((np.sum(d <= 0) + 1) / (len(d) + 1)),
            "resamples": int(len(d))}


# ----------------------------------------------------------------------------------------------- data
def warm() -> pd.DataFrame:
    if sha256_file(ROOT / WARM) != learner3.HISTORY_SHA256:
        raise RuntimeError("warm start differs from v2.4's pinned file")
    ev = pd.read_csv(ROOT / WARM, dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    return ev[ev[LABEL].notna() & (ev["session"] >= FULL_WINDOW_FROM)].reset_index(drop=True)


def confirm_set(key: str) -> pd.DataFrame:
    c = CONFIRM[key]
    build = json.loads((ROOT / c["build"]).read_text())
    if not str(build.get("units", "")).startswith("as_traded"):
        raise RuntimeError(f"confirm set {key} is not built in as-traded units")
    ev = pd.read_csv(ROOT / c["events"], dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    lab = pd.read_csv(ROOT / c["labels"], dtype={"ticker": str, "session": str})
    lab = lab.rename(columns={"NEXT_DUMP10_1_y": LABEL, c["v24_column"]: "v24_raw"})[["set_id", LABEL, "v24_raw"]]
    out = ev.merge(lab, on="set_id", how="inner")
    out = out[(out["session"] >= c["range"][0]) & (out["session"] <= c["range"][1]) & out[LABEL].notna()]
    return out.reset_index(drop=True)


# ----------------------------------------------------------------------------------------------- stages
def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    sc = scenarios()
    proto = {
        "study_id": "TUNE_SWEEP_v1", "frozen_at": utc_stamp(),
        "owner_instruction": "2026-10-30: unlimited scenarios, fine-tune on historical results, then minute intervals",
        "label": LABEL, "features": FEATURES, "feature_sets": FEATURE_SETS,
        "excluded_features": {"names": list(MISMATCHED), "why": "defined differently in history and in the confirm sets"},
        "split": {"TRAIN": [FULL_WINDOW_FROM, "2022-12-31"], "VALIDATE": ["2023-01-01", "2023-12-31"],
                  "REFIT_FOR_CONFIRM": [FULL_WINDOW_FROM, "2023-12-31"],
                  "CONFIRM_A": CONFIRM["A"]["range"], "CONFIRM_B": CONFIRM["B"]["range"]},
        "n_scenarios": len(sc), "scenarios_sha256": hashlib.sha256(json.dumps(sc, sort_keys=True).encode()).hexdigest(),
        "selection": "two candidates, fixed now: (1) BEST = the scenario with the highest VALIDATE AUC (ties: lower id); "
                     "(2) TOP10 = the mean of the ten highest-VALIDATE-AUC scenarios' probabilities. Both refit on "
                     "2020-2023 and score each confirm set once",
        "baseline": "v2.4 as replayed on the same events (its own raw forecasts, made session by session) and STATIC_V24 = "
                    "scenario logistic/ALL/l2=1 refit on 2020-2023 (v2.4's features in a fixed model)",
        "bar": "a candidate IMPROVES on v2.4 on a confirm set when Holm over the two candidates rejects on the "
               "one-sided session-bootstrap p of AUC(candidate) - AUC(v2.4 replay) <= 0 at 5% (smaller p tested at "
               "2.5%, the other at 5% only if the first rejects); it BEATS CHANCE when its AUC's z against 0.5 "
               "(session bootstrap se, 2000 resamples) is >= 3",
        "environment": "scikit-learn 1.9.1, lightgbm 4.7.0, scipy 1.18.1, pandas 2.2.3, numpy 2.3.5 (pinned venv)",
        "bootstrap": {"unit": "signal session", "resamples": 2000, "seed": SEED},
        "honesty": ["the VALIDATE leaderboard is optimistic by construction (many scenarios, one period): it is never the "
                    "reported skill; only the confirm sets are",
                    "CONFIRM_A's labels were read once before (RECENT_REPLAY_v1, v2.4's AUC); no scenario or selection "
                    "used them; CONFIRM_B has never been read by any study",
                    "no scenario is added, removed or re-tuned after --sweep; a new grid is a new study",
                    "survivorship: history survived to 2026-10-08 (3-6 years), confirm names only 0-12 months",
                    "CHART_SCALE (a fixed linear scaling with +-4 clipping) was computed over all 2020-2023 events, 2023 "
                    "included; it is v2.4's frozen constant and not re-estimated here",
                    "the grid is 88% LightGBM, so TOP10 is likely near-duplicate LightGBM settings"],
        "inputs": {WARM: sha256_file(ROOT / WARM)},
        "code": {p: sha256_file(ROOT / p) for p in CODE_PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    (HERE / "scenarios.json").write_text(json.dumps(sc, indent=0) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "n_scenarios", "split", "selection", "bar")}, indent=1))
    return 0


def check() -> dict:
    proto = json.loads(PROTO.read_text())
    for p, want in proto["code"].items():
        if sha256_file(ROOT / p) != want:
            raise RuntimeError(f"{p} changed since the freeze")
    sc = scenarios()
    if hashlib.sha256(json.dumps(sc, sort_keys=True).encode()).hexdigest() != proto["scenarios_sha256"]:
        raise RuntimeError("the scenario grid changed since the freeze")
    return proto


def sweep() -> int:
    check()
    out = RESULTS / "leaderboard.csv"
    if out.exists():
        sys.exit("error: the sweep runs once")
    ev = warm()
    tr = ev[ev["session"] <= "2022-12-31"].reset_index(drop=True)
    va = ev[(ev["session"] >= "2023-01-01") & (ev["session"] <= "2023-12-31")].reset_index(drop=True)
    yv = va[LABEL].to_numpy(float)
    rows, preds = [], {}
    t0 = time.time()
    for i, s in enumerate(scenarios()):
        try:
            p = fit_predict(s, tr, va)
            m = metrics(p, yv)
            preds[s["id"]] = p
        except Exception as exc:  # a scenario that cannot be fitted is recorded, never dropped silently
            m = {"error": f"{type(exc).__name__}: {exc}"}
        rows.append({"id": s["id"], "family": s["family"], "features": s["features"],
                     "params": json.dumps({k: v for k, v in s.items() if k not in ("id", "family", "features")}), **m})
        if i % 50 == 0:
            print(f"{i}/{len(scenarios())} scenarios, {time.time() - t0:.0f}s", flush=True)
    RESULTS.mkdir(exist_ok=True)
    lb = pd.DataFrame(rows).sort_values(["auc", "id"], ascending=[False, True])
    lb.to_csv(out, index=False)
    np.savez_compressed(RESULTS / "validate_predictions.npz", **preds)
    summary = {"ran_at": utc_stamp(), "train_n": len(tr), "validate_n": len(va), "scenarios": len(rows),
               "failed": int(lb["auc"].isna().sum()), "best": lb.iloc[0][["id", "family", "features", "params", "auc"]].to_dict(),
               "top10_ids": lb["id"].head(10).tolist(),
               "auc_spread": {"max": float(lb["auc"].max()), "median": float(lb["auc"].median()), "min": float(lb["auc"].min())},
               "by_family_best": lb.groupby("family")["auc"].max().round(4).to_dict()}
    (RESULTS / "SWEEP.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


def confirm(key: str) -> int:
    proto = check()
    out = RESULTS / f"CONFIRM_{key}.json"
    if out.exists():
        sys.exit(f"error: confirm {key} runs once")
    sw = json.loads((RESULTS / "SWEEP.json").read_text())
    lb = pd.read_csv(RESULTS / "leaderboard.csv").sort_values(["auc", "id"], ascending=[False, True])
    if lb["id"].head(10).tolist() != sw["top10_ids"] or lb.iloc[0]["id"] != sw["best"]["id"]:
        raise RuntimeError("SWEEP.json does not match the leaderboard")
    by_id = {s["id"]: s for s in scenarios()}
    ev = warm()
    fit = ev[(ev["session"] >= FULL_WINDOW_FROM) & (ev["session"] <= "2023-12-31")].reset_index(drop=True)
    cs = confirm_set(key)
    y, sess = cs[LABEL].to_numpy(float), cs["session"].to_numpy()
    best = fit_predict(by_id[sw["best"]["id"]], fit, cs)
    top10 = np.mean([fit_predict(by_id[i], fit, cs) for i in sw["top10_ids"]], axis=0)
    static = fit_predict({"family": "logistic", "features": "ALL", "l2": 1}, fit, cs)
    v24 = cs["v24_raw"].to_numpy(float)

    def z_vs_half(p):
        uniq = np.unique(sess)
        groups = [np.flatnonzero(sess == s) for s in uniq]
        rng = np.random.default_rng(SEED)
        draws = [auc(p[idx], y[idx]) for idx in (np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
                                                   for _ in range(2000))]
        se = float(np.std([d for d in draws if d is not None], ddof=1))
        return (auc(p, y) - 0.5) / se, se

    res = {"confirm": key, "ran_at": utc_stamp(), "range": CONFIRM[key]["range"], "n": int(len(cs)),
           "sessions": int(len(np.unique(sess))), "candidates": {},
           "selection": {"best_id": sw["best"]["id"], "top10_ids": sw["top10_ids"],
                         "sweep_sha256": sha256_file(RESULTS / "SWEEP.json"),
                         "leaderboard_sha256": sha256_file(RESULTS / "leaderboard.csv")},
           "inputs": {CONFIRM[key][k]: sha256_file(ROOT / CONFIRM[key][k]) for k in ("events", "build", "labels")}}
    raw_p = {}
    for name, p in (("BEST", best), ("TOP10", top10), ("STATIC_V24", static), ("V24_REPLAY", v24)):
        z, se = z_vs_half(p)
        res["candidates"][name] = {**metrics(p, y), "z_vs_chance": z, "se": se}
    for name, p in (("BEST", best), ("TOP10", top10)):
        pb = paired_boot(sess, y, p, v24)
        raw_p[name] = pb
        res["candidates"][name]["vs_v24"] = pb
    # Holm step-down over the two candidates on their one-sided bootstrap p: smaller p at 2.5%, then the other at 5%
    order = sorted(raw_p, key=lambda k: raw_p[k]["p_one_sided"])
    improves, still = {}, True
    for rank, name in enumerate(order):
        level = 0.05 / (len(order) - rank)
        improves[name] = bool(still and raw_p[name]["p_one_sided"] <= level)
        still = improves[name]
    for name in ("BEST", "TOP10"):
        res["candidates"][name]["IMPROVES_ON_V24"] = improves[name]
        res["candidates"][name]["BEATS_CHANCE"] = bool(res["candidates"][name]["z_vs_chance"] >= 3)
    pd.DataFrame({"set_id": cs["set_id"], "session": sess, "y": y, "best": best, "top10": top10, "static_v24": static,
                  "v24_replay": v24}).to_csv(RESULTS / f"confirm_{key}_predictions.csv.gz", index=False)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--sweep", action="store_true")
    g.add_argument("--confirm", choices=("A", "B"))
    a = ap.parse_args()
    return freeze() if a.freeze else sweep() if a.sweep else confirm(a.confirm)


if __name__ == "__main__":
    sys.exit(main())

"""CRYPTO_PUMP_HISTORY_v1: one run of protocol.json. Builds candidate rows for every event at both cut-offs from the hashed
hourly bars, fits BENCH and FULL in each fold, ranks every scored event's candidates, and writes results/ranks.csv.gz,
results/RESULT.json and the trial result file. Refuses to run twice."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import events as E  # noqa: E402

_spec = importlib.util.spec_from_file_location("ta_run", ROOT / "research" / "TA_HISTORY_v1" / "run.py")
ta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ta)  # TA_HISTORY_v1's fit() and design(), imported, not copied

PROTO = json.loads((HERE / "protocol.json").read_text())
RES = HERE / "results"
TRIALS = ROOT / "research" / "QUANT_GRADE" / "trials"
BARS = ROOT / "data" / "raw" / "binance_pumps"
SIZE = ["lv7", "lv30", "ltr30", "lage"]
PRIOR = ["np", "ds", "anyp"]
TAPE = ["r1", "r6", "r24", "r168", "vr24", "vr1", "rng24", "vol7"]
FULL = SIZE + PRIOR + TAPE
MODELS = {"BENCH": ["lv30"], "FULL": FULL}
EPS, B, SEED = 1e-8, 2000, 20261029


def hour_of(t: datetime) -> int:
    return int(t.timestamp()) // 3600


def load_bars(manifest: dict) -> dict:
    bars = {}
    for pair, h in manifest["pairs"].items():
        p = BARS / f"{pair}.npz"
        if hashlib.sha256(p.read_bytes()).hexdigest() != h:
            raise RuntimeError(f"{p.name} differs from the manifest")
        z = np.load(p)
        if len(z["hour"]):
            bars[pair] = {k: z[k] for k in ("hour", "high", "low", "close", "qvol", "trades")}
    return bars


def features(b: dict, L: int) -> dict | None:
    """Features of one pair from bars whose open hour is <= L (all closed by the cut-off); None when not a candidate."""
    hr = b["hour"]
    end = int(np.searchsorted(hr, L, "right"))
    if end == 0 or hr[end - 1] <= L - 24 or hr[0] > L - 7 * 24:
        return None

    def since(k):  # index of the first bar with open hour > L - k
        return int(np.searchsorted(hr, L - k, "right"))

    def vol(k):
        return float(b["qvol"][since(k):end].sum())

    def ret(k):
        j = int(np.searchsorted(hr, L - k, "right")) - 1
        return float(np.log(b["close"][end - 1] / b["close"][j])) if j >= 0 and b["close"][j] > 0 and b["close"][end - 1] > 0 else np.nan

    v1, v24, v30 = float(b["qvol"][end - 1]) if hr[end - 1] == L else 0.0, vol(24), vol(720)
    s24 = since(24)
    c7 = b["close"][since(168):end]
    lr = np.diff(np.log(c7[c7 > 0])) if (c7 > 0).sum() > 2 else np.array([])
    hi, lo = b["high"][s24:end], b["low"][s24:end]
    return {"lv7": float(np.log1p(vol(168))), "lv30": float(np.log1p(v30)),
            "ltr30": float(np.log1p(b["trades"][since(720):end].sum() / 720)), "lage": float(np.log1p((L - hr[0]) / 24)),
            "r1": ret(1), "r6": ret(6), "r24": ret(24), "r168": ret(168),
            "vr24": float(np.log((v24 + EPS) / (v30 / 30 + EPS))), "vr1": float(np.log((v1 + EPS) / (v24 / 24 + EPS))),
            "rng24": float(np.log(hi.max() / lo.min())) if len(hi) and lo.min() > 0 else np.nan,
            "vol7": float(lr.std()) if len(lr) > 2 else np.nan}


def candidate_rows(evs: list[dict], bars: dict, cutoff: str) -> tuple[pd.DataFrame, dict]:
    rows, dropped = [], {"pumped_pair_not_candidate": 0}
    past = {}
    for e in evs:
        past.setdefault(e["pair"], []).append(e["time"])
    for i, e in enumerate(evs):
        day0 = datetime.fromisoformat(e["date"]).replace(tzinfo=timezone.utc)
        cut = day0 if cutoff == "DAILY" else e["time"].replace(minute=0, second=0, microsecond=0) - pd.Timedelta(hours=1)
        L = hour_of(cut) - 1
        block = []
        for pair, b in bars.items():
            f = features(b, L)
            if f is None:
                continue
            prev = [t for t in past.get(pair, []) if t < cut]
            f.update({"np": float(np.log1p(len(prev))), "ds": float(np.log1p((cut - max(prev)).days if prev else 3650)),
                      "anyp": float(bool(prev)), "event": i, "date": e["date"], "pair": pair, "y": int(pair == e["pair"])})
            block.append(f)
        if not any(r["y"] for r in block):
            dropped["pumped_pair_not_candidate"] += 1
            continue
        rows += block
    return pd.DataFrame(rows), dropped


def ranks(df: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    d = df[["event", "date", "pair", "y"]].copy()
    d["p"] = p
    out = []
    for ev, g in d.groupby("event", sort=True):
        pp = g.loc[g["y"] == 1, "p"].iloc[0]
        others = g.loc[g["y"] == 0, "p"].to_numpy()
        out.append({"event": ev, "date": g["date"].iloc[0], "n": len(g), "rank": 1 + int((others >= pp).sum())})
    return pd.DataFrame(out)


def main() -> int:
    if (RES / "RESULT.json").exists():
        sys.exit("error: CRYPTO_PUMP_HISTORY_v1 has been run; one look only")
    bars = load_bars(json.loads((RES / "PRICE_MANIFEST.json").read_text()))
    evs = E.events()
    result = {"protocol": PROTO["protocol_id"], "events": len(evs), "cutoffs": {}}
    all_ranks, tests = [], {}
    rng = np.random.default_rng(SEED)
    for cutoff in ("DAILY", "HOURLY"):
        df, dropped = candidate_rows(evs, bars, cutoff)
        res = {"dropped": dropped, "candidate_rows": len(df), "events_kept": int(df["event"].nunique()), "folds": {}}
        per_fold = {}
        for name, f in PROTO["folds"].items():
            tr = df[(df["date"] >= f["fit"][0]) & (df["date"] <= f["fit"][1])]
            te = df[(df["date"] >= f["score"][0]) & (df["date"] <= f["score"][1])]
            fr, briers, coefs = {}, {}, {}
            for m, cols in MODELS.items():
                Xa, Xb = ta.design(tr, te, cols)
                beta = ta.fit(Xa, tr["y"].to_numpy(float))
                p = 1 / (1 + np.exp(-(Xb @ beta)))
                fr[m] = ranks(te, p)
                briers[m] = float(np.mean((p - te["y"].to_numpy()) ** 2))
                coefs[m] = dict(zip(cols, beta[1:].round(4).tolist()))
                all_ranks.append(fr[m].assign(cutoff=cutoff, fold=name, model=m))
            dates = fr["FULL"]["date"].to_numpy()
            cl = pd.factorize(dates)[0]
            per_fold[name] = {"r": {m: fr[m]["rank"].to_numpy() for m in MODELS}, "n": fr["FULL"]["n"].to_numpy(),
                              "members": [np.flatnonzero(cl == c) for c in range(cl.max() + 1)], "brier": briers,
                              "rows": len(te)}
            res["folds"][name] = {"events": len(fr["FULL"]), "median_candidates": float(np.median(fr["FULL"]["n"])),
                                  "top1": {m: float((fr[m]["rank"] <= 1).mean()) for m in MODELS},
                                  "top5": {m: float((fr[m]["rank"] <= 5).mean()) for m in MODELS},
                                  "top10": {m: float((fr[m]["rank"] <= 10).mean()) for m in MODELS},
                                  "mrr": {m: float((1 / fr[m]["rank"]).mean()) for m in MODELS},
                                  "chance_top5": float((5 / fr["FULL"]["n"]).mean()), "brier": briers,
                                  "coefficients_FULL": coefs["FULL"]}

        def pooled(sel=None):
            out = {}
            for metric in ("top5", "mrr"):
                vals = {m: [] for m in MODELS}
                for name, pf in per_fold.items():
                    idx = np.arange(len(pf["n"])) if sel is None else sel[name]
                    for m in MODELS:
                        r = pf["r"][m][idx]
                        vals[m].append((r <= 5).astype(float) if metric == "top5" else 1 / r)
                out[metric] = {m: float(np.concatenate(v).mean()) for m, v in vals.items()}
            return out

        p0 = pooled()
        boot = [pooled({n: np.concatenate([pf["members"][c] for c in rng.integers(0, len(pf["members"]), len(pf["members"]))])
                        for n, pf in per_fold.items()}) for _ in range(B)]
        brier = {m: sum(pf["brier"][m] * pf["rows"] for pf in per_fold.values()) / sum(pf["rows"] for pf in per_fold.values())
                 for m in MODELS}
        res["pooled"], res["pooled_brier"] = p0, brier
        for metric in ("top5", "mrr"):
            d = np.array([x[metric]["FULL"] - x[metric]["BENCH"] for x in boot])
            tests[f"{cutoff} {metric}"] = {"delta": p0[metric]["FULL"] - p0[metric]["BENCH"],
                                           "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                                           "p_one_sided": float((np.sum(d <= 0) + 1) / (B + 1)),
                                           "brier_full_lower": brier["FULL"] < brier["BENCH"]}
        result["cutoffs"][cutoff] = res
    order, adj, run = sorted(tests, key=lambda k: tests[k]["p_one_sided"]), {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * tests[k]["p_one_sided"]))
        adj[k] = run
    result["decision"] = {k: {**v, "holm_p": adj[k], "verdict": "BEATS VOLUME" if adj[k] <= 0.05 and v["brier_full_lower"] else "DOES NOT BEAT VOLUME"}
                          for k, v in tests.items()}
    pd.concat(all_ranks).to_csv(RES / "ranks.csv.gz", index=False)
    (RES / "RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=float) + "\n")
    trial = {"id": "CRYPTO_PUMP_HISTORY_v1_result", "experiment": "CRYPTO_PUMP_HISTORY_v1", "date": datetime.now(timezone.utc).date().isoformat(),
             "hypothesis": json.loads((TRIALS / "CRYPTO_PUMP_HISTORY_v1.json").read_text())["hypothesis"],
             "one_sided_p": min(adj.values()), "p_source": "research/CRYPTO_PUMP_HISTORY_v1/results/RESULT.json decision (Holm over four; bootstrap over event dates)",
             "variants_searched": 4, "outcome": "; ".join(f"{k} {v['verdict']}" for k, v in result["decision"].items()),
             "counted": True, "registered": "2026-10-29", "note": "the result of the PENDING registration CRYPTO_PUMP_HISTORY_v1.json: one trial"}
    (TRIALS / "CRYPTO_PUMP_HISTORY_v1_result.json").write_text(json.dumps(trial, indent=1) + "\n")
    print(json.dumps({k: {kk: v[kk] for kk in ("delta", "holm_p", "verdict")} for k, v in result["decision"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

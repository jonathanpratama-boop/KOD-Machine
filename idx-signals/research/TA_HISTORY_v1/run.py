"""TA_HISTORY_v1: one run of protocol.json. Computes the RESEARCH and CHART indicators for every event from the pinned
price panel, fits BASE, BASE + RESEARCH, BASE + CHART and BASE + both in each fold, scores once, and writes
results/indicators.csv.gz, results/RESULT.json and the trial result file. Refuses to run twice."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import global_panel, learner3  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

PROTO = json.loads((HERE / "protocol.json").read_text())
RES = HERE / "results"
TRIALS = ROOT / "research" / "QUANT_GRADE" / "trials"
BASE = list(learner3.FEATURES)
RESEARCH = ["max20", "near_high252", "mom_12_1", "has_year"]
CHART = ["rsi14", "macd_hist", "stoch_k14", "bollinger_b"]
BLOCKS = {"BASE": BASE, "RESEARCH": BASE + RESEARCH, "CHART": BASE + CHART, "BOTH": BASE + RESEARCH + CHART}
STATEMENTS = {"NEXT_DUMP10_1": "y_NEXT_DUMP10_1", "DUMP10_5": "y_DUMP10_5"}
LAM, LAM_ICPT, B, SEED = 16.0, 1 / 1.5 ** 2, 2000, 20261029


def indicators(ev: pd.DataFrame) -> pd.DataFrame:
    p = PROTO["prices"]
    df, meta = global_panel.load(ROOT / p["manifest"])
    if meta["sha256"] != p["panel_sha256"]:
        raise RuntimeError("panel hash differs from the protocol")
    df = df[df["date"] <= "2023-12-29"]
    m = Market.from_panel(df, price_limits=False)
    tickers, dates = {t: i for i, t in enumerate(m.tickers.astype(str))}, {d: j for j, d in enumerate(m.dates.astype(str))}
    with np.errstate(divide="ignore", invalid="ignore"):
        ok = m.present & (m.prev > 0) & (m.close > 0)
        logret = np.where(ok, np.log(m.close / m.prev), 0.0)
        ret1 = np.where(ok, m.close / m.prev - 1, np.nan)
    level = np.exp(np.cumsum(logret, axis=1))
    with np.errstate(divide="ignore", invalid="ignore"):
        hi = np.where(m.present & (m.close > 0), m.high / m.close, np.nan) * level
        lo = np.where(m.present & (m.close > 0), m.low / m.close, np.nan) * level
    rows = []
    for r in ev.itertuples(index=False):
        n, d = tickers.get(r.ticker), dates.get(r.session)
        out = {k: np.nan for k in RESEARCH + CHART}
        if n is None or d is None:
            rows.append(out)
            continue
        pres = m.present[n]
        w = slice(max(0, d - 20), d)
        rr = ret1[n, w][pres[w]]
        if len(rr) >= 15:
            out["max20"] = float(np.nanmax(rr))
        w = slice(max(0, d - 251), d + 1)
        if d >= 251 and pres[w].sum() >= 200:
            out["near_high252"] = float(level[n, d] / np.max(level[n, w][pres[w]]))
        if d >= 252 and pres[d - 21] and pres[d - 252]:
            out["mom_12_1"] = float(level[n, d - 21] / level[n, d - 252] - 1)
        out["has_year"] = float(np.isfinite(out["near_high252"]) and np.isfinite(out["mom_12_1"]))
        c = pd.Series(level[n, max(0, d - 120): d + 1][pres[max(0, d - 120): d + 1]])
        if len(c) >= 30:
            diff = c.diff()
            up = diff.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
            dn = (-diff.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
            out["rsi14"] = float(100.0 if dn == 0 else 100 - 100 / (1 + up / dn))
            macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
            out["macd_hist"] = float((macd - macd.ewm(span=9, adjust=False).mean()).iloc[-1] / c.iloc[-1])
            h14 = hi[n, max(0, d - 13): d + 1]; l14 = lo[n, max(0, d - 13): d + 1]
            span = np.nanmax(h14) - np.nanmin(l14)
            out["stoch_k14"] = float((c.iloc[-1] - np.nanmin(l14)) / span) if span > 0 else np.nan
            ma, sd = c.iloc[-20:].mean(), c.iloc[-20:].std()
            out["bollinger_b"] = float((c.iloc[-1] - (ma - 2 * sd)) / (4 * sd)) if sd > 0 else np.nan
        rows.append(out)
    return pd.DataFrame(rows, index=ev.index)


def fit(X, y):
    lam = np.r_[LAM_ICPT, np.full(X.shape[1] - 1, LAM)]
    beta = np.zeros(X.shape[1])

    def obj(b):
        z = X @ b
        return float(np.sum(np.logaddexp(0, z) - y * z) + 0.5 * np.sum(lam * b * b))

    f0 = obj(beta)
    for _ in range(200):
        p = 1 / (1 + np.exp(-(X @ beta)))
        g = X.T @ (p - y) + lam * beta
        if np.linalg.norm(g) < 1e-8:
            return beta
        H = X.T @ (X * (p * (1 - p))[:, None]) + np.diag(lam)
        step, t = np.linalg.solve(H, g), 1.0
        while t > 1e-10:
            f1 = obj(beta - t * step)
            if f1 <= f0 + 1e-12 * (1 + abs(f0)):
                break
            t /= 2
        beta, f0 = beta - t * step, f1
    raise RuntimeError("Newton did not converge")


def design(train: pd.DataFrame, test: pd.DataFrame, cols: list[str]):
    a, b = train[cols].to_numpy(float), test[cols].to_numpy(float)
    mu, sd = np.nanmean(a, axis=0), np.nanstd(a, axis=0)
    mu, sd = np.where(np.isfinite(mu), mu, 0.0), np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
    za, zb = np.nan_to_num((a - mu) / sd), np.nan_to_num((b - mu) / sd)
    return np.c_[np.ones(len(za)), za], np.c_[np.ones(len(zb)), zb]


def auc(p, y):
    pos, neg = int(y.sum()), int(len(y) - y.sum())
    if not pos or not neg:
        return float("nan"), 0
    rk = pd.Series(p).rank(method="average").to_numpy()
    return float((rk[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg)), pos * neg


def main() -> int:
    if (RES / "RESULT.json").exists():
        sys.exit("error: TA_HISTORY_v1 has been run; one look only")
    e = PROTO["events"]
    path = ROOT / e["file"]
    if sha256_file(path) != e["sha256"]:
        raise RuntimeError("event file hash differs from the protocol")
    ev = pd.read_csv(path, dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    ind = indicators(ev)
    ev = pd.concat([ev, ind], axis=1)
    RES.mkdir(exist_ok=True)
    ev[["ticker", "session", *RESEARCH, *CHART]].to_csv(RES / "indicators.csv.gz", index=False)
    result = {"protocol": PROTO["protocol_id"], "events": len(ev),
              "coverage": {k: float(ev[k].notna().mean()) for k in RESEARCH[:3] + CHART}, "statements": {}}
    rng = np.random.default_rng(SEED)
    for stmt, col in STATEMENTS.items():
        res = {"folds": {}}
        folds = {}
        for name, f in PROTO["folds"].items():
            if name == "note":
                continue
            g = ev[ev[col].notna()]
            tr = g[(g["session"] >= f["fit"][0]) & (g["session"] <= f["fit"][1])]
            te = g[(g["session"] >= f["score"][0]) & (g["session"] <= f["score"][1])]
            y_tr, y_te = tr[col].to_numpy(float), te[col].to_numpy(float)
            preds, coefs = {}, {}
            for blk, cols in BLOCKS.items():
                Xa, Xb = design(tr, te, cols)
                beta = fit(Xa, y_tr)
                preds[blk] = 1 / (1 + np.exp(-(Xb @ beta)))
                coefs[blk] = dict(zip(cols, beta[1:].round(4).tolist()))
            weeks = pd.to_datetime(te["session"]).dt.strftime("%G-W%V").to_numpy()
            cl = pd.factorize(weeks)[0]
            members = [np.flatnonzero(cl == c) for c in range(cl.max() + 1)]
            folds[name] = (y_te, preds, members)
            res["folds"][name] = {"n_fit": len(tr), "n_score": len(te), "rate_score": float(y_te.mean()),
                                  "auc": {b: auc(p, y_te)[0] for b, p in preds.items()},
                                  "brier": {b: float(np.mean((p - y_te) ** 2)) for b, p in preds.items()},
                                  "coefficients": {b: {k: v for k, v in c.items() if k in RESEARCH + CHART} for b, c in coefs.items() if b != "BASE"}}

        def pooled(sel=None):
            """Pooled AUC per block and pooled Brier per block over the folds (sel: one bootstrap draw per fold)."""
            num = {b: 0.0 for b in BLOCKS}; den = {b: 0.0 for b in BLOCKS}; br = {b: 0.0 for b in BLOCKS}; nb = 0
            for name, (y, preds, members) in folds.items():
                idx = np.arange(len(y)) if sel is None else sel[name]
                for b, p in preds.items():
                    a, w = auc(p[idx], y[idx])
                    if w:
                        num[b] += a * w; den[b] += w
                    br[b] += float(np.sum((p[idx] - y[idx]) ** 2))
                nb += len(idx)
            return {b: num[b] / den[b] for b in BLOCKS}, {b: br[b] / nb for b in BLOCKS}

        a0, b0 = pooled()
        boot = []
        for _ in range(B):
            sel = {name: np.concatenate([mem[c] for c in rng.integers(0, len(mem), len(mem))]) for name, (_, _, mem) in folds.items()}
            boot.append(pooled(sel)[0])
        res["pooled_auc"] = a0
        res["pooled_brier"] = b0
        res["delta"] = {}
        for blk in ("RESEARCH", "CHART", "BOTH"):
            d = np.array([x[blk] - x["BASE"] for x in boot])
            res["delta"][blk] = {"delta_auc": a0[blk] - a0["BASE"], "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                                 "p_one_sided": float((np.sum(d <= 0) + 1) / (B + 1)),
                                 "brier_gain_over_base": b0["BASE"] - b0[blk]}
        result["statements"][stmt] = res
    tests = [(blk, st) for blk in ("RESEARCH", "CHART") for st in STATEMENTS]
    ps = {t: result["statements"][t[1]]["delta"][t[0]]["p_one_sided"] for t in tests}
    order, adj, run = sorted(ps, key=ps.get), {}, 0.0
    for i, t in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[t]))
        adj[t] = run
    result["decision"] = {f"{blk} on {st}": {"holm_p": adj[(blk, st)],
                                              "brier_gain_over_base": result["statements"][st]["delta"][blk]["brier_gain_over_base"],
                                              "verdict": "ADDS" if adj[(blk, st)] <= 0.05 and result["statements"][st]["delta"][blk]["brier_gain_over_base"] > 0 else "DOES NOT ADD"}
                          for blk, st in tests}
    (RES / "RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    trial = {"id": "TA_HISTORY_v1_result", "experiment": "TA_HISTORY_v1", "date": "2026-10-29",
             "hypothesis": json.loads((TRIALS / "TA_HISTORY_v1.json").read_text())["hypothesis"],
             "one_sided_p": min(adj.values()), "p_source": "research/TA_HISTORY_v1/results/RESULT.json decision (Holm over four; week-cluster bootstrap)",
             "variants_searched": 4, "outcome": "; ".join(f"{k} {v['verdict']}" for k, v in result["decision"].items()),
             "counted": True, "registered": "2026-10-29", "note": "the result of the PENDING registration TA_HISTORY_v1.json: one trial"}
    (TRIALS / "TA_HISTORY_v1_result.json").write_text(json.dumps(trial, indent=1) + "\n")
    print(json.dumps(result["decision"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

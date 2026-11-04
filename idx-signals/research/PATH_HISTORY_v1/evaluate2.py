"""PATH_HISTORY_v1 evaluation (evaluate2.py supersedes evaluate.py, ADDENDUM_3), per protocol.json and addenda 1-3: fit on train rows, score test rows once.

Reads results/events.csv.gz (build.py) and data/ (collect.py); writes results/RESULT.json, REPORT.md and the trial
result file. Every "pooled" AUC is the within-market (stratified) AUC (addendum 2).
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA, RES = HERE / "data", HERE / "results"
TRIALS = ROOT / "research" / "QUANT_GRADE" / "trials"
P0 = ("s_ret1", "s_ret5", "s_ret20", "s_dd60", "log_volr", "s_cpos", "log_adv")
P1 = P0 + ("gap", "vol20_pre", "spike_z", "log_price", "spikes60", "streak", "dist_high252", "log_age", "breadth", "mkt_ret",
           "ara_streak")
E_EXTRA = ("news", "offering90", "shelf3y", "atm12m", "revsplit12m", "short_ratio", "short_abn", "log_turnover",
           "log_shares", "has_edgar", "has_short", "has_shares")
PRIMARY = ("DUMP10_5", "PUMP30_5", "NEXT_DUMP10", "NEXT_LOSES")
SECONDARY = ("PUMP_AND_DUMP_5", "PUMP30_20", "PUMP100_20", "NEXT_RUN10", "BEATS_TWINS_5")
MARKETS = ("US", "CRYPTO", "IDX")
LAM_SHARED, LAM_TASK, LAM_ICPT = 16.0, 25.0, 1 / 1.5 ** 2
B, SEED, SMOOTH = 2000, 20261029, 20.0
NEWS = {"8-K", "8-K/A", "6-K", "6-K/A"}
OFFER = {"S-1", "S-1/A", "S-1MEF", "F-1", "F-1/A", "S-3", "F-3", "S-3ASR", "424B1", "424B3", "424B4", "424B5"}
SHELF = {"S-3", "F-3", "S-3ASR"}


# ------------------------------------------------------------------------------- E_US features
def us_features(ev: pd.DataFrame) -> pd.DataFrame:
    us = ev[ev["market"] == "US"]
    out = pd.DataFrame(0.0, index=ev.index, columns=list(E_EXTRA))
    fil = pd.read_csv(DATA / "us_filings.csv.gz", dtype={"ticker": str, "form": str, "filingDate": str})
    fil["form"] = fil["form"].str.upper()
    by_t = {t: g for t, g in fil.groupby("ticker")}
    cik_of = fil.groupby("ticker")["cik"].first().to_dict()
    sh = pd.read_csv(DATA / "us_shares.csv.gz", dtype={"end": str})
    sh_by = {int(c): g.sort_values("end") for c, g in sh.groupby("cik")}
    sv = pd.read_csv(DATA / "us_short.csv.gz", dtype={"ticker": str, "date": str})
    sv = sv[sv["total_volume"] > 0].assign(ratio=lambda x: x["short_volume"] / x["total_volume"])
    sv_by = {t: g.sort_values("date").set_index("date")["ratio"] for t, g in sv.groupby("ticker")}
    for i, r in us.iterrows():
        d, dd = r["session"], date.fromisoformat(r["session"])
        g = by_t.get(r["ticker"])
        if g is not None:
            fd, form = g["filingDate"], g["form"]
            out.at[i, "has_edgar"] = 1.0
            out.at[i, "news"] = float((form.isin(NEWS) & fd.isin([r["prev_session"], d])).any())
            out.at[i, "offering90"] = float((form.isin(OFFER) & (fd > (dd - timedelta(days=90)).isoformat()) & (fd <= d)).any())
            out.at[i, "shelf3y"] = float((form.isin(SHELF) & (fd > (dd - timedelta(days=3 * 365)).isoformat()) & (fd <= d)).any())
            out.at[i, "atm12m"] = float(((form == "424B5") & (fd > (dd - timedelta(days=365)).isoformat()) & (fd <= d)).any())
            c = sh_by.get(int(cik_of[r["ticker"]]))
            if c is not None:
                cand = c[c["end"] <= (dd - timedelta(days=120)).isoformat()]
                splits = [s for s in str(r.get("split_dates_2y") or "").split("|") if s and s != "nan"]
                if len(cand):
                    last = cand.iloc[-1]
                    if float(last["val"]) > 0 and not any(last["end"] < s <= d for s in splits):
                        out.at[i, "has_shares"] = 1.0
                        out.at[i, "log_shares"] = math.log10(float(last["val"]))
                        vt = r.get("vol_traded")
                        if vt is not None and np.isfinite(vt) and vt > 0:
                            out.at[i, "log_turnover"] = math.log10(float(vt) / float(last["val"]))
        out.at[i, "revsplit12m"] = float(bool(r.get("revsplit12m")) and str(r.get("revsplit12m")) != "False")
        s = sv_by.get(r["ticker"])
        if s is not None and d in s.index:
            out.at[i, "has_short"] = 1.0
            out.at[i, "short_ratio"] = float(s.loc[d])
            prev = s[s.index < d].tail(20)
            if len(prev) >= 5:
                out.at[i, "short_abn"] = float(s.loc[d] - prev.median())
    return out


# ------------------------------------------------------------------------------- model
def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def fit(X: np.ndarray, y: np.ndarray, lam: np.ndarray) -> np.ndarray:
    """Penalised logistic regression by Newton with step-halving; raises unless the gradient norm falls below 1e-8."""
    beta = np.zeros(X.shape[1])

    def obj(b):
        z = X @ b
        return float(np.sum(np.logaddexp(0, z) - y * z) + 0.5 * np.sum(lam * b * b))

    f0 = obj(beta)
    for _ in range(200):
        p = sigmoid(X @ beta)
        g = X.T @ (p - y) + lam * beta
        if np.linalg.norm(g) < 1e-8:
            return beta
        H = X.T @ (X * (p * (1 - p))[:, None]) + np.diag(lam)
        step = np.linalg.solve(H, g)
        t = 1.0
        while t > 1e-8:
            f1 = obj(beta - t * step)
            if f1 <= f0 + 1e-12 * (1 + abs(f0)):
                break
            t /= 2
        beta, f0 = beta - t * step, f1
    raise RuntimeError("Newton did not converge")


def design(Z: np.ndarray, mk: np.ndarray, markets: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Market intercepts, shared slopes, and market deviations when there is more than one market."""
    cols, lam = [], []
    for m in markets:
        cols.append((mk == m).astype(float)[:, None]); lam.append(np.array([LAM_ICPT]))
    cols.append(Z); lam.append(np.full(Z.shape[1], LAM_SHARED))
    if len(markets) > 1:
        for m in markets:
            cols.append(Z * (mk == m)[:, None]); lam.append(np.full(Z.shape[1], LAM_TASK))
    return np.hstack(cols), np.concatenate(lam)


def standardise(train: np.ndarray, *others: np.ndarray):
    mu = np.nanmean(train, axis=0)
    sd = np.nanstd(train, axis=0)
    sd = np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
    mu = np.where(np.isfinite(mu), mu, 0.0)
    return [np.nan_to_num((a - mu) / sd, nan=0.0) for a in (train, *others)]


# ------------------------------------------------------------------------------- metrics
def strat_auc(p: np.ndarray, y: np.ndarray, mk: np.ndarray) -> float:
    num = den = 0.0
    for m in MARKETS:
        s = mk == m
        pos, neg = int(y[s].sum()), int(s.sum() - y[s].sum())
        if pos == 0 or neg == 0:
            continue
        r = pd.Series(p[s]).rank(method="average").to_numpy()
        auc = (r[y[s] == 1].sum() - pos * (pos + 1) / 2) / (pos * neg)
        num += auc * pos * neg
        den += pos * neg
    return num / den if den else float("nan")


def context_feature(ev: pd.DataFrame, stmt: str, tr: np.ndarray, te: np.ndarray, base: dict) -> np.ndarray:
    """The keyboard prior: a smoothed frequency of the statement in the same context in train rows (leave-one-out for
    train rows), as logit(P_ctx) - logit(p_market)."""
    def key(r):
        sp = min(int(r["spikes60"]), 2)
        st = 1 if r["streak"] <= 1 else (2 if r["streak"] == 2 else 3)
        g = r["gap"]
        gb = "na" if g is None or not np.isfinite(g) else (0 if g < 0.10 else (1 if g < 0.30 else 2))
        k = (r["market"], sp, st, gb)
        if r["market"] == "US":
            k += (int(r["news"]), int(r["offering90"] or r["atm12m"]))
        return k

    keys = [key(r) for _, r in ev.iterrows()]
    y = ev[f"S_{stmt}"].to_numpy()
    n, h = {}, {}
    for i in np.flatnonzero(tr):
        n[keys[i]] = n.get(keys[i], 0) + 1
        h[keys[i]] = h.get(keys[i], 0) + y[i]
    out = np.zeros(len(ev))
    for i in np.flatnonzero(tr | te):
        pm = base[ev["market"].iat[i]]
        nn, hh = n.get(keys[i], 0), h.get(keys[i], 0.0)
        if tr[i]:
            nn, hh = nn - 1, hh - y[i]
        pc = (hh + SMOOTH * pm) / (nn + SMOOTH)
        pc = min(max(pc, 1e-4), 1 - 1e-4)
        out[i] = math.log(pc / (1 - pc)) - math.log(pm / (1 - pm))
    return out


def run_statement(ev: pd.DataFrame, us_x: pd.DataFrame, stmt: str, k: int) -> dict:
    y_all = ev[f"S_{stmt}"]
    graded = y_all.notna().to_numpy()
    tr = graded & (ev["split"] == "train").to_numpy()
    te = graded & (ev["split"] == "test").to_numpy()
    y = np.nan_to_num(y_all.to_numpy(dtype=float))
    mk = ev["market"].to_numpy()
    markets = tuple(m for m in MARKETS if tr[mk == m].sum() > 0)
    base = {m: float(y[tr & (mk == m)].mean()) for m in markets}
    anchor = np.array([base.get(m, np.nan) for m in mk])
    full = pd.concat([ev, us_x], axis=1)
    ctx = context_feature(full, stmt, tr, te, base)
    preds = {}
    coefs = {}
    blocks = {"P0": list(P0), "P1": list(P1), "CONTEXT": list(P1) + ["ctx"]}
    full = full.assign(ctx=ctx)
    for name, cols in blocks.items():
        Xtr, Xte = standardise(full.loc[tr, cols].to_numpy(dtype=float), full.loc[te, cols].to_numpy(dtype=float))
        Dtr, lam = design(Xtr, mk[tr], markets)
        Dte, _ = design(Xte, mk[te], markets)
        beta = fit(Dtr, y[tr], lam)
        preds[name] = sigmoid(Dte @ beta)
        if name == "P1":
            coefs[name] = dict(zip(cols, beta[len(markets): len(markets) + len(cols)].round(4).tolist()))
    us_tr, us_te = tr & (mk == "US"), te & (mk == "US")
    cols = list(P1) + list(E_EXTRA)
    if us_tr.sum() and us_te.sum():
        Xtr, Xte = standardise(full.loc[us_tr, cols].to_numpy(dtype=float), full.loc[us_te, cols].to_numpy(dtype=float))
        Dtr, lam = design(Xtr, mk[us_tr], ("US",))
        Dte, _ = design(Xte, mk[us_te], ("US",))
        beta = fit(Dtr, y[us_tr], lam)
        e_pred = sigmoid(Dte @ beta)
        coefs["E_US"] = dict(zip(cols, beta[1: 1 + len(cols)].round(4).tolist()))
    else:
        e_pred = None
    yt, mt, at = y[te], mk[te], anchor[te]
    weeks = pd.to_datetime(ev.loc[te, "session"]).dt.strftime("%G-W%V").to_numpy()
    cl = pd.factorize(weeks)[0]
    members = [np.flatnonzero(cl == c) for c in range(cl.max() + 1)]
    rng = np.random.default_rng([SEED, k])
    draws = [np.concatenate([members[c] for c in rng.integers(0, len(members), len(members))]) for _ in range(B)]
    us_pos = np.flatnonzero(mt == "US")
    us_map = {j: q for q, j in enumerate(us_pos)}

    def summary(p, idx_rows=None, ref=None):
        """AUC, Brier gain and bootstrap for predictions p on the test rows (or on the US test rows)."""
        sel = np.arange(len(yt)) if idx_rows is None else idx_rows
        yy, mm, aa = yt[sel], mt[sel], at[sel]
        auc = strat_auc(p, yy, mm)
        gain = float(np.mean((aa - yy) ** 2 - (p - yy) ** 2))
        bs, bg, bd = [], [], []
        for dr in draws:
            if idx_rows is not None:
                dr = np.array([us_map[j] for j in dr if j in us_map], dtype=int)
            if not len(dr):
                continue
            bs.append(strat_auc(p[dr], yy[dr], mm[dr]))
            bg.append(float(np.mean((aa[dr] - yy[dr]) ** 2 - (p[dr] - yy[dr]) ** 2)))
            if ref is not None:
                bd.append(bs[-1] - strat_auc(ref[dr], yy[dr], mm[dr]))
        bs = np.array(bs)
        res = {"auc": auc, "auc_ci95": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))],
               "p_auc_le_half": float((np.sum(bs <= 0.5) + 1) / (len(bs) + 1)),
               "brier_gain": gain, "brier_gain_ci95": [float(np.percentile(bg, 2.5)), float(np.percentile(bg, 97.5))],
               "brier_skill": 1 - float(np.mean((p - yy) ** 2)) / float(np.mean((aa - yy) ** 2)),
               "per_market_auc": {m: strat_auc(p[mm == m], yy[mm == m], mm[mm == m]) for m in MARKETS if (mm == m).sum()}}
        if ref is not None:
            bd = np.array(bd)
            res["delta_auc"] = auc - strat_auc(ref, yy, mm)
            res["delta_auc_ci95"] = [float(np.nanpercentile(bd, 2.5)), float(np.nanpercentile(bd, 97.5))]
        return res

    out = {"n_train": int(tr.sum()), "n_test": int(te.sum()),
           "rate_train": {m: base[m] for m in markets},
           "rate_test": {m: float(yt[mt == m].mean()) for m in MARKETS if (mt == m).sum()},
           "n_test_by_market": {m: int((mt == m).sum()) for m in MARKETS if (mt == m).sum()},
           "blocks": {"P0": summary(preds["P0"]), "P1": summary(preds["P1"], ref=preds["P0"]),
                      "CONTEXT": summary(preds["CONTEXT"], ref=preds["P0"])},
           "coefficients_standardised": coefs}
    seg = ev.loc[te, "segment"].to_numpy()
    idx26 = seg == "IDX:2025-02-24..2026-10-06"
    if idx26.sum():
        out["IDX_2025_2026_P1_auc"] = strat_auc(preds["P1"][idx26], yt[idx26], mt[idx26])
        out["IDX_2025_2026_n"] = int(idx26.sum())
    if e_pred is not None:
        out["blocks"]["E_US"] = summary(e_pred, idx_rows=us_pos, ref=preds["P1"][us_pos])
    return out


def holm(ps: dict) -> dict:
    order = sorted(ps, key=ps.get)
    adj, run = {}, 0.0
    for i, s in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[s]))
        adj[s] = run
    return adj


def main():
    ev = pd.read_csv(RES / "events.csv.gz", dtype={"ticker": str, "session": str, "prev_session": str,
                                                 "split_dates_2y": str, "twins": str}, keep_default_na=False,
                     na_values=[""])
    us_x = us_features(ev)
    result = {"protocol": "KOD-PATH-HISTORY-v1", "addenda": ["ADDENDUM_1.md", "ADDENDUM_2.md"],
              "events": int(len(ev)), "events_by_market": ev.groupby("market").size().to_dict(),
              "events_by_split": ev.groupby("split").size().to_dict(),
              "us_coverage": {k: float(us_x.loc[ev["market"] == "US", k].mean()) for k in ("has_edgar", "has_short", "has_shares", "news", "offering90", "shelf3y", "atm12m", "revsplit12m")},
              "statements": {}}
    for k, stmt in enumerate(PRIMARY + SECONDARY):
        print(f"evaluating {stmt}", flush=True)
        result["statements"][stmt] = run_statement(ev, us_x, stmt, k)
    ps = {s: result["statements"][s]["blocks"]["P1"]["p_auc_le_half"] for s in PRIMARY}
    adj = holm(ps)
    decision = {}
    for s in PRIMARY:
        b = result["statements"][s]["blocks"]["P1"]
        decision[s] = {"holm_p": adj[s], "brier_gain": b["brier_gain"],
                       "verdict": "LEARNABLE" if adj[s] <= 0.05 and b["brier_gain"] > 0 else "NOT_LEARNABLE_WITH_THESE_FEATURES"}
    result["decision"] = decision
    RES.mkdir(exist_ok=True)
    (RES / "RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=float) + "\n")
    trial = {"id": "PATH_HISTORY_v1_result", "experiment": "PATH_HISTORY_v1", "date": "2026-10-29",
             "hypothesis": json.loads((TRIALS / "PATH_HISTORY_v1.json").read_text())["hypothesis"],
             "one_sided_p": min(adj.values()), "p_source": "research/PATH_HISTORY_v1/results/RESULT.json decision (Holm-adjusted, smallest of the four primary statements; cluster bootstrap over signal ISO weeks)",
             "variants_searched": 4,
             "outcome": "; ".join(f"{s} {d['verdict']}" for s, d in decision.items()),
             "counted": True, "registered": "2026-10-29",
             "note": "the result of the PENDING registration PATH_HISTORY_v1.json: one trial (ADDENDUM_2)"}
    (TRIALS / "PATH_HISTORY_v1_result.json").write_text(json.dumps(trial, indent=1) + "\n")
    print(json.dumps(decision, indent=1))


if __name__ == "__main__":
    main()

"""NEIGHBOURS_v1 single run (PROTOCOL.md + ADDENDUM_1.md). Usage: python3 run.py (after build.py)"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
if (HERE / "RESULT.json").exists(): sys.exit("RESULT.json exists; runs once")
d = pd.read_csv(HERE / "rows.csv.gz", parse_dates=["date"])
d = d[d.peers_ok & d.fwd5.notna() & d.fwd3.notna() & d.fwd1.notna()].reset_index(drop=True)
COIN_A = ["ret1", "ret3", "ret7", "ret20", "volr", "hi60", "vol20"]; DAY_A = ["btc7", "breadth"]
COIN_B = ["p_ret1", "p_ret3", "p_ret7", "p_part", "rel7"]
ST = [f"st{s}_r{h}" for s in range(1, 6) for h in (1, 3)]
g = d.groupby("date")
for c in COIN_A + COIN_B:
    d[c + "_rk"] = g[c].rank(pct=True) - 0.5
    d[c + "_rk"] = d[c + "_rk"].fillna(0.0)
y = d.fwd3 - g.fwd3.transform("mean")
lo, hi = g.fwd3.transform(lambda s: s.quantile(.01)) - g.fwd3.transform("mean"), g.fwd3.transform(lambda s: s.quantile(.99)) - g.fwd3.transform("mean")
d["y"] = y.clip(lo, hi)
def design(model, tr_mask):
    cols = [c + "_rk" for c in COIN_A]
    X = [d[cols].to_numpy(float)]
    mu = d.loc[tr_mask, DAY_A].mean(); sd = d.loc[tr_mask, DAY_A].std().replace(0, 1)
    X.append(((d[DAY_A] - mu) / sd).fillna(0).to_numpy(float))
    if model in ("B", "C"): X.append(d[[c + "_rk" for c in COIN_B]].to_numpy(float))
    if model == "C":
        smu = d.loc[tr_mask, ST].mean(); ssd = d.loc[tr_mask, ST].std().replace(0, 1)
        Zs = ((d[ST] - smu) / ssd).fillna(0).to_numpy(float)
        for s in range(1, 6):
            X.append(Zs * (d.station.to_numpy() == s)[:, None])
    return np.hstack(X)
pred = {m: np.full(len(d), np.nan) for m in "ABC"}
exitday = d.date + pd.Timedelta(days=5)
for Y in range(2021, 2027):
    start = pd.Timestamp(f"{Y}-01-01"); tr = (exitday < start).to_numpy(); te = (d.date.dt.year == Y).to_numpy()
    for m in "ABC":
        X = design(m, tr); Xt = np.c_[np.ones(tr.sum()), X[tr]]
        lam = 10 * np.eye(Xt.shape[1]); lam[0, 0] = 0
        beta = np.linalg.solve(Xt.T @ Xt + lam, Xt.T @ d.y.to_numpy()[tr])
        pred[m][te] = np.c_[np.ones(te.sum()), X[te]] @ beta
for m in "ABC": d["p" + m] = pred[m]
T = d[d.date.dt.year >= 2021].copy()
def daily_ic(col, target):
    return T.groupby("date").apply(lambda x: x[col].rank().corr(x[target].rank()), include_groups=False)
res = {"rows_test": len(T), "days_test": int(T.date.nunique()), "ic": {}, "ic_diff": {}, "decisions": {}}
rng = np.random.default_rng(20261103)
def block_boot(s, b=20, n=5000):
    v = s.dropna().to_numpy(); k = int(np.ceil(len(v) / b)); means = []
    for _ in range(n):
        idx = np.concatenate([np.arange(i, min(i + b, len(v))) for i in rng.integers(0, len(v) - b, k)])[:len(v)]
        means.append(v[idx].mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
for h in ("fwd3", "fwd1", "fwd5"):
    ics = {m: daily_ic("p" + m, h) for m in "ABC"}
    res["ic"][h] = {m: {"mean": float(ics[m].mean()), "by_year": {int(y): float(v.mean()) for y, v in ics[m].groupby(ics[m].index.year)}} for m in "ABC"}
    for a, b in (("B", "A"), ("C", "B")):
        diff = ics[a] - ics[b]; lo_, hi_ = block_boot(diff)
        res["ic_diff"][f"{h}_{a}-{b}"] = {"mean": float(diff.mean()), "lo95": lo_, "hi95": hi_, "by_year": {int(y): float(v.mean()) for y, v in diff.groupby(diff.index.year)}}
days = sorted(T.date.unique())[::3]
picks = {k: [] for k in ("A", "B", "C", "random5", "all", "strong_group")}
for dt in days:
    x = T[T.date == dt]
    if len(x) < 10: continue
    for m in "ABC": picks[m].append((dt, x.nlargest(5, "p" + m).fwd3.mean()))
    picks["random5"].append((dt, x.sample(5, random_state=int(rng.integers(1e9))).fwd3.mean()))
    picks["all"].append((dt, x.fwd3.mean()))
    sm = x.groupby("station").ret7.median().idxmax()
    picks["strong_group"].append((dt, x[x.station == sm].nlargest(5, "ret7").fwd3.mean()))
for k, v in picks.items():
    s = pd.Series(dict(v)); s.index = pd.to_datetime(s.index)
    byy = s.groupby(s.index.year).mean()
    mon = s.groupby(s.index.to_period("M")).sum().sort_values(ascending=False)
    res["decisions"][k] = {"n_rebalances": len(s), "gross_mean": float(s.mean()), "net_0.4pct": float(s.mean() - 0.004), "net_2pct_etoro": float(s.mean() - 0.02),
                           "by_year_gross": {int(y): float(v) for y, v in byy.items()},
                           "gross_mean_without_best_month": float(s[s.index.to_period("M") != mon.index[0]].mean())}
yrs = range(2021, 2027)
def beats(a, b): return sum(res["decisions"][a]["by_year_gross"].get(y, -9) > res["decisions"][b]["by_year_gross"].get(y, 9) for y in yrs)
r = res["ic_diff"]
res["reading"] = {"neighbours_add_information": bool(r["fwd3_B-A"]["lo95"] > 0 and r["fwd3_B-A"]["mean"] > 0 and beats("B", "A") >= 4),
                  "next_stop_adds_information": bool(r["fwd3_C-B"]["lo95"] > 0 and r["fwd3_C-B"]["mean"] > 0 and beats("C", "B") >= 4),
                  "years_B_beats_A": beats("B", "A"), "years_C_beats_B": beats("C", "B")}
(HERE / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))

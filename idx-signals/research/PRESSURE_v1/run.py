"""PRESSURE_v1 single run (PROTOCOL.md). Usage: python3 run.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; NB = HERE.parent / "NEIGHBOURS_v1"
if (HERE / "RESULT.json").exists(): sys.exit("RESULT.json exists; runs once")
d = pd.read_csv(NB / "rows.csv.gz", parse_dates=["date"])
d = d[d.peers_ok & d.fwd5.notna() & d.fwd3.notna() & d.fwd1.notna()].reset_index(drop=True)
tk = pd.read_csv(HERE / "taker.csv.gz", parse_dates=["date"]).sort_values(["ticker", "date"])
tk["sell"] = tk.quote_vol - tk.taker_buy_quote
g = tk.groupby("ticker")
tk["tb1"] = tk.taker_buy_quote / tk.quote_vol - 0.5
tk["tb5"] = g.taker_buy_quote.transform(lambda s: s.rolling(5, min_periods=4).sum()) / g.quote_vol.transform(lambda s: s.rolling(5, min_periods=4).sum())
imb3 = (tk.taker_buy_quote - tk.sell).groupby(tk.ticker).transform(lambda s: s.rolling(3, min_periods=3).sum())
tk["tbz"] = imb3 / g.quote_vol.transform(lambda s: s.rolling(20, min_periods=15).median())
d = d.merge(tk[["ticker", "date", "tb1", "tb5", "tbz"]], on=["ticker", "date"], how="left")
cov = float(d.tb1.notna().mean())
COIN_A = ["ret1", "ret3", "ret7", "ret20", "volr", "hi60", "vol20"]; DAY_A = ["btc7", "breadth"]; PR = ["tb1", "tb5", "tbz"]
gd = d.groupby("date")
for c in COIN_A + PR:
    d[c + "_rk"] = (gd[c].rank(pct=True) - 0.5).fillna(0.0)
y = d.fwd3 - gd.fwd3.transform("mean")
lo = gd.fwd3.transform(lambda s: s.quantile(.01)) - gd.fwd3.transform("mean"); hi = gd.fwd3.transform(lambda s: s.quantile(.99)) - gd.fwd3.transform("mean")
d["y"] = y.clip(lo, hi)
def design(model, tr):
    X = [d[[c + "_rk" for c in COIN_A]].to_numpy(float)]
    mu = d.loc[tr, DAY_A].mean(); sd = d.loc[tr, DAY_A].std().replace(0, 1)
    X.append(((d[DAY_A] - mu) / sd).fillna(0).to_numpy(float))
    if model == "P": X.append(d[[c + "_rk" for c in PR]].to_numpy(float))
    return np.hstack(X)
pred = {m: np.full(len(d), np.nan) for m in "AP"}
exitday = d.date + pd.Timedelta(days=5)
for Y in range(2021, 2027):
    tr = (exitday < pd.Timestamp(f"{Y}-01-01")).to_numpy(); te = (d.date.dt.year == Y).to_numpy()
    for m in "AP":
        X = design(m, tr); Xt = np.c_[np.ones(tr.sum()), X[tr]]; lam = 10 * np.eye(Xt.shape[1]); lam[0, 0] = 0
        beta = np.linalg.solve(Xt.T @ Xt + lam, Xt.T @ d.y.to_numpy()[tr]); pred[m][te] = np.c_[np.ones(te.sum()), X[te]] @ beta
for m in "AP": d["p" + m] = pred[m]
T = d[d.date.dt.year >= 2021].copy()
rng = np.random.default_rng(20261103)
def block_boot(s, b=20, n=5000):
    v = s.dropna().to_numpy(); k = int(np.ceil(len(v) / b)); means = []
    for _ in range(n):
        idx = np.concatenate([np.arange(i, min(i + b, len(v))) for i in rng.integers(0, len(v) - b, k)])[:len(v)]; means.append(v[idx].mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
res = {"taker_coverage_of_rows": cov, "fetch_failures": json.load(open(HERE / "fetch_manifest.json"))["status"], "ic": {}, "ic_diff": {}, "decisions": {}, "single_feature_ic": {}}
for h in ("fwd3", "fwd1", "fwd5"):
    ics = {m: T.groupby("date").apply(lambda x: x["p" + m].rank().corr(x[h].rank()), include_groups=False) for m in "AP"}
    res["ic"][h] = {m: float(ics[m].mean()) for m in "AP"}
    diff = ics["P"] - ics["A"]; l, u = block_boot(diff)
    res["ic_diff"][h] = {"mean": float(diff.mean()), "lo95": l, "hi95": u, "by_year": {int(yy): float(v.mean()) for yy, v in diff.groupby(diff.index.year)}}
for c in PR:
    ic = T.groupby("date").apply(lambda x: x[c].rank().corr(x.fwd3.rank()), include_groups=False)
    res["single_feature_ic"][c] = {"mean": float(ic.mean()), "by_year": {int(yy): float(v.mean()) for yy, v in ic.groupby(ic.index.year)}}
days = sorted(T.date.unique())[::3]; picks = {"A": [], "P": []}
for dt in days:
    x = T[T.date == dt]
    if len(x) < 10: continue
    for m in "AP": picks[m].append((dt, x.nlargest(5, "p" + m).fwd3.mean()))
for k, v in picks.items():
    s = pd.Series(dict(v)); s.index = pd.to_datetime(s.index)
    res["decisions"][k] = {"gross_mean": float(s.mean()), "net_0.4pct": float(s.mean() - 0.004), "net_2pct_etoro": float(s.mean() - 0.02),
                           "by_year_gross": {int(yy): float(v) for yy, v in s.groupby(s.index.year).mean().items()}}
beats = sum(res["decisions"]["P"]["by_year_gross"][yy] > res["decisions"]["A"]["by_year_gross"][yy] for yy in range(2021, 2027))
r = res["ic_diff"]["fwd3"]
res["years_P_beats_A"] = beats
res["reading"] = "PRESSURE ADDS INFORMATION" if (r["mean"] > 0 and r["lo95"] > 0 and beats >= 4) else "NO INCREMENTAL VALUE"
(HERE / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))

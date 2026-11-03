"""GROUP_FLOW_v1 single run (PROTOCOL.md). Usage: python3 run.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
if (HERE / "RESULT.json").exists(): sys.exit("RESULT.json exists; runs once")
sys.path.insert(0, str(HERE.parent / "US_INSIDER_BUY")); import ib_stats as st
df = pd.read_csv(ROOT / "data/panel/panel_us_repair-20261008T114805Z.csv.gz", usecols=["date", "ticker", "close", "volume"], parse_dates=["date"])
df = df[df.date <= "2023-12-29"]
C = df.pivot(index="date", columns="ticker", values="close").sort_index()
Vd = (df.assign(v=df.close * df.volume).pivot(index="date", columns="ticker", values="v")).reindex_like(C)
R = (C / C.shift(1) - 1).to_numpy(float)
Cv = C.to_numpy(float)
liq = Vd.rolling(20, min_periods=15).median().shift(1).to_numpy(float)
dates = C.index; tick = np.array(C.columns)
s0 = int(np.searchsorted(dates.values, np.datetime64("2020-07-01"))); s1 = int(np.searchsorted(dates.values, np.datetime64("2023-11-29"), side="right"))
rows, last = [], {}
for s in range(max(s0, 121), s1):
    if s + 20 >= len(dates): break
    liquid = (liq[s] >= 1e6) & (Cv[s - 1] >= 1.0)
    jumps = np.flatnonzero(liquid & (R[s] >= 0.30) & np.isfinite(R[s]))
    if not len(jumps): continue
    W = R[s - 120:s]                       # sessions s-120 .. s-1
    okcols = liquid & (np.isfinite(W).sum(0) >= 100)
    Wc = np.where(np.isfinite(W), W, np.nan)
    mu = np.nanmean(Wc, 0); sd = np.nanstd(Wc, 0)
    Z = np.where(np.isfinite(Wc), (Wc - mu) / np.where(sd > 0, sd, np.nan), 0.0)
    cnt = np.isfinite(Wc).astype(float)
    for j in jumps:
        if j in last and s - last[j] < 20: continue
        if not okcols[j]: continue
        n_shared = cnt[:, [j]].T @ cnt          # shared sessions with every other name
        corr = (Z[:, j] @ Z) / np.maximum(n_shared[0], 1)
        cand = okcols.copy(); cand[j] = False; cand &= n_shared[0] >= 100
        idx = np.flatnonzero(cand)
        if len(idx) < 20: continue
        peers = idx[np.argsort(-corr[idx])[:20]]
        g = float(np.nanmedian(R[s, peers]))
        e = Cv[s, j]; fut = Cv[s + 1:s + 21, j]
        if not np.isfinite(e) or np.isnan(fut).any(): continue
        last[j] = s
        rows.append({"date": dates[s].date().isoformat(), "ticker": tick[j], "jump": R[s, j], "group_move": g,
                     "peer_corr_median": float(np.median(corr[peers])), "fwd5": fut[4] / e - 1, "fwd20": fut[19] / e - 1,
                     "falls": bool((fut <= e / 1.30).any())})
ev = pd.DataFrame(rows)
ev["cls"] = np.where(ev.group_move >= 0.03, "WITH_GROUP", np.where(ev.group_move.abs() <= 0.01, "ALONE", "BETWEEN"))
ev["keeps"] = ev.fwd20 > 0
ev["period"] = np.where(ev.date < "2022-01-01", "2020_21", "2022_23")
ev.to_csv(HERE / "events.csv", index=False)
def summ(g): return {"n": int(len(g)), "fwd5_mean": float(g.fwd5.mean()), "fwd20_mean": float(g.fwd20.mean()), "fwd20_median": float(g.fwd20.median()),
                     "keeps": float(g.keeps.mean()), "falls": float(g.falls.mean())}
res = {"events": len(ev), "by": {}}
ok_all = True
for p, gp in ev.groupby("period"):
    res["by"][p] = {c: summ(g) for c, g in gp.groupby("cls")}
    w, a = gp[gp.cls == "WITH_GROUP"], gp[gp.cls == "ALONE"]
    both = pd.concat([w.assign(x=w.fwd20 - a.fwd20.mean()), ])
    # bootstrap of the difference in means: resample weeks within each class
    rng = np.random.default_rng(20261103); diffs = []
    wk_w = st.week_id(w.date); wk_a = st.week_id(a.date)
    gw = {k: v.fwd20.to_numpy() for k, v in w.assign(k=wk_w).groupby("k")}; ga = {k: v.fwd20.to_numpy() for k, v in a.assign(k=wk_a).groupby("k")}
    kw, ka = list(gw), list(ga)
    for _ in range(5000):
        sw = np.concatenate([gw[k] for k in rng.choice(kw, len(kw))]); sa = np.concatenate([ga[k] for k in rng.choice(ka, len(ka))])
        diffs.append(sw.mean() - sa.mean())
    diffs = np.array(diffs)
    res["by"][p]["with_minus_alone_fwd20"] = {"mean": float(w.fwd20.mean() - a.fwd20.mean()), "lo95": float(np.percentile(diffs, 2.5)), "hi95": float(np.percentile(diffs, 97.5))}
    ok_all &= (w.fwd20.median() > a.fwd20.median()) and (w.keeps.mean() > a.keeps.mean())
res["reading"] = "FLOW-BACKED JUMPS LAST" if ok_all else "NO DIFFERENCE"
(HERE / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))

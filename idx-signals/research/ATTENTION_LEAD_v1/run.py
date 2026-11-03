"""ATTENTION_LEAD_v1 single run (PROTOCOL.md). Usage (from this folder): python3 run.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "US_INSIDER_BUY"))
import ib_stats as st

if (HERE / "RESULT.json").exists(): sys.exit("RESULT.json exists; runs once")
px = pd.read_csv(ROOT / "data/panel/panel_us_repair-20261008T114805Z.csv.gz", usecols=["date", "ticker", "close"], parse_dates=["date"])
px = px[(px.date >= "2020-06-01") & (px.date <= "2023-12-29")]
C = px.pivot(index="date", columns="ticker", values="close").sort_index()
pv = pd.read_csv(HERE / "pageviews.csv.gz", parse_dates=["date"], dtype={"ticker": str})
V = pv.pivot(index="date", columns="ticker", values="views").sort_index()
V = V.reindex(pd.date_range(V.index.min(), V.index.max(), freq="D"))
names = [t for t in V.columns if t in C.columns]
V, C = V[names], C[names]
med = V.shift(1).rolling(30, min_periods=25).median()
ratio = V / med
sessions = C.index
# map each calendar day D to: last session <= D (filters) and first session > D (entry)
last_idx = np.searchsorted(sessions.values, V.index.values, side="right") - 1
entry_idx = np.searchsorted(sessions.values, V.index.values, side="right")
Cv = C.to_numpy(float)
r1 = Cv / np.vstack([np.full((1, Cv.shape[1]), np.nan), Cv[:-1]]) - 1
r5 = Cv / np.vstack([np.full((5, Cv.shape[1]), np.nan), Cv[:-5]]) - 1
H = 20
fmax = np.full_like(Cv, np.nan); fmin = np.full_like(Cv, np.nan); f20 = np.full_like(Cv, np.nan)
for i in range(len(sessions) - H):
    w = Cv[i + 1:i + H + 1]
    ok = ~np.isnan(w).any(0)
    fmax[i] = np.where(ok, np.nanmax(w, 0), np.nan); fmin[i] = np.where(ok, np.nanmin(w, 0), np.nan); f20[i] = Cv[i + H]
rows = []
first_day = pd.Timestamp("2020-07-01")
for k, D in enumerate(V.index):
    if D < first_day: continue
    li, ei = last_idx[k], entry_idx[k]
    if li < 5 or ei >= len(sessions) - H: continue
    rv, mv, vv = ratio.iloc[k].to_numpy(float), med.iloc[k].to_numpy(float), V.iloc[k].to_numpy(float)
    flat = (np.abs(r5[li]) < 0.10) & (np.abs(r1[li]) < 0.05)
    e = Cv[ei]
    valid = flat & (mv >= 50) & np.isfinite(e) & np.isfinite(f20[ei])
    ev = valid & (rv >= 3) & (vv >= 500)
    ct = valid & (rv < 1.5)
    if not ev.any() or ct.sum() < 5: continue
    up = fmax[ei] / e >= 1.30; dn = fmin[ei] / e <= 1 / 1.30; fr = f20[ei] / e - 1
    cmean = np.nanmean(fr[ct]); cup = up[ct].mean(); cdn = dn[ct].mean()
    for j in np.flatnonzero(ev):
        rows.append({"day": D.date().isoformat(), "entry": sessions[ei].date().isoformat(), "ticker": names[j], "ratio": rv[j], "views": vv[j],
                     "up30": bool(up[j]), "dn23": bool(dn[j]), "fwd20": fr[j], "ctrl_fwd20": cmean, "ctrl_up30": cup, "ctrl_dn23": cdn, "n_ctrl": int(ct.sum())})
ev = pd.DataFrame(rows).sort_values(["ticker", "entry"])
keep, last = [], {}
spos = {d.date().isoformat(): i for i, d in enumerate(sessions)}
for t, d in zip(ev.ticker, ev.entry):
    i = spos[d]; ok = t not in last or i - last[t] >= 20
    keep.append(ok)
    if ok: last[t] = i
ev = ev[keep].reset_index(drop=True)
ev["excess"] = ev.fwd20 - ev.ctrl_fwd20
ev.to_csv(HERE / "events.csv", index=False)
w = st.week_id(ev.entry)
b = st.Boot(w, 10_000, 20261103).mean(ev.excess, w)
res = {"events": len(ev), "tickers": int(ev.ticker.nunique()), "universe_names": len(names),
       "up30": float(ev.up30.mean()), "dn23": float(ev.dn23.mean()), "ctrl_up30": float(ev.ctrl_up30.mean()), "ctrl_dn23": float(ev.ctrl_dn23.mean()),
       "fwd20_mean": float(ev.fwd20.mean()), "fwd20_median": float(ev.fwd20.median()), "ctrl_fwd20_mean": float(ev.ctrl_fwd20.mean()),
       "excess": b, "excess_median": float(ev.excess.median()), "winsorised_excess": st.winsor_mean(ev.excess),
       "by_year": {y: {"n": int(len(g)), "up30": float(g.up30.mean()), "dn23": float(g.dn23.mean()), "excess": float(g.excess.mean())} for y, g in ev.groupby(ev.entry.str[:4])}}
up_lift = res["up30"] / res["ctrl_up30"] if res["ctrl_up30"] > 0 else float("nan")
res["up_lift"] = up_lift
c1 = up_lift >= 1.5; c2 = (res["up30"] - res["dn23"]) > (res["ctrl_up30"] - res["ctrl_dn23"]); c3 = b["mean"] > 0 and b["t"] >= 2.0
res["criteria"] = {"up30_ge_1.5x_controls": bool(c1), "up_minus_down_above_controls": bool(c2), "excess_t_ge_2": bool(c3)}
res["reading"] = ("ATTENTION LEADS, UPWARD" if (c1 and c2 and c3) else
                  "ATTENTION LEADS, BOTH WAYS" if (c1 and res["dn23"] >= 1.5 * res["ctrl_dn23"]) else "NO USABLE LEAD")
# descriptive: abnormal views around one-day +30% jumps
ab = V / V.shift(11).rolling(20, min_periods=15).median()   # median of D-30..D-11
day_pos = {d: i for i, d in enumerate(V.index)}
prof = {k: [] for k in range(-10, 6)}
for i in range(1, len(sessions)):
    for j in np.flatnonzero(r1[i] >= 0.30):
        D = sessions[i]
        if D < first_day or D not in day_pos: continue
        p = day_pos[D]
        if p - 10 < 0 or p + 5 >= len(V.index): continue
        for k in prof:
            x = ab.iat[p + k, j]
            if np.isfinite(x): prof[k].append(x)
res["jump_profile_median_abnormal_views"] = {str(k): (float(np.median(v)) if v else None) for k, v in prof.items()}
res["jump_profile_n"] = len(prof[0])
(HERE / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
print(json.dumps(res, indent=1, default=float))

"""PATHS_v0 (exploratory): no stop loss, no take profit. For each v0 ignition and its controls, follow the price
for 30 days after entry: returns at fixed checkpoints, peak gain, when the peak came, how far it fell before the
peak, and how much of the peak was given back by day 30. Discovery data 2020-2022 only."""
import json, os
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out")
COST = 0.003; HMAX = 720  # 30 days
# Safe: panel_1h.pkl is produced locally by build_panel.py from hash-logged Binance zips, never external.
p = pd.read_pickle(os.path.join(OUT, "panel_1h.pkl"))
grid = pd.date_range("2020-01-01", "2022-12-31 23:00", freq="h", tz="UTC")
syms = sorted(p["sym"].unique()); idx = {s: i for i, s in enumerate(syms)}; T = len(grid)
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"):
        m[idx[s], grid.get_indexer(g["ts"])] = g[col].values
    return m
O, H, L, C = (mat(c) for c in ["open", "high", "low", "close"]); del p
CK = {"1d": 24, "3d": 72, "7d": 168, "14d": 336, "30d": 720}
def path(sym, trig_hour):
    i = idx[sym]; e = grid.get_loc(pd.Timestamp(trig_hour)) + 1
    if e + HMAX > T: return None
    ent = O[i, e]
    if not np.isfinite(ent) or ent <= 0: return None
    hh, ll, cl = H[i, e:e + HMAX], L[i, e:e + HMAX], C[i, e:e + HMAX]
    if np.isfinite(cl).sum() < 0.9 * HMAX: return dict(status="GAPPY_OR_DELISTED", final_obs=int(np.isfinite(cl).sum()))
    entc = ent * (1 + COST)
    r = {f"net_{k}": (cl[h - 1] * (1 - COST) / entc - 1) if np.isfinite(cl[h - 1]) else np.nan for k, h in CK.items()}
    pk = int(np.nanargmax(hh)); peak = hh[pk] / entc - 1
    dd_before = np.nanmin(ll[:pk + 1]) / entc - 1
    after = cl[pk:]; end = after[np.isfinite(after)][-1]
    return dict(status="OK", **r, peak_gain=peak, peak_hour=pk, low_before_peak=dd_before,
                low_30d=np.nanmin(ll) / entc - 1, giveback_to_30d=end / hh[pk] - 1)
ev = pd.read_csv(os.path.join(OUT, "events_v0.csv")); ev = ev[ev.status == "OK"]
ct = pd.read_csv(os.path.join(OUT, "controls_v0.csv"))
E = [dict(sym=r.sym, trigger_hour=r.trigger_hour, **(path(r.sym, r.trigger_hour) or {"status": "NO_30D_WINDOW"})) for r in ev.itertuples()]
K = [dict(sym=r.sym, trigger_hour=r.trigger_hour, **(path(r.sym, r.trigger_hour) or {"status": "NO_30D_WINDOW"})) for r in ct.itertuples()]
E, K = pd.DataFrame(E), pd.DataFrame(K)
E.to_csv(os.path.join(OUT, "paths_events_v0.csv"), index=False); K.to_csv(os.path.join(OUT, "paths_controls_v0.csv"), index=False)
def summ(d):
    d = d[d.status == "OK"]; o = {"n": len(d)}
    for k in CK:
        x = d[f"net_{k}"]; o[k] = dict(mean=round(x.mean(), 4), median=round(x.median(), 4), pct_profit=round((x > 0).mean(), 3))
    o["peak_gain_median"] = round(d.peak_gain.median(), 4)
    o["peak_ge_30pct"] = round((d.peak_gain >= .3).mean(), 3); o["peak_ge_100pct"] = round((d.peak_gain >= 1).mean(), 3)
    o["peak_in_first_24h"] = round((d.peak_hour < 24).mean(), 3)
    o["peak_hour_median"] = int(d.peak_hour.median())
    big = d[d.peak_gain >= .3]
    o["among_peak_ge_30"] = dict(n=len(big), peak_hour_median=int(big.peak_hour.median()) if len(big) else None,
                                 low_before_peak_median=round(big.low_before_peak.median(), 4) if len(big) else None,
                                 giveback_to_30d_median=round(big.giveback_to_30d.median(), 4) if len(big) else None,
                                 net_30d_median=round(big.net_30d.median(), 4) if len(big) else None)
    o["low_30d_median"] = round(d.low_30d.median(), 4)
    return o
res = {"events": summ(E), "controls": summ(K),
       "status_counts": {"events": E.status.value_counts().to_dict(), "controls": K.status.value_counts().to_dict()}}
json.dump(res, open(os.path.join(OUT, "summary_paths_v0.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))

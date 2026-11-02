"""FILTERS_EXITS_v0 (exploratory). Written before looking at any filter result.
Question: among v0 ignitions, do chart features known AT the trigger hour separate the runners from the faders,
and do any rule-based exits (decided in advance) turn them profitable vs the same exits on random coins?

Luck controls (fixed now):
  - Explore on 2020-2021 events only. Check the best cells on 2022 (untouched by selection). 2023+ not on disk.
  - Count every cell tested. Null distribution of the best cell: shuffle feature values across explore events
    200 times, re-run the whole search, record the best cell's mean each time. A real cell must beat the 95th pct.
  - Same exits on controls (random coins, same hour) to separate filter skill from exit mechanics.
Execution: entry next-hour open, 0.3%/side cost. Exits checked on hourly closes and filled at next hour's open,
except take-profit, filled at the TP price when the hour's high reaches it. Max hold 30 days.
"""
import json, os, hashlib
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out")
COST = 0.003; HMAX = 720
# Safe: panel_1h.pkl is produced locally by build_panel.py from hash-logged Binance zips, never external.
p = pd.read_pickle(os.path.join(OUT, "panel_1h.pkl"))
grid = pd.date_range("2020-01-01", "2022-12-31 23:00", freq="h", tz="UTC")
syms = sorted(p["sym"].unique()); idx = {s: i for i, s in enumerate(syms)}; T = len(grid)
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"):
        m[idx[s], grid.get_indexer(g["ts"])] = g[col].values
    return m
O, H, L, C, Q = (mat(c) for c in ["open", "high", "low", "close", "quote_vol"]); del p
first_obs = np.array([np.argmax(np.isfinite(C[i])) for i in range(len(syms))])
BTC = C[idx["BTCUSDT"]]

def rsi(cl, n=14):
    d = np.diff(cl); d = d[np.isfinite(d)]
    if len(d) < n * 3: return np.nan
    g = np.where(d > 0, d, 0); l = np.where(d < 0, -d, 0)
    ag, al = g[:n].mean(), l[:n].mean()
    for k in range(n, len(d)):
        ag = (ag * (n - 1) + g[k]) / n; al = (al * (n - 1) + l[k]) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)

ev = pd.read_csv(os.path.join(OUT, "events_v0.csv")); ev = ev[ev.status == "OK"].reset_index(drop=True)
ev_t = grid.get_indexer(pd.to_datetime(ev.trigger_hour))
trig_count = pd.Series(ev_t).value_counts()
feats = []
for k, r in ev.iterrows():
    i, t = idx[r.sym], ev_t[k]
    lo30 = max(0, t - 720)
    hi_prior = np.nanmax(H[i, lo30:t - 3]) if t - 3 > lo30 else np.nan  # resistance: 30d high before the move began
    lo_prior = np.nanmin(L[i, lo30:t - 3]) if t - 3 > lo30 else np.nan
    base = r.avg_hourly_quote
    pre24 = np.nanmean(Q[i, t - 27:t - 3]) / base if base > 0 else np.nan
    rng_h = H[i, t] - L[i, t]
    breadth = sum(trig_count.get(tt, 0) for tt in range(t - 3, t + 4)) - 1
    feats.append(dict(
        rsi14=rsi(C[i, max(0, t - 200):t + 1]),
        above_30d_high=float(C[i, t] > hi_prior) if np.isfinite(hi_prior) else np.nan,
        dist_30d_high=C[i, t] / hi_prior - 1 if np.isfinite(hi_prior) else np.nan,
        up_from_30d_low=C[i, t] / lo_prior - 1 if np.isfinite(lo_prior) else np.nan,
        vol_mult=r.vol_mult, r3=r.r3, prior7d=r.prior7d, prebuild_vol24=pre24,
        btc_24h=BTC[t] / BTC[t - 24] - 1, btc_7d=BTC[t] / BTC[t - 168] - 1,
        coin_age_days=(t - first_obs[i]) / 24, log_liquidity=np.log10(base),
        upper_wick=(H[i, t] - C[i, t]) / rng_h if rng_h > 0 else np.nan,
        breadth_pm3h=breadth, hour_utc=t % 24))
F = pd.DataFrame(feats)

def exits(i, e):
    """Return dict of net returns under each pre-set exit; None if no data."""
    if e + HMAX > T: return None
    ent = O[i, e]
    if not np.isfinite(ent) or ent <= 0: return None
    hh, ll, cl, op = H[i, e:e + HMAX], L[i, e:e + HMAX], C[i, e:e + HMAX], O[i, e:e + HMAX + 1] if e + HMAX < T else O[i, e:e + HMAX]
    if np.isfinite(cl).sum() < 0.9 * HMAX: return None
    entc = ent * (1 + COST)
    cl_f = pd.Series(cl).ffill().values
    def nxt_open(k):  # fill at next hour's open (fallback: that close)
        v = O[i, e + k + 1] if e + k + 1 < T else np.nan
        return v if np.isfinite(v) else cl_f[k]
    def out(px): return px * (1 - COST) / entc - 1
    res = {"X1_hold3d": out(cl_f[71])}
    def trail(pct, maxh=HMAX):
        peak = ent
        for k in range(maxh):
            if np.isfinite(hh[k]): peak = max(peak, hh[k])
            if cl_f[k] <= peak * (1 - pct): return out(nxt_open(k))
        return out(cl_f[maxh - 1])
    def tp_sl(tp, sl, maxh):
        for k in range(maxh):
            if sl is not None and cl_f[k] <= ent * (1 + sl): return out(nxt_open(k))
            if np.isfinite(hh[k]) and hh[k] >= ent * (1 + tp): return out(ent * (1 + tp))
        return out(cl_f[maxh - 1])
    res["X2_trail20"] = trail(0.20); res["X3_tp30_sl15_7d"] = tp_sl(0.30, -0.15, 168)
    res["X4_tp50_14d"] = tp_sl(0.50, None, 336); res["X5_trail30"] = trail(0.30)
    res["runner"] = float(tp_sl(0.30, -0.15, 168) > 0.25)  # hit +30% before -15% within 7d
    return res
EX = [exits(idx[r.sym], ev_t[k] + 1) for k, r in ev.iterrows()]
keep = [x is not None for x in EX]
D = pd.concat([ev[["sym", "trigger_hour"]], F], axis=1)[keep].reset_index(drop=True)
D = pd.concat([D, pd.DataFrame([x for x in EX if x is not None])], axis=1)
D["year"] = D.trigger_hour.str[:4]
ct = pd.read_csv(os.path.join(OUT, "controls_v0.csv"))
ct_t = grid.get_indexer(pd.to_datetime(ct.trigger_hour))
CX = [exits(idx[r.sym], ct_t[k] + 1) for k, r in enumerate(ct.itertuples())]
CD = pd.DataFrame([dict(year=ct.trigger_hour.iloc[k][:4], **x) for k, x in enumerate(CX) if x is not None])
D.to_csv(os.path.join(OUT, "filters_events_v0.csv"), index=False); CD.to_csv(os.path.join(OUT, "filters_controls_v0.csv"), index=False)

EXITS = ["X1_hold3d", "X2_trail20", "X3_tp30_sl15_7d", "X4_tp50_14d", "X5_trail30"]
FEATS = list(F.columns)
exp = D[D.year.isin(["2020", "2021"])].reset_index(drop=True); chk = D[D.year == "2022"].reset_index(drop=True)
def search(Fexp, Y):
    """Every feature x quintile x exit cell; returns list of (feat, q, lo, hi, exit, n, mean)."""
    cells = []
    for f in FEATS:
        x = Fexp[f].values
        ok = np.isfinite(x)
        if ok.sum() < 100: continue
        uniq = np.unique(x[ok])
        if len(uniq) <= 5: edges = [(u, u) for u in uniq]
        else:
            q = np.nanpercentile(x, [0, 20, 40, 60, 80, 100]); edges = list(zip(q[:-1], q[1:]))
        for b, (lo, hi) in enumerate(edges):
            m = ok & (x >= lo) & (x <= hi)
            if m.sum() < 50: continue
            for xn in EXITS:
                cells.append((f, b, float(lo), float(hi), xn, int(m.sum()), float(np.nanmean(Y[xn].values[m]))))
    return cells
cells = search(exp[FEATS], exp)
cells_df = pd.DataFrame(cells, columns=["feature", "bin", "lo", "hi", "exit", "n", "mean_net"]).sort_values("mean_net", ascending=False)
cells_df.to_csv(os.path.join(OUT, "filters_cells_explore_v0.csv"), index=False)
rng = np.random.default_rng(99); null_max = []
for _ in range(200):
    perm = exp[FEATS].sample(frac=1, random_state=int(rng.integers(1e9))).reset_index(drop=True)
    null_max.append(max(c[6] for c in search(perm, exp)))
bar = float(np.percentile(null_max, 95))
def cell_mask(df, f, lo, hi): x = df[f].values; return np.isfinite(x) & (x >= lo) & (x <= hi)
top = []
for _, c in cells_df.head(15).iterrows():
    m = cell_mask(chk, c.feature, c.lo, c.hi)
    top.append(dict(feature=c.feature, bin=int(c.bin), range=[round(c.lo, 4), round(c.hi, 4)], exit=c.exit,
                    explore_n=int(c.n), explore_mean=round(c.mean_net, 4), beats_luck_bar=bool(c.mean_net > bar),
                    check2022_n=int(m.sum()), check2022_mean=round(float(np.nanmean(chk[c.exit].values[m])), 4) if m.sum() else None,
                    check2022_all_events_same_exit=round(float(chk[c.exit].mean()), 4),
                    check2022_controls_same_exit=round(float(CD[CD.year == "2022"][c.exit].mean()), 4)))
base = {xn: dict(events_explore=round(float(exp[xn].mean()), 4), controls_explore=round(float(CD[CD.year.isin(["2020", "2021"])][xn].mean()), 4),
                 events_2022=round(float(chk[xn].mean()), 4), controls_2022=round(float(CD[CD.year == "2022"][xn].mean()), 4)) for xn in EXITS}
runner_by_feat = {}
for f in FEATS:
    x = exp[f]; 
    try: qb = pd.qcut(x, 5, duplicates="drop")
    except Exception: continue
    runner_by_feat[f] = {str(k): round(float(v), 3) for k, v in exp.groupby(qb, observed=True).runner.mean().items()}
res = dict(n_events=len(D), n_explore=len(exp), n_check2022=len(chk), n_controls=len(CD),
           cells_tested=len(cells), luck_bar_95pct_of_best_shuffled_cell=round(bar, 4),
           null_best_cell_median=round(float(np.median(null_max)), 4),
           exits_baseline=base, top15_explore_cells=top,
           runner_rate_explore_overall=round(float(exp.runner.mean()), 3), runner_rate_by_feature_quintile=runner_by_feat,
           script_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest())
json.dump(res, open(os.path.join(OUT, "summary_filters_v0.json"), "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in res.items() if k != "runner_rate_by_feature_quintile"}, indent=1, default=float))

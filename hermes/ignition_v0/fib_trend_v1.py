"""FIB_TREND_v1 (exploratory, UPSIDE only). Written before looking at results.
Part A — Fibonacci: does where the price sits on the Fibonacci grid of the recent swing (50-day, 200-day, 500-hour)
  raise upside odds for crypto ignitions? Features: position in the swing range, Fibonacci zone
  (0/.236/.382/.5/.618/.786/1/1.272/1.618), swing direction (low-then-high = pullback in uptrend), distance to the nearest
  Fibonacci level, and whether the 3-hour move crossed the .618 or 1.0 level. Same luck controls as before
  (explore 2020-21, check 2022, 200 shuffles, every cell counted).
Part B — like-for-like (fixed now, before results): TREND = above at least 5 of the 6 daily SMAs (11/21/50/100/200/500,
  with SMA200 available) AND price within 15% of the 200-day high. Compare ignitions in TREND vs random coins in TREND
  at the same hour, on upside and exits, 2020-21 and 2022 separately. Also per single trend feature (top fifth by
  ignition cut-offs). If random coins in TREND do as well, the ignition adds nothing beyond plain momentum.
No look-ahead: daily features use days closed before the trigger day; hourly use closes up to the trigger hour.
"""
import glob, io, json, os, zipfile, hashlib
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out"); RAW = os.path.join(ROOT, "raw")
COST = 0.003; HMAX = 720; NS = [11, 21, 50, 100, 200, 500]
LEVELS = np.array([0, .236, .382, .5, .618, .786, 1.0, 1.272, 1.618])

rows = []
for fp in glob.glob(os.path.join(RAW, "k1d", "*.zip")):
    sym = os.path.basename(fp).split("-1d-")[0]
    with zipfile.ZipFile(fp) as z:
        df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
    df = df.iloc[:, [0, 2, 3, 4]].astype(float); df.columns = ["t", "high", "low", "close"]; df["sym"] = sym; rows.append(df)
Dd = pd.concat(rows); Dd["date"] = pd.to_datetime(Dd.t.astype("int64"), unit="ms", utc=True).dt.normalize()
Dd = Dd.drop_duplicates(["sym", "date"]).sort_values(["sym", "date"])
daily = {s: (g.date.values, g.high.values, g.low.values, g.close.values) for s, g in Dd.groupby("sym")}; del Dd, rows

# Safe: panel_1h.pkl is produced locally by build_panel.py from hash-logged Binance zips, never external.
p = pd.read_pickle(os.path.join(OUT, "panel_1h.pkl"))
grid = pd.date_range("2020-01-01", "2022-12-31 23:00", freq="h", tz="UTC")
syms = sorted(p["sym"].unique()); idx = {s: i for i, s in enumerate(syms)}; T = len(grid)
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"): m[idx[s], grid.get_indexer(g["ts"])] = g[col].values
    return m
O, H, L, C = (mat(c) for c in ["open", "high", "low", "close"]); del p

def fib(px, start, hi_arr, lo_arr, tag):
    f = {}
    if len(hi_arr) < 20 or not np.isfinite(px): return f
    iH, iL = int(np.nanargmax(hi_arr)), int(np.nanargmin(lo_arr)); Hh, Ll = hi_arr[iH], lo_arr[iL]
    if not (Hh > Ll > 0): return f
    pos = (px - Ll) / (Hh - Ll); pos0 = (start - Ll) / (Hh - Ll) if np.isfinite(start) else np.nan
    f[f"fib{tag}_pos"] = pos
    f[f"fib{tag}_zone"] = float(np.digitize(pos, LEVELS))
    f[f"fib{tag}_uptrend_swing"] = float(iL < iH)
    f[f"fib{tag}_near"] = float(np.min(np.abs(LEVELS[1:] - pos)))
    f[f"fib{tag}_cross618_or_1"] = float(np.isfinite(pos0) and any(pos0 < lv <= pos for lv in (.618, 1.0)))
    return f

def features(sym, t, px, start):
    f = {}; th = grid[t]; day = th.normalize()
    if sym in daily:
        dd, dh, dl, dc = daily[sym]; k = np.searchsorted(dd, np.datetime64(day.tz_convert(None)), side="left")
        dh, dl, dc = dh[:k], dl[:k], dc[:k]
        sm = {n: (dc[-n:].mean() if len(dc) >= n else np.nan) for n in NS}
        if np.isfinite(sm[200]):
            f["above_count"] = float(sum(px > sm[n] for n in NS if np.isfinite(sm[n])))
            f["stack"] = float(sm[11] > sm[21] > sm[50] > sm[100] > sm[200])
        f["sma100_dist"] = px / sm[100] - 1 if np.isfinite(sm[100]) else np.nan
        f["res200_dist"] = px / dh[-200:].max() - 1 if len(dh) >= 200 else np.nan
        f.update(fib(px, start, dh[-50:], dl[-50:], "50d"))
        if len(dh) >= 200: f.update(fib(px, start, dh[-200:], dl[-200:], "200d"))
    i = idx[sym]
    if t >= 500: f.update(fib(px, start, H[i, t - 500:t], L[i, t - 500:t], "500h"))
    return f

def exits(i, e):
    if e + HMAX > T: return None
    ent = O[i, e]
    if not np.isfinite(ent) or ent <= 0: return None
    hh, cl = H[i, e:e + HMAX], C[i, e:e + HMAX]
    if np.isfinite(cl).sum() < 0.9 * HMAX: return None
    entc = ent * (1 + COST); cl_f = pd.Series(cl).ffill().values
    def nxt(k):
        v = O[i, e + k + 1] if e + k + 1 < T else np.nan
        return v if np.isfinite(v) else cl_f[k]
    out = lambda px: px * (1 - COST) / entc - 1
    def tp_sl(tp, sl, mh):
        for k in range(mh):
            if sl is not None and cl_f[k] <= ent * (1 + sl): return out(nxt(k))
            if np.isfinite(hh[k]) and hh[k] >= ent * (1 + tp): return out(ent * (1 + tp))
        return out(cl_f[mh - 1])
    def trail(pct):
        pk = ent
        for k in range(HMAX):
            if np.isfinite(hh[k]): pk = max(pk, hh[k])
            if cl_f[k] <= pk * (1 - pct): return out(nxt(k))
        return out(cl_f[-1])
    x3 = tp_sl(.30, -.15, 168); peak = np.nanmax(hh) / entc - 1
    return dict(runner=float(x3 > .25), reach50_30d=float(peak >= .5), reach100_30d=float(peak >= 1),
                X1_hold3d=out(cl_f[71]), X3_tp30_sl15_7d=x3, X4_tp50_14d=tp_sl(.5, None, 336), X2_trail20=trail(.2), X5_trail30=trail(.3))

ev = pd.read_csv(os.path.join(OUT, "events_v0.csv")); ev = ev[ev.status == "OK"]
ER = []
for r in ev.itertuples():
    t = grid.get_loc(pd.Timestamp(r.trigger_hour)); x = exits(idx[r.sym], t + 1)
    if x is None: continue
    ER.append(dict(kind="event", sym=r.sym, trigger_hour=r.trigger_hour, year=int(r.trigger_hour[:4]),
                   **x, **features(r.sym, t, r.trig_close, r.start_px)))
ct = pd.read_csv(os.path.join(OUT, "controls_v0.csv"))
for r in ct.itertuples():
    t = grid.get_loc(pd.Timestamp(r.trigger_hour)); i = idx[r.sym]; x = exits(i, t + 1)
    if x is None: continue
    ER.append(dict(kind="control", sym=r.sym, trigger_hour=r.trigger_hour, year=int(r.trigger_hour[:4]),
                   **x, **features(r.sym, t, C[i, t], C[i, t - 3])))
A = pd.DataFrame(ER); A.to_csv(os.path.join(OUT, "fib_trend_v1_all.csv"), index=False)
E, K = A[A.kind == "event"].reset_index(drop=True), A[A.kind == "control"].reset_index(drop=True)
OUTC = ["runner", "reach50_30d", "reach100_30d", "X1_hold3d", "X3_tp30_sl15_7d", "X4_tp50_14d", "X2_trail20", "X5_trail30"]
FIBF = [c for c in A.columns if c.startswith("fib")]

# ---- Part A: Fibonacci search
exp, chk = E[E.year <= 2021].reset_index(drop=True), E[E.year == 2022].reset_index(drop=True)
def edges(x):
    ok = np.isfinite(x); u = np.unique(x[ok])
    if len(u) <= 10: return [(v, v) for v in u]
    q = np.nanpercentile(x, [0, 20, 40, 60, 80, 100]); return list(zip(q[:-1], q[1:]))
def search(Fx, Y, oc):
    out = []
    for f in FIBF:
        x = Fx[f].values.astype(float); ok = np.isfinite(x)
        if ok.sum() < 200: continue
        for lo, hi in edges(x):
            m = ok & (x >= lo) & (x <= hi); y = Y[oc].values[m]
            if len(y) >= 60: out.append((f, float(lo), float(hi), len(y), float(np.nanmean(y))))
    return out
rng = np.random.default_rng(618); partA = {}; ncells = 0
for oc in OUTC:
    cells = sorted(search(exp[FIBF], exp, oc), key=lambda c: -c[4]); ncells += len(cells)
    null = [max(c[4] for c in search(exp[FIBF].sample(frac=1, random_state=int(rng.integers(1e9))).reset_index(drop=True), exp, oc)) for _ in range(200)]
    bar = float(np.percentile(null, 95)); top = []
    for f, lo, hi, n, mu in cells[:6]:
        x = chk[f].values.astype(float); m = np.isfinite(x) & (x >= lo) & (x <= hi)
        top.append(dict(feature=f, range=[round(lo, 3), round(hi, 3)], explore_n=n, explore=round(mu, 4), beats_luck=bool(mu > bar),
                        check2022_n=int(m.sum()), check2022=round(float(np.nanmean(chk[oc].values[m])), 4) if m.sum() else None))
    partA[oc] = dict(explore_all=round(float(exp[oc].mean()), 4), check2022_all=round(float(chk[oc].mean()), 4), luck_bar=round(bar, 4), top=top)
desc = {}
for f in FIBF:
    x = exp[f].values.astype(float)
    if np.isfinite(x).sum() < 200: continue
    desc[f] = []
    for lo, hi in edges(x):
        me = np.isfinite(x) & (x >= lo) & (x <= hi); xc = chk[f].values.astype(float); mc = np.isfinite(xc) & (xc >= lo) & (xc <= hi)
        desc[f].append(dict(range=[round(lo, 3), round(hi, 3)], n_e=int(me.sum()), runner_e=round(float(exp.runner[me].mean()), 3),
                            r100_e=round(float(exp.reach100_30d[me].mean()), 3), n_c=int(mc.sum()),
                            runner_c=round(float(chk.runner[mc].mean()), 3) if mc.sum() else None))

# ---- Part B: like-for-like
def trend_mask(d): return (d.above_count >= 5) & (d.res200_dist >= -0.15)
def block(d):
    return {oc: round(float(d[oc].mean()), 4) for oc in OUTC} | {"n": int(len(d))}
partB = {}
for yrs, name in [((2020, 2021), "2020_21"), ((2022,), "2022")]:
    e, k = E[E.year.isin(yrs)], K[K.year.isin(yrs)]
    partB[name] = dict(TREND=dict(ignitions=block(e[trend_mask(e)]), random_coins=block(k[trend_mask(k)])),
                       NOT_TREND=dict(ignitions=block(e[~trend_mask(e)]), random_coins=block(k[~trend_mask(k)])),
                       ALL=dict(ignitions=block(e), random_coins=block(k)))
singles = {}
for f in ["sma100_dist", "res200_dist", "above_count", "stack"]:
    cut = float(np.nanpercentile(E[E.year <= 2021][f], 80)) if f not in ("above_count", "stack") else (6.0 if f == "above_count" else 1.0)
    singles[f] = {"cut": cut}
    for yrs, name in [((2020, 2021), "2020_21"), ((2022,), "2022")]:
        e, k = E[E.year.isin(yrs) & (E[f] >= cut)], K[K.year.isin(yrs) & (K[f] >= cut)]
        singles[f][name] = dict(ignitions=block(e), random_coins=block(k))
res = dict(n_events=len(E), n_controls=len(K), partA_cells=ncells, partA=partA, partA_by_feature=desc, partB_TREND=partB,
           partB_single_features=singles, script_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest())
json.dump(res, open(os.path.join(OUT, "summary_fib_trend_v1.json"), "w"), indent=1, default=float)
print("done", len(E), len(K), ncells)

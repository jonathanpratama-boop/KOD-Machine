"""PATHS_v1 — follow every candidate's full price path (unrealized gains and losses), no exit rule. Exploratory, 2026-11-03.
Same candidates as ENTRY_TIMING_v1 (hourly ignitions 2020-26). Entry = next hour open after the trigger close.
Records, for each candidate, mark-to-market at checkpoints up to 30 days, running best/worst, time of the peak, and what was
visible in the first hours after entry (follow-through, new highs, volume persistence). No trading rule is applied or tuned."""
import glob, io, json, os, sys, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RS = os.path.dirname(HERE); IG = os.path.join(RS, "ignition_v0")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
PART = sys.argv[1]
CK = [1, 2, 3, 4, 6, 8, 12, 18, 24, 36, 48, 72, 96, 120, 168, 240, 336, 504, 720]
def read_zip(fp, cols):
    with zipfile.ZipFile(fp) as z: df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
    df = df.iloc[:, cols].astype(float); t = df.iloc[:, 0].values.astype("int64"); df.iloc[:, 0] = np.where(t > 1e14, t // 1000, t); return df
if PART == "disc":
    # panel_1h.pkl is our own build_panel.py output from Binance archive zips (local, trusted)
    p = pd.read_pickle(os.path.join(IG, "out/panel_1h.pkl")).rename(columns={"quote_vol": "qv"}); g0 = pd.Timestamp("2020-01-01", tz="UTC")
else:
    uni = set(json.load(open(os.path.join(IG, "raw_holdout/universe_holdout.json")))["universe"]); fr = []
    for fp in sorted(glob.glob(os.path.join(IG, "raw_holdout/k1h/*.zip"))):
        s = os.path.basename(fp).split("-1h-")[0]
        if s not in uni: continue
        try:
            d = read_zip(fp, [0, 1, 2, 3, 4, 7]); d.columns = ["t", "open", "high", "low", "close", "qv"]; d["sym"] = s; fr.append(d)
        except Exception: pass
    p = pd.concat(fr); del fr; p["ts"] = pd.to_datetime(p.t.astype("int64"), unit="ms", utc=True); g0 = pd.Timestamp("2022-11-01", tz="UTC")
grid = pd.date_range(g0, p.ts.max().floor("h"), freq="h")
p = p[(p.ts >= grid[0]) & (p.ts <= grid[-1])].drop_duplicates(["sym", "ts"])
syms = sorted(p.sym.unique()); SI = {s: i for i, s in enumerate(syms)}; T = len(grid)
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"): m[SI[s], grid.get_indexer(g.ts)] = g[col].values
    return m
O, H, L, C, Q = (mat(c) for c in ["open", "high", "low", "close", "qv"]); del p
print(PART, C.shape, flush=True)
# BTC context path (same window) for market-relative reading
jb = SI.get("BTCUSDT")
psy = pd.read_csv(os.path.join(RS, "psych_v1/out/ignitions_with_psych.csv"), usecols=["sym", "ts", "score", "trend", "fng_prev", "fund24", "moved_3h"])
psy["ts"] = pd.to_datetime(psy.ts, utc=True)
psy = psy[(psy.ts >= grid[0]) & (psy.ts <= grid[-1])]
rows = []
for r in psy.itertuples():
    if r.sym not in SI: continue
    i, e = SI[r.sym], grid.get_loc(r.ts)
    if e < 4 or e + 2 >= T: continue
    ent = O[i, e + 1]
    if not (np.isfinite(ent) and ent > 0): continue
    k0 = e + 1; n = min(720, T - k0)
    c = pd.Series(C[i, k0:k0 + n]).ffill().values; h = H[i, k0:k0 + n]; l = L[i, k0:k0 + n]
    if np.isfinite(c).sum() < 0.9 * min(n, 336): continue
    hh = np.fmax.accumulate(np.where(np.isfinite(h), h, -np.inf)); ll = np.fmin.accumulate(np.where(np.isfinite(l), l, np.inf))
    row = dict(sym=r.sym, ts=str(r.ts), year=r.ts.year, score=r.score, trend=r.trend, fng_prev=r.fng_prev, fund24=r.fund24,
               moved_3h=r.moved_3h, horizon=n)
    for k in CK:
        if k <= n:
            row[f"r{k}"] = c[k - 1] / ent - 1; row[f"mfe{k}"] = hh[k - 1] / ent - 1; row[f"mae{k}"] = ll[k - 1] / ent - 1
    kp = int(np.nanargmax(np.where(np.isfinite(h), h, -np.inf))); row["peak"] = h[kp] / ent - 1; row["h_peak"] = kp + 1
    row["trough_before_peak"] = np.nanmin(l[:kp + 1]) / ent - 1
    trig_hi = np.nanmax(H[i, e - 2:e + 1])
    row["newhigh_6h"] = bool(np.nanmax(h[:6]) > trig_hi) if np.isfinite(h[:6]).any() else np.nan
    q3 = np.nansum(Q[i, e - 2:e + 1]) / 3
    row["vol_persist_6h"] = np.nanmean(Q[i, k0:k0 + 6]) / q3 if q3 > 0 else np.nan
    if jb is not None and np.isfinite(O[jb, k0]):
        cb = pd.Series(C[jb, k0:k0 + n]).ffill().values
        for k in (6, 24, 168):
            if k <= n: row[f"btc{k}"] = cb[k - 1] / O[jb, k0] - 1
    rows.append(row)
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUT, f"paths_{PART}.csv"), index=False); print("done", PART, len(R), flush=True)

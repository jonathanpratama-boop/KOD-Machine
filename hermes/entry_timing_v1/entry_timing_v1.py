"""ENTRY_TIMING_v1 (see PLAN.md). Exploratory. Same candidates, same exit (TP+50% from fill else 336h), different entries."""
import glob, io, json, os, sys, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); IG = os.path.join(os.path.dirname(HERE), "ignition_v0")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
COST = 0.003; TP = 1.5; HOLD = 336
PART = sys.argv[1]  # "disc" (2020-22) or "hold" (2023-26)

def read_zip(fp, cols):
    with zipfile.ZipFile(fp) as z: df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
    df = df.iloc[:, cols].astype(float); t = df.iloc[:, 0].values.astype("int64"); df.iloc[:, 0] = np.where(t > 1e14, t // 1000, t); return df

# ---------------- hourly matrices
if PART == "disc":
    # panel_1h.pkl was written by our own build_panel.py from Binance archive zips (local, trusted)
    p = pd.read_pickle(os.path.join(IG, "out/panel_1h.pkl")).rename(columns={"quote_vol": "qv"})
    g0 = pd.Timestamp("2020-01-01", tz="UTC")
else:
    uni = set(json.load(open(os.path.join(IG, "raw_holdout/universe_holdout.json")))["universe"]); fr = []
    for fp in sorted(glob.glob(os.path.join(IG, "raw_holdout/k1h/*.zip"))):
        s = os.path.basename(fp).split("-1h-")[0]
        if s not in uni: continue
        try:
            d = read_zip(fp, [0, 1, 2, 3, 4, 7]); d.columns = ["t", "open", "high", "low", "close", "qv"]; d["sym"] = s; fr.append(d)
        except Exception: pass
    p = pd.concat(fr); del fr; p["ts"] = pd.to_datetime(p.t.astype("int64"), unit="ms", utc=True)
    g0 = pd.Timestamp("2022-11-01", tz="UTC")
grid = pd.date_range(g0, p.ts.max().floor("h"), freq="h")
p = p[(p.ts >= grid[0]) & (p.ts <= grid[-1])].drop_duplicates(["sym", "ts"])
syms = sorted(p.sym.unique()); SI = {s: i for i, s in enumerate(syms)}; T = len(grid)
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"): m[SI[s], grid.get_indexer(g.ts)] = g[col].values
    return m
O, H, L, C, Q = (mat(c) for c in ["open", "high", "low", "close", "qv"]); del p
print(PART, "hourly", C.shape, grid[0], grid[-1], flush=True)

# ---------------- daily trend state (previous completed day)
dr = []
for fp in glob.glob(os.path.join(IG, "raw/k1d/*.zip")) + glob.glob(os.path.join(IG, "raw_holdout/k1d/*.zip")):
    s = os.path.basename(fp).split("-1d-")[0]
    if s not in SI: continue
    try:
        d = read_zip(fp, [0, 2, 4]); d.columns = ["t", "high", "close"]; d["sym"] = s; dr.append(d)
    except Exception: pass
D = pd.concat(dr); del dr; D["date"] = pd.to_datetime(D.t.astype("int64"), unit="ms").dt.normalize()
D = D.drop_duplicates(["sym", "date"]).sort_values(["sym", "date"])
trend_state = {}
for s, g in D.groupby("sym"):
    c = g.close.values; h = g.high.values
    s50 = pd.Series(c).rolling(50).mean().values; s200 = pd.Series(c).rolling(200).mean().values; h200 = pd.Series(h).rolling(200).max().values
    st = (c > s50) & (c > s200) & (c >= 0.85 * h200)
    trend_state[s] = (g.date.values, st)
del D
def trend_before(s, ts):
    if s not in trend_state: return False
    dd, st = trend_state[s]; k = np.searchsorted(dd, np.datetime64(ts.tz_convert(None).normalize()), side="left") - 1
    return bool(st[k]) if k >= 0 else False

# ---------------- candidates
if PART == "disc":
    A = pd.read_csv(os.path.join(IG, "out/fib_trend_v1_all.csv")); A = A[A.kind == "event"].copy()
    A["score"] = ((A.above_count >= 5).astype(int) + (A["stack"] == 1).astype(int) + (A.res200_dist >= -0.15).astype(int)
                  + (A.sma100_dist >= 0.5).astype(int) + (A.fib200d_cross618_or_1 == 1).astype(int) + (A.fib50d_cross618_or_1 == 1).astype(int))
else:
    A = pd.read_csv(os.path.join(IG, "out_holdout/holdout_trades.csv")); A = A[(A.kind == "event")].copy()
A["ts"] = pd.to_datetime(A.trigger_hour, utc=True)
cand = [(SI[r.sym], grid.get_loc(r.ts), int(r.score), r.ts) for r in A.itertuples() if r.sym in SI and r.ts in grid]

# earlier detector: +5% in 1h on >=5x hourly volume, prior-week rise <=30% (to the hour before), liquidity as scan_v0
def shift(a, k): o = np.full_like(a, np.nan); o[:, k:] = a[:, :-k]; return o
cs = np.concatenate([np.zeros((len(syms), 1)), np.nancumsum(np.nan_to_num(Q), axis=1)], axis=1)
cc = np.concatenate([np.zeros((len(syms), 1)), np.cumsum(np.isfinite(Q).astype(float), axis=1)], axis=1)
t = np.arange(T); lo = t - 170; hi = t - 2; valid = lo >= 0
base = np.full_like(Q, np.nan); nobs = np.full_like(Q, np.nan)
base[:, valid] = (cs[:, hi[valid]] - cs[:, lo[valid]]) / 168.0; nobs[:, valid] = cc[:, hi[valid]] - cc[:, lo[valid]]
base = np.where(nobs >= 150, base, np.nan)
with np.errstate(invalid="ignore", divide="ignore"):
    r1 = C / shift(C, 1) - 1; trig5 = (r1 >= .05) & (Q / base >= 5) & (shift(C, 1) / shift(C, 169) - 1 <= .30) & (base >= 20000)
start_t = 0 if PART == "disc" else grid.get_loc(pd.Timestamp("2023-01-01", tz="UTC"))
trig5[:, :start_t] = False; trig5[:, T - HOLD - 100:] = False
early, last = [], {}
for e_t in range(T):
    for i in np.where(trig5[:, e_t])[0]:
        if e_t - last.get(i, -10**9) < 72: continue
        last[i] = e_t; early.append((i, e_t, -1, grid[e_t]))
print("candidates", len(cand), "early", len(early), flush=True)

# ---------------- simulation helpers
def exit_from(i, px, k, chk):
    """fill at price px in hour k; TP checked from hour chk; time exit at close of hour k+HOLD-1."""
    if k + HOLD > T: return None
    c = C[i, k:k + HOLD]
    if np.isfinite(c).sum() < .9 * HOLD: return None
    entc = px * (1 + COST); hh = H[i, chk:k + HOLD]
    hit = np.where(np.isfinite(hh) & (hh >= px * TP))[0]
    if len(hit): return px * TP * (1 - COST) / entc - 1, 1
    cf = pd.Series(c).ffill().values
    return cf[-1] * (1 - COST) / entc - 1, 0

def variants(i, e):
    tc = C[i, e]; out = {}
    def mk(k):  # market buy at open of hour k
        if k >= T or not (np.isfinite(O[i, k]) and O[i, k] > 0): return None
        r = exit_from(i, O[i, k], k, k); return None if r is None else (r[0], r[1], O[i, k] / tc - 1)
    out["V0_NEXT_OPEN"] = mk(e + 1)
    for x in (5, 10, 15):
        lim = tc * (1 - x / 100); res = None
        for k in range(e + 1, min(T, e + 73)):
            if np.isfinite(L[i, k]) and L[i, k] <= lim:
                px = min(O[i, k], lim) if np.isfinite(O[i, k]) else lim
                r = exit_from(i, px, k, k + 1); res = None if r is None else (r[0], r[1], px / tc - 1); break
        out[f"V1_LIMIT_{x}"] = res if res is not None else "NOFILL"
    for w in (6, 24):
        k = e + w
        out[f"V2_HOLD_{w}H"] = (mk(k + 1) if (k < T and np.isfinite(C[i, k]) and C[i, k] >= tc) else "NOFILL")
    res = "NOFILL"; dipped = False
    for k in range(e + 1, min(T, e + 73)):
        if not np.isfinite(C[i, k]): continue
        if C[i, k] <= tc * .95: dipped = True
        elif dipped and C[i, k] > tc: res = mk(k + 1) or "NOFILL"; break
    out["V3_DIP_RECLAIM"] = res
    res = "NOFILL"
    if e + 25 < T:
        d1 = np.nanmax(H[i, e + 1:e + 25]) if np.isfinite(H[i, e + 1:e + 25]).any() else np.nan
        for k in range(e + 25, min(T, e + 97)):
            if np.isfinite(C[i, k]) and np.isfinite(d1) and C[i, k] > d1: res = mk(k + 1) or "NOFILL"; break
    out["V4_BREAK_DAY1_HIGH"] = res
    # anatomy
    an = dict(moved_3h=tc / C[i, e - 3] - 1 if e >= 3 and np.isfinite(C[i, e - 3]) else np.nan,
              dip72=np.nanmin(L[i, e + 1:e + 73]) / tc - 1 if np.isfinite(L[i, e + 1:e + 73]).any() else np.nan,
              peak336=np.nanmax(H[i, e + 1:e + 337]) / tc - 1 if np.isfinite(H[i, e + 1:e + 337]).any() else np.nan)
    if np.isfinite(an["peak336"]) and an["peak336"] > 0:
        seg = H[i, e + 1:e + 337]; kpk = int(np.nanargmax(seg)); an["hours_to_peak"] = kpk + 1
        an["dip_before_peak"] = np.nanmin(L[i, e + 1:e + 2 + kpk]) / tc - 1
    return out, an

rows = []
for kind, lst in (("ignition", cand), ("early1h", early)):
    for n, (i, e, sc, ts) in enumerate(lst):
        if e < 3 or e + 2 >= T: continue
        out, an = variants(i, e) if kind == "ignition" else ({"V5_EARLY_1H": None}, {})
        if kind == "early1h":
            k = e + 1
            if k < T and np.isfinite(O[i, k]) and O[i, k] > 0:
                r = exit_from(i, O[i, k], k, k); out["V5_EARLY_1H"] = None if r is None else (r[0], r[1], O[i, k] / C[i, e] - 1)
            # did a full ignition (+10%/3h, vol>=5x) follow within 6h? (descriptive, uses the future)
            an["became_ignition_6h"] = bool(any(np.isfinite(C[i, k]) and np.isfinite(C[i, e - 2]) and C[i, k] / C[i, max(0, k - 3)] - 1 >= .10 for k in range(e, min(T, e + 7))))
            an["peak336"] = np.nanmax(H[i, e + 1:e + 337]) / C[i, e] - 1 if np.isfinite(H[i, e + 1:e + 337]).any() else np.nan
        base_row = dict(kind=kind, sym=syms[i], ts=str(ts), year=ts.year, score=sc, trend=trend_before(syms[i], ts), **an)
        for v, r in out.items():
            if r is None: rows.append({**base_row, "variant": v, "status": "NO_WINDOW"})
            elif r == "NOFILL": rows.append({**base_row, "variant": v, "status": "NOFILL"})
            else: rows.append({**base_row, "variant": v, "status": "TRADE", "net": r[0], "tp": r[1], "entry_vs_trig": r[2]})
        if n % 2000 == 0: print(kind, n, len(lst), flush=True)
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUT, f"trades_{PART}.csv"), index=False)
print("done", PART, len(R), flush=True)

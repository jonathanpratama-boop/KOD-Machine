"""SPIKE_DEFAULT_v1 (see PLAN.md). Exploratory."""
import glob, io, json, os, sys, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RS = os.path.dirname(HERE); IG = os.path.join(RS, "ignition_v0")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
PART = sys.argv[1]; COST = 0.003
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
O, H, L, C = (mat(c) for c in ["open", "high", "low", "close"]); del p
print(PART, C.shape, flush=True)
fng = pd.DataFrame(json.load(open(os.path.join(IG, "raw/fng_alternative_me.json")))["data"])
fng["d"] = pd.to_datetime(fng.timestamp.astype("int64"), unit="s", utc=True).dt.normalize(); fng = fng.set_index("d")["value"].astype(int)
# candidates
ev = pd.read_csv(os.path.join(RS, "psych_v1/out/ignitions_with_psych.csv"), usecols=["sym", "ts", "score", "trend", "fng_prev"])
ev["ts"] = pd.to_datetime(ev.ts, utc=True); ev["kind"] = "event"
if PART == "disc":
    ct = pd.read_csv(os.path.join(IG, "out/fib_trend_v1_all.csv"), usecols=["kind", "sym", "trigger_hour"])
else:
    ct = pd.read_csv(os.path.join(IG, "out_holdout/holdout_trades.csv"), usecols=["kind", "sym", "trigger_hour"])
ct = ct[ct.kind == "control"].rename(columns={"trigger_hour": "ts"}); ct["ts"] = pd.to_datetime(ct.ts, utc=True)
ct = ct.sample(min(20000, len(ct)), random_state=20261103)
ct["fng_prev"] = (ct.ts.dt.normalize() - pd.Timedelta(days=1)).map(fng); ct["score"] = np.nan; ct["trend"] = np.nan
cand = pd.concat([ev, ct[["sym", "ts", "score", "trend", "fng_prev", "kind"]]])
cand = cand[(cand.ts >= grid[0]) & (cand.ts <= grid[-1]) & cand.sym.isin(SI)]
if PART == "disc": cand = cand[cand.ts < pd.Timestamp("2023-01-01", tz="UTC")]
else: cand = cand[cand.ts >= pd.Timestamp("2023-01-01", tz="UTC")]

def first(mask):
    w = np.where(mask)[0]; return w[0] if len(w) else None
def spike(i, k0, tp, sl, hours=72):
    ent = O[i, k0]; n = min(hours, T - k0)
    if n < hours: return None
    o, h, l, c = O[i, k0:k0 + n], H[i, k0:k0 + n], L[i, k0:k0 + n], C[i, k0:k0 + n]
    if np.isfinite(c).sum() < .9 * n: return None
    up = ent * (1 + tp); dn = ent * (1 - sl) if sl else -np.inf
    a = first(np.isfinite(h) & (h >= up)); b = first(np.isfinite(l) & (l <= dn)) if sl else None
    if b is not None and (a is None or b <= a):
        px = min(o[b], dn) if np.isfinite(o[b]) else dn; return px * (1 - COST) / (ent * (1 + COST)) - 1, "stop"
    if a is not None:
        px = max(o[a], up) if np.isfinite(o[a]) else up; return px * (1 - COST) / (ent * (1 + COST)) - 1, "tp"
    last = pd.Series(c).ffill().values[-1]; return last * (1 - COST) / (ent * (1 + COST)) - 1, "time"
def hold(i, k0, hours=336):
    ent = O[i, k0]; n = min(hours, T - k0)
    if n < hours: return None
    o, h, l, c = O[i, k0:k0 + n], H[i, k0:k0 + n], L[i, k0:k0 + n], C[i, k0:k0 + n]
    if np.isfinite(c).sum() < .9 * n: return None
    peak = np.fmax.accumulate(np.where(np.isfinite(h), h, ent)); pk_prev = np.concatenate([[ent], peak[:-1]])
    g = pk_prev / ent - 1
    level = np.where(g >= .20, ent * (1 + g / 2), ent * .85)
    b = first(np.isfinite(l) & (l <= level))
    if b is not None:
        px = min(o[b], level[b]) if np.isfinite(o[b]) else level[b]; return px * (1 - COST) / (ent * (1 + COST)) - 1, "trail/stop"
    last = pd.Series(c).ffill().values[-1]; return last * (1 - COST) / (ent * (1 + COST)) - 1, "time"
def old_tp50(i, k0, hours=336):
    ent = O[i, k0]; n = min(hours, T - k0)
    if n < hours: return None
    h, c = H[i, k0:k0 + n], C[i, k0:k0 + n]
    if np.isfinite(c).sum() < .9 * n: return None
    a = first(np.isfinite(h) & (h >= ent * 1.5))
    if a is not None: return 1.5 * (1 - COST) / (1 + COST) - 1, "tp"
    return pd.Series(c).ffill().values[-1] * (1 - COST) / (ent * (1 + COST)) - 1, "time"
VARS = [(tp, sl) for tp in (.10, .15, .20) for sl in (.10, .15, None)]
rows = []
for n_, r in enumerate(cand.itertuples()):
    i, e = SI[r.sym], grid.get_loc(r.ts); k0 = e + 1
    if k0 >= T or not (np.isfinite(O[i, k0]) and O[i, k0] > 0): continue
    greed = bool(r.fng_prev > 75) if np.isfinite(r.fng_prev) else False
    base = dict(kind=r.kind, sym=r.sym, ts=str(r.ts), year=r.ts.year, score=r.score, trend=r.trend, fng_prev=r.fng_prev)
    hh = hold(i, k0) if greed else None
    for tp, sl in VARS:
        s = spike(i, k0, tp, sl)
        if s is None: continue
        name = f"T{int(tp*100)}_L{int(sl*100) if sl else 'none'}"
        rows.append({**base, "variant": name + "_HOLDoff", "net": s[0], "how": s[1]})
        if greed:
            if hh is not None: rows.append({**base, "variant": name + "_HOLDon", "net": hh[0], "how": hh[1]})
        else: rows.append({**base, "variant": name + "_HOLDon", "net": s[0], "how": s[1]})
    x = old_tp50(i, k0)
    if x is not None: rows.append({**base, "variant": "REF_TP50_14d", "net": x[0], "how": x[1]})
    s = spike(i, k0, 99, None)
    if s is not None: rows.append({**base, "variant": "REF_HOLD72h", "net": s[0], "how": s[1]})
    if n_ % 5000 == 0: print(n_, len(cand), flush=True)
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUT, f"trades_{PART}.csv.gz"), index=False, compression="gzip"); print("done", PART, len(R), flush=True)

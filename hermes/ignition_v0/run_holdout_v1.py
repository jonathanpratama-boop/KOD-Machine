"""COMBO_HOLDOUT_v1 runner. Implements PROTOCOL_COMBO_HOLDOUT_v1.md (GitHub hermes/ignition-combo-holdout-v1 @ ac14151)
exactly: same detector as scan_v0.py, same clues as combo_v1.py/fib_trend_v1.py, Version A and B, primary exit TP+50%
else hour 336, pass bar as written. Run ONCE. Events: trigger hour >= 2023-01-01 UTC. Warm-up hours from 2022-11.
Implementation notes (engineering, not rule changes): microsecond timestamps normalised to ms; the primary exit needs
336 hours of data after entry (>=90% present), secondary 30-day metrics need 720 hours; events without enough data are
counted and reported, not dropped silently."""
import glob, io, json, os, zipfile, hashlib
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); RH = os.path.join(ROOT, "raw_holdout"); OUT = os.path.join(ROOT, "out_holdout")
os.makedirs(OUT, exist_ok=True)
COST = 0.003; NS = [11, 21, 50, 100, 200, 500]
SPEC = dict(trigger_ret_3h=0.10, trigger_vol_mult=5.0, max_prior_run_7d=0.30, min_avg_hourly_quote_usd=20000, cooldown_h=72, horizon_h=72)
uni = json.load(open(os.path.join(RH, "universe_holdout.json")))["universe"]

def read_zip(fp, cols_idx):
    with zipfile.ZipFile(fp) as z:
        df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
    df = df.iloc[:, cols_idx].astype(float)
    t = df.iloc[:, 0].values.astype("int64"); t = np.where(t > 1e14, t // 1000, t)  # us -> ms
    df.iloc[:, 0] = t; return df
# ---- hourly
fr, log = [], {"hourly_files": 0, "hourly_fail": []}
for fp in sorted(glob.glob(os.path.join(RH, "k1h", "*.zip"))):
    s = os.path.basename(fp).split("-1h-")[0]
    if s not in uni: continue
    try:
        d = read_zip(fp, [0, 1, 2, 3, 4, 7]); d.columns = ["t", "open", "high", "low", "close", "qv"]; d["sym"] = s; fr.append(d); log["hourly_files"] += 1
    except Exception as e: log["hourly_fail"].append([os.path.basename(fp), repr(e)])
p = pd.concat(fr); p["ts"] = pd.to_datetime(p.t.astype("int64"), unit="ms", utc=True); del fr
grid = pd.date_range(pd.Timestamp("2022-11-01", tz="UTC"), p.ts.max().floor("h"), freq="h")
p = p[(p.ts >= grid[0]) & (p.ts <= grid[-1])].drop_duplicates(["sym", "ts"])
syms = sorted(p.sym.unique()); idx = {s: i for i, s in enumerate(syms)}; T = len(grid)
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"): m[idx[s], grid.get_indexer(g.ts)] = g[col].values
    return m
O, H, L, C, Q = (mat(c) for c in ["open", "high", "low", "close", "qv"]); del p
log.update(symbols_hourly=len(syms), grid_start=str(grid[0]), grid_end=str(grid[-1]))
# ---- daily (2017-08..2022-12 from raw/k1d, 2023+ from raw_holdout/k1d; same source data.binance.vision)
dr = []
for fp in glob.glob(os.path.join(ROOT, "raw", "k1d", "*.zip")) + glob.glob(os.path.join(RH, "k1d", "*.zip")):
    s = os.path.basename(fp).split("-1d-")[0]
    if s not in idx: continue
    try:
        d = read_zip(fp, [0, 2, 3, 4]); d.columns = ["t", "high", "low", "close"]; d["sym"] = s; dr.append(d)
    except Exception: pass
Dd = pd.concat(dr); Dd["date"] = pd.to_datetime(Dd.t.astype("int64"), unit="ms", utc=True).dt.normalize()
Dd = Dd.drop_duplicates(["sym", "date"]).sort_values(["sym", "date"])
daily = {s: (g.date.values, g.high.values, g.low.values, g.close.values) for s, g in Dd.groupby("sym")}; del Dd, dr

# ---- detector (as scan_v0.py)
def shift(a, k): o = np.full_like(a, np.nan); o[:, k:] = a[:, :-k]; return o
r3 = C / shift(C, 3) - 1; q3 = Q + shift(Q, 1) + shift(Q, 2)
cs = np.concatenate([np.zeros((len(syms), 1)), np.nancumsum(np.nan_to_num(Q), axis=1)], axis=1)
cc = np.concatenate([np.zeros((len(syms), 1)), np.cumsum(np.isfinite(Q).astype(float), axis=1)], axis=1)
t = np.arange(T); lo = t - 170; hi = t - 2; valid = lo >= 0
base = np.full_like(Q, np.nan); nobs = np.full_like(Q, np.nan)
base[:, valid] = (cs[:, hi[valid]] - cs[:, lo[valid]]) / 168.0; nobs[:, valid] = cc[:, hi[valid]] - cc[:, lo[valid]]
base = np.where(nobs >= 150, base, np.nan)
vmult = q3 / (3 * base); prior = shift(C, 3) / shift(C, 171) - 1; liquid = base >= SPEC["min_avg_hourly_quote_usd"]
with np.errstate(invalid="ignore"):
    trig = (r3 >= .10) & (vmult >= 5) & (prior <= .30) & liquid
trig &= (t[None, :] < T - SPEC["horizon_h"] - 1)
start_t = grid.get_loc(pd.Timestamp("2023-01-01", tz="UTC"))
def ok72(i, e):
    ent = O[i, e]
    return np.isfinite(ent) and ent > 0 and np.isfinite(C[i, e:e + 72]).sum() >= 72 * .9
rng = np.random.default_rng(7); last = {}; ev, ct = [], []
for e_t in range(T):
    col = np.where(trig[:, e_t])[0]
    for i in col:
        if e_t - last.get(i, -10**9) < SPEC["cooldown_h"]: continue
        last[i] = e_t
        if e_t < start_t: continue
        if not ok72(i, e_t + 1): ev.append((i, e_t, "NO_OUTCOME_DATA")); continue
        ev.append((i, e_t, "OK"))
        recent = trig[:, max(0, e_t - 72):min(T, e_t + 73)].any(axis=1)
        pool = np.where(liquid[:, e_t] & ~recent)[0]
        if len(pool):
            for j in rng.choice(pool, size=min(5, len(pool)), replace=False):
                if ok72(j, e_t + 1): ct.append((j, e_t))

# ---- clues (as fib_trend_v1.py features)
LV = (.618, 1.0)
def cross(px, start, h, l):
    if len(h) < 20: return np.nan
    Hh, Ll = np.nanmax(h), np.nanmin(l)
    if not (Hh > Ll > 0) or not np.isfinite(start): return np.nan
    a, b = (start - Ll) / (Hh - Ll), (px - Ll) / (Hh - Ll); return float(any(a < v <= b for v in LV))
def clues(i, tt):
    s = syms[i]; px, start = C[i, tt], C[i, tt - 3]; day = grid[tt].normalize()
    f = dict(above_count=np.nan, stack=np.nan, res200_dist=np.nan, sma100_dist=np.nan, fib200=np.nan, fib50=np.nan)
    if s not in daily: return f
    dd, dh, dl, dc = daily[s]; k = np.searchsorted(dd, np.datetime64(day.tz_convert(None)), side="left")
    dh, dl, dc = dh[:k], dl[:k], dc[:k]
    sm = {n: (dc[-n:].mean() if len(dc) >= n else np.nan) for n in NS}
    if np.isfinite(sm[200]):
        f["above_count"] = float(sum(px > sm[n] for n in NS if np.isfinite(sm[n]))); f["stack"] = float(sm[11] > sm[21] > sm[50] > sm[100] > sm[200])
    if np.isfinite(sm[100]): f["sma100_dist"] = px / sm[100] - 1
    if len(dh) >= 200: f["res200_dist"] = px / dh[-200:].max() - 1; f["fib200"] = cross(px, start, dh[-200:], dl[-200:])
    f["fib50"] = cross(px, start, dh[-50:], dl[-50:])
    return f
def score(f):
    return int((f["above_count"] >= 5) + (f["stack"] == 1) + (f["res200_dist"] >= -0.15) + (f["sma100_dist"] >= 0.5) + (f["fib200"] == 1) + (f["fib50"] == 1))

# ---- exits
def exits(i, e):
    ent = O[i, e]; r = {}
    if not (np.isfinite(ent) and ent > 0): return None
    entc = ent * (1 + COST); out = lambda x: x * (1 - COST) / entc - 1
    def win(n):
        if e + n > T: return None
        c = C[i, e:e + n]
        return None if np.isfinite(c).sum() < .9 * n else (H[i, e:e + n], pd.Series(c).ffill().values)
    w = win(336)
    if w is None: return None
    hh, cf = w; r["X4"] = next((out(ent * 1.5) for k in range(336) if np.isfinite(hh[k]) and hh[k] >= ent * 1.5), out(cf[335]))
    w7 = win(168)
    if w7:
        hh7, cf7 = w7; r["hold7d"] = out(cf7[167])
        rr = np.nan
        for k in range(168):
            if cf7[k] <= ent * .85: rr = 0.0; break
            if np.isfinite(hh7[k]) and hh7[k] >= ent * 1.3: rr = 1.0; break
        r["runner"] = 0.0 if np.isnan(rr) else rr
    w30 = win(720)
    if w30:
        hh3, cf3 = w30; r["reach100"] = float(np.nanmax(hh3) / entc - 1 >= 1); pk = ent; v = out(cf3[-1])
        for k in range(720):
            if np.isfinite(hh3[k]): pk = max(pk, hh3[k])
            if cf3[k] <= pk * .7:
                nx = O[i, e + k + 1] if e + k + 1 < T else np.nan; v = out(nx if np.isfinite(nx) else cf3[k]); break
        r["X5_trail30"] = v
    return r
fng = pd.DataFrame(json.load(open(os.path.join(ROOT, "raw", "fng_alternative_me.json")))["data"])
fng["date"] = pd.to_datetime(fng.timestamp.astype("int64"), unit="s", utc=True).dt.normalize(); fng = fng.set_index("date")["value"].astype(int)
rows = []
for kind, lst in [("event", [(i, e) for i, e, s in ev if s == "OK"]), ("control", ct)]:
    for i, e_t in lst:
        f = clues(i, e_t); x = exits(i, e_t + 1)
        prevd = grid[e_t].normalize() - pd.Timedelta(days=1)
        rows.append(dict(kind=kind, sym=syms[i], trigger_hour=str(grid[e_t]), year=grid[e_t].year, score=score(f),
                         fng_prev=float(fng.get(prevd, np.nan)), status="OK" if x else "NO_336H_WINDOW", **f, **(x or {})))
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUT, "holdout_trades.csv"), index=False)

# ---- verdict
rb = np.random.default_rng(2023)
def boot(d, B=2000):
    g = {k: v.X4.values for k, v in d.groupby(d.trigger_hour.str[:10])}; days = list(g)
    return np.array([np.concatenate([g[k] for k in rb.choice(days, len(days))]).mean() for _ in range(B)]) if days else np.array([np.nan])
def verdict(sel_e, sel_r, name):
    e = R[sel_e & (R.status == "OK")]; r_ = R[sel_r & (R.status == "OK")]
    o = dict(version=name, n=int(len(e)), n_no_window=int((sel_e & (R.status != "OK")).sum()), random_n=int(len(r_)))
    if len(e) == 0: o["verdict"] = "INCONCLUSIVE (0 trades)"; return o
    be, br = boot(e), boot(r_) if len(r_) else np.array([np.nan])
    v = e.X4.sort_values(ascending=False)
    o.update(mean=round(float(e.X4.mean()), 4), mean_ci95=[round(float(np.percentile(be, 2.5)), 4), round(float(np.percentile(be, 97.5)), 4)],
             median=round(float(e.X4.median()), 4), pct_profit=round(float((e.X4 > 0).mean()), 3),
             random_mean=round(float(r_.X4.mean()), 4) if len(r_) else None,
             diff_vs_random=round(float(e.X4.mean() - r_.X4.mean()), 4) if len(r_) else None,
             diff_lb95=round(float(np.percentile(be - br, 2.5)), 4) if len(r_) else None,
             top5_share=round(float(v.head(5).sum() / v.sum()), 3) if v.sum() != 0 else None,
             mean_without_top5=round(float(v.iloc[5:].mean()), 4) if len(v) > 5 else None,
             by_year={int(y): dict(n=int(len(g)), mean=round(float(g.X4.mean()), 4), median=round(float(g.X4.median()), 4)) for y, g in e.groupby("year")},
             secondary=dict(hold7d=round(float(e.hold7d.mean()), 4) if "hold7d" in e else None, runner=round(float(e.runner.mean()), 3) if "runner" in e else None,
                            reach100=round(float(e.reach100.mean()), 3) if "reach100" in e else None, X5_trail30=round(float(e.X5_trail30.mean()), 4) if "X5_trail30" in e else None))
    c1 = o["mean"] > 0 and o["mean_ci95"][0] > 0; c2 = o["median"] > 0
    c3 = o["diff_vs_random"] is not None and o["diff_vs_random"] > 0 and o["diff_lb95"] > -0.02
    c4 = o["n"] >= 30 and not any(v["n"] >= 10 and v["mean"] < -0.10 for v in o["by_year"].values())
    o["criteria"] = dict(mean_and_lb_positive=bool(c1), median_positive=bool(c2), beats_random=bool(c3), n30_and_no_bad_year=bool(c4))
    o["verdict"] = "PASS" if all([c1, c2, c3, c4]) else ("INCONCLUSIVE (<30 trades)" if o["n"] < 30 else "FAIL")
    return o
greed = R.fng_prev >= 55
res = dict(protocol="PROTOCOL_COMBO_HOLDOUT_v1.md @ GitHub ac14151", log=log,
           events_total=len(ev), events_no_outcome=sum(1 for _, _, s in ev if s != "OK"), controls_total=len(ct),
           all_ignitions=dict(n=int(((R.kind == "event") & (R.status == "OK")).sum()), X4_mean=round(float(R[(R.kind == "event") & (R.status == "OK")].X4.mean()), 4)),
           all_random=dict(n=int(((R.kind == "control") & (R.status == "OK")).sum()), X4_mean=round(float(R[(R.kind == "control") & (R.status == "OK")].X4.mean()), 4)),
           version_A=verdict((R.kind == "event") & (R.score >= 4), (R.kind == "control") & (R.score >= 4), "A"),
           version_B=verdict((R.kind == "event") & (R.score >= 4) & greed, (R.kind == "control") & (R.score >= 4) & greed, "B"),
           script_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest())
json.dump(res, open(os.path.join(OUT, "RESULT_COMBO_HOLDOUT_v1.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))

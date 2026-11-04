"""PSYCH_v1  (funding buckets per 24h sum: <-0.01% negative; -0.01..0.04% baseline (Binance default 0.01%/8h); 0.04..0.15% positive; >0.15% high)
PSYCH_v1 — do crowd-psychology measures change how our candidate moves behave? (exploratory, 2026-11-03)
All data previously seen. Descriptive only; no rule is selected here.
A. Crowd mood (prior-day Fear & Greed) vs the anatomy of hourly ignitions (peak size, time to peak, give-back, TP hit).
B. Crowding at the trigger (perp funding in the 24h before): crowded shorts (negative) vs crowded longs (high positive).
C. Same crowding measure for the daily spike shorts of BEAR_v1 (perp mode): where do squeezes come from?
"""
import glob, io, json, os, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RS = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
res = {}
# ---- ignitions (V0 rows carry anatomy + baseline trade)
T = pd.concat([pd.read_csv(os.path.join(RS, f"entry_timing_v1/out/trades_{p}.csv"), low_memory=False) for p in ("disc", "hold")])
T = T[(T.kind == "ignition") & (T.variant == "V0_NEXT_OPEN") & (T.status == "TRADE")].copy()
T["ts"] = pd.to_datetime(T.ts, utc=True)
T["period"] = np.where(T.year <= 2021, "2020-21", np.where(T.year == 2022, "2022", "2023-26"))
T["giveback"] = T.peak336 - T.net  # rough: how much of the peak was not kept by the fixed exit
fng = pd.DataFrame(json.load(open(os.path.join(RS, "ignition_v0/raw/fng_alternative_me.json")))["data"])
fng["d"] = pd.to_datetime(fng.timestamp.astype("int64"), unit="s", utc=True).dt.normalize(); fng = fng.set_index("d")["value"].astype(int)
T["fng_prev"] = (T.ts.dt.normalize() - pd.Timedelta(days=1)).map(fng)
T["mood"] = pd.cut(T.fng_prev, [-1, 24, 45, 55, 75, 101], labels=["ExtremeFear", "Fear", "Neutral", "Greed", "ExtremeGreed"])
def anat(g):
    return dict(n=int(len(g)), peak_med=round(g.peak336.median() * 100, 1), peak50_share=round((g.peak336 >= .5).mean() * 100),
                hrs_to_peak_med=float(g.hours_to_peak.median()), dip72_med=round(g.dip72.median() * 100, 1),
                tp_hit=round(g.tp.mean() * 100), net_mean=round(g.net.mean() * 100, 1), net_med=round(g.net.median() * 100, 1))
res["A_mood_all_periods"] = {str(k): anat(g) for k, g in T.groupby("mood", observed=True)}
res["A_mood_by_period"] = {f"{p}|{k}": anat(g) for (p, k), g in T.groupby(["period", "mood"], observed=True) if len(g) >= 20}
res["A_mood_trend_subset"] = {str(k): anat(g) for k, g in T[T.trend == True].groupby("mood", observed=True)}

# ---- funding (8h/4h rates); daily sums and "last 24h before t" sums
rows = []
syms = set(T.sym)
ev = pd.read_csv(os.path.join(RS, "bear_v1/out/events_perp.csv")); syms |= set(ev.sym)
for fp in glob.glob(os.path.join(RS, "bear_v1/raw_funding/*.zip")):
    s = os.path.basename(fp).split("-fundingRate-")[0]
    if s not in syms: continue
    with zipfile.ZipFile(fp) as z: df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
    df = df.rename(columns={"calc_time": "t", "last_funding_rate": "rate"})[["t", "rate"]]; df["sym"] = s; rows.append(df)
F = pd.concat(rows); F["ts"] = pd.to_datetime(F.t.astype("int64"), unit="ms", utc=True); F = F.sort_values(["sym", "ts"])
FS = {s: (g.ts.values, g.rate.values.astype(float)) for s, g in F.groupby("sym")}
def fund24(s, t):
    if s not in FS: return np.nan
    ts, r = FS[s]; t = np.datetime64(t.tz_convert(None)) if hasattr(t, "tz_convert") else np.datetime64(t)
    m = (ts <= t) & (ts > t - np.timedelta64(24, "h"))
    return r[m].sum() if m.any() else np.nan
T["fund24"] = [fund24(s, t) for s, t in zip(T.sym, T.ts)]
def fb(x):
    return pd.cut(x, [-10, -0.0001, 0.0004, 0.0015, 10], labels=["neg(shorts crowded)", "neutral", "positive", "high(longs crowded)"])
T["crowd"] = fb(T.fund24)
res["B_funding_coverage"] = dict(ignitions=int(len(T)), with_perp_funding=int(T.fund24.notna().sum()))
res["B_crowding_ignitions"] = {str(k): anat(g) for k, g in T.groupby("crowd", observed=True)}
res["B_crowding_by_period"] = {f"{p}|{k}": anat(g) for (p, k), g in T.groupby(["period", "crowd"], observed=True) if len(g) >= 20}
res["B_crowding_x_mood"] = {f"{m}|{k}": anat(g) for (m, k), g in T.groupby(["mood", "crowd"], observed=True) if len(g) >= 30}

# ---- C: daily spike shorts (perp mode events; spike day d, short from d+1 open) — funding through the spike day close
ev = ev[ev.arm == "F_ALL_SPIKES"].copy(); ev["d"] = pd.to_datetime(ev.d, utc=True)
ev["fund24"] = [fund24(s, d + pd.Timedelta(hours=24)) for s, d in zip(ev.sym, ev.d)]
ev["crowd"] = fb(ev.fund24)
def sh(g):
    x = g.r.dropna()
    return dict(n=int(len(x)), mean=round(x.mean() * 100, 1), median=round(x.median() * 100, 1), win=round((x > 0).mean() * 100),
                loss_over_50pct=int((x <= -.5).sum()), worst=round(x.min() * 100))
res["C_spike_shorts_by_crowding"] = {str(k): sh(g) for k, g in ev.groupby("crowd", observed=True)}
res["C_spike_shorts_all"] = sh(ev)
T.to_csv(os.path.join(OUT, "ignitions_with_psych.csv"), index=False)
json.dump(res, open(os.path.join(OUT, "RESULT_psych_v1.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))

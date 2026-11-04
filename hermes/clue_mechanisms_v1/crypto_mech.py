"""CLUE_MECHANISMS_v1 crypto part (see PLAN.md). Exploratory; all periods previously seen."""
import glob, io, json, os, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
IG = os.path.join(os.path.dirname(HERE), "ignition_v0")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
COST = 0.003
res = {}

# ---------------- H1 on hourly ignitions (2020-22, scan_v0 outputs)
ev = pd.read_csv(os.path.join(IG, "out/events_v0.csv")); ev = ev[ev.status == "OK"] if "status" in ev else ev
ct = pd.read_csv(os.path.join(IG, "out/controls_v0.csv"))
def h1(d):
    d = d.dropna(subset=["mfe72", "mae72"])
    return dict(n=len(d), up30=round((d.mfe72 >= .30).mean(), 4), up20=round((d.mfe72 >= .20).mean(), 4),
                down20=round((d.mae72 <= -.20).mean(), 4), down30=round((d.mae72 <= -.30).mean(), 4),
                both20=round(((d.mfe72 >= .2) & (d.mae72 <= -.2)).mean(), 4),
                med_range=round((d.mfe72 - d.mae72).median(), 4))
res["H1_hourly_ignition_72h"] = {"events": h1(ev), "controls": h1(ct)}

# ---------------- daily panel
uni = set(json.load(open(os.path.join(IG, "raw/universe.json")))["universe"]) if isinstance(json.load(open(os.path.join(IG, "raw/universe.json"))), dict) else set(json.load(open(os.path.join(IG, "raw/universe.json"))))
uh = json.load(open(os.path.join(IG, "raw_holdout/universe_holdout.json")))["universe"]; uni |= set(uh)
fr = []
for fp in glob.glob(os.path.join(IG, "raw/k1d/*.zip")) + glob.glob(os.path.join(IG, "raw_holdout/k1d/*.zip")):
    s = os.path.basename(fp).split("-1d-")[0]
    if s not in uni: continue
    try:
        with zipfile.ZipFile(fp) as z: df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
        if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
        df = df.iloc[:, [0, 1, 2, 3, 4, 7]].astype(float); df.columns = ["t", "o", "h", "l", "c", "qv"]
        t = df.t.values.astype("int64"); df["t"] = np.where(t > 1e14, t // 1000, t); df["sym"] = s; fr.append(df)
    except Exception: pass
p = pd.concat(fr); p["d"] = pd.to_datetime(p.t.astype("int64"), unit="ms").dt.normalize()
p = p[(p.d >= "2017-08-01") & (p.d <= "2026-10-31")].drop_duplicates(["sym", "d"])
W = {k: p.pivot(index="d", columns="sym", values=k).sort_index() for k in ["o", "h", "l", "c", "qv"]}
O, H, L, C, QV = (W[k] for k in ["o", "h", "l", "c", "qv"])
days = C.index; full = pd.date_range(days.min(), days.max(), freq="D"); O, H, L, C, QV = (x.reindex(full) for x in (O, H, L, C, QV)); days = full
print("daily panel", C.shape, days.min().date(), days.max().date())
R = C.pct_change(fill_method=None)
age = C.notna().cumsum()
medqv = QV.rolling(20, min_periods=15).median().shift(1)        # known before day t
elig = (medqv >= 1e6) & (age.shift(1) >= 200) & C.shift(1).notna()
s50, s200 = C.rolling(50).mean(), C.rolling(200).mean()
hi200 = H.rolling(200).max()
trend = (C > s50) & (C > s200) & (s50 > s200) & (C >= 0.75 * hi200)      # state at close of day t
breadth = (C > s50).where(elig.shift(-1, fill_value=False) | elig).sum(1) / (elig.sum(1).replace(0, np.nan))
BTC = C["BTCUSDT"]
res["panel"] = dict(symbols=int(C.shape[1]), start=str(days.min().date()), end=str(days.max().date()))

# ---------------- daily +30% events (close-to-close), eligible, entry next-day open
spike = (R >= 0.30) & elig
Cv, Ov, Hv, Lv = C.values, O.values, H.values, L.values
eligv = elig.values
ew = R.where(elig).mean(1)                                      # equal-weight eligible daily return
ewc = (1 + ew.fillna(0)).cumprod().values
rows = []
si, sj = np.where(spike.values)
syms = list(C.columns)
for i, j in zip(si, sj):
    if i + 31 >= len(days): continue
    e = Ov[i + 1, j]
    if not np.isfinite(e) or e <= 0: continue
    r = {"sym": syms[j], "d": days[i], "year": days[i].year, "spike": R.values[i, j],
         "trend": bool(trend.values[i - 1, j]) if i > 0 else False,   # trend BEFORE the spike day
         "liq": medqv.values[i, j], "run30": Cv[i - 1, j] / Cv[i - 31, j] - 1 if i > 31 else np.nan,
         "breadth": breadth.values[i], "btc_up": bool(BTC.values[i] > s200["BTCUSDT"].values[i]),
         "hold_d2": bool(Cv[i + 1, j] >= Cv[i, j]) if np.isfinite(Cv[i + 1, j]) else np.nan}
    for k in [5, 10, 20, 30]:
        x = Cv[i + k, j]
        r[f"ret{k}"] = x / e - 1 if np.isfinite(x) else np.nan
        r[f"mkt{k}"] = ewc[i + k] / ewc[i] - 1
        r[f"abn{k}"] = r[f"ret{k}"] - r[f"mkt{k}"]
    seg = slice(i + 1, i + 31)
    r["mfe30"] = np.nanmax(Hv[seg, j]) / e - 1; r["mae30"] = np.nanmin(Lv[seg, j]) / e - 1
    rows.append(r)
E = pd.DataFrame(rows); E.to_csv(os.path.join(OUT, "crypto_daily_spikes.csv"), index=False)
# random eligible coin-days as controls (5 per spike date, no future-based exclusion)
rng = np.random.default_rng(20261103); crow = []
for i in np.unique(si):
    if i + 31 >= len(days): continue
    cand = np.where(eligv[i] & ~spike.values[i])[0]
    for j in rng.choice(cand, min(5, len(cand)), replace=False):
        e = Ov[i + 1, j]
        if not np.isfinite(e) or e <= 0: continue
        seg = slice(i + 1, i + 31); x = Cv[i + 20, j]
        crow.append({"year": days[i].year, "ret20": x / e - 1 if np.isfinite(x) else np.nan,
                     "abn20": (x / e - 1) - (ewc[i + 20] / ewc[i] - 1) if np.isfinite(x) else np.nan,
                     "mfe30": np.nanmax(Hv[seg, j]) / e - 1, "mae30": np.nanmin(Lv[seg, j]) / e - 1})
Cn = pd.DataFrame(crow)
def h1d(d): return dict(n=len(d), up30=round((d.mfe30 >= .3).mean(), 4), down30=round((d.mae30 <= -.3).mean(), 4),
                        both30=round(((d.mfe30 >= .3) & (d.mae30 <= -.3)).mean(), 4))
res["H1_daily_spike_30d"] = {"spikes": h1d(E), "random": h1d(Cn)}

def summ(d, col="abn20"):
    x = d[col].dropna()
    if len(x) < 5: return dict(n=int(len(x)))
    return dict(n=int(len(x)), mean=round(x.mean(), 4), median=round(x.median(), 4), pos=round((x > 0).mean(), 3))
H2 = {"all_abn5": summ(E, "abn5"), "all_abn10": summ(E, "abn10"), "all_abn20": summ(E, "abn20"), "all_abn30": summ(E, "abn30"),
      "all_raw20": summ(E, "ret20"), "random_abn20": summ(Cn, "abn20"), "random_raw20": summ(Cn, "ret20")}
H2["by_year"] = {int(y): summ(g) for y, g in E.groupby("year")}
H2["trend_before"] = {str(k): summ(g) for k, g in E.groupby("trend")}
H2["spike_size"] = {str(k): summ(g) for k, g in E.groupby(pd.cut(E.spike, [.3, .5, 1, 100]), observed=True)}
H2["liquidity_q"] = {str(k): summ(g) for k, g in E.groupby(pd.qcut(E.liq, 4), observed=True)}
H2["prior_run30_q"] = {str(k): summ(g) for k, g in E.groupby(pd.qcut(E.run30, 4), observed=True)}
H2["held_day2"] = {str(k): summ(g) for k, g in E.groupby("hold_d2")}
H2["btc_above_sma200"] = {str(k): summ(g) for k, g in E.groupby("btc_up")}
H2["breadth"] = {str(k): summ(g) for k, g in E.groupby(pd.cut(E.breadth, [0, .3, .5, .7, 1]), observed=True)}
H2["trend_x_breadth50"] = {f"trend={a},breadth>=0.5={b}": summ(g) for (a, b), g in E.groupby([E.trend, E.breadth >= .5])}
H2["trend_x_heldday2"] = {f"trend={a},held={b}": summ(g) for (a, b), g in E.groupby([E.trend, E.hold_d2])}
res["H2_daily_spike_decay"] = H2

# ---------------- H3/H4 weekly baskets (decide on Sunday close, hold next 7 days: Mon open ~ Sun close in 24/7 market)
reb = [d for d in days if d.weekday() == 6 and d >= pd.Timestamp("2018-03-04")]
spk20 = (R >= 0.30).rolling(20, min_periods=1).max().astype(bool)
basket_defs = {
    "ALL": lambda i: elig.iloc[i + 1] if i + 1 < len(days) else elig.iloc[i],
}
def weights(name, d):
    i = days.get_loc(d); e = elig.iloc[i + 1] & C.iloc[i].notna()
    if name == "ALL": m = e
    elif name == "NO_SPIKERS": m = e & ~spk20.iloc[i]
    elif name == "TREND": m = e & trend.iloc[i]
    elif name == "TREND_NO_SPIKERS": m = e & trend.iloc[i] & ~spk20.iloc[i]
    elif name == "TREND_NO_SPIKERS_GATED": m = (e & trend.iloc[i] & ~spk20.iloc[i]) if breadth.iloc[i] >= .5 else e & False
    elif name == "ALL_GATED": m = e if breadth.iloc[i] >= .5 else e & False
    elif name == "BTC": m = pd.Series(False, index=C.columns); m["BTCUSDT"] = True
    elif name == "BTC_GATED_SMA200": m = pd.Series(False, index=C.columns); m["BTCUSDT"] = bool(BTC.iloc[i] > s200["BTCUSDT"].iloc[i])
    m = m[m].index
    return pd.Series(1.0 / len(m), index=m) if len(m) else pd.Series(dtype=float)
names = ["ALL", "NO_SPIKERS", "TREND", "TREND_NO_SPIKERS", "ALL_GATED", "TREND_NO_SPIKERS_GATED", "BTC", "BTC_GATED_SMA200"]
wk = []; prev = {n: pd.Series(dtype=float) for n in names}; npos = {n: [] for n in names}
for a, b in zip(reb[:-1], reb[1:]):
    ia, ib = days.get_loc(a), days.get_loc(b)
    gross = C.iloc[ib] / C.iloc[ia] - 1
    # coins that stop trading inside the week: use last available close (delisting losses partly captured)
    lastc = C.iloc[ia:ib + 1].ffill().iloc[-1]; gross = gross.fillna(lastc / C.iloc[ia] - 1)
    row = {"start": a}
    for n in names:
        w = weights(n, a); npos[n].append(len(w))
        turn = w.subtract(prev[n], fill_value=0).abs().sum()
        row[n] = float((w * gross.reindex(w.index).fillna(0)).sum() - COST * turn) if len(w) or len(prev[n]) else 0.0
        drift = (w * (1 + gross.reindex(w.index).fillna(0))); prev[n] = drift / drift.sum() if drift.sum() > 0 else w
    wk.append(row)
WK = pd.DataFrame(wk).set_index("start"); WK.to_csv(os.path.join(OUT, "crypto_weekly_baskets.csv"))
def stats(x):
    x = x.dropna(); eq = (1 + x).cumprod(); yrs = len(x) / 52.18
    return dict(weeks=len(x), cagr=round(eq.iloc[-1] ** (1 / yrs) - 1, 3) if yrs > 0 else None,
                total=round(eq.iloc[-1] - 1, 3), sharpe=round(x.mean() / x.std() * np.sqrt(52.18), 2) if x.std() > 0 else None,
                maxdd=round((eq / eq.cummax() - 1).min(), 3), in_market=round((x != 0).mean(), 2))
periods = {"2018-19": ("2018", "2019"), "2020-21": ("2020", "2021"), "2022": ("2022", "2022"), "2023-24": ("2023", "2024"),
           "2025-26": ("2025", "2026"), "ALL": ("2018", "2026")}
res["H3H4_weekly_baskets"] = {pn: {n: stats(WK.loc[a:b, n]) for n in names} for pn, (a, b) in periods.items()}
res["H3H4_avg_positions"] = {n: round(float(np.mean(v)), 1) for n, v in npos.items()}
json.dump(res, open(os.path.join(OUT, "crypto_results.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))

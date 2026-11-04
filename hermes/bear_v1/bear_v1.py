"""BEAR_v1 (see PLAN.md). Exploratory. Daily Binance spot data; optional perp funding from raw_funding/."""
import glob, io, json, os, sys, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); IG = os.path.join(os.path.dirname(HERE), "ignition_v0")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
COST, CARRY = 0.003, 0.0003
MODE = sys.argv[1] if len(sys.argv) > 1 else "proxy"   # proxy | perp

def read_zip(fp, cols):
    with zipfile.ZipFile(fp) as z: df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).lstrip("-").isdigit(): df = df.iloc[1:]
    df = df.iloc[:, cols].astype(float); t = df.iloc[:, 0].values.astype("int64"); df.iloc[:, 0] = np.where(t > 1e14, t // 1000, t); return df

u1 = json.load(open(os.path.join(IG, "raw/universe.json"))); u1 = u1["usdt_universe"] if isinstance(u1, dict) else u1
uni = set(u1) | set(json.load(open(os.path.join(IG, "raw_holdout/universe_holdout.json")))["universe"])
fr = []
for fp in glob.glob(os.path.join(IG, "raw/k1d/*.zip")) + glob.glob(os.path.join(IG, "raw_holdout/k1d/*.zip")):
    s = os.path.basename(fp).split("-1d-")[0]
    if s not in uni: continue
    try:
        d = read_zip(fp, [0, 1, 2, 3, 4, 7]); d.columns = ["t", "o", "h", "l", "c", "qv"]; d["sym"] = s; fr.append(d)
    except Exception: pass
p = pd.concat(fr); del fr; p["d"] = pd.to_datetime(p.t.astype("int64"), unit="ms").dt.normalize()
p = p[(p.d >= "2017-08-01") & (p.d <= "2026-10-31")].drop_duplicates(["sym", "d"])
days = pd.date_range(p.d.min(), p.d.max(), freq="D")
O, H, L, C, QV = (p.pivot(index="d", columns="sym", values=k).reindex(days) for k in ["o", "h", "l", "c", "qv"]); del p
syms = list(C.columns); print("panel", C.shape, days[0].date(), days[-1].date(), flush=True)

R = C.pct_change(fill_method=None)
medqv = QV.rolling(20, min_periods=15).median()
age = C.notna().cumsum()
elig = (medqv >= 1e6) & (age >= 200) & C.notna()                 # state at close of day t (use for decisions after t)
s50, s200 = C.rolling(50).mean(), C.rolling(200).mean(); h200 = H.rolling(200).max()
lead = (C > s50) & (C > s200) & (C >= 0.85 * h200)
weak = (C < s50) & (s50 < s200) & (C <= 0.60 * h200) & (C / C.shift(20) - 1 < 0)
breadth = ((C > s50) & elig).sum(1) / elig.sum(1).replace(0, np.nan)
btc = C["BTCUSDT"]; bear = (btc < btc.rolling(200).mean()); altbear = breadth < 0.35
spk20 = (R >= 0.30).rolling(20, min_periods=1).max().fillna(0).astype(bool)
rel30 = (C / C.shift(30)).div(btc / btc.shift(30), axis=0) - 1
fng = pd.DataFrame(json.load(open(os.path.join(IG, "raw/fng_alternative_me.json")))["data"])
fng["d"] = pd.to_datetime(fng.timestamp.astype("int64"), unit="s").dt.normalize(); fng = fng.set_index("d")["value"].astype(int).reindex(days)

# ---- perp availability + funding (daily sum of 8h rates; positive = longs pay shorts)
perp_ok = None; fund = None
if MODE == "perp":
    rows = []
    for fp in glob.glob(os.path.join(HERE, "raw_funding/*.zip")):
        s = os.path.basename(fp).split("-fundingRate-")[0]
        if s not in C.columns: continue
        try:
            d = read_zip(fp, [0, 2]); d.columns = ["t", "rate"]; d["sym"] = s; rows.append(d)
        except Exception: pass
    F = pd.concat(rows); F["d"] = pd.to_datetime(F.t.astype("int64"), unit="ms").dt.normalize()
    fund = F.groupby(["d", "sym"]).rate.sum().unstack().reindex(days)
    first = F.groupby("sym").d.min(); perp_ok = pd.DataFrame(False, index=days, columns=C.columns)
    for s, d0 in first.items(): perp_ok.loc[d0:, s] = True
    print("funding symbols", fund.shape[1], "rows", len(F), flush=True)

def era(d): return "2018-20" if d.year <= 2020 else ("2021-23" if d.year <= 2023 else "2024-26")

# ---- weekly baskets
reb = [d for d in days if d.weekday() == 6 and d >= pd.Timestamp("2018-03-04")]
def basket(name, d):
    e = elig.loc[d].copy(); e["BTCUSDT"] = False
    sh = (perp_ok.loc[d] if perp_ok is not None else True)
    if name == "L_BTC": return pd.Series({"BTCUSDT": 1.0})
    if name == "L_ALTS": m = e
    elif name == "S_ALTS": m = e & sh
    elif name == "S_WEAK": m = e & weak.loc[d] & sh
    elif name == "L_LEADERS": m = e & lead.loc[d]
    elif name == "L_RS":
        x = rel30.loc[d][e & (C.loc[d] > s50.loc[d])].dropna()
        m = pd.Series(False, index=C.columns); m[x[x >= x.quantile(.9)].index] = True if len(x) >= 10 else False
    elif name == "S_SPIKERS": m = e & spk20.loc[d] & ~lead.shift(1, fill_value=False).loc[d] & sh
    elif name == "LS_LEADERS_WEAK":
        a, b = basket("L_LEADERS", d), basket("S_WEAK", d)
        if len(a) == 0 or len(b) == 0: return pd.Series(dtype=float)
        return pd.concat([a * .5, -b.abs() * .5]).groupby(level=0).sum()
    m = m[m.fillna(False).astype(bool)].index
    if len(m) == 0: return pd.Series(dtype=float)
    sgn = -1.0 if name.startswith("S_") else 1.0
    return pd.Series(sgn / len(m), index=m)
ARMS = ["L_BTC", "L_ALTS", "S_ALTS", "S_WEAK", "L_LEADERS", "L_RS", "S_SPIKERS", "LS_LEADERS_WEAK"]
wk = []
for regime_name, reg in (("BEAR_btc_sma200", bear), ("ALT_BEAR_breadth35", altbear)):
    prev = {n: pd.Series(dtype=float) for n in ARMS}
    for a, b in zip(reb[:-1], reb[1:]):
        if not bool(reg.loc[a]):
            prev = {n: pd.Series(dtype=float) for n in ARMS}; continue
        ia, ib = days.get_loc(a), days.get_loc(b)
        px0 = C.iloc[ia]; px1 = C.iloc[ia:ib + 1].ffill().iloc[-1]; g = px1 / px0 - 1   # stopped coins: last close
        row = dict(regime=regime_name, start=a, era=era(a), breadth=round(float(breadth.loc[a]), 3))
        for n in ARMS:
            w = basket(n, a)
            if len(w) == 0: row[n] = 0.0; row[n + "_n"] = 0; prev[n] = pd.Series(dtype=float); continue
            gr = g.reindex(w.index).fillna(0)
            turn = float(w.subtract(prev[n], fill_value=0).abs().sum())          # entry from cash = full turnover
            r = float((w * gr).sum()) - COST * turn
            dr = w * (1 + gr); prev[n] = dr / dr.abs().sum() * w.abs().sum() if dr.abs().sum() > 0 else w
            short_w = -w[w < 0]
            if len(short_w):
                if fund is not None: r += float((short_w * fund.iloc[ia + 1:ib + 1].reindex(columns=short_w.index).sum()).sum())
                else: r -= CARRY * 7 * short_w.sum()
            row[n] = r; row[n + "_n"] = int(len(w))
        wk.append(row)
WK = pd.DataFrame(wk); WK.to_csv(os.path.join(OUT, f"weekly_{MODE}.csv"), index=False)

def st(x):
    x = pd.Series(x).dropna()
    if len(x) == 0: return dict(n=0)
    eq = (1 + x).cumprod()
    return dict(n=int(len(x)), mean=round(x.mean(), 4), median=round(x.median(), 4), pos=round((x > 0).mean(), 3),
                worst=round(x.min(), 3), best=round(x.max(), 3), compounded=round(eq.iloc[-1] - 1, 3), maxdd=round((eq / eq.cummax() - 1).min(), 3))
res = {"mode": MODE, "panel": [int(C.shape[1]), str(days[0].date()), str(days[-1].date())],
       "bear_weeks": {r: {e: int(len(g)) for e, g in WK[WK.regime == r].groupby("era")} for r in WK.regime.unique()}}
res["weekly"] = {r: {e: {n: st(g[n]) for n in ARMS} | {"avg_names": {n: round(g[n + "_n"].mean(), 1) for n in ARMS}}
                     for e, g in list(WK[WK.regime == r].groupby("era")) + [("ALL", WK[WK.regime == r])]} for r in WK.regime.unique()}

# ---- event arms (BEAR regime at the event day close)
Cv, Ov = C.values, O.values; ev = []
def trade_short(j, i0, hold=10, stop=.30):
    e = Ov[i0, j]
    if not (np.isfinite(e) and e > 0): return None
    for k in range(i0, min(len(days) - 1, i0 + hold)):
        c = Cv[k, j]
        if np.isfinite(c) and c >= e * (1 + stop):
            x = Ov[k + 1, j] if np.isfinite(Ov[k + 1, j]) else c
            return -(x / e - 1) - 2 * COST - CARRY * (k + 1 - i0)
    k = min(len(days) - 1, i0 + hold - 1); c = pd.Series(Cv[i0:k + 1, j]).ffill().iloc[-1]
    if not np.isfinite(c): return None
    f = float(fund.iloc[i0:k + 1][syms[j]].sum()) if fund is not None and syms[j] in fund else -CARRY * hold
    return -(c / e - 1) - 2 * COST + f
def trade_long(j, i0, hold):
    e = Ov[i0, j]
    if not (np.isfinite(e) and e > 0) or i0 + hold > len(days): return None
    c = pd.Series(Cv[i0:i0 + hold, j]).ffill().iloc[-1]
    return c / e - 1 - 2 * COST if np.isfinite(c) else None
spk = ((R >= .30) & elig).values; leadv = lead.values; bearv = bear.values; ok_short = perp_ok.values if perp_ok is not None else None
for i, j in zip(*np.where(spk)):
    if i < 1 or i + 13 >= len(days) or not bearv[i] or leadv[i - 1, j]: continue
    if ok_short is not None and not ok_short[i, j]: continue
    r_all = trade_short(j, i + 1)
    if r_all is not None: ev.append(dict(arm="F_ALL_SPIKES", d=days[i], era=era(days[i]), sym=syms[j], r=r_all))
    if np.isfinite(Cv[i + 1, j]) and Cv[i + 1, j] < Cv[i, j]:
        r = trade_short(j, i + 2)
        if r is not None: ev.append(dict(arm="F_FAILED_SPIKE", d=days[i], era=era(days[i]), sym=syms[j], r=r))
jb = syms.index("BTCUSDT"); last = -99
for i in range(1, len(days) - 21):
    if bearv[i] and np.isfinite(fng.iloc[i]) and fng.iloc[i] <= 15 and i - last >= 10:
        last = i
        for hold in (10, 20):
            r = trade_long(jb, i + 1, hold)
            if r is not None: ev.append(dict(arm=f"B_FEAR_BTC_{hold}d", d=days[i], era=era(days[i]), sym="BTCUSDT", r=r))
drop3 = (C / C.shift(3) - 1).values; lastj = {}
for i in range(4, len(days) - 11):
    if not bearv[i]: continue
    for j in np.where(leadv[i - 3] & (drop3[i] <= -0.20) & elig.values[i])[0]:
        if i - lastj.get(j, -99) < 10: continue
        lastj[j] = i; r = trade_long(j, i + 1, 10)
        if r is not None: ev.append(dict(arm="B_LEADER_DIP", d=days[i], era=era(days[i]), sym=syms[j], r=r))
alt_ew = (1 + R.where(elig).drop(columns="BTCUSDT").mean(1).fillna(0)).cumprod(); last = -99
for i in range(1, len(days) - 21):
    if bearv[i] and breadth.iloc[i] <= .10 and i - last >= 20:
        last = i; ev.append(dict(arm="B_CAPITULATION_20d", d=days[i], era=era(days[i]), sym="ALT_EW", r=float(alt_ew.iloc[i + 20] / alt_ew.iloc[i] - 1 - 2 * COST)))
EV = pd.DataFrame(ev); EV.to_csv(os.path.join(OUT, f"events_{MODE}.csv"), index=False)
res["events"] = {a: {e: st(g2.r) for e, g2 in list(g.groupby("era")) + [("ALL", g)]} for a, g in EV.groupby("arm")}
json.dump(res, open(os.path.join(OUT, f"RESULT_{MODE}.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))

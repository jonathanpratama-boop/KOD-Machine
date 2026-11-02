"""SMA_MTF_v0 (exploratory, UPSIDE only). Written before looking at results.
For every v0 crypto ignition (2020-2022), measure chart context on hourly, daily and weekly candles and ask:
does it raise the odds of UPSIDE (run to +30% before -15% within 7d; reach +50% / +100% within 30d)
and the net profit of pre-set exits, vs all ignitions and vs random coins?

No look-ahead: daily/weekly indicators use only candles fully closed BEFORE the trigger day/week; the current price is
the trigger-hour close. Hourly indicators use closes up to the trigger hour.
Luck controls: explore 2020-21, check 2022, 200-shuffle luck bar on the best cell per outcome, every cell counted.
"""
import glob, io, json, os, zipfile, hashlib
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out"); RAW = os.path.join(ROOT, "raw")
NS = [11, 21, 50, 100, 200, 500]; NW = [11, 21, 50]

# ---- daily candles 2017-08..2022-12
rows = []
for fp in glob.glob(os.path.join(RAW, "k1d", "*.zip")):
    sym = os.path.basename(fp).split("-1d-")[0]
    with zipfile.ZipFile(fp) as z:
        df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
    df = df.iloc[:, [0, 2, 3, 4, 7]].astype(float); df.columns = ["t", "high", "low", "close", "qv"]; df["sym"] = sym
    rows.append(df)
Dd = pd.concat(rows); Dd["date"] = pd.to_datetime(Dd.t.astype("int64"), unit="ms", utc=True).dt.normalize()
Dd = Dd.drop_duplicates(["sym", "date"]).sort_values(["sym", "date"])
daily = {s: g.set_index("date")[["high", "low", "close", "qv"]] for s, g in Dd.groupby("sym")}
del Dd, rows

def rsi(x, n=14):
    d = np.diff(x)
    if len(d) < n * 2: return np.nan
    g, l = np.clip(d, 0, None), np.clip(-d, 0, None); ag, al = g[:n].mean(), l[:n].mean()
    for k in range(n, len(d)): ag = (ag * (n - 1) + g[k]) / n; al = (al * (n - 1) + l[k]) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)

# ---- hourly closes for hourly SMAs
# Safe: panel_1h.pkl is produced locally by build_panel.py from hash-logged Binance zips, never external.
p = pd.read_pickle(os.path.join(OUT, "panel_1h.pkl"))
hourly = {s: g.set_index("ts")["close"] for s, g in p.groupby("sym")}; del p

ev = pd.read_csv(os.path.join(OUT, "filters_events_v0.csv"))
base = pd.read_csv(os.path.join(OUT, "events_v0.csv"))[["sym", "trigger_hour", "trig_close"]]
pk = pd.read_csv(os.path.join(OUT, "paths_events_v0.csv"))[["sym", "trigger_hour", "peak_gain", "status"]]
ev = ev.merge(base, on=["sym", "trigger_hour"]).merge(pk, on=["sym", "trigger_hour"], how="left")
ev["reach50_30d"] = np.where(ev.status == "OK", (ev.peak_gain >= .5).astype(float), np.nan)
ev["reach100_30d"] = np.where(ev.status == "OK", (ev.peak_gain >= 1).astype(float), np.nan)

feats = []
for r in ev.itertuples():
    th = pd.Timestamp(r.trigger_hour); day = th.normalize(); px = r.trig_close; f = {}
    d = daily.get(r.sym)
    if d is not None:
        d = d[d.index < day]  # fully closed days only
        c = d.close.values
        for n in NS:
            f[f"d_sma{n}_dist"] = px / c[-n:].mean() - 1 if len(c) >= n else np.nan
        sm = {n: (c[-n:].mean() if len(c) >= n else np.nan) for n in NS}
        f["d_above_count"] = float(sum(px > sm[n] for n in NS if np.isfinite(sm[n]))) if np.isfinite(sm[200]) else np.nan
        f["d_stack_11_21_50_100_200"] = float(sm[11] > sm[21] > sm[50] > sm[100] > sm[200]) if np.isfinite(sm[200]) else np.nan
        f["d_golden_50_200"] = float(sm[50] > sm[200]) if np.isfinite(sm[200]) else np.nan
        for n in [20, 50, 200]:
            f[f"d_res{n}_dist"] = px / d.high.values[-n:].max() - 1 if len(c) >= n else np.nan   # vs resistance
            f[f"d_sup{n}_dist"] = px / d.low.values[-n:].min() - 1 if len(c) >= n else np.nan    # vs support
        f["d_rsi14"] = rsi(np.append(c[-200:], px))
        if len(c) >= 14:
            hi, lo = d.high.values[-14:].max(), d.low.values[-14:].min()
            f["d_stoch14"] = (px - lo) / (hi - lo) if hi > lo else np.nan
        q = d.qv.values
        f["d_vol5_vs_50"] = q[-5:].mean() / q[-50:].mean() if len(q) >= 50 and q[-50:].mean() > 0 else np.nan
        sgn = np.sign(np.diff(c[-21:])) if len(c) >= 21 else None
        f["d_obv20_norm"] = (sgn * q[-20:]).sum() / q[-20:].sum() if sgn is not None and q[-20:].sum() > 0 else np.nan
        wk = d.close.resample("W-SUN").last().dropna()
        wk = wk[wk.index < day - pd.Timedelta(days=day.dayofweek)]  # completed weeks only
        w = wk.values
        for n in NW:
            f[f"w_sma{n}_dist"] = px / w[-n:].mean() - 1 if len(w) >= n else np.nan
        f["w_rsi14"] = rsi(np.append(w[-100:], px)) if len(w) >= 30 else np.nan
    h = hourly.get(r.sym)
    if h is not None:
        hc = h[h.index <= th].values
        for n in NS:
            f[f"h_sma{n}_dist"] = px / hc[-n:].mean() - 1 if len(hc) >= n else np.nan
    feats.append(f)
F = pd.DataFrame(feats); FEATS = list(F.columns)
D = pd.concat([ev.reset_index(drop=True), F], axis=1)
D.to_csv(os.path.join(OUT, "sma_mtf_events_v0.csv"), index=False)
CT = pd.read_csv(os.path.join(OUT, "filters_controls_v0.csv"))

OUTCOMES = ["runner", "reach50_30d", "reach100_30d", "X3_tp30_sl15_7d", "X4_tp50_14d", "X2_trail20", "X5_trail30"]
exp = D[D.year.isin([2020, 2021])].reset_index(drop=True); chk = D[D.year == 2022].reset_index(drop=True)
def edges(x):
    ok = np.isfinite(x); u = np.unique(x[ok])
    if len(u) <= 7: return [(v, v) for v in u]
    q = np.nanpercentile(x, [0, 20, 40, 60, 80, 100]); return list(zip(q[:-1], q[1:]))
def search(Fx, Y, oc):
    out = []
    for f in FEATS:
        x = Fx[f].values.astype(float); ok = np.isfinite(x)
        if ok.sum() < 200: continue
        for b, (lo, hi) in enumerate(edges(x)):
            m = ok & (x >= lo) & (x <= hi); y = Y[oc].values[m]; y = y[np.isfinite(y)]
            if len(y) >= 60: out.append((f, b, float(lo), float(hi), len(y), float(y.mean())))
    return out
rng = np.random.default_rng(2026); res = {"n_events": len(D), "n_explore": len(exp), "n_check2022": len(chk),
      "features": FEATS, "outcomes": {}}
total_cells = 0
for oc in OUTCOMES:
    cells = sorted(search(exp[FEATS], exp, oc), key=lambda c: -c[5]); total_cells += len(cells)
    null = []
    for _ in range(200):
        perm = exp[FEATS].sample(frac=1, random_state=int(rng.integers(1e9))).reset_index(drop=True)
        null.append(max(c[5] for c in search(perm, exp, oc)))
    bar = float(np.percentile(null, 95))
    top = []
    for f, b, lo, hi, n, mu in cells[:10]:
        x = chk[f].values.astype(float); m = np.isfinite(x) & (x >= lo) & (x <= hi); y = chk[oc].values[m]; y = y[np.isfinite(y)]
        top.append(dict(feature=f, bin=b, range=[round(lo, 4), round(hi, 4)], explore_n=n, explore=round(mu, 4),
                        beats_luck=bool(mu > bar), check2022_n=int(len(y)), check2022=round(float(y.mean()), 4) if len(y) else None))
    o = dict(explore_all=round(float(np.nanmean(exp[oc])), 4), check2022_all=round(float(np.nanmean(chk[oc])), 4),
             luck_bar=round(bar, 4), top10=top)
    if oc.startswith("X"):
        o["controls_2020_21"] = round(float(CT[CT.year.isin([2020, 2021])][oc].mean()), 4)
        o["controls_2022"] = round(float(CT[CT.year == 2022][oc].mean()), 4)
    res["outcomes"][oc] = o
res["cells_tested_total"] = total_cells
# descriptive: runner / reach100 by quintile for each feature, explore and 2022 (same edges)
desc = {}
for f in FEATS:
    x = exp[f].values.astype(float)
    if np.isfinite(x).sum() < 200: continue
    rowsd = []
    for lo, hi in edges(x):
        me = np.isfinite(x) & (x >= lo) & (x <= hi); xc = chk[f].values.astype(float); mc = np.isfinite(xc) & (xc >= lo) & (xc <= hi)
        rowsd.append(dict(range=[round(lo, 3), round(hi, 3)], n_e=int(me.sum()), runner_e=round(float(np.nanmean(exp.runner[me])), 3),
                          r100_e=round(float(np.nanmean(exp.reach100_30d[me])), 3), n_c=int(mc.sum()),
                          runner_c=round(float(np.nanmean(chk.runner[mc])), 3) if mc.sum() else None))
    desc[f] = rowsd
res["by_feature"] = desc
res["script_sha256"] = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
json.dump(res, open(os.path.join(OUT, "summary_sma_mtf_v0.json"), "w"), indent=1, default=float)
print("done", res["n_events"], res["cells_tested_total"])

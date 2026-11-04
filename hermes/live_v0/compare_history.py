"""LIVE_v0 compare: how unusual is today's live state versus 2018-2026 history? (descriptive)"""
import glob, io, json, os, zipfile
import numpy as np, pandas as pd
RS = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); IG = os.path.join(RS, "ignition_v0")
def rz(fp, cols):
    with zipfile.ZipFile(fp) as z: df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).lstrip("-").isdigit(): df = df.iloc[1:]
    df = df.iloc[:, cols].astype(float); t = df.iloc[:, 0].values.astype("int64"); df.iloc[:, 0] = np.where(t > 1e14, t // 1000, t); return df
fr = []
for fp in glob.glob(os.path.join(IG, "raw/k1d/*.zip")) + glob.glob(os.path.join(IG, "raw_holdout/k1d/*.zip")):
    try:
        d = rz(fp, [0, 4, 7]); d.columns = ["t", "c", "qv"]; d["sym"] = os.path.basename(fp).split("-1d-")[0]; fr.append(d)
    except Exception: pass
p = pd.concat(fr); p["d"] = pd.to_datetime(p.t.astype("int64"), unit="ms").dt.normalize(); p = p.drop_duplicates(["sym", "d"])
C = p.pivot(index="d", columns="sym", values="c").sort_index(); QV = p.pivot(index="d", columns="sym", values="qv").reindex(C.index)
liq = QV.rolling(20, min_periods=15).median() >= 480_000
above = (C > C.rolling(50).mean()) & liq & C.rolling(50).mean().notna()
breadth = above.sum(1) / (liq & C.rolling(50).mean().notna()).sum(1)
btc = C["BTCUSDT"]; btc_up = btc > btc.rolling(200).mean()
alt = C.drop(columns="BTCUSDT").where(liq).pct_change(fill_method=None).mean(1)
altidx = (1 + alt.fillna(0)).cumprod()
fng = pd.DataFrame(json.load(open(os.path.join(IG, "raw/fng_alternative_me.json")))["data"])
fng["d"] = pd.to_datetime(fng.timestamp.astype("int64"), unit="s").dt.normalize(); fng = fng.set_index("d")["value"].astype(int).reindex(C.index)
df = pd.DataFrame(dict(breadth=breadth, btc_up=btc_up, fng=fng, btc=btc, alt=altidx)).loc["2018-03-01":]
for k in (7, 30):
    df[f"btc_fwd{k}"] = df.btc.shift(-k) / df.btc - 1; df[f"alt_fwd{k}"] = df.alt.shift(-k) / df.alt - 1
res = {"days": len(df), "share_days_breadth_le_10pct": round(float((df.breadth <= .10).mean()), 3),
       "share_days_breadth_le_10_and_btc_above_sma200": round(float(((df.breadth <= .10) & df.btc_up).mean()), 3),
       "share_days_fng_20_32": round(float(df.fng.between(20, 32).mean()), 3)}
like = df[(df.breadth <= .12) & df.btc_up & df.fng.between(18, 34)]
res["lookalike_days"] = len(like)
res["lookalike_dates_sample"] = [str(d.date()) for d in like.index[::max(1, len(like) // 15)]]
res["lookalike_years"] = like.index.year.value_counts().sort_index().to_dict()
def s(x): x = x.dropna(); return dict(n=len(x), mean=round(x.mean() * 100, 1), median=round(x.median() * 100, 1), pos=round((x > 0).mean() * 100))
res["after_lookalike"] = {c: s(like[c]) for c in ["btc_fwd7", "btc_fwd30", "alt_fwd7", "alt_fwd30"]}
res["after_all_days"] = {c: s(df[c]) for c in ["btc_fwd7", "btc_fwd30", "alt_fwd7", "alt_fwd30"]}
# funding extremes
F = []
for fp in glob.glob(os.path.join(RS, "bear_v1/raw_funding/*.zip")):
    with zipfile.ZipFile(fp) as z: d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
    F.append(d["last_funding_rate"].astype(float).values)
F = np.concatenate(F)
res["funding_prints"] = int(len(F)); res["share_funding_le_-1pct"] = float((F <= -0.01).mean()); res["share_funding_le_-0.135pct"] = float((F <= -0.00135).mean())
res["funding_percentile_of_-1.35pct"] = round(float((F <= -0.01351886).mean() * 100), 4)
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_history.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))

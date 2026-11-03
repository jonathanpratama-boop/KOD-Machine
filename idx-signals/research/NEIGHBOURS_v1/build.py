"""NEIGHBOURS_v1 step 1: one row per eligible coin-day with the features of models A, B, C and the forward returns.
Writes rows.parquet-like rows.csv.gz (gitignored). Usage: python3 build.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT)); from idxsig import global_panel as gp
df = pd.read_csv(ROOT / "data/panel/panel_crypto-20261008T003354Z.csv.gz", usecols=["date", "ticker", "open", "close", "value"], parse_dates=["date"])
df = df[~df.ticker.isin(gp.STABLE) & ~df.ticker.str.contains(gp.LEVERAGED)]
O = df.pivot(index="date", columns="ticker", values="open").sort_index()
C = df.pivot(index="date", columns="ticker", values="close").reindex_like(O)
V = df.pivot(index="date", columns="ticker", values="value").reindex_like(O)
dates, tick = O.index, np.array(O.columns)
R = C / C.shift(1) - 1
liq = V.rolling(20, min_periods=15).median()
hist = C.notna().cumsum()
elig = (liq >= 1e6) & (hist >= 120) & C.notna()
btc = R["BTC"]
f = {"ret1": R, "ret3": C / C.shift(3) - 1, "ret7": C / C.shift(7) - 1, "ret20": C / C.shift(20) - 1,
     "volr": V.rolling(5, min_periods=4).mean() / V.rolling(20, min_periods=15).mean(),
     "hi60": C / C.rolling(60, min_periods=40).max(), "vol20": R.rolling(20, min_periods=15).std()}
sma50 = C.rolling(50, min_periods=40).mean()
breadth = ((C > sma50) & elig).sum(1) / elig.sum(1)
btc7 = C["BTC"] / C["BTC"].shift(7) - 1
fwd = {h: C.shift(-h) / O.shift(-1) - 1 for h in (1, 3, 5)}
resid = R.sub(btc, axis=0)
liq60 = V.rolling(60, min_periods=40).median()
Rv, Res, E = R.to_numpy(float), resid.to_numpy(float), elig.to_numpy(bool)
r7 = f["ret7"].to_numpy(float); r3 = f["ret3"].to_numpy(float)
L60 = liq60.to_numpy(float)
bi, ei = list(tick).index("BTC"), list(tick).index("ETH")
out = []
for t in range(130, len(dates) - 6):
    cols = np.flatnonzero(E[t])
    if len(cols) < 30: continue
    W = Res[t - 120:t][:, cols]
    ok = np.isfinite(W); cnt = ok.sum(0)
    mu = np.where(cnt > 0, np.nansum(W, 0) / np.maximum(cnt, 1), 0); Z = np.where(ok, W - mu, 0.0)
    sd = np.sqrt((Z ** 2).sum(0) / np.maximum(cnt, 1)); Z = Z / np.where(sd > 0, sd, np.inf)
    shared = ok.T.astype(float) @ ok.astype(float)
    corr = (Z.T @ Z) / np.maximum(shared, 1)
    corr[shared < 100] = -np.inf; np.fill_diagonal(corr, -np.inf)
    peers = np.argsort(-corr, axis=1)[:, :20]
    has = np.isfinite(np.take_along_axis(corr, peers, 1)).all(1)
    pr1 = np.nanmedian(Rv[t, cols][peers], 1); pr3 = np.nanmedian(r3[t, cols][peers], 1); pr7 = np.nanmedian(r7[t, cols][peers], 1)
    part = (Rv[t, cols][peers] >= 0.03).mean(1)
    # stations from liquidity up to t-1
    st = np.full(len(cols), 5)
    alt = [k for k, c in enumerate(cols) if c not in (bi, ei)]
    order = sorted(alt, key=lambda k: -np.nan_to_num(L60[t - 1, cols[k]], nan=-1))
    for rnk, k in enumerate(order): st[k] = 3 if rnk < 20 else (4 if rnk < 60 else 5)
    for k, c in enumerate(cols):
        if c == bi: st[k] = 1
        if c == ei: st[k] = 2
    smed = {}
    for s in range(1, 6):
        m = st == s
        smed[(s, 1)] = float(np.nanmedian(Rv[t, cols][m])) if m.any() else 0.0
        smed[(s, 3)] = float(np.nanmedian(r3[t, cols][m])) if m.any() else 0.0
    row = pd.DataFrame({"date": dates[t], "ticker": tick[cols], "station": st, "peers_ok": has,
                        "p_ret1": pr1, "p_ret3": pr3, "p_ret7": pr7, "p_part": part, "rel7": r7[t, cols] - pr7})
    for k, v in f.items(): row[k] = v.iloc[t, cols].to_numpy(float)
    row["btc7"] = btc7.iloc[t]; row["breadth"] = breadth.iloc[t]
    for (s, h), v in smed.items(): row[f"st{s}_r{h}"] = v
    for h, v in fwd.items(): row[f"fwd{h}"] = v.iloc[t, cols].to_numpy(float)
    out.append(row)
rows = pd.concat(out, ignore_index=True)
rows.to_csv(HERE / "rows.csv.gz", index=False, compression="gzip")
print(rows.shape, rows.date.min().date(), rows.date.max().date(), rows.groupby(rows.date.dt.year).size().to_dict())
print(rows.station.value_counts().to_dict(), "peers_ok", round(rows.peers_ok.mean(), 3))

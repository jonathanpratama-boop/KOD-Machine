"""SEESAW_v1 run, v2: identical to run.py except spearmanr is a pandas rank correlation (scipy is not installed) and LEVERAGED is read as a regex. Run 1 (run.py) crashed at import before reading data. This file produced RESULT.json and monthly.csv. Usage: python3 run_v2.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
def spearmanr(a, b):
    r = pd.Series(list(a)).rank().corr(pd.Series(list(b)).rank())
    return r, float('nan')
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
if (HERE / "RESULT.json").exists(): sys.exit("RESULT.json exists; runs once")
sys.path.insert(0, str(ROOT)); from idxsig import global_panel
st = json.load(open(HERE / "stablecoins_all.json"))
sc = pd.Series({pd.Timestamp(int(x["date"]), unit="s").normalize(): x["totalCirculatingUSD"].get("peggedUSD", np.nan) for x in st}).sort_index()
df = pd.read_csv(ROOT / "data/panel/panel_crypto-20261008T003354Z.csv.gz", usecols=["date", "ticker", "close", "value"], parse_dates=["date"])
C = df.pivot(index="date", columns="ticker", values="close").sort_index(); Vq = df.pivot(index="date", columns="ticker", values="value").reindex_like(C)
base = {c: c[:-4] if c.endswith("USDT") else c for c in C.columns}
bad = set(global_panel.STABLE)
levre = global_panel.LEVERAGED
alts = [c for c in C.columns if base[c] not in bad and c not in bad and not levre.search(c) and not levre.search(base[c]) and base[c] != "BTC" and c not in ("BTCUSDT", "BTC")]
btc = C["BTCUSDT"] if "BTCUSDT" in C.columns else C["BTC"]
liq = Vq[alts].rolling(20, min_periods=15).median()
sma50 = C[alts].rolling(50, min_periods=40).mean()
rows = []
for d in pd.date_range("2020-02-01", "2026-09-01", freq="MS"):
    prev = C.index[C.index < d]
    if len(prev) < 60: continue
    t0 = prev[-1]
    uni = [a for a in alts if liq.at[t0, a] >= 1e6 and np.isfinite(C.at[t0, a])]
    t30 = prev[-31] if len(prev) > 31 else None
    s_now = sc[sc.index <= t0].iloc[-1]; s_30 = sc[sc.index <= t0 - pd.Timedelta(days=30)].iloc[-1]
    S1 = s_now / s_30 - 1
    r30 = C.loc[t0, uni] / C.loc[t30, uni] - 1
    S2 = float(r30.median() - (btc[t0] / btc[t30] - 1))
    S3 = float((C.loc[t0, uni] > sma50.loc[t0, uni]).mean())
    fut = C.loc[(C.index > t0) & (C.index <= t0 + pd.Timedelta(days=30)), uni]
    hit = (fut.max() / C.loc[t0, uni] >= 1.30)
    end = fut.ffill().iloc[-1] / C.loc[t0, uni] - 1
    rows.append({"month": d.strftime("%Y-%m"), "n_alts": len(uni), "S1_stable_30d": S1, "S2_alt_minus_btc": S2, "S3_breadth50": S3,
                 "moonshot_rate": float(hit.mean()), "median_alt_30d": float(end.median()), "btc_30d_next": float(btc[fut.index[-1]] / btc[t0] - 1)})
m = pd.DataFrame(rows); m.to_csv(HERE / "monthly.csv", index=False)
m["period"] = np.where(m.month <= "2022-12", "dev_2020_22", "check_2023_26")
m["tide_on"] = (m.S1_stable_30d > 0) & (m.S2_alt_minus_btc > 0)
res = {"months": len(m), "periods": {}}
for p, g in m.groupby("period"):
    r = {"n": len(g)}
    for s in ("S1_stable_30d", "S2_alt_minus_btc", "S3_breadth50"):
        rho, pv = spearmanr(g[s], g.moonshot_rate); r[s] = {"rho_moonshot": float(rho), "p": float(pv), "rho_median_ret": float(spearmanr(g[s], g.median_alt_30d)[0])}
    for k, gg in g.groupby("tide_on"):
        r["tide_on" if k else "tide_off"] = {"n": len(gg), "moonshot_rate": float(gg.moonshot_rate.mean()), "median_alt_30d": float(gg.median_alt_30d.mean())}
    res["periods"][p] = r
c = res["periods"]["check_2023_26"]; dv = res["periods"]["dev_2020_22"]
lead = (c.get("tide_on", {}).get("moonshot_rate", -1) > c.get("tide_off", {}).get("moonshot_rate", 9) and
        c.get("tide_on", {}).get("median_alt_30d", -9) > c.get("tide_off", {}).get("median_alt_30d", 9) and
        any(dv[s]["rho_moonshot"] > 0 and c[s]["rho_moonshot"] > 0 for s in ("S1_stable_30d", "S2_alt_minus_btc")))
res["reading"] = "FLOW LEADS THE TIDE" if lead else "FLOW DESCRIBES, DOES NOT LEAD"
(HERE / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res, indent=1))
print(m[["month","S1_stable_30d","S2_alt_minus_btc","S3_breadth50","tide_on","moonshot_rate","median_alt_30d"]].round(3).to_string(index=False))

"""FNG_v1 — do trades behave differently under Extreme Fear / Fear / Neutral / Greed / Extreme Greed?
Source: alternative.me Crypto Fear & Greed Index (raw/fng_alternative_me.json, sha256 logged in research log).
No look-ahead: each trade uses the index value of the PREVIOUS UTC day (the value stamped for the trigger day is
published around 00:00 UTC and is built from earlier data, but the previous day is the safe choice).
Groups: all ignitions, random coins, ignitions in the COMBO_v1 rule (score >= 4). Periods 2020-21 and 2022.
Descriptive only: no rule is chosen from this table here.
"""
import json, os
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out")
f = pd.DataFrame(json.load(open(os.path.join(ROOT, "raw", "fng_alternative_me.json")))["data"])
f["date"] = pd.to_datetime(f.timestamp.astype("int64"), unit="s", utc=True).dt.normalize()
f = f.set_index("date").sort_index()
A = pd.read_csv(os.path.join(OUT, "fib_trend_v1_all.csv"))
A["score"] = ((A["above_count"] >= 5).astype(int) + (A["stack"] == 1).astype(int) + (A["res200_dist"] >= -0.15).astype(int)
              + (A["sma100_dist"] >= 0.5).astype(int) + (A["fib200d_cross618_or_1"] == 1).astype(int) + (A["fib50d_cross618_or_1"] == 1).astype(int))
prev = pd.to_datetime(A.trigger_hour).dt.normalize() - pd.Timedelta(days=1)
A["fng"] = f["value"].astype(int).reindex(prev).values
A["mood"] = f["value_classification"].reindex(prev).values
ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
X = ["runner", "reach100_30d", "X1_hold3d", "X3_tp30_sl15_7d", "X4_tp50_14d", "X5_trail30"]
def st(d):
    o = {"n": int(len(d))}
    if len(d) < 1: return o
    for x in X: o[x] = round(float(d[x].mean()), 4)
    o["X4_median"] = round(float(d.X4_tp50_14d.median()), 4); o["X4_pct_profit"] = round(float((d.X4_tp50_14d > 0).mean()), 3)
    return o
res = {"missing_fng": int(A.fng.isna().sum())}
for per, yrs in [("2020_21", [2020, 2021]), ("2022", [2022]), ("all_2020_22", [2020, 2021, 2022])]:
    d = A[A.year.isin(yrs)]; res[per] = {}
    for m in ORDER:
        dm = d[d.mood == m]
        res[per][m] = dict(ignitions=st(dm[dm.kind == "event"]), random=st(dm[dm.kind == "control"]),
                           combo=st(dm[(dm.kind == "event") & (dm.score >= 4)]))
json.dump(res, open(os.path.join(OUT, "summary_fng_v1.json"), "w"), indent=1)
for per in ["2020_21", "2022", "all_2020_22"]:
    print("=====", per)
    for m in ORDER:
        r = res[per][m]
        for g in ["ignitions", "random", "combo"]:
            s = r[g]
            if s["n"]: print(f"{m:14s} {g:9s} n={s['n']:5d} run={s['runner']:.3f} r100={s['reach100_30d']:.3f} hold3d={s['X1_hold3d']:+.4f} tp30sl15={s['X3_tp30_sl15_7d']:+.4f} tp50={s['X4_tp50_14d']:+.4f} med={s['X4_median']:+.4f} win={s['X4_pct_profit']:.2f} trail30={s['X5_trail30']:+.4f}")
print("missing", res["missing_fng"])

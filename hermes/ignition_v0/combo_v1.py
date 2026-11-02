"""COMBO_v1 — all upside clues at once (exploratory; rule fixed BEFORE looking at any COMBO result).
Clues come from earlier 2020-21 exploration, so 2020-21 numbers are IN-SAMPLE (optimistic). 2022 is the check.
COMMON clues (computable for ignitions and random coins alike), each 1 point:
  C1 above >=5 of 6 daily SMAs (11/21/50/100/200/500)     C2 SMAs stacked 11>21>50>100>200
  C3 within 15% of (or above) the 200-day high             C4 price >=50% above its 100-day SMA
  C5 move crossed the .618 or 1.0 Fibonacci level of the 200-day swing
  C6 move crossed the .618 or 1.0 Fibonacci level of the 50-day swing
EXTRA momentum clues (ignitions only): E1 daily RSI14 >=65, E2 weekly RSI14 >=60, E3 above weekly SMA11.
PRIMARY rule (fixed now): ignition AND COMMON score >= 4. Exits judged: TP50/14d (X4) and trail-30% (X5), plus hold 7d.
Reported per score level: n, runner rate, reach +100%, mean and MEDIAN net, % profitable, share of total profit from the
top 5 trades, vs random coins with the same score. Bootstrap by trigger day for the primary rule.
"""
import json, os
import numpy as np, pandas as pd
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
A = pd.read_csv(os.path.join(OUT, "fib_trend_v1_all.csv"))
S = pd.read_csv(os.path.join(OUT, "sma_mtf_events_v0.csv"))[["sym", "trigger_hour", "d_rsi14", "w_rsi14", "w_sma11_dist"]]
P = pd.read_csv(os.path.join(OUT, "paths_events_v0.csv"))[["sym", "trigger_hour", "net_7d"]]
Pc = pd.read_csv(os.path.join(OUT, "paths_controls_v0.csv"))[["sym", "trigger_hour", "net_7d"]].drop_duplicates(["sym", "trigger_hour"])
E = A[A.kind == "event"].merge(S, on=["sym", "trigger_hour"], how="left").merge(P, on=["sym", "trigger_hour"], how="left")
K = A[A.kind == "control"].drop_duplicates(["sym", "trigger_hour"]).merge(Pc, on=["sym", "trigger_hour"], how="left")
def common(d):
    return ((d["above_count"] >= 5).astype(int) + (d["stack"] == 1).astype(int) + (d["res200_dist"] >= -0.15).astype(int)
            + (d["sma100_dist"] >= 0.5).astype(int) + (d["fib200d_cross618_or_1"] == 1).astype(int) + (d["fib50d_cross618_or_1"] == 1).astype(int))
E["score"] = common(E); K["score"] = common(K)
E["extra"] = (E.d_rsi14 >= 65).astype(int) + (E.w_rsi14 >= 60).astype(int) + (E.w_sma11_dist > 0).astype(int)
E["full"] = E.score + E.extra
X = ["X4_tp50_14d", "X5_trail30", "net_7d"]
def stats(d):
    o = dict(n=int(len(d)))
    if len(d) == 0: return o
    o.update(runner=round(float(d.runner.mean()), 3), reach100=round(float(d.reach100_30d.mean()), 3))
    for x in X:
        v = d[x].dropna().sort_values(ascending=False)
        if len(v) == 0: continue
        tot = v.sum()
        o[x] = dict(mean=round(float(v.mean()), 4), median=round(float(v.median()), 4), pct_profit=round(float((v > 0).mean()), 3),
                    mean_without_top5=round(float(v.iloc[5:].mean()), 4) if len(v) > 10 else None)
    return o
rng = np.random.default_rng(44)
def boot(d, x):
    d = d.dropna(subset=[x]); d = d.assign(day=d.trigger_hour.str[:10]); g = {k: v[x].values for k, v in d.groupby("day")}; days = list(g)
    if len(days) < 5: return None
    bs = [np.concatenate([g[k] for k in rng.choice(days, len(days))]).mean() for _ in range(2000)]
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]
res = {}
for per, yrs in [("2020_21", [2020, 2021]), ("2022", [2022])]:
    e, k = E[E.year.isin(yrs)], K[K.year.isin(yrs)]
    r = {"by_common_score": {}, "by_full_score_ignitions": {}}
    for s in range(7):
        r["by_common_score"][s] = dict(ignitions=stats(e[e.score == s]), random=stats(k[k.score == s]))
    for s in range(10):
        if (e.full == s).any(): r["by_full_score_ignitions"][s] = stats(e[e.full == s])
    pe, pk = e[e.score >= 4], k[k.score >= 4]
    r["PRIMARY_score_ge4"] = dict(ignitions=stats(pe), random=stats(pk), all_ignitions=stats(e), all_random=stats(k),
                                 ci_ignitions={x: boot(pe, x) for x in X}, ci_random={x: boot(pk, x) for x in X})
    r["coins_in_primary"] = sorted(pe.sym.unique().tolist())
    res[per] = r
json.dump(res, open(os.path.join(OUT, "summary_combo_v1.json"), "w"), indent=1, default=float)
for per in res:
    print("=====", per)
    for s, v in res[per]["by_common_score"].items():
        i, r_ = v["ignitions"], v["random"]
        if i["n"]: print(f"score {s}: IGN n={i['n']} run={i.get('runner')} r100={i.get('reach100')} X4 mean/med/%={i.get('X4_tp50_14d')} | RND n={r_['n']} X4={r_.get('X4_tp50_14d', {}).get('mean') if r_['n'] else None}")
    for s, v in res[per]["by_full_score_ignitions"].items():
        print(f"  full {s}: n={v['n']} run={v.get('runner')} X4={v.get('X4_tp50_14d')} 7d={v.get('net_7d')}")
    pr = res[per]["PRIMARY_score_ge4"]; print("PRIMARY", json.dumps(pr, default=float))

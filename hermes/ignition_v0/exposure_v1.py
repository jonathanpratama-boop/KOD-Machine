"""EXPOSURE_v1 (read-only decomposition, no tuning). Question: is the 'uptrend' result skill, or just market exposure?
For every trade (ignitions and random coins), compare its fixed-hold return (3d/7d/14d/30d, net of costs) with
(a) BTC's return over the same window and (b) the average random coin bought at the same hour (the altcoin market).
Regress trade return on BTC return (alpha = what is left after market exposure). Uncertainty: bootstrap by trigger
day (trades on the same day are not independent). TREND as fixed in FIB_TREND_v1 (>=5 of 6 daily SMAs and within 15%
of the 200-day high). Periods 2020-21 and 2022 reported separately.
"""
import json, os
import numpy as np, pandas as pd
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# Safe: panel_1h.pkl is produced locally by build_panel.py from hash-logged Binance zips, never external.
p = pd.read_pickle(os.path.join(OUT, "panel_1h.pkl"))
btc = p[p.sym == "BTCUSDT"].set_index("ts"); BO, BC = btc.open, btc.close; del p
A = pd.read_csv(os.path.join(OUT, "fib_trend_v1_all.csv"))
A["trend"] = (A.above_count >= 5) & (A.res200_dist >= -0.15)
pe = pd.read_csv(os.path.join(OUT, "paths_events_v0.csv")); pe["kind"] = "event"
pc = pd.read_csv(os.path.join(OUT, "paths_controls_v0.csv")).drop(columns=["event_sym"], errors="ignore"); pc["kind"] = "control"
P = pd.concat([pe, pc]); P = P[P.status == "OK"].drop_duplicates(["kind", "sym", "trigger_hour"])
M = A[["kind", "sym", "trigger_hour", "year", "trend"]].drop_duplicates(["kind", "sym", "trigger_hour"]).merge(P, on=["kind", "sym", "trigger_hour"])
H = {"3d": 72, "7d": 168, "14d": 336, "30d": 720}
ent = pd.to_datetime(M.trigger_hour) + pd.Timedelta(hours=1)
for k, h in H.items():
    o = BO.reindex(ent).values; c = BC.reindex(ent + pd.Timedelta(hours=h - 1)).values
    M[f"btc_{k}"] = c / o - 1
M["day"] = M.trigger_hour.str[:10]
# altcoin market at the same hour = mean of all random coins bought that hour
for k in H:
    mk = M[M.kind == "control"].groupby("trigger_hour")[f"net_{k}"].mean().rename(f"alt_{k}")
    M = M.merge(mk, left_on="trigger_hour", right_index=True, how="left")
rng = np.random.default_rng(5)
def fit(d, k):
    d = d[np.isfinite(d[f"net_{k}"]) & np.isfinite(d[f"btc_{k}"])]
    if len(d) < 15: return dict(n=len(d))
    def ab(x):
        y, b = x[f"net_{k}"].values, x[f"btc_{k}"].values
        beta = np.cov(y, b)[0, 1] / np.var(b, ddof=1); return y.mean() - beta * b.mean(), beta
    a, b = ab(d); days = d.day.unique(); g = {dd: x for dd, x in d.groupby("day")}; bs = []
    for _ in range(500):
        s = pd.concat([g[dd] for dd in rng.choice(days, len(days))]); bs.append(ab(s)[0])
    vs_alt = (d[f"net_{k}"] - d[f"alt_{k}"]).values
    return dict(n=len(d), days=len(days), mean=round(float(d[f"net_{k}"].mean()), 4), btc_same_window=round(float(d[f"btc_{k}"].mean()), 4),
                beta_to_btc=round(float(b), 2), alpha=round(float(a), 4), alpha_95=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                vs_alt_market=round(float(np.nanmean(vs_alt)), 4))
res = {}
for per, yrs in [("2020_21", [2020, 2021]), ("2022", [2022])]:
    d = M[M.year.isin(yrs)]; res[per] = {}
    for name, sel in [("ignitions_TREND", (d.kind == "event") & d.trend), ("random_TREND", (d.kind == "control") & d.trend),
                      ("ignitions_NOT_TREND", (d.kind == "event") & ~d.trend), ("random_ALL", d.kind == "control")]:
        res[per][name] = {k: fit(d[sel], k) for k in H}
json.dump(res, open(os.path.join(OUT, "summary_exposure_v1.json"), "w"), indent=1)
for per in res:
    for name in res[per]:
        for k in H:
            r = res[per][name][k]
            if "alpha" in r: print(per, name, k, r["n"], r["mean"], "btc", r["btc_same_window"], "beta", r["beta_to_btc"], "alpha", r["alpha"], r["alpha_95"], "vsAlt", r["vs_alt_market"])

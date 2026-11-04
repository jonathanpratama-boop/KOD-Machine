"""Summarise SPIKE_DEFAULT_v1."""
import os, json
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
R = pd.concat([pd.read_csv(f"trades_{p}.csv.gz") for p in ("disc", "hold")])
R["period"] = np.where(R.year <= 2021, "2020-21", np.where(R.year == 2022, "2022", "2023-26"))
def st(x):
    x = x.dropna(); return dict(n=len(x), mean=round(x.mean() * 100, 2), median=round(x.median() * 100, 2), pos=round((x > 0).mean() * 100, 1))
rows = []
for (per, v), g in R.groupby(["period", "variant"]):
    e, c = g[g.kind == "event"], g[g.kind == "control"]
    se, sc = st(e.net), st(c.net)
    rows.append(dict(period=per, variant=v, ev_n=se["n"], ev_mean=se["mean"], ev_med=se["median"], ev_pos=se["pos"],
                     ctl_mean=sc["mean"], ctl_med=sc["median"], combo_mean=st(e[e.score >= 4].net)["mean"],
                     trend_mean=st(e[e.trend == True].net).get("mean")))
S = pd.DataFrame(rows); S.to_csv("summary_by_variant.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(S.sort_values(["variant", "period"]).to_string(index=False))
P = "T15_L10_HOLDon"
e = R[(R.kind == "event") & (R.variant == P)]
print("\nPRIMARY by year (events):", {int(y): st(g.net) for y, g in e.groupby("year")})
e2 = e.copy(); e2["mood"] = pd.cut(e2.fng_prev, [-1, 24, 45, 55, 75, 101], labels=["ExtFear", "Fear", "Neutral", "Greed", "ExtGreed"])
print("PRIMARY by mood (events):", {str(m): st(g.net) for m, g in e2.groupby("mood", observed=True)})
print("PRIMARY exit mix (events):", (e.how.value_counts(normalize=True) * 100).round(1).to_dict())
for per in ["2020-21", "2022", "2023-26"]:
    g = e[e.period == per]; print(per, "exit mix", (g.how.value_counts(normalize=True) * 100).round(1).to_dict())
json.dump(dict(primary_by_year={int(y): st(g.net) for y, g in e.groupby("year")}), open("primary.json", "w"))

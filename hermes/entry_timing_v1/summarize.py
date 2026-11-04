"""Summarise ENTRY_TIMING_v1 trades (descriptive)."""
import pandas as pd, numpy as np, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
R = pd.concat([pd.read_csv("trades_disc.csv"), pd.read_csv("trades_hold.csv")])
R["period"] = np.where(R.year <= 2021, "2020-21", np.where(R.year == 2022, "2022", "2023-26"))
ig = R[R.kind == "ignition"]
v0 = ig[ig.variant == "V0_NEXT_OPEN"].set_index(["sym", "ts"])
win = set(v0[(v0.status == "TRADE") & (v0.tp == 1)].index)
def agg(d, cands):
    t = d[d.status == "TRADE"]
    o = dict(cands=int(cands), trades=int(len(t)), fill=round(len(t) / max(cands, 1), 2))
    if len(t):
        o.update(mean=round(t.net.mean() * 100, 1), median=round(t.net.median() * 100, 1), pos=round((t.net > 0).mean() * 100),
                 tp=round(t.tp.mean() * 100), px_vs_trig=round(t.entry_vs_trig.median() * 100, 1))
    return o
out = []
subsets = {"all": lambda d: d, "combo>=4": lambda d: d[d.score >= 4], "daily_trend": lambda d: d[d.trend == True]}
for per in ["2020-21", "2022", "2023-26"]:
    for sn, f in subsets.items():
        g = f(ig[ig.period == per])
        ncand = g[g.variant == "V0_NEXT_OPEN"].shape[0]
        wins = set(g.set_index(["sym", "ts"]).index) & win
        for v, gv in g.groupby("variant"):
            o = agg(gv, ncand); traded = set(gv[gv.status == "TRADE"].set_index(["sym", "ts"]).index)
            o["missed_winners_pct"] = round(100 * len(wins - traded) / max(len(wins), 1)) if v != "V0_NEXT_OPEN" else 0
            out.append(dict(period=per, subset=sn, variant=v, **o))
    e = R[(R.kind == "early1h") & (R.period == per)]
    for sn in ["all", "daily_trend"]:
        g = subsets[sn](e); out.append(dict(period=per, subset=sn, variant="V5_EARLY_1H", **agg(g, len(g))))
T = pd.DataFrame(out); T.to_csv("summary_entry_timing.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(T.to_string(index=False))
a = ig[ig.variant == "V0_NEXT_OPEN"]
print("\nANATOMY (ignitions)")
for per, g in a.groupby("period"):
    print(per, "n", len(g), "moved3h med %.1f%%" % (g.moved_3h.median() * 100), "dip72 med %.1f%%" % (g.dip72.median() * 100),
          "dip<=-5%% %.0f%%" % ((g.dip72 <= -.05).mean() * 100), "dip<=-10%% %.0f%%" % ((g.dip72 <= -.10).mean() * 100),
          "peak336 med %.1f%%" % (g.peak336.median() * 100), "hrs_to_peak med %.0f" % g.hours_to_peak.median())
    w = g[g.peak336 >= .5]
    print("   peak>=50%% n %d: dip before peak med %.1f%%, dip<=-10%% %.0f%%, hrs to peak med %.0f" %
          (len(w), w.dip_before_peak.median() * 100, (w.dip_before_peak <= -.10).mean() * 100, w.hours_to_peak.median()))
e = R[R.kind == "early1h"]
print("\nEARLY detector became full ignition within 6h:", e.groupby("period").became_ignition_6h.mean().round(3).to_dict())

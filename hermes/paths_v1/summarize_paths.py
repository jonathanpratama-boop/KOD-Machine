"""Summarise PATHS_v1 (descriptive). Shapes and buckets defined before looking at results (see comments)."""
import os, json
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
R = pd.concat([pd.read_csv("paths_disc.csv"), pd.read_csv("paths_hold.csv")])
R = R[R.r336.notna()].copy()
R["period"] = np.where(R.year <= 2021, "2020-21", np.where(R.year == 2022, "2022", "2023-26"))
R["mood"] = pd.cut(R.fng_prev, [-1, 24, 45, 55, 75, 101], labels=["ExtFear", "Fear", "Neutral", "Greed", "ExtGreed"])
def shape(x):
    if x.mfe336 >= .30 and x.r336 >= .20: return "RUNNER_KEPT"
    if x.mfe336 >= .20 and x.r336 < .05: return "SPIKE_GIVEBACK"
    if x.mfe72 < .20 and x.r336 >= .20: return "GRINDER"
    if x.mfe336 < .05 and x.r336 <= -.15: return "DEAD"
    if x.r336 < -.05: return "FADE"
    return "FLAT"
R["path_shape"] = R.apply(shape, axis=1)
P = ["2020-21", "2022", "2023-26"]; out = {}
pct = lambda s: round(100 * float(s), 1)
# A. unrealized wins given back (within 14 days)
A = []
for per in P + ["ALL"]:
    g = R if per == "ALL" else R[R.period == per]
    for x in (.10, .20, .30, .50):
        w = g[g.mfe336 >= x]
        A.append(dict(period=per, was_up=f"+{int(x*100)}%", share=pct(len(w) / len(g)), then_negative_d14=pct((w.r336 < 0).mean()),
                      median_end=pct(w.r336.median()), median_h_to_peak=float(w.h_peak.median())))
out["A_unrealized_wins"] = A
# B. unrealized losses recovered
B = []
for per in P + ["ALL"]:
    g = R if per == "ALL" else R[R.period == per]
    for x in (-.10, -.20, -.30):
        w = g[g.mae336 <= x]
        B.append(dict(period=per, was_down=f"{int(x*100)}%", share=pct(len(w) / len(g)), recovered_positive=pct((w.r336 > 0).mean()),
                      recovered_20=pct((w.r336 >= .2).mean())))
out["B_unrealized_losses"] = B
# C. shapes
out["C_shapes_by_period"] = {per: (R[R.period == per].path_shape.value_counts(normalize=True) * 100).round(1).to_dict() for per in P}
out["C_shapes_by_mood"] = {str(m): (g.path_shape.value_counts(normalize=True) * 100).round(1).to_dict() for m, g in R.groupby("mood", observed=True)}
# D. what is visible at hour 6 / 24 -> what happens next (forward from that hour)
def fwd(g, k): return (1 + g.r336) / (1 + g[f"r{k}"]) - 1
D = []
for k in (6, 24):
    R[f"b{k}"] = pd.cut(R[f"r{k}"], [-9, -.10, -.03, .03, .10, .25, 99], labels=["<=-10%", "-10..-3%", "-3..+3%", "+3..+10%", "+10..+25%", ">+25%"])
    for per in P:
        for b, g in R[R.period == per].groupby(f"b{k}", observed=True):
            if len(g) < 25: continue
            f = fwd(g, k)
            D.append(dict(hour=k, period=per, state=str(b), n=len(g), share=pct(len(g) / (R.period == per).sum()),
                          fwd_mean=pct(f.mean()), fwd_median=pct(f.median()), fwd_pos=pct((f > 0).mean()),
                          runner_kept=pct((g.path_shape == "RUNNER_KEPT").mean())))
out["D_state_then_forward"] = D
# E. follow-through signals at 6h
E = []
R["outperf_btc24"] = (R.r24 - R.btc24) > 0
for per in P:
    g = R[R.period == per]
    for col, lab in (("newhigh_6h", "new high above trigger bar within 6h"), ("outperf_btc24", "beat BTC over first 24h")):
        for v, gg in g.groupby(col):
            k = 6 if col == "newhigh_6h" else 24
            f = fwd(gg, k); E.append(dict(period=per, signal=lab, value=bool(v), n=len(gg), fwd_mean=pct(f.mean()), fwd_median=pct(f.median()),
                                          runner_kept=pct((gg.path_shape == "RUNNER_KEPT").mean())))
    vq = pd.qcut(g.vol_persist_6h, 3, labels=["low", "mid", "high"])
    for v, gg in g.groupby(vq, observed=True):
        f = fwd(gg, 6); E.append(dict(period=per, signal="volume kept up over first 6h (tercile)", value=str(v), n=len(gg),
                                      fwd_mean=pct(f.mean()), fwd_median=pct(f.median()), runner_kept=pct((gg.path_shape == "RUNNER_KEPT").mean())))
out["E_followthrough"] = E
# F. where the peak sits
out["F_peak_timing"] = {per: dict(peak_within_6h=pct((R[R.period == per].h_peak <= 6).mean()), within_24h=pct((R[R.period == per].h_peak <= 24).mean()),
                                   after_7d=pct((R[R.period == per].h_peak > 168).mean())) for per in P}
json.dump(out, open("SUMMARY_paths_v1.json", "w"), indent=1, default=str)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 300)
for k, v in out.items():
    print("==", k); print(pd.DataFrame(v).to_string(index=isinstance(v, dict)) if isinstance(v, list) else pd.DataFrame(v).T.to_string())

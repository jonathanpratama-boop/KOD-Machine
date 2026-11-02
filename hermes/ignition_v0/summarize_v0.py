"""Recompute v0 summary from per-event values (fixes summary bug: boolean hit columns were object dtype,
so .mean() was wrong). Adds luck checks: bootstrap CIs, concentration, per-year, mae data-glitch flags."""
import json, os
import numpy as np, pandas as pd
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
ev = pd.read_csv(os.path.join(OUT, "events_v0.csv")); ct = pd.read_csv(os.path.join(OUT, "controls_v0.csv"))
ok = ev[ev.status == "OK"].copy()
rng = np.random.default_rng(11)
def ci(x, f=np.mean, B=2000):
    x = np.asarray(x[np.isfinite(x)]); bs = [f(rng.choice(x, len(x))) for _ in range(B)]
    return [round(float(f(x)), 4), round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]
def summ(d):
    m = d.mfe72.values
    return dict(n=len(d), p_reach30=ci((m >= .3).astype(float)), p_reach50=ci((m >= .5).astype(float)),
                p_reach100=ci((m >= 1).astype(float)), net24_mean=ci(d.net24.values), net72_mean=ci(d.net72.values),
                net72_median=round(float(d.net72.median()), 4), win72=round(float((d.net72 > 0).mean()), 4))
res = {"events": summ(ok), "controls": summ(ct)}
res["by_year"] = {y: {"events": summ(ok[ok.trigger_hour.str[:4] == y]), "controls": summ(ct[ct.trigger_hour.str[:4] == y])}
                  for y in ["2020", "2021", "2022"]}
# concentration: how much of the total net72 comes from the top 1% / top 20 events
s = ok.net72.dropna().sort_values(ascending=False)
res["concentration"] = dict(total_net72_sum=round(float(s.sum()), 3), top20_sum=round(float(s.head(20).sum()), 3),
                            sum_without_top20=round(float(s.iloc[20:].sum()), 3))
res["data_flags"] = {"events_mae_le_minus90pct": int((ok.mae72 <= -0.9).sum())}
res["already_moved_from_start_median"] = round(float(ok.already_moved_from_start.median()), 4)
json.dump(res, open(os.path.join(OUT, "summary_v0_fixed.json"), "w"), indent=1)
print(json.dumps(res, indent=1))

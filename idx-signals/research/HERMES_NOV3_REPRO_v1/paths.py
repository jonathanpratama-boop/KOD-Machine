"""Study 3 PATHS (PROTOCOL.md): every alert with a 30-day window, hour by hour, no exit rule."""
import json, pickle
import numpy as np, pandas as pd
import lib

C_ = lib.COST
rows = []
for seg in ("disc", "hold"):
    sg = lib.Seg(seg); det = lib.detect(sg); R = pickle.load(open(lib.CACHE / f"alerts_{seg}.pkl", "rb"))["R"]
    b = sg.idx.get("BTCUSDT")
    for r in R[R.kind == "event"].itertuples():
        i, t = r.i, r.e_t; e = t + 1; w = lib.window(sg, i, e, 720)
        ent = sg.O[i, e]
        if w is None or not (np.isfinite(ent) and ent > 0):
            continue
        hh, ll, cf, _ = w; entc = ent * (1 + C_)
        g = lambda x: x * (1 - C_) / entc - 1
        up14, dn14 = np.nanmax(hh[:336]) / ent - 1, np.nanmin(ll[:336]) / ent - 1
        d14 = g(cf[335]); pk30 = int(np.nanargmax(hh))
        h6 = cf[5] / ent - 1
        btc24 = sg.C[b, e + 23] / sg.O[b, e] - 1 if b is not None and np.isfinite(sg.O[b, e]) else np.nan
        coin24 = cf[23] / ent - 1
        newhigh6 = bool(np.nanmax(hh[:6]) > sg.H[i, t]) if np.isfinite(sg.H[i, t]) else False
        vol24 = np.nanmean(sg.Q[i, e:e + 24]) / det["base"][i, t] if np.isfinite(det["base"][i, t]) else np.nan
        rows.append(dict(seg=seg, period=r.period, mood=r.mood, up14=up14, dn14=dn14, d14=d14, up72=np.nanmax(hh[:72]) / ent - 1,
                         h6=h6, after_h6=cf[335] / cf[5] - 1, peak30_hour=pk30,
                         kept_runner=bool(up14 >= .30 and (cf[335] / ent - 1) >= 0.5 * up14),
                         beat_btc24=bool(coin24 > btc24) if np.isfinite(btc24) else np.nan, newhigh6=newhigh6,
                         volhigh24=bool(vol24 >= 3) if np.isfinite(vol24) else np.nan, reach50=bool(up14 >= .5)))
P = pd.DataFrame(rows); PER = ["2020-21", "2022", "2023-26"]
res = {"n": int(len(P)), "by_period_n": P.period.value_counts().to_dict(), "P1": {}, "P2": {}, "P3": {}, "P4": {}, "P5": {}, "P6": {}, "first24h_peak": {}}
for p in PER:
    d = P[P.period == p]
    res["P1"][p] = {f"+{int(x*100)}": dict(touched=float((d.up14 >= x).mean()), of_those_negative_d14=float((d[d.up14 >= x].d14 < 0).mean()))
                    for x in (.10, .20, .30, .50)}
    res["P2"][p] = {f"-{int(x*100)}": dict(touched=float((d.dn14 <= -x).mean()), of_those_positive_d14=float((d[d.dn14 <= -x].d14 > 0).mean()))
                    for x in (.10, .20, .30)}
    res["P3"][p] = float(((d.d14 >= .20) & (d.up72 < .20)).mean())
    bk = {"-3..+3%": d[(d.h6 >= -.03) & (d.h6 <= .03)], "+10..+25%": d[(d.h6 >= .10) & (d.h6 <= .25)], ">+25%": d[d.h6 > .25]}
    res["P4"][p] = {k: dict(n=int(len(v)), kept_runner=float(v.kept_runner.mean()) if len(v) else None,
                            after_h6_median=float(v.after_h6.median()) if len(v) else None) for k, v in bk.items()}
    res["P5"][p] = {}
    for s in ("beat_btc24", "newhigh6", "volhigh24"):
        yes, no = d[d[s] == True], d[d[s] == False]
        res["P5"][p][s] = dict(with_n=int(len(yes)), with_reach50=float(yes.reach50.mean()), without_reach50=float(no.reach50.mean()),
                               with_d14_median=float(yes.d14.median()), without_d14_median=float(no.d14.median()))
    res["P6"][p] = float(d.kept_runner.mean())
    res["first24h_peak"][p] = float((d.peak30_hour < 24).mean())
res["P6_by_mood"] = {m: dict(n=int(len(v)), kept_runner=float(v.kept_runner.mean())) for m, v in P.groupby("mood")}
P.to_csv(lib.HERE / "out" / "paths_alerts.csv.gz", index=False, compression="gzip")
(lib.HERE / "out" / "RESULT_paths.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
print(json.dumps(res, indent=1, default=float))

"""Study 2 PSYCH (PROTOCOL.md): alerts by previous-day Fear & Greed class; funding crowding for alerts and spike shorts.
Run after bear.py (uses out/bear_trades.csv.gz for the spike-short part)."""
import json, pickle
import numpy as np, pandas as pd
import lib

ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
F = lib.load_funding(); FS = {s: (g.ts.values, g.rate.values) for s, g in F.groupby("sym")}
def fund_at(sym, ts):
    if sym not in FS: return np.nan
    t, r = FS[sym]; k = np.searchsorted(t, np.datetime64(pd.Timestamp(ts).tz_convert(None)), side="right") - 1
    return r[k] if k >= 0 else np.nan
grp = lambda f: None if not np.isfinite(f) else ("crowded_longs" if f >= 0.0003 else ("crowded_shorts" if f < 0 else "normal"))
rows = []
for seg in ("disc", "hold"):
    sg = lib.Seg(seg); R = pickle.load(open(lib.CACHE / f"alerts_{seg}.pkl", "rb"))["R"]
    for r in R[R.kind == "event"].itertuples():
        e = r.e_t + 1; w = lib.window(sg, r.i, e, 336); ent = sg.O[r.i, e]
        if w is None or not (np.isfinite(ent) and ent > 0): continue
        k = int(np.nanargmax(w[0]))
        rows.append(dict(period=r.period, mood=r.mood, x4=r.x4, peak=w[0][k] / ent - 1, peak_hour=k, reach50=bool(w[0][k] >= 1.5 * ent),
                         funding=fund_at(r.sym, r.trigger_hour)))
D = pd.DataFrame(rows); D["fgroup"] = D.funding.map(grp)
def st(d): return dict(n=int(len(d)), peak_median=float(d.peak.median()), peak_hour_median=float(d.peak_hour.median()),
                       reach50=float(d.reach50.mean()), x4_mean=float(d.x4.mean()), x4_median=float(d.x4.median()))
res = {"n": int(len(D)), "missing_mood": int(D.mood.isna().sum()), "by_mood": {m: st(D[D.mood == m]) for m in ORDER},
       "by_mood_period": {p: {m: st(g[g.mood == m]) for m in ORDER if (g.mood == m).any()} for p, g in D.groupby("period")},
       "alerts_by_funding": {k: dict(n=int(len(g)), x4_mean=float(g.x4.mean()), peak_hour_median=float(g.peak_hour.median()))
                             for k, g in D.groupby("fgroup")},
       "alerts_with_funding": int(D.funding.notna().sum())}
eg = D[D.mood == "Extreme Greed"]
res["extreme_greed_by_funding"] = {k: dict(n=int(len(g)), x4_mean=float(g.x4.mean())) for k, g in eg.groupby("fgroup")}
TR = pd.read_csv(lib.HERE / "out" / "bear_trades.csv.gz")
for v in ("proxy", "perp"):
    s = TR[(TR.arm == "SHORT_SPIKE") & (TR.version == v)].copy(); s["fgroup"] = s.fund_entry.map(lambda f: grp(f) if pd.notna(f) else None)
    big = s[s.ret < -0.5]
    res[f"spike_shorts_{v}"] = dict(n=int(len(s)), by_funding={k: dict(n=int(len(g)), mean=float(g.ret.mean())) for k, g in s.groupby("fgroup")},
                                   losses_worse_than_50=int(len(big)), of_those_crowded_shorts=int((big.fgroup == "crowded_shorts").sum()),
                                   of_those_no_funding=int(big.fgroup.isna().sum()))
(lib.HERE / "out" / "RESULT_psych.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
print(json.dumps(res, indent=1, default=float))

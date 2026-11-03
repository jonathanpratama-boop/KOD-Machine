"""POST-RUN check (written after the studies ran; not part of the locked protocol; descriptive only).
Paths P5 measured from entry flatters strength signs (they include the early rise). Here: buy when the sign is
visible (close of hour 6 for newhigh6, close of hour 24 for beat_btc24 and volhigh24), hold to the day-14 close,
0.3% per side, same alerts as paths.py. Answers whether Hermes's "strength = worse typical result" holds when tradable."""
import json, pickle
import numpy as np, pandas as pd
import lib

C_ = lib.COST
rows = []
for seg in ("disc", "hold"):
    sg = lib.Seg(seg); det = lib.detect(sg); R = pickle.load(open(lib.CACHE / f"alerts_{seg}.pkl", "rb"))["R"]
    b = sg.idx.get("BTCUSDT")
    for r in R[R.kind == "event"].itertuples():
        i, t = r.i, r.e_t; e = t + 1; w = lib.window(sg, i, e, 720); ent = sg.O[i, e]
        if w is None or not (np.isfinite(ent) and ent > 0): continue
        hh, ll, cf, _ = w
        btc24 = sg.C[b, e + 23] / sg.O[b, e] - 1
        vol24 = np.nanmean(sg.Q[i, e:e + 24]) / det["base"][i, t]
        net = lambda a, z: z * (1 - C_) / (a * (1 + C_)) - 1
        rows.append(dict(period=r.period, newhigh6=bool(np.nanmax(hh[:6]) > sg.H[i, t]), beat_btc24=bool(cf[23] / ent - 1 > btc24),
                         volhigh24=bool(vol24 >= 3), from6=net(cf[5], cf[335]), from24=net(cf[23], cf[335]),
                         reach50_from6=bool(np.nanmax(hh[6:336]) >= 1.5 * cf[5]), reach50_from24=bool(np.nanmax(hh[24:336]) >= 1.5 * cf[23])))
P = pd.DataFrame(rows); res = {}
for p, d in P.groupby("period"):
    res[p] = {}
    for s, col, rc in (("newhigh6", "from6", "reach50_from6"), ("beat_btc24", "from24", "reach50_from24"), ("volhigh24", "from24", "reach50_from24")):
        y, n = d[d[s]], d[~d[s]]
        res[p][s] = dict(with_n=int(len(y)), with_median=float(y[col].median()), without_median=float(n[col].median()),
                         with_mean=float(y[col].mean()), without_mean=float(n[col].mean()),
                         with_reach50=float(y[rc].mean()), without_reach50=float(n[rc].mean()))
(lib.HERE / "out" / "POST_CHECK_strength_from_sign.json").write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))

"""Study 4 SPIKE_DEFAULT (PROTOCOL.md): 18 quick-exit versions on alerts and on both control sets.
Extreme Greed (previous-day class) alerts and controls: take-profit doubled, time limit 336h."""
import itertools, json, pickle
import numpy as np, pandas as pd
import lib

VERS = [(tp, sl, mh) for tp, sl, mh in itertools.product((.10, .15, .20), (-.10, -.15, None), (72, 168))]
rows = []
for seg in ("disc", "hold"):
    sg = lib.Seg(seg); R = pickle.load(open(lib.CACHE / f"alerts_{seg}.pkl", "rb"))["R"]
    for r in R.itertuples():
        i, e = r.i, r.e_t + 1; ent = sg.O[i, e]; eg = r.mood == "Extreme Greed"
        o = dict(seg=seg, kind=r.kind, period=r.period, year=r.year, eg=eg, X4=r.x4, HOLD72=lib.sim_exit(sg, i, e, ent, None, None, 72))
        for tp, sl, mh in VERS:
            k = f"TP{int(tp*100)}_SL{'none' if sl is None else int(-sl*100)}_{mh}h"
            o[k] = lib.sim_exit(sg, i, e, ent, 2 * tp if eg else tp, sl, 336 if eg else mh)
            o[k + "_noEG"] = lib.sim_exit(sg, i, e, ent, tp, sl, mh) if eg else o[k]
        rows.append(o)
D = pd.DataFrame(rows)
COLS = ["X4", "HOLD72"] + [f"TP{int(tp*100)}_SL{'none' if sl is None else int(-sl*100)}_{mh}h" for tp, sl, mh in VERS]
PER = ["2020-21", "2022", "2023-26"]
res = {"n": D.groupby("kind").size().to_dict(), "table": {}, "by_year_main": {}, "eg_effect": {}}
for c in COLS:
    res["table"][c] = {}
    for kind in ("event", "control", "control_past"):
        d = D[D.kind == kind]
        res["table"][c][kind] = {p: dict(n=int(d[d.period == p][c].notna().sum()), mean=float(d[d.period == p][c].mean()),
                                         median=float(d[d.period == p][c].median()), win=float((d[d.period == p][c] > 0).mean()))
                                 for p in PER}
    if c not in ("X4", "HOLD72"):
        e = D[D.kind == "event"]
        res["eg_effect"][c] = {p: float(e[e.period == p][c].mean() - e[e.period == p][c + "_noEG"].mean()) for p in PER}
e = D[D.kind == "event"]
res["by_year_main"] = {int(y): float(g["TP15_SL10_72h"].mean()) for y, g in e.groupby("year")}
quick = [c for c in COLS if c not in ("X4",)]
res["best_2023_26"] = max(quick, key=lambda c: res["table"][c]["event"]["2023-26"]["mean"])
res["any_positive_mean"] = {c: [p for p in PER if res["table"][c]["event"][p]["mean"] > 0] for c in quick}
res["alerts_minus_random_2023_26"] = {c: dict(vs_hermes_controls=res["table"][c]["event"]["2023-26"]["mean"] - res["table"][c]["control"]["2023-26"]["mean"],
                                              vs_past_only_controls=res["table"][c]["event"]["2023-26"]["mean"] - res["table"][c]["control_past"]["2023-26"]["mean"])
                                      for c in COLS}
D.to_csv(lib.HERE / "out" / "spike_default_trades.csv.gz", index=False, compression="gzip")
(lib.HERE / "out" / "RESULT_spike_default.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
for c in COLS:
    t = res["table"][c]
    print(f"{c:22s}", " ".join(f"{p}:{t['event'][p]['mean']:+.4f}" for p in PER), f"| rnd23-26 {t['control']['2023-26']['mean']:+.4f} past-only {t['control_past']['2023-26']['mean']:+.4f}")
print("best", res["best_2023_26"], "by year main", res["by_year_main"])

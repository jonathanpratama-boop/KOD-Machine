"""Build alerts/controls for both segments and run the PROTOCOL validation gate against Hermes's pushed numbers.
Writes VALIDATION.json and raw/cache/alerts_<seg>.pkl (per-alert and per-control rows used by the studies)."""
import json, pickle, sys
import numpy as np, pandas as pd
import lib

fng_v, fng_c = lib.load_fng()
out, tables = {}, {}
for seg in ("disc", "hold"):
    sg = lib.Seg(seg); det = lib.detect(sg)
    ev, ct, ct2 = lib.events_and_controls(sg, det)
    daily = lib.load_daily(set(sg.syms))
    rows = []
    for kind, lst in (("event", [(i, e) for i, e, s in ev if s == "OK"]), ("control", ct), ("control_past", ct2)):
        for i, e_t in lst:
            e = e_t + 1; ent = sg.O[i, e]; entc = ent * (1 + lib.COST)
            hh, cl = sg.H[i, e:e + 72], sg.C[i, e:e + 72]
            f = lib.clues(sg, daily, i, e_t)
            prev = sg.grid[e_t].normalize() - pd.Timedelta(days=1)
            rows.append(dict(kind=kind, i=i, sym=sg.syms[i], e_t=e_t, trigger_hour=str(sg.grid[e_t]), year=sg.grid[e_t].year,
                             mfe72=np.nanmax(hh) / entc - 1,
                             net72=cl[71] * (1 - lib.COST) / entc - 1 if np.isfinite(cl[71]) else np.nan,
                             score=lib.score(f), trend=lib.trend(f), x4=lib.x4(sg, i, e, ent),
                             fng=float(fng_v.get(prev, np.nan)), mood=fng_c.get(prev, None), **f))
    R = pd.DataFrame(rows)
    R["period"] = np.where(R.year <= 2021, "2020-21", np.where(R.year == 2022, "2022", "2023-26"))
    pickle.dump(dict(R=R, ev_all=ev), open(lib.CACHE / f"alerts_{seg}.pkl", "wb"), protocol=4)
    E, K = R[R.kind == "event"], R[R.kind == "control"]
    o = dict(symbols=len(sg.syms), hourly_files=sg.nfiles, grid=[str(sg.grid[0]), str(sg.grid[-1])],
             events_total=len(ev), events_ok=int(len(E)), controls=int(len(K)), controls_past_only=int((R.kind == "control_past").sum()),
             hit30_72h=float((E.mfe72 >= .3).mean()), net72_mean=float(E.net72.mean()),
             x4={p: dict(n=int(g.x4.notna().sum()), mean=float(g.x4.mean())) for p, g in E.groupby("period")},
             x4_random={p: dict(n=int(g.x4.notna().sum()), mean=float(g.x4.mean())) for p, g in K.groupby("period")},
             x4_all=dict(n=int(E.x4.notna().sum()), mean=float(E.x4.mean())), x4_random_all=dict(n=int(K.x4.notna().sum()), mean=float(K.x4.mean())))
    a = E[(E.score >= 4) & E.x4.notna()]
    o["combo_A"] = dict(n=int(len(a)), mean=float(a.x4.mean()), median=float(a.x4.median()))
    out[seg] = o

def near(x, t, tol): return abs(x - t) <= tol
d, h = out["disc"], out["hold"]
checks = {
    "disc_alerts_5267": near(d["events_ok"], 5267, 0.02 * 5267),
    "disc_controls_26321": near(d["controls"], 26321, 0.02 * 26321),
    "disc_hit30_17.5pct": near(d["hit30_72h"], 0.1747, 0.005),
    "disc_net72_-4.1pct": near(d["net72_mean"], -0.0414, 0.005),
    "disc_x4_2020_21_+3.46pct": near(d["x4"]["2020-21"]["mean"], 0.0346, 0.005),
    "disc_x4_2022_-5.04pct": near(d["x4"]["2022"]["mean"], -0.0504, 0.005),
    "hold_alerts_x4_6971": near(h["x4_all"]["n"], 6971, 0.02 * 6971),
    "hold_x4_-2.95pct": near(h["x4_all"]["mean"], -0.0295, 0.005),
    "hold_comboA_968": near(h["combo_A"]["n"], 968, 0.02 * 968),
    "hold_comboA_+1.10pct": near(h["combo_A"]["mean"], 0.0110, 0.005),
}
out["checks"] = checks; out["gate"] = "PASS" if all(checks.values()) else "FAIL"
(lib.HERE / "VALIDATION.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
print(json.dumps(out, indent=1, default=float))
sys.exit(0 if out["gate"] == "PASS" else 1)

"""Study 1 ENTRY_TIMING (PROTOCOL.md). Same alerts, X4 exit from each entry's fill, 0.3% per side.
Intrabar fills (limit, breakout) start the 336h exit window at the next hour; open fills start it at the fill hour."""
import json, pickle
import numpy as np, pandas as pd
import lib

TP_NET = 1.5 * (1 - lib.COST) / (1 + lib.COST) - 1
fng_v, fng_c = lib.load_fng()
rows, early_rows, lead = [], [], {}
for seg in ("disc", "hold"):
    sg = lib.Seg(seg); det = lib.detect(sg); A_ = pickle.load(open(lib.CACHE / f"alerts_{seg}.pkl", "rb"))["R"]
    E = A_[A_.kind == "event"]
    O, H, L, C, T = sg.O, sg.H, sg.L, sg.C, sg.T
    for r in E.itertuples():
        i, t = r.i, r.e_t; A = C[i, t]; res = {}
        res["E0"] = lib.x4(sg, i, t + 1, O[i, t + 1])
        for x in (0.05, 0.10, 0.15):
            lim, v = A * (1 - x), None
            for k in range(t + 1, min(T, t + 73)):
                if np.isfinite(L[i, k]) and L[i, k] <= lim:
                    o = O[i, k]
                    v = lib.x4(sg, i, k, o) if np.isfinite(o) and o <= lim else lib.x4(sg, i, k + 1, lim)
                    break
            res[f"L{int(x * 100)}"] = v
        for hk in (6, 24):
            res[f"H{hk}"] = lib.x4(sg, i, t + hk + 1, O[i, t + hk + 1]) if t + hk + 1 < T and np.isfinite(C[i, t + hk]) and C[i, t + hk] >= A else None
        v, dip = None, None
        for k in range(t + 1, min(T, t + 73)):
            if dip is None and np.isfinite(L[i, k]) and L[i, k] <= .95 * A:
                dip = k; continue
            if dip is not None and np.isfinite(C[i, k]) and C[i, k] > A:
                v = lib.x4(sg, i, k + 1, O[i, k + 1]) if k + 1 < T else None; break
        res["DIP_RECLAIM"] = v
        v = None
        if t + 25 < T:
            d1 = np.nanmax(H[i, t + 1:t + 25]) if np.isfinite(H[i, t + 1:t + 25]).any() else np.nan
            for k in range(t + 25, min(T, t + 97)):
                if np.isfinite(d1) and np.isfinite(H[i, k]) and H[i, k] > d1:
                    o = O[i, k]
                    v = lib.x4(sg, i, k, o) if np.isfinite(o) and o >= d1 else lib.x4(sg, i, k + 1, d1)
                    break
        res["BREAK_D1"] = v
        w = lib.window(sg, i, t + 1, 336); ent = O[i, t + 1]
        pk = pkh = np.nan
        if w is not None and np.isfinite(ent) and ent > 0:
            pkh = int(np.nanargmax(w[0])); pk = w[0][pkh] / ent - 1
        pull = np.nanmin(L[i, t + 1:t + 73]) / A - 1
        rows.append(dict(seg=seg, sym=r.sym, trigger_hour=r.trigger_hour, period=r.period, strong=r.score >= 4, trend=r.trend,
                         peak14=pk, peak_hour14=pkh, pullback72=pull, **res))
    # EARLY alarm: +5% in 1h on 5x volume, other filters as the alert
    de = lib.detect(sg, ret_h=1, ret_min=0.05)
    ev, _, _ = lib.events_and_controls(sg, de, n_ctrl=0)
    daily = lib.load_daily(set(sg.syms)); trig = det["trig"]
    for i, t, s in ev:
        if s != "OK":
            continue
        f = lib.clues(sg, daily, i, t); yr = sg.grid[t].year
        full = bool(trig[i, t:min(T, t + 72)].any())
        early_rows.append(dict(seg=seg, sym=sg.syms[i], period="2020-21" if yr <= 2021 else ("2022" if yr == 2022 else "2023-26"),
                               strong=lib.score(f) >= 4, trend=lib.trend(f), EARLY=lib.x4(sg, i, t + 1, O[i, t + 1]), becomes_full=full))
    # how often an EARLY alarm on the same coin came before each standard alert (within the previous 72h)
    et = np.zeros_like(trig)
    for i, t, s in ev:
        et[i, t] = True
    for r in E.itertuples():
        w_ = et[r.i, max(0, r.e_t - 72):r.e_t]
        lead.setdefault(r.period, []).append(72 - int(np.argmax(w_)) if w_.any() else None)
D = pd.DataFrame(rows); X = pd.DataFrame(early_rows)
D["good"] = D.E0 >= TP_NET - 1e-9
ENTRIES = ["E0", "L5", "L10", "L15", "H6", "H24", "DIP_RECLAIM", "BREAK_D1"]
PER = ["2020-21", "2022", "2023-26"]
res = {"n_alerts": int(len(D)), "table": {}, "early": {}, "shape": {}}
for g, m in (("all", D.index == D.index), ("strong", D.strong), ("trend", D.trend)):
    res["table"][g] = {}
    for en in ENTRIES:
        res["table"][g][en] = {}
        for p in PER:
            d = D[m & (D.period == p)]; v = d[en].dropna(); good = d[d.good]
            res["table"][g][en][p] = dict(n=int(len(v)), mean=float(v.mean()) if len(v) else None, median=float(v.median()) if len(v) else None,
                                          pct_profit=float((v > 0).mean()) if len(v) else None,
                                          good_moves=int(len(good)), good_skipped=float(good[en].isna().mean()) if len(good) else None)
    res["early"][g] = {}
    mx = X.index == X.index if g == "all" else X[g]
    for p in PER:
        v = X[mx & (X.period == p)]
        res["early"][g][p] = dict(n=int(v.EARLY.notna().sum()), mean=float(v.EARLY.mean()), median=float(v.EARLY.median()),
                                  becomes_full=float(v.becomes_full.mean()))
for p in PER:
    d = D[D.period == p]; gd = d[d.good]; l = [x for x in lead[p] if x is not None]
    res["shape"][p] = dict(peak14_median=float(d.peak14.median()), peak_hour14_median=float(d.peak_hour14.median()),
                           pullback72_median_all=float(d.pullback72.median()), pullback72_median_good=float(gd.pullback72.median()),
                           alerts_with_prior_early_alarm=float(len(l) / len(lead[p])), early_lead_hours_median=float(np.median(l)) if l else None)
D.to_csv(lib.HERE / "out" / "entry_timing_trades.csv.gz", index=False, compression="gzip")
(lib.HERE / "out" / "RESULT_entry_timing.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
print(json.dumps({"shape": res["shape"], "early_all": res["early"]["all"]}, indent=1, default=float))
for g in ("all", "strong", "trend"):
    for en in ENTRIES:
        print(g, en, {p: (res["table"][g][en][p]["n"], round(res["table"][g][en][p]["mean"] or 0, 4), round(res["table"][g][en][p]["median"] or 0, 4),
                          res["table"][g][en][p]["good_skipped"]) for p in PER})

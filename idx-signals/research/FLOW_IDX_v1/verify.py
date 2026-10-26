"""Independent verifier for FLOW_IDX_v1 (PROTOCOL.md, "Rehearsal, verification, record").

It does not import idxsig.flow_features or idxsig.lead_ladder. It recomputes the eight flow features per ticker from
the raw mirror files with its own code and requires them to equal the runner's arrays; recomputes the episode, lead
session, void, hot and pool checks and the tail counts of a seeded sample of event rows (LEAD_LADDER_v1's verify_v2
checks, loaded by path); and recomputes every lift, lower bound, per-year lift, gate and verdict from the per-event
tables.

    python3 research/FLOW_IDX_v1/verify.py rehearsal | stage1 | stage2
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zlib
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from idxsig.provenance import MANIFESTS, read_manifest  # noqa: E402

_spec = importlib.util.spec_from_file_location("ladder_v1_verify", HERE.parent / "LEAD_LADDER_v1" / "verify_v2.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
import run  # noqa: E402  (loader of the pinned study only; its ladder code is not used below)

PROTO, L = run.PROTO, run.LADDER
NAMES = ("fnet5", "fnet20", "fpart20", "bidq1", "bidq5", "bidx1", "blk5", "blk20")
COLS = ["date", "volume", "value", "foreign_buy", "foreign_sell", "bid_volume", "offer_volume", "non_regular_value"]


def own_features(study):
    dates = pd.DatetimeIndex(np.asarray(study.dates).astype("datetime64[ns]"))
    tick = [str(t) for t in study.m.tickers]
    pos = {t: i for i, t in enumerate(tick)}
    F = {k: np.full((len(tick), len(dates)), np.nan) for k in NAMES}
    _, records = read_manifest(MANIFESTS / PROTO["raw_manifest"])
    last = pd.Timestamp(PROTO["last_row_date"])
    for rec in records:
        if "ticker" not in rec or rec["ticker"] not in pos:
            continue
        i = pos[rec["ticker"]]
        d = pd.read_csv(ROOT / rec["path"], usecols=COLS)
        d["date"] = pd.to_datetime(d["date"].str[:10])
        d = d[d["date"] <= last].drop_duplicates("date", keep="last").set_index("date").reindex(dates)
        tr = pd.Series(study.m.tradeable[i], index=dates)
        vol, val, fb, fs, bv, ov, nrv = (d[c].where(tr) for c in COLS[1:])
        rs = lambda x, w, mn: x.rolling(w, min_periods=mn).sum()  # noqa: E731
        F["fnet5"][i] = (rs(fb - fs, 5, 4) / rs(vol, 5, 4)).where(rs(vol, 5, 4) > 0).to_numpy()
        F["fnet20"][i] = (rs(fb - fs, 20, 15) / rs(vol, 20, 15)).where(rs(vol, 20, 15) > 0).to_numpy()
        F["fpart20"][i] = (rs(fb + fs, 20, 15) / (2 * rs(vol, 20, 15))).where(rs(vol, 20, 15) > 0).to_numpy()
        q = (bv / (bv + ov)).where((bv + ov) > 0)
        F["bidq1"][i] = q.to_numpy()
        F["bidq5"][i] = q.rolling(5, min_periods=3).mean().to_numpy()
        med = vol.rolling(20, min_periods=10).median().shift(1)
        F["bidx1"][i] = np.log10((bv + 1) / (med + 1)).to_numpy()
        for name, w, mn in (("blk5", 5, 4), ("blk20", 20, 15)):
            num = rs(nrv, w, mn)
            den = rs(val, w, mn) + num
            F[name][i] = (num / den).where(den > 0).to_numpy()
    return F


class FlowWorld(base.World):
    def __init__(self, study, feats, window):
        m = study.m
        self.L = study.level
        hist = np.cumsum(m.present, axis=1) - m.present
        self.elig = m.tradeable & m.present & (m.prev > 0) & (hist >= L["min_history"])
        self.buckets = [study.buckets[k] for k in L["pool"]["buckets"]]
        self.sig, self.binary = feats, set()
        self.vol20 = study.sig["vol20"]
        self.lo, self.hi = m.bounds(*PROTO["windows"][window])
        self._q = {}

    def ext_at(self, u):
        return np.array([base.is_extended(self.L, c, u) if self.elig[c, u] else False for c in range(self.L.shape[0])])

    def hot_at(self, u, ext):
        ok = self.elig[:, u] & ~ext
        x = self.vol20[ok, u]
        x = x[np.isfinite(x)]
        if len(x) < 20:
            return np.zeros(self.L.shape[0], dtype=bool)
        return np.isfinite(self.vol20[:, u]) & (self.vol20[:, u] >= np.quantile(x, PROTO["hot"]["quantile"]))

    def family_pool(self, n, u, t, kind, voided, hot):
        ext = self.ext_at(u)
        ok = self.elig[:, u].copy()
        recent = np.zeros(len(ok), dtype=bool)
        for s in range(u, t + 1):
            recent |= self.q_column(kind, s)
        ok &= ~recent
        if voided:
            ok &= ~ext
        hotv = self.hot_at(u, ext) if hot else None
        if hot:
            ok &= hotv
        ok[n] = False
        cand = np.flatnonzero(ok)
        for level in range(len(self.buckets), -1, -1):
            p = cand
            for b in self.buckets[:level]:
                p = p[b[p, u] == b[n, u]]
            if len(p) >= L["pool"]["min_size"] or level == 0:
                return p, (bool(hotv[n]) if hot else True), ext
        return cand, (bool(hotv[n]) if hot else True), ext


def check_rows(out_dir, window, placebo, w, sample):
    errors = []
    rng = np.random.default_rng(L["bootstrap"]["seed"] + (1 if window == "validation" else 0))
    for fam in PROTO["families"]:
        tab = pd.read_csv(out_dir / f"events_{fam}_{window}.csv.gz", keep_default_na=False, na_values=[""], dtype={"ticker": str})
        for i in rng.choice(len(tab), size=min(sample // 4, len(tab)), replace=False):
            r = tab.iloc[i]
            n, t, u, kind, voided = int(r["name_idx"]), int(r["t"]), int(r["u"]), r["kind"], r["analysis"] == "void"
            kd, sep = L["kinds"][kind], L["separation_sessions"]
            if not (placebo and kind in L["pairs"]):
                if not w.q(kind, n, t) or any(w.q(kind, n, s) for s in range(max(0, t - sep), t)) \
                        or not (w.lo + sep <= t < w.hi - kd["horizon"]) or not w.elig[n, t]:
                    errors.append(f"{fam} {window} row {i}: episode start")
            if u != t - int(r["lead"]) or not w.elig[n, u] or (voided and base.is_extended(w.L, n, u)):
                errors.append(f"{fam} {window} row {i}: lead session")
            pool, event_hot, _ = w.family_pool(n, u, t, kind, voided, fam == "IDX_HOT")
            if not event_hot:
                errors.append(f"{fam} {window} row {i}: event not hot at u")
            if len(pool) != int(r["pool_size"]):
                errors.append(f"{fam} {window} row {i}: pool {len(pool)} vs {r['pool_size']}")
                continue
            for f in [c.split("|")[0] for c in tab.columns if c.endswith("|auc") and pd.notna(r[c])]:
                v, xs = w.sig[f][n, u], w.sig[f][pool, u]
                xs = xs[np.isfinite(xs)]
                hi, lo = np.quantile(xs, 0.9), np.quantile(xs, 0.1)
                for tail, (I, E) in {"top": (float(v > hi), float(np.mean(xs > hi))), "bottom": (float(v < lo), float(np.mean(xs < lo)))}.items():
                    if abs(I - float(r[f"{f}|{tail}|I"])) > 1e-9 or abs(E - float(r[f"{f}|{tail}|E"])) > 1e-9:
                        errors.append(f"{fam} {window} row {i} {f} {tail}")
    return errors


def lift_of(g, f, tail, key, z):
    I = g[f"{f}|{tail}|I"]
    sel = I.notna()
    I, E = I[sel].to_numpy(float), g.loc[sel, f"{f}|{tail}|E"].to_numpy(float)
    wk, yr = g.loc[sel, "_week"].to_numpy(), g.loc[sel, "_year"].to_numpy()
    lift = I.sum() / E.sum() if E.sum() > 0 else float("nan")
    uw, inv = np.unique(wk, return_inverse=True)
    Iw, Ew = np.bincount(inv, I, len(uw)), np.bincount(inv, E, len(uw))
    reps = L["bootstrap"]["resamples"]
    cnt = np.random.default_rng(L["bootstrap"]["seed"] + zlib.crc32(key.encode()) % 10**6).multinomial(
        len(uw), np.full(len(uw), 1.0 / len(uw)), size=reps)
    with np.errstate(divide="ignore", invalid="ignore"):
        bl = (cnt @ Iw) / (cnt @ Ew)
    good = np.isfinite(bl) & (bl > 0)
    se = float(np.std(np.log(bl[good]), ddof=1)) if good.sum() >= reps // 2 else float("inf")
    lower = float(np.exp(np.log(lift) - z * se)) if lift > 0 and np.isfinite(se) else 0.0
    years = {int(y): (int((yr == y).sum()), I[yr == y].sum() / E[yr == y].sum() if E[yr == y].sum() > 0 else None) for y in np.unique(yr)}
    return {"lift": lift, "lower": lower, "events": int(sel.sum()), "expected": float(E.sum()), "years": years}


def check_lifts(out_dir, window, z):
    errors, mine = [], {}
    lifts = pd.read_csv(out_dir / f"lifts_{window}.csv")
    for fam in PROTO["families"]:
        tab = pd.read_csv(out_dir / f"events_{fam}_{window}.csv.gz", keep_default_na=False, na_values=[""], dtype={"ticker": str})
        td = pd.DatetimeIndex(pd.to_datetime(tab["t_date"]))
        iso = td.isocalendar()
        tab["_week"], tab["_year"] = iso["year"].to_numpy() * 100 + iso["week"].to_numpy(), td.year
        for r in lifts[lifts["market"] == fam].itertuples(index=False):
            g = tab[(tab["kind"] == r.kind) & (tab["analysis"] == r.analysis) & (tab["lead"] == r.lead)]
            c = lift_of(g, r.feature, r.tail, f"{fam}|{r.kind}|{r.analysis}|{int(r.lead)}|{r.feature}|{r.tail}", z)
            if c["events"] != r.events or not np.isclose(c["lift"], r.lift, rtol=1e-8, equal_nan=True) \
                    or not np.isclose(c["lower"], r.lower_bound, rtol=1e-6, atol=1e-12):
                errors.append(f"lift {fam} {r.kind} {r.analysis} {r.lead} {r.feature} {r.tail}")
            mine[(fam, r.kind, r.analysis, int(r.lead), r.feature, r.tail)] = c
    return errors, mine


def stage1_gates(mine):
    gs = L["gates"]
    out = {}
    for (fam, kind, analysis, lead, f, tail), c in mine.items():
        if analysis != "void" or kind not in L["pairs"] or lead not in L["gated_leads"]:
            continue
        dl = mine[(fam, L["pairs"][kind], "void", lead, f, tail)]["lift"]
        yl = [ly for cnt, ly in c["years"].values() if cnt >= gs["G4_min_events_per_year"]]
        g = {"G1": c["lift"] >= gs["G1_min_lift"], "G2": c["lower"] > gs["G2_lower_bound_above"],
             "G3": bool(np.isfinite(dl) and c["lift"] >= gs["G3_min_ratio_to_down"] * dl),
             "G4": bool(yl) and all(v is not None and v >= gs["G4_min_lift_each_year"] for v in yl),
             "G5": c["events"] >= gs["G5_min_events"] and c["expected"] >= gs["G5_min_expected"]}
        out[(fam, kind, lead, f, tail)] = (all(g.values()), c["lift"])
    return out


def main():
    which = sys.argv[1]
    out_dir = HERE / {"rehearsal": "rehearsal", "stage1": "stage1", "stage2": "stage2"}[which]
    study, flows = run.load_world()
    feats = own_features(study)
    errors = []
    for k in NAMES:
        if not np.allclose(feats[k], flows[k], rtol=1e-9, atol=1e-12, equal_nan=True):
            errors.append(f"feature array {k} differs from the runner's")
    windows = ["discovery", "validation"] if which == "rehearsal" else (["discovery"] if which == "stage1" else ["validation"])
    summary = json.loads((out_dir / "summary.json").read_text())
    report = {"checked": which}
    p1z = PROTO["z_stage1"]
    for window in windows:
        w = FlowWorld(study, feats, window)
        errors += check_rows(out_dir, window, which == "rehearsal", w, PROTO["verifier_sample"])
        z = p1z
        if which == "stage2":
            m = len(json.loads((HERE / "stage1" / "frozen.json").read_text())["cells"])
            z = NormalDist().inv_cdf(1 - PROTO["stage2"]["V2_alpha"] / m)
        e, mine = check_lifts(out_dir, window, z)
        errors += e
        if window == "discovery":
            g1 = stage1_gates(mine)
            passes = sorted(k for k, (p, _) in g1.items() if p)
            if which == "rehearsal":
                if len(passes) != summary["stage1_cells_passing_G1_G5"]:
                    errors.append("rehearsal passing count differs")
                report["rehearsal_stage1_passing"] = len(passes)
            if which == "stage1":
                plc = run.placebo_lifts(HERE / "rehearsal" / "lifts_discovery.csv")
                final = sorted(k for k in passes if g1[k][1] >= PROTO["gates"]["G6_min_ratio_to_placebo"] * plc[k])
                frozen = sorted((c["family"], c["kind"], c["lead"], c["feature"], c["tail"])
                                for c in json.loads((out_dir / "frozen.json").read_text())["cells"])
                if final != frozen:
                    errors.append(f"frozen cells differ: {len(final)} vs {len(frozen)}")
                verdict = "FLOW_CANDIDATES" if final else "NO_FLOW_LEAD"
                if verdict != summary["result"]["verdict"]:
                    errors.append(f"verdict {summary['result']['verdict']} vs {verdict}")
                report["verdict_recomputed"], report["frozen"] = verdict, len(final)
        if which == "stage2":
            plc = run.placebo_lifts(HERE / "rehearsal" / "lifts_validation.csv")
            v = PROTO["stage2"]
            res = pd.read_csv(out_dir / "gates_validation.csv")
            passing = 0
            for r in res.itertuples(index=False):
                c = mine[(r.family, r.kind, "void", int(r.lead), r.feature, r.tail)]
                dl = mine[(r.family, L["pairs"][r.kind], "void", int(r.lead), r.feature, r.tail)]["lift"]
                testable = c["events"] >= v["V4_min_events"] and c["expected"] >= v["V4_min_expected"]
                ok = testable and c["lift"] >= v["V1_min_lift"] and c["lower"] > 1.0 and c["lift"] >= v["V3_min_ratio_to_down"] * dl \
                    and c["lift"] >= v["V5_min_ratio_to_placebo"] * plc[(r.family, r.kind, int(r.lead), r.feature, r.tail)]
                if bool(r.passes) != bool(ok):
                    errors.append(f"stage2 cell {r.family} {r.kind} {r.lead} {r.feature} {r.tail}: {r.passes} vs {ok}")
                passing += bool(ok)
            verdict = "FLOW_LEAD_VALIDATED" if passing else ("NOT_VALIDATED" if res["testable"].any() else "NOT_TESTABLE")
            if verdict != summary["result"]["verdict"]:
                errors.append(f"verdict {summary['result']['verdict']} vs {verdict}")
            report["verdict_recomputed"] = verdict
    report.update({"error_count": len(errors), "errors": errors[:100], "status": "VERIFIED" if not errors else "MISMATCH"})
    with (out_dir / "VERIFY.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "errors"}), *errors[:20], sep="\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

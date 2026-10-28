"""Independent verifier for LEAD_LADDER_v1 (PROTOCOL.md, "Run, verification and record"), version 2.

Supersedes verify.py, which crashed on its first run (its one-session check in q_column did not collapse the
window: a shape error, no result). That one line is the only change; verify.py stays as committed.

It does not import idxsig.lead_ladder or idxsig.void. From the pinned panels (through idxsig.e1.Study, whose features
and buckets are E1/E2's pinned code) it recomputes, for a seeded sample of event rows: the episode's kind, its start
condition, eligibility at the lead session, the void status, the pool and the tail counts. From the runner's own
per-event tables it recomputes every lift, expectation, per-year lift, bootstrap lower bound, gate and the verdict.

    python3 research/LEAD_LADDER_v1/verify_v2.py rehearsal
    python3 research/LEAD_LADDER_v1/verify_v2.py results
"""

from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

PROTO = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
TOL = 1e-9


def level_path_ok(L, n, t, horizon, direction, thr, max_day):
    base = L[n, t]
    if not np.isfinite(base):
        return False
    fut = L[n, t + 1: t + horizon + 1]
    fin = fut[np.isfinite(fut)]
    if not len(fin):
        return False
    hit = (fin.max() / base >= thr) if direction == "up" else (fin.min() / base <= 1.0 / thr)
    if not hit:
        return False
    if max_day is not None:
        seq = L[n, t: t + horizon + 1]
        for a, b in zip(seq[:-1], seq[1:]):
            if np.isfinite(a) and np.isfinite(b):
                r = b / a
                if direction == "up" and r > max_day:
                    return False
                if direction == "down" and r < 1.0 / max_day:
                    return False
    return True


def is_extended(L, n, u):
    vd = PROTO["void"]
    prior = L[n, max(0, u - vd["window"]): u]
    prior = prior[np.isfinite(prior)]
    if len(prior) < vd["min_periods"] or not np.isfinite(L[n, u]):
        return False
    return bool(L[n, u] > vd["threshold"] * np.median(prior))


class World:
    def __init__(self, market):
        import run  # the runner's loader only builds the pinned study; nothing of its ladder is used below

        lad, study, meta = run.build(market)
        m = study.m
        self.L = study.level
        self.present, self.tradeable, self.prev = m.present, m.tradeable, m.prev
        hist = np.cumsum(m.present, axis=1) - m.present
        self.elig = m.tradeable & m.present & (m.prev > 0) & (hist >= PROTO["min_history"])
        self.buckets = [study.buckets[k] for k in PROTO["pool"]["buckets"]]
        self.sig = study.sig
        self.binary = set(study.binary)
        self.lo, self.hi = m.bounds(*PROTO["markets"][market]["window"])
        self._q = {}

    def q(self, kind, n, t):
        key = (kind, n, t)
        if key not in self._q:
            kd = PROTO["kinds"][kind]
            self._q[key] = level_path_ok(self.L, n, t, kd["horizon"], kd["direction"], kd["threshold"], kd["max_day"])
        return self._q[key]

    def q_column(self, kind, t):
        kd = PROTO["kinds"][kind]
        L = self.L
        H = kd["horizon"]
        base = L[:, t]
        fut = L[:, t + 1: t + H + 1]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = fut / base[:, None]
            if kd["direction"] == "up":
                best = np.nanmax(np.where(np.isfinite(r), r, -np.inf), axis=1)
                hit = best >= kd["threshold"]
            else:
                best = np.nanmin(np.where(np.isfinite(r), r, np.inf), axis=1)
                hit = best <= 1.0 / kd["threshold"]
            ok = np.isfinite(r).any(axis=1) & np.isfinite(base) & hit
            if kd["max_day"] is not None:
                seq = L[:, t: t + H + 1]
                st = seq[:, 1:] / seq[:, :-1]
                bad = (st > kd["max_day"]) if kd["direction"] == "up" else (st < 1.0 / kd["max_day"])
                ok &= ~bad.any(axis=1)  # NaN comparisons are False: a gap is not checked
        return ok

    def pool(self, n, u, t, kind, voided):
        names = np.arange(self.L.shape[0])
        ok = self.elig[:, u].copy()
        recent = np.zeros(len(names), dtype=bool)
        for s in range(u, t + 1):
            recent |= self.q_column(kind, s)
        ok &= ~recent
        if voided:
            ext = np.array([is_extended(self.L, c, u) if ok[c] else False for c in names])
            ok &= ~ext
        ok[n] = False
        cand = names[ok]
        for level in range(len(self.buckets), -1, -1):
            p = cand
            for b in self.buckets[:level]:
                p = p[b[p, u] == b[n, u]]
            if len(p) >= PROTO["pool"]["min_size"] or level == 0:
                return p
        return cand


def check_rows(out_dir: Path, sample: int, placebo: bool) -> list[str]:
    errors = []
    rng = np.random.default_rng(PROTO["bootstrap"]["seed"])
    for market in PROTO["markets"]:
        path = out_dir / f"events_{market}.csv.gz"
        if not path.exists():
            continue
        tab = pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={"ticker": str})
        w = World(market)
        idx = rng.choice(len(tab), size=min(sample // len(PROTO["markets"]), len(tab)), replace=False)
        for i in idx:
            r = tab.iloc[i]
            n, t, u, kind, voided = int(r["name_idx"]), int(r["t"]), int(r["u"]), r["kind"], r["analysis"] == "void"
            real_event = not (placebo and kind in PROTO["pairs"])
            if real_event:
                kd = PROTO["kinds"][kind]
                sep = PROTO["separation_sessions"]
                if not w.q(kind, n, t):
                    errors.append(f"{market} row {i}: {kind} does not qualify at t")
                if any(w.q(kind, n, s) for s in range(max(0, t - sep), t)):
                    errors.append(f"{market} row {i}: an earlier {kind} session within {sep}")
                if not (w.lo + sep <= t < w.hi - kd["horizon"]) or not w.elig[n, t]:
                    errors.append(f"{market} row {i}: start outside the window or not eligible")
            if u != t - int(r["lead"]) or not w.elig[n, u]:
                errors.append(f"{market} row {i}: lead session wrong or not eligible")
            if voided and is_extended(w.L, n, u):
                errors.append(f"{market} row {i}: extended event kept in the void analysis")
            pool = w.pool(n, u, t, kind, voided)
            if len(pool) != int(r["pool_size"]):
                errors.append(f"{market} row {i}: pool {len(pool)} vs {r['pool_size']}")
                continue
            feats = [c.split("|")[0] for c in tab.columns if c.endswith("|auc") and pd.notna(r[c])]
            for f in feats:
                v = w.sig[f][n, u]
                xs = w.sig[f][pool, u]
                xs = xs[np.isfinite(xs)]
                if f in w.binary:
                    exp = {"top": (float(v == 1), float(np.mean(xs == 1)))}
                else:
                    hi, lo = np.quantile(xs, PROTO["tails"]["top_quantile"]), np.quantile(xs, PROTO["tails"]["bottom_quantile"])
                    exp = {"top": (float(v > hi), float(np.mean(xs > hi))), "bottom": (float(v < lo), float(np.mean(xs < lo)))}
                for tail, (I, E) in exp.items():
                    if abs(I - float(r[f"{f}|{tail}|I"])) > TOL or abs(E - float(r[f"{f}|{tail}|E"])) > TOL:
                        errors.append(f"{market} row {i} {f} {tail}: ({I}, {E}) vs ({r[f'{f}|{tail}|I']}, {r[f'{f}|{tail}|E']})")
    return errors


def check_aggregates(out_dir: Path) -> tuple[list[str], dict]:
    errors = []
    lifts = pd.read_csv(out_dir / "lifts.csv")
    gates = pd.read_csv(out_dir / "gates.csv")
    z, reps, gs = PROTO["z_one_sided"], PROTO["bootstrap"]["resamples"], PROTO["gates"]
    mine = {}
    for market in lifts["market"].unique():
        tab = pd.read_csv(out_dir / f"events_{market}.csv.gz", keep_default_na=False, na_values=[""], dtype={"ticker": str})
        td = pd.DatetimeIndex(pd.to_datetime(tab["t_date"]))
        iso = td.isocalendar()
        tab["_week"] = iso["year"].to_numpy() * 100 + iso["week"].to_numpy()
        tab["_year"] = td.year
        for r in lifts[lifts["market"] == market].itertuples(index=False):
            g = tab[(tab["kind"] == r.kind) & (tab["analysis"] == r.analysis) & (tab["lead"] == r.lead)]
            I = g[f"{r.feature}|{r.tail}|I"]
            sel = I.notna()
            I, E = I[sel].to_numpy(float), g.loc[sel, f"{r.feature}|{r.tail}|E"].to_numpy(float)
            lift = I.sum() / E.sum() if E.sum() > 0 else float("nan")
            weeks = g.loc[sel, "_week"].to_numpy()
            uw, inv = np.unique(weeks, return_inverse=True)
            Iw, Ew = np.bincount(inv, I, len(uw)), np.bincount(inv, E, len(uw))
            seed = PROTO["bootstrap"]["seed"] + zlib.crc32(f"{market}|{r.kind}|{r.analysis}|{int(r.lead)}|{r.feature}|{r.tail}".encode()) % 10**6
            cnt = np.random.default_rng(seed).multinomial(len(uw), np.full(len(uw), 1.0 / len(uw)), size=reps)
            with np.errstate(divide="ignore", invalid="ignore"):
                bl = (cnt @ Iw) / (cnt @ Ew)
            good = np.isfinite(bl) & (bl > 0)
            se = float(np.std(np.log(bl[good]), ddof=1)) if good.sum() >= reps // 2 else float("inf")
            lower = float(np.exp(np.log(lift) - z * se)) if lift > 0 and np.isfinite(se) else 0.0
            years = {}
            for y in np.unique(g.loc[sel, "_year"]):
                ys = g.loc[sel, "_year"].to_numpy() == y
                years[str(int(y))] = (int(ys.sum()), I[ys].sum() / E[ys].sum() if E[ys].sum() > 0 else None)
            ry = json.loads(r.years)
            for y, (cnt_y, ly) in years.items():
                if ry[y]["events"] != cnt_y or (ly is None) != (ry[y]["lift"] is None) or (ly is not None and abs(ly - ry[y]["lift"]) > 1e-6 * max(1, ly)):
                    errors.append(f"{market} {r.kind} {r.analysis} {r.lead} {r.feature} {r.tail}: year {y}")
            if int(r.events) != int(sel.sum()) or not np.isclose(lift, r.lift, rtol=1e-8, equal_nan=True) \
                    or not np.isclose(lower, r.lower_bound, rtol=1e-6, atol=1e-12):
                errors.append(f"{market} {r.kind} {r.analysis} {r.lead} {r.feature} {r.tail}: lift {lift} lower {lower} vs {r.lift} {r.lower_bound}")
            mine[(market, r.kind, r.analysis, int(r.lead), r.feature, r.tail)] = (lift, lower, int(sel.sum()), E.sum(), years)
    passing = []
    for r in gates.itertuples(index=False):
        lift, lower, n, e, years = mine[(r.market, r.kind, "void", int(r.lead), r.feature, r.tail)]
        down = PROTO["pairs"][r.kind]
        dl = mine.get((r.market, down, "void", int(r.lead), r.feature, r.tail), (float("nan"),))[0]
        yl = [ly for c, ly in years.values() if c >= gs["G4_min_events_per_year"]]
        g = {"G1": lift >= gs["G1_min_lift"], "G2": lower > gs["G2_lower_bound_above"],
             "G3": bool(np.isfinite(dl) and lift >= gs["G3_min_ratio_to_down"] * dl),
             "G4": bool(yl) and all(v is not None and v >= gs["G4_min_lift_each_year"] for v in yl),
             "G5": n >= gs["G5_min_events"] and e >= gs["G5_min_expected"]}
        for k, v in g.items():
            if bool(getattr(r, k)) != bool(v):
                errors.append(f"gate {k} {r.market} {r.kind} {r.lead} {r.feature} {r.tail}: {getattr(r, k)} vs {v}")
        if all(g.values()):
            passing.append(r.market)
    confirming = {m for m, v in PROTO["markets"].items() if v["can_confirm"]}
    verdict = "LEAD_FOUND" if confirming & set(passing) else ("LEAD_US_ONLY" if passing else "NO_DAYS_AHEAD_LEAD")
    expected_cells = sum(1 for _ in gates.itertuples())
    return errors, {"verdict": verdict, "cells_passing": len(passing), "cells_gated": expected_cells}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "results"
    out_dir = HERE / which
    errors = check_rows(out_dir, PROTO["verifier_sample"], placebo=(which == "rehearsal"))
    agg_errors, mine = check_aggregates(out_dir)
    errors += agg_errors
    summary = json.loads((out_dir / "summary.json").read_text())
    if summary["result"]["verdict"] != mine["verdict"]:
        errors.append(f"verdict {summary['result']['verdict']} vs {mine['verdict']}")
    report = {"checked": which, "row_sample": PROTO["verifier_sample"], "verdict_recomputed": mine["verdict"],
              "cells_gated": mine["cells_gated"], "cells_passing": mine["cells_passing"],
              "errors": errors[:200], "error_count": len(errors), "status": "VERIFIED" if not errors else "MISMATCH"}
    path = out_dir / "VERIFY.json"
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2, default=float) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "errors"}, indent=1), *errors[:20], sep="\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

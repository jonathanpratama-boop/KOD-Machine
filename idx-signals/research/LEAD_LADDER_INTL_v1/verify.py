"""Independent verifier for LEAD_LADDER_INTL_v1 (PROTOCOL.md).

Rows: a seeded sample of event rows is recomputed from the panels with LEAD_LADDER_v1's verify_v2.py checks
(episode kind, start, eligibility, void status, pool, tail counts), which do not import idxsig.lead_ladder; arrays
come from idxsig.e1.Study. Aggregates: every pooled lift, lower bound, per-year lift, gate and the verdict are
recomputed from the per-event tables with code written here.

    python3 research/LEAD_LADDER_INTL_v1/verify.py rehearsal|results
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
sys.path.insert(0, str(HERE.parent / "LEAD_LADDER_v1"))
sys.path.insert(0, str(HERE))

import verify_v2 as base  # noqa: E402

PROTO = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
L = json.loads((ROOT / PROTO["ladder_protocol"]).read_text(encoding="utf-8"))
L["pool"]["buckets"] = PROTO["pool_buckets"]
base.PROTO = L  # the row checks read kinds, void, pool and tails from the ladder protocol


class World(base.World):
    def __init__(self, market):
        import run as intl_run

        _, study, _, _ = intl_run.build_market(market)
        m = study.m
        self.L = study.level
        hist = np.cumsum(m.present, axis=1) - m.present
        self.elig = m.tradeable & m.present & (m.prev > 0) & (hist >= L["min_history"])
        self.buckets = [study.buckets[k] for k in PROTO["pool_buckets"]]
        self.sig, self.binary = study.sig, set(study.binary)
        self.lo, self.hi = m.bounds(*PROTO["periods"]["discovery"])
        self._q = {}


def check_rows(out_dir, placebo):
    errors = []
    rng = np.random.default_rng(L["bootstrap"]["seed"])
    per = max(1, PROTO["verifier_sample"] // len(PROTO["markets"]))
    for market in PROTO["markets"]:
        tab = pd.read_csv(out_dir / f"events_{market}.csv.gz", keep_default_na=False, na_values=[""], dtype={"ticker": str})
        w = World(market)
        for i in rng.choice(len(tab), size=min(per, len(tab)), replace=False):
            r = tab.iloc[i]
            n, t, u, kind, voided = int(r["name_idx"]), int(r["t"]), int(r["u"]), r["kind"], r["analysis"] == "void"
            if not (placebo and kind in L["pairs"]):
                kd, sep = L["kinds"][kind], L["separation_sessions"]
                if not w.q(kind, n, t) or any(w.q(kind, n, s) for s in range(max(0, t - sep), t)) \
                        or not (w.lo + sep <= t < w.hi - kd["horizon"]) or not w.elig[n, t]:
                    errors.append(f"{market} row {i}: episode start")
            if u != t - int(r["lead"]) or not w.elig[n, u] or (voided and base.is_extended(w.L, n, u)):
                errors.append(f"{market} row {i}: lead session")
            pool = w.pool(n, u, t, kind, voided)
            if len(pool) != int(r["pool_size"]):
                errors.append(f"{market} row {i}: pool {len(pool)} vs {r['pool_size']}")
                continue
            for f in [c.split("|")[0] for c in tab.columns if c.endswith("|auc") and pd.notna(r[c])]:
                v, xs = w.sig[f][n, u], w.sig[f][pool, u]
                xs = xs[np.isfinite(xs)]
                if f in w.binary:
                    exp = {"top": (float(v == 1), float(np.mean(xs == 1)))}
                else:
                    hi, lo = np.quantile(xs, 0.9), np.quantile(xs, 0.1)
                    exp = {"top": (float(v > hi), float(np.mean(xs > hi))), "bottom": (float(v < lo), float(np.mean(xs < lo)))}
                for tail, (I, E) in exp.items():
                    if abs(I - float(r[f"{f}|{tail}|I"])) > 1e-9 or abs(E - float(r[f"{f}|{tail}|E"])) > 1e-9:
                        errors.append(f"{market} row {i} {f} {tail}")
    return errors


def lift_of(g, f, tail, key):
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
    years = {int(y): (int((yr == y).sum()), I[yr == y].sum() / E[yr == y].sum() if E[yr == y].sum() > 0 else None) for y in np.unique(yr)}
    return lift, se, int(sel.sum()), E.sum(), years


def gates(lift, se, n, e, years, down, z):
    gs = L["gates"]
    lower = float(np.exp(np.log(lift) - z * se)) if lift > 0 and np.isfinite(se) else 0.0
    yl = [ly for c, ly in years.values() if c >= gs["G4_min_events_per_year"]]
    g = {"G1": lift >= gs["G1_min_lift"], "G2": lower > gs["G2_lower_bound_above"],
         "G3": bool(np.isfinite(down) and lift >= gs["G3_min_ratio_to_down"] * down),
         "G4": bool(yl) and all(v is not None and v >= gs["G4_min_lift_each_year"] for v in yl),
         "G5": n >= gs["G5_min_events"] and e >= gs["G5_min_expected"]}
    return lower, g


def check_aggregates(out_dir):
    errors = []
    tab = pd.concat([pd.read_csv(out_dir / f"events_{m}.csv.gz", keep_default_na=False, na_values=[""], dtype={"ticker": str})
                     for m in PROTO["markets"]], ignore_index=True)
    td = pd.DatetimeIndex(pd.to_datetime(tab["t_date"]))
    iso = td.isocalendar()
    tab["_week"], tab["_year"] = iso["year"].to_numpy() * 100 + iso["week"].to_numpy(), td.year
    lifts = pd.read_csv(out_dir / "lifts_pooled.csv")
    for r in lifts.itertuples(index=False):
        g = tab[(tab["kind"] == r.kind) & (tab["analysis"] == r.analysis) & (tab["lead"] == r.lead)]
        lift, se, n, e, _ = lift_of(g, r.feature, r.tail, f"INTL|{r.kind}|{r.analysis}|{int(r.lead)}|{r.feature}|{r.tail}")
        if n != r.events or not np.isclose(lift, r.lift, rtol=1e-8, equal_nan=True) or \
                not np.isclose(se, r.log_se, rtol=1e-6, equal_nan=True):
            errors.append(f"lift {r.kind} {r.analysis} {r.lead} {r.feature} {r.tail}")
    summary = json.loads((out_dir / "summary.json").read_text())
    prim_status = []
    for c in PROTO["primary"]:
        def cell(kind):
            g = tab[(tab["kind"] == kind) & (tab["analysis"] == "void") & (tab["lead"] == c["lead"])]
            return lift_of(g, c["feature"], c["tail"], f"INTL|{kind}|void|{c['lead']}|{c['feature']}|{c['tail']}")
        lift, se, n, e, years = cell(c["kind"])
        down = cell(L["pairs"][c["kind"]])[0]
        lower, g = gates(lift, se, n, e, years, down, PROTO["z_primary"])
        status = "NOT_TESTABLE" if n < L["gates"]["G5_min_events"] else ("PASS" if all(g.values()) else "FAIL")
        prim_status.append(status)
        got = next(p for p in summary["result"]["primary"] if p["id"] == c["id"])
        if got["status"] != status or not np.isclose(got["lower_bound"], lower, rtol=1e-6):
            errors.append(f"primary {c['id']}: {got['status']} vs {status}")
    verdict = "REPLICATED_SCREEN" if "PASS" in prim_status else (
        "NOT_TESTABLE" if all(s == "NOT_TESTABLE" for s in prim_status) else "NOT_REPLICATED")
    if verdict != summary["result"]["verdict"]:
        errors.append(f"verdict {summary['result']['verdict']} vs {verdict}")
    sec = pd.read_csv(out_dir / "gates_secondary.csv")
    for r in sec.itertuples(index=False):
        def cell(kind):
            g = tab[(tab["kind"] == kind) & (tab["analysis"] == "void") & (tab["lead"] == r.lead)]
            return lift_of(g, r.feature, r.tail, f"INTL|{kind}|void|{int(r.lead)}|{r.feature}|{r.tail}")
        lift, se, n, e, years = cell(r.kind)
        _, g = gates(lift, se, n, e, years, cell(L["pairs"][r.kind])[0], PROTO["z_secondary"])
        if bool(r.passes) != all(g.values()):
            errors.append(f"secondary {r.kind} {r.lead} {r.feature} {r.tail}")
    return errors, verdict


def main():
    which = sys.argv[1]
    out_dir = HERE / which
    errors = check_rows(out_dir, which == "rehearsal")
    agg_errors, verdict = check_aggregates(out_dir)
    errors += agg_errors
    report = {"checked": which, "verdict_recomputed": verdict, "error_count": len(errors), "errors": errors[:100],
              "status": "VERIFIED" if not errors else "MISMATCH"}
    with (out_dir / "VERIFY.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "errors"}), *errors[:20], sep="\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

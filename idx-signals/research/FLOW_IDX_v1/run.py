"""FLOW_IDX_v1 runner (PROTOCOL.md). Modes, each writing a new directory (exclusive create):

  feasibility  counts only: share of eligible name-days with each flow feature, hot share, events per kind
  placebo      rehearsal: up episodes replaced by random eligible names; both windows, both families
  stage1       the discovery run; writes the frozen cells (needs PINS.json, rehearsal/, a clean checkout)
  stage2       the 2023 validation of the frozen cells only (needs stage1/frozen.json committed)
"""

from __future__ import annotations

import argparse
import copy
import json
import multiprocessing as mp
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from idxsig import e1, flow_features as fx, lead_ladder as ll, panel  # noqa: E402
from idxsig.provenance import MANIFESTS, check_files, sha256_file  # noqa: E402
from idxsig.results import code_state  # noqa: E402

PROTO = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
LADDER = json.loads((ROOT / PROTO["ladder_protocol"]).read_text(encoding="utf-8"))
_LADS = None


def load_world():
    df, meta, _ = panel.load(MANIFESTS / PROTO["panel_manifest"])
    if meta["sha256"] != PROTO["panel_sha256"]:
        raise RuntimeError("the panel is not the pinned one")
    study = e1.Study(df, meta)
    raw_manifest = MANIFESTS / PROTO["raw_manifest"]
    problems = check_files(raw_manifest)
    if problems:
        raise RuntimeError(f"raw mirror files differ from {raw_manifest.name}: {problems[:3]}")
    tickers = [str(t) for t in study.m.tickers]
    raw = fx.load_raw(raw_manifest, tickers, study.dates, PROTO["last_row_date"])
    return study, fx.features(raw, study.m.tradeable)


def make_ladders(study, flows, window):
    m = study.m
    lo, hi = m.bounds(*PROTO["windows"][window])

    def one():
        return ll.Ladder(study.level, m.present, m.tradeable, m.prev, study.buckets, flows, (), study.dates, (lo, hi), LADDER)

    base, hot_lad = one(), one()
    hot = fx.hot_mask(study.sig["vol20"], base.elig & ~base.ext, PROTO["hot"]["quantile"])
    hot_lad.elig = hot_lad.elig & hot
    return {"IDX": base, "IDX_HOT": hot_lad}


def placebo_events(lad, kind, seed):
    n, t = lad.events(kind)
    rng = np.random.default_rng(seed + (0 if kind == "FAST_UP" else 1))
    return np.array([rng.choice(np.flatnonzero(lad.elig[:, tt])) for tt in t], dtype=np.int64), t


def _job(a):
    fam, kind, events = a
    return fam, kind, _LADS[fam].table(kind, events)


def tables(study, lads, out: Path, window: str, placebo: bool, workers: int):
    global _LADS
    _LADS = lads
    base = lads["IDX"]
    jobs = []
    for fam in lads:
        for kind in LADDER["kinds"]:
            ev = placebo_events(base, kind, PROTO["placebo_seed"]) if placebo and kind in LADDER["pairs"] else None
            jobs.append((fam, kind, ev))
    with mp.get_context("fork").Pool(min(workers, len(jobs))) as pool:
        res = pool.map(_job, jobs)
    tabs = {}
    for fam in lads:
        tab = pd.concat([t for f, _, t in res if f == fam], ignore_index=True)
        tab["ticker"] = np.asarray(study.m.tickers).astype(str)[tab["name_idx"].to_numpy()]
        tab["t_date"] = base.dates[tab["t"].to_numpy()].astype(str)
        tab["u_date"] = base.dates[tab["u"].to_numpy()].astype(str)
        tab.insert(0, "family", fam)
        tab.to_csv(out / f"events_{fam}_{window}.csv.gz", index=False, float_format="%.10g", lineterminator="\n",
                   compression={"method": "gzip", "mtime": 0})
        tabs[fam] = tab
    return tabs


def aggregate_all(tabs, dates, proto):
    parts = [ll.aggregate(tab, dates, list(fx.NAMES), set(), proto, fam) for fam, tab in tabs.items()]
    return pd.concat(parts, ignore_index=True)


def write_csv(path: Path, df: pd.DataFrame):
    out = df.copy()
    if "years" in out:
        out["years"] = out["years"].map(lambda d: json.dumps(d, sort_keys=True))
    with path.open("x", encoding="utf-8", newline="") as fh:
        out.to_csv(fh, index=False, float_format="%.10g", lineterminator="\n")


def write_json(path: Path, obj):
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True, default=float) + "\n")


def cell_key(r):
    return (r["market"], r["kind"], int(r["lead"]), r["feature"], r["tail"])


def placebo_lifts(path: Path) -> dict:
    p = pd.read_csv(path)
    p = p[p["analysis"] == "void"]
    return {(r.market, r.kind, int(r.lead), r.feature, r.tail): r.lift for r in p.itertuples(index=False)}


def stage1_proto():
    p = copy.deepcopy(LADDER)
    p["z_one_sided"] = PROTO["z_stage1"]
    return p


def header(mode):
    return {"protocol_id": PROTO["protocol_id"], "protocol_sha256": sha256_file(HERE / "protocol.json"), "mode": mode,
            "computed_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "code": code_state()}


def require_pins():
    pins = json.loads((HERE / "PINS.json").read_text(encoding="utf-8"))
    for rel_, sha in pins["files"].items():
        if sha256_file(ROOT.parent / rel_) != sha:
            raise SystemExit(f"{rel_} differs from PINS.json")
    if code_state()["dirty"]:
        raise SystemExit("commit first: the recorded run names the code that produced it")


def feasibility(study, flows, out, workers):
    summary = header("feasibility")
    for window in ("discovery", "validation"):
        lads = make_ladders(study, flows, window)
        base = lads["IDX"]
        lo, hi = base.lo, base.hi
        ok = (base.elig & ~base.ext)[:, lo:hi]
        info = {"eligible_not_extended_name_days": int(ok.sum()),
                "hot_name_days": int((lads["IDX_HOT"].elig[:, lo:hi] & ok).sum()),
                "feature_coverage": {f: round(float((np.isfinite(flows[f][:, lo:hi]) & ok).sum() / ok.sum()), 4) for f in fx.NAMES}}
        for fam, lad in lads.items():
            info[f"{fam}_events"] = {k: int(len(lad.events(k)[0])) for k in LADDER["kinds"]}
        summary[window] = info
        print(window, json.dumps(info)[:600], flush=True)
    write_json(out / "summary.json", summary)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("feasibility", "placebo", "stage1", "stage2"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    if args.mode in ("stage1", "stage2"):
        require_pins()
    out = HERE / {"feasibility": "feasibility", "placebo": "rehearsal", "stage1": "stage1", "stage2": "stage2"}[args.mode]
    out.mkdir(exist_ok=False)
    study, flows = load_world()
    if args.mode == "feasibility":
        return feasibility(study, flows, out, args.workers)
    summary = header(args.mode)
    p1 = stage1_proto()
    if args.mode in ("placebo", "stage1"):
        lads = make_ladders(study, flows, "discovery")
        tabs = tables(study, lads, out, "discovery", args.mode == "placebo", args.workers)
        agg = aggregate_all(tabs, study.dates, p1)
        write_csv(out / "lifts_discovery.csv", agg)
        gates = ll.gate(agg, p1)
        if args.mode == "placebo":
            summary["stage1_cells_passing_G1_G5"] = int(gates["passes"].sum())
            summary["stage1_movement_only"] = int(gates["movement_only"].sum())
        else:
            plc = placebo_lifts(HERE / "rehearsal" / "lifts_discovery.csv")
            gates["placebo_lift"] = [plc.get((r.market, r.kind, int(r.lead), r.feature, r.tail), np.nan) for r in gates.itertuples()]
            gates["G6"] = gates["lift"] >= PROTO["gates"]["G6_min_ratio_to_placebo"] * gates["placebo_lift"]
            gates["final_pass"] = gates["passes"] & gates["G6"]
            write_csv(out / "gates.csv", gates)
            frozen = gates[gates["final_pass"]]
            cells = [{"family": r.market, "kind": r.kind, "lead": int(r.lead), "feature": r.feature, "tail": r.tail,
                      "lift": r.lift, "lower_bound": r.lower_bound, "down_lift": r.down_lift, "placebo_lift": r.placebo_lift}
                     for r in frozen.itertuples()]
            write_json(out / "frozen.json", {"cells": cells})
            summary["result"] = {"verdict": "FLOW_CANDIDATES" if cells else "NO_FLOW_LEAD", "cells_gated": int(len(gates)),
                                 "passing_G1_G5": int(gates["passes"].sum()), "frozen": len(cells),
                                 "movement_only": int(gates["movement_only"].sum()), "frozen_cells": cells[:50]}
    if args.mode in ("placebo", "stage2"):
        if args.mode == "stage2":
            frozen = json.loads((HERE / "stage1" / "frozen.json").read_text(encoding="utf-8"))["cells"]
            if not frozen:
                raise SystemExit("no frozen cells: Stage 2 is not run")
            z_b = NormalDist().inv_cdf(1 - PROTO["stage2"]["V2_alpha"] / len(frozen))
        else:
            z_b = PROTO["z_stage1"]
        p2 = copy.deepcopy(LADDER)
        p2["z_one_sided"] = z_b
        lads = make_ladders(study, flows, "validation")
        tabs = tables(study, lads, out, "validation", args.mode == "placebo", args.workers)
        agg = aggregate_all(tabs, study.dates, p2)
        write_csv(out / "lifts_validation.csv", agg)
        if args.mode == "stage2":
            v = PROTO["stage2"]
            plc = placebo_lifts(HERE / "rehearsal" / "lifts_validation.csv")
            av = agg[agg["analysis"] == "void"].set_index(["market", "kind", "lead", "feature", "tail"])
            rows = []
            for c in frozen:
                k = (c["family"], c["kind"], c["lead"], c["feature"], c["tail"])
                r = av.loc[k]
                dn = av.loc[(c["family"], LADDER["pairs"][c["kind"]], c["lead"], c["feature"], c["tail"])]
                pl = plc.get(k, np.nan)
                testable = r["events"] >= v["V4_min_events"] and r["expected"] >= v["V4_min_expected"]
                g = {"V1": r["lift"] >= v["V1_min_lift"], "V2": r["lower_bound"] > 1.0,
                     "V3": r["lift"] >= v["V3_min_ratio_to_down"] * dn["lift"],
                     "V5": bool(np.isfinite(pl) and r["lift"] >= v["V5_min_ratio_to_placebo"] * pl)}
                rows.append({**c, "val_events": int(r["events"]), "val_expected": float(r["expected"]), "val_lift": float(r["lift"]),
                             "val_lower_bound": float(r["lower_bound"]), "val_down_lift": float(dn["lift"]), "val_placebo_lift": pl,
                             "testable": bool(testable), **{k_: bool(x) for k_, x in g.items()},
                             "passes": bool(testable and all(g.values()))})
            res = pd.DataFrame(rows)
            write_csv(out / "gates_validation.csv", res)
            verdict = ("FLOW_LEAD_VALIDATED" if res["passes"].any() else
                       "NOT_VALIDATED" if res["testable"].any() else "NOT_TESTABLE")
            summary["result"] = {"verdict": verdict, "frozen": len(frozen), "z_b": z_b, "testable": int(res["testable"].sum()),
                                 "passing": int(res["passes"].sum()),
                                 "passing_cells": res[res["passes"]].to_dict("records")}
        else:
            gv = ll.gate(agg, p2)
            summary["validation_cells_passing_G1_G5"] = int(gv["passes"].sum())
    write_json(out / "summary.json", summary)
    print(json.dumps(summary.get("result", {k: v for k, v in summary.items() if k.startswith(("stage1", "validation"))}),
                     indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()

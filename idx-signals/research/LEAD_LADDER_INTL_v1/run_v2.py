"""LEAD_LADDER_INTL_v1 runner, version 2 (PROTOCOL.md, ADDENDUM_1.md: panels start at 2019-07-29 on load;
run.py stays as committed). Modes (each a new directory, exclusive create):

  build         Yahoo panels for the nine markets from their fetch manifests (data only; no statistic)
  feasibility   counts only: pooled events per primary cell with a pool of >= 5
  placebo       rehearsal: up episodes replaced by random eligible names on the same sessions
  run           the recorded run (needs PINS.json and a clean checkout)
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from idxsig import e1, intl_panel, lead_ladder as ll  # noqa: E402
from idxsig.provenance import MANIFESTS, sha256_file  # noqa: E402
from idxsig.results import code_state  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

PROTO = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
LADDER = json.loads((ROOT / PROTO["ladder_protocol"]).read_text(encoding="utf-8"))
LADDER["pool"]["buckets"] = PROTO["pool_buckets"]  # no market cap outside IDX (no share counts)
STUDY_PROTO = HERE / "study_protocol.json"
_LAD = None


def panel_manifest(market: str) -> Path:
    found = sorted(MANIFESTS.glob(f"panel_intl_{market.lower()}-*.json"))
    if not found:
        raise FileNotFoundError(f"no INTL {market} panel; run `run.py build`")
    return found[-1]


def build_market(market: str, manifest: Path | None = None):
    manifest = manifest or panel_manifest(market)
    df, meta = intl_panel.load(manifest)
    df = df[df["date"] >= pd.Timestamp("2019-07-29")].reset_index(drop=True)  # ADDENDUM_1.md
    # Study checks for the E2 panel format; the INTL panels use the current causal format (global_panel.FORMAT),
    # which differs only in preprocessing (no future-informed row removal). Nothing else in Study depends on it.
    study = e1.Study(df, {**meta, "format": "panel-global-v1"}, protocol_path=STUDY_PROTO,
                     profile=intl_panel.profile(market), family_module=moonshot_g)
    m = study.m
    lo, hi = m.bounds(*PROTO["periods"]["discovery"])
    names = list(study.continuous + study.binary)
    lad = ll.Ladder(study.level, m.present, m.tradeable, m.prev, study.buckets, {f: study.sig[f] for f in names},
                    study.binary, study.dates, (lo, hi), LADDER)
    return lad, study, meta, manifest


def _table(job):
    kind, events = job
    return _LAD.table(kind, events)


def placebo_events(lad, kind, seed):
    n, t = lad.events(kind)
    rng = np.random.default_rng(seed + (0 if kind == "FAST_UP" else 1))
    return np.array([rng.choice(np.flatnonzero(lad.elig[:, tt])) for tt in t], dtype=np.int64), t


def pooled(tab: pd.DataFrame, features: list[str], binary: set) -> pd.DataFrame:
    """Lifts over all markets: summed observed / expected; ISO-week bootstrap on t's calendar date."""
    reps, seed0 = LADDER["bootstrap"]["resamples"], LADDER["bootstrap"]["seed"]
    td = pd.DatetimeIndex(pd.to_datetime(tab["t_date"]))
    iso = td.isocalendar()
    week = iso["year"].to_numpy() * 100 + iso["week"].to_numpy()
    year = td.year.to_numpy()
    rows = []
    for (kind, analysis, lead), idx in tab.groupby(["kind", "analysis", "lead"]).indices.items():
        g = tab.iloc[idx]
        for f in features:
            for tail in (("top",) if f in binary else ("top", "bottom")):
                ci, ce = f"{f}|{tail}|I", f"{f}|{tail}|E"
                if ci not in g:
                    continue
                sel = g[ci].notna().to_numpy()
                I, E = g[ci].to_numpy(float)[sel], g[ce].to_numpy(float)[sel]
                w, y = week[idx][sel], year[idx][sel]
                sI, sE = I.sum(), E.sum()
                lift = sI / sE if sE > 0 else float("nan")
                se = float("inf")
                if len(I) and sE > 0:
                    uw, inv = np.unique(w, return_inverse=True)
                    Iw, Ew = np.bincount(inv, I, len(uw)), np.bincount(inv, E, len(uw))
                    rng = np.random.default_rng(seed0 + zlib.crc32(f"INTL|{kind}|{analysis}|{int(lead)}|{f}|{tail}".encode()) % 10**6)
                    cnt = rng.multinomial(len(uw), np.full(len(uw), 1.0 / len(uw)), size=reps)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        bl = (cnt @ Iw) / (cnt @ Ew)
                    good = np.isfinite(bl) & (bl > 0)
                    if good.sum() >= reps // 2:
                        se = float(np.std(np.log(bl[good]), ddof=1))
                years = {str(int(v)): {"events": int((y == v).sum()),
                                       "lift": float(I[y == v].sum() / E[y == v].sum()) if E[y == v].sum() > 0 else None}
                         for v in np.unique(y)}
                lb = lambda z: float(np.exp(np.log(lift) - z * se)) if lift > 0 and np.isfinite(se) else 0.0  # noqa: E731
                rows.append({"kind": kind, "analysis": analysis, "lead": int(lead), "feature": f, "tail": tail,
                             "events": int(len(I)), "observed": float(sI), "expected": float(sE), "lift": lift,
                             "log_se": se, "lower_primary": lb(PROTO["z_primary"]),
                             "lower_secondary": lb(PROTO["z_secondary"]), "years": years})
    return pd.DataFrame(rows)


def gate_row(r, agg_idx, lower_col):
    gs = LADDER["gates"]
    down = LADDER["pairs"][r["kind"]]
    try:
        dl = float(agg_idx.loc[("void", down, r["lead"], r["feature"], r["tail"]), "lift"])
    except KeyError:
        dl = float("nan")
    yrs = [v["lift"] for v in r["years"].values() if v["events"] >= gs["G4_min_events_per_year"]]
    g = {"G1": r["lift"] >= gs["G1_min_lift"], "G2": r[lower_col] > gs["G2_lower_bound_above"],
         "G3": bool(np.isfinite(dl) and r["lift"] >= gs["G3_min_ratio_to_down"] * dl),
         "G4": bool(yrs) and all(v is not None and v >= gs["G4_min_lift_each_year"] for v in yrs),
         "G5": r["events"] >= gs["G5_min_events"] and r["expected"] >= gs["G5_min_expected"]}
    g = {k: bool(v) for k, v in g.items()}
    return {**g, "down_lift": dl, "passes": all(g.values()),
            "movement_only": g["G1"] and g["G2"] and g["G4"] and g["G5"] and not g["G3"]}


def judge(agg: pd.DataFrame) -> dict:
    idx = agg.set_index(["analysis", "kind", "lead", "feature", "tail"])
    prim = []
    for c in PROTO["primary"]:
        try:
            r = idx.loc[("void", c["kind"], c["lead"], c["feature"], c["tail"])].to_dict()
        except KeyError:
            prim.append({**c, "status": "NOT_TESTABLE", "reason": "no scored events"})
            continue
        r.update({"kind": c["kind"], "lead": c["lead"], "feature": c["feature"], "tail": c["tail"]})
        g = gate_row(r, idx, "lower_primary")
        status = "NOT_TESTABLE" if r["events"] < LADDER["gates"]["G5_min_events"] else ("PASS" if g["passes"] else "FAIL")
        prim.append({**c, "events": r["events"], "expected": r["expected"], "lift": r["lift"],
                     "lower_bound": r["lower_primary"], **g, "status": status})
    if any(p["status"] == "PASS" for p in prim):
        verdict = "REPLICATED_SCREEN"
    elif any(p["status"] == "NOT_TESTABLE" for p in prim):
        verdict = "NOT_TESTABLE" if all(p["status"] == "NOT_TESTABLE" for p in prim) else "NOT_REPLICATED"
    else:
        verdict = "NOT_REPLICATED"
    sec = []
    for r in agg[(agg["analysis"] == "void") & agg["kind"].isin(list(LADDER["pairs"])) &
                 agg["lead"].isin(LADDER["gated_leads"])].to_dict("records"):
        sec.append({k: r[k] for k in ("kind", "lead", "feature", "tail", "events", "lift")} | {"lower_bound": r["lower_secondary"]}
                   | gate_row(r, idx, "lower_secondary"))
    sec = pd.DataFrame(sec)
    return {"verdict": verdict, "primary": prim,
            "secondary": {"cells": int(len(sec)), "passing": int(sec["passes"].sum()) if len(sec) else 0,
                          "movement_only": int(sec["movement_only"].sum()) if len(sec) else 0,
                          "passing_cells": sec[sec["passes"]][["kind", "lead", "feature", "tail", "lift", "lower_bound", "down_lift"]].to_dict("records") if len(sec) else []}}, sec


def write_json(path, obj):
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True, default=float) + "\n")


def main(argv=None):
    global _LAD
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("build", "feasibility", "placebo", "run"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    markets = list(PROTO["markets"])
    if args.mode == "build":
        for m in markets:
            found = sorted(MANIFESTS.glob(f"yahoo_intl_{m.lower()}-*.jsonl"))
            intl_panel.build(m, found[-1])
        return
    state = code_state()
    if args.mode == "run":
        pins = json.loads((HERE / "PINS.json").read_text(encoding="utf-8"))
        for rel_, sha in pins["files"].items():
            if sha256_file(ROOT.parent / rel_) != sha:
                raise SystemExit(f"{rel_} differs from PINS.json")
        if state["dirty"]:
            raise SystemExit("commit first")
    out = HERE / {"feasibility": "feasibility", "placebo": "rehearsal", "run": "results"}[args.mode]
    out.mkdir(exist_ok=False)
    summary = {"protocol_id": PROTO["protocol_id"], "protocol_sha256": sha256_file(HERE / "protocol.json"),
               "mode": args.mode, "computed_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "code": state,
               "markets": {}}
    tabs, features, binary = [], None, None
    ctx = mp.get_context("fork")
    for market in markets:
        lad, study, meta, manifest = build_market(market)
        _LAD = lad
        features, binary = lad.feature_names, lad.binary
        kinds = list(LADDER["kinds"])
        info = {"panel_manifest": manifest.name, "panel_sha256": meta["sha256"], "tickers": meta["tickers"],
                "episodes": {k: int(len(lad.events(k)[0])) for k in kinds}}
        if args.mode == "feasibility":
            for c in PROTO["primary"]:
                n, t = lad.events(c["kind"])
                ok = 0
                for i, tt in zip(n, t):
                    u = tt - c["lead"]
                    if u >= 0 and lad.elig[i, u] and not lad.ext[i, u]:
                        ok += len(lad.pool(i, u, tt, c["kind"], True)[0]) >= LADDER["pool"]["min_size"]
                info[f"{c['id']}_events_with_pool"] = int(ok)
        else:
            jobs = [(k, placebo_events(lad, k, PROTO["placebo_seed"]) if args.mode == "placebo" and k in LADDER["pairs"] else None)
                    for k in kinds]
            with ctx.Pool(min(args.workers, len(jobs))) as pool:
                tab = pd.concat(pool.map(_table, jobs), ignore_index=True)
            tab["ticker"] = np.asarray(study.m.tickers).astype(str)[tab["name_idx"].to_numpy()]
            tab["t_date"] = lad.dates[tab["t"].to_numpy()].astype(str)
            tab["u_date"] = lad.dates[tab["u"].to_numpy()].astype(str)
            tab.insert(0, "market", market)
            tab.to_csv(out / f"events_{market}.csv.gz", index=False, float_format="%.10g", lineterminator="\n",
                       compression={"method": "gzip", "mtime": 0})
            tabs.append(tab)
            info["rows"] = int(len(tab))
        summary["markets"][market] = info
        print(market, json.dumps(info["episodes"]), flush=True)
    if args.mode == "feasibility":
        summary["pooled_primary_events_with_pool"] = {c["id"]: sum(v[f"{c['id']}_events_with_pool"] for v in summary["markets"].values())
                                                      for c in PROTO["primary"]}
    else:
        tab = pd.concat(tabs, ignore_index=True)
        agg = pooled(tab, features, binary)
        a = agg.copy()
        a["years"] = a["years"].map(lambda d: json.dumps(d, sort_keys=True))
        with (out / "lifts_pooled.csv").open("x", encoding="utf-8", newline="") as fh:
            a.to_csv(fh, index=False, float_format="%.10g", lineterminator="\n")
        result, sec = judge(agg)
        with (out / "gates_secondary.csv").open("x", encoding="utf-8", newline="") as fh:
            sec.to_csv(fh, index=False, float_format="%.10g", lineterminator="\n")
        per = []
        for market, g in tab.groupby("market"):
            for c in PROTO["primary"]:
                s = g[(g["kind"] == c["kind"]) & (g["analysis"] == "void") & (g["lead"] == c["lead"])]
                col = f"{c['feature']}|{c['tail']}"
                ok = s[f"{col}|I"].notna()
                e = s.loc[ok, f"{col}|E"].sum()
                per.append({"market": market, "cell": c["id"], "events": int(ok.sum()),
                            "lift": float(s.loc[ok, f"{col}|I"].sum() / e) if e > 0 else None})
        result["per_market_primary_descriptive"] = per
        summary["result"] = result
    write_json(out / "summary.json", summary)
    print(json.dumps(summary.get("result", summary.get("pooled_primary_events_with_pool")), indent=1, default=float)[:2500])


if __name__ == "__main__":
    main()

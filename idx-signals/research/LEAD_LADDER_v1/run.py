"""LEAD_LADDER_v1 runner (PROTOCOL.md). Modes, each writing a new directory (exclusive create):

  feasibility   counts only: episodes per market and kind, events per lead with a pool of >= 5 (no feature value)
  placebo       the rehearsal: FAST_UP / SLOW_UP events replaced by random eligible names on the same sessions
  run           the recorded run (needs PINS.json and a clean checkout)

    python3 research/LEAD_LADDER_v1/run.py feasibility
    python3 research/LEAD_LADDER_v1/run.py placebo
    python3 research/LEAD_LADDER_v1/run.py run
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from idxsig import e1, global_panel, lead_ladder as ll, panel  # noqa: E402
from idxsig.profiles import PROFILES  # noqa: E402
from idxsig.provenance import MANIFESTS, sha256_file  # noqa: E402
from idxsig.results import code_state  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

PROTO_PATH = HERE / "protocol.json"
PROTO = json.loads(PROTO_PATH.read_text(encoding="utf-8"))
CODE = [ROOT / "idxsig" / "lead_ladder.py", ROOT / "idxsig" / "void.py", ROOT / "idxsig" / "e1.py",
        ROOT / "idxsig" / "controls.py", ROOT / "idxsig" / "execution.py", HERE / "run.py", HERE / "verify.py"]
_LADDER = None  # set in the parent before forking workers


def build(market: str):
    spec = PROTO["markets"][market]
    manifest = MANIFESTS / spec["panel_manifest"]
    if market == "IDX":
        df, meta, _ = panel.load(manifest)
        study = e1.Study(df, meta)
    else:
        df, meta = global_panel.load(manifest)
        study = e1.Study(df, meta, protocol_path=ROOT / spec["study_protocol"], profile=PROFILES[market],
                         family_module=moonshot_g)
    if meta["sha256"] != spec["panel_sha256"]:
        raise RuntimeError(f"{market}: panel {meta['sha256'][:12]} is not the pinned {spec['panel_sha256'][:12]}")
    m = study.m
    lo, hi = m.bounds(*spec["window"])
    names = list(study.continuous + study.binary)
    lad = ll.Ladder(study.level, m.present, m.tradeable, m.prev, study.buckets, {f: study.sig[f] for f in names},
                    study.binary, study.dates, (lo, hi), PROTO)
    return lad, study, meta


def _table(args):
    kind, events = args
    return _LADDER.table(kind, events)


def _feasible(kind):
    lad = _LADDER
    n, t = lad.events(kind)
    rows = []
    for k in PROTO["leads"]:
        scored = void_ok = 0
        for i, tt in zip(n, t):
            u = tt - k
            if u < 0 or not lad.elig[i, u] or lad.ext[i, u]:
                continue
            void_ok += 1
            pool, _ = lad.pool(i, u, tt, kind, True)
            scored += len(pool) >= PROTO["pool"]["min_size"]
        rows.append({"kind": kind, "lead": k, "episodes": int(len(n)), "eligible_not_extended": void_ok,
                     "with_pool_ge_5": scored})
    return rows


def placebo_events(lad, kind: str, seed: int):
    n, t = lad.events(kind)
    rng = np.random.default_rng(seed + (0 if kind == "FAST_UP" else 1))
    out_n = np.empty(len(n), dtype=np.int64)
    for j, tt in enumerate(t):
        cand = np.flatnonzero(lad.elig[:, tt])
        out_n[j] = rng.choice(cand)
    return out_n, t


def write_json(path: Path, obj):
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True, default=float) + "\n")


def main(argv=None):
    global _LADDER
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("feasibility", "placebo", "run"))
    ap.add_argument("--markets", default="IDX,CRYPTO,US")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state = code_state()
    if args.mode == "run":
        pins = json.loads((HERE / "PINS.json").read_text(encoding="utf-8"))
        for rel, sha in pins["files"].items():
            if sha256_file(ROOT.parent / rel) != sha:
                raise SystemExit(f"{rel} differs from PINS.json")
        if state["dirty"]:
            raise SystemExit("commit first: the recorded run names the code that produced it")
    out = HERE / {"feasibility": "feasibility", "placebo": "rehearsal", "run": "results"}[args.mode]
    out.mkdir(exist_ok=False)
    summary = {"protocol_id": PROTO["protocol_id"], "protocol_sha256": sha256_file(PROTO_PATH), "mode": args.mode,
               "computed_at": stamp, "code": state, "markets": {}}
    all_agg, all_gates = [], []
    ctx = mp.get_context("fork")
    for market in args.markets.split(","):
        lad, study, meta = build(market)
        _LADDER = lad
        info = {"panel_sha256": meta["sha256"], "window": PROTO["markets"][market]["window"],
                "window_sessions": [str(lad.dates[lad.lo]), str(lad.dates[lad.hi - 1])],
                "features": lad.feature_names, "binary": sorted(lad.binary)}
        kinds = list(PROTO["kinds"])
        if args.mode == "feasibility":
            with ctx.Pool(min(args.workers, len(kinds))) as pool:
                rows = [r for rs in pool.map(_feasible, kinds) for r in rs]
            df = pd.DataFrame(rows)
            df.insert(0, "market", market)
            with (out / f"counts_{market}.csv").open("x", encoding="utf-8", newline="") as fh:
                df.to_csv(fh, index=False, lineterminator="\n")
            info["counts"] = rows
        else:
            jobs = []
            for kind in kinds:
                ev = None
                if args.mode == "placebo" and kind in PROTO["pairs"]:
                    ev = placebo_events(lad, kind, PROTO["placebo_seed"])
                jobs.append((kind, ev))
            with ctx.Pool(min(args.workers, len(jobs))) as pool:
                tabs = pool.map(_table, jobs)
            tab = pd.concat(tabs, ignore_index=True)
            tab["ticker"] = np.asarray(study.m.tickers)[tab["name_idx"].to_numpy()].astype(str)
            tab["t_date"] = lad.dates[tab["t"].to_numpy()].astype(str)
            tab["u_date"] = lad.dates[tab["u"].to_numpy()].astype(str)
            tab.insert(0, "market", market)
            tab.to_csv(out / f"events_{market}.csv.gz", index=False, float_format="%.10g", lineterminator="\n",
                       compression={"method": "gzip", "mtime": 0})
            agg = ll.aggregate(tab, lad.dates, lad.feature_names, lad.binary, PROTO, market)
            all_agg.append(agg)
            info["episodes"] = {k: int(len(lad.events(k)[0])) for k in kinds}
            info["rows"] = int(len(tab))
        summary["markets"][market] = info
        print(market, json.dumps({k: v for k, v in info.items() if k in ("episodes", "rows")}), flush=True)
    if args.mode != "feasibility":
        agg = pd.concat(all_agg, ignore_index=True)
        agg_out = agg.copy()
        agg_out["years"] = agg_out["years"].map(lambda d: json.dumps(d, sort_keys=True))
        with (out / "lifts.csv").open("x", encoding="utf-8", newline="") as fh:
            agg_out.to_csv(fh, index=False, float_format="%.10g", lineterminator="\n")
        gates = ll.gate(agg, PROTO)
        with (out / "gates.csv").open("x", encoding="utf-8", newline="") as fh:
            gates.to_csv(fh, index=False, float_format="%.10g", lineterminator="\n")
        summary["result"] = ll.verdict(gates, PROTO)
        if len(gates) != PROTO["tests_counted"]:
            summary["result"]["note_cells"] = f"{len(gates)} gated cells, protocol counts {PROTO['tests_counted']}"
    write_json(out / "summary.json", summary)
    print(json.dumps(summary.get("result", {}), indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()

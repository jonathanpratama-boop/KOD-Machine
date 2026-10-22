"""SLOW_10K: the recorded runs of PROTOCOL.md (with ADDENDUM_1.md). `--stage 1` runs the filings of 2021-01-04 .. 2022-12-30; `--stage 2` runs 2023-01-03 .. 2023-09-29 and is allowed only if
results_stage1/RESULT.json says PASS. Reads PINS.json (sha256 of the events, the similarities, the filing list, the US repair panel and the code) and refuses to run if anything differs, if the
GO rule fails (nothing is written then), or if the stage's results exist. Holds 20, 60 (primary) and 120 are run on the same events with 200 matched control draws each.
Usage (from idx-signals/): python3 research/SLOW_10K/run.py --stage 1
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from idxsig import event_study as es, global_panel  # noqa: E402
from tenk_stats import (GO_MIN_PER_BUCKET, Boot, scored_sets, shuffle_check, stage1_gates, stage1_reading, stage2_gates, stage2_reading,  # noqa: E402
                        week_id)

PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
START, END = "2020-06-01", "2023-12-29"
HOLDS, PRIMARY = (20, 60, 120), 60
DRAWS, SEED, BOOT_SEED, RESAMPLES = 200, 20261007, 20261201, 10_000


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def p_one_sided(t: float) -> float:
    return 0.5 * math.erfc(t / math.sqrt(2))


def hold_table(res: pd.DataFrame) -> dict:
    """Per bucket (Q1..Q5) and the spread: scored events, mean net, mean excess with a week-cluster bootstrap, for one hold."""
    f = res[res.net_return.notna() & res.control_mean.notna()]
    boot = Boot(week_id(f.entry_date), RESAMPLES, BOOT_SEED)
    out = {"scored": int(len(f)), "status": es.status_counts(res), "quintiles": {}}
    for q, g in f.groupby("quintile"):
        s = boot.mean(g.excess, week_id(g.entry_date))
        out["quintiles"][q] = {**s, "mean_net": float(g.net_return.mean()), "mean_control": float(g.control_mean.mean()), "hit_rate": float((g.net_return > 0).mean())}
    q5, q1 = f[f.quintile == "Q5"], f[f.quintile == "Q1"]
    if len(q5) >= 10 and len(q1) >= 10:
        out["spread"] = boot.spread(q5.excess, week_id(q5.entry_date), q1.excess, week_id(q1.entry_date))
    return out


def compute(prep, ev: pd.DataFrame, stage: int, inputs: dict, go_check: bool = True) -> tuple[dict, pd.DataFrame]:
    """Everything the run computes, from a prepared market and an event table (columns ticker, public_date, bucket, quintile, cosine, length_ratio)."""
    results = {}
    for hold in HOLDS:
        res = es.run_events(prep, ev, es.us_config(hold), draws=DRAWS, seed=SEED)
        res["price_band"] = prep.feats["price_band"][res.tick_idx.to_numpy(), res.sig_idx.to_numpy()]
        results[hold] = res
    prim = results[PRIMARY]
    q5, q1 = scored_sets(prim)
    if go_check and stage == 1 and (len(q5) < GO_MIN_PER_BUCKET or len(q1) < GO_MIN_PER_BUCKET):
        raise RuntimeError(f"GO rule fails: scored Q5 {len(q5)}, Q1 {len(q1)} < {GO_MIN_PER_BUCKET}")
    tables = {str(h): hold_table(r) for h, r in results.items()}
    spread = tables[str(PRIMARY)]["spread"]
    f = prim[prim.net_return.notna() & prim.control_mean.notna()]
    boot = Boot(week_id(f.entry_date), RESAMPLES, BOOT_SEED)
    res = {"experiment": "SLOW_10K", "protocol": "research/SLOW_10K/PROTOCOL.md (+ ADDENDUM_1.md)", "stage": stage,
           "label": "historical research only; never prospective performance; survivor-only prices", "inputs": inputs, "window": [START, END],
           "events": {"in_stage": int(len(ev)), "mapped": int(len(prim)), "status_counts": es.status_counts(prim), "scored": int(len(f)),
                      "by_bucket": {k: int(v) for k, v in ev.groupby("bucket").size().items()}},
           "primary_hold": PRIMARY, "spread": spread, "p_one_sided": p_one_sided(spread["t"]), "holds": tables, "variants_reported": len(HOLDS)}
    if stage == 1:
        shuf = shuffle_check(f, boot)
        gates, years = stage1_gates(f, spread, shuf)
        res.update({"shuffled_label_t": shuf, "by_year": years, "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL", "reading": stage1_reading(gates, spread)})
    else:
        gates = stage2_gates(spread)
        res.update({"gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL", "reading": stage2_reading(gates)})
    by_year = {y: g for y, g in f.assign(y=f.entry_date.str[:4]).groupby("y")}
    res["spread_by_entry_year"] = {y: float(g[g.bucket == "Q5"].excess.mean() - g[g.bucket == "Q1"].excess.mean()) for y, g in by_year.items()
                                   if (g.bucket == "Q5").any() and (g.bucket == "Q1").any()}
    res["by_price_band"] = {str(b): {"q5": int((g.bucket == "Q5").sum()), "q1": int((g.bucket == "Q1").sum()),
                                     "spread": float(g[g.bucket == "Q5"].excess.mean() - g[g.bucket == "Q1"].excess.mean()) if (g.bucket == "Q5").any() and (g.bucket == "Q1").any() else None}
                            for b, g in f.groupby("price_band")}
    res["similarity"] = {"mean_by_bucket": {k: float(v) for k, v in ev.groupby("bucket").cosine.mean().items()},
                         "corr_with_length_ratio": float(ev[["cosine", "length_ratio"]].corr().iloc[0, 1])}
    return res, prim


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    stage = ap.parse_args().stage
    out_dir = HERE / f"results_stage{stage}"
    if (out_dir / "RESULT.json").exists():
        sys.exit(f"error: {out_dir.name}/RESULT.json exists; this stage runs once")
    if stage == 2:
        r1 = HERE / "results_stage1" / "RESULT.json"
        if not r1.exists() or json.loads(r1.read_text())["verdict"] != "PASS":
            sys.exit("error: stage 2 runs only if stage 1 passed")
    pins = json.loads((HERE / "PINS.json").read_text())
    bad = [p for p, h in pins["code"].items() if sha(ROOT / p) != h]
    if bad or sha(HERE / "events.csv") != pins["events_csv"] or sha(HERE / "similarity.csv.gz") != pins["similarity_csv"] or sha(HERE / "filings.csv.gz") != pins["filings_csv"]:
        sys.exit(f"error: inputs or code differ from PINS.json: {bad}")
    df, meta = global_panel.load(PANEL_MANIFEST)
    if meta["sha256"] != pins["panel"]:
        sys.exit("error: the panel differs from PINS.json")
    ev = pd.read_csv(HERE / "events.csv", dtype={"accession": str})
    ev = ev[ev.stage == stage].reset_index(drop=True)
    prep = es.prepare_us(df, START, END)
    if str(prep.m.dates[-1]) > END:
        sys.exit("error: the window reaches the sealed holdout")
    try:
        res, prim = compute(prep, ev, stage, {k: pins[k] for k in ("events_csv", "similarity_csv", "filings_csv", "panel")})
    except RuntimeError as exc:
        sys.exit(f"error: {exc}; nothing written")
    out_dir.mkdir(exist_ok=True)
    prim.to_csv(out_dir / "events.csv", index=False)
    pd.DataFrame([{"hold": h, "bucket": q, **{k: v for k, v in s.items()}} for h, t in res["holds"].items() for q, s in t["quintiles"].items()]).to_csv(out_dir / "quintiles.csv", index=False)
    (out_dir / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("stage", "events", "spread", "p_one_sided", "gates", "verdict", "reading")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

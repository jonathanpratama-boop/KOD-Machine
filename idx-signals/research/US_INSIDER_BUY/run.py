"""US_INSIDER_BUY: the recorded runs of PROTOCOL.md. `--stage 1` runs the events of 2021-01-04 .. 2022-12-30; `--stage 2` runs 2023-01-03 .. 2023-09-29 and is allowed only if
results_stage1/RESULT.json says PASS. Reads PINS.json (sha256 of the events, the Form 4 extract, the 10-K filing list that maps CIKs to tickers, the US repair panel and the code) and
refuses to run if anything differs, if the GO rule fails (nothing is written then), or if the stage's results exist. Holds 20, 60 (primary) and 120 are run on the same events with 200
matched control draws each; the events of each hold are written so the verifier can recompute all of them.
Usage (from idx-signals/): python3 research/US_INSIDER_BUY/run.py --stage 1
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
import ib_stats as st  # noqa: E402

PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
START, END = "2020-06-01", "2023-12-29"
HOLDS, PRIMARY = (20, 60, 120), 60
DRAWS, SEED, BOOT_SEED, RESAMPLES = 200, 20261007, 20261203, 10_000
SIZE_BINS, SIZE_LABELS = [50_000, 100_000, 500_000, float("inf")], ["50-100k", "100-500k", "500k+"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def p_one_sided(t: float) -> float:
    return 0.5 * math.erfc(t / math.sqrt(2))


def hold_table(res: pd.DataFrame) -> dict:
    f = st.scored(res)
    w = st.week_id(f.entry_date)
    s = st.Boot(w, RESAMPLES, BOOT_SEED).mean(f.excess, w)
    return {"scored": int(len(f)), "status": es.status_counts(res),
            "excess": {**s, "winsorised_mean": st.winsor_mean(f.excess), "median": float(f.excess.median())},
            "mean_net": float(f.net_return.mean()), "mean_control": float(f.control_mean.mean()), "hit_rate": float((f.net_return > 0).mean())}


def compute(prep, ev: pd.DataFrame, stage: int, inputs: dict, go_check: bool = True) -> tuple[dict, dict]:
    """Everything the run computes, from a prepared market and an event table (columns ticker, public_date, stage, top_exec, total_value, officer, director, lag_days).
    Returns the result dict and the executed events of every hold."""
    results = {}
    for hold in HOLDS:
        res = es.run_events(prep, ev, es.us_config(hold), draws=DRAWS, seed=SEED)
        res["price_band"] = prep.feats["price_band"][res.tick_idx.to_numpy(), res.sig_idx.to_numpy()]
        results[hold] = res
    prim = results[PRIMARY]
    f = st.scored(prim)
    if go_check and stage == 1:
        ok, info = st.go_check(f)
        if not ok:
            raise RuntimeError(f"GO rule fails: {info}")
    tables = {str(h): hold_table(r) for h, r in results.items()}
    stats = tables[str(PRIMARY)]["excess"]
    boot = st.Boot(st.week_id(f.entry_date), RESAMPLES, BOOT_SEED)

    def sub(mask) -> dict:
        g = f[mask]
        return boot.mean(g.excess, st.week_id(g.entry_date)) if len(g) >= 10 else {"n": int(len(g))}

    top = f.top_exec.astype(bool)
    size = pd.cut(f.total_value, SIZE_BINS, right=False, labels=SIZE_LABELS)
    res = {"experiment": "US_INSIDER_BUY", "protocol": "research/US_INSIDER_BUY/PROTOCOL.md", "stage": stage,
           "label": "historical research only; never prospective performance; survivor-only prices", "inputs": inputs, "window": [START, END],
           "events": {"in_stage": int(len(ev)), "mapped": int(len(prim)), "status_counts": es.status_counts(prim), "scored": int(len(f))},
           "primary_hold": PRIMARY, "excess": stats, "winsorised_mean_excess": st.winsor_mean(f.excess), "p_one_sided": p_one_sided(stats["t"]), "holds": tables,
           "variants_reported": len(HOLDS) + 2 + len(SIZE_LABELS),
           "splits_hold_60": {"top_exec": {"yes": sub(top), "no": sub(~top)}, "size": {lab: sub(size == lab) for lab in SIZE_LABELS}},
           "by_entry_year": {y: {"n": int(len(g)), "mean_excess": float(g.excess.mean())} for y, g in f.groupby(f.entry_date.str[:4])},
           "by_price_band": {str(b): {"n": int(len(g)), "mean_excess": float(g.excess.mean())} for b, g in f.groupby("price_band")},
           "lag_days": {"median": float(f.lag_days.median()), "share_within_2_days": float((f.lag_days <= 2).mean())},
           "owner_mix": {"officer_only": int((f.officer & ~f.director).sum()), "director_only": int((~f.officer & f.director).sum()), "both": int((f.officer & f.director).sum())}}
    if stage == 1:
        gates, years = st.stage1_gates(f, stats, {h: tables[str(h)]["excess"]["mean"] for h in HOLDS if h != PRIMARY})
        res.update({"gates": gates, "gate_years": years, "verdict": "PASS" if all(gates.values()) else "FAIL", "reading": st.stage1_reading(gates, stats)})
    else:
        gates = st.stage2_gates(stats)
        res.update({"gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL", "reading": st.stage2_reading(gates)})
    return res, results


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
    if bad or sha(HERE / "events.csv") != pins["events_csv"] or sha(HERE / "form4_purchases.csv.gz") != pins["form4_csv"] \
            or sha(HERE.parent / "SLOW_10K" / "filings.csv.gz") != pins["filings_csv"]:
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
        res, results = compute(prep, ev, stage, {k: pins[k] for k in ("events_csv", "form4_csv", "filings_csv", "panel")})
    except RuntimeError as exc:
        sys.exit(f"error: {exc}; nothing written")
    out_dir.mkdir(exist_ok=True)
    for h, r in results.items():
        r.to_csv(out_dir / f"events_hold{h}.csv", index=False)
    (out_dir / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("stage", "events", "excess", "winsorised_mean_excess", "p_one_sided", "gates", "verdict", "reading")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""US_8K_ITEMS: the recorded runs of PROTOCOL.md. --stage 1 runs the Stage 1 events of each of the nine items at holds 5, 20 (primary) and 60; --stage 2 runs 2023 events of the items that
passed Stage 1 (hold 20). --feasibility prints counts only (scored events per item at hold 20) and writes feasibility/FEASIBILITY.json. Reads PINS.json and refuses on any difference.
Usage (from idx-signals/): python3 research/US_8K_ITEMS/run.py --feasibility | --stage 1 | --stage 2"""
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
sys.path.insert(0, str(HERE.parent / "US_INSIDER_BUY"))
from idxsig import event_study as es, global_panel  # noqa: E402
import ib_stats as st  # noqa: E402

PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
START, END = "2020-06-01", "2023-12-29"
ITEMS = ["1.01", "1.02", "2.02", "2.03", "3.02", "5.02", "5.07", "7.01", "8.01"]
HOLDS, PRIMARY = (5, 20, 60), 20
DRAWS, SEED, BOOT_SEED, RESAMPLES = 200, 20261007, 20261204, 10_000
HURDLE_T, MIN_EXC, MIN_WINS, MIN_YEAR, GO_MIN = 3.6, 0.01, 0.005, 100, 500
HURDLE_T2, MIN_EXC2 = 1.65, 0.005


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def table(res: pd.DataFrame) -> dict:
    f = st.scored(res)
    if len(f) < 10:
        return {"scored": int(len(f))}
    w = st.week_id(f.entry_date)
    s = st.Boot(w, RESAMPLES, BOOT_SEED).mean(f.excess, w)
    return {"scored": int(len(f)), **s, "winsorised_mean": st.winsor_mean(f.excess), "hit_rate": float((f.net_return > 0).mean()),
            "by_year": {y: {"n": int(len(g)), "mean_excess": float(g.excess.mean())} for y, g in f.groupby(f.entry_date.str[:4])}}


def run_item(prep, ev, holds):
    out = {}
    for h in holds:
        out[h] = es.run_events(prep, ev, es.us_config(h), draws=DRAWS, seed=SEED)
    return out


def gates(t20, t5, t60):
    yrs = [t20["by_year"].get(y, {"n": 0, "mean_excess": None}) for y in ("2021", "2022")]
    return {"G1_t_ge_3.6": bool(t20["mean"] > 0 and t20["t"] >= HURDLE_T), "G2_excess_ge_1pct_and_winsorised_ge_0.5pct": bool(t20["mean"] >= MIN_EXC and t20["winsorised_mean"] >= MIN_WINS),
            "G3_positive_2021_and_2022": bool(all(y["n"] >= MIN_YEAR and y["mean_excess"] is not None and y["mean_excess"] > 0 for y in yrs)),
            "G4_positive_at_holds_5_and_60": bool(t5.get("mean", -1) > 0 and t60.get("mean", -1) > 0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--feasibility", action="store_true")
    g.add_argument("--stage", type=int, choices=(1, 2))
    a = ap.parse_args()
    stage = 1 if a.feasibility else a.stage
    out_dir = HERE / ("feasibility" if a.feasibility else f"results_stage{stage}")
    target = out_dir / ("FEASIBILITY.json" if a.feasibility else "RESULT.json")
    if target.exists():
        sys.exit(f"error: {target.name} exists; this runs once")
    pins = json.loads((HERE / "PINS.json").read_text()) if not a.feasibility else None
    if pins:
        bad = [p for p, h in pins["code"].items() if sha(ROOT / p) != h]
        if bad or sha(HERE / "events.csv") != pins["events_csv"] or sha(HERE / "filings8k.csv.gz") != pins["filings8k"]:
            sys.exit(f"error: inputs or code differ from PINS.json: {bad}")
    df, meta = global_panel.load(PANEL_MANIFEST)
    if pins and meta["sha256"] != pins["panel"]:
        sys.exit("error: panel differs")
    prep = es.prepare_us(df, START, END)
    ev_all = pd.read_csv(HERE / "events.csv", dtype={"accession": str, "item": str})
    ev_all = ev_all[ev_all.stage == stage]
    out_dir.mkdir(exist_ok=True)
    if a.feasibility:
        cnt = {}
        for it in ITEMS:
            res = es.run_events(prep, ev_all[ev_all["item"] == it], es.us_config(PRIMARY), draws=DRAWS, seed=SEED)
            f = st.scored(res)
            cnt[it] = {"events": int((ev_all["item"] == it).sum()), "scored_hold20": int(len(f)), "testable": bool(len(f) >= GO_MIN),
                       "scored_2021": int((f.entry_date.str[:4] == "2021").sum()), "scored_2022": int((f.entry_date.str[:4] == "2022").sum())}
        cnt["go"] = any(v["testable"] for k, v in cnt.items())
        target.write_text(json.dumps(cnt, indent=1) + "\n")
        print(json.dumps(cnt, indent=1))
        return 0
    passed_items = ITEMS
    if stage == 2:
        r1 = json.loads((HERE / "results_stage1" / "RESULT.json").read_text())
        passed_items = [i for i, v in r1["items"].items() if v.get("pass")]
        if not passed_items:
            sys.exit("error: no item passed Stage 1")
    res = {"experiment": "US_8K_ITEMS", "protocol": "research/US_8K_ITEMS/PROTOCOL.md", "stage": stage, "label": "historical research only; survivor-only prices",
           "inputs": {"events_csv": pins["events_csv"], "filings8k": pins["filings8k"], "panel": pins["panel"]}, "variants_reported": len(ITEMS) * len(HOLDS), "items": {}}
    for it in passed_items if stage == 2 else ITEMS:
        ev = ev_all[ev_all["item"] == it].reset_index(drop=True)
        holds = HOLDS if stage == 1 else (PRIMARY,)
        runs = run_item(prep, ev, holds)
        tabs = {h: table(r) for h, r in runs.items()}
        t20 = tabs[PRIMARY]
        rec = {"events": int(len(ev)), "holds": {str(h): t for h, t in tabs.items()}}
        if stage == 1:
            testable = t20["scored"] >= GO_MIN
            rec["testable"] = bool(testable)
            if testable:
                gg = gates(t20, tabs[5], tabs[60])
                rec.update({"gates": gg, "pass": bool(all(gg.values())), "negative": bool(t20["t"] <= -HURDLE_T), "p_one_sided": 0.5 * math.erfc(t20["t"] / math.sqrt(2))})
        else:
            rec["gates"] = {"G1p_t_ge_1.65": bool(t20["mean"] > 0 and t20["t"] >= HURDLE_T2), "G2p_ge_0.5pct": bool(t20["mean"] >= MIN_EXC2)}
            rec["pass"] = bool(all(rec["gates"].values()))
        res["items"][it] = rec
        for h, r in runs.items():
            r.to_csv(out_dir / f"events_{it}_hold{h}.csv", index=False)
        print(it, rec.get("pass"), {k: (round(v, 4) if isinstance(v, float) else v) for k, v in t20.items() if k in ("scored", "mean", "t")}, flush=True)
    res["verdict"] = "PASS" if any(v.get("pass") for v in res["items"].values()) else "FAIL"
    res["passing_items"] = [i for i, v in res["items"].items() if v.get("pass")]
    target.write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(res["verdict"], res["passing_items"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

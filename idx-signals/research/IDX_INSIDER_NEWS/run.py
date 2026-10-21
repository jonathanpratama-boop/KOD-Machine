"""IDX_INSIDER_NEWS: the single recorded run of PROTOCOL.md. Reads events.csv (insider-purchase articles the audited labelling accepted),
the pinned IDX panel and corporate-action registry, executes every event on the harness (idxsig.idx_events) for holds of 5, 20 and 60
sessions, draws each event's matched controls, and writes results/{RESULT.json, events.csv, grid.csv}. Refuses a second run.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/run.py
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import corporate_actions, idx_events, panel  # noqa: E402
from idxsig.execution import ExecConfig  # noqa: E402
from idxsig.market import Fees  # noqa: E402
from idxsig.provenance import MANIFESTS  # noqa: E402

_spec = importlib.util.spec_from_file_location("ann1m_run", ROOT / "research" / "BINANCE_ANN_1M" / "run.py")
m1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m1)                       # cluster_boot, winsor, p_one_sided

OUT = HERE / "results"
PANEL_MANIFEST = MANIFESTS / "panel-20261013T194245Z.json"
REGISTRY_MANIFEST = MANIFESTS / "ca_registry-20261013T194256Z.json"
START, END = "2021-01-22", "2023-12-29"            # TIER_1 data from 2021-01-22; the sealed holdout starts 2024-01-02
HOLDS, PRIMARY = (5, 20, 60), 20
DRAWS, SEED, BOOT, BOOT_SEED, HURDLE = 200, 20261007, 10_000, 20261024, 3.0
EXTRA_PER_SIDE, MIN_YEAR_EVENTS = 0.005, 20
EXPECTED: dict = {}                                 # filled by the protocol: sha256 of events.csv, the panel and the registry


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_inputs():
    df, meta, _ = panel.load(PANEL_MANIFEST)
    reg, rmeta = corporate_actions.load(REGISTRY_MANIFEST, panel_sha256=meta["sha256"])
    return df, reg, {"panel_sha256": meta["sha256"], "registry_sha256": rmeta["sha256"]}


def config(hold: int) -> ExecConfig:
    return ExecConfig(holding_days=hold, entry_lag=1, notional=10_000_000.0, max_participation=0.10, fees=Fees(0.0015, 0.0025),
                      data_end_exit="last_close", ca_mode="registry", fill_model="C")


def summarize(f: pd.DataFrame, seed: int) -> dict:
    day = f.posted_wib.str[:10]
    ex = m1.cluster_boot(f.excess, day, boot=BOOT, seed=seed)
    net = f.net_return.to_numpy()
    return {"n": int(len(f)), "mean_net": float(net.mean()), "winsorised_net": float(m1.winsor(net).mean()),
            "median_net": float(np.median(net)), "hit_rate": float((net > 0).mean()), "mean_control": float(f.control_mean.mean()),
            "mean_excess": ex["mean"], "t_excess": ex["t"], "lo95_excess": ex["lo95"], "hi95_excess": ex["hi95"],
            "share_excess_positive": ex["share_positive"], "clusters": ex["clusters"],
            "mean_net_extra_cost": float(net.mean() - 2 * EXTRA_PER_SIDE)}


def gates(primary: pd.DataFrame, stats: dict) -> dict:
    yr = primary.assign(year=primary.posted_wib.str[:4]).groupby("year").excess.agg(["count", "mean"])
    big = yr[yr["count"] >= MIN_YEAR_EVENTS]
    return {
        "G1_excess_t_ge_3": bool(stats["mean_excess"] > 0 and stats["t_excess"] >= HURDLE),
        "G2_net_and_winsorised_net_gt_0": bool(stats["mean_net"] > 0 and stats["winsorised_net"] > 0),
        "G3_excess_gt_0_in_each_year_with_20_events": bool(len(big) > 0 and (big["mean"] > 0).all()),
        "G4_net_gt_0_with_extra_0.5pct_per_side": bool(stats["mean_net_extra_cost"] > 0),
    }, {str(k): {"n": int(r["count"]), "mean_excess": float(r["mean"])} for k, r in yr.iterrows()}


def main() -> int:
    if (OUT / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this test runs once")
    events_path = HERE / "events.csv"
    df, reg, meta = load_inputs()
    got = {"events_csv": sha_file(events_path), "panel": meta["panel_sha256"], "registry": meta["registry_sha256"]}
    if EXPECTED and got != EXPECTED:
        sys.exit(f"error: inputs differ from the protocol: {got} != {EXPECTED}")
    events = pd.read_csv(events_path)
    if events.posted_wib.str[:10].max() > "2023-11-30":
        sys.exit("error: an event is too late for a 20-session hold before the sealed holdout")
    prep = idx_events.prepare(df, reg, START, END)
    if str(prep.m.dates[-1]) >= "2024-01-02":
        sys.exit("error: the window reaches the sealed IDX holdout")
    results, grid = {}, []
    for k, hold in enumerate(HOLDS):
        res = idx_events.run_events(prep, events, config(hold), draws=DRAWS, seed=SEED)
        results[hold] = res
        f = idx_events.filled(res)
        if len(f) >= 10:
            grid.append({"hold": hold, "mapped": int(len(res)), "status": idx_events.status_counts(res), **summarize(f, BOOT_SEED + k)})
    prim = results[PRIMARY]
    f = idx_events.filled(prim)
    stats = summarize(f, BOOT_SEED + HOLDS.index(PRIMARY))
    g, years = gates(f, stats)
    verdict = "PASS" if all(g.values()) else "FAIL"
    res = {
        "experiment": "IDX_INSIDER_NEWS", "protocol": "research/IDX_INSIDER_NEWS/PROTOCOL.md",
        "label": "historical research only; never prospective performance; news-posting times, not official filing times",
        "inputs": got, "window": [START, END],
        "events": {"in_table": int(len(events)), "mapped_to_panel": int(len(prim)), "status_counts": idx_events.status_counts(prim),
                   "filled_and_scored": int(len(f))},
        "primary_hold_20": stats, "years_primary": years, "gates": g, "verdict": verdict,
        "p_one_sided": m1.p_one_sided(stats["t_excess"]), "variants_reported": len(grid), "grid": grid,
    }
    OUT.mkdir(exist_ok=True)
    pd.DataFrame([{k: v for k, v in r.items() if k != "status"} for r in grid]).to_csv(OUT / "grid.csv", index=False)
    prim.to_csv(OUT / "events.csv", index=False)
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("events", "primary_hold_20", "years_primary", "gates", "verdict")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

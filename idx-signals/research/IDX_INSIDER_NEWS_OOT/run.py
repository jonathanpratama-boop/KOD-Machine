"""IDX_INSIDER_NEWS_OOT: the single recorded run of PROTOCOL.md. Reads PINS.json (sha256 of events.csv, the IDX panel, the corporate-action
registry and the code that runs) and refuses to start if anything differs, if the GO rule fails, or if results/RESULT.json exists. Executes
every event on the harness (idxsig.idx_events) for holds of 5, 20 and 60 sessions with 200 matched control draws each, applies the gates of
oot_stats.py, and writes results/{RESULT.json, events.csv, grid.csv}.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/run.py
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from oot_common import END, FIRST, HERE, LAST, OLD, ROOT, SEALED_END, START, load_old
from oot_stats import G1, gates, half_years, pooled, reading, tail

sys.path.insert(0, str(ROOT))
from idxsig import idx_events  # noqa: E402

r2 = load_old("run_v2")                                  # config(), summarize(), load_inputs(): test 23's, unchanged
OUT = HERE / "results"
GO_MIN_EXITED = 100


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if (OUT / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this test runs once")
    pins = json.loads((HERE / "PINS.json").read_text())
    code = {p: sha_file(ROOT / p) for p in pins["code"]}
    if code != pins["code"]:
        sys.exit(f"error: code differs from the pins: {[p for p in code if code[p] != pins['code'][p]]}")
    events_path = HERE / "events.csv"
    df, reg, meta = r2.load_inputs()
    got = {"events_csv": sha_file(events_path), "panel": meta["panel_sha256"], "registry": meta["registry_sha256"]}
    if got != {k: pins[k] for k in got}:
        sys.exit(f"error: inputs differ from the pins: {got}")
    events = pd.read_csv(events_path)
    day = events.posted_wib.str[:10]
    if day.min() < FIRST or day.max() > LAST:
        sys.exit("error: an event lies outside the protocol's window")
    prep = idx_events.prepare(df, reg, START, END)
    if str(prep.m.dates[0]) <= SEALED_END or str(prep.m.dates[-1]) != END:
        sys.exit("error: the market window is not the protocol's")
    results, grid = {}, []
    for k, hold in enumerate(r2.HOLDS):
        res = idx_events.run_events(prep, events, r2.config(hold), draws=r2.DRAWS, seed=r2.SEED)
        results[hold] = res
        if hold == r2.PRIMARY and (res.status == "EXITED").sum() < GO_MIN_EXITED:
            sys.exit(f"error: GO rule fails: {(res.status == 'EXITED').sum()} EXITED events < {GO_MIN_EXITED}; nothing written")
        f = idx_events.filled(res)
        if len(f) >= 10:
            grid.append({"hold": hold, "mapped": int(len(res)), "status": idx_events.status_counts(res), **r2.summarize(f, r2.BOOT_SEED + k)})
    prim = results[r2.PRIMARY]
    f = idx_events.filled(prim)
    stats = r2.summarize(f, r2.BOOT_SEED + r2.HOLDS.index(r2.PRIMARY))
    g, years = gates(f, stats)
    disc = json.loads((OLD / "results_corrected" / "RESULT.json").read_text())["primary_hold_20"]
    res = {
        "experiment": "IDX_INSIDER_NEWS_OOT", "protocol": "research/IDX_INSIDER_NEWS_OOT/PROTOCOL.md",
        "label": "historical research only; never prospective performance; news-posting times, not official filing times; TIER_3 (Yahoo, survivor-only) prices",
        "inputs": got, "window": [START, END], "events_window": [FIRST, LAST],
        "events": {"in_table": int(len(events)), "mapped_to_panel": int(len(prim)), "status_counts": idx_events.status_counts(prim),
                   "filled_and_scored": int(len(f))},
        "primary_hold_20": stats, "years_primary": years, "half_years_primary": half_years(f), "tail_primary": tail(f),
        "discovery_hold_20": {k: disc[k] for k in ("n", "mean_net", "mean_excess", "t_excess", "lo95_excess", "hi95_excess")},
        "pooled_with_discovery": pooled(disc, stats), "gates": g, "verdict": "PASS" if all(g.values()) else "FAIL", "reading": reading(g, stats),
        "p_one_sided": r2.m1.p_one_sided(stats["t_excess"]), "variants_reported": len(grid), "grid": grid,
    }
    OUT.mkdir(exist_ok=True)
    pd.DataFrame([{k: v for k, v in r.items() if k != "status"} for r in grid]).to_csv(OUT / "grid.csv", index=False)
    prim.to_csv(OUT / "events.csv", index=False)
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("events", "primary_hold_20", "years_primary", "half_years_primary", "tail_primary", "pooled_with_discovery",
                                          "gates", "verdict", "reading")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

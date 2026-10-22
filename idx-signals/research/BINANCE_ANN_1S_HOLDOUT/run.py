"""BINANCE_ANN_1S_HOLDOUT: the single recorded run of PROTOCOL.md. Reads the stored trades (ticks/ticks.npz, hashed in ticks/MANIFEST.json), computes
the reaction curve, the 18-cell capture grid and the four gates for the holdout events and their placebo with BINANCE_ANN_1S/run.py's own functions
(loaded unchanged), and writes results/{RESULT.json, curve.csv, grid.csv, grid_placebo.csv, events.csv}. Needs AUTHORIZATION.md; refuses a second run;
refuses if fewer than 30 events are usable and fillable at the gate cell (GO rule 2) and writes nothing then.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1S_HOLDOUT/run.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from hold_common import GO_MIN_FILLABLE, HERE, HURDLE_T, ROOT, S1, SEED, load, require_authorization, require_pinned_code, sha_file

s1 = load(S1 / "run.py", "ann1s_run")                # analyse, cell_stats, constants: tests 21/22's own code
m1 = s1.m1
OUT = HERE / "results"
G1, G2, G3, G4 = ("G1_L2s_H300_net_t_ge_1.65", "G2_L5s_H300_net_gt_0", "G3_L2s_H300_winsorised_net_gt_0", "G4_placebo_net_t_lt_2.5")


def decide(g1: dict, g2: dict, t_pl: float, reaction: dict, clock_flag: bool, hurdle: float) -> tuple[dict, str, str]:
    """The gates and the protocol's reading rules, in order."""
    gates = {G1: bool(g1.get("mean_net", -1) > 0 and g1.get("t_net", 0) >= hurdle), G2: bool(g2.get("mean_net", -1) > 0),
             G3: bool(g1.get("winsorised_net", -1) > 0), G4: bool(t_pl < 2.5)}
    if all(gates.values()):
        return gates, "PASS", "PASS: the seconds-level reaction and its capture at 2 s replicate on events not analysed before"
    if gates[G1]:
        return gates, "FAIL", "G1_HOLDS_ANOTHER_GATE_FAILS"
    if g1.get("mean_net", -1) > 0 and g1.get("t_net", 0) >= 1.0:
        return gates, "FAIL", "LEAN_WITHOUT_POWER"
    if clock_flag:
        sub = "THE_MOVE_STARTS_BEFORE_THE_PUBLISHED_TIME"
    elif reaction["R_60"] > 0.01 and reaction["share_done_by_1s"] >= 0.8:
        sub = "THE_WINDOW_HAS_CLOSED_THE_MARKET_GOT_FASTER"
    elif reaction["R_60"] <= 0.01:
        sub = "THE_REACTION_ITSELF_SHRANK"
    else:
        sub = "NO_CLEAR_WINDOW"
    return gates, "FAIL", f"NO_SIGN_IT_PERSISTED: {sub}"


def core(ticks_dir: Path, seed: int, hurdle: float, check_go: bool = True) -> dict:
    """Everything the run computes, from a ticks directory (npz + MANIFEST.json). Used by main() and by the rehearsal."""
    man = json.loads((ticks_dir / "MANIFEST.json").read_text())
    npz = ROOT / man["npz"]["path"]
    if sha_file(npz) != man["npz"]["sha256"]:
        sys.exit("error: ticks.npz does not match its manifest")
    z = np.load(npz)
    idx = z["index"]
    series = {}
    for s in man["series"]:
        lo, hi = idx[s["row"]], idx[s["row"] + 1]
        series[(s["event_key"], s["kind"])] = (s, z["ts"][lo:hi], z["price"][lo:hi], z["m"][lo:hi])
    s1.SEED = seed
    ev, pl = s1.analyse(series, "event"), s1.analyse(series, "placebo")
    gi = s1.CELLS.index((s1.GATE_L, s1.GATE_H))
    n_fill = int(ev[f"G_{s1.GATE_L}_{s1.GATE_H}"].notna().sum())
    if check_go and n_fill < GO_MIN_FILLABLE:
        sys.exit(f"error: GO rule 2 fails: {n_fill} events usable and fillable at the gate cell < {GO_MIN_FILLABLE}; nothing written")
    grid = [s1.cell_stats(ev, lat, hold, k) for k, (lat, hold) in enumerate(s1.CELLS)]
    grid_pl = [s1.cell_stats(pl, lat, hold, k) for k, (lat, hold) in enumerate(s1.CELLS)]
    g1, g2 = grid[gi], grid[s1.CELLS.index((s1.GATE_L2, s1.GATE_H))]
    gross_pl = pl[f"G_{s1.GATE_L}_{s1.GATE_H}"].dropna()
    t_pl = m1.cluster_boot(gross_pl - 2 * s1.FEE, pl.loc[gross_pl.index].day, boot=s1.BOOT, seed=seed + gi)["t"]
    mean = lambda c: float(ev[c].mean())  # noqa: E731
    r60, r1 = mean("R_60"), mean("R_1")
    share1 = r1 / r60 if r60 > 0 else float("nan")
    pre_mean, total_mean = float(ev.pre60.mean()), float(ev.total60.mean())
    clock = bool(total_mean > 0.01 and pre_mean >= 0.25 * total_mean)
    reaction = {"R_-1": mean("R_-1"), "R_0": mean("R_0"), "R_0.5": mean("R_0.5"), "R_1": r1, "R_2": mean("R_2"), "R_5": mean("R_5"), "R_10": mean("R_10"),
                "R_60": r60, "R_300": mean("R_300"), "share_done_by_1s": share1, "share_done_by_2s": mean("R_2") / r60 if r60 > 0 else None}
    gates, verdict, reading = decide(g1, g2, float(t_pl), reaction, clock, hurdle)
    cc = f"G_{s1.GATE_L}_{s1.GATE_H}"
    by_year = {str(y): {"n": int(g[cc].notna().sum()), "mean_net": float(g[cc].mean() - 2 * s1.FEE)} for y, g in ev.groupby("year") if g[cc].notna().any()}
    curve = pd.DataFrame({"s": s1.S_CURVE, "event_mean": [ev[f"R_{s}"].mean() for s in s1.S_CURVE], "event_median": [ev[f"R_{s}"].median() for s in s1.S_CURVE],
                          "event_lo95": [m1.cluster_boot(ev[f"R_{s}"].dropna(), ev.loc[ev[f"R_{s}"].notna()].day, boot=s1.BOOT, seed=seed + 100)["lo95"] for s in s1.S_CURVE],
                          "event_hi95": [m1.cluster_boot(ev[f"R_{s}"].dropna(), ev.loc[ev[f"R_{s}"].notna()].day, boot=s1.BOOT, seed=seed + 100)["hi95"] for s in s1.S_CURVE],
                          "placebo_mean": [pl[f"R_{s}"].mean() for s in s1.S_CURVE], "placebo_median": [pl[f"R_{s}"].median() for s in s1.S_CURVE]})
    half = ev.half_move_s.dropna()
    res = {
        "inputs": {"ticks_npz_sha256": man["npz"]["sha256"], "events_csv_sha256": man["events_csv_sha256"], "seed": seed, "hurdle_t": hurdle},
        "events": {"in_manifest": len({k for k, _ in series}), "usable_event": int(len(ev)), "usable_placebo": int(len(pl)), "fillable_at_gate_cell": n_fill},
        "reaction": reaction,
        "clock_check": {"pre_mean": pre_mean, "total_mean": total_mean, "pre_share": pre_mean / total_mean if total_mean else None, "R_-60": mean("R_-60"),
                        "R_-30": mean("R_-30"), "R_-10": mean("R_-10"), "R_-5": mean("R_-5"), "R_-2": mean("R_-2")},
        "half_move": {"n": int(len(half)), "median_s": float(half.median()) if len(half) else None,
                      "q25_s": float(half.quantile(.25)) if len(half) else None, "q75_s": float(half.quantile(.75)) if len(half) else None,
                      "share_by_s": {str(t): float((half <= t).mean()) for t in (0.5, 1, 2, 5, 10, 30)} if len(half) else {}},
        "spread_median": {"before_T": float(ev.spread_before.median()), "first_2s": float(ev.spread_after_2s.median())},
        "gate_cell_L2_H300": g1, "gate_cell_L5_H300": g2, "placebo_L2_H300": {**grid_pl[gi], "net_t": float(t_pl)}, "by_year_gate_cell": by_year,
        "gates": gates, "verdict": verdict, "clock_flag": clock, "reading": reading,
        "p_one_sided_G1": m1.p_one_sided(g1["t_net"]) if "t_net" in g1 else None, "variants_reported": len(s1.CELLS),
    }
    return {"res": res, "curve": curve, "grid": pd.DataFrame(grid), "grid_pl": pd.DataFrame(grid_pl), "events": ev}


def main() -> int:
    require_authorization()
    require_pinned_code()
    if (OUT / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this test runs once")
    man = json.loads((HERE / "ticks" / "MANIFEST.json").read_text())
    if sha_file(HERE / "feasibility" / "events.csv") != man["events_csv_sha256"]:
        sys.exit("error: feasibility/events.csv changed since the trades were fetched")
    out = core(HERE / "ticks", SEED, HURDLE_T)
    res = {"experiment": "BINANCE_ANN_1S_HOLDOUT", "protocol": "research/BINANCE_ANN_1S_HOLDOUT/PROTOCOL.md",
           "label": "historical research only; never prospective performance; out-of-time test of test 22 on events announced 2024-01-01..2026-09-30", **out["res"]}
    OUT.mkdir(exist_ok=True)
    out["grid"].to_csv(OUT / "grid.csv", index=False)
    out["grid_pl"].to_csv(OUT / "grid_placebo.csv", index=False)
    out["curve"].to_csv(OUT / "curve.csv", index=False)
    out["events"].to_csv(OUT / "events.csv", index=False)
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("events", "reaction", "clock_check", "half_move", "spread_median", "gate_cell_L2_H300", "gate_cell_L5_H300",
                                          "placebo_L2_H300", "by_year_gate_cell", "gates", "verdict", "reading")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""BINANCE_ANN_1S: the single recorded run of PROTOCOL.md. Reads the stored trades (ticks/ticks.npz, hashed in
ticks/MANIFEST.json), computes the reaction curve, the capture grid and the four gates for the 112 events and their placebo,
and writes results/{RESULT.json, curve.csv, grid.csv, events.csv}. Refuses a second run.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1S/run.py
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
OUT = HERE / "results"
_spec = importlib.util.spec_from_file_location("ann1m_run", ROOT / "research" / "BINANCE_ANN_1M" / "run.py")
m1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m1)                       # cluster_boot, winsor, p_one_sided: the registered test's own code

S_CURVE = (-60, -30, -10, -5, -2, -1, 0, 0.25, 0.5, 1, 2, 3, 5, 10, 20, 30, 60, 120, 300)
LATENCY, HOLD = (0.5, 1, 2, 5, 10, 30), (60, 300, 3600)
FEE, FEE_HIGH = 0.001, 0.002                       # per side
SEED, HURDLE, BOOT = 20261023, 3.0, 10_000
ENTRY_WAIT_MS, EXIT_WAIT_MS, FRESH_MS, FRESH_N = 60_000, 120_000, 60_000, 3
GATE_L, GATE_H, GATE_L2 = 2, 300, 5
CELLS = [(l, h) for l in LATENCY for h in HOLD]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def p0(ts: np.ndarray, price: np.ndarray, T: int):
    """Price of the last trade strictly before T, if at least FRESH_N trades fall in the FRESH_MS before T."""
    k = int(np.searchsorted(ts, T, side="left"))
    if k == 0 or k - int(np.searchsorted(ts, T - FRESH_MS, side="left")) < FRESH_N:
        return None
    return float(price[k - 1])


def price_at(ts: np.ndarray, price: np.ndarray, t: float):
    k = int(np.searchsorted(ts, t, side="right"))
    return float(price[k - 1]) if k else None


def first_trade(ts, price, m, t0: float, wait_ms: int, taker_buy: bool):
    """(time, price) of the first buyer-initiated (taker_buy) or seller-initiated trade in [t0, t0 + wait_ms], else None."""
    lo, hi = int(np.searchsorted(ts, t0, side="left")), int(np.searchsorted(ts, t0 + wait_ms, side="right"))
    hits = np.flatnonzero(m[lo:hi] == (not taker_buy))
    return (int(ts[lo + hits[0]]), float(price[lo + hits[0]])) if len(hits) else None


def capture(ts, price, m, T: int, latency_s: float, hold_s: float):
    """Gross return of: buy at the first taker-buy trade at or after T + latency, sell at the first taker-sell trade at or
    after entry + hold. None if either leg cannot be filled in its window."""
    e = first_trade(ts, price, m, T + latency_s * 1000, ENTRY_WAIT_MS, True)
    if e is None:
        return None
    x = first_trade(ts, price, m, e[0] + hold_s * 1000, EXIT_WAIT_MS, False)
    return None if x is None else x[1] / e[1] - 1.0


def half_move_time(ts, price, T: int, base: float, r60: float):
    """Seconds after T until the price first reaches half of its own 60-second reaction."""
    k = int(np.searchsorted(ts, T, side="left"))
    hit = np.flatnonzero(price[k:] >= base * (1 + 0.5 * r60))
    return float((ts[k + hit[0]] - T) / 1000) if len(hit) else None


def spread(ts, price, m, lo: int, hi: int):
    """(last taker-buy price - last taker-sell price) / mid within [lo, hi), else None."""
    a, b = int(np.searchsorted(ts, lo, side="left")), int(np.searchsorted(ts, hi, side="left"))
    buys, sells = np.flatnonzero(~m[a:b]), np.flatnonzero(m[a:b])
    if not len(buys) or not len(sells):
        return None
    pb, ps = price[a + buys[-1]], price[a + sells[-1]]
    return float((pb - ps) / ((pb + ps) / 2))


def analyse(series: dict, kind: str) -> pd.DataFrame:
    """One row per usable series of `kind`: the reaction at each s, the half-move time and the capture grid (gross)."""
    rows = []
    for (key, k), (s, ts, price, m) in sorted(series.items(), key=lambda kv: kv[1][0]["T"]):
        if k != kind:
            continue
        T = s["T"]
        base = p0(ts, price, T)
        if base is None:
            continue
        rec = {"event_key": key, "token": s["token"], "T": T, "t_event_ms": s["t_event_ms"], "p0": base}
        for sec in S_CURVE:
            p = price_at(ts, price, T + sec * 1000)
            rec[f"R_{sec}"] = np.nan if p is None else p / base - 1.0
        r60 = rec["R_60"]
        early, late = price_at(ts, price, T - 60_000), price_at(ts, price, T + 60_000)
        rec["pre60"] = np.nan if early is None else base / early - 1.0
        rec["total60"] = np.nan if early is None or late is None else late / early - 1.0
        rec["half_move_s"] = half_move_time(ts, price, T, base, r60) if r60 >= 0.01 else np.nan
        sp_b, sp_a = spread(ts, price, m, T - 60_000, T), spread(ts, price, m, T, T + 2_000)
        rec["spread_before"], rec["spread_after_2s"] = (np.nan if sp_b is None else sp_b), (np.nan if sp_a is None else sp_a)
        for (lat, hold) in CELLS:
            g = capture(ts, price, m, T, lat, hold)
            rec[f"G_{lat}_{hold}"] = np.nan if g is None else g
        rows.append(rec)
    df = pd.DataFrame(rows)
    ts_day = pd.to_datetime(df.t_event_ms, unit="ms", utc=True)
    df["day"], df["year"] = ts_day.dt.strftime("%Y-%m-%d"), ts_day.dt.year
    return df


def cell_stats(df: pd.DataFrame, lat, hold, k: int) -> dict:
    g = df[f"G_{lat}_{hold}"].dropna()
    sub = df.loc[g.index]
    if len(g) < 10:
        return {"L": lat, "H": hold, "n": int(len(g)), "unfillable": int(len(df) - len(g))}
    st = m1.cluster_boot(g - 2 * FEE, sub.day, boot=BOOT, seed=SEED + k)
    return {"L": lat, "H": hold, "n": int(len(g)), "unfillable": int(len(df) - len(g)), "mean_gross": float(g.mean()),
            "mean_net": st["mean"], "t_net": st["t"], "lo95_net": st["lo95"], "share_net_positive": st["share_positive"],
            "mean_net_conservative": float(g.mean() - 2 * FEE_HIGH), "winsorised_net": float(m1.winsor((g - 2 * FEE).to_numpy()).mean())}


def main() -> int:
    if (OUT / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this test runs once")
    man = json.loads((HERE / "ticks" / "MANIFEST.json").read_text())
    if sha_file(ROOT / man["npz"]["path"]) != man["npz"]["sha256"]:
        sys.exit("error: ticks.npz does not match its manifest")
    for name, f in (("events_csv_sha256", ROOT / "research" / "BINANCE_ANN_1M" / "results" / "events.csv"),
                    ("feasibility_events_sha256", ROOT / "research" / "BINANCE_ANN_1M" / "feasibility" / "events.csv")):
        if sha_file(f) != man[name]:
            sys.exit(f"error: {f.name} changed since the trades were fetched")
    z = np.load(ROOT / man["npz"]["path"])
    series = {}
    idx = z["index"]
    for s in man["series"]:
        lo, hi = idx[s["row"]], idx[s["row"] + 1]
        series[(s["event_key"], s["kind"])] = (s, z["ts"][lo:hi], z["price"][lo:hi], z["m"][lo:hi])
    ev, pl = analyse(series, "event"), analyse(series, "placebo")
    n_total = len({k for k, _ in series})
    grid, grid_pl = [], []
    for k, (lat, hold) in enumerate(CELLS):
        grid.append(cell_stats(ev, lat, hold, k))
        grid_pl.append(cell_stats(pl, lat, hold, k))
    gi = CELLS.index((GATE_L, GATE_H))
    g1, g2 = grid[gi], grid[CELLS.index((GATE_L2, GATE_H))]
    pl1 = grid_pl[gi]
    gross_pl = pl[f"G_{GATE_L}_{GATE_H}"].dropna()
    t_pl = m1.cluster_boot(gross_pl - 2 * FEE, pl.loc[gross_pl.index].day, boot=BOOT, seed=SEED + gi)["t"]   # placebo NET
    gates = {
        "G1_L2s_H300_net_t_ge_3": bool(g1.get("mean_net", -1) > 0 and g1.get("t_net", 0) >= HURDLE),
        "G2_L5s_H300_net_gt_0": bool(g2.get("mean_net", -1) > 0),
        "G3_L2s_H300_winsorised_net_gt_0": bool(g1.get("winsorised_net", -1) > 0),
        "G4_placebo_net_t_lt_2.5": bool(t_pl < 2.5),
    }
    verdict = "PASS" if all(gates.values()) else "FAIL"
    mean = lambda c: float(ev[c].mean())  # noqa: E731
    r60, r1, rm1 = mean("R_60"), mean("R_1"), mean("R_-1")
    share1 = r1 / r60 if r60 > 0 else float("nan")
    pre_mean, total_mean = float(ev.pre60.mean()), float(ev.total60.mean())
    clock = bool(total_mean > 0.01 and pre_mean >= 0.25 * total_mean)
    if verdict == "PASS":
        reading = "PASS: a window of seconds survives fees"
    elif clock:
        reading = "FAIL: the move starts before the published time (early clock or a leak)"
    elif r60 > 0.01 and share1 >= 0.8:
        reading = "FAIL: about four fifths of the move is done within one second of the published time"
    elif r60 > 0.01 and share1 < 0.5:
        reading = "FAIL: a window of seconds exists but the net capture is not significant"
    else:
        reading = "FAIL: in between (half to four fifths of the move done within one second) or no clear move"
    curve = pd.DataFrame({"s": S_CURVE,
                          "event_mean": [ev[f"R_{s}"].mean() for s in S_CURVE], "event_median": [ev[f"R_{s}"].median() for s in S_CURVE],
                          "event_lo95": [m1.cluster_boot(ev[f"R_{s}"].dropna(), ev.loc[ev[f"R_{s}"].notna()].day, boot=BOOT, seed=SEED + 100)["lo95"] for s in S_CURVE],
                          "event_hi95": [m1.cluster_boot(ev[f"R_{s}"].dropna(), ev.loc[ev[f"R_{s}"].notna()].day, boot=BOOT, seed=SEED + 100)["hi95"] for s in S_CURVE],
                          "placebo_mean": [pl[f"R_{s}"].mean() for s in S_CURVE], "placebo_median": [pl[f"R_{s}"].median() for s in S_CURVE]})
    half = ev.half_move_s.dropna()
    res = {
        "experiment": "BINANCE_ANN_1S", "protocol": "research/BINANCE_ANN_1S/PROTOCOL.md",
        "label": "historical research only; never prospective performance; follow-up on the same events as BINANCE_ANN_1M",
        "inputs": {"ticks_npz_sha256": man["npz"]["sha256"], "events_csv_sha256": man["events_csv_sha256"]},
        "events": {"in_registered_run": n_total, "usable_event": int(len(ev)), "usable_placebo": int(len(pl))},
        "reaction": {"R_-1": rm1, "R_0": mean("R_0"), "R_0.5": mean("R_0.5"), "R_1": r1, "R_2": mean("R_2"), "R_5": mean("R_5"),
                     "R_10": mean("R_10"), "R_60": r60, "R_300": mean("R_300"), "share_done_by_1s": share1,
                     "share_done_by_2s": mean("R_2") / r60 if r60 > 0 else None},
        "clock_check": {"pre_mean": pre_mean, "total_mean": total_mean, "pre_share": pre_mean / total_mean if total_mean else None,
                        "R_-60": mean("R_-60"), "R_-30": mean("R_-30"), "R_-10": mean("R_-10"), "R_-5": mean("R_-5"),
                        "R_-2": mean("R_-2")},
        "half_move": {"n": int(len(half)), "median_s": float(half.median()) if len(half) else None,
                      "q25_s": float(half.quantile(.25)) if len(half) else None, "q75_s": float(half.quantile(.75)) if len(half) else None,
                      "share_by_s": {str(t): float((half <= t).mean()) for t in (0.5, 1, 2, 5, 10, 30)} if len(half) else {}},
        "spread_median": {"before_T": float(ev.spread_before.median()), "first_2s": float(ev.spread_after_2s.median())},
        "gate_cell_L2_H300": g1, "gate_cell_L5_H300": g2, "placebo_L2_H300": {**pl1, "net_t": float(t_pl)},
        "gates": gates, "verdict": verdict, "clock_flag": clock, "reading": reading,
        "p_one_sided_G1": m1.p_one_sided(g1["t_net"]) if "t_net" in g1 else None, "variants_reported": len(CELLS),
    }
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(grid).to_csv(OUT / "grid.csv", index=False)
    pd.DataFrame(grid_pl).to_csv(OUT / "grid_placebo.csv", index=False)
    curve.to_csv(OUT / "curve.csv", index=False)
    ev.to_csv(OUT / "events.csv", index=False)
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("events", "reaction", "clock_check", "half_move", "gate_cell_L2_H300", "gate_cell_L5_H300", "placebo_L2_H300",
                                          "gates", "verdict", "reading")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""BINANCE_ANN_1M: the single recorded run of PROTOCOL.md. Reads the stored 1-minute closes and trade counts
(minutes/minutes.npz, hashed in minutes/MANIFEST.json) and the eligible events (feasibility/events.csv), computes the four
gates and the reported extras, and writes results/{RESULT.json, events.csv, grid.csv, paths.csv}. Refuses a second run.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1M/run.py
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "results"
M_LO = -65                                    # minute offset of column 0 (columns hold offsets -65 .. +1455)
MINUTE, DAY_MS = 60_000, 86_400_000
DELAYS, HORIZONS = (0, 1, 4, 14), (5, 15, 60, 240, 1440)
PATH_M = (-60, -30, -15, -5, -1, 0, 1, 2, 3, 4, 5, 10, 15, 30, 60, 120, 240, 480, 1440)
COST, COST_LOW, COST_HIGH = 0.002, 0.001, 0.004     # per side
BOOT, SEED, HURDLE = 10_000, 20261022, 3.0
MIN_CTRL, K_KEEP, PRE_TRADED = 5, 10, 30
MIN_YEAR_EVENTS = 20
PRIMARY, DELAYED = (0, 60), (4, 60)


def col(m: int) -> int:
    return m - M_LO


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ffill(closes: np.ndarray) -> np.ndarray:
    """Row-wise forward fill; columns before a row's first bar stay NaN."""
    c = np.asarray(closes, float)
    ok = ~np.isnan(c)
    pos = np.where(ok, np.arange(c.shape[1]), 0)
    np.maximum.accumulate(pos, axis=1, out=pos)
    out = np.take_along_axis(c, pos, axis=1)
    first = np.where(ok.any(axis=1), ok.argmax(axis=1), c.shape[1])
    out[np.arange(c.shape[1])[None, :] < first[:, None]] = np.nan
    return out


def quality(trades: np.ndarray) -> bool:
    """Traded in the announcement bar and in at least PRE_TRADED of the 60 minutes before it."""
    return bool(trades[col(0)] > 0 and (trades[col(-60):col(0)] > 0).sum() >= PRE_TRADED)


def traded_at(trades: np.ndarray, d: int) -> bool:
    return bool(trades[col(d)] > 0)


def gross(c: np.ndarray, d: int, h: int) -> float:
    return float(c[col(d + h)] / c[col(d)] - 1.0)


def winsor(x: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(x, [1, 99])
    return np.clip(x, lo, hi)


def p_one_sided(t: float) -> float:
    return 0.5 * math.erfc(t / math.sqrt(2.0))


def cluster_boot(x, clusters, boot: int = BOOT, seed: int = SEED) -> dict:
    """Mean of x with a day-cluster bootstrap: resample clusters with replacement, recompute the pooled mean."""
    x, clusters = np.asarray(x, float), np.asarray(clusters)
    uniq, inv = np.unique(clusters, return_inverse=True)
    s, n = np.bincount(inv, weights=x), np.bincount(inv).astype(float)
    draws = np.random.default_rng(seed).integers(0, len(uniq), size=(boot, len(uniq)))
    means = s[draws].sum(1) / n[draws].sum(1)
    mean, se = float(x.mean()), float(means.std(ddof=1))
    return {"n": int(len(x)), "clusters": int(len(uniq)), "mean": mean, "se": se, "t": mean / se if se > 0 else float("nan"),
            "lo95": float(np.percentile(means, 2.5)), "hi95": float(np.percentile(means, 97.5)),
            "share_positive": float((x > 0).mean())}


def event_table(events: pd.DataFrame, man: dict, closes: np.ndarray, trades: np.ndarray) -> list[dict]:
    """For every event: its series row, its controls (first K_KEEP that pass the quality rule, in permutation order) and
    the base validity. No return is computed here."""
    rows = {}
    for s in man["series"]:
        rows.setdefault(s["event_key"], {"event": None, "controls": []})
        if s["role"] == "event":
            rows[s["event_key"]]["event"] = s["row"]
        else:
            rows[s["event_key"]]["controls"].append((s["rank"], s["row"]))
    out = []
    for e in man["events"]:
        r = rows[e["event_key"]]
        ev_row = r["event"]
        ctrl = [row for _, row in sorted(r["controls"]) if quality(trades[row])][:K_KEEP]
        out.append({"event_key": e["event_key"], "token": e["token"], "pair": e["pair"], "t_ms": e["t_ms"], "row": ev_row,
                    "controls": ctrl, "quality": quality(trades[ev_row]), "valid": bool(quality(trades[ev_row]) and len(ctrl) >= MIN_CTRL)})
    return out


def spec_values(table: list[dict], cf: np.ndarray, trades: np.ndarray, d: int, h: int) -> pd.DataFrame:
    """Per event gross, control mean and excess for entry delay d and hold h. An event is in the spec if it is valid, it
    traded in its entry bar, and at least MIN_CTRL controls also traded there."""
    rec = []
    for e in table:
        if not e["valid"] or not traded_at(trades[e["row"]], d):
            continue
        ctrl = [r for r in e["controls"] if traded_at(trades[r], d)]
        if len(ctrl) < MIN_CTRL:
            continue
        g = gross(cf[e["row"]], d, h)
        cg = np.array([gross(cf[r], d, h) for r in ctrl])
        if not np.isfinite(g) or not np.isfinite(cg).all():
            continue
        rec.append({"event_key": e["event_key"], "token": e["token"], "t_ms": e["t_ms"], "gross": g,
                    "control_mean": float(cg.mean()), "excess": g - float(cg.mean()), "n_controls": len(ctrl)})
    df = pd.DataFrame(rec)
    if len(df):
        ts = pd.to_datetime(df.t_ms, unit="ms", utc=True)
        df["day"], df["year"] = ts.dt.strftime("%Y-%m-%d"), ts.dt.year
    return df


def path_means(table: list[dict], cf: np.ndarray) -> pd.DataFrame:
    """Mean path from C[b0-1] at each offset in PATH_M for the event, its controls and the difference (valid events)."""
    ev, ct = [], []
    for e in table:
        if not e["valid"]:
            continue
        base = lambda r: cf[r][col(-1)]  # noqa: E731
        ev.append([cf[e["row"]][col(m)] / base(e["row"]) - 1.0 for m in PATH_M])
        ct.append(np.mean([[cf[r][col(m)] / base(r) - 1.0 for m in PATH_M] for r in e["controls"]], axis=0))
    ev, ct = np.array(ev), np.array(ct)
    return pd.DataFrame({"m": PATH_M, "event": np.nanmean(ev, 0), "controls": np.nanmean(ct, 0),
                         "excess": np.nanmean(ev - ct, 0), "n": np.isfinite(ev - ct).sum(0)})


def pre_and_minute(table: list[dict], cf: np.ndarray) -> dict:
    pre, minute = [], []
    for e in table:
        if not e["valid"]:
            continue
        f = lambda r, a, b: cf[r][col(a)] / cf[r][col(b)] - 1.0  # noqa: E731
        pre.append(f(e["row"], -1, -61) - np.mean([f(r, -1, -61) for r in e["controls"]]))
        minute.append(f(e["row"], 0, -1) - np.mean([f(r, 0, -1) for r in e["controls"]]))
    return {"pre_announcement_excess_m60_to_m1": float(np.nanmean(pre)), "announcement_minute_excess": float(np.nanmean(minute))}


def main() -> int:
    if (OUT / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this test runs once")
    man = json.loads((HERE / "minutes" / "MANIFEST.json").read_text())
    if sha_file(ROOT / man["npz"]["path"]) != man["npz"]["sha256"]:
        sys.exit("error: minutes.npz does not match its manifest")
    if sha_file(HERE / "feasibility" / "events.csv") != man["events_csv_sha256"]:
        sys.exit("error: events.csv changed since the minutes were fetched")
    z = np.load(ROOT / man["npz"]["path"])
    closes, trades = z["closes"].astype(float), z["trades"]
    cf = ffill(closes)
    events = pd.read_csv(HERE / "feasibility" / "events.csv")
    table = event_table(events, man, closes, trades)
    n_valid = sum(e["valid"] for e in table)

    grid, cells = [], {}
    for k, (d, h) in enumerate((d, h) for d in DELAYS for h in HORIZONS):
        df = spec_values(table, cf, trades, d, h)
        cells[(d, h)] = df
        if len(df) >= 10:
            st = cluster_boot(df.excess, df.day, seed=SEED + k)
            gst = cluster_boot(df.gross, df.day, seed=SEED + k)
            grid.append({"d": d, "h": h, "n": st["n"], "mean_gross": gst["mean"], "mean_excess": st["mean"], "t_excess": st["t"],
                         "lo95_excess": st["lo95"], "share_excess_positive": st["share_positive"],
                         "mean_net": gst["mean"] - 2 * COST, "mean_net_low_cost": gst["mean"] - 2 * COST_LOW,
                         "mean_net_high_cost": gst["mean"] - 2 * COST_HIGH})
    prim, dly = cells[PRIMARY], cells[DELAYED]
    st = cluster_boot(prim.excess, prim.day, seed=SEED + [(d, h) for d in DELAYS for h in HORIZONS].index(PRIMARY))
    net = prim.gross - 2 * COST
    years = {int(y): {"n": int(len(g)), "mean_excess": float(g.excess.mean())} for y, g in prim.groupby("year")}
    big_years = {y: v for y, v in years.items() if v["n"] >= MIN_YEAR_EVENTS}
    gates = {
        "G1_excess_t_ge_3": bool(st["mean"] > 0 and st["t"] >= HURDLE),
        "G2_net_and_winsorised_net_gt_0": bool(net.mean() > 0 and winsor(net.to_numpy()).mean() > 0),
        "G3_excess_gt_0_in_each_year_with_20_events": bool(big_years and all(v["mean_excess"] > 0 for v in big_years.values())),
        "G4_delayed_5min_excess_gt_0": bool(len(dly) > 0 and dly.excess.mean() > 0),
    }
    paths = path_means(table, cf)
    extra = pre_and_minute(table, cf)
    ex0 = float(paths.loc[paths.m == 0, "excess"].iloc[0])
    ex60 = float(paths.loc[paths.m == 60, "excess"].iloc[0])
    leak = bool(extra["pre_announcement_excess_m60_to_m1"] > 0 and extra["pre_announcement_excess_m60_to_m1"] >= ex60)
    within_minute = bool(ex60 > 0 and ex0 >= 0.5 * ex60)
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict == "PASS":
        reading = "PASS: partly capturable after an obtainable delay and costs"
    elif leak:
        reading = "FAIL: the clock or a leak places the move before the published time"
    elif within_minute:
        reading = "FAIL: priced inside the announcement minute; an obtainable entry is later than the move"
    else:
        reading = "FAIL: nothing obtainable at minute resolution in 2020-2023"
    res = {
        "experiment": "BINANCE_ANN_1M", "protocol": "research/BINANCE_ANN_1M/PROTOCOL.md",
        "label": "historical research only; never prospective performance",
        "inputs": {"minutes_npz_sha256": man["npz"]["sha256"], "events_csv_sha256": man["events_csv_sha256"],
                   "panel_manifest": man["panel_manifest"]},
        "events": {"eligible": len(table), "quality_ok": sum(e["quality"] for e in table), "valid": n_valid,
                   "in_primary_spec": int(len(prim)), "in_delayed_spec": int(len(dly))},
        "primary_d0_h60": {**st, "mean_gross": float(prim.gross.mean()), "mean_net": float(net.mean()),
                           "winsorised_mean_net": float(winsor(net.to_numpy()).mean()), "p_one_sided": p_one_sided(st["t"])},
        "delayed_d4_h60": cluster_boot(dly.excess, dly.day, seed=SEED + 99),
        "years_primary": years, "path_excess_m0": ex0, "path_excess_m60": ex60, **extra,
        "leak_flag": leak, "priced_within_minute_flag": within_minute, "gates": gates, "verdict": verdict, "reading": reading,
        "variants_reported": len(grid),
    }
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(grid).to_csv(OUT / "grid.csv", index=False)
    paths.to_csv(OUT / "paths.csv", index=False)
    prim.assign(net=net).to_csv(OUT / "events.csv", index=False)
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("events", "primary_d0_h60", "delayed_d4_h60", "gates", "verdict", "reading")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

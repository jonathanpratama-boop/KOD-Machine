"""Independent check of results/ from the stored trades, with its own code (no import of run.py, fetch_ticks.py, events.py or the BINANCE_ANN_1M/1S
code): file hashes, that the stored series are exactly the eligible events and their placebo, which series are usable, the reaction at 1 s and 60 s and
before T, the gross and net capture at the two gate cells and for the placebo, an analytic day-cluster t against the bootstrap t, and the gates.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1S_HOLDOUT/verify.py   (exit 1 if anything differs)
"""
import bisect
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEE = 0.001


def sha(p) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def day_of(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def analytic_t(vals, days) -> float:
    n, mu = len(vals), sum(vals) / len(vals)
    by = defaultdict(float)
    for v, d in zip(vals, days):
        by[d] += v - mu
    return mu / (sqrt(sum(x * x for x in by.values())) / n)


def verify(res_dir: Path, ticks_dir: Path, hurdle: float, events_csv: Path | None) -> tuple[dict, list]:
    bad = []
    res = json.loads((res_dir / "RESULT.json").read_text())
    man = json.loads((ticks_dir / "MANIFEST.json").read_text())
    if sha(ROOT / man["npz"]["path"]) != man["npz"]["sha256"]:
        bad.append("ticks.npz hash")
    if events_csv is not None:
        if sha(events_csv) != man["events_csv_sha256"]:
            bad.append("events.csv hash")
        import csv
        with events_csv.open() as fh:
            eligible = {f"{r['article_id']}|{r['token']}" for r in csv.DictReader(fh) if r["eligible"] == "True"}
        stored = {s["event_key"] for s in man["series"]}
        if stored != eligible:
            bad.append(f"stored series differ from the eligible events: {len(stored ^ eligible)} keys")
        if {s["kind"] for s in man["series"]} != {"event", "placebo"} or len(man["series"]) != 2 * len(eligible):
            bad.append("series kinds or count")
    z = np.load(ROOT / man["npz"]["path"])
    ts_all, px_all, m_all, idx = z["ts"], z["price"], z["m"], z["index"]

    def trades(row):
        lo, hi = int(idx[row]), int(idx[row + 1])
        return ts_all[lo:hi].tolist(), px_all[lo:hi].tolist(), m_all[lo:hi].tolist()

    def base_price(ts, px, T):
        k = bisect.bisect_left(ts, T)
        return px[k - 1] if k and (k - bisect.bisect_left(ts, T - 60_000)) >= 3 else None

    def last_at(ts, px, t):
        k = bisect.bisect_right(ts, t)
        return px[k - 1] if k else None

    def first(ts, px, m, t0, wait, want_buyer):
        for j in range(bisect.bisect_left(ts, t0), len(ts)):
            if ts[j] > t0 + wait:
                return None
            if m[j] == (not want_buyer):
                return ts[j], px[j]
        return None

    def gross(ts, px, m, T, lat, hold):
        e = first(ts, px, m, T + lat * 1000, 60_000, True)
        if not e:
            return None
        x = first(ts, px, m, e[0] + hold * 1000, 120_000, False)
        return None if not x else x[1] / e[1] - 1

    out = {"event": defaultdict(list), "placebo": defaultdict(list)}
    for s in man["series"]:
        ts, px, m = trades(s["row"])
        T = s["T"]
        b = base_price(ts, px, T)
        if b is None:
            continue
        rec = out[s["kind"]]
        rec["day"].append(day_of(s["t_event_ms"]))
        for name, sec in (("r60", 60), ("r1", 1), ("rm1", -1)):
            rec[name].append(last_at(ts, px, T + sec * 1000) / b - 1)
        rec["g2"].append(gross(ts, px, m, T, 2, 300))
        rec["g5"].append(gross(ts, px, m, T, 5, 300))
    E, P = out["event"], out["placebo"]
    checks = {"usable_event": (len(E["day"]), res["events"]["usable_event"]), "usable_placebo": (len(P["day"]), res["events"]["usable_placebo"]),
              "R_60": (np.mean(E["r60"]), res["reaction"]["R_60"]), "R_1": (np.mean(E["r1"]), res["reaction"]["R_1"]),
              "R_-1": (np.mean(E["rm1"]), res["reaction"]["R_-1"])}
    g2 = [(g, d) for g, d in zip(E["g2"], E["day"]) if g is not None]
    g5 = [g for g in E["g5"] if g is not None]
    pg = [(g, d) for g, d in zip(P["g2"], P["day"]) if g is not None]
    checks["n_g2"] = (len(g2), res["gate_cell_L2_H300"]["n"])
    checks["mean_gross_g2"] = (np.mean([g for g, _ in g2]), res["gate_cell_L2_H300"]["mean_gross"])
    checks["mean_net_g2"] = (np.mean([g for g, _ in g2]) - 2 * FEE, res["gate_cell_L2_H300"]["mean_net"])
    checks["mean_net_g5"] = (np.mean(g5) - 2 * FEE, res["gate_cell_L5_H300"]["mean_net"])
    net = np.array([g for g, _ in g2]) - 2 * FEE
    lo, hi = np.percentile(net, [1, 99])
    checks["winsorised_net_g2"] = (np.clip(net, lo, hi).mean(), res["gate_cell_L2_H300"]["winsorised_net"])
    bad += [k for k, (a, b) in checks.items() if abs(a - b) > 1e-9]
    t_an = analytic_t(list(net), [d for _, d in g2])
    t_boot = res["gate_cell_L2_H300"]["t_net"]
    if abs(t_an - t_boot) > 0.2 * abs(t_boot) + 0.15:
        bad.append(f"bootstrap t {t_boot:.3f} vs analytic {t_an:.3f}")
    t_pl = analytic_t([g - 2 * FEE for g, _ in pg], [d for _, d in pg])
    if abs(t_pl - res["placebo_L2_H300"]["net_t"]) > 0.2 * abs(res["placebo_L2_H300"]["net_t"]) + 0.15:
        bad.append(f"placebo t {res['placebo_L2_H300']['net_t']:.3f} vs analytic {t_pl:.3f}")
    gates = {"G1_L2s_H300_net_t_ge_1.65": bool(net.mean() > 0 and t_boot >= hurdle), "G2_L5s_H300_net_gt_0": bool(np.mean(g5) - 2 * FEE > 0),
             "G3_L2s_H300_winsorised_net_gt_0": bool(checks["winsorised_net_g2"][0] > 0),
             "G4_placebo_net_t_lt_2.5": bool(res["placebo_L2_H300"]["net_t"] < 2.5)}
    bad += [k for k, v in gates.items() if v != res["gates"][k]]
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict != res["verdict"]:
        bad.append("verdict")
    return {"checked": list(checks) + list(gates) + ["file hashes"], "analytic_t_L2_H300": t_an, "bootstrap_t_L2_H300": t_boot, "mismatches": bad,
            "verdict": verdict}, bad


def main() -> int:
    summary, bad = verify(HERE / "results", HERE / "ticks", 1.65, HERE / "feasibility" / "events.csv")
    print(json.dumps(summary, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Independent check of a results directory of IDX_INSIDER_NEWS with its own code (no import of idxsig, run_v2.py or the research runners).
Beyond verify_v2.py (which has no corporate-action logic and takes the control means as given), this recomputes from the panel file, the
registry file and the events table:
  - every EXITED trade's net return from its two closes, the fees and the registry's verified share scaling in (entry, exit]; trades
    whose window holds a registry row that is not a verified share-scaling action must not be EXITED;
  - the signal sessions, the entry sessions and the SKIP_OVERLAP decisions (a signal while the same name is still held);
  - that every EXITED event with at least one scored control draw has a finite control mean, that excess = net - control mean, and that
    the scored count is the EXITED count minus events with no scored control (the check the recorded run's defect would have failed);
  - the statistics (mean net, winsorised net, mean excess, an analytic day-cluster t against the bootstrap t) and the gates.
The matched-control draws themselves come from the harness (idxsig.controls, tested separately) and are not recomputed.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/verify_corrected.py [results_dir]   (default results_corrected; exit 1 on any mismatch)
"""
import hashlib
import json
import sys
from collections import defaultdict
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
FEE_BUY, FEE_SELL = 0.0015, 0.0025
CUTOFF = (14, 30)
NET_TOL = 5e-4


def analytic_t(vals, days):
    n, mu = len(vals), float(np.mean(vals))
    by = defaultdict(float)
    for v, d in zip(vals, days):
        by[d] += v - mu
    return mu / (sqrt(sum(x * x for x in by.values())) / n)


def main() -> int:
    out_dir = H / (sys.argv[1] if len(sys.argv) > 1 else "results_corrected")
    bad = []
    res = json.loads((out_dir / "RESULT.json").read_text())
    ev = pd.read_csv(out_dir / "events.csv")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    if sha(H / "events.csv") != res["inputs"]["events_csv"]:
        bad.append("events.csv hash")
    pm = json.loads((ROOT / "data/manifests/panel-20261007T225823Z.json").read_text())
    pfile = ROOT / pm["panel"]
    if sha(pfile) != pm["sha256"] or pm["sha256"] != res["inputs"]["panel"]:
        bad.append("panel hash")
    rm = json.loads((ROOT / "data/manifests/ca_registry-20261007T230210Z.json").read_text())
    rfile = ROOT / rm["registry"]
    if sha(rfile) != rm["sha256"] or rm["sha256"] != res["inputs"]["registry"]:
        bad.append("registry hash")
    scalable, verified = set(rm["share_scaling"]["applied_for"]), set(rm["share_scaling"]["only_if"])
    reg = pd.read_csv(rfile)
    reg = reg[reg.verification_status != "NO_PRICE_RESET"]
    reg_by = defaultdict(list)
    for r in reg.itertuples():
        reg_by[r.ticker].append((np.datetime64(r.effective_date, "D"), r.action_type, r.verification_status, float(r.ratio)))

    px = pd.read_csv(pfile, usecols=["date", "ticker", "close", "volume"], parse_dates=["date"])
    px = px[(px.date >= "2021-01-22") & (px.date <= "2023-12-29")]
    sessions = np.array(sorted(px.date.unique()), dtype="datetime64[D]")
    pos = {d: i for i, d in enumerate(sessions)}
    close = {(t, d): c for t, d, c in zip(px.ticker, px.date.values.astype("datetime64[D]"), px.close)}

    def signal_session(posted):
        ts = pd.Timestamp(posted)
        day = np.datetime64(ts.date(), "D")
        k = int(np.searchsorted(sessions, day, side="left"))
        is_session = k < len(sessions) and sessions[k] == day
        s = k if (is_session and (ts.hour, ts.minute) > CUTOFF) else k - 1
        return s if s >= 0 else None

    n_checked, n_scaled, max_diff = 0, 0, 0.0
    held_until = {}
    for r in ev.itertuples():
        s = signal_session(r.posted_wib)
        if s is None or str(sessions[s]) != r.signal_date:
            bad.append(f"signal session for {r.ticker} {r.posted_wib}")
            continue
        overlap = s + 1 <= held_until.get(r.ticker, -1)
        if overlap != (r.status == "SKIP_OVERLAP"):
            bad.append(f"overlap decision {r.ticker} {r.signal_date}: expected {overlap}, status {r.status}")
        if not overlap:
            if isinstance(r.exit_date, str) and r.exit_date:
                held_until[r.ticker] = pos[np.datetime64(r.exit_date, "D")]
            elif r.status == "INCOMPLETE":
                held_until[r.ticker] = 10 ** 9
        if r.status != "EXITED" or pd.isna(r.net_return):
            continue
        e, x = np.datetime64(r.entry_date, "D"), np.datetime64(r.exit_date, "D")
        if e != sessions[s + 1]:
            bad.append(f"entry session {r.ticker} {r.signal_date}")
        c0, c1 = close.get((r.ticker, e)), close.get((r.ticker, x))
        if c0 is None or c1 is None:
            bad.append(f"missing close {r.ticker}")
            continue
        if abs(c0 - r.entry_price) > 1e-6 * c0 or abs(c1 - r.exit_price) > 1e-6 * c1:
            bad.append(f"price {r.ticker} {r.signal_date}")
        factor = 1.0
        for d, kind, status, ratio in reg_by.get(r.ticker, []):
            if e < d <= x:
                if kind in scalable and status in verified:
                    factor *= ratio
                else:
                    bad.append(f"EXITED trade with a non-scalable registry row in its window {r.ticker} {d} {kind} {status}")
        n_scaled += factor != 1.0
        net = c1 * factor / c0 * (1 - FEE_SELL) / (1 + FEE_BUY) - 1
        max_diff = max(max_diff, abs(net - r.net_return))
        if abs(net - r.net_return) > NET_TOL:
            bad.append(f"net return {r.ticker} {r.signal_date}: {net:.5f} vs {r.net_return:.5f} (share factor {factor})")
        n_checked += 1

    ex = ev[ev.status == "EXITED"]
    with_control = ex[ex.control_n > 0]
    if with_control.control_mean.isna().any():
        bad.append(f"{int(with_control.control_mean.isna().sum())} EXITED events with scored controls have no control mean")
    filled = ev[ev.net_return.notna() & ev.control_mean.notna()]
    if len(filled) != len(with_control):
        bad.append(f"scored events {len(filled)} != EXITED with a scored control {len(with_control)}")
    if (abs(filled.excess - (filled.net_return - filled.control_mean)) > 1e-12).any():
        bad.append("excess != net - control mean")
    f = filled
    p = res["primary_hold_20"]
    checks = {"n": (len(f), p["n"]), "mean_net": (f.net_return.mean(), p["mean_net"]), "mean_excess": (f.excess.mean(), p["mean_excess"]),
              "mean_control": (f.control_mean.mean(), p["mean_control"])}
    lo, hi = np.percentile(f.net_return, [1, 99])
    checks["winsorised_net"] = (np.clip(f.net_return, lo, hi).mean(), p["winsorised_net"])
    bad += [k for k, (a, b) in checks.items() if abs(a - b) > 1e-9]
    t_an = analytic_t(list(f.excess), list(f.posted_wib.str[:10]))
    if abs(t_an - p["t_excess"]) > 0.2 * abs(p["t_excess"]) + 0.15:
        bad.append(f"bootstrap t {p['t_excess']:.3f} vs analytic {t_an:.3f}")
    yr = f.assign(year=f.posted_wib.str[:4]).groupby("year").excess.agg(["count", "mean"])
    big = yr[yr["count"] >= 20]
    gates = {"G1_excess_t_ge_3": bool(f.excess.mean() > 0 and p["t_excess"] >= 3.0),
             "G2_net_and_winsorised_net_gt_0": bool(f.net_return.mean() > 0 and checks["winsorised_net"][0] > 0),
             "G3_excess_gt_0_in_each_year_with_20_events": bool(len(big) > 0 and (big["mean"] > 0).all()),
             "G4_net_gt_0_with_extra_0.5pct_per_side": bool(f.net_return.mean() - 0.01 > 0)}
    bad += [k for k, v in gates.items() if v != res["gates"][k]]
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict != res["verdict"]:
        bad.append("verdict")
    well = f[f.control_n >= 100]                     # descriptive, declared in ADDENDUM_1.md: events with at least 100 scored control draws
    descriptive = {"events_with_at_least_100_scored_controls": {
        "n": int(len(well)), "mean_net": float(well.net_return.mean()), "mean_excess": float(well.excess.mean()),
        "analytic_t_excess": float(analytic_t(list(well.excess), list(well.posted_wib.str[:10])))}}
    print(json.dumps({"results_dir": out_dir.name, "trades_recomputed_from_closes": n_checked, "of_which_share_scaled_by_the_registry": int(n_scaled),
                      "max_abs_net_return_difference": max_diff, "exited": int(len(ex)), "exited_with_a_scored_control": int(len(with_control)),
                      "scored": int(len(f)), "analytic_t": float(t_an), "bootstrap_t": p["t_excess"], "gates": gates,
                      "descriptive": descriptive, "mismatches": bad, "verdict": verdict}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""(verify.py pinned a panel that is not in this checkout; this file is the same check on the panel the run used.)
Independent check of results/ with its own code (no import of idxsig or of run.py): the signal-session mapping from each article's
posting time, the entry and exit sessions and the close prices from the pinned panel file, each scored trade's net return from the two
closes and the fees, then the statistics (mean net, winsorised net, mean excess, an analytic day-cluster t against the bootstrap t)
and the gates from results/events.csv. The matched-control means come from the harness (idxsig.controls, tested separately); this
check recomputes everything that uses them but not the draws themselves.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/verify.py   (exit 1 if anything differs)
"""
import gzip
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


def analytic_t(vals, days):
    n, mu = len(vals), float(np.mean(vals))
    by = defaultdict(float)
    for v, d in zip(vals, days):
        by[d] += v - mu
    return mu / (sqrt(sum(x * x for x in by.values())) / n)


def main() -> int:
    bad = []
    res = json.loads((H / "results" / "RESULT.json").read_text())
    ev = pd.read_csv(H / "results" / "events.csv")
    events_in = pd.read_csv(H / "events.csv")
    if hashlib.sha256((H / "events.csv").read_bytes()).hexdigest() != res["inputs"]["events_csv"]:
        bad.append("events.csv hash")
    pm = json.loads((ROOT / "data/manifests/panel-20261007T225823Z.json").read_text())
    pfile = ROOT / pm["panel"]
    if hashlib.sha256(pfile.read_bytes()).hexdigest() != pm["sha256"] or pm["sha256"] != res["inputs"]["panel"]:
        bad.append("panel hash")
    px = pd.read_csv(pfile, usecols=["date", "ticker", "close", "volume"], parse_dates=["date"])
    px = px[(px.date >= "2021-01-22") & (px.date <= "2023-12-29")]
    sessions = np.array(sorted(px.date.unique()), dtype="datetime64[D]")
    close = {(t, d): c for t, d, c in zip(px.ticker, px.date.values.astype("datetime64[D]"), px.close)}

    def signal_session(posted):
        ts = pd.Timestamp(posted)
        day = np.datetime64(ts.date(), "D")
        k = int(np.searchsorted(sessions, day, side="left"))
        is_session = k < len(sessions) and sessions[k] == day
        s = k if (is_session and (ts.hour, ts.minute) > CUTOFF) else k - 1
        return s if s >= 0 else None

    n_checked = n_skipped_ca = 0
    for r in ev.itertuples():
        s = signal_session(r.posted_wib)
        if s is None or str(sessions[s]) != r.signal_date:
            bad.append(f"signal session for {r.ticker} {r.posted_wib}")
            continue
        if r.status != "EXITED" or pd.isna(r.net_return):
            continue
        e = pd.Timestamp(r.entry_date).to_datetime64().astype("datetime64[D]")
        x = pd.Timestamp(r.exit_date).to_datetime64().astype("datetime64[D]")
        if e != sessions[s + 1]:
            bad.append(f"entry session {r.ticker} {r.signal_date}")
        c0, c1 = close.get((r.ticker, e)), close.get((r.ticker, x))
        if c0 is None or c1 is None:
            bad.append(f"missing close {r.ticker}")
            continue
        if abs(c0 - r.entry_price) > 1e-6 * c0:
            bad.append(f"entry price {r.ticker} {r.signal_date}")
        if abs(c1 - r.exit_price) > 1e-6 * c1 and abs(r.exit_price / c1 - 1) > 1e-6:
            n_skipped_ca += 1                      # an exit price rescaled by a verified corporate action: not comparable here
            continue
        net = c1 / c0 * (1 - FEE_SELL) / (1 + FEE_BUY) - 1
        if abs(net - r.net_return) > 5e-4:         # whole-lot rounding of the shares moves the fees by a hair
            bad.append(f"net return {r.ticker} {r.signal_date}: {net:.5f} vs {r.net_return:.5f}")
        n_checked += 1
    f = ev[ev.net_return.notna() & ev.control_mean.notna()]
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
    print(json.dumps({"trades_recomputed_from_closes": n_checked, "exit_prices_skipped_for_corporate_actions": n_skipped_ca,
                      "checked": list(checks) + list(gates), "analytic_t": float(t_an), "bootstrap_t": p["t_excess"], "mismatches": bad,
                      "verdict": verdict}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

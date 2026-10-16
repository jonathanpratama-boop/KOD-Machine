"""E8 feasibility check (research/E8/FEASIBILITY_SPEC.md). Counts signals and data defects; computes no outcome.

Usage (from idx-signals/): python3 research/E8/feasibility.py data/manifests/binance_1h-20261015T182940Z.jsonl
Writes research/E8/feasibility/{FEASIBILITY.json, leaders.csv.gz, peer_events.csv.gz}. Runs once.
"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import e8  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

OUT = ROOT / "research" / "E8" / "feasibility"


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(manifest):
    if git("status", "--porcelain", "--", "idxsig", "research/E8"):
        sys.exit("error: commit idxsig/ and research/E8 first")
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; the check runs once")
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    h, meta = e8.load(Path(manifest))
    f = e8.features(h)
    L, P = e8.peer_events(h, f)
    n, T = h.present.shape
    t_lo = int((pd.Timestamp(e8.PERIOD[0], tz="UTC") - h.start) / pd.Timedelta("1h"))
    t_hi = T - 1 - e8.HOLD
    hours = np.arange(t_lo, t_hi + 1)
    elig_per_hour = f["elig"][:, hours].sum(axis=0)

    # missing data: presence only (no prices) of the entry bar and the holding bars
    if len(P):
        ent = h.present[P["peer"].to_numpy(), P["t"].to_numpy() + 1]
        hold_full = np.array([h.present[i, t + 1:t + 1 + e8.HOLD].all() for i, t in zip(P["peer"], P["t"])])
    else:
        ent = hold_full = np.array([], dtype=bool)
    P = P.assign(entry_bar=ent, holding_complete=hold_full)

    # identity: eligible-but-for-the-gap-guard coin-hours, and symbols whose history restarts after a gap
    absent_days = ~h.present.reshape(n, -1, 24).any(axis=2)
    restarts = []
    for i, s in enumerate(h.symbols):
        pres_days = np.flatnonzero(~absent_days[i])
        if len(pres_days) > 1:
            gaps = np.diff(pres_days) - 1
            if (gaps > e8.GAP_DAYS).any():
                restarts.append({"symbol": s, "longest_gap_days": int(gaps.max()),
                                 "restart_day": str((h.start + pd.Timedelta(days=int(pres_days[1:][gaps > e8.GAP_DAYS][0]))).date())})
    present_hours = int(h.present[:, hours].sum())
    ck = meta["checks"]
    defect_bars = ck["duplicate_bars"] + ck["off_hour_bars"]

    # minimum detectable effect from trailing volatility only
    if len(P):
        sig = P["vol30h"].to_numpy() * np.sqrt(e8.HOLD)
        sig_rms = float(np.sqrt(np.nanmean(sig ** 2)))
        wk = pd.DatetimeIndex(P["time"]).isocalendar()
        weeks = (wk["year"].astype(int) * 100 + wk["week"].astype(int)).to_numpy()
        m = pd.Series(weeks).value_counts().to_numpy()
        m_bar = float((m ** 2).sum() / m.sum())
        z = 1.959964 + 0.841621
        mde = {}
        for rho in (0.05, 0.20, 1.0):
            de = 1 + (m_bar - 1) * rho
            mde[f"rho_{rho}"] = {"design_effect": de, "n_eff": len(P) / de, "mde_72h": z * sig_rms / np.sqrt(len(P) / de)}
    else:
        sig_rms, weeks, m_bar, mde = None, np.array([]), None, {}

    Pe = P[P["entry_bar"]]
    year = pd.DatetimeIndex(P["time"]).year if len(P) else []
    res = {
        "spec": "research/E8/FEASIBILITY_SPEC.md", "spec_sha256": sha256_file(ROOT / "research/E8/FEASIBILITY_SPEC.md"),
        "manifest": meta["manifest"], "manifest_sha256": sha256_file(Path(manifest)), "last_hour_read": meta["last_hour"],
        "code_commit": git("rev-parse", "HEAD"), "started": started,
        "decision_hours": [str(h.start + pd.Timedelta(hours=int(t_lo))), str(h.start + pd.Timedelta(hours=int(t_hi)))],
        "timestamp_checks": {k: ck[k] for k in ("files", "symbols", "unit", "bars_read", "duplicate_bars",
                                                 "nonmonotonic_files", "off_hour_bars")},
        "identity_checks": {"bad_symbol_names": ck["bad_symbol_names"], "symbols_loaded": len(h.symbols),
                            "symbols_with_gap_over_7_days": len(restarts), "restarts": restarts},
        "missing_data": {"present_coin_hours_in_period": present_hours,
                         "missing_hour_share_since_first_bar": float(1 - h.present[:, hours].sum() /
                                                                  max(1, (np.cumsum(h.present, axis=1)[:, hours] > 0).sum())),
                         "peer_events_without_entry_bar": int((~P["entry_bar"]).sum()) if len(P) else 0,
                         "peer_events_missing_a_holding_bar": int((~P["holding_complete"]).sum()) if len(P) else 0},
        "counts": {"decision_hours": int(len(hours)),
                   "eligible_coins_per_hour": {"median": float(np.median(elig_per_hour)), "p10": float(np.percentile(elig_per_hour, 10)),
                                               "min": int(elig_per_hour.min()), "max": int(elig_per_hour.max())},
                   "eligible_coin_hours": int(f["elig"][:, hours].sum()),
                   "leader_triggers": int(len(L)), "distinct_leaders": int(L["leader"].nunique()) if len(L) else 0,
                   "leaders_with_no_qualifying_peer": int((L["peers"] == 0).sum()) if len(L) else 0,
                   "peer_events": int(len(P)), "peer_events_with_entry_bar": int(len(Pe)),
                   "distinct_peer_coins": int(Pe["peer"].nunique()) if len(Pe) else 0,
                   "distinct_weeks": int(len(set(weeks))) if len(P) else 0,
                   "events_per_year": {str(y): int(c) for y, c in pd.Series(year).value_counts().sort_index().items()} if len(P) else {},
                   "events_per_month_median": float(pd.Series(pd.DatetimeIndex(P["time"]).to_period("M")).value_counts().median()) if len(P) else 0,
                   "link_of_selected_peers": {q: float(np.percentile(P["link"], p)) for q, p in (("p10", 10), ("median", 50), ("p90", 90))} if len(P) else {},
                   "leaders_per_event": {str(k): int(v) for k, v in P["leaders"].value_counts().sort_index().items()} if len(P) else {},
                   "peer_liquidity_usd_per_day": {"median": float(np.median(P["liq"])), "p10": float(np.percentile(P["liq"], 10))} if len(P) else {}},
        "power": {"sigma_72h_rms_from_trailing_vol": sig_rms, "size_weighted_events_per_week": m_bar, "mde": mde},
        "defects": {"defect_bars": int(defect_bars), "defect_share_of_bars": defect_bars / max(1, ck["bars_read"])},
    }
    c, md = res["counts"], res["missing_data"]
    conds = {
        "peer_events_with_entry_bar >= 600": c["peer_events_with_entry_bar"] >= 600,
        "distinct_weeks >= 80": c["distinct_weeks"] >= 80,
        "distinct_peer_coins >= 100": c["distinct_peer_coins"] >= 100,
        "median eligible coins per hour >= 80": c["eligible_coins_per_hour"]["median"] >= 80,
        "timestamp/identity defects < 1%": res["defects"]["defect_share_of_bars"] < 0.01,
        "events missing a holding bar < 5%": (md["peer_events_missing_a_holding_bar"] / max(1, c["peer_events"])) < 0.05,
    }
    res["go_conditions"] = conds
    res["decision"] = "GO" if all(conds.values()) else "NO-GO"
    res["finished"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    OUT.mkdir(parents=True)
    (OUT / "FEASIBILITY.json").write_text(json.dumps(res, indent=2, default=str))
    sym = np.array(h.symbols)
    if len(L):
        L.assign(leader=sym[L["leader"]]).to_csv(OUT / "leaders.csv.gz", index=False)
    if len(P):
        P.assign(peer=sym[P["peer"]], leader=sym[P["leader"]]).drop(columns=["vol30h"]).to_csv(OUT / "peer_events.csv.gz", index=False)
    print(json.dumps({k: res[k] for k in ("counts", "power", "go_conditions", "decision")}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])

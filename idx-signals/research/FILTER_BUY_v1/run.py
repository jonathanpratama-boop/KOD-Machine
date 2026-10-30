"""FILTER_BUY_v1: does skipping the spikes KOD expects to dump make buying US +30% spikes any better?

Owner (2026-10-30, "Sure" to option 1): use KOD as a "don't buy" filter, not as a short.

    python3 run.py --freeze    # protocol.json, before any return is computed
    python3 run.py             # the one run: results/RESULT.json, results/trades.csv.gz, REPORT.md

Data: the as-traded replays of research/REPLAY_UNITS_v2 (v2.4's raw next-day-dump forecasts, made session by
session before their outcomes) on 2026-04..10 (A) and 2025-11..2026-03 (B), and the same price pull. No forecast
or feature is changed or re-chosen here.

The buy: at the open of the session after the spike, long equal weight, sold at that session's close (H1) or at the
close of the 5th session (H5, descriptive). A name with no usable bar is skipped and counted. Costs: round-trip
trading cost only (a long has no borrow): CHEAP 0.2%, TYPICAL 0.6%, BRUTAL 1.5%.

The filter: flagged = the third of that period's spikes with the highest raw v2.4 dump probability (a ranking, no
outcome); kept = the other two thirds. Primary statement, per period, at TYPICAL cost on H1:
mean(kept) - mean(all). The filter IMPROVES buying in a period when that difference is above zero with a one-sided
95% lower bound (session bootstrap, 2000 resamples, seed 20261031) above zero; the verdict needs both periods.
Reported beside it, never as a pass: whether buying the kept spikes is profitable on its own.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "REPLAY_UNITS_v2"))
from idxsig.provenance import MANIFESTS, sha256_file, utc_stamp  # noqa: E402

PROTO = HERE / "protocol.json"
RESULTS = HERE / "results"
MANIFEST = "yahoo_us_replay-20261030T071025Z.jsonl"
PERIODS = {
    "A": {"label": "2026-04-01..2026-10-28", "forecasts": "research/REPLAY_UNITS_v2/results_A/forecasts.csv.gz"},
    "B": {"label": "2025-11-03..2026-03-31", "forecasts": "research/REPLAY_UNITS_v2/results_B/forecasts.csv.gz"},
}
COSTS = {"CHEAP": 0.002, "TYPICAL": 0.006, "BRUTAL": 0.015}
FLAGGED_SHARE = 1 / 3
SEED, B = 20261031, 2000


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    PROTO.write_text(
        json.dumps(
            {
                "study_id": "FILTER_BUY_v1",
                "frozen_at": utc_stamp(),
                "question": "does skipping the spikes KOD v2.4 expects to dump next day improve buying US +30% spikes?",
                "periods": PERIODS,
                "buy": "long at the open of s+1; H1 sold at that close, H5 (descriptive) at the close of s+5",
                "costs": COSTS,
                "filter": f"flagged = top {FLAGGED_SHARE:.0%} of the period's spikes by raw v2.4 dump probability; kept = the rest",
                "primary": "per period, TYPICAL cost, H1: mean(kept) - mean(all) > 0 with one-sided 95% session-bootstrap "
                "lower bound > 0; verdict needs both periods",
                "bootstrap": {"unit": "signal session", "resamples": B, "seed": SEED},
                "beside_it": ["mean of flagged, kept and all at every cost", "H5", "certified calls as the flag",
                              "whether buying the kept spikes is profitable (never a pass criterion)"],
                "limits": ["both periods' forecasts were already read once for AUC (REPLAY_UNITS_v2), not for returns",
                           "survivorship: names delisted since are absent, which flatters buying",
                           "open and close prints, not fills; small caps may not fill at the open"],
                "inputs": {p["forecasts"]: sha256_file(ROOT / p["forecasts"]) for p in PERIODS.values()}
                | {f"data/manifests/{MANIFEST}": sha256_file(MANIFESTS / MANIFEST)},
                "code": {"research/FILTER_BUY_v1/run.py": sha256_file(Path(__file__))},
            },
            indent=1,
        )
        + "\n"
    )
    print(PROTO.read_text())
    return 0


def lower_bound(df: pd.DataFrame, a: str, b: str) -> dict:
    """mean(a) - mean(b) over trades, session bootstrap; a and b are boolean selectors on columns 'net' and 'in_*'."""
    sessions = df["session"].to_numpy()
    groups = [np.flatnonzero(sessions == s) for s in np.unique(sessions)]
    net, sel_a, sel_b = df["net"].to_numpy(), df[a].to_numpy(bool), df[b].to_numpy(bool)
    rng = np.random.default_rng(SEED)
    d = []
    for _ in range(B):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if sel_a[idx].any() and sel_b[idx].any():
            d.append(net[idx][sel_a[idx]].mean() - net[idx][sel_b[idx]].mean())
    diff = net[sel_a].mean() - net[sel_b].mean()
    return {"diff": float(diff), "lower_95": float(np.quantile(d, 0.05)), "p_one_sided": float((np.sum(np.array(d) <= 0) + 1) / (len(d) + 1))}


def main() -> int:
    if "--freeze" in sys.argv:
        return freeze()
    if (RESULTS / "RESULT.json").exists():
        sys.exit("error: results exist; this study runs once")
    proto = json.loads(PROTO.read_text())
    for path, want in {**proto["inputs"], **proto["code"]}.items():
        if sha256_file(ROOT / path) != want:
            raise RuntimeError(f"{path} changed since the freeze")
    import build  # REPLAY_UNITS_v2's market loader (the same causal frame)

    m, *_ = build.market(MANIFESTS / MANIFEST)
    tick = {t: i for i, t in enumerate(m.tickers.astype(str))}
    dates = {s: i for i, s in enumerate(m.dates.astype(str))}
    res, frames = {"study": "FILTER_BUY_v1", "ran_at": utc_stamp(), "periods": {}}, []
    for key, p in PERIODS.items():
        f = pd.read_csv(ROOT / p["forecasts"], dtype={"ticker": str, "session": str})
        cut = f["NEXT_DUMP10_1_raw"].quantile(1 - FLAGGED_SHARE)
        rows, skipped = [], 0
        for r in f.itertuples(index=False):
            n, d = tick.get(r.ticker), dates.get(r.session)
            if n is None or d is None or d + 1 >= m.shape[1] or not m.present[n, d + 1]:
                skipped += 1
                continue
            o = float(m.open[n, d + 1])
            c1 = float(m.close[n, d + 1])
            k = d + 5
            c5 = float(m.close[n, k]) if k < m.shape[1] and m.present[n, k] else np.nan
            if not (np.isfinite(o) and o > 0 and np.isfinite(c1) and c1 > 0):
                skipped += 1
                continue
            rows.append({"period": key, "ticker": r.ticker, "session": r.session, "raw": r.NEXT_DUMP10_1_raw,
                         "g1": c1 / o - 1, "g5": c5 / o - 1 if np.isfinite(c5) and c5 > 0 else np.nan,
                         "cert_call": bool(r.cert_call), "flagged": bool(r.NEXT_DUMP10_1_raw >= cut)})
        t = pd.DataFrame(rows)
        t["in_all"], t["in_kept"], t["in_flagged"] = True, ~t["flagged"], t["flagged"]
        frames.append(t)
        out = {"label": p["label"], "spikes": int(len(f)), "traded": int(len(t)), "skipped": skipped,
               "flag_cutoff": float(cut), "flagged": int(t["flagged"].sum())}
        for h in ("g1", "g5"):
            th = t[t[h].notna()].copy()
            for sc, cost in COSTS.items():
                th["net"] = th[h] - cost
                out[f"{h}_{sc}"] = {
                    "all": float(th["net"].mean()), "kept": float(th.loc[th.in_kept, "net"].mean()),
                    "flagged": float(th.loc[th.in_flagged, "net"].mean()),
                    "certified": float(th.loc[th.cert_call, "net"].mean()) if th.cert_call.any() else None,
                    "kept_win_rate": float((th.loc[th.in_kept, "net"] > 0).mean()),
                    "filter_gain": lower_bound(th, "in_kept", "in_all"),
                    "kept_vs_flagged": lower_bound(th, "in_kept", "in_flagged"),
                }
        res["periods"][key] = out
    typ = [res["periods"][k]["g1_TYPICAL"]["filter_gain"] for k in PERIODS]
    res["verdict"] = ("FILTER IMPROVES buying in both periods" if all(g["diff"] > 0 and g["lower_95"] > 0 for g in typ)
                      else "FILTER NOT SHOWN: the gain does not clear the bar in both periods")
    RESULTS.mkdir(exist_ok=True)
    pd.concat(frames).to_csv(RESULTS / "trades.csv.gz", index=False)
    (RESULTS / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

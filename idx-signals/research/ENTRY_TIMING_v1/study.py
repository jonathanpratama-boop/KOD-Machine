"""ENTRY_TIMING_v1: when to buy a US +30% spike, and which ones to skip, using KOD v2.4's dump forecast.

Owner (2026-10-30): "what about 5 day buy? Don't buy makes sense too. We should deepen that. But when to buy?"

    python3 study.py explore     # EXPLORATORY: 120 rules on period A (2026-04..10); picks one rule, writes protocol.json
    python3 study.py confirm     # once: the one frozen rule on period B (2025-11..2026-03)

A rule = entry delay x hold x group. Entry at the open of the d-th session after the spike (d = 1..6), exit at the
close of the h-th session counted from entry (h = 1, 3, 5, 10, 20). Groups by v2.4's raw next-day dump probability,
ranked within the period (no outcome): ALL; KEPT (bottom two thirds); SAFEST (bottom third); FLAGGED (top third).
Cost: TYPICAL round trip 0.6% (a long has no borrow). A trade whose entry or exit bar is missing is skipped and counted.

Selection on A, fixed now: among rules with at least 200 trades, the highest one-sided 95% lower bound of the mean
net return (session bootstrap, 2000 resamples, seed 20261031); ties by mean. The confirmation on B passes when the
frozen rule's mean net return is above zero with a lower bound above zero. B's immediate-entry 5-day groups were
already seen in FILTER_BUY_v1; every other rule on B is unseen.
"""

from __future__ import annotations

import itertools
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

MANIFEST = "yahoo_us_replay-20261030T071025Z.jsonl"
FORECASTS = {"A": "research/REPLAY_UNITS_v2/results_A/forecasts.csv.gz",
             "B": "research/REPLAY_UNITS_v2/results_B/forecasts.csv.gz"}
DELAYS, HOLDS = (1, 2, 3, 4, 5, 6), (1, 3, 5, 10, 20)
GROUPS = ("ALL", "KEPT", "SAFEST", "FLAGGED")
COST, MIN_TRADES, SEED, B = 0.006, 200, 20261031, 2000
PROTO, RESULTS = HERE / "protocol.json", HERE / "results"


def trades(key: str, m, tick, dates) -> pd.DataFrame:
    f = pd.read_csv(ROOT / FORECASTS[key], dtype={"ticker": str, "session": str})
    lo, hi = f["NEXT_DUMP10_1_raw"].quantile([1 / 3, 2 / 3])
    rows = []
    for r in f.itertuples(index=False):
        n, d0 = tick.get(r.ticker), dates.get(r.session)
        if n is None or d0 is None:
            continue
        g = "SAFEST" if r.NEXT_DUMP10_1_raw <= lo else ("FLAGGED" if r.NEXT_DUMP10_1_raw >= hi else "MIDDLE")
        for d, h in itertools.product(DELAYS, HOLDS):
            e, x = d0 + d, d0 + d + h - 1
            if x >= m.shape[1] or not (m.present[n, e] and m.present[n, x]):
                continue
            o, c = float(m.open[n, e]), float(m.close[n, x])
            if not (np.isfinite(o) and o > 0 and np.isfinite(c) and c > 0):
                continue
            rows.append({"ticker": r.ticker, "session": r.session, "group": g, "delay": d, "hold": h, "net": c / o - 1 - COST})
    return pd.DataFrame(rows)


def select(t: pd.DataFrame, group: str) -> pd.DataFrame:
    return {"ALL": t, "KEPT": t[t.group != "FLAGGED"], "SAFEST": t[t.group == "SAFEST"], "FLAGGED": t[t.group == "FLAGGED"]}[group]


def stats(x: pd.DataFrame) -> dict:
    sessions = x["session"].to_numpy()
    groups = [np.flatnonzero(sessions == s) for s in np.unique(sessions)]
    v = x["net"].to_numpy()
    rng = np.random.default_rng(SEED)
    draws = [v[np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])].mean() for _ in range(B)]
    return {"trades": int(len(v)), "mean": float(v.mean()), "median": float(np.median(v)),
            "win_rate": float((v > 0).mean()), "lower_95": float(np.quantile(draws, 0.05))}


def market():
    import build

    m, *_ = build.market(MANIFESTS / MANIFEST)
    return m, {t: i for i, t in enumerate(m.tickers.astype(str))}, {s: i for i, s in enumerate(m.dates.astype(str))}


def explore() -> int:
    if PROTO.exists():
        sys.exit("error: the exploration ran and froze its choice already")
    m, tick, dates = market()
    t = trades("A", m, tick, dates)
    rows = []
    for d, h, g in itertools.product(DELAYS, HOLDS, GROUPS):
        x = select(t[(t.delay == d) & (t.hold == h)], g)
        if len(x):
            rows.append({"delay": d, "hold": h, "group": g, **stats(x)})
    table = pd.DataFrame(rows).sort_values(["lower_95", "mean"], ascending=False)
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "explore_A.csv", index=False)
    eligible = table[table.trades >= MIN_TRADES]
    best = eligible.iloc[0].to_dict()
    PROTO.write_text(json.dumps({
        "study_id": "ENTRY_TIMING_v1", "frozen_at": utc_stamp(),
        "exploration": {"period": "A 2026-04-01..2026-10-28", "rules_tried": int(len(table)),
                        "selection": f"highest one-sided 95% lower bound among rules with >= {MIN_TRADES} trades",
                        "table": "results/explore_A.csv", "table_sha256": sha256_file(RESULTS / "explore_A.csv")},
        "frozen_rule": {"delay": int(best["delay"]), "hold": int(best["hold"]), "group": best["group"],
                        "on_A": {k: best[k] for k in ("trades", "mean", "median", "win_rate", "lower_95")}},
        "confirmation": {"period": "B 2025-11-03..2026-03-31", "pass": "mean net > 0 and one-sided 95% lower bound > 0",
                         "cost": COST, "bootstrap": {"unit": "signal session", "resamples": B, "seed": SEED}},
        "honesty": ["the A figure is the best of many rules on one period: optimistic by construction",
                    "B's immediate-entry 5-day groups were seen in FILTER_BUY_v1; other rules on B are unseen",
                    "survivorship flatters buying; open prints are not fills; paper only"],
        "inputs": {**{v: sha256_file(ROOT / v) for v in FORECASTS.values()},
                   f"data/manifests/{MANIFEST}": sha256_file(MANIFESTS / MANIFEST)},
        "code": {"research/ENTRY_TIMING_v1/study.py": sha256_file(Path(__file__))},
    }, indent=1) + "\n")
    print(table.head(15).to_string(index=False))
    print("\nFROZEN:", json.loads(PROTO.read_text())["frozen_rule"])
    return 0


def confirm() -> int:
    proto = json.loads(PROTO.read_text())
    out = RESULTS / "CONFIRM_B.json"
    if out.exists():
        sys.exit("error: the confirmation runs once")
    for path, want in {**proto["inputs"], **proto["code"]}.items():
        if sha256_file(ROOT / path) != want:
            raise RuntimeError(f"{path} changed since the freeze")
    rule = proto["frozen_rule"]
    m, tick, dates = market()
    t = trades("B", m, tick, dates)
    x = select(t[(t.delay == rule["delay"]) & (t.hold == rule["hold"])], rule["group"])
    s = stats(x)
    same_rule_all = stats(select(t[(t.delay == rule["delay"]) & (t.hold == rule["hold"])], "ALL"))
    res = {"rule": rule, "ran_at": utc_stamp(), "on_B": s, "same_timing_all_spikes_on_B": same_rule_all,
           "verdict": "CONFIRMED on B" if s["mean"] > 0 and s["lower_95"] > 0 else "NOT CONFIRMED on B"}
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(explore() if sys.argv[1:] == ["explore"] else confirm() if sys.argv[1:] == ["confirm"] else 2)

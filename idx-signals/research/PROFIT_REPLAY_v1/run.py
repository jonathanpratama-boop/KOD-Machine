"""PROFIT_REPLAY_v1: would KOD's certified next-day dump calls have made money as paper shorts, after costs?

Stage 1 of the profit test (owner's go-ahead 2026-10-30). Reads RECENT_REPLAY_v1's forecasts (made before their
outcomes, session by session) and the same price pull. Nothing about the forecasts is changed or chosen here.

    python3 run.py --freeze      # writes protocol.json (the rules) before any return is computed
    python3 run.py               # the one run: results/RESULT.json and REPORT.md

The trade, fixed in protocol.json: for every certified DUMP call (call_cert, as replayed), short at the open of the
next session (the forecast is made after the signal close, so the next open is the first possible entry) and cover
at that session's close (primary, H1); the same entry covered at the close of the 5th session is descriptive (H5).
Costs are charged as a fraction of the entry notional under three pre-declared scenarios. The bar: under the TYPICAL
scenario the mean net H1 return per trade is positive and its one-sided 95% lower bound (bootstrap over signal
sessions, 2000 resamples, seed 20261030) is above zero.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "RECENT_REPLAY_v1"))
from idxsig.provenance import MANIFESTS, sha256_file, utc_stamp  # noqa: E402

HERE = Path(__file__).resolve().parent
PROTO_PATH = HERE / "protocol.json"
FORECASTS = "research/RECENT_REPLAY_v1/results/forecasts.csv.gz"
REPLAY_PROTO = "research/RECENT_REPLAY_v1/protocol.json"
SCENARIOS = {  # round-trip trading cost (commission + spread + slippage) and borrow/locate per day held
    "CHEAP": {"trading": 0.0020, "borrow_per_day": 0.0010},
    "TYPICAL": {"trading": 0.0060, "borrow_per_day": 0.0050},
    "BRUTAL": {"trading": 0.0150, "borrow_per_day": 0.0200},
}
SEED, B = 20261030, 2000


def freeze() -> int:
    if PROTO_PATH.exists():
        sys.exit("error: protocol.json exists; the rules are frozen once")
    rp = json.loads((ROOT / REPLAY_PROTO).read_text())
    proto = {
        "study_id": "PROFIT_REPLAY_v1", "frozen_at": utc_stamp(),
        "question": "would RECENT_REPLAY_v1's certified next-day dump calls have made money as paper shorts after costs?",
        "selection": "every row of the replay forecasts with cert_call true (182, chosen by call_cert before any outcome)",
        "reference": "every replay spike shorted the same way (what shorting all spikes would have done), descriptive",
        "trade": {"entry": "short at the open of session s+1", "H1": "cover at the close of s+1 (primary)",
                  "H5": "cover at the close of s+5 (descriptive)",
                  "gross_return": "(entry - exit) / entry; a missing or non-positive open or exit bar skips the trade (counted)",
                  "days_held": {"H1": 1, "H5": 5}},
        "costs": SCENARIOS, "costs_note": "borrow/locate charged for at least one day even on an intraday H1 round trip",
        "bar": "TYPICAL: mean net H1 return per trade > 0 and its one-sided 95% lower bound (session bootstrap) > 0",
        "bootstrap": {"unit": "signal session", "resamples": B, "seed": SEED},
        "known_limits": ["no historical borrow availability: some names were not shortable; a pass is conditional on locating",
                         "open and close prints, not fills; no halt or squeeze path inside the day",
                         "the replay range was read once already (RECENT_REPLAY_v1): this is a go/no-go, not proof",
                         "survivorship: names delisted since are absent"],
        "inputs": {FORECASTS: sha256_file(ROOT / FORECASTS), REPLAY_PROTO: sha256_file(ROOT / REPLAY_PROTO),
                   f"data/manifests/{rp['manifest']}": sha256_file(MANIFESTS / rp["manifest"])},
        "code": {"research/PROFIT_REPLAY_v1/run.py": sha256_file(Path(__file__))},
        "manifest": rp["manifest"],
    }
    PROTO_PATH.write_text(json.dumps(proto, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "selection", "bar")}, indent=1))
    return 0


def boot_lb(df: pd.DataFrame, col: str) -> tuple[float, float]:
    """(mean, one-sided 95% lower bound) of the per-trade mean, resampling signal sessions."""
    sess = df["session"].to_numpy()
    uniq = np.unique(sess)
    groups = [np.flatnonzero(sess == s) for s in uniq]
    v = df[col].to_numpy()
    rng = np.random.default_rng(SEED)
    draws = np.empty(B)
    for b in range(B):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        draws[b] = v[idx].mean()
    return float(v.mean()), float(np.quantile(draws, 0.05))


def main() -> int:
    if "--freeze" in sys.argv:
        return freeze()
    if (HERE / "results" / "RESULT.json").exists():
        sys.exit("error: results exist; this study runs once")
    proto = json.loads(PROTO_PATH.read_text())
    for path, want in {**proto["inputs"], **proto["code"]}.items():
        if sha256_file(ROOT / path) != want:
            raise RuntimeError(f"{path} changed since the freeze")
    import build  # RECENT_REPLAY_v1's market loader (same causal frame)
    m, *_ = build.market(MANIFESTS / proto["manifest"])
    tick = {t: i for i, t in enumerate(m.tickers.astype(str))}
    dates = {s: i for i, s in enumerate(m.dates.astype(str))}
    f = pd.read_csv(ROOT / FORECASTS, dtype={"ticker": str, "session": str})
    rows, skipped = [], 0
    for r in f.itertuples(index=False):
        n, d = tick.get(r.ticker), dates.get(r.session)
        out = {"ticker": r.ticker, "session": r.session, "cert_call": bool(r.cert_call), "raw": r.NEXT_DUMP10_1_raw}
        if n is None or d is None or d + 1 >= m.shape[1] or not m.present[n, d + 1]:
            skipped += 1
            continue
        o = float(m.open[n, d + 1])
        if not np.isfinite(o) or o <= 0:
            skipped += 1
            continue
        out["entry"] = o
        c1 = float(m.close[n, d + 1])
        out["g1"] = (o - c1) / o if np.isfinite(c1) and c1 > 0 else np.nan
        k = d + 5
        c5 = float(m.close[n, k]) if k < m.shape[1] and m.present[n, k] else np.nan
        out["g5"] = (o - c5) / o if np.isfinite(c5) and c5 > 0 else np.nan
        out["gap"] = o / float(m.close[n, d]) - 1
        rows.append(out)
    t = pd.DataFrame(rows)
    res = {"study": "PROFIT_REPLAY_v1", "ran_at": utc_stamp(), "skipped_no_entry": skipped, "groups": {}}
    for name, g in (("CERTIFIED_CALLS", t[t.cert_call]), ("ALL_SPIKES", t)):
        gr = {"trades": int(len(g)), "mean_gap_at_entry": float(g["gap"].mean())}
        for h, days in (("H1", 1), ("H5", 5)):
            gh = g[g[f"g{h[1]}"].notna()].copy()
            gr[h] = {"trades": int(len(gh)), "gross_mean": float(gh[f"g{h[1]}"].mean()),
                     "gross_median": float(gh[f"g{h[1]}"].median()),
                     "win_rate_gross": float((gh[f"g{h[1]}"] > 0).mean()),
                     "worst_trade": float(gh[f"g{h[1]}"].min()), "best_trade": float(gh[f"g{h[1]}"].max())}
            for sc, cost in SCENARIOS.items():
                gh["net"] = gh[f"g{h[1]}"] - cost["trading"] - cost["borrow_per_day"] * days
                mean, lb = boot_lb(gh, "net")
                daily = gh.groupby("session")["net"].mean()
                eq = (1 + daily).cumprod()
                gr[h][sc] = {"net_mean": mean, "net_lower_95": lb, "win_rate": float((gh["net"] > 0).mean()),
                             "per_1000_per_trade": 1000 * mean,
                             "equal_weight_daily_total": float(eq.iloc[-1] - 1) if len(eq) else None,
                             "max_drawdown": float((eq / eq.cummax() - 1).min()) if len(eq) else None}
        res["groups"][name] = gr
        if name == "CERTIFIED_CALLS":
            gm = g[g["g1"].notna()].copy()
            gm["net"] = gm["g1"] - SCENARIOS["TYPICAL"]["trading"] - SCENARIOS["TYPICAL"]["borrow_per_day"]
            res["by_month_typical_H1"] = {k: {"trades": int(len(v)), "net_mean": float(v["net"].mean())}
                                          for k, v in gm.groupby(gm["session"].str[:7])}
    typ = res["groups"]["CERTIFIED_CALLS"]["H1"]["TYPICAL"]
    res["verdict"] = ("PASSES the go/no-go: profitable after typical costs" if typ["net_mean"] > 0 and typ["net_lower_95"] > 0
                      else "FAILS the go/no-go: not reliably profitable after typical costs")
    (HERE / "results").mkdir(exist_ok=True)
    t.to_csv(HERE / "results" / "trades.csv.gz", index=False)
    (HERE / "results" / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

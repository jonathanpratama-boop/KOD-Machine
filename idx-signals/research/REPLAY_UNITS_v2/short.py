"""REPLAY_UNITS_v2 short (copy of FRESH_SHORT_v1/short.py, rules unchanged in short_rules.json): the redesigned paper
short on the as-traded replay of 2025-11-03..2026-03-31 (results_B). FRESH_SHORT_v1 docstring follows.


Design 1 of PROFIT_REPLAY_v1's report, fixed here before the period's replay or any return is computed:
for every certified next-day dump call (call_cert, replayed by replay.py session by session), short at the open of
s+1; stop: if a later session's high reaches 1.30 x entry, cover at the stop (or at that session's open when it
opened above the stop); otherwise cover at the close of s+5. Costs per scenario, charged on the entry notional,
borrow per day held. Bar: TYPICAL mean net return per trade > 0 and its one-sided 95% lower bound (bootstrap over
signal sessions, 2000 resamples, seed 20261031) > 0. Beside it: a book that puts 2% of capital in each position.

    python3 short.py --freeze   # the rules, before anything else in this study runs
    python3 short.py            # the one run, after replay.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from idxsig.provenance import MANIFESTS, sha256_file, utc_stamp  # noqa: E402

RULES = HERE / "short_rules.json"
RES = HERE / "results_B"
MANIFEST = "yahoo_us_replay-20261030T071025Z.jsonl"
STOP, HOLD, POSITION = 1.30, 5, 0.02
SCENARIOS = {"CHEAP": {"trading": 0.0020, "borrow_per_day": 0.0010},
             "TYPICAL": {"trading": 0.0060, "borrow_per_day": 0.0050},
             "BRUTAL": {"trading": 0.0150, "borrow_per_day": 0.0200}}
SEED, B = 20261031, 2000


def freeze() -> int:
    if RULES.exists():
        sys.exit("error: short_rules.json exists")
    RULES.write_text(json.dumps({
        "study_id": "FRESH_SHORT_v1", "frozen_at": utc_stamp(),
        "period": ["2025-11-03", "2026-03-31"],
        "why_this_period": "inside the 400-day pull, before RECENT_REPLAY_v1's range; no KOD study has read its outcomes",
        "selection": "certified next-day dump calls of this period's replay (call_cert bar from 2022-2023 + this "
                     "replay's own earlier outcomes)",
        "trade": {"entry": "short at the open of s+1", "stop": f"cover at {STOP} x entry when a session's high reaches it "
                  "(at that session's open if it opened above)", "exit": f"else cover at the close of s+{HOLD}",
                  "position": f"{POSITION:.0%} of capital per trade in the book view"},
        "costs": SCENARIOS, "bar": "TYPICAL mean net per trade > 0 and one-sided 95% session-bootstrap lower bound > 0",
        "bootstrap": {"resamples": B, "seed": SEED}, "manifest": MANIFEST,
        "limits": ["no historical borrow availability", "daily bars: the stop is assumed filled at its price",
                   "survivorship: names delisted since are absent", "paper only"],
        "code": {"research/FRESH_SHORT_v1/short.py": sha256_file(Path(__file__))}}, indent=1) + "\n")
    print(RULES.read_text())
    return 0


def trade(m, n: int, d: int) -> dict | None:
    if d + 1 >= m.shape[1] or not m.present[n, d + 1]:
        return None
    e = float(m.open[n, d + 1])
    if not np.isfinite(e) or e <= 0:
        return None
    stop = e * STOP
    last = d + HOLD
    if last >= m.shape[1]:
        return None
    for k in range(d + 1, last + 1):
        if not m.present[n, k]:
            continue
        o, h = float(m.open[n, k]), float(m.high[n, k])
        if k > d + 1 and np.isfinite(o) and o >= stop:
            return {"entry": e, "exit": o, "days": k - d, "how": "stopped at the open"}
        if np.isfinite(h) and h >= stop:
            return {"entry": e, "exit": stop, "days": k - d, "how": "stopped"}
    c = float(m.close[n, last]) if m.present[n, last] else np.nan
    if not np.isfinite(c) or c <= 0:
        return None
    return {"entry": e, "exit": c, "days": HOLD, "how": "held"}


def lb(df: pd.DataFrame, col: str) -> float:
    groups = [np.flatnonzero(df["session"].to_numpy() == s) for s in df["session"].unique()]
    v, rng = df[col].to_numpy(), np.random.default_rng(SEED)
    return float(np.quantile([v[np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])].mean()
                              for _ in range(B)], 0.05))


def main() -> int:
    if "--freeze" in sys.argv:
        return freeze()
    rules = json.loads(RULES.read_text())
    proto = json.loads((HERE / "protocol_B.json").read_text())
    if sha256_file(Path(__file__)) != proto["code_pins"]["research/REPLAY_UNITS_v2/short.py"]:
        raise RuntimeError("short.py changed since the freeze")
    out_path = RES / "SHORT_RESULT.json"
    if out_path.exists():
        sys.exit("error: the short test runs once")
    import build
    m, *_ = build.market(MANIFESTS / MANIFEST)
    tick = {t: i for i, t in enumerate(m.tickers.astype(str))}
    dates = {s: i for i, s in enumerate(m.dates.astype(str))}
    f = pd.read_csv(RES / "forecasts.csv.gz", dtype={"ticker": str, "session": str})
    rows = []
    for r in f.itertuples(index=False):
        t = trade(m, tick[r.ticker], dates[r.session])
        if t is not None:
            rows.append({"ticker": r.ticker, "session": r.session, "cert_call": bool(r.cert_call), **t,
                         "gross": (t["entry"] - t["exit"]) / t["entry"]})
    tr = pd.DataFrame(rows)
    res = {"study": "REPLAY_UNITS_v2 short (FRESH_SHORT_v1 rules)", "ran_at": utc_stamp(), "groups": {}}
    for name, g in (("CERTIFIED_CALLS", tr[tr.cert_call].copy()), ("ALL_SPIKES", tr.copy())):
        gr = {"trades": int(len(g)), "gross_mean": float(g.gross.mean()), "gross_median": float(g.gross.median()),
              "stopped_share": float(g.how.str.startswith("stopped").mean()), "worst": float(g.gross.min()),
              "best": float(g.gross.max()), "win_rate_gross": float((g.gross > 0).mean())}
        for sc, c in SCENARIOS.items():
            g["net"] = g.gross - c["trading"] - c["borrow_per_day"] * g.days
            daily = g.groupby("session")["net"].sum() * POSITION
            book = (1 + daily).cumprod()
            gr[sc] = {"net_mean": float(g.net.mean()), "net_lower_95": lb(g, "net"), "win_rate": float((g.net > 0).mean()),
                      "book_total_2pct_per_trade": float(book.iloc[-1] - 1),
                      "book_max_drawdown": float((book / book.cummax() - 1).min())}
        res["groups"][name] = gr
    c = res["groups"]["CERTIFIED_CALLS"]["TYPICAL"]
    res["verdict"] = ("PASSES: profitable after typical costs on unseen data" if c["net_mean"] > 0 and c["net_lower_95"] > 0
                      else "FAILS: not reliably profitable after typical costs on unseen data")
    tr.to_csv(RES / "short_trades.csv.gz", index=False)
    out_path.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

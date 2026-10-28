"""MOVERS_NOW_v1 recorded check (PROTOCOL.md). Usage (from idx-signals/): python3 research/MOVERS_NOW_v1/check.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "US_INSIDER_BUY"))
import harness_idx as hx  # noqa: E402
import ib_stats as st  # noqa: E402
from idxsig import sensors  # noqa: E402

HEADLINES = sys.argv[1] if len(sys.argv) > 1 else None   # en_ticker_headlines.csv.gz built from EmitenNews sitemaps 2024-2026


def news_flag(rows: pd.DataFrame, h: pd.DataFrame) -> pd.Series:
    s = h[h.slug.map(lambda x: bool(sensors.dilution_kinds(x)))][["ticker", "date"]].drop_duplicates()
    keys = set()
    for k in range(1, 8):
        keys |= set(zip(s.ticker, s.date + pd.Timedelta(days=k)))
    return pd.Series([x in keys for x in zip(rows.ticker, rows.date)], index=rows.index)


def stats(res: pd.DataFrame) -> dict:
    f = res[res.net_return.notna() & res.excess_b.notna()]
    out = hx.summary(res)
    if len(f) >= 5:
        w = st.week_id(f.signal_date)
        out["excess_vs_any_B_boot"] = st.Boot(w, 10_000, 20261203).mean(f.excess_b, w)
        out["by_month"] = {m: {"n": int(len(g)), "net_mean": float(g.net_return.mean()), "excess_b_mean": float(g.excess_b.mean())}
                           for m, g in f.groupby(f.signal_date.str[:7])}
    return out


def main() -> int:
    out = HERE / "CHECK_RESULT.json"
    if out.exists():
        sys.exit("error: CHECK_RESULT.json exists; this runs once")
    rows = pd.read_csv(HERE / "rows_IDX.csv.gz", parse_dates=["date"])
    C = rows[(rows.date >= "2026-04-01") & (rows.date <= "2026-09-08")].copy()
    h = pd.read_csv(HEADLINES, parse_dates=["date"])
    C["dil_news"] = news_flag(C, h)
    flat = (C.ret20.abs() < 0.10) & (C.hi60 < 0.95)
    rules = {"R1_momentum": (C.hi60 >= 0.99) & (C.ret20 >= 0.15), "R2_dilution_news_before_move": C.dil_news & flat}
    res_all, prep = {}, None
    for name, mask in rules.items():
        ev = hx.signals(C, mask)
        if len(ev) == 0:
            res_all[name] = {"signals": 0}
            continue
        res, prep = hx.run(ev, prep=prep)
        res.to_csv(HERE / f"check_{name}.csv", index=False)
        s = stats(res)
        b = s.get("excess_vs_any_B_boot", {})
        s["holds_up"] = bool(b and b["mean"] > 0 and b["t"] >= 1.65)
        res_all[name] = {"signals": int(len(ev)), **s}
    out.write_text(json.dumps(res_all, indent=1, default=float) + "\n")
    print(json.dumps(res_all, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

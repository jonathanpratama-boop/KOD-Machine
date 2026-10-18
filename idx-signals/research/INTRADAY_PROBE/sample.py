"""Fixed probe sample (PROBE_SPEC.md): 12 sessions and, per session, 30 panel names stratified by liquidity tercile,
plus the fixed identity set. Reads only dates, tickers, closes and traded value (no returns).

Usage (from idx-signals/): python3 research/INTRADAY_PROBE/sample.py  -> research/INTRADAY_PROBE/sample.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
SEED = 20261018
IDENTITY = ["FB", "TWTR", "BBBY", "ATVI", "SIVB", "FRC", "DWAC", "SQ", "SNDL", "MRAM"]


def main() -> int:
    p = pd.read_csv(PANEL, usecols=["date", "ticker", "close", "value", "unit_factor"], dtype={"ticker": str},
                    keep_default_na=False, na_values=[""])
    p = p[(p.date >= "2020-06-01") & (p.date <= "2022-12-30")].sort_values(["ticker", "date"])
    p["med_value"] = p.groupby("ticker").value.transform(lambda s: s.shift(1).rolling(20).median())
    rng = np.random.default_rng(SEED)
    sessions = sorted(p[p.date >= "2020-07-01"].date.unique())
    dates = sorted(rng.choice(sessions, size=12, replace=False))
    rows = []
    for d in dates:
        day = p[(p.date == d) & (p.close * p.unit_factor >= 1) & p.med_value.notna()].copy()
        day["tercile"] = pd.qcut(day.med_value.rank(method="first"), 3, labels=["low", "mid", "high"])
        for t, grp in day.groupby("tercile", observed=True):
            for tk in grp.sample(n=10, random_state=int(rng.integers(1 << 31))).ticker:
                rows.append({"date": d, "ticker": tk, "group": f"panel_{t}"})
        rows += [{"date": d, "ticker": tk, "group": "identity"} for tk in IDENTITY]
    out = pd.DataFrame(rows)
    out.to_csv(Path(__file__).with_name("sample.csv"), index=False)
    print(f"{len(dates)} dates, {len(out)} (name, date) pairs: {dates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""MOVERS_NOW_v1 exploration (learn window 2025-01-02 .. 2026-03-31). Writes rows_<market>.parquet-like csv.gz and prints the tables.
Usage (from idx-signals/): python3 research/MOVERS_NOW_v1/study.py IDX"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mv_lib as mv  # noqa: E402

market = sys.argv[1]
P = mv.load(market)
f, y = mv.features(P), mv.labels(P)
trad = mv.etoro_symbols().get(market)
t = mv.long_table(market, f, y, trad)
t = t[t.date >= "2025-01-02"]
t.to_csv(HERE / f"rows_{market}.csv.gz", index=False)
print(market, "rows", len(t), "names", t.ticker.nunique(), "dates", t.date.min().date(), t.date.max().date())

"""CASES_GLOBAL_v1 selection (PROTOCOL.md)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE.parent
rng = np.random.default_rng(20261027)
groups = [("US", R / "LEAD_LADDER_v1/results/events_US.csv.gz", 10), ("CRYPTO", R / "LEAD_LADDER_v1/results/events_CRYPTO.csv.gz", 5)]
out = []
for market, path, k in groups:
    ev = pd.read_csv(path, usecols=["kind", "ticker", "t", "t_date"], dtype={"ticker": str}, keep_default_na=False)
    ep = ev[ev["kind"] == "FAST_UP"].drop_duplicates(["ticker", "t"]).sort_values(["t_date", "ticker"]).reset_index(drop=True)
    for i in np.sort(rng.choice(len(ep), size=k, replace=False)):
        out.append({"market": market, **ep.iloc[i][["ticker", "t", "t_date"]].to_dict()})
intl = []
for f in sorted((R / "LEAD_LADDER_INTL_v1/results").glob("events_*.csv.gz")):
    ev = pd.read_csv(f, usecols=["market", "kind", "ticker", "t", "t_date"], dtype={"ticker": str}, keep_default_na=False)
    intl.append(ev[ev["kind"] == "FAST_UP"].drop_duplicates(["ticker", "t"]))
ep = pd.concat(intl).sort_values(["market", "t_date", "ticker"]).reset_index(drop=True)
for i in np.sort(rng.choice(len(ep), size=5, replace=False)):
    out.append(ep.iloc[i][["market", "ticker", "t", "t_date"]].to_dict())
out = [{k: (int(v) if k == "t" else str(v)) for k, v in c.items()} for c in out]
with (HERE / "selection.json").open("x", encoding="utf-8") as fh:
    fh.write(json.dumps({"seed": 20261027, "cases": out}, indent=1) + "\n")
for c in out:
    print(c)

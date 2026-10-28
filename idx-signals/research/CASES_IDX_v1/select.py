"""CASES_IDX_v1 selection (PROTOCOL.md): 20 FAST_UP episodes at random, seed 20261027."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ev = pd.read_csv(HERE.parent / "LEAD_LADDER_v1" / "results" / "events_IDX.csv.gz", usecols=["kind", "ticker", "t", "t_date"],
                 dtype={"ticker": str})
ep = ev[ev["kind"] == "FAST_UP"].drop_duplicates(["ticker", "t"]).sort_values(["t_date", "ticker"]).reset_index(drop=True)
pick = np.sort(np.random.default_rng(20261027).choice(len(ep), size=20, replace=False))
out = ep.iloc[pick][["ticker", "t", "t_date"]].reset_index(drop=True)
with (HERE / "selection.json").open("x", encoding="utf-8") as fh:
    fh.write(json.dumps({"population": int(len(ep)), "seed": 20261027, "cases": out.to_dict("records")}, indent=2) + "\n")
print(out.to_string())

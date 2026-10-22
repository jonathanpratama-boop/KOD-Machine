"""US_8K_ITEMS step 2: events.csv from filings8k.csv.gz (no price read). Usage (from idx-signals/): python3 research/US_8K_ITEMS/build_events.py"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from k_lib import build_events  # noqa: E402

out = HERE / "events.csv"
if out.exists():
    sys.exit("error: events.csv exists")
ev = build_events(pd.read_csv(HERE / "filings8k.csv.gz", dtype={"accession": str, "items": str}, keep_default_na=False, na_values=[""]))
ev.to_csv(out, index=False)
print(len(ev), ev.groupby(["stage", "item"]).size().unstack(0).to_dict())

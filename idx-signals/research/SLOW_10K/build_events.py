"""SLOW_10K step 3: the event table from similarity.csv.gz. Every filing with a similarity gets its bucket from the filings accepted in the previous 365 days
(tenk_lib.buckets: Q1 / Q5 / MID, and tenk_buckets.buckets5 for the descriptive quintiles); the events are the classified filings of the stage windows (by filing date).
No price is read. Writes events.csv (refuses to overwrite). Usage (from idx-signals/): python3 research/SLOW_10K/build_events.py"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tenk_buckets import buckets5  # noqa: E402
from tenk_lib import buckets  # noqa: E402

STAGES = {1: ("2021-01-04", "2022-12-30"), 2: ("2023-01-03", "2023-09-29")}


def build(sim: pd.DataFrame) -> pd.DataFrame:
    s = sim[(sim.http_status == 200) & sim.cosine.notna()].copy()
    s["filing_date"] = pd.to_datetime(s["filing_date"])
    s = s.sort_values(["filing_date", "cik", "accession"]).reset_index(drop=True)
    s["bucket"] = buckets(s)
    s["quintile"] = buckets5(s)
    assert ((s.bucket == "Q1") == (s.quintile == "Q1")).all() and ((s.bucket == "Q5") == (s.quintile == "Q5")).all()
    s["stage"] = 0
    for k, (a, b) in STAGES.items():
        s.loc[(s.filing_date >= a) & (s.filing_date <= b), "stage"] = k
    ev = s[(s.stage > 0) & (s.bucket != "")].copy()
    ev["public_date"] = ev.filing_date.dt.strftime("%Y-%m-%d")
    return ev[["ticker", "cik", "accession", "public_date", "stage", "bucket", "quintile", "cosine", "length_ratio", "n_tokens", "gap_days"]].reset_index(drop=True)


def main() -> int:
    out = HERE / "events.csv"
    if out.exists():
        sys.exit("error: events.csv exists")
    ev = build(pd.read_csv(HERE / "similarity.csv.gz", dtype={"accession": str}))
    ev.to_csv(out, index=False)
    print(len(ev), "events;", ev.groupby(["stage", "bucket"]).size().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())

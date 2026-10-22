"""US_INSIDER_BUY step 2: the event table from form4_purchases.csv.gz and SLOW_10K's committed filings.csv.gz (issuer CIK -> panel ticker). No price is read. Writes events.csv and
feasibility/FUNNEL.json (refuses to overwrite). Usage (from idx-signals/): python3 research/US_INSIDER_BUY/build_events.py"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ib_lib import build_events  # noqa: E402

FILINGS = HERE.parent / "SLOW_10K" / "filings.csv.gz"


def cik_map() -> pd.Series:
    f = pd.read_csv(FILINGS, usecols=["cik", "ticker"], dtype={"ticker": str}, keep_default_na=False)
    return f.drop_duplicates("cik").set_index("cik")["ticker"]


def main() -> int:
    out, funnel_path = HERE / "events.csv", HERE / "feasibility" / "FUNNEL.json"
    if out.exists() or funnel_path.exists():
        sys.exit("error: events.csv or feasibility/FUNNEL.json exists")
    lines = pd.read_csv(HERE / "form4_purchases.csv.gz", dtype={"accession": str, "symbol": str, "aff10b5one": str}, keep_default_na=False,
                        na_values=[""])
    lines["aff10b5one"] = lines["aff10b5one"].fillna("")
    lines["symbol"] = lines["symbol"].fillna("")
    ev, funnel = build_events(lines, cik_map())
    ev.to_csv(out, index=False)
    funnel_path.parent.mkdir(exist_ok=True)
    funnel["events_by_stage_and_role"] = {f"{s}|top_exec={t}": int(n) for (s, t), n in ev.groupby(["stage", "top_exec"]).size().items()}
    funnel_path.write_text(json.dumps(funnel, indent=1) + "\n")
    print(json.dumps(funnel, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Catalyst-side warm start, 13D pool fixed (open item since LEARNER v2.3's ADDENDUM_3).

The v2.2 warm start (research/LEARNER_v2/warmstart) counted, for every event, earlier events on the same ticker within 90
days (repeat_90d, corroborate_90d, conflict_90d). Its Form 4 and 8-K pools held every collected event, but its 13D pool held
only the 1,188 filings the kill test went on to score (results/events_all.csv): whether a filing could be scored depends on
prices after it, so the 13D counts leaked eventual scorability. This build recounts with the 13D pool taken from the full
collection (KILL_TEST_2020_2023/events.csv.gz, 4,857 filings, dated by filing date), changes nothing else, and reports every
row whose counts change. Writes events.csv.gz and BUILD.json here; the frozen warm start is not touched."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "warmstart"
_spec = importlib.util.spec_from_file_location("ws", OLD / "build.py")
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)  # the frozen build's counts() and paths, imported, not copied
FULL_13D = ROOT / "research" / "CATALYST_REGISTER_v1" / "KILL_TEST_2020_2023" / "events.csv.gz"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    old = pd.read_csv(OLD / "events.csv.gz", low_memory=False, dtype={"accession": str})
    full = pd.read_csv(FULL_13D, low_memory=False, dtype={"accession": str})
    full["ticker"] = full["tickers"].astype(str).str.split(r"[;, |]").str[0].str.strip().str.upper()
    full = full[full["ticker"].notna() & (full["ticker"] != "") & (full["ticker"] != "NAN")]
    f4e = pd.read_csv(ws.F4_EVENTS, low_memory=False, dtype={"accession": str})
    d8e = pd.read_csv(ws.DIL_EVENTS, low_memory=False, dtype={"accession": str})
    d8e = d8e[d8e["item"].astype(str) == "3.02"] if "item" in d8e.columns else d8e.iloc[0:0]
    pool = pd.concat([
        pd.DataFrame({"source": "kill13d", "accession": full["accession"], "ticker": full["ticker"], "date": full["date_filed"], "direction": 1}),
        pd.DataFrame({"source": "form4", "accession": f4e["accession"], "ticker": f4e["ticker"], "date": f4e["public_date"], "direction": 1}),
        pd.DataFrame({"source": "dil302", "accession": d8e["accession"], "ticker": d8e["ticker"], "date": d8e["public_date"], "direction": -1}),
    ], ignore_index=True)
    pool = pool[pool["date"] <= ws.LAST_DATE].dropna(subset=["ticker"])
    cols = ["repeat_90d", "corroborate_90d", "conflict_90d"]
    new = ws.counts(old.drop(columns=cols), pool)
    changed = (new[cols].to_numpy() != old[cols].to_numpy()).any(axis=1)
    new.to_csv(HERE / "events.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.10g")
    summary = {"built_by": "research/LEARNER_v2/warmstart_cat_fix/build.py", "from": {"warm_start": sha(OLD / "events.csv.gz"),
               "full_13d_collection": sha(FULL_13D)}, "rows": int(len(new)),
               "pool_13d": {"before_scored_filings": int(len(pd.read_csv(ws.KILL, usecols=["accession"]))),
                            "after_full_collection_with_ticker": int(len(full))},
               "rows_changed": int(changed.sum()),
               "rows_changed_by_source": {s: int((changed & (new["source"] == s)).sum()) for s in ("kill13d", "form4", "dil302")},
               "mean_counts": {c: {"before": float(old[c].mean()), "after": float(new[c].mean())} for c in cols},
               "events_csv_gz": sha(HERE / "events.csv.gz")}
    (HERE / "BUILD.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

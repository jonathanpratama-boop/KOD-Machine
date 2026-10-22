"""US_INSIDER_BUY step 1: download the 14 quarterly SEC Insider Transactions Data Sets (2020q3 .. 2023q4), keep the purchase lines (ib_lib.parse_quarter) in form4_purchases.csv.gz and
write a manifest with each zip's URL, size, sha256 and funnel counts. The zips are read in memory and not stored. The SEC fair-access contact is read from KOD_SEC_CONTACT and never
written to a file. Writes form4_purchases.csv.gz and data/manifests/sec_form345-<stamp>.json (refuses to overwrite; writes nothing if any quarter fails).
Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/US_INSIDER_BUY/fetch_form345.py
"""
import gzip
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "SLOW_10K"))
from ib_lib import QUARTERS, URL, parse_quarter  # noqa: E402
from tenk_lib import Limiter, get  # noqa: E402


def main() -> int:
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)")
    out = HERE / "form4_purchases.csv.gz"
    if out.exists():
        sys.exit("error: form4_purchases.csv.gz exists")
    ua = f"KOD-Machine research {contact}"
    limiter = Limiter(interval=0.5)
    parts, log, seen, overlap = [], [], set(), 0
    for q in QUARTERS:
        url = URL.format(quarter=q)
        status, body = get(url, ua, limiter, max_bytes=500_000_000)
        rec = {"quarter": q, "url": url, "status": status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest() if body else ""}
        if status != 200:
            sys.exit(f"error: {url} HTTP {status}; nothing written")
        lines, counts = parse_quarter(zipfile.ZipFile(io.BytesIO(body)))
        dup = lines["accession"].isin(seen)
        overlap += int(dup.sum())
        lines = lines[~dup]
        seen |= set(lines["accession"])
        rec["funnel"] = {**counts, "lines_already_seen_in_an_earlier_quarter": int(dup.sum())}
        parts.append(lines)
        log.append(rec)
        print(q, rec["funnel"], flush=True)
    df = pd.concat(parts, ignore_index=True)
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man = {"fetched_at": stamp, "source": "SEC Insider Transactions Data Sets (Forms 3, 4, 5)", "quarters": QUARTERS, "files": log, "extract": "research/US_INSIDER_BUY/form4_purchases.csv.gz",
           "extract_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "lines": int(len(df)), "accessions": int(df["accession"].nunique()), "lines_in_two_quarters": overlap,
           "lines_by_filing_year": {str(k): int(v) for k, v in df.groupby(df["filing_date"].str[:4]).size().items()}}
    path = ROOT / "data" / "manifests" / f"sec_form345-{stamp}.json"
    path.write_text(json.dumps(man) + "\n")
    print(json.dumps({k: v for k, v in man.items() if k != "files"}, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

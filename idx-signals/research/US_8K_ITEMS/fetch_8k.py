"""US_8K_ITEMS step 1: the 8-K filings (form '8-K', filing date 2020-06-01 .. 2023-09-29, with their items) of the issuers in SLOW_10K's filings.csv.gz, from EDGAR submissions JSON (recent block
and the older chunk files overlapping the span). Writes filings8k.csv.gz and data/manifests/sec_8k_filings-<stamp>.json. Contact from KOD_SEC_CONTACT (never written to a file).
Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/US_8K_ITEMS/fetch_8k.py"""
import concurrent.futures as cf
import gzip
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "SLOW_10K"))
sys.path.insert(0, str(ROOT))
from idxsig import catalyst  # noqa: E402
from tenk_lib import Limiter, get  # noqa: E402

SPAN = ("2020-06-01", "2023-09-29")


def eight_ks(sub: dict) -> list[dict]:
    rec = sub["filings"]["recent"] if "recent" in sub.get("filings", {}) else sub
    n = len(rec["form"])
    items = rec.get("items", [""] * n)
    return [{"accession": rec["accessionNumber"][i], "filing_date": rec["filingDate"][i], "items": items[i]} for i in range(n)
            if rec["form"][i] == "8-K" and SPAN[0] <= rec["filingDate"][i] <= SPAN[1]]


def main() -> int:
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT")
    out = HERE / "filings8k.csv.gz"
    if out.exists():
        sys.exit("error: filings8k.csv.gz exists")
    ua, limiter = f"KOD-Machine research {contact}", Limiter()
    cm = pd.read_csv(HERE.parent / "SLOW_10K" / "filings.csv.gz", usecols=["cik", "ticker"], dtype={"ticker": str}, keep_default_na=False).drop_duplicates("cik")
    pick = dict(zip(cm.cik.astype(int), cm.ticker))
    log = []

    def fetch(cik):
        url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        st, b = get(url, ua, limiter)
        log.append({"url": url, "status": st, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
        if st != 200:
            return cik, None, st
        found = eight_ks(json.loads(b))
        for name in catalyst.chunk_names(b, *SPAN):
            u = f"https://data.sec.gov/submissions/{name}"
            st2, b2 = get(u, ua, limiter)
            log.append({"url": u, "status": st2, "bytes": len(b2), "sha256": hashlib.sha256(b2).hexdigest()})
            if st2 == 200:
                found += eight_ks(json.loads(b2))
        return cik, found, 200

    recs, failed = [], []
    with cf.ThreadPoolExecutor(4) as ex:
        for k, (cik, found, st) in enumerate(ex.map(fetch, sorted(pick)), 1):
            if found is None:
                failed.append({"cik": cik, "status": st})
            recs += [{"cik": cik, "ticker": pick[cik], **f} for f in found or []]
            if k % 500 == 0:
                print(f"{k}/{len(pick)} issuers, {len(recs)} filings", flush=True)
    df = pd.DataFrame(recs).drop_duplicates(["cik", "accession"]).sort_values(["cik", "filing_date", "accession"]).reset_index(drop=True)
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man = {"fetched_at": stamp, "span": SPAN, "issuers": len(pick), "issuers_with_an_8k": int(df.cik.nunique()), "filings": int(len(df)), "failed_issuers": failed,
           "file": "research/US_8K_ITEMS/filings8k.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "requests": len(log), "responses": log}
    path = ROOT / "data" / "manifests" / f"sec_8k_filings-{stamp}.json"
    path.write_text(json.dumps(man) + "\n")
    print(json.dumps({k: v for k, v in man.items() if k != "responses"}, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""SEC_8K_v1 step 1: filing rows (8-K with items, 13D/13G, S-1/S-3/S-8, 424B offerings, proxies, late-filing notices; 2020-12-01 .. 2023-09-29) for every
issuer of the US repair panel that SLOW_10K/filings.csv.gz maps to a CIK (3,520). Reads data.sec.gov submissions JSON plus the older chunk files overlapping the span.
The SEC contact is read from KOD_SEC_CONTACT (or IDXSIG_SEC_USER_AGENT) and never written. Writes filings.csv.gz and fetch_manifest.json (url, status, bytes, sha256).
Usage (from idx-signals/): python3 research/SEC_8K_v1/fetch.py"""
import concurrent.futures as cf
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "SLOW_10K"))
from idxsig import catalyst  # noqa: E402
from tenk_lib import Limiter, get  # noqa: E402
import sk_lib  # noqa: E402


def main() -> int:
    contact = (os.environ.get("KOD_SEC_CONTACT") or os.environ.get("IDXSIG_SEC_USER_AGENT") or "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)")
    out = HERE / "filings.csv.gz"
    if out.exists():
        sys.exit("error: filings.csv.gz exists")
    ua = contact if contact.startswith("KOD") else f"KOD-Machine research {contact}"
    lim = Limiter(0.21)
    pick = pd.read_csv(HERE.parent / "SLOW_10K" / "filings.csv.gz", usecols=["cik", "ticker"], dtype={"ticker": str}, keep_default_na=False).drop_duplicates("cik")
    log = []

    def fetch(row):
        cik, ticker = int(row[0]), row[1]
        url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        st, b = get(url, ua, lim)
        log.append({"url": url, "status": st, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
        if st != 200:
            return []
        found = sk_lib.rows(json.loads(b))
        for name in catalyst.chunk_names(b, *sk_lib.SPAN):
            u2 = f"https://data.sec.gov/submissions/{name}"
            s2, b2 = get(u2, ua, lim)
            log.append({"url": u2, "status": s2, "bytes": len(b2), "sha256": hashlib.sha256(b2).hexdigest()})
            if s2 == 200:
                found += sk_lib.rows(json.loads(b2))
        return [{**r, "cik": cik, "ticker": ticker} for r in found]

    recs = []
    with cf.ThreadPoolExecutor(4) as ex:
        for k, found in enumerate(ex.map(fetch, pick[["cik", "ticker"]].itertuples(index=False)), 1):
            recs += found
            if k % 250 == 0:
                print(f"{k}/{len(pick)} issuers, {len(recs)} rows", flush=True)
    df = pd.DataFrame(recs).drop_duplicates("accession" if False else ["cik", "accession"])
    df.to_csv(out, index=False, compression="gzip")
    bad = sum(1 for r in log if r["status"] != 200)
    (HERE / "fetch_manifest.json").write_text(json.dumps({"issuers": len(pick), "rows": len(df), "requests": len(log), "failed": bad, "log": log}) + "\n")
    print(f"done: {len(df)} rows, {len(log)} requests, {bad} failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

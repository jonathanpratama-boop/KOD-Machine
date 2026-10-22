"""SLOW_10K step 1: the 10-K filings (form '10-K', filing date 2019-01-01 .. 2023-09-29) of the issuers in the US repair panel that SEC's ticker map links to a CIK.
One ticker per CIK (the one with the most panel rows, then alphabetical), so a company with two share classes is one issuer. Reads EDGAR's submissions JSON (the recent block and the older
chunk files that overlap the span); nothing is stored but the list, and each response's URL, size and sha256 go into a manifest. The SEC declares-a-contact rule: the contact is read from
KOD_SEC_CONTACT and never written to a file. Writes filings.csv.gz and data/manifests/sec_10k_filings-<stamp>.json.
Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/SLOW_10K/fetch_filings.py
"""
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from idxsig import catalyst  # noqa: E402
from tenk_lib import Limiter, get  # noqa: E402

PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
SPAN = ("2019-01-01", "2023-09-29")


def ten_ks(sub: dict) -> list[dict]:
    rec = sub["filings"]["recent"] if "recent" in sub.get("filings", {}) else sub
    out = []
    for i, form in enumerate(rec["form"]):
        d = rec["filingDate"][i]
        if form == "10-K" and SPAN[0] <= d <= SPAN[1]:
            out.append({"accession": rec["accessionNumber"][i], "filing_date": d, "report_date": rec.get("reportDate", [""] * len(rec["form"]))[i],
                        "primary_document": rec["primaryDocument"][i]})
    return out


def main() -> int:
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)")
    out = HERE / "filings.csv.gz"
    if out.exists():
        sys.exit("error: filings.csv.gz exists")
    ua = f"KOD-Machine research {contact}"
    limiter = Limiter()
    panel = pd.read_csv(PANEL, usecols=["ticker"], dtype={"ticker": str}, keep_default_na=False)
    counts = panel.ticker.value_counts()
    status, body = get("https://www.sec.gov/files/company_tickers.json", ua, limiter)
    if status != 200:
        sys.exit(f"error: SEC ticker map HTTP {status}")
    cmap = {v["ticker"].upper().replace(".", "-"): int(v["cik_str"]) for v in json.loads(body).values()}
    rows = [(t, cmap[t.upper().replace(".", "-")], int(counts[t])) for t in counts.index if t.upper().replace(".", "-") in cmap]
    pick = {}
    for t, cik, n in sorted(rows, key=lambda r: (-r[2], r[0])):
        pick.setdefault(cik, t)
    print(f"{len(counts)} panel tickers, {len(rows)} with a CIK, {len(pick)} issuers", flush=True)
    log = []

    def fetch(cik):
        base = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        st, b = get(base, ua, limiter)
        log.append({"url": base, "status": st, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
        if st != 200:
            return cik, None, st
        found = ten_ks(json.loads(b))
        for name in catalyst.chunk_names(b, *SPAN):
            url = f"https://data.sec.gov/submissions/{name}"
            st2, b2 = get(url, ua, limiter)
            log.append({"url": url, "status": st2, "bytes": len(b2), "sha256": hashlib.sha256(b2).hexdigest()})
            if st2 == 200:
                found += ten_ks(json.loads(b2))
        return cik, found, 200

    recs, failed = [], []
    with cf.ThreadPoolExecutor(4) as ex:
        for k, (cik, found, st) in enumerate(ex.map(fetch, sorted(pick)), 1):
            if found is None:
                failed.append({"cik": cik, "status": st})
            for f in found or []:
                recs.append({"cik": cik, "ticker": pick[cik], **f,
                             "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accession'].replace('-', '')}/{f['primary_document']}"})
            if k % 500 == 0:
                print(f"{k}/{len(pick)} issuers, {len(recs)} filings", flush=True)
    df = pd.DataFrame(recs).drop_duplicates(["cik", "accession"]).sort_values(["cik", "filing_date", "accession"]).reset_index(drop=True)
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man = {"fetched_at": stamp, "span": SPAN, "issuers": len(pick), "issuers_with_a_10k": int(df.cik.nunique()), "filings": int(len(df)), "failed_issuers": failed,
           "file": "research/SLOW_10K/filings.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "requests": len(log) + 1,
           "responses": log, "panel": PANEL.name,
           "filings_by_year": {str(k): int(v) for k, v in df.groupby(df.filing_date.str[:4]).size().items()}}
    path = ROOT / "data" / "manifests" / f"sec_10k_filings-{stamp}.json"
    path.write_text(json.dumps(man) + "\n")
    print(json.dumps({k: v for k, v in man.items() if k != "responses"}, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

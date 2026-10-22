"""SLOW_10K step 2: for each issuer in filings.csv.gz, download its 10-K main documents in date order, build term frequencies (tenk_lib.tf_from_html), and compute the
cosine similarity of each with the issuer's previous 10-K (300-450 days earlier). Documents are not stored: each document's URL, size and sha256 and its features are written
(similarity.csv.gz, plus a per-issuer cache outside the repository so a restart resumes). No price is read. KOD_SEC_CONTACT as in step 1. Several processes share one rate limiter
(about 4.7 requests a second in all).
Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/SLOW_10K/fetch_similarity.py --cache <scratch dir> [--procs 4] [--limit N]
"""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from tenk_lib import Limiter, choose_previous, cosine, get, norm, tf_from_html  # noqa: E402

_STATE = {}


def init(limiter, ua):
    _STATE["limiter"], _STATE["ua"] = limiter, ua


def process_issuer(task):
    cik, ticker, filings, cache_dir = task
    cache = Path(cache_dir) / f"{cik}.json"
    if cache.exists():
        return cik, json.loads(cache.read_text())
    rows, kept = [], []
    for f in filings:                                   # date order
        t0 = time.time()
        status, body = get(f["url"], _STATE["ua"], _STATE["limiter"])
        rec = {"cik": cik, "ticker": ticker, "accession": f["accession"], "filing_date": f["filing_date"], "report_date": f["report_date"], "url": f["url"], "http_status": status,
               "doc_bytes": len(body), "doc_sha256": hashlib.sha256(body).hexdigest() if body else None}
        if status != 200 or not body:
            rows.append(rec)
            continue
        tf = tf_from_html(body)
        nt = sum(tf.values())
        rec.update({"n_tokens": nt, "n_unique": len(tf)})
        d = pd.Timestamp(f["filing_date"])
        prev = choose_previous(d, kept)
        nrm = norm(tf)
        if prev is not None and nt:
            rec.update({"prev_accession": prev["accession"], "gap_days": (d - prev["filing_date"]).days, "cosine": cosine(tf, prev["tf"], nrm, prev["norm"]),
                        "length_ratio": nt / prev["n_tokens"]})
        rec["seconds"] = round(time.time() - t0, 2)
        rows.append(rec)
        kept.append({"accession": f["accession"], "filing_date": d, "tf": tf, "norm": nrm, "n_tokens": nt})
    cache.write_text(json.dumps(rows))
    return cik, rows


def main() -> int:
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)")
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="process only the first N issuers (a smoke test; writes nothing to the repository)")
    args = ap.parse_args()
    out = HERE / "similarity.csv.gz"
    if out.exists() and not args.limit:
        sys.exit("error: similarity.csv.gz exists")
    fil = pd.read_csv(HERE / "filings.csv.gz", dtype={"accession": str, "report_date": str}, keep_default_na=False)
    groups = [(int(c), g.ticker.iloc[0], g.sort_values(["filing_date", "accession"]).to_dict("records"), args.cache) for c, g in fil.groupby("cik")]
    if args.limit:
        groups = groups[:args.limit]
    Path(args.cache).mkdir(parents=True, exist_ok=True)
    print(f"{len(groups)} issuers, {sum(len(g[2]) for g in groups)} filings", flush=True)
    limiter = Limiter()
    rows, t0 = [], time.time()
    with cf.ProcessPoolExecutor(args.procs, initializer=init, initargs=(limiter, f"KOD-Machine research {contact}")) as ex:
        for k, (cik, r) in enumerate(ex.map(process_issuer, groups, chunksize=1), 1):
            rows += r
            if k % 100 == 0:
                print(f"{k}/{len(groups)} issuers, {len(rows)} filings, {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows).sort_values(["filing_date", "cik", "accession"]).reset_index(drop=True)
    if args.limit:
        print(df[["ticker", "filing_date", "http_status", "doc_bytes", "n_tokens", "gap_days", "cosine", "length_ratio", "seconds"]].to_string())
        return 0
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man = {"fetched_at": stamp, "seconds": round(time.time() - t0), "filings": int(len(df)), "downloaded_ok": int((df.http_status == 200).sum()),
           "with_similarity": int(df.cosine.notna().sum()), "failed": int((df.http_status != 200).sum()),
           "file": "research/SLOW_10K/similarity.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "filings_file_sha256": hashlib.sha256((HERE / "filings.csv.gz").read_bytes()).hexdigest(),
           "feature": "tenk_lib.tf_from_html + cosine (see PROTOCOL.md)"}
    path = ROOT / "data" / "manifests" / f"sec_10k_similarity-{stamp}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

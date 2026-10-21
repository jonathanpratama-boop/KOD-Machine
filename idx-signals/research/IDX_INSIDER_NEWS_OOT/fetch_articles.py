"""IDX_INSIDER_NEWS_OOT step 2: fetch the candidate articles with test 23's candidate rule and parser, unchanged
(research/IDX_INSIDER_NEWS/fetch_articles.py: purchase-like word in the slug and an IDX ticker code among the slug words, ticker list pinned to
the IDX mirror commit), for index rows dated FIRST .. 2026-10-06. Keeps title, posting time (WIB), the first 2,500 characters of the body
and the page's sha256. Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/fetch_articles.py [--workers 3]
"""
import argparse
import gzip
import hashlib
import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd

from oot_common import END, FIRST, HERE, ROOT, load_old


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    out = HERE / "articles.csv.gz"
    if out.exists():
        sys.exit("error: articles.csv.gz exists")
    old = load_old("fetch_articles")
    old.INDEX = HERE / "sitemap_index.csv.gz"
    cand = old.candidates()
    cand = cand[(cand.date >= FIRST) & (cand.date <= END)].reset_index(drop=True)
    if cand.date.min() < FIRST:
        sys.exit("error: a candidate before the first date")
    print(f"{len(cand)} candidate articles")

    def one(row):
        time.sleep(0.35)
        raw = old.fetch(row.url)
        if raw is None:
            return {"url": row.url, "slug": row.slug, "sitemap_date": row.date, "failed": True}
        return {"url": row.url, "slug": row.slug, "sitemap_date": row.date, "failed": False, "html_sha256": hashlib.sha256(raw).hexdigest(),
                "html_bytes": len(raw), **old.parse(raw)}

    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(one, cand.itertuples()))
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    ok = df[~df.failed]
    man = {"fetched_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "seconds": round(time.time() - t0), "candidates": int(len(cand)),
           "failed": int(df.failed.sum()), "without_posting_time": int(ok.posted_wib.isna().sum()), "without_body": int((ok.body_head.fillna("") == "").sum()),
           "file": "research/IDX_INSIDER_NEWS_OOT/articles.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
           "candidate_rule": "test 23's fetch_articles.candidates() on this index (BROAD words in the slug and a four-letter ticker code among the slug words)"}
    path = ROOT / "data" / "manifests" / f"emitennews_articles_oot-{man['fetched_at']}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

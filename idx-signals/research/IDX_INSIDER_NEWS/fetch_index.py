"""IDX_INSIDER_NEWS step 1: store EmitenNews' yearly sitemaps for 2021-2023 as a headline index (article slug and the date the
sitemap gives it). 2020 is not used (its sitemap covers 4 months) and 2024 onward is never fetched (sealed IDX holdout from
2024-01-02). Writes sitemap_index.csv.gz and data/manifests/emitennews_sitemaps-<stamp>.json (each sitemap's URL, bytes, sha256).
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/fetch_index.py
"""
import gzip
import hashlib
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
YEARS = (2021, 2022, 2023)
UA = {"User-Agent": "Mozilla/5.0 (KOD-Machine research)"}


def main() -> int:
    out = HERE / "sitemap_index.csv.gz"
    if out.exists():
        sys.exit("error: sitemap_index.csv.gz exists")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows, files = [], []
    for y in YEARS:
        url = f"https://www.emitennews.com/sitemap-{y}.xml"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            body = r.read()
        files.append({"url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
        for loc, last in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", body.decode()):
            if "/news/" in loc:
                rows.append({"date": last, "slug": loc.rsplit("/", 1)[1], "url": loc})
    df = pd.DataFrame(rows).drop_duplicates("url").sort_values(["date", "slug"]).reset_index(drop=True)
    if df.date.max() >= "2024-01-01":
        sys.exit("error: a 2024 date reached the index")
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    man = {"fetched_at": stamp, "sitemaps": files, "rows": int(len(df)), "first": df.date.min(), "last": df.date.max(),
           "rows_by_year": {str(k): int(v) for k, v in df.groupby(df.date.str[:4]).size().items()},
           "file": "research/IDX_INSIDER_NEWS/sitemap_index.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
           "note": "date is the sitemap's lastmod (a date, no time); it may be a later update date, never earlier than publication"}
    path = ROOT / "data" / "manifests" / f"emitennews_sitemaps-{stamp}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

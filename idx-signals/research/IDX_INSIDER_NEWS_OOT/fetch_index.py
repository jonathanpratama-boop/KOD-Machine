"""IDX_INSIDER_NEWS_OOT step 1: EmitenNews' yearly sitemaps for 2025 and 2026 as a headline index (article slug and the date the sitemap
gives it). Rows dated before FIRST (2025-03-03) are dropped in memory and never stored, counted or printed: the days up to 2025-02-21 are
the sealed IDX holdout and the five sessions after it are the embargo. Writes sitemap_index.csv.gz and
data/manifests/emitennews_sitemaps_oot-<stamp>.json (each sitemap's URL, bytes and sha256; the kept rows).
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/fetch_index.py
"""
import gzip
import hashlib
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from oot_common import FIRST, HERE, ROOT

YEARS = (2025, 2026)
UA = {"User-Agent": "Mozilla/5.0 (KOD-Machine research)"}


def parse(body: str, first: str = FIRST) -> list[dict]:
    """Sitemap entries of news pages dated `first` or later (earlier ones are never kept)."""
    rows = []
    for loc, last in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", body):
        if "/news/" in loc and last[:10] >= first:
            rows.append({"date": last[:10], "slug": loc.rsplit("/", 1)[1], "url": loc})
    return rows


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
        rows += parse(body.decode())
    df = pd.DataFrame(rows).drop_duplicates("url").sort_values(["date", "slug"]).reset_index(drop=True)
    if df.date.min() < FIRST:
        sys.exit("error: a row before the first date reached the index")
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    man = {"fetched_at": stamp, "sitemaps": files, "kept_from": FIRST, "rows": int(len(df)), "first": df.date.min(), "last": df.date.max(),
           "file": "research/IDX_INSIDER_NEWS_OOT/sitemap_index.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
           "note": "rows dated before kept_from were dropped in memory; date is the sitemap's lastmod, never earlier than publication"}
    path = ROOT / "data" / "manifests" / f"emitennews_sitemaps_oot-{stamp}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

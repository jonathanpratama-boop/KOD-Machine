"""Fetch Binance's 'New Cryptocurrency Listing' announcement catalog (CMS catalogId 48): id, title, release time in
milliseconds. Writes announcements.csv.gz (every article, newest first, as served) and a hash manifest
data/manifests/binance_announcements-<stamp>.json. Titles and times only; no price is read.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1M/fetch_announcements.py
"""
import gzip
import hashlib
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
URL = ("https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48"
       "&pageNo={page}&pageSize={size}")
UA = {"User-Agent": "Mozilla/5.0 (KOD-Machine research)"}
PAGE_SIZE = 50


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows, total, page = [], None, 1
    while True:
        with urllib.request.urlopen(urllib.request.Request(URL.format(page=page, size=PAGE_SIZE), headers=UA), timeout=60) as r:
            body = json.loads(r.read())
        cat = body["data"]["catalogs"][0]
        total = cat["total"]
        arts = cat["articles"]
        if not arts:
            break
        rows.extend({"id": a["id"], "code": a["code"], "release_ms": a["releaseDate"], "title": a["title"]} for a in arts)
        if len(rows) >= total:
            break
        page += 1
        time.sleep(0.4)
    df = pd.DataFrame(rows).drop_duplicates("id").sort_values("release_ms", ascending=False).reset_index(drop=True)
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    out = Path(__file__).resolve().parent / "announcements.csv.gz"
    with out.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode("utf-8"))
    man = {"fetched_at": stamp, "source": URL.format(page="N", size=PAGE_SIZE), "catalog": "New Cryptocurrency Listing (48)",
           "reported_total": total, "rows": int(len(df)),
           "first_release": datetime.fromtimestamp(df.release_ms.min() / 1000, timezone.utc).isoformat(),
           "last_release": datetime.fromtimestamp(df.release_ms.max() / 1000, timezone.utc).isoformat(),
           "file": "research/BINANCE_ANN_1M/announcements.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    path = ROOT / "data" / "manifests" / f"binance_announcements-{stamp}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

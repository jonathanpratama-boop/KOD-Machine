"""IDX_INSIDER_NEWS step 2: fetch the candidate articles (headline words that suggest a share purchase and a token that is an IDX
ticker code) and keep only what the labelling and the event study need: title, posting time (WIB, from the page), the first 2,500
characters of the body, and the sha256 of the page bytes. Candidate rule (fixed here, before any price is looked at):
  slug words contain one of borong bungkus serok akumulasi lahap sikat beli membeli tambah menambah kuasai menguasai ambil kerek
  naikkan tebus, AND at least one slug word is a four-letter IDX ticker code of the mirror's list (data/raw/idx_mirror, List Emiten/all.csv).
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/fetch_articles.py [--workers 3]
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INDEX = HERE / "sitemap_index.csv.gz"
TICKERS = ROOT / "data" / "raw" / "idx_mirror" / "bc0ac7712ce5" / "List Emiten" / "all.csv"
BROAD = re.compile(r"\b(borong|bungkus|serok|akumulasi|lahap|sikat|beli|membeli|tambah|menambah|kuasai|menguasai|ambil|kerek|naikkan|tebus)\b")
UA = {"User-Agent": "Mozilla/5.0 (KOD-Machine research script)"}
BODY_CHARS = 2500
WIB = timezone(timedelta(hours=7))


def ticker_set() -> set[str]:
    with TICKERS.open(encoding="utf-8", errors="ignore") as fh:
        return {r["code"].strip().lower() for r in csv.DictReader(fh) if re.fullmatch(r"[A-Za-z]{4}", (r["code"] or "").strip())}


def candidates() -> pd.DataFrame:
    df = pd.read_csv(INDEX)
    tick = ticker_set()
    words = df.slug.str.replace("-", " ")
    keep = words.map(lambda s: bool(BROAD.search(s))) & words.map(lambda s: any(w in tick for w in s.split()))
    return df[keep].reset_index(drop=True)


def parse(raw: bytes) -> dict:
    soup = BeautifulSoup(raw.decode("utf-8", "ignore"), "lxml")
    h1, tp, body = soup.select_one("h1.m-0"), soup.select_one("span.time-posted"), soup.select_one("div.article-body")
    posted = None
    if tp:
        m = re.search(r"(\d{2})/(\d{2})/(\d{4}),\s*(\d{2}):(\d{2})", tp.get_text())
        if m:
            d, mo, y, hh, mm = map(int, m.groups())
            posted = datetime(y, mo, d, hh, mm, tzinfo=WIB)
    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)) if body else ""
    return {"title": h1.get_text(" ", strip=True) if h1 else None, "posted_wib": posted.isoformat() if posted else None,
            "posted_utc": posted.astimezone(timezone.utc).isoformat() if posted else None, "body_head": text[:BODY_CHARS]}


def fetch(url: str, retries: int = 3) -> bytes | None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                if r.geturl().endswith("/404"):
                    return None
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 * (attempt + 1))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    out = HERE / "articles.csv.gz"
    if out.exists():
        sys.exit("error: articles.csv.gz exists")
    cand = candidates()
    if cand.date.max() >= "2024-01-01":
        sys.exit("error: a 2024 date reached the candidates")
    print(f"{len(cand)} candidate articles")

    def one(row):
        time.sleep(0.35)
        raw = fetch(row.url)
        if raw is None:
            return {"url": row.url, "slug": row.slug, "sitemap_date": row.date, "failed": True}
        return {"url": row.url, "slug": row.slug, "sitemap_date": row.date, "failed": False, "html_sha256": hashlib.sha256(raw).hexdigest(),
                "html_bytes": len(raw), **parse(raw)}

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
           "file": "research/IDX_INSIDER_NEWS/articles.csv.gz", "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
           "candidate_rule": "BROAD words in the slug and a four-letter IDX ticker code among the slug words (fetch_articles.py)"}
    path = ROOT / "data" / "manifests" / f"emitennews_articles-{man['fetched_at']}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

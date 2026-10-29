"""UMA_IDX_v1 collect: Unusual Market Activity (UMA) notices on IDX as reported by EmitenNews, 2019 to October 2026.

idx.co.id refuses this container (HTTP 403), so the labels come from the press: every EmitenNews article whose URL slug
has the word "uma" (yearly sitemaps, as idxsig/sensors.py reads them), fetched once; its stocks are the codes in parentheses
in the headline and the four-letter slug words that are listed IDX codes (the IDX panel's tickers) and that the article writes as a code (in capitals in the headline or in brackets), so Indonesian words that are also codes (NAIK, PADA, POLA) are not taken, dated by the sitemap's
date. Writes labels.csv (one row per article and stock) and COLLECT.json. No price is
read. IDX ends stock-level UMA and suspension in early November 2026 (EmitenNews, 30 October 2026): these labels are
history; the live successor is IDX's public notice that an investigation has started."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) KOD-Machine-research"}
SLUG = re.compile(r"<loc>https://www\.emitennews\.com/news/([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>")
CODE = re.compile(r"\(([A-Z]{4})\)")
NOT_CODES = {"IHSG", "BEI", "OJK", "UMA", "LQ45", "IDX", "ARA", "ARB", "HMETD", "RUPS", "RUPST", "RUPSLB", "PT"}


def get(url: str) -> str:
    for k in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(3 * (k + 1))
    raise RuntimeError(url)


def listed() -> set[str]:
    sys.path.insert(0, str(HERE.parents[1]))
    from idxsig import panel
    from idxsig.provenance import MANIFESTS
    return set(panel.load(MANIFESTS / "panel-20261007T225823Z.json")[0]["ticker"].astype(str).unique())


def main() -> int:
    global LISTED
    LISTED = listed()
    articles = []
    for y in range(2019, 2027):
        articles += [(s, d) for s, d in SLUG.findall(get(f"https://www.emitennews.com/sitemap-{y}.xml")) if "uma" in s.split("-")]
    rows, seen = [], set()
    for slug, lastmod in sorted(set(articles), key=lambda a: a[1]):
        page = get(f"https://www.emitennews.com/news/{slug}")
        t = re.search(r"<title>(.*?)</title>", page, re.S)
        title = html.unescape(t.group(1)).strip() if t else slug
        body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
        text = " ".join(html.unescape(re.sub("<[^>]+>", "", p)) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S))
        text = text.split("Baca juga")[0]
        # the article's own stocks: codes in the headline, or four-letter slug words that are listed IDX codes; body
        # text is not used (pages carry sidebar stories that name unrelated stocks)
        codes = {c for c in CODE.findall(title) if c not in NOT_CODES}
        page_codes = set(CODE.findall(text)) | set(re.findall(r"(?<![A-Za-z])([A-Z]{4})(?![A-Za-z])", title))
        codes |= {w.upper() for w in slug.split("-") if len(w) == 4 and w.upper() in LISTED and w.upper() not in NOT_CODES
                  and w.upper() in page_codes}  # written as a code (capitals in the headline, or in brackets), not a word
        for c in sorted(codes):
            if (slug, c) not in seen:
                seen.add((slug, c))
                rows.append({"date": lastmod[:10], "ticker": c, "title": title, "url": f"https://www.emitennews.com/news/{slug}"})
        time.sleep(0.5)
    with open(HERE / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "ticker", "title", "url"])
        w.writeheader(); w.writerows(rows)
    meta = {"collected_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "articles": len(set(articles)),
            "labels": len(rows), "tickers": len({r["ticker"] for r in rows}),
            "by_year": {y: sum(r["date"][:4] == str(y) for r in rows) for y in range(2019, 2027)},
            "labels_sha256": hashlib.sha256((HERE / "labels.csv").read_bytes()).hexdigest(),
            "caveat": "the press reports a subset of IDX's UMA notices; a label is a stock named in the headline or URL of an UMA article; the date is the sitemap's (normally the publication date)"}
    (HERE / "COLLECT.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

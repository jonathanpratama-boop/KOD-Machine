"""Select calendar 2025 financial results from all seven frozen issuer wire archives."""

import argparse
from pathlib import Path
import re
from urllib.parse import urlsplit
from idxsig import guidance_margin_feed as feed

ISSUERS = {
    "ZKH": ("1862044", "zkh-group-limited"),
    "TGT": ("27419", "target-corporation"),
    "ZIM": ("1654126", "zim-integrated-shipping-services-ltd."),
    "RRGB": ("1171759", "red-robin-gourmet-burgers%2C-inc."),
    "PSTG": ("1474432", "pure-storage"),
    "KLIC": ("56978", "kulicke-%26-soffa-industries%2C-inc."),
    "UTI": ("1261654", "universal-technical-institute%2C-inc."),
}


def year(row):
    match = re.match(r"^\w+ \d+, (20\d\d),", row["title"])
    return int(match[1]) if match else None


def earnings(row):
    slug = urlsplit(row["url"]).path.rsplit("/", 1)[-1]
    if re.search(
        r"(to-report|to-announce|date-for|schedule|conference-call|upcoming|preliminary|to-release|sets-date|to-present|presentation|will-release|earnings-call)",
        slug,
    ):
        return False
    return bool(
        re.search(r"(quarter|fiscal-year|full-year|annual-results)", slug)
        and re.search(r"(results|earnings|profitability|profit|revenue|sales)", slug)
        and re.search(
            r"(reports|announces|posts|delivers|releases|achieves|announced)", slug
        )
    )


def run(root):
    result = {}
    for ticker, (cik, slug) in ISSUERS.items():
        links = {}
        folder = root / "listings"
        folder.mkdir(exist_ok=True)
        failures = []
        exhausted = False
        for page in range(1, 16):
            url = f"https://www.prnewswire.com/news/{slug}/?page={page}&pagesize=100"
            try:
                doc = feed.retain_source(root, url)
            except OSError as e:
                failures.append(type(e).__name__)
                break
            rows = doc["archive_links"]
            if not rows or rows[-1]["url"] in links:
                failures.append("Pagination exhausted or repeated")
                break
            for entry in rows:
                links[entry["url"]] = entry
            if (year(rows[-1]) or 9999) <= 2024:
                exhausted = True
                break
            if not doc.get("next_url") and len(rows) < 100:
                exhausted = True
                break
        manifest = []
        for i, row in enumerate(links.values()):
            if year(row) != 2025 or not earnings(row):
                continue
            try:
                d = feed.retain_source(root, row["url"])
            except OSError as e:
                failures.append(row["url"] + ": " + type(e).__name__)
                continue
            if not d["published_at"] or not d["published_at"].startswith("2025-"):
                failures.append(row["url"] + ": publication mismatch")
                continue
            manifest.append(
                dict(
                    ticker=ticker,
                    cik=cik,
                    url=row["url"],
                    index=i,
                    at=d["published_at"],
                    hash=d["raw_sha256"],
                    id=d["id"],
                    title=row["title"],
                )
            )
        print(
            ticker,
            len(links),
            len(manifest),
            [e["at"] for e in manifest],
            failures,
            flush=True,
        )
        result[ticker] = {
            "earnings": manifest,
            "links": list(links.values()),
            "errors": failures,
            "archive_covers_window": exhausted,
            "observed_2025_links": sum(year(row) == 2025 for row in links.values()),
        }
        feed.write_json(root / "inventory.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    run(parser.parse_args().state)

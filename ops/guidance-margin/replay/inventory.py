"""Build a consecutive calendar-2025 wire earnings inventory before reading prices."""

import argparse
from pathlib import Path
import re
from urllib.parse import urlsplit
from idxsig import guidance_margin_feed as feed

ISSUERS = {
    "LOW": ("60667", "https://www.prnewswire.com/news/lowe%27s-companies%2C-inc./"),
    "PANW": ("1327567", "https://www.prnewswire.com/news/palo-alto-networks%2C-inc./"),
}


def archive_year(item):
    match = re.search(r"\b(20\d\d)\b", item["title"])
    return int(match[1]) if match else None


def earnings(item):
    slug = urlsplit(item["url"]).path.rsplit("/", 1)[-1].lower()
    return bool(
        re.search(
            r"(reports|announces)-(fiscal-)?(first|second|third|fourth)-quarter", slug
        )
        and re.search(r"(earnings-results|financial-results)", slug)
    )


def run(state):
    result = {}
    for ticker, (cik, url) in ISSUERS.items():
        links = {}
        for page in range(1, 16):
            archive = feed.retain_source(state, f"{url}?page={page}&pagesize=100")
            rows = archive["archive_links"]
            if not rows or rows[-1]["url"] in links:
                break
            for row in rows:
                links[row["url"]] = row
            print(
                ticker,
                page,
                len(rows),
                rows[0]["title"][:50],
                rows[-1]["title"][:65],
                flush=True,
            )
            if (archive_year(rows[-1]) or 9999) < 2025:
                break
        manifest = []
        for i, row in enumerate(links.values()):
            if not earnings(row):
                continue
            doc = feed.retain_source(state, row["url"])
            manifest.append(
                {
                    "ticker": ticker,
                    "cik": cik,
                    "url": row["url"],
                    "index": i,
                    "at": doc["published_at"],
                    "hash": doc["raw_sha256"],
                    "id": doc["id"],
                    "title": row["title"],
                }
            )
        result[ticker] = {"links": list(links.values()), "earnings": manifest}
        print(
            ticker,
            len(links),
            [(d["at"], d["title"][:60]) for d in manifest],
            flush=True,
        )
        feed.write_json(state / "inventory.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    run(parser.parse_args().state)

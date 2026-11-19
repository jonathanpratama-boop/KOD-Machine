"""Refresh point-in-time issuer evidence for the guidance reader."""

import csv
import hashlib
import io
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .guidance_margin_identity import SEC_DIRECTORY
from .provenance import publish_bytes

NASDAQ = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
PATH = "edgar/reference/data/company_tickers.parquet"
LAST_COMMIT = "https://api.github.com/repos/dgunning/edgartools/commits?per_page=1&path=" + PATH
EXCHANGES = {"Q": "Nasdaq", "N": "NYSE", "A": "NYSE American", "P": "NYSE Arca"}


def download(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "KOD Research jonathanpratama@users.noreply.github.com"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        data = response.read(12_000_001)
    if len(data) > 12_000_000:
        raise ValueError("Oversized directory")
    return data


def company_key(value):
    value = value.lower().replace("&", " and ").replace("'", "").replace("’", "")
    tokens = re.findall(r"[a-z0-9]+", value)
    if tokens[:1] == ["the"]:
        tokens.pop(0)
    while tokens and tokens[-1] in {
        "incorporated",
        "inc",
        "corporation",
        "corp",
        "limited",
        "ltd",
        "plc",
    }:
        tokens.pop()
    return tuple(tokens)


def listed_issuer(security):
    return re.split(
        r"\s+(?:-\s+|Class\s+[A-Z0-9]+\s+(?:Common|Ordinary)|Common (?:Stock|Shares)|Ordinary Shares|American Depositary)",
        security,
        maxsplit=1,
        flags=re.I,
    )[0].strip()


def collect(root, at, fetcher):
    sources = []

    def retain(url):
        raw = fetcher(url)
        digest = hashlib.sha256(raw).hexdigest()
        path = root / "issuer_directory_sources" / digest
        if not path.exists():
            publish_bytes(path, raw)
        sources.append({"url": url, "sha256": digest})
        return raw

    try:
        payload = json.loads(retain(SEC_DIRECTORY))
        rows = [dict(zip(payload["fields"], row, strict=True)) for row in payload["data"]]
        current_symbols = {str(r["ticker"]).upper() for r in rows if r["ticker"]}
        mode = "SEC"
    except (OSError, ValueError, KeyError):
        import pyarrow.parquet as pq

        commit = json.loads(fetcher(LAST_COMMIT))[0]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid EDGAR mirror revision")
        url = f"https://raw.githubusercontent.com/dgunning/edgartools/{commit}/{PATH}"
        rows = pq.read_table(
            io.BytesIO(retain(url)), columns=["cik", "ticker", "exchange", "name"]
        ).to_pylist()
        data = retain(NASDAQ).decode().splitlines()
        stamp = re.fullmatch(r"File Creation Time: (\d{8}\d{2}:\d{2})\|*", data[-1])
        if (
            not stamp
            or not 0 <= (at.date() - datetime.strptime(stamp[1], "%m%d%Y%H:%M").date()).days <= 4
        ):
            raise ValueError("Exchange directory is stale")
        securities = {
            (r["Symbol"], EXCHANGES[r["Listing Exchange"]]): listed_issuer(r["Security Name"])
            for r in csv.DictReader(data[:-1], delimiter="|")
            if r["Listing Exchange"] in EXCHANGES and r["Test Issue"] == "N" and r["ETF"] == "N"
        }
        current_symbols = {ticker for ticker, _ in securities}
        rows = [
            r
            for r in rows
            if (r["ticker"], r["exchange"]) in securities
            and company_key(securities[(r["ticker"], r["exchange"])]) == company_key(r["name"])
        ]
        mode = "EDGAR mirror and Nasdaq Trader"

    listings = {}
    for row in rows:
        if row["exchange"] not in EXCHANGES.values() or not str(row["cik"]).isdigit():
            continue
        ticker = str(row["ticker"]).upper()
        listing = [str(int(row["cik"])), row["name"], row["exchange"]]
        if ticker in listings and listing != listings[ticker]:
            listings[ticker] = None
        else:
            listings[ticker] = listing
    if not listings:
        raise ValueError("Empty listing directory")
    return {
        "mode": mode,
        "verified_at": at.isoformat(),
        "sources": sources,
        "listings": listings,
        "unresolved_tickers": sorted(current_symbols - listings.keys()),
    }


def refresh(root, *, at=None, fetcher=download):
    root = Path(root)
    at = at or datetime.now(timezone.utc)
    path = root / "issuer_directory.json"
    if path.exists():
        prior = json.loads(path.read_text())
        if at - datetime.fromisoformat(prior["verified_at"]) < timedelta(days=1):
            return prior
    updated = collect(root, at, fetcher)
    publish_bytes(path, json.dumps(updated, ensure_ascii=False).encode(), replace=True)
    return updated

"""US-listed common stocks from the NASDAQ Trader symbol directory (current listings only).

nasdaqlisted.txt covers Nasdaq; otherlisted.txt covers NYSE, NYSE American, NYSE Arca,
Cboe BZX and IEX listings. Both are snapshots of today's listings: names delisted before
the download are absent, so any history built on this universe is survivor-only.
Kept: common stock / ordinary shares / ADS. Dropped: ETFs, test issues, warrants, units,
rights, preferreds, notes, and symbols with class suffixes Yahoo spells differently.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.request

from ..provenance import RAW, rel, sha256_bytes, utc_stamp, write_manifest

URLS = {
    "nasdaqlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "otherlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
EXCLUDE = re.compile(r"\b(warrants?|units?|rights?|preferred|depositary shares? representing|notes? due|"
                     r"debentures?|trust preferred|% |acquisition corp)\b", re.I)


def fetch() -> tuple[list[str], str]:
    out_dir = RAW / "us_universe" / utc_stamp().replace(":", "").replace("-", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    records, tickers = [], set()
    for name, url in URLS.items():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research harness)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
        path = out_dir / f"{name}.txt"
        path.write_bytes(body)
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8", "replace")), delimiter="|"))
        rows = [r for r in rows if not (r.get("Symbol") or r.get("ACT Symbol") or "").startswith("File Creation")]
        kept = 0
        for r in rows:
            sym = (r.get("Symbol") or r.get("ACT Symbol") or "").strip()
            if not sym or r.get("ETF") == "Y" or r.get("Test Issue") == "Y" or not re.fullmatch(r"[A-Z]{1,5}", sym):
                continue
            if EXCLUDE.search(r.get("Security Name", "")):
                continue
            tickers.add(sym)
            kept += 1
        records.append({"file": name, "path": rel(path), "source_url": url, "downloaded_at": utc_stamp(),
                        "bytes": len(body), "sha256": sha256_bytes(body), "rows": len(rows), "kept": kept})
    header = {"source": "nasdaqtrader_symdir", "description": "US exchange listings snapshot (survivor-only)",
              "kept_common_stocks": len(tickers)}
    manifest = write_manifest(f"us_universe-{utc_stamp().replace(':', '').replace('-', '')}.jsonl", header, records)
    return sorted(tickers), manifest.name


def parse_dir(raw_dir) -> list[str]:
    """The same filter as fetch(), applied to an already downloaded snapshot."""
    from pathlib import Path

    tickers = set()
    for name in URLS:
        text = (Path(raw_dir) / f"{name}.txt").read_text(encoding="utf-8", errors="replace")
        for r in csv.DictReader(io.StringIO(text), delimiter="|"):
            sym = (r.get("Symbol") or r.get("ACT Symbol") or "").strip()
            if sym.startswith("File Creation") or not sym or r.get("ETF") == "Y" or r.get("Test Issue") == "Y":
                continue
            if not re.fullmatch(r"[A-Z]{1,5}", sym) or EXCLUDE.search(r.get("Security Name", "")):
                continue
            tickers.add(sym)
    return sorted(tickers)

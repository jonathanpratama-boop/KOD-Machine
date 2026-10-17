"""E10 step 1: fetch every Item 2.02 earnings-release filing for the screened US panel issuers (no price is read
beyond the liquidity screen fixed in FEASIBILITY_SPEC.md: median close and median traded value).

A. Ticker -> CIK (SEC company_tickers.json); submissions JSON plus chunk files overlapping 2019-10-01..2022-11-30,
   cached by idxsig.us_actions.SecClient under data/raw/sec/<stamp>/.
B. For every 8-K / 8-K/A with item 2.02 accepted in that window: the full submission text (<accession>.txt). Only the
   header acceptance time and the EX-99 exhibit texts are kept, gzipped, under data/raw/sec_e10/<stamp>/; the sha256
   and size of every raw response go to data/manifests/sec_e10-<stamp>.jsonl.

The User-Agent declares the owner's contact from the environment variable KOD_SEC_CONTACT; it is never written to a
file. Resumable: rerun with the same --stamp and finished filings are skipped.

Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/E10/collect.py --stamp <YYYYMMDDTHHMMSSZ>
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import catalyst, guidance  # noqa: E402
from idxsig.us_actions import SecClient, cik_map  # noqa: E402

E10 = ROOT / "research" / "E10"
PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
SCREEN = ("2020-07-01", "2022-12-30")
SPAN = ("2019-10-01", "2022-11-30")
MIN_PRICE, MIN_VALUE = 2.0, 250_000.0


def screened_tickers() -> list[str]:
    p = pd.read_csv(PANEL, usecols=["date", "ticker", "close", "value"], dtype={"ticker": str},
                    keep_default_na=False, na_values=[""])
    p = p[(p.date >= SCREEN[0]) & (p.date <= SCREEN[1])]
    g = p.groupby("ticker").agg(px=("close", "median"), val=("value", "median"))
    return sorted(g.index[(g.px >= MIN_PRICE) & (g.val >= MIN_VALUE)])


class Fetcher:
    """Polite raw fetch (at most ~8 requests a second across threads); keeps nothing but what the caller saves."""

    def __init__(self, agent: str, interval: float = 0.125):
        self.agent, self.interval, self.last, self.lock = agent, interval, 0.0, threading.Lock()

    def get(self, url: str) -> tuple[int, bytes]:
        status, body = 0, b""
        for attempt in range(5):
            with self.lock:
                wait = self.interval - (time.monotonic() - self.last)
                if wait > 0:
                    time.sleep(wait)
                self.last = time.monotonic()
            req = urllib.request.Request(url, headers={"User-Agent": self.agent, "Accept-Encoding": "identity"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return resp.status, resp.read()
            except urllib.error.HTTPError as exc:
                status, body = exc.code, exc.read()
                if exc.code not in (429, 500, 502, 503, 504):
                    return status, body
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                status, body = 0, b""
            time.sleep(2 * 2 ** attempt)
        return status, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)")
    agent = f"KOD-Machine research {contact}"
    stamp = args.stamp
    client = SecClient(agent, ROOT / "data" / "raw" / "sec" / stamp)
    client.min_interval = 0.125
    out_dir = ROOT / "data" / "raw" / "sec_e10" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = ROOT / "data" / "manifests" / f"sec_e10-{stamp}.jsonl"

    tickers = screened_tickers()
    cmap = cik_map(client)
    issuers = [(t, cmap.get(t.upper().replace(".", "-"))) for t in tickers]
    mapped = [(t, c) for t, c in issuers if c]
    print(f"screened {len(tickers)} tickers, {len(mapped)} with a CIK", flush=True)

    def filings_of(item):
        t, cik = item
        url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        status, main_body = client.get(url)
        if status != 200:
            return t, cik, None
        chunks = []
        for name in catalyst.chunk_names(main_body, *SPAN):
            s, b = client.get(f"https://data.sec.gov/submissions/{name}")
            if s == 200:
                chunks.append(b)
        return t, cik, catalyst.parse_submissions(main_body, chunks)

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for t, cik, df in pool.map(filings_of, mapped):
            done += 1
            if done % 250 == 0:
                print(f"submissions {done}/{len(mapped)}", flush=True)
            if df is None:
                continue
            f = df[df.form.isin(["8-K", "8-K/A"]) & df["items"].str.contains(r"\b2\.02\b")]
            f = f[(f.filingDate >= SPAN[0]) & (f.filingDate <= SPAN[1])]
            for r in f.itertuples():
                rows.append({"ticker": t, "cik": cik, "accession": r.accessionNumber, "form": r.form,
                             "filing_date": r.filingDate, "acceptance_json": r.acceptanceDateTime})
    filings = pd.DataFrame(rows).drop_duplicates(["cik", "accession"])
    filings.to_csv(E10 / "filings.csv", index=False)
    print(f"Item 2.02 filings: {len(filings)} from {filings.cik.nunique()} issuers", flush=True)

    fetch = Fetcher(agent)
    lock = threading.Lock()
    todo = [r for r in filings.itertuples() if not (out_dir / f"{r.accession}.json.gz").exists()]
    print(f"to fetch: {len(todo)}", flush=True)

    def one(r):
        acc_nodash = r.accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{r.cik}/{acc_nodash}/{r.accession}.txt"
        status, raw = fetch.get(url)
        rec = {"accession": r.accession, "cik": int(r.cik), "ticker": r.ticker, "url": url, "http_status": status,
               "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
               "downloaded_at": datetime.now(timezone.utc).isoformat()}
        if status == 200:
            blob = {"accession": r.accession, "cik": int(r.cik), "ticker": r.ticker, "form": r.form,
                    "filing_date": r.filing_date, "acceptance_json": r.acceptance_json,
                    "acceptance_header": guidance.acceptance(raw), "texts": guidance.exhibit_texts(raw)}
            path = out_dir / f"{r.accession}.json.gz"
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(gzip.compress(json.dumps(blob).encode()))
            tmp.replace(path)
            rec["path"] = str(path.relative_to(ROOT))
        with lock:
            with manifest.open("a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
        return status

    done, bad = 0, 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for status in pool.map(one, todo):
            done += 1
            bad += status != 200
            if done % 500 == 0:
                print(f"filings {done}/{len(todo)} (non-200: {bad})", flush=True)
    print(f"done: {done} fetched, {bad} non-200", flush=True)
    sub_manifest = ROOT / "data" / "manifests" / f"sec_e10_submissions-{stamp}.jsonl"
    with sub_manifest.open("a") as fh:
        for rec in client.records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

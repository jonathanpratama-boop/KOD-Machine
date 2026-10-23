"""Bounded SEC-only fetching and normalization; never imports a trading client."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import threading
import time
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from kod import earnings
from kod.hashing import fmt_ts, parse_ts, utc_now

ALLOWED_HOSTS = frozenset({"www.sec.gov", "sec.gov", "data.sec.gov"})
MAX_BYTES = 12 * 1024 * 1024
_rate_lock = threading.Lock()
_last_start = 0.0


SUBMISSIONS_DATE_BASIS = ("SEC filing date only (submissions feed). Its acceptanceDateTime is not used: it runs hours late against "
                         "filings' own headers. Import the exhibit to read the exact acceptance time.")


class SourceUnavailable(ValueError):
    """A failed/not-configured source, not a successfully empty feed."""


def validate_url(url: str, *, check_dns: bool = True) -> str:
    try:
        p = urlsplit(url)
        valid = (p.scheme == "https" and p.hostname in ALLOWED_HOSTS
                 and p.port in (None, 443) and not p.username and not p.password
                 and not p.query and not p.fragment and not earnings.has_dot_segments(p.path))
    except ValueError:
        valid = False
    if not valid:
        raise SourceUnavailable("Use a direct HTTPS SEC URL without credentials, query, fragment or '.'/'..' path segments; other sources can be uploaded locally.")
    if check_dns:
        try:
            addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise SourceUnavailable("SEC host could not be resolved; use a local source or retry later.") from exc
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise SourceUnavailable("SEC URL resolved to a non-public network destination.")
    return url


class SecClient:
    """One conservative host limiter and bounded stream; optional injected test transport."""

    def __init__(self, contact=None, offline=False, transport=None):
        self.contact = contact or os.environ.get("KOD_SEC_CONTACT", "").strip()
        self.offline = offline
        self.transport = transport
        self.last_mapping_raw = None
        self.last_mapping_observed_at = None

    def get(self, url: str) -> bytes:
        global _last_start
        if self.offline:
            raise SourceUnavailable("Offline mode: network refresh is disabled.")
        if not self.contact or "@" not in self.contact or "\r" in self.contact or "\n" in self.contact:
            raise SourceUnavailable("SEC is not configured: set KOD_SEC_CONTACT to your real contact email; it is never saved.")
        validate_url(url, check_dns=self.transport is None)
        import httpx
        headers = {"User-Agent": "KOD-Workstation/0.1 " + self.contact,
                   "Accept-Encoding": "gzip, deflate"}
        last_status = None
        with httpx.Client(transport=self.transport, timeout=httpx.Timeout(20, connect=8),
                          follow_redirects=False, headers=headers, trust_env=self.transport is None) as client:
            current = url
            redirects = 0
            for attempt in range(4):
                validate_url(current, check_dns=self.transport is None)
                with _rate_lock:
                    wait = max(0.0, 0.5 - (time.monotonic() - _last_start))
                    if wait:
                        time.sleep(wait)
                    _last_start = time.monotonic()
                try:
                    with client.stream("GET", current) as response:
                        last_status = response.status_code
                        if last_status in (301, 302, 303, 307, 308):
                            redirects += 1
                            if redirects > 2 or not response.headers.get("location"):
                                raise SourceUnavailable("SEC redirect limit reached.")
                            current = validate_url(urljoin(current, response.headers["location"]),
                                                   check_dns=self.transport is None)
                            continue
                        if last_status in (429, 500, 502, 503, 504) and attempt < 3:
                            delay = response.headers.get("retry-after", "")
                            delay = min(float(delay), 10.0) if re.fullmatch(r"\d+(\.\d+)?", delay) else 0.5 * (2 ** attempt)
                            time.sleep(delay)
                            continue
                        if last_status != 200:
                            raise SourceUnavailable(f"SEC returned HTTP {last_status}; no empty-success result was recorded.")
                        length = response.headers.get("content-length", "")
                        if length.isdigit() and int(length) > MAX_BYTES:
                            raise SourceUnavailable("SEC response exceeds the 12 MiB limit; upload a bounded document instead.")
                        data = bytearray()
                        for chunk in response.iter_bytes():
                            data.extend(chunk)
                            if len(data) > MAX_BYTES:
                                raise SourceUnavailable("SEC response exceeds the 12 MiB limit.")
                        return bytes(data)
                except SourceUnavailable:
                    raise
                except httpx.HTTPError as exc:
                    if attempt == 3:
                        raise SourceUnavailable("SEC network request failed; cached research remains available.") from exc
                    time.sleep(0.5 * (2 ** attempt))
        raise SourceUnavailable(f"SEC request did not complete (last HTTP {last_status}).")

    def resolve(self, ticker: str) -> dict:
        symbol = ticker.strip().upper()
        if not re.fullmatch(r"[A-Z0-9.^-]{1,20}", symbol):
            raise SourceUnavailable("Enter a plain US ticker.")
        raw = self.get("https://www.sec.gov/files/company_tickers_exchange.json")
        self.last_mapping_raw = raw
        self.last_mapping_observed_at = utc_now()
        try:
            data = json.loads(raw)
            fields = data["fields"]
            rows = [dict(zip(fields, r)) for r in data["data"]]
            hits = [r for r in rows if str(r.get("ticker", "")).upper() == symbol]
            if len(hits) != 1:
                raise SourceUnavailable("Ticker mapping is missing or ambiguous; add an explicit company and CIK.")
            r = hits[0]
            exchange = str(r.get("exchange", "")).upper()
            return {"ticker": symbol, "name": r["name"], "cik": str(r["cik"]).zfill(10),
                    "venue": {"NASDAQ": "XNAS", "NYSE": "XNYS"}.get(exchange, exchange or "UNSPECIFIED"),
                    "currency": "USD", "association": "verified_from_filing_metadata"}
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, SourceUnavailable):
                raise
            raise SourceUnavailable("SEC ticker response has an unsupported schema.") from exc


def acceptance_time(value: str | None) -> str | None:
    """Respect explicit zones; naive SEC acceptance values use New York clock."""
    if not value or not isinstance(value, str):
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=ZoneInfo("America/New_York"))
        return fmt_ts(moment)
    except ValueError:
        return None


def normalize_submissions(raw: bytes, expected_cik: str) -> list[dict]:
    try:
        data = json.loads(raw, parse_float=Decimal)
        if int(data["cik"]) != int(expected_cik):
            raise SourceUnavailable("SEC response CIK differs from the selected company; nothing was imported.")
        recent = data["filings"]["recent"]
        accessions = recent["accessionNumber"]
        if not isinstance(accessions, list):
            raise TypeError
        required = ("form", "primaryDocument", "filingDate")
        if any(len(recent[k]) != len(accessions) for k in required):
            raise SourceUnavailable("SEC filing columns have different lengths; refresh was not treated as empty.")
        out = []
        for i, accession in enumerate(accessions):
            form = recent["form"][i]
            if form not in {"8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A"}:
                continue
            filename = recent["primaryDocument"][i]
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession) or not re.fullmatch(r"[A-Za-z0-9_.-]+", filename):
                raise SourceUnavailable("SEC filing identity has an unsupported format.")
            accepted = recent.get("acceptanceDateTime", [])
            value = accepted[i] if i < len(accepted) else None
            filing_date = recent["filingDate"][i]
            if not isinstance(filing_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", filing_date):
                raise SourceUnavailable("SEC filing date has an unsupported format.")
            cik = str(int(expected_cik))
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{filename}"
            # The feed's acceptanceDateTime is not used as a publication time. On the eight
            # 2024 earnings filings in examples/earnings_demo it ran 4-5 hours later than each
            # filing's own SGML header (the New York offset applied twice), which moves
            # after-close filings to the next day. The filing date is kept at date precision;
            # importing the exhibit fetches the header for an exact acceptance time.
            out.append({"external_id": accession, "form": form, "title": f"{form} · {filing_date}",
                        "source_url": url, "published_at": filing_date,
                        "published_basis": SUBMISSIONS_DATE_BASIS,
                        "metadata": {"filing_date": recent["filingDate"][i], "primary_document": filename,
                                     "acceptance_raw": value, "acceptance_raw_used": False, "association": "verified_from_filing_metadata",
                                     "items": recent.get("items", [])[i] if i < len(recent.get("items", [])) else "",
                                     "coverage": "SEC recent submissions only; older-history chunks not fetched"}})
        return out
    except SourceUnavailable:
        raise
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise SourceUnavailable("SEC submissions response is malformed or unsupported; retained as a failed refresh.") from exc


@contextmanager
def _refresh_lock(root: Path, security_id: str):
    """Advisory process lock: CLI and web cannot refresh the same company together."""
    import fcntl
    folder = Path(root) / "locks"
    folder.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(security_id.encode()).hexdigest()
    with (folder / (name + ".lock")).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SourceUnavailable("A refresh for this company is already running.") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def refresh_security(service, security_id: str, client=None) -> dict:
    store = service.store
    security = store.get_security(security_id)
    if not security.get("cik"):
        return store.record_job("sec", security_id, "not_configured", "Add the issuer's explicit CIK before SEC refresh.")
    started = service.clock()
    try:
        with _refresh_lock(store.root, security_id):
            raw = (client or SecClient()).get(f"https://data.sec.gov/submissions/CIK{str(security['cik']).zfill(10)}.json")
            events = normalize_submissions(raw, security["cik"])
            now = service.clock()
            doc = store.save_document(security_id, raw, "submissions.json",
                                      f"https://data.sec.gov/submissions/CIK{str(security['cik']).zfill(10)}.json",
                                      observed_at=now, role="metadata", provider="sec", external_id="submissions",
                                      association="verified_from_filing_metadata", extraction_status="metadata",
                                      metadata={"coverage": "recent submissions only"})
            before = {e["external_id"] for e in store.events(security_id)}
            for event in events:
                store.save_event(security_id, observed_at=now, document_id=doc["id"], **event)
            count = len({e["external_id"] for e in events} - before)
            return store.record_job("sec", security_id, "success",
                                    f"Checked recent SEC filings; {count} new supported filing(s). Older history is not included.",
                                    started_at=started, finished_at=now, new_count=count)
    except (SourceUnavailable, OSError, ValueError) as exc:
        return store.record_job("sec", security_id, "failed", str(exc),
                                started_at=started, finished_at=service.clock())


def import_url(service, security_id: str, url: str, role="current", published_at=None, client=None) -> dict:
    client = client or SecClient()
    if client.offline:
        raise SourceUnavailable("Offline mode: network import is disabled.")
    validate_url(url, check_dns=client.transport is None)
    security = service.store.get_security(security_id)
    match = re.search(r"/Archives/edgar/data/(\d+)/", urlsplit(url).path, re.I)
    if match and security.get("cik") and int(match.group(1)) != int(security["cik"]):
        raise SourceUnavailable("The SEC document CIK differs from the selected company.")
    raw = client.get(url)
    headers = None
    hurl = earnings.sec_headers_url(url)
    if hurl and not published_at:
        try:
            headers = client.get(hurl)
        except SourceUnavailable:
            # The source is still useful; publication time remains explicitly unknown.
            headers = None
    return service.ingest(security_id, raw, Path(urlsplit(url).path).name, url,
                          published_at=published_at, sec_headers=headers, role=role, provider="sec",
                          association="user_asserted",
                          external_id=urlsplit(url).path)


def refresh_companyfacts(service, security_id: str, client=None) -> dict:
    """Explicit, bounded collection of one company's SEC companyfacts and submissions (two requests), under the company's refresh lock. The outcome is
    recorded as a job: success with the number of new observations, or failure with the reason (never an empty success). Returns the coverage report
    with the job's message; raises SourceUnavailable or ValueError after recording a failure."""
    client = client or SecClient()
    store = service.store
    security = store.get_security(security_id)
    started = service.clock()
    try:
        if not security.get("cik"):
            raise SourceUnavailable("This company has no CIK; resolve it from the SEC ticker list first.")
        cik = int(security["cik"])
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        subs_url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        with _refresh_lock(store.root, security_id):
            raw = client.get(facts_url)
            subs = client.get(subs_url)
            # import_companyfacts records the success job itself (one job per refresh).
            coverage = service.import_companyfacts(security_id, raw, facts_url, observed_at=service.clock(), submissions=subs, submissions_url=subs_url)
        message = (f"Recorded {coverage['added']} new filed-history observation(s) from SEC companyfacts ({coverage['observations']} in the response). "
                   "Whole-entity standard-taxonomy facts only.")
        return {**coverage, "message": message}
    except (SourceUnavailable, OSError, ValueError) as exc:
        store.record_job("sec-companyfacts", security_id, "failed", str(exc), started_at=started, finished_at=service.clock())
        if isinstance(exc, OSError):
            raise SourceUnavailable(str(exc)) from exc
        raise
    except Exception as exc:              # a response of an unexpected shape: a failed job with the error type, never a traceback or an empty success
        message = (f"the SEC companyfacts response could not be read ({type(exc).__name__}); the downloaded bytes are kept as evidence but no "
                   "financial observation was recorded from them")
        store.record_job("sec-companyfacts", security_id, "failed", message, started_at=started, finished_at=service.clock())
        raise SourceUnavailable(message) from exc

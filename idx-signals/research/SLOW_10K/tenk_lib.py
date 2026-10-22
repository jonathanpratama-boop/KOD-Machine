"""SLOW_10K shared code (see PROTOCOL.md and ADDENDUM_1.md): a rate limiter shared by processes, a non-caching EDGAR download, the text feature (term
frequencies and cosine similarity of a 10-K with last year's), the choice of the previous 10-K, and the causal buckets."""
import gzip
import html
import math
import multiprocessing as mp
import re
import time
import urllib.error
import urllib.request
from collections import Counter

import numpy as np
import pandas as pd

MIN_GAP, MAX_GAP, TRAILING_DAYS, MIN_TRAILING = 300, 450, 365, 200


class Limiter:
    """At most one request start per `interval` seconds across threads and processes (CLOCK_MONOTONIC is system-wide on Linux)."""

    def __init__(self, interval: float = 0.21):
        self.interval = interval
        self._lock = mp.Lock()
        self._next = mp.Value("d", 0.0, lock=False)

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next.value)
            self._next.value = start + self.interval
        if start > now:
            time.sleep(start - now)


def get(url: str, user_agent: str, limiter: Limiter, retries: int = 4, max_bytes: int = 60_000_000) -> tuple[int, bytes]:
    """(status, body); nothing is cached. gzip is requested and undone here."""
    status, body = 0, b""
    for attempt in range(retries):
        limiter.wait()
        req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read(max_bytes + 1)
                status = resp.status
                body = gzip.decompress(raw) if resp.headers.get("Content-Encoding") == "gzip" else raw
            if len(body) > max_bytes:
                return 413, b""
            return status, body
        except urllib.error.HTTPError as exc:
            status, body = exc.code, b""
            if exc.code not in (429, 500, 502, 503, 504):
                return status, body
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            status, body = 0, b""
        time.sleep(2 * 2 ** attempt)
    return status, body


def _strip_blocks(raw: bytes, open_tag: bytes, close_tag: bytes) -> bytes:
    """Remove every <open_tag ...> ... </close_tag> block (case-insensitive)."""
    low, out, pos = raw.lower(), [], 0
    while True:
        i = low.find(open_tag, pos)
        if i < 0:
            out.append(raw[pos:])
            break
        j = low.find(close_tag, i)
        out.append(raw[pos:i])
        if j < 0:
            break
        pos = j + len(close_tag)
    return b" ".join(out)


TAGS = re.compile(rb"<[^>]+>")
WORDS = re.compile(r"[a-z]{3,}")


def tf_from_html(raw: bytes) -> Counter:
    """Term frequencies of a filing: hidden inline-XBRL header, scripts and styles removed, tags stripped, entities unescaped, lower-cased,
    alphabetic tokens of three or more letters."""
    raw = _strip_blocks(raw, b"<ix:header", b"</ix:header>")
    raw = _strip_blocks(raw, b"<script", b"</script>")
    raw = _strip_blocks(raw, b"<style", b"</style>")
    text = html.unescape(TAGS.sub(b" ", raw).decode("utf-8", "ignore")).lower()
    return Counter(WORDS.findall(text))


def norm(tf: Counter) -> float:
    return math.sqrt(sum(v * v for v in tf.values()))


def cosine(a: Counter, b: Counter, na: float | None = None, nb: float | None = None) -> float:
    na, nb = na if na is not None else norm(a), nb if nb is not None else norm(b)
    if not na or not nb:
        return float("nan")
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return sum(v * big.get(k, 0) for k, v in small.items()) / (na * nb)


def choose_previous(filing_date: pd.Timestamp, earlier: list[dict]) -> dict | None:
    """The issuer's earlier 10-K with filing date 300-450 days before `filing_date`, the closest to 365 days if several."""
    best, best_key = None, None
    for e in earlier:
        gap = (filing_date - e["filing_date"]).days
        if MIN_GAP <= gap <= MAX_GAP and (best is None or abs(gap - 365) < best_key):
            best, best_key = e, abs(gap - 365)
    return best


def buckets(f: pd.DataFrame) -> pd.Series:
    """'Q1' (changer), 'Q5' (stable), 'MID' or '' (not classified) for each filing with a similarity, by comparison with the similarities of filings whose
    filing date is strictly earlier and at most 365 days before; at least 200 such filings are needed. `f` needs filing_date and cosine."""
    f = f.reset_index(drop=True)
    date = f["filing_date"].to_numpy("datetime64[D]")
    sim = f["cosine"].to_numpy(float)
    ok = np.isfinite(sim)
    out = np.full(len(f), "", dtype=object)
    for i in np.flatnonzero(ok):
        window = ok & (date < date[i]) & (date >= date[i] - np.timedelta64(TRAILING_DAYS, "D"))
        if window.sum() < MIN_TRAILING:
            continue
        q20, q80 = np.percentile(sim[window], [20, 80])
        out[i] = "Q1" if sim[i] <= q20 else ("Q5" if sim[i] >= q80 else "MID")
    return pd.Series(out, index=f.index)

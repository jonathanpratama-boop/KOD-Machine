"""US split schedule: provider records, SEC corroboration, and price-unit factors.

Yahoo's daily quote arrays are split-adjusted to the day of the pull, and so is its volume
(shown against an independent provider in research/E2/repair/conventions.json). Every price
adjustment Yahoo applies is listed in the payload's events.splits, each timestamped 09:30
America/New_York on the session from which prices are in the new units. So the price a share
actually traded at on session t is

    as_traded(t) = adjusted(t) x F(t),   F(t) = product of numerator/denominator over events
                                          effective on a session strictly after t,

and as-traded volume = adjusted volume / F(t). Returns are ratios of adjusted prices and need
no factor. Later events are used only to restore the units of earlier prices (measurement),
never as information available at t.

A provider record is not proof. Each event is checked against SEC EDGAR full-text search: a
filing by the same company within [effective - 45 days, effective + 5 days] that states the
same exact ratio and effective date in a definite event statement. Nothing here infers a split from a
change in price ratios. Statuses:

  VERIFIED            a filing states the ratio and the effective session date
  RATIO_CONFIRMED     definite ratio statement without a matching effective date; NOT accepted
  MENTION_ONLY        a filing in the window mentions a split or consolidation, ratio not found
  NO_EVIDENCE         no matching filing found
  NO_CIK              the ticker is not in SEC's current ticker map
  NOT_A_SPLIT         the provider ratio is not a share split (e.g. 1281:1000, a spin-off or
                      stock-dividend price adjustment); its share-count meaning is unverified

Raw SEC responses are cached under data/raw/sec/<stamp>/ and listed in a manifest with their
hashes, like every other source.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from math import gcd
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .provenance import RAW, PKG_ROOT, read_manifest, rel, sha256_bytes, utc_stamp, write_manifest

VERSION = "us-actions-v2"
NEW_YORK = ZoneInfo("America/New_York")
ACCEPTED = ("VERIFIED",)
# SEC asks automated clients to declare a contact. This placeholder is what the research runs
# used; set IDXSIG_SEC_USER_AGENT to a real contact for routine use.
DEFAULT_USER_AGENT = "KOD research harness research@example.org"
STATUSES = ("VERIFIED", "RATIO_CONFIRMED", "MENTION_ONLY", "NO_EVIDENCE", "NO_CIK", "NOT_A_SPLIT")


def _rel(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:  # a cache outside the package (tests, scratch)
        return str(path)


# ------------------------------------------------------------------------------ provider events
def classify_ratio(numerator: float, denominator: float) -> str:
    """A share split moves holdings by a small whole-number ratio (1:10, 3:2, 20:1, 1:250).
    Yahoo also lists price adjustments such as 1281:1000 (spin-offs, stock dividends)."""
    if (
        numerator <= 0
        or denominator <= 0
        or numerator != int(numerator)
        or denominator != int(denominator)
    ):
        return "NOT_A_SPLIT"
    n, d = int(numerator), int(denominator)
    g = gcd(n, d)
    n, d = n // g, d // g
    return "SPLIT" if (min(n, d) == 1 or max(n, d) <= 20) else "NOT_A_SPLIT"


def yahoo_events(raw_manifest: Path, market: str = "US") -> pd.DataFrame:
    """Every split record in a Yahoo pull, with the payload it came from."""
    zone = {"US": NEW_YORK, "IDX": ZoneInfo("Asia/Jakarta")}[market]
    _, records = read_manifest(raw_manifest)
    rows = []
    for rec in records:
        if rec.get("http_status") != 200:
            continue
        payload = json.loads((PKG_ROOT / rec["path"]).read_text(encoding="utf-8"))["chart"][
            "result"
        ][0]
        for ev in ((payload.get("events") or {}).get("splits") or {}).values():
            stamp = int(ev["date"])
            local = datetime.fromtimestamp(stamp, timezone.utc).astimezone(zone)
            rows.append(
                {
                    "ticker": rec["ticker"],
                    "effective_session": local.date().isoformat(),
                    "local_time": local.strftime("%H:%M"),
                    "numerator": float(ev["numerator"]),
                    "denominator": float(ev["denominator"]),
                    "provider_ratio": ev.get("splitRatio"),
                    "event_timestamp": stamp,
                    "payload": rec["path"],
                    "payload_sha256": rec["sha256"],
                }
            )
    cols = [
        "ticker",
        "effective_session",
        "local_time",
        "numerator",
        "denominator",
        "provider_ratio",
        "event_timestamp",
        "payload",
        "payload_sha256",
    ]
    out = (
        pd.DataFrame(rows, columns=cols)
        .sort_values(["ticker", "effective_session"])
        .reset_index(drop=True)
    )
    out["kind"] = [classify_ratio(n, d) for n, d in zip(out["numerator"], out["denominator"])]
    return out


def unit_factors(dates: np.ndarray, events: pd.DataFrame) -> np.ndarray:
    """F(t) for each session in `dates` (datetime64[D]) from one name's events."""
    f = np.ones(len(dates))
    for ev in events.itertuples(index=False):
        eff = np.datetime64(ev.effective_session, "D")
        f[dates < eff] *= ev.numerator / ev.denominator
    return f


# ------------------------------------------------------------------------------ SEC evidence
WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty-five": 25,
    "thirty": 30,
    "thirty-five": 35,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "seventy-five": 75,
    "eighty": 80,
    "ninety": 90,
    "one hundred": 100,
    "hundred": 100,
    "two hundred": 200,
    "two hundred fifty": 250,
    "three hundred": 300,
    "five hundred": 500,
    "one thousand": 1000,
}
NUM = r"(\d+(?:,\d{3})*(?:\.\d+)?)"
RATIO_PATTERNS = (
    # 1-for-10, 1 for 10, 20-for-1 (new-for-old)
    (re.compile(NUM + r"\s*[-–]?\s*for\s*[-–]?\s*" + NUM, re.I), False),
    # 1:10 (new:old as written in "1:10 reverse split")
    (
        re.compile(
            NUM
            + r"\s*:\s*"
            + NUM
            + r"(?=\s*(?:reverse|forward|stock|share|split|consolidation|ratio|basis))",
            re.I,
        ),
        False,
    ),
    # one new share for every ten shares / 1 post-consolidation share for every 10 pre-consolidation shares
    (
        re.compile(
            NUM
            + r"\s+(?:\S+\s+){0,4}?shares?\s+(?:of\s+\w+\s+stock\s+)?for\s+(?:each|every)\s+"
            + NUM,
            re.I,
        ),
        False,
    ),
    # ADS ratio change: from one ADS representing X shares to one ADS representing Y shares (new:old = X:Y)
    (
        re.compile(
            r"ADSs?\s+(?:\S+\s+){0,3}?represent(?:ing|s)?\s+"
            + NUM
            + r"\s+(?:\S+\s+){0,8}?(?:to|into)\s+"
            r"(?:\S+\s+){0,4}?ADSs?\s+(?:\S+\s+){0,3}?represent(?:ing|s)?\s+" + NUM,
            re.I,
        ),
        False,
    ),
    # every ten shares ... combined/converted/reclassified into one share (old ... into new)
    (
        re.compile(
            r"(?:each|every)\s+"
            + NUM
            + r"\s+(?:\S+\s+){0,6}?(?:shares?|ADSs?)\s+(?:\S+\s+){0,14}?into\s+"
            + NUM,
            re.I,
        ),
        True,
    ),
)
SPLIT_WORDS = re.compile(
    r"reverse\s+(?:stock\s+)?split|share\s+consolidation|stock\s+split|forward\s+split|"
    r"ADS\s+ratio|ratio\s+of\s+(?:the\s+)?ADSs?|"
    r"reverse\s+share\s+split|consolidation\s+of\s+(?:the\s+)?(?:issued|outstanding|common)",
    re.I,
)
REVERSE_WORDS = re.compile(r"reverse|consolidat|ADS\s+ratio|ratio\s+of\s+(?:the\s+)?ADSs?", re.I)


def _normalise_numbers(text: str) -> str:
    text = re.sub(r"\s*\(\s*\d+(?:,\d{3})*(?:\.\d+)?\s*\)", "", text)  # "one (1)" -> "one"
    for word in sorted(WORDS, key=len, reverse=True):  # longest first
        text = re.sub(rf"\b{word}\b", str(WORDS[word]), text, flags=re.I)
    return text


def text_of(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t.replace("\xa0", " "))


def ratios_in(text: str) -> set[tuple[int, int]]:
    """(new, old) share pairs stated in a filing, reduced."""
    norm = _normalise_numbers(text)
    out = set()
    for pattern, old_first in RATIO_PATTERNS:
        for m in pattern.finditer(norm):
            try:
                a, b = (float(x.replace(",", "")) for x in m.groups())
            except ValueError:
                continue
            if old_first:
                a, b = b, a
            if a <= 0 or b <= 0 or a != int(a) or b != int(b) or max(a, b) > 100_000 or a == b:
                continue  # "1-for-1" (e.g. a prospectus' share-for-share exchange) is not a split ratio
            g = gcd(int(a), int(b))
            out.add((int(a) // g, int(b) // g))
    return out


def date_strings(day: date) -> list[str]:
    m = day.strftime("%B")
    return [
        f"{m} {day.day}, {day.year}",
        f"{m} {day.day} , {day.year}",
        f"{m} {day.day}th, {day.year}",
        f"{m} {day.day}st, {day.year}",
        f"{m} {day.day}nd, {day.year}",
        f"{m} {day.day}rd, {day.year}",
        f"{day.strftime('%b')}. {day.day}, {day.year}",
        f"{day.strftime('%b')} {day.day}, {day.year}",
        f"{day.day} {m} {day.year}",
        day.isoformat(),
        f"{day.month}/{day.day}/{day.year}",
        f"{day.month:02d}/{day.day:02d}/{day.year}",
    ]


# Deliberately conservative: unsupported wording needs review, never an inferred approval.
# A whole filing may mention several historical/proposed splits and unrelated dates.
AMBIGUOUS = re.compile(
    r"\b(?:propos\w*|rang\w*|between|up to|may(?!\s+\d)|might|could|if|unless|subject to|"
    r"not|never|no longer|cancel\w*|abandon\w*|rescind\w*|postpon\w*|"
    r"authoriz\w*|discretion|hypothetical|illustrat\w*|would)\b",
    re.I,
)
IMPLEMENTED = re.compile(
    r"\b(?:effective(?:\s+(?:at|on|as of|from))?|effected|implemented|completed|"
    r"consummated|began trading|commenced trading|will begin trading|"
    r"will commence trading)\b",
    re.I,
)
CONTINUATION = re.compile(
    r"^(?:the (?:company['’]s )?(?:common stock|shares|stock|reverse (?:stock )?split|"
    r"stock split|split)|trading|it)\b",
    re.I,
)


def split_statements(text: str) -> list[str]:
    """Single event statements, optionally followed by a directly related trading sentence.

    Sentence-local matching sacrifices recall to avoid stitching a proposal, a historical
    ratio, and an unrelated date together. Long/table-like passages need manual review.
    """
    # Do not cut a date off at "5:00 p.m. Eastern Time on ..." or a company suffix.
    protected = re.sub(
        r"\b(?:a\.m\.|p\.m\.|U\.S\.|Inc\.|Corp\.|Co\.|Ltd\.|"
        r"Jan\.|Feb\.|Mar\.|Apr\.|Jun\.|Jul\.|Aug\.|Sep\.|Sept\.|Oct\.|Nov\.|Dec\.)",
        lambda m: m.group().replace(".", "\u2024"),
        text,
        flags=re.I,
    )
    sentences = [s.replace("\u2024", ".") for s in re.split(r"(?<=[.!?;])\s+", protected)]
    out = []
    for i, sentence in enumerate(sentences):
        if not SPLIT_WORDS.search(sentence) or not ratios_in(sentence):
            continue
        context = sentence
        for following in sentences[i + 1 : i + 3]:
            if not CONTINUATION.search(following):
                break
            context += " " + following
        if len(context) > 1600 or AMBIGUOUS.search(context) or not IMPLEMENTED.search(context):
            continue
        if len(ratios_in(context)) != 1:
            continue
        out.append(context)
    return out


def _effective_date_in(text: str, effective: date) -> bool:
    # Require the date next to implementation/trading language, not a filing/meeting date.
    day = "(?:" + "|".join(re.escape(s) for s in date_strings(effective)) + ")"
    weekday = r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?"
    clock = (
        r"(?:at\s+(?:(?:the\s+)?(?:open|opening)(?:\s+of\s+(?:trading|business))?|"
        r"\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)(?:\s+(?:Eastern|New York|ET|EST|EDT)"
        r"(?:\s+(?:Standard|Daylight))?(?:\s+Time)?)?)\s+)?"
    )
    effective_on = r"\beffective\s+" + clock + r"(?:(?:on|as of|from)\s+)?" + weekday
    trading = r"\b(?:began|commenced|will begin|will commence) trading"
    trading_on = trading + r"[^!?;]{0,140}?\bon\s+" + weekday
    # A trading-start sentence resolves an after-close legal date to the first new-units
    # session. If its date cannot be parsed, leave the event unverified.
    if re.search(trading, text, re.I):
        return bool(re.search(trading_on + day, text, re.I))
    # An explicitly after-close event alone cannot establish the first trading session.
    if re.search(r"\b(?:after (?:the )?(?:market )?close|p\.?m\.?)\b", text, re.I):
        return False
    return bool(re.search(effective_on + day, text, re.I))


def judge(text: str, numerator: float, denominator: float, effective: date) -> dict:
    """Confirm only an exact, unambiguous event; retain the matched excerpt for audit.

    RATIO_CONFIRMED is diagnostic only. Acceptance requires the effective date in the
    same event statement. Never invert a written ratio to agree with the provider.
    """
    n, d = int(numerator), int(denominator)
    if n <= 0 or d <= 0 or n != numerator or d != denominator:
        raise ValueError("split ratio must contain positive integers")
    g = gcd(n, d)
    want = (n // g, d // g)
    pairs = ratios_in(text)
    statements = []
    for statement in split_statements(text) if want in pairs else []:
        if ratios_in(statement) != {want}:
            continue
        reverse_words = bool(REVERSE_WORDS.search(statement))
        if (want[0] < want[1]) != reverse_words:
            continue
        statements.append(statement)
    dated = [s for s in statements if _effective_date_in(s, effective)]
    return {
        "mentions_split": bool(SPLIT_WORDS.search(text)),
        "ratio_ok": bool(statements),
        "date_ok": bool(dated),
        "pairs_found": sorted(pairs)[:12],
        "matched_statements": (dated or statements)[:3],
        "verifier_version": VERSION,
    }


@dataclass
class SecClient:
    """Polite EDGAR access: a declared User-Agent, at most ~5 requests a second, every response
    cached and hashed. `offline` serves only from an existing cache directory."""

    user_agent: str
    out_dir: Path
    min_interval: float = 0.21
    offline: bool = False
    cache_misses: set[str] = field(default_factory=set)
    _last: float = 0.0
    records: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _record(self, row: dict) -> None:
        with self._lock:
            self.records.append(row)

    def _wait_turn(self) -> None:
        with self._lock:  # one request start per min_interval across all threads
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def get(self, url: str) -> tuple[int, bytes]:
        key = hashlib.sha256(url.encode()).hexdigest()[:32]
        path = self.out_dir / f"{key}.bin"
        meta = self.out_dir / f"{key}.json"
        if path.exists() and meta.exists():
            info = json.loads(meta.read_text())
            body = path.read_bytes()
            self._record({**info, "path": _rel(path), "sha256": sha256_bytes(body), "cached": True})
            return info["http_status"], body
        if self.offline:
            with self._lock:
                self.cache_misses.add(url)
            return 0, b""
        status, body = 0, b""
        for attempt in range(5):
            self._wait_turn()
            req = urllib.request.Request(
                url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "identity"}
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    status, body = resp.status, resp.read()
                break
            except urllib.error.HTTPError as exc:
                status, body = exc.code, exc.read()
                if exc.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                status, body = 0, b""
            time.sleep(2 * 2**attempt)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        info = {"url": url, "http_status": status, "downloaded_at": utc_stamp()}
        meta.write_text(json.dumps(info, sort_keys=True))
        self._record({**info, "path": _rel(path), "sha256": sha256_bytes(body), "cached": False})
        return status, body


def cik_map(client: SecClient) -> dict[str, int]:
    status, body = client.get("https://www.sec.gov/files/company_tickers.json")
    if status != 200:
        raise RuntimeError(f"SEC ticker map: HTTP {status}")
    return {
        v["ticker"].upper().replace(".", "-"): int(v["cik_str"]) for v in json.loads(body).values()
    }


QUERY = (
    '"reverse stock split" OR "reverse split" OR "share consolidation" OR "stock split" OR "forward split" '
    'OR "reverse share split" OR "split-adjusted" OR "ADS ratio" OR "ratio of the ADSs"'
)


def search(client: SecClient, cik: int, start: date, end: date) -> list[dict]:
    params = {
        "q": QUERY,
        "dateRange": "custom",
        "startdt": start.isoformat(),
        "enddt": end.isoformat(),
        "ciks": f"{cik:010d}",
    }
    status, body = client.get(
        "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(params)
    )
    if status != 200:
        return []
    hits = json.loads(body).get("hits", {}).get("hits", [])
    out = []
    for h in hits:
        adsh, _, filename = h["_id"].partition(":")
        src = h.get("_source", {})
        out.append(
            {
                "accession": adsh,
                "file": filename,
                "form": src.get("form"),
                "file_date": src.get("file_date"),
                "file_type": src.get("file_type"),
                "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{filename}",
            }
        )
    return out


def _priority(hit: dict) -> tuple:
    form = (hit.get("form") or "").upper()
    ftype = (hit.get("file_type") or "").upper()
    main = 0 if form.startswith(("8-K", "6-K")) else 1
    press = 0 if ftype.startswith("EX-99") or ftype in ("8-K", "6-K") else 1
    return (main, press, hit.get("file_date") or "")


def verify_event(
    client: SecClient,
    ciks: dict,
    ticker: str,
    effective: str,
    numerator: float,
    denominator: float,
    kind: str,
    max_docs: int = 6,
    before_days: int = 45,
    after_days: int = 5,
) -> dict:
    if kind != "SPLIT":
        return {"status": "NOT_A_SPLIT", "evidence": []}
    cik = ciks.get(ticker.upper())
    if cik is None:
        return {"status": "NO_CIK", "evidence": []}
    eff = date.fromisoformat(effective)
    hits = sorted(
        search(client, cik, eff - timedelta(days=before_days), eff + timedelta(days=after_days)),
        key=_priority,
    )
    evidence, best = [], "NO_EVIDENCE"
    rank = {s: i for i, s in enumerate(STATUSES)}
    for hit in hits[:max_docs]:
        status, body = client.get(hit["url"])
        if status != 200:
            continue
        v = judge(text_of(body), numerator, denominator, eff)
        found = (
            "VERIFIED"
            if v["ratio_ok"] and v["date_ok"]
            else "RATIO_CONFIRMED"
            if v["ratio_ok"]
            else "MENTION_ONLY"
            if v["mentions_split"]
            else None
        )
        if found is None:
            continue
        evidence.append(
            {
                **{k: hit[k] for k in ("accession", "form", "file_date", "url")},
                "finding": found,
                "ratio_ok": v["ratio_ok"],
                "date_ok": v["date_ok"],
                "matched_statements": v["matched_statements"],
                "verifier_version": VERSION,
            }
        )
        if rank[found] < rank[best]:
            best = found
        if best == "VERIFIED":
            break
    return {"status": best, "cik": cik, "filings_searched": len(hits), "evidence": evidence}


def verify_schedule(
    events: pd.DataFrame,
    client: SecClient,
    log=print,
    workers: int = 4,
    max_docs: int = 6,
    before_days: int = 45,
    after_days: int = 5,
) -> pd.DataFrame:
    """Results come back in the input order whatever the thread count."""
    from concurrent.futures import ThreadPoolExecutor

    ciks = cik_map(client)
    rows = list(events.itertuples(index=False))

    def one(ev):
        res = verify_event(
            client,
            ciks,
            ev.ticker,
            ev.effective_session,
            ev.numerator,
            ev.denominator,
            ev.kind,
            max_docs,
            before_days,
            after_days,
        )
        row = {
            k: v
            for k, v in ev._asdict().items()
            if k not in ("status", "cik", "filings_searched", "evidence", "pass")
        }
        return {
            **row,
            "status": res["status"],
            "cik": res.get("cik"),
            "filings_searched": res.get("filings_searched", 0),
            "evidence": json.dumps(res["evidence"], sort_keys=True),
        }

    out = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, row in enumerate(pool.map(one, rows)):
            out.append(row)
            if (i + 1) % 100 == 0:
                log(f"sec {i + 1}/{len(rows)}")
    return pd.DataFrame(out)


SECOND_PASS = {"max_docs": 10, "before_days": 150, "after_days": 10}


def build_schedule(
    raw_manifest: Path,
    user_agent: str,
    effective_after: str,
    universe_end: str,
    cache_dir: Path | None = None,
    offline: bool = False,
    log=print,
    recheck: Path | None = None,
) -> Path:
    """Provider events for names that traded on or before `universe_end`, effective after
    `effective_after`, each checked against SEC filings. Writes a CSV and a manifest.
    recheck: an earlier schedule manifest; only approvals from this verifier version are kept; all older split
    rows are searched again with a wider window (SECOND_PASS), the pass recorded per row."""
    events = yahoo_events(raw_manifest)
    _, records = read_manifest(raw_manifest)
    listed = {
        r["ticker"] for r in records if r.get("first_date") and r["first_date"] <= universe_end
    }
    scope = events[(events["effective_session"] > effective_after) & events["ticker"].isin(listed)]
    stamp = utc_stamp().replace("-", "").replace(":", "")
    client = SecClient(user_agent, cache_dir or RAW / "sec" / stamp, offline=offline)
    if recheck is None:
        checked = verify_schedule(scope.reset_index(drop=True), client, log).assign(**{"pass": 1})
    else:
        prev_meta = json.loads(Path(recheck).read_text(encoding="utf-8"))
        prev = pd.read_csv(
            PKG_ROOT / prev_meta["schedule"],
            dtype={"ticker": str},
            keep_default_na=False,
            na_values=[""],
        )
        if (
            hashlib.sha256((PKG_ROOT / prev_meta["schedule"]).read_bytes()).hexdigest()
            != prev_meta["schedule_sha256"]
        ):
            raise RuntimeError(f"{Path(recheck).name}: schedule file changed")
        if (
            prev_meta["raw_manifest_sha256"]
            != hashlib.sha256(raw_manifest.read_bytes()).hexdigest()
            or prev_meta["effective_after"] != effective_after
            or prev_meta["universe_end"] != universe_end
        ):
            raise ValueError("recheck must use the same input manifest and scope")
        # An older parser's approvals must never survive an upgrade without re-evaluation.
        reusable = prev["status"].isin(ACCEPTED) if prev_meta.get("version") == VERSION else False
        keep = prev[reusable | (prev["kind"] != "SPLIT")].assign(**{"pass": 1})
        redo = prev[~prev.index.isin(keep.index)]
        again = verify_schedule(redo.reset_index(drop=True), client, log, **SECOND_PASS).assign(
            **{"pass": 2}
        )
        checked = pd.concat([keep, again], ignore_index=True).sort_values(
            ["ticker", "effective_session"]
        )
        checked = checked.reset_index(drop=True)
    out_dir = PKG_ROOT / "data" / "corporate_actions"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"us_splits-{stamp}.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as fh:
        checked.to_csv(fh, index=False, lineterminator="\n")
    sec_manifest = write_manifest(
        f"sec_split_evidence-{stamp}.jsonl",
        {"source": "sec_edgar", "user_agent": user_agent, "purpose": "split corroboration"},
        [r for r in {r["path"]: r for r in client.records}.values()],
    )
    meta = {
        "version": VERSION,
        "built_at": utc_stamp(),
        "raw_manifest": raw_manifest.name,
        "raw_manifest_sha256": hashlib.sha256(raw_manifest.read_bytes()).hexdigest(),
        "sec_manifest": sec_manifest.name,
        "effective_after": effective_after,
        "universe_end": universe_end,
        "schedule": rel(csv_path),
        "schedule_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "offline": offline,
        "offline_cache_misses": len(client.cache_misses),
        "events_in_scope": int(len(checked)),
        "status_counts": checked["status"].value_counts().to_dict(),
        "accepted_statuses": list(ACCEPTED),
        "provider_events_outside_scope": int(len(events) - len(scope)),
        "first_pass": {"max_docs": 6, "before_days": 45, "after_days": 5},
        "second_pass": ({**SECOND_PASS, "recheck_of": Path(recheck).name} if recheck else None),
    }
    mpath = out_dir / f"us_splits-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    log(json.dumps(meta["status_counts"]))
    return mpath


# ------------------------------------------------------------------------------ coverage
JUMP = 1.9  # a close/previous ratio this far from 1 is what a 1:2 reverse or 2:1 split would leave
# SPLIT_FILING_NEARBY (a consistent split filing in the window whose effective date is not the
# jump session) is reported, not quarantined: inspection of coverage v1 showed it mostly matches
# a split weeks before an unrelated jump. Decided before any repaired run.
COVERAGE_QUARANTINE = (
    "MISSING_PROVIDER_SPLIT",
    "PROVIDER_DATE_MISMATCH",
    "JUMP_ON_RECORD_SESSION",
    "NO_CIK",
)


def jump_rows(panel: pd.DataFrame, events: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Sessions in [start, end] where the adjusted close moved by JUMP or more: where an unrecorded
    split would show. The move only triggers a search; it is never taken as proof of a split."""
    w = panel[(panel["date"] >= pd.Timestamp(start)) & (panel["date"] <= pd.Timestamp(end))]
    r = w["close"] / w["previous"]
    rows = w.loc[(r >= JUMP) | (r <= 1 / JUMP), ["ticker", "date"]].assign(ratio=r)
    rows["date"] = rows["date"].dt.date.astype(str)
    recorded = set(zip(events["ticker"], events["effective_session"]))
    rows["on_record_session"] = [(t, d) in recorded for t, d in zip(rows["ticker"], rows["date"])]
    return rows.reset_index(drop=True)


def check_jump(
    client: SecClient,
    ciks: dict,
    events: pd.DataFrame,
    ticker: str,
    session: str,
    ratio: float,
    on_record_session: bool,
    max_docs: int = 6,
) -> dict:
    if on_record_session:
        return {"status": "JUMP_ON_RECORD_SESSION", "evidence": []}
    cik = ciks.get(ticker.upper())
    if cik is None:
        return {"status": "NO_CIK", "evidence": []}
    day = date.fromisoformat(session)
    near = events[
        (events["ticker"] == ticker)
        & (
            pd.to_datetime(events["effective_session"]).sub(pd.Timestamp(day)).abs()
            <= pd.Timedelta(days=10)
        )
    ]
    hits = sorted(
        search(client, cik, day - timedelta(days=45), day + timedelta(days=5)), key=_priority
    )
    best, evidence = "NO_SPLIT_EVIDENCE", []
    for hit in hits[:max_docs]:
        status, body = client.get(hit["url"])
        if status != 200:
            continue
        text = text_of(body)
        if not SPLIT_WORDS.search(text):
            continue
        judged = [
            (p, judge(text, *p, day))
            for p in ratios_in(text)
            if abs(np.log(ratio) - np.log(p[1] / p[0])) < np.log(2)
        ]
        consistent = [p for p, v in judged if v["ratio_ok"]]
        if not consistent:
            continue
        dated = any(v["date_ok"] for _, v in judged)
        found = "MISSING_PROVIDER_SPLIT" if dated else "SPLIT_FILING_NEARBY"
        evidence.append(
            {
                **{k: hit[k] for k in ("accession", "form", "file_date", "url")},
                "finding": found,
                "pairs": consistent[:4],
                "verifier_version": VERSION,
                "matched_statements": [
                    excerpt for _, v in judged for excerpt in v["matched_statements"]
                ][:3],
            }
        )
        if found == "MISSING_PROVIDER_SPLIT":
            best = found
            break
        best = found
    if best == "MISSING_PROVIDER_SPLIT" and len(near):
        best = (
            "PROVIDER_DATE_MISMATCH"  # a provider record within 10 days, yet the jump is unadjusted
        )
    return {"status": best, "cik": cik, "filings_searched": len(hits), "evidence": evidence}


def build_coverage(
    raw_manifest: Path,
    user_agent: str,
    start: str,
    end: str,
    cache_dir: Path | None = None,
    offline: bool = False,
    workers: int = 4,
    log=print,
) -> Path:
    from concurrent.futures import ThreadPoolExecutor

    from . import global_panel

    raw, _ = global_panel.load_us(raw_manifest)
    raw = raw[raw["date"] <= pd.Timestamp(end)]
    panel, _ = global_panel._finish(raw)
    events = yahoo_events(raw_manifest)
    rows = jump_rows(panel, events, start, end)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    client = SecClient(user_agent, cache_dir or RAW / "sec" / stamp, offline=offline)
    ciks = cik_map(client)

    def one(r):
        res = check_jump(client, ciks, events, r.ticker, r.date, r.ratio, r.on_record_session)
        return {
            **r._asdict(),
            "status": res["status"],
            "cik": res.get("cik"),
            "filings_searched": res.get("filings_searched", 0),
            "evidence": json.dumps(res["evidence"], sort_keys=True),
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        checked = pd.DataFrame(list(pool.map(one, list(rows.itertuples(index=False)))))
    out_dir = PKG_ROOT / "data" / "corporate_actions"
    csv_path = out_dir / f"us_splits-coverage-{stamp}.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as fh:
        checked.to_csv(fh, index=False, lineterminator="\n")
    sec_manifest = write_manifest(
        f"sec_split_coverage-{stamp}.jsonl",
        {"source": "sec_edgar", "user_agent": user_agent, "purpose": "unrecorded split search"},
        [r for r in {r["path"]: r for r in client.records}.values()],
    )
    quarantine = (
        sorted(set(checked.loc[checked["status"].isin(COVERAGE_QUARANTINE), "ticker"]))
        if len(checked)
        else []
    )
    meta = {
        "version": VERSION,
        "built_at": utc_stamp(),
        "raw_manifest": raw_manifest.name,
        "raw_manifest_sha256": hashlib.sha256(raw_manifest.read_bytes()).hexdigest(),
        "window": [start, end],
        "offline": offline,
        "offline_cache_misses": len(client.cache_misses),
        "jump_threshold": JUMP,
        "rows": rel(csv_path),
        "rows_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "sec_manifest": sec_manifest.name,
        "jump_rows": int(len(checked)),
        "status_counts": checked["status"].value_counts().to_dict() if len(checked) else {},
        "quarantine_statuses": list(COVERAGE_QUARANTINE),
        "quarantine_tickers": quarantine,
    }
    mpath = out_dir / f"us_splits-coverage-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    log(json.dumps(meta["status_counts"]))
    return mpath


# ------------------------------------------------------------------------------ share counts
# A second, independent corroboration for research panels: the shares outstanding a company
# reports on its SEC cover pages (XBRL dei:EntityCommonStockSharesOutstanding, as filed). A real
# 1-for-10 reverse split cuts the count about tenfold; dilution between reports only raises it.
# Used only for records effective AFTER the research window: there the exact session does not
# affect any in-window price unit, so proving the ratio and that the split came after the window
# is enough. Inside the window the text rule (VERIFIED, with the date) stays the only acceptance.
# Paper scoring does not use this. Rule fixed 2026-10-08 before running on the full set.
SHARES_VERSION = "sec-shares-v1"
SHARES_RULE = {"q_low": 0.8, "q_high": 2.0, "max_bracket_days": 400, "margin": 0.5}
RESEARCH_ACCEPTED = ("VERIFIED", "SHARES_CONFIRMED")


def share_points(client: SecClient, cik: int) -> list[dict]:
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityCommonStockSharesOutstanding.json"
    status, body = client.get(url)
    if status != 200:
        return []
    facts = json.loads(body).get("units", {}).get("shares", [])
    return [
        {
            "end": f["end"],
            "val": float(f["val"]),
            "filed": f.get("filed", ""),
            "form": f.get("form"),
            "accn": f.get("accn"),
        }
        for f in facts
        if f.get("val")
    ]


def check_shares(
    points: list[dict],
    ticker_events: pd.DataFrame,
    effective: str,
    window_end: str,
    rule: dict = SHARES_RULE,
) -> dict:
    """Whether the cover-page share counts around `effective` show the provider's split(s)."""
    pre = [
        p
        for p in points
        if p["end"] < effective and p["filed"] < effective and p["end"] >= window_end
    ]
    post = [p for p in points if p["end"] >= effective]
    if not pre or not post:
        return {
            "ok": False,
            "why": "no as-filed count after the window and before the split, or none after it",
        }
    a = max(pre, key=lambda p: (p["end"], p["filed"]))
    b = min(post, key=lambda p: (p["end"], p["filed"]))
    between = ticker_events[
        (ticker_events["effective_session"] > a["end"])
        & (ticker_events["effective_session"] <= b["end"])
    ]
    if (between["kind"] != "SPLIT").any():
        return {"ok": False, "why": "a non-split price adjustment lies between the two counts"}
    expected = (
        float(np.prod(between["numerator"] / between["denominator"])) if len(between) else 1.0
    )
    days = (date.fromisoformat(b["end"]) - date.fromisoformat(a["end"])).days
    observed = b["val"] / a["val"]
    q = observed / expected
    ok = (
        expected != 1.0
        and rule["q_low"] <= q <= rule["q_high"]
        and days <= rule["max_bracket_days"]
        and abs(np.log(q)) < rule["margin"] * abs(np.log(expected))
    )
    return {
        "ok": bool(ok),
        "pre": a,
        "post": b,
        "events_between": between["effective_session"].tolist(),
        "expected": expected,
        "observed": observed,
        "q": q,
        "bracket_days": days,
        "why": "consistent"
        if ok
        else "count change does not match the provider ratio within the rule",
    }


def build_share_corroboration(
    schedule_manifest: Path,
    raw_manifest: Path,
    window_end: str,
    user_agent: str,
    cache_dir: Path | None = None,
    offline: bool = False,
    log=print,
) -> Path:
    """A new schedule: the text-verified schedule with SHARES_CONFIRMED added where the rule holds."""
    smeta = json.loads(Path(schedule_manifest).read_text(encoding="utf-8"))
    if smeta.get("version") != VERSION:
        raise ValueError("share corroboration builds on a schedule from the current text verifier")
    sched_path = PKG_ROOT / smeta["schedule"]
    if hashlib.sha256(sched_path.read_bytes()).hexdigest() != smeta["schedule_sha256"]:
        raise RuntimeError(f"{Path(schedule_manifest).name}: schedule file changed")
    sched = pd.read_csv(sched_path, dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    events = yahoo_events(raw_manifest)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    client = SecClient(user_agent, cache_dir or RAW / "sec" / stamp, offline=offline)
    ciks = cik_map(client)
    todo = sched[
        (sched["kind"] == "SPLIT")
        & (sched["status"] != "VERIFIED")
        & (sched["effective_session"] > window_end)
    ]
    sched["shares_evidence"] = ""
    points_by = {}
    for i, r in enumerate(todo.itertuples()):
        cik = ciks.get(r.ticker.upper())
        if cik is None:
            continue
        if cik not in points_by:
            points_by[cik] = share_points(client, cik)
        res = check_shares(
            points_by[cik], events[events["ticker"] == r.ticker], r.effective_session, window_end
        )
        sched.at[r.Index, "shares_evidence"] = json.dumps(res, sort_keys=True, default=str)
        if res["ok"]:
            sched.at[r.Index, "status"] = "SHARES_CONFIRMED"
        if (i + 1) % 100 == 0:
            log(f"shares {i + 1}/{len(todo)}")
    out_dir = PKG_ROOT / "data" / "corporate_actions"
    csv_path = out_dir / f"us_splits-shares-{stamp}.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as fh:
        sched.to_csv(fh, index=False, lineterminator="\n")
    sec_manifest = write_manifest(
        f"sec_share_counts-{stamp}.jsonl",
        {"source": "sec_edgar_xbrl", "user_agent": user_agent, "purpose": "split share counts"},
        [r for r in {r["path"]: r for r in client.records}.values()],
    )
    meta = {
        **{
            k: smeta[k]
            for k in ("raw_manifest", "raw_manifest_sha256", "effective_after", "universe_end")
        },
        "version": VERSION,
        "built_at": utc_stamp(),
        "schedule": rel(csv_path),
        "schedule_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "text_schedule": {
            "manifest": Path(schedule_manifest).name,
            "sha256": hashlib.sha256(Path(schedule_manifest).read_bytes()).hexdigest(),
            "status_counts": smeta.get("status_counts"),
        },
        "share_count_corroboration": {
            "version": SHARES_VERSION,
            "rule": SHARES_RULE,
            "window_end": window_end,
            "sec_manifest": sec_manifest.name,
            "candidates": int(len(todo)),
            "confirmed": int((sched["status"] == "SHARES_CONFIRMED").sum()),
            "offline": offline,
            "offline_cache_misses": len(client.cache_misses),
        },
        "events_in_scope": int(len(sched)),
        "status_counts": sched["status"].value_counts().to_dict(),
        "accepted_statuses": list(RESEARCH_ACCEPTED),
    }
    mpath = out_dir / f"us_splits-shares-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    log(json.dumps(meta["share_count_corroboration"]))
    return mpath


# ------------------------------------------------------------- schedule reconciliation (v2)
RECONCILE_VERSION = "ca-reconcile-v1"
# Statuses a provider event gets when no single, matching verification record exists. None of
# them is ever accepted: a missing record is unresolved, not silently fine.
UNRESOLVED = (
    "UNRESOLVED_NO_RECORD",
    "UNRESOLVED_DUPLICATE_RECORD",
    "UNRESOLVED_PAYLOAD_MISMATCH",
    "UNRESOLVED_SHARES_OUTSIDE_WINDOW",
)
KEY = ["ticker", "effective_session", "numerator", "denominator"]


def sha256_path(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_bound_inputs(raw_manifest: Path, smeta: dict, coverage: dict | None = None) -> None:
    """The schedule (and coverage) must have been built from exactly these input bytes: the raw
    manifest by sha256 (a name alone can be reused), the schedule and coverage rows by sha256."""
    raw_sha = sha256_path(raw_manifest)
    if (
        smeta.get("raw_manifest") != Path(raw_manifest).name
        or smeta.get("raw_manifest_sha256") != raw_sha
    ):
        raise RuntimeError(
            "split schedule was built from a different raw manifest (name or sha256 differs)"
        )
    if sha256_path(PKG_ROOT / smeta["schedule"]) != smeta.get("schedule_sha256"):
        raise RuntimeError("split schedule rows differ from the sha256 its manifest records")
    if coverage is not None:
        if (
            coverage.get("raw_manifest") != Path(raw_manifest).name
            or coverage.get("raw_manifest_sha256") != raw_sha
        ):
            raise RuntimeError(
                "split coverage was built from a different raw manifest (name or sha256 differs)"
            )
        if sha256_path(PKG_ROOT / coverage["rows"]) != coverage.get("rows_sha256"):
            raise RuntimeError("split coverage rows differ from the sha256 their manifest records")


def reconcile_schedule(
    events: pd.DataFrame,
    sched: pd.DataFrame,
    effective_after: str,
    tickers,
    accepted: tuple,
    read_through: str,
    share_window_end: str | None = None,
) -> pd.DataFrame:
    """One row per provider split event that can change the units of a panel row: every event of a
    panel name effective after `effective_after`. Each needs exactly one verification record with
    the same key and the same payload hash; otherwise it gets an UNRESOLVED_* status. A
    SHARES_CONFIRMED record counts only for an event after the share-count window
    (`share_window_end`), and only when the panel reads no further than that window."""
    tickers = set(tickers)
    ev = events[
        (events["ticker"].isin(tickers)) & (events["effective_session"] > effective_after)
    ].copy()
    sched = sched.copy()
    for col in ("numerator", "denominator"):
        sched[col] = sched[col].astype(float)
        ev[col] = ev[col].astype(float)
    counts = sched.groupby(KEY).size().rename("n_records").reset_index()
    first = sched.drop_duplicates(KEY)[KEY + ["status", "payload_sha256"]].rename(
        columns={"payload_sha256": "record_payload_sha256", "status": "record_status"}
    )
    out = ev.merge(counts, on=KEY, how="left").merge(first, on=KEY, how="left")
    out["n_records"] = out["n_records"].fillna(0).astype(int)
    status = out["record_status"].astype(object).copy()
    status[out["n_records"] == 0] = "UNRESOLVED_NO_RECORD"
    status[out["n_records"] > 1] = "UNRESOLVED_DUPLICATE_RECORD"
    mismatch = (out["n_records"] == 1) & (out["record_payload_sha256"] != out["payload_sha256"])
    status[mismatch] = "UNRESOLVED_PAYLOAD_MISMATCH"
    if "SHARES_CONFIRMED" in accepted:
        if share_window_end is None:
            raise ValueError(
                "SHARES_CONFIRMED is accepted but the schedule declares no share-count window"
            )
        if read_through > share_window_end:
            raise ValueError(
                f"share-count corroboration is permitted for panels reading through {share_window_end} "
                f"at most; this panel reads through {read_through}"
            )
        outside = (status == "SHARES_CONFIRMED") & (out["effective_session"] <= share_window_end)
        status[outside] = "UNRESOLVED_SHARES_OUTSIDE_WINDOW"
    out["status"] = status
    out["accepted"] = out["status"].isin([a for a in accepted if a not in UNRESOLVED])
    return out.sort_values(KEY).reset_index(drop=True)

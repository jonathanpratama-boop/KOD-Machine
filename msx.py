#!/usr/bin/env python3
"""msx - Moonshot run toolkit (Python 3.9+, standard library only).

Deterministic mechanics for the Moonshot Project's scheduled runs, so the model spends its
judgment on news and decisions instead of arithmetic and page-reading:

  clock / cal       system clock in UTC, ET and WIB; NYSE sessions, holidays, early closes
  projdoc           copy a project_read result (inline or local file) to disk, exact bytes
  bars              daily bars from chartexchange and stockanalysis, reconciled per date
  resolve           first-passage outcomes (+30% before -5% / -10%) for registered items
  reg               append-only, hash-chained register of frozen records and resolutions
  ledger            outline / get / apply (patch with a no-loss guard) / guard / archive
  wire, news, filings, quote, stats, premarket, gainers, screen, kod-us
                    compact parsers for public pages (no retries; a refusal ends that host)
  stress, pct, barriers, cap
                    the ledger's recurring arithmetic, in Decimal
  selftest          integrity hash, calendar and logic checks; --net probes the data hosts

Rules built in: every fetch is logged with its sha256; HTTP 401/403/429/503 stops further
requests to that host for the run (never worked around); same-day bars are PROVISIONAL until a
second source agrees; both barriers inside one daily bar = CENSORED; nothing here trades.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = "3.0.2"
SELF_SHA256 = "930989b533daad01757300fd48dde4d51c7d338387a0f2293136fe6487905cd9"

# ----------------------------------------------------------------------------- time

UTC = dt.timezone.utc
WIB = dt.timezone(dt.timedelta(hours=7), "WIB")


def utcnow():
    s = os.environ.get("MSX_NOW")          # test override, e.g. 2026-10-13T23:30:00Z
    if s:
        return parse_iso(s)
    return dt.datetime.now(UTC).replace(microsecond=0)


def parse_iso(s):
    s = s.strip().replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        raise ValueError(f"timestamp without a zone: {s!r} (use Z or +hh:mm)")
    return t.astimezone(UTC)


def iso(t):
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nth_sunday(year, month, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(6 - d.weekday()) % 7)
    return d + dt.timedelta(days=7 * (n - 1))


def dst_window_utc(year):
    """US DST: 2nd Sunday of March 02:00 EST (07:00Z) to 1st Sunday of November 02:00 EDT (06:00Z)."""
    s, e = _nth_sunday(year, 3, 2), _nth_sunday(year, 11, 1)
    return (dt.datetime(s.year, s.month, s.day, 7, tzinfo=UTC),
            dt.datetime(e.year, e.month, e.day, 6, tzinfo=UTC))


def et_tz(t_utc):
    a, b = dst_window_utc(t_utc.year)
    if a <= t_utc < b:
        return dt.timezone(dt.timedelta(hours=-4), "EDT")
    return dt.timezone(dt.timedelta(hours=-5), "EST")


def to_et(t):
    t = t.astimezone(UTC)
    return t.astimezone(et_tz(t))


def to_wib(t):
    return t.astimezone(WIB)


def et_wall_to_utc(d, hh, mm=0):
    for off in (-4, -5):
        cand = dt.datetime(d.year, d.month, d.day, hh, mm,
                           tzinfo=dt.timezone(dt.timedelta(hours=off))).astimezone(UTC)
        if et_tz(cand).utcoffset(None) == dt.timedelta(hours=off):
            return cand
    return dt.datetime(d.year, d.month, d.day, hh, mm,
                       tzinfo=dt.timezone(dt.timedelta(hours=-5))).astimezone(UTC)


def fmt_triple(t):
    e, w = to_et(t), to_wib(t)
    return (f"{iso(t)} · {e.strftime('%Y-%m-%d %H:%M:%S')} {e.tzname()} · "
            f"{w.strftime('%Y-%m-%d %H:%M:%S')} WIB")


# ----------------------------------------------------------------------------- NYSE calendar
# 2026 from the NYSE calendar as recorded in procedures §1; 2027 rule-based (verify before relying).
NYSE_HOLIDAYS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
    "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
    "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
}
NYSE_EARLY_CLOSE = {"2026-11-27": (13, 0), "2026-12-24": (13, 0), "2027-11-26": (13, 0)}
CAL_VERIFIED_YEARS = {2026}
CAL_RULE_YEARS = {2027}


def as_date(x):
    if isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x))


def cal_note(d):
    d = as_date(d)
    if d.year in CAL_VERIFIED_YEARS:
        return ""
    if d.year in CAL_RULE_YEARS:
        return "calendar rule-based for this year (verify against the NYSE calendar)"
    return "CALENDAR_UNVERIFIED: no holiday table for this year (weekdays assumed open)"


def is_session(d):
    d = as_date(d)
    return d.weekday() < 5 and d.isoformat() not in NYSE_HOLIDAYS


def close_hm(d):
    return NYSE_EARLY_CLOSE.get(as_date(d).isoformat(), (16, 0))


def session_open_utc(d):
    return et_wall_to_utc(as_date(d), 9, 30)


def session_close_utc(d):
    hh, mm = close_hm(d)
    return et_wall_to_utc(as_date(d), hh, mm)


def next_session(d, include=False):
    d = as_date(d)
    x = d if include else d + dt.timedelta(days=1)
    while not is_session(x):
        x += dt.timedelta(days=1)
    return x


def prev_session(d, include=False):
    d = as_date(d)
    x = d if include else d - dt.timedelta(days=1)
    while not is_session(x):
        x -= dt.timedelta(days=1)
    return x


def sessions_from(d, n):
    out, x = [], as_date(d)
    while len(out) < n:
        if is_session(x):
            out.append(x)
        x += dt.timedelta(days=1)
    return out


def last_completed_session(now):
    x = to_et(now).date()
    while not (is_session(x) and session_close_utc(x) <= now):
        x -= dt.timedelta(days=1)
    return x


def market_phase(now):
    e = to_et(now)
    d = e.date()
    if not is_session(d):
        return "CLOSED (" + ("weekend" if d.weekday() >= 5 else "NYSE holiday") + ")"
    o, c = session_open_utc(d), session_close_utc(d)
    pre, post = et_wall_to_utc(d, 4, 0), et_wall_to_utc(d, 20, 0)
    if now < pre:
        return "OVERNIGHT (before 04:00 ET)"
    if now < o:
        return "PRE-MARKET"
    if now < c:
        return "REGULAR SESSION" + (" (early close day)" if close_hm(d) != (16, 0) else "")
    if now < post:
        return "AFTER-HOURS"
    return "CLOSED (after 20:00 ET)"


# ----------------------------------------------------------------------------- numbers

def D(x):
    if isinstance(x, Decimal):
        return x
    s = str(x).strip().replace(",", "").replace("$", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"not a number: {x!r}")


def parse_num(s):
    if s is None:
        return None
    s = htmlmod.unescape(str(s)).strip().replace(",", "").replace("$", "")
    if s in ("", "-", "--", "n/a", "N/A", "—", "–"):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


_ABBR = {"K": Decimal(10) ** 3, "M": Decimal(10) ** 6, "B": Decimal(10) ** 9, "T": Decimal(10) ** 12}


def parse_abbrev(s):
    if s is None:
        return None
    s = htmlmod.unescape(str(s)).strip().replace(",", "").replace("$", "")
    m = re.fullmatch(r"([+-]?\d*\.?\d+)\s*([KMBT]?)", s)
    if not m:
        return None
    v = Decimal(m.group(1))
    return v * _ABBR[m.group(2)] if m.group(2) else v


def q(x, places=4):
    """Round half-up to at most `places` decimals and drop trailing zeros (keeps >= 2 decimals)."""
    x = D(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    s = format(x, "f")
    if "." in s:
        s = s.rstrip("0")
        if len(s.split(".")[1]) < 2:
            s = format(D(s).quantize(Decimal("0.01")), "f")
    return s


def fmt_pct(x, places=2):
    v = D(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{sign}{abs(v)}%"


def pct_change(new, old):
    return (D(new) / D(old) - 1) * 100


def fmt_money(x):
    x = D(x)
    a = abs(x)
    for unit, div in (("T", _ABBR["T"]), ("B", _ABBR["B"]), ("M", _ABBR["M"]), ("K", _ABBR["K"])):
        if a >= div:
            return f"{'-' if x < 0 else ''}${q(a / div, 3 if unit in 'TB' else 1)}{unit}"
    return f"${q(x, 2)}"


# ----------------------------------------------------------------------------- network

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA,
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.9"}
BUDGET = {"stockanalysis.com": 40, "chartexchange.com": 60, "www.stocktitan.net": 30}
GAP_S = {"stockanalysis.com": 1.5, "chartexchange.com": 0.7, "www.stocktitan.net": 1.0}
STOP_CODES = {401, 403, 429, 503}


def workdir():
    p = Path(os.environ.get("MSX_WORK", os.path.expanduser("~/msx_work")))
    (p / "raw").mkdir(parents=True, exist_ok=True)
    return p


class Fetch:
    def __init__(self, status, text, url, sha=None, t=None, note=""):
        self.status, self.text, self.url, self.sha, self.t, self.note = status, text, url, sha, t, note

    @property
    def ok(self):
        return self.status == 200


class Net:
    def __init__(self, work=None):
        self.work = Path(work) if work else workdir()
        (self.work / "raw").mkdir(parents=True, exist_ok=True)
        self.state_file = self.work / "net_state.json"
        self.state = {"used": {}, "blocked": {}, "last": {}, "cache": {}, "exch": {}, "errors": {}}
        if self.state_file.exists():
            try:
                self.state.update(json.loads(self.state_file.read_text()))
            except Exception:
                pass
        if time.time() - self.state.get("t0", 0) > 6 * 3600:      # a new run: fresh budgets and blocks
            self.state.update(used={}, blocked={}, errors={}, t0=time.time())

    def save(self):
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=1, sort_keys=True))
        tmp.replace(self.state_file)

    def log(self, rec):
        with open(self.work / "fetch_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def get(self, url, ttl=900, bust=False):
        now = time.time()
        host = urllib.parse.urlsplit(url).hostname or ""
        c = self.state["cache"].get(url)
        if c and now - c["t"] <= ttl and (self.work / "raw" / c["file"]).exists():
            txt = (self.work / "raw" / c["file"]).read_bytes().decode("utf-8", "replace")
            return Fetch(200, txt, url, c["sha"], c["t"], "cache")
        if host in self.state["blocked"]:
            return Fetch("BLOCKED", "", url, note=self.state["blocked"][host])
        used = self.state["used"].get(host, 0)
        if used >= BUDGET.get(host, 20):
            return Fetch("BUDGET", "", url, note=f"request budget for {host} used ({used})")
        wait = GAP_S.get(host, 1.0) - (now - self.state["last"].get(host, 0))
        if wait > 0:
            time.sleep(wait)
        real = url + ((("&" if "?" in url else "?") + "t=" + str(int(time.time()))) if bust else "")
        self.state["used"][host] = used + 1
        self.state["last"][host] = time.time()
        status, body, note = None, b"", ""
        t0 = time.time()
        try:
            req = urllib.request.Request(real, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
            if e.code in STOP_CODES:
                note = f"HTTP {e.code} at {iso(utcnow())} — host not retried this run"
                self.state["blocked"][host] = note
        except Exception as e:  # network error or timeout
            status = "ERR"
            note = repr(e)[:160]
            n = self.state["errors"].get(host, 0) + 1
            self.state["errors"][host] = n
            if n >= 2:
                self.state["blocked"][host] = f"2 network errors — host not retried this run ({note})"
        sha = hashlib.sha256(body).hexdigest() if body else None
        self.log({"t": iso(utcnow()), "url": real, "status": status, "bytes": len(body), "sha256": sha,
                  "elapsed_s": round(time.time() - t0, 2), "note": note})
        if status == 200:
            fname = sha[:24] + ".html"
            (self.work / "raw" / fname).write_bytes(body)
            self.state["cache"][url] = {"file": fname, "sha": sha, "t": time.time()}
        self.save()
        return Fetch(status, body.decode("utf-8", "replace") if body else "", url, sha, time.time(), note)


# ----------------------------------------------------------------------------- parsing helpers

def text_of(h):
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", htmlmod.unescape(h)).strip()


def cell_text(c):
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<!--.*?-->", "", c, flags=re.S)))).strip()


def parse_cx_history(h):
    """chartexchange /symbol/<ex>-<t>/historical/: rows <tr id="YYYY-MM-DD">."""
    out = {}
    for d, body in re.findall(r'<tr id="(\d{4}-\d{2}-\d{2})">(.*?)</tr>', h, re.S):
        cells = [cell_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)]
        if len(cells) < 7:
            continue
        o, hi, lo, c = (parse_num(x) for x in cells[1:5])
        if None in (o, hi, lo, c):
            continue
        vol = parse_num(cells[6])
        out[d] = {"o": o, "h": hi, "l": lo, "c": c, "v": int(vol) if vol is not None else None}
    return out


def parse_sa_history(h):
    """stockanalysis /stocks/<t>/history/: first table; returns (bars, last_updated or None)."""
    out = {}
    m = re.search(r"<table.*?</table>", h, re.S)
    if m:
        for body in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S):
            cells = [cell_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)]
            if len(cells) < 8:
                continue
            try:
                d = dt.datetime.strptime(cells[0], "%b %d, %Y").date().isoformat()
            except ValueError:
                continue
            o, hi, lo, c = (parse_num(x) for x in cells[1:5])
            if None in (o, hi, lo, c):
                continue
            vol = parse_num(cells[7])
            out[d] = {"o": o, "h": hi, "l": lo, "c": c, "v": int(vol) if vol is not None else None}
    upd = None
    m = re.search(r'lastUpdated:"(\d{4}-\d{2}-\d{2})"', h)
    if m:
        upd = m.group(1)
    else:
        m = re.search(r"Last updated:\s*(?:<[^>]+>\s*)*([A-Z][a-z]{2} \d{1,2}, \d{4})", h)
        if m:
            try:
                upd = dt.datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat()
            except ValueError:
                pass
    return out, upd


QUOTE_BLOCK = re.compile(
    r"(\d[\d,]*\.?\d*) ([+-]?[\d,]*\.?\d+) \(([+-]?[\d.,]+)%\) "
    r"(?:(At close|Market open|Market closed|Pre-market|After-hours|Overnight|Real-time)\s*:?\s*)?"
    r"([A-Z][a-z]{2} \d{1,2}, \d{4}(?:, \d{1,2}:\d{2} [AP]M E[DS]T)?)")


def parse_sa_quote(h):
    t = text_of(h)
    out = {"exchange": None, "prints": [], "fields": {}}
    m = re.search(r"\b(NASDAQ|NYSEAMERICAN|NYSEARCA|NYSE|BATS|CBOE|OTC[A-Z]*): ([A-Z0-9.\-]+) · ", t)
    if m:
        out["exchange"] = m.group(1)
    i = t.find("Real-Time Price")
    seg = t[i:i + 600] if i >= 0 else t[:4000]
    for p, ch, pc, label, ts in QUOTE_BLOCK.findall(seg):
        out["prints"].append({"price": p.replace(",", ""), "change": ch, "pct": pc, "label": label or "(no label)",
                              "time": ts})
    pats = {"Market Cap": r"Market Cap ([\d.,]+[KMBT]?)", "Shares Out": r"Shares Out ([\d.,]+[KMBT]?)",
            "Volume": r"Volume ([\d,]+)", "Open": r"Open ([\d.,]+)", "Previous Close": r"Previous Close ([\d.,]+)",
            "Day's Range": r"Day's Range ([\d.,]+ - [\d.,]+)", "52-Week Range": r"52-Week Range ([\d.,]+ - [\d.,]+)",
            "Earnings Date": r"Est\. Earnings ([A-Z][a-z]{2} \d{1,2}, \d{4})"}
    j = t.find("Market Cap")
    seg2 = t[j:j + 900] if j >= 0 else ""
    for k, p in pats.items():
        mm = re.search(p, seg2)
        if mm:
            out["fields"][k] = mm.group(1)
    return out


def parse_sa_stats(h):
    out = {}
    for body in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", body, re.S)]
        if len(cells) >= 2 and cells[0] and cells[0] not in out:
            out[cells[0]] = cells[1]
    m = re.search(r"Last updated:\s*(?:<[^>]+>\s*)*([A-Z][a-z]{2} \d{1,2}, \d{4})", h)
    if m:
        out["_last_updated"] = m.group(1)
    return out


_KV = re.compile(r'(\w+):("(?:[^"\\]|\\.)*"|-?\d*\.?\d+(?:[eE][+-]?\d+)?|null|true|false)')


def _js_obj(body):
    o = {}
    for k, v in _KV.findall(body):
        if v.startswith('"'):
            o[k] = json.loads(v)
        elif v in ("null", "true", "false"):
            o[k] = {"null": None, "true": True, "false": False}[v]
        else:
            o[k] = Decimal(v if not v.startswith(".") and not v.startswith("-.") else v.replace(".", "0.", 1))
    return o


def parse_sa_movers(h):
    """Embedded SvelteKit data on stockanalysis movers pages: list of {main, dir, filters, rows}."""
    out = []
    for m in re.finditer(r"\},data:\[\{no:", h):
        start = m.end() - len("{no:")
        end = h.find("}]", start)
        if end < 0:
            continue
        arr = h[start:end + 1]
        rows = [_js_obj(b) for b in re.findall(r"\{(no:\d+,.*?)\}", arr, re.S)]
        back = h[max(0, m.start() - 700):m.start()]
        main = re.findall(r'main:"(\w+)"', back)
        sd = re.findall(r'sortDirection:"(\w+)"', back)
        filt = re.findall(r'filters:\[([^\]]*)\]', back)
        out.append({"main": main[-1] if main else None, "dir": sd[-1] if sd else None,
                    "filters": filt[-1] if filt else "", "rows": rows})
    return out


def parse_st_feed(h):
    """StockTitan live/today/day pages: one dict per news row."""
    items = []
    for r in re.split(r'<div class="d-flex py-2 news-row', h)[1:]:
        dd = re.search(r'<span (?:name="date"|data-role="date")[^>]*>([^<]+)</span>', r)
        tm = re.search(r'<span (?:name="time"|data-role="time")[^>]*>([^<]+)</span>', r)
        ticks = re.findall(r'<span class="symbol-link notranslate">([^<]+)</span>\s*:\s*([A-Za-z ]+?)\s*</a>', r)
        tit = re.search(r'class="text-gray-dark feed-link"[^>]*>(.*?)</a>', r, re.S)
        href = re.search(r'href="(/news/[A-Za-z0-9.\-]+/[a-z0-9\-]+\.html)"', r)
        imp = re.search(r'impact-bar" data-level="(\d)"', r)
        sen = re.search(r'sentiment-bar" data-level="(\d)"', r)
        tags = re.findall(r'<span class="badge[^"]*">([^<]+)</span>', r)
        if not (dd and tm and tit):
            continue
        try:
            when = dt.datetime.strptime(dd.group(1).strip() + " " + tm.group(1).strip(), "%m/%d/%Y %I:%M %p")
        except ValueError:
            continue
        items.append({"et": when, "tickers": [(a.strip(), b.strip()) for a, b in ticks],
                      "title": cell_text(tit.group(1)), "href": href.group(1) if href else "",
                      "impact": int(imp.group(1)) if imp else None, "sentiment": int(sen.group(1)) if sen else None,
                      "tags": [cell_text(x) for x in tags]})
    return items


FORM_RE = re.compile(r"(8-k-a|8-k|10-q-a|10-q|10-k-a|10-k|s-1-a|s-1|s-3asr|s-3-a|s-3|s-8|s-4|f-1|f-3|f-10|424b\d|"
                     r"def-14a|defa14a|def-14c|pre-14a|6-k|20-f|sc-13d-a|sc-13d|sc-13g-a|sc-13g|13d|13g|144|"
                     r"ars|px14a6g|425|8-a12b|nt-10-q|nt-10-k|efct|form-4|4|3|5)-")


def parse_st_ticker(h):
    """StockTitan per-ticker news or SEC-filing pages: (utc datetime, text, href)."""
    out = []
    parts = re.split(r'<time datetime="', h)
    for p in parts[1:]:
        ts = p[:p.find('"')]
        try:
            t = parse_iso(ts)
        except Exception:
            continue
        nxt = p[p.find(">") + 1:4000]
        a = re.search(r'<a href="(/(?:news|sec-filings)/[^"]+)"[^>]*>(.*?)</a>', nxt, re.S)
        txt = cell_text(re.sub(r"<time.*", "", nxt, flags=re.S)[:2500])
        form = None
        if a and a.group(1).startswith("/sec-filings/"):
            slug = a.group(1).rsplit("/", 1)[-1]
            fm = FORM_RE.match(slug)
            form = fm.group(1).upper() if fm else None
        out.append({"utc": t, "href": a.group(1) if a else "", "title": cell_text(a.group(2)) if a else "",
                    "text": txt[:400], "form": form})
    return out


# ----------------------------------------------------------------------------- bars

EXCHANGES = ("nasdaq", "nyse", "nyseamerican")


def get_bars(net, ticker):
    t = ticker.upper()
    res = {"ticker": t, "cx": {}, "sa": {}, "cx_url": None, "sa_url": None, "sa_updated": None,
           "cx_sha": None, "sa_sha": None, "notes": []}
    known = net.state["exch"].get(t)
    order = ([known] if known else []) + [e for e in EXCHANGES if e != known]
    for ex in order:
        url = f"https://chartexchange.com/symbol/{ex}-{t.lower().replace('.', '')}/historical/"
        f = net.get(url, bust=True)
        if f.ok:
            rows = parse_cx_history(f.text)
            if rows:
                res.update(cx=rows, cx_url=url, cx_sha=f.sha)
                net.state["exch"][t] = ex
                net.save()
                break
            res["notes"].append(f"chartexchange {ex}: page without price rows")
        elif f.status == 404:
            continue
        else:
            res["notes"].append(f"chartexchange: {f.status} {f.note}".strip())
            break
    else:
        if not res["cx"]:
            res["notes"].append("chartexchange: symbol not found on nasdaq/nyse/nyseamerican")
    url = f"https://stockanalysis.com/stocks/{t.lower()}/history/"
    f = net.get(url, bust=True)
    if f.ok:
        rows, upd = parse_sa_history(f.text)
        res.update(sa=rows, sa_url=url, sa_updated=upd, sa_sha=f.sha)
        if not rows:
            res["notes"].append("stockanalysis: page without price rows")
    else:
        res["notes"].append(f"stockanalysis: {f.status} {f.note}".strip())
    return res


def bar_str(b):
    if not b:
        return "—"
    v = f" v{b['v']:,}" if b.get("v") is not None else ""
    return f"O {q(b['o'])} H {q(b['h'])} L {q(b['l'])} C {q(b['c'])}{v}"


def compare_bars(a, b):
    if a and b:
        diff = [k for k in "ohlc" if a[k] != b[k]]
        return "AGREE" if not diff else "DATA_CONFLICT(" + ",".join(diff) + ")"
    return "chartexchange only" if a else ("stockanalysis only" if b else "none")


def freshness(res, now):
    exp = last_completed_session(now).isoformat()
    out = []
    for src, name in (("cx", "chartexchange"), ("sa", "stockanalysis")):
        rows = res[src]
        newest = max(rows) if rows else None
        flag = "OK" if newest and newest >= exp else ("STALE" if newest else "EMPTY")
        if newest and newest > exp:
            flag = f"OK (row {newest} is the session in progress — partial, intraday; resolutions ignore it)"
        extra = f"; page 'last updated' {res['sa_updated']}" if src == "sa" and res.get("sa_updated") else ""
        out.append(f"{name}: newest row {newest or '—'} (expected {exp}) {flag}{extra}")
    return out


# ----------------------------------------------------------------------------- first passage

TERMINAL = {"WIN", "LOSS", "CENSORED", "EXPIRY"}


def first_passage(ref, sessions, bars, up, down, now):
    """Daily-bar first passage: WIN (+up first), LOSS (-down first), CENSORED (both in one bar),
    EXPIRY (neither by the last session), MISSING (a completed session without a bar),
    OPEN (window not finished)."""
    ref = D(ref)
    upb, dnb = ref * (1 + D(up)), ref * (1 - D(down))
    for k, d in enumerate(sessions, 1):
        ds = d.isoformat()
        if session_close_utc(d) > now:
            return {"status": "OPEN", "k": k - 1, "date": None, "up": upb, "dn": dnb,
                    "left": len(sessions) - k + 1}
        b = bars.get(ds)
        if b is None:
            return {"status": "MISSING", "k": k, "date": ds, "up": upb, "dn": dnb}
        hu, hd = b["h"] >= upb, b["l"] <= dnb
        if hu and hd:
            return {"status": "CENSORED", "k": k, "date": ds, "bar": b, "up": upb, "dn": dnb}
        if hu:
            return {"status": "WIN", "k": k, "date": ds, "bar": b, "up": upb, "dn": dnb}
        if hd:
            return {"status": "LOSS", "k": k, "date": ds, "bar": b, "up": upb, "dn": dnb}
    last = sessions[-1].isoformat()
    b = bars[last]
    return {"status": "EXPIRY", "k": len(sessions), "date": last, "bar": b, "up": upb, "dn": dnb,
            "ret": (b["c"] / ref - 1) * 100}


def outcome_key(o):
    return (o["status"], o.get("date"))


def outcome_str(o):
    s = o["status"]
    if s in ("WIN", "LOSS", "CENSORED"):
        b = o["bar"]
        hit = []
        if s in ("WIN", "CENSORED"):
            hit.append(f"high {q(b['h'])} ≥ {q(o['up'])}")
        if s in ("LOSS", "CENSORED"):
            hit.append(f"low {q(b['l'])} ≤ {q(o['dn'])}")
        return f"{s} {o['date']} (session {o['k']}; {'; '.join(hit)})"
    if s == "EXPIRY":
        return f"EXPIRY {o['date']} ({fmt_pct(o['ret'])} at the {q(o['bar']['c'])} close; no touch)"
    if s == "MISSING":
        return f"MISSING (no bar for {o['date']}, session {o['k']})"
    return f"open ({o['k']} session(s) without a touch; {o['left']} left)"


def resolve_item(item, res, now):
    """Two scenarios (stockanalysis-first, chartexchange-first); agreement decides, else UNRESOLVED."""
    sessions = sessions_from(item["ref_date"], int(item.get("n", 5)))
    if session_open_utc(sessions[0]) > now:
        return {"pending": True, "sessions": sessions}
    downs = [D(x) for x in item["downs"]]
    up = D(item.get("up", "0.30"))
    scen = []
    for prim, sec in (("sa", "cx"), ("cx", "sa")):
        bars = dict(res[sec])
        bars.update(res[prim])
        if item.get("ref_price"):
            ref, rsrc = D(item["ref_price"]), "registered"
        else:
            b0 = bars.get(sessions[0].isoformat())
            if not b0:
                if session_close_utc(sessions[0]) <= now:
                    scen.append({"prim": prim, "ref": None})
                else:
                    scen.append({"prim": prim, "ref": None, "intraday": True})
                continue
            ref, rsrc = b0["o"], prim if sessions[0].isoformat() in res[prim] else sec
        cols = [first_passage(ref, sessions, bars, up, dn, now) for dn in downs]
        scen.append({"prim": prim, "ref": ref, "rsrc": rsrc, "cols": cols})
    return {"pending": False, "sessions": sessions, "scen": scen, "downs": downs, "up": up}


def summarize_resolution(item, r, res, now):
    lines = []
    if r.get("pending"):
        return [f"{item['id']} {item['ticker']} — PENDING (window starts {r['sessions'][0]})"], []
    sc = r["scen"]
    if any(s["ref"] is None for s in sc):
        intr = any(s.get("intraday") for s in sc)
        msg = "reference open not yet available (session in progress)" if intr else "MISSING reference bar"
        return [f"{item['id']} {item['ticker']} — {msg} ({r['sessions'][0]})"], []
    a, b = sc[0], sc[1]
    ref_txt = f"reference {q(a['ref'])}"
    if a["ref"] != b["ref"]:
        ref_txt += f" (stockanalysis) vs {q(b['ref'])} (chartexchange) — DATA_CONFLICT"
    elif item.get("ref_price"):
        ref_txt += " (registered)"
    else:
        src0 = r["sessions"][0].isoformat()
        both = src0 in res["sa"] and src0 in res["cx"]
        ref_txt += f" ({'both sources' if both else ('stockanalysis' if src0 in res['sa'] else 'chartexchange')} open {src0})"
    window = f"{r['sessions'][0]} → {r['sessions'][-1]}"
    if session_close_utc(r["sessions"][0]) > now:
        ref_txt += " — reference session still in progress (provisional)"
    lines.append(f"{item['id']} {item['ticker']} — {ref_txt} · window {window}")
    rec_ref = item.get("recorded_ref")
    if rec_ref and not item.get("ref_price") and D(rec_ref) not in (a["ref"], b["ref"]):
        lines.append(f"  note: the ledger recorded {rec_ref} as the reference (a provisional first capture); the sources now "
                     f"show {q(a['ref'])} → record CORRECTED_INPUT if an outcome changes")
    out_records = []
    for ci, dn in enumerate(r["downs"]):
        oa, ob = a["cols"][ci], b["cols"][ci]
        label = f"  col{ci + 1} (+{q(r['up'] * 100, 2)}% before −{q(dn * 100, 2)}%; barriers {q(oa['up'])} / {q(oa['dn'])})"
        if outcome_key(oa) == outcome_key(ob):
            final = oa["status"] in TERMINAL and _decided_by_both(oa, r, res)
            tag = "FINAL" if final else ("PROVISIONAL" if oa["status"] in TERMINAL else "")
            lines.append(f"{label}: {outcome_str(oa)}" + (f" [{tag}]" if tag else ""))
            out_records.append({"col": ci + 1, "status": oa["status"], "date": oa.get("date"),
                                "final": bool(final), "text": outcome_str(oa)})
        else:
            lines.append(f"{label}: UNRESOLVED — stockanalysis-first {outcome_str(oa)} | chartexchange-first {outcome_str(ob)}")
            out_records.append({"col": ci + 1, "status": "UNRESOLVED", "date": None, "final": False,
                                "text": f"sa-first {outcome_str(oa)} | cx-first {outcome_str(ob)}"})
    return lines, out_records


def _decided_by_both(o, r, res):
    """FINAL only when every bar the outcome used exists in both sources (and they agree on it)."""
    used = []
    for d in r["sessions"]:
        used.append(d.isoformat())
        if o.get("date") == d.isoformat():
            break
    for ds in used:
        a, b = res["cx"].get(ds), res["sa"].get(ds)
        if not (a and b):
            return False
    return True


# ----------------------------------------------------------------------------- register

GENESIS_PREV = "0" * 64
ITEM_KINDS = {"FORECAST", "E001", "E002", "SHADOW"}
REG_KINDS = ITEM_KINDS | {"GENESIS", "DECISION", "RESOLUTION", "NOTE", "RUN"}


def canon(rec):
    body = {k: rec[k] for k in rec if k != "hash"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def rec_hash(rec):
    return hashlib.sha256(canon(rec).encode("utf-8")).hexdigest()


class RegError(Exception):
    pass


def reg_read(path, verify=True):
    recs = []
    p = Path(path)
    if not p.exists():
        return recs
    raw = p.read_text(encoding="utf-8")
    for n, line in enumerate(raw.split("\n"), 1):
        if not line.strip():
            continue
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise RegError(f"line {n}: not JSON ({e})")
    if verify:
        prev = GENESIS_PREV
        for i, r in enumerate(recs, 1):
            if r.get("seq") != i:
                raise RegError(f"record {i}: seq {r.get('seq')} out of order")
            if r.get("prev") != prev:
                raise RegError(f"record {i}: prev does not match the hash of record {i - 1}")
            if r.get("hash") != rec_hash(r):
                raise RegError(f"record {i}: hash mismatch (edited after writing?)")
            prev = r["hash"]
    return recs


def validate_item(kind, payload):
    if kind not in ITEM_KINDS:
        return
    for k in ("ticker", "ref_date", "downs"):
        if k not in payload:
            raise RegError(f"{kind} payload needs '{k}'")
    if not is_session(payload["ref_date"]):
        raise RegError(f"ref_date {payload['ref_date']} is not an NYSE session")
    for x in payload["downs"]:
        if not (Decimal(0) < D(x) < Decimal(1)):
            raise RegError("downs are fractions, e.g. [\"0.05\", \"0.10\"]")
    if "ref_price" in payload and payload["ref_price"] is not None:
        D(payload["ref_price"])


def reg_append(path, kind, rid, run, payload, now=None):
    if kind not in REG_KINDS:
        raise RegError(f"unknown kind {kind}")
    validate_item(kind, payload)
    recs = reg_read(path)
    ids = {(r["kind"], r["id"]) for r in recs}
    if kind in ITEM_KINDS | {"DECISION"} and (kind, rid) in ids:
        raise RegError(f"{kind} {rid} already registered (append a NOTE or RESOLUTION instead)")
    rec = {"seq": len(recs) + 1, "prev": recs[-1]["hash"] if recs else GENESIS_PREV,
           "ts": iso(now or utcnow()), "kind": kind, "id": rid, "run": run, "payload": payload}
    rec["hash"] = rec_hash(rec)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return rec


def reg_status(recs):
    """Items with their latest resolution per column."""
    items, latest = {}, {}
    for r in recs:
        if r["kind"] in ITEM_KINDS:
            items[r["id"]] = r
        elif r["kind"] == "RESOLUTION":
            p = r["payload"]
            latest[(p["item"], int(p["col"]))] = r
    out = []
    for iid, r in items.items():
        p = r["payload"]
        cols = []
        for ci in range(1, len(p["downs"]) + 1):
            lr = latest.get((iid, ci))
            cols.append(lr["payload"] if lr else None)
        closed = all(c and c["status"] in TERMINAL and c.get("final") for c in cols)
        out.append({"id": iid, "kind": r["kind"], "payload": p, "cols": cols, "closed": closed, "seq": r["seq"]})
    return out


def reg_head(recs):
    return (recs[-1]["hash"] if recs else GENESIS_PREV), len(recs)


# ----------------------------------------------------------------------------- ledger

SEC_RE = re.compile(r"^## (\d+[a-z]?)\. ")
S14_TITLE = "## 14. Superseded lines (verbatim; the weekly review moves them to that week's archive)"


def read_lines(path):
    raw = Path(path).read_bytes().decode("utf-8")
    if "\r" in raw:
        raise SystemExit("CR characters in the ledger; aborting")
    return raw.split("\n")


def write_lines(path, lines):
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def sha_lines(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def section_bounds(lines):
    heads = [(m.group(1), i) for i, s in enumerate(lines) for m in [SEC_RE.match(s)] if m]
    b = {}
    for j, (k, i) in enumerate(heads):
        b[k] = (i, heads[j + 1][1] if j + 1 < len(heads) else len(lines))
    return b


def sec_end(lines, key):
    a, b = section_bounds(lines)[key]
    i = b
    while i - 1 > a and lines[i - 1] == "":
        i -= 1
    return i


def find_in(lines, key, pred, last=False):
    a, b = section_bounds(lines)[key]
    hits = [i for i in range(a, b) if pred(lines[i])]
    if not hits:
        return None
    return hits[-1] if last else hits[0]


def block_end(lines, i):
    """Index after the last non-blank line of the block starting at i."""
    e = i + 1
    while e < len(lines) and lines[e] != "":
        e += 1
    return e


def ensure_s14(lines):
    if "14" not in section_bounds(lines):
        while lines and lines[-1] == "":
            lines.pop()
        lines += ["", S14_TITLE, ""]
    return lines


def move_to_s14(lines, run, what, old):
    ensure_s14(lines)
    i = sec_end(lines, "14")
    if lines[i - 1] == S14_TITLE:
        lines.insert(i, "")
        i += 1
    lines.insert(i, f"- {run} · superseded {what}: {old}")


IS_DPTR = re.compile(r"^- D-\d{3} → D-\d{3}: moved")
DPTR_RANGE = re.compile(r"^- D-(\d{3}) → D-(\d{3}): moved verbatim to `([^`]+)`")


def decision_check(recs, ledger_lines):
    """Registered DECISION records vs the live ledger → (missing, archived).
    A record whose exact line is gone but whose ID lies in a '- D-aaa → D-bbb: moved verbatim to `doc`'
    pointer range was moved by an archive; anything else missing is a mismatch."""
    led = set(ledger_lines)
    arch = {}
    for ln in ledger_lines:
        m = DPTR_RANGE.match(ln)
        if m:
            for k in range(int(m.group(1)), int(m.group(2)) + 1):
                arch[f"D-{k:03d}"] = m.group(3)
    missing, archived = [], []
    for r in recs:
        if r["kind"] != "DECISION" or r["payload"]["text"] in led:
            continue
        (archived if r["id"] in arch else missing).append(r["id"])
    return missing, archived


def parse_patch(text):
    blocks, cur = [], None
    for line in text.split("\n"):
        if line.startswith("@@ "):
            cur = {"head": line[3:].strip(), "body": []}
            blocks.append(cur)
        elif cur is not None:
            cur["body"].append(line)
        elif line.strip():
            raise SystemExit(f"patch text before the first '@@' directive: {line[:80]!r}")
    for b in blocks:
        while b["body"] and b["body"][-1] == "":
            b["body"].pop()
        while b["body"] and b["body"][0] == "":
            b["body"].pop(0)
    return blocks


def _require(cond, msg):
    if not cond:
        raise SystemExit("PATCH ERROR: " + msg)


def apply_patch(lines, blocks, run):
    lines = list(lines)
    report, items = [], []
    for blk in blocks:
        head, body = blk["head"], blk["body"]
        name, _, arg = head.partition(" ")
        arg = arg.strip()
        if name == "items":
            for ln in body:
                if ln.strip():
                    items.append(json.loads(ln))
            report.append(f"items: {len(items)} register record(s) queued")
            continue
        _require(body or name == "replace", f"@@ {head}: empty body")
        if name == "header":
            _require(len(body) == 1, "header body must be one line")
            idx = next((i for i in range(min(12, len(lines))) if lines[i].startswith("Created: ")), None)
            _require(idx is not None, "no 'Created:' header line in the first 12 lines")
            old = lines[idx]
            pre = old.split(" · Last updated: ")[0]
            new = pre + " · Last updated: " + body[0].removeprefix("Last updated: ")
            lines[idx] = new
            move_to_s14(lines, run, "header line", old)
            report.append(f"header: replaced line {idx + 1}; old header moved to §14")
        elif name == "scan":
            _require(body[0].startswith("### S-"), "scan body must start with '### S-nnn'")
            i = find_in(lines, "6", lambda s: s.startswith("### KOD ("))
            if i is None:
                i = sec_end(lines, "6")
                lines[i:i] = [""] + body
            else:
                lines[i:i] = body + [""]
            report.append(f"scan: {body[0][:40]} inserted at line {i + 1}")
        elif name == "decision":
            _require(all(s.startswith("- D-") for s in body), "decision lines must start with '- D-'")
            j = find_in(lines, "11", lambda s: s.startswith("- D-"), last=True)
            _require(j is not None, "no decision list in §11")
            lines[j + 1:j + 1] = body
            report.append(f"decision: {len(body)} line(s) after line {j + 1}")
        elif name == "forecast-row":
            _require(all(s.startswith("| F-") for s in body), "forecast rows must start with '| F-'")
            j = find_in(lines, "11", lambda s: s.startswith("| F-"), last=True)
            lines[j + 1:j + 1] = body
            report.append(f"forecast-row: {len(body)} row(s) after line {j + 1}")
        elif name in ("additions", "e001", "e002-update", "r3-log", "process", "r4-check"):
            key = {"additions": "11", "e001": "12", "e002-update": "12a", "r3-log": "7", "process": "9",
                   "r4-check": "10"}[name]
            if name == "process":
                _require(body[0].startswith("- "), "process corrections are bullets ('- ')")
            i = sec_end(lines, key)
            lines[i:i] = body
            report.append(f"{name}: {len(body)} line(s) at the end of §{key} (line {i + 1})")
        elif name == "e002-row":
            _require(all(s.startswith("| ") for s in body), "E-002 rows start with '| '")
            j = find_in(lines, "12a", lambda s: s.startswith("| "), last=True)
            lines[j + 1:j + 1] = body
            report.append(f"e002-row: {len(body)} row(s) after line {j + 1}")
        elif name == "candidate-row":
            _require(all(s.startswith("| C-") for s in body), "candidate rows start with '| C-'")
            j = find_in(lines, "5", lambda s: s.startswith("| C-"), last=True)
            lines[j + 1:j + 1] = body
            report.append(f"candidate-row: {len(body)} row(s) after line {j + 1}")
        elif name == "candidate-block":
            _require(re.match(r"C-\d{3} ", body[0]) is not None, "candidate block starts with 'C-nnn TICKER — candidate test'")
            r = find_in(lines, "5", lambda s: re.match(r"C-\d{3} revision log:", s) is not None, last=True)
            if r is None:
                i = find_in(lines, "5", lambda s: s.startswith("Radar — scheduled events"))
                lines[i:i] = body + [""]
            else:
                e = block_end(lines, r)
                lines[e:e] = [""] + body
                i = e
            report.append(f"candidate-block: {body[0][:40]} at line {i + 1}")
        elif name == "note":
            i = find_in(lines, "5", lambda s: s.startswith("Radar — scheduled events"))
            _require(i is not None, "no radar line in §5")
            lines[i:i] = body + [""]
            report.append(f"note: {len(body)} line(s) before the radar (line {i + 1})")
        elif name == "radar":
            f = find_in(lines, "5", lambda s: s.startswith("Format: ID · asset"))
            _require(f is not None, "no 'Format:' line in §5")
            i = f
            while lines[i - 1] == "":
                i -= 1
            lines[i:i] = body
            report.append(f"radar: {len(body)} line(s) at line {i + 1}")
        elif name == "revlog":
            _require(re.fullmatch(r"C-\d{3}", arg) is not None, "usage: @@ revlog C-nnn")
            hits = [i for i, s in enumerate(lines) if s.startswith(f"{arg} revision log:")]
            _require(len(hits) == 1, f"'{arg} revision log:' found {len(hits)} times")
            e = block_end(lines, hits[0])
            lines[e:e] = body
            report.append(f"revlog {arg}: {len(body)} line(s) at line {e + 1}")
        elif name == "row":
            sec, _, key = arg.partition(" ") if arg.startswith("§") else ("", "", arg)
            sec = sec.lstrip("§")
            _require(key, "usage: @@ row [§sec] KEY")
            _require(len(body) == 1 and body[0].startswith(f"| {key} |"), f"row body must be one line starting '| {key} |'")
            rng = section_bounds(lines).get(sec) if sec else (0, len(lines))
            _require(rng is not None, f"no section §{sec}")
            hits = [i for i in range(*rng) if lines[i].startswith(f"| {key} |")]
            _require(len(hits) == 1, f"row '| {key} |' found {len(hits)} times" + ("" if sec else " (add §section)"))
            old = lines[hits[0]]
            lines[hits[0]] = body[0]
            where = [k for k, (a, b) in section_bounds(lines).items() if a <= hits[0] < b]
            move_to_s14(lines, run, f"row §{where[0] if where else '?'} '{key}'", old)
            report.append(f"row {key}: replaced line {hits[0] + 1}; old row moved to §14")
        elif name == "replace":
            _require("@@ with" not in head, "use: @@ replace / <old line> / @@ with / <new lines>")
            raise SystemExit("PATCH ERROR: 'replace' needs a following '@@ with' block")
        elif name == "with":
            raise SystemExit("PATCH ERROR: '@@ with' without '@@ replace'")
        else:
            raise SystemExit(f"PATCH ERROR: unknown directive '@@ {head}'")
    return lines, report, items


def apply_patch_text(lines, text, run):
    """Handles '@@ replace' + '@@ with' pairs, then the other directives in order."""
    blocks = parse_patch(text)
    merged = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b["head"] == "replace":
            _require(i + 1 < len(blocks) and blocks[i + 1]["head"] == "with", "'@@ replace' must be followed by '@@ with'")
            merged.append({"head": "__replace", "old": b["body"], "new": blocks[i + 1]["body"]})
            i += 2
        else:
            merged.append(b)
            i += 1
    out, report, items = list(lines), [], []
    for b in merged:
        if b["head"] == "__replace":
            _require(len(b["old"]) == 1, "replace: the old text must be exactly one whole line")
            hits = [k for k, s in enumerate(out) if s == b["old"][0]]
            _require(len(hits) == 1, f"replace: old line found {len(hits)} times")
            out[hits[0]:hits[0] + 1] = b["new"]
            move_to_s14(out, run, "line", b["old"][0])
            report.append(f"replace: line {hits[0] + 1} replaced; old line moved to §14")
        else:
            out, rep, its = apply_patch(out, [b], run)
            report += rep
            items += its
    return out, report, items


def guard(old, new):
    """No-loss check: headings kept in order; every removed line survives inside an added line."""
    problems = []
    ho = [s for s in old if SEC_RE.match(s)]
    hn = [s for s in new if SEC_RE.match(s)]
    if [h for h in hn if h in ho] != ho:
        problems.append("section headings lost or reordered")
    co, cn = Counter(old), Counter(new)
    removed = co - cn
    added = list((cn - co).elements())
    lost = []
    for line in removed.elements():
        if line == "":
            continue
        if not any(line in a for a in added):
            lost.append(line)
    if lost:
        problems.append(f"{len(lost)} removed line(s) not preserved anywhere: " +
                        " | ".join(x[:90] for x in lost[:5]))
    return problems, sum(removed.values()), len(added)


def ledger_ids(lines):
    txt = "\n".join(lines)
    def mx(p):
        v = [int(x) for x in re.findall(p, txt)]
        return max(v) if v else 0
    return {"S": mx(r"### S-(\d{3})") or mx(r"→ S-(\d{3})"), "D": max(mx(r"\n- D-(\d{3})"), mx(r"→ D-(\d{3})")),
            "F": mx(r"\n\| F-(\d{3}) \|"), "C": max(mx(r"\n\| C-(\d{3}) \|"), mx(r"\n- C-(\d{3}) "))}


def table_cells(row):
    return [c.strip() for c in row.strip().strip("|").split(" | ")]


def outline(lines, path=""):
    out = []
    raw = "\n".join(lines).encode("utf-8")
    out.append(f"{path} · {len(raw):,} bytes · {len(lines):,} lines · sha256 {hashlib.sha256(raw).hexdigest()}")
    hdr = next((s for s in lines[:12] if s.startswith("Created: ")), "")
    if hdr:
        lu = hdr.split(" · Last updated: ")[-1]
        out.append("Last updated: " + lu[:230] + ("…" if len(lu) > 230 else ""))
    pv = next((s for s in lines[:12] if s.startswith("Procedures in force")), "")
    out.append(pv[:160])
    b = section_bounds(lines)
    for k, (a, e) in sorted(b.items(), key=lambda kv: kv[1][0]):
        size = len("\n".join(lines[a:e]).encode("utf-8"))
        out.append(f"  §{k:<3} L{a + 1}–{e} ({size / 1024:.1f} KB) {lines[a][3:][:70]}")
    out.append("Candidates (table):")
    for s in lines:
        if s.startswith("| C-"):
            c = table_cells(s)
            st = c[4] if len(c) > 4 else ""
            out.append(f"  {c[0]} {c[1][:40]} · state: {st[:150]}{'…' if len(st) > 150 else ''} · review by {c[-1][:40] if c else ''}")
    scans = [(i, s) for i, s in enumerate(lines) if s.startswith("### S-")]
    out.append("Latest scans: " + ", ".join(f"{s[4:9]} (L{i + 1})" for i, s in scans[-3:]))
    decs = [s[2:7] for s in lines if s.startswith("- D-") and not IS_DPTR.match(s)]
    out.append("Latest decision records: " + ", ".join(decs[-3:]))
    fo = [table_cells(s) for s in lines if s.startswith("| F-")]
    if fo:
        out.append(f"Forecast table: {fo[0][0]} → {fo[-1][0]} ({len(fo)} rows; outcomes live in the register and the §11 scoreboards, "
                   "not in the table's Resolution cells)")
    e2 = []
    if "12a" in b:
        a, e = b["12a"]
        for s in lines[a:e]:
            if s.startswith("| ") and not s.startswith("| Case") and not s.startswith("|---"):
                c = table_cells(s)
                if len(c) >= 6 and any(w in x.lower().replace("*", "")[:12] for x in (c[4], c[5]) for w in ("open", "unresolved", "pending")):
                    e2.append(f"{c[0]} (col1 {c[4][:18]}…; col2 {c[5][:18]}…)")
    out.append("E-002 rows with an open column: " + "; ".join(e2))
    r4 = [s for s in lines if s.startswith("| 20") and "|" in s and ("PAUSED" in s or "ACTIVE" in s)]
    if r4:
        out.append("R4 table, last row: " + r4[-1][:200])
    ids = ledger_ids(lines)
    out.append(f"Next IDs: S-{ids['S'] + 1:03d} · D-{ids['D'] + 1:03d} · F-{ids['F'] + 1:03d} · C-{ids['C'] + 1:03d}")
    if "14" in b:
        a, e = b["14"]
        out.append(f"§14 holds {sum(1 for s in lines[a:e] if s.startswith('- '))} superseded line(s) awaiting the weekly archive")
    return out


E2_STATUS = re.compile(r"\b(WIN|LOSS|CENSORED|EXPIRY|UNRESOLVED|MISSING|open|pending)\b", re.I)


def e002_readout(lines):
    """Parse the §12a table: H1/H2 labels and the first status word of each column."""
    b = section_bounds(lines)
    a, e = b["12a"]
    cases = []
    for s in lines[a:e]:
        if not s.startswith("| ") or s.startswith("| Case") or s.startswith("|---"):
            continue
        c = table_cells(s)
        if len(c) < 6:
            continue
        h1 = re.search(r"H1-(PASS|FAIL|UNKNOWN)", c[1])
        h2 = re.search(r"H2-(PASS|FAIL|UNKNOWN)", c[1])
        st = []
        for x in (c[4], c[5]):
            m = E2_STATUS.search(x.replace("*", ""))
            st.append(m.group(1).upper() if m else "?")
        cases.append({"case": c[0], "h1": h1.group(1) if h1 else "?", "h2": h2.group(1) if h2 else "?",
                      "c1": st[0], "c2": st[1], "control": "control case" in c[1]})
    out = [f"E-002 cases in the §12a table: {len(cases)}"]
    for col in ("c1", "c2"):
        grp = {"H1∧H2-PASS": [x for x in cases if x["h1"] == "PASS" and x["h2"] == "PASS"],
               "all other": [x for x in cases if not (x["h1"] == "PASS" and x["h2"] == "PASS")]}
        parts = []
        rates = {}
        for g, xs in grp.items():
            res = [x for x in xs if x[col] in ("WIN", "LOSS", "EXPIRY")]
            wins = sum(1 for x in res if x[col] == "WIN")
            other = Counter(x[col] for x in xs if x[col] not in ("WIN", "LOSS", "EXPIRY"))
            rates[g] = (wins, len(res))
            parts.append(f"{g}: {wins} WIN of {len(res)} resolved ({', '.join(f'{k} {v}' for k, v in sorted(other.items())) or 'none other'}) "
                         f"[{', '.join(x['case'] for x in xs)}]")
        (wa, na), (wb, nb) = rates["H1∧H2-PASS"], rates["all other"]
        ra = wa / na if na else 0.0
        rb = wb / nb if nb else 0.0
        ok_n = na >= 6 and nb >= 6
        verdict = ("criterion MET (≥ 2× and ≥ 6 per group)" if ok_n and ra >= 2 * rb and ra > 0 else
                   ("criterion not met" if ok_n else "too few resolved per group for the pre-registered read-out (needs ≥ 6 each)"))
        out.append(f"column {col[1]}: " + " · ".join(parts) + f" → rates {ra:.1%} vs {rb:.1%}; {verdict}")
    out.append("Exploratory only; CENSORED, open and UNRESOLVED cases are excluded from the rates.")
    return out


def get_parts(lines, sec=None, cid=None, last_scans=0, rng=None):
    b = section_bounds(lines)
    out = []
    if sec:
        a, e = b[sec]
        out += lines[a:e]
    if cid:
        for s in lines:
            if s.startswith(f"| {cid} |"):
                out.append(s)
        i = next((k for k, s in enumerate(lines) if s.startswith(f"{cid} ") and "candidate test" in s[:60]), None)
        if i is not None:
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith(f"{cid} revision log:")), None)
            stop = block_end(lines, j) if j is not None else block_end(lines, i)
            out += [""] + lines[i:stop]
    if last_scans:
        idx = [k for k, s in enumerate(lines) if s.startswith("### S-")]
        for k in idx[-last_scans:]:
            out += [""] + lines[k:block_end(lines, k)]
    if rng:
        a, e = rng
        out += lines[a - 1:e]
    return out


# ----------------------------------------------------------------------------- weekly archive

def archive_ledger(lines, name, when, keep=3, close=(), index_lines=()):
    N = len(lines)
    b = section_bounds(lines)
    move = {}

    def mv(i, g):
        if i in move:
            raise SystemExit(f"line {i + 1} selected twice")
        move[i] = g

    groups = []

    def group(key, title):
        groups.append((key, title))

    # §6 scans
    a, e = b["6"]
    scans = [i for i in range(a, e) if re.match(r"### S-\d{3}", lines[i])]
    g6 = scans[:-keep] if keep else scans
    for i in g6:
        for k in range(i, block_end(lines, i)):
            mv(k, "s6")
        if block_end(lines, i) < N and lines[block_end(lines, i)] == "":
            mv(block_end(lines, i), "s6")
    group("s6", "§6 Scanner log")
    # §11 decision records
    a, e = b["11"]
    decs = [i for i in range(a, e) if lines[i].startswith("- D-") and not IS_DPTR.match(lines[i])]
    for i in decs[:-keep]:
        mv(i, "s11dec")
    group("s11dec", "§11 Forecast register — decision records")
    # §11 additions blocks
    adds = [i for i in range(a, e) if re.match(r"S-\d{3} additions \(", lines[i])]
    for n_, i in enumerate(adds[:-keep] if keep else adds):
        stop = adds[adds.index(i) + 1] if adds.index(i) + 1 < len(adds) else block_end(lines, i)
        k = i
        while k < stop and lines[k] != "":
            mv(k, "s11add")
            k += 1
    group("s11add", "§11 Forecast register — additions, resolutions and scoreboards")
    # §12a updates
    a, e = b["12a"]
    ups = [i for i in range(a, e) if re.match(r"S-\d{3} update \(", lines[i])]
    for i in ups[:-keep]:
        mv(i, "s12a")
    group("s12a", "§12a E-002 — per-run updates")
    # §12 screening lines
    a, e = b["12"]
    scr = [i for i in range(a, e) if re.match(r"- 20\d\d-\d\d-\d\d \(S-\d{3}", lines[i])]
    for i in scr[:-keep]:
        mv(i, "s12")
    group("s12", "§12 E-001 — screening log lines")
    # §7 rule-test lines
    a, e = b["7"]
    r3 = [i for i in range(a, e) if re.match(r"S-\d{3} \(", lines[i])]
    for i in r3[:-keep]:
        mv(i, "s7")
    group("s7", "§7 Rule-test log — per-run lines")
    # §10 checks (keep S-008c and the latest)
    a, e = b["10"]
    chk = [i for i in range(a, e) if lines[i].startswith("Check at S-")]
    keepc = {i for i in chk if lines[i].startswith("Check at S-008c")} | ({chk[-1]} if chk else set())
    for i in chk:
        if i not in keepc:
            mv(i, "s10")
    group("s10", "§10 Equity and circuit breaker — routine checks")
    # §5 radar lines
    a, e = b["5"]
    rad = [i for i in range(a, e) if re.match(r"- S-\d{3} radar", lines[i])]
    for i in rad[:-keep]:
        mv(i, "s5radar")
    group("s5radar", "§5 Candidates — radar entries")
    # closed candidates
    for cid in close:
        rows = [i for i in range(a, e) if lines[i].startswith(f"| {cid} |")]
        if len(rows) != 1:
            raise SystemExit(f"{cid}: table row found {len(rows)} times")
        mv(rows[0], "s5rows")
        t = [i for i in range(a, e) if lines[i].startswith(f"{cid} ") and "candidate test" in lines[i][:60]]
        lg = [i for i in range(a, e) if lines[i].startswith(f"{cid} revision log:")]
        if len(t) != 1 or len(lg) != 1:
            raise SystemExit(f"{cid}: candidate test / revision log not found exactly once")
        for k in range(t[0], block_end(lines, lg[0])):
            if k not in move:
                mv(k, "s5logs")
        if lines[block_end(lines, lg[0])] == "":
            mv(block_end(lines, lg[0]), "s5logs")
    group("s5rows", "§5 Candidates — closed table rows")
    group("s5logs", "§5 Candidates — closed candidate tests and revision logs")
    # §14 superseded lines
    if "14" in b:
        a, e = b["14"]
        for i in range(a + 1, e):
            if lines[i].startswith("- "):
                mv(i, "s14")
    group("s14", "§14 Superseded lines (header lines, replaced table rows, replaced lines)")

    if not move:
        return None
    ARCH = f"`moonshot/{name}`"

    def ids_of(key, pat):
        found = [re.search(pat, lines[i]) for i in sorted(k for k, g in move.items() if g == key)]
        found = [m.group(1) for m in found if m]
        return (found[0], found[-1]) if found else None

    ptr = {}
    sr = ids_of("s6", r"### (S-\d{3})")
    if sr:
        ptr["s6"] = f"{sr[0]} → {sr[1]} moved verbatim to {ARCH} (§6 there) on {when}; numbering continues below."
    dr = ids_of("s11dec", r"- (D-\d{3})")
    if dr:
        ptr["s11dec"] = f"- {dr[0]} → {dr[1]}: moved verbatim to {ARCH} (§11 there) on {when}."
    ar = ids_of("s11add", r"(S-\d{3}) additions")
    if ar:
        ptr["s11add"] = f"{ar[0]} → {ar[1]} additions, resolutions and scoreboards moved verbatim to {ARCH} (§11 there) on {when}."
    ur = ids_of("s12a", r"(S-\d{3}) update")
    if ur:
        ptr["s12a"] = f"{ur[0]} → {ur[1]} updates moved verbatim to {ARCH} (§12a there) on {when}."
    cr = ids_of("s12", r"\((S-\d{3})")
    if cr:
        ptr["s12"] = f"- Screening lines {cr[0]} → {cr[1]} moved verbatim to {ARCH} (§12 there) on {when}."
    rr = ids_of("s7", r"(S-\d{3}) \(")
    if rr:
        ptr["s7"] = f"{rr[0]} → {rr[1]} moved verbatim to {ARCH} (§7 there) on {when}."
    if any(g == "s10" for g in move.values()):
        ptr["s10"] = f"Routine checks moved verbatim to {ARCH} (§10 there) on {when}; the R4 hit (S-008c) and the latest check stay."
    rd = ids_of("s5radar", r"- (S-\d{3}) radar")
    if rd:
        ptr["s5radar"] = f"- Radar entries {rd[0]} → {rd[1]} moved verbatim to {ARCH} (§5 there) on {when}."
    if close:
        ptr["close"] = (f"Closed candidates {', '.join(close)} — table rows, candidate tests and revision logs moved "
                        f"verbatim to {ARCH} (§5 there) on {when}. Final state and re-open trigger:")
    if any(g == "s14" for g in move.values()):
        ptr["s14"] = f"Superseded lines through {when} moved verbatim to {ARCH} (§14 there)."

    # where pointers go (before the first kept item of each group, or after the last moved one)
    first_kept = {
        "s6": next((i for i in scans if i not in move), None),
        "s11dec": next((i for i in decs if i not in move), None),
        "s11add": next((i for i in adds if i not in move), None),
        "s12a": next((i for i in ups if i not in move), None),
        "s12": next((i for i in scr if i not in move), None),
        "s7": next((i for i in r3 if i not in move), None),
        "s10": next((i for i in chk if i not in move), None),
        "s5radar": next((i for i in rad if i not in move), None),
    }
    before = {}
    for g, text in ptr.items():
        if g in ("close", "s14"):
            continue
        at = first_kept.get(g)
        if at is None:
            at = max(i for i, gg in move.items() if gg == g) + 1
            while at < N and at in move:
                at += 1
        before.setdefault(at, []).extend([text, ""] if g == "s6" else [text])
    if "close" in ptr:
        a5, e5 = section_bounds(lines)["5"]
        idx = [i for i in range(a5, e5) if re.match(r"- C-\d{3} ", lines[i])]
        at = (max(idx) + 1) if idx else next(i for i in range(a5, e5) if lines[i].startswith("Radar — scheduled events"))
        before.setdefault(at, []).extend([ptr["close"]] + list(index_lines))
    if "s14" in ptr:
        at = section_bounds(lines)["14"][1]
        before.setdefault(at, []).append(ptr["s14"])

    live = []
    for i, s in enumerate(lines):
        for t in before.get(i, []):
            live.append((t, None))
        if i not in move:
            live.append((s, i))
    for t in before.get(N, []):
        live.append((t, None))
    arch = []
    src_raw = "\n".join(lines).encode("utf-8")
    src_sha = hashlib.sha256(src_raw).hexdigest()
    arch.append((f"# Moonshot Ledger — Archive {when}", None))
    arch.append(("", None))
    arch.append((f"Frozen. Lines moved verbatim from `moonshot/ledger.md` on {when} by the weekly review. Source "
                 f"before the move: {len(src_raw):,} bytes, {N:,} lines, sha256 {src_sha}. Every line under a "
                 f"heading below is byte-identical to the source and in source order; only the headings and this "
                 f"paragraph are new. Do not edit this file. Section numbers match the ledger.", None))
    for key, title in groups:
        idx = sorted(i for i, g in move.items() if g == key)
        if not idx:
            continue
        arch += [("", None), (f"## {title}", None), ("", None)]
        for i in idx:
            arch.append((lines[i], i))
    if arch[-1][0] != "":
        arch.append(("", None))
    # verification
    origins = [o for _, o in live if o is not None] + [o for _, o in arch if o is not None]
    if sorted(origins) != list(range(N)):
        raise SystemExit("ARCHIVE VERIFY FAILED: a source line is missing or duplicated")
    for t, o in live + arch:
        if o is not None and t != lines[o]:
            raise SystemExit(f"ARCHIVE VERIFY FAILED: line {o + 1} altered")
    lo = [o for _, o in live if o is not None]
    if lo != sorted(lo):
        raise SystemExit("ARCHIVE VERIFY FAILED: live order changed")
    added_l = Counter(t for t, o in live if o is None)
    added_a = Counter(t for t, o in arch if o is None)
    lt, at_ = [t for t, _ in live], [t for t, _ in arch]
    if (Counter(lt) - added_l) + (Counter(at_) - added_a) != Counter(lines):
        raise SystemExit("ARCHIVE VERIFY FAILED: multiset check")
    summary = {"source_bytes": len(src_raw), "source_sha256": src_sha, "moved_lines": len(move),
               "kept_lines": N - len(move),
               "moved_by_group": {k: sum(1 for g in move.values() if g == k) for k, _ in groups}}
    return lt, at_, summary


# ----------------------------------------------------------------------------- transcript / project docs

def transcript_files(max_age_h=12):
    roots = [os.path.expanduser("~/.claude/projects")]
    fs = []
    now = time.time()
    for r in roots:
        for p in glob.glob(os.path.join(r, "**", "*.jsonl"), recursive=True):
            try:
                if now - os.path.getmtime(p) <= max_age_h * 3600:
                    fs.append(p)
            except OSError:
                pass
    return sorted(fs, key=os.path.getmtime, reverse=True)


def _tool_texts(obj):
    msg = obj.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_result":
                parts = c.get("content")
                if isinstance(parts, str):
                    yield parts
                elif isinstance(parts, list):
                    for p in parts:
                        if isinstance(p, dict) and isinstance(p.get("text"), str):
                            yield p["text"]
    tur = obj.get("toolUseResult")
    if isinstance(tur, dict):
        yield json.dumps(tur)
    elif isinstance(tur, str):
        yield tur


def find_project_read(path, max_age_h=12):
    """Latest project_read result for `path` in this machine's recent transcripts → (bytes, source)."""
    for f in transcript_files(max_age_h):
        found = None
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "project_read" not in line or path not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for t in _tool_texts(obj):
                    try:
                        j = json.loads(t)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if isinstance(j, dict) and j.get("method") == "project_read" and j.get("path") == path:
                        found = j
        if found:
            if isinstance(found.get("content"), str):
                return found["content"].encode("utf-8"), f"inline result in {f}"
            if found.get("local_file") and Path(found["local_file"]).exists():
                return Path(found["local_file"]).read_bytes(), f"local file {found['local_file']}"
    return None, None


# ----------------------------------------------------------------------------- KOD paper ledger (read-only)

KOD_BRANCH = "claude/idx-signals-test-repo-ds0jw7"


def kod_repo(hint=None):
    cands = [hint] if hint else []
    cands += [os.path.expanduser("~/kod-machine"), "/home/claude/kod-machine", "/home/user/KOD-Machine",
              os.path.expanduser("~/KOD-Machine")]
    cands += [str(Path(p).parents[2]) for p in glob.glob("/home/*/*/idx-signals/paper/ledger.jsonl")]
    for c in cands:
        if c and (Path(c) / "idx-signals" / "paper" / "ledger.jsonl").exists():
            return c
    return None


def kod_us(date, hint=None):
    repo = kod_repo(hint)
    if not repo:
        return None, "KOD checkout not found on this machine"
    note = ""
    try:
        subprocess.run(["git", "-C", repo, "fetch", "--quiet", "origin", KOD_BRANCH], timeout=90,
                       check=True, capture_output=True)
        data = subprocess.run(["git", "-C", repo, "show", f"origin/{KOD_BRANCH}:idx-signals/paper/ledger.jsonl"],
                              timeout=30, check=True, capture_output=True).stdout.decode("utf-8")
        note = f"origin/{KOD_BRANCH} (fetched)"
    except Exception as e:
        data = (Path(repo) / "idx-signals" / "paper" / "ledger.jsonl").read_text(encoding="utf-8")
        note = f"working tree (fetch failed: {repr(e)[:80]})"
    rows = []
    for line in data.split("\n"):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = r.get("decision_id") or r.get("scan_id") or ""
        if r.get("market") == "US" and f"SCAN-US-{date}" in rid and (r.get("instrument") or {}).get("ticker"):
            rows.append(r)
    return rows, f"{repo} · {note}"


# ----------------------------------------------------------------------------- commands

def cmd_clock(a):
    now = parse_iso(a.at) if a.at else utcnow()
    e = to_et(now)
    d = e.date()
    print("NOW  " + fmt_triple(now))
    print(f"US date {d} ({d.strftime('%a')}) · {market_phase(now)}")
    if is_session(d):
        o, c = session_open_utc(d), session_close_utc(d)
        nd = " (+1d)" if to_wib(c).date() != to_wib(o).date() else ""
        print(f"Session {d}: {to_et(o):%H:%M}–{to_et(c):%H:%M} ET = {to_wib(o):%H:%M}–{to_wib(c):%H:%M}{nd} WIB "
              f"({iso(o)} → {iso(c)})")
    print(f"Previous session {prev_session(d)} · next session {next_session(d)} · last completed session "
          f"{last_completed_session(now)}")
    a1, b1 = dst_window_utc(d.year)
    print(f"US DST {d.year}: {iso(a1)} → {iso(b1)} (ET = UTC−4 inside, UTC−5 outside; WIB = UTC+7, no DST)")
    n = cal_note(d)
    if n:
        print(n)


def cmd_cal(a):
    if a.sessions:
        d, n = a.sessions
        ss = sessions_from(d, int(n))
        print(" ".join(x.isoformat() for x in ss))
        last = ss[-1]
        hh, mm = close_hm(last)
        print(f"deadline {last} {hh:02d}:{mm:02d} America/New_York = {iso(session_close_utc(last))} = "
              f"{to_wib(session_close_utc(last)).strftime('%Y-%m-%d %H:%M')} WIB")
        for x in ss:
            if cal_note(x):
                print(cal_note(x))
                break
    if a.check:
        d = as_date(a.check)
        msg = "session" if is_session(d) else ("weekend" if d.weekday() >= 5 else "NYSE holiday")
        if is_session(d) and close_hm(d) != (16, 0):
            msg += f" (early close {close_hm(d)[0]:02d}:{close_hm(d)[1]:02d} ET)"
        print(f"{d}: {msg}. {cal_note(d)}".strip())


def cmd_projdoc(a):
    data, src = find_project_read(a.path, a.max_age)
    if data is None:
        print(f"NOT FOUND: no project_read result for {a.path} in transcripts of the last {a.max_age} h")
        return 3
    Path(a.out).write_bytes(data)
    print(f"{a.path} → {a.out} · {len(data):,} bytes · sha256 {hashlib.sha256(data).hexdigest()} · {src}")
    return 0


def cmd_bars(a):
    net = Net()
    now = utcnow()
    for t in a.tickers:
        res = get_bars(net, t)
        print(f"== {t.upper()} · chartexchange {res['cx_url'] or '—'} · stockanalysis {res['sa_url'] or '—'}")
        for line in freshness(res, now):
            print("   " + line)
        for n_ in res["notes"]:
            print("   note: " + n_)
        dates = sorted(set(res["cx"]) | set(res["sa"]), reverse=True)
        if a.since:
            dates = [d for d in dates if d >= a.since]
        for d in dates[: a.n]:
            cx, sa = res["cx"].get(d), res["sa"].get(d)
            st = compare_bars(cx, sa)
            if session_close_utc(d) > now:
                st += ", INTRADAY partial"
            if st == "AGREE":
                print(f"   {d}  {bar_str(cx)}  [both]")
            else:
                print(f"   {d}  cx {bar_str(cx)} | sa {bar_str(sa)}  [{st}]")
        if a.pct and len(dates) >= 2:
            d0 = dates[0]
            prev = next((x for x in dates[1:] if x < d0), None)
            if prev:
                b0 = res["sa"].get(d0) or res["cx"].get(d0)
                b1 = res["sa"].get(prev) or res["cx"].get(prev)
                print(f"   {d0}: close {fmt_pct(pct_change(b0['c'], b1['c']))} vs {prev} · open {fmt_pct(pct_change(b0['o'], b1['c']))} · "
                      f"open→close {fmt_pct(pct_change(b0['c'], b0['o']))} · open→high {fmt_pct(pct_change(b0['h'], b0['o']))} · "
                      f"open→low {fmt_pct(pct_change(b0['l'], b0['o']))}")
    return 0


def cmd_resolve(a):
    net = Net()
    now = parse_iso(a.at) if a.at else utcnow()
    items = []
    if a.registry:
        recs = reg_read(a.registry)
        st = reg_status(recs)
        for s in st:
            if s["closed"] and not a.all:
                continue
            if a.only and s["id"] not in a.only:
                continue
            p = dict(s["payload"])
            p["id"], p["kind"] = s["id"], s["kind"]
            items.append(p)
    if a.item:
        for js in a.item:
            items.append(json.loads(js))
    if not items:
        print("No open registered items.")
        return 0
    cache = {}
    new_records = []
    print(f"Resolution as of {fmt_triple(now)} (daily bars; both barriers in one bar = CENSORED)")
    for it in items:
        t = it["ticker"].upper()
        if t not in cache:
            cache[t] = get_bars(net, t)
        res = cache[t]
        r = resolve_item(it, res, now)
        lines, recs = summarize_resolution(it, r, res, now)
        for ln in lines:
            print(ln)
        for n_ in res["notes"]:
            print("  note: " + n_)
        for rec in recs:
            new_records.append((it, rec))
    if a.commit and a.registry:
        recs = reg_read(a.registry)
        latest = {}
        for r in recs:
            if r["kind"] == "RESOLUTION":
                latest[(r["payload"]["item"], int(r["payload"]["col"]))] = r["payload"]
        n = 0
        for it, rec in new_records:
            prev = latest.get((it["id"], rec["col"]))
            if rec["status"] == "OPEN" and not prev:
                continue
            if prev and prev["status"] == rec["status"] and prev.get("date") == rec["date"] and prev.get("final") == rec["final"]:
                continue
            payload = {"item": it["id"], "col": rec["col"], "status": rec["status"], "date": rec["date"],
                       "final": rec["final"], "text": rec["text"]}
            reg_append(a.registry, "RESOLUTION", f"{it['id']}#c{rec['col']}", a.run or "?", payload, now)
            n += 1
        h, cnt = reg_head(reg_read(a.registry))
        print(f"register: {n} resolution record(s) appended · n={cnt} head={h[:16]}")
    return 0


def cmd_reg(a):
    path = a.file
    if a.action == "verify":
        try:
            recs = reg_read(path)
        except RegError as e:
            print(f"REGISTER INVALID: {e}")
            return 2
        h, n = reg_head(recs)
        kinds = Counter(r["kind"] for r in recs)
        print(f"register OK · {n} records · head {h} · " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
        if a.ledger:
            missing, archived = decision_check(recs, read_lines(a.ledger))
            live = sum(1 for r in recs if r["kind"] == "DECISION") - len(missing) - len(archived)
            note = (f"; {len(archived)} archived per the ledger's pointer lines ({archived[0]} → {archived[-1]})"
                    if archived else "")
            if missing:
                print("ledger decision text: MISMATCH — registered decision line(s) not in the ledger and not "
                      "covered by an archive pointer: " + ", ".join(missing) + note)
            else:
                print(f"ledger decision text: OK — {live} registered decision record(s) match the ledger verbatim" + note)
        return 0
    if a.action == "add":
        payload = json.loads(Path(a.payload_file).read_text()) if a.payload_file else json.loads(a.payload or "{}")
        rec = reg_append(path, a.kind, a.id, a.run, payload)
        print(f"appended seq {rec['seq']} {rec['kind']} {rec['id']} · head {rec['hash'][:16]}")
        return 0
    if a.action == "items":
        st = reg_status(reg_read(path))
        for s in st:
            if s["closed"] and not a.all:
                continue
            p = s["payload"]
            cols = " · ".join(f"col{i + 1} {c['status'] + (' ' + c['date'] if c.get('date') else '') + ('' if c.get('final') else ' (prov.)') if c else 'open'}"
                              for i, c in enumerate(s["cols"]))
            print(f"{s['id']} [{s['kind']}] {p['ticker']} ref {p.get('ref_price') or 'open ' + p['ref_date']} · {cols}")
        return 0
    if a.action == "show":
        for r in reg_read(path):
            if r["id"] == a.id or (r["kind"] == "RESOLUTION" and r["payload"].get("item") == a.id):
                print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if a.action == "freeze":
        # register every '@@ decision' line and '@@ items' record of a patch file
        text = Path(a.patch).read_text(encoding="utf-8")
        blocks = parse_patch(text.replace("\r", ""))
        n = 0
        for b in blocks:
            if b["head"] == "decision":
                for ln in b["body"]:
                    m = re.match(r"- (D-\d{3}) ", ln)
                    reg_append(path, "DECISION", m.group(1), a.run, {"text": ln, "sha256": hashlib.sha256(ln.encode()).hexdigest()})
                    n += 1
            if b["head"] == "items":
                for ln in b["body"]:
                    if ln.strip():
                        j = json.loads(ln)
                        reg_append(path, j.pop("kind"), j.pop("id"), a.run, j)
                        n += 1
        h, cnt = reg_head(reg_read(path))
        print(f"register: {n} record(s) frozen · n={cnt} head={h[:16]}")
        return 0
    return 1


def cmd_ledger(a):
    if a.action == "outline":
        for ln in outline(read_lines(a.file), a.file):
            print(ln)
        return 0
    if a.action == "get":
        rng = tuple(int(x) for x in a.lines.split("-")) if a.lines else None
        print("\n".join(get_parts(read_lines(a.file), a.sec, a.id, a.last_scans, rng)))
        return 0
    if a.action == "apply":
        old = read_lines(a.file)
        text = Path(a.patch).read_text(encoding="utf-8").replace("\r", "")
        new, report, items = apply_patch_text(old, text, a.run)
        problems, nrem, nadd = guard(old, new)
        for r in report:
            print("  " + r)
        if problems:
            print("GUARD FAILED: " + "; ".join(problems))
            return 2
        write_lines(a.out, new)
        ob, nb = len("\n".join(old).encode()), len("\n".join(new).encode())
        print(f"GUARD OK · {nadd} line(s) added, {nrem} replaced/moved · {ob:,} → {nb:,} bytes · "
              f"new sha256 {sha_lines(new)} → {a.out}")
        if items:
            print(f"  note: {len(items)} '@@ items' record(s) are registered by 'reg freeze', not written to the ledger")
        return 0
    if a.action == "guard":
        old, new = read_lines(a.file), read_lines(a.new)
        problems, nrem, nadd = guard(old, new)
        if problems:
            print("GUARD FAILED: " + "; ".join(problems))
            return 2
        print(f"GUARD OK · {nadd} added, {nrem} replaced/moved · {sha_lines(old)[:16]} → {sha_lines(new)[:16]}")
        return 0
    if a.action == "e002":
        for ln in e002_readout(read_lines(a.file)):
            print(ln)
        return 0
    if a.action == "same":
        x, y = Path(a.file).read_bytes(), Path(a.new).read_bytes()
        hx, hy = hashlib.sha256(x).hexdigest(), hashlib.sha256(y).hexdigest()
        print(("SAME" if hx == hy else "DIFFERENT") + f" · {hx[:16]} ({len(x):,} B) vs {hy[:16]} ({len(y):,} B)")
        return 0 if hx == hy else 2
    if a.action == "archive":
        lines = read_lines(a.file)
        idx = Path(a.index_file).read_text(encoding="utf-8").strip("\n").split("\n") if a.index_file else []
        close = [c for c in (a.close or "").split(",") if c]
        r = archive_ledger(lines, a.name, a.when, a.keep, close, idx)
        if r is None:
            print("Nothing to archive.")
            return 0
        live, arch, summ = r
        out = Path(a.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "ledger.md").write_text("\n".join(live), encoding="utf-8")
        (out / a.name).write_text("\n".join(arch), encoding="utf-8")
        lb, ab = len("\n".join(live).encode()), len("\n".join(arch).encode())
        print(json.dumps(summ, indent=1))
        print(f"ARCHIVE VERIFIED · live {lb:,} B sha256 {hashlib.sha256(chr(10).join(live).encode()).hexdigest()} · "
              f"archive {ab:,} B sha256 {hashlib.sha256(chr(10).join(arch).encode()).hexdigest()} → {out}")
        return 0
    return 1


def _flags(title):
    t = title.lower()
    f = []
    if re.search(r"\b(offering|priced|pricing|registered direct|private placement|at-the-market|atm program|warrants?|convertible|notes due|shelf registration|mixed shelf)\b", t):
        f.append("SUPPLY")
    if re.search(r"\b(topline|top-line|phase [123]|phase i{1,3}\b|pivotal|primary endpoint|fda|approval|approves|approved|pdufa|crl|complete response|clinical hold)\b", t):
        f.append("PROB")
    if re.search(r"\b(acquire|acquisition|merger|to be acquired|definitive agreement|tender offer|take private|go private|buyout|strategic alternatives)\b", t):
        f.append("NAV")
    if re.search(r"\b(guidance|raises|preliminary|record revenue|contract|award|order|agreement|partnership|collaboration|backlog)\b", t):
        f.append("ECON")
    return f


def cmd_wire(a):
    net = Net()
    now = utcnow()
    def when(x, default):
        if not x:
            return default
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", x)
        if m:                                   # HH:MM = today (ET) at that time
            return et_wall_to_utc(to_et(now).date(), int(m.group(1)), int(m.group(2)))
        return parse_iso(x)
    since = when(a.since, et_wall_to_utc(prev_session(to_et(now).date()), 16, 0))
    until = when(a.until, now)
    days = []
    x = to_et(since).date()
    while x <= to_et(until).date():
        days.append(x)
        x += dt.timedelta(days=1)
    items, notes = [], []
    today = to_et(now).date()
    for d in days:
        url = "https://www.stocktitan.net/news/today" if d == today else f"https://www.stocktitan.net/news/{d.isoformat()}/"
        f = net.get(url, ttl=600)
        if not f.ok:
            notes.append(f"{url}: {f.status} {f.note}")
            continue
        got = parse_st_feed(f.text)
        notes.append(f"{url}: {len(got)} items ({got[-1]['et'].strftime('%H:%M') if got else '—'} → "
                     f"{got[0]['et'].strftime('%H:%M') if got else '—'} ET) sha256 {f.sha[:12]}")
        items += got
    se, ue = to_et(since).replace(tzinfo=None), to_et(until).replace(tzinfo=None)
    sel = [i for i in items if se <= i["et"] <= ue]
    seen, uniq = set(), []
    for i in sorted(sel, key=lambda i: i["et"]):
        k = i["href"] or i["title"]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(i)
    shown = 0
    for i in uniq:
        exch = {e for _, e in i["tickers"]}
        if not a.otc and exch and exch <= {"OTC"}:
            continue
        fl = _flags(i["title"])
        if a.min_impact and (i["impact"] or 0) < a.min_impact and not (fl and a.keep_flagged):
            continue
        if a.flagged and not fl:
            continue
        tk = ",".join(f"{s}:{e}" for s, e in i["tickers"]) or "—"
        tags = (" #" + " #".join(i["tags"])) if i["tags"] and a.tags else ""
        print(f"{i['et'].strftime('%m-%d %H:%M')} {tk:<22} i{i['impact'] or '-'} s{i['sentiment'] or '-'} "
              f"{'[' + '/'.join(fl) + '] ' if fl else ''}{i['title'][:a.width]}{tags}")
        shown += 1
    print(f"-- {shown} shown of {len(uniq)} items in window {to_et(since).strftime('%m-%d %H:%M')} → "
          f"{to_et(until).strftime('%m-%d %H:%M')} ET (OTC {'included' if a.otc else 'excluded'}"
          f"{', min impact ' + str(a.min_impact) if a.min_impact else ''})")
    for n_ in notes:
        print("   source: " + n_)
    return 0


def cmd_news(a, filings=False):
    net = Net()
    for t in a.tickers:
        url = f"https://www.stocktitan.net/{'sec-filings' if filings else 'news'}/{t.upper()}/"
        f = net.get(url, ttl=600)
        if not f.ok:
            print(f"== {t.upper()}: {f.status} {f.note}")
            continue
        its = parse_st_ticker(f.text)
        print(f"== {t.upper()} {'filings' if filings else 'news'} ({len(its)} items; sha256 {f.sha[:12]})")
        for i in its[: a.n]:
            e = to_et(i["utc"])
            if filings:
                body = re.sub(r"^\d\d/\d\d/\d{4} \d\d:\d\d [AP]M (Filing )?", "", i["text"])
                print(f"   {e.strftime('%Y-%m-%d %H:%M')} {e.tzname()} [{i['form'] or '?'}] {body[:150]}")
            else:
                print(f"   {e.strftime('%Y-%m-%d %H:%M')} {e.tzname()} {i['title'][:150]}")
    return 0


def cmd_quote(a):
    net = Net()
    for t in a.tickers:
        url = f"https://stockanalysis.com/stocks/{t.lower()}/"
        f = net.get(url, ttl=120, bust=True)
        if not f.ok:
            print(f"== {t.upper()}: {f.status} {f.note}")
            continue
        qd = parse_sa_quote(f.text)
        if qd["exchange"]:
            ex = {"NASDAQ": "nasdaq", "NYSE": "nyse", "NYSEAMERICAN": "nyseamerican"}.get(qd["exchange"])
            if ex:
                net.state["exch"][t.upper()] = ex
                net.save()
        print(f"== {t.upper()} ({qd['exchange'] or '?'}) stockanalysis quote page, fetched {fmt_triple(utcnow())[:20]}; "
              "each print carries its own time label — historical, not executable")
        for p in qd["prints"]:
            lab = p['label'] if p['label'] != "(no label)" else "Latest (regular session or unlabelled)"
            print(f"   {lab}: {p['price']} ({p['change']}, {p['pct']}%) at {p['time']}")
        if qd["fields"]:
            print("   " + " · ".join(f"{k} {v}" for k, v in qd["fields"].items()))
    return 0


STATS_KEYS = ["Market Cap", "Enterprise Value", "Shares Outstanding", "Float", "Short % of Float", "Short Interest",
              "Average Volume (20 Days)", "Cash & Cash Equivalents", "Total Debt", "Net Cash", "Operating Cash Flow",
              "Free Cash Flow", "Capital Expenditures", "Revenue", "Net Income", "Shares Change (YoY)",
              "Shares Change (QoQ)", "Earnings Date", "52-Week Price Change", "Analyst Count", "Price Target",
              "_last_updated"]


def cmd_stats(a):
    net = Net()
    for t in a.tickers:
        url = f"https://stockanalysis.com/stocks/{t.lower()}/statistics/"
        f = net.get(url, ttl=3600)
        if not f.ok:
            print(f"== {t.upper()}: {f.status} {f.note}")
            continue
        s = parse_sa_stats(f.text)
        print(f"== {t.upper()} statistics (stockanalysis; period ends not shown on the page)")
        print("   " + " · ".join(f"{k.strip('_')} {s[k]}" for k in STATS_KEYS if k in s))
    return 0


def _movers(net, url, label):
    f = net.get(url, ttl=300, bust=True)
    if not f.ok:
        print(f"{label}: {f.status} {f.note}")
        return []
    return parse_sa_movers(f.text)


def cmd_premarket(a):
    net = Net()
    now = utcnow()
    today = to_et(now).date().isoformat()
    for blk in _movers(net, "https://stockanalysis.com/markets/premarket/", "premarket"):
        rows = blk["rows"]
        dates = Counter(str(r.get("premarketDate")) for r in rows)
        stale = [d for d in dates if d != today]
        print(f"== stockanalysis pre-market {blk['dir'] or '?'} ({blk['main']}) · {len(rows)} rows · dates {dict(dates)}"
              + (" · STALE ROWS" if stale else ""))
        for r in rows:
            cap = r.get("marketCap")
            big = cap is not None and D(cap) >= D(a.min_cap)
            print(f"   {r.get('no'):>2} {r.get('s'):<6} {fmt_pct(r.get('premarketChangePercent', 0)):>9} "
                  f"{q(r.get('premarketPrice') or 0)} vol {int(r.get('premarketVolume') or 0):,} cap "
                  f"{fmt_money(cap) if cap is not None else '—'}{'  ≥cap' if big else ''}  {str(r.get('n'))[:40]}")
    return 0


def cmd_gainers(a):
    net = Net()
    for blk in _movers(net, "https://stockanalysis.com/markets/gainers/", "gainers"):
        rows = blk["rows"]
        dates = Counter(str(r.get("priceDate")) for r in rows)
        print(f"== stockanalysis gainers · {len(rows)} rows · priceDate {dict(dates)}")
        for r in rows:
            ch, cap = D(r.get("change") or 0), r.get("marketCap")
            pre = (D(cap) / (1 + ch / 100)) if cap is not None else None
            print(f"   {r.get('no'):>2} {r.get('s'):<6} {fmt_pct(ch):>9} {q(r.get('price') or 0)} cap {fmt_money(cap) if cap is not None else '—'}"
                  f" (pre-move {fmt_money(pre) if pre is not None else '—'}) {str(r.get('n'))[:40]}")
    return 0


INSTRUMENT_EXCL = re.compile(r"\b(ETF|ETN|Fund|2X|3X|Leveraged|Inverse|Warrants?|Rights?|Units?)\b", re.I)


def cmd_screen(a):
    """E-001 screen: stockanalysis gainers (date-checked) + extra tickers, verified on daily bars."""
    net = Net()
    now = utcnow()
    day = a.date or last_completed_session(now).isoformat()
    minmove, mincap = D(a.min_move), D(a.min_cap)
    cands, notes = {}, []
    for blk in _movers(net, "https://stockanalysis.com/markets/gainers/", "gainers"):
        rows = blk["rows"]
        dates = Counter(str(r.get("priceDate")) for r in rows)
        notes.append(f"gainers list: {len(rows)} rows, priceDate {dict(dates)}")
        if rows and all(str(r.get("priceDate")) != day for r in rows):
            notes.append(f"gainers list is not for {day} → not used (STALE)")
            continue
        for r in rows:
            if str(r.get("priceDate")) != day:
                continue
            ch = D(r.get("change") or 0)
            cap = r.get("marketCap")
            pre = D(cap) / (1 + ch / 100) if cap is not None else None
            cands[str(r["s"])] = {"src": "gainers", "change": ch, "pre_cap": pre, "name": str(r.get("n")),
                                  "price": r.get("price")}
        if rows and str(rows[-1].get("priceDate")) == day and D(rows[-1].get("change") or 0) >= minmove:
            notes.append(f"LIST TRUNCATED: the last of {len(rows)} rows is still ≥ +{minmove}% — names beyond it are not visible")
    for t in (a.extra or "").split(","):
        if t.strip():
            cands.setdefault(t.strip().upper(), {"src": "extra", "change": None, "pre_cap": None, "name": "", "price": None})
    print(f"E-001 screen for {day} (move ≥ +{minmove}%, pre-event cap ≥ {fmt_money(mincap)}) · {fmt_triple(now)}")
    if session_close_utc(day) > now:
        print("   WARNING: this session has not closed yet — every value below is intraday, not a closing value")
    for n_ in notes:
        print("   " + n_)
    hits = []
    for t, c in sorted(cands.items(), key=lambda kv: -(kv[1]["change"] or 0)):
        if c["change"] is not None and c["change"] < minmove:
            continue
        excl = INSTRUMENT_EXCL.search(c["name"] or "")
        if c["src"] == "gainers" and (c["pre_cap"] is None or c["pre_cap"] < mincap):
            print(f"   {t:<6} {fmt_pct(c['change']):>9} pre-move cap {fmt_money(c['pre_cap']) if c['pre_cap'] is not None else '—'} → below the cap floor")
            continue
        if excl:
            print(f"   {t:<6} {fmt_pct(c['change']):>9} → instrument excluded ({excl.group(0)}: {c['name'][:40]})")
            continue
        res = get_bars(net, t)
        d0 = res["sa"].get(day) or res["cx"].get(day)
        prevd = prev_session(day).isoformat()
        d1 = res["sa"].get(prevd) or res["cx"].get(prevd)
        if not (d0 and d1):
            print(f"   {t:<6} bars missing for {day}/{prevd} → verify by hand ({'; '.join(res['notes'])})")
            continue
        mv = pct_change(d0["c"], d1["c"])
        conf = compare_bars(res["cx"].get(day), res["sa"].get(day))
        line = (f"   {t:<6} close {q(d0['c'])} vs {q(d1['c'])} = {fmt_pct(mv)} · open {q(d0['o'])} high {q(d0['h'])} "
                f"low {q(d0['l'])} · bars {conf} · pre-move cap {fmt_money(c['pre_cap']) if c['pre_cap'] is not None else 'check stats'}")
        if mv >= minmove:
            hits.append(t)
            print(line + "  → CANDIDATE (check: news-driven? capped deal? eToro?)")
        else:
            print(line + "  → below the move threshold on the close")
    print(f"-- {len(hits)} candidate(s) for the model's E-001 judgment: {', '.join(hits) or 'none'}")
    return 0


def cmd_kod(a):
    rows, note = kod_us(a.date, a.repo)
    if rows is None:
        print(f"KOD: {note}")
        return 3
    print(f"KOD US paper scan decisions for {a.date} · {note} · {len(rows)} record(s) (≥ +30% day detector; read-only)")
    for r in rows:
        ev = r.get("evidence", {})
        ins = r.get("instrument", {})
        r1 = ev.get("ret1")
        print(f"   {ins.get('ticker', '?'):<6} ret1 {fmt_pct(D(str(r1)) * 100) if r1 is not None else '—'} · "
              f"decision {r.get('decision')} · {r.get('decided_at')}")
    return 0


def cmd_stress(a):
    eq, fx = D(a.equity_aud), D(a.audusd)
    pos_usd = eq * fx
    comm = D(a.commission_usd) / pos_usd * 100
    costs = {"AUD-funded": 2 * D(a.fx_fee) + 2 * comm, "USD-funded": 2 * comm}
    print(f"Whole position: AUD {q(eq, 2)} ≈ USD {q(pos_usd, 2)} at AUDUSD {fx} · commission ${a.commission_usd}/side = "
          f"{q(comm, 3)}% · FX {a.fx_fee}% per conversion · spread excluded · costs: "
          + " / ".join(f"{k} {q(v, 3)}%" for k, v in costs.items()))
    rows = [("ordinary (stop + slippage)", -(D(a.stop) + D(a.slip)))]
    for g in a.gap or []:
        rows.append((f"gap / halt-then-gap −{g}%", -D(g)))
    if a.tp:
        rows.append((f"take-profit +{a.tp}%", D(a.tp)))
    for name, mv in rows:
        cells = []
        for k, c in costs.items():
            net_pct = mv - c
            cells.append(f"{k} {fmt_pct(net_pct)} = {'−' if net_pct < 0 else '+'}AUD {q(abs(eq * net_pct / 100), 2)}")
        print(f"  {name:<30} move {fmt_pct(mv):>8} → " + " · ".join(cells))
    return 0


def cmd_pct(a):
    print(f"{fmt_pct(pct_change(a.new, a.old))} ({a.new} vs {a.old})")
    return 0


def cmd_barriers(a):
    ref = D(a.ref)
    parts = [f"+{a.up}% {q(ref * (1 + D(a.up) / 100))}"]
    for d in (a.down or "5,10").split(","):
        parts.append(f"−{d}% {q(ref * (1 - D(d) / 100))}")
    print(f"reference {a.ref}: " + " · ".join(parts))
    return 0


def cmd_cap(a):
    sh, px = parse_abbrev(a.shares), D(a.price)
    print(f"{fmt_money(sh * px)} ({a.shares} shares × ${a.price})")
    return 0


def self_hash_ok(path=None):
    b = Path(path or __file__).read_bytes()
    m = re.search(rb'^SELF_SHA256 = "([0-9a-f]{64})"$', b, re.M)
    if not m:
        return False, "no SELF_SHA256 line"
    calc = hashlib.sha256(b[:m.start(1)] + b"0" * 64 + b[m.end(1):]).hexdigest()
    return calc == m.group(1).decode(), calc


def cmd_stamp(a):
    p = Path(a.file)
    b = p.read_bytes()
    m = re.search(rb'^SELF_SHA256 = "([0-9a-f]{64})"$', b, re.M)
    zero = b[:m.start(1)] + b"0" * 64 + b[m.end(1):]
    h = hashlib.sha256(zero).hexdigest().encode()
    p.write_bytes(zero[:m.start(1)] + h + zero[m.end(1):])
    print(f"stamped {p} · self-hash {h.decode()} · file sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")
    return 0


def _check(name, cond, fails):
    if not cond:
        fails.append(name)


def cmd_selftest(a):
    fails = []
    ok, h = self_hash_ok()
    print(f"msx {VERSION} · python {sys.version.split()[0]} · self-hash {'OK' if ok else 'MISMATCH'} ({h[:16]})")
    if not ok:
        fails.append("self-hash")
    # calendar
    _check("dst-off", et_tz(parse_iso("2026-11-01T05:59:00Z")).utcoffset(None) == dt.timedelta(hours=-4), fails)
    _check("dst-on", et_tz(parse_iso("2026-11-01T06:00:00Z")).utcoffset(None) == dt.timedelta(hours=-5), fails)
    _check("dst-spring", et_tz(parse_iso("2027-03-14T07:00:00Z")).utcoffset(None) == dt.timedelta(hours=-4), fails)
    _check("holiday", not is_session("2026-11-26") and is_session("2026-11-27") and close_hm("2026-11-27") == (13, 0), fails)
    _check("sessions", [d.isoformat() for d in sessions_from("2026-10-13", 5)] ==
           ["2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19"], fails)
    _check("sessions-thanksgiving", [d.isoformat() for d in sessions_from("2026-11-24", 3)] ==
           ["2026-11-24", "2026-11-25", "2026-11-27"], fails)
    _check("open-utc", iso(session_open_utc("2026-11-02")) == "2026-11-02T14:30:00Z", fails)
    _check("lcs", last_completed_session(parse_iso("2026-10-13T19:59:00Z")).isoformat() == "2026-10-12", fails)
    _check("lcs2", last_completed_session(parse_iso("2026-10-13T20:00:00Z")).isoformat() == "2026-10-13", fails)
    # first passage
    now = parse_iso("2026-10-20T00:00:00Z")
    ss = sessions_from("2026-10-13", 5)
    bars = {"2026-10-13": {"o": D("10"), "h": D("10.4"), "l": D("9.6"), "c": D("10")},
            "2026-10-14": {"o": D("10"), "h": D("13.0"), "l": D("9.9"), "c": D("12")}}
    r = first_passage(D("10"), ss, bars, "0.30", "0.05", now)
    _check("fp-win", r["status"] == "WIN" and r["date"] == "2026-10-14", fails)
    r = first_passage(D("10"), ss, bars, "0.30", "0.03", now)
    _check("fp-loss", r["status"] == "LOSS" and r["date"] == "2026-10-13", fails)
    bars2 = {"2026-10-13": {"o": D("10"), "h": D("13"), "l": D("9.5"), "c": D("10")}}
    _check("fp-censored", first_passage(D("10"), ss, bars2, "0.30", "0.05", now)["status"] == "CENSORED", fails)
    _check("fp-missing", first_passage(D("10"), ss, {"2026-10-13": bars["2026-10-13"]}, "0.30", "0.05", now)["status"] == "MISSING", fails)
    _check("fp-open", first_passage(D("10"), ss, bars, "0.50", "0.10", parse_iso("2026-10-15T12:00:00Z"))["status"] == "OPEN", fails)
    full = {d.isoformat(): {"o": D("10"), "h": D("10.5"), "l": D("9.8"), "c": D("10.2")} for d in ss}
    r = first_passage(D("10"), ss, full, "0.30", "0.05", now)
    _check("fp-expiry", r["status"] == "EXPIRY" and r["ret"] == D("2.0"), fails)
    _check("fp-inclusive", first_passage(D("5.17"), ss, {"2026-10-13": {"o": D("5.17"), "h": D("5.21"), "l": D("4.653"), "c": D("4.79")}},
                                         "0.30", "0.10", now)["status"] == "LOSS", fails)
    # register
    tmp = workdir() / "selftest_register.jsonl"
    if tmp.exists():
        tmp.unlink()
    reg_append(tmp, "GENESIS", "G", "test", {"note": "selftest"})
    reg_append(tmp, "E002", "E2:TEST:2026-10-13", "test", {"ticker": "TEST", "ref_date": "2026-10-13", "downs": ["0.05", "0.10"]})
    _check("reg-verify", len(reg_read(tmp)) == 2, fails)
    txt = tmp.read_text().replace('"TEST"', '"TSET"', 1)
    tmp.write_text(txt)
    try:
        reg_read(tmp)
        fails.append("reg-tamper")
    except RegError:
        pass
    # registered decision lines vs the live ledger, including lines moved by a weekly archive
    recs_d = [{"kind": "DECISION", "id": f"D-0{n}", "payload": {"text": f"- D-0{n} · t{n}"}} for n in (20, 21, 22)]
    ptr_d = "- D-020 → D-021: moved verbatim to `moonshot/ledger-archive-2026-10-17.md` (§11 there) on 2026-10-17 09:05 WIB."
    _check("reg-decision-archived", decision_check(recs_d, [ptr_d, "- D-022 · t22"]) == ([], ["D-020", "D-021"]), fails)
    _check("reg-decision-missing", decision_check(recs_d, ["- D-022 · t22"]) == (["D-020", "D-021"], []), fails)
    tmp.unlink()
    # ledger patch + guard
    led = ["# L", "", "Created: x · Last updated: old", "", "## 5. Candidates", "", "| C-001 | A | s |",
           "", "C-001 A — candidate test (S-001):", "1. x", "", "C-001 revision log:", "- a", "",
           "Radar — scheduled events:", "- r1", "", "Format: ID · asset", "", "## 6. Scanner log", "",
           "### S-001 — x", "- y", "", "### KOD (Kodiak) — reference case", "- k", "", "## 7. Rule-test log", "", "S-001 (x)", "",
           "## 9. Process corrections", "", "- p1", "", "## 10. Equity", "", "Check at S-001", "",
           "## 11. Forecast register", "", "| F-001 | x |", "", "- D-001 · x", "", "## 12. E-001", "", "Status", "",
           "## 12a. E-002", "", "| Case | x |", "| A | 1 |", "", "## 13. Audit", "", "text"]
    patch = ("@@ header\nLast updated: new\n@@ scan\n### S-002 — y\n- z\n@@ decision\n- D-002 · y\n@@ revlog C-001\n- b\n"
             "@@ row C-001\n| C-001 | A | t |\n@@ e002-row\n| B | 2 |\n@@ additions\nS-002 additions (x): y\n@@ radar\n- r2\n")
    new, rep, its = apply_patch_text(led, patch, "S-002")
    probs, _, _ = guard(led, new)
    _check("patch-guard", not probs, fails)
    _check("patch-content", "| C-001 | A | t |" in new and "- D-002 · y" in new and "### S-002 — y" in new and
           new.index("### S-002 — y") < new.index("### KOD (Kodiak) — reference case") and
           any(s.startswith("- S-002 · superseded row") for s in new) and new.index("- r2") < new.index("Format: ID · asset"), fails)
    bad = [s for s in new if s != "- k"]
    _check("guard-catches-loss", bool(guard(new, bad)[0]), fails)
    # parsers
    cx = ('<tr id="2026-10-12"><td>2026-10-12</td><td>71.08</td><td>72.89</td><td>68.97</td><td>70.65</td>'
          '<td class="down">-1.023%</td><td>2,427,716</td><td class="">0.000%</td></tr>')
    p = parse_cx_history(cx)
    _check("parse-cx", p.get("2026-10-12", {}).get("l") == D("68.97") and p["2026-10-12"]["v"] == 2427716, fails)
    mv = 'x},data:[{no:1,s:"AB",n:"A B",change:25.5,priceDate:"2026-10-12",price:3.04,volume:100,marketCap:7036189},{no:2,s:"CD",n:"C",change:.5,priceDate:"2026-10-12",price:1,volume:1,marketCap:null}]'
    pm = parse_sa_movers('query:{main:"change",sortDirection:"desc"' + mv)
    _check("parse-movers", pm and pm[0]["rows"][1]["change"] == D("0.5") and pm[0]["rows"][0]["s"] == "AB", fails)
    if a.net:
        net = Net()
        for name, url in (("chartexchange", "https://chartexchange.com/symbol/nyse-zim/historical/"),
                          ("stockanalysis", "https://stockanalysis.com/stocks/zim/history/"),
                          ("stocktitan", "https://www.stocktitan.net/news/ZIM/")):
            f = net.get(url, bust=(name != "stocktitan"))
            print(f"net {name}: {f.status} {len(f.text):,} chars {f.note}".rstrip())
            if not f.ok:
                fails.append(f"net-{name}")
    print("SELFTEST " + ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
    return 0 if not fails else 2


def main(argv=None):
    ap = argparse.ArgumentParser(prog="msx", description=__doc__.split("\n")[0])
    ap.add_argument("--version", action="version", version=f"msx {VERSION}")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("clock", help="now in UTC/ET/WIB, NYSE phase, sessions")
    p.add_argument("--at", help="ISO time instead of the system clock")
    p.set_defaults(fn=cmd_clock)

    p = sp.add_parser("cal", help="NYSE calendar: --sessions DATE N, --check DATE")
    p.add_argument("--sessions", nargs=2, metavar=("DATE", "N"))
    p.add_argument("--check")
    p.set_defaults(fn=cmd_cal)

    p = sp.add_parser("projdoc", help="write the latest project_read result for PATH to a file")
    p.add_argument("path")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--max-age", type=float, default=12, help="hours of transcripts to search")
    p.set_defaults(fn=cmd_projdoc)

    p = sp.add_parser("bars", help="daily bars, both sources, reconciled")
    p.add_argument("tickers", nargs="+")
    p.add_argument("-n", type=int, default=7)
    p.add_argument("--since")
    p.add_argument("--pct", action="store_true", help="day-move summary for the newest bar")
    p.set_defaults(fn=cmd_bars)

    p = sp.add_parser("resolve", help="first-passage outcomes for registered (or --item) records")
    p.add_argument("--registry")
    p.add_argument("--item", action="append", help="JSON item (id, ticker, ref_date, downs, [ref_price, up, n])")
    p.add_argument("--only", nargs="*")
    p.add_argument("--all", action="store_true", help="include closed items")
    p.add_argument("--commit", action="store_true", help="append changed outcomes to the register")
    p.add_argument("--run")
    p.add_argument("--at")
    p.set_defaults(fn=cmd_resolve)

    p = sp.add_parser("reg", help="register: verify | add | items | show | freeze")
    p.add_argument("action", choices=["verify", "add", "items", "show", "freeze"])
    p.add_argument("file")
    p.add_argument("--kind")
    p.add_argument("--id")
    p.add_argument("--run", default="?")
    p.add_argument("--payload")
    p.add_argument("--payload-file")
    p.add_argument("--patch")
    p.add_argument("--ledger")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_reg)

    p = sp.add_parser("ledger", help="ledger: outline | get | apply | guard | same | archive | e002")
    p.add_argument("action", choices=["outline", "get", "apply", "guard", "same", "archive", "e002"])
    p.add_argument("file")
    p.add_argument("new", nargs="?")
    p.add_argument("--sec")
    p.add_argument("--id")
    p.add_argument("--last-scans", type=int, default=0)
    p.add_argument("--lines")
    p.add_argument("--patch")
    p.add_argument("--run", default="?")
    p.add_argument("-o", "--out")
    p.add_argument("--name")
    p.add_argument("--when")
    p.add_argument("--keep", type=int, default=3)
    p.add_argument("--close")
    p.add_argument("--index-file")
    p.add_argument("--out-dir")
    p.set_defaults(fn=cmd_ledger)

    p = sp.add_parser("wire", help="StockTitan day pages → compact headline list (default: since prior 16:00 ET)")
    p.add_argument("--since", help="ISO time, or HH:MM = today at that ET time (default: prior session 16:00 ET)")
    p.add_argument("--until", help="ISO time or HH:MM ET (default: now)")
    p.add_argument("--min-impact", type=int, default=0)
    p.add_argument("--keep-flagged", action="store_true", help="keep keyword-flagged items below --min-impact")
    p.add_argument("--flagged", action="store_true", help="only keyword-flagged items")
    p.add_argument("--otc", action="store_true")
    p.add_argument("--tags", action="store_true")
    p.add_argument("--width", type=int, default=120)
    p.set_defaults(fn=cmd_wire)

    p = sp.add_parser("news", help="StockTitan per-ticker news")
    p.add_argument("tickers", nargs="+")
    p.add_argument("-n", type=int, default=6)
    p.set_defaults(fn=lambda a: cmd_news(a, False))

    p = sp.add_parser("filings", help="StockTitan per-ticker SEC filings")
    p.add_argument("tickers", nargs="+")
    p.add_argument("-n", type=int, default=8)
    p.set_defaults(fn=lambda a: cmd_news(a, True))

    p = sp.add_parser("quote", help="stockanalysis quote prints with their time labels")
    p.add_argument("tickers", nargs="+")
    p.set_defaults(fn=cmd_quote)

    p = sp.add_parser("stats", help="stockanalysis statistics (cap, shares, float, short, cash, debt, FCF, ADV)")
    p.add_argument("tickers", nargs="+")
    p.set_defaults(fn=cmd_stats)

    p = sp.add_parser("premarket", help="stockanalysis pre-market movers (date-checked)")
    p.add_argument("--min-cap", default="300000000")
    p.set_defaults(fn=cmd_premarket)

    p = sp.add_parser("gainers", help="stockanalysis day gainers (date-checked)")
    p.set_defaults(fn=cmd_gainers)

    p = sp.add_parser("screen", help="E-001 screen: gainers + --extra tickers, verified on daily bars")
    p.add_argument("--date")
    p.add_argument("--extra", help="comma-separated tickers from other lists (FMP, KOD)")
    p.add_argument("--min-move", default="20")
    p.add_argument("--min-cap", default="300000000")
    p.set_defaults(fn=cmd_screen)

    p = sp.add_parser("kod-us", help="KOD US paper-scan decisions for a session date (read-only)")
    p.add_argument("--date", required=True)
    p.add_argument("--repo")
    p.set_defaults(fn=cmd_kod)

    p = sp.add_parser("stress", help="whole-position stress table in AUD, AUD- vs USD-funded")
    p.add_argument("--equity-aud", default="776.3")
    p.add_argument("--audusd", default="0.7020")
    p.add_argument("--stop", default="5")
    p.add_argument("--slip", default="0.5")
    p.add_argument("--gap", action="append")
    p.add_argument("--tp", default="30")
    p.add_argument("--fx-fee", default="0.75")
    p.add_argument("--commission-usd", default="2")
    p.set_defaults(fn=cmd_stress)

    p = sp.add_parser("pct", help="percent change NEW vs OLD")
    p.add_argument("new")
    p.add_argument("old")
    p.set_defaults(fn=cmd_pct)

    p = sp.add_parser("barriers", help="barrier levels from a reference price")
    p.add_argument("ref")
    p.add_argument("--up", default="30")
    p.add_argument("--down", default="5,10")
    p.set_defaults(fn=cmd_barriers)

    p = sp.add_parser("cap", help="market cap = shares × price")
    p.add_argument("--shares", required=True)
    p.add_argument("--price", required=True)
    p.set_defaults(fn=cmd_cap)

    p = sp.add_parser("selftest", help="integrity and logic checks; --net probes the three data hosts")
    p.add_argument("--net", action="store_true")
    p.set_defaults(fn=cmd_selftest)

    p = sp.add_parser("stamp", help="(maintainer) write the self-hash into a copy of this file")
    p.add_argument("file")
    p.set_defaults(fn=cmd_stamp)

    a = ap.parse_args(argv)
    if a.cmd == "ledger" and a.action in ("guard", "same") and not a.new:
        ap.error("ledger guard/same need OLD NEW")
    if a.cmd == "ledger" and a.action == "apply" and not (a.patch and a.out):
        ap.error("ledger apply needs --patch and -o")
    if a.cmd == "ledger" and a.action == "archive" and not (a.name and a.when and a.out_dir):
        ap.error("ledger archive needs --name, --when and --out-dir")
    rc = a.fn(a)
    return rc or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:          # output piped into head/tail
        try:
            sys.stdout = open(os.devnull, "w")
        except OSError:
            pass
        sys.exit(0)

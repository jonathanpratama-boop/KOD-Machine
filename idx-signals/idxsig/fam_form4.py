"""Catalyst Register family FORM4 (research/CATALYST_FAMILIES/FORM4/protocol.json). Paper only, no orders.

A prospective replication of US_INSIDER_BUY (counted test 26) on live EDGAR data: a Form 4 with open-market purchases
of common equity by an officer or a director, USD 50,000 or more, no 10b5-1 flag, read from the EDGAR daily form index
of each NYSE session from the window start. One event per issuer per filing date and per 90 days; every sealed set is
FIRE with descriptive tags; the H20 plan is paired with five matched, 13D-free operating twins. This module only builds
the BATCH and CATALYST_SET records; the CLI appends them (catalysts.append).

The purchase rules reuse research/US_INSIDER_BUY/ib_lib.py (is_common, _TOP, MIN_VALUE), loaded by file path so the
committed research code is the one definition.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import numpy as np

from . import catalysts as cr
from . import paper
from . import speculation as spec
from .provenance import utc_stamp

FAMILY = "FORM4"
FORM = "4"  # EDGAR form type exactly '4'; '4/A' is not used
INDEX_URL = "https://www.sec.gov/Archives/edgar/daily-index/{y}/QTR{q}/form.{ymd}.idx"
ARCHIVE_URL = "https://www.sec.gov/Archives/{path}"
IB_LIB = cr.PKG_ROOT / "research" / "US_INSIDER_BUY" / "ib_lib.py"


def _load_ib_lib():
    s = importlib.util.spec_from_file_location("us_insider_buy_ib_lib", IB_LIB)
    mod = importlib.util.module_from_spec(s)
    s.loader.exec_module(mod)
    return mod


ib = _load_ib_lib()
is_common, TOP = ib.is_common, ib._TOP
MIN_VALUE = ib.MIN_VALUE  # USD 50,000, test 26's purchase-filing floor
REPEAT_DAYS = cr.REPEAT_DAYS  # 90 calendar days


# ------------------------------------------------------------------------------- index dates and the daily index (pure)
def index_url(day: str) -> str:
    d = date.fromisoformat(day)
    return INDEX_URL.format(y=d.year, q=(d.month - 1) // 3 + 1, ymd=d.strftime("%Y%m%d"))


def index_dates(window_start: str, signal_session: str, covered: set[str]) -> list[str]:
    """NYSE sessions from the window start through the signal session (the last session before the entry) that no
    earlier FORM4 batch read (protocol 'source')."""
    if signal_session < window_start:
        return []
    days = np.arange(np.datetime64(window_start, "D"), np.datetime64(signal_session, "D") + 1)
    return [str(d) for d in days if cr.us_is_session(str(d)) and str(d) not in covered]


_INDEX_LINE = re.compile(r"^(?P<form>\S+)\s+(?P<name>.*?)\s+(?P<cik>\d{1,10})\s+(?P<date>\d{8}|\d{4}-\d{2}-\d{2})\s+(?P<file>\S+)\s*$")


def parse_index(body: bytes) -> list[dict]:
    """Rows of a daily form.idx: the lines after the dashed header rule, read from the right (file name, date filed,
    CIK; the form type is the first token and the company name, which may hold spaces, is the rest)."""
    lines = body.decode("latin-1").splitlines()
    start = next((i + 1 for i, ln in enumerate(lines) if ln.startswith("---")), 0)
    out = []
    for ln in lines[start:]:
        m = _INDEX_LINE.match(ln.strip())
        if not m:
            continue
        d = m["date"].replace("-", "")
        out.append({"form": m["form"], "company": m["name"].strip(), "cik": int(m["cik"]),
                    "date_filed": f"{d[:4]}-{d[4:6]}-{d[6:]}", "file_name": m["file"],
                    "accession": m["file"].rsplit("/", 1)[-1].removesuffix(".txt")})
    return out


def form4_filings(rows: list[dict]) -> list[dict]:
    """The index's form '4' filings, one per accession (the index lists a filing once per associated entity)."""
    seen, out = set(), []
    for r in rows:
        if r["form"] == FORM and r["accession"] not in seen:
            seen.add(r["accession"])
            out.append(r)
    return out


# ------------------------------------------------------------------------------- Form 4 XML (pure)
def form4_xml(text: bytes) -> bytes:
    """The ownershipDocument between <XML> and </XML> of a filing's full text (or the body itself if it is the XML)."""
    m = re.search(rb"<XML>(.*?)</XML>", text or b"", re.S | re.I)
    xml = (m.group(1) if m else (text or b"")).strip()
    if b"<ownershipDocument" not in xml:
        raise ValueError("no ownershipDocument XML in the filing")
    return xml


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str):
            el.tag = el.tag.rsplit("}", 1)[-1]
    return root


def _text(el: ET.Element | None) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _val(el: ET.Element, path: str) -> str:
    """A field's value: its <value> child when present (footnote siblings and children ignored), else its own text."""
    node = el.find(path)
    if node is None:
        return ""
    v = node.find("value")
    return _text(v if v is not None else node)


def _flag(s: str) -> bool:
    return s.strip().lower() in ("1", "true")


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_form4(xml: bytes) -> dict:
    """Issuer, reporting owners (relationship flags, officer title), the document-level 10b5-1 flag and the
    non-derivative transaction lines of an EDGAR ownership document. Raises ValueError when it cannot be read."""
    try:
        root = _strip_ns(ET.fromstring(xml))
    except ET.ParseError as exc:
        raise ValueError(f"unparsable XML: {exc}") from exc
    if root.tag != "ownershipDocument":
        raise ValueError(f"root element {root.tag!r}, not ownershipDocument")
    cik = _text(root.find("issuer/issuerCik"))
    if not cik.isdigit():
        raise ValueError("no issuer CIK")
    owners = []
    for o in root.findall("reportingOwner"):
        rel = o.find("reportingOwnerRelationship")
        get = (lambda k: _text(rel.find(k))) if rel is not None else (lambda k: "")
        owners.append({"cik": _text(o.find("reportingOwnerId/rptOwnerCik")), "name": _text(o.find("reportingOwnerId/rptOwnerName")),
                       "director": _flag(get("isDirector")), "officer": _flag(get("isOfficer")),
                       "tenpct": _flag(get("isTenPercentOwner")), "other": _flag(get("isOther")), "title": get("officerTitle")})
    lines = []
    for t in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        lines.append({"title": _val(t, "securityTitle"), "date": _val(t, "transactionDate")[:10],
                      "code": _text(t.find("transactionCoding/transactionCode")).upper(),
                      "shares": _num(_val(t, "transactionAmounts/transactionShares")),
                      "price": _num(_val(t, "transactionAmounts/transactionPricePerShare")),
                      "ad": _val(t, "transactionAmounts/transactionAcquiredDisposedCode").upper()})
    return {"document_type": _text(root.find("documentType")), "issuer_cik": int(cik),
            "issuer_name": _text(root.find("issuer/issuerName")), "symbol": _text(root.find("issuer/issuerTradingSymbol")),
            "aff10b5one": _flag(_text(root.find("aff10b5One"))), "owners": owners, "lines": lines}


def is_purchase_line(line: dict) -> bool:
    """Test 26's purchase line: code P, acquired, a common-equity title (ib_lib.is_common), shares and price > 0."""
    return (line["code"] == "P" and line["ad"] == "A" and is_common(line["title"])
            and (line["shares"] or 0) > 0 and (line["price"] or 0) > 0)


def purchase_test(doc: dict, min_value: float = MIN_VALUE) -> tuple[str | None, dict]:
    """Test 26's purchase filing: at least one purchase line, an officer or director among the owners, no 10b5-1 flag,
    purchase lines totalling at least `min_value`. Returns (the first failing reason or None, the filing's summary)."""
    buys = [x for x in doc["lines"] if is_purchase_line(x)]
    owners = doc["owners"]
    summary = {"total_value": float(sum(x["shares"] * x["price"] for x in buys)), "n_lines": len(buys),
               "trans_first": min((x["date"] for x in buys), default=None),
               "trans_last": max((x["date"] for x in buys), default=None),
               "officer": any(o["officer"] for o in owners), "director": any(o["director"] for o in owners),
               "top_exec": any(o["officer"] and bool(TOP.search(o["title"] or "")) for o in owners)}
    if not buys:
        return "NO_PURCHASE_LINE", summary
    if not (summary["officer"] or summary["director"]):
        return "NO_OFFICER_OR_DIRECTOR", summary
    if doc["aff10b5one"]:
        return "PLAN_10B5_1", summary
    if summary["total_value"] < min_value:
        return "BELOW_USD_50000", summary
    return None, summary


def _lag(day: str, last: str) -> int | None:
    """Calendar days from the last purchase's transaction date to the filing date (None if the date is unreadable)."""
    try:
        return (date.fromisoformat(day) - date.fromisoformat(last)).days
    except ValueError:
        return None


def group_events(filings: list[dict]) -> list[dict]:
    """One event per issuer per filing date: the first purchase filing by accession number, values summed
    (protocol 'issuer.repeat')."""
    groups: dict[tuple[int, str], list[dict]] = {}
    for f in sorted(filings, key=lambda f: (f["filing_date"], f["issuer_cik"], f["accession"])):
        groups.setdefault((f["issuer_cik"], f["filing_date"]), []).append(f)
    out = []
    for (cik, day), fs in groups.items():
        owners = {o["cik"] or o["name"]: o for f in fs for o in f["owners"]}
        last = max(f["trans_last"] or "" for f in fs)
        out.append({"accession": fs[0]["accession"], "accessions": [f["accession"] for f in fs], "issuer_cik": cik,
                    "issuer_name": fs[0]["issuer_name"], "symbol": fs[0]["symbol"], "filing_date": day,
                    "url": fs[0]["url"], "total_value": float(sum(f["total_value"] for f in fs)),
                    "n_lines": sum(f["n_lines"] for f in fs), "n_owners": len(owners),
                    "owners": [{k: o[k] for k in ("cik", "name", "director", "officer", "title")} for o in owners.values()],
                    "top_exec": any(f["top_exec"] for f in fs), "trans_first": min(f["trans_first"] or "" for f in fs) or None,
                    "trans_last": last or None, "lag_days": _lag(day, last),
                    "xml_sha256": {f["accession"]: f["xml_sha256"] for f in fs}})
    return sorted(out, key=lambda e: (e["filing_date"], e["accession"]))


# ------------------------------------------------------------------------------- batch
def _count(d: dict, key: str) -> None:
    d[key] = d.get(key, 0) + 1


def read_filings(client, dates: list[str]) -> tuple[list[dict], list[dict], dict, dict, list[str], dict]:
    """Read each date's index and its Form 4 filings, one at a time (no body kept past its parse). Returns
    (index log, purchase filings, counts by status, not-purchase reasons, unreadable accessions, digest of all XML read)."""
    log, purchases, counts, reasons, unreadable = [], [], {}, {}, []
    digest, n_xml = hashlib.sha256(), 0
    for day in dates:
        url = index_url(day)
        status, body = client.get(url)
        if status != 200:  # not yet published: left for the next batch
            log.append({"date": day, "status": "PENDING", "url": url, "http_status": status})
            continue
        rows = parse_index(body)
        filings = form4_filings(rows)
        log.append({"date": day, "status": "READ", "url": url, "sha256": cr._sha(body),
                    "form4_lines": sum(r["form"] == FORM for r in rows), "form4_filings": len(filings)})
        del body, rows
        for f in filings:
            furl = ARCHIVE_URL.format(path=f["file_name"])
            st, text = client.get(furl)
            if st != 200:
                _count(counts, "SKIP_UNREADABLE")
                unreadable.append(f"{f['accession']}|HTTP {st}")
                continue
            try:
                xml = form4_xml(text)
                doc = parse_form4(xml)
            except ValueError:
                _count(counts, "SKIP_PARSE_FAILED")
                continue
            finally:
                del text
            sha = cr._sha(xml)
            digest.update(f"{f['accession']} {sha}\n".encode())
            n_xml += 1
            why, summary = purchase_test(doc)
            if why:
                _count(counts, "SKIP_NOT_PURCHASE")
                _count(reasons, why)
                continue
            purchases.append({**summary, "accession": f["accession"], "filing_date": f["date_filed"], "url": furl,
                              "issuer_cik": doc["issuer_cik"], "issuer_name": doc["issuer_name"], "symbol": doc["symbol"],
                              "owners": doc["owners"], "xml_sha256": sha})
    return log, purchases, counts, reasons, unreadable, {"n": n_xml, "sha256": digest.hexdigest()}


def batch(now: datetime, client, ledger: list[dict] | None = None, records: list[dict] | None = None,
          clock=None) -> tuple[dict, list[dict]]:
    """Read the daily indexes not yet covered and build (BATCH, sets) for every new purchase event (protocol FORM4)."""
    fam, fam_sha = cr.family_protocol(FAMILY)
    ledger = paper.ledger_lines() if ledger is None else ledger
    records = cr.cat_lines() if records is None else records
    entry = cr.us_entry_session(now)
    signal = cr.us_prev_session(entry)
    cutoff = cr.us_cutoff(entry)
    scan = cr._scan_for(ledger, "US", signal)
    if scan is None:
        raise RuntimeError(f"no US paper scan for the signal session {signal}; run paper-scan --market US first")
    earlier = [r for r in records if r["type"] == "BATCH" and r["family"] == FAMILY]
    covered = {d["date"] for b in earlier for d in b["index_dates"] if d["status"] == "READ"}
    dates = index_dates(fam["window_start"], signal, covered)
    log, purchases, counts, reasons, unreadable, digest = read_filings(client, dates)
    events = group_events(purchases)
    status, tm_body = client.get(cr.TICKERS_URL)
    if status != 200:
        raise RuntimeError(f"SEC ticker map: HTTP {status}")
    by_cik, by_ticker = cr.ticker_maps(tm_body)
    feats = spec.scan_features(scan)
    universe = set(cr._universe(feats)["ticker"])
    chosen = {}
    for ev in events:
        tickers = by_cik.get(ev["issuer_cik"], [])
        ok = [t for t in tickers if t in universe]
        chosen[ev["accession"]] = (tickers, ok[0] if ok else None)
    excluded = sorted({*scan["candidates_ranked"], *(t for _, t in chosen.values() if t)})
    sealed = {}
    for r in records:
        if r["type"] == "CATALYST_SET" and r["family"] == FAMILY:
            cik, day = r["event"]["issuer_cik"], r["event"]["filing_date"]
            sealed[cik] = max(sealed.get(cik, day), day)
    today = now.astimezone(cr.NY).date().isoformat()
    statuses, sets = [], []
    for ev in events:
        acc, cik, day = ev["accession"], ev["issuer_cik"], ev["filing_date"]
        tickers, ticker = chosen[acc]
        row = {"accession": acc, "accessions": ev["accessions"], "issuer_cik": cik, "issuer_name": ev["issuer_name"],
               "filing_date": day, "total_value": ev["total_value"], "tickers": tickers, "ticker": ticker}

        def skip(code, reason):
            statuses.append({**row, "status": code, "reason": reason})

        if not tickers:
            skip("SKIP_NO_TICKER", "the issuer CIK has no ticker in company_tickers_exchange")
            continue
        if ticker is None:
            skip("SKIP_NOT_IN_UNIVERSE", f"none of {tickers} is fresh and eligible in {scan['scan_id']}")
            continue
        if day < signal:
            skip("SKIP_LATE", f"filed {day}, before the signal session {signal}; the register missed its entry")
            continue
        prior = sealed.get(cik)
        if prior and abs((date.fromisoformat(day) - date.fromisoformat(prior)).days) < REPEAT_DAYS:
            skip("SKIP_REPEAT_90D", f"a FORM4 set on the same issuer was sealed for a filing of {prior}")
            continue
        if not cr.is_operating(cr.submissions(client, cik), today):
            skip("SKIP_NOT_OPERATING", f"no 10-K, 10-Q, 20-F or 40-F in {cr.OPERATING_DAYS} days, a fund report, or no submissions")
            continue
        frow = feats[feats["ticker"] == ticker].iloc[0]
        set_id = f"CAT-FORM4-{acc}"
        seed = cr.set_seed(set_id)
        twins, level, checked = cr.sec13d_twins(feats, ticker, excluded, scan["detector"]["selected"], seed,
                                                client, by_ticker, today)
        tags = {k: ev[k] for k in ("total_value", "n_owners", "top_exec", "lag_days")}
        sets.append({
            "type": "CATALYST_SET", "register": cr.REGISTER_VERSION, "family": FAMILY, "market": "US",
            "set_id": set_id, "event_id": acc, "ticker": ticker, "signal_session": signal,
            "event": {**{k: v for k, v in ev.items() if k not in tags}, "form": FORM, "public_date": day},
            "entry": {"basis": "open", "session": entry, "text": "the entry session's opening print"},
            "entry_cutoff": utc_stamp(cutoff), "direction": int(fam["direction"]),
            "scan_id": scan["scan_id"], "scan_record_hash": scan["record_hash"],
            "features_file": scan["features_file"], "features_sha256": scan["features_sha256"],
            "signal": cr._signal(frow),
            "coverage": {"class": "FIRE", "rules": {}, "reasons": [], "inputs": tags,
                         "note": "no abstention rule (a replication of test 26's event); inputs are descriptive tags"},
            "twins": twins, "twins_match_level": level, "twins_seed": seed, "twins_checked": checked,
            "cone": cr._cone(fam, records, "US", FAMILY),
            "windows": {"H20": {k: fam["plan"][k] for k in ("kind", "entry_window", "holding_sessions")}},
            "plan": "H20", "protocol": {"id": fam["protocol_id"], "sha256": fam_sha}})
        statuses.append({**row, "status": "SEALED", "set_id": set_id, "coverage": "FIRE"})
        sealed[cik] = day
    sealed_at = (clock or (lambda: datetime.now(timezone.utc)))()
    if sets and sealed_at >= cutoff:
        raise RuntimeError(f"the entry cutoff {utc_stamp(cutoff)} passed while the batch was built; nothing sealed")
    for s in sets:
        s["sealed_at"] = utc_stamp(sealed_at)
    out = {"type": "BATCH", "register": cr.REGISTER_VERSION, "family": FAMILY, "market": "US",
           "sealed_at": utc_stamp(sealed_at), "window_start": fam["window_start"], "signal_session": signal,
           "entry_session": entry, "entry_cutoff": utc_stamp(cutoff), "scan_id": scan["scan_id"],
           "index_dates": log, "pending_dates": [d["date"] for d in log if d["status"] == "PENDING"],
           "filings_xml": digest, "unreadable": unreadable, "coverage_gap": bool(unreadable),
           "ticker_map_sha256": cr._sha(tm_body), "events": statuses, "counts": counts,
           "not_purchase_reasons": reasons, "protocol": {"id": fam["protocol_id"], "sha256": fam_sha}}
    return out, sets


def card_lines(s: dict) -> tuple[str, str, str]:
    """The report card's head, event and coverage lines of a FORM4 set (catalysts.card)."""
    ev, tags = s["event"], s["coverage"]["inputs"]
    owners = ", ".join(f"{o['name']} ({o['title'] or ('director' if o['director'] else 'officer')})" for o in ev["owners"])
    head = (f"### FORM4 {s['ticker']} ({ev['issuer_name']}) - filed {ev['filing_date']}, sealed {s['sealed_at']}, "
            f"cutoff {s['entry_cutoff']}")
    what = f"Form 4 `{ev['accession']}` ({len(ev['accessions'])} filing(s)) by {owners or 'n/a'}."
    lag = "n/a" if tags["lag_days"] is None else f"{tags['lag_days']} days"
    cls = (f"Coverage **FIRE**; purchases USD {tags['total_value']:,.0f}, owners {tags['n_owners']}, "
           f"top executive {'yes' if tags['top_exec'] else 'no'}, lag {lag}.")
    return head, what, cls

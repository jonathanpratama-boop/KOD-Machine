"""Catalyst Register family FORM4_SHARP (research/CATALYST_FAMILIES/FORM4_SHARP/protocol.json). Paper only, no orders.

FORM4's events narrowed to where counted test 26 found its edge and away from where the literature and this lab find
none, with no new data source: FIRE when the buyer is a top executive or buys USD 100k to 500k, the issuer has no
recent dilution filing, and not every buyer is a routine trader (Cohen, Malloy and Pomorski 2012: the same calendar
month every year). The plan is paired with 20 twins; H60 is the primary window; the mechanism statement
MECH_SECOND_BUY_20 is graded from the register's own later FORM4 batches. Each set is built from a FORM4 set sealed in
the same run (catalyst-seal --family FORM4 first); the frozen FORM4 family is not changed. This module only builds
records; the CLI appends them.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import numpy as np

from . import catalyst as e9
from . import catalysts as cr
from . import fam_form4 as f4
from . import paper
from . import speculation as spec
from .provenance import utc_stamp

FAMILY = "FORM4_SHARP"
PARENT = "FORM4"
BAND = (100_000.0, 500_000.0)  # VALUE_BAND: at least the first, below the second
ROUTINE_YEARS = 3
PER_YEAR = 3  # at most this many earlier Form 4 filings read per owner and year
OPEN_MARKET = frozenset({"P", "S"})
CHUNK_URL = "https://data.sec.gov/submissions/{name}"
FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}.txt"


# ------------------------------------------------------------------------------- pure rules
def sharp(top_exec: bool, total_value: float) -> dict:
    band = BAND[0] <= float(total_value) < BAND[1]
    return {"TOP_EXEC": bool(top_exec), "VALUE_BAND": band, "sharp": bool(top_exec) or band}


def holdings_increase(xml: bytes) -> dict:
    """Shares bought on the filing's purchase lines, and the holding after its last purchase line
    (postTransactionAmounts/sharesOwnedFollowingTransaction); the increase is bought / (after - bought)."""
    root = f4._strip_ns(ET.fromstring(xml))
    bought, after = 0.0, None
    for t in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        line = {"title": f4._val(t, "securityTitle"), "code": f4._text(t.find("transactionCoding/transactionCode")).upper(),
                "shares": f4._num(f4._val(t, "transactionAmounts/transactionShares")),
                "price": f4._num(f4._val(t, "transactionAmounts/transactionPricePerShare")),
                "ad": f4._val(t, "transactionAmounts/transactionAcquiredDisposedCode").upper()}
        if f4.is_purchase_line(line):
            bought += float(line["shares"])
            after = f4._num(f4._val(t, "postTransactionAmounts/sharesOwnedFollowingTransaction"))
    inc = bought / (after - bought) if (after is not None and after > bought and bought > 0) else None
    return {"bought": bought, "after": after, "increase": inc}


def open_market_codes(xml: bytes) -> set[str]:
    root = f4._strip_ns(ET.fromstring(xml))
    return {f4._text(t.find("transactionCoding/transactionCode")).upper()
            for t in root.findall("nonDerivativeTable/nonDerivativeTransaction")} & OPEN_MARKET


def coverage(sh: dict, dilution: list[str] | None, routine: dict) -> dict:
    rules = {"NOT_SHARP": not sh["sharp"], "DILUTION_RECENT": dilution is None or bool(dilution),
             "ROUTINE": bool(routine["routine"])}
    return {"class": "ABSTAIN" if any(rules.values()) else "FIRE", "rules": rules,
            "reasons": [k for k, v in rules.items() if v]}


# ------------------------------------------------------------------------------- EDGAR reads
def owner_filings(client, cik: int, start: str, end: str):
    """The owner's submissions (recent block plus chunk files overlapping start..end), or None if unreadable."""
    st, main = client.get(cr.SUBMISSIONS_URL.format(cik=int(cik)))
    if st != 200 or not main:
        return None, [f"submissions HTTP {st}"]
    chunks, notes = [], []
    try:
        for name in e9.chunk_names(main, start, end):
            cst, body = client.get(CHUNK_URL.format(name=name))
            if cst != 200:
                return None, [f"chunk {name}: HTTP {cst}"]
            chunks.append(body)
        return e9.parse_submissions(main, chunks), notes
    except (ValueError, KeyError) as exc:
        return None, [f"submissions unreadable: {exc}"]


def owner_routine(client, owner_cik: int | None, month_day: str) -> dict:
    """Routine (protocol rule ROUTINE): in each of the 3 calendar years before the transaction's year, a Form 4 by the
    owner filed in the transaction's calendar month with a P or S line (at most 3 filings read per year)."""
    if not owner_cik:
        return {"cik": None, "routine": False, "unknown": True, "years": {}, "note": "no owner CIK"}
    d = date.fromisoformat(month_day)
    years = [d.year - k for k in range(1, ROUTINE_YEARS + 1)]
    filings, notes = owner_filings(client, owner_cik, f"{years[-1]}-{d.month:02d}-01", f"{years[0]}-{d.month:02d}-31")
    if filings is None:
        return {"cik": owner_cik, "routine": False, "unknown": True, "years": {}, "note": "; ".join(notes)}
    out, unknown = {}, False
    for y in years:
        prefix = f"{y}-{d.month:02d}"
        f = filings[(filings["form"] == f4.FORM) & filings["filingDate"].astype(str).str.startswith(prefix)]
        hit, reads = False, []
        for r in list(f.sort_values(["filingDate", "accessionNumber"]).itertuples())[:PER_YEAR]:
            st, text = client.get(FILING_URL.format(cik=int(owner_cik), acc=r.accessionNumber))
            if st != 200:
                reads.append({"accession": r.accessionNumber, "http_status": st})
                continue
            try:
                xml = f4.form4_xml(text)
                codes = open_market_codes(xml)
            except (ValueError, ET.ParseError):
                reads.append({"accession": r.accessionNumber, "parse": "failed"})
                continue
            reads.append({"accession": r.accessionNumber, "sha256": cr._sha(xml), "codes": sorted(codes)})
            if codes:
                hit = True
                break
        if not hit and any("sha256" not in x for x in reads):
            unknown = True
        out[str(y)] = {"hit": hit, "filings_in_month": int(len(f)), "read": reads}
    return {"cik": owner_cik, "routine": all(v["hit"] for v in out.values()), "unknown": unknown, "years": out}


# ------------------------------------------------------------------------------- batch
def _parent_batch(records: list[dict], entry: str) -> dict | None:
    hits = [r for r in records if r["type"] == "BATCH" and r["family"] == PARENT and r["entry_session"] == entry]
    return hits[-1] if hits else None


def _filing_url(ev: dict, acc: str) -> str:
    return ev["url"] if acc == ev["accession"] else FILING_URL.format(cik=ev["issuer_cik"], acc=acc)


def batch(now: datetime, client, ledger: list[dict] | None = None, records: list[dict] | None = None,
          clock=None) -> tuple[dict, list[dict]]:
    """Build (BATCH, sets) from the FORM4 sets the FORM4 batch of this entry session sealed."""
    fam, fam_sha = cr.family_protocol(FAMILY)
    ledger = paper.ledger_lines() if ledger is None else ledger
    records = cr.cat_lines() if records is None else records
    entry = cr.us_entry_session(now)
    signal = cr.us_prev_session(entry)
    cutoff = cr.us_cutoff(entry)
    scan = cr._scan_for(ledger, "US", signal)
    if scan is None:
        raise RuntimeError(f"no US paper scan for the signal session {signal}; run paper-scan --market US first")
    pb = _parent_batch(records, entry)
    if pb is None:
        raise RuntimeError(f"no {PARENT} batch for the entry session {entry}; run catalyst-seal --family {PARENT} first")
    by_id = {r["set_id"]: r for r in records if r["type"] == "CATALYST_SET"}
    # a parent this family already sealed or skipped is final (a recorded skip is not retried)
    done = {e.get("parent_set_id") for r in records if r["type"] == "BATCH" and r["family"] == FAMILY for e in r["events"]}
    done |= {r["parent"]["set_id"] for r in by_id.values() if r["family"] == FAMILY and r.get("parent")}
    parents = [by_id[e["set_id"]] for e in pb["events"] if e["status"] == "SEALED" and e.get("set_id") in by_id]
    parents = [p for p in parents if p["set_id"] not in done and p["event"]["filing_date"] >= fam["window_start"]]
    status, tm_body = client.get(cr.TICKERS_URL)
    if status != 200:
        raise RuntimeError(f"SEC ticker map: HTTP {status}")
    _, by_ticker = cr.ticker_maps(tm_body)
    feats = spec.scan_features(scan)
    excluded = sorted({*scan["candidates_ranked"], *(t for e in pb["events"] for t in e.get("tickers") or [])})
    today = now.astimezone(cr.NY).date().isoformat()
    statuses, sets = [], []
    for p in parents:
        ev, tags = p["event"], p["coverage"]["inputs"]
        row = {"accession": ev["accession"], "parent_set_id": p["set_id"], "issuer_cik": ev["issuer_cik"],
               "issuer_name": ev["issuer_name"], "filing_date": ev["filing_date"], "ticker": p["ticker"],
               "tickers": [p["ticker"]]}
        docs, changed = [], None
        for acc in ev["accessions"]:
            st, text = client.get(_filing_url(ev, acc))
            if st != 200:
                changed = f"{acc}: HTTP {st}"
                break
            try:
                xml = f4.form4_xml(text)
                doc = f4.parse_form4(xml)
            except ValueError as exc:
                changed = f"{acc}: {exc}"
                break
            if cr._sha(xml) != ev["xml_sha256"].get(acc):
                changed = f"{acc}: XML sha256 differs from the FORM4 set"
                break
            docs.append((acc, xml, doc))
        if changed:
            statuses.append({**row, "status": "SKIP_XML_CHANGED", "reason": changed})
            continue
        inc = {acc: holdings_increase(xml) for acc, xml, _ in docs}
        incs = [v["increase"] for v in inc.values() if v["increase"] is not None]
        buyers = {}
        for _, _, doc in docs:
            if any(f4.is_purchase_line(x) for x in doc["lines"]):
                for o in doc["owners"]:
                    key = int(o["cik"]) if str(o["cik"]).isdigit() else None
                    buyers.setdefault(key or o["name"], key)
        month_day = ev.get("trans_last") or ev["filing_date"]
        owners = [owner_routine(client, cik, month_day) for cik in buyers.values()]
        routine = {"routine": bool(owners) and all(o["routine"] for o in owners), "owners": owners}
        issuer_filings = cr.submissions(client, ev["issuer_cik"])
        dil = cr.dilution_filings(issuer_filings, signal, today) if issuer_filings is not None else None
        sh = sharp(tags["top_exec"], tags["total_value"])
        cov = coverage(sh, dil, routine)
        cov["inputs"] = {**tags, **sh, "dilution_filings": dil, "routine": routine,
                         "pct_increase": {"by_filing": inc, "max": max(incs) if incs else None}}
        set_id = f"CAT-{FAMILY}-{ev['accession']}"
        twins, level, log = cr.sec13d_twins(feats, p["ticker"], excluded, scan["detector"]["selected"], p["twins_seed"],
                                            client, by_ticker, today, n=cr.TWINS_20, checks=cr.TWIN_CHECKS_20)
        windows = {k: {kk: vv for kk, vv in w.items() if kk in ("kind", "entry_window", "holding_sessions", "sessions",
                                                                 "calendar_days")} for k, w in fam["windows"].items()}
        sets.append({
            "type": "CATALYST_SET", "register": cr.REGISTER_VERSION, "family": FAMILY, "market": "US",
            "set_id": set_id, "event_id": ev["accession"], "ticker": p["ticker"], "signal_session": signal,
            "parent": {"set_id": p["set_id"], "record_hash": p["record_hash"]},
            "event": ev, "entry": p["entry"], "entry_cutoff": utc_stamp(cutoff), "direction": int(fam["direction"]),
            "scan_id": scan["scan_id"], "scan_record_hash": scan["record_hash"],
            "features_file": scan["features_file"], "features_sha256": scan["features_sha256"],
            "signal": p["signal"], "coverage": cov,
            "twins": twins, "twins_match_level": level, "twins_seed": p["twins_seed"], "twins_checked": log,
            "cone": cr._cone(fam, records, "US", FAMILY), "windows": windows, "plan": "H60",
            "protocol": {"id": fam["protocol_id"], "sha256": fam_sha}})
        statuses.append({**row, "status": "SEALED", "set_id": set_id, "coverage": cov["class"]})
    sealed_at = (clock or (lambda: datetime.now(timezone.utc)))()
    if sets and sealed_at >= cutoff:
        raise RuntimeError(f"the entry cutoff {utc_stamp(cutoff)} passed while the batch was built; nothing sealed")
    for s in sets:
        s["sealed_at"] = utc_stamp(sealed_at)
    out = {"type": "BATCH", "register": cr.REGISTER_VERSION, "family": FAMILY, "market": "US",
           "sealed_at": utc_stamp(sealed_at), "window_start": fam["window_start"], "signal_session": signal,
           "entry_session": entry, "entry_cutoff": utc_stamp(cutoff), "scan_id": scan["scan_id"],
           "parent_batch": {"family": PARENT, "sealed_at": pb["sealed_at"], "record_hash": pb["record_hash"]},
           "ticker_map_sha256": cr._sha(tm_body), "events": statuses,
           "protocol": {"id": fam["protocol_id"], "sha256": fam_sha}}
    return out, sets


# ------------------------------------------------------------------------------- mechanism statement
def session_after(day: str, k: int) -> str:
    """The k-th NYSE session after `day`."""
    d = np.datetime64(day, "D")
    while k > 0:
        d = d + np.timedelta64(1, "D")
        if cr.us_is_session(str(d)):
            k -= 1
    return str(d)


def resolve_mechanism(s: dict, window_id: str, records: list[dict], client=None) -> dict | None:
    """MECH_SECOND_BUY_20 from the register's own FORM4 batches: a purchase event (any status) on the same issuer with
    a filing date after this event's and on or before the 20th session after the signal session. None while the
    batches have not yet read every NYSE date in that span."""
    w = s["windows"].get(window_id, {})
    if w.get("kind") != "mechanism":
        return None
    ev = s["event"]
    end = session_after(s["signal_session"], int(w["sessions"]))
    span = [str(d) for d in np.arange(np.datetime64(ev["filing_date"], "D") + np.timedelta64(1, "D"),
                                             np.datetime64(end, "D") + np.timedelta64(1, "D"))
            if cr.us_is_session(str(d))]
    batches = [r for r in records if r["type"] == "BATCH" and r["family"] == PARENT]
    status = {}
    gap_batches = []
    for b in batches:
        days = [d["date"] for d in b.get("index_dates", [])]
        for d in b.get("index_dates", []):
            if d["status"] in ("READ", "MISSING"):
                status[d["date"]] = d["status"]
        if b.get("unreadable") and set(days) & set(span):
            gap_batches.append(b["sealed_at"])
    if any(d not in status for d in span):
        return None  # not all dates read yet
    hits = sorted({(e["filing_date"], e["accession"]) for b in batches for e in b.get("events", [])
                   if e.get("issuer_cik") == ev["issuer_cik"] and ev["filing_date"] < e.get("filing_date", "") <= end})
    missing = [d for d in span if status[d] == "MISSING"]
    outcome = True if hits else (None if (missing or gap_batches) else False)
    return cr.mechanism_record(s, window_id, {"MECH_SECOND_BUY_20": outcome},
                               {"span": [span[0], span[-1]] if span else [], "end_session": end, "hits": hits,
                                "missing_dates": missing, "batches_with_unreadable_filings": gap_batches})


def split_labels(sets: list[dict]) -> dict[str, dict[str, str]]:
    """The protocol's descriptive splits per set (decision window): each abstention rule's own class (sets abstained on
    by that rule alone), and PCT_INCREASE terciles of the FIRE sets (cut points from the sets sealed so far)."""
    out: dict[str, dict[str, str]] = {}
    for s in sets:
        reasons = s["coverage"]["reasons"]
        if len(reasons) == 1:
            out.setdefault(s["set_id"], {})["ONLY_RULE"] = reasons[0]
    fire = [(s["set_id"], s["coverage"]["inputs"]["pct_increase"]["max"]) for s in sets if s["coverage"]["class"] == "FIRE"]
    vals = [v for _, v in fire if v is not None]
    if len(vals) >= 3:
        lo, hi = np.quantile(vals, [1 / 3, 2 / 3])
        for sid, v in fire:
            out.setdefault(sid, {})["PCT_INCREASE"] = ("unknown" if v is None else
                                                       "low" if v <= lo else "high" if v > hi else "middle")
    return out


def card_lines(s: dict) -> tuple[str, str, str]:
    ev, cov = s["event"], s["coverage"]
    inp = cov["inputs"]
    owners = ", ".join(f"{o['name']} ({o['title'] or ('director' if o['director'] else 'officer')})" for o in ev["owners"])
    head = (f"### {FAMILY} {s['ticker']} ({ev['issuer_name']}) - filed {ev['filing_date']}, sealed {s['sealed_at']}, "
            f"cutoff {s['entry_cutoff']}")
    pct = inp["pct_increase"]["max"]
    what = (f"Form 4 `{ev['accession']}` by {owners or 'n/a'}; purchases USD {inp['total_value']:,.0f}; top executive "
            f"{'yes' if inp['TOP_EXEC'] else 'no'}; holding up {'n/a' if pct is None else f'{pct:+.1%}'}.")
    cls = (f"Coverage **{cov['class']}**" + (f" ({', '.join(cov['reasons'])})" if cov["reasons"] else "")
           + f"; dilution filings {'unknown' if inp['dilution_filings'] is None else len(inp['dilution_filings'])}"
           + f"; routine owners {sum(o['routine'] for o in inp['routine']['owners'])} of {len(inp['routine']['owners'])}"
           + f"; parent {s['parent']['set_id']}.")
    return head, what, cls

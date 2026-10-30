"""Catalyst Register family SEC13D_V2 (research/CATALYST_FAMILIES/SEC13D_V2/protocol.json). Paper only, no orders.

The SEC13D family's filings read more fully, with no new data source: the structured primary document's cover page
gives the reporting persons' holdings and percent of class, so the abstention rule knows the issuer's size even when
the XBRL share count is missing; Item 4 is split into strong intent and boilerplate; Item 5(c) is recorded; the plan is
paired with 20 twins; H60 runs beside H20; and the mechanism statement MECH_13DA_UP_60 asks EDGAR whether the filer
raised its stake within 60 days. Each set is built from a SEC13D set sealed in the same run (catalyst-seal --family
SEC13D first); the frozen SEC13D family is not changed. This module only builds records; the CLI appends them.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta, timezone

import numpy as np

from . import catalysts as cr
from . import paper
from . import speculation as spec
from .provenance import utc_stamp

FAMILY = "SEC13D_V2"
PARENT = "SEC13D"
STRONG_INTENT = (
    "nominate",
    "proxy",
    "strategic alternatives",
    "sale of the",
    "change of control",
    "take private",
    "going private",
)
AMENDMENTS = frozenset({"SCHEDULE 13D/A", "SC 13D/A"})
MAX_AMENDMENTS = 10
MAX_PRICES = 50
RETRY_DAYS = 10  # a mechanism window whose EDGAR source stays unreadable this long after it ends is recorded ungraded
_PERSON = re.compile(rb"<reportingPersonInfo>(.*?)</reportingPersonInfo>", re.S)
_PRICE = re.compile(r"\$\s?([0-9][0-9,]*\.?[0-9]*)")


# ------------------------------------------------------------------------------- the structured filing (pure)
def _field(block: bytes, name: str) -> str | None:
    m = re.search(rb"<" + name.encode() + rb">(.*?)</" + name.encode() + rb">", block, re.S)
    return html.unescape(m.group(1).decode("utf-8", "replace")).strip() if m else None


def _float(s: str | None) -> float | None:
    try:
        return float(str(s).replace(",", "")) if s not in (None, "") else None
    except ValueError:
        return None


def cover_page(body: bytes | None) -> dict:
    """The cover page's reporting persons: CIK (None for a person without one), name, aggregate amount owned and
    percent of class; and the implied shares outstanding from the person with the largest percent of class."""
    persons = []
    for block in _PERSON.findall(body or b""):
        cik = _field(block, "reportingPersonCIK")
        persons.append(
            {
                "cik": int(cik) if cik and cik.isdigit() else None,
                "name": _field(block, "reportingPersonName"),
                "amount": _float(_field(block, "aggregateAmountOwned")),
                "percent": _float(_field(block, "percentOfClass")),
            }
        )
    usable = [p for p in persons if (p["percent"] or 0) > 0 and (p["amount"] or 0) > 0]
    best = max(usable, key=lambda p: p["percent"]) if usable else None
    return {
        "persons": persons,
        "max_percent": max((p["percent"] or 0 for p in persons), default=None) if persons else None,
        "implied_shares": best["amount"] / (best["percent"] / 100.0) if best else None,
        "implied_from": {"cik": best["cik"], "name": best["name"]} if best else None,
    }


def strong_intent(item4: dict | None, body: bytes | None) -> dict:
    m = re.search(rb"<transactionPurpose>(.*?)</transactionPurpose>", body or b"", re.S)
    low = html.unescape(m.group(1).decode("utf-8", "replace")).lower() if m else ""
    words = [w for w in STRONG_INTENT if w in low]
    return {"found": bool(m), "words": words, "strong": bool(words)}


def item5c(body: bytes | None, close: float | None) -> dict:
    """Item 5(c): the filer's transactions in the last 60 days as written; the dollar prices it states."""
    m = re.search(rb"<transactionDesc>(.*?)</transactionDesc>", body or b"", re.S)
    if not m:
        return {"found": False}
    text = html.unescape(m.group(1).decode("utf-8", "replace")).strip()
    low = text.lower()
    none = bool(re.search(r"\bno\b[^.]{0,120}transaction", low))
    prices = [
        p for p in (_float(x.rstrip(".")) for x in _PRICE.findall(text)[:MAX_PRICES]) if p and p > 0
    ]
    mean = float(np.mean(prices)) if prices else None
    return {
        "found": True,
        "chars": len(text),
        "sha256": cr._sha(text.encode()),
        "no_transactions": none,
        "prices": len(prices),
        "mean_price": mean,
        "close_to_mean_price": (float(close) / mean) if (mean and close) else None,
    }


def coverage(parent: dict, cover: dict, close: float) -> dict:
    """The frozen rules: DILUTION_RECENT and MOVED_ALREADY as the SEC13D set; MICROCAP on the XBRL shares, else the
    cover page's implied shares; neither: MV_UNKNOWN."""
    pin = parent["coverage"].get("inputs", {})
    prules = parent["coverage"]["rules"]
    fact = pin.get("shares_fact")
    if fact and fact.get("val"):
        shares, source = float(fact["val"]), "XBRL"
    elif cover.get("implied_shares"):
        shares, source = float(cover["implied_shares"]), "COVER_PAGE"
    else:
        shares, source = None, None
    mv = shares * float(close) if shares and close and close > 0 else None
    rules = {
        "DILUTION_RECENT": bool(prules["DILUTION_RECENT"]),
        "MOVED_ALREADY": bool(prules["MOVED_ALREADY"]),
        "MICROCAP": mv is None or mv < cr.MICROCAP_USD,
    }
    return {
        "class": "ABSTAIN" if any(rules.values()) else "FIRE",
        "rules": rules,
        "reasons": [
            k if not (k == "MICROCAP" and mv is None) else "MV_UNKNOWN"
            for k, v in rules.items()
            if v
        ],
        "inputs": {
            **pin,
            "shares": shares,
            "shares_source": source,
            "market_value_usd": mv,
            "parent_market_value_usd": pin.get("market_value_usd"),
        },
    }


# ------------------------------------------------------------------------------- batch
def _parent_batch(records: list[dict], entry: str) -> dict | None:
    hits = [
        r
        for r in records
        if r["type"] == "BATCH" and r["family"] == PARENT and r["entry_session"] == entry
    ]
    return hits[-1] if hits else None


def batch(
    now: datetime,
    client,
    ledger: list[dict] | None = None,
    records: list[dict] | None = None,
    clock=None,
) -> tuple[dict, list[dict]]:
    """Build (BATCH, sets) from the SEC13D sets the SEC13D batch of this entry session sealed."""
    fam, fam_sha = cr.family_protocol(FAMILY)
    ledger = paper.ledger_lines() if ledger is None else ledger
    records = cr.cat_lines() if records is None else records
    entry = cr.us_entry_session(now)
    signal = cr.us_prev_session(entry)
    cutoff = cr.us_cutoff(entry)
    scan = cr._scan_for(ledger, "US", signal)
    if scan is None:
        raise RuntimeError(
            f"no US paper scan for the signal session {signal}; run paper-scan --market US first"
        )
    pb = _parent_batch(records, entry)
    if pb is None:
        raise RuntimeError(
            f"no {PARENT} batch for the entry session {entry}; run catalyst-seal --family {PARENT} first"
        )
    window_start = datetime.fromisoformat(fam["window_start"])
    by_id = {r["set_id"]: r for r in records if r["type"] == "CATALYST_SET"}
    # a parent this family already sealed or skipped is final (a recorded skip is not retried)
    done = {
        e.get("parent_set_id")
        for r in records
        if r["type"] == "BATCH" and r["family"] == FAMILY
        for e in r["events"]
    }
    done |= {
        r["parent"]["set_id"] for r in by_id.values() if r["family"] == FAMILY and r.get("parent")
    }
    pbs = [
        r
        for r in records
        if r["type"] == "BATCH" and r["family"] == PARENT and r["entry_session"] == entry
    ]
    parents = [
        by_id[e["set_id"]]
        for b in pbs
        for e in b["events"]
        if e["status"] == "SEALED" and e.get("set_id") in by_id
    ]
    parents = [
        p
        for p in parents
        if p["set_id"] not in done
        and datetime.fromisoformat(p["event"]["accepted"]) >= window_start
    ]
    status, tm_body = client.get(cr.TICKERS_URL)
    if status != 200:
        raise RuntimeError(f"SEC ticker map: HTTP {status}")
    _, by_ticker = cr.ticker_maps(tm_body)
    feats = spec.scan_features(scan)
    excluded = sorted(
        {
            *scan["candidates_ranked"],
            *(t for b in pbs for e in b["events"] for t in e.get("tickers") or []),
        }
    )
    today = now.astimezone(cr.NY).date().isoformat()
    statuses, sets = [], []
    for p in parents:
        ev = p["event"]
        acc = ev["accession"]
        row = {
            "accession": acc,
            "parent_set_id": p["set_id"],
            "subject_cik": ev["subject_cik"],
            "subject_name": ev["subject_name"],
            "ticker": p["ticker"],
            "tickers": [p["ticker"]],
        }
        st, body = client.get(
            cr.PRIMARY_DOC_URL.format(cik=ev["subject_cik"], acc=acc.replace("-", ""))
        )
        if st != 200 or not body:
            statuses.append(
                {**row, "status": "SKIP_NO_PRIMARY_DOC", "reason": f"primary_doc.xml HTTP {st}"}
            )
            continue
        close = float(p["signal"]["close"])
        cover = cover_page(body)
        cov = coverage(p, cover, close)
        set_id = f"CAT-{FAMILY}-{acc}"
        twins, level, log = cr.sec13d_twins(
            feats,
            p["ticker"],
            excluded,
            scan["detector"]["selected"],
            p["twins_seed"],
            client,
            by_ticker,
            today,
            n=cr.TWINS_20,
            checks=cr.TWIN_CHECKS_20,
        )
        windows = {
            k: {
                kk: vv
                for kk, vv in w.items()
                if kk in ("kind", "entry_window", "holding_sessions", "sessions", "calendar_days")
            }
            for k, w in fam["windows"].items()
        }
        sets.append(
            {
                "type": "CATALYST_SET",
                "register": cr.REGISTER_VERSION,
                "family": FAMILY,
                "market": "US",
                "set_id": set_id,
                "event_id": acc,
                "ticker": p["ticker"],
                "signal_session": signal,
                "parent": {"set_id": p["set_id"], "record_hash": p["record_hash"]},
                "event": {
                    **ev,
                    "primary_doc_sha256": cr._sha(body),
                    "cover_page": cover,
                    "strong_intent": strong_intent(ev.get("item4"), body),
                    "item5c": item5c(body, close),
                },
                "entry": p["entry"],
                "entry_cutoff": utc_stamp(cutoff),
                "direction": int(fam["direction"]),
                "scan_id": scan["scan_id"],
                "scan_record_hash": scan["record_hash"],
                "features_file": scan["features_file"],
                "features_sha256": scan["features_sha256"],
                "signal": p["signal"],
                "coverage": cov,
                "twins": twins,
                "twins_match_level": level,
                "twins_seed": p["twins_seed"],
                "twins_checked": log,
                "cone": cr._cone(fam, records, "US", FAMILY),
                "windows": windows,
                "plan": "H20",
                "protocol": {"id": fam["protocol_id"], "sha256": fam_sha},
            }
        )
        statuses.append({**row, "status": "SEALED", "set_id": set_id, "coverage": cov["class"]})
    sealed_at = (clock or (lambda: datetime.now(timezone.utc)))()
    if sets and sealed_at >= cutoff:
        raise RuntimeError(
            f"the entry cutoff {utc_stamp(cutoff)} passed while the batch was built; nothing sealed"
        )
    for s in sets:
        s["sealed_at"] = utc_stamp(sealed_at)
    out = {
        "type": "BATCH",
        "register": cr.REGISTER_VERSION,
        "family": FAMILY,
        "market": "US",
        "sealed_at": utc_stamp(sealed_at),
        "window_start": fam["window_start"],
        "signal_session": signal,
        "entry_session": entry,
        "entry_cutoff": utc_stamp(cutoff),
        "scan_id": scan["scan_id"],
        "parent_batch": {
            "family": PARENT,
            "sealed_at": pb["sealed_at"],
            "record_hash": pb["record_hash"],
        },
        "ticker_map_sha256": cr._sha(tm_body),
        "events": statuses,
        "protocol": {"id": fam["protocol_id"], "sha256": fam_sha},
    }
    return out, sets


# ------------------------------------------------------------------------------- mechanism statement
def resolve_mechanism(
    s: dict, window_id: str, records: list[dict], client, today: str | None = None
) -> dict | None:
    """MECH_13DA_UP_60 from EDGAR: an amendment on the subject within 60 calendar days, filed with a reporting person
    of the original, reporting a larger percent of class than the original's largest. None: not gradable yet."""
    w = s["windows"].get(window_id, {})
    if w.get("kind") != "mechanism" or client is None:
        return None
    ev = s["event"]
    day = datetime.fromisoformat(ev["accepted"]).astimezone(cr.NY).date()
    end = day + timedelta(days=int(w["calendar_days"]))
    today_d = date.fromisoformat(today or datetime.now(timezone.utc).date().isoformat())
    give_up = (today_d - end).days > RETRY_DAYS
    filings = cr.submissions(client, ev["subject_cik"])
    if filings is None:
        return (
            cr.mechanism_record(
                s, window_id, {"MECH_13DA_UP_60": None}, {"submissions": "unreadable"}
            )
            if give_up
            else None
        )
    f = filings[
        filings["form"].str.upper().isin(AMENDMENTS)
        & (filings["filingDate"] > day.isoformat())
        & (filings["filingDate"] <= end.isoformat())
    ].sort_values(["filingDate", "accessionNumber"])
    orig = ev.get("cover_page") or {}
    orig_ciks = {p["cik"] for p in orig.get("persons", []) if p.get("cik")}
    orig_max = orig.get("max_percent") or 0.0
    read, outcome, unreadable = [], False, False
    for r in list(f.itertuples())[:MAX_AMENDMENTS]:
        st, body = client.get(
            cr.PRIMARY_DOC_URL.format(cik=ev["subject_cik"], acc=r.accessionNumber.replace("-", ""))
        )
        if st != 200 or not body:
            unreadable = True
            read.append(
                {"accession": r.accessionNumber, "filing_date": r.filingDate, "http_status": st}
            )
            continue
        cp = cover_page(body)
        shared = sorted(orig_ciks & {p["cik"] for p in cp["persons"] if p.get("cik")})
        up = bool(shared) and (cp["max_percent"] or 0.0) > orig_max
        read.append(
            {
                "accession": r.accessionNumber,
                "filing_date": r.filingDate,
                "sha256": cr._sha(body),
                "max_percent": cp["max_percent"],
                "shared_reporting_ciks": shared,
                "raises_stake": up,
            }
        )
        outcome = outcome or up
    if not outcome and unreadable:
        if not give_up:
            return None
        outcome = None
    return cr.mechanism_record(
        s,
        window_id,
        {"MECH_13DA_UP_60": outcome},
        {
            "amendments_listed": int(len(f)),
            "read": read,
            "original_max_percent": orig_max,
            "window": [day.isoformat(), end.isoformat()],
        },
    )


def split_labels(sets: list[dict]) -> dict[str, dict[str, str]]:
    """The protocol's descriptive splits per set (decision window): FIRE sets by shares source, STRONG_INTENT and
    POSITION (FIRE sets only)."""
    out = {}
    for s in sets:
        if s["coverage"]["class"] != "FIRE":
            continue
        ev = s["event"]
        out[s["set_id"]] = {
            "SHARES_SOURCE": str(s["coverage"]["inputs"].get("shares_source")),
            "STRONG_INTENT": str(bool(ev.get("strong_intent", {}).get("strong"))),
            "POSITION": str(ev.get("position")),
        }
    return out


def card_lines(s: dict) -> tuple[str, str, str]:
    ev, cov = s["event"], s["coverage"]
    inp = cov.get("inputs", {})
    head = (
        f"### {FAMILY} {s['ticker']} ({ev['subject_name']}) - accepted {ev['accepted']}, sealed {s['sealed_at']}, "
        f"cutoff {s['entry_cutoff']}"
    )
    si, i5 = ev.get("strong_intent", {}), ev.get("item5c", {})
    what = (
        f"Filing `{ev['accession']}` by {', '.join(ev['filed_by']) or 'n/a'}; cover page max "
        f"{ev['cover_page'].get('max_percent')}% of class; strong intent: {', '.join(si.get('words', [])) or 'none'}; "
        f"Item 5(c): "
        + ("no transactions" if i5.get("no_transactions") else f"{i5.get('prices', 0)} price(s)")
        + "."
    )
    mv = inp.get("market_value_usd")
    cls = (
        f"Coverage **{cov['class']}**"
        + (f" ({', '.join(cov['reasons'])})" if cov["reasons"] else "")
        + f"; market value {'n/a' if mv is None else f'USD {mv / 1e6:,.1f}M'} from {inp.get('shares_source') or 'nothing'}"
        + f"; parent {s['parent']['set_id']}."
    )
    return head, what, cls

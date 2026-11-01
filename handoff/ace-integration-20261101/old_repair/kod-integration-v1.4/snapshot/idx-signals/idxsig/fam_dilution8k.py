"""Catalyst family DILUTION_8K (research/CATALYST_FAMILIES/DILUTION_8K/protocol.json). Paper only, no orders.

An avoid flag: an 8-K (form exactly '8-K') whose EDGAR current-feed entry lists Item 3.02 (unregistered sales of
equity), sealed before the next NYSE entry with direction -1 and five matched, dilution-free twins. Every sealed set is
FIRE; the pre-entry move is recorded as an input only. This module builds (BATCH, sets); the CLI appends them.
"""

from __future__ import annotations

import html
import math
import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import catalysts as cr
from . import paper
from . import speculation as spec
from .provenance import utc_stamp

FAMILY = "DILUTION_8K"
FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb="
    "&owner=include&start={start}&count=100&output=atom"
)
FEED_PAGES = 9
EVENT_FORM = "8-K"
EVENT_ITEM = "3.02"
ISSUER_ROLES = frozenset({"filer", "issuer"})
_ITEM = re.compile(r"Item\s+(\d+\.\d+)\s*:")


# ------------------------------------------------------------------------------- feed parsing (pure)
def items_of_summary(summary: str | None) -> list[str]:
    """Item numbers ('3.02', ...) listed as 'Item N.NN:' in a feed entry's summary (already XML-unescaped; any
    remaining HTML escaping is undone here too)."""
    return list(dict.fromkeys(_ITEM.findall(html.unescape(summary or ""))))


def parse_feed(body: bytes) -> list[dict]:
    """Entries of the EDGAR current 8-K feed, as catalysts.parse_feed, plus the items listed in each summary."""
    out = []
    for e in cr._ENTRY.findall(body.decode("utf-8", "replace")):
        title, updated = cr._tag(e, "title"), cr._tag(e, "updated")
        link = re.search(r'<link[^>]*href="([^"]+)"', e)
        cat = re.search(r'<category[^>]*term="([^"]+)"', e)
        m = cr._TITLE.match(title or "")
        acc = cr._ACC.search(link.group(1)) if link else None
        if not (m and updated and cat and acc):
            continue
        out.append(
            {
                "form": html.unescape(cat.group(1)).strip(),
                "name": m["name"].strip(),
                "cik": int(m["cik"]),
                "role": m["role"].strip(),
                "accepted": updated,
                "accession": acc.group(1),
                "url": link.group(1),
                "items": items_of_summary(cr._tag(e, "summary")),
            }
        )
    return out


def events(entries: list[dict]) -> list[dict]:
    """The family's events: form exactly '8-K' listing Item 3.02, one per accession, with its Filer (issuer) entries
    in feed order, in acceptance order. 8-K/A and 8-Ks without Item 3.02 are not events."""
    by_acc: dict[str, dict] = {}
    for e in entries:
        if e["form"] != EVENT_FORM or EVENT_ITEM not in e["items"]:
            continue
        rec = by_acc.setdefault(
            e["accession"],
            {
                "accession": e["accession"],
                "accepted": e["accepted"],
                "url": e["url"],
                "items": e["items"],
                "filers": [],
                "others": [],
            },
        )
        who = {"cik": e["cik"], "name": e["name"], "role": e["role"]}
        bucket = rec["filers"] if e["role"].lower() in ISSUER_ROLES else rec["others"]
        if who not in bucket:  # one accession can appear on two pages while the feed shifts
            bucket.append(who)
    return sorted(
        by_acc.values(), key=lambda r: (datetime.fromisoformat(r["accepted"]), r["accession"])
    )


def issuer(ev: dict, by_cik: dict[int, list[str]], universe: set[str] | None = None) -> dict | None:
    """The issuer: the first Filer entry with a ticker in the universe, else the first with any ticker, else the
    first Filer entry (None without one); co-registrant filings list several Filers."""
    universe = universe or set()
    return next(
        (f for f in ev["filers"] if set(by_cik.get(f["cik"], [])) & universe),
        next(
            (f for f in ev["filers"] if by_cik.get(f["cik"])),
            ev["filers"][0] if ev["filers"] else None,
        ),
    )


def earlier_302(
    filings: pd.DataFrame, accession: str, day: str, days: int = cr.REPEAT_DAYS
) -> list[str]:
    """Other 8-K filings listing Item 3.02 (submissions 'items') dated in the `days` days before `day` (same-day
    filings are left to the register's own order, as catalysts.earlier_13d)."""
    if filings is None or not len(filings):
        return []
    start = (date.fromisoformat(day) - timedelta(days=days)).isoformat()
    f = filings[
        (filings["form"].str.upper() == EVENT_FORM)
        & (filings["accessionNumber"] != accession)
        & (filings["filingDate"] >= start)
        & (filings["filingDate"] < day)
    ]
    return [
        f"{r.form}|{r.accessionNumber}|{r.filingDate}|{r.items}"
        for r in f.itertuples()
        if EVENT_ITEM in cr.e9.items_of(r.items)
    ]


def coverage(position: str, close: float, previous: float | None, signal: str) -> dict:
    """Always FIRE (no abstention rule); the pre-entry move is recorded, as SEC13D's MOVED_ALREADY input: from the
    previous close when accepted DURING the signal session, none when accepted AFTER its close."""
    if position == "DURING":
        ratio = close / previous if previous else float("nan")
        ref = {"session": cr.us_prev_session(signal), "close": previous}
    else:
        ratio, ref = 1.0, {"session": signal, "close": close}
    return {
        "class": "FIRE",
        "rules": {},
        "reasons": [],
        "inputs": {
            "pre_entry_move": ratio - 1 if math.isfinite(ratio) else None,
            "reference_close": ref,
        },
    }


# ------------------------------------------------------------------------------- batch
def batch(
    now: datetime,
    client,
    ledger: list[dict] | None = None,
    records: list[dict] | None = None,
    clock=None,
) -> tuple[dict, list[dict]]:
    """Read the 8-K feed and build (BATCH, sets) for every new Item 3.02 8-K accepted since the window start
    (the protocol's batches, issuer and timing rules; bookkeeping as catalysts.sec13d_batch)."""
    fam, fam_sha = cr.family_protocol(FAMILY)
    ledger = paper.ledger_lines() if ledger is None else ledger
    records = cr.cat_lines() if records is None else records
    window_start = datetime.fromisoformat(fam["window_start"])
    entry = cr.us_entry_session(now)
    signal = cr.us_prev_session(entry)
    cutoff = cr.us_cutoff(entry)
    scan = cr._scan_for(ledger, "US", signal)
    if scan is None:
        raise RuntimeError(
            f"no US paper scan for the signal session {signal}; run paper-scan --market US first"
        )
    earlier_batches = [r for r in records if r["type"] == "BATCH" and r["family"] == FAMILY]
    prev_newest = next(
        (
            datetime.fromisoformat(b["feed"]["newest_entry"])
            for b in reversed(earlier_batches)
            if b["feed"]["newest_entry"]
        ),
        None,
    )
    pages, entries = [], []
    for k in range(FEED_PAGES):
        status, body = client.get(FEED_URL.format(start=100 * k))
        if status != 200:
            raise RuntimeError(f"EDGAR current 8-K feed page {k}: HTTP {status}")
        got = parse_feed(body)
        pages.append({"start": 100 * k, "sha256": cr._sha(body), "entries": len(got)})
        entries += got
        oldest = min((datetime.fromisoformat(e["accepted"]) for e in got), default=None)
        if (
            oldest is None
            or oldest < window_start
            or (prev_newest is not None and oldest < prev_newest)
        ):
            break
    times = [datetime.fromisoformat(e["accepted"]) for e in entries]
    listed = {e["accession"] for r in earlier_batches for e in r["events"]}
    evs = [
        e
        for e in events(entries)
        if datetime.fromisoformat(e["accepted"]) >= window_start and e["accession"] not in listed
    ]
    # A gap: the read never reached back to the previous batch's newest entry (the window start for the first
    # batch), or it read nothing at all. Missed filings are recorded as a gap, never backfilled.
    gap = (not times) or min(times) > (prev_newest if prev_newest is not None else window_start)
    status, tm_body = client.get(cr.TICKERS_URL)
    if status != 200:
        raise RuntimeError(f"SEC ticker map: HTTP {status}")
    by_cik, by_ticker = cr.ticker_maps(tm_body)
    feats = spec.scan_features(scan)
    universe = set(cr._universe(feats)["ticker"])
    chosen = {}
    for ev in evs:
        who = issuer(ev, by_cik, universe)
        tickers = by_cik.get(who["cik"], []) if who else []
        ok = [t for t in tickers if t in universe]
        chosen[ev["accession"]] = (who, tickers, ok[0] if ok else None)
    # every ticker of an event issuer (all its share classes), so a twin is never the event company itself
    excluded = sorted(
        {*scan["candidates_ranked"], *(t for _, tks, _ in chosen.values() for t in tks)}
    )
    # The repeat rule: any earlier Item 3.02 8-K of the issuer seen by this family (whatever its status) in the
    # 90 days before, plus the issuer's submissions; a skipped earlier filing is still "another 8-K with Item 3.02".
    seen_issuers: dict[int, datetime] = {}
    for b in earlier_batches:
        for e in b["events"]:
            if e.get("issuer_cik") is not None:
                t = datetime.fromisoformat(e["accepted"])
                seen_issuers[e["issuer_cik"]] = max(t, seen_issuers.get(e["issuer_cik"], t))
    statuses, sets = [], []
    today = now.astimezone(cr.NY).date().isoformat()
    for ev in evs:
        acc = ev["accession"]
        accepted = datetime.fromisoformat(ev["accepted"])
        who, tickers, ticker = chosen[acc]
        prior = seen_issuers.get(who["cik"]) if who else None
        if who:  # remembered whatever happens next, so a later filing of the issuer is a repeat of this one
            seen_issuers[who["cik"]] = accepted
        row = {
            "accession": acc,
            "issuer_cik": who["cik"] if who else None,
            "issuer_name": who["name"] if who else None,
            "accepted": ev["accepted"],
            "items": ev["items"],
            "tickers": tickers,
            "ticker": ticker,
        }

        def skip(code, reason):
            statuses.append({**row, "status": code, "reason": reason})

        if who is None:
            skip("SKIP_NO_TICKER", "no Filer entry for the filing in the feed")
            continue
        if not tickers:
            skip("SKIP_NO_TICKER", "the issuer CIK has no ticker in company_tickers_exchange")
            continue
        if ticker is None:
            skip(
                "SKIP_NOT_IN_UNIVERSE",
                f"none of {tickers} is fresh and eligible in {scan['scan_id']}",
            )
            continue
        pos = cr.acceptance_position(accepted, signal)
        if pos == "LATE":
            skip(
                "SKIP_LATE",
                f"accepted at or before the close of {cr.us_prev_session(signal)}; the register missed its window",
            )
            continue
        if (
            prior is not None
            and timedelta(0) <= accepted - prior
            and accepted.astimezone(cr.NY).date() - prior.astimezone(cr.NY).date()
            <= timedelta(days=cr.REPEAT_DAYS)
        ):
            skip(
                "SKIP_REPEAT_90D",
                f"an earlier Item 3.02 8-K of the issuer was accepted {prior.isoformat()}",
            )
            continue
        filings = cr.submissions(client, who["cik"])
        if not cr.is_operating(filings, today):
            skip(
                "SKIP_NOT_OPERATING",
                f"no 10-K, 10-Q, 20-F or 40-F in {cr.OPERATING_DAYS} days, a fund report, or no submissions",
            )
            continue
        repeat = earlier_302(filings, acc, accepted.astimezone(cr.NY).date().isoformat())
        if repeat:
            skip("SKIP_REPEAT_90D", "; ".join(repeat[:3]))
            continue
        frow = feats[feats["ticker"] == ticker].iloc[0]
        cov = coverage(pos, float(frow["close"]), spec._num(frow["previous"]), signal)
        set_id = f"CAT-{FAMILY}-{acc}"
        twins, level, log = cr.sec13d_twins(
            feats,
            ticker,
            excluded,
            scan["detector"]["selected"],
            cr.set_seed(set_id),
            client,
            by_ticker,
            today,
            reject=cr.reject_dilution,
        )
        sets.append(
            {
                "type": "CATALYST_SET",
                "register": cr.REGISTER_VERSION,
                "family": FAMILY,
                "market": "US",
                "set_id": set_id,
                "event_id": acc,
                "ticker": ticker,
                "signal_session": signal,
                "event": {
                    "accession": acc,
                    "form": EVENT_FORM,
                    "items": ev["items"],
                    "accepted": ev["accepted"],
                    "accepted_utc": utc_stamp(accepted.astimezone(timezone.utc)),
                    "position": pos,
                    "issuer_cik": who["cik"],
                    "issuer_name": who["name"],
                    "filers": ev["filers"],
                    "other_entries": ev["others"],
                    "url": ev["url"],
                },
                "entry": {"basis": "open", "session": entry, "text": fam["plan"]["entry"]},
                "entry_cutoff": utc_stamp(cutoff),
                "direction": int(fam["direction"]),
                "scan_id": scan["scan_id"],
                "scan_record_hash": scan["record_hash"],
                "features_file": scan["features_file"],
                "features_sha256": scan["features_sha256"],
                "signal": cr._signal(frow),
                "coverage": cov,
                "twins": twins,
                "twins_match_level": level,
                "twins_seed": cr.set_seed(set_id),
                "twins_checked": log,
                "cone": cr._cone(fam, records, "US", FAMILY),
                "windows": {
                    fam["plan"]["window"]: {
                        k: fam["plan"][k] for k in ("kind", "entry_window", "holding_sessions")
                    }
                },
                "plan": fam["plan"]["window"],
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
        "feed": {
            "pages": pages,
            "entries": len(entries),
            "oldest_entry": min(times).isoformat() if times else None,
            "newest_entry": max(times).isoformat() if times else None,
            "coverage_gap": gap,
        },
        "ticker_map_sha256": cr._sha(tm_body),
        "events": statuses,
        "protocol": {"id": fam["protocol_id"], "sha256": fam_sha},
    }
    return out, sets

"""Free public sensors: read, log, never trade.

Each source is a public endpoint that answers without a key or login (checked 2026-10-27 from the research container):
the Bluesky public API for any account's posts (Unusual Whales posts there as unusualwhales.bsky.social), StockTwits
trending symbols, SEC EDGAR full-text search for 8-K catalysts by keyword, CoinGecko trending coins, and Binance's
new-listing announcements. A pull writes every raw response, gzipped, under paper/sensors/raw/<stamp>/ with its sha256,
and appends one SENSOR_ALERT record per new item (deduplicated by source and id) plus one SENSOR_PULL record to
paper/sensors/sensors.jsonl, hash-chained by paper.append. A sensor is a scanner to be scored, not a rule: nothing here
reads a price or makes a decision. Scoring (lift of a source's symbols against the base rate, net of costs) comes later,
from the daily bars the paper scans already pull.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import paper
from .provenance import PKG_ROOT

SENSORS_DIR = PKG_ROOT / "paper" / "sensors"
LOG = SENSORS_DIR / "sensors.jsonl"
RAW = SENSORS_DIR / "raw"
UA = "KOD-Machine research harness (owner-operated; sensors.py)"
DEFAULT_HANDLES = ("unusualwhales.bsky.social",)
DEFAULT_KEYWORDS = (
    "fast track",
    "breakthrough therapy",
    "definitive agreement",
    "merger agreement",
    "contract award",
    "FDA approval",
)
CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")
PAREN = re.compile(r"\(([A-Z]{1,6})\)")
TEXT_MAX = 500


def _rel(path: Path) -> str:
    """Path relative to the package when inside it (the committed layout), else absolute (tests, scratch runs)."""
    try:
        return str(path.resolve().relative_to(PKG_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _abs(raw_path: str) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else PKG_ROOT / p


def _utc(moment: datetime | None = None) -> str:
    return (
        (moment or datetime.now(timezone.utc))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def fetch(url: str, user_agent: str = UA, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": user_agent, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def symbols_in(text: str) -> list[str]:
    """Cashtags ($NVDA) and parenthesised codes (Nvidia (NVDA)), in order of appearance, unique."""
    out = []
    for m in CASHTAG.finditer(text or ""):
        out.append(m.group(1))
    for m in PAREN.finditer(text or ""):
        out.append(m.group(1))
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


# ------------------------------------------------------------------------------------------------ sources
# Each source returns (alerts, raw_bytes). An alert: source_id, posted_at (the source's own time, or None), symbols,
# text, url, extra.


def bluesky(handle: str, limit: int = 100, fetcher=fetch) -> tuple[list[dict], bytes]:
    q = urllib.parse.urlencode({"actor": handle, "limit": limit, "filter": "posts_no_replies"})
    raw = fetcher(f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?{q}")
    alerts = []
    for item in json.loads(raw).get("feed", []):
        if "reason" in item:  # a repost
            continue
        post = item["post"]
        rec = post.get("record", {})
        text = rec.get("text", "")
        rkey = post["uri"].rsplit("/", 1)[-1]
        alerts.append(
            {
                "source_id": post["uri"],
                "posted_at": rec.get("createdAt"),
                "symbols": symbols_in(text),
                "text": text[:TEXT_MAX],
                "url": f"https://bsky.app/profile/{post['author']['handle']}/post/{rkey}",
                "extra": {"likes": post.get("likeCount"), "reposts": post.get("repostCount")},
            }
        )
    return alerts, raw


def stocktwits_trending(fetcher=fetch, today: str | None = None) -> tuple[list[dict], bytes]:
    raw = fetcher("https://api.stocktwits.com/api/2/trending/symbols.json")
    day = today or _utc()[:10]
    alerts = []
    for rank, s in enumerate(json.loads(raw).get("symbols", []), start=1):
        alerts.append(
            {
                "source_id": f"{day}:{s['symbol']}",
                "posted_at": None,
                "symbols": [s["symbol"]],
                "text": f"StockTwits trending #{rank}: {s.get('title', '')}",
                "url": f"https://stocktwits.com/symbol/{s['symbol']}",
                "extra": {"rank": rank},
            }
        )
    return alerts, raw


def edgar_8k(
    keywords=DEFAULT_KEYWORDS,
    days: int = 3,
    fetcher=fetch,
    today: str | None = None,
    user_agent: str | None = None,
) -> tuple[list[dict], bytes]:
    end = datetime.fromisoformat(today) if today else datetime.now(timezone.utc)
    start = (end - timedelta(days=days)).date().isoformat()
    ua = user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT") or UA
    pages, alerts, seen = [], [], set()
    for kw in keywords:
        q = urllib.parse.urlencode(
            {
                "q": f'"{kw}"',
                "forms": "8-K",
                "dateRange": "custom",
                "startdt": start,
                "enddt": end.date().isoformat(),
            }
        )
        raw = fetcher(f"https://efts.sec.gov/LATEST/search-index?{q}", user_agent=ua)
        pages.append({"keyword": kw, "response": json.loads(raw)})
        for hit in pages[-1]["response"].get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            adsh = src.get("adsh") or hit.get("_id", "").split(":")[0]
            if not adsh or adsh in seen:
                continue
            seen.add(adsh)
            names = src.get("display_names") or []
            syms = []
            for n in names:
                syms += [s for s in PAREN.findall(n) if not s.startswith("CIK")]
            cik = (src.get("ciks") or [""])[0].lstrip("0")
            doc = hit.get("_id", "").split(":")[-1]
            alerts.append(
                {
                    "source_id": adsh,
                    "posted_at": src.get("file_date"),
                    "symbols": list(dict.fromkeys(syms)),
                    "text": f'8-K matching "{kw}": {"; ".join(names)[:TEXT_MAX]}',
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{doc}"
                    if cik
                    else "",
                    "extra": {
                        "keyword": kw,
                        "form": src.get("form"),
                        "period_ending": src.get("period_ending"),
                    },
                }
            )
    return alerts, json.dumps(pages, sort_keys=True).encode()


def coingecko_trending(fetcher=fetch, today: str | None = None) -> tuple[list[dict], bytes]:
    raw = fetcher("https://api.coingecko.com/api/v3/search/trending")
    day = today or _utc()[:10]
    alerts = []
    for rank, c in enumerate(json.loads(raw).get("coins", []), start=1):
        it = c.get("item", {})
        sym = str(it.get("symbol", "")).upper()
        alerts.append(
            {
                "source_id": f"{day}:{it.get('id')}",
                "posted_at": None,
                "symbols": [sym] if sym else [],
                "text": f"CoinGecko trending #{rank}: {it.get('name')} ({sym}), market-cap rank {it.get('market_cap_rank')}",
                "url": f"https://www.coingecko.com/en/coins/{it.get('id')}",
                "extra": {"rank": rank},
            }
        )
    return alerts, raw


def binance_listings(fetcher=fetch) -> tuple[list[dict], bytes]:
    url = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=20"
        "&catalogId=48"
    )
    raw = fetcher(url)
    alerts = []
    for cat in json.loads(raw).get("data", {}).get("catalogs", []):
        for a in cat.get("articles", []):
            title = a.get("title", "")
            ms = a.get("releaseDate")
            posted = _utc(datetime.fromtimestamp(ms / 1000, timezone.utc)) if ms else None
            alerts.append(
                {
                    "source_id": str(a.get("code")),
                    "posted_at": posted,
                    "symbols": [s for s in re.findall(r"\(([A-Z0-9]{2,10})\)", title)],
                    "text": title[:TEXT_MAX],
                    "url": f"https://www.binance.com/en/support/announcement/{a.get('code')}",
                    "extra": {"catalog": cat.get("catalogName")},
                }
            )
    return alerts, raw


# Share-issue phrases, matched on whole hyphen-separated slug words (a substring match let "waran" hit "penawaran" and
# "saham-baru" hit "saham baru lepas suspensi", where "baru" means "just").
DILUTION_PHRASES = {
    "rights_issue": (("rights", "issue"), ("right", "issue"), ("hmetd",), ("pmhmetd",)),
    "private_placement": (("private", "placement"), ("pmthmetd",), ("tanpa", "hmetd")),
    "capital_increase": (("penambahan", "modal"), ("tambah", "modal")),
    "convertible_or_warrant": (("obligasi", "konversi"), ("waran",), ("konversi", "waran")),
}
ISSUE_VERBS = {"penerbitan", "terbitkan", "menerbitkan"}


def dilution_kinds(slug: str) -> list[str]:
    words = slug.lower().split("-")

    def has(seq):
        n = len(seq)
        return any(tuple(words[i : i + n]) == seq for i in range(len(words) - n + 1))

    kinds = [k for k, seqs in DILUTION_PHRASES.items() if any(has(q) for q in seqs)]
    if has(("saham", "baru")) and ISSUE_VERBS & set(
        words
    ):  # "new shares" only next to an issuing verb
        kinds.append("new_shares")
    if (
        "private_placement" in kinds
        and has(("tanpa", "hmetd"))
        and not (has(("rights", "issue")) or has(("right", "issue")))
    ):
        kinds = [
            k for k in kinds if k != "rights_issue"
        ]  # "tanpa HMETD" (without pre-emptive rights) is a placement, not a rights issue
    return kinds


EN_STOP = {"AKSI"}  # ticker codes that are also common Indonesian headline words
EN_SLUG = re.compile(
    r"<loc>https://www\.emitennews\.com/news/([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>"
)


def idx_tickers(root: Path | None = None) -> set[str]:
    """IDX codes known locally: the pinned mirror's per-ticker files plus data/universe/extra_tickers.csv."""
    root = root or PKG_ROOT / "data"
    codes = {f.stem.upper() for f in (root / "raw" / "idx_mirror").glob("*/Saham/Semua/*.csv")}
    extra = root / "universe" / "extra_tickers.csv"
    if extra.exists():
        codes |= {
            ln.split(",")[0].strip().upper()
            for ln in extra.read_text().splitlines()[1:]
            if ln.strip()
        }
    return codes


def emitennews_dilution(
    tickers: set[str] | None = None,
    year: int | None = None,
    days: int = 7,
    fetcher=fetch,
    today: str | None = None,
) -> tuple[list[dict], bytes]:
    """EmitenNews headlines (public sitemap; robots.txt allows it) about new shares: rights issues, private placements, convertible bonds,
    warrants. Only the last `days` days by the sitemap's lastmod. A watch flag only: IDX_DILUTION_v1 tested a different event (the day new shares
    reach IDX's listed-share count, 2023, 15 trades, see its ERRATA_1), and no test has yet scored these announcements."""
    day = today or _utc()[:10]
    raw = fetcher(f"https://www.emitennews.com/sitemap-{year or int(day[:4])}.xml")
    codes = idx_tickers() if tickers is None else tickers
    cutoff = (datetime.fromisoformat(day) - timedelta(days=days)).date().isoformat()
    alerts = []
    for slug, lastmod in EN_SLUG.findall(raw.decode("utf-8", "replace")):
        words = dilution_kinds(slug)
        if not words or lastmod[:10] < cutoff:
            continue
        syms = sorted(
            {
                t.upper()
                for t in slug.split("-")
                if t.upper() in codes and len(t) == 4 and t.upper() not in EN_STOP
            }
        )
        alerts.append(
            {
                "source_id": slug,
                "posted_at": lastmod[:10],
                "symbols": syms,
                "text": slug.replace("-", " ")[:TEXT_MAX],
                "url": f"https://www.emitennews.com/news/{slug}",
                "extra": {"kind": words, "market": "IDX"},
            }
        )
    return alerts, raw


def default_sources(handles=DEFAULT_HANDLES, keywords=DEFAULT_KEYWORDS, fetcher=fetch) -> dict:
    src = {f"bluesky:{h}": (lambda h=h: bluesky(h, fetcher=fetcher)) for h in handles}
    src["stocktwits_trending"] = lambda: stocktwits_trending(fetcher=fetcher)
    src["edgar_8k"] = lambda: edgar_8k(keywords, fetcher=fetcher)
    src["coingecko_trending"] = lambda: coingecko_trending(fetcher=fetcher)
    src["binance_listings"] = lambda: binance_listings(fetcher=fetcher)
    src["emitennews_dilution"] = lambda: emitennews_dilution(fetcher=fetcher)
    return src


# ------------------------------------------------------------------------------------------------ log
def known_ids(path: Path = LOG) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    return {
        (r["source"], r["source_id"])
        for r in paper.ledger_lines(path)
        if r.get("type") == "SENSOR_ALERT"
    }


def pull(
    sources: dict,
    log: Path = LOG,
    raw_dir: Path = RAW,
    timestamper=None,
    now: datetime | None = None,
) -> dict:
    """Run every source; one source's failure does not lose the others. Returns the pull summary."""
    stamp = _utc(now)
    folder = raw_dir / stamp.replace("-", "").replace(":", "")
    folder.mkdir(parents=True, exist_ok=False)
    seen = known_ids(log)
    records, counts, errors = [], {}, {}
    for name, run in sources.items():
        try:
            alerts, raw = run()
        except Exception as exc:  # noqa: BLE001  a dead feed is recorded, not fatal
            errors[name] = f"{type(exc).__name__}: {exc}"[:300]
            continue
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        path = folder / f"{safe}.json.gz"
        with gzip.GzipFile(path, "wb", mtime=0) as fh:
            fh.write(raw)
        sha = hashlib.sha256(raw).hexdigest()
        new = 0
        for a in alerts:
            if (name, a["source_id"]) in seen:
                continue
            seen.add((name, a["source_id"]))
            new += 1
            records.append(
                {
                    "type": "SENSOR_ALERT",
                    "source": name,
                    "source_id": a["source_id"],
                    "posted_at": a.get("posted_at"),
                    "observed_at": stamp,
                    "symbols": a.get("symbols", []),
                    "text": a.get("text", "")[:TEXT_MAX],
                    "url": a.get("url", ""),
                    "extra": a.get("extra", {}),
                    "raw_path": _rel(path),
                    "raw_sha256": sha,
                }
            )
        counts[name] = {"items": len(alerts), "new": new}
    records.append(
        {
            "type": "SENSOR_PULL",
            "observed_at": stamp,
            "counts": counts,
            "errors": errors,
            "raw_dir": _rel(folder),
        }
    )
    stored = paper.append(records, path=log, timestamper=timestamper)
    return {
        "stamp": stamp,
        "records": len(stored),
        "alerts_new": sum(c["new"] for c in counts.values()),
        "counts": counts,
        "errors": errors,
        "head": stored[-1]["record_hash"],
    }


def verify(log: Path = LOG) -> list[str]:
    """Chain intact, every raw file present and matching its sha256."""
    problems = list(paper.verify_chain(log)) if log.exists() else [f"{log.name} missing"]
    for r in paper.ledger_lines(log) if log.exists() else []:
        if r.get("type") != "SENSOR_ALERT":
            continue
        p = _abs(r["raw_path"])
        if not p.exists():
            problems.append(f"missing raw {r['raw_path']}")
            continue
        with gzip.open(p, "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != r["raw_sha256"]:
                problems.append(f"raw hash mismatch {r['raw_path']}")
    return problems

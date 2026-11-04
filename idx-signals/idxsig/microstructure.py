"""Measured microstructure for crypto paper candidates: a read-only side-car, never an input to a decision.

The frozen paper cycle assumes a cost per side (PAPER-POLICY-v4: 0.2% for crypto) and daily bars. This module measures
what the assumption stands for, for the same candidates, without changing any rule or any ledger line:

  BOOK      the Binance spot order book (1000 levels a side) taken right after the decision: spread, the depth within a
            few percent of the mid, and the average price of a market buy and a market sell of fixed sizes (and of the
            plan's own position sizes). Forward only: a book cannot be recovered afterwards.
  TIMELINE  the candidate's 1-minute bars for the signal day and the day after: when in the day the move happened
            (the minute it first crossed +10/20/30% over the previous close), how much was given back from the peak,
            the last hour's return, and the path after the day's close. Built 26 hours after the day ended, or later
            for history (retrospective=True when more than 3 days after the decision); descriptive only, no profit is
            claimed from it.

Records are hash-chained in paper/microstructure/crypto.jsonl through paper.append (the ledger's own mechanism); the raw
responses and bars sit beside it, hashed in the record, in git (data/raw is not tracked, and the cloud container is not
kept). Nothing here places an order. Spot data comes from data-api.binance.vision (api.binance.com refuses US hosts).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import paper
from .provenance import PKG_ROOT, rel

DIR = PKG_ROOT / "paper" / "microstructure"
SIDECAR = DIR / "crypto.jsonl"
RAW = DIR / "raw"
BASE = "https://data-api.binance.vision/api/v3"
SIZES_USDT = (100.0, 1_000.0, 10_000.0)
DEPTH_LEVELS = 1000
PCTS = (0.01, 0.02, 0.05)
CROSS = (0.10, 0.20, 0.30)
HORIZONS_MIN = (60, 240, 1440)
LOOKBACK_MS = 6 * 3_600_000  # bars fetched before the signal day, to find the previous close
POST_MS = 25 * 3_600_000  # bars fetched after the day's end (24 h of path + a margin)
DECISION_TIME_MAX_OFFSET_S = (
    900  # a book counts as "at decision time" if taken within 15 minutes of the decision
)
TIMELINE_AFTER_H = 26  # a timeline is built once the signal day has been over for this long
RETROSPECTIVE_AFTER_S = (
    3 * 86_400
)  # built more than this long after the decision = a rebuild of history
FEE_PER_SIDE = 0.001  # Binance spot, standard tier: recorded separately from the book slippage
MINUTE = 60_000
DAY = 86_400_000


# ---------------------------------------------------------------------------------- network
def _get(url: str, retries: int = 3, timeout: int = 25):
    """GET JSON with bounded retries; access blocks and rate limits stop immediately."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 451):
                raise RuntimeError(f"access blocked by Binance (HTTP {exc.code}) on {url}") from exc
            if exc.code in (418, 429):
                raise RuntimeError(f"rate limited by Binance (HTTP {exc.code}) on {url}") from exc
            last = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url}: {last}")


def fetch_depth(pair: str, limit: int = DEPTH_LEVELS) -> tuple[dict, dict]:
    """(raw depth response, timing) with local UTC milliseconds before and after the request and the server clock
    offset (server time minus the local midpoint)."""
    t0 = int(time.time() * 1000)
    server = _get(f"{BASE}/time")["serverTime"]
    t1 = int(time.time() * 1000)
    raw = _get(f"{BASE}/depth?symbol={pair}&limit={limit}")
    t2 = int(time.time() * 1000)
    return raw, {
        "request_start_ms": t1,
        "response_end_ms": t2,
        "server_clock_offset_ms": int(server - (t0 + t1) / 2),
    }


def fetch_minutes(pair: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    """1-minute bars with open time in [start_ms, end_ms). Minutes without a trade are absent from the API's answer."""
    rows, cursor = [], start_ms
    while cursor < end_ms:
        page = _get(
            f"{BASE}/klines?symbol={pair}&interval=1m&startTime={cursor}&endTime={end_ms - 1}&limit=1000"
        )
        if not page:
            break
        rows.extend(page)
        cursor = page[-1][0] + MINUTE
        if len(page) < 1000:
            break
        time.sleep(0.15)
    cols = ["t", "o", "h", "l", "c", "v", "close_t", "qv", "n", "tb", "tq", "_"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df.drop(columns=["close_t", "tb", "tq", "_"])
    for c in ("o", "h", "l", "c", "v", "qv"):
        df[c] = df[c].astype(float)
    df["t"], df["n"] = df["t"].astype("int64"), df["n"].astype("int64")
    return df.drop(columns=["close_t", "tb", "tq", "_"]).drop_duplicates("t").reset_index(drop=True)


# ---------------------------------------------------------------------------------- the book
def _levels(rows) -> list[tuple[float, float]]:
    return [(float(p), float(q)) for p, q in rows if float(q) > 0]


def book_fill(levels: list[tuple[float, float]], notional: float, mid: float, side: str) -> dict:
    """Average price of a market order worth `notional` USDT at the mid, walked through the book.
    side="buy": `levels` are the asks, best first; spend `notional` USDT. side="sell": `levels` are the bids, best
    first; sell the quantity worth `notional` at the mid. slippage_bps is against the mid (so it includes the half
    spread), positive = worse than the mid. If the fetched levels cannot absorb the order, complete is False and
    the slippage is measured on the part that filled, which understates the true cost."""
    if side == "buy":
        remaining, base, spent = notional, 0.0, 0.0
        for price, qty in levels:
            take = min(remaining, price * qty)
            base += take / price
            spent += take
            remaining -= take
            if remaining <= 1e-9:
                break
        done = spent > 0
        vwap = spent / base if done else None
        filled = spent / notional
        slip = (vwap / mid - 1.0) * 1e4 if done else None
    elif side == "sell":
        target = notional / mid
        remaining, got = target, 0.0
        for price, qty in levels:
            take = min(remaining, qty)
            got += take * price
            remaining -= take
            if remaining <= 1e-12:
                break
        sold = target - remaining
        done = sold > 0
        vwap = got / sold if done else None
        filled = sold / target
        slip = (1.0 - vwap / mid) * 1e4 if done else None
    else:
        raise ValueError(side)
    return {
        "complete": bool(filled >= 1 - 1e-9),
        "filled_fraction": round(float(filled), 6),
        "vwap": vwap,
        "slippage_bps": None if slip is None else round(float(slip), 3),
    }


def depth_within(levels: list[tuple[float, float]], mid: float, pct: float) -> float:
    """USDT value resting within `pct` of the mid on one side."""
    return float(sum(p * q for p, q in levels if abs(p / mid - 1.0) <= pct))


def book_metrics(depth: dict, sizes=SIZES_USDT) -> dict | None:
    """Spread, depth and fill prices from one depth response. None if a side of the book is empty."""
    bids, asks = _levels(depth["bids"]), _levels(depth["asks"])
    if not bids or not asks:
        return None
    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2.0
    out = {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": mid,
        "spread_bps": round((best_ask - best_bid) / mid * 1e4, 3),
        "levels": [len(bids), len(asks)],
        "span_pct": [round((mid - bids[-1][0]) / mid, 6), round((asks[-1][0] - mid) / mid, 6)],
        "depth_usdt": {
            f"{int(p * 100)}pct": {
                "bid": round(depth_within(bids, mid, p), 2),
                "ask": round(depth_within(asks, mid, p), 2),
            }
            for p in PCTS
        },
        "fills": {},
    }
    for s in sorted({float(x) for x in sizes}):
        out["fills"][f"{s:g}"] = {
            "buy": book_fill(asks, s, mid, "buy"),
            "sell": book_fill(bids, s, mid, "sell"),
        }
    return out


# ---------------------------------------------------------------------------------- the minutes
def _grid(bars: pd.DataFrame, start_ms: int, n: int) -> tuple[np.ndarray, ...]:
    """Close, high, quote volume and trade count per minute from start_ms, n minutes. A minute without a trade carries
    the last close forward (volume 0); before the first bar the close is NaN."""
    idx = ((bars["t"].to_numpy() - start_ms) // MINUTE).astype(int)
    keep = (idx >= 0) & (idx < n)
    close, high = np.full(n, np.nan), np.full(n, np.nan)
    qv, cnt = np.zeros(n), np.zeros(n)
    close[idx[keep]] = bars["c"].to_numpy()[keep]
    high[idx[keep]] = bars["h"].to_numpy()[keep]
    qv[idx[keep]] = bars["qv"].to_numpy()[keep]
    cnt[idx[keep]] = bars["n"].to_numpy()[keep]
    return pd.Series(close).ffill().to_numpy(), high, qv, cnt


def timeline_metrics(bars: pd.DataFrame, day_start_ms: int, available_until_ms: int) -> dict:
    """What the signal day looked like minute by minute, and the path after its close (UTC day, like the daily scan).
    `available_until_ms` is the end of the last minute that had finished when the bars were fetched: later horizons are
    None, never extrapolated. All returns are fractions."""
    n_day, n_all = DAY // MINUTE, (DAY + POST_MS) // MINUTE
    pre = bars[bars["t"] < day_start_ms]
    prev_close = float(pre["c"].iloc[-1]) if len(pre) else None
    close, high, qv, cnt = _grid(bars[bars["t"] >= day_start_ms], day_start_ms, n_all)
    day_close_arr = close[:n_day]
    if np.isnan(day_close_arr).all():
        return {"error": "no bars on the signal day"}
    day_end = float(day_close_arr[-1])
    base = prev_close if prev_close else float(bars[bars["t"] >= day_start_ms]["o"].iloc[0])
    day_high = np.nanmax(high[:n_day])
    peak_min = int(np.nanargmax(high[:n_day]))
    cross = {}
    for x in CROSS:
        hit = np.flatnonzero(day_close_arr >= base * (1 + x))
        cross[f"{int(round(x * 100))}"] = int(hit[0]) if len(hit) else None
    last = (
        lambda h: day_end / day_close_arr[n_day - 1 - h] - 1.0
        if not np.isnan(day_close_arr[n_day - 1 - h])
        else None
    )  # noqa: E731
    day_qv = float(qv[:n_day].sum())
    post = {}
    for h in HORIZONS_MIN:
        end_of_target = day_start_ms + DAY + h * MINUTE  # the end of the minute that closes at +h
        ok = end_of_target <= available_until_ms and n_day + h - 1 < n_all
        post[f"{h}m"] = float(close[n_day + h - 1] / day_end - 1.0) if ok else None
    return {
        "base_price": base,
        "base_is_previous_close": prev_close is not None,
        "day_close": day_end,
        "ret_day": day_end / base - 1.0,
        "peak_ret": float(day_high / base - 1.0),
        "peak_minute": peak_min,
        "giveback_from_peak": float(day_end / day_high - 1.0),
        "cross_minute": cross,
        "ret_last_1h": last(60),
        "ret_last_4h": last(240),
        "quote_volume_day": day_qv,
        "volume_share_last_1h": float(qv[n_day - 60 : n_day].sum() / day_qv) if day_qv else None,
        "minutes_with_trades": int((cnt[:n_day] > 0).sum()),
        "post_close_ret": post,
    }


# ---------------------------------------------------------------------------------- storage
def _gz(text: str) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(text.encode("utf-8"))
    return buf.getvalue()


def _store(path: Path, payload: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(payload)
    return {"path": rel(path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def bars_csv(bars: pd.DataFrame) -> str:
    out = io.StringIO()
    bars[["t", "o", "h", "l", "c", "v", "qv", "n"]].to_csv(
        out, index=False, float_format="%.10g", lineterminator="\n"
    )
    return out.getvalue()


def sidecar_keys(path: Path = SIDECAR) -> set[tuple[str, str]]:
    """(record type, decision_id) already recorded, so a rerun or a backfill never doubles a record."""
    return {(r["type"], r["decision_id"]) for r in paper.ledger_lines(path)}


def verify(path: Path = SIDECAR) -> list[str]:
    """Chain problems plus any raw file that is missing or whose hash differs from the record."""
    problems = paper.verify_chain(path) if path.exists() else []
    for r in paper.ledger_lines(path):
        ref = r.get("raw")
        if ref:
            p = PKG_ROOT / ref["path"]
            if not p.exists():
                problems.append(f"{r['decision_id']}: {ref['path']} is missing")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != ref["sha256"]:
                problems.append(
                    f"{r['decision_id']}: {ref['path']} does not match its recorded hash"
                )
    return problems


# ---------------------------------------------------------------------------------- the candidates
def scan_decisions(scan_id: str, ledger: Path = paper.LEDGER) -> list[dict]:
    """The DECISION records of one crypto scan, from the ledger (read only)."""
    if not scan_id.startswith("SCAN-CRYPTO-"):
        raise ValueError(f"{scan_id} is not a crypto scan")
    return [
        r for r in paper.ledger_lines(ledger) if r["type"] == "DECISION" and r["scan_id"] == scan_id
    ]


def crypto_scans(ledger: Path = paper.LEDGER) -> list[tuple[str, str]]:
    """(scan_id, signal session) of every crypto scan that has candidates, oldest first."""
    candidates = {r["scan_id"] for r in paper.ledger_lines(ledger) if r["type"] == "DECISION"}
    return [
        (r["scan_id"], r["session"])
        for r in paper.ledger_lines(ledger)
        if r["type"] == "SCAN" and r.get("market") == "CRYPTO" and r["scan_id"] in candidates
    ]


def _parse_utc(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def take_book(decision: dict, sidecar: Path = SIDECAR, now: datetime | None = None) -> dict | None:
    """Fetch and record one decision's book. Returns the stored record, or None if it could not be taken."""
    pair, scan_id = decision["instrument"]["pair"], decision["scan_id"]
    try:
        raw, timing = fetch_depth(pair)
    except RuntimeError as exc:
        print(f"microstructure: no book for {pair}: {exc}")
        return None
    metrics = book_metrics(raw, sizes=SIZES_USDT + tuple(_plan_sizes(decision)))
    if metrics is None:
        print(f"microstructure: empty book for {pair}")
        return None
    taken = datetime.fromtimestamp(timing["request_start_ms"] / 1000, tz=timezone.utc)
    stamp = taken.strftime("%Y%m%dT%H%M%SZ")
    ref = _store(
        RAW / scan_id / f"{decision['instrument']['ticker']}.depth.{stamp}.json.gz",
        _gz(json.dumps(raw, separators=(",", ":"))),
    )
    rec = {
        "type": "BOOK",
        "decision_id": decision["decision_id"],
        "scan_id": scan_id,
        "pair": pair,
        "decided_at": decision["decided_at"],
        "taken_at": taken.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offset_s": round(
            timing["request_start_ms"] / 1000 - _parse_utc(decision["decided_at"]).timestamp(), 1
        ),
        "timing": timing,
        "decision_quote": decision.get("verified_price", {}).get("quote"),
        "assumed_cost_per_side": (decision.get("plan", {}).get("costs_per_side") or [None])[0],
        "assumed_fee_per_side": FEE_PER_SIDE,
        "plan_sizes_usdt": _plan_sizes(decision),
        "book": metrics,
        "raw": ref,
        "source": f"{BASE}/depth?symbol={pair}&limit={DEPTH_LEVELS}",
    }
    return paper.append([rec], path=sidecar)[0]


def _plan_sizes(decision: dict) -> list[float]:
    return sorted(
        {
            round(float(s["position_usdt"]), 2)
            for s in decision.get("plan", {}).get("scenarios", [])
            if s.get("position_usdt")
        }
    )


def take_timeline(
    decision: dict, sidecar: Path = SIDECAR, now: datetime | None = None
) -> dict | None:
    pair, scan_id, session = (
        decision["instrument"]["pair"],
        decision["scan_id"],
        decision["signal_session"],
    )
    day_start = int(
        datetime.strptime(session, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000
    )
    fetched = now or datetime.now(timezone.utc)
    fetched_ms = int(fetched.timestamp() * 1000)
    try:
        bars = fetch_minutes(
            pair, day_start - LOOKBACK_MS, min(day_start + DAY + POST_MS, fetched_ms)
        )
    except RuntimeError as exc:
        print(f"microstructure: no minutes for {pair}: {exc}")
        return None
    if bars.empty:
        print(f"microstructure: no minute bars for {pair} on {session}")
        return None
    available_until = (
        fetched_ms // MINUTE
    ) * MINUTE  # minutes that had finished when the call was made
    metrics = timeline_metrics(bars, day_start, available_until)
    if "error" in metrics:
        print(f"microstructure: {pair} {session}: {metrics['error']}")
        return None
    ref = _store(
        RAW / scan_id / f"{decision['instrument']['ticker']}.minutes.csv.gz", _gz(bars_csv(bars))
    )
    late = (fetched - _parse_utc(decision["decided_at"])).total_seconds() > RETROSPECTIVE_AFTER_S
    rec = {
        "type": "TIMELINE",
        "decision_id": decision["decision_id"],
        "scan_id": scan_id,
        "pair": pair,
        "signal_session": session,
        "retrospective": bool(late),
        "fetched_at": fetched.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decided_at": decision["decided_at"],
        "daily_close_in_ledger": decision.get("verified_price", {}).get("close"),
        "decision_quote": decision.get("verified_price", {}).get("quote"),
        "metrics": metrics,
        "raw": ref,
        "bars": int(len(bars)),
        "source": f"{BASE}/klines?symbol={pair}&interval=1m",
    }
    return paper.append([rec], path=sidecar)[0]


def run_for_scan(
    scan_id: str,
    books: bool = True,
    timelines: bool = True,
    ledger: Path = paper.LEDGER,
    sidecar: Path = SIDECAR,
    now: datetime | None = None,
) -> list[Path]:
    """Record BOOK (time-sensitive, first) and TIMELINE for every candidate of one crypto scan that does not have them
    yet. Returns the files written, for the commit."""
    done, written = sidecar_keys(sidecar), set()
    decisions = scan_decisions(scan_id, ledger)
    before = len(paper.ledger_lines(sidecar))
    for kind, wanted, take in (
        ("BOOK", books, lambda d: take_book(d, sidecar)),
        ("TIMELINE", timelines, lambda d: take_timeline(d, sidecar, now)),
    ):
        for d in decisions if wanted else []:
            if (kind, d["decision_id"]) in done:
                continue
            try:  # one candidate's failure must not lose the others' records
                rec = take(d)
            except Exception as exc:  # noqa: BLE001
                print(f"microstructure: {kind} for {d['decision_id']} failed: {exc}")
                rec = None
            if rec:
                written.add(PKG_ROOT / rec["raw"]["path"])
    if len(paper.ledger_lines(sidecar)) > before:
        written.add(sidecar)
    return sorted(written)


def catch_up(
    now: datetime | None = None, ledger: Path = paper.LEDGER, sidecar: Path = SIDECAR
) -> list[Path]:
    """TIMELINE for every crypto scan whose signal day ended at least TIMELINE_AFTER_H hours ago (so the full next-day
    path exists) and has none yet. Also rebuilds history the first time it runs. Never takes a book."""
    now = now or datetime.now(timezone.utc)
    written: set[Path] = set()
    for scan_id, session in crypto_scans(ledger):
        day_end = datetime.strptime(session, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(
            days=1
        )
        if now >= day_end + timedelta(hours=TIMELINE_AFTER_H):
            written.update(
                run_for_scan(
                    scan_id, books=False, timelines=True, ledger=ledger, sidecar=sidecar, now=now
                )
            )
    return sorted(written)


# ---------------------------------------------------------------------------------- the summary
def _q(xs: list[float], p: float) -> float | None:
    return float(np.percentile(xs, p)) if xs else None


def summarize(sidecar: Path = SIDECAR) -> dict:
    """Plain statistics of what the side-car holds. Descriptive only: no return here is a trading result."""
    recs = paper.ledger_lines(sidecar)
    books = [r for r in recs if r["type"] == "BOOK"]
    live = [r for r in books if r["offset_s"] <= DECISION_TIME_MAX_OFFSET_S]
    out: dict = {
        "books": {
            "recorded": len(books),
            "at_decision_time": len(live),
            "note": f"'at decision time' = taken within {DECISION_TIME_MAX_OFFSET_S}s of the decision",
        }
    }
    if live:
        sizes = sorted(
            {k for r in live for k in r["book"]["fills"] if float(k) in SIZES_USDT}, key=float
        )
        out["books"]["spread_bps"] = {
            "median": _q([r["book"]["spread_bps"] for r in live], 50),
            "p90": _q([r["book"]["spread_bps"] for r in live], 90),
        }
        out["books"]["assumed_cost_per_side_bps"] = live[0]["assumed_cost_per_side"] * 1e4
        out["books"]["fee_per_side_bps"] = FEE_PER_SIDE * 1e4
        out["books"]["by_size_usdt"] = {}
        for s in sizes:
            cell = {}
            for side in ("buy", "sell"):
                fills = [r["book"]["fills"][s][side] for r in live if s in r["book"]["fills"]]
                full = [f["slippage_bps"] for f in fills if f["complete"]]
                cell[side] = {
                    "n": len(fills),
                    "complete_share": round(len(full) / len(fills), 3) if fills else None,
                    "median_bps": _q(full, 50),
                    "p90_bps": _q(full, 90),
                }
            out["books"]["by_size_usdt"][s] = cell
    tl = [r for r in recs if r["type"] == "TIMELINE"]
    out["timelines"] = {"recorded": len(tl), "retrospective": sum(r["retrospective"] for r in tl)}
    if tl:
        m = [r["metrics"] for r in tl]
        crossed = lambda k: [
            x["cross_minute"][k] for x in m if x["cross_minute"].get(k) is not None
        ]  # noqa: E731
        out["timelines"].update(
            {
                "ret_day": {
                    "median": _q([x["ret_day"] for x in m], 50),
                    "min": min(x["ret_day"] for x in m),
                },
                "peak_ret_median": _q([x["peak_ret"] for x in m], 50),
                "giveback_from_peak_median": _q([x["giveback_from_peak"] for x in m], 50),
                "minute_of_first_30pct_close": {
                    "n": len(crossed("30")),
                    "median": _q(crossed("30"), 50),
                },
                "minute_of_peak_median": _q([x["peak_minute"] for x in m], 50),
                "ret_last_1h_median": _q(
                    [x["ret_last_1h"] for x in m if x["ret_last_1h"] is not None], 50
                ),
                "post_close_ret": {
                    h: {"n": len(v), "median": _q(v, 50), "mean": float(np.mean(v)) if v else None}
                    for h in (f"{x}m" for x in HORIZONS_MIN)
                    for v in [
                        [
                            x_["post_close_ret"][h]
                            for x_ in m
                            if x_["post_close_ret"].get(h) is not None
                        ]
                    ]
                },
            }
        )
    return out

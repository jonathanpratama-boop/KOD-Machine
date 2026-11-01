"""CRYPTO_ACCOUNT_v1: a crypto spot paper account (research/CRYPTO_ACCOUNT_v1/protocol_v1_4.json). Paper only: no orders.

A separate adapter beside the frozen US stock account. It reuses that account's tested cash accounting
(paper_account.orders_of / account_state: cash, reservations, fills, cancels, realized P&L) by writing records
of the same shapes, and replaces everything market-specific:

  * time: 24/7 UTC timestamps; no sessions, no opens. An order lives ORDER_VALID after it is placed.
  * prices: only recorded Binance spot best bid/ask observations (CRYPTO_QUOTE records, taken from the public
    bookTicker endpoint and timestamped when observed). Nothing fills, stops or exits on a price that was not
    recorded in this ledger.
  * fees: an explicit taker fee per side (FEE); the bid/ask spread is paid by buying at the ask, selling at the bid.
  * decisions: an order needs a quote observed within QUOTE_MAX_AGE before it is placed; a missing, stale or
    failed quote is a DECLINE (NO_FRESH_QUOTE). A failed fetch is recorded (CRYPTO_QUOTE_ERROR), never replaced
    by an older quote.
  * fills: a limit buy fills at the ask of the first quote observed at or after the order was placed (never its
    decision quote) and before it expires, whose ask is at or below the limit; otherwise it expires unfilled
    (ACCT_ENTRY EXPIRED_UNFILLED, with the quotes and fetch failures of its life). Each run observes again right
    after placing orders (cycle), so an order can fill in the run that placed it.
  * exits: the stop is set at the fill, MAX_STOP below it; the HOLD deadline runs from the fill. A position exits
    at the bid of the first quote observed after the fill whose bid is at or below the stop (that bid can be
    well below the stop: quotes are sparse), or at the bid of the first quote observed at or after the deadline
    (how late is recorded). No fill or exit uses a quote observed after the run's own clock.

Version history: v1 (research/CRYPTO_ACCOUNT_v1/protocol.json, code at commit b4aec00) let an order use the
latest recorded quote of any age, as its decision price and as its fill, with a deadline counted from that old
quote. v1.1 (protocol_v1_1.json, CORRECTION_1.md) corrected fill timing.
v1.2 (protocol_v1_2.json, CORRECTION_2.md) blocks new orders after failed fetches even with a recent cache;
v1.3 (protocol_v1_3.json, CORRECTION_3.md) rejects invalid prices at both quote input boundaries;
v1.4 (protocol_v1_4.json, CORRECTION_4.md) guards state phases with CAS and uses as-of decision/mark valuation;
every new record carries rules = RULES. Historical records and protocols remain unchanged.

Decisions come from the crypto paper scan (paper/ledger.jsonl, the frozen paper policy). The account only buys a
decision the policy itself made a buy; every PASS is recorded as a decline with the policy's reason. Quantities
are fractional (exchange lot-size and minimum-notional rules are not modelled). Records live in
paper/crypto_account.jsonl (hash chain, RFC 3161 stamped); nothing is edited, a correction is a new line.
"""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote as quote_url

from . import paper
from . import paper_account as stock
from .provenance import utc_stamp

LEDGER = paper.PAPER / "crypto_account.jsonl"
REPORT = paper.PAPER / "CRYPTO_ACCOUNT.md"
ACCOUNT_ID = "CRYPTO_ACCOUNT_v1"
RULES = "CRYPTO_ACCOUNT_v1.4"
ARM = "CRYPTO_SPOT"
QUOTE, QUOTE_ERROR = "CRYPTO_QUOTE", "CRYPTO_QUOTE_ERROR"
ORDER, DECLINE, CANCEL, ENTRY, EXIT, MARK = (
    stock.ORDER,
    stock.DECLINE,
    stock.CANCEL,
    stock.ENTRY,
    stock.EXIT,
    stock.MARK,
)
START_CASH = stock.START_CASH  # 10,000 USDT
RISK_FRACTION = stock.RISK_FRACTION  # 0.5% planned loss per position
MAX_PLANNED_RISK = stock.MAX_PLANNED_RISK  # 1.5% for pending and open together
MAX_NEW_PER_DAY = 3  # new orders per UTC day
MAX_POSITION = 0.20  # of equity in one coin
FEE = 0.001  # taker fee per side (Binance spot base rate)
CHASE = 0.01  # limit = the policy's decision-time quote x (1 + CHASE)
MAX_STOP = 0.05  # stop set at the fill, 5% below it
ORDER_VALID = timedelta(hours=1)
QUOTE_MAX_AGE = timedelta(
    minutes=5
)  # the newest quote a decision may use, at the moment it is made
HOLD = timedelta(days=5)
FIRST_SIGNAL = "2026-10-30"
BOOK_TICKER = "https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol={}"


def lines() -> list[dict]:
    return paper.ledger_lines(LEDGER) if LEDGER.exists() else []


def _t(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _stamp(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def floor8(x: float) -> float:
    return math.floor(x * 1e8 + 1e-6) / 1e8


# ---------------------------------------------------------------------------------------- quotes
def validated_book(bid, ask) -> tuple[float, float]:
    """Reject nonfinite, nonpositive or crossed prices before recording a quote."""
    if isinstance(bid, bool) or isinstance(ask, bool) or bid is None or ask is None:
        raise ValueError("unusable book: Boolean or null price")
    try:
        bid, ask = float(bid), float(ask)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("unusable book: non-numeric price") from exc
    if not (math.isfinite(bid) and math.isfinite(ask) and bid > 0 and ask >= bid):
        raise ValueError(f"unusable book: bid {bid} ask {ask}")
    return bid, ask


def book_ticker(symbol: str) -> tuple[float, float, str]:
    """Best bid and ask from Binance's public spot endpoint; raises if there is no usable answer."""
    url = BOOK_TICKER.format(quote_url(symbol))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read())
    bid, ask = validated_book(body["bidPrice"], body["askPrice"])
    return bid, ask, url


def fetch_quotes(symbols: list[str], get=book_ticker) -> list[dict]:
    """One CRYPTO_QUOTE per symbol that answered and one CRYPTO_QUOTE_ERROR per symbol that did not."""
    out = []
    for sym in sorted(set(symbols)):
        try:
            bid, ask, url = get(sym)
            bid, ask = validated_book(bid, ask)
        except Exception as exc:  # noqa: BLE001 - recorded, never replaced by an older quote
            out.append(
                {
                    "type": QUOTE_ERROR,
                    "account": ACCOUNT_ID,
                    "rules": RULES,
                    "symbol": sym,
                    "attempted_at": utc_stamp(),
                    "error": f"{type(exc).__name__}: {exc}"[:200],
                }
            )
            continue
        out.append(
            {
                "type": QUOTE,
                "account": ACCOUNT_ID,
                "rules": RULES,
                "symbol": sym,
                "bid": bid,
                "ask": ask,
                "observed_at": utc_stamp(),
                "source": url,
            }
        )
    return out


def quotes_of(recs: list[dict], symbol: str) -> list[dict]:
    return sorted(
        (r for r in recs if r["type"] == QUOTE and r["symbol"] == symbol),
        key=lambda r: r["observed_at"],
    )


def errors_of(recs: list[dict], symbol: str) -> list[dict]:
    return [r for r in recs if r["type"] == QUOTE_ERROR and r["symbol"] == symbol]


def fresh_quote(recs: list[dict], symbol: str, now: datetime) -> tuple[dict | None, str]:
    """A recent quote not superseded by a failed fetch, as of `now`.

    Observation time orders events; ledger order breaks same-second ties. Future
    events cannot authorize or block a decision. Settlement remains independent:
    a fetch failure does not erase valid observations for an existing order.
    """
    seen = [q for q in quotes_of(recs, symbol) if q["observed_at"] <= _stamp(now)]
    events = [
        (r.get("observed_at") or r.get("attempted_at"), i, r)
        for i, r in enumerate(recs)
        if r["type"] in (QUOTE, QUOTE_ERROR) and r["symbol"] == symbol
        and (r.get("observed_at") or r.get("attempted_at")) <= _stamp(now)
    ]
    latest = max(events, key=lambda e: (e[0], e[1]))[2] if events else None
    errs = [latest] if latest and latest["type"] == QUOTE_ERROR else []
    why = f"the fetch failed at {errs[-1]['attempted_at']} ({errs[-1]['error']}); " if errs else ""
    if seen and now - _t(seen[-1]["observed_at"]) <= QUOTE_MAX_AGE:
        if errs:
            return None, why + "the cached quote cannot authorize a new order"
        return seen[-1], ""
    if seen:
        return (
            None,
            why
            + f"the newest recorded quote is from {seen[-1]['observed_at']}, older than {QUOTE_MAX_AGE}",
        )
    return None, why + "no quote was ever recorded for the coin"


# ------------------------------------------------------------------------------------- decisions
def candidates(ledger_recs: list[dict]) -> list[dict]:
    """The crypto paper scan's decisions from FIRST_SIGNAL on, oldest first."""
    return sorted(
        (
            r
            for r in ledger_recs
            if r.get("market") == "CRYPTO"
            and r.get("type") == "DECISION"
            and r["signal_session"] >= FIRST_SIGNAL
        ),
        key=lambda r: (r["decided_at"], r["decision_id"]),
    )


def symbol_of(decision: dict) -> str:
    return f"{decision['instrument']['ticker']}USDT"


class FutureLedgerStateError(ValueError):
    """An as-of account view cannot safely reconstruct future business events."""


def account(recs: list[dict], now: datetime | None = None) -> dict:
    """Cash, reservations and realized P&L from the stock account's tested accounting; the open positions valued
    here at the latest recorded bid, with this adapter's fee, and their risk to the stop.
    An explicit `now` excludes later quotes and rejects future business events;
    omitted `now` retains the historical whole-ledger reporting view."""
    if now is not None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("as-of valuation needs a timezone-aware clock")
        for r in recs:
            if r["type"] in (ORDER, DECLINE, CANCEL, ENTRY, EXIT, MARK):
                for field in ("made_at", "recorded_at", "filled_at", "exited_at"):
                    if r.get(field) and _t(r[field]) > now:
                        raise FutureLedgerStateError(f"{r['type']} has future {field}; refusing as-of valuation")
        # Quote facts can be ignored until observed. Business events cannot be
        # partially filtered without rebuilding accounting, so those fail closed.
        recs = [r for r in recs if r["type"] != QUOTE or _t(r["observed_at"]) <= now]
    st = stock.account_state(recs, ARM)
    value = unrealized = open_risk = 0.0
    positions = []
    for h, x in stock.orders_of(recs, ARM).items():
        en = x["entry"]
        if en is None or en["status"] != "FILLED" or x["exit"] is not None:
            continue
        qs = quotes_of(recs, x["order"]["symbol"])
        last = qs[-1] if qs else None
        bid = last["bid"] if last else en["price"]
        worth = en["shares"] * bid
        value += worth
        unrealized += worth * (1 - FEE) - stock.cost_basis(en)
        open_risk += max(worth - en["shares"] * en["stop"], 0.0) + en["shares"] * en["stop"] * FEE
        positions.append(
            {
                "order_record_hash": h,
                "symbol": x["order"]["symbol"],
                "quantity": en["shares"],
                "bid": bid,
                "valued_at": last["observed_at"] if last else None,
                "value": worth,
            }
        )
    pending_risk = sum(
        x["order"]["planned_risk_usd"]
        for x in stock.orders_of(recs, ARM).values()
        if x["entry"] is None and x["cancel"] is None
    )
    return {
        "cash": st["cash"],
        "reserved": st["reserved"],
        "free_cash": st["free_cash"],
        "open_value": value,
        "equity": st["cash"] + value,
        "realized": st["realized"],
        "unrealized": unrealized,
        "planned_risk": pending_risk + open_risk,
        "open": positions,
    }


def decide(recs: list[dict], cands: list[dict], now: datetime) -> list[dict]:
    """ORDER or DECLINE for each scan decision this account has not decided yet."""
    decided = {r["decision_id"] for r in recs if r["type"] in (ORDER, DECLINE)}
    state = account(recs, now=now)
    today = _stamp(now)[:10]
    placed_today = sum(1 for r in recs if r["type"] == ORDER and r["made_at"][:10] == today)
    out = []
    for d in cands:
        if d["decision_id"] in decided:
            continue
        sym = symbol_of(d)
        q, stale = fresh_quote(recs, sym, now)
        base = {
            "account": ACCOUNT_ID,
            "rules": RULES,
            "arm": ARM,
            "decision_id": d["decision_id"],
            "set_id": d["decision_id"],
            "ticker": d["instrument"]["ticker"],
            "symbol": sym,
            "signal_session": d["signal_session"],
            "policy_decision": d["decision"],
            "decision_record_hash": d["record_hash"],
            "made_at": _stamp(now),
        }
        if not d["decision"].upper().startswith("BUY"):
            out.append(
                {
                    "type": DECLINE,
                    **base,
                    "reason": f"POLICY_{d['decision']}: {d.get('reason', '')}",
                }
            )
            continue
        if q is None:
            out.append({"type": DECLINE, **base, "reason": f"NO_FRESH_QUOTE: {stale}"})
            continue
        price = d.get("verified_price")
        raw_ref = price.get("quote") if isinstance(price, dict) else None
        try:
            if isinstance(raw_ref, bool):
                raise ValueError("Boolean policy quote")
            ref = float(raw_ref)
            if not (math.isfinite(ref) and ref > 0):
                raise ValueError("nonpositive or nonfinite policy quote")
        except (TypeError, ValueError, OverflowError):
            out.append(
                {
                    "type": DECLINE,
                    **base,
                    "reason": "NO_DECISION_PRICE: policy quote must be a positive finite non-Boolean number",
                }
            )
            continue
        limit = ref * (1 + CHASE)
        stop_at_limit = limit * (1 - MAX_STOP)
        per_unit = (limit - stop_at_limit) + limit * 2 * FEE
        qty = floor8(
            min(RISK_FRACTION * state["equity"] / per_unit, MAX_POSITION * state["equity"] / limit)
        )
        reserve = round(qty * limit * (1 + FEE), 8)
        risk = round(qty * per_unit, 8)
        reason = (
            "NO_SIZE: no quantity fits the limits"
            if qty <= 0
            else f"LIMIT_NEW_PER_DAY: {MAX_NEW_PER_DAY} orders already placed on {today}"
            if placed_today >= MAX_NEW_PER_DAY
            else f"LIMIT_PLANNED_RISK: {state['planned_risk']:.2f} + {risk:.2f} would exceed "
            f"{MAX_PLANNED_RISK:.1%} of equity {state['equity']:.2f}"
            if state["planned_risk"] + risk > MAX_PLANNED_RISK * state["equity"] + 1e-9
            else f"INSUFFICIENT_CASH: reserving {reserve:.2f} needs more than the free cash {state['free_cash']:.2f}"
            if reserve > state["free_cash"] + 1e-9
            else None
        )
        if reason:
            out.append({"type": DECLINE, **base, "reason": reason})
            continue
        out.append(
            {
                "type": ORDER,
                **base,
                "limit": limit,
                "quantity": qty,
                "reserved_usd": reserve,
                "planned_risk_usd": risk,
                "fee_per_side": FEE,
                "decision_quote_record_hash": q["record_hash"],
                "decision_quote_at": q["observed_at"],
                "valid_until": _stamp(now + ORDER_VALID),
                "account_state": {
                    k: round(state[k], 2) for k in ("equity", "cash", "free_cash", "planned_risk")
                },
                "plan": {"shares": qty, "max_entry": limit},
                "order": f"buy {qty:g} {sym} at or below {limit:g}, valid until {_stamp(now + ORDER_VALID)}",
            }
        )
        placed_today += 1
        state["reserved"] += reserve
        state["free_cash"] -= reserve
        state["planned_risk"] += risk
    return out


def cancel(recs: list[dict], order_hash: str, reason: str, now: datetime) -> dict:
    x = stock.orders_of(recs, ARM).get(order_hash)
    if (
        x is None
        or x["entry"] is not None
        or x["cancel"] is not None
        or now >= _t(x["order"]["valid_until"])
    ):
        raise ValueError("only a pending, unexpired order can be cancelled")
    o = x["order"]
    return {
        "type": CANCEL,
        "account": ACCOUNT_ID,
        "rules": RULES,
        "arm": ARM,
        "set_id": o["set_id"],
        "ticker": o["ticker"],
        "order_record_hash": order_hash,
        "reason": reason,
        "made_at": _stamp(now),
    }


# ----------------------------------------------------------------------------------- fills, exits
def settle(recs: list[dict], now: datetime) -> list[dict]:
    """ENTRY for pending orders (fill or expiry), EXIT for open positions, from recorded quotes only."""
    out = []
    for h, x in stock.orders_of(recs, ARM).items():
        o = x["order"]
        if x["cancel"] is not None or x["exit"] is not None:
            continue
        base = {
            "account": ACCOUNT_ID,
            "rules": RULES,
            "arm": ARM,
            "set_id": o["set_id"],
            "ticker": o["ticker"],
            "order_record_hash": h,
            "recorded_at": _stamp(now),
        }
        qs = [q for q in quotes_of(recs, o["symbol"]) if q["observed_at"] <= _stamp(now)]
        en = x["entry"]
        if en is None:
            live = [
                q
                for q in qs
                if o["made_at"] <= q["observed_at"] <= o["valid_until"]
                and q["record_hash"] != o["decision_quote_record_hash"]
            ]
            fill = next((q for q in live if q["ask"] <= o["limit"]), None)
            if fill is not None:
                en = {
                    "type": ENTRY,
                    **base,
                    "status": "FILLED",
                    "price": fill["ask"],
                    "shares": o["quantity"],
                    "cost_in": FEE,
                    "stop": fill["ask"] * (1 - MAX_STOP),
                    "filled_at": fill["observed_at"],
                    "quote_record_hash": fill["record_hash"],
                    "deadline": _stamp(_t(fill["observed_at"]) + HOLD),
                }
                out.append(en)
            elif now > _t(o["valid_until"]):
                failed = [
                    e
                    for e in errors_of(recs, o["symbol"])
                    if o["made_at"] <= e["attempted_at"] <= o["valid_until"]
                ]
                out.append(
                    {
                        "type": ENTRY,
                        **base,
                        "status": "EXPIRED_UNFILLED",
                        "reason": f"no ask at or below {o['limit']:g} observed between {o['made_at']} and "
                        f"{o['valid_until']} ({len(live)} quote(s) observed, {len(failed)} fetch failure(s))",
                    }
                )
                continue
            else:
                continue
        if en["status"] != "FILLED":
            continue
        for q in qs:
            if q["observed_at"] <= en["filled_at"]:
                continue
            why = (
                "STOP"
                if q["bid"] <= en["stop"]
                else "TIME_EXIT"
                if q["observed_at"] >= en["deadline"]
                else None
            )
            if why:
                proceeds = en["shares"] * q["bid"] * (1 - FEE)
                late = (_t(q["observed_at"]) - _t(en["deadline"])).total_seconds() / 3600
                out.append(
                    {
                        "type": EXIT,
                        **base,
                        "exit_reason": why,
                        "hours_after_deadline": round(late, 2) if why == "TIME_EXIT" else None,
                        "price": q["bid"],
                        "cost_out": FEE,
                        "exited_at": q["observed_at"],
                        "exit_session": q["observed_at"],
                        "quote_record_hash": q["record_hash"],
                        "net_pnl_usd": round(proceeds - stock.cost_basis(en), 8),
                        "net_return": proceeds / stock.cost_basis(en) - 1,
                    }
                )
                break
    return out


def mark(recs: list[dict], now: datetime) -> dict:
    st = account(recs, now=now)
    return {
        "type": MARK,
        "account": ACCOUNT_ID,
        "rules": RULES,
        "arm": ARM,
        "session": _stamp(now),
        **{
            k: round(st[k], 2)
            for k in ("cash", "reserved", "open_value", "equity", "realized", "unrealized")
        },
        "open_positions": [{**p, "value": round(p["value"], 2)} for p in st["open"]],
        "made_at": _stamp(now),
    }


def symbols_needed(recs: list[dict], cands: list[dict]) -> list[str]:
    """Coins with a pending order, an open position, or an undecided buy decision."""
    out = {
        symbol_of(d)
        for d in cands
        if d["decision"].upper().startswith("BUY")
        and d["decision_id"]
        not in {r["decision_id"] for r in recs if r["type"] in (ORDER, DECLINE)}
    }
    for x in stock.orders_of(recs, ARM).values():
        if (
            x["cancel"] is None
            and x["exit"] is None
            and (x["entry"] is None or x["entry"]["status"] == "FILLED")
        ):
            out.add(x["order"]["symbol"])
    return sorted(out)


class StaleHeadConflict(RuntimeError):
    """The phase's ledger prefix changed; the proposal was not committed."""


MAX_PHASE_ATTEMPTS = 3
_UNGUARDED = object()
_STALE_HEAD_MESSAGE = "ledger head changed; recompute the proposal against the current prefix"


def _append_at_head(append, recs, expected_head):
    """Local translation of the frozen paper writer's exact CAS failure only."""
    try:
        return append(recs, expected_head=expected_head)
    except RuntimeError as exc:
        if type(exc) is RuntimeError and str(exc) == _STALE_HEAD_MESSAGE:
            raise StaleHeadConflict(str(exc)) from exc
        raise


def cycle(cands: list[dict], fetch, clock, append, watch_extra=()) -> dict:
    """One run, each phase written before the next reads the ledger: observe; record fills, expiries and exits;
    decide; observe again the coins of orders just placed and record their fills; mark.
    State-derived phases commit against the exact snapshot head and recompute at
    most MAX_PHASE_ATTEMPTS times. The append callback must forward expected_head."""

    events: list[dict] = []
    receipt_warnings: list[str] = []

    def put(recs, track=True, expected_head=_UNGUARDED):
        if recs:
            try:
                if expected_head is _UNGUARDED:
                    append(recs)
                else:
                    _append_at_head(append, recs, expected_head)
            except paper.ReceiptPendingError as exc:
                # The writer already committed and released its lock. Never
                # replay the business phase merely to retry external receipts.
                recs = exc.records
                receipt_warnings.append(str(exc))
            if track:
                events.extend(recs)
        return recs

    def phase(compute, track=True):
        for attempt in range(MAX_PHASE_ATTEMPTS):
            snapshot = lines()
            head = snapshot[-1]["record_hash"] if snapshot else None
            proposal = compute(snapshot, clock())
            if not proposal:
                return []
            try:
                return put(proposal, track=track, expected_head=head)
            except StaleHeadConflict:
                if attempt + 1 == MAX_PHASE_ATTEMPTS:
                    raise StaleHeadConflict("crypto account phase contention: retry budget exhausted")
        raise AssertionError("unreachable")

    observed = put(
        fetch(sorted(set(symbols_needed(lines(), cands)) | set(watch_extra))), track=False
    )
    phase(settle)
    decided = phase(lambda snapshot, now: decide(snapshot, cands, now))
    placed = sorted({r["symbol"] for r in decided if r["type"] == ORDER})
    after = put(fetch(placed), track=False) if placed else []
    if placed:
        phase(settle)
    marked = phase(lambda snapshot, now: [mark(snapshot, now)], track=False)
    return {"observed": observed + after, "events": events, "mark": marked[0],
            "receipt_warnings": receipt_warnings}


# ---------------------------------------------------------------------------------------- report
def render(recs: list[dict]) -> str:
    st = account(recs)
    book = stock.orders_of(recs, ARM)
    as_of = max(
        (r.get("made_at") or r.get("recorded_at") or r.get("observed_at") or "" for r in recs),
        default="no records yet",
    )
    out = [
        "# KOD crypto spot paper account (CRYPTO_ACCOUNT_v1, rules v1.4)",
        "",
        (
            f"As of the latest record ({as_of}). Paper only: no orders, no money. "
            "Protocol: `research/CRYPTO_ACCOUNT_v1/protocol_v1_4.json` (supersedes v1.3; see CORRECTION_4.md)."
        ),
        "",
        (
            f"- **Rules:** {START_CASH:,.0f} USDT; {RISK_FRACTION:.1%} planned loss per position, "
            f"{MAX_PLANNED_RISK:.1%} in total, {MAX_NEW_PER_DAY} new orders per UTC day, no leverage; buys only what "
            f"the frozen crypto policy decides to buy; limit {CHASE:.0%} above the policy's quote, valid "
            f"{ORDER_VALID}; fills at a recorded ask, exits at a recorded bid; stop {MAX_STOP:.0%} below the fill; "
            f"time exit after {HOLD.days} days; fee {FEE:.2%} per side."
        ),
        "",
        "| Cash | Reserved | Available | Open value | Equity | Realized | Unrealized |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        "| "
        + " | ".join(
            f"{st[k]:,.2f}"
            for k in (
                "cash",
                "reserved",
                "free_cash",
                "open_value",
                "equity",
                "realized",
                "unrealized",
            )
        )
        + " |",
        "",
        "## Open positions",
        "",
    ]
    entries = {
        x["order"]["symbol"]: x["entry"] for x in book.values() if x["entry"] and not x["exit"]
    }
    out += [
        f"- {p['symbol']}: {p['quantity']:g} valued {p['value']:,.2f} USDT at the bid recorded "
        f"{p['valued_at'] or '(none: carried at entry price)'}"
        + (
            f"; time exit due since {entries[p['symbol']]['deadline']}, waiting for a fresh quote"
            if entries.get(p["symbol"]) and as_of >= entries[p["symbol"]]["deadline"]
            else ""
        )
        for p in st["open"]
    ] or ["- None."]
    errors = [r for r in recs if r["type"] == QUOTE_ERROR]
    out += ["", "## Quote fetch failures", ""] + (
        [f"- {e['attempted_at']} {e['symbol']}: {e['error']}" for e in errors[-10:]] or ["- None."]
    )
    out += [
        "",
        "## Every decision",
        "",
        "| Decided | Coin | Policy | Account | Fill | Exit | Net P&L |",
        "|---|---|---|---|---|---|---:|",
    ]
    for r in recs:
        if r["type"] == DECLINE:
            out.append(
                f"| {r['made_at']} | {r['symbol']} | {r['policy_decision']} | declined: "
                f"{r['reason'][:140]} | - | - | - |"
            )
        elif r["type"] == ORDER:
            x = book[r["record_hash"]]
            en, ex = x["entry"], x["exit"]
            fill = (
                "cancelled"
                if x["cancel"]
                else "pending"
                if en is None
                else f"{en['status']} @ {en['price']:g}"
                if en["status"] == "FILLED"
                else en["status"]
            )
            out.append(
                f"| {r['made_at']} | {r['symbol']} | {r['policy_decision']} | {r['order']} | {fill} | "
                + (
                    f"{ex['exit_reason']} @ {ex['price']:g} | {ex['net_pnl_usd']:+,.2f} |"
                    if ex
                    else "- | - |"
                )
            )
    return "\n".join(out) + "\n"


def write_report():
    REPORT.write_text(render(lines()), encoding="utf-8")
    return REPORT


def verify() -> list[str]:
    if not LEDGER.exists():
        return []
    problems = [f"crypto_account.jsonl: {p}" for p in paper.verify_chain(LEDGER)]
    recs = lines()
    by_hash = {r["record_hash"]: r for r in recs}
    decided, followed, fills = set(), set(), {}
    for i, r in enumerate(recs):
        if r["type"] in (ORDER, DECLINE):
            if r["decision_id"] in decided:
                problems.append(f"{r['decision_id']}: decided twice")
            decided.add(r["decision_id"])
        if r["type"] == ORDER:
            if r.get("rules") in ("CRYPTO_ACCOUNT_v1.2", "CRYPTO_ACCOUNT_v1.3", "CRYPTO_ACCOUNT_v1.4"):
                eligible, why = fresh_quote(recs[:i], r["symbol"], _t(r["made_at"]))
                if eligible is None:
                    problems.append(f"{r['decision_id']}: order has no eligible decision quote: {why}")
            q = by_hash.get(r["decision_quote_record_hash"])
            if q is None or q["type"] != QUOTE or q["symbol"] != r["symbol"]:
                problems.append(f"{r['decision_id']}: order does not point at its quote")
            elif not (
                q["observed_at"] <= r["made_at"]
                and _t(r["made_at"]) - _t(q["observed_at"]) <= QUOTE_MAX_AGE
            ):
                problems.append(f"{r['decision_id']}: order placed on a quote that was not fresh")
        if r["type"] not in (ENTRY, EXIT, CANCEL):
            continue
        o = by_hash.get(r["order_record_hash"])
        if o is None or o["type"] != ORDER:
            problems.append(f"{r['set_id']}: {r['type']} does not point at its order")
            continue
        if (r["order_record_hash"], r["type"]) in followed:
            problems.append(f"{r['set_id']}: {r['type']} recorded twice")
        followed.add((r["order_record_hash"], r["type"]))
        if r["type"] == CANCEL and r["made_at"] >= o["valid_until"]:
            problems.append(f"{r['set_id']}: cancelled after the order expired")
        if r.get("status") != "FILLED" and r["type"] != EXIT:
            continue
        q = by_hash.get(r["quote_record_hash"])
        if q is None or q["type"] != QUOTE or q["symbol"] != o["symbol"]:
            problems.append(f"{r['set_id']}: {r['type']} does not point at a recorded quote")
            continue
        if q["observed_at"] > r["recorded_at"]:
            problems.append(
                f"{r['set_id']}: {r['type']} uses a quote observed after it was recorded"
            )
        if r["type"] == ENTRY:
            fills[r["order_record_hash"]] = r
            if not (
                o["made_at"] <= q["observed_at"] <= o["valid_until"]
                and q["record_hash"] != o["decision_quote_record_hash"]
            ):
                problems.append(f"{r['set_id']}: fill not observed while the order was live")
            if not (q["ask"] == r["price"] and q["ask"] <= o["limit"]):
                problems.append(f"{r['set_id']}: fill not at a qualifying recorded ask")
            if r["filled_at"] != q["observed_at"] or r["deadline"] != _stamp(
                _t(q["observed_at"]) + HOLD
            ):
                problems.append(
                    f"{r['set_id']}: fill time or holding deadline not from the fill quote"
                )
            continue
        en = fills.get(r["order_record_hash"])
        if en is None:
            problems.append(f"{r['set_id']}: exit without a filled entry")
            continue
        if q["bid"] != r["price"]:
            problems.append(f"{r['set_id']}: exit not at the recorded bid")
        if q["observed_at"] <= en["filled_at"]:
            problems.append(f"{r['set_id']}: exit quote not after the fill")
        if r["exit_reason"] == "STOP" and q["bid"] > en["stop"]:
            problems.append(f"{r['set_id']}: stop exit above the stop")
        if r["exit_reason"] == "TIME_EXIT" and q["observed_at"] < en["deadline"]:
            problems.append(f"{r['set_id']}: time exit before the deadline")
    return problems

"""Versioned Coinbase USD reference profile of reviewed v2 account; no order API.

A small event adapter around the existing paper_cash_v1 Decimal fill and ledger
primitives. Not a historical bar backtester. Read ADAPTER_SPEC.md.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor/paper_cash_accounting.py"
VENDOR_HASH = "29688797f6738e4aa02ca87403a5a90d60dec0bca54cffab36a4a4a7e266f8a6"
if hashlib.sha256(VENDOR.read_bytes()).hexdigest() != VENDOR_HASH:
    raise ValueError("reviewed accounting source hash mismatch")
_spec = importlib.util.spec_from_file_location("reviewed_paper_cash", VENDOR)
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)
D = Decimal
SYMBOLS = ("BTC-USD", "ETH-USD")
VERSION = "COINBASE_EXCHANGE_USD_REFERENCE_v1"


def wire(x):
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, dict):
        return {k: wire(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [wire(v) for v in x]
    return x


def canonical(x):
    return json.dumps(wire(x), sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


def number(x, *, minimum=D(0), positive=False):
    if isinstance(x, bool) or not isinstance(x, (str, int, float, Decimal)):
        raise ValueError("finite numeric input required")
    n = D(str(x))
    if not n.is_finite() or n < minimum or (positive and n <= 0):
        raise ValueError("invalid numeric input")
    return n


def utc(s):
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return t.astimezone(timezone.utc)


def stamp(t):
    return t.isoformat().replace("+00:00", "Z")


def bundle_pins():
    paths = ["paper_reference_core.py", "ADAPTER_SPEC.md", "ADAPTER_ADDENDUM_1.md", "ADAPTER_ADDENDUM_2.md", "adapter.py", "run_once.py",
             "vendor/paper_cash_accounting.py"]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def scenario_record(s):
    required = {"id", "fee", "slippage", "precision", "quote_max_age_seconds",
                "intent_life_seconds", "daily_grace_seconds"}
    if set(s) != required or not isinstance(s["id"], str) or not s["id"]:
        raise ValueError("explicit versioned scenario fields required")
    for k in ("fee", "slippage"):
        if number(s[k]) >= 1:
            raise ValueError("scenario cost must be below one")
    for k in ("precision", "quote_max_age_seconds", "intent_life_seconds", "daily_grace_seconds"):
        if isinstance(s[k], bool) or not isinstance(s[k], int) or s[k] < 0:
            raise ValueError("nonnegative integer scenario field required")
    if s["precision"] > 12 or not 0 < s["quote_max_age_seconds"] <= 120 or not 0 < s["intent_life_seconds"] <= 3600 or s["daily_grace_seconds"] > 300:
        raise ValueError("unsupported candidate timing/precision")
    return wire(s)


def evidence(payload, received_at):
    """Fixture helper; this creates a local hash, NOT an external time receipt."""
    return {"kind": "synthetic", "payload": wire(payload), "received_at": received_at,
            "payload_sha256": sha(payload)}


def unpack(e, at):
    from adapter import validate_evidence
    return copy.deepcopy(validate_evidence(e, at))


def fresh_quote(st, symbol, at):
    e = st["quotes"].get(symbol)
    if not e:
        return None
    q = e["payload"]
    age = (utc(at) - utc(q["observed_at"])).total_seconds()
    if not 0 <= age <= st["scenario"]["quote_max_age_seconds"] or utc(e["received_at"]) > utc(at):
        return None
    return q


def account_view(st, at):
    cash = st["cash_total"]
    reserved = sum((o.get("reserved", D(0)) for o in st["intents"] if o["status"] == "PENDING"), D(0))
    if cash < 0 or reserved < 0 or reserved > cash:
        raise ValueError("cash reservation invariant broken")
    missing, values = [], {}
    for symbol, qty in st["holdings"].items():
        if qty < 0:
            raise ValueError("short position forbidden")
        if not qty:
            values[symbol] = D(0)
            continue
        q = fresh_quote(st, symbol, at)
        if q is None:
            missing.append(symbol)
        else:
            values[symbol] = qty * number(q["bid"], positive=True)
    gross = None if missing else sum(values.values(), D(0))
    nav = None if gross is None else cash + gross
    exposure = None if nav is None or nav <= 0 else gross / nav
    if exposure is not None and exposure > 1:
        raise ValueError("gross exposure exceeds equity")
    return {"cash_total": cash, "cash_reserved": reserved, "cash_available": cash - reserved,
            "holdings": copy.deepcopy(st["holdings"]), "nav": nav, "gross_value": gross,
            "gross_fraction": exposure, "missing_marks": missing, "nav_basis": "fresh_bid_indicative"}


def cancel_pending(st, reason):
    for o in st["intents"]:
        if o["status"] == "PENDING":
            o.update(status="CANCELLED", reserved=D(0), cancellation_reason=reason)


def reserve(st):
    pending = [o for o in st["intents"] if o["status"] == "PENDING" and o["side"] == "BUY"]
    total = sum((o["budget"] for o in pending), D(0))
    alloc = min(st["cash_total"], total)
    left = alloc
    for i, o in enumerate(pending):
        amount = left if i == len(pending) - 1 else (alloc * o["budget"] / total if total else D(0))
        o["reserved"] = amount
        left -= amount


def liquidations(st, at, trigger):
    for symbol, qty in st["holdings"].items():
        exists = any(o["symbol"] == symbol and o["status"] == "PENDING" for o in st["intents"])
        if qty and not exists:
            st["intents"].append({"id": f"liquidate:{trigger}:{symbol}", "symbol": symbol,
                "side": "SELL", "quantity": qty, "reserved": D(0), "status": "PENDING",
                "made_at": at, "expires_at": stamp(utc(at) + timedelta(seconds=st["scenario"]["intent_life_seconds"])),
                "reason": "PERSISTENT_KILL"})


def kill(st, at, reason, trigger):
    if st["kill"] is None:
        st["kill"] = {"at": at, "reason": reason, "trigger": trigger}
        cancel_pending(st, "KILLED")
        liquidations(st, at, trigger)


def risk(st, at, trigger):
    v = account_view(st, at)
    if v["nav"] is not None:
        st["peak"] = max(st["peak"], v["nav"])
        dd = (st["peak"] - v["nav"]) / st["peak"]
        st["maximum_observed_drawdown"] = max(st["maximum_observed_drawdown"], dd)
        if dd >= D(".25"):
            kill(st, at, "DRAWDOWN_AT_LEAST_25_PERCENT", trigger)
    return v


def expire(st, at):
    for o in st["intents"]:
        if o["status"] == "PENDING" and utc(at) >= utc(o["expires_at"]):
            o.update(status="EXPIRED", reserved=D(0))
    reserve(st)


def signals(e, signal_date, at):
    p = unpack(e, at)
    if set(p) != set(SYMBOLS):
        raise ValueError("both specified spot instruments required")
    end = date.fromisoformat(signal_date)
    if utc(at) < datetime.combine(end + timedelta(days=1), datetime.min.time(), timezone.utc):
        raise ValueError("signal day not complete")
    raw, metrics = {}, {}
    for symbol in SYMBOLS:
        bars = p[symbol]
        if len(bars) != 40:
            raise ValueError("exactly 40 clean consecutive closes required")
        closes = []
        for i, bar in enumerate(bars):
            expected = end - timedelta(days=39-i)
            if bar["day"] != expected.isoformat():
                raise ValueError("missing/duplicate/nonconsecutive day")
            close_at = datetime.combine(expected + timedelta(days=1), datetime.min.time(), timezone.utc)
            if bar["first_public_at"] is not None or not close_at <= utc(bar["available_at"]) == utc(bar["received_at"]) <= utc(e["received_at"]) <= utc(at):
                raise ValueError("noncausal bar availability")
            if bar["source_sha256"] != sha({"day": bar["day"], "close": bar["close"]}):
                raise ValueError("bar content hash mismatch")
            closes.append(float(number(bar["close"], positive=True)))
        sma10, sma40 = statistics.mean(closes[-10:]), statistics.mean(closes)
        logs = [math.log(closes[i]/closes[i-1]) for i in range(20,40)]
        sigma = statistics.stdev(logs)
        is_long = sma10 > sma40
        if is_long and (not math.isfinite(sigma) or sigma <= 0):
            raise ValueError("nonpositive volatility for long signal")
        raw[symbol] = D(str(min(1.0, .015/sigma))) if is_long else D(0)
        metrics[symbol] = {"sma10": sma10, "sma40": sma40, "sigma20": sigma, "long": is_long}
    total = sum(raw.values(), D(0))
    targets = {s: v / total if total > 1 else v for s, v in raw.items()}
    return raw, targets, metrics


def sharpe_status(samples):
    if len(samples) < 91:
        return {"status": "INSUFFICIENT_90_RETURNS", "value": None, "negative": False}
    window = samples[-91:]
    if any(x["nav"] is None for x in window) or any(date.fromisoformat(b["date"]) - date.fromisoformat(a["date"]) != timedelta(days=1) for a,b in zip(window,window[1:])):
        return {"status": "MISSING_DAILY_MARK", "value": None, "negative": False}
    if any(x["nav"] <= 0 for x in window):
        return {"status": "NONPOSITIVE_NAV", "value": None, "negative": False}
    returns = [float(b["nav"]/a["nav"]-1) for a,b in zip(window,window[1:])]
    mean, sd = statistics.mean(returns), statistics.stdev(returns)
    if sd == 0:
        label = "ZERO_MEAN_ZERO_VARIANCE" if mean == 0 else "NEGATIVE_INFINITY" if mean < 0 else "POSITIVE_INFINITY"
        return {"status": label, "value": None, "negative": mean < 0}
    value = mean/sd*math.sqrt(365)
    return {"status": "FINITE", "value": value, "negative": value < 0, "returns": 90}


def operation_id(c):
    op = c["op"]
    if op == "init": return "init:" + c["account_id"]
    if op == "observe": return "observe:" + sha(c["evidence"])
    if op == "decision": return "decision:" + c["signal_date"]
    if op in ("daily", "missed"): return op + ":" + c["date"]
    if op == "audit": return "audit:" + c["reference_sha256"]
    if op == "advance": return "advance:" + c["at"]
    raise ValueError("unsupported operation / no live adapter")


def initial(c):
    if c.get("mode") != "coinbase_exchange_usd_reference_simulation":
        raise ValueError("explicit USD reference simulation mode required")
    from adapter import SCENARIO
    if c["scenario"] != SCENARIO: raise ValueError("profile scenario mismatch")
    s = scenario_record(c["scenario"])
    cash = number(c["initial_cash"], positive=True)
    utc(c["at"])
    st = {"version": VERSION, "account_id": c["account_id"], "scenario": s,
          "scenario_sha256": sha(s), "pins": bundle_pins(), "cash_total": cash,
          "quote_currency": "USD", "source_profile": VERSION,
          "holdings": dict.fromkeys(SYMBOLS, D(0)), "quotes": {}, "intents": [],
          "peak": cash, "maximum_observed_drawdown": D(0), "kill": None,
          "daily": [], "clock": c["at"], "realized_fees": D(0), "fills": []}
    return st


def apply(st, c):
    op, at, oid = c["op"], c["at"], operation_id(c)
    if op == "init":
        if st is not None: raise ValueError("account already initialized")
        st = initial(c)
        return st, {"status": "INITIALIZED", "account": account_view(st, at)}
    if st is None: raise ValueError("init required")
    if utc(at) < utc(st["clock"]): raise ValueError("operation clock cannot move backwards")
    st = copy.deepcopy(st)
    st["clock"] = at
    expire(st, at)
    if st["kill"]: liquidations(st, at, oid)
    result = {}
    if op == "observe":
        e = c["evidence"]
        q = unpack(e, at)
        if q.get("venue") != "COINBASE_EXCHANGE_REFERENCE" or q.get("product") != "spot" or q.get("symbol") not in SYMBOLS:
            raise ValueError("unsupported venue / product / symbol")
        if not utc(q["observed_at"]) <= utc(e["received_at"]) <= utc(at):
            raise ValueError("quote received before observation or in future")
        bid, ask = number(q["bid"], positive=True), number(q["ask"], positive=True)
        if ask < bid: raise ValueError("crossed quote")
        for k in ("bid_qty", "ask_qty"):
            if q.get(k) is not None: number(q[k])
        previous = st["quotes"].get(q["symbol"])
        if previous and utc(q["observed_at"]) < utc(previous["payload"]["observed_at"]):
            raise ValueError("out-of-order quote")
        if previous and (q["source_sequence"] < previous["payload"]["source_sequence"] or utc(q["source_observed_at"]) < utc(previous["payload"]["source_observed_at"])):
            raise ValueError("regressing source book sequence/time")
        st["quotes"][q["symbol"]] = copy.deepcopy(e)
        # Observe risk BEFORE filling pending buys; kill never fills at triggering quote.
        risk(st, at, oid)
        result["fills"] = []
        result["blocked"] = []
        for o in sorted(st["intents"], key=lambda x: x["side"] == "BUY"):
            if o["status"] != "PENDING" or o["symbol"] != q["symbol"]:
                continue
            if not utc(o["made_at"]) < utc(q["observed_at"]) <= utc(e["received_at"]) <= utc(at) < utc(o["expires_at"]) or fresh_quote(st, q["symbol"], at) is None:
                result["blocked"].append({"intent": o["id"], "reason": "INELIGIBLE_TIME"})
                continue
            if not utc(q["request_started_at"]) > utc(o["made_at"]) or not utc(q["source_observed_at"]) > utc(o["made_at"]):
                result["blocked"].append({"intent": o["id"], "reason": "REFERENCE_OBSERVATION_NOT_POST_INTENT"})
                continue
            size = q.get("ask_qty" if o["side"] == "BUY" else "bid_qty")
            if size is None:
                result["blocked"].append({"intent": o["id"], "reason": "UNKNOWN_LIQUIDITY"})
                continue
            limit = number(size)
            precision = st["scenario"]["precision"]
            step = D(1).scaleb(-precision)
            fee, slip = st["scenario"]["fee"], st["scenario"]["slippage"]
            if o["side"] == "BUY":
                if st["kill"]: raise ValueError("buy pending after kill")
                if any(x["status"] == "PENDING" and x["side"] == "SELL" for x in st["intents"]):
                    result["blocked"].append({"intent": o["id"], "reason": "WAITING_FOR_SELLS"})
                    continue
                if account_view(st, at)["nav"] is None:
                    result["blocked"].append({"intent": o["id"], "reason": "UNKNOWN_AGGREGATE_NAV_AT_FILL"})
                    continue
                reserve(st)
                if o["reserved"] == 0:
                    result["blocked"].append({"intent": o["id"], "reason": "WAITING_FOR_ACTUAL_CASH"})
                    continue
                sized = _core.buy_size(o["reserved"], number(q["modeled_ask"]), fee, "0", precision)
                qty = min(sized["units"], limit).quantize(step, rounding=ROUND_FLOOR)
                px = number(q["modeled_ask"])
                if qty * px < number(q["rules"]["min_market_funds"]):
                    o.update(status="IOC_REJECTED_MIN_NOTIONAL", reserved=D(0))
                    result["blocked"].append({"intent": o["id"], "reason": "MIN_MARKET_FUNDS"})
                    reserve(st)
                    continue
                cost = _core.cash_round(qty*px*number(fee))
                debit = qty*px+cost
                st["cash_total"] -= debit
                st["holdings"][q["symbol"]] += qty
                cash_change = -debit
            else:
                qty = min(o["quantity"], st["holdings"][q["symbol"]], limit).quantize(step, rounding=ROUND_FLOOR)
                px = number(q["modeled_bid"])
                if qty * px < number(q["rules"]["min_market_funds"]):
                    o.update(status="IOC_REJECTED_MIN_NOTIONAL", reserved=D(0))
                    result["blocked"].append({"intent": o["id"], "reason": "MIN_MARKET_FUNDS"})
                    continue
                liquid = _core.liquidation([qty], px, fee, "0")
                cost = liquid["commission"]
                cash_change = liquid["net"]
                st["cash_total"] += cash_change
                st["holdings"][q["symbol"]] -= qty
            o.update(status="IOC_COMPLETE", reserved=D(0), filled_quantity=qty,
                     fill_observation=oid, remainder_cancelled=True)
            if qty:
                fill = {"id": "fill:"+o["id"], "intent_id": o["id"], "side": o["side"],
                    "symbol": q["symbol"], "quantity": qty, "price": px, "fee": cost,
                    "cash_change": cash_change, "observation_id": oid,
                    "observed_at": q["observed_at"], "received_at": e["received_at"],
                    "fill_recorded_at": at, "available_quantity": limit,
                    "evidence": "public_reference_top_book_10pct_cap_not_actual_execution",
                    "source_profile": VERSION, "quote_currency": "USD",
                    "scenario_sha256": st["scenario_sha256"]}
                st["fills"].append(fill)
                result["fills"].append(fill)
                st["realized_fees"] += cost
            reserve(st)
            risk(st, at, oid)
        # Residual kill holdings receive a new intent, not an invented fill.
        if st["kill"]: liquidations(st, at, oid+":residual")
        result["status"] = "OBSERVED"
    elif op == "decision":
        if st["kill"]:
            result["status"] = "BLOCKED_PERSISTENT_KILL"
        else:
            raw, targets, metrics = signals(c["evidence"], c["signal_date"], at)
            quotes = {s: fresh_quote(st, s, at) for s in SYMBOLS}
            view = risk(st, at, oid)
            if st["kill"]:
                result["status"] = "BLOCKED_PERSISTENT_KILL"
            elif view["nav"] is None or any(q is None for q in quotes.values()):
                result["status"] = "DECLINED_UNKNOWN_NAV_OR_QUOTE"
            else:
                cancel_pending(st, "SUPERSEDED_DECISION")
                for symbol in SYMBOLS:
                    current = st["holdings"][symbol] * number(quotes[symbol]["bid"], positive=True)
                    desired = targets[symbol] * view["nav"]
                    delta = desired - current
                    if delta == 0: continue
                    o = {"id": oid+":"+symbol, "symbol": symbol,
                         "side": "BUY" if delta > 0 else "SELL", "reserved": D(0),
                         "made_at": at, "expires_at": stamp(utc(at)+timedelta(seconds=st["scenario"]["intent_life_seconds"])),
                         "status": "PENDING", "decision_quote_sha256": st["quotes"][symbol]["payload_sha256"]}
                    if delta > 0: o["budget"] = delta
                    else: o["quantity"] = min(st["holdings"][symbol], -delta/number(quotes[symbol]["bid"], positive=True))
                    st["intents"].append(o)
                reserve(st)
                result.update(status="DECIDED", raw_targets=raw, normalized_targets=targets, signal_metrics=metrics)
    elif op == "daily":
        day = date.fromisoformat(c["date"])
        boundary = datetime.combine(day, datetime.min.time(), timezone.utc)
        lateness = (utc(at)-boundary).total_seconds()
        if lateness < 0: raise ValueError("future daily boundary")
        if st["daily"] and day <= date.fromisoformat(st["daily"][-1]["date"]):
            raise ValueError("daily marks must advance")
        v = risk(st, at, oid)
        nav = v["nav"] if lateness <= st["scenario"]["daily_grace_seconds"] else None
        sample = {"date": c["date"], "at": at, "nav": nav,
                  "status": "COMPLETE" if nav is not None else "MISSED_CUTOFF" if lateness > st["scenario"]["daily_grace_seconds"] else "UNKNOWN_MARKS",
                  "daily_return": None}
        if st["daily"] and nav is not None:
            prev = st["daily"][-1]
            if prev["nav"] is not None and prev["nav"] > 0 and day-date.fromisoformat(prev["date"]) == timedelta(days=1):
                sample["daily_return"] = nav/prev["nav"]-1
        st["daily"].append(sample)
        sh = sharpe_status(st["daily"])
        if sh["negative"]: kill(st, at, "NEGATIVE_TRAILING_90_DAY_SHARPE", oid)
        result.update(status=sample["status"], sample=sample, trailing_sharpe=sh)
    elif op == "missed":
        if date.fromisoformat(c["date"]) > utc(at).date(): raise ValueError("future missed cycle")
        result.update(status="MISSED_CYCLE", cycle_date=c["date"], reason=c["reason"], logged_at=at)
    elif op == "audit":
        if len(c["reference_sha256"]) != 64: raise ValueError("audit reference hash required")
        result.update(status="AUDIT_ONLY_NO_BALANCE_EFFECT", reference_sha256=c["reference_sha256"], details=c["details"])
    elif op == "advance":
        result["status"] = "ADVANCED_NO_SYNTHETIC_FILL"
    else:
        raise ValueError("unsupported operation")
    result.update(account=account_view(st, at), kill=st["kill"], peak=st["peak"],
                  maximum_observed_drawdown=st["maximum_observed_drawdown"])
    return st, result


class Ledger:
    """Single local journal. flock serializes whole replay/validate/append transaction.

    On partial writes, fail closed rather than truncate or invent successful events.
    The lock is advisory: every writer must use this API; external deployment unsupported.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _sync_directory(self):
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _sync_existing(self):
        # A previous complete append may have failed its durability barrier.
        # An idempotent retry must establish that barrier, not merely find bytes.
        with open(self.path, "rb") as f:
            os.fsync(f.fileno())
        self._sync_directory()

    def _read(self):
        raw = self.path.read_bytes() if self.path.exists() else b""
        if raw and not raw.endswith(b"\n"): raise ValueError("torn journal tail; manual preservation/recovery required")
        rows = [json.loads(line) for line in raw.splitlines()]
        _core.verify_chain(rows)
        st = None
        for row in rows:
            if row["provenance"] != bundle_pins(): raise ValueError("source/code/protocol pin mismatch")
            if row["input_sha256"] != sha(row["command"]): raise ValueError("input hash mismatch")
            if row["id"] != operation_id(row["command"]): raise ValueError("semantic operation id mismatch")
            st, result = apply(st, row["command"])
            if wire(result) != row["result"] or sha(st) != row["state_sha256"]:
                raise ValueError("deterministic replay mismatch")
        return rows, st

    def transact(self, command):
        command = json.loads(canonical(command))
        oid = operation_id(command)
        with open(str(self.path)+".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows, st = self._read()
            for row in rows:
                if row["id"] == oid:
                    if row["command"] != command: raise ValueError("same economic operation id with conflicting payload")
                    self._sync_existing()
                    return copy.deepcopy(row["result"])
            st, result = apply(st, command)
            record = _core.append_event(rows, {"id": oid, "type": "PAPER_OPERATION",
                "command": command, "input_sha256": sha(command), "provenance": bundle_pins(),
                "result": wire(result), "state_sha256": sha(st)})
            with open(self.path, "ab", buffering=0) as f:
                raw = (canonical(record)+"\n").encode()
                view = memoryview(raw)
                while view:
                    written = f.write(view)
                    if not written: raise OSError("journal append incomplete")
                    view = view[written:]
                os.fsync(f.fileno())
            self._sync_directory()
            return wire(result)

    def state(self):
        with open(str(self.path)+".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            return self._read()[1]

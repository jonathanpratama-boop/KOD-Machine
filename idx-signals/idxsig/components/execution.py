"""Recorded, simulation-only order lifecycle with deterministic recovery.

This opt-in executor owns a distinct directory and profile. It never connects to
a venue or mutates the incumbent trend account. Fill prices and evidence IDs are
caller-retained references, not independently verified exchange executions.
"""

from __future__ import annotations

import copy
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..runtime.data import parse_time, utc_text
from ..runtime.storage import atomic_json, canonical, digest, immutable_json, locked, read_json

VERSION = "KOD_SIMULATION_EXECUTOR_V1"
ACTIVE = {"PENDING", "PARTIAL", "UNKNOWN"}
TERMINAL = {"FILLED", "CANCELLED", "EXPIRED", "REJECTED"}


def _number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("finite decimal required")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("finite decimal required") from exc
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        raise ValueError("nonnegative finite decimal required")
    return result


def _text(value):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError("nonempty bounded identifier required")
    if any(ord(char) < 32 for char in value):
        raise ValueError("control character in identifier")
    return value


def _wire(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _wire(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_wire(item) for item in value]
    return value


def _profile(profile):
    required = {
        "schema_version",
        "simulation_only",
        "evidence_type",
        "id",
        "initial_cash",
        "fee_rate",
        "quote_currency",
        "symbols",
    }
    if not isinstance(profile, dict) or not required <= profile.keys():
        raise ValueError("complete executor profile required")
    if profile.keys() - required - {"initial_holdings"}:
        raise ValueError("unknown executor profile fields")
    if profile["schema_version"] != VERSION or profile["simulation_only"] is not True:
        raise ValueError("versioned simulation-only executor profile required")
    if _text(profile["evidence_type"]) not in {"synthetic", "recorded"}:
        raise ValueError("executor accepts synthetic or recorded evidence only")
    result = copy.deepcopy(profile)
    result["id"] = _text(profile["id"])
    result["quote_currency"] = _text(profile["quote_currency"])
    symbols = profile["symbols"]
    if not isinstance(symbols, list) or not symbols or len(symbols) > 1000:
        raise ValueError("explicit bounded instrument universe required")
    for symbol in symbols:
        _text(symbol)
    if len(symbols) != len(set(symbols)):
        raise ValueError("duplicate instrument in executor profile")
    result["initial_cash"] = _number(profile["initial_cash"])
    result["fee_rate"] = _number(profile["fee_rate"])
    if result["fee_rate"] >= 1:
        raise ValueError("fee rate must be below one")
    holdings = profile.get("initial_holdings", {})
    if not isinstance(holdings, dict):
        raise ValueError("explicit initial holdings mapping required")
    result["initial_holdings"] = {_text(key): _number(value) for key, value in holdings.items()}
    if not holdings.keys() <= set(symbols):
        raise ValueError("initial holding is outside declared instrument universe")
    return _wire(result)


def _state(profile):
    return {
        "cash": _number(profile["initial_cash"]),
        "holdings": {key: _number(value) for key, value in profile["initial_holdings"].items()},
        "orders": {},
        "fills": {},
        "last_at": None,
        "event_count": 0,
    }


def _reserved(state, fee):
    cash, holdings = Decimal(0), {}
    for order in state["orders"].values():
        if order["status"] not in ACTIVE:
            continue
        remaining = order["quantity"] - order["filled_quantity"]
        if order["side"] == "BUY":
            cash += remaining * order["limit_price"] * (1 + fee)
        else:
            holdings[order["symbol"]] = holdings.get(order["symbol"], Decimal(0)) + remaining
    if cash > state["cash"] or state["cash"] < 0:
        raise ValueError("insufficient unreserved cash")
    if any(
        quantity > state["holdings"].get(symbol, Decimal(0))
        for symbol, quantity in holdings.items()
    ):
        raise ValueError("insufficient unreserved holdings; shorting forbidden")
    return cash, holdings


def _fields(event, required, optional=()):
    required = set(required) | {"event_id", "kind", "at", "order_id"}
    if (
        not isinstance(event, dict)
        or not required <= event.keys()
        or event.keys() - required - set(optional)
    ):
        raise ValueError("invalid event fields")


def _submit(state, event, at):
    _fields(event, {"symbol", "side", "quantity", "limit_price", "expires_at"}, {"decision"})
    oid = _text(event["order_id"])
    if oid in state["orders"] or _text(event["side"]) not in {"BUY", "SELL"}:
        raise ValueError("duplicate order or unsupported side")
    expires = parse_time(event["expires_at"])
    if expires <= at:
        raise ValueError("expiry must follow submission")
    state["orders"][oid] = {
        "order_id": oid,
        "symbol": _text(event["symbol"]),
        "side": event["side"],
        "quantity": _number(event["quantity"], positive=True),
        "limit_price": _number(event["limit_price"], positive=True),
        "filled_quantity": Decimal(0),
        "fees": Decimal(0),
        "status": "PENDING",
        "made_at": utc_text(at),
        "expires_at": utc_text(expires),
    }
    if "decision" in event:
        decision = event["decision"]
        required = {"plan_id", "input_sha256", "strategy_id", "strategy_version", "scope"}
        if not isinstance(decision, dict) or set(decision) != required:
            raise ValueError("invalid decision lineage")
        if decision["scope"] != "SHADOW_SIMULATION":
            raise ValueError("executor accepts shadow simulation decisions only")
        for key in required:
            _text(decision[key])
        checksum = decision["input_sha256"]
        if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
            raise ValueError("decision input hash must be SHA-256")
        state["orders"][oid]["decision"] = copy.deepcopy(decision)


def _fill(state, event, order, at, fee):
    _fields(event, {"fill_id", "quantity", "price", "evidence_id", "observed_at"})
    fid = _text(event["fill_id"])
    observed = parse_time(event["observed_at"])
    if fid in state["fills"] or order["status"] not in ACTIVE:
        raise ValueError("duplicate fill or inactive order")
    if not parse_time(order["made_at"]) < observed <= at < parse_time(order["expires_at"]):
        raise ValueError("fill requires a later observation before expiry")
    quantity, price = (
        _number(event["quantity"], positive=True),
        _number(event["price"], positive=True),
    )
    if quantity > order["quantity"] - order["filled_quantity"]:
        raise ValueError("fill exceeds remaining quantity")
    if (order["side"] == "BUY" and price > order["limit_price"]) or (
        order["side"] == "SELL" and price < order["limit_price"]
    ):
        raise ValueError("fill violates limit price")
    amount, charge = quantity * price, quantity * price * fee
    sign = 1 if order["side"] == "BUY" else -1
    state["cash"] += -amount - charge if sign == 1 else amount - charge
    symbol = order["symbol"]
    state["holdings"][symbol] = state["holdings"].get(symbol, Decimal(0)) + sign * quantity
    order["filled_quantity"] += quantity
    order["fees"] += charge
    order["status"] = "FILLED" if order["filled_quantity"] == order["quantity"] else "PARTIAL"
    state["fills"][fid] = {
        "fill_id": fid,
        "order_id": order["order_id"],
        "quantity": quantity,
        "price": price,
        "fee": charge,
        "observed_at": utc_text(observed),
        "recorded_at": utc_text(at),
        "evidence_id": _text(event["evidence_id"]),
        "simulation_only": True,
    }


def _reconcile(state, event, order, at):
    _fields(event, {"status", "filled_quantity", "evidence_id", "observed_at"})
    _text(event["evidence_id"])
    observed = parse_time(event["observed_at"])
    if not parse_time(order["made_at"]) < observed <= at:
        raise ValueError("reconciliation requires a later retained observation")
    if order["status"] == "UNKNOWN" and observed <= parse_time(order["uncertain_since"]):
        raise ValueError("reconciliation report must follow the latest uncertainty")
    latest_fill = max(
        (
            parse_time(fill["observed_at"])
            for fill in state["fills"].values()
            if fill["order_id"] == order["order_id"]
        ),
        default=parse_time(order["made_at"]),
    )
    if observed < latest_fill:
        raise ValueError("reconciliation report predates retained fills")
    target = _text(event["status"])
    quantity = _number(event["filled_quantity"])
    if quantity != order["filled_quantity"]:
        raise ValueError("reconciliation cannot invent missing fills")
    allowed = {"PENDING", "PARTIAL", "FILLED", "CANCELLED", "EXPIRED", "REJECTED"}
    if target not in allowed or (order["status"] in TERMINAL and target != order["status"]):
        raise ValueError("invalid reconciliation transition")
    if target in {"PENDING", "REJECTED"} and quantity != 0:
        raise ValueError("reported status conflicts with retained fills")
    if target == "PARTIAL" and not 0 < quantity < order["quantity"]:
        raise ValueError("partial status requires retained partial fills")
    if target == "FILLED" and quantity != order["quantity"]:
        raise ValueError("filled status requires all retained fills")
    if target == "EXPIRED" and at < parse_time(order["expires_at"]):
        raise ValueError("cannot expire before deadline")
    if target in {"PENDING", "PARTIAL"} and at >= parse_time(order["expires_at"]):
        raise ValueError("cannot reopen an expired intent")
    order["status"] = target
    order["reconciliation"] = {
        "evidence_id": event["evidence_id"],
        "observed_at": utc_text(observed),
    }


def _apply(state, event, profile):
    if not isinstance(event, dict):
        raise ValueError("event object required")
    _text(event.get("event_id"))
    at = parse_time(event.get("at"))
    if state["last_at"] is not None and at < parse_time(state["last_at"]):
        raise ValueError("out-of-order event receipt")
    kind = _text(event.get("kind"))
    if kind == "submit":
        if _text(event.get("symbol")) not in profile["symbols"]:
            raise ValueError("submission is outside declared instrument universe")
        _submit(state, event, at)
    else:
        oid = _text(event.get("order_id"))
        if oid not in state["orders"]:
            raise ValueError("unknown order")
        order = state["orders"][oid]
        if kind == "fill":
            _fill(state, event, order, at, _number(profile["fee_rate"]))
        elif kind == "reconcile":
            _reconcile(state, event, order, at)
        else:
            _fields(event, {"reason"})
            _text(event["reason"])
            statuses = {
                "cancel": "CANCELLED",
                "expire": "EXPIRED",
                "reject": "REJECTED",
                "unknown": "UNKNOWN",
            }
            if kind not in statuses or order["status"] not in ACTIVE:
                raise ValueError("invalid lifecycle transition")
            if kind == "expire" and at < parse_time(order["expires_at"]):
                raise ValueError("cannot expire before deadline")
            if kind == "reject" and order["filled_quantity"]:
                raise ValueError("cannot reject an already partially filled order")
            order.update(status=statuses[kind], reason=event["reason"])
            if kind == "unknown":
                order["uncertain_since"] = utc_text(at)
    _reserved(state, _number(profile["fee_rate"]))
    state["last_at"] = utc_text(at)
    state["event_count"] += 1


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate event JSON key")
            result[key] = value
        return result

    def bad(value):
        raise ValueError("nonfinite event JSON")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


class ReplayExecutor:
    """A durable simulation whose sole state authority is its verified event log."""

    def __init__(self, root, profile):
        self.root, self.profile = Path(root), _profile(profile)
        self._guard_paths()
        with locked(self.root):
            extras = {path.name for path in self.root.iterdir()} - {
                ".runtime.lock",
                "executor.json",
                "events.jsonl",
                "checkpoint.json",
            }
            if extras:
                raise ValueError("executor requires a separate directory; existing artifacts found")
            marker = self.root / "executor.json"
            journal = self.root / "events.jsonl"
            if not marker.exists():
                if journal.exists() and journal.stat().st_size:
                    raise ValueError("event log has no retained executor profile")
                with journal.open("ab") as stream:
                    stream.flush()
                    os.fsync(stream.fileno())
                immutable_json(self.root / "checkpoint.json", {"sequence": 0, "record_hash": None})
            immutable_json(
                marker, {"profile": self.profile, "profile_sha256": digest(self.profile)}
            )
            self._read()

    def _guard_paths(self):
        if self.root.is_symlink() or (
            self.root.exists() and any(path.is_symlink() for path in self.root.iterdir())
        ):
            raise ValueError("executor root and files must not be symbolic links")

    def _read(self):
        marker = read_json(self.root / "executor.json")
        if marker != {"profile": self.profile, "profile_sha256": digest(self.profile)}:
            raise ValueError("executor profile integrity failure")
        path = self.root / "events.jsonl"
        if not path.exists() or not (self.root / "checkpoint.json").exists():
            raise ValueError("missing executor journal or checkpoint")
        raw = path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ValueError("torn executor journal; preserve and recover before appending")
        state, rows, previous, identities = _state(self.profile), [], None, {}
        for sequence, line in enumerate(raw.splitlines(), 1):
            row = _json(line)
            if not isinstance(row, dict) or set(row) != {
                "sequence",
                "previous_hash",
                "event",
                "record_hash",
            }:
                raise ValueError("invalid executor journal entry")
            body = {key: value for key, value in row.items() if key != "record_hash"}
            if (
                type(row["sequence"]) is not int
                or row["sequence"] != sequence
                or row["previous_hash"] != previous
                or digest(body) != row["record_hash"]
            ):
                raise ValueError("executor journal integrity failure")
            if not isinstance(row["event"], dict):
                raise ValueError("event object required")
            eid = _text(row["event"].get("event_id"))
            if eid in identities:
                raise ValueError("duplicate event identity in journal")
            _apply(state, row["event"], self.profile)
            identities[eid] = row["event"]
            rows.append(row)
            previous = row["record_hash"]
        checkpoint = read_json(self.root / "checkpoint.json")
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"sequence", "record_hash"}:
            raise ValueError("invalid executor checkpoint")
        sequence = checkpoint["sequence"]
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or not 0 <= sequence <= len(rows)
        ):
            raise ValueError("executor journal was truncated after checkpoint")
        expected = rows[sequence - 1]["record_hash"] if sequence else None
        if checkpoint["record_hash"] != expected:
            raise ValueError("executor checkpoint integrity failure")
        return state, rows, identities

    def apply(self, event):
        event = _json(canonical(event))
        if not isinstance(event, dict):
            raise ValueError("event object required")
        self._guard_paths()
        with locked(self.root):
            state, rows, identities = self._read()
            identity = _text(event.get("event_id"))
            if identity in identities:
                if identities[identity] != event:
                    raise ValueError("conflicting event identity reuse")
                # A previous append may have survived while checkpoint publication
                # failed. Acknowledge the retry only after durability is restored.
                self._checkpoint(rows[-1])
                return self._view(state)
            _apply(state, event, self.profile)
            body = {
                "sequence": len(rows) + 1,
                "previous_hash": rows[-1]["record_hash"] if rows else None,
                "event": event,
            }
            row = dict(body, record_hash=digest(body))
            with (self.root / "events.jsonl").open("ab") as stream:
                stream.write(canonical(row) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            self._checkpoint(row)
            return self._view(state)

    def _checkpoint(self, row):
        """Caller holds the writer lock; even retries must finish durable commit."""
        with (self.root / "events.jsonl").open("rb") as stream:
            os.fsync(stream.fileno())
        directory = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        atomic_json(
            self.root / "checkpoint.json",
            {"sequence": row["sequence"], "record_hash": row["record_hash"]},
        )

    def _view(self, state):
        cash, holdings = _reserved(state, _number(self.profile["fee_rate"]))
        return _wire(
            dict(
                state,
                cash_reserved=cash,
                cash_available=state["cash"] - cash,
                holdings_reserved=holdings,
            )
        )

    def snapshot(self):
        self._guard_paths()
        with locked(self.root):
            return self._view(self._read()[0])

    def verify(self):
        return {"ok": True, "state": self.snapshot(), "simulation_only": True}


def execution_run(root, request):
    """Apply an explicit finite batch. A retry safely skips identical events."""
    if (
        not isinstance(request, dict)
        or set(request) != {"profile", "events"}
        or not isinstance(request["events"], list)
    ):
        raise ValueError("executor request requires profile and event list")
    if len(request["events"]) > 10000:
        raise ValueError("executor batch exceeds 10000 events")
    executor = ReplayExecutor(root, request["profile"])
    for event in request["events"]:
        executor.apply(event)
    state = executor.snapshot()
    return {
        "ok": True,
        "schema_version": VERSION,
        "simulation_only": True,
        "evidence_type": executor.profile["evidence_type"],
        "quote_currency": executor.profile["quote_currency"],
        "state": state,
        "event_count": state["event_count"],
        "execution_basis": "CALLER_RETAINED_SIMULATION_REFERENCES",
    }

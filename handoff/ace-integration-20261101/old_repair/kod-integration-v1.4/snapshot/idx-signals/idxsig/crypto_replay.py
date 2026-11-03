"""CRYPTO_REPLAY_v1: a historical crypto spot paper-account replay on daily UTC bars (research/CRYPTO_REPLAY_v1).

Simulation only. This is NOT the live quote-driven adapter (crypto_account.py): a daily candle cannot show what a
live order book would have filled, so every execution rule below is an explicitly modelled, idealized assumption.

Timing (verified in premove_core.build_examples): a ranking dated d uses bars through the close of UTC day d only.
The account decides after that close and enters at the open of day d + 1 + entry_delay. Bars are UTC calendar
days, weekends included.

One account per arm, all with the same Policy:
  * spot, long only, no leverage; START_CASH USDT.
  * an order is a market buy at the entry day's open for a fixed USDT notional N reserved at the decision, so cash
    can never be overspent: N = risk x equity / L, where L is the fraction of N lost if the stop fills exactly at
    its level: L = 1 - (1 - stop)(1 - slip)(1 - fee) / (1 + fee). Planned risk per position is therefore exactly
    risk x equity at the decision, whatever the open turns out to be.
  * candidates are taken in frozen rank order; one skips if its coin is already held or pending, if MAX_NEW_PER_DAY
    orders were already placed for that decision day, if the aggregate planned risk would exceed MAX_RISK, or if N
    exceeds the free cash. Aggregate planned risk = the sum of the planned risk fractions (RISK of equity at each
    order's own decision) of every pending order and open position, so with the defaults at most three positions
    are pending or open at once, and neither a small loss nor an open gain changes that.
  * entry fill F = open x (1 + slip), fee on the notional; stop = F x (1 - stop), target = F x (1 + target).
  * exits, bar by bar (the entry bar is bar 1): from bar 2 a gap open at or below the stop exits at that open (worse
    than the stop); a gap open at or above the target exits at the target (no credit for the better open); within a
    bar, low <= stop and high >= target together is AMBIGUOUS and resolved stop-first; otherwise the touched level;
    else at the close of bar `hold_bars`. Every exit pays slippage and the fee. If the bar-5 close is missing the
    position is still held, stop and target still resting, until the next valid bar exits it (stop, target or that
    bar's close); such rolled exits are counted.
  * a missing or invalid bar never fills or exits anything: an order whose entry bar is missing is rejected; a held
    position simply waits (counted); a time exit whose bar is missing rolls to the next valid close (counted); a
    position still open when the data ends is UNRESOLVED and valued at its last valid close (dated).
Equity each day = cash + open positions at their last valid close; reserved cash stays inside cash. The daily row is
completed after that night's decisions, so it shows the night's reservations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Policy:
    start_cash: float = 10_000.0
    risk: float = 0.005  # planned loss at the stop per position, of equity at the decision
    max_risk: float = 0.015  # pending plus open planned risk, of equity at the decision
    max_new_per_day: int = 3
    stop: float = 0.05
    target: float = 0.10
    hold_bars: int = 5  # the entry bar is bar 1
    fee: float = 0.001  # per side, on the traded notional
    slip: float = 0.001  # per side, adverse
    entry_delay: int = 0  # extra daily bars between the decision and the entry open

    @property
    def loss_fraction(self) -> float:
        return 1 - (1 - self.stop) * (1 - self.slip) * (1 - self.fee) / (1 + self.fee)

    def record(self) -> dict:
        return {**asdict(self), "loss_fraction": self.loss_fraction}


@dataclass
class Bars:
    """Daily UTC bars of one coin on a full calendar; `valid` is False where the bar is missing or unusable."""

    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    valid: pd.Series

    def get(self, day: date):
        ts = pd.Timestamp(day)
        if ts not in self.valid.index or not bool(self.valid.loc[ts]):
            return None
        return (
            float(self.open.loc[ts]),
            float(self.high.loc[ts]),
            float(self.low.loc[ts]),
            float(self.close.loc[ts]),
        )

    def last_close(self, day: date):
        """(close, its date) of the last valid bar on or before `day`, or (None, None)."""
        upto = self.valid.loc[: pd.Timestamp(day)]
        days = upto.index[upto.to_numpy(dtype=bool)]
        if not len(days):
            return None, None
        return float(self.close.loc[days[-1]]), days[-1].date()


def bars_from_panel(panel: pd.DataFrame, first: date, last: date) -> dict[str, Bars]:
    """One Bars per ticker on the calendar first..last. A bar is valid when present, complete, OHLCV > 0 and quote
    value known (premove_core's validity rule). Nothing is forward-filled."""
    calendar = pd.date_range(pd.Timestamp(first), pd.Timestamp(last), freq="D")
    out = {}
    for ticker, g in panel.groupby("ticker", sort=True):
        g = g.set_index(pd.to_datetime(g["date"])).reindex(calendar)
        valid = (
            g["complete_bar"].eq(True)
            & (g[["open", "high", "low", "close", "volume"]] > 0).all(axis=1)
            & g["value"].notna()
        )
        out[ticker] = Bars(g["open"], g["high"], g["low"], g["close"], valid.fillna(False))
    return out


@dataclass
class Account:
    policy: Policy
    cash: float = 0.0
    reserved: float = 0.0
    pending: dict = field(default_factory=dict)  # order id -> order
    open: dict = field(default_factory=dict)  # order id -> position
    realized: float = 0.0
    events: list = field(default_factory=list)
    daily: list = field(default_factory=list)
    counters: dict = field(default_factory=dict)
    next_id: int = 1

    def count(self, key: str, n: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + n


def _exit(
    acct: Account, oid: int, pos: dict, day: date, raw: float, reason: str, bar_index: int, **extra
):
    p = acct.policy
    fill = raw * (1 - p.slip)
    proceeds = pos["units"] * fill * (1 - p.fee)
    pnl = proceeds - pos["notional"]
    acct.cash += proceeds
    acct.realized += pnl
    acct.events.append(
        {
            "type": "EXIT",
            "order_id": oid,
            "ticker": pos["ticker"],
            "day": day.isoformat(),
            "reason": reason,
            "bar_index": bar_index,
            "raw_price": raw,
            "fill_price": fill,
            "proceeds": proceeds,
            "pnl": pnl,
            "net_return": pnl / pos["notional"],
            "fee_usd": pos["units"] * fill * p.fee,
            "slippage_usd": pos["units"] * raw * p.slip,
            **extra,
        }
    )
    del acct.open[oid]


def _fill_orders(acct: Account, bars: dict[str, Bars], day: date) -> None:
    p = acct.policy
    for oid in sorted(o for o, x in acct.pending.items() if x["entry_day"] == day):
        order = acct.pending.pop(oid)
        acct.reserved -= order["notional"]
        bar = bars[order["ticker"]].get(day) if order["ticker"] in bars else None
        if bar is None:
            acct.count("missing_entry_bar")
            acct.events.append(
                {
                    "type": "ENTRY",
                    "order_id": oid,
                    "ticker": order["ticker"],
                    "day": day.isoformat(),
                    "status": "REJECTED_MISSING_ENTRY_BAR",
                }
            )
            continue
        raw = bar[0]
        fill = raw * (1 + p.slip)
        units = order["notional"] / (fill * (1 + p.fee))
        acct.cash -= order["notional"]
        acct.open[oid] = {
            "ticker": order["ticker"],
            "units": units,
            "notional": order["notional"],
            "entry_day": day,
            "fill": fill,
            "stop": fill * (1 - p.stop),
            "target": fill * (1 + p.target),
            "deadline": day + timedelta(days=p.hold_bars - 1),
            "planned_risk": order["planned_risk"],
            "risk_fraction": order["risk_fraction"],
            "signal_day": order["signal_day"],
            "rank": order["rank"],
        }
        acct.events.append(
            {
                "type": "ENTRY",
                "order_id": oid,
                "ticker": order["ticker"],
                "day": day.isoformat(),
                "status": "FILLED",
                "raw_open": raw,
                "fill_price": fill,
                "units": units,
                "notional": order["notional"],
                "fee_usd": units * fill * p.fee,
                "slippage_usd": units * raw * p.slip,
                "stop": fill * (1 - p.stop),
                "target": fill * (1 + p.target),
                "deadline": (day + timedelta(days=p.hold_bars - 1)).isoformat(),
            }
        )


def _manage_positions(acct: Account, bars: dict[str, Bars], day: date) -> None:
    for oid in sorted(acct.open):
        pos = acct.open[oid]
        k = (day - pos["entry_day"]).days + 1
        bar = bars[pos["ticker"]].get(day)
        if bar is None:
            acct.count("missing_bar_while_held")
            if day == pos["deadline"]:
                acct.count("time_exit_rolled")
            continue
        o, h, lo, c = bar
        if k > 1 and o <= pos["stop"]:
            _exit(acct, oid, pos, day, o, "STOP_GAP", k)
        elif k > 1 and o >= pos["target"]:
            _exit(acct, oid, pos, day, pos["target"], "TARGET_GAP", k)
        elif lo <= pos["stop"] and h >= pos["target"]:
            acct.count("ambiguous_bar")
            _exit(acct, oid, pos, day, pos["stop"], "STOP", k, ambiguous=True)
        elif lo <= pos["stop"]:
            _exit(acct, oid, pos, day, pos["stop"], "STOP", k)
        elif h >= pos["target"]:
            _exit(acct, oid, pos, day, pos["target"], "TARGET", k)
        elif day >= pos["deadline"]:
            _exit(
                acct,
                oid,
                pos,
                day,
                c,
                "TIME_EXIT" if day == pos["deadline"] else "TIME_EXIT_ROLLED",
                k,
            )


def _mark(acct: Account, bars: dict[str, Bars], day: date) -> dict:
    p = acct.policy
    value = unrealized = open_risk = 0.0
    stale = 0
    for pos in acct.open.values():
        close, on = bars[pos["ticker"]].last_close(day)
        if on != day:
            stale += 1
        worth = pos["units"] * close
        value += worth
        unrealized += worth - pos["notional"]
        open_risk += max(worth - pos["units"] * pos["stop"] * (1 - p.slip) * (1 - p.fee), 0.0)
    equity = acct.cash + value
    row = {
        "day": day.isoformat(),
        "cash": acct.cash,
        "reserved": acct.reserved,
        "free_cash": acct.cash - acct.reserved,
        "open_value": value,
        "equity": equity,
        "realized": acct.realized,
        "unrealized": unrealized,
        "open_positions": len(acct.open),
        "pending_orders": len(acct.pending),
        "stale_marks": stale,
        "open_risk": open_risk,
        "exposure": value / equity if equity > 0 else 0.0,
    }
    acct.daily.append(row)
    return row


def _decide(acct: Account, ranked: list[dict], day: date, row: dict) -> None:
    p = acct.policy
    equity = row["equity"]
    entry_day = day + timedelta(days=1 + p.entry_delay)
    held = {x["ticker"] for x in acct.open.values()} | {x["ticker"] for x in acct.pending.values()}
    risk_used = sum(x["risk_fraction"] for x in acct.pending.values()) + sum(
        x["risk_fraction"] for x in acct.open.values()
    )
    placed = 0
    for cand in ranked:
        base = {
            "type": "DECISION",
            "ticker": cand["ticker"],
            "signal_day": day.isoformat(),
            "rank": cand["rank"],
        }
        risk = p.risk * equity
        notional = risk / p.loss_fraction
        if cand["ticker"] in held:
            why = "SKIP_DUPLICATE_SYMBOL"
        elif placed >= p.max_new_per_day:
            why = "SKIP_DAILY_LIMIT"
        elif risk_used + p.risk > p.max_risk + 1e-12:
            why = "SKIP_RISK_LIMIT"
        elif notional > acct.cash - acct.reserved + 1e-9:
            why = "SKIP_INSUFFICIENT_CASH"
        else:
            why = None
        if why:
            acct.count(why)
            acct.events.append({**base, "decision": why})
            continue
        oid = acct.next_id
        acct.next_id += 1
        acct.pending[oid] = {
            "ticker": cand["ticker"],
            "notional": notional,
            "planned_risk": risk,
            "risk_fraction": p.risk,
            "entry_day": entry_day,
            "signal_day": day.isoformat(),
            "rank": cand["rank"],
        }
        acct.reserved += notional
        risk_used += p.risk
        held.add(cand["ticker"])
        placed += 1
        acct.events.append(
            {
                **base,
                "decision": "ORDER",
                "order_id": oid,
                "entry_day": entry_day.isoformat(),
                "notional": notional,
                "planned_risk": risk,
                "equity_at_decision": equity,
                "aggregate_risk_after": risk_used,
            }
        )
    row.update(
        reserved=acct.reserved,
        free_cash=acct.cash - acct.reserved,
        pending_orders=len(acct.pending),
    )


def run(
    shortlist: pd.DataFrame | None, bars: dict[str, Bars], first: date, last: date, policy: Policy
) -> Account:
    """Replay one arm over UTC days first..last. `shortlist` has date, ticker, rank (None = cash only).
    Each day: fill orders due at its open, manage positions over its bar, mark at its close, then decide on the
    rankings dated that day."""
    acct = Account(policy=policy, cash=policy.start_cash)
    by_day: dict[date, list[dict]] = {}
    if shortlist is not None:
        for r in shortlist.sort_values(["date", "rank", "ticker"]).itertuples(index=False):
            by_day.setdefault(pd.Timestamp(r.date).date(), []).append(
                {"ticker": r.ticker, "rank": int(r.rank)}
            )
    day = first
    while day <= last:
        _fill_orders(acct, bars, day)
        _manage_positions(acct, bars, day)
        _decide(acct, by_day.get(day, []), day, _mark(acct, bars, day))
        day += timedelta(days=1)
    exit_cost = (1 - policy.slip) * (1 - policy.fee)
    for oid, pos in sorted(acct.open.items()):
        close, on = bars[pos["ticker"]].last_close(last)
        acct.count("unresolved_end_of_data")
        acct.events.append(
            {
                "type": "UNRESOLVED",
                "order_id": oid,
                "ticker": pos["ticker"],
                "entry_day": pos["entry_day"].isoformat(),
                "deadline": pos["deadline"].isoformat(),
                "bars_held": (last - pos["entry_day"]).days + 1,
                "valued_at_close_of": on.isoformat() if on else None,
                "value": pos["units"] * close,
                "unrealized": pos["units"] * close - pos["notional"],
                "net_liquidation_value": pos["units"] * close * exit_cost,
                "value_if_stopped": pos["units"] * pos["stop"] * exit_cost,
                "value_if_target": pos["units"] * pos["target"] * exit_cost,
                "note": "not realized: the 2024 bars that would finish this trade are never read",
            }
        )
    for oid, order in sorted(acct.pending.items()):
        acct.count("unfilled_end_of_data")
        acct.events.append(
            {
                "type": "UNFILLED",
                "order_id": oid,
                "ticker": order["ticker"],
                "entry_day": order["entry_day"].isoformat(),
                "reason": "entry day after the data ends",
            }
        )
    return acct


# ---------------------------------------------------------------------------------------------- results
def summarize(acct: Account) -> dict:
    p = acct.policy
    exits = [e for e in acct.events if e["type"] == "EXIT"]
    entries = [e for e in acct.events if e["type"] == "ENTRY" and e["status"] == "FILLED"]
    pnls = np.array([e["pnl"] for e in exits])
    wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
    equity = np.array([d["equity"] for d in acct.daily])
    peak = np.maximum.accumulate(np.concatenate([[p.start_cash], equity]))[1:]
    drawdown = equity / peak - 1
    last = acct.daily[-1]
    mean_equity = float(equity.mean())
    traded = sum(e["notional"] for e in entries) + sum(e["proceeds"] for e in exits)
    reasons: dict[str, int] = {}
    for e in exits:
        reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
    return {
        "start_equity": p.start_cash,
        "end_equity": last["equity"],
        "net_return": last["equity"] / p.start_cash - 1,
        "realized_pnl": acct.realized,
        "unrealized_pnl": last["unrealized"],
        "max_drawdown": float(drawdown.min()),
        "max_drawdown_day": acct.daily[int(drawdown.argmin())]["day"],
        "orders": sum(
            1 for e in acct.events if e["type"] == "DECISION" and e["decision"] == "ORDER"
        ),
        "fills": len(entries),
        "closed_trades": len(exits),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": float(len(wins) / len(exits)) if exits else None,
        "average_win": float(wins.mean()) if len(wins) else None,
        "average_loss": float(losses.mean()) if len(losses) else None,
        "expectancy_per_trade": float(pnls.mean()) if len(pnls) else None,
        "profit_factor": float(wins.sum() / -losses.sum())
        if len(losses) and losses.sum() < 0
        else None,
        "fees_usd": sum(e["fee_usd"] for e in entries) + sum(e["fee_usd"] for e in exits),
        "slippage_usd": sum(e["slippage_usd"] for e in entries)
        + sum(e["slippage_usd"] for e in exits),
        "mean_exposure": float(np.mean([d["exposure"] for d in acct.daily])),
        "days_with_a_position": int(sum(d["open_positions"] > 0 for d in acct.daily)),
        "turnover": traded / mean_equity if mean_equity else None,
        "exit_reasons": reasons,
        "skips_and_rejections": {k: v for k, v in sorted(acct.counters.items())},
    }


def check_invariants(acct: Account) -> list[str]:
    """Accounting and causality checks on a finished replay; an empty list means all hold."""
    p, problems = acct.policy, []
    orders = {
        e["order_id"]: e
        for e in acct.events
        if e["type"] == "DECISION" and e["decision"] == "ORDER"
    }
    entries = {e["order_id"]: e for e in acct.events if e["type"] == "ENTRY"}
    for oid, e in entries.items():
        if e["day"] <= orders[oid]["signal_day"]:
            problems.append(f"order {oid}: entry on or before its decision day")
        if e["day"] != orders[oid]["entry_day"]:
            problems.append(f"order {oid}: entry on another day than planned")
    for e in (x for x in acct.events if x["type"] == "EXIT"):
        en = entries.get(e["order_id"])
        if en is None or en["status"] != "FILLED" or e["day"] < en["day"]:
            problems.append(f"order {e['order_id']}: exit before or without its fill")
    for d in acct.daily:
        if d["cash"] < -1e-6 or d["free_cash"] < -1e-6:
            problems.append(f"{d['day']}: cash overspent")
        if abs(d["equity"] - (p.start_cash + d["realized"] + d["unrealized"])) > 1e-6:
            problems.append(f"{d['day']}: equity does not reconcile with realized + unrealized")
    return problems


def audit_trades(acct: Account, bars: dict[str, Bars]) -> list[str]:
    """Re-derive every fill and exit from the raw bars, independently of the replay loop: the entry open, the fill
    and units, the first bar that should have closed the trade and at what price, and the P&L arithmetic."""
    p, problems = acct.policy, []
    entries = {
        e["order_id"]: e for e in acct.events if e["type"] == "ENTRY" and e["status"] == "FILLED"
    }
    exits = {e["order_id"]: e for e in acct.events if e["type"] == "EXIT"}
    end = date.fromisoformat(acct.daily[-1]["day"])
    for oid, en in entries.items():
        b = bars[en["ticker"]]
        day0 = date.fromisoformat(en["day"])
        bar = b.get(day0)
        if bar is None or abs(bar[0] - en["raw_open"]) > 1e-12:
            problems.append(f"order {oid}: entry open does not match the bar")
            continue
        fill = bar[0] * (1 + p.slip)
        units = en["notional"] / (fill * (1 + p.fee))
        if abs(fill - en["fill_price"]) > 1e-9 * fill or abs(units - en["units"]) > 1e-9 * units:
            problems.append(f"order {oid}: fill or units do not follow from the open")
        stop, target = fill * (1 - p.stop), fill * (1 + p.target)
        deadline = day0 + timedelta(days=p.hold_bars - 1)
        expected, day = None, day0
        while expected is None and day <= end:
            k = (day - day0).days + 1
            bar = b.get(day)
            if bar is not None:
                o, h, lo, c = bar
                if k > 1 and o <= stop:
                    expected = (day, "STOP_GAP", o)
                elif k > 1 and o >= target:
                    expected = (day, "TARGET_GAP", target)
                elif lo <= stop:
                    expected = (day, "STOP", stop)
                elif h >= target:
                    expected = (day, "TARGET", target)
                elif day >= deadline:
                    expected = (day, "TIME_EXIT" if day == deadline else "TIME_EXIT_ROLLED", c)
            day += timedelta(days=1)
        ex = exits.get(oid)
        if expected is None:
            if ex is not None:
                problems.append(f"order {oid}: exit recorded where the bars show none")
            continue
        if ex is None:
            problems.append(
                f"order {oid}: the bars show an exit on {expected[0]} that was not recorded"
            )
            continue
        same = (ex["day"], ex["reason"]) == (expected[0].isoformat(), expected[1])
        if not same or abs(ex["raw_price"] - expected[2]) > 1e-9 * expected[2]:
            problems.append(
                f"order {oid}: exit {ex['day']} {ex['reason']} {ex['raw_price']} but the bars give "
                f"{expected[0]} {expected[1]} {expected[2]}"
            )
            continue
        pnl = units * expected[2] * (1 - p.slip) * (1 - p.fee) - en["notional"]
        if abs(pnl - ex["pnl"]) > 1e-6:
            problems.append(f"order {oid}: P&L does not follow from the prices and costs")
    return problems


def tested_accounting_crosscheck(acct: Account) -> dict:
    """Cash, reservations and realized P&L recomputed by the US paper account's tested accounting
    (paper_account.account_state) from this replay's orders, entries and exits."""
    from . import paper_account as stock

    recs = []
    for e in acct.events:
        if e["type"] == "DECISION" and e["decision"] == "ORDER":
            recs.append(
                {
                    "type": stock.ORDER,
                    "arm": "REPLAY",
                    "record_hash": f"o{e['order_id']}",
                    "reserved_usd": e["notional"],
                    "planned_risk_usd": e["planned_risk"],
                    "ticker": e["ticker"],
                }
            )
        elif e["type"] == "ENTRY":
            rec = {
                "type": stock.ENTRY,
                "arm": "REPLAY",
                "order_record_hash": f"o{e['order_id']}",
                "status": e["status"],
            }
            if e["status"] == "FILLED":
                rec.update(
                    shares=e["units"],
                    price=e["fill_price"],
                    cost_in=acct.policy.fee,
                    stop=e["stop"],
                )
            recs.append(rec)
        elif e["type"] == "EXIT":
            recs.append(
                {
                    "type": stock.EXIT,
                    "arm": "REPLAY",
                    "order_record_hash": f"o{e['order_id']}",
                    "net_pnl_usd": e["pnl"],
                }
            )
    st = stock.account_state(recs, "REPLAY")
    st["cash"] += (
        acct.policy.start_cash - stock.START_CASH
    )  # the stock module starts at its own constant
    st["free_cash"] = st["cash"] - st["reserved"]
    return {
        "cash": st["cash"],
        "reserved": st["reserved"],
        "realized": st["realized"],
        "replay_cash": acct.cash,
        "replay_reserved": acct.reserved,
        "replay_realized": acct.realized,
        "match": abs(st["cash"] - acct.cash) < 1e-6
        and abs(st["reserved"] - acct.reserved) < 1e-6
        and abs(st["realized"] - acct.realized) < 1e-6,
    }


def fingerprint(acct: Account) -> str:
    """A digest of every event and daily row, for the repeat-run check."""
    import hashlib

    blob = json.dumps({"events": acct.events, "daily": acct.daily}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()

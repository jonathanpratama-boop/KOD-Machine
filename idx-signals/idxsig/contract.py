"""EXEC-US-v2: one trading contract for US daily-bar strategies, account included.

Historical replay and forward paper scoring both drive `Account.step`, one session at a time, on
data through that session only. Replay calls it over a stored panel. Forward scoring calls it each
day on the data available that day, with the account state saved as JSON between calls.
The trading rules live only in `step`, so the same inputs give the same orders, fills, exits and
balances in both modes. The full specification, with every assumption, is in
research/EXEC_US_v2/CONTRACT.md; a change to any rule here is a new CONTRACT_VERSION.

Legacy execution is untouched: EXEC-US-v1 (exec_us.py, PAPER-POLICY-v4) and the backtest fill
models A, B, B2 and C (execution.py) keep their versions and behaviour.

Units: the panel is split-adjusted, and as-traded = adjusted x unit_factor F (verified split
schedule). Every price and share count in a record is AS TRADED in the session named next to it.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass

import numpy as np

from .exec_us import cost_rate, floor_tick

CONTRACT_VERSION = "EXEC-US-v2"

SCAN_STATUSES = ("SIGNALS", "NO_SIGNAL", "FAILED")
ORDER_OUTCOMES = (
    "REJECTED_NO_PLAN",            # at the decision: no entry both above the stop and within the 5% and chase limits
    "REJECTED_SIZE_ZERO",          # at the decision: no whole share fits risk, capital and liquidity limits
    "REJECTED_INSUFFICIENT_CASH",  # at the decision: unreserved cash does not cover one share
    "REJECTED_ALREADY_HELD",       # at the decision: the name is held or has an order working
    "UNFILLED_NOT_TRADED",         # at the entry open: no opening print / no volume that session
    "UNFILLED_OPEN_ABOVE_LIMIT",   # at the entry open: the gap put the open above the permitted entry
    "UNFILLED_NO_LIQUIDITY",       # at the entry open: the fill bound allows no share
    "FILLED",                      # the whole planned quantity (the bound is an assumption; see fill_evidence)
    "PARTIAL",                     # part of it; the rest is cancelled
)
FILL_EVIDENCE = ("daily bar only: the open print and whole-session volume are observed; the opening "
                 "auction's own volume is not. Whole-session volume is an upper bound on what the auction "
                 "could fill, so the fill quantity is an assumption, not proof of liquidity.")


@dataclass(frozen=True)
class ContractSpec:
    max_stop_distance: float = 0.05     # entry-to-invalidation at most 5%, measured at the permitted entry
    chase_limit: float = 0.10           # and no entry above signal close x 1.10
    max_hold_sessions: int = 5          # the entry session is session 1; time exit at the close of session 5
    starting_cash_usd: float = 10_000.0  # hypothetical cash account, no leverage, no shorting
    risk_fraction: float = 0.01         # planned loss at the stop (costs included, gaps excluded) <= 1% of equity
    max_position_fraction: float = 0.20  # position at the permitted entry <= 20% of equity
    plan_participation: float = 0.10    # planned value <= 10% of the 20-session median traded value
    fill_participation: float = 0.10    # filled shares <= 10% of the entry session's whole volume (upper bound)
    capacity_window: int = 20
    stop_slippage: float = 0.0          # assumed: a triggered stop fills at the stop (or the open on a gap)

    def record(self) -> dict:
        return {"contract_version": CONTRACT_VERSION, **asdict(self)}

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.record(), sort_keys=True).encode()).hexdigest()


SPEC = ContractSpec()


class ScanFailed(Exception):
    """The scan could not establish its inputs (stale or missing data, a hash mismatch, an error)."""


def adv_value(value, present, k: int, window: int) -> float:
    """Median traded value (USD) of the `window` sessions through k; a listed session without trades
    counts as 0. Traded value needs no share-unit conversion: a split changes shares, not dollars."""
    a = max(k - window + 1, 0)
    listed = present[a: k + 1]
    if not listed.any():
        return 0.0
    return float(np.median(np.nan_to_num(value[a: k + 1])[listed]))


def plan_order(signal_close: float, invalidation: float, adv_usd: float, equity: float,
               spec: ContractSpec = SPEC) -> dict:
    """The decision-time plan, in signal-session as-traded units, before cash is checked.

    The invalidation comes from the strategy and is never moved: an entry that cannot meet the 5%
    rule at this stop is not taken. Size: the smallest of the risk, capital and liquidity limits,
    each computed at the permitted entry (the worst price the order accepts)."""
    stop = floor_tick(invalidation)
    by_stop = floor_tick(stop / (1 - spec.max_stop_distance))
    by_chase = floor_tick(signal_close * (1 + spec.chase_limit))
    limit = min(by_stop, by_chase)
    plan = {"signal_close": signal_close, "invalidation": stop, "limit_by_stop_rule": by_stop,
            "limit_by_chase_rule": by_chase, "entry_limit": limit,
            "stop_distance_from_signal_close": (signal_close - stop) / signal_close,
            "adv20_value_usd": adv_usd, "equity_at_decision_usd": equity}
    if not stop > 0 or limit <= stop:
        return {**plan, "outcome": "REJECTED_NO_PLAN",
                "reason": "no entry price is above the stop and within both the 5% rule and the chase limit"}
    c_in, c_out = cost_rate(limit, "buy"), cost_rate(limit, "sell")
    risk_per_share = (limit - stop) + limit * (c_in + c_out)
    by_risk = spec.risk_fraction * equity / risk_per_share
    by_capital = spec.max_position_fraction * equity / limit
    by_liquidity = spec.plan_participation * adv_usd / limit
    shares = int(math.floor(min(by_risk, by_capital, by_liquidity) + 1e-9))
    binding = min((by_risk, "risk"), (by_capital, "capital"), (by_liquidity, "liquidity"))[1]
    plan.update(stop_distance_at_limit=(limit - stop) / limit, risk_per_share=risk_per_share,
                shares_by_risk=by_risk, shares_by_capital=by_capital, shares_by_liquidity=by_liquidity,
                binding_limit=binding, shares=shares)
    if shares < 1:
        return {**plan, "outcome": "REJECTED_SIZE_ZERO", "reason": f"no whole share fits ({binding} binds)"}
    return {**plan, "outcome": "PLANNED"}


def reservation_per_share(entry_limit: float, stop: float) -> float:
    """Cash held per planned share until the open: the limit price plus the highest buy cost any
    fill inside the band can carry (cost tiers rise as the price falls, so the stop's tier)."""
    return entry_limit * (1 + max(cost_rate(entry_limit, "buy"), cost_rate(stop, "buy")))


def _r(x: float) -> float:
    return round(float(x), 6)


class Account:
    """The account state is a plain dict, so forward scoring can save it as JSON between sessions."""

    def __init__(self, spec: ContractSpec = SPEC, state: dict | None = None):
        self.spec = spec
        self.state = copy.deepcopy(state) if state is not None else {
            "contract": spec.record(), "contract_sha256": spec.sha256(), "cash_usd": spec.starting_cash_usd,
            "orders": [], "positions": [], "closed": [], "events": [], "last_session_index": -1,
            "last_session": None}
        if self.state["contract_sha256"] != spec.sha256():
            raise ValueError("state was made under another contract; a contract change is a new version")

    # -- helpers ---------------------------------------------------------------------------------------
    def _event(self, session: str, kind: str, **kw):
        self.state["events"].append({"session": session, "event": kind, **kw,
                                     "cash_usd": _r(self.state["cash_usd"]),
                                     "reserved_usd": _r(sum(o["reserved_usd"] for o in self.state["orders"]))})

    def _equity(self, m, k: int) -> float:
        """Cash + reservations + positions at the close of k (last traded close if k did not trade)."""
        total = self.state["cash_usd"] + sum(o["reserved_usd"] for o in self.state["orders"])
        for p in self.state["positions"]:
            n = p["n"]
            last = max(i for i in range(p["entry_index"], k + 1) if m.present[n, i] and np.isfinite(m.close[n, i]))
            total += p["qty_adj"] * m.close[n, last]
        return total

    # -- one session -------------------------------------------------------------------------------------
    def step(self, m, k: int, signals: list, expected_session: str | None = None) -> dict:
        """Process session k on a market holding data through k at least (columns beyond k are never
        read). `signals` is [(ticker index, invalidation as traded at k)] from data through k, or a
        ScanFailed instance. Order inside the session: entry orders at the open, then exits, then the
        decisions after the close."""
        st = self.state
        session = str(m.dates[k])
        if k <= st["last_session_index"]:
            raise ValueError(f"session {session} already processed")
        if expected_session is not None and session != expected_session:
            raise ScanFailed(f"STALE_DATA: the data ends at {session}, the scan expects {expected_session}")
        uf = m.unit_factor if m.unit_factor is not None else np.ones(m.shape)

        # 1. Entry orders at the open of k (orders placed after an earlier close, entry session = k).
        for o in list(st["orders"]):
            self._open_fill(m, k, uf, o, session)
        # 2. Exits for positions held into k.
        for p in list(st["positions"]):
            self._exit_check(m, k, uf, p, session)
        # 3. Decisions after the close of k.
        if isinstance(signals, ScanFailed):
            scan = {"session": session, "status": "FAILED", "reason": str(signals), "signals": 0}
            self._event(session, "SCAN_FAILED", reason=str(signals))
        else:
            scan = {"session": session, "status": "SIGNALS" if signals else "NO_SIGNAL", "signals": len(signals)}
            self._event(session, "SCAN_" + scan["status"], signals=len(signals))
            self._decide(m, k, uf, signals, session)
        st["last_session_index"], st["last_session"] = k, session
        equity = self._equity(m, k)
        self._event(session, "MARK_TO_CLOSE", equity_usd=_r(equity), positions=len(st["positions"]))
        return scan

    def _decide(self, m, k, uf, signals, session):
        st, spec = self.state, self.spec
        equity = self._equity(m, k)
        busy = {o["n"] for o in st["orders"]} | {p["n"] for p in st["positions"]}
        ranked = []
        for n, invalidation in signals:
            adv = adv_value(m.value[n], m.present[n], k, spec.capacity_window)
            ranked.append((-adv, str(m.tickers[n]), int(n), float(invalidation), adv))
        ranked.sort()  # priority: higher 20-session median traded value first, then ticker
        for rank, (_, ticker, n, invalidation, adv) in enumerate(ranked, 1):
            close = float(m.close[n, k] * uf[n, k])
            plan = plan_order(close, invalidation, adv, equity, spec)
            base = {"ticker": ticker, "signal_session": session, "priority": rank, "plan": plan}
            if n in busy:
                self._event(session, "ORDER_REJECTED", ticker=ticker, outcome="REJECTED_ALREADY_HELD", priority=rank)
                st["closed"].append({**base, "outcome": "REJECTED_ALREADY_HELD"})
                continue
            if plan["outcome"] != "PLANNED":
                self._event(session, "ORDER_REJECTED", ticker=ticker, outcome=plan["outcome"], priority=rank,
                            reason=plan["reason"])
                st["closed"].append({**base, "outcome": plan["outcome"]})
                continue
            per_share = reservation_per_share(plan["entry_limit"], plan["invalidation"])
            affordable = int(math.floor(st["cash_usd"] / per_share + 1e-9))
            shares = min(plan["shares"], affordable)
            if shares < 1:
                self._event(session, "ORDER_REJECTED", ticker=ticker, outcome="REJECTED_INSUFFICIENT_CASH",
                            priority=rank, needed_per_share_usd=_r(per_share))
                st["closed"].append({**base, "outcome": "REJECTED_INSUFFICIENT_CASH"})
                continue
            reserved = shares * per_share
            st["cash_usd"] -= reserved
            order = {**base, "n": n, "signal_index": k, "shares_ordered": shares,
                     "cash_limited": shares < plan["shares"], "reserved_usd": reserved,
                     "planned_risk_usd": shares * plan["risk_per_share"],
                     "planned_account_risk": shares * plan["risk_per_share"] / equity,
                     "order": {"type": "BUY LIMIT ON OPEN", "limit": plan["entry_limit"],
                               "submitted": "before the open of the next session",
                               "expires": "unfilled remainder cancelled after the opening print",
                               "attached_stop": plan["invalidation"]}}
            st["orders"].append(order)
            busy.add(n)
            self._event(session, "ORDER_PLACED", ticker=ticker, priority=rank, shares=shares,
                        limit=plan["entry_limit"], stop=plan["invalidation"], reserved_usd=_r(reserved),
                        cash_limited=order["cash_limited"], binding_limit=plan["binding_limit"])

    def _open_fill(self, m, k, uf, o, session):
        st, spec = self.state, self.spec
        n, s = o["n"], o["signal_index"]
        st["orders"].remove(o)
        st["cash_usd"] += o["reserved_usd"]  # released; the fill is debited below
        conv = uf[n, s] / uf[n, k]           # signal-session shares -> session-k shares (split at the open)
        limit_k, stop_k = o["plan"]["entry_limit"] / conv, o["plan"]["invalidation"] / conv
        planned_k = int(math.floor(o["shares_ordered"] * conv + 1e-9))
        opened = m.open[n, k] * uf[n, k] if m.present[n, k] and np.isfinite(m.open[n, k]) else float("nan")
        vol_k = np.nan_to_num(m.volume[n, k]) / uf[n, k] if m.present[n, k] else 0.0
        rec = {**{x: o[x] for x in ("ticker", "signal_session", "priority", "plan", "shares_ordered",
                                    "cash_limited", "reserved_usd", "planned_risk_usd", "planned_account_risk",
                                    "order")},
               "entry_session": session, "units_conversion_at_entry": conv,
               "limit_at_entry_units": limit_k, "stop_at_entry_units": stop_k, "planned_shares_at_entry_units": planned_k,
               "open_as_traded": None if not np.isfinite(opened) else opened, "entry_session_volume": vol_k}
        if not (np.isfinite(opened) and opened > 0 and vol_k > 0):
            outcome, reason = "UNFILLED_NOT_TRADED", "no opening print on the entry session"
        elif opened > limit_k * (1 + 1e-9):
            outcome = "UNFILLED_OPEN_ABOVE_LIMIT"
            reason = (f"open {opened:g} above the limit {limit_k:g}: the stop at {stop_k:g} would be "
                      f"{(opened - stop_k) / opened:.2%} away")
        else:
            bound = int(math.floor(spec.fill_participation * vol_k + 1e-9))
            filled = min(planned_k, bound)
            if filled < 1:
                outcome, reason = "UNFILLED_NO_LIQUIDITY", (f"{spec.fill_participation:.0%} of the session's "
                                                            f"{vol_k:,.0f} shares is below one share")
            else:
                outcome = "FILLED" if filled == planned_k else "PARTIAL"
                reason = None if outcome == "FILLED" else (f"bound {bound:,} shares = {spec.fill_participation:.0%} "
                                                           f"of the session's {vol_k:,.0f}")
        if outcome not in ("FILLED", "PARTIAL"):
            self._event(session, "ORDER_" + outcome, ticker=o["ticker"], reason=reason)
            st["closed"].append({**rec, "outcome": outcome, "reason": reason})
            return
        c_in = cost_rate(opened, "buy")
        debit = filled * opened * (1 + c_in)
        st["cash_usd"] -= debit
        pos = {**rec, "outcome": outcome, "reason": reason, "fill_evidence": FILL_EVIDENCE, "n": n,
               "entry_index": k, "shares_filled": filled, "entry_price": opened, "entry_cost_rate": c_in,
               "entry_debit_usd": debit, "qty_adj": filled * uf[n, k], "stop_adj": stop_k / uf[n, k],
               "stop_distance_at_fill": (opened - stop_k) / opened,
               # Loss planned at this fill if the stop fills at its level: the distance (none when the open
               # is already at or below the stop) plus the round-trip costs.
               "planned_risk_at_fill_usd": filled * (max(opened - stop_k, 0.0)
                                                     + opened * (c_in + cost_rate(min(opened, stop_k), "sell")))}
        st["positions"].append(pos)
        self._event(session, "ORDER_" + outcome, ticker=o["ticker"], shares=filled, price=opened,
                    cost_rate=_r(c_in), debit_usd=_r(debit), stop=stop_k, reason=reason)

    def _exit_check(self, m, k, uf, p, session):
        st, spec = self.state, self.spec
        n, e = p["n"], p["entry_index"]
        if not (m.present[n, k] and np.isfinite(m.close[n, k])):
            return  # no trading: neither the stop nor the time exit can fill
        held = k - e + 1  # market sessions, the entry session counting as 1
        stop_adj = p["stop_adj"]
        if k == e and m.open[n, k] <= stop_adj:
            # The limit-on-open filled at an open at or below the stop; the attached stop triggers at
            # once. Assumed: it sells at that open (the post-auction price is not in a daily bar).
            reason, px_adj = "STOP_AT_OPEN_ON_ENTRY", m.open[n, k]
        elif k > e and np.isfinite(m.open[n, k]) and m.open[n, k] <= stop_adj:
            reason, px_adj = "STOP_GAP_AT_OPEN", m.open[n, k]
        elif np.isfinite(m.low[n, k]) and m.low[n, k] <= stop_adj:
            reason, px_adj = "STOP", stop_adj * (1 - spec.stop_slippage)
        elif held >= spec.max_hold_sessions:
            reason = "TIME_EXIT_AT_CLOSE" if held == spec.max_hold_sessions else "TIME_EXIT_ROLLED"
            px_adj = m.close[n, k]
        else:
            return
        shares_k = p["qty_adj"] / uf[n, k]  # same holding in session-k shares
        px = float(px_adj * uf[n, k])
        c_out = cost_rate(px, "sell")
        proceeds = shares_k * px * (1 - c_out)
        st["cash_usd"] += proceeds
        st["positions"].remove(p)
        pnl = proceeds - p["entry_debit_usd"]
        loss_beyond_plan = max(0.0, -pnl - p["planned_risk_at_fill_usd"])
        closed = {**{x: p[x] for x in p if x not in ("n", "qty_adj", "stop_adj")}, "exit_session": session,
                  "sessions_held": held, "exit_reason": reason, "shares_at_exit": shares_k, "exit_price": px,
                  "exit_cost_rate": c_out, "exit_proceeds_usd": proceeds, "net_pnl_usd": pnl,
                  "net_return": pnl / p["entry_debit_usd"], "realized_loss_beyond_planned_risk_usd": loss_beyond_plan}
        st["closed"].append(closed)
        self._event(session, "EXIT_" + reason, ticker=p["ticker"], shares=shares_k, price=px, cost_rate=_r(c_out),
                    proceeds_usd=_r(proceeds), net_pnl_usd=_r(pnl),
                    loss_beyond_planned_risk_usd=_r(loss_beyond_plan))


# -- the two drivers ---------------------------------------------------------------------------------------

def replay(m, signals_by_index: dict, k0: int, k1: int, spec: ContractSpec = SPEC,
           permitted: tuple[str, str] | None = None) -> Account:
    """Historical replay of sessions k0..k1 on a stored panel. `signals_by_index` maps a session index
    to [(ticker index, invalidation)] computed causally from data through that session.
    `permitted`: the research window the evidence may use; a session outside it is refused."""
    _check_window(m, k0, k1, permitted)
    acc = Account(spec)
    for k in range(k0, k1 + 1):
        s = signals_by_index.get(k, [])
        acc.step(m, k, s)
    return acc


def forward_step(state: dict | None, m_through_today, signals, expected_session: str,
                 spec: ContractSpec = SPEC) -> tuple[dict, dict]:
    """Forward paper scoring for one day: the saved state (JSON), the data available today (its last
    column is the latest session), today's signals or a ScanFailed. Returns (new state, scan record).
    A failed scan (stale or missing data) leaves orders and positions untouched and is recorded."""
    acc = Account(spec, json.loads(json.dumps(state)) if state is not None else None)
    k = m_through_today.shape[1] - 1
    last = str(m_through_today.dates[k])
    # Sessions the scan missed: the broker still worked the orders and stops, so fills and exits are
    # processed from the data now available, but no decision is made for a session without a scan.
    for gap in range(acc.state["last_session_index"] + 1, k) if acc.state["last_session_index"] >= 0 else ():
        acc.step(m_through_today, gap, ScanFailed(f"MISSED: no scan ran after the close of {m_through_today.dates[gap]}"))
    if last != expected_session:
        st = acc.state
        st["events"].append({"session": expected_session, "event": "SCAN_FAILED",
                             "reason": f"STALE_DATA: the data ends at {last}", "cash_usd": _r(st["cash_usd"]),
                             "reserved_usd": _r(sum(o["reserved_usd"] for o in st["orders"]))})
        return json.loads(json.dumps(st, default=float)), {"session": expected_session, "status": "FAILED",
                                                           "reason": f"STALE_DATA: the data ends at {last}"}
    scan = acc.step(m_through_today, k, signals, expected_session)
    return json.loads(json.dumps(acc.state, default=float)), scan


def _check_window(m, k0, k1, permitted):
    if permitted is None:
        return
    lo, hi = str(m.dates[k0]), str(m.dates[k1])
    if lo < permitted[0] or hi > permitted[1]:
        raise ValueError(f"sessions {lo}..{hi} fall outside the permitted research window "
                         f"{permitted[0]}..{permitted[1]}")

"""EXEC-US-v2.1: one trading contract for US daily-bar strategies, account included.

Historical replay and forward paper scoring both drive `Account.step`, one session at a time, on
data through that session only. Replay calls it over a stored panel. Forward scoring calls it each
day on the data downloaded that day, with the account state saved as JSON between calls.
The trading rules live only in `step`, so the same inputs give the same orders, fills, exits and
balances in both modes. The specification, with every assumption, is
research/EXEC_US_v2_1/CONTRACT.md; a change to any rule here is a new CONTRACT_VERSION.

Saved state never depends on how a download is laid out:
  * names are identified by ticker, sessions by date (never by row or column number), so a later
    download with other row order or a rolling date window resolves to the same instruments;
  * quantities and prices are stored AS TRADED in a named session and carried to the next session
    through the split ratio F[from] / F[to] of the current download. The adjusted-price basis of
    any download (which a provider changes after every split) is never stored.

v2 (commit 21eb6aa) stored row and column numbers and adjusted-basis quantities, sized with the
exit cost at the entry price's tier, and let exits fill on sessions without trades; v2.1 fixes all
four (research/EXEC_US_v2_1/README.md). Legacy execution is untouched: EXEC-US-v1 (exec_us.py,
PAPER-POLICY-v4) and the backtest fill models A, B, B2 and C (execution.py).

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

from .exec_us import US, cost_rate, floor_tick, tick

CONTRACT_VERSION = "EXEC-US-v2.1"

SCAN_STATUSES = ("SIGNALS", "NO_SIGNAL", "FAILED")
ORDER_OUTCOMES = (
    "REJECTED_NO_PLAN",            # at the decision: no entry both above the stop and within the 5% and chase limits
    "REJECTED_SIZE_ZERO",          # at the decision: no whole share fits risk, capital and liquidity limits
    "REJECTED_INSUFFICIENT_CASH",  # at the decision: unreserved cash does not cover one share
    "REJECTED_ALREADY_HELD",       # at the decision: the name is held or has an order working
    "UNFILLED_NOT_TRADED",         # at the entry open: no opening print / no trades that session / not in the data
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


# -- prices and costs ----------------------------------------------------------------------------------------

def _band_prices(low: float, high: float) -> list[float]:
    """Prices in (low, high] where buy value p x (1 + cost(p)) can peak: `high` and, below each cost
    tier boundary inside the band, the last tick under it (cost tiers rise as the price falls)."""
    out = [high]
    for bound, _ in US.cost_tiers:
        if low < bound <= high:
            below = floor_tick(bound - tick(bound - 1e-9))
            if below > low:
                out.append(below)
    return out


def risk_per_share(limit: float, stop: float) -> float:
    """Worst planned loss per share: a fill anywhere in (stop, limit] at its buy cost, sold at the
    stop at the stop's sell cost (the exit tier is the stop's, not the entry's). Gaps excluded."""
    proceeds = stop * (1 - cost_rate(stop, "sell"))
    return max(p * (1 + cost_rate(p, "buy")) for p in _band_prices(stop, limit)) - proceeds


def reservation_per_share(entry_limit: float, stop: float) -> float:
    """Cash held per planned share until the open: the most any fill inside the band can cost."""
    return max(p * (1 + cost_rate(p, "buy")) for p in _band_prices(stop, entry_limit))


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
    rps = risk_per_share(limit, stop)
    by_risk = spec.risk_fraction * equity / rps
    by_capital = spec.max_position_fraction * equity / limit
    by_liquidity = spec.plan_participation * adv_usd / limit
    shares = int(math.floor(min(by_risk, by_capital, by_liquidity) + 1e-9))
    binding = min((by_risk, "risk"), (by_capital, "capital"), (by_liquidity, "liquidity"))[1]
    plan.update(stop_distance_at_limit=(limit - stop) / limit, risk_per_share=rps,
                exit_cost_at_stop=cost_rate(stop, "sell"),
                shares_by_risk=by_risk, shares_by_capital=by_capital, shares_by_liquidity=by_liquidity,
                binding_limit=binding, shares=shares)
    if shares < 1:
        return {**plan, "outcome": "REJECTED_SIZE_ZERO", "reason": f"no whole share fits ({binding} binds)"}
    return {**plan, "outcome": "PLANNED"}


def _r(x: float) -> float:
    return round(float(x), 6)


# -- one download, read by identity --------------------------------------------------------------------------

class _Data:
    """A download read by ticker and date. Column k is the session being processed; nothing after it
    is read. Prices are returned as traded in their own session."""

    def __init__(self, m, k: int):
        self.m, self.k = m, k
        self.row = {str(t): i for i, t in enumerate(m.tickers)}
        self.col = {str(d): j for j, d in enumerate(m.dates[: k + 1])}
        self.uf = m.unit_factor if m.unit_factor is not None else np.ones(m.shape)

    def n(self, ticker: str):
        return self.row.get(ticker)

    def traded(self, n, j=None) -> bool:
        """Listed, with trades (volume > 0) and a finite close: only then can an order fill."""
        j = self.k if j is None else j
        m = self.m
        return (n is not None and bool(m.present[n, j]) and np.isfinite(m.close[n, j]) and m.close[n, j] > 0
                and np.nan_to_num(m.volume[n, j]) > 0)

    def px(self, field: str, n, j=None) -> float:
        j = self.k if j is None else j
        return float(getattr(self.m, field)[n, j] * self.uf[n, j])

    def to_today(self, n, session: str) -> float:
        """Shares held at `session` x this ratio = the same holding in today's shares (F[from] / F[k]).
        Raises if the download lacks the session: the units then cannot be established."""
        j = self.col.get(session)
        if j is None:
            raise ScanFailed(f"MISSING_HISTORY: the data does not contain {session}, needed to carry units")
        return float(self.uf[n, j] / self.uf[n, self.k])


class Account:
    """The account state is a plain dict, so forward scoring can save it as JSON between sessions."""

    def __init__(self, spec: ContractSpec = SPEC, state: dict | None = None):
        self.spec = spec
        self.state = copy.deepcopy(state) if state is not None else {
            "contract": spec.record(), "contract_sha256": spec.sha256(), "cash_usd": spec.starting_cash_usd,
            "orders": [], "positions": [], "closed": [], "events": [], "last_session": None}
        if self.state["contract_sha256"] != spec.sha256():
            raise ValueError("state was made under another contract; a contract change is a new version")

    def _event(self, session: str, kind: str, **kw):
        self.state["events"].append({"session": session, "event": kind, **kw,
                                     "cash_usd": _r(self.state["cash_usd"]),
                                     "reserved_usd": _r(sum(o["reserved_usd"] for o in self.state["orders"]))})

    def equity(self, data: _Data) -> float:
        """Cash + reservations + positions at the last traded close in this download (as traded today)."""
        total = self.state["cash_usd"] + sum(o["reserved_usd"] for o in self.state["orders"])
        for p in self.state["positions"]:
            n = data.n(p["ticker"])
            if n is None:
                total += p["shares"] * p["last_close"]
                continue
            j = next((j for j in range(data.k, -1, -1) if data.traded(n, j)), None)
            # adjusted close of session j x F today = that close expressed in today's shares
            total += p["shares"] * (float(data.m.close[n, j] * data.uf[n, data.k]) if j is not None
                                    else p["last_close"])
        return total

    # -- one session -------------------------------------------------------------------------------------
    def step(self, m, k: int, signals, expected_session: str | None = None) -> dict:
        """Process session k of a download holding data through k at least (later columns are never
        read). `signals` is [(row in this download, invalidation as traded at k)] from data through k,
        or a ScanFailed. Inside the session: entry orders at the open, then exits, then the decisions
        after the close."""
        st = self.state
        session = str(m.dates[k])
        if st["last_session"] is not None and session <= st["last_session"]:
            raise ValueError(f"session {session} already processed (last: {st['last_session']})")
        if expected_session is not None and session != expected_session:
            raise ScanFailed(f"STALE_DATA: the data ends at {session}, the scan expects {expected_session}")
        data = _Data(m, k)
        for o in list(st["orders"]):
            self._open_fill(data, o, session)
        for p in list(st["positions"]):
            self._hold(data, p, session)
        if isinstance(signals, ScanFailed):
            scan = {"session": session, "status": "FAILED", "reason": str(signals), "signals": 0}
            self._event(session, "SCAN_FAILED", reason=str(signals))
        else:
            scan = {"session": session, "status": "SIGNALS" if signals else "NO_SIGNAL", "signals": len(signals)}
            self._event(session, "SCAN_" + scan["status"], signals=len(signals))
            self._decide(data, signals, session)
        st["last_session"] = session
        self._event(session, "MARK_TO_CLOSE", equity_usd=_r(self.equity(data)), positions=len(st["positions"]))
        return scan

    def _decide(self, data: _Data, signals, session):
        st, spec, m, k = self.state, self.spec, data.m, data.k
        equity = self.equity(data)
        busy = {o["ticker"] for o in st["orders"]} | {p["ticker"] for p in st["positions"]}
        ranked = []
        for n, invalidation in signals:
            adv = adv_value(m.value[n], m.present[n], k, spec.capacity_window)
            ranked.append((-adv, str(m.tickers[n]), int(n), float(invalidation), adv))
        ranked.sort()  # priority: higher 20-session median traded value first, then ticker
        for rank, (_, ticker, n, invalidation, adv) in enumerate(ranked, 1):
            plan = plan_order(data.px("close", n), invalidation, adv, equity, spec)
            base = {"ticker": ticker, "signal_session": session, "priority": rank, "plan": plan}
            if ticker in busy:
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
            order = {**base, "shares_ordered": shares, "cash_limited": shares < plan["shares"],
                     "reserved_usd": reserved, "planned_risk_usd": shares * plan["risk_per_share"],
                     "planned_account_risk": shares * plan["risk_per_share"] / equity,
                     "order": {"type": "BUY LIMIT ON OPEN", "limit": plan["entry_limit"],
                               "submitted": "before the open of the next session",
                               "expires": "unfilled remainder cancelled after the opening print",
                               "attached_stop": plan["invalidation"]}}
            st["orders"].append(order)
            busy.add(ticker)
            self._event(session, "ORDER_PLACED", ticker=ticker, priority=rank, shares=shares,
                        limit=plan["entry_limit"], stop=plan["invalidation"], reserved_usd=_r(reserved),
                        cash_limited=order["cash_limited"], binding_limit=plan["binding_limit"])

    def _open_fill(self, data: _Data, o, session):
        st, spec, m, k = self.state, self.spec, data.m, data.k
        st["orders"].remove(o)
        st["cash_usd"] += o["reserved_usd"]  # released; the fill is debited below
        n = data.n(o["ticker"])
        rec = {**{x: o[x] for x in ("ticker", "signal_session", "priority", "plan", "shares_ordered",
                                    "cash_limited", "reserved_usd", "planned_risk_usd", "planned_account_risk",
                                    "order")}, "entry_session": session}
        if n is None:
            outcome, reason = "UNFILLED_NOT_TRADED", "the name is not in the data for the entry session"
            self._event(session, "ORDER_" + outcome, ticker=o["ticker"], reason=reason)
            st["closed"].append({**rec, "outcome": outcome, "reason": reason})
            return
        conv = data.to_today(n, o["signal_session"])   # signal-session shares -> entry-session shares
        limit_k, stop_k = o["plan"]["entry_limit"] / conv, o["plan"]["invalidation"] / conv
        planned_k = int(math.floor(o["shares_ordered"] * conv + 1e-9))
        traded = data.traded(n) and np.isfinite(m.open[n, k]) and m.open[n, k] > 0
        opened = data.px("open", n) if traded else float("nan")
        vol_k = float(np.nan_to_num(m.volume[n, k]) / data.uf[n, k]) if m.present[n, k] else 0.0
        rec.update(units_conversion_at_entry=conv, limit_at_entry_units=limit_k, stop_at_entry_units=stop_k,
                   planned_shares_at_entry_units=planned_k, open_as_traded=opened if traded else None,
                   entry_session_volume=vol_k)
        if not traded:
            outcome, reason = "UNFILLED_NOT_TRADED", "no opening print or no trades on the entry session"
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
        exit_ref = min(opened, stop_k)  # the stop, or the open itself when the open is at or below the stop
        pos = {**rec, "outcome": outcome, "reason": reason, "fill_evidence": FILL_EVIDENCE,
               "shares_filled": filled, "entry_price": opened, "entry_cost_rate": c_in, "entry_debit_usd": debit,
               "stop_distance_at_fill": (opened - stop_k) / opened,
               # loss planned at this fill if the stop fills at its level, costs at each side's own tier
               "planned_risk_at_fill_usd": filled * (opened * (1 + c_in) - exit_ref * (1 - cost_rate(exit_ref, "sell"))),
               # carried state, as traded in `units_session`
               "shares": float(filled), "stop": stop_k, "units_session": session, "sessions_held": 0,
               "last_close": data.px("close", n)}
        st["positions"].append(pos)
        self._event(session, "ORDER_" + outcome, ticker=o["ticker"], shares=filled, price=opened,
                    cost_rate=_r(c_in), debit_usd=_r(debit), stop=stop_k, reason=reason)

    def _hold(self, data: _Data, p, session):
        """Carry a position into this session (split ratio from the last session it was carried to),
        then check its exits. A session without trades fills nothing; the hold still counts it."""
        st, spec = self.state, self.spec
        n = data.n(p["ticker"])
        p["sessions_held"] += 1
        if n is None:
            self._event(session, "POSITION_NOT_IN_DATA", ticker=p["ticker"])
            return
        conv = data.to_today(n, p["units_session"])
        p["shares"], p["stop"], p["units_session"] = p["shares"] * conv, p["stop"] / conv, session
        if not data.traded(n):
            return
        p["last_close"] = data.px("close", n)
        stop, first = p["stop"], session == p["entry_session"]
        o, lo, c = data.px("open", n), data.px("low", n), data.px("close", n)
        if first and np.isfinite(o) and o <= stop:
            # The limit-on-open filled at an open at or below the stop; the attached stop triggers at
            # once. Assumed: it sells at that open (the post-auction price is not in a daily bar).
            reason, px = "STOP_AT_OPEN_ON_ENTRY", o
        elif not first and np.isfinite(o) and o <= stop:
            reason, px = "STOP_GAP_AT_OPEN", o
        elif np.isfinite(lo) and lo <= stop:
            reason, px = "STOP", stop * (1 - spec.stop_slippage)
        elif p["sessions_held"] >= spec.max_hold_sessions:
            reason = "TIME_EXIT_AT_CLOSE" if p["sessions_held"] == spec.max_hold_sessions else "TIME_EXIT_ROLLED"
            px = c
        else:
            return
        c_out = cost_rate(px, "sell")
        proceeds = p["shares"] * px * (1 - c_out)
        st["cash_usd"] += proceeds
        st["positions"].remove(p)
        pnl = proceeds - p["entry_debit_usd"]
        loss_beyond_plan = max(0.0, -pnl - p["planned_risk_at_fill_usd"])
        closed = {**{x: p[x] for x in p if x not in ("shares", "stop", "units_session", "last_close")},
                  "exit_session": session, "exit_reason": reason, "shares_at_exit": p["shares"], "exit_price": px,
                  "stop_at_exit_units": p["stop"], "exit_cost_rate": c_out, "exit_proceeds_usd": proceeds,
                  "net_pnl_usd": pnl, "net_return": pnl / p["entry_debit_usd"],
                  "realized_loss_beyond_planned_risk_usd": loss_beyond_plan}
        st["closed"].append(closed)
        self._event(session, "EXIT_" + reason, ticker=p["ticker"], shares=p["shares"], price=px, cost_rate=_r(c_out),
                    proceeds_usd=_r(proceeds), net_pnl_usd=_r(pnl), loss_beyond_planned_risk_usd=_r(loss_beyond_plan))


# -- the two drivers ---------------------------------------------------------------------------------------

def replay(m, signals_by_index: dict, k0: int, k1: int, spec: ContractSpec = SPEC,
           permitted: tuple[str, str] | None = None) -> Account:
    """Historical replay of sessions k0..k1 on a stored panel. `signals_by_index` maps a session index
    to [(ticker index, invalidation)] computed causally from data through that session.
    `permitted`: the research window the evidence may use; a session outside it is refused."""
    _check_window(m, k0, k1, permitted)
    acc = Account(spec)
    for k in range(k0, k1 + 1):
        acc.step(m, k, signals_by_index.get(k, []))
    return acc


def _canonical(state: dict) -> dict:
    return json.loads(json.dumps(state, default=float))


def forward_step(state: dict | None, m_today, signals, expected_session: str,
                 spec: ContractSpec = SPEC) -> tuple[dict, dict]:
    """Forward paper scoring for one day: the saved state (JSON), today's download (its last column is
    the latest session; any row order, any start date), today's signals or a ScanFailed. Returns
    (new state, scan record). A failed scan leaves orders and positions untouched and is recorded."""
    acc = Account(spec, _canonical(state) if state is not None else None)
    st = acc.state
    k = m_today.shape[1] - 1
    last = str(m_today.dates[k])

    def failed(reason):
        st["events"].append({"session": expected_session, "event": "SCAN_FAILED", "reason": reason,
                             "cash_usd": _r(st["cash_usd"]),
                             "reserved_usd": _r(sum(o["reserved_usd"] for o in st["orders"]))})
        return _canonical(st), {"session": expected_session, "status": "FAILED", "reason": reason}

    if last != expected_session:
        return failed(f"STALE_DATA: the data ends at {last}")
    dates = [str(d) for d in m_today.dates]
    if st["last_session"] is not None and st["last_session"] not in dates:
        return failed(f"MISSING_HISTORY: the data starts after {st['last_session']}, the last session processed")
    # Sessions the scan missed: the broker still worked the orders and stops, so fills and exits are
    # processed from the data now available, but no decision is made for a session without a scan.
    start = dates.index(st["last_session"]) + 1 if st["last_session"] is not None else k
    for gap in range(start, k):
        acc.step(m_today, gap, ScanFailed(f"MISSED: no scan ran after the close of {dates[gap]}"))
    scan = acc.step(m_today, k, signals, expected_session)
    return _canonical(acc.state), scan


def _check_window(m, k0, k1, permitted):
    if permitted is None:
        return
    lo, hi = str(m.dates[k0]), str(m.dates[k1])
    if lo < permitted[0] or hi > permitted[1]:
        raise ValueError(f"sessions {lo}..{hi} fall outside the permitted research window "
                         f"{permitted[0]}..{permitted[1]}")

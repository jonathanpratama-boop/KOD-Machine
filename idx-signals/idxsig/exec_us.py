"""EXEC-US-v1: the one execution model for US daily-bar strategies.

Historical replay (`replay`) and paper scoring (`paper.score` for PAPER-POLICY-v5 decisions) both
call `make_plan` and `execute` below, so the same bars give the same entry, rejection, exit and net
result in both. A change to any rule here is a new EXEC_VERSION; records keep the version they
were made under.

Timeline (s = signal session, e = s + 1 = entry session)
  * The condition is computed from completed bars through the close of s. Nothing is bought at
    that close: a condition discovered from a closing price is acted on at the next achievable
    price, the opening print of e.
  * At the decision (after the close of s) the plan is fixed, in the as-traded units of s:
      1. invalidation (stop) first, supplied by the strategy and floored to the tick;
      2. max_entry = the highest entry whose stop distance is at most `max_stop_distance` (5%):
         floor((stop / (1 - 0.05)) to the tick), and never above signal close x (1 + chase_limit);
      3. size from that permitted entry (the worst fill the order accepts):
         risk/share = (max_entry - stop) + max_entry x (entry cost + exit cost) at max_entry,
         shares = floor(min(risk_fraction x equity / risk/share,
                            max_position_fraction x equity / max_entry,
                            max_participation x capacity))
         where capacity is FILL-B-v2: the median volume of the 20 sessions through s, all in the
         same (signal-session) share units, a listed session without trades counting as 0.
  * Entry order: buy `shares` at the opening print of e, limit max_entry, valid for that print
    only. It is rejected (never filled later) if e has no bar with volume and an open, if the
    open is above max_entry (the stop would be wider than 5% at that price: STOP_TOO_WIDE), or if
    the open is at or below the stop.
  * After the fill a resting sell-stop sits at the stop. In each held session k (from e): if k > e
    and the open is at or below the stop, it fills at the open (gap through); otherwise if the low
    reaches the stop, it fills at the stop. The stop is an order submitted in advance, so its fill
    is achievable; it is not a close observed after the fact. No slippage beyond the stop level is
    modelled (labelled).
  * Time exit: a market-on-close order for the close of session e + exit_after_sessions, known in
    advance, so that closing fill is achievable (rolled to the next traded session if that one did
    not trade; a name that stops trading is closed at its last traded close, labelled).
  * Costs: profiles.US fees plus the price-tier cost at the as-traded price of each fill.
  * Units: prices and shares are converted between sessions by the unit factor F (as-traded =
    adjusted x F). Returns come from the adjusted series, so a split during the hold changes
    nothing but share counts and cost tiers.
  * Excursions: `close_excursion` (closes only) and `intraday_excursion` (highs/lows) are
    descriptive and kept apart from the executable net return.

The hypothetical account (equity, risk fraction, caps) is part of the spec and is printed in
every plan, because the real budget is unknown.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

import numpy as np

from .profiles import PROFILES

EXEC_VERSION = "EXEC-US-v1"
STATUSES = ("FILLED", "REJECTED_NO_PLAN", "REJECTED_NOT_TRADED", "REJECTED_STOP_TOO_WIDE",
            "REJECTED_AT_OR_BELOW_STOP", "PENDING")


@dataclass(frozen=True)
class ExecSpec:
    max_stop_distance: float = 0.05      # Jonathan's constraint: stop at most 5% below the permitted entry
    chase_limit: float = 0.10            # and no entry above signal close x 1.10
    exit_after_sessions: int = 5         # market-on-close exit at the close of entry session + 5
    equity_usd: float = 10_000.0         # hypothetical account
    risk_fraction: float = 0.01          # 1% of equity at risk at the stop (gap risk excluded)
    max_position_fraction: float = 0.20  # at most 20% of equity in one name
    max_participation: float = 0.10      # at most 10% of FILL-B-v2 capacity
    capacity_window: int = 20

    def record(self) -> dict:
        return {"exec_version": EXEC_VERSION, **asdict(self)}

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.record(), sort_keys=True).encode()).hexdigest()


SPEC = ExecSpec()
US = PROFILES["US"]


def tick(price: float) -> float:
    return 0.01 if price >= 1 else 0.0001


def floor_tick(price: float) -> float:
    t = tick(price)
    return round(math.floor(price / t + 1e-9) * t, 6)


def cost_rate(price_as_traded: float, side: str) -> float:
    fee = US.fee_buy if side == "buy" else US.fee_sell
    return float(fee + US.per_side_cost(np.array([price_as_traded]))[0])


def capacity_shares(volume_adj: np.ndarray, present: np.ndarray, uf: np.ndarray, s: int, window: int = 20) -> float:
    """FILL-B-v2 at the decision: median of the `window` sessions through s, each session's adjusted
    volume put into the signal session's share units (/ F[s]); listed sessions without trades count
    as zero, sessions before listing are ignored."""
    a = max(s - window + 1, 0)
    listed = present[a: s + 1]
    if not listed.any():
        return 0.0
    return float(np.median(np.nan_to_num(volume_adj[a: s + 1])[listed] / uf[s]))


def make_plan(signal_close: float, invalidation: float, capacity: float, spec: ExecSpec = SPEC) -> dict:
    """The decision-time plan in signal-session as-traded units. Rejected plans carry a reason."""
    stop = floor_tick(invalidation)
    by_stop = floor_tick(stop / (1 - spec.max_stop_distance))
    by_chase = floor_tick(signal_close * (1 + spec.chase_limit))
    max_entry = min(by_stop, by_chase)
    plan = {"exec_version": EXEC_VERSION, "spec_sha256": spec.sha256(), "signal_close": signal_close,
            "invalidation": stop, "max_entry_by_stop_rule": by_stop, "max_entry_by_chase_rule": by_chase,
            "max_entry": max_entry, "capacity_shares": capacity,
            "account": {"equity_usd": spec.equity_usd, "risk_fraction": spec.risk_fraction,
                        "max_position_fraction": spec.max_position_fraction,
                        "max_participation": spec.max_participation, "note": "hypothetical account"}}
    if not stop > 0 or max_entry <= stop:
        return {**plan, "status": "REJECTED_NO_PLAN", "reason": "no entry price is both above the stop and within "
                                                                  "the 5% stop rule and the chase limit"}
    c_in, c_out = cost_rate(max_entry, "buy"), cost_rate(max_entry, "sell")
    risk_per_share = (max_entry - stop) + max_entry * (c_in + c_out)
    by_risk = spec.risk_fraction * spec.equity_usd / risk_per_share
    by_capital = spec.max_position_fraction * spec.equity_usd / max_entry
    by_liquidity = spec.max_participation * capacity
    shares = int(math.floor(min(by_risk, by_capital, by_liquidity) + 1e-9))
    plan.update(stop_distance_at_max_entry=(max_entry - stop) / max_entry, cost_in_at_max_entry=c_in,
                cost_out_at_max_entry=c_out, risk_per_share=risk_per_share,
                shares_by_risk=by_risk, shares_by_capital=by_capital, shares_by_liquidity=by_liquidity,
                shares=shares, max_planned_loss_usd=round(shares * risk_per_share, 2),
                position_at_max_entry_usd=round(shares * max_entry, 2))
    if shares < 1:
        return {**plan, "status": "REJECTED_NO_PLAN", "reason": "no whole share fits the risk, capital and "
                                                                  "liquidity limits"}
    return {**plan, "status": "PLANNED"}


def execute(o, h, lo, c, v, present, uf, s: int, plan: dict, spec: ExecSpec = SPEC) -> dict:
    """Run one plan on one name's adjusted bars (arrays over the same sessions). `s` is the signal
    session index; the plan's prices are in session s's as-traded units."""
    out = {"exec_version": EXEC_VERSION, "spec_sha256": spec.sha256()}
    if plan.get("status") != "PLANNED":
        return {**out, "status": "REJECTED_NO_PLAN", "reason": plan.get("reason")}
    n = len(c)
    e = s + 1
    if e >= n:
        return {**out, "status": "PENDING", "reason": "entry session not in the data yet"}
    to_adj = 1.0 / uf[s]                     # signal-session as-traded -> adjusted
    stop_adj, max_adj = plan["invalidation"] * to_adj, plan["max_entry"] * to_adj
    if not (present[e] and np.isfinite(o[e]) and o[e] > 0 and np.nan_to_num(v[e]) > 0):
        return {**out, "status": "REJECTED_NOT_TRADED", "entry_session_index": e,
                "reason": "no opening print on the entry session"}
    open_traded = o[e] * uf[e]
    stop_e, max_e = stop_adj * uf[e], max_adj * uf[e]
    if o[e] > max_adj * (1 + 1e-12):
        dist = (open_traded - stop_e) / open_traded
        return {**out, "status": "REJECTED_STOP_TOO_WIDE", "entry_session_index": e, "open_as_traded": open_traded,
                "max_entry_as_traded": max_e, "stop_as_traded": stop_e, "stop_distance_at_open": dist,
                "reason": f"open {open_traded:g} is above the permitted entry {max_e:g}: the stop at {stop_e:g} "
                          f"would be {dist:.2%} away, more than {spec.max_stop_distance:.0%}"}
    if o[e] <= stop_adj:
        return {**out, "status": "REJECTED_AT_OR_BELOW_STOP", "entry_session_index": e, "open_as_traded": open_traded,
                "stop_as_traded": stop_e, "reason": "the open is at or below the invalidation level"}
    shares_e = int(math.floor(plan["shares"] * uf[s] / uf[e] + 1e-9))  # same holding after a split at e
    c_in = cost_rate(open_traded, "buy")
    last = e + spec.exit_after_sessions
    exit_k, exit_adj, reason = None, None, None
    for k in range(e, n):
        if not (present[k] and np.isfinite(c[k])):
            continue  # no trading that session: neither the stop nor the time exit can fill
        if k > e and np.isfinite(o[k]) and o[k] <= stop_adj:
            exit_k, exit_adj, reason = k, float(o[k]), "STOP_GAP_AT_OPEN"
            break
        if np.isfinite(lo[k]) and lo[k] <= stop_adj:
            exit_k, exit_adj, reason = k, float(stop_adj), "STOP"
            break
        if k >= last:  # rolls to the next traded session if the planned one did not trade
            exit_k, exit_adj, reason = k, float(c[k]), "TIME_EXIT_AT_CLOSE" if k == last else "TIME_EXIT_ROLLED"
            break
    if exit_k is None:
        if n - 1 < last:
            return {**out, "status": "PENDING", "entry_session_index": e,
                    "reason": "holding period not complete in the data"}
        k = max(i for i in range(e, n) if present[i] and np.isfinite(c[i]))
        exit_k, exit_adj, reason = k, float(c[k]), "DATA_END_LAST_CLOSE"
    exit_traded = exit_adj * uf[exit_k]
    c_out = cost_rate(exit_traded, "sell")
    gross = exit_adj / o[e] - 1
    net = (1 + gross) * (1 - c_out) / (1 + c_in) - 1
    closes = [c[k] / o[e] - 1 for k in range(e, exit_k + 1) if present[k] and np.isfinite(c[k])]
    highs = [h[k] / o[e] - 1 for k in range(e, exit_k + 1) if present[k] and np.isfinite(h[k])]
    lows = [lo[k] / o[e] - 1 for k in range(e, exit_k + 1) if present[k] and np.isfinite(lo[k])]
    entry_value = shares_e * open_traded
    pnl = entry_value * ((1 + gross) * (1 - c_out)) - entry_value * (1 + c_in)
    return {**out, "status": "FILLED", "entry_session_index": e, "exit_session_index": exit_k,
            "entry_price_as_traded": open_traded, "stop_as_traded_at_entry": stop_e,
            "stop_distance_at_entry": (open_traded - stop_e) / open_traded,
            "shares_at_entry": shares_e, "entry_cost_rate": c_in,
            "exit_reason": reason, "exit_price_as_traded": exit_traded, "exit_cost_rate": c_out,
            "gross_return": gross, "net_return": net, "net_pnl_usd": round(pnl, 2),
            "close_excursion": {"max": max(closes), "min": min(closes),
                                "note": "closing prices only; descriptive, not executable"},
            "intraday_excursion": {"max_high": max(highs), "min_low": min(lows),
                                   "note": "daily highs and lows; descriptive, not executable"}}


def run_one(o, h, lo, c, v, present, uf, s: int, invalidation: float, spec: ExecSpec = SPEC) -> dict:
    """Plan at the close of s from bars through s only, then execute."""
    cap = capacity_shares(v, present, uf, s, spec.capacity_window)
    plan = make_plan(float(c[s] * uf[s]), float(invalidation), cap, spec)
    return {"plan": plan, "result": execute(o, h, lo, c, v, present, uf, s, plan, spec)}


def replay(m, signals, invalidation_of, spec: ExecSpec = SPEC) -> list[dict]:
    """Historical replay on an execution.Market with `unit_factor` attached (Market.with_units).
    `signals` is [(ticker index, signal session index)]; `invalidation_of(m, n, s)` returns the
    stop in signal-session as-traded units from data through s."""
    uf_all = m.unit_factor if m.unit_factor is not None else np.ones(m.shape)
    out = []
    for n, s in signals:
        row = run_one(m.open[n], m.high[n], m.low[n], m.close[n], m.volume[n], m.present[n], uf_all[n], s,
                      invalidation_of(m, n, s), spec)
        out.append({"ticker": m.tickers[n], "signal_session": str(m.dates[s]), **row})
    return out


def signal_low_invalidation(m, n, s) -> float:
    """PAPER-POLICY-v5 / MOONSHOT_E2_US_D1 invalidation: the signal session's low, as traded."""
    uf = m.unit_factor[n, s] if m.unit_factor is not None else 1.0
    return float(m.low[n, s] * uf)

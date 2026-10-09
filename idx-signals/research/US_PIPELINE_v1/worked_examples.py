"""Worked examples of EXEC-US-v1 with the full calculation trail.

Picks, deterministically, from the 2023 replay (checks.py must have run): the first profitable
filled trade, the first losing filled trade and the first entry rejected by the 5% rule, among
names not quarantined (by ticker, then date), and adds the $100 / $95 / $110 reference case.
Each is recomputed here from the committed panel with exec_us, and must equal the replay row.

    python3 research/US_PIPELINE_v1/worked_examples.py   ->  WORKED_EXAMPLES.md
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import exec_us, global_panel  # noqa: E402
from idxsig.backtest import _dense  # noqa: E402
from idxsig.execution import Market  # noqa: E402

HERE = Path(__file__).parent
PANEL = ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json"


def money(x):
    return f"${x:,.4f}" if abs(x) < 1 else f"${x:,.2f}"


def trail(title, why, m, n, s, plan, res):
    uf = m.unit_factor[n]
    L = [f"## {title}", "", why, ""]
    L += ["**Decision after the close of the signal session** (data through that close only)", "",
          "| Item | Value | How |", "|---|---|---|",
          f"| Ticker, signal session | {m.tickers[n]}, {m.dates[s]} | MOONSHOT_E2_US_D1 fired at this close |",
          f"| Signal close (as traded) | {money(plan['signal_close'])} | adjusted close x unit factor {uf[s]:g} |",
          f"| 1. Invalidation (first) | {money(plan['invalidation'])} | signal-session low, floored to the cent |",
          f"| 2. Max entry by the 5% rule | {money(plan['max_entry_by_stop_rule'])} | floor(stop / 0.95) |",
          f"| Max entry by the chase limit | {money(plan['max_entry_by_chase_rule'])} | floor(signal close x 1.10) |",
          f"| Permitted entry | {money(plan['max_entry'])} | the lower of the two |"]
    if plan["status"] == "PLANNED":
        a = plan["account"]
        L += [f"| Costs at the permitted entry | buy {plan['cost_in_at_max_entry']:.4%}, sell {plan['cost_out_at_max_entry']:.4%} | fees + price-tier cost |",
              f"| Risk per share | {money(plan['risk_per_share'])} | (entry - stop) + entry x (buy + sell cost) |",
              f"| Shares by risk | {plan['shares_by_risk']:,.2f} | {a['risk_fraction']:.0%} x ${a['equity_usd']:,.0f} / risk per share |",
              f"| Shares by capital | {plan['shares_by_capital']:,.2f} | {a['max_position_fraction']:.0%} x ${a['equity_usd']:,.0f} / permitted entry |",
              f"| Shares by liquidity | {plan['shares_by_liquidity']:,.2f} | {a['max_participation']:.0%} x {plan['capacity_shares']:,.0f} (20-session median volume, signal-session shares) |",
              f"| 3. Shares | {plan['shares']:,} | floor of the smallest |",
              f"| Max planned loss | {money(plan['max_planned_loss_usd'])} | shares x risk per share (gap risk excluded) |"]
    L += ["", "**Execution**", ""]
    e = s + 1
    L += [f"- Entry session {m.dates[e]}: open {money(m.open[n, e] * uf[e])} (as traded), band "
          f"({money(plan['invalidation'])}, {money(plan['max_entry'])}]."]
    if res["status"] != "FILLED":
        L += [f"- **{res['status']}**: {res['reason']}.", "- No later fill. The order was valid for that opening print only.", ""]
        return L
    L += [f"- Filled {res['shares_at_entry']:,} shares at {money(res['entry_price_as_traded'])}; stop distance at the fill "
          f"{res['stop_distance_at_entry']:.2%} (at most 5%); buy cost {res['entry_cost_rate']:.4%}.", "",
          "| Session | Open | High | Low | Close | Stop | Event |", "|---|---|---|---|---|---|---|"]
    stop_adj = plan["invalidation"] / uf[s]
    for k in range(e, res["exit_session_index"] + 1):
        ev = ""
        if k == res["exit_session_index"]:
            ev = f"exit: {res['exit_reason']} at {money(res['exit_price_as_traded'])}"
        elif k == e:
            ev = "entry at the open"
        L.append(f"| {m.dates[k]} | {money(m.open[n, k] * uf[k])} | {money(m.high[n, k] * uf[k])} | "
                 f"{money(m.low[n, k] * uf[k])} | {money(m.close[n, k] * uf[k])} | {money(stop_adj * uf[k])} | {ev} |")
    g = res["gross_return"]
    L += ["", f"- Gross return: exit / entry - 1 = {g:+.4%} (split-adjusted prices, so a split in the hold changes nothing).",
          f"- Net return: (1 + gross) x (1 - sell cost {res['exit_cost_rate']:.4%}) / (1 + buy cost {res['entry_cost_rate']:.4%}) - 1 "
          f"= **{res['net_return']:+.4%}**; P&L on {res['shares_at_entry']:,} shares: **{money(res['net_pnl_usd'])}**.",
          f"- Not part of the result: best close {res['close_excursion']['max']:+.2%}, worst close {res['close_excursion']['min']:+.2%}; "
          f"highest high {res['intraday_excursion']['max_high']:+.2%}, lowest low {res['intraday_excursion']['min_low']:+.2%} "
          "(descriptive excursions, not executable).", ""]
    return L


def main():
    rows = json.loads((HERE / "replay_2023_exec_us_v1_full.json").read_text())
    quarantined = set(json.loads(PANEL.read_text())["unit_quarantine"]["tickers"])
    frame, _ = global_panel.load(PANEL)
    m = Market.from_panel(frame, price_limits=False)
    m = m.with_units(_dense(m, frame, "unit_factor", 1.0))
    dates = m.dates.astype(str)
    # Examples need a signal close of at least $1: the first profitable trade by ticker order is a
    # $0.02 name whose single $0.0001-tick move is +50% (mechanically right, unreadable as an example).
    clean = sorted((r for r in rows if r["ticker"] not in quarantined and r["plan"]["signal_close"] >= 1),
                   key=lambda r: (r["ticker"], r["signal_session"]))
    picks = [("Profitable trade", "The first non-quarantined filled trade (signal close at least $1) with a positive net return.",
              next(r for r in clean if r["result"]["status"] == "FILLED" and r["result"]["net_return"] > 0)),
             ("Losing trade", "The first non-quarantined filled trade (signal close at least $1) with a negative net return.",
              next(r for r in clean if r["result"]["status"] == "FILLED" and r["result"]["net_return"] < 0)),
             ("Rejected entry", "The first non-quarantined signal (signal close at least $1) whose opening print was outside the 5% band.",
              next(r for r in clean if r["result"]["status"] == "REJECTED_STOP_TOO_WIDE"))]
    out = ["# EXEC-US-v1 worked examples", "",
           "Generated by `worked_examples.py` from the committed v3 repair panel "
           "(`panel_us_repair-20261008T114805Z`). Each example is recomputed with `exec_us` and checked against "
           f"the replay row. Spec `{exec_us.SPEC.sha256()[:12]}`: hypothetical $10,000 account, 1% risk, "
           "20% position cap, 10% of capacity, stop at most 5% below the permitted entry, exit at the close of "
           "the 5th session after the entry session. Picks are the first by ticker and date among names not "
           "quarantined with a signal close of at least $1 (sub-$1 names move in large steps per tick). "
           "Research only; no order.", ""]
    for title, why, r in picks:
        n = list(m.tickers).index(r["ticker"])
        s = int(np.flatnonzero(dates == r["signal_session"])[0])
        again = exec_us.run_one(m.open[n], m.high[n], m.low[n], m.close[n], m.volume[n], m.present[n], m.unit_factor[n],
                                s, exec_us.signal_low_invalidation(m, n, s))
        assert again["result"]["status"] == r["result"]["status"]
        if again["result"]["status"] == "FILLED":
            assert abs(again["result"]["net_return"] - r["result"]["net_return"]) < 1e-12
        out += trail(title, why, m, n, s, again["plan"], again["result"])
    # reference case
    plan = exec_us.make_plan(100.0, 95.0, 1e6)
    o = np.full(8, 100.0)
    o[1] = 110.0
    res = exec_us.execute(o, o + 2, o - 1, o.copy(), np.full(8, 1e6), np.ones(8, bool), np.ones(8), 0, plan)
    out += ["## Reference case: signal $100, stop $95, proposed entry $110", "",
            f"- Invalidation first: {money(plan['invalidation'])}. Permitted entry: floor(95 / 0.95) = {money(plan['max_entry'])} "
            f"(chase limit {money(plan['max_entry_by_chase_rule'])} is higher, so the 5% rule binds).",
            f"- Size at the permitted entry: risk/share {money(plan['risk_per_share'])} -> {plan['shares']} shares, "
            f"max planned loss {money(plan['max_planned_loss_usd'])}.",
            f"- Next open $110: **{res['status']}**: {res['reason']}.",
            "- Under PAPER-POLICY-v3 the same signal could carry a stop 5-15% below the $100 close and a chase limit of $110, "
            "with risk not recomputed at the higher entry.", ""]
    (HERE / "WORKED_EXAMPLES.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()

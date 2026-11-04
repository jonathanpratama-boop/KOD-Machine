"""EXEC-US-v2 end-to-end demonstration: input -> signal -> planned order -> fill or rejection -> exit
-> costs -> account balance, run twice on identical inputs and required to agree.

  * Replay: the frozen US detector (MOONSHOT_E2_US_D1) over the stored panel with prefix-first
    causal signals, then contract.replay over the demo sessions.
  * Forward: for each demo session, the panel truncated to that session (later bars do not exist),
    the detector called once on that day's view, and contract.forward_step with yesterday's account
    state read back from JSON, as a daily paper scan would run.

Data: the pinned US repair panel (hash-checked on load), sessions 2023-09-25 .. 2023-10-20, inside
the permitted research window 2023-01-03 .. 2023-12-29 (the year the split schedule is verified;
already examined by E2 and US_PIPELINE_v1). Integration example of the mechanics only: a few weeks
of one already-rejected detector say nothing about profitability, and no baseline is computed.

    python3 research/EXEC_US_v2/demo.py      (from idx-signals/)
writes trace.json (machine-readable), TRACE.md (readable) and tests.txt (the contract's tests)."""

import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import contract, global_panel  # noqa: E402
from idxsig import rules as rule_registry  # noqa: E402
from idxsig.backtest import _dense  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

HERE = Path(__file__).parent
PANEL = ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json"
RULE = "MOONSHOT_E2_US_D1"
PERMITTED = ("2023-01-03", "2023-12-29")
HISTORY_FROM, DEMO_FROM, DEMO_TO = "2023-01-03", "2023-09-25", "2023-10-20"


def load():
    frame, meta = global_panel.load(PANEL)  # refuses a panel whose bytes differ from the manifest
    full = Market.from_panel(frame, price_limits=False)
    full = full.with_units(_dense(full, frame, "unit_factor", 1.0))
    lo, hi = full.bounds(HISTORY_FROM, DEMO_TO)
    return full.slice(lo, hi + 1), meta


def invalidation(m, n, k):
    """PAPER-POLICY-v4 / MOONSHOT_E2_US_D1 invalidation: the signal session's low, as traded."""
    return float(m.low[n, k] * m.unit_factor[n, k])


def replay_signals(m, rule, k0, k1):
    sig, info = rule_registry.causal_signals(rule, m)
    return {k: [(int(n), invalidation(m, int(n), k)) for n in np.flatnonzero(sig[:, k] == 1)]
            for k in range(k0, k1 + 1)}, info


def forward_signals(m_today, rule):
    """One detector call on the data available today; returns today's signals."""
    k = m_today.shape[1] - 1
    src = rule_registry.CausalSource(m_today)
    out = np.full(m_today.shape, np.nan)
    rows = src.rows_at(k)
    out[:rows] = rule_registry._call(rule, src.view(k))
    out = src.unorder(out)
    return [(int(n), invalidation(m_today, int(n), k)) for n in np.flatnonzero(out[:, k] == 1)]


def canonical(state) -> str:
    return json.dumps(json.loads(json.dumps(state, default=float)), sort_keys=True)


def bar(m, n, k):
    f = float(m.unit_factor[n, k])
    return {"session": str(m.dates[k]), **{x: round(float(getattr(m, x)[n, k] * f), 6)
                                           for x in ("open", "high", "low", "close")},
            "volume_as_traded": float(np.nan_to_num(m.volume[n, k]) / f), "unit_factor": f}


def trace_rows(m, state, quarantined):
    idx = {str(t): i for i, t in enumerate(m.tickers)}
    dates = [str(d) for d in m.dates]
    rows = []
    for c in sorted(state["closed"] + state["positions"] + state["orders"],
                    key=lambda c: (c["signal_session"], c["priority"])):
        n, s = idx[c["ticker"]], dates.index(c["signal_session"])
        row = {"ticker": c["ticker"], "units_verified": c["ticker"] not in quarantined,
               "input_bar": bar(m, n, s), "signal": {"detector": RULE, "session": c["signal_session"],
                                                       "priority": c["priority"]},
               "plan": c["plan"], "outcome": c.get("outcome", "ORDER_WORKING")}
        for key in ("shares_ordered", "cash_limited", "reserved_usd", "planned_risk_usd", "planned_account_risk",
                    "order", "entry_session", "open_as_traded", "entry_session_volume", "limit_at_entry_units",
                    "stop_at_entry_units", "shares_filled", "entry_price", "entry_cost_rate", "entry_debit_usd",
                    "stop_distance_at_fill", "planned_risk_at_fill_usd", "fill_evidence", "reason", "exit_session",
                    "sessions_held", "exit_reason", "shares_at_exit", "exit_price", "exit_cost_rate",
                    "exit_proceeds_usd", "net_pnl_usd", "net_return", "realized_loss_beyond_planned_risk_usd"):
            if key in c:
                row[key] = c[key]
        if c in state["positions"]:
            row["outcome"] = c["outcome"] + " (still held at the end of the demo)"
        rows.append(row)
    return rows


def money(x):
    return "" if x is None else f"${x:,.2f}"


def markdown(out) -> str:
    L = ["# EXEC-US-v2 demonstration trace", "",
         f"Generated by `python3 research/EXEC_US_v2/demo.py`. Contract `{out['contract']['contract_version']}` "
         f"(spec sha256 `{out['contract_sha256'][:16]}…`), panel `{out['panel']['sha256'][:16]}…`, detector {RULE}, "
         f"sessions {DEMO_FROM} .. {DEMO_TO}.", "",
         "**Mechanics only.** A few weeks of an already-rejected detector, on a hypothetical $10,000 account. "
         "This is not evidence of profitability and not a forecast.", "",
         "## Replay and forward agree", "",
         f"- Replay and forward-scoring account states identical: **{out['agreement']['states_identical']}** "
         f"(sha256 `{out['agreement']['replay_state_sha256'][:16]}…` both ways).",
         f"- Signals identical day by day: **{out['agreement']['signals_identical']}** "
         f"({out['agreement']['signals_total']} signals).",
         f"- Forward mode never had a bar after the session it scored: "
         f"**{out['agreement']['forward_saw_no_future_bars']}**.", "",
         "## Account", "",
         f"Start {money(out['account']['starting_cash_usd'])} cash. End: cash {money(out['account']['cash_usd'])}, "
         f"reserved {money(out['account']['reserved_usd'])}, equity marked at the last close "
         f"{money(out['account']['equity_usd'])}; {out['account']['open_positions']} position(s) and "
         f"{out['account']['working_orders']} order(s) still open.", "",
         "Outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(out["outcome_counts"].items())) + ".", "",
         "## Trades that reached the market", ""]
    for r in out["trace"]:
        if "entry_session" not in r:
            continue
        p = r["plan"]
        L += [f"### {r['ticker']} — signal {r['signal']['session']} (priority {r['signal']['priority']})"
              + ("" if r["units_verified"] else " — units not verified by the split schedule (labelled)"), "",
              f"1. **Input** {r['input_bar']['session']}: open {money(r['input_bar']['open'])}, high "
              f"{money(r['input_bar']['high'])}, low {money(r['input_bar']['low'])}, close {money(r['input_bar']['close'])}, "
              f"volume {r['input_bar']['volume_as_traded']:,.0f}.",
              f"2. **Signal**: {RULE} true at that close (data through the close only).",
              f"3. **Plan**: invalidation {money(p['invalidation'])} (signal low; never moved); permitted entry "
              f"{money(p['entry_limit'])} = min(stop / 0.95 = {money(p['limit_by_stop_rule'])}, close × 1.10 = "
              f"{money(p['limit_by_chase_rule'])}); stop distance at that entry {p['stop_distance_at_limit']:.2%}. "
              f"Shares: risk {p['shares_by_risk']:,.1f}, capital {p['shares_by_capital']:,.1f}, liquidity "
              f"{p['shares_by_liquidity']:,.1f} → **{p['shares']:,}** ({p['binding_limit']} binds).",
              f"4. **Order**: buy {r['shares_ordered']:,} limit-on-open at {money(p['entry_limit'])}, stop "
              f"{money(p['invalidation'])} attached; cash reserved {money(r['reserved_usd'])}; planned risk "
              f"{money(r['planned_risk_usd'])} = {r['planned_account_risk']:.2%} of equity"
              + (" (cut to the cash available)" if r["cash_limited"] else "") + ".",
              f"5. **Open {r['entry_session']}**: {money(r.get('open_as_traded'))} → **{r['outcome']}**"
              + (f" — {r['reason']}" if r.get("reason") else "") + "."]
        if "shares_filled" in r:
            L += [f"   Filled {r['shares_filled']:,} at {money(r['entry_price'])} (buy cost {r['entry_cost_rate']:.3%}; "
                  f"debit {money(r['entry_debit_usd'])}); stop distance at the fill {r['stop_distance_at_fill']:.2%}; "
                  f"fill bound 10% of the session's {r['entry_session_volume']:,.0f} shares (an assumption)."]
        if "exit_session" in r:
            L += [f"6. **Exit {r['exit_session']}** ({r['sessions_held']} sessions): {r['exit_reason']} at "
                  f"{money(r['exit_price'])} (sell cost {r['exit_cost_rate']:.3%}; proceeds {money(r['exit_proceeds_usd'])}).",
                  f"7. **Result**: net {money(r['net_pnl_usd'])} ({r['net_return']:+.2%}); loss beyond the planned "
                  f"risk {money(r['realized_loss_beyond_planned_risk_usd'])}."]
        L.append("")
    L += ["## Every signal", "", "| Signal | Ticker | Pri | Outcome | Limit | Open | Shares | Net |", "|---|---|---|---|---|---|---|---|"]
    for r in out["trace"]:
        L.append(f"| {r['signal']['session']} | {r['ticker']} | {r['signal']['priority']} | {r['outcome']} | "
                 f"{money(r['plan'].get('entry_limit'))} | {money(r.get('open_as_traded'))} | "
                 f"{r.get('shares_filled', '')} | {money(r.get('net_pnl_usd'))} |")
    L += ["", "## Account events (cash after each event)", "", "| Session | Event | Ticker | Detail | Cash | Reserved |",
          "|---|---|---|---|---|---|"]
    for e in out["events"]:
        if e["event"] in ("SCAN_SIGNALS",):
            continue
        detail = {k: v for k, v in e.items() if k not in ("session", "event", "ticker", "cash_usd", "reserved_usd")}
        L.append(f"| {e['session']} | {e['event']} | {e.get('ticker', '')} | "
                 f"{', '.join(f'{k}={v}' for k, v in detail.items())} | {money(e['cash_usd'])} | {money(e['reserved_usd'])} |")
    return "\n".join(L) + "\n"


def main() -> int:
    m, meta = load()
    rule = rule_registry.get(RULE)
    k0, k1 = int(np.searchsorted(m.dates, np.datetime64(DEMO_FROM))), m.shape[1] - 1
    sig_replay, sig_info = replay_signals(m, rule, k0, k1)
    rep = contract.replay(m, sig_replay, k0, k1, permitted=PERMITTED)

    state, fwd_sig, saw_future = None, {}, False
    ledger, prev = [], "0" * 64
    for k in range(k0, k1 + 1):
        today = m.truncate(k)
        saw_future |= today.shape[1] != k + 1
        fwd_sig[k] = forward_signals(today, rule)
        state, scan = contract.forward_step(state, today, fwd_sig[k], str(m.dates[k]))
        body = {"session": str(m.dates[k]), "scan": scan, "state_sha256": hashlib.sha256(canonical(state).encode()).hexdigest(),
                "prev_hash": prev}
        prev = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        ledger.append({**body, "record_hash": prev})

    rep_state = json.loads(canonical(rep.state))
    st = state
    quarantined = set(meta["unit_quarantine"]["tickers"])
    k_end = k1
    equity = contract.Account(contract.SPEC, st)._equity(m, k_end)
    out = {"contract": contract.SPEC.record(), "contract_sha256": contract.SPEC.sha256(),
           "panel": {"manifest": str(PANEL.relative_to(ROOT)), "manifest_sha256": sha256_file(PANEL),
                     "sha256": meta["sha256"]},
           "detector": {"rule": RULE, "sha256": rule.sha256, "signal_mode": sig_info["mode"],
                        "invalidation": "signal-session low, as traded"},
           "sessions": [DEMO_FROM, DEMO_TO], "permitted_research_window": list(PERMITTED),
           "agreement": {"states_identical": canonical(rep.state) == canonical(st),
                         "replay_state_sha256": hashlib.sha256(canonical(rep.state).encode()).hexdigest(),
                         "forward_state_sha256": hashlib.sha256(canonical(st).encode()).hexdigest(),
                         "signals_identical": all(sorted(sig_replay[k]) == sorted(fwd_sig[k]) for k in sig_replay),
                         "signals_total": sum(len(v) for v in sig_replay.values()),
                         "forward_saw_no_future_bars": not saw_future,
                         "forward_ledger_head": prev},
           "account": {"starting_cash_usd": contract.SPEC.starting_cash_usd, "cash_usd": st["cash_usd"],
                       "reserved_usd": sum(o["reserved_usd"] for o in st["orders"]), "equity_usd": equity,
                       "open_positions": len(st["positions"]), "working_orders": len(st["orders"])},
           "outcome_counts": {}, "trace": trace_rows(m, st, quarantined), "events": st["events"],
           "forward_ledger": ledger}
    for r in out["trace"]:
        out["outcome_counts"][r["outcome"]] = out["outcome_counts"].get(r["outcome"], 0) + 1
    assert rep_state == json.loads(canonical(st)) or not out["agreement"]["states_identical"]

    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName("tests.test_contract"))
    out["contract_tests"] = {"ran": res.testsRun, "failures": len(res.failures), "errors": len(res.errors)}
    (HERE / "tests.txt").write_text(buf.getvalue())
    (HERE / "trace.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    (HERE / "TRACE.md").write_text(markdown(out))
    print(json.dumps({k: out[k] for k in ("agreement", "account", "outcome_counts", "contract_tests")}, indent=1,
                     default=float))
    ok = out["agreement"]["states_identical"] and out["agreement"]["signals_identical"] and \
        out["agreement"]["forward_saw_no_future_bars"] and res.wasSuccessful()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

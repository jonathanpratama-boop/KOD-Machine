"""EXEC-US-v2.1 end-to-end demonstration: input -> signal -> planned order -> fill or rejection -> exit
-> costs -> account balance, run twice on identical market data and required to agree.

  * Replay: the frozen US detector (MOONSHOT_E2_US_D1) over the stored panel with prefix-first
    causal signals, then contract.replay over the demo sessions.
  * Forward: each demo session gets its own simulated daily DOWNLOAD of the same market data,
    laid out the way a provider would deliver it on that day:
      - a rolling window (the last WINDOW sessions only);
      - rows in a different order every day (seeded shuffle);
      - prices and volumes re-adjusted to that day's split basis (a provider re-adjusts history
        after every split): adjusted = as traded / (F[j] / F[today]).
    The detector is called once on that download, and contract.forward_step runs with yesterday's
    account state read back from JSON. Ace's review of v2 showed that agreement on one frozen
    layout proves little; this checks it across changing layouts.

Data: the pinned US repair panel (hash-checked on load), sessions 2023-09-25 .. 2023-10-20 (20
sessions), inside the permitted research window 2023-01-03 .. 2023-12-29. Mechanics only: a few
weeks of one already-rejected detector say nothing about profitability, and no baseline is computed.

    python3 research/EXEC_US_v2_1/demo.py      (from idx-signals/)
writes trace.json, TRACE.md and tests.txt next to this file; exits 0 only if every check passes."""

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
EXPECTED_SESSIONS = 20
WINDOW = 120  # sessions in each simulated daily download (the detector needs at most 60 + 20)
SEED = 20261009


def window(m, start: str, end: str):
    """Sessions start..end inclusive. Market.bounds already returns an exclusive end (v2's demo added
    one more and replayed a 21st session; Ace's review)."""
    lo, hi = m.bounds(start, end)
    return m.slice(lo, hi)


def load():
    frame, meta = global_panel.load(PANEL)  # refuses a panel whose bytes differ from the manifest
    full = Market.from_panel(frame, price_limits=False)
    full = full.with_units(_dense(full, frame, "unit_factor", 1.0))
    return window(full, HISTORY_FROM, DEMO_TO), meta


def download(m, k: int, rng) -> Market:
    """What a provider would deliver after the close of session k: the last WINDOW sessions, rows
    shuffled, and every price re-adjusted to session k's split basis."""
    lo = max(0, k - WINDOW + 1)
    order = rng.permutation(m.shape[0])
    rebase = m.unit_factor[:, [k]]                    # F[today] per name
    arrays = {f: getattr(m, f)[:, lo: k + 1].copy() for f in Market.FIELDS}
    for f in ("close", "prev", "high", "low", "open"):
        arrays[f] = arrays[f] * rebase                # adjusted to today's basis
    arrays["volume"] = arrays["volume"] / rebase
    uf = m.unit_factor[:, lo: k + 1] / rebase         # as traded = adjusted x F, F[today] = 1
    arrays = {f: a[order] for f, a in arrays.items()}
    return Market(m.tickers[order], m.dates[lo: k + 1], **arrays, unit_factor=uf[order])


def invalidation(m, n, k):
    """PAPER-POLICY-v4 / MOONSHOT_E2_US_D1 invalidation: the signal session's low, as traded."""
    return float(m.low[n, k] * m.unit_factor[n, k])


def replay_signals(m, rule, k0, k1):
    sig, info = rule_registry.causal_signals(rule, m)
    return {k: [(int(n), invalidation(m, int(n), k)) for n in np.flatnonzero(sig[:, k] == 1)]
            for k in range(k0, k1 + 1)}, info


def forward_signals(d, rule):
    """One detector call on today's download; returns today's signals as rows of that download."""
    k = d.shape[1] - 1
    src = rule_registry.CausalSource(d)
    out = np.full(d.shape, np.nan)
    out[: src.rows_at(k)] = rule_registry._call(rule, src.view(k))
    out = src.unorder(out)
    return [(int(n), invalidation(d, int(n), k)) for n in np.flatnonzero(out[:, k] == 1)]


def canonical(state) -> str:
    return json.dumps(json.loads(json.dumps(state, default=float)), sort_keys=True)


def by_ticker(m, sig):
    return sorted((str(m.tickers[n]), round(inv, 6)) for n, inv in sig)


def bar(m, n, k):
    f = float(m.unit_factor[n, k])
    return {"session": str(m.dates[k]), **{x: round(float(getattr(m, x)[n, k] * f), 6)
                                           for x in ("open", "high", "low", "close")},
            "volume_as_traded": float(np.nan_to_num(m.volume[n, k]) / f), "unit_factor": f}


TRACE_KEYS = ("shares_ordered", "cash_limited", "reserved_usd", "planned_risk_usd", "planned_account_risk", "order",
              "entry_session", "open_as_traded", "entry_session_volume", "units_conversion_at_entry",
              "limit_at_entry_units", "stop_at_entry_units", "planned_shares_at_entry_units", "shares_filled",
              "entry_price", "entry_cost_rate", "entry_debit_usd", "stop_distance_at_fill", "planned_risk_at_fill_usd",
              "fill_evidence", "reason", "exit_session", "sessions_held", "exit_reason", "shares_at_exit",
              "stop_at_exit_units", "exit_price", "exit_cost_rate", "exit_proceeds_usd", "net_pnl_usd", "net_return",
              "realized_loss_beyond_planned_risk_usd", "shares", "stop", "units_session")


def trace_rows(m, state, quarantined):
    idx = {str(t): i for i, t in enumerate(m.tickers)}
    dates = [str(d) for d in m.dates]
    rows = []
    held = {id(p) for p in state["positions"]}
    working = {id(o) for o in state["orders"]}
    for c in sorted(state["closed"] + state["positions"] + state["orders"],
                    key=lambda c: (c["signal_session"], c["priority"])):
        n, s = idx[c["ticker"]], dates.index(c["signal_session"])
        row = {"ticker": c["ticker"], "units_verified": c["ticker"] not in quarantined,
               "input_bar": bar(m, n, s), "signal": {"detector": RULE, "session": c["signal_session"],
                                                       "priority": c["priority"]},
               "plan": c["plan"], "outcome": c.get("outcome", "ORDER_WORKING")}
        row.update({key: c[key] for key in TRACE_KEYS if key in c})
        if id(c) in held:
            row["outcome"] = c["outcome"] + " (still held at the end of the demo)"
        if id(c) in working:
            row["outcome"] = "ORDER_WORKING (entry after the demo's last session)"
        rows.append(row)
    return rows


def money(x):
    return "" if x is None else f"${x:,.2f}"


def markdown(out) -> str:
    a = out["agreement"]
    L = ["# EXEC-US-v2.1 demonstration trace", "",
         f"Generated by `python3 research/EXEC_US_v2_1/demo.py`. Contract `{out['contract']['contract_version']}` "
         f"(spec sha256 `{out['contract_sha256'][:16]}…`), panel `{out['panel']['sha256'][:16]}…`, detector {RULE}, "
         f"sessions {out['sessions_processed'][0]} .. {out['sessions_processed'][-1]} "
         f"({len(out['sessions_processed'])} sessions).", "",
         "**Mechanics only.** A few weeks of an already-rejected detector, on a hypothetical $10,000 account. "
         "This is not evidence of profitability and not a forecast.", "",
         "## Replay and forward agree across changing downloads", "",
         "Forward mode received a different download each day: the last "
         f"{WINDOW} sessions only, rows shuffled, and prices re-adjusted to that day's split basis.", "",
         f"- Account states identical: **{a['states_identical']}** (sha256 `{a['replay_state_sha256'][:16]}…` both ways).",
         f"- Signals identical day by day, by ticker and invalidation: **{a['signals_identical']}** "
         f"({a['signals_total']} signals).",
         f"- Forward mode never had a bar after the session it scored: **{a['forward_saw_no_future_bars']}**.",
         f"- Sessions processed: **{len(out['sessions_processed'])}**, first {out['sessions_processed'][0]}, "
         f"last {out['sessions_processed'][-1]} (declared {DEMO_FROM} .. {DEMO_TO}).",
         f"- Downloads where a name's split basis changed inside the window: {a['downloads_with_rebased_names']}.", "",
         "## Account", "",
         f"Start {money(out['account']['starting_cash_usd'])} cash. At the close of {out['sessions_processed'][-1]}: "
         f"cash {money(out['account']['cash_usd'])}, reserved {money(out['account']['reserved_usd'])}, equity "
         f"{money(out['account']['equity_usd'])}; {out['account']['open_positions']} position(s) held and "
         f"{out['account']['working_orders']} order(s) working.", "",
         "Outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(out["outcome_counts"].items())) + ".", "",
         "## Trades that reached the market", ""]
    for r in out["trace"]:
        if "entry_price" not in r and "open_as_traded" not in r:
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
              f"{money(p['limit_by_chase_rule'])}); stop distance there {p['stop_distance_at_limit']:.2%}; risk per "
              f"share {money(p['risk_per_share'])} (exit cost at the stop's tier, {p['exit_cost_at_stop']:.3%}). "
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
                  f"planned risk at the fill {money(r['planned_risk_at_fill_usd'])}; fill bound 10% of the session's "
                  f"{r['entry_session_volume']:,.0f} shares (an assumption)."]
        if "exit_session" in r:
            L += [f"6. **Exit {r['exit_session']}** (session {r['sessions_held']} of the hold): {r['exit_reason']}, "
                  f"{r['shares_at_exit']:,.2f} shares at {money(r['exit_price'])} (sell cost {r['exit_cost_rate']:.3%}; "
                  f"proceeds {money(r['exit_proceeds_usd'])}).",
                  f"7. **Result**: net {money(r['net_pnl_usd'])} ({r['net_return']:+.2%}); loss beyond the planned "
                  f"risk {money(r['realized_loss_beyond_planned_risk_usd'])}."]
        L.append("")
    L += ["## Every signal", "", "| Signal | Ticker | Pri | Outcome | Limit | Open | Shares | Net |",
          "|---|---|---|---|---|---|---|---|"]
    for r in out["trace"]:
        L.append(f"| {r['signal']['session']} | {r['ticker']} | {r['signal']['priority']} | {r['outcome']} | "
                 f"{money(r['plan'].get('entry_limit'))} | {money(r.get('open_as_traded'))} | "
                 f"{r.get('shares_filled', '')} | {money(r.get('net_pnl_usd'))} |")
    L += ["", "## Account events (cash after each event)", "", "| Session | Event | Ticker | Detail | Cash | Reserved |",
          "|---|---|---|---|---|---|"]
    for e in out["events"]:
        if e["event"] == "SCAN_SIGNALS":
            continue
        detail = {k: v for k, v in e.items() if k not in ("session", "event", "ticker", "cash_usd", "reserved_usd")}
        L.append(f"| {e['session']} | {e['event']} | {e.get('ticker', '')} | "
                 f"{', '.join(f'{k}={v}' for k, v in detail.items())} | {money(e['cash_usd'])} | {money(e['reserved_usd'])} |")
    return "\n".join(L) + "\n"


def main() -> int:
    m, meta = load()
    rule = rule_registry.get(RULE)
    k0, k1 = int(np.searchsorted(m.dates, np.datetime64(DEMO_FROM))), m.shape[1] - 1
    sessions = [str(d) for d in m.dates[k0: k1 + 1]]
    sig_replay, sig_info = replay_signals(m, rule, k0, k1)
    rep = contract.replay(m, sig_replay, k0, k1, permitted=PERMITTED)

    rng = np.random.default_rng(SEED)
    state, fwd_sig, saw_future, rebased = None, {}, False, 0
    ledger, prev = [], "0" * 64
    for k in range(k0, k1 + 1):
        d = download(m, k, rng)
        saw_future |= str(d.dates[-1]) != str(m.dates[k])
        rebased += int((np.abs(d.unit_factor - 1) > 1e-12).any())
        today = forward_signals(d, rule)
        fwd_sig[k] = by_ticker(d, today)
        state, scan = contract.forward_step(state, d, today, str(m.dates[k]))
        body = {"session": str(m.dates[k]), "scan": scan, "download": {"first_session": str(d.dates[0]),
                "rows": d.shape[0], "first_row": str(d.tickers[0])},
                "state_sha256": hashlib.sha256(canonical(state).encode()).hexdigest(), "prev_hash": prev}
        prev = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        ledger.append({**body, "record_hash": prev})

    st = json.loads(canonical(state))
    quarantined = set(meta["unit_quarantine"]["tickers"])
    acc = contract.Account(contract.SPEC, st)
    equity = acc.equity(contract._Data(m, k1))
    out = {"contract": contract.SPEC.record(), "contract_sha256": contract.SPEC.sha256(),
           "panel": {"manifest": str(PANEL.relative_to(ROOT)), "manifest_sha256": sha256_file(PANEL),
                     "sha256": meta["sha256"]},
           "detector": {"rule": RULE, "sha256": rule.sha256, "signal_mode": sig_info["mode"],
                        "invalidation": "signal-session low, as traded"},
           "declared_sessions": [DEMO_FROM, DEMO_TO], "sessions_processed": sessions,
           "permitted_research_window": list(PERMITTED),
           "forward_downloads": {"window_sessions": WINDOW, "row_order": f"shuffled daily (seed {SEED})",
                                 "adjustment": "re-adjusted to each day's split basis"},
           "agreement": {"states_identical": canonical(rep.state) == canonical(st),
                         "replay_state_sha256": hashlib.sha256(canonical(rep.state).encode()).hexdigest(),
                         "forward_state_sha256": hashlib.sha256(canonical(st).encode()).hexdigest(),
                         "signals_identical": all(by_ticker(m, sig_replay[k]) == fwd_sig[k] for k in sig_replay),
                         "signals_total": sum(len(v) for v in sig_replay.values()),
                         "forward_saw_no_future_bars": not saw_future,
                         "downloads_with_rebased_names": rebased,
                         "forward_ledger_head": prev},
           "account": {"starting_cash_usd": contract.SPEC.starting_cash_usd, "cash_usd": st["cash_usd"],
                       "reserved_usd": sum(o["reserved_usd"] for o in st["orders"]), "equity_usd": equity,
                       "open_positions": len(st["positions"]), "working_orders": len(st["orders"])},
           "outcome_counts": {}, "trace": trace_rows(m, st, quarantined), "events": st["events"],
           "forward_ledger": ledger}
    for r in out["trace"]:
        out["outcome_counts"][r["outcome"]] = out["outcome_counts"].get(r["outcome"], 0) + 1
    window_ok = (sessions[0], sessions[-1], len(sessions)) == (DEMO_FROM, DEMO_TO, EXPECTED_SESSIONS) and \
        [x["session"] for x in ledger] == sessions
    out["agreement"]["window_matches_declaration"] = window_ok

    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName("tests.test_contract"))
    out["contract_tests"] = {"ran": res.testsRun, "failures": len(res.failures), "errors": len(res.errors)}
    (HERE / "tests.txt").write_text(buf.getvalue())
    (HERE / "trace.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    (HERE / "TRACE.md").write_text(markdown(out))
    print(json.dumps({k: out[k] for k in ("agreement", "account", "outcome_counts", "contract_tests")}, indent=1,
                     default=float))
    a = out["agreement"]
    ok = (a["states_identical"] and a["signals_identical"] and a["forward_saw_no_future_bars"] and window_ok
          and res.wasSuccessful())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

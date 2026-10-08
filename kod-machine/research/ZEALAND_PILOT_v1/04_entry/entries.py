"""ZEALAND_PILOT_v1 step 3: entry opportunities, exactly as pre-registered in 01_protocol/protocol.json.

Inputs (all committed, sha256-checked):
  01_protocol/pin/ZEAL.CO.json                       Yahoo ZEAL.CO daily bars: the protocol's price series
  04_entry/inputs/nasdaq_nordic_ZEAL_TX730846_*.json  Nasdaq Nordic official daily bars: cross-check, turnover, quotes
  04_entry/inputs/yahoo_OMXC25.json                  OMX Copenhagen 25 (benchmark)

Prices are home-listing official opens and closes in DKK. Costs are the protocol's labelled
assumptions (0.20% per side base, 0.60% stress). No US convention is used: there is no
pre-market or after-hours price; the first execution after the 07:00 CET release is the
09:00 CET opening auction (auction times are the 2026 factsheet's, assumed for 2025).

Run: python3 entries.py  ->  results.json and a printed table.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROTOCOL = json.loads((ROOT / "01_protocol" / "protocol.json").read_text())
INPUTS = {
    "yahoo": (ROOT / "01_protocol/pin/ZEAL.CO.json", "a20b3934ebc11a3f4d44e9e11d73e5636ecf3543994ce58ad5b10d6b40598b8b"),
    "nasdaq": (HERE / "inputs/nasdaq_nordic_ZEAL_TX730846_2024-11-01_2025-07-15.json",
               "f2752dc42d4a51a9f5b0407de798195f03fc797eaa1f9da85f5f3e0e4dc75bb6"),
    "index": (HERE / "inputs/yahoo_OMXC25.json", "76906453248063e828285a0350ef40e5c7d76dfefc1e772f6baf2e1cecc8a165"),
}
EVENT = "2025-03-12"
EXITS = (0, 1, 5, 20, 60)
REF_POSITION = 1_000_000  # DKK
BASE, STRESS = PROTOCOL["costs"]["base_per_side"], PROTOCOL["costs"]["stress_per_side"]
# (id, session, at) as defined in protocol.json "entries"
ENTRIES = [
    ("E1_PRE_T30D", "2025-02-10", "close"),
    ("E2_PRE_T24H", "2025-03-10", "close"),
    ("E3_PRE_CUTOFF", "2025-03-11", "close"),
    ("E4_EVENT_OPEN", "2025-03-12", "open"),
    ("E5_EVENT_CLOSE", "2025-03-12", "close"),
    ("E6_NEXT_OPEN", "2025-03-13", "open"),
]


def load(name):
    path, sha = INPUTS[name]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise SystemExit(f"{path} does not match its sha256")
    return json.loads(raw)


def yahoo_bars(doc) -> dict[str, dict]:
    r = doc["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = {}
    for i, ts in enumerate(r["timestamp"]):
        row = {k: q[k][i] for k in ("open", "high", "low", "close", "volume")}
        if None not in row.values():
            out[datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")] = row
    return out


def nasdaq_bars(doc) -> dict[str, dict]:
    num = lambda s: float(str(s).replace(",", "")) if s not in (None, "", "-") else None  # noqa: E731
    return {r["dateTime"]: {"open": num(r["open"]), "high": num(r["high"]), "low": num(r["low"]),
                            "close": num(r["close"]), "volume": num(r["totalVolume"]), "turnover": num(r["turnover"]),
                            "trades": num(r["trades"]), "bid": num(r["bid"]), "ask": num(r["ask"])}
            for r in doc["data"]["charts"]["rows"]}


def net(entry: float, exit_: float, c: float) -> float:
    return exit_ * (1 - c) / (entry * (1 + c)) - 1


def main() -> None:
    y, n, ix = yahoo_bars(load("yahoo")), nasdaq_bars(load("nasdaq")), yahoo_bars(load("index"))
    days = sorted(y)
    e = days.index(EVENT)

    # cross-check: every session both sources have, Oct 2024 .. Jul 2025
    common = [d for d in days if d in n and n[d]["close"]]
    worst = max(common, key=lambda d: max(abs(y[d][k] - n[d][k]) / n[d][k] for k in ("open", "high", "low", "close")))
    xcheck = {
        "sessions_compared": len(common), "first": common[0], "last": common[-1],
        "max_relative_ohlc_difference": max(abs(y[d][k] - n[d][k]) / n[d][k] for d in common for k in ("open", "high", "low", "close")),
        "worst_session": worst,
        "sessions_with_any_ohlc_difference": sum(any(abs(y[d][k] - n[d][k]) > 1e-9 for k in ("open", "high", "low", "close")) for d in common),
        "max_relative_volume_difference": max(abs(y[d]["volume"] - n[d]["volume"]) / n[d]["volume"] for d in common),
        "nasdaq_sessions_missing_in_yahoo": [d for d in n if d not in y],
    }

    rows = []
    for eid, session, at in ENTRIES:
        i = days.index(session)
        px = y[session][at]
        turnover_proxy = y[session]["volume"] * y[session]["close"]
        official = n.get(session, {})
        for k in EXITS:
            j = e + k
            if j < i or (j == i and at == "close"):
                continue
            exit_px = y[days[j]]["close"]
            path_from = i if at == "open" else i + 1
            lows = [y[days[t]]["low"] for t in range(path_from, j + 1)]
            highs = [y[days[t]]["high"] for t in range(path_from, j + 1)]
            ix_entry = ix[session][at] if session in ix else None
            ix_exit = ix[days[j]]["close"] if days[j] in ix else None
            bench = (ix_exit / ix_entry - 1) if ix_entry and ix_exit else None
            nb = net(px, exit_px, BASE)
            rows.append({
                "entry": eid, "entry_session": session, "entry_at": at, "entry_price": px,
                "exit": f"event+{k}", "exit_session": days[j], "exit_price": exit_px,
                "gross": exit_px / px - 1, "net_base": nb, "net_stress": net(px, exit_px, STRESS),
                "benchmark_omxc25": bench, "excess_net_base_vs_benchmark": (nb - bench) if bench is not None else None,
                "path_worst_low": (min(lows) / px - 1) if lows else None,
                "path_best_high": (max(highs) / px - 1) if highs else None,
                "entry_session_value_dkk_volume_x_close": turnover_proxy,
                "entry_session_official_turnover_dkk": official.get("turnover"),
                "reference_position_share_of_turnover": REF_POSITION / (official.get("turnover") or turnover_proxy),
            })

    prev, ev = y[days[e - 1]], y[EVENT]
    gap = {
        "release_utc": PROTOCOL["event"]["release_time_utc"],
        "first_home_listing_execution": "opening auction of 2025-03-12 (uncross 09:00:00-09:00:05 CET per the auctions factsheet; assumed for 2025)",
        "previous_close": prev["close"], "event_open": ev["open"], "event_close": ev["close"],
        "event_low": ev["low"], "event_high": ev["high"],
        "close_to_open": ev["open"] / prev["close"] - 1, "open_to_close": ev["close"] / ev["open"] - 1,
        "close_to_close": ev["close"] / prev["close"] - 1,
        "share_of_close_to_close_move_before_first_execution": (ev["open"] - prev["close"]) / (ev["close"] - prev["close"]),
        "event_low_vs_previous_close": ev["low"] / prev["close"] - 1,
        "official_event_session": n.get(EVENT), "official_previous_session": n.get(days[e - 1]),
    }

    run_up = {
        "closes": {d: y[d]["close"] for d in days[days.index("2025-02-07"):e + 1]},
        "E1_to_E3_gross": y["2025-03-11"]["close"] / y["2025-02-10"]["close"] - 1,
        "omxc25_E1_to_E3": ix["2025-03-11"]["close"] / ix["2025-02-10"]["close"] - 1,
        "max_close_2025-02-10..2025-03-11": max(y[d]["close"] for d in days[days.index("2025-02-10"):e]),
    }

    pick = lambda eid, k: next(r for r in rows if r["entry"] == eid and r["exit"] == f"event+{k}")  # noqa: E731
    candidates = [
        {
            "id": "H-A pending partnering, documents only",
            "condition": "a PRIMARY document states the issuer intends to partner its lead programme(s) and no date or window is given",
            "first_visible": "2024-08-15 (P02); still true at T-30D, T-72H and T-24H",
            "entry_it_triggers": "E1_PRE_T30D (the earliest protocol entry; a rule without the date cannot wait for it)",
            "C1_ex_ante": True, "C1_note": "grade B exchange documents and grade C dated press, all published before T-30D",
            "C2_general": True, "C2_note": "no Zealand constant; many issuers state undated partnering intent",
            "C3_feasible": None, "C3_detail": pick("E1_PRE_T30D", 5),
            "C4_falsifiable": True,
        },
        {
            "id": "H-B pending partnering plus a high-volume drawdown",
            "condition": "H-A and, at the T-24H set, volume_creep_before_story = true with a 20-session fall",
            "entry_it_triggers": "E2_PRE_T24H or E3_PRE_CUTOFF",
            "C1_ex_ante": False,
            "C1_note": "the price facts rest on series retrieved in 2026 (KOD grade D); C1 admits grades A-C only. Any drawdown "
                       "threshold would also be chosen after seeing this path.",
            "C2_general": None, "C2_note": "not assessed: fails C1",
            "C3_feasible": None, "C3_detail": [pick("E2_PRE_T24H", 5), pick("E3_PRE_CUTOFF", 5)],
            "C4_falsifiable": None,
        },
        {
            "id": "H-C post-release drift",
            "condition": "an inside-information announcement of a partnership with upfront cash, entered after release",
            "entry_it_triggers": "E4_EVENT_OPEN (first execution), E5_EVENT_CLOSE, E6_NEXT_OPEN",
            "C1_ex_ante": True, "C1_note": "the release itself (E00, grade B) is public at the trigger",
            "C2_general": True, "C2_note": "no Zealand constant",
            "C3_feasible": None, "C3_detail": [pick("E4_EVENT_OPEN", 5), pick("E5_EVENT_CLOSE", 5), pick("E6_NEXT_OPEN", 5)],
            "C4_falsifiable": True,
        },
    ]
    for c in candidates:
        detail = c["C3_detail"] if isinstance(c["C3_detail"], list) else [c["C3_detail"]]
        ok = [d["net_base"] > 0 and d["excess_net_base_vs_benchmark"] > 0
              and d["reference_position_share_of_turnover"] <= 1 / 20 for d in detail]
        c["C3_feasible"] = all(ok)
        c["passes_all"] = bool(c["C1_ex_ante"] and c["C2_general"] and c["C3_feasible"] and c["C4_falsifiable"])
    conclusion = ("FROZEN_HYPOTHESIS" if any(c["passes_all"] for c in candidates) else "NO_ACTIONABLE_EDGE_ESTABLISHED")

    out = {"protocol": "ZEALAND_PILOT_v1", "inputs": {k: {"path": str(v[0].relative_to(ROOT)), "sha256": v[1]} for k, v in INPUTS.items()},
           "costs": {"base_per_side": BASE, "stress_per_side": STRESS, "status": "assumption"},
           "cross_check": xcheck, "release_and_gap": gap, "run_up": run_up, "entries": rows,
           "candidates": candidates, "conclusion": conclusion}
    (HERE / "results.json").write_text(json.dumps(out, indent=2) + "\n")

    print(f"cross-check: {xcheck['sessions_compared']} sessions, max OHLC diff {xcheck['max_relative_ohlc_difference']:.4%}, "
          f"max volume diff {xcheck['max_relative_volume_difference']:.4%}")
    print(f"gap: prev close {gap['previous_close']} -> open {gap['event_open']} ({gap['close_to_open']:+.1%}), "
          f"close {gap['event_close']} ({gap['close_to_close']:+.1%}); open-to-close {gap['open_to_close']:+.1%}")
    print(f"run-up: E1->E3 {run_up['E1_to_E3_gross']:+.1%} (OMXC25 {run_up['omxc25_E1_to_E3']:+.1%})")
    print(f"{'entry':16} {'exit':9} {'px_in':>7} {'px_out':>7} {'gross':>7} {'net':>7} {'stress':>7} {'idx':>7} {'excess':>7} {'worst':>7} {'best':>7}")
    for r in rows:
        f = lambda v: f"{v:+.1%}" if v is not None else "   n/a"  # noqa: E731
        print(f"{r['entry']:16} {r['exit']:9} {r['entry_price']:7.1f} {r['exit_price']:7.1f} {f(r['gross']):>7} {f(r['net_base']):>7} "
              f"{f(r['net_stress']):>7} {f(r['benchmark_omxc25']):>7} {f(r['excess_net_base_vs_benchmark']):>7} "
              f"{f(r['path_worst_low']):>7} {f(r['path_best_high']):>7}")
    for c in candidates:
        print(c["id"], {k: c[k] for k in ("C1_ex_ante", "C2_general", "C3_feasible", "C4_falsifiable", "passes_all")})
    print("conclusion:", conclusion)


if __name__ == "__main__":
    main()

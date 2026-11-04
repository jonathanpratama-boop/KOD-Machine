"""CRYPTO_REPLAY_v1: the accelerated historical crypto paper-account replay of 2023 (simulation only).

    python3 research/CRYPTO_REPLAY_v1/replay.py --freeze --panel <panel.csv.gz>   # protocol.json, before any result
    python3 research/CRYPTO_REPLAY_v1/replay.py --panel <panel.csv.gz>            # the one run: run/

Inputs: the rebuilt, verified frozen rankings (rankings/shortlists_2023.csv.gz, rankings/VERIFY.json; rankings.py)
and the run's own panel (sha256 f1dfd57d...). The early population's five-name daily shortlists of three frozen
arms are traded by idxsig/crypto_replay.py under one Policy; a cash-only account is the reference. 2023 was
studied before: retrospective development evidence, not validation. Nothing after 2023-12-31 is read.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import crypto_replay as cr
from idxsig.provenance import sha256_file, utc_stamp

PROTO, RUN = HERE / "protocol.json", HERE / "run"
PANEL_SHA256 = "f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766"
FIRST, LAST = date(2023, 1, 1), date(2023, 12, 31)
POPULATION = "early"
ARMS = ("summary", "sequence", "shuffled")
SCENARIOS = {
    "BASE": cr.Policy(),
    "ENTRY_DELAY_1": cr.Policy(entry_delay=1),
    "DOUBLE_COSTS": cr.Policy(fee=0.002, slip=0.002),
    "DELAY_AND_DOUBLE": cr.Policy(entry_delay=1, fee=0.002, slip=0.002),
}
PRIMARY = "BASE"
BOOT = {"block_days": 10, "draws": 2000, "seed": 20261031}
PINS = (
    "idxsig/crypto_replay.py",
    "research/CRYPTO_REPLAY_v1/replay.py",
    "research/CRYPTO_REPLAY_v1/rankings.py",
    "research/CRYPTO_REPLAY_v1/report.py",
    "tests/test_crypto_replay.py",
    "research/CRYPTO_REPLAY_v1/rankings/shortlists_2023.csv.gz",
    "research/CRYPTO_REPLAY_v1/rankings/VERIFY.json",
    "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/models.json",
    "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/summary.json",
    "research/PREMOVE_SHADOW_v1/control_model.json",
    "idxsig/paper_account.py",
)


def freeze(panel: Path) -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists; the protocol is frozen once")
    verify = json.loads((HERE / "rankings/VERIFY.json").read_text())
    if not verify["verdict"].startswith("REBUILT RANKINGS MATCH"):
        sys.exit("error: the rankings were not verified")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    PROTO.write_text(
        json.dumps(
            {
                "study_id": "CRYPTO_REPLAY_v1",
                "frozen_at": utc_stamp(),
                "status": (
                    "a separate hypothetical test of the frozen PREMOVE_SEQUENCE_v1 rankings: every day's frozen "
                    "top-five early-population shortlist is offered to the account in rank order and the account "
                    "limits decide which names enter. It is not a replay of the live crypto paper policy (which "
                    "decides PASS) and grants no permission to activate buys. Retrospective development evidence "
                    "on 2023, a year KOD has studied before; NOT untouched validation. Simulation only: no orders. "
                    "2024 data is never opened, not even to finish year-end trades: positions open at the end of "
                    "2023-12-31 stay unresolved, valued at their last 2023 close."
                ),
                "question": "Under one fixed account and execution policy, does trading the frozen sequence model's daily "
                "shortlist end 2023 with more simulated equity than the frozen summary model's, the shuffled "
                "control's and cash, after modelled costs and under conservative assumptions?",
                "rankings": {
                    "source": "PREMOVE_SEQUENCE_v1 run 20261030T024900Z; its forecasts.csv.gz and shortlists.csv.gz are not "
                    "in the repository (owner's external archive KOD-premove-results-20261030.tar.gz), so they were "
                    "rebuilt with the frozen coefficients and temperatures, no fitting, and verified against "
                    "summary.json: both models' probability metrics to 1e-12 and every shortlist count, both "
                    "populations (rankings/VERIFY.json)",
                    "arms": {
                        "summary": "frozen summary-feature model (models.json)",
                        "sequence": "frozen sequence-enhanced model (models.json)",
                        "shuffled": "frozen shuffled-sequence control (PREMOVE_SHADOW_v1/control_model.json, fitted on "
                        "2020-2022 only; not part of the PR #19 run artifacts, included as the control)",
                        "cash": "no trades",
                    },
                    "population": (
                        "early (ret1 < 10% and ret5 < 20% on the signal day: the pre-move question's population, "
                        "primary in PREMOVE_SHADOW_v1; PR #19 reported it beside 'all'); five names per day, frozen "
                        "rank order (upside probability descending, ticker ascending); the account limits decide "
                        "which enter"
                    ),
                    "timing": "a ranking dated d uses bars through the close of UTC day d (premove_core.build_examples); "
                    "orders are decided after that close",
                },
                "policy": {name: p.record() for name, p in SCENARIOS.items()},
                "policy_text": [
                    "spot, long only, no leverage, no shorts; 10,000 simulated USDT per arm and scenario",
                    (
                        "order = market buy at the entry day's open for a USDT notional reserved at the decision, sized so the "
                        "loss if the stop fills at its level is 0.5% of equity at the decision"
                    ),
                    (
                        "aggregate planned risk <= 1.5%: the sum of the planned risk fractions (0.5% of equity at each order's "
                        "own decision) of pending orders and open positions, i.e. at most three at once"
                    ),
                    (
                        "at most 3 new orders per decision day; no second concurrent order or position in one coin; free cash "
                        "must cover the notional; candidates in frozen rank order"
                    ),
                    "entry fill = open x (1 + slippage); stop 5% below and target 10% above that fill",
                    (
                        "exits bar by bar, entry bar = bar 1: gap open <= stop exits at the open; gap open >= target exits at "
                        "the target; a bar touching both is resolved stop-first and counted; else the touched level; else the "
                        "close of bar 5; every exit pays slippage and fee"
                    ),
                    (
                        "missing or invalid bars: an entry without its bar is rejected; a held position waits; a time exit "
                        "rolls to the next valid close; positions open when the data ends are unresolved, valued at their "
                        "last valid close; orders whose entry day is after the data are unfilled"
                    ),
                    "no averaging down, stop widening, overrides or parameter search",
                ],
                "scenarios": {
                    "BASE": "next UTC open, 0.1% fee + 0.1% slippage per side (primary, idealized)",
                    "ENTRY_DELAY_1": "one additional bar before entry (predeclared sensitivity)",
                    "DOUBLE_COSTS": "0.2% fee + 0.2% slippage per side",
                    "DELAY_AND_DOUBLE": "both",
                },
                "primary": PRIMARY,
                "comparison": {
                    "headline": (
                        "end equity and net return of sequence versus summary under the same scenario; then "
                        "versus the shuffled control and cash"
                    ),
                    "uncertainty": f"paired circular moving-block bootstrap of daily equity-return differences ({BOOT}); descriptive",
                    "no_selection": "all four scenarios are reported; none is chosen after seeing results",
                },
                "predictive_vs_executable": (
                    "ranking quality (published shortlist hit counts) is reported beside account results and "
                    "never substituted for them"
                ),
                "honesty": [
                    (
                        "daily bars cannot show intraday order, queue position or depth: a touched price is not a "
                        "guaranteed fill; stop-first ambiguity is conservative but not exact"
                    ),
                    (
                        "the universe is today's archive catalogue: delisted coins are missing (survivorship flatters "
                        "buying)"
                    ),
                    "costs are assumptions, not measured fills",
                    "one year, few trades: no statistical certainty",
                ],
                "inputs": {"panel_sha256": PANEL_SHA256},
                "pins": {p: sha256_file(ROOT / p) for p in PINS},
            },
            indent=1,
        )
        + "\n"
    )
    print(PROTO.read_text())
    return 0


def block_bootstrap(diff: np.ndarray) -> dict:
    """Cumulative sum of daily return differences and its 95% interval from circular moving blocks."""
    rng = np.random.default_rng(BOOT["seed"])
    n, b = len(diff), BOOT["block_days"]
    starts = np.arange(n)  # circular blocks: every day equally likely to be drawn
    draws = []
    for _ in range(BOOT["draws"]):
        idx = np.concatenate(
            [np.arange(s, s + b) % n for s in rng.choice(starts, int(np.ceil(n / b)))]
        )[:n]
        draws.append(diff[idx].sum())
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "sum_of_daily_return_differences": float(diff.sum()),
        "lower95": float(lo),
        "upper95": float(hi),
        **BOOT,
    }


def trades_table(acct: cr.Account) -> pd.DataFrame:
    rows = {}
    for e in acct.events:
        if e["type"] == "DECISION":
            key = e.get("order_id") or f"skip-{e['signal_day']}-{e['ticker']}"
            rows[key] = {
                "signal_day": e["signal_day"],
                "ticker": e["ticker"],
                "rank": e["rank"],
                "decision": e["decision"],
                "notional": e.get("notional"),
                "planned_risk": e.get("planned_risk"),
                "equity_at_decision": e.get("equity_at_decision"),
            }
        elif e["type"] == "ENTRY":
            rows[e["order_id"]].update(
                entry_day=e["day"],
                entry_status=e["status"],
                raw_open=e.get("raw_open"),
                fill_price=e.get("fill_price"),
                units=e.get("units"),
                stop=e.get("stop"),
                target=e.get("target"),
                entry_fee=e.get("fee_usd"),
                entry_slippage=e.get("slippage_usd"),
            )
        elif e["type"] == "EXIT":
            rows[e["order_id"]].update(
                exit_day=e["day"],
                exit_reason=e["reason"],
                bar_index=e["bar_index"],
                exit_raw=e["raw_price"],
                exit_fill=e["fill_price"],
                proceeds=e["proceeds"],
                pnl=e["pnl"],
                net_return=e["net_return"],
                exit_fee=e["fee_usd"],
                exit_slippage=e["slippage_usd"],
                ambiguous=e.get("ambiguous", False),
            )
        elif e["type"] in ("UNRESOLVED", "UNFILLED"):
            rows[e["order_id"]].update(
                end_state=e["type"],
                end_value=e.get("value"),
                end_unrealized=e.get("unrealized"),
                valued_at=e.get("valued_at_close_of"),
            )
    return pd.DataFrame(rows.values())


def committed(path: Path) -> bool:
    """True when the file is tracked by git and identical to HEAD, so the recorded commit holds the code that ran."""
    rel = str(path.relative_to(ROOT.parent))
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=ROOT.parent,
        capture_output=True,
        check=False,
    )
    clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", rel],
        cwd=ROOT.parent,
        capture_output=True,
        check=False,
    )
    return tracked.returncode == 0 and clean.returncode == 0


def run(panel: Path) -> int:
    proto = json.loads(PROTO.read_text())
    if RUN.exists():
        sys.exit("error: the replay runs once (run/ exists)")
    for path, want in proto["pins"].items():
        if sha256_file(ROOT / path) != want:
            sys.exit(f"error: {path} changed since the freeze")
    for path in [PROTO, *(ROOT / p for p in proto["pins"])]:
        if not committed(path):
            sys.exit(f"error: {path} is not committed as it stands; commit the frozen code first")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    raw = pd.read_csv(panel)
    raw = raw[(raw["date"] >= FIRST.isoformat()) & (raw["date"] <= LAST.isoformat())]
    bars = cr.bars_from_panel(raw, FIRST, LAST)
    lists = pd.read_csv(HERE / "rankings/shortlists_2023.csv.gz")
    lists = lists[lists.population == POPULATION]
    files: dict[str, pd.DataFrame] = {}  # nothing is written until every arm passes its checks
    result = {
        "study": "CRYPTO_REPLAY_v1",
        "ran_at": utc_stamp(),
        "status": proto["status"],
        "scenarios": {},
    }
    for name, policy in SCENARIOS.items():
        result["scenarios"][name] = {"policy": policy.record(), "arms": {}}
        daily = {}
        for arm in (*ARMS, "cash"):
            sl = None if arm == "cash" else lists[lists.method == arm][["date", "ticker", "rank"]]
            acct = cr.run(sl, bars, FIRST, LAST, policy)
            again = cr.run(sl, bars, FIRST, LAST, policy)
            problems = cr.check_invariants(acct) + cr.audit_trades(acct, bars)
            cross = cr.tested_accounting_crosscheck(acct)
            if problems or not cross["match"] or cr.fingerprint(acct) != cr.fingerprint(again):
                sys.exit(f"error: {name}/{arm} failed its checks: {problems[:3]} {cross}")
            summary = cr.summarize(acct)
            summary.update(
                invariants="all hold",
                independent_trade_audit="every fill and exit re-derived from the raw bars: all match",
                tested_accounting_crosscheck=cross,
                repeat_run_identical=True,
                fingerprint=cr.fingerprint(acct),
                unresolved=[e for e in acct.events if e["type"] == "UNRESOLVED"],
                unfilled=[e for e in acct.events if e["type"] == "UNFILLED"],
            )
            result["scenarios"][name]["arms"][arm] = summary
            daily[arm] = pd.DataFrame(acct.daily)
            if arm != "cash":
                files[f"trades_{name}_{arm}.csv.gz"] = trades_table(acct)
            files[f"daily_{name}_{arm}.csv.gz"] = daily[arm]
        eq = {arm: daily[arm]["equity"].to_numpy() for arm in daily}
        ret = {
            arm: np.diff(np.concatenate([[cr.Policy().start_cash], v]))
            / np.concatenate([[cr.Policy().start_cash], v[:-1]])
            for arm, v in eq.items()
        }
        result["scenarios"][name]["comparisons"] = {
            f"{a}_minus_{b}": {
                "end_equity_difference": float(eq[a][-1] - eq[b][-1]),
                **block_bootstrap(ret[a] - ret[b]),
            }
            for a, b in (
                ("sequence", "summary"),
                ("sequence", "shuffled"),
                ("summary", "shuffled"),
                ("sequence", "cash"),
                ("summary", "cash"),
                ("shuffled", "cash"),
            )
        }
    verify = json.loads((HERE / "rankings/VERIFY.json").read_text())
    early = lists.assign(hit=(lists.label_known.astype(bool) & (lists.up_first == 1)))
    result["predictive_ranking_quality"] = {
        "published_early_shortlist_up_hits": {
            a: verify["checks"][f"shortlist/early/{a}"]["published"]["up_hits"]
            for a in ("summary", "sequence")
        },
        "rebuilt_early_shortlist_up_hits": {
            a: int(early[early.method == a].hit.sum()) for a in ARMS
        },
        "alerts_per_arm": int((early.method == "summary").sum()),
        "note": "an up hit = the price reached its volatility-scaled barrier (at least +10%) on a daily close within "
        "5 days before falling as far; it ignores costs, stops and whether the account could take the trade",
    }
    result["code"] = {
        "commit_at_run": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True
        ).stdout.strip(),
        "pins": proto["pins"],
    }
    RUN.mkdir()
    for fname, frame in files.items():
        frame.to_csv(RUN / fname, index=False)
    (RUN / "RESULT.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(
        json.dumps(
            {
                n: {
                    a: {
                        k: s["arms"][a][k]
                        for k in (
                            "end_equity",
                            "net_return",
                            "closed_trades",
                            "win_rate",
                            "max_drawdown",
                        )
                    }
                    for a in s["arms"]
                }
                for n, s in result["scenarios"].items()
            },
            indent=1,
            default=str,
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    return freeze(args.panel) if args.freeze else run(args.panel)


if __name__ == "__main__":
    sys.exit(main())

"""ADMISSION_v1: one cash-constrained 2023 comparison of the original admission policy versus a fresh-alert 10-15%
policy, through the audited CRYPTO_REPLAY_v1 account engine (research/ADMISSION_v1/protocol.json). Simulation only.

    python3 research/ADMISSION_v1/admission.py --freeze --panel <panel.csv.gz>
    python3 research/ADMISSION_v1/admission.py --panel <panel.csv.gz>

Baseline: the original frozen early top-five shortlist in score order (CRYPTO_REPLAY_v1, reproduced exactly).
Challenger: the SAME daily top five, filtered to alerts that are (a) in the band 0.10 <= p < 0.15, p being the model's
frozen temperature-adjusted upside probability, and (b) fresh: the coin was not in that model's original top five on
the previous calendar day. When the previous day's list is not in the frozen data (2023-01-01, whose 2022-12-31 list
was never frozen) or has no rows, freshness is unknown and the alert is not eligible. Vacancies are never refilled
from outside the original five; eligible alerts keep their original rank and tie-break. Everything else (cash,
sizing, reservations, the risk convention, the daily limit, duplicates, entries, stops, targets, time exits, costs,
gaps, ambiguous bars, missing data, year end) is the engine's, unchanged.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import crypto_replay as cr
from idxsig.provenance import sha256_file, utc_stamp

REPLAY = ROOT / "research/CRYPTO_REPLAY_v1"
PROTO, RUN = HERE / "protocol.json", HERE / "run"
PANEL_SHA256 = "f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766"
FIRST, LAST = date(2023, 1, 1), date(2023, 12, 31)
MODELS = ("summary", "sequence")
BAND = (0.10, 0.15)  # lower inclusive, upper exclusive
CASES = {"BASE": cr.Policy(), "DOUBLE_COSTS": cr.Policy(fee=0.002, slip=0.002)}
REPLAY_SCENARIO = {
    "BASE": "BASE",
    "DOUBLE_COSTS": "DOUBLE_COSTS",
}  # baseline must reproduce these fingerprints
BOOT = {"block_days": 10, "draws": 2000, "seed": 20261031}
PINS = (
    "idxsig/crypto_replay.py",
    "research/ADMISSION_v1/admission.py",
    "tests/test_admission.py",
    "research/CRYPTO_REPLAY_v1/protocol.json",
    "research/CRYPTO_REPLAY_v1/rankings/shortlists_2023.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/RESULT.json",
)


# ------------------------------------------------------------------------------------------------- the filter
def eligibility(shortlist: pd.DataFrame) -> pd.DataFrame:
    """One model's original top-five shortlist (date, ticker, rank, rank_score) with a `reason` per row: ELIGIBLE,
    BELOW_BAND, AT_OR_ABOVE_BAND, NOT_FRESH or FRESHNESS_UNKNOWN. Freshness looks only at the previous calendar
    day's original top five; it is checked before the band."""
    s = shortlist.copy()
    by_day = {d: set(g.ticker) for d, g in s.groupby("date")}
    reasons = []
    for d, t, p in zip(s.date, s.ticker, s.rank_score):
        prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
        if prev not in by_day:
            reasons.append("FRESHNESS_UNKNOWN")
        elif t in by_day[prev]:
            reasons.append("NOT_FRESH")
        elif p < BAND[0]:
            reasons.append("BELOW_BAND")
        elif p >= BAND[1]:
            reasons.append("AT_OR_ABOVE_BAND")
        else:
            reasons.append("ELIGIBLE")
    s["reason"] = reasons
    return s


def challenger(shortlist: pd.DataFrame) -> pd.DataFrame:
    """The eligible subset of the same top five, original ranks kept; nothing is added."""
    e = eligibility(shortlist)
    return e[e.reason == "ELIGIBLE"][["date", "ticker", "rank", "rank_score"]].reset_index(
        drop=True
    )


# ------------------------------------------------------------------------------------------------- protocol
def freeze(panel: Path) -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    proto = {
        "study_id": "ADMISSION_v1",
        "frozen_at": utc_stamp(),
        "asked_by": "Ace, 2026-10-31: one cash-constrained 2023 comparison, original admission vs fresh 10-15%",
        "status": (
            "retrospective development evidence on 2023 (already studied, including by SCORE_VALUE_v1, which "
            "suggested this rule); not validation; simulation only, no orders; 2024+ not opened"
        ),
        "models": "summary and sequence separately, frozen temperature-adjusted probabilities (rank_score), "
        "no refit or recalibration",
        "baseline": "the original frozen early top-five shortlist in score order; must reproduce CRYPTO_REPLAY_v1's "
        "BASE and DOUBLE_COSTS fingerprints for both models exactly",
        "challenger": {
            "band": "0.10 <= p < 0.15",
            "fresh": "the coin is not in the same model's original top five on the previous calendar day, "
            "regardless of yesterday's band",
            "freshness_unknown": "the previous calendar day has no frozen list (2023-01-01: no 2022-12-31 list was "
            "frozen) -> not eligible",
            "no_refill": "only alerts from the original five; vacancies stay empty",
            "order": "original rank and tie-break (score descending, ticker ascending)",
            "note": "tests the combined freshness-and-band policy, not priority alone",
        },
        "unchanged": (
            "everything else is idxsig.crypto_replay as audited: 10,000 USDT; notional = 0.5% of equity at the "
            "decision / loss fraction; cash reserved at the decision; risk convention = the sum of planned risk "
            "fractions (0.5% each) of pending and open positions <= 1.5%, i.e. at most three at once (the audited "
            "convention, kept and disclosed); at most 3 new orders per day; no duplicate coin; next UTC open entry; "
            "5% stop, 10% target, bar-5 close; gaps at the open; stop-first ambiguity; missing-data and year-end "
            "rules"
        ),
        "cases": {name: p.record() for name, p in CASES.items()},
        "deliverables": [
            (
                "per model and case: ending equity, net return, max daily-close drawdown, realized/unrealized, fees and "
                "slippage, turnover, mean exposure, alerts by eligibility reason, entries, skips and rejections"
            ),
            (
                "paired differences from baseline: end equity and a circular block bootstrap of daily return "
                f"differences {BOOT}"
            ),
            (
                "monthly returns of both policies; share of realized P&L from the 1, 3 and 5 largest winners and "
                "P&L without the 5 largest"
            ),
            "return per unit of mean exposure (to separate selection from simply holding less)",
        ],
        "verdict_rules": {
            "per_case": "IMPROVES if challenger ending equity > baseline and its max drawdown is not deeper; "
            "WORSE if ending equity < baseline; MIXED otherwise",
            "overall": "improved the 2023 account only if IMPROVES in both models and both cost cases; any other "
            "pattern is reported as it is; either way retrospective development evidence, not a proven edge",
        },
        "validation": [
            "baseline fingerprints equal CRYPTO_REPLAY_v1's",
            "every challenger order is in that day's original five, fresh and in the band",
            "invariants, independent trade audit, tested-accounting cross-check, identical repeat run",
            "pinned source hashes unchanged",
        ],
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(
        json.dumps(
            {k: proto[k] for k in ("study_id", "frozen_at", "challenger", "verdict_rules")},
            indent=1,
        )
    )
    return 0


# ------------------------------------------------------------------------------------------------- analysis
def block_bootstrap(diff: np.ndarray) -> dict:
    rng = np.random.default_rng(BOOT["seed"])
    n, b = len(diff), BOOT["block_days"]
    draws = []
    for _ in range(BOOT["draws"]):
        starts = rng.integers(0, n, int(np.ceil(n / b)))
        idx = np.concatenate([np.arange(s, s + b) % n for s in starts])[:n]
        draws.append(diff[idx].sum())
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "sum_of_daily_return_differences": float(diff.sum()),
        "lower95": float(lo),
        "upper95": float(hi),
        **BOOT,
    }


def daily_returns(daily: pd.DataFrame, start: float) -> np.ndarray:
    eq = daily.equity.to_numpy()
    prev = np.concatenate([[start], eq[:-1]])
    return eq / prev - 1


def monthly(daily: pd.DataFrame, start: float) -> dict:
    d = daily.assign(month=daily.day.str[:7])
    ends = d.groupby("month").equity.last()
    prev = ends.shift(1).fillna(start)
    return {m: float(ends[m] / prev[m] - 1) for m in ends.index}


def concentration(acct: cr.Account) -> dict:
    pnl = np.sort(np.array([e["pnl"] for e in acct.events if e["type"] == "EXIT"]))[::-1]
    total = float(pnl.sum()) if len(pnl) else 0.0
    wins = pnl[pnl > 0]
    out = {"realized": total, "largest_winners_usd": [float(x) for x in wins[:5]]}
    for k in (1, 3, 5):
        top = float(wins[:k].sum())
        out[f"top{k}_share_of_gross_wins"] = top / float(wins.sum()) if len(wins) else None
    out["realized_without_top5_winners"] = total - float(wins[:5].sum())
    return out


def summarize(acct: cr.Account) -> dict:
    s = cr.summarize(acct)
    s["return_per_mean_exposure"] = (
        s["net_return"] / s["mean_exposure"] if s["mean_exposure"] else None
    )
    return s


def verdict(base: dict, chal: dict) -> str:
    if chal["end_equity"] > base["end_equity"] and chal["max_drawdown"] >= base["max_drawdown"]:
        return "IMPROVES"
    if chal["end_equity"] < base["end_equity"]:
        return "WORSE"
    return "MIXED"


def run(panel: Path) -> int:
    proto = json.loads(PROTO.read_text())
    if RUN.exists():
        sys.exit("error: run/ exists; the comparison runs once")
    for path, want in proto["pins"].items():
        if sha256_file(ROOT / path) != want:
            sys.exit(f"error: {path} changed since the freeze")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    raw = pd.read_csv(panel)
    raw = raw[(raw["date"] >= FIRST.isoformat()) & (raw["date"] <= LAST.isoformat())]
    bars = cr.bars_from_panel(raw, FIRST, LAST)
    lists = pd.read_csv(REPLAY / "rankings/shortlists_2023.csv.gz")
    lists = lists[lists.population == "early"]
    replay = json.loads((REPLAY / "run/RESULT.json").read_text())
    res = {"study": "ADMISSION_v1", "ran_at": utc_stamp(), "status": proto["status"], "models": {}}
    files: dict[str, pd.DataFrame] = {}
    for model in MODELS:
        sl = lists[lists.method == model][["date", "ticker", "rank", "rank_score"]].reset_index(
            drop=True
        )
        elig = eligibility(sl)
        chal_sl = challenger(sl)
        files[f"eligibility_{model}.csv.gz"] = elig
        res["models"][model] = {
            "alerts": len(sl),
            "eligibility": elig.reason.value_counts().to_dict(),
            "eligible_days": int(chal_sl.date.nunique()),
            "cases": {},
        }
        allowed = set(zip(chal_sl.date, chal_sl.ticker))
        original = set(zip(sl.date, sl.ticker))
        for case, policy in CASES.items():
            out = {}
            accts = {}
            for policy_name, frame in (("baseline", sl), ("challenger", chal_sl)):
                acct = cr.run(frame[["date", "ticker", "rank"]], bars, FIRST, LAST, policy)
                again = cr.run(frame[["date", "ticker", "rank"]], bars, FIRST, LAST, policy)
                problems = cr.check_invariants(acct) + cr.audit_trades(acct, bars)
                cross = cr.tested_accounting_crosscheck(acct)
                if problems or not cross["match"] or cr.fingerprint(acct) != cr.fingerprint(again):
                    sys.exit(
                        f"error: {model}/{case}/{policy_name} failed its checks: {problems[:3]}"
                    )
                orders = [
                    e for e in acct.events if e["type"] == "DECISION" and e["decision"] == "ORDER"
                ]
                if policy_name == "challenger":
                    bad = [o for o in orders if (o["signal_day"], o["ticker"]) not in allowed]
                    if bad or not allowed <= original:
                        sys.exit(
                            f"error: {model}/{case}: the challenger admitted an ineligible alert: {bad[:3]}"
                        )
                else:
                    want = replay["scenarios"][REPLAY_SCENARIO[case]]["arms"][model]["fingerprint"]
                    if cr.fingerprint(acct) != want:
                        sys.exit(
                            f"error: {model}/{case}: the baseline does not reproduce CRYPTO_REPLAY_v1"
                        )
                s = summarize(acct)
                s.update(
                    fingerprint=cr.fingerprint(acct),
                    monthly=monthly(pd.DataFrame(acct.daily), policy.start_cash),
                    concentration=concentration(acct),
                    unresolved=[e for e in acct.events if e["type"] == "UNRESOLVED"],
                    unfilled=[e for e in acct.events if e["type"] == "UNFILLED"],
                    checks="invariants, trade audit, accounting cross-check and repeat run passed",
                )
                if policy_name == "baseline":
                    s["reproduces_crypto_replay_v1"] = True
                out[policy_name] = s
                accts[policy_name] = acct
                files[f"trades_{model}_{case}_{policy_name}.csv.gz"] = trades_table(acct)
                files[f"daily_{model}_{case}_{policy_name}.csv.gz"] = pd.DataFrame(acct.daily)
            b, c = out["baseline"], out["challenger"]
            rb = daily_returns(pd.DataFrame(accts["baseline"].daily), policy.start_cash)
            rc = daily_returns(pd.DataFrame(accts["challenger"].daily), policy.start_cash)
            out["paired"] = {
                "end_equity_difference": c["end_equity"] - b["end_equity"],
                "net_return_difference": c["net_return"] - b["net_return"],
                "max_drawdown_difference": c["max_drawdown"] - b["max_drawdown"],
                "mean_exposure_difference": c["mean_exposure"] - b["mean_exposure"],
                "daily_return_bootstrap": block_bootstrap(rc - rb),
                "monthly_difference": {m: c["monthly"][m] - b["monthly"][m] for m in b["monthly"]},
            }
            out["verdict"] = verdict(b, c)
            res["models"][model]["cases"][case] = out
    verdicts = [res["models"][m]["cases"][k]["verdict"] for m in MODELS for k in CASES]
    res["overall"] = (
        "The challenger improved the 2023 account in both models and both cost cases (retrospective development "
        "evidence, not a proven edge)."
        if all(v == "IMPROVES" for v in verdicts)
        else "The challenger did not improve the 2023 account in every model and cost case: "
        + ", ".join(
            f"{m}/{k} {res['models'][m]['cases'][k]['verdict']}" for m in MODELS for k in CASES
        )
        + "."
    )
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RUN.mkdir()
    for name, frame in files.items():
        frame.to_csv(RUN / name, index=False)
    (RUN / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (HERE / "REPORT.md").write_text(render(res), encoding="utf-8")
    print(res["overall"])
    return 0


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
                "entry_day": e.get("entry_day"),
            }
        elif e["type"] == "ENTRY":
            rows[e["order_id"]].update(
                entry_status=e["status"],
                raw_open=e.get("raw_open"),
                fill_price=e.get("fill_price"),
                units=e.get("units"),
            )
        elif e["type"] == "EXIT":
            rows[e["order_id"]].update(
                exit_day=e["day"],
                exit_reason=e["reason"],
                bar_index=e["bar_index"],
                exit_raw=e["raw_price"],
                pnl=e["pnl"],
                net_return=e["net_return"],
                fees=e["fee_usd"],
                slippage=e["slippage_usd"],
            )
        elif e["type"] in ("UNRESOLVED", "UNFILLED"):
            rows[e["order_id"]].update(end_state=e["type"], end_value=e.get("value"))
    return pd.DataFrame(rows.values())


# ------------------------------------------------------------------------------------------------- report
def pc(x, d=2):
    return "-" if x is None else f"{x * 100:+.{d}f}%"


def usd(x):
    return "-" if x is None else f"{x:,.2f}"


def render(res: dict) -> str:
    L = [
        "# ADMISSION_v1: original admission versus fresh alerts at 0.10 <= p < 0.15 (2023, cash-constrained)",
        "",
        f"Ran {res['ran_at']} at commit `{res['commit']}`. {res['status']}",
        "",
        (
            "Both policies use the audited CRYPTO_REPLAY_v1 account engine unchanged; the challenger only removes alerts "
            "from the same daily top five (never adds). Its risk convention is the audited one: at most three pending "
            "or open positions at 0.5% planned risk each."
        ),
        "",
        "## Verdict (fixed rules)",
        "",
        f"- {res['overall']}",
        "",
    ]
    for model, m in res["models"].items():
        L += [
            f"## {model}",
            "",
            (
                f"Alerts {m['alerts']}; eligibility of the original top five: {m['eligibility']}; days with an eligible "
                f"alert: {m['eligible_days']}."
            ),
            "",
        ]
        for case, c in m["cases"].items():
            b, h, p = c["baseline"], c["challenger"], c["paired"]
            L += [
                f"### {case}: verdict {c['verdict']}",
                "",
                (
                    "| Policy | End equity | Net return | Max drawdown | Realized | Unrealized | Fees | Slippage | Turnover | "
                    "Mean exposure | Return / exposure | Orders | Fills | Closed | Win rate |"
                ),
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for name, s in (("baseline", b), ("challenger", h)):
                L.append(
                    f"| {name} | {usd(s['end_equity'])} | {pc(s['net_return'])} | {pc(s['max_drawdown'])} "
                    f"({s['max_drawdown_day']}) | {usd(s['realized_pnl'])} | {usd(s['unrealized_pnl'])} | "
                    f"{usd(s['fees_usd'])} | {usd(s['slippage_usd'])} | {s['turnover']:.2f} | "
                    f"{s['mean_exposure']:.1%} | {s['return_per_mean_exposure']:.2f} | {s['orders']} | "
                    f"{s['fills']} | {s['closed_trades']} | {pc(s['win_rate'], 1)} |"
                )
            bb = p["daily_return_bootstrap"]
            L += [
                "",
                (
                    f"Paired (challenger minus baseline): end equity {p['end_equity_difference']:+,.2f} USDT; net return "
                    f"{pc(p['net_return_difference'])}; max drawdown {pc(p['max_drawdown_difference'])}; mean exposure "
                    f"{pc(p['mean_exposure_difference'], 1)}; summed daily return difference "
                    f"{pc(bb['sum_of_daily_return_differences'])} (95% {pc(bb['lower95'])} to {pc(bb['upper95'])})."
                ),
                "",
                (
                    f"Skips and rejections: baseline {b['skips_and_rejections']}; challenger {h['skips_and_rejections']}. "
                    f"Exit reasons: baseline {b['exit_reasons']}; challenger {h['exit_reasons']}."
                ),
                "",
                (
                    f"Concentration: baseline realized {usd(b['concentration']['realized'])}, without its 5 largest "
                    f"winners {usd(b['concentration']['realized_without_top5_winners'])}; challenger realized "
                    f"{usd(h['concentration']['realized'])}, without its 5 largest winners "
                    f"{usd(h['concentration']['realized_without_top5_winners'])}; challenger's largest winners "
                    f"{[round(x, 2) for x in h['concentration']['largest_winners_usd']]}."
                ),
                "",
                "| Month | Baseline | Challenger | Difference |",
                "|---|---:|---:|---:|",
            ]
            for mo, diff in p["monthly_difference"].items():
                L.append(f"| {mo} | {pc(b['monthly'][mo])} | {pc(h['monthly'][mo])} | {pc(diff)} |")
            L.append("")
    L += [
        "## Reading this",
        "",
        (
            "- Holding fewer positions lowers exposure and usually drawdown whatever the selection; 'return per unit of "
            "mean exposure' and the paired daily differences are shown so a smaller account is not mistaken for a "
            "better one."
        ),
        (
            "- 2023 was already studied and this rule was suggested by SCORE_VALUE_v1 on the same year: any improvement "
            "is retrospective development evidence, not a proven edge."
        ),
        "- This tests freshness and the band together, not priority alone.",
        "",
    ]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    return freeze(args.panel) if args.freeze else run(args.panel)


if __name__ == "__main__":
    sys.exit(main())

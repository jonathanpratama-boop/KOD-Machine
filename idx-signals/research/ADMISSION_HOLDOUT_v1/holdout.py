"""ADMISSION_HOLDOUT_v1: the one owner-authorised out-of-sample test of ADMISSION_v1's rule on 2024-01-01..2026-10-29.

    python3 research/ADMISSION_HOLDOUT_v1/holdout.py --freeze                         # before any 2024+ bar is read
    python3 research/ADMISSION_HOLDOUT_v1/collect.py --out data/raw/premove/holdout-2024-2026
    python3 research/ADMISSION_HOLDOUT_v1/holdout.py --collection data/raw/premove/holdout-2024-2026

Exactly ADMISSION_v1's comparison, moved to the new period: summary and sequence separately, scored with the frozen
PREMOVE_SEQUENCE_v1 coefficients and temperatures (no refit); baseline = the daily early top five in score order;
challenger = the same five filtered to fresh alerts (not in yesterday's original top five) with 0.10 <= p < 0.15
(research/ADMISSION_v1/admission.py, unchanged); the audited idxsig/crypto_replay engine unchanged; base and
doubled costs. Freshness on 2024-01-01 uses the 2023-12-31 top five computed the same way. Nothing else is run.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import crypto_replay as cr
from idxsig import premove, premove_shadow
from idxsig.premove_core import build_examples, prepare_panel
from idxsig.provenance import sha256_file, utc_stamp

_spec = importlib.util.spec_from_file_location(
    "admission", ROOT / "research/ADMISSION_v1/admission.py"
)
adm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adm)

PROTO, RUN = HERE / "protocol.json", HERE / "run"
FIRST, LAST = date(2024, 1, 1), date(2026, 10, 29)
SCORE_FROM = "2023-12-31"  # the day before FIRST: freshness evidence only, never traded
MODELS = adm.MODELS
CASES = adm.CASES
PINS = (
    "idxsig/crypto_replay.py",
    "idxsig/premove.py",
    "idxsig/premove_core.py",
    "idxsig/premove_shadow.py",
    "research/ADMISSION_v1/admission.py",
    "research/ADMISSION_v1/protocol.json",
    "research/ADMISSION_HOLDOUT_v1/holdout.py",
    "research/ADMISSION_HOLDOUT_v1/collect.py",
    "tools/collect_premove_crypto.py",
    "tests/test_admission_holdout.py",
    "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/models.json",
    "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/summary.json",
    "research/PREMOVE_SHADOW_v1/protocol.json",
)


def path_of(p: str) -> Path:
    return ROOT.parent / p if p.startswith("tools/") else ROOT / p


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    proto = {
        "study_id": "ADMISSION_HOLDOUT_v1",
        "frozen_at": utc_stamp(),
        "authorisation": "owner, 2026-10-31: 'I give you permission' to read 2024-01-01..2026-10-29 daily crypto "
        "bars for one frozen test of the fresh 10-15% admission rule",
        "frozen_before": "any 2024+ bar was collected for this study",
        "previously_read_2024_plus": [
            "CRYPTO_TUNE_v1: daily bars around +30% spike days, 2024-01..2026-10 (owner-authorised)",
            "BINANCE_ANN_1S_HOLDOUT: seconds-level windows around futures-launch announcements, 2024+",
            "no pre-move ranking or account study has read 2024+; the bars are not pristine, the question is",
        ],
        "window": {
            "decisions": f"{FIRST}..{LAST}",
            "warm_up_bars": "2023-07-01..2023-12-31 (features only)",
            "not_read": "2026-10-30 onward (PREMOVE_SHADOW_v1 prospective trial)",
        },
        "rule_under_test": "ADMISSION_v1 challenger, unchanged: same daily early top five, fresh (not in yesterday's "
        "original top five), 0.10 <= p < 0.15, no refill, original order",
        "baseline": "ADMISSION_v1 baseline, unchanged: the daily early top five in score order",
        "scoring": "frozen PREMOVE_SEQUENCE_v1 summary and sequence coefficients and temperatures on the collected "
        "panel (premove_core.build_examples, eligibility unchanged); top five per day by probability desc, ticker "
        "asc; the 2023-12-31 list supplies freshness for 2024-01-01 and is not traded",
        "engine": "idxsig/crypto_replay.py unchanged (audited), including its risk convention: at most three "
        "pending or open positions at 0.5% planned risk each",
        "cases": {name: p.record() for name, p in CASES.items()},
        "verdict": {
            "per_case": "IMPROVES if challenger ending equity > baseline and its max drawdown is not deeper; WORSE "
            "if ending equity < baseline; MIXED otherwise (ADMISSION_v1's rule)",
            "overall": "CONFIRMED only if IMPROVES in both models and both cost cases; otherwise NOT CONFIRMED",
            "also_reported": "paired circular block bootstrap of daily return differences, monthly and yearly "
            "returns, concentration, exposure and return per unit of exposure; baseline and challenger vs cash",
        },
        "honesty": [
            "the universe is today's archive catalogue (survivorship flatters buying)",
            "daily bars and modelled costs; touched prices are not guaranteed fills",
            "one test: no reruns, no variants, whatever the result",
        ],
        "pins": {p: sha256_file(path_of(p)) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(
        json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "window", "verdict")}, indent=1)
    )
    return 0


def shortlists(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The early top five per day from SCORE_FROM to LAST for each model, with rank and probability (rank_score)."""
    examples = build_examples(prepare_panel(panel, market="CRYPTO"))
    frame = premove.period(examples.frame, SCORE_FROM, LAST.isoformat())
    arms, temps = premove_shadow.load_arms(), premove_shadow.temperatures()
    for arm in MODELS:
        frame[f"{arm}_up"] = premove.probabilities(arms[arm].predict(frame), temps[arm])[:, 0]
    early = frame.loc[(frame.ret1 < 0.10) & (frame.ret5 < 0.20)].copy()
    early["date"] = early["date"].dt.strftime("%Y-%m-%d")
    out = {}
    for arm in MODELS:
        top = (
            early.sort_values(
                ["date", f"{arm}_up", "ticker"], ascending=[True, False, True], kind="stable"
            )
            .groupby("date", sort=True)
            .head(5)
            .copy()
        )
        top["rank"] = top.groupby("date").cumcount() + 1
        top["rank_score"] = top[f"{arm}_up"]
        out[arm] = top[["date", "ticker", "rank", "rank_score"]].reset_index(drop=True)
    return out


def holdout_lists(sl: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(baseline, challenger, eligibility) restricted to the traded window; freshness may look back to SCORE_FROM."""
    elig = adm.eligibility(sl)
    chal = adm.challenger(sl)
    keep = FIRST.isoformat()
    return (
        sl[sl.date >= keep].reset_index(drop=True),
        chal[chal.date >= keep].reset_index(drop=True),
        elig[elig.date >= keep].reset_index(drop=True),
    )


def yearly(monthly: dict) -> dict:
    out: dict[str, float] = {}
    for m, r in monthly.items():
        out[m[:4]] = (1 + out.get(m[:4], 0.0)) * (1 + r) - 1
    return out


def run(collection: Path) -> int:
    proto = json.loads(PROTO.read_text())
    if RUN.exists():
        sys.exit("error: run/ exists; the holdout runs once")
    for p, want in proto["pins"].items():
        if sha256_file(path_of(p)) != want:
            sys.exit(f"error: {p} changed since the freeze")
    manifest = json.loads((collection / "COLLECTION.json").read_text())
    panel_path = collection / manifest["panel"]
    if sha256_file(panel_path) != manifest["panel_sha256"] or manifest["bounds"] != [
        "2023-07-01",
        "2026-10-29",
    ]:
        sys.exit("error: the collection does not match its manifest or the authorised window")
    raw = pd.read_csv(panel_path)
    if raw.date.max() > LAST.isoformat():
        sys.exit("error: bars after the authorised window")
    lists = shortlists(raw)
    bars = cr.bars_from_panel(raw[raw.date >= FIRST.isoformat()], FIRST, LAST)
    res = {
        "study": "ADMISSION_HOLDOUT_v1",
        "ran_at": utc_stamp(),
        "collection": {
            k: manifest[k]
            for k in (
                "collected_at",
                "bounds",
                "panel_sha256",
                "universe_pairs",
                "usable_pairs",
                "rows",
            )
        }
        | {"failed_pairs": len(manifest["failed_pairs"])},
        "models": {},
    }
    files: dict[str, pd.DataFrame] = {}
    for model in MODELS:
        base_sl, chal_sl, elig = holdout_lists(lists[model])
        allowed = set(zip(chal_sl.date, chal_sl.ticker))
        if not allowed <= set(zip(base_sl.date, base_sl.ticker)):
            sys.exit("error: the challenger list is not a subset of the original five")
        files[f"shortlist_{model}.csv.gz"] = elig
        res["models"][model] = {
            "alerts": len(base_sl),
            "days": int(base_sl.date.nunique()),
            "eligibility": elig.reason.value_counts().to_dict(),
            "eligible_days": int(chal_sl.date.nunique()),
            "cases": {},
        }
        for case, policy in CASES.items():
            out, accts = {}, {}
            for name, frame in (("baseline", base_sl), ("challenger", chal_sl)):
                acct = cr.run(frame[["date", "ticker", "rank"]], bars, FIRST, LAST, policy)
                again = cr.run(frame[["date", "ticker", "rank"]], bars, FIRST, LAST, policy)
                problems = cr.check_invariants(acct) + cr.audit_trades(acct, bars)
                cross = cr.tested_accounting_crosscheck(acct)
                if problems or not cross["match"] or cr.fingerprint(acct) != cr.fingerprint(again):
                    sys.exit(f"error: {model}/{case}/{name} failed its checks: {problems[:3]}")
                if name == "challenger":
                    bad = [
                        e
                        for e in acct.events
                        if e["type"] == "DECISION"
                        and e["decision"] == "ORDER"
                        and (e["signal_day"], e["ticker"]) not in allowed
                    ]
                    if bad:
                        sys.exit(f"error: the challenger admitted an ineligible alert: {bad[:2]}")
                s = adm.summarize(acct)
                s.update(
                    fingerprint=cr.fingerprint(acct),
                    monthly=adm.monthly(pd.DataFrame(acct.daily), policy.start_cash),
                    concentration=adm.concentration(acct),
                    unresolved=[e for e in acct.events if e["type"] == "UNRESOLVED"],
                    unfilled=[e for e in acct.events if e["type"] == "UNFILLED"],
                )
                s["yearly"] = yearly(s["monthly"])
                out[name], accts[name] = s, acct
                files[f"trades_{model}_{case}_{name}.csv.gz"] = adm.trades_table(acct)
                files[f"daily_{model}_{case}_{name}.csv.gz"] = pd.DataFrame(acct.daily)
            b, c = out["baseline"], out["challenger"]
            rb = adm.daily_returns(pd.DataFrame(accts["baseline"].daily), policy.start_cash)
            rc = adm.daily_returns(pd.DataFrame(accts["challenger"].daily), policy.start_cash)
            out["paired"] = {
                "end_equity_difference": c["end_equity"] - b["end_equity"],
                "net_return_difference": c["net_return"] - b["net_return"],
                "max_drawdown_difference": c["max_drawdown"] - b["max_drawdown"],
                "mean_exposure_difference": c["mean_exposure"] - b["mean_exposure"],
                "daily_return_bootstrap": adm.block_bootstrap(rc - rb),
                "months_challenger_ahead": int(
                    sum(c["monthly"][m] > b["monthly"][m] for m in b["monthly"])
                ),
                "months": len(b["monthly"]),
            }
            out["verdict"] = adm.verdict(b, c)
            res["models"][model]["cases"][case] = out
    verdicts = {f"{m}/{k}": res["models"][m]["cases"][k]["verdict"] for m in MODELS for k in CASES}
    res["verdicts"] = verdicts
    res["overall"] = (
        "CONFIRMED" if all(v == "IMPROVES" for v in verdicts.values()) else "NOT CONFIRMED"
    )
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RUN.mkdir()
    for name, frame in files.items():
        frame.to_csv(RUN / name, index=False)
    (RUN / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (HERE / "REPORT.md").write_text(render(res), encoding="utf-8")
    print(res["overall"], verdicts)
    return 0


def rpe(s: dict) -> str:
    v = s["return_per_mean_exposure"]
    return "n/a" if v is None else f"{v:+.2f}"


def render(res: dict) -> str:
    pc, usd = adm.pc, adm.usd
    col = res["collection"]
    L = [
        "# ADMISSION_HOLDOUT_v1: the fresh 10-15% rule on 2024-01-01..2026-10-29",
        "",
        (
            f"Ran {res['ran_at']} at commit `{res['commit']}`. Owner-authorised, one run, frozen before any 2024+ bar "
            f"was collected. Panel {col['panel_sha256'][:12]}..., {col['rows']:,} bars, {col['usable_pairs']} pairs "
            f"({col['failed_pairs']} failed requests)."
        ),
        "",
        f"## Verdict: {res['overall']}",
        "",
        *[f"- {k}: {v}" for k, v in res["verdicts"].items()],
        "",
    ]
    for model, m in res["models"].items():
        L += [
            f"## {model}",
            "",
            (
                f"{m['alerts']} alerts over {m['days']} days; eligibility {m['eligibility']}; "
                f"days with an eligible alert {m['eligible_days']}."
            ),
            "",
        ]
        for case, c in m["cases"].items():
            b, h, p = c["baseline"], c["challenger"], c["paired"]
            bb = p["daily_return_bootstrap"]
            L += [
                f"### {case}: {c['verdict']}",
                "",
                "| Policy | End equity | Net return | Max drawdown | Fills | Closed | Mean exposure | Return / exposure "
                "| Fees + slippage | Realized | Unrealized | "
                + " | ".join(sorted(b["yearly"]))
                + " |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
                + "---:|" * len(b["yearly"]),
            ]
            for name, s in (("baseline", b), ("challenger", h)):
                L.append(
                    f"| {name} | {usd(s['end_equity'])} | {pc(s['net_return'])} | {pc(s['max_drawdown'])} | "
                    f"{s['fills']} | {s['closed_trades']} | {s['mean_exposure']:.1%} | "
                    f"{rpe(s)} | {usd(s['fees_usd'] + s['slippage_usd'])} | "
                    f"{usd(s['realized_pnl'])} | {usd(s['unrealized_pnl'])} | "
                    + " | ".join(pc(s["yearly"][y]) for y in sorted(b["yearly"]))
                    + " |"
                )
            L += [
                "",
                (
                    f"Challenger minus baseline: {p['end_equity_difference']:+,.2f} USDT; drawdown "
                    f"{pc(p['max_drawdown_difference'])}; ahead in {p['months_challenger_ahead']} of {p['months']} "
                    f"months; summed daily return difference {pc(bb['sum_of_daily_return_differences'])} (95% "
                    f"{pc(bb['lower95'])} to {pc(bb['upper95'])}). Without its 5 largest winners the challenger "
                    f"realized {usd(h['concentration']['realized_without_top5_winners'])} (baseline "
                    f"{usd(b['concentration']['realized_without_top5_winners'])}). Skips: challenger "
                    f"{h['skips_and_rejections']}."
                ),
                "",
            ]
    L += [
        "## Limits",
        "",
        "- Survivorship: today's archive catalogue. Daily bars, modelled costs.",
        (
            "- The 2024+ bars were read before by CRYPTO_TUNE_v1 (spike days) and BINANCE_ANN_1S_HOLDOUT (announcement "
            "windows); this question had not been asked of them."
        ),
        "",
    ]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--collection", type=Path)
    args = ap.parse_args()
    if args.freeze:
        return freeze()
    if not args.collection:
        sys.exit("error: --collection is required")
    return run(args.collection)


if __name__ == "__main__":
    sys.exit(main())

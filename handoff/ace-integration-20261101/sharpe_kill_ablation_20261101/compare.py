"""Frozen comparison for the Sharpe-kill ablation (reused-data diagnostic). No strategy logic, no network.

Reads the reproduced baseline outputs (published engine) and the challenger outputs (challenger engine), replays
every trend journal with the engine that produced it (core Ledger: hash chain, provenance pins, deterministic
replay), and reports the pre-declared metrics and reading rule from PROTOCOL.md.

  python3 compare.py --baseline-dir B --challenger-dir C --published-engine E1 --challenger-engine E2 \
      --json COMPARISON.json --md COMPARISON.md
"""
import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
from datetime import date
from pathlib import Path

PARTS = ("development", "validation")
POLICY = "TREND_V2_SHARED"
BENCH = ("CASH", "PASSIVE_50_50_RISK_MATCHED", "CONVENTIONAL_50_50_BUY_HOLD_NO_KILL")
INITIAL = 10000.0
MATERIAL_NAV = 1000.0   # USDT = 10% of each partition's starting cash (PROTOCOL.md reading rule)
MATERIAL_DD = 0.05      # 5 percentage points of sampled maximum drawdown
CLASSIFICATION = "REUSED_DATA_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION"


def load_engine(directory, name):
    # The core imports daily_adapter by name during replay. daily_adapter does not import the core and is
    # byte-identical in both engines (checked in main), so one copy on sys.path serves both.
    if str(directory) not in sys.path:
        sys.path.append(str(directory))
    spec = importlib.util.spec_from_file_location(name, Path(directory) / "daily_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rows_of(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def extract(rows):
    daily, fills = [], []
    for x in rows:
        op, res = x["command"]["op"], x["result"]
        if op == "daily":
            a = res["account"]
            sh = res.get("trailing_sharpe") or {}
            daily.append({"date": x["command"]["date"], "nav": float(a["nav"]), "gross": float(a["gross_fraction"]),
                          "kill": res.get("kill"), "mdd": float(res["maximum_observed_drawdown"]),
                          "sharpe_status": sh.get("status"), "sharpe_negative": bool(sh.get("negative"))})
        elif op == "observe":
            for f in res.get("fills", []):
                fills.append({"at": f["model_observed_at"], "symbol": f["symbol"], "side": f["side"],
                              "quantity": float(f["quantity"]), "price": float(f["price"]), "fee": float(f["fee"]),
                              "intent_id": f["intent_id"]})
    return daily, fills


def invested_stats(daily):
    rets = [b["nav"] / a["nav"] - 1 for a, b in zip(daily, daily[1:]) if a["gross"] > 0]
    total = len(daily) - 1
    out = {"return_days": total, "invested_days": len(rets), "time_invested_fraction": len(rets) / total if total else 0}
    if len(rets) > 1:
        out.update(invested_mean_daily=statistics.mean(rets), invested_daily_vol=statistics.stdev(rets),
                   invested_vol_annualized=statistics.stdev(rets) * 365 ** 0.5)
    return out


def close_drawdown(daily):
    peak, worst, worst_date, peak_date, worst_peak_date = INITIAL, 0.0, None, daily[0]["date"], None
    for d in daily:
        if d["nav"] > peak:
            peak, peak_date = d["nav"], d["date"]
        dd = (peak - d["nav"]) / peak
        if dd > worst:
            worst, worst_date, worst_peak_date = dd, d["date"], peak_date
    return {"max_drawdown_daily_open_marks": worst, "trough_date": worst_date, "peak_date": worst_peak_date}


def year_end(daily):
    out = {}
    for d in daily:
        out[d["date"][:4]] = round(d["nav"], 2)
    return out


def runs(dates):
    """Count separate runs of consecutive dates."""
    n, prev = 0, None
    for s in dates:
        d = date.fromisoformat(s)
        if prev is None or (d - prev).days != 1:
            n += 1
        prev = d
    return n


def first_divergence(a_rows, b_rows):
    for i, (x, y) in enumerate(zip(a_rows, b_rows)):
        if x["id"] != y["id"] or x["result"] != y["result"] or x["state_sha256"] != y["state_sha256"]:
            return {"index": i, "baseline_op": x["id"], "challenger_op": y["id"],
                    "date": x["command"].get("date") or x["command"].get("at")}
    if len(a_rows) != len(b_rows):
        i = min(len(a_rows), len(b_rows))
        return {"index": i, "note": "one journal is a prefix of the other", "baseline_rows": len(a_rows), "challenger_rows": len(b_rows)}
    return None


def summary_view(s):
    return {"end_nav": float(s["end_account"]["nav"]), "growth": float(s["growth"]), "CAGR": float(s["CAGR"]),
            "sampled_max_drawdown": float(s["sampled_max_drawdown"]), "daily_vol_annualized": s["daily_vol_annualized"],
            "daily_Sharpe": s["daily_Sharpe"], "fills": s["fills"], "paid_fees": float(s["paid_fees"]),
            "normalized_turnover": float(s["normalized_turnover"]), "mean_exposure": float(s["exposure"]["mean"]),
            "invested_samples": s["exposure"]["invested_samples"], "samples": s["exposure"]["samples"],
            "kill": s["kill"], "liquidation": s["liquidation"], "remaining_holdings": s["liquidation"]["remaining_holdings"],
            "journal_sha256": s["journal"]["journal_sha256"]}


def account(path, summary_path, engine):
    rows = rows_of(path)
    state = engine.Ledger(path).state()          # verifies chain, provenance pins and deterministic replay
    daily, fills = extract(rows)
    s = summary_view(json.loads(Path(summary_path).read_text()))
    cancelled = [{"id": o["id"], "symbol": o["symbol"], "side": o["side"], "made_at": o.get("made_at")}
                 for o in state["intents"] if o["status"] == "CANCELLED" and o.get("cancellation_reason") == "KILLED"]
    liq = [f for f in fills if f["intent_id"].startswith("liquidate:")]
    neg = [d["date"] for d in daily if d["sharpe_negative"]]
    eligible = next((d["date"] for d in daily if d["sharpe_status"] not in (None, "INSUFFICIENT_90_RETURNS")), None)
    kill_day = next((d for d in daily if d["kill"]), None)
    return {"rows": rows, "daily": daily, "fills": fills, "summary": s, "invested": invested_stats(daily),
            "close_drawdown": close_drawdown(daily), "year_end_nav": year_end(daily),
            "kill_cancelled_intents": cancelled, "kill_liquidation_fills": liq,
            "kill_daily": ({"date": kill_day["date"], "nav": kill_day["nav"], "mdd_at_kill": kill_day["mdd"],
                            "growth_at_kill": kill_day["nav"] / INITIAL - 1} if kill_day else None),
            "sharpe_rule_first_able_to_fire": eligible,
            "sharpe_negative_days": len(neg), "sharpe_negative_first": neg[0] if neg else None,
            "sharpe_negative_runs": runs(neg)}


def reading(base, chal):
    dnav = chal["summary"]["end_nav"] - base["summary"]["end_nav"]
    ddd = chal["summary"]["sampled_max_drawdown"] - base["summary"]["sampled_max_drawdown"]
    suppressed = dnav >= MATERIAL_NAV
    protected = ddd >= MATERIAL_DD or dnav <= -MATERIAL_NAV
    label = ("BOTH" if suppressed and protected else "SUPPRESSED_RETURNS" if suppressed
             else "PROTECTED_CAPITAL" if protected else "NO_MATERIAL_EFFECT")
    return {"end_nav_difference_challenger_minus_baseline": dnav,
            "max_drawdown_difference_challenger_minus_baseline": ddd,
            "suppressed_returns": suppressed, "protected_capital": protected, "label": label,
            "rule": f"suppressed if challenger end NAV >= baseline + {MATERIAL_NAV:.0f}; protected if challenger "
                    f"sampled max drawdown >= baseline + {MATERIAL_DD:.0%} or challenger end NAV <= baseline - {MATERIAL_NAV:.0f}"}


def public(acct):
    return {k: v for k, v in acct.items() if k not in ("rows", "daily", "fills")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("--baseline-dir", "--challenger-dir", "--published-engine", "--challenger-engine", "--json", "--md"):
        p.add_argument(name, type=Path, required=True)
    args = p.parse_args()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    if sha(args.published_engine / "daily_adapter.py") != sha(args.challenger_engine / "daily_adapter.py"):
        raise SystemExit("daily_adapter.py differs between engines")
    pub = load_engine(args.published_engine, "kod_published_core")
    cha = load_engine(args.challenger_engine, "kod_challenger_core")
    out = {"classification": CLASSIFICATION, "partitions": {}}
    for part in PARTS:
        b = account(args.baseline_dir / f"{part}_{POLICY}.jsonl", args.baseline_dir / f"{part}_{POLICY}_summary.json", pub)
        c = account(args.challenger_dir / f"{part}_{POLICY}.jsonl", args.challenger_dir / f"{part}_{POLICY}_summary.json", cha)
        div = first_divergence(b["rows"], c["rows"])
        div_date = None
        for x, y in zip(b["daily"], c["daily"]):
            if x["nav"] != y["nav"]:
                div_date = x["date"]
                break
        after = div["date"][:10] if div else None
        extra = {"baseline_fills_total": len(b["fills"]), "challenger_fills_total": len(c["fills"]),
                 "additional_fills": len(c["fills"]) - len(b["fills"]),
                 "baseline_fills_after_divergence": sum(1 for f in b["fills"] if after and f["at"][:10] >= after),
                 "challenger_fills_after_divergence": sum(1 for f in c["fills"] if after and f["at"][:10] >= after)}
        bench = {}
        for pol in BENCH:
            bench[pol] = summary_view(json.loads((args.baseline_dir / f"{part}_{pol}_summary.json").read_text()))
        out["partitions"][part] = {"baseline": public(b), "challenger": public(c), "first_divergence": div,
                                   "first_daily_nav_difference": div_date, "trades": extra,
                                   "reading": reading(b, c), "benchmarks_from_published_run": bench}
    args.json.write_text(json.dumps(out, indent=2, default=str) + "\n")
    args.md.write_text(render(out))
    print(json.dumps({k: v["reading"]["label"] for k, v in out["partitions"].items()}))


def pct(x):
    return "n/a" if x is None else f"{x * 100:+.2f}%"


def render(out):
    L = ["# Sharpe-kill ablation: comparison", "", f"Classification: **{out['classification']}**. Reused historical data; "
         "describes what the negative-90-day-Sharpe kill did on this history. It cannot show that removing it would "
         "improve future returns.", ""]
    for part, r in out["partitions"].items():
        b, c = r["baseline"], r["challenger"]
        bs, cs = b["summary"], c["summary"]
        L += [f"## {part}", "",
              "| | Baseline (both kills) | Challenger (drawdown kill only) |", "|---|---:|---:|",
              f"| Ending NAV (USDT, from 10,000) | {bs['end_nav']:,.2f} | {cs['end_nav']:,.2f} |",
              f"| Total growth | {pct(bs['growth'])} | {pct(cs['growth'])} |",
              f"| Annualised growth | {pct(bs['CAGR'])} | {pct(cs['CAGR'])} |",
              f"| Sampled max drawdown | {pct(bs['sampled_max_drawdown'])} | {pct(cs['sampled_max_drawdown'])} |",
              f"| Annualised vol, whole partition | {pct(bs['daily_vol_annualized'])} | {pct(cs['daily_vol_annualized'])} |",
              f"| Daily Sharpe (annualised) | {bs['daily_Sharpe']:.2f} | {cs['daily_Sharpe']:.2f} |",
              f"| Time invested | {b['invested']['invested_days']} of {b['invested']['return_days']} days | "
              f"{c['invested']['invested_days']} of {c['invested']['return_days']} days |",
              f"| Annualised vol while invested | {pct(b['invested'].get('invested_vol_annualized'))} | "
              f"{pct(c['invested'].get('invested_vol_annualized'))} |",
              f"| Fills / fees (USDT) | {bs['fills']} / {bs['paid_fees']:,.2f} | {cs['fills']} / {cs['paid_fees']:,.2f} |",
              f"| Kill | {fmt_kill(bs['kill'])} | {fmt_kill(cs['kill'])} |", "",
              f"First divergence: {r['first_divergence']}. First daily NAV difference: {r['first_daily_nav_difference']}.",
              f"Additional fills in challenger: {r['trades']['additional_fills']}.",
              f"Days the removed Sharpe rule would have fired (challenger): {c['sharpe_negative_days']} "
              f"in {c['sharpe_negative_runs']} separate runs, first {c['sharpe_negative_first']}.",
              f"Reading (pre-declared): **{r['reading']['label']}** "
              f"(end NAV difference {r['reading']['end_nav_difference_challenger_minus_baseline']:+,.2f} USDT; "
              f"max drawdown difference {r['reading']['max_drawdown_difference_challenger_minus_baseline'] * 100:+.2f} pp).", "",
              "Year-end NAV (last daily open mark of each year):", "",
              "| Year | Baseline | Challenger |", "|---|---:|---:|"]
        for y in sorted(set(b["year_end_nav"]) | set(c["year_end_nav"])):
            L.append(f"| {y} | {b['year_end_nav'].get(y, 0):,.2f} | {c['year_end_nav'].get(y, 0):,.2f} |")
        L += ["", "Benchmarks from the published run (different risk policies; see notes):", "",
              "| Policy | Ending NAV | Growth | Sampled max drawdown | Mean exposure | Kill |", "|---|---:|---:|---:|---:|---|"]
        for pol, s in r["benchmarks_from_published_run"].items():
            L.append(f"| {pol} | {s['end_nav']:,.2f} | {pct(s['growth'])} | {pct(s['sampled_max_drawdown'])} | "
                     f"{s['mean_exposure'] * 100:.1f}% | {fmt_kill(s['kill'])} |")
        L.append("")
    return "\n".join(L) + "\n"


def fmt_kill(k):
    return "none" if not k else f"{k['at'][:10]} {k['reason']}"


if __name__ == "__main__":
    main()

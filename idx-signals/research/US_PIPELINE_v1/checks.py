"""US pipeline milestone: targeted checks of which existing results the repairs affect.

Run from idx-signals with the code committed (write_run refuses a dirty tree):
    python3 research/US_PIPELINE_v1/checks.py
Writes checks.json (and appends one research run, the FILL-B-v2 rerun, to results/). Nothing
existing is edited. Inputs are the committed v3 repair panel and its schedule/coverage files.
"""
import gc
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import exec_us, global_panel, paper, us_actions  # noqa: E402
from idxsig import rules as rule_registry  # noqa: E402
from idxsig.backtest import RunConfig, _dense, run, signals  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402
from idxsig.results import write_run  # noqa: E402

HERE = Path(__file__).parent
PANEL = ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json"
RAW = ROOT / "data/manifests/yahoo_us-20261008T001812Z.jsonl"
SCHEDULES = {"v3 (shares)": "data/corporate_actions/us_splits-shares-20261008T114309Z.json",
             "v2 (Codex reaudit)": "data/corporate_actions/us_splits-reaudit-20261008T112522Z.json"}
COVERAGE = "data/corporate_actions/us_splits-coverage-reaudit-20261008T112522Z.json"
FILL_B_RUN = "20261008T115656Z_MOONSHOT_E2_US_D1_v1"


def reconciliation(tickers) -> dict:
    events = us_actions.yahoo_events(RAW)
    cov = json.loads((ROOT / COVERAGE).read_text())
    out = {}
    for label, path in SCHEDULES.items():
        smeta = json.loads((ROOT / path).read_text())
        us_actions.check_bound_inputs(RAW, smeta, cov)  # raises if any input is not the bound one
        sched = pd.read_csv(ROOT / smeta["schedule"], dtype={"ticker": str}, keep_default_na=False, na_values=[""])
        accepted = tuple(sorted(set(smeta.get("accepted_statuses", us_actions.ACCEPTED)) & set(us_actions.RESEARCH_ACCEPTED)))
        window = (smeta.get("share_count_corroboration") or {}).get("window_end")
        recon = us_actions.reconcile_schedule(events, sched, smeta["effective_after"], tickers, accepted, "2023-12-29", window)
        all_scope = events[events["effective_session"] > smeta["effective_after"]]
        out[label] = {"inputs_bound_by_sha256": True, "events_relevant_to_panel_names": int(len(recon)),
                      "status_counts": recon["status"].value_counts().to_dict(),
                      "unresolved": int(recon["status"].isin(us_actions.UNRESOLVED).sum()),
                      "provider_events_after_window_start_all_names": int(len(all_scope)),
                      "of_which_without_any_record_and_not_panel_names": int(
                          (~all_scope.set_index(us_actions.KEY).index.isin(
                              sched.set_index(us_actions.KEY).index)).sum())}
    return out


def fill_b_rerun(frame, meta) -> dict:
    old = ROOT / "results/runs" / FILL_B_RUN
    old_summary = json.loads((old / "summary.json").read_text())
    cfg = RunConfig(**{**old_summary["config"], "fill_model": "B2"})
    result = run(cfg, frame, meta)
    new = write_run(result, commit=False)
    s = result["summary"]
    before = pd.read_csv(old / "trades.csv.gz", keep_default_na=False).set_index(["ticker", "signal_date"])
    after = result["trades"].set_index(["ticker", "signal_date"])
    both = before.index.intersection(after.index)
    trans = pd.DataFrame({"old": before.loc[both, "status"], "new": after.loc[both, "status"]}).value_counts()
    rec = {"previous_run": FILL_B_RUN, "previous_fill_model": "B (FILL-B-v1)", "run": new.name, "fill_model": "B2",
           "scored": s["rule_trades"]["scored"], "previous_scored": old_summary["rule_trades"]["scored"],
           "rule_avg_net_return": s["rule_trades"]["avg_net_return"],
           "previous_rule_avg_net_return": old_summary["rule_trades"]["avg_net_return"],
           "matched_random": s["random_matched"]["avg_net_return"],
           "previous_matched_random": old_summary["random_matched"]["avg_net_return"],
           "status_transitions": {f"{a} -> {b}": int(n) for (a, b), n in trans.items() if a != b}}
    del result
    gc.collect()
    return rec


def approval_resolution() -> dict:
    """What the old lookup (last matching run in RUNS.jsonl) resolved to, against the pins."""
    old = {}
    for market, rule_id, window in (("IDX", "MOONSHOT_E1_D1", paper.VALIDATION_WINDOWS["IDX"]),
                                     ("US", "MOONSHOT_E2_US_D1", paper.VALIDATION_WINDOWS["US"]),
                                     ("CRYPTO", "MOONSHOT_E2_CRYPTO_D1", paper.VALIDATION_WINDOWS["CRYPTO"])):
        matches = []
        for line in (ROOT / "results/RUNS.jsonl").read_text().splitlines():
            r = json.loads(line)
            if rule_id not in r.get("dir", ""):
                continue
            s = json.loads((ROOT / r["dir"] / "summary.json").read_text())
            if (s["config"]["start"], s["config"]["end"]) == tuple(window):
                matches.append(s["run_id"])
        old[market] = {"matching_runs_in_order": matches, "old_lookup_resolved_to": matches[-1] if matches else None,
                       "pin": paper.APPROVAL_PINS.get(market)}
    scans = [{"scan_id": r["scan_id"], "market": r.get("market", "IDX"),
              "cited_run": ((r.get("validation_evidence") or {}).get("trading") or {}).get("run_id")}
             for r in paper.ledger_lines() if r["type"] == "SCAN"]
    decisions = Counter(r["decision"] for r in paper.ledger_lines() if r["type"] == "DECISION")
    return {"by_market": old, "recorded_scans": scans, "recorded_decisions": dict(decisions),
            "note": "no recorded decision was a BUY; the change of resolution never altered a decision"}


def paper_stop_distances() -> list:
    rows = []
    for r in paper.ledger_lines():
        if r["type"] != "DECISION" or "max_chase_price" not in (r.get("plan") or {}):
            continue
        p = r["plan"]
        rows.append({"decision_id": r["decision_id"], "policy": r["policy"]["policy_id"], "decision": r["decision"],
                     "signal_close": r["verified_price"]["close"], "invalidation": p["invalidation"],
                     "max_chase_price": p["max_chase_price"],
                     "stop_distance_from_signal_close": 1 - p["invalidation"] / r["verified_price"]["close"],
                     "stop_distance_at_max_permitted_entry": 1 - p["invalidation"] / p["max_chase_price"],
                     "violates_5pct_rule_at_max_entry": 1 - p["invalidation"] / p["max_chase_price"] > 0.05})
    return rows


def replay_2023(frame, meta) -> dict:
    """The 2023 signals of MOONSHOT_E2_US_D1 through EXEC-US-v1 (PAPER-POLICY-v4's US execution),
    quarantined names included and labelled. Descriptive: no random baseline, not approval evidence."""
    full = Market.from_panel(frame, price_limits=False)
    full = full.with_units(_dense(full, frame, "unit_factor", 1.0))
    lo, hi = full.bounds("2023-01-01", "2023-12-31")
    rule = rule_registry.get("MOONSHOT_E2_US_D1")
    sig, _ = signals(rule, full.slice(lo, hi), None)
    tick_idx, sig_idx = np.nonzero(sig == 1)
    pairs = [(int(n), int(s) + lo) for n, s in zip(tick_idx, sig_idx)]
    rows = exec_us.replay(full, pairs, exec_us.signal_low_invalidation)
    quarantined = set(meta["unit_quarantine"]["tickers"])
    flat = []
    for r in rows:
        res, plan = r["result"], r["plan"]
        flat.append({"ticker": r["ticker"], "signal_session": r["signal_session"], "status": res["status"],
                     "quarantined_by_later_records": r["ticker"] in quarantined,
                     "signal_close": plan["signal_close"], "invalidation": plan["invalidation"],
                     "max_entry": plan["max_entry"], "shares": plan.get("shares"),
                     "entry": res.get("entry_price_as_traded"), "exit": res.get("exit_price_as_traded"),
                     "exit_reason": res.get("exit_reason"), "net_return": res.get("net_return"),
                     "net_pnl_usd": res.get("net_pnl_usd")})
    df = pd.DataFrame(flat)
    df.to_csv(HERE / "replay_2023_exec_us_v1.csv", index=False, float_format="%.10g", lineterminator="\n")
    filled = df[df["status"] == "FILLED"]
    summary = {"signals": int(len(df)), "status_counts": df["status"].value_counts().to_dict(),
               "filled": int(len(filled)),
               "filled_avg_net_return": float(filled["net_return"].mean()) if len(filled) else None,
               "filled_median_net_return": float(filled["net_return"].median()) if len(filled) else None,
               "filled_excluding_quarantined": int((~filled["quarantined_by_later_records"]).sum()),
               "filled_avg_net_excluding_quarantined": float(filled.loc[~filled["quarantined_by_later_records"],
                                                                         "net_return"].mean()) if len(filled) else None,
               "exit_reasons": filled["exit_reason"].value_counts().to_dict(),
               "csv": "replay_2023_exec_us_v1.csv", "csv_sha256": sha256_file(HERE / "replay_2023_exec_us_v1.csv"),
               "exec_spec": exec_us.SPEC.record(), "exec_spec_sha256": exec_us.SPEC.sha256(),
               "note": "descriptive replay; no random baseline; not approval evidence"}
    return {"rows": rows, "summary": summary}


def main():
    frame, meta = global_panel.load(PANEL)
    out = {"panel_manifest": str(PANEL.relative_to(ROOT)), "panel_manifest_sha256": sha256_file(PANEL),
           "panel_rebuild_under_reconcile_v1": {
               "result": "identical panel bytes (sha256 equal) and identical 669-name quarantine",
               "triggered_after_read_through": 399,
               "how": "build_us_repair with the v3 inputs into an ignored directory, 2026-10-08; not committed"}}
    out["reconciliation"] = reconciliation(set(frame["ticker"]))
    out["approval"] = approval_resolution()
    out["paper_stop_distances"] = paper_stop_distances()
    rep = replay_2023(frame, meta)
    out["replay_2023_exec_us_v1"] = rep["summary"]
    (HERE / "replay_2023_exec_us_v1_full.json").write_text(json.dumps(rep["rows"], indent=1, default=float) + "\n")
    out["fill_b_v2_rerun"] = fill_b_rerun(frame, meta)
    out["paper_ledger_sha256"] = sha256_file(ROOT / "paper/ledger.jsonl")
    with (HERE / "checks.json").open("x") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=True, default=float) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "paper_stop_distances"}, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()

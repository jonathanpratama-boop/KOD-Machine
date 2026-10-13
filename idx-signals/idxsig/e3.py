"""Experiment E3 (research/E3/protocol.json, KOD-IDX-E3-v1): execution plans for the ARA detectors.

E1 validated F1_ARA for detection and failed it for execution under the one plan the harness
had (buy the next close, hold five sessions). E3 asks whether any plan from a fixed, pre-registered
family turns the signals of the E1 family's ARA detectors into a positive net return that beats
matched random entries executed under the same plan. Stages, each a new directory under
research/E3/ (frozen by the commit guard):

  reproduce   the recorded E1 trading runs re-run on E3's panel and registry with their original
              configuration; the protocol's precondition (identical, or an accepted, recorded deviation)
  discovery   every (detector, plan) pair through the harness on the discovery period; the
              pre-registered selection; the chosen pair is then written into moonshot_e3.SELECTED
  validation  the frozen pair on the validation period only, as a recorded harness run (results/runs/)

Selection on discovery, one test on validation. The holdout is sealed: the harness refuses it.
"""

from __future__ import annotations

import itertools
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import RunConfig, run
from .provenance import PKG_ROOT, rel, sha256_file
from .results import _jsonable, code_state, write_run
from .rules import moonshot_e3

E3_DIR = PKG_ROOT / "research" / "E3"
PROTOCOL = E3_DIR / "protocol.json"
RUN_INDEX = PKG_ROOT / "results" / "RUNS.jsonl"
PLAN_KEYS = ("entry_rule", "entry_window", "exit_rule", "holding_days")


def protocol(path: Path = PROTOCOL) -> tuple[dict, str]:
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def plan_grid(proto: dict) -> list[dict]:
    p = proto["plans"]
    return [{"entry_rule": e, "entry_window": int(w), "exit_rule": x, "holding_days": int(h)}
            for (e, w), x, h in itertools.product([tuple(v) for v in p["entries"]], p["exits"], p["holding_days"])]


def plan_id(detector: str, plan: dict) -> str:
    return f"{detector}|{plan['entry_rule']}{plan['entry_window']}|{plan['exit_rule']}|h{plan['holding_days']}"


def years_of(period) -> list[int]:
    return list(range(int(period[0][:4]), int(period[1][:4]) + 1))


def harness_config(proto: dict, rule_id: str, period: str, plan: dict | None = None) -> RunConfig:
    """The protocol's harness settings as a RunConfig. Without a plan the rule's own (frozen) plan applies."""
    h = proto["harness"]
    start, end = proto["periods"][period]
    return RunConfig(
        rule_id=rule_id, market="IDX", start=start, end=end,
        holding_days=int(plan["holding_days"]) if plan else None,
        entry_rule=plan["entry_rule"] if plan else None,
        entry_window=int(plan["entry_window"]) if plan else None,
        exit_rule=plan["exit_rule"] if plan else None,
        entry_lag=1, notional=float(h["notional_idr"]), max_participation=h["max_participation"],
        fee_buy=h["fee_buy"], fee_sell=h["fee_sell"], overlap=h["overlap"], random_draws=h["random_draws"],
        seed=h["seed"], data_end_exit=h["data_end_exit"], ca_mode=h["ca_mode"], lookahead_cuts=None,
        controls_version=h["controls_version"], units=h["units"], fill_model=h["fill_model"],
    )


def plan_row(summary: dict, detector: str, plan: dict, years: list[int]) -> dict:
    """One line of the plan table from a harness summary."""
    r, sig = summary["rule_trades"], summary["signals"]
    matched = summary["random_matched"]["avg_net_return"] or {}
    same = summary["random"]["avg_net_return"] or {}
    by_year = {int(y["year"]): y for y in summary["by_year"]}
    row = {"plan_id": plan_id(detector, plan), "detector": detector, **{k: plan[k] for k in PLAN_KEYS},
           "signals": sig["total"], "attempted": sig["attempted"], "filled": r["filled"], "fill_rate": r["fill_rate"],
           "scored": r["scored"], "hit_rate": r["hit_rate"], "avg_net_return": r["avg_net_return"],
           "median_net_return": r["median_net_return"],
           "matched_random_avg_net_return": matched.get("random_mean"),
           "matched_random_p2_5": matched.get("random_p2_5"), "matched_random_p97_5": matched.get("random_p97_5"),
           "p_one_sided_vs_matched": matched.get("p_value_one_sided"),
           "same_session_random_avg_net_return": same.get("random_mean"),
           "p_one_sided_vs_same_session": same.get("p_value_one_sided")}
    for y in years:
        yr = by_year.get(y, {})
        row[f"scored_{y}"] = int(yr.get("scored", 0))
        row[f"avg_net_return_{y}"] = yr.get("avg_net_return")
    row["status_counts"] = json.dumps(r["status_counts"], sort_keys=True)
    row["rule_sha256"] = summary["rule"]["sha256"]
    return row


def admissibility(row: dict, proto: dict, years: list[int]) -> list[str]:
    """Why a plan is not admissible under the protocol's selection rule; empty when it is."""
    s = proto["selection"]
    out = []
    if row["scored"] < s["min_scored"]:
        out.append(f"scored {row['scored']} < {s['min_scored']}")
    avg = row.get("avg_net_return")
    if avg is None or not avg > 0:
        out.append("average net return not positive")
    p = row.get("p_one_sided_vs_matched")
    if p is None or not p < s["max_p_one_sided_vs_matched"]:
        out.append(f"p vs matched random {p} not below {s['max_p_one_sided_vs_matched']}")
    for y in years:
        n, a = row.get(f"scored_{y}", 0), row.get(f"avg_net_return_{y}")
        if n >= s["min_scored_per_year"] and (a is None or not a > 0):
            out.append(f"average net return in {y} not positive ({n} scored)")
    return out


def select(table: pd.DataFrame, proto: dict, years: list[int]) -> dict | None:
    """The admissible plan with the highest average net return; ties by scored trades, then grid order."""
    rows = table.to_dict("records")
    ok = [(i, r) for i, r in enumerate(rows) if not admissibility(r, proto, years)]
    if not ok:
        return None
    ok.sort(key=lambda ir: (-float(ir[1]["avg_net_return"]), -int(ir[1]["scored"]), ir[0]))
    return ok[0][1]


def selected_tuple(row: dict) -> tuple:
    """What goes into moonshot_e3.SELECTED."""
    return (str(row["detector"]), str(row["entry_rule"]), int(row["entry_window"]), str(row["exit_rule"]),
            int(row["holding_days"]))


def _runtime() -> dict:
    return {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(_jsonable(obj), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, float_format="%.10g")


def recorded_run(run_dir: str) -> dict:
    for line in RUN_INDEX.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["dir"] == run_dir:
            return rec
    raise KeyError(f"{run_dir} is not in {rel(RUN_INDEX)}")


def _stamp(proto_sha: str, proto: dict, stage: str, meta: dict, registry) -> dict:
    return {"protocol_id": proto["protocol_id"], "protocol_sha256": proto_sha, "stage": stage, "computed_at": _now(),
            "panel_sha256": meta["sha256"], "registry_sha256": registry[1]["sha256"],
            "detector_module_sha256": sha256_file(Path(moonshot_e3.__file__)), "code": code_state(),
            "runtime": _runtime(), "holdout": "sealed: the harness refuses any detector window that touches it"}


def run_reproduce(df, meta, registry, out: Path, proto: dict, proto_sha: str, log=print) -> dict:
    """Precondition: the recorded runs named in the protocol, re-run here with their original
    configuration. REPRODUCED when signals, scored count, average net return and the matched-random
    mean are identical; otherwise DEVIATES, with both sides on record."""
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for run_dir in proto["precondition"]["runs"]:
        rec = recorded_run(run_dir)
        recorded = json.loads((PKG_ROOT / run_dir / "summary.json").read_text(encoding="utf-8"))
        cfg_fields = {k: v for k, v in recorded["config"].items() if k in RunConfig.__dataclass_fields__}
        cfg = RunConfig(**cfg_fields)
        log(f"reproducing {run_dir}")
        summary = run(cfg, df, meta, ca_registry=registry)["summary"]

        def facts(s):
            return {"signals": s["signals"]["total"], "scored": s["rule_trades"]["scored"],
                    "avg_net_return": s["rule_trades"]["avg_net_return"],
                    "matched_random_avg_net_return": (s["random_matched"]["avg_net_return"] or {}).get("random_mean"),
                    "status_counts": s["rule_trades"]["status_counts"]}

        want, got = facts(recorded), facts(summary)
        same = all(want[k] == got[k] for k in ("signals", "scored", "status_counts")) and all(
            (want[k] is None and got[k] is None) or (want[k] is not None and got[k] is not None
                                                     and abs(want[k] - got[k]) < 1e-12)
            for k in ("avg_net_return", "matched_random_avg_net_return"))
        results.append({"run_dir": run_dir, "run_id": rec["run_id"], "config": cfg_fields, "recorded": want,
                        "reproduced": got, "recorded_panel_sha256": recorded["panel"]["panel_sha256"],
                        "recorded_registry_sha256": recorded["corporate_action_model"].get("registry_sha256"),
                        "status": "REPRODUCED" if same else "DEVIATES"})
    result = {**_stamp(proto_sha, proto, "reproduce", meta, registry), "runs": results,
              "status": "REPRODUCED" if all(r["status"] == "REPRODUCED" for r in results) else "DEVIATES"}
    write_json(out / "result.json", result)
    return result


def run_discovery(df, meta, registry, out: Path, proto: dict, proto_sha: str, log=print,
                  accept_deviation: bool = False) -> dict:
    repro_path = E3_DIR / "reproduce" / "result.json"
    if not repro_path.exists():
        raise RuntimeError("the precondition has not been run (e3-reproduce)")
    repro = json.loads(repro_path.read_text(encoding="utf-8"))
    if repro["panel_sha256"] != meta["sha256"] or repro["registry_sha256"] != registry[1]["sha256"]:
        raise RuntimeError("the precondition ran on different data than this discovery")
    if repro["status"] != "REPRODUCED" and not accept_deviation:
        raise RuntimeError("the recorded runs did not reproduce identically on this data; see "
                           f"{rel(repro_path)} and pass --accept-deviation to proceed with that on record")
    out.mkdir(parents=True, exist_ok=False)
    years = years_of(proto["periods"]["discovery"])
    grid = plan_grid(proto)
    cache: dict = {}
    rows, summaries = [], {}
    for det in proto["detectors"]["candidates"]:
        rule_id = moonshot_e3.candidate_rule_id(det)
        for plan in grid:
            summary = run(harness_config(proto, rule_id, "discovery", plan), df, meta, ca_registry=registry,
                          signal_cache=cache)["summary"]
            row = plan_row(summary, det, plan, years)
            rows.append(row)
            summaries[row["plan_id"]] = summary
            log(f"{row['plan_id']}: scored {row['scored']}, avg net {row['avg_net_return']}, "
                f"matched {row['matched_random_avg_net_return']}, p {row['p_one_sided_vs_matched']}")
    table = pd.DataFrame(rows)
    reasons = [admissibility(r, proto, years) for r in rows]
    table["admissible"] = [not r for r in reasons]
    table["inadmissible_because"] = ["; ".join(r) for r in reasons]
    write_csv(out / "plans.csv", table)
    ref = proto["selection"]["reference_plan"]
    ref_id = plan_id(ref["detector"], ref)
    write_json(out / "reference_summary.json", summaries[ref_id])
    chosen = select(table, proto, years)
    if chosen is not None:
        write_json(out / "selected_summary.json", summaries[chosen["plan_id"]])
    summary = {**_stamp(proto_sha, proto, "discovery", meta, registry),
               "precondition": {"status": repro["status"], "accepted_deviation": bool(accept_deviation)},
               "detectors": list(proto["detectors"]["candidates"]), "plans_per_detector": len(grid),
               "runs": len(rows), "admissible": int(table["admissible"].sum()),
               "reference_plan": next(r for r in rows if r["plan_id"] == ref_id),
               "selected": chosen, "selected_tuple": list(selected_tuple(chosen)) if chosen else None,
               "freeze": ("write selected_tuple into idxsig/rules/moonshot_e3.SELECTED and commit before "
                          "e3-validation" if chosen else
                          "no admissible plan: SELECTED stays None, MOONSHOT_E3_D1 is not created, the paper "
                          "policy keeps PASS")}
    write_json(out / "summary.json", summary)
    return summary


def run_validation(df, meta, registry, out: Path, proto: dict, proto_sha: str, log=print) -> dict:
    if moonshot_e3.SELECTED is None:
        raise RuntimeError("no frozen (detector, plan): run discovery and write SELECTED first")
    disc = json.loads((E3_DIR / "discovery" / "summary.json").read_text(encoding="utf-8"))
    if list(moonshot_e3.SELECTED) != list(disc["selected_tuple"] or []):
        raise RuntimeError(f"moonshot_e3.SELECTED {moonshot_e3.SELECTED} is not the pair discovery selected "
                           f"({disc['selected_tuple']})")
    out.mkdir(parents=True, exist_ok=False)
    log(f"validating {moonshot_e3.SELECTED}")
    output = run(harness_config(proto, moonshot_e3.RULE_ID, "validation"), df, meta, ca_registry=registry)
    run_dir = write_run(output)  # the trading run on record, committed, as E1's was
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    det, entry_rule, window, exit_rule, hold = moonshot_e3.SELECTED
    plan = {"entry_rule": entry_rule, "entry_window": window, "exit_rule": exit_rule, "holding_days": hold}
    row = plan_row(summary, det, plan, years_of(proto["periods"]["validation"]))
    v = proto["validation"]
    passed = (row["scored"] >= v["min_scored"] and row["avg_net_return"] is not None and row["avg_net_return"] > 0
              and row["p_one_sided_vs_matched"] is not None
              and row["p_one_sided_vs_matched"] < v["max_p_one_sided_vs_matched"])
    result = {**_stamp(proto_sha, proto, "validation", meta, registry), "selected": list(moonshot_e3.SELECTED),
              "run_id": summary["run_id"], "run_dir": rel(run_dir), "plan_text": summary["execution"]["plan_text"],
              "result": row, "criteria": v, "passed": bool(passed),
              "consequence": ("PAPER-POLICY-v4 may underwrite a paper BUY ON TRIGGER for this pair; judged "
                              "prospectively from here; no real orders" if passed else
                              "the paper policy keeps PASS; this plan family is exhausted for these detectors")}
    write_json(out / "result.json", result)
    return result

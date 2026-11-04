"""Experiment E4 (research/E4/protocol.json, KOD-GLOBAL-E4-v1): the fade, on the short side.

E2 found that a +30% day marks names with a fat right tail and that buying them loses: the median
five-session move after a flag was about -10% against 0% for matched names, in every market. E4
asks whether the SHORT side of the E2 family's already-ran detectors, under a fixed family of
execution plans, earns a positive net return after fees, slippage and carry, beats matched random
shorts executed under the same plan, does so in every discovery year, and wins more often than it
loses with a bounded tail. Crypto first (perpetual futures make the short real; delisted pairs are
in the panel); the same protocol names US as a second market under a borrow assumption.

Stages, each a new directory under research/E4/<market>/ (frozen by the commit guard):

  reproduce   the recorded E2 trading run for the market re-run on E4's panel (precondition)
  discovery   every (detector, plan) pair through the harness on the discovery period; selection
  validation  the frozen pair on the validation period only, as a recorded harness run

Selection on discovery, one test on validation. The holdout (2024 on) is never loaded: the study
window ends at the validation period's last session.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import e3
from .backtest import RunConfig, run
from .e3 import (
    _now,
    _runtime,
    admissibility as base_admissibility,
    plan_grid,
    plan_id,
    plan_row,
    write_csv,
    write_json,
    years_of,
)
from .provenance import PKG_ROOT, rel, sha256_file
from .results import code_state, write_run
from .rules import moonshot_e4

E4_DIR = PKG_ROOT / "research" / "E4"
PROTOCOL = E4_DIR / "protocol.json"
PLAN_KEYS = ("entry_rule", "entry_window", "exit_rule", "holding_days")
VERSIONS = ("v1", "v2")


def version_dir(version: str = "v1") -> Path:
    """v1 lives in research/E4/, later versions in research/E4/<version>/ (the commit guard freezes both)."""
    if version not in VERSIONS:
        raise ValueError(f"unknown E4 protocol version {version!r}")
    return E4_DIR if version == "v1" else E4_DIR / version


def protocol(path: Path | None = None, version: str = "v1") -> tuple[dict, str]:
    path = path or version_dir(version) / "protocol.json"
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def market_dir(market: str, version: str = "v1") -> Path:
    return version_dir(version) / market


def harness_config(
    proto: dict,
    market: str,
    rule_id: str,
    period: str,
    plan: dict | None = None,
    side: str | None = None,
) -> RunConfig:
    """The protocol's harness settings for `market` as a RunConfig. Without a plan the rule's own
    (frozen) plan applies; `side` None means the rule's plan's side, else long."""
    h = proto["harness"]
    mk = proto["markets"][market]
    start, end = proto["periods"][period]
    return RunConfig(
        rule_id=rule_id,
        market=market,
        start=start,
        end=end,
        holding_days=int(plan["holding_days"]) if plan else None,
        entry_rule=plan["entry_rule"] if plan else None,
        entry_window=int(plan["entry_window"]) if plan else None,
        exit_rule=plan["exit_rule"] if plan else None,
        side=side,
        entry_lag=1,
        notional=float(mk["notional"]),
        max_participation=h["max_participation"],
        fee_buy=mk["fee_buy"],
        fee_sell=mk["fee_sell"],
        overlap=h["overlap"],
        random_draws=h["random_draws"],
        seed=h["seed"],
        data_end_exit=h["data_end_exit"],
        ca_mode=h["ca_mode"],
        lookahead_cuts=None,
        controls_version=h["controls_version"],
        units="panel",
        fill_model=h["fill_model"],
        liquidation=h.get("liquidation"),
        jump_ratio=h.get("jump_ratio"),
    )


def tail_stats(trades: pd.DataFrame) -> dict:
    """What the hit rate hides: the worst trades of the plan."""
    net = trades.loc[trades["status"].isin(("EXITED", "EXIT_DATA_END")), "net_return"].to_numpy(
        dtype=float
    )
    net = net[np.isfinite(net)]
    if not len(net):
        return {
            "worst_net_return": None,
            "p1_net_return": None,
            "p5_net_return": None,
            "mean_worst_10": None,
            "share_below_minus_20pct": None,
        }
    s = np.sort(net)
    out = {
        "worst_net_return": float(s[0]),
        "p1_net_return": float(np.percentile(s, 1)),
        "p5_net_return": float(np.percentile(s, 5)),
        "mean_worst_10": float(s[:10].mean()),
        "share_below_minus_20pct": float((s < -0.20).mean()),
    }
    if "liquidated" in trades:
        scored = trades["status"].isin(("EXITED", "EXIT_DATA_END"))
        out["share_liquidated"] = (
            float(trades.loc[scored, "liquidated"].astype(bool).mean()) if scored.any() else None
        )
    return out


def tail_criteria(row: dict, s: dict) -> list[str]:
    """The tail rules a protocol's selection/validation block names: v1's 1st percentile, v2's 5th
    percentile and liquidation share. Whichever keys are present apply."""
    out = []
    if "max_p1_loss" in s:
        p1 = row.get("p1_net_return")
        if p1 is None or not p1 >= s["max_p1_loss"]:
            out.append(
                f"1st percentile of trade returns {p1} below {s['max_p1_loss']} (tail not bounded)"
            )
    if "max_p5_loss" in s:
        p5 = row.get("p5_net_return")
        if p5 is None or not p5 >= s["max_p5_loss"]:
            out.append(
                f"5th percentile of trade returns {p5} below {s['max_p5_loss']} (tail not bounded)"
            )
    if "max_share_liquidated" in s:
        share = row.get("share_liquidated")
        if share is None or not share <= s["max_share_liquidated"]:
            out.append(f"liquidated share {share} above {s['max_share_liquidated']}")
    return out


def admissibility(row: dict, proto: dict, years: list[int]) -> list[str]:
    """E3's rule (scored, positive, beats matched random, positive in every year) plus E4's: a hit rate
    above min_hit_rate, and the protocol's tail criteria."""
    s = proto["selection"]
    out = base_admissibility(row, proto, years)
    hit = row.get("hit_rate")
    if hit is None or not hit >= s["min_hit_rate"]:
        out.append(f"hit rate {hit} below {s['min_hit_rate']}")
    out.extend(tail_criteria(row, s))
    return out


def select(table: pd.DataFrame, proto: dict, years: list[int]) -> dict | None:
    rows = table.to_dict("records")
    ok = [(i, r) for i, r in enumerate(rows) if not admissibility(r, proto, years)]
    if not ok:
        return None
    ok.sort(key=lambda ir: (-float(ir[1]["avg_net_return"]), -int(ir[1]["scored"]), ir[0]))
    return ok[0][1]


def _stamp(proto_sha: str, proto: dict, market: str, stage: str, meta: dict) -> dict:
    return {
        "protocol_id": proto["protocol_id"],
        "protocol_sha256": proto_sha,
        "market": market,
        "stage": stage,
        "computed_at": _now(),
        "panel_sha256": meta["sha256"],
        "panel_manifest": meta.get("_manifest"),
        "detector_module_sha256": sha256_file(Path(moonshot_e4.__file__)),
        "code": code_state(),
        "runtime": _runtime(),
        "holdout": "sealed: never loaded; the study window ends at the validation period",
    }


def run_reproduce(df, meta, out: Path, proto: dict, proto_sha: str, market: str, log=print) -> dict:
    """Precondition: the recorded E2 trading run for the market, re-run here with its original
    configuration (the long side). REPRODUCED when signals, scored count, status counts, average net
    return and the matched-random mean are identical; otherwise DEVIATES, both sides on record."""
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for run_dir in proto["markets"][market]["precondition_runs"]:
        rec = e3.recorded_run(run_dir)
        recorded = json.loads((PKG_ROOT / run_dir / "summary.json").read_text(encoding="utf-8"))
        cfg_fields = {
            k: v for k, v in recorded["config"].items() if k in RunConfig.__dataclass_fields__
        }
        cfg = RunConfig(**cfg_fields)
        log(f"reproducing {run_dir}")
        summary = run(cfg, df, meta)["summary"]

        def facts(s):
            return {
                "signals": s["signals"]["total"],
                "scored": s["rule_trades"]["scored"],
                "avg_net_return": s["rule_trades"]["avg_net_return"],
                "matched_random_avg_net_return": (s["random_matched"]["avg_net_return"] or {}).get(
                    "random_mean"
                ),
                "status_counts": s["rule_trades"]["status_counts"],
            }

        want, got = facts(recorded), facts(summary)
        same = all(want[k] == got[k] for k in ("signals", "scored", "status_counts")) and all(
            (want[k] is None and got[k] is None)
            or (want[k] is not None and got[k] is not None and abs(want[k] - got[k]) < 1e-12)
            for k in ("avg_net_return", "matched_random_avg_net_return")
        )
        results.append(
            {
                "run_dir": run_dir,
                "run_id": rec["run_id"],
                "config": cfg_fields,
                "recorded": want,
                "reproduced": got,
                "recorded_panel_sha256": recorded["panel"]["panel_sha256"],
                "status": "REPRODUCED" if same else "DEVIATES",
            }
        )
    result = {
        **_stamp(proto_sha, proto, market, "reproduce", meta),
        "runs": results,
        "status": "REPRODUCED" if all(r["status"] == "REPRODUCED" for r in results) else "DEVIATES",
    }
    write_json(out / "result.json", result)
    return result


def run_discovery(
    df,
    meta,
    out: Path,
    proto: dict,
    proto_sha: str,
    market: str,
    log=print,
    accept_deviation: bool = False,
) -> dict:
    named = proto["markets"][market].get("precondition_result")
    repro_path = out.parent / "reproduce" / "result.json"
    if named:  # the protocol names it relative to the package or to the repository root
        repro_path = next(
            (p for p in (PKG_ROOT / named, PKG_ROOT.parent / named) if p.exists()), PKG_ROOT / named
        )
    if not repro_path.exists():
        raise RuntimeError(f"the precondition has not been run for {market} (e4-reproduce)")
    repro = json.loads(repro_path.read_text(encoding="utf-8"))
    if repro["panel_sha256"] != meta["sha256"]:
        raise RuntimeError("the precondition ran on different data than this discovery")
    if repro["status"] != "REPRODUCED" and not accept_deviation:
        raise RuntimeError(
            "the recorded run did not reproduce identically on this data; see "
            f"{rel(repro_path)} and pass --accept-deviation to proceed with that on record"
        )
    out.mkdir(parents=True, exist_ok=False)
    years = years_of(proto["periods"]["discovery"])
    grid = plan_grid(proto)
    cache: dict = {}
    rows, summaries = [], {}
    for det in proto["detectors"]["candidates"]:
        rule_id = moonshot_e4.candidate_rule_id(det)
        for plan in grid:
            output = run(
                harness_config(proto, market, rule_id, "discovery", plan, side=moonshot_e4.SIDE),
                df,
                meta,
                signal_cache=cache,
            )
            summary = output["summary"]
            row = {**plan_row(summary, det, plan, years), **tail_stats(output["trades"])}
            rows.append(row)
            summaries[row["plan_id"]] = summary
            log(
                f"{row['plan_id']}: scored {row['scored']}, hit {row['hit_rate']}, avg net {row['avg_net_return']}, "
                f"matched {row['matched_random_avg_net_return']}, p {row['p_one_sided_vs_matched']}, "
                f"p1 {row['p1_net_return']}"
            )
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
    summary = {
        **_stamp(proto_sha, proto, market, "discovery", meta),
        "precondition": {"status": repro["status"], "accepted_deviation": bool(accept_deviation)},
        "side": moonshot_e4.SIDE,
        "detectors": list(proto["detectors"]["candidates"]),
        "plans_per_detector": len(grid),
        "runs": len(rows),
        "admissible": int(table["admissible"].sum()),
        "reference_plan": next(r for r in rows if r["plan_id"] == ref_id),
        "selected": chosen,
        "selected_tuple": list(e3.selected_tuple(chosen)) if chosen else None,
        "freeze": (
            "write selected_tuple into idxsig/rules/moonshot_e4.SELECTED and commit before "
            "e4-validation"
            if chosen
            else "no admissible plan: SELECTED stays None, MOONSHOT_E4_D1 is not created, the paper "
            "policy is unchanged"
        ),
    }
    write_json(out / "summary.json", summary)
    return summary


def run_validation(
    df, meta, out: Path, proto: dict, proto_sha: str, market: str, log=print
) -> dict:
    if moonshot_e4.SELECTED is None:
        raise RuntimeError("no frozen (detector, plan): run discovery and write SELECTED first")
    if moonshot_e4.SELECTED_PROTOCOL != proto["protocol_id"]:
        raise RuntimeError(
            f"moonshot_e4.SELECTED was frozen under {moonshot_e4.SELECTED_PROTOCOL}, not "
            f"{proto['protocol_id']}"
        )
    disc = json.loads((out.parent / "discovery" / "summary.json").read_text(encoding="utf-8"))
    if list(moonshot_e4.SELECTED) != list(disc["selected_tuple"] or []):
        raise RuntimeError(
            f"moonshot_e4.SELECTED {moonshot_e4.SELECTED} is not the pair discovery selected "
            f"({disc['selected_tuple']})"
        )
    out.mkdir(parents=True, exist_ok=False)
    log(f"validating {moonshot_e4.SELECTED} on {market}, short side")
    output = run(harness_config(proto, market, moonshot_e4.RULE_ID, "validation"), df, meta)
    run_dir = write_run(output)  # the trading run on record, committed
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    det, entry_rule, window, exit_rule, hold = moonshot_e4.SELECTED
    plan = {
        "entry_rule": entry_rule,
        "entry_window": window,
        "exit_rule": exit_rule,
        "holding_days": hold,
    }
    row = {
        **plan_row(summary, det, plan, years_of(proto["periods"]["validation"])),
        **tail_stats(output["trades"]),
    }
    v = proto["validation"]
    passed = (
        row["scored"] >= v["min_scored"]
        and row["avg_net_return"] is not None
        and row["avg_net_return"] > 0
        and row["p_one_sided_vs_matched"] is not None
        and row["p_one_sided_vs_matched"] < v["max_p_one_sided_vs_matched"]
        and row["hit_rate"] is not None
        and row["hit_rate"] >= v["min_hit_rate"]
        and not tail_criteria(row, v)
    )
    result = {
        **_stamp(proto_sha, proto, market, "validation", meta),
        "selected": list(moonshot_e4.SELECTED),
        "side": moonshot_e4.SIDE,
        "run_id": summary["run_id"],
        "run_dir": rel(run_dir),
        "plan_text": summary["execution"]["plan_text"],
        "short_side": summary["execution"].get("short_side"),
        "result": row,
        "criteria": v,
        "passed": bool(passed),
        "consequence": (
            "a paper policy for the short side may underwrite paper SHORT ON TRIGGER decisions "
            "for this pair, judged prospectively; no real orders"
            if passed
            else "no paper policy change; this plan family is exhausted for these detectors"
        ),
    }
    write_json(out / "result.json", result)
    return result

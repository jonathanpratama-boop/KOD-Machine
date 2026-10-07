"""Append-only run store.

Each run gets a new directory results/runs/<run_id>/ written with exclusive-create opens
and then made read-only. Its file hashes go into one new line of results/RUNS.jsonl. A
run directory is never written twice; an existing run id is an error. `verify_runs`
re-hashes every file, checks the index against git HEAD (it may only grow), and fails on
any edit or deletion. tools/check_append_only.py enforces the same rule on every commit.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import stat
import subprocess
from pathlib import Path

import numpy as np

from .provenance import PKG_ROOT, rel, sha256_bytes, sha256_file, utc_stamp

RESULTS = PKG_ROOT / "results"
RUNS = RESULTS / "runs"
INDEX = RESULTS / "RUNS.jsonl"


class DirtyTreeError(RuntimeError):
    pass


def _git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=PKG_ROOT, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def code_state() -> dict:
    try:
        head = _git("rev-parse", "HEAD").strip()
        dirty = _git("status", "--porcelain", "--", "idxsig").strip()
    except (RuntimeError, FileNotFoundError):
        return {"commit": None, "dirty": None}
    return {"commit": head, "dirty": bool(dirty)}


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, float) and obj != obj:
        return None
    return obj


def _pct(x) -> str:
    return "—" if x is None else f"{100 * x:+.2f}%"


def _rate(x) -> str:
    return "—" if x is None else f"{100 * x:.1f}%"


def _vs(label: str, base: dict | None) -> str:
    if not base:
        return f"{label}: no comparison."
    return (f"{label}: {_pct(base.get('difference'))} (rule at percentile "
            f"{base.get('percentile_of_observed', float('nan')):.1f} of draws, one-sided p = "
            f"{base.get('p_value_one_sided', float('nan')):.3f}).")


def _dist_cell(base: dict, fmt) -> str:
    if not base:
        return "—"
    return (f"{fmt(base.get('random_mean'))} (95% of draws {fmt(base.get('random_p2_5'))} .. "
            f"{fmt(base.get('random_p97_5'))})")


def render_report(run_id: str, summary: dict) -> str:
    r, sig = summary["rule_trades"], summary["signals"]
    mt, rnd = summary["random_matched"], summary["random"]
    u, rule = summary["universe"], summary["rule"]
    look = summary["lookahead_check"]
    lines = [
        f"# Run {run_id}",
        "",
        f"Rule: **{rule['rule_id']} {rule['version']}** ({rule['kind']}), holding {rule['holding_days']} sessions",
        f"Rule SHA-256: `{rule['sha256']}`",
        f"Code: `{summary['code']['commit']}`{' (dirty)' if summary['code']['dirty'] else ''}",
        f"Panel: `{summary['panel']['panel_sha256']}`",
        f"Window: {u['first_session']} .. {u['last_session']} ({u['sessions']} sessions, "
        f"{u['tickers_in_window']} tickers, {u['tickers_ending_inside_window']} stop trading inside the window)",
        "",
        "> " + rule["text"].replace("\n", "\n> "),
        "",
        "## Result",
        "",
        "| | Rule | Matched random (primary) | Same-session random |",
        "|---|---:|---:|---:|",
        f"| Signals | {sig['total']} (rate {_rate(sig['signal_rate'])} of evaluable ticker-sessions) | — | — |",
        f"| Attempted (after overlap skip) | {sig['attempted']} | {mt['draws']} draws × {sig['attempted']} | "
        f"{rnd['draws']} draws × {sig['attempted']} |",
        f"| Filled | {r['filled']} ({_rate(r['fill_rate'])}) | {_rate(mt['pooled']['fill_rate'])} | "
        f"{_rate(rnd['pooled']['fill_rate'])} |",
        f"| Scored trades | {r['scored']} | {mt['pooled']['scored']} | {rnd['pooled']['scored']} |",
        f"| Hit rate (net return > 0) | {_rate(r['hit_rate'])} | {_dist_cell(mt['hit_rate'], _rate)} | "
        f"{_dist_cell(rnd['hit_rate'], _rate)} |",
        f"| Average net return | {_pct(r['avg_net_return'])} | {_dist_cell(mt['avg_net_return'], _pct)} | "
        f"{_dist_cell(rnd['avg_net_return'], _pct)} |",
        f"| Median net return | {_pct(r['median_net_return'])} | {_pct(mt['pooled']['median_net_return'])} | "
        f"{_pct(rnd['pooled']['median_net_return'])} |",
        "",
        _vs("Average return vs matched random", mt["avg_net_return"]),
        _vs("Hit rate vs matched random", mt["hit_rate"]),
        _vs("Average return vs same-session random", rnd["avg_net_return"]),
        _vs("Hit rate vs same-session random", rnd["hit_rate"]),
        "",
        "Matched controls found at: " + ", ".join(f"{k} {v}" for k, v in mt.get("match_level_used", {}).items()),
        "",
        "Status counts (rule): " + ", ".join(f"{k} {v}" for k, v in r["status_counts"].items()),
        "",
        "Status counts (matched random, pooled): "
        + ", ".join(f"{k} {v}" for k, v in mt["pooled"]["status_counts"].items()),
        "",
        "## By signal year",
        "",
        "| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for y in summary["by_year"]:
        lines.append(
            f"| {y['year']} | {y['attempts']} | {y['scored']} | {_rate(y['hit_rate'])} | {_pct(y['avg_net_return'])} | "
            f"{_rate(y.get('random_matched_hit_rate'))} | {_pct(y.get('random_matched_avg_net_return'))} | "
            f"{_pct(y.get('random_avg_net_return'))} |"
        )
    c = summary["config"]
    if look["mode"] == "exhaustive":
        look_text = f"exhaustive: the rule was recomputed on all {look['sessions_checked']} prefixes; 0 signals changed"
    else:
        look_text = "sampled at " + ", ".join(look["truncated_after"]) + " (not a proof)"
    lines += [
        "",
        "## Execution",
        "",
        f"- {summary['execution']['price']}, entry lag {c['entry_lag']}",
        f"- 100-share lots, notional Rp {c['notional']:,.0f} per trade, at most {c['max_participation']:.0%} of session volume",
        f"- Fees: buy {c['fee_buy']:.2%}, sell {c['fee_sell']:.2%}",
        f"- {summary['execution']['auto_rejection']}",
        f"- Corporate actions: {summary['execution']['corporate_actions']}",
        f"- Overlap: {c['overlap']}; names that stop trading exit at {c['data_end_exit']}",
        f"- Lookahead check: {look_text}",
        "",
        "## Warnings",
        "",
    ]
    lines += [f"- {w}" for w in summary["warnings"]] or ["- none"]
    lines.append("")
    return "\n".join(lines)


def _write_exclusive(path: Path, data: bytes) -> str:
    with path.open("xb") as fh:
        fh.write(data)
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return sha256_bytes(data)


def write_run(output: dict, *, allow_dirty: bool = False, commit: bool = True, root: Path | None = None) -> Path:
    runs = (root / "runs") if root else RUNS
    index = (root / "RUNS.jsonl") if root else INDEX
    state = code_state()
    if state["dirty"] and not allow_dirty:
        raise DirtyTreeError("idxsig/ has uncommitted changes; commit the code first so the run names the code it ran")
    summary = dict(output["summary"])
    summary["code"] = state
    created = utc_stamp()
    rule = summary["rule"]
    run_id = f"{created.replace('-', '').replace(':', '')}_{rule['rule_id']}_{rule['version']}"
    summary["run_id"] = run_id
    summary["created_at"] = created
    summary = _jsonable(summary)
    run_dir = runs / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    files = {}
    files["summary.json"] = _write_exclusive(run_dir / "summary.json", (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode())
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(output["trades"].to_csv(index=False, float_format="%.10g").encode())
    files["trades.csv.gz"] = _write_exclusive(run_dir / "trades.csv.gz", buf.getvalue())
    files["random_draws.csv"] = _write_exclusive(run_dir / "random_draws.csv",
                                                 output["draws"].to_csv(index=False, float_format="%.10g").encode())
    files["REPORT.md"] = _write_exclusive(run_dir / "REPORT.md", render_report(run_id, summary).encode())
    r = summary["rule_trades"]
    avg = summary["random"]["avg_net_return"] or {}
    matched = summary["random_matched"]["avg_net_return"] or {}
    line = {
        "run_id": run_id,
        "created_at": created,
        "rule_id": rule["rule_id"],
        "rule_version": rule["version"],
        "rule_kind": rule["kind"],
        "rule_sha256": rule["sha256"],
        "code_commit": state["commit"],
        "code_dirty": state["dirty"],
        "panel_sha256": summary["panel"]["panel_sha256"],
        "window": [summary["universe"]["first_session"], summary["universe"]["last_session"]],
        "holding_days": rule["holding_days"],
        "signals": summary["signals"]["total"],
        "scored": r["scored"],
        "hit_rate": r["hit_rate"],
        "avg_net_return": r["avg_net_return"],
        "matched_random_avg_net_return": matched.get("random_mean"),
        "p_value_avg_return_vs_matched": matched.get("p_value_one_sided"),
        "random_avg_net_return": avg.get("random_mean"),
        "p_value_avg_return": avg.get("p_value_one_sided"),
        "dir": rel(run_dir) if not root else str(run_dir),
        "files": files,
    }
    with index.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_jsonable(line), sort_keys=True) + "\n")
    if commit:
        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "").strip()
        message = (
            f"idxsig run {run_id}\n\n{rule['rule_id']} {rule['version']}: {summary['signals']['total']} signals, "
            f"{r['scored']} scored, hit rate {_rate(r['hit_rate'])}, avg net {_pct(r['avg_net_return'])} "
            f"vs matched random {_pct(matched.get('random_mean'))}, same-session random {_pct(avg.get('random_mean'))}"
        )
        if trailer:
            message += "\n\n" + trailer
        paths = [rel(run_dir), rel(index)]
        _git("add", "--", *paths)
        _git("commit", "-q", "-m", message, "--only", "--", *paths)
    return run_dir


def verify_runs(root: Path | None = None, use_git: bool = True) -> list[str]:
    runs = (root / "runs") if root else RUNS
    index = (root / "RUNS.jsonl") if root else INDEX
    problems = []
    lines = index.read_text(encoding="utf-8").splitlines() if index.exists() else []
    seen = set()
    for n, raw in enumerate(lines, 1):
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            problems.append(f"RUNS.jsonl line {n} is not JSON")
            continue
        run_id = entry["run_id"]
        if run_id in seen:
            problems.append(f"run {run_id} is listed twice")
        seen.add(run_id)
        run_dir = runs / run_id
        if not run_dir.is_dir():
            problems.append(f"run {run_id}: directory missing")
            continue
        on_disk = {p.name for p in run_dir.iterdir()}
        for name, digest in entry["files"].items():
            path = run_dir / name
            if not path.exists():
                problems.append(f"run {run_id}: {name} missing")
            elif sha256_file(path) != digest:
                problems.append(f"run {run_id}: {name} was edited after the run")
        extra = on_disk - set(entry["files"])
        if extra:
            problems.append(f"run {run_id}: files not in the index: {sorted(extra)}")
    if runs.exists():
        for d in sorted(p for p in runs.iterdir() if p.is_dir()):
            if d.name not in seen:
                problems.append(f"run directory {d.name} is not in RUNS.jsonl")
    if use_git and root is None:
        try:
            committed = _git("show", f"HEAD:./{rel(index)}", check=False)  # ./ = relative to idx-signals/
            current = index.read_text(encoding="utf-8") if index.exists() else ""
            if committed and not current.startswith(committed):
                problems.append("RUNS.jsonl no longer starts with the committed RUNS.jsonl: earlier lines were changed")
            changed = _git("diff", "--name-status", "HEAD", "--", rel(runs), check=False)
            for row in changed.splitlines():
                code, _, name = row.partition("\t")
                if code[:1] in ("M", "D", "R"):
                    problems.append(f"committed run file changed: {code} {name}")
        except FileNotFoundError:
            pass
    return problems

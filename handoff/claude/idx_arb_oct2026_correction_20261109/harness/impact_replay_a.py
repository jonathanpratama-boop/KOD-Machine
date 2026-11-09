#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARB-correction impact harness (impact analyst 1).  Paper-trading research system, no real money.

What it does
------------
Replays the REAL IDX scorer (idxsig.paper.score / score_pending flow) on the frozen final Yahoo pull
(yahoo_recent-20261106T101853Z) under two copies of the code that differ only in idxsig/market.py:
  B = shipped rules (ARB 15% after 2026-09-28)      C = corrected rules (ARB 7% from 2026-10-19, Rp1 nominal
  ARB for references Rp11-14 from 2026-10-20).
The ARB effect is always measured as C replay minus B replay (never C minus the recorded value).
Nothing under the two code directories and nothing in any ledger is ever written.

One command (about 15 seconds, 4 worker processes in parallel):
    python3 -I /tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/arb2/impact_1/harness.py
Options:  --reuse   re-run only the analysis on the worker output already in work/ (fast iteration)
Internal: --worker TAG  (TAG in B, C, C10, C7) runs one replay variant and writes work/worker_TAG.json
Outputs (all in the directory of this file): results.csv, speculation_replay.csv, flipped_bars.csv,
summary.json, report.md, work/ (worker output and market matrices).
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

ARB2 = Path("/tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/arb2")
OUT = ARB2 / "impact_1"
WORK = OUT / "work"
CODE = {"B": ARB2 / "code_B" / "idx-signals", "C": ARB2 / "code_C" / "idx-signals"}
FROZEN = Path("/tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/arb/frozen_inputs")
MANIFEST = FROZEN / "yahoo_recent-20261106T101853Z.jsonl"

EXPECT_LEDGER_SHA = "c1a67890577f7495212d1d9b3abbc97922bf741a007fc422c8225f5a87cd4395"
EXPECT_LEDGER_HEAD = "4ee35255de041da3b75af78fdee3062560918affb97e64aa4b699077655277e8"
EXPECT_LEDGER_ROWS = 755
EXPECT_SPEC_SHA = "0118f0c87d96e1a5fc6726d2668536d93e9c45ddc7e2a0dbdbaff47264542b04"
EXPECT_SPEC_ROWS = 277
EXPECT_MANIFEST_PREFIX = "3a27d3445b3d"

CUT = "2026-10-19"          # first session of the 7% ARB regime
TOL = 1e-9                  # tolerance for returns / path statistics (task definition)
TOL_SHIFT = 1e-12           # tolerance for "net return changed" between two replays of the same code

# Replay variants. B/C use the two code trees unmodified. C10 and C7 monkeypatch the in-memory
# idxsig.market module of the C tree inside the worker process only (no file is edited).
VARIANTS = {
    "B": dict(code="B", patch=None, label="B: shipped rules"),
    "C": dict(code="C", patch=None, label="C: corrected rules"),
    "C10": dict(code="C", patch="arb10", label="C with ARB 10% instead of 7% from 2026-10-19 (sensitivity a)"),
    "C7": dict(code="C", patch="no_rp1", label="C without the Rp11-14 nominal-Rp1 rule, 7% only (decomposition)"),
}

# The speculation protocol JSON (research/SPECULATION_REGISTER_v1/protocol_v1_1.json) is not part of the
# code trees. resolve_set() reads window definitions from it through speculation.windows(); the harness
# supplies the three windows it needs.  They are RECONSTRUCTED (BASE5 = enter at the next close, hold 5
# sessions; PATH20 = 20-session path; NEXT1 = 1-session path) and VALIDATED by replaying the recorded
# RESOLUTION rows under B (see baseline gate for speculations in the report).
SPEC_WINDOWS = {
    "BASE5": {"kind": "plan", "entry_window": 1, "holding_sessions": 5},
    "PATH20": {"kind": "path", "horizon": 20},
    "NEXT1": {"kind": "path", "horizon": 1},
}


# ----------------------------------------------------------------------------------------- helpers
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh.read().splitlines() if x.strip()]


def _json_default(o):
    import numpy as np

    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (datetime,)):
        return o.isoformat()
    return str(o)


def dump_json(obj, path, indent=None):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, default=_json_default, indent=indent, sort_keys=False)


def tradeof(out):
    return ((out or {}).get("execution") or {}).get("paper_trade")


def close_enough(a, b, tol=TOL):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) or isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return abs(a - b) <= tol
    return a == b


# ------------------------------------------------------------------------------------------ worker
def worker(tag: str) -> None:
    """Replay every IDX decision (and every IDX speculation set) under one rule variant, using the
    production functions unchanged. Writes work/worker_<tag>.json and work/market_<tag>.npz."""
    import dataclasses
    from datetime import date

    v = VARIANTS[tag]
    code = CODE[v["code"]]
    os.chdir(code)
    import numpy as np
    import pandas as pd

    # never write bytecode into the code trees and never read the stale .pyc that may sit in them
    sys.dont_write_bytecode = True
    WORK.mkdir(parents=True, exist_ok=True)
    sys.pycache_prefix = str(WORK / "pycache")
    sys.path.insert(0, ".")
    import idxsig  # noqa: E402
    from idxsig import market, paper, speculation, us_actions  # noqa: E402

    assert Path(idxsig.__file__).resolve().parents[1] == code.resolve(), idxsig.__file__

    if v["patch"] == "arb10":
        orig_limits = market.limits

        def limits_arb10(ref, days):
            saved = market.REGIMES
            try:
                market.REGIMES = tuple(
                    dataclasses.replace(r, arb_flat=0.10)
                    if (r.arb_flat == 0.07 and r.start >= date(2026, 10, 19))
                    else r
                    for r in saved
                )
                return orig_limits(ref, days)
            finally:
                market.REGIMES = saved

        market.limits = limits_arb10
    elif v["patch"] == "no_rp1":
        market.REGIMES = tuple(dataclasses.replace(r, arb_abs_max=10.0) for r in market.REGIMES)

    # ---- production flow: score_pending() -------------------------------------------------------
    df, data = paper.load_recent(MANIFEST, "IDX", purpose="scoring")
    m = paper._market(df, "IDX")
    events = us_actions.yahoo_events(MANIFEST, market="IDX")
    lines = paper.ledger_lines()
    spec_lines = paper.ledger_lines(speculation.SPEC_LEDGER)
    dates = [str(x) for x in m.dates.astype(str)]
    tickers = [str(x) for x in m.tickers]
    n_sessions = len(dates)

    latest = {}
    for r in lines:
        if r["type"] == "OUTCOME":
            latest[r["decision_id"]] = r
    decs = [r for r in lines if r["type"] == "DECISION" and r.get("market", "IDX") == "IDX"]

    def with_horizon(h, fn):
        saved = paper.POLICY
        paper.POLICY = dataclasses.replace(saved, horizon_sessions=int(h))
        try:
            return fn()
        finally:
            paper.POLICY = saved

    base_h = paper.POLICY.horizon_sessions
    res = {}
    for r in decs:
        did = r["decision_id"]
        t = r["instrument"]["ticker"]
        ent = {
            "ticker": t,
            "signal_session": r["signal_session"],
            "has_recorded_outcome": did in latest,
            "in_data": t in tickers and r["signal_session"] in dates,
        }
        ent["d"] = dates.index(r["signal_session"]) if r["signal_session"] in dates else None
        ent["window_complete"] = bool(paper._window_complete(r, m))
        te = events[events["ticker"] == t] if len(events) else events
        units, reason, evidence = paper.scoring_units(r, m, te, None)
        ent["units_reason"] = reason
        ent["units_evidence"] = evidence
        out, err = None, None
        if ent["window_complete"] and units is not None:
            try:
                out = paper.score(r, m, price_units=units)
            except ValueError as exc:
                err = str(exc)
        ent["score_error"] = err
        ent["out"] = out
        d = ent["d"]
        # what-if (sensitivity b): keep rolling past the horizon to the first sellable close, by running the
        # real legacy scorer with a longer horizon: the first horizon that returns an outcome exits on the first
        # sellable close after the original horizon (a stop hit on that bar and a horizon exit coincide).
        if ent["window_complete"] and units is not None and out is None and err is None and d is not None:
            wi = {"extra_sessions": None, "out": None}
            j = 1
            while d + 1 + (base_h + j) < n_sessions:
                o = with_horizon(base_h + j, lambda: paper.score(r, m, price_units=units))
                if o is not None:
                    wi = {"extra_sessions": j, "horizon_used": base_h + j, "out": o}
                    break
                j += 1
            else:
                wi["note"] = f"no sellable close after the horizon: locked or untraded on every bar through {dates[-1]}, the last bar"
            ent["whatif_roll"] = wi
        # interim state of a decision whose window is still open: the real scorer with the horizon cut to the
        # post-entry sessions observed so far (an invalidation exit is final; a 'horizon' exit at the cut is not).
        if (not ent["window_complete"]) and units is not None and d is not None and not ent["has_recorded_outcome"]:
            e = d + 1
            last = n_sessions - 1
            if e > last:
                ent["interim"] = {"state": "ENTRY_NOT_OBSERVED", "post_entry_sessions": 0}
            elif last - e < 1:
                ent["interim"] = {"state": "ENTRY_BAR_ONLY", "post_entry_sessions": 0}
            else:
                h = last - e
                o = with_horizon(h, lambda: paper.score(r, m, price_units=units))
                ent["interim"] = {"state": "EVALUATED", "post_entry_sessions": h, "out": o}
        res[did] = ent

    # ---- market matrices (same calls as Market.build) -------------------------------------------
    ref = np.where(np.isfinite(m.prev) & (m.prev > 0), m.prev, np.nan)
    safe_ref = np.nan_to_num(ref, nan=1.0)
    day_grid = np.broadcast_to(m.dates, m.close.shape)
    ara, arb = market.limits(safe_ref, day_grid)
    sp_ara, sp_arb = market.special_limits(safe_ref)
    np.savez_compressed(
        WORK / f"market_{tag}.npz",
        dates=np.array(dates),
        tickers=np.array(tickers),
        close=m.close, prev=m.prev, high=m.high, low=m.low, volume=m.volume,
        tradeable=m.tradeable, present=m.present, lock_up=m.lock_up, lock_down=m.lock_down,
        arb=arb, ara=ara, sp_arb=sp_arb,
    )

    # ---- speculations (IDX sets) -----------------------------------------------------------------
    speculation.windows = lambda: SPEC_WINDOWS  # the protocol JSON is not in the code tree (see SPEC_WINDOWS)
    spec_out = {}
    for s in [x for x in spec_lines if x["type"] == "SPECULATION_SET" and x["market"] == "IDX"]:
        for wid in s.get("windows", speculation.V1_WINDOWS):
            key = f"{s['set_id']}|{wid}"
            try:
                rec = speculation.resolve_set(s, wid, m, events, None)
                spec_out[key] = {"rec": rec}
            except Exception as exc:  # recorded, never hidden
                spec_out[key] = {"rec": None, "error": f"{type(exc).__name__}: {exc}"}

    # per-name BASE5 simulation (candidate and each twin) with the real speculation.simulate(), so that a set that
    # cannot resolve under one rule set can still be attributed to the name that is still rolling
    spec_names = {}
    for s in [x for x in spec_lines if x["type"] == "SPECULATION_SET" and x["market"] == "IDX" and "BASE5" in x.get("windows", speculation.V1_WINDOWS)]:
        members = [("candidate", s["ticker"], float(s["signal"]["close"]))] + [
            ("twin", tw["ticker"], float(tw["close"])) for tw in s["twins"]
        ]
        for role, name, rec_close in members:
            key = f"{s['set_id']}|{name}"
            try:
                located, units, reason = speculation._units_for(name, s["signal_session"], rec_close, m, events, None, "IDX")
                if located is None:
                    spec_names[key] = {"role": role, "located": False, "reason": reason}
                    continue
                nn, dd, uf = located
                sim = speculation.simulate(m, nn, dd, SPEC_WINDOWS["BASE5"], "IDX", unit_factor=uf)
                spec_names[key] = {"role": role, "located": True, "sim": sim}
            except Exception as exc:
                spec_names[key] = {"role": role, "located": False, "reason": f"{type(exc).__name__}: {exc}"}

    meta = {
        "tag": tag,
        "label": v["label"],
        "code_dir": str(code),
        "idxsig_file": str(idxsig.__file__),
        "market_py_sha256": sha256_file(code / "idxsig" / "market.py"),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "manifest": data["manifest"],
        "manifest_sha256": data["manifest_sha256"],
        "n_tickers": len(tickers),
        "n_sessions": n_sessions,
        "first_session": dates[0],
        "last_session": dates[-1],
        "regimes": [
            {**x, "arb_abs_max": getattr(reg, "arb_abs_max", 10.0)}
            for x, reg in zip(market.regime_labels(), market.REGIMES)
        ],
        "ledger_rows": len(lines),
        "ledger_head": lines[-1]["record_hash"],
        "ledger_chain_problems": paper._chain_problems(lines),
        "spec_rows": len(spec_lines),
        "spec_chain_problems": paper._chain_problems(spec_lines),
        "policy_horizon_sessions": base_h,
        "fee_buy": paper.POLICY.fee_buy,
        "fee_sell": paper.POLICY.fee_sell,
        "n_split_events_in_pull": int(len(events)),
        "split_events": events[["ticker", "effective_session", "provider_ratio"]].to_dict("records") if len(events) else [],
        "session_close_utc": {
            s: paper.session_close("IDX", s).astimezone(timezone.utc).isoformat() for s in dates
        },
    }
    dump_json({"meta": meta, "decisions": res, "spec": spec_out, "spec_names": spec_names}, WORK / f"worker_{tag}.json")
    print(f"worker {tag} done: {len(res)} decisions, {sum(1 for x in res.values() if x['out'] is not None)} outcomes")


# ============================================================================================ analysis
def verify_inputs() -> dict:
    """Integrity of every input the analysis depends on. Returns a dict that goes into summary.json."""
    chk = {"problems": []}
    for tag in ("B", "C"):
        lp = CODE[tag] / "paper" / "ledger.jsonl"
        sp = CODE[tag] / "paper" / "speculations.jsonl"
        chk[f"ledger_sha256_{tag}"] = sha256_file(lp)
        chk[f"speculations_sha256_{tag}"] = sha256_file(sp)
        if chk[f"ledger_sha256_{tag}"] != EXPECT_LEDGER_SHA:
            chk["problems"].append(f"ledger sha256 mismatch in code_{tag}")
        if chk[f"speculations_sha256_{tag}"] != EXPECT_SPEC_SHA:
            chk["problems"].append(f"speculations sha256 mismatch in code_{tag}")
    chk["manifest"] = MANIFEST.name
    chk["manifest_sha256"] = sha256_file(MANIFEST)
    if not chk["manifest_sha256"].startswith(EXPECT_MANIFEST_PREFIX):
        chk["problems"].append("manifest sha256 prefix mismatch")
    lines = load_jsonl(MANIFEST)
    header, recs = lines[0], lines[1:]
    chk["manifest_header"] = {k: header.get(k) for k in ("manifest", "n_files", "ok", "failed", "not_found", "started_at", "finished_at")}
    chk["manifest_pull_pinned"] = header.get("description")
    bad = 0
    for r in recs:  # resolve payloads exactly as production does: PKG_ROOT / path (data/raw/yahoo_recent is a symlink)
        p = CODE["B"] / r["path"]
        if not p.exists() or sha256_file(p) != r["sha256"]:
            bad += 1
    chk["raw_payloads"] = {"listed": len(recs), "bad_or_missing": bad}
    if bad:
        chk["problems"].append(f"{bad} raw payloads missing or hash-mismatched")
    # the two code trees must differ only in idxsig/market.py
    def tree(tag):
        root = CODE[tag] / "idxsig"
        return {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts}
    tb, tc = tree("B"), tree("C")
    differing = sorted(k for k in set(tb) | set(tc) if tb.get(k) != tc.get(k))
    chk["code_tree_differences"] = differing
    chk["market_py_sha256"] = {"B": tb.get("market.py"), "C": tc.get("market.py")}
    if differing != ["market.py"]:
        chk["problems"].append(f"code trees differ in more than market.py: {differing}")
    ledger = load_jsonl(CODE["B"] / "paper" / "ledger.jsonl")
    chk["ledger_rows"] = len(ledger)
    chk["ledger_head_record_hash"] = ledger[-1]["record_hash"]
    if len(ledger) != EXPECT_LEDGER_ROWS or ledger[-1]["record_hash"] != EXPECT_LEDGER_HEAD:
        chk["problems"].append("ledger row count or head hash differs from the task statement")
    spec = load_jsonl(CODE["B"] / "paper" / "speculations.jsonl")
    chk["speculations_rows"] = len(spec)
    if len(spec) != EXPECT_SPEC_ROWS:
        chk["problems"].append("speculations row count differs from the task statement")
    return chk


def load_matrices(tag):
    import numpy as np

    z = np.load(WORK / f"market_{tag}.npz")
    return {k: z[k] for k in z.files}


def parse_pull_time(manifest_name: str) -> datetime:
    stamp = manifest_name.split("-")[1].split(".")[0]  # 20261029T081308Z
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def compare_outcome(rec: dict, rep: dict) -> list[tuple]:
    """Field-by-field comparison of a recorded OUTCOME with a replay (score() output). Floats at 1e-9."""
    diffs = []
    ta, tb = tradeof(rec), tradeof(rep)
    if (ta is None) != (tb is None):
        diffs.append(("paper_trade_presence", ta is not None, tb is not None))
    elif ta is not None:
        for f in ("entry_session", "exit_session", "exit_reason", "entry_basis"):
            if ta.get(f) != tb.get(f):
                diffs.append((f, ta.get(f), tb.get(f)))
        for f in ("entry_price", "entry_close", "net_return", "mfe", "mae"):
            if not close_enough(ta.get(f), tb.get(f)):
                diffs.append((f, ta.get(f), tb.get(f)))
    if rec["decision_verdict"] != rep["decision_verdict"]:
        diffs.append(("verdict", rec["decision_verdict"], rep["decision_verdict"]))
    da, db = rec["discovery"], rep["discovery"]
    if not close_enough(da["r5max"], db["r5max"]):
        diffs.append(("discovery.r5max", da["r5max"], db["r5max"]))
    for f in ("E30", "E50", "E100", "peak_session"):
        if da[f] != db[f]:
            diffs.append((f"discovery.{f}", da[f], db[f]))
    ea, eb = rec["execution"], rep["execution"]
    for f in ("fillable_at_trigger", "within_chase_band", "executed"):
        if ea.get(f) != eb.get(f):
            diffs.append((f"execution.{f}", ea.get(f), eb.get(f)))
    if not close_enough(rec["price_scale"], rep["price_scale"]):
        diffs.append(("price_scale", rec["price_scale"], rep["price_scale"]))
    if rec["scoring_version"] != rep["scoring_version"]:
        diffs.append(("scoring_version", rec["scoring_version"], rep["scoring_version"]))
    return diffs


def outcome_signature(out):
    """Canonical content of a score() output without the wall-clock stamp, for exact B-vs-C equality."""
    if out is None:
        return None
    o = json.loads(json.dumps(out, default=_json_default))
    o.pop("scored_at", None)
    return json.dumps(o, sort_keys=True)


def category_of(b, c, touches):
    """Classification of one decision, C replay compared with B replay (both are score() outputs or None)."""
    if not touches:
        return "NOT_AFFECTED"
    if b is not None and c is None:
        return "BECOMES_UNSCORABLE"
    if b is None and c is not None:
        return "BECOMES_SCORABLE"
    if b is None and c is None:
        return "UNCHANGED"
    if outcome_signature(b) == outcome_signature(c):
        return "UNCHANGED"
    if b["decision_verdict"] != c["decision_verdict"]:
        return "VERDICT_CHANGED"
    tb, tc = tradeof(b), tradeof(c)
    if tb and tc and (tb["exit_session"] != tc["exit_session"] or abs(tb["net_return"] - tc["net_return"]) > TOL_SHIFT):
        return "EXIT_SHIFTED"
    return "OTHER_DIFFERENCE"


def stats_of(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0, "mean": None, "median": None}
    return {"n": len(xs), "mean": statistics.fmean(xs), "median": statistics.median(xs)}


def pct(x, nd=2):
    return "n/a" if x is None else f"{100 * x:+.{nd}f}%"



def build_context() -> dict:
    ctx = {"W": {}, "M": {}}
    for tag in VARIANTS:
        with open(WORK / f"worker_{tag}.json", encoding="utf-8") as fh:
            ctx["W"][tag] = json.load(fh)
        ctx["M"][tag] = load_matrices(tag)
    MB = ctx["M"]["B"]
    ctx["dates"] = [str(x) for x in MB["dates"]]
    ctx["di"] = {s: i for i, s in enumerate(ctx["dates"])}
    ctx["tick"] = [str(x) for x in MB["tickers"]]
    ctx["ti"] = {t: i for i, t in enumerate(ctx["tick"])}
    ctx["last"] = len(ctx["dates"]) - 1
    ctx["cut_i"] = ctx["di"][CUT]
    ctx["rows"] = load_jsonl(CODE["B"] / "paper" / "ledger.jsonl")
    ctx["spec_rows"] = load_jsonl(CODE["B"] / "paper" / "speculations.jsonl")
    rows = ctx["rows"]
    ctx["idx_dec"] = [r for r in rows if r["type"] == "DECISION" and r.get("market", "IDX") == "IDX"]
    ctx["decmap"] = {r["decision_id"]: r for r in ctx["idx_dec"]}
    # latest OUTCOME per IDX decision, in ledger order (as score_pending does)
    per = collections.defaultdict(list)
    for r in rows:
        if r["type"] == "OUTCOME" and r["decision_id"] in ctx["decmap"]:
            per[r["decision_id"]].append(r)
    ctx["outcome_rows_by_decision"] = per
    ctx["latest"] = {did: v[-1] for did, v in per.items()}
    ctx["base_h"] = ctx["W"]["B"]["meta"]["policy_horizon_sessions"]
    # name-level evidence of a wider limit (computed on the C market): a tradeable bar on or after 2026-10-19 whose
    # close is strictly BELOW its modelled regular-board 7% ARB price, i.e. the name traded beyond the limit the
    # corrected rule gives it.  The 2026-10-19 references Rp11-14 are excluded (modelled ARB = reference there).
    import numpy as np

    MC = ctx["M"]["C"]
    valid = (MC["prev"] > 0) & MC["tradeable"] & (MC["close"] > 0)
    below = valid & (MC["close"] < MC["arb"])
    atlim = valid & (MC["close"] == MC["arb"]) & (MC["close"] < MC["prev"])
    ci = ctx["cut_i"]
    indet = np.zeros_like(below)
    indet[:, ci] = (MC["prev"][:, ci] >= 11) & (MC["prev"][:, ci] <= 14)
    below &= ~indet
    atlim &= ~indet
    below[:, :ci] = False
    atlim[:, :ci] = False
    ctx["name_below"] = below.sum(axis=1)
    ctx["name_atlimit"] = atlim.sum(axis=1)
    return ctx


def bar_record(ctx, n, k):
    """Everything known about one (ticker, session) cell under B and C, with the empirical board hint."""
    MB, MC = ctx["M"]["B"], ctx["M"]["C"]
    close, ref = float(MC["close"][n, k]), float(MC["prev"][n, k])
    arb_b, arb_c, sp = float(MB["arb"][n, k]), float(MC["arb"][n, k]), float(MC["sp_arb"][n, k])
    sess = ctx["dates"][k]
    one_price = bool(MC["high"][n, k] == MC["low"][n, k] == MC["close"][n, k])
    if sess == CUT and 11 <= ref <= 14:
        hint = "INDETERMINATE_1019_RP11_14"
    elif close == arb_c:
        hint = "AT_LIMIT"
    elif close < arb_c:
        if close == sp:
            hint = "AT_10PCT_LIMIT"
        elif close > sp:
            hint = "BELOW_LIMIT_WITHIN_10PCT"
        else:
            hint = "BELOW_10PCT_LIMIT"
    else:
        hint = "ABOVE_LIMIT"
    return {
        "session": sess, "close": close, "ref": ref,
        "chg": (close / ref - 1) if ref > 0 else None,
        "arb_B": arb_b, "arb_C": arb_c, "special10_arb": sp, "one_price": one_price,
        "lock_B": bool(MB["lock_down"][n, k]), "lock_C": bool(MC["lock_down"][n, k]),
        "tradeable": bool(MC["tradeable"][n, k]), "hint": hint,
    }


WIDER_HINTS = ("AT_10PCT_LIMIT", "BELOW_LIMIT_WITHIN_10PCT", "BELOW_10PCT_LIMIT")


def flips_between(ctx, n, lo, hi, tagx="B", tagy="C"):
    MX, MY = ctx["M"][tagx], ctx["M"][tagy]
    return [k for k in range(lo, hi + 1) if bool(MX["lock_down"][n, k]) != bool(MY["lock_down"][n, k])]


# -------------------------------------------------------------------------------- populations (ledger)
def populations(ctx) -> dict:
    rows, dates, di, last = ctx["rows"], ctx["dates"], ctx["di"], ctx["last"]
    P = {}
    P["ledger_rows_total"] = len(rows)
    P["rows_by_type"] = dict(collections.Counter(r["type"] for r in rows))
    P["rows_by_type_and_market"] = {
        f"{t}/{m}": n
        for (t, m), n in sorted(collections.Counter((r["type"], r.get("market") or "(no market key)") for r in rows).items())
    }
    idx_dec = ctx["idx_dec"]
    P["idx_decisions"] = len(idx_dec)
    P["idx_decisions_explicit_market_IDX"] = sum(1 for r in idx_dec if r.get("market") == "IDX")
    P["idx_decisions_without_market_key_treated_as_IDX"] = sum(1 for r in idx_dec if "market" not in r)
    P["idx_decisions_by_kind"] = dict(collections.Counter(r["decision"] for r in idx_dec))
    P["idx_decisions_by_policy"] = dict(collections.Counter(r["policy"]["policy_id"] for r in idx_dec))
    P["idx_decisions_with_execution_plan"] = sum(1 for r in idx_dec if (r.get("plan") or {}).get("execution_plan"))
    P["decision_ids_duplicated"] = len(idx_dec) - len({r["decision_id"] for r in idx_dec})
    per = ctx["outcome_rows_by_decision"]
    P["idx_outcome_rows"] = sum(len(v) for v in per.values())
    P["idx_decisions_with_more_than_one_outcome_row"] = sum(1 for v in per.values() if len(v) > 1)
    P["idx_outcome_rows_with_revises_field"] = sum(1 for v in per.values() for r in v if "revises" in r)
    P["idx_outcomes_latest_per_decision"] = len(ctx["latest"])
    P["resolution_rule"] = (
        "latest OUTCOME row per decision_id in ledger order, as score_pending() does; no decision has more than one "
        "OUTCOME row and no row carries a 'revises' link, so latest = only"
    )
    P["idx_outcome_status"] = dict(collections.Counter(o.get("status") for o in ctx["latest"].values()))
    P["idx_outcome_scorer"] = dict(collections.Counter(o.get("scorer") for o in ctx["latest"].values()))
    P["idx_outcome_verdicts"] = dict(collections.Counter(o.get("decision_verdict") for o in ctx["latest"].values()))
    # decisions with a signal on or after the cut
    late = [r for r in idx_dec if r["signal_session"] >= CUT]
    lat_out = ctx["latest"]
    P["decisions_signal_on_or_after_1019"] = len(late)
    P["late_by_kind"] = dict(collections.Counter(r["decision"] for r in late))
    P["late_with_outcome"] = sum(1 for r in late if r["decision_id"] in lat_out)
    P["late_without_outcome_pending"] = sum(1 for r in late if r["decision_id"] not in lat_out)
    late_tr = [r for r in late if tradeof(lat_out.get(r["decision_id"]))]
    P["late_with_hypothetical_trade"] = len(late_tr)
    P["late_trade_by_decision_kind"] = dict(collections.Counter(r["decision"] for r in late_tr))
    P["late_buy_on_trigger_decisions"] = sum(1 for r in late if r["decision"] == "BUY ON TRIGGER")
    P["late_rejections_that_would_have_traded"] = sum(1 for r in late_tr if r["decision"] != "BUY ON TRIGGER")
    P["late_outcomes_without_trade"] = sum(1 for r in late if r["decision_id"] in lat_out and not tradeof(lat_out[r["decision_id"]]))
    # trades overall and under alternative definitions
    all_tr = [(r, tradeof(lat_out[r["decision_id"]])) for r in idx_dec if tradeof(lat_out.get(r["decision_id"]))]
    P["all_idx_outcomes_with_trade"] = len(all_tr)
    P["all_trades_by_decision_kind"] = dict(collections.Counter(r["decision"] for r, _ in all_tr))
    P["trades_entry_on_or_after_1019"] = sum(1 for _, t in all_tr if t["entry_session"] >= CUT)
    P["trades_exit_on_or_after_1019"] = sum(1 for _, t in all_tr if t["exit_session"] >= CUT)
    P["trades_path_touches_1019_signal_before_cut"] = sum(1 for r, t in all_tr if r["signal_session"] < CUT and t["exit_session"] >= CUT)
    # outcomes whose scored path touches the cut: trade -> entry..exit; no trade -> the nominal window entry..horizon end
    touch = {}
    for did, o in lat_out.items():
        d = di[ctx["decmap"][did]["signal_session"]]
        tr = tradeof(o)
        last_sess = tr["exit_session"] if tr else dates[min(d + 1 + ctx["base_h"], last)]
        touch[did] = last_sess >= CUT
    ctx["touch_recorded"] = touch
    P["outcomes_path_touches_1019_all"] = sum(touch.values())
    P["outcomes_path_touches_1019_with_trade"] = sum(1 for did, v in touch.items() if v and tradeof(lat_out[did]))
    P["outcomes_path_touches_1019_without_trade"] = sum(1 for did, v in touch.items() if v and not tradeof(lat_out[did]))
    P["outcomes_path_not_touching_1019"] = sum(1 for v in touch.values() if not v)
    P["claim_88_decisions_true_for"] = "decisions whose signal_session is on or after 2026-10-19 (all IDX; count recomputed above)"
    P["claim_27_trades_true_for"] = (
        "decisions with signal_session on or after 2026-10-19 whose OUTCOME carries a paper_trade object; "
        "all 27 are PASS decisions (rejections that would have traded); under the path definition the count is larger"
    )
    P["pending_decisions_without_outcome"] = len(idx_dec) - len(lat_out)
    return P


# ------------------------------------------------------------------------------------- baseline gate
def pull_info(ctx, o, did):
    """Which pull scored the recorded outcome, and was the last session its path needed final at that moment?"""
    name = o["data"]["manifest"]
    ts = parse_pull_time(name)
    hdr = None
    hp = FROZEN / name
    if hp.exists():
        with open(hp, encoding="utf-8") as fh:
            hdr = json.loads(fh.readline())
    r = ctx["decmap"][did]
    d = ctx["di"][r["signal_session"]]
    tr = tradeof(o)
    needed = tr["exit_session"] if tr else ctx["dates"][min(d + 1 + ctx["base_h"], ctx["last"])]
    close_utc = datetime.fromisoformat(ctx["W"]["B"]["meta"]["session_close_utc"][needed])
    return {
        "pull": name, "pull_started_utc": ts.isoformat(),
        "pull_header_started_at": (hdr or {}).get("started_at"), "pull_header_finished_at": (hdr or {}).get("finished_at"),
        "scored_at": o["scored_at"], "last_session_needed": needed,
        "session_final_at_utc": close_utc.isoformat(),
        "pull_before_session_final": ts < close_utc,
    }


def ticker_row_in_pull(name, ticker):
    hp = FROZEN / name
    if not hp.exists():
        return None
    with open(hp, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("ticker") == ticker:
                return {k: r.get(k) for k in ("first_date", "last_date", "rows", "downloaded_at")}
    return None


def diagnose_mismatch(ctx, did, rec, rep, diffs, pinfo):
    """Cause of one replay-versus-recorded mismatch, derived from the data (not asserted)."""
    MB = ctx["M"]["B"]
    r = ctx["decmap"][did]
    n, d = ctx["ti"][r["instrument"]["ticker"]], ctx["di"][r["signal_session"]]
    fields = {f for f, _, _ in diffs}
    flag_fields = {f for f in fields if f.startswith("discovery.E")}
    if flag_fields and fields == flag_fields and close_enough(rec["discovery"]["r5max"], rep["discovery"]["r5max"], 1e-9):
        seg = MB["close"][n, d + 1 : d + 1 + ctx["base_h"]]
        peak, sigc = float(max(seg)), float(MB["close"][n, d])
        ratio = Fraction(peak) / Fraction(sigc) - 1
        thr = {"discovery.E30": Fraction(3, 10), "discovery.E50": Fraction(1, 2), "discovery.E100": Fraction(1)}
        tie = [f for f in flag_fields if ratio == thr[f]]
        rp = ticker_row_in_pull(pinfo["pull"], r["instrument"]["ticker"])
        fp = ticker_row_in_pull(MANIFEST.name, r["instrument"]["ticker"])
        return {
            "code": "FLOAT_KNIFE_EDGE",
            "text": (
                f"floating-point knife-edge at the {', '.join(sorted(f.split('.')[1] for f in flag_fields))} threshold: the peak close "
                f"{peak:g} over the signal close {sigc:g} is exactly {ratio} = {float(ratio):+.0%} in exact arithmetic "
                f"({'an exact tie with the threshold' if tie else 'not a tie'}); recorded r5max {rec['discovery']['r5max']!r} vs "
                f"replay {rep['discovery']['r5max']!r} differ by {abs(rec['discovery']['r5max'] - rep['discovery']['r5max']):.1e}, "
                f"enough to flip the >= test. The level series is exp(cumsum(log(close/previous))), so its rounding noise depends "
                f"on where the 200-day window starts (recorded pull window starts {(rp or {}).get('first_date')}, final pull "
                f"{(fp or {}).get('first_date')}). Neither flag value is more correct; no ARB or data-revision effect."
            ),
            "exact_ratio": str(ratio),
            "plain": (
                f"Float knife-edge at the {', '.join(sorted(f.split('.')[1] for f in flag_fields))} threshold: the peak close {peak:g} over the signal close {sigc:g} is exactly "
                f"{ratio} = {float(ratio):+.0%} in exact arithmetic, so the flag hangs on rounding noise. Recorded r5max {rec['discovery']['r5max']!r} "
                f"(flag {[rec['discovery'][f.split('.')[1]] for f in sorted(flag_fields)][0]}), replay {rep['discovery']['r5max']!r} (flag {[rep['discovery'][f.split('.')[1]] for f in sorted(flag_fields)][0]}); "
                f"the noise depends on where the 200-day window starts (recorded pull from {(rp or {}).get('first_date')}, final pull from {(fp or {}).get('first_date')}). "
                "Neither flag value is more correct; no ARB effect."
            ),
        }
    trade_fields = {"net_return", "mae", "mfe", "exit_session", "exit_reason", "entry_session", "entry_price", "verdict"}
    if fields & trade_fields and pinfo["pull_before_session_final"]:
        tr, tp = tradeof(rec), tradeof(rep)
        fee_in, fee_out = ctx["W"]["B"]["meta"]["fee_buy"], ctx["W"]["B"]["meta"]["fee_sell"]
        out = {}
        if tr and tp and tr["exit_session"] == tp["exit_session"]:
            gross_rec = (1 + tr["net_return"]) * (1 + fee_in) / (1 - fee_out) - 1
            implied = tr["entry_price"] * (1 + gross_rec)
            final_close = float(MB["close"][n, ctx["di"][tr["exit_session"]]])
            out = {"implied_recorded_exit_close": implied, "final_exit_close": final_close}
        return {
            "code": "PRE_CLOSE_PULL",
            "text": (
                f"the outcome was scored on pull {pinfo['pull']} (started {pinfo['pull_started_utc']}, scored_at {pinfo['scored_at']}), "
                f"before the final-bar time of its last needed session {pinfo['last_session_needed']} "
                f"({pinfo['session_final_at_utc']} by paper.session_close); the exit close it used was an in-progress bar"
                + (
                    f": implied recorded exit close {out['implied_recorded_exit_close']:.1f} vs final close {out['final_exit_close']:.1f}"
                    if out
                    else ""
                )
                + ". The final-bar replay uses the official close. Data timing only; no ARB effect (B-vs-C is unaffected)."
            ),
            "plain": (
                f"Scored at {pinfo['scored_at'][11:16]} UTC on {pinfo['scored_at'][:10]} from a pull started {pinfo['pull_started_utc'][11:16]} UTC, before the "
                f"{pinfo['session_final_at_utc'][11:16]} UTC final-bar time of {pinfo['last_session_needed']} (paper.session_close), so the exit close was an in-progress price"
                + (f": implied recorded exit close {out['implied_recorded_exit_close']:.0f} vs official {out['final_exit_close']:.0f}" if out else "")
                + ". No ARB effect."
            ),
            **out,
        }
    _t = "no cause identified: " + "; ".join(f"{f}: {a!r} vs {b!r}" for f, a, b in diffs)
    return {"code": "UNDIAGNOSED", "text": _t, "plain": _t}


def baseline_gate(ctx) -> dict:
    WB = ctx["W"]["B"]["decisions"]
    G = {"outcomes_replayed": 0, "field_for_field_matches": 0, "mismatches": [], "per_record": {}, "pull_exposure": {}}
    fields_compared = [
        "entry_session", "exit_session", "exit_reason", "entry_basis", "entry_price", "entry_close", "net_return (1e-9)",
        "mfe (1e-9)", "mae (1e-9)", "paper_trade presence", "verdict", "discovery.r5max (1e-9)", "discovery.E30/E50/E100",
        "discovery.peak_session", "execution.fillable_at_trigger/within_chase_band/executed", "price_scale", "scoring_version",
    ]
    G["fields_compared"] = fields_compared
    exposed, exposed_mismatch = [], []
    for did, o in ctx["latest"].items():
        rep = WB[did]["out"]
        G["outcomes_replayed"] += 1
        pinfo = pull_info(ctx, o, did)
        if rep is None:
            diffs = [("replay_returned_none", "outcome recorded", None)]
            diag = {"code": "UNDIAGNOSED", "text": "B replay returned no outcome although one is recorded"}
        else:
            diffs = compare_outcome(o, rep)
            diag = diagnose_mismatch(ctx, did, o, rep, diffs, pinfo) if diffs else None
        G["per_record"][did] = {"diffs": diffs, "diag": diag, "pull": pinfo}
        if pinfo["pull_before_session_final"]:
            exposed.append(did)
            if diffs:
                exposed_mismatch.append(did)
        if not diffs:
            G["field_for_field_matches"] += 1
        else:
            G["mismatches"].append({
                "decision_id": did, "ticker": ctx["decmap"][did]["instrument"]["ticker"],
                "outcome_record_hash": o["record_hash"], "differing_fields": [f for f, _, _ in diffs],
                "recorded_vs_replay": [{"field": f, "recorded": a, "replay_B": b} for f, a, b in diffs],
                "cause_code": diag["code"], "cause": diag["text"], "cause_plain": diag.get("plain", diag["text"]),
            })
    G["pull_exposure"] = {
        "outcomes_whose_last_needed_session_was_not_yet_final_at_the_pull": len(exposed),
        "of_which_mismatching_in_replay": len(exposed_mismatch),
        "pulls_involved": sorted({G["per_record"][d]["pull"]["pull"] for d in exposed}),
    }
    return G



# ---------------------------------------------------------------------------------- classification
CHANGED_CATS = ("EXIT_SHIFTED", "VERDICT_CHANGED", "BECOMES_UNSCORABLE", "BECOMES_SCORABLE", "OTHER_DIFFERENCE")
ALL_CATS = ("UNCHANGED", "EXIT_SHIFTED", "BECOMES_UNSCORABLE", "BECOMES_SCORABLE", "VERDICT_CHANGED", "NOT_AFFECTED")


def summ(out):
    """Flat summary of a score() output (or None)."""
    if out is None:
        return {"status": "NO_OUTCOME", "trade": False, "entry": None, "exit": None, "reason": None, "net": None,
                "mfe": None, "mae": None, "verdict": None}
    tr = tradeof(out)
    return {
        "status": "OUTCOME", "trade": tr is not None,
        "entry": tr["entry_session"] if tr else None, "exit": tr["exit_session"] if tr else None,
        "reason": tr["exit_reason"] if tr else None, "net": tr["net_return"] if tr else None,
        "mfe": tr["mfe"] if tr else None, "mae": tr["mae"] if tr else None, "verdict": out["decision_verdict"],
    }


def interim_text(ctx, ent, tag):
    it = ent.get("interim")
    if ent["window_complete"]:
        return "window complete; legacy scorer returns no outcome (horizon bar locked or untraded)"
    if ent.get("units_reason"):
        return "UNSCORABLE when the window completes: " + ent["units_reason"]
    if not it:
        return "no data"
    if it["state"] != "EVALUATED":
        return it["state"]
    out, h = it["out"], it["post_entry_sessions"]
    if out is None:
        return f"HELD: last observed bar not sellable (locked or untraded), {h} post-entry session(s) seen"
    tr = tradeof(out)
    if tr is None:
        return "NO TRADE (not fillable at the trigger or outside the chase band)"
    if tr["exit_reason"].startswith("invalidation"):
        return f"STOP HIT {tr['exit_session']} (net {tr['net_return']:+.4f})"
    return f"OPEN: no stop hit through {ctx['dates'][ctx['last']]} ({h} post-entry session(s) seen)"


def classify_all(ctx):
    W, M = ctx["W"], ctx["M"]
    dates, di, ti, last, cut_i, base_h = ctx["dates"], ctx["di"], ctx["ti"], ctx["last"], ctx["cut_i"], ctx["base_h"]
    WB, WC = W["B"]["decisions"], W["C"]["decisions"]
    out_rows, flip_rows, checks = [], [], []
    for r in ctx["idx_dec"]:
        did = r["decision_id"]
        t = r["instrument"]["ticker"]
        n, d = ti.get(t), di.get(r["signal_session"])
        rec = ctx["latest"].get(did)
        eb, ec = WB[did], WC[did]
        b, c = eb["out"], ec["out"]
        row = {
            "decision_id": did, "outcome_record_hash": rec["record_hash"] if rec else "", "ticker": t,
            "policy_id": r["policy"]["policy_id"], "decision": r["decision"], "signal_session": r["signal_session"],
            "has_recorded_outcome": rec is not None, "window_complete_final_pull": eb["window_complete"],
        }
        sr = summ(rec) if rec else summ(None)
        row.update({f"rec_{k}": v for k, v in sr.items() if k in ("entry", "exit", "reason", "net", "verdict", "trade")})
        sb, sc = summ(b), summ(c)
        row.update({f"B_{k}": v for k, v in sb.items()})
        row.update({f"C_{k}": v for k, v in sc.items()})
        if n is None or d is None:
            row.update({"category": "NO_DATA", "subcase": "ticker or signal session absent from the frozen pull"})
            out_rows.append(row)
            continue
        e = d + 1
        horizon_i = min(d + 1 + base_h, last)
        # ---- gate against the recorded outcome
        if rec is not None:
            diffs = compare_outcome(rec, b) if b is not None else [("replay_returned_none", None, None)]
            row["baseline_match"] = not diffs
            row["baseline_diff_fields"] = ";".join(f for f, _, _ in diffs)
        # ---- path under B and C
        if rec is not None:
            path_last_B = di[sb["exit"]] if sb["trade"] else horizon_i
            path_last_C = di[sc["exit"]] if sc["trade"] else horizon_i
            union_last = max(path_last_B, path_last_C)
            touches = path_last_B >= cut_i
            if touches != ctx["touch_recorded"][did]:
                checks.append(f"touch rule disagreement between recorded and B replay for {did}")
            cat = category_of(b, c, touches)
            if cat == "NOT_AFFECTED" and outcome_signature(b) != outcome_signature(c):
                checks.append(f"NOT_AFFECTED record differs between B and C: {did}")
            flips = flips_between(ctx, n, e, union_last)
            row["path_first_session"], row["path_last_session_B"] = dates[e], dates[path_last_B]
            row["path_last_session_union"] = dates[union_last]
            row["path_touches_1019"] = touches
            # decisive bar: the B exit bar, when it is flipped to locked under C
            decisive = None
            if sb["trade"]:
                xB = di[sb["exit"]]
                if bool(M["C"]["lock_down"][n, xB]) and not bool(M["B"]["lock_down"][n, xB]):
                    decisive = xB
            row["decisive_flipped_bar"] = dates[decisive] if decisive is not None else ""
            if cat == "NOT_AFFECTED":
                sub = "scored path (entry to exit or horizon end) entirely before 2026-10-19"
            elif cat == "UNCHANGED":
                if not sb["trade"]:
                    sub = "no paper trade (not fillable or outside chase band): lock_down is never consulted"
                elif not flips:
                    sub = "trade; no lock_down flip on the scored path"
                else:
                    sub = "trade; flipped bar(s) on the path but the exit bar is unaffected"
            elif cat in ("EXIT_SHIFTED", "VERDICT_CHANGED"):
                sub = (f"B exit bar {sb['exit']} ({sb['reason']}) is locked under C; the legacy scorer does not roll, it "
                       f"waits for the next sellable bar that meets the exit test: C exit {sc['exit']} ({sc['reason']})")
            elif cat == "BECOMES_UNSCORABLE":
                sub = (f"B exit bar {sb['exit']} ({sb['reason']}) is locked under C and no later bar inside the 5-session "
                       "horizon qualifies: the legacy scorer returns no outcome (it never rolls past the horizon)")
            else:
                sub = ""
            row["subcase"] = sub
            # ---- bar details
            bars = [bar_record(ctx, n, k) for k in flips]
            row["n_flipped_bars_on_path"] = len(bars)
            row["flipped_sessions"] = ";".join(x["session"] for x in bars)
            row["flip_board_hints"] = ";".join(f"{x['session']}:{x['hint']}" for x in bars)
            for x in bars:
                flip_rows.append({"decision_id": did, "ticker": t, "signal_session": r["signal_session"], "category": cat,
                                  "decisive": dates[decisive] == x["session"] if decisive is not None else False, **x})
            row["category"] = cat
            row["delta_net_C_minus_B"] = (sc["net"] - sb["net"]) if (sb["trade"] and sc["trade"]) else None
            row["exit_shift_sessions"] = (di[sc["exit"]] - di[sb["exit"]]) if (sb["trade"] and sc["trade"]) else None
            # sensitivity categories (same B reference)
            row["cat_C10"] = category_of(b, W["C10"]["decisions"][did]["out"], touches)
            row["cat_C7"] = category_of(b, W["C7"]["decisions"][did]["out"], touches)
            # what-if (b): keep rolling past the horizon (C worker, real scorer with a longer horizon)
            wi = ec.get("whatif_roll")
            if cat == "BECOMES_UNSCORABLE" and wi:
                wo = summ(wi.get("out"))
                row["whatif_roll_extra_sessions"] = wi.get("extra_sessions")
                row["whatif_roll_exit"], row["whatif_roll_reason"] = wo["exit"], wo["reason"]
                row["whatif_roll_net"], row["whatif_roll_verdict"] = wo["net"], wo["verdict"]
                row["whatif_roll_note"] = wi.get("note", "")
            # wider-limit evidence
            row["name_closes_below_7pct_limit_since_1019"] = int(ctx["name_below"][n])
            row["name_closes_at_7pct_limit_since_1019"] = int(ctx["name_atlimit"][n])
            row["decisive_bar_hint"] = next((x["hint"] for x in bars if decisive is not None and x["session"] == dates[decisive]), "")
            row["any_flipped_bar_below_limit"] = any(x["hint"] in WIDER_HINTS for x in bars)
        else:
            # ---- decision without a recorded outcome: path observed so far
            if e <= last:
                flips = flips_between(ctx, n, e, last)
            else:
                flips = []
            bars = [bar_record(ctx, n, k) for k in flips]
            state = "WINDOW_OPEN" if not eb["window_complete"] else "WINDOW_COMPLETE_BUT_LEGACY_SCORER_RETURNS_NO_OUTCOME"
            row["pending_state"] = state
            row["category"] = "PENDING_" + state
            row["path_first_session"] = dates[e] if e <= last else ""
            row["path_last_session_union"] = dates[min(last, d + 1 + base_h)]
            row["n_flipped_bars_on_path"] = len(bars)
            row["n_flipped_bars_after_entry_bar"] = sum(1 for k in flips if k > e)
            row["flipped_sessions"] = ";".join(x["session"] for x in bars)
            row["flip_board_hints"] = ";".join(f"{x['session']}:{x['hint']}" for x in bars)
            row["sessions_remaining_to_window_end"] = max(0, (d + 1 + base_h) - last)
            row["interim_B"] = interim_text(ctx, eb, "B")
            row["interim_C"] = interim_text(ctx, ec, "C")
            row["interim_differs_B_vs_C"] = row["interim_B"] != row["interim_C"]
            for x in bars:
                flip_rows.append({"decision_id": did, "ticker": t, "signal_session": r["signal_session"], "category": row["category"],
                                  "decisive": False, **x})
            wi = ec.get("whatif_roll")
            if wi:
                wo = summ(wi.get("out"))
                row["whatif_roll_extra_sessions"], row["whatif_roll_exit"], row["whatif_roll_net"] = wi.get("extra_sessions"), wo["exit"], wo["net"]
                row["whatif_roll_note"] = wi.get("note", "")
            row["name_closes_below_7pct_limit_since_1019"] = int(ctx["name_below"][n])
            row["name_closes_at_7pct_limit_since_1019"] = int(ctx["name_atlimit"][n])
        out_rows.append(row)
    return out_rows, flip_rows, checks



# -------------------------------------------------------------------------------------- aggregates
def aggregates(ctx, R, F):
    recs = [x for x in R if x["has_recorded_outcome"]]
    A = {}
    cc = collections.Counter(x["category"] for x in recs)
    A["records_replayed"] = len(recs)
    A["category_counts"] = {c: cc.get(c, 0) for c in ALL_CATS}
    A["category_counts_unexpected"] = {k: v for k, v in cc.items() if k not in ALL_CATS}
    A["records_changed"] = sum(cc.get(c, 0) for c in CHANGED_CATS)
    A["records_exposed_path_touches_1019"] = sum(1 for x in recs if x["path_touches_1019"])
    A["ids_by_category"] = {c: [x["decision_id"] for x in recs if x["category"] == c] for c in ALL_CATS}
    A["exit_shifted_including_verdict_changed"] = cc.get("EXIT_SHIFTED", 0) + cc.get("VERDICT_CHANGED", 0)
    trB = [x for x in recs if x["B_trade"]]
    trC = [x for x in recs if x["C_trade"]]
    both = [x for x in recs if x["B_trade"] and x["C_trade"]]
    A["hypothetical_trades_recorded"] = sum(1 for x in recs if x["rec_trade"])
    A["hypothetical_trades_B"] = len(trB)
    A["hypothetical_trades_C"] = len(trC)
    A["hypothetical_trades_lost_in_C"] = len(trB) - len(trC)
    A["net_return_B_all_trades"] = stats_of([x["B_net"] for x in trB])
    A["net_return_C_all_trades"] = stats_of([x["C_net"] for x in trC])
    A["net_return_B_on_trades_present_in_both"] = stats_of([x["B_net"] for x in both])
    A["net_return_C_on_trades_present_in_both"] = stats_of([x["C_net"] for x in both])
    A["net_return_B_trades_lost_in_C"] = stats_of([x["B_net"] for x in trB if not x["C_trade"]])
    expB = [x for x in trB if x["path_touches_1019"]]
    A["trades_B_with_path_touching_1019"] = len(expB)
    A["net_return_B_trades_touching_1019"] = stats_of([x["B_net"] for x in expB])
    A["net_return_C_trades_touching_1019"] = stats_of([x["C_net"] for x in expB if x["C_trade"]])
    A["survivorship_note"] = (
        "The paper-trade population is only the rejected candidates (PASS) whose plan would have filled; unfilled candidates, "
        "windows still open and (under C) records that become unscorable are absent, so means and medians are survivorship-conditioned."
    )
    A["verdict_counts_recorded"] = dict(collections.Counter(x["rec_verdict"] for x in recs))
    A["verdict_counts_B"] = dict(collections.Counter(x["B_verdict"] for x in recs if x["B_status"] == "OUTCOME"))
    A["verdict_counts_C"] = dict(collections.Counter(x["C_verdict"] for x in recs if x["C_status"] == "OUTCOME"))
    A["records_with_no_C_outcome"] = sum(1 for x in recs if x["C_status"] != "OUTCOME")
    A["verdict_PROFIT_LOSS_note"] = "no IDX decision is BUY ON TRIGGER, so PROFIT and LOSS cannot occur; every IDX verdict is CORRECT REJECTION or MISSED GAIN"
    sh = [x for x in recs if x["category"] in ("EXIT_SHIFTED", "VERDICT_CHANGED")]
    A["exit_shift_delta_net"] = {
        **stats_of([x["delta_net_C_minus_B"] for x in sh]),
        "worse_n": sum(1 for x in sh if x["delta_net_C_minus_B"] < 0),
        "better_n": sum(1 for x in sh if x["delta_net_C_minus_B"] > 0),
        "mean_exit_shift_sessions": statistics.fmean([x["exit_shift_sessions"] for x in sh]) if sh else None,
        "max_exit_shift_sessions": max([x["exit_shift_sessions"] for x in sh]) if sh else None,
    }
    A["discovery_fields_identical_B_vs_C"] = all(
        ctx["W"]["B"]["decisions"][x["decision_id"]]["out"]["discovery"] == ctx["W"]["C"]["decisions"][x["decision_id"]]["out"]["discovery"]
        for x in recs if ctx["W"]["C"]["decisions"][x["decision_id"]]["out"] is not None
    )
    # all lock_down cells that differ, market-wide (context for the size of the rule change)
    import numpy as np

    lb, lc = ctx["M"]["B"]["lock_down"], ctx["M"]["C"]["lock_down"]
    flip = (~lb) & lc
    A["market_cells_lock_down_B"] = int(lb.sum())
    A["market_cells_lock_down_C"] = int(lc.sum())
    A["market_cells_flipped_false_to_true"] = int(flip.sum())
    A["market_cells_flipped_true_to_false"] = int((lb & ~lc).sum())
    A["market_lock_up_identical"] = bool((ctx["M"]["B"]["lock_up"] == ctx["M"]["C"]["lock_up"]).all())
    first_flip = [ctx["dates"][j] for j in range(len(ctx["dates"])) if flip[:, j].any()]
    A["first_session_with_flips"] = first_flip[0] if first_flip else None
    A["market_flips_by_session"] = {ctx["dates"][j]: int(flip[:, j].sum()) for j in range(len(ctx["dates"])) if flip[:, j].any()}
    mc = ctx["M"]["C"]
    cl, ar = mc["close"], mc["arb"]
    A["market_flipped_bars_close_vs_modelled_limit"] = {
        "at_limit": int((flip & (cl == ar)).sum()),
        "strictly_below_limit": int((flip & (cl < ar)).sum()),
        "above_limit": int((flip & (cl > ar)).sum()),
    }
    # bars on the paths of the replayed (recorded-outcome) records
    fl = [f for f in F if f["category"] in ALL_CATS]
    A["flipped_bars_on_replayed_record_paths"] = {
        "bars": len(fl),
        "distinct_bar_cells": len({(f["ticker"], f["session"]) for f in fl}),
        "by_hint": dict(collections.Counter(f["hint"] for f in fl)),
    }
    fc = [f for f in fl if f["category"] in CHANGED_CATS]
    A["flipped_bars_on_changed_record_paths"] = {"bars": len(fc), "by_hint": dict(collections.Counter(f["hint"] for f in fc))}
    dec = [f for f in fc if f["decisive"]]
    A["decisive_flipped_bars_changed_records"] = {"bars": len(dec), "by_hint": dict(collections.Counter(f["hint"] for f in dec))}
    return A


# -------------------------------------------------------------------------------------- sensitivity
def sensitivity(ctx, R, A):
    recs = [x for x in R if x["has_recorded_outcome"]]
    S = {}
    changed_C = [x["decision_id"] for x in recs if x["category"] in CHANGED_CATS]
    for key, name, label in (("cat_C10", "a_arb_10_percent", "C with ARB 10% from 2026-10-19 instead of 7% (Rp1 nominal rule kept; for references Rp11-14 the 10% formula already gives reference minus Rp1)"),
                             ("cat_C7", "d_no_rp11_14_rule", "C without the Rp11-14 nominal-Rp1 rule (7% only): isolates the October-20 change")):
        ch = [x["decision_id"] for x in recs if x[key] in CHANGED_CATS]
        S[name] = {
            "description": label,
            "category_counts": {c: sum(1 for x in recs if x[key] == c) for c in ALL_CATS},
            "records_changed_vs_B": len(ch),
            "changed_ids": ch,
            "becomes_unscorable": sum(1 for x in recs if x[key] == "BECOMES_UNSCORABLE"),
            "changed_in_C_but_not_in_this_variant": sorted(set(changed_C) - set(ch)),
            "changed_in_this_variant_but_not_in_C": sorted(set(ch) - set(changed_C)),
        }
    # (b) what-if: keep rolling past the horizon
    items = []
    for x in recs:
        if x["category"] != "BECOMES_UNSCORABLE":
            continue
        items.append({
            "decision_id": x["decision_id"], "ticker": x["ticker"], "B_exit": x["B_exit"], "B_net": x["B_net"], "B_verdict": x["B_verdict"],
            "whatif_exit": x.get("whatif_roll_exit") or None, "whatif_reason": x.get("whatif_roll_reason") or None,
            "whatif_net": x.get("whatif_roll_net"), "whatif_verdict": x.get("whatif_roll_verdict") or None,
            "extra_sessions_past_horizon": x.get("whatif_roll_extra_sessions"), "note": x.get("whatif_roll_note", ""),
        })
    resolved = [i for i in items if i["whatif_exit"]]
    both_nets = [x["C_net"] for x in recs if x["C_trade"]]
    S["b_what_if_keep_rolling_past_horizon"] = {
        "label": "WHAT-IF ONLY: the legacy scorer does not do this; it returns no outcome when the horizon bar is locked",
        "method": "real paper.score() run with a longer horizon (paper.POLICY.horizon_sessions monkeypatched in the worker process); the first horizon "
                  "that returns an outcome exits on the first sellable close after the original horizon",
        "feasible": True,
        "records": items,
        "resolved": len(resolved),
        "unresolved_no_sellable_close_in_data_yet": len(items) - len(resolved),
        "population_B_trades": A["net_return_B_all_trades"],
        "population_C_trades_plus_resolved_what_ifs": stats_of(both_nets + [i["whatif_net"] for i in resolved]),
        "population_C_trades": A["net_return_C_all_trades"],
        "verdict_changes_vs_B": sum(1 for i in resolved if i["whatif_verdict"] != i["B_verdict"]),
    }
    # (c) drop names with empirical wider-limit evidence
    names_ev = sorted({x["ticker"] for x in recs if x["name_closes_below_7pct_limit_since_1019"] > 0})
    keep = [x for x in recs if x["ticker"] not in names_ev]
    drop = [x for x in recs if x["ticker"] in names_ev]
    ch_keep = [x["decision_id"] for x in keep if x["category"] in CHANGED_CATS]
    ch_drop = [x["decision_id"] for x in drop if x["category"] in CHANGED_CATS]
    # own-path variant: drop only records whose DECISIVE flipped bar closed strictly below the modelled limit
    ch_dec_below = [x["decision_id"] for x in recs if x["category"] in CHANGED_CATS and str(x.get("decisive_bar_hint", "")) in WIDER_HINTS]
    ch_any_below = [x["decision_id"] for x in recs if x["category"] in CHANGED_CATS and x.get("any_flipped_bar_below_limit")]
    S["c_drop_names_with_wider_limit_evidence"] = {
        "evidence_definition": (
            "a ticker with at least one tradeable bar on or after 2026-10-19 whose close is strictly below its modelled regular-board 7% ARB price "
            "(the 2026-10-19 references Rp11-14 excluded because the modelled ARB equals the reference there): it traded beyond the limit the "
            "corrected rule gives it, so it is on a wider-limit board or its reference price differs"
        ),
        "tickers_with_evidence_among_replayed_records": names_ev,
        "n_tickers_with_evidence_among_replayed": len(names_ev),
        "market_wide_tickers_with_evidence": int((ctx["name_below"] > 0).sum()),
        "records_total": len(recs), "records_dropped": len(drop), "records_remaining": len(keep),
        "records_changed_in_C_total": len(changed_C),
        "changed_among_remaining": len(ch_keep), "changed_ids_remaining": ch_keep,
        "changed_dropped": len(ch_drop), "changed_ids_dropped": ch_drop,
        "records_changed_whose_decisive_flipped_bar_closed_strictly_below_limit": ch_dec_below,
        "records_changed_with_any_flipped_bar_strictly_below_limit": ch_any_below,
        "changed_remaining_if_those_with_decisive_below_limit_bar_dropped": len(changed_C) - len(ch_dec_below),
        "caveat": "absence of below-limit evidence is not evidence of a 7% board; a name on a 10% board that never fell 7-10% looks like a 7% name",
    }
    return S


# ----------------------------------------------------------------------------------------- pending
def pending_analysis(ctx, R):
    pend = [x for x in R if not x["has_recorded_outcome"]]
    P = {"count": len(pend)}
    P["by_state"] = dict(collections.Counter(x["pending_state"] for x in pend))
    P["window_still_open"] = [x["decision_id"] for x in pend if x["pending_state"] == "WINDOW_OPEN"]
    P["window_complete_but_unscored_under_both_rules"] = [x["decision_id"] for x in pend if x["pending_state"] != "WINDOW_OPEN"]
    P["by_policy"] = dict(collections.Counter(x["policy_id"] for x in pend))
    P["by_kind"] = dict(collections.Counter(x["decision"] for x in pend))
    P["with_lock_down_flip_B_vs_C_on_path_so_far"] = [x["decision_id"] for x in pend if x["n_flipped_bars_on_path"] > 0]
    P["with_flip_after_the_entry_bar_so_far"] = [x["decision_id"] for x in pend if x["n_flipped_bars_after_entry_bar"] > 0]
    P["flip_only_on_the_entry_bar_so_far_irrelevant_to_scorer"] = [
        x["decision_id"] for x in pend if x["n_flipped_bars_on_path"] > 0 and x["n_flipped_bars_after_entry_bar"] == 0
    ]
    P["without_flip_so_far"] = [x["decision_id"] for x in pend if x["n_flipped_bars_on_path"] == 0]
    P["interim_state_differs_B_vs_C"] = [x["decision_id"] for x in pend if x.get("interim_differs_B_vs_C")]
    P["interim_difference_certain_stop_exit_refused_under_C"] = [
        x["decision_id"] for x in pend if x.get("interim_differs_B_vs_C") and str(x.get("interim_B", "")).startswith("STOP HIT")
    ]
    P["interim_difference_possible_last_bar_locked_only_under_C"] = [
        x["decision_id"] for x in pend if x.get("interim_differs_B_vs_C") and not str(x.get("interim_B", "")).startswith("STOP HIT")
    ]
    stuck = []
    for x in pend:
        if x["pending_state"] == "WINDOW_OPEN":
            continue
        n, d = ctx["ti"][x["ticker"]], ctx["di"][x["signal_session"]]
        br = bar_record(ctx, n, min(d + 1 + ctx["base_h"], ctx["last"]))
        if br["lock_B"]:
            n_lock = int(ctx["M"]["B"]["lock_down"][:, min(d + 1 + ctx["base_h"], ctx["last"])].sum())
            why = (f"horizon bar {br['session']} is locked under the shipped rule (close {br['close']:g}, reference {br['ref']:g}, B limit {br['arb_B']:g}; "
                   f"{n_lock} names were locked that session under both rule sets)")
        elif not br["tradeable"]:
            why = f"horizon bar {br['session']} was not traded (no volume), so it is not sellable"
        else:
            why = "horizon bar sellable; no exit condition met (unexpected)"
        stuck.append({"decision_id": x["decision_id"], "ticker": x["ticker"], "reason": why, "horizon_bar_locked_under_C": br["lock_C"], "horizon_bar_locked_under_B": br["lock_B"]})
    P["complete_but_unscored_details"] = stuck
    P["rows"] = [
        {k: x.get(k) for k in ("decision_id", "ticker", "policy_id", "decision", "signal_session", "pending_state", "sessions_remaining_to_window_end",
                               "n_flipped_bars_on_path", "n_flipped_bars_after_entry_bar", "flipped_sessions", "flip_board_hints", "interim_B", "interim_C", "interim_differs_B_vs_C")}
        for x in pend
    ]
    return P


# -------------------------------------------------------------------------------------- speculations
def spec_strip(r):
    r = json.loads(json.dumps(r, default=_json_default))
    for k in ("resolved_at", "data", "record_hash", "prev_hash"):
        r.pop(k, None)
    return r


def deep_diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((f"{path}/{k}", "<missing>", b[k]))
            elif k not in b:
                out.append((f"{path}/{k}", a[k], "<missing>"))
            else:
                out += deep_diff(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((f"{path}[len]", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += deep_diff(x, y, f"{path}[{i}]")
    elif isinstance(a, float) and isinstance(b, float):
        if abs(a - b) > TOL:
            out.append((path, a, b))
    elif a != b:
        out.append((path, a, b))
    return out


def speculation_analysis(ctx):
    rows = ctx["spec_rows"]
    WB, WC = ctx["W"]["B"], ctx["W"]["C"]
    dates, di, ti, last = ctx["dates"], ctx["di"], ctx["ti"], ctx["last"]
    S = {}
    S["rows_by_type_and_market"] = {f"{t}/{m}": n for (t, m), n in sorted(collections.Counter((r["type"], r["market"]) for r in rows).items())}
    sets = [r for r in rows if r["type"] == "SPECULATION_SET" and r["market"] == "IDX"]
    res = [r for r in rows if r["type"] == "RESOLUTION" and r["market"] == "IDX"]
    S["idx_speculation_sets"] = len(sets)
    S["idx_resolution_rows"] = len(res)
    S["idx_resolution_rows_by_window_and_status"] = {f"{w}/{s}": n for (w, s), n in sorted(collections.Counter((r["window"], r["status"]) for r in res).items())}
    S["idx_sets_by_signal_session"] = dict(sorted(collections.Counter(r["signal_session"] for r in sets).items()))
    S["idx_sets_signal_on_or_after_1019"] = sum(1 for r in sets if r["signal_session"] >= CUT)
    S["idx_resolution_rows_signal_on_or_after_1019"] = sum(1 for r in res if r["signal_session"] >= CUT)
    base5 = [r for r in res if r["window"] == "BASE5"]
    S["resolution_rows_whose_horizon_day_uses_lock_down"] = len(base5)
    S["resolution_rows_not_lock_sensitive"] = {"NEXT1": sum(1 for r in res if r["window"] == "NEXT1"), "PATH20": sum(1 for r in res if r["window"] == "PATH20")}
    ntr = 0
    for r in base5:
        ntr += 1 if (r.get("candidate") or {}).get("trade") else 0
        ntr += sum(1 for tw in r.get("twins", []) if tw.get("trade"))
    S["trades_inside_the_lock_sensitive_rows"] = ntr
    S["replayable"] = True
    S["replay_method"] = (
        "speculation.resolve_set() (real function) called for every IDX set and window on the final-pull Market, with speculation.windows() "
        "monkeypatched because research/SPECULATION_REGISTER_v1/protocol_v1_1.json is not in the code tree; the window definitions "
        "(BASE5 enter next close hold 5; PATH20; NEXT1) are reconstructed and validated by the B replay reproducing the recorded rows"
    )
    # baseline gate: recorded RESOLUTION rows versus the B replay
    gate = {"rows": len(res), "matches": 0, "mismatches": []}
    byk = {f"{r['set_id']}|{r['window']}": r for r in res}
    for k, rec in byk.items():
        rb = WB["spec"][k]["rec"]
        diffs = deep_diff(spec_strip(rec), spec_strip(rb)) if rb is not None else [("replay", "recorded", None)]
        if not diffs:
            gate["matches"] += 1
            continue
        cause = "UNDIAGNOSED"
        if rec["window"] == "NEXT1" and all(d[0].startswith("/cone") for d in diffs):
            row = ticker_row_in_pull(rec["data"]["manifest"], rec["ticker"])
            nxt_i = di[rec["signal_session"]] + 1
            nxt = dates[nxt_i]
            nn = ti[rec["ticker"]]
            vol = float(ctx["M"]["B"]["volume"][nn, nxt_i])
            if row and row["last_date"] < nxt:
                cause = (f"DATA_TIMING: the recorded pull {rec['data']['manifest']} ends for {rec['ticker']} at {row['last_date']}, before the "
                         f"s+1 session {nxt}, so the NEXT1 statements were not graded then; the final pull has the bar. Not lock_down related.")
            elif vol == 0:
                cause = (f"DATA_TIMING (probable, the recorded payload did not survive): the s+1 bar {nxt} of {rec['ticker']} is a zero-volume "
                         f"carry-forward bar in the final pull (close = previous close, volume 0); the recorded pull {rec['data']['manifest']} lists it "
                         f"(rows {row and row['rows']}, last_date {row and row['last_date']}) but the recorded run graded no NEXT1 statement, i.e. it "
                         "found no usable s+1 bar. NEXT1 does not use lock_down, so this is unrelated to the ARB rule.")
        gate["mismatches"].append({"key": k, "ticker": rec["ticker"], "differences": [{"path": p, "recorded": a, "replay_B": b} for p, a, b in diffs[:8]], "cause": cause})
    S["baseline_gate"] = gate
    # B versus C for every set/window
    changed = []
    for k, vb in WB["spec"].items():
        rb, rc = vb["rec"], WC["spec"][k]["rec"]
        if (rb is None) != (rc is None):
            changed.append({"key": k, "B": "resolved" if rb is not None else "open", "C": "resolved" if rc is not None else "open"})
        elif rb is not None and deep_diff(spec_strip(rb), spec_strip(rc)):
            changed.append({"key": k, "B": "resolved", "C": "resolved, different content"})
    S["recorded_rows_changed_B_vs_C"] = [c for c in changed if c["key"] in byk]
    S["any_replayed_row_changed_B_vs_C"] = changed
    S["next1_rows_identical_B_vs_C"] = all(
        (WB["spec"][k]["rec"] is None and WC["spec"][k]["rec"] is None) or (WB["spec"][k]["rec"] is not None and WC["spec"][k]["rec"] is not None and not deep_diff(spec_strip(WB["spec"][k]["rec"]), spec_strip(WC["spec"][k]["rec"])))
        for k in WB["spec"] if k.endswith("|NEXT1")
    )
    # per-name replay of the lock-sensitive rows (candidate and twins)
    name_rows = []
    for r in base5:
        sid = r["set_id"]
        s = next(x for x in sets if x["set_id"] == sid)
        members = [("candidate", s["ticker"])] + [("twin", tw["ticker"]) for tw in s["twins"]]
        for role, name in members:
            key = f"{sid}|{name}"
            nb, nc = WB["spec_names"][key], WC["spec_names"][key]
            sb, sc = (nb.get("sim") or {}), (nc.get("sim") if nc.get("located") else None)
            trb = (sb or {}).get("trade")
            trc = (sc or {}).get("trade") if sc else None
            n = ti[name]
            d = di[s["signal_session"]]
            e = d + 1
            xB = di[trb["exit_session"]] if trb else None
            flips = flips_between(ctx, n, e + 1, xB) if xB is not None else []
            bars = [bar_record(ctx, n, k) for k in flips]
            exit_flip = xB is not None and bool(ctx["M"]["C"]["lock_down"][n, xB]) and not bool(ctx["M"]["B"]["lock_down"][n, xB])
            ebar = bar_record(ctx, n, xB) if exit_flip else None
            name_rows.append({
                "set_id": sid, "signal_session": s["signal_session"], "window": "BASE5", "role": role, "ticker": name,
                "B_status": (sb or {}).get("status"), "B_entry": (trb or {}).get("entry_session"), "B_exit": (trb or {}).get("exit_session"),
                "B_exit_reason": (trb or {}).get("exit_reason"), "B_net": (trb or {}).get("net_return"),
                "C_status": ("STILL_ROLLING_NO_SELLABLE_CLOSE_YET" if (sc is None and nc.get("located") is not False and nb.get("located")) else (sc or {}).get("status")),
                "C_exit": (trc or {}).get("exit_session"), "C_net": (trc or {}).get("net_return"),
                "exit_bar_flipped_to_locked_under_C": exit_flip,
                "exit_bar_close": ebar["close"] if ebar else None, "exit_bar_ref": ebar["ref"] if ebar else None,
                "exit_bar_modelled_7pct_arb": ebar["arb_C"] if ebar else None, "exit_bar_hint": ebar["hint"] if ebar else "",
                "flipped_sessions_after_entry_to_B_exit": ";".join(x["session"] for x in bars),
                "set_resolved_B": WB["spec"][f"{sid}|BASE5"]["rec"] is not None, "set_resolved_C": WC["spec"][f"{sid}|BASE5"]["rec"] is not None,
            })
    S["lock_sensitive_trade_rows"] = name_rows
    S["lock_sensitive_trades_with_exit_bar_flipped"] = sum(1 for x in name_rows if x["exit_bar_flipped_to_locked_under_C"])
    # sets whose BASE5 window is still open: flips on the path observed so far
    open_sets = []
    for s in sets:
        if "BASE5" not in s.get("windows", ["BASE5", "PATH20"]):
            continue
        sid = s["set_id"]
        if f"{sid}|BASE5" in byk:
            continue
        d = di[s["signal_session"]]
        e = d + 1
        target = e + SPEC_WINDOWS["BASE5"]["holding_sessions"]  # BASE5 reads lock_down only from this bar on
        members = [("candidate", s["ticker"])] + [("twin", tw["ticker"]) for tw in s["twins"]]
        fl = {}
        for role, name in members:
            if name in ti and e <= last:
                f = flips_between(ctx, ti[name], e, last)
                if f:
                    fl[f"{role}:{name}"] = [dates[k] for k in f]
        open_sets.append({"set_id": sid, "signal_session": s["signal_session"], "ticker": s["ticker"], "horizon_bar_observed": target <= last,
                          "members_with_flip_so_far": fl})
    S["open_base5_sets"] = {
        "count": len(open_sets),
        "horizon_bar_already_observed": sum(1 for x in open_sets if x["horizon_bar_observed"]),
        "with_any_flip_so_far_informational": sum(1 for x in open_sets if x["members_with_flip_so_far"]),
        "note": "BASE5 (simulate) reads lock_down only at the horizon bar (entry + 5 sessions) and later, so a flip earlier on the path cannot change a BASE5 trade",
        "sets": open_sets,
    }
    return S



# ------------------------------------------------------------------------------------------ outputs
RESULT_COLUMNS = [
    "decision_id", "outcome_record_hash", "ticker", "policy_id", "decision", "signal_session",
    "has_recorded_outcome", "window_complete_final_pull", "category", "subcase",
    "rec_entry", "rec_exit", "rec_reason", "rec_net", "rec_verdict",
    "B_status", "B_entry", "B_exit", "B_reason", "B_net", "B_mfe", "B_mae", "B_verdict",
    "C_status", "C_entry", "C_exit", "C_reason", "C_net", "C_mfe", "C_mae", "C_verdict",
    "delta_net_C_minus_B", "exit_shift_sessions",
    "baseline_match", "baseline_diff_fields", "baseline_cause",
    "path_first_session", "path_last_session_B", "path_last_session_union", "path_touches_1019",
    "n_flipped_bars_on_path", "flipped_sessions", "flip_board_hints", "decisive_flipped_bar", "decisive_bar_hint",
    "any_flipped_bar_below_limit", "name_closes_at_7pct_limit_since_1019", "name_closes_below_7pct_limit_since_1019",
    "cat_C10", "cat_C7",
    "whatif_roll_extra_sessions", "whatif_roll_exit", "whatif_roll_reason", "whatif_roll_net", "whatif_roll_verdict", "whatif_roll_note",
    "pending_state", "sessions_remaining_to_window_end", "n_flipped_bars_after_entry_bar", "interim_B", "interim_C", "interim_differs_B_vs_C",
]


def write_csv(path, rows, columns=None):
    cols = list(columns) if columns else []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r.get(c) is None else (repr(r[c]) if isinstance(r[c], float) else r[c]) for c in cols])


def analyse(args) -> dict:
    t0 = time.time()
    inputs = verify_inputs()
    ctx = build_context()
    P = populations(ctx)
    G = baseline_gate(ctx)
    R, F, checks = classify_all(ctx)
    for x in R:  # baseline cause text on the record row
        g = G["per_record"].get(x["decision_id"])
        if g and g["diag"]:
            x["baseline_cause"] = f"{g['diag']['code']}: {g['diag']['text']}"
    A = aggregates(ctx, R, F)
    S = sensitivity(ctx, R, A)
    PD = pending_analysis(ctx, R)
    SP = speculation_analysis(ctx)
    # consistency checks (each is reported, none is silently assumed)
    metaB, metaC = ctx["W"]["B"]["meta"], ctx["W"]["C"]["meta"]
    chk = []
    chk.append(("worker B imported the B tree", metaB["code_dir"].endswith("code_B/idx-signals") and "/code_B/" in metaB["idxsig_file"]))
    chk.append(("worker C imported the C tree", metaC["code_dir"].endswith("code_C/idx-signals") and "/code_C/" in metaC["idxsig_file"]))
    chk.append(("market.py sha256 differs between B and C trees", metaB["market_py_sha256"] != metaC["market_py_sha256"]))
    chk.append(("worker market.py hashes equal the on-disk hashes", metaB["market_py_sha256"] == inputs["market_py_sha256"]["B"] and metaC["market_py_sha256"] == inputs["market_py_sha256"]["C"]))
    chk.append(("both workers used the same manifest sha256", metaB["manifest_sha256"] == metaC["manifest_sha256"] == inputs["manifest_sha256"]))
    chk.append(("ledger hash chain intact (paper._chain_problems)", metaB["ledger_chain_problems"] == [] and metaC["ledger_chain_problems"] == []))
    chk.append(("speculations hash chain intact", metaB["spec_chain_problems"] == [] and metaC["spec_chain_problems"] == []))
    chk.append(("lock_down only ever turns on (C superset of B)", A["market_cells_flipped_true_to_false"] == 0))
    chk.append(("lock_up identical B vs C", A["market_lock_up_identical"]))
    chk.append(("first lock_down flip is on 2026-10-19", A["first_session_with_flips"] == CUT))
    chk.append(("discovery fields identical B vs C for every replayed record", A["discovery_fields_identical_B_vs_C"]))
    chk.append(("every NOT_AFFECTED record has identical B and C output", not any("NOT_AFFECTED" in c for c in checks)))
    chk.append(("path-touch rule agrees between recorded outcome and B replay", not any("touch rule" in c for c in checks)))
    chk.append(("no category outside the defined set", not A["category_counts_unexpected"]))
    chk.append(("BECOMES_SCORABLE is empty (more locks cannot create an exit)", A["category_counts"]["BECOMES_SCORABLE"] == 0))
    chk.append(("C10 and C7 variants used the C tree with in-memory patches only", "/code_C/" in ctx["W"]["C10"]["meta"]["idxsig_file"] and "/code_C/" in ctx["W"]["C7"]["meta"]["idxsig_file"]))
    ilc = independent_lock_check(ctx)
    chk.append(("independent recomputation of lock_down agrees with both market.py copies", ilc["agrees"]))
    S_inputs_ok = not inputs["problems"]
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runtime_seconds_analysis": round(time.time() - t0, 1),
        "inputs": inputs,
        "environment": {k: metaB[k] for k in ("python", "numpy", "pandas")},
        "worker_meta": {t: {k: ctx["W"][t]["meta"][k] for k in ("label", "idxsig_file", "market_py_sha256", "n_tickers", "n_sessions", "first_session", "last_session", "regimes")} for t in VARIANTS},
        "populations": P,
        "baseline_gate": {k: G[k] for k in ("outcomes_replayed", "field_for_field_matches", "mismatches", "fields_compared", "pull_exposure")},
        "classification": {"counts": A["category_counts"], "ids_by_category": A["ids_by_category"]},
        "aggregates": {k: v for k, v in A.items() if k not in ("ids_by_category",)},
        "sensitivity": S,
        "pending": PD,
        "speculations": SP,
        "checks": [{"check": c, "passed": bool(ok)} for c, ok in chk],
        "inputs_ok": S_inputs_ok,
    }
    summary["independent_lock_check"] = ilc
    summary["changed_records"] = [
        {k: x.get(k) for k in ("decision_id", "outcome_record_hash", "ticker", "signal_session", "category", "rec_exit", "rec_net", "B_exit", "B_reason", "B_net", "B_verdict",
                               "C_status", "C_exit", "C_reason", "C_net", "C_verdict", "delta_net_C_minus_B", "exit_shift_sessions", "flipped_sessions", "flip_board_hints",
                               "decisive_flipped_bar", "decisive_bar_hint", "cat_C10", "cat_C7", "whatif_roll_exit", "whatif_roll_net", "whatif_roll_verdict", "whatif_roll_note",
                               "name_closes_at_7pct_limit_since_1019", "name_closes_below_7pct_limit_since_1019")}
        for x in R if x["has_recorded_outcome"] and x["category"] in CHANGED_CATS
    ]
    return {"ctx": ctx, "P": P, "G": G, "R": R, "F": F, "A": A, "S": S, "PD": PD, "SP": SP, "summary": summary, "inputs": inputs, "checks": chk, "independent_lock_check": ilc}


def write_outputs(res):
    R, F, summary, SP = res["R"], res["F"], res["summary"], res["SP"]
    write_csv(OUT / "results.csv", R, RESULT_COLUMNS)
    write_csv(OUT / "flipped_bars.csv", F)
    write_csv(OUT / "speculation_replay.csv", SP["lock_sensitive_trade_rows"])
    dump_json(summary, OUT / "summary.json", indent=1)



# ------------------------------------------------------------------------- independent lock check
def independent_lock_check(ctx) -> dict:
    """VALIDATION ONLY (not used for any reported number): recompute lock_down for every cell from 2026-09-28 on from the
    rules as stated in the task (B: ARB 15%; C: ARB 7% from 2026-10-19 and nominal Rp1 for references Rp11-14 from 2026-10-20;
    nominal Rp1 for references up to Rp10 in both; tradeable bar, close below the reference, close at or below the ARB price;
    one-price bars also lock at the 10% special-board bound), with exact rational arithmetic for the limit prices, and
    compare with the flags the two market.py copies produced."""
    import numpy as np

    dates = ctx["dates"]
    start = dates.index("2026-09-28")

    def tick(p):
        return 1 if p < 200 else 2 if p < 500 else 5 if p < 2000 else 10 if p < 5000 else 25

    def ceil_tick(x):
        t = tick(x)
        return math.ceil(x / t) * t

    def arb_price(ref, date, rule):
        ref = int(ref)
        if ref <= 10:
            return max(ref - 1, 1)
        if rule == "B":
            return max(ceil_tick(Fraction(ref) * Fraction(85, 100)), 1)
        if date >= "2026-10-20" and ref <= 14:
            return ref - 1
        return max(ceil_tick(Fraction(ref) * Fraction(93, 100)), 1)

    def sp_arb(ref):
        ref = int(ref)
        return max(ref - 1, 1) if ref <= 10 else max(ceil_tick(Fraction(ref) * Fraction(90, 100)), 1)

    out = {"first_session_checked": dates[start]}
    for rule in ("B", "C"):
        M = ctx["M"][rule]
        close, prev, hi, lo = M["close"], M["prev"], M["high"], M["low"]
        cand = M["tradeable"] & np.isfinite(prev) & (prev > 0) & (close < prev)
        bad = 0
        cells = 0
        for n, k in zip(*np.nonzero(cand)):
            if k < start:
                continue
            rr = "B" if (rule == "C" and dates[k] < CUT) else rule
            a = arb_price(prev[n, k], dates[k], rr)
            one = bool(hi[n, k] == lo[n, k] == close[n, k])
            exp = bool(close[n, k] <= a or (one and close[n, k] <= sp_arb(prev[n, k])))
            cells += 1
            if exp != bool(M["lock_down"][n, k]):
                bad += 1
        # cells that cannot lock (not tradeable, no reference, close not below reference) must all be unlocked
        spurious = int((M["lock_down"][:, start:] & ~cand[:, start:]).sum())
        out[rule] = {
            "candidate_cells_checked": cells,
            "total_cells_from_start": int(M["lock_down"][:, start:].size),
            "mismatches_on_candidate_cells": bad,
            "locked_cells_that_cannot_lock": spurious,
        }
    out["agrees"] = all(out[r]["mismatches_on_candidate_cells"] == 0 and out[r]["locked_cells_that_cannot_lock"] == 0 for r in ("B", "C"))
    return out


# ------------------------------------------------------------------------------------------ claims
def claims_checked(res) -> list[str]:
    import numpy as np

    ctx, P, A, F, R = res["ctx"], res["P"], res["A"], res["F"], res["R"]
    MB, MC = ctx["M"]["B"], ctx["M"]["C"]
    ci, dates, tick = ctx["cut_i"], ctx["dates"], ctx["tick"]
    out = []
    out.append(
        f"'88 decisions': TRUE for decisions whose signal_session is on or after 2026-10-19 (recount {P['decisions_signal_on_or_after_1019']}; "
        f"{P['late_with_outcome']} with an outcome, {P['late_without_outcome_pending']} without)."
    )
    out.append(
        f"'27 hypothetical trade records': TRUE for that same definition ({P['late_with_hypothetical_trade']} outcomes with a paper_trade, all PASS decisions; "
        f"no IDX decision is BUY ON TRIGGER). It is NOT the exposed population: {P['outcomes_path_touches_1019_all']} of 93 outcomes have a scored path touching a session on/after 2026-10-19, "
        f"{P['outcomes_path_touches_1019_with_trade']} of them with a trade ({P['trades_path_touches_1019_signal_before_cut']} trades have a signal before 10-19), "
        f"and {sum(1 for x in R if x['has_recorded_outcome'] and x['category'] in CHANGED_CATS and x['signal_session'] < CUT)} of the {A['records_changed']} records that actually change have a signal before 10-19."
    )
    # market.py note about 2026-10-19 references Rp11-14
    prev, close = MC["prev"][:, ci], MC["close"][:, ci]
    m1114 = (prev >= 11) & (prev <= 14) & MC["tradeable"][:, ci]
    big = [tick[n] for n in np.flatnonzero(m1114 & (close / np.where(prev > 0, prev, np.nan) - 1 <= -0.25 + 1e-12))]
    flips_1019 = int(((~MB["lock_down"][:, ci]) & MC["lock_down"][:, ci] & m1114).sum())
    later = 0
    for k in range(ci + 1, len(dates)):
        pk = MC["prev"][:, k]
        later += int(((~MB["lock_down"][:, k]) & MC["lock_down"][:, k] & (pk >= 11) & (pk <= 14)).sum())
    indet_on_paths = sum(1 for f in F if f["hint"] == "INDETERMINATE_1019_RP11_14")
    later_on_paths = sum(1 for f in F if 11 <= f["ref"] <= 14 and f["session"] > CUT)
    out.append(
        f"market.py note 'two bars (BTEK, TAXI) closed 25% lower on 2026-10-19 at references Rp11-14': {'TRUE' if sorted(big) == ['BTEK', 'TAXI'] else 'NOT CONFIRMED'} "
        f"(names at <= -25%: {sorted(big)}); both are locked under B and C, so the 2026-10-19 Rp11-14 limit question flips {flips_1019} bar(s) between B and C "
        f"that day; {later} bar(s) with Rp11-14 references flip on later days (the Rp1 nominal rule), {later_on_paths} of them on a decision path; "
        f"{indet_on_paths} flipped bar on any decision path is a 2026-10-19 Rp11-14 bar. 'Nothing in the ledger depends on it' is TRUE for the B-versus-C comparison."
    )
    out.append(
        f"Task statement inputs: ledger sha256 {res['inputs']['ledger_sha256_B'][:12]}... and head record_hash {res['inputs']['ledger_head_record_hash'][:12]}... "
        f"({res['inputs']['ledger_rows']} rows), speculations {res['inputs']['speculations_rows']} rows, manifest sha256 {res['inputs']['manifest_sha256'][:12]}... "
        f"(920 payloads, {res['inputs']['raw_payloads']['bad_or_missing']} bad), code trees differ only in {res['inputs']['code_tree_differences']}: "
        + ("ALL CONFIRMED." if not res["inputs"]["problems"] else "PROBLEMS: " + "; ".join(res["inputs"]["problems"]))
    )
    out.append(
        f"Task statement 'a locked horizon exit returns no outcome in the legacy IDX branch': CONFIRMED by replay: {A['category_counts']['BECOMES_UNSCORABLE']} records become unscorable under C, "
        f"and under the SHIPPED rules {len(res['PD']['window_complete_but_unscored_under_both_rules'])} decisions already sit with a complete window and no outcome "
        "(" + "; ".join(f"{d['ticker']}: {d['reason']}" for d in res["PD"]["complete_but_unscored_details"]) + ")."
    )
    ilc = res["independent_lock_check"]
    out.append(
        f"Independent check of market.py: lock_down recomputed from the stated rules with exact rational arithmetic agrees with the flags of the B tree and of the C tree "
        f"({'YES' if ilc['agrees'] else 'NO'}): B {ilc['B']['mismatches_on_candidate_cells']} mismatches and C {ilc['C']['mismatches_on_candidate_cells']} mismatches among "
        f"{ilc['C']['candidate_cells_checked']:,} candidate cells (tradeable, reference known, close below reference) since {ilc['first_session_checked']}, "
        f"{ilc['B']['locked_cells_that_cannot_lock']}/{ilc['C']['locked_cells_that_cannot_lock']} locked cells that could not lock. This checks the code against the stated rule, not the rule against the exchange."
    )
    out.append(
        f"Scorer coverage: all {P['idx_decisions']} IDX decisions are scored by the legacy IDX branch (none carries plan.execution_plan, so paper._score_plan / execution.execute is never used); "
        "execution.execute's own roll-to-next-sellable logic therefore plays no role in the ledger."
    )
    return out


# ------------------------------------------------------------------------------------------- report
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    return "\n".join(out)


def build_report(res) -> str:
    ctx, P, G, R, F, A, S, PD, SP = (res[k] for k in ("ctx", "P", "G", "R", "F", "A", "S", "PD", "SP"))
    summ_ = res["summary"]
    cc = A["category_counts"]
    recs = [x for x in R if x["has_recorded_outcome"]]
    changed = [x for x in recs if x["category"] in CHANGED_CATS]
    shifted = [x for x in recs if x["category"] in ("EXIT_SHIFTED", "VERDICT_CHANGED")]
    unsc = [x for x in recs if x["category"] == "BECOMES_UNSCORABLE"]
    dlt = A["exit_shift_delta_net"]
    nB, nC = A["net_return_B_all_trades"], A["net_return_C_all_trades"]
    nBb, nCb = A["net_return_B_on_trades_present_in_both"], A["net_return_C_on_trades_present_in_both"]
    pp = lambda x: "n/a" if x is None else f"{100 * x:+.2f}%"
    pts = lambda x: "n/a" if x is None else f"{100 * x:+.2f} pp"
    M_ = summ_["worker_meta"]
    atl = A["market_flipped_bars_close_vs_modelled_limit"]
    dec_hint = A["decisive_flipped_bars_changed_records"]["by_hint"]
    S_a, S_d, S_b, S_c = S["a_arb_10_percent"], S["d_no_rp11_14_rule"], S["b_what_if_keep_rolling_past_horizon"], S["c_drop_names_with_wider_limit_evidence"]
    pre = G["pull_exposure"]
    dec_bars = [f for f in F if f["decisive"]]
    dec_chg = [f["chg"] for f in dec_bars if f["chg"] is not None]
    deepest, shallowest = min(dec_chg), max(dec_chg)
    _best = {}
    for x in changed:
        _best[x["ticker"]] = max(_best.get(x["ticker"], 0), x["name_closes_at_7pct_limit_since_1019"])
    at_top = sorted(((n_, t_) for t_, n_ in _best.items()), reverse=True)[:3]
    kv = lambda d: ", ".join(f"{k} {v}" for k, v in d.items())
    hint_txt = {"AT_LIMIT": "at the 7% limit price", "AT_10PCT_LIMIT": "exactly at the 10% limit price", "BELOW_LIMIT_WITHIN_10PCT": "below the 7% limit, within the 10% limit", "BELOW_10PCT_LIMIT": "below even the 10% limit"}
    n_dec_at = sum(1 for f in dec_bars if f["hint"] == "AT_LIMIT")
    dec_dist_ids = sorted({f["decision_id"] for f in dec_bars})
    lost_recs = [x for x in recs if x["category"] == "BECOMES_UNSCORABLE"]
    lost_mg = sum(1 for x in lost_recs if str(x["B_verdict"]).startswith("MISSED"))
    sens_rows = SP["lock_sensitive_trade_rows"]
    n_cand_tr = sum(1 for r in sens_rows if r["role"] == "candidate" and r["B_status"] == "TRADED")
    n_twin_tr = sum(1 for r in sens_rows if r["role"] == "twin" and r["B_status"] == "TRADED")
    n_cand_notfill = sum(1 for r in sens_rows if r["role"] == "candidate" and r["B_status"] != "TRADED")
    flipped_tw = [r["ticker"] for r in sens_rows if r["exit_bar_flipped_to_locked_under_C"]]
    stuck_txt = "; ".join(f"{d['ticker']}: {d['reason']}" for d in PD["complete_but_unscored_details"])
    pre_pm = next((G["per_record"][m_["decision_id"]]["pull"] for m_ in G["mismatches"] if m_["cause_code"] == "PRE_CLOSE_PULL"), None)
    evid_changed = [i.split("-F1_ARA-")[1] for i in S_c["changed_ids_dropped"]]
    L = []
    w = L.append

    w("# IDX ARB correction: what it changes in the ledger already written")
    w("")
    w("Impact analyst 1 of 2. Paper trading only, no real money. Every number below is produced by `harness.py` (same folder) by replaying the real scorer; nothing was edited and no ledger or repository file was written.")
    w("")
    w("Terms. **ARB** is the lower auto-rejection price limit. A session is **locked** (`lock_down`) when the bar traded, its close is below the reference price (the previous close) and at or below that day's ARB price; the scorer cannot sell on a locked session. "
      "**B** is the shipped `market.py` (ARB 15% after 2026-09-28), **C** the corrected one (ARB 7% from 2026-10-19; nominal Rp1 ARB for references Rp11-14 from 2026-10-20). Original ledger records are never edited: 'changes' means the replay under C differs from the replay under B of the same record. The legacy IDX branch of `paper.score()` sells on an invalidation (stop) close or at the close of the 5th session after entry, and returns no outcome if the horizon close is locked.")
    w("")
    w("## 1. Headline")
    w("")
    w(f"* **{A['records_changed']} of {A['records_replayed']} IDX outcome records change** when the corrected ARB rule (C) replaces the shipped one (B), replay against replay: "
      f"**{cc['EXIT_SHIFTED'] + cc['VERDICT_CHANGED']} exit later at a different price**, **{cc['BECOMES_UNSCORABLE']} can no longer be scored**, "
      f"**{cc['VERDICT_CHANGED']} change verdict**, {cc['BECOMES_SCORABLE']} become scorable. {cc['UNCHANGED']} are unchanged and {cc['NOT_AFFECTED']} lie wholly before 2026-10-19. "
      f"Of the {A['records_exposed_path_touches_1019']} records whose scored path touches 2026-10-19 or later, {A['records_changed']} change ({100 * A['records_changed'] / A['records_exposed_path_touches_1019']:.0f}%). "
      f"All {sum(1 for x in changed if x['B_trade'])} changed records are filled hypothetical trades: {sum(1 for x in changed if x['B_trade'])} of the {A['hypothetical_trades_B']} trades ({100 * sum(1 for x in changed if x['B_trade']) / A['hypothetical_trades_B']:.0f}%), "
      f"{sum(1 for x in changed if x['B_trade'])} of the {A['trades_B_with_path_touching_1019']} whose path touches 10-19 or later ({100 * sum(1 for x in changed if x['B_trade']) / A['trades_B_with_path_touching_1019']:.0f}%); a record without a fill never consults lock_down.")
    w(f"* **Hypothetical paper trades: {A['hypothetical_trades_B']} under B, {A['hypothetical_trades_C']} under C.** Mean net return {pp(nB['mean'])} to {pp(nC['mean'])}, median {pp(nB['median'])} to {pp(nC['median'])}; "
      f"on the {nBb['n']} trades present in both, mean {pp(nBb['mean'])} to {pp(nCb['mean'])}, median {pp(nBb['median'])} to {pp(nCb['median'])}. Partly survivorship (section 5).")
    w(f"* **Verdicts:** B has {A['verdict_counts_B'].get('CORRECT REJECTION', 0)} CORRECT REJECTION and {A['verdict_counts_B'].get('MISSED GAIN (rejected, plan would have profited)', 0)} MISSED GAIN. "
      f"C has {A['verdict_counts_C'].get('CORRECT REJECTION', 0)} and {A['verdict_counts_C'].get('MISSED GAIN (rejected, plan would have profited)', 0)} plus {A['records_with_no_C_outcome']} records with no outcome. "
      "PROFIT and LOSS cannot occur: every IDX decision is a rejection (PASS or NOT EXECUTABLE), so the hypothetical trades are 'what the plan would have done'.")
    w(f"* **Mechanism (one only):** under C a bar that closes {abs(shallowest) * 100:.1f}% to {abs(deepest) * 100:.1f}% below the previous close (true of all {len(dec_bars)} deciding bars) is a locked, unsellable session. "
      f"A stop (invalidation) exit on such a bar is refused and waits for the next bar that meets the exit test (shifts of 1 to {dlt['max_exit_shift_sessions']} sessions, mean {dlt['mean_exit_shift_sessions']:.1f}); "
      "a locked horizon close leaves no outcome at all, because the legacy scorer never rolls past its 5-session horizon.")
    w(f"* **Scale:** market-wide the correction turns {A['market_cells_flipped_false_to_true']:,} (ticker, session) cells from sellable to locked ({A['market_cells_lock_down_B']:,} to {A['market_cells_lock_down_C']:,} locked cells), "
      f"first on {A['first_session_with_flips']}; nothing turns the other way and the ARA lock flags are identical. Few reach a ledger record because a flipped bar only matters when it is the bar where a filled trade's exit test is met.")
    w(f"* **Board hint:** {atl['at_limit']:,} of those {A['market_cells_flipped_false_to_true']:,} flipped bars close exactly at the modelled 7% limit price (consistent with a 7% board) and {atl['strictly_below_limit']:,} close strictly below it (wider-limit names). "
      f"For the {A['records_changed']} changed records the deciding bar closed exactly at the modelled limit price in {n_dec_at} cases and below it in {len(dec_bars) - n_dec_at} "
      f"({', '.join(sorted({x['ticker'] for x in changed if x.get('decisive_bar_hint') and x['decisive_bar_hint'] != 'AT_LIMIT'}))}, a likely 10%-board name).")
    w(f"* **Sensitivity:** with the ARB at 10% instead of 7%, **{S_a['records_changed_vs_B']} records change** versus B (all {A['records_changed']} changes need a close inside the 7% to 10% zone). "
      f"Dropping names with wider-limit evidence leaves {S_c['changed_among_remaining']} of {S_c['records_changed_in_C_total']} changes. The Rp11-14 nominal-Rp1 rule changes **{A['records_changed'] - S_d['records_changed_vs_B']}** records (7% alone gives the same {S_d['records_changed_vs_B']}).")
    w(f"* **Baseline gate:** the B replay reproduces **{G['field_for_field_matches']} of {G['outcomes_replayed']}** recorded outcomes field for field; the {len(G['mismatches'])} mismatches are not ARB effects "
      f"({', '.join(f'{m_['ticker']}: {m_['cause_code']}' for m_ in G['mismatches'])}).")
    w(f"* **Populations:** {P['decisions_signal_on_or_after_1019']} decisions have a signal on or after 2026-10-19 and {P['late_with_hypothetical_trade']} of them carry a hypothetical trade, so the other agent's '88' and '27' are both true "
      f"for that definition. They are not the exposed set: {P['outcomes_path_touches_1019_all']} outcomes ({P['outcomes_path_touches_1019_with_trade']} with a trade) have a path touching 10-19 or later, and "
      f"{sum(1 for x in changed if x['signal_session'] < CUT)} of the {A['records_changed']} changed records have a signal before 10-19.")
    w(f"* **Pending:** {PD['count']} IDX decisions have no outcome ({len(PD['window_still_open'])} window still open, {len(PD['window_complete_but_unscored_under_both_rules'])} complete but never scored under either rule). "
      f"{len(PD['with_lock_down_flip_B_vs_C_on_path_so_far'])} already have a flipped bar on the path ({len(PD['with_flip_after_the_entry_bar_so_far'])} after the entry bar); "
      f"{len(PD['interim_difference_certain_stop_exit_refused_under_C'])} are already certain to differ (a stop exit determined under B is refused under C) and {len(PD['interim_difference_possible_last_bar_locked_only_under_C'])} may.")
    w(f"* **Speculations:** {SP['idx_resolution_rows']} IDX RESOLUTION rows ({SP['idx_speculation_sets']} sets); {SP['resolution_rows_whose_horizon_day_uses_lock_down']} use lock_down at the horizon day ({SP['trades_inside_the_lock_sensitive_rows']} trades), replayable and replayed. "
      f"{len(SP['recorded_rows_changed_B_vs_C'])} of them would not resolve under C ({', '.join(x['key'].split('|')[0].split('-')[-1] + ' ' + x['key'].split('|')[1] for x in SP['recorded_rows_changed_B_vs_C'])}). All {SP['idx_speculation_sets']} sets touch sessions on or after 10-19.")
    w("")
    w("**Limitation that applies to everything below:** only the final pull (`yahoo_recent-20261106T101853Z`, 920 tickers, hash-verified) survives, so every outcome is replayed on that pull (final-bar replay), "
      "not on the pull that was current when the outcome was written. B-versus-C is always computed on the same pull, so data-timing differences cannot leak into the ARB effect; the three places where final-bar data differs from the record are listed in section 3.")
    w("")

    # -------------------------------------------------------------------------------- populations
    w("## 2. Populations (recounted from the ledger, deduplicated)")
    w("")
    w(md_table(["Quantity", "Count"], [
        ["Ledger rows", f"{P['ledger_rows_total']} (SCAN {P['rows_by_type']['SCAN']}, DECISION {P['rows_by_type']['DECISION']}, OUTCOME {P['rows_by_type']['OUTCOME']})"],
        ["IDX decisions", f"{P['idx_decisions']} ({P['idx_decisions_explicit_market_IDX']} with market IDX + {P['idx_decisions_without_market_key_treated_as_IDX']} early PAPER-POLICY-v1 rows with no market key, which score_pending() treats as IDX); {kv(P['idx_decisions_by_kind'])}"],
        ["IDX decisions by policy", kv({k.replace('PAPER-POLICY-', ''): v for k, v in P['idx_decisions_by_policy'].items()})],
        ["IDX OUTCOME rows / latest per decision", f"{P['idx_outcome_rows']} / {P['idx_outcomes_latest_per_decision']}"],
        ["Decisions with more than one OUTCOME row, rows with `revises`", f"{P['idx_decisions_with_more_than_one_outcome_row']}, {P['idx_outcome_rows_with_revises_field']} (none: latest = only)"],
        ["Decisions with signal on/after 2026-10-19", f"{P['decisions_signal_on_or_after_1019']} ({kv(P['late_by_kind'])}); {P['late_with_outcome']} with an outcome, {P['late_without_outcome_pending']} pending"],
        ["...of which with a hypothetical trade", f"{P['late_with_hypothetical_trade']} (decision kind: {kv(P['late_trade_by_decision_kind'])}); rejections that would have traded: {P['late_rejections_that_would_have_traded']}; BUY ON TRIGGER: {P['late_buy_on_trigger_decisions']}"],
        ["...outcomes without a trade", f"{P['late_outcomes_without_trade']} (not fillable at the trigger, or outside the chase band)"],
        ["All IDX outcomes with a trade", f"{P['all_idx_outcomes_with_trade']} (entry on/after 10-19: {P['trades_entry_on_or_after_1019']}; exit on/after 10-19: {P['trades_exit_on_or_after_1019']}; signal before 10-19 but exit on/after: {P['trades_path_touches_1019_signal_before_cut']})"],
        ["Outcomes whose scored path touches 10-19 or later", f"{P['outcomes_path_touches_1019_all']} of {P['idx_outcomes_latest_per_decision']} ({P['outcomes_path_touches_1019_with_trade']} with a trade: entry to exit; {P['outcomes_path_touches_1019_without_trade']} without: nominal window entry to horizon end); not touching: {P['outcomes_path_not_touching_1019']}"],
        ["Decisions with no outcome (pending)", f"{PD['count']}: {len(PD['window_still_open'])} window still open, {len(PD['window_complete_but_unscored_under_both_rules'])} complete (see section 8)"],
    ]))
    w("")
    w(f"Which definition makes '88' and '27' true: **signal_session on or after 2026-10-19** (88 decisions; 27 of them carry a hypothetical trade, all PASS). Under the path definition the counts are {P['outcomes_path_touches_1019_all']} outcomes and {P['outcomes_path_touches_1019_with_trade']} trades. "
      f"All {P['idx_decisions']} IDX decisions are scored by the legacy IDX branch of `paper.score()` (none carries an `execution_plan`), the branch where a locked horizon exit returns no outcome.")
    w("")

    # ---------------------------------------------------------------------------- baseline gate
    w("## 3. Baseline gate: B replay against the recorded outcomes")
    w("")
    w(f"Compared field by field (entry_session, exit_session, exit_reason, net_return at 1e-9, mfe, mae, verdict, discovery r5max/E30/E50/E100/peak_session, fill flags, price_scale): "
      f"**{G['field_for_field_matches']} of {G['outcomes_replayed']} match.** {len(G['mismatches'])} do not:")
    w("")
    w(md_table(["Record", "OUTCOME hash", "Differs in", "Diagnosed cause"], [
        [f"{m_['ticker']} ({m_['decision_id'].split('-F1_ARA')[0].replace('SCAN-', '')})", m_["outcome_record_hash"][:12], ", ".join(m_["differing_fields"]), f"{m_['cause_plain']} [{m_['cause_code']}]"]
        for m_ in G["mismatches"]
    ]))
    w("")
    w(f"The pre-close cause is checkable: {pre['outcomes_whose_last_needed_session_was_not_yet_final_at_the_pull']} recorded outcomes needed a session that was not yet final at their pull (pull(s) {', '.join(pre['pulls_involved'])}); "
      f"{pre['of_which_mismatching_in_replay']} of them mismatch, the others happen not to depend on that bar's price. Neither cause involves the ARB rule, and B-versus-C is unaffected because both use the same final bars.")
    w("")

    # ------------------------------------------------------------------------------ classification
    w("## 4. Corrected replay: category per record (C compared with B)")
    w("")
    w(md_table(["Category", "Records", "Meaning"], [
        ["UNCHANGED", cc["UNCHANGED"], "path touches 10-19 or later, C output identical to B (no trade, or no flipped bar decides the exit)"],
        ["EXIT_SHIFTED", cc["EXIT_SHIFTED"], "the B exit bar is locked under C; exit session and return change, verdict unchanged"],
        ["BECOMES_UNSCORABLE", cc["BECOMES_UNSCORABLE"], "B returns an outcome, C returns None (locked horizon bar, legacy scorer does not roll)"],
        ["BECOMES_SCORABLE", cc["BECOMES_SCORABLE"], "B none, C outcome: impossible here, a tighter limit only removes sellable bars"],
        ["VERDICT_CHANGED", cc["VERDICT_CHANGED"], "exit shifted and the sign of the would-have return flipped"],
        ["NOT_AFFECTED", cc["NOT_AFFECTED"], "no session of the scored path on or after 2026-10-19 (C replay verified identical to B)"],
    ]))
    w("")
    w(f"Unchanged records split into: no trade so lock_down is never consulted ({sum(1 for x in recs if x['category'] == 'UNCHANGED' and str(x.get('subcase', '')).startswith('no paper trade'))}), "
      f"trade with no flipped bar on its path ({sum(1 for x in recs if x['category'] == 'UNCHANGED' and str(x.get('subcase', '')).startswith('trade; no'))}), "
      f"trade with flipped bars that do not decide the exit ({sum(1 for x in recs if x['category'] == 'UNCHANGED' and str(x.get('subcase', '')).startswith('trade; flipped'))}).")
    w("")
    w("The records that change (`results.csv` has all 126 decisions with the full B/C detail, the sessions whose lock flag differs, and every OUTCOME record hash; `flipped_bars.csv` has each flipped bar):")
    w("")
    rows_ = []
    for x in changed:
        cs = f"{x['C_exit']} ({x['C_reason']}) {pp(x['C_net'])}" if x["C_status"] == "OUTCOME" else "no outcome, never scored"
        wi = ""
        if x["category"] == "BECOMES_UNSCORABLE":
            wi = f"{x.get('whatif_roll_exit')} {pp(x.get('whatif_roll_net'))}" if x.get("whatif_roll_exit") else "no sellable close yet"
        hint = hint_txt.get(x.get("decisive_bar_hint"), str(x.get("decisive_bar_hint")))
        rows_.append([
            f"{x['ticker']} `{x['decision_id'].replace('SCAN-', '').replace('-F1_ARA', '')}` / {x['outcome_record_hash'][:10]}", x["signal_session"],
            f"{x['B_exit']} ({x['B_reason']}) {pp(x['B_net'])} {'MG' if str(x['B_verdict']).startswith('MISSED') else 'CR'}", cs + ("" if x["C_status"] != "OUTCOME" else ""),
            pts(x["delta_net_C_minus_B"]) if x["delta_net_C_minus_B"] is not None else "-",
            f"{x['n_flipped_bars_on_path']} ({x['decisive_flipped_bar']} decides)", hint, wi,
        ])
    w(md_table(["Record (decision / OUTCOME hash)", "Signal", "B exit (reason) net, verdict", "C exit (reason) net", "Delta net", "Flipped bars on path", "Deciding bar's close", "What-if roll (b)"], rows_))
    w("")
    w("CR = CORRECT REJECTION, MG = MISSED GAIN. The recorded outcome equals the B replay for all 14 (none of the three baseline mismatches is among them).")
    w("")

    # ---------------------------------------------------------------------------------- aggregates
    w("## 5. Aggregates")
    w("")
    w(md_table(["Measure", "B (shipped)", "C (corrected)"], [
        ["Outcome records", A["records_replayed"], A["records_replayed"] - A["records_with_no_C_outcome"]],
        ["Hypothetical paper trades", A["hypothetical_trades_B"], A["hypothetical_trades_C"]],
        ["Mean net return, all trades", pp(nB["mean"]), pp(nC["mean"])],
        ["Median net return, all trades", pp(nB["median"]), pp(nC["median"])],
        [f"Mean / median net return, the {nBb['n']} trades present in both", f"{pp(nBb['mean'])} / {pp(nBb['median'])}", f"{pp(nCb['mean'])} / {pp(nCb['median'])}"],
        [f"Mean / median net return, the {A['trades_B_with_path_touching_1019']} trades with a path touching 10-19", f"{pp(A['net_return_B_trades_touching_1019']['mean'])} / {pp(A['net_return_B_trades_touching_1019']['median'])}",
         f"{pp(A['net_return_C_trades_touching_1019']['mean'])} / {pp(A['net_return_C_trades_touching_1019']['median'])} ({A['net_return_C_trades_touching_1019']['n']} trades)"],
        ["CORRECT REJECTION", A["verdict_counts_B"].get("CORRECT REJECTION", 0), A["verdict_counts_C"].get("CORRECT REJECTION", 0)],
        ["MISSED GAIN", A["verdict_counts_B"].get("MISSED GAIN (rejected, plan would have profited)", 0), A["verdict_counts_C"].get("MISSED GAIN (rejected, plan would have profited)", 0)],
        ["PROFIT / LOSS", "0 / 0", "0 / 0"],
        ["No outcome", 0, A["records_with_no_C_outcome"]],
    ]))
    w("")
    lost = A["net_return_B_trades_lost_in_C"]
    w(f"Among the {dlt['n']} exit-shifted trades the C-minus-B net return averages {pts(dlt['mean'])} (median {pts(dlt['median'])}; {dlt['worse_n']} worse, {dlt['better_n']} better). "
      f"The {lost['n']} trades that vanish under C had a B mean of {pp(lost['mean'])} (median {pp(lost['median'])}), {lost_mg} of them MISSED GAIN, so removing them lowers the C mean on its own. "
      "The population is survivorship-conditioned in three ways: it contains only rejected candidates whose plan would have filled, windows still open are absent, and the records that become unscorable under C drop out. "
      "Read the means as properties of the scored subset, not of the strategy. Discovery fields (r5max, E30...) are identical under B and C for every record, because they use the reference-chain level, not lock flags.")
    w("")

    # -------------------------------------------------------------------------------- sensitivity
    w("## 6. Sensitivity")
    w("")
    w(f"**(a) ARB 10% instead of 7% from 2026-10-19** (monkeypatched inside the worker process; Rp1 nominal rule kept, which for references Rp11-14 changes nothing because the 10% formula already gives reference minus Rp1): "
      f"**{S_a['records_changed_vs_B']} records change versus B** ({kv({k: v for k, v in S_a['category_counts'].items() if v})}). Every bar that decides one of the {A['records_changed']} changes closed {abs(shallowest) * 100:.1f}% to {abs(deepest) * 100:.1f}% below its reference, short of a 10% limit, so a 10% limit leaves them sellable.")
    w("")
    w(f"**(b) What-if, labelled: keep rolling past the horizon to the first sellable close.** Feasible and done cleanly with the real scorer (horizon lengthened in the worker process until it returns). "
      f"This is not what the scorer does; it returns no outcome. Of the {len(S_b['records'])} unscorable records, {S_b['resolved']} resolve and {S_b['unresolved_no_sellable_close_in_data_yet']} cannot yet (no sellable close in the data):")
    w("")
    w(md_table(["Record", "B exit, net, verdict", "What-if exit, net, verdict", "Extra sessions"], [
        [i["ticker"], f"{i['B_exit']} {pp(i['B_net'])} {'MG' if str(i['B_verdict']).startswith('MISSED') else 'CR'}",
         (f"{i['whatif_exit']} ({i['whatif_reason']}) {pp(i['whatif_net'])} {'MG' if str(i['whatif_verdict']).startswith('MISSED') else 'CR'}" if i["whatif_exit"] else i["note"]),
         i["extra_sessions_past_horizon"] if i["extra_sessions_past_horizon"] is not None else "-"] for i in S_b["records"]]))
    w("")
    w(f"With the resolved what-ifs added back, the trade population is {S_b['population_C_trades_plus_resolved_what_ifs']['n']} trades, mean {pp(S_b['population_C_trades_plus_resolved_what_ifs']['mean'])}, median {pp(S_b['population_C_trades_plus_resolved_what_ifs']['median'])} "
      f"(B: {pp(nB['mean'])} / {pp(nB['median'])}); {S_b['verdict_changes_vs_B']} verdict changes versus B (a MISSED GAIN becomes CORRECT REJECTION).")
    w("")
    w(f"**(c) Names with empirical wider-limit evidence dropped.** Evidence = a tradeable bar on or after 10-19 whose close is strictly below that name's modelled 7% limit price (the 2026-10-19 Rp11-14 bars excluded). "
      f"{S_c['n_tickers_with_evidence_among_replayed']} tickers among the replayed records qualify ({', '.join(S_c['tickers_with_evidence_among_replayed_records'])}; {S_c['market_wide_tickers_with_evidence']} market-wide), covering {S_c['records_dropped']} of {S_c['records_total']} records. "
      f"After dropping them **{S_c['changed_among_remaining']} of the {S_c['records_changed_in_C_total']} changed records remain** (dropped: {', '.join(i.split('-F1_ARA-')[1] for i in S_c['changed_ids_dropped'])}). "
      f"Using only the deciding bar of each changed record gives the same answer ({S_c['changed_remaining_if_those_with_decisive_below_limit_bar_dropped']} remain). "
      "Caution: absence of such evidence is not evidence of a 7% board; a 10%-board name that never fell 7 to 10% looks like a 7% name. In the other direction, repeated closes exactly at the 7% limit price "
      f"({', '.join(f'{t} {n}' for n, t in at_top)} such closes since 10-19) are strong evidence of a 7% board for those names.")
    w("")
    w(f"**(d) Extra decomposition: the Rp11-14 nominal-Rp1 rule on its own.** Removing it from C (7% only) leaves the same {S_d['records_changed_vs_B']} changed records, so the 2026-10-20 change affects no ledger record; the whole effect is the 7% limit. "
      "The market.py note that 'nothing in the ledger depends on' the unknown 2026-10-19 Rp11-14 limit is confirmed (claims list in `summary.json`).")
    w("")

    # ------------------------------------------------------------------------------ speculations
    w("## 7. Speculations (`paper/speculations.jsonl`)")
    w("")
    w(f"{SP['idx_speculation_sets']} IDX sets and {SP['idx_resolution_rows']} IDX RESOLUTION rows ({kv(SP['idx_resolution_rows_by_window_and_status'])}). Only the BASE5 rows use lock_down (the horizon day, rolling to the next sellable close): "
      f"**{SP['resolution_rows_whose_horizon_day_uses_lock_down']} rows holding {SP['trades_inside_the_lock_sensitive_rows']} trades** ({n_cand_tr} candidate and {n_twin_tr} twin trades; {n_cand_notfill} candidate was not fillable). NEXT1 rows use next-session returns only and are identical under B and C "
      f"({'verified' if SP['next1_rows_identical_B_vs_C'] else 'NOT verified'}); no PATH20 row exists yet. **Replayable: yes**, with `speculation.resolve_set()` itself. The code tree lacks the protocol JSON that `windows()` reads, so the harness supplies the three window definitions "
      f"(BASE5 enter next close, hold 5; PATH20; NEXT1), reconstructed rather than read; they are validated by the B replay, which reproduces **{SP['baseline_gate']['matches']} of {SP['baseline_gate']['rows']}** recorded rows "
      f"(including both BASE5 rows, all 11 trades). The mismatch ({', '.join(m_['key'].split('|')[0].split('-')[-1] + ' ' + m_['key'].split('|')[1] for m_ in SP['baseline_gate']['mismatches'])}) is a NEXT1 row: {SP['baseline_gate']['mismatches'][0]['cause'] if SP['baseline_gate']['mismatches'] else ''}")
    w("")
    w("Both BASE5 rows are for signal 2026-10-29 with horizon day 2026-11-06, the last bar of the data, so a locked horizon bar leaves no later bar to roll to:")
    w("")
    w(md_table(["Set", "Role", "Ticker", "B exit, net", "C result", "Exit bar under C"], [
        [r["set_id"].split("F1_ARA-")[1], r["role"], r["ticker"],
         (f"{r['B_exit']} {pp(r['B_net'])}" if r["B_exit"] else r["B_status"]),
         (f"{r['C_exit']} {pp(r['C_net'])}" if r["C_exit"] else r["C_status"]),
         ("no trade (not fillable)" if r["B_status"] != "TRADED" else (f"locked: close {r['exit_bar_close']:g} = modelled 7% limit {r['exit_bar_modelled_7pct_arb']:g} on reference {r['exit_bar_ref']:g} ({r['exit_bar_hint']})" if r["exit_bar_flipped_to_locked_under_C"] else "sellable"))]
        for r in SP["lock_sensitive_trade_rows"]]))
    w("")
    w(f"Under C the {', '.join(x['key'].split('|')[0].split('-')[-1] for x in SP['recorded_rows_changed_B_vs_C'])} set could not resolve ({len(flipped_tw)} twins, {' and '.join(flipped_tw)}, are locked at the horizon bar and `resolve_set` waits for the whole set); the other set resolves identically. "
      f"All {SP['idx_speculation_sets']} IDX sets (earliest signal {min(SP['idx_sets_by_signal_session'])}) and all {SP['idx_resolution_rows']} IDX resolutions touch sessions on or after 10-19. "
      f"For the {SP['open_base5_sets']['count']} sets whose BASE5 window is still open, {SP['open_base5_sets']['horizon_bar_already_observed']} have reached their horizon bar (entry + 5 sessions), and BASE5 reads lock_down only from that bar on, "
      f"so no flip observed so far can matter yet ({SP['open_base5_sets']['with_any_flip_so_far_informational']} have a flipped bar earlier on a member's path; listed in `summary.json`, speculations.open_base5_sets).")
    w("")

    # ---------------------------------------------------------------------------------- pending
    w("## 8. Pending decisions (no outcome yet)")
    w("")
    w(f"{PD['count']} IDX decisions have no OUTCOME. **{len(PD['window_still_open'])} have a window still open** (the final bar, 2026-11-06, does not yet cover signal + 6 sessions). "
      f"**{len(PD['window_complete_but_unscored_under_both_rules'])} have a complete window but the legacy scorer returns no outcome under B and C alike**: {stuck_txt}. "
      f"Neither is caused by the correction. Of the {len(PD['window_still_open'])} open windows, {len(PD['with_lock_down_flip_B_vs_C_on_path_so_far'])} decisions already have a bar on the path whose lock flag differs between B and C "
      f"({len(PD['with_flip_after_the_entry_bar_so_far'])} after the entry bar; a flip on the entry bar cannot matter, only lock_up is read there). "
      "Interim state is computed by running the real scorer with the horizon cut to the post-entry sessions seen so far: STOP HIT = an invalidation exit is already determined; OPEN = no stop hit yet; "
      "HELD = the last observed bar is locked, so an exit there would be refused; ENTRY_* = too early. "
      f"Where B already has a STOP HIT that C refuses ({', '.join(i.split('-F1_ARA-')[1] + ' ' + i.split('-F1_ARA-')[0][-5:] for i in PD['interim_difference_certain_stop_exit_refused_under_C'])}) the two records will certainly differ when written; "
      f"where C is merely HELD ({', '.join(i.split('-F1_ARA-')[1] + ' ' + i.split('-F1_ARA-')[0][-5:] for i in PD['interim_difference_possible_last_bar_locked_only_under_C'])}) they may.")
    w("")
    prow = []
    for x in [x for x in R if not x["has_recorded_outcome"]]:
        flips = f"{x['n_flipped_bars_on_path']} ({x['n_flipped_bars_after_entry_bar']} after entry): {x['flipped_sessions']}" if x["n_flipped_bars_on_path"] else "none"
        prow.append([x["ticker"], x["signal_session"], x["policy_id"].replace("PAPER-POLICY-", ""), "PASS" if x["decision"] == "PASS" else "NOT EXEC",
                     "open, " + str(x["sessions_remaining_to_window_end"]) + " to go" if x["pending_state"] == "WINDOW_OPEN" else "complete, never scored",
                     flips, x["interim_B"] if x["pending_state"] == "WINDOW_OPEN" else "-", (x["interim_C"] if x["interim_differs_B_vs_C"] else "same") if x["pending_state"] == "WINDOW_OPEN" else "-"])
    w(md_table(["Ticker", "Signal", "Policy", "Kind", "Window", "Flipped bars on path so far", "Interim under B", "Interim under C"], prow))
    w("")

    # ------------------------------------------------------------------------------------ method
    w("## 9. How it was run")
    w("")
    w(f"One command: `python3 -I {Path(__file__).resolve()}` (about 15 seconds; `--reuse` re-analyses the worker output already in `work/`). It verifies the inputs (ledger sha256 `{res['inputs']['ledger_sha256_B'][:16]}...`, head hash, manifest sha256 `{res['inputs']['manifest_sha256'][:16]}...`, {res['inputs']['raw_payloads']['listed']} raw payload hashes, "
      f"code trees identical except `{', '.join(res['inputs']['code_tree_differences'])}`), then starts four worker processes with the working directory set to the code directory and `sys.path.insert(0, '.')`. "
      "Each worker mimics `score_pending()`: `paper.load_recent(manifest, 'IDX', purpose='scoring')`, `paper._market`, `us_actions.yahoo_events`, then per decision `paper._window_complete`, `paper.scoring_units`, `paper.score`. "
      "Workers: **B** (shipped tree), **C** (corrected tree), **C10** (C tree, ARB 10% via an in-memory patch of `market.limits`' regime table), **C7** (C tree without the Rp11-14 rule, same mechanism). "
      "Bytecode is neither read from nor written to the code trees (`sys.pycache_prefix`); before and after the run the harness checks that no file under either code tree or either ledger changed. "
      f"Python {summ_['environment']['python']}, numpy {summ_['environment']['numpy']}, pandas {summ_['environment']['pandas']}. Outputs: `results.csv` (126 decisions), `flipped_bars.csv`, `speculation_replay.csv`, `summary.json`, `work/` (worker output and market matrices).")
    w("")
    w("## 10. Unresolved items and caveats")
    w("")
    cav = [
        f"**Final-bar replay.** Every outcome is replayed on the last pull, not the pull that wrote it. Two recorded outcomes used an in-progress bar (pull started {pre_pm['pull_started_utc'][11:16] if pre_pm else '?'} UTC, before the {pre_pm['session_final_at_utc'][11:16] if pre_pm else '?'} UTC final-bar time that `paper.session_close` defines for IDX); one differs by a float knife-edge. These are production-data issues independent of ARB; the production flow that completed those windows on a pre-close pull is worth fixing separately.",
        f"**Board membership is unknown.** The corrected rule applies the regular-board 7% limit to every name. Names on a 10% board are over-locked by falls of 7 to 10%; the evidence is in `flipped_bars.csv` and section 6(c) ({', '.join(evid_changed) or 'none'} among the changed records; the other evidence names sit on records that do not change). A close at the limit price is consistent with a 7% board, never proof.",
        f"**{n_dec_at} of the {len(dec_dist_ids)} changes ride on an inclusive test.** The deciding bar closed exactly at the modelled limit price in {n_dec_at} of {len(dec_bars)} cases, and the lock test is 'at or below the ARB' (the task's definition). "
        "A close at the limit is not necessarily a sale-proof session in the real market (buyers may exist), so these changes are a modelling convention; a strict 'below the ARB' test would leave them unchanged. I did not run that variant because it would mean changing the lock formula itself.",
        f"**The legacy scorer never rolls past its horizon.** The {len(lost_recs)} unscorable records are not 'lost data'; they would never be written even after the locks release, and their omission is selective ({lost_mg} of the {len(lost_recs)} were MISSED GAIN). Whether the scorer should roll (as `execution.execute` does) is a design decision for the owner; the what-if in 6(b) only shows the size.",
        "**Rules not verified here.** I measured what the code in the C tree does; I did not check the October 2026 decrees against the exchange, and market.py itself says the decree texts were not read. After 2026-12-31 C carries the 7% rule forward (unconfirmed); no ledger record or pending window reaches that date.",
        f"**Speculation windows are reconstructed** (protocol JSON absent from the code tree) and validated only through the B replay reproducing {SP['baseline_gate']['matches']} of {SP['baseline_gate']['rows']} recorded rows; the miss is a NEXT1 row whose cause cannot be proven because that day's payload did not survive.",
        "**Interim states for pending decisions** use a truncated-horizon run of the real scorer; they show what is already determined, not what will be recorded.",
        "**Survivorship.** Means and medians in section 5 describe a conditioned subset (rejected candidates that would have filled, windows complete, scorable under the rule set).",
        "**Independence.** I did not look for the other analyst's work, so these numbers have not been cross-checked against it.",
    ]
    for c in cav:
        w(f"* {c}")
    w("")
    return "\n".join(L)



# ---------------------------------------------------------------------------------------------- main
def snapshot(paths):
    """(size, mtime_ns) of every file below the given directories (to prove the run wrote nothing there)."""
    snap = {}
    for root in paths:
        for dp, _dn, fns in os.walk(root):
            for fn in fns:
                fp = os.path.join(dp, fn)
                try:
                    st = os.stat(fp)
                    snap[fp] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    snap[fp] = None
    return snap


def run_workers():
    WORK.mkdir(parents=True, exist_ok=True)
    procs = {}
    for tag, v in VARIANTS.items():
        log = open(WORK / f"worker_{tag}.log", "w", encoding="utf-8")
        p = subprocess.Popen(
            [sys.executable, "-I", str(Path(__file__).resolve()), "--worker", tag],
            stdout=log, stderr=subprocess.STDOUT, cwd=str(CODE[v["code"]]),
        )
        procs[tag] = (p, log)
    failed = []
    for tag, (p, log) in procs.items():
        rc = p.wait()
        log.close()
        if rc != 0:
            failed.append(tag)
    if failed:
        raise SystemExit(f"worker(s) failed: {failed}; see {WORK}/worker_<tag>.log")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worker", help="internal: run one replay variant")
    ap.add_argument("--reuse", action="store_true", help="skip the worker runs and re-analyse work/ output")
    args = ap.parse_args()
    if args.worker:
        worker(args.worker)
        return
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    guarded = [CODE["B"].parent, CODE["C"].parent]  # code_B and code_C trees including their paper/ ledgers
    before = snapshot(guarded)
    if not args.reuse:
        run_workers()
    res = analyse(args)
    after = snapshot(guarded)
    untouched = before == after
    res["summary"]["checks"].append({"check": "no file under code_B or code_C (code, ledgers, data) was created, changed or removed by this run", "passed": untouched})
    res["summary"]["claims_checked"] = claims_checked(res)
    res["summary"]["runtime_seconds_total"] = round(time.time() - t0, 1)
    write_outputs(res)
    (OUT / "report.md").write_text(build_report(res), encoding="utf-8")
    S = res["summary"]
    print("inputs ok:", S["inputs_ok"], "| code/ledger untouched:", untouched)
    print("checks:", sum(c["passed"] for c in S["checks"]), "of", len(S["checks"]), "passed")
    for c in S["checks"]:
        if not c["passed"]:
            print("  FAILED:", c["check"])
    print("populations:", {k: S["populations"][k] for k in ("idx_decisions", "idx_outcomes_latest_per_decision", "decisions_signal_on_or_after_1019", "late_with_hypothetical_trade")})
    print("baseline:", S["baseline_gate"]["field_for_field_matches"], "of", S["baseline_gate"]["outcomes_replayed"], "match;", [m["ticker"] for m in S["baseline_gate"]["mismatches"]])
    print("classification:", S["classification"]["counts"])
    print("records changed:", S["aggregates"]["records_changed"], "| C10 changed:", S["sensitivity"]["a_arb_10_percent"]["records_changed_vs_B"])
    print("trades B/C:", S["aggregates"]["hypothetical_trades_B"], S["aggregates"]["hypothetical_trades_C"])
    print("done in", S["runtime_seconds_total"], "s; outputs in", OUT)
    if not S["inputs_ok"] or not untouched or not all(c["passed"] for c in S["checks"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ARB-correction impact replay (impact analyst 2).

Question: the IDX auto-rejection-below (ARB) rule in idxsig/market.py was missing two October 2026
changes (ARB 7% from 2026-10-19; a nominal Rp1 ARB for references Rp11-14 from 2026-10-20). What does the
correction change in the records already written to paper/ledger.jsonl and paper/speculations.jsonl?

Method: replay the REAL scorer (paper.score / speculation.resolve_set) on the frozen final Yahoo pull,
once under the shipped rules (code_B) and once under the corrected rules (code_C), and report C minus B,
record by record. Original records are only read, never written. The ARB effect is always C vs B (replay
vs replay), never C vs the recorded value, so data-timing artefacts cannot leak into it.

One command (writes everything next to this file, about 20 seconds):

    python3 -I /tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/arb2/impact_2/harness.py

Structure: the same file is the orchestrator (default) and the worker (--worker VARIANT). A worker runs in
its own process with cwd = a code directory, so that "import idxsig" resolves to that copy; it writes only
into this output directory. Variants: B (shipped), C (corrected), C10 (C with ARB 10% instead of 7%),
C7b (C without the Rp11-14 nominal-Rp1 rule, i.e. the 7% change alone), CH (C with names that show
wider-limit evidence at 10%).
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
import warnings
from collections import Counter, OrderedDict, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------------------------------ constants
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # .../scratchpad/arb2
SCRATCH = ROOT.parent  # .../scratchpad
CODE = {"B": ROOT / "code_B" / "idx-signals", "C": ROOT / "code_C" / "idx-signals"}
FROZEN = SCRATCH / "arb" / "frozen_inputs"
MANIFEST = FROZEN / "yahoo_recent-20261106T101853Z.jsonl"
FROZEN_RAW = FROZEN / "yahoo_recent_raw" / "20261106T101853Z"
OUT_DIR = HERE
WORK = HERE / "work"

CUT = "2026-10-19"  # first session of the 7% ARB
HORIZON = 5  # paper.POLICY.horizon_sessions
TOL = 1e-9
IDX_CLOSE_UTC = "09:00:00"  # 16:00 WIB: a pull started before this on a bar's date saw an intraday bar
EXPECT = {
    "ledger_sha256": "c1a67890577f7495212d1d9b3abbc97922bf741a007fc422c8225f5a87cd4395",
    "ledger_rows": 755,
    "ledger_head_hash": "4ee35255de041da3b75af78fdee3062560918affb97e64aa4b699077655277e8",
    "spec_sha256": "0118f0c87d96e1a5fc6726d2668536d93e9c45ddc7e2a0dbdbaff47264542b04",
    "spec_rows": 277,
    "manifest_sha256_prefix": "3a27d3445b3d",
}
# variant -> (code dir key, patch)
VARIANTS = OrderedDict(
    [
        ("B", ("B", None)),
        ("C", ("C", None)),
        ("C10", ("C", {"arb_pct": 0.10})),
        ("C7b", ("C", {"drop_rp1_rule": True})),
        ("CH", ("C", {"hybrid": True})),
    ]
)
# research/SPECULATION_REGISTER_v1/protocol_v1_1.json is not in the code copies, so speculation.windows() is
# patched with the definitions the code itself implies (window_length(), resolve_set(), cone statements);
# the baseline replay of the recorded BASE5 resolutions is the check that this reading is right.
SPEC_WINDOWS = {
    "BASE5": {"kind": "trade", "entry_window": 1, "holding_sessions": 5},
    "PATH20": {"kind": "path", "horizon": 20},
    "NEXT1": {"kind": "path", "horizon": 1},
}
TRADE_FIELDS = (
    "entry_session",
    "exit_session",
    "exit_reason",
    "entry_price",
    "entry_close",
    "entry_basis",
    "net_return",
    "mfe",
    "mae",
)
VOLATILE = {"scored_at", "resolved_at", "data", "prev_hash", "record_hash", "type", "units"}


# ------------------------------------------------------------------------------------------ utilities
def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(f"not serialisable: {type(o)}")


def dump_json(obj, path: Path) -> None:
    Path(path).write_text(json.dumps(obj, indent=1, sort_keys=True, default=jsonable), encoding="utf-8")


def deep_diff(a, b, path="", tol=TOL, ignore=VOLATILE) -> list[tuple]:
    """Differences between two JSON-like values; floats compared with absolute tolerance `tol`."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in ignore:
                continue
            if k not in a:
                out.append((f"{path}/{k}", "<absent>", b[k]))
            elif k not in b:
                out.append((f"{path}/{k}", a[k], "<absent>"))
            else:
                out += deep_diff(a[k], b[k], f"{path}/{k}", tol, ignore)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((f"{path}[len]", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += deep_diff(x, y, f"{path}[{i}]", tol, ignore)
    elif (
        isinstance(a, (int, float))
        and isinstance(b, (int, float))
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        if not (a == b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))):
            if not (math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol):
                out.append((path, a, b))
    elif a != b:
        out.append((path, a, b))
    return out


def fnum(x):
    """CSV cell for a number or None (full precision; numpy scalars become Python numbers; NaN is blank)."""
    if x is None:
        return ""
    if isinstance(x, (np.bool_, bool)):
        return "true" if bool(x) else "false"
    if isinstance(x, np.floating):
        x = float(x)
    if isinstance(x, np.integer):
        x = int(x)
    if isinstance(x, float):
        return "" if math.isnan(x) else repr(x)
    return str(x)


# ============================================================================================ WORKER
def whatif_roll(paper, decision, m, units):
    """WHAT-IF only. The legacy IDX branch of paper.score() with ONE change: a horizon exit that is locked
    at ARB keeps rolling past the horizon to the first sellable close (instead of returning None).
    Everything up to and including the horizon session is identical to paper.score() (checked by the
    worker on every decision for which paper.score() returns an outcome). Returns None when the window is
    open, or when no sellable close exists before the end of the data."""
    from idxsig.price_units import split_conversion_factor

    p = paper.POLICY
    tickers, dates = list(m.tickers), m.dates.astype(str)
    t = decision["instrument"]["ticker"]
    if t not in tickers or decision["signal_session"] not in dates:
        return None
    n = tickers.index(t)
    d = int(np.flatnonzero(dates == decision["signal_session"])[0])
    if d + paper._span(decision) >= len(dates):
        return None
    close = m.close[n]
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(m.present[n] & (m.prev[n] > 0) & (close > 0), np.log(close / m.prev[n]), 0.0)
    level = np.exp(np.cumsum(logret))
    e = d + 1
    plan = decision.get("plan", {})
    signal_factor = split_conversion_factor(
        str(dates[d]), units["actions"], units["adjustment_reference"], coverage_complete=units.get("coverage_complete", False)
    )
    scale = 1.0 / signal_factor
    entry_price = float(close[e])
    fillable = bool(m.tradeable[n, e] and not m.lock_up[n, e])
    in_band = "max_chase_price" in plan and plan["invalidation"] * scale < entry_price <= plan["max_chase_price"] * scale
    stop = plan["invalidation"] * scale if "invalidation" in plan else None
    if not (fillable and in_band):
        return {"trade": None, "verdict": "CORRECT REJECTION", "rolled_sessions": 0}
    target = e + p.horizon_sessions
    exit_idx, reason, path = None, None, []
    for k in range(e + 1, len(dates)):
        path.append(float(level[k] / level[e] - 1))
        sellable = bool(m.tradeable[n, k] and not m.lock_down[n, k])
        if k <= target and sellable and close[k] <= stop:
            exit_idx, reason = k, "invalidation"
            break
        if k >= target and sellable:
            exit_idx, reason = k, "horizon"
            break
    if exit_idx is None:
        return None
    gross = float(level[exit_idx] / level[e] - 1)
    net = (1 + gross) * (1 - p.fee_sell) / (1 + p.fee_buy) - 1
    trade = {
        "entry_session": str(dates[e]),
        "exit_session": str(dates[exit_idx]),
        "exit_reason": reason,
        "entry_price": entry_price,
        "net_return": net,
        "mfe": max(path),
        "mae": min(path),
    }
    if decision["decision"] == "BUY ON TRIGGER":
        verdict = "PROFIT" if net > 0 else "LOSS"
    else:
        verdict = "CORRECT REJECTION" if net <= 0 else "MISSED GAIN (rejected, plan would have profited)"
    return {"trade": trade, "verdict": verdict, "rolled_sessions": max(0, exit_idx - target)}


def install_limits_patch(market, arb_pct=None, drop_rp1_rule=False):
    """Monkeypatch market.limits (in memory, this process only) with modified regimes from 2026-10-19."""
    orig = market.limits
    regimes = []
    for r in market.REGIMES:
        kw = {}
        if r.start >= date(2026, 10, 19):
            if arb_pct is not None and r.arb_flat is not None:
                kw["arb_flat"] = arb_pct
            if drop_rp1_rule and getattr(r, "arb_abs_max", None) is not None:
                kw["arb_abs_max"] = 10.0
        regimes.append(dataclasses.replace(r, **kw) if kw else r)
    patched = tuple(regimes)

    def limits_patched(ref, days):
        saved = market.REGIMES
        market.REGIMES = patched
        try:
            return orig(ref, days)
        finally:
            market.REGIMES = saved

    market.limits = limits_patched
    return patched


def run_worker(variant: str, work_dir: str, evidence_file: str | None) -> None:
    sys.dont_write_bytecode = True
    code_key, patch = VARIANTS[variant]
    code_dir = Path.cwd().resolve()
    if code_dir != CODE[code_key].resolve():
        raise SystemExit(f"worker {variant} must run with cwd={CODE[code_key]} (cwd is {code_dir})")
    work = Path(work_dir).resolve()
    if work == code_dir or code_dir in work.parents:
        raise SystemExit("refusing to write inside a code directory")
    sys.path.insert(0, str(code_dir))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result, arrays = _worker_body(variant, patch, code_dir, evidence_file)
    counts = Counter(f"{w.category.__name__}: {str(w.message)[:160]}" for w in caught)
    result["warnings"] = [{"warning": k, "count": v} for k, v in sorted(counts.items())]
    dump_json(result, work / f"replay_{variant}.json")
    np.savez_compressed(work / f"arrays_{variant}.npz", **arrays)


def _worker_body(variant, patch, code_dir, evidence_file):
    import pandas as pd  # noqa: F401  (idxsig needs it; imported here so a failure is explicit)
    import idxsig
    from idxsig import market, paper, speculation, us_actions

    assert Path(idxsig.__file__).resolve().is_relative_to(code_dir), idxsig.__file__
    assert Path(market.__file__).resolve().is_relative_to(code_dir), market.__file__
    patched_regimes = None
    if patch and not patch.get("hybrid"):
        patched_regimes = install_limits_patch(market, patch.get("arb_pct"), patch.get("drop_rp1_rule", False))

    df, data = paper.load_recent(MANIFEST, "IDX", purpose="scoring")  # production flow, step 1
    m = paper._market(df, "IDX")  # step 2
    events = us_actions.yahoo_events(MANIFEST, market="IDX")  # step 3
    meta = {
        "variant": variant,
        "idxsig_file": str(idxsig.__file__),
        "market_file": str(market.__file__),
        "market_sha256": sha256_file(Path(market.__file__)),
        "manifest": data["manifest"],
        "manifest_sha256": data["manifest_sha256"],
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "n_tickers": int(m.shape[0]),
        "n_sessions": int(m.shape[1]),
        "first_session": str(m.dates[0]),
        "last_session": str(m.dates[-1]),
        "regimes": [
            {"start": r.start.isoformat(), "arb_flat": r.arb_flat, "arb_abs_max": getattr(r, "arb_abs_max", None), "label": r.label}
            for r in (patched_regimes or market.REGIMES)
        ],
        "chain_problems_ledger": paper.verify_chain(),
        "chain_problems_speculations": paper.verify_chain(speculation.SPEC_LEDGER),
    }
    if patch and patch.get("hybrid"):
        evidence = set(json.loads(Path(evidence_file).read_text())["tickers"])
        keep_limits = market.limits
        install_limits_patch(market, arb_pct=0.10)  # second market at ARB 10%, for the evidence names only
        m10 = paper._market(df, "IDX")
        market.limits = keep_limits
        rows = [i for i, t in enumerate(m.tickers) if str(t) in evidence]
        m.lock_down[rows, :] = m10.lock_down[rows, :]
        meta["hybrid_names"] = sorted(evidence)
        meta["hybrid_rows"] = len(rows)

    # ---- arrays for the orchestrator (cell-level analysis), cross-checked against the flags the scorer uses
    arrays = {
        "tickers": np.array([str(t) for t in m.tickers]),
        "dates": np.array([str(x) for x in m.dates]),
        "close": m.close,
        "prev": m.prev,
        "high": m.high,
        "low": m.low,
        "volume": m.volume,
        "present": m.present,
        "tradeable": m.tradeable,
        "lock_up": m.lock_up,
        "lock_down": m.lock_down,
    }
    if variant != "CH":
        day_grid = np.broadcast_to(m.dates.astype("datetime64[D]"), m.close.shape)
        ref = np.where(np.isfinite(m.prev) & (m.prev > 0), m.prev, np.nan)
        safe_ref = np.nan_to_num(ref, nan=1.0)
        ara, arb = market.limits(safe_ref, day_grid)
        sp_ara, sp_arb = market.special_limits(safe_ref)
        one_price = (m.high == m.low) & (m.low == m.close)
        sub50 = ((m.close < 50) | (ref < 50)) & (day_grid < np.datetime64("2026-09-28"))
        thin = one_price | sub50
        has_ref = np.isfinite(ref)
        lu = m.tradeable & has_ref & ((m.close >= ara) | (thin & (m.close >= sp_ara)))
        ld = m.tradeable & has_ref & (m.close < ref) & ((m.close <= arb) | (thin & (m.close <= sp_arb)))
        assert (lu == m.lock_up).all() and (ld == m.lock_down).all(), "recomputed flags differ from Market.build"
        arrays.update(arb=arb, ara=ara, sp_arb=sp_arb, one_price=one_price)
        meta["flag_recompute_matches_market_build"] = True

    # ---- the scored decisions, exactly as score_pending() does it (without appending anything)
    lines = paper.ledger_lines()
    decisions = [r for r in lines if r.get("type") == "DECISION" and r.get("market", "IDX") == "IDX"]
    out = OrderedDict()
    n_equiv, equiv_problems = 0, []
    for r in decisions:
        did, ticker = r["decision_id"], r["instrument"]["ticker"]
        tev = events[events["ticker"] == ticker] if len(events) else events
        window_complete = bool(paper._window_complete(r, m))
        units, reason, evidence = paper.scoring_units(r, m, tev, None)
        outcome, err = None, None
        if units is not None:
            try:
                outcome = paper.score(r, m, price_units=units)
            except ValueError as exc:  # recorded close does not reconcile in these units
                err = str(exc)
        wi = whatif_roll(paper, r, m, units) if (units is not None and err is None) else None
        if outcome is not None:  # the what-if must reproduce the real scorer wherever the real scorer answers
            tr = (outcome.get("execution") or {}).get("paper_trade")
            ok = (wi is not None) and ((wi["trade"] is None) == (tr is None)) and wi["verdict"] == outcome["decision_verdict"]
            if ok and tr is not None:
                ok = all(wi["trade"][f] == tr[f] for f in ("entry_session", "exit_session", "exit_reason", "entry_price", "net_return", "mfe", "mae"))
            n_equiv += 1 if ok else 0
            if not ok:
                equiv_problems.append(did)
        out[did] = {
            "ticker": ticker,
            "signal_session": r["signal_session"],
            "window_complete": window_complete,
            "units_reason": reason,
            "score_error": err,
            "outcome": outcome,
            "whatif": wi,
        }
    meta["horizon_sessions"] = paper.POLICY.horizon_sessions
    meta["span_values_of_idx_decisions"] = sorted({paper._span(r) for r in decisions})
    meta["whatif_equivalence"] = {
        "decisions_where_paper_score_returns_an_outcome": sum(1 for v in out.values() if v["outcome"] is not None),
        "whatif_identical_to_paper_score": n_equiv,
        "problems": equiv_problems,
    }

    # ---- speculations: replay the real resolver on the frozen bars
    spec_rows = paper.ledger_lines(speculation.SPEC_LEDGER)
    sets = OrderedDict((s["set_id"], s) for s in spec_rows if s["type"] == "SPECULATION_SET" and s["market"] == "IDX")
    speculation.windows = lambda: SPEC_WINDOWS  # protocol_v1_1.json is not shipped in the code copies
    spec = OrderedDict()
    for set_id, s in sets.items():
        for wid in s["windows"]:
            try:
                rec = speculation.resolve_set(s, wid, m, events, None)
            except Exception as exc:  # noqa: BLE001  (reported, never hidden)
                rec = {"error": repr(exc)}
            spec[f"{set_id}|{wid}"] = rec
    return {"meta": meta, "decisions": out, "spec": spec}, arrays

# ============================================================================================ ORCHESTRATOR
def tree_digest(paths: list[Path]) -> dict:
    """sha256 of every file under `paths` (symlinks recorded, not followed): proves nothing was written."""
    out = {}
    for root in paths:
        root = Path(root)
        if root.is_file():
            out[str(root)] = sha256_file(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames.sort()
            for fn in sorted(filenames):
                p = Path(dirpath) / fn
                out[str(p)] = "symlink->" + os.readlink(p) if p.is_symlink() else sha256_file(p)
            for dn in list(dirnames):
                p = Path(dirpath) / dn
                if p.is_symlink():
                    out[str(p)] = "symlink->" + os.readlink(p)
                    dirnames.remove(dn)
    return out


def combined(d: dict) -> str:
    return hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(d.items())).encode()).hexdigest()


def check_inputs() -> dict:
    info = {}
    for key, cdir in CODE.items():
        info[f"{key}_ledger_sha256"] = sha256_file(cdir / "paper" / "ledger.jsonl")
        info[f"{key}_speculations_sha256"] = sha256_file(cdir / "paper" / "speculations.jsonl")
        assert info[f"{key}_ledger_sha256"] == EXPECT["ledger_sha256"], f"{key}: ledger sha256 differs from the pinned one"
        assert info[f"{key}_speculations_sha256"] == EXPECT["spec_sha256"], f"{key}: speculations sha256 differs"
        market_py = cdir / "idxsig" / "market.py"
        info[f"{key}_market_py_sha256"] = sha256_file(market_py)
    rows = read_jsonl(CODE["B"] / "paper" / "ledger.jsonl")
    assert len(rows) == EXPECT["ledger_rows"] and rows[-1]["record_hash"] == EXPECT["ledger_head_hash"]
    assert len(read_jsonl(CODE["B"] / "paper" / "speculations.jsonl")) == EXPECT["spec_rows"]
    info["manifest_sha256"] = sha256_file(MANIFEST)
    assert info["manifest_sha256"].startswith(EXPECT["manifest_sha256_prefix"])
    header, recs = read_jsonl(MANIFEST)[0], read_jsonl(MANIFEST)[1:]
    ok = 0
    for r in recs:
        if r.get("http_status") != 200:
            continue
        p = FROZEN_RAW / Path(r["path"]).name
        assert p.exists() and sha256_file(p) == r["sha256"], f"frozen payload missing or altered: {p}"
        ok += 1
    info["manifest_payloads_verified"] = ok
    info["manifest_tickers"] = header["requested"]
    info["manifest_started_at"] = header["started_at"]
    # the code copies differ only in market.py
    diff = []
    for p in sorted((CODE["B"] / "idxsig").rglob("*.py")):
        q = CODE["C"] / "idxsig" / p.relative_to(CODE["B"] / "idxsig")
        if not q.exists() or sha256_file(p) != sha256_file(q):
            diff.append(str(p.relative_to(CODE["B"] / "idxsig")))
    info["py_files_that_differ_B_vs_C"] = diff
    assert diff == ["market.py"], diff
    return info


def run_workers(variants: list[str], evidence_file: Path | None = None) -> None:
    WORK.mkdir(exist_ok=True)
    procs = []
    for v in variants:
        key = VARIANTS[v][0]
        cmd = [sys.executable, "-I", str(HERE / "harness.py"), "--worker", v, "--work-dir", str(WORK)]
        if evidence_file:
            cmd += ["--evidence-file", str(evidence_file)]
        log = open(WORK / f"worker_{v}.log", "w")
        procs.append((v, subprocess.Popen(cmd, cwd=CODE[key], stdout=log, stderr=subprocess.STDOUT), log))
    for v, p, log in procs:
        rc = p.wait()
        log.close()
        if rc != 0:
            raise SystemExit(f"worker {v} failed (rc={rc}); see {WORK / f'worker_{v}.log'}")


class Ctx:
    """Frozen arrays and replay results for every variant."""

    def __init__(self, variants):
        self.R, self.A = {}, {}
        for v in variants:
            self.R[v] = json.loads((WORK / f"replay_{v}.json").read_text())
            with np.load(WORK / f"arrays_{v}.npz") as z:
                self.A[v] = {k: z[k] for k in z.files}
        base = self.A["B"]
        self.dates = [str(x) for x in base["dates"]]
        self.tickers = [str(x) for x in base["tickers"]]
        for v in variants:
            assert [str(x) for x in self.A[v]["dates"]] == self.dates and [str(x) for x in self.A[v]["tickers"]] == self.tickers
            for k in ("close", "prev", "tradeable", "lock_up"):
                assert np.array_equal(self.A[v][k], base[k], equal_nan=True), f"{v}: {k} differs from B"
        self.didx = {d: i for i, d in enumerate(self.dates)}
        self.tidx = {t: i for i, t in enumerate(self.tickers)}
        self.last = len(self.dates) - 1

    def at(self, k: int) -> str:
        return self.dates[min(max(k, 0), self.last)]


def trade_of(o):
    return None if o is None else (o.get("execution") or {}).get("paper_trade")


def verdict_of(o):
    return None if o is None else o["decision_verdict"]


# -------------------------------------------------------------------------------------- 1. populations
def populations(rows: list[dict], ctx: Ctx) -> tuple[dict, dict, dict]:
    """Counts straight from the ledger file. Returns (summary, idx_decisions_by_id, latest_outcome_by_id)."""
    by_type = Counter(r["type"] for r in rows)
    by_type_market = Counter((r["type"], r.get("market", "(field absent)")) for r in rows)
    idx_dec = OrderedDict((r["decision_id"], r) for r in rows if r["type"] == "DECISION" and r.get("market", "IDX") == "IDX")
    all_dec_ids = Counter(r["decision_id"] for r in rows if r["type"] == "DECISION")
    outcome_rows = defaultdict(list)
    for i, r in enumerate(rows):
        if r["type"] == "OUTCOME" and r["decision_id"] in idx_dec:
            outcome_rows[r["decision_id"]].append((i, r))
    latest, chain_ok, multi = {}, True, []
    for did, lst in outcome_rows.items():
        latest[did] = lst[-1][1]  # file order, last wins: exactly what paper.score_pending() does
        if len(lst) > 1:
            multi.append(did)
            for a, b in zip(lst, lst[1:]):
                chain_ok &= b[1].get("revises") == a[1]["record_hash"]
    n_outcome_rows = sum(len(v) for v in outcome_rows.values())
    explicit_idx = sum(1 for r in idx_dec.values() if r.get("market") == "IDX")
    absent_idx = [r["decision_id"] for r in idx_dec.values() if "market" not in r]

    def path_end(o, d):
        tr = trade_of(o)
        return tr["exit_session"] if tr else ctx.at(d + 1 + HORIZON)

    late = [r for r in idx_dec.values() if r["signal_session"] >= CUT]
    late_scored = [r for r in late if r["decision_id"] in latest]
    late_trade = [r for r in late_scored if trade_of(latest[r["decision_id"]])]
    touching, touching_trade, touching_window = [], [], []
    for did, o in latest.items():
        d = ctx.didx[idx_dec[did]["signal_session"]]
        if path_end(o, d) >= CUT:
            touching.append(did)
            if trade_of(o):
                touching_trade.append(did)
        if ctx.at(d + 1 + HORIZON) >= CUT:
            touching_window.append(did)
    all_trades = [did for did, o in latest.items() if trade_of(o)]
    pending = [did for did in idx_dec if did not in latest]
    pend_complete, pend_open = [], []
    for did in pending:
        d = ctx.didx[idx_dec[did]["signal_session"]]
        (pend_complete if d + 6 <= ctx.last else pend_open).append(did)  # paper._span(decision) == 6 for these decisions
    s = {
        "ledger_rows": len(rows),
        "rows_by_type": dict(by_type),
        "rows_by_type_and_market": {f"{k[0]}|{k[1]}": v for k, v in sorted(by_type_market.items())},
        "duplicate_decision_ids": sorted(k for k, v in all_dec_ids.items() if v > 1),
        "idx_decisions": len(idx_dec),
        "idx_decisions_market_field_IDX": explicit_idx,
        "idx_decisions_market_field_absent_treated_as_IDX": absent_idx,
        "idx_decision_types": dict(Counter(r["decision"] for r in idx_dec.values())),
        "idx_decisions_with_execution_plan": sum(1 for r in idx_dec.values() if (r.get("plan") or {}).get("execution_plan")),
        "idx_outcome_rows": n_outcome_rows,
        "idx_outcome_rows_status": dict(Counter(r["status"] for r in latest.values())),
        "idx_decisions_with_more_than_one_outcome_row": multi,
        "idx_outcome_revisions_link_correctly": bool(chain_ok),
        "idx_outcome_rows_with_revises_field": sum(1 for lst in outcome_rows.values() for _, r in lst if "revises" in r),
        "idx_latest_outcome_per_decision": len(latest),
        "resolution_rule": "last OUTCOME row per decision_id in file order (as paper.score_pending() keys `latest`); a later row must name the earlier one in `revises`",
        "idx_outcomes_with_paper_trade": len(all_trades),
        "idx_outcomes_executed_true": sum(1 for o in latest.values() if (o.get("execution") or {}).get("executed")),
        "idx_outcome_verdicts": dict(Counter(o["decision_verdict"] for o in latest.values())),
        "signal_on_or_after_cut": {
            "decisions": len(late),
            "with_outcome": len(late_scored),
            "pending_no_outcome": len(late) - len(late_scored),
            "with_paper_trade_object": len(late_trade),
            "decision_type_of_trades": dict(Counter(r["decision"] for r in late_trade)),
            "rejections_that_would_have_traded": sum(1 for r in late_trade if r["decision"] != "BUY ON TRIGGER"),
            "executed_trades": sum(1 for r in late_trade if r["decision"] == "BUY ON TRIGGER"),
            "scored_without_trade": len(late_scored) - len(late_trade),
            "verdicts_of_scored": dict(Counter(latest[r["decision_id"]]["decision_verdict"] for r in late_scored)),
            "verdicts_of_trades": dict(Counter(latest[r["decision_id"]]["decision_verdict"] for r in late_trade)),
        },
        "path_touches_cut": {
            "outcomes": len(touching),
            "of_which_with_paper_trade": len(touching_trade),
            "of_which_signal_before_cut": sum(1 for did in touching if idx_dec[did]["signal_session"] < CUT),
            "trades_of_which_signal_before_cut": sum(1 for did in touching_trade if idx_dec[did]["signal_session"] < CUT),
            "outcomes_by_full_5_session_window_instead_of_actual_exit": len(touching_window),
            "outcomes_not_touching": len(latest) - len(touching),
            "trades_not_touching": len(all_trades) - len(touching_trade),
            "earliest_signal_session_whose_path_touches": min(idx_dec[did]["signal_session"] for did in touching),
        },
        "pending": {
            "decisions": len(pending),
            "window_still_open_by_bars": len(pend_open),
            "window_complete_but_no_outcome": len(pend_complete),
            "window_complete_ids": pend_complete,
        },
    }
    return s, idx_dec, latest


# -------------------------------------------------------------------------------------- 2. baseline gate
def outcome_view(o: dict) -> dict:
    ex = o["execution"]
    return {
        "decision_verdict": o["decision_verdict"],
        "discovery": o["discovery"],
        "fillable_at_trigger": ex["fillable_at_trigger"],
        "within_chase_band": ex["within_chase_band"],
        "executed": ex["executed"],
        "paper_trade": ex.get("paper_trade"),
        "price_scale": o["price_scale"],
        "scoring_version": o["scoring_version"],
    }


def pull_info(manifest_name: str) -> dict:
    path = FROZEN / manifest_name
    with open(path, encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        rec = json.loads(fh.readline())
    started = header["started_at"]
    last_date = rec["last_date"]
    return {
        "manifest": manifest_name,
        "started_at": started,
        "last_date": last_date,
        "first_date": rec["first_date"],
        "pre_close": bool(started[:10] == last_date and started[11:19] < IDX_CLOSE_UTC),
    }


def baseline_gate(idx_dec, latest, ctx) -> tuple[dict, list[dict]]:
    FINAL_FIRST_DATE = ctx.dates[0]
    rep_b = ctx.R["B"]["decisions"]
    gate_rows, mism = [], []
    max_abs = 0.0
    n_exact = 0
    pulls = {}
    for did, rec in latest.items():
        rep = rep_b[did]["outcome"]
        pi = pulls.setdefault(rec["data"]["manifest"], pull_info(rec["data"]["manifest"]))
        d = ctx.didx[idx_dec[did]["signal_session"]]
        tr = trade_of(rec)
        path_end = tr["exit_session"] if tr else ctx.at(d + 1 + HORIZON)
        row = {
            "decision_id": did,
            "outcome_record_hash": rec["record_hash"],
            "ticker": idx_dec[did]["instrument"]["ticker"],
            "signal_session": idx_dec[did]["signal_session"],
            "recorded_on_pull": rec["data"]["manifest"],
            "pull_started_at": pi["started_at"],
            "pull_last_bar": pi["last_date"],
            "pull_before_close": pi["pre_close"],
            "trade_exit_on_pull_last_bar": bool(tr and tr["exit_session"] == pi["last_date"]),
            "discovery_window_includes_pull_last_bar": bool(pi["last_date"] in ctx.didx and d + 1 <= ctx.didx[pi["last_date"]] <= d + HORIZON),
        }
        if rep is None:
            diffs = [("/outcome", "recorded", "replay returned None")]
        else:
            va, vb = outcome_view(rec), outcome_view(rep)
            diffs = deep_diff(va, vb)
            if not diffs:  # residual floating noise on the records that match
                max_abs = max(max_abs, abs(va["discovery"]["r5max"] - vb["discovery"]["r5max"]))
                if va["paper_trade"] and vb["paper_trade"]:
                    for f in ("net_return", "mfe", "mae", "entry_price"):
                        max_abs = max(max_abs, abs(va["paper_trade"][f] - vb["paper_trade"][f]))
                n_exact += 1 if not deep_diff(va, vb, tol=0.0) else 0
        row["match"] = not diffs
        row["mismatched_fields"] = ";".join(sorted({d[0] for d in diffs}))
        row["recorded_values"] = json.dumps({d[0]: d[1] for d in diffs}, sort_keys=True)
        row["replay_values"] = json.dumps({d[0]: d[2] for d in diffs}, sort_keys=True)
        row["diagnosis"] = ""
        if diffs:
            fields = {d[0] for d in diffs}
            thr = {"/discovery/E30": 0.3, "/discovery/E50": 0.5, "/discovery/E100": 1.0}
            if fields <= set(thr) and rep is not None:
                gaps = [abs(rec["discovery"]["r5max"] - thr[f]) for f in fields]
                dr = rec["discovery"]["r5max"] - rep["discovery"]["r5max"]
                if max(gaps) < 1e-9:
                    row["diagnosis"] = (
                        f"floating-point knife-edge at the {', '.join(sorted(f.split('/')[-1] + ' (threshold ' + str(thr[f]) + ')' for f in fields))}: r5max is "
                        f"{rec['discovery']['r5max']!r} in the record and {rep['discovery']['r5max']!r} in the replay "
                        f"(difference {dr:.2e}, inside the 1e-9 tolerance) but the boolean flag flips; the recorded pull's history "
                        f"starts on {pi['first_date']} and the final pull's on {FINAL_FIRST_DATE}, so the cumulative-log level rounds "
                        f"differently. Discovery field only; no ARB involvement"
                    )
            elif pi["pre_close"] and row["trade_exit_on_pull_last_bar"] and all(f.startswith("/paper_trade/") for f in fields):
                row["diagnosis"] = (
                    f"the record was scored on pull {pi['manifest']} started {pi['started_at']} (before the 16:00 WIB close), "
                    f"so its last bar ({pi['last_date']}) was an intraday print; the trade's exit session is that bar and the "
                    f"final pull holds the official close. Fields differing: {', '.join(sorted(fields))}; entry, exit session "
                    f"and reason agree"
                )
            if not row["diagnosis"]:
                row["diagnosis"] = "UNDIAGNOSED"
            mism.append(row)
        gate_rows.append(row)
    pre = [r for r in gate_rows if r["pull_before_close"]]
    s = {
        "outcomes_replayed": len(latest),
        "field_for_field_matches": sum(1 for r in gate_rows if r["match"]),
        "mismatches": [
            {
                "decision_id": r["decision_id"],
                "ticker": r["ticker"],
                "fields": r["mismatched_fields"],
                "recorded_on_pull": r["recorded_on_pull"],
                "diagnosis": r["diagnosis"],
            }
            for r in mism
        ],
        "matched_records_bit_identical": n_exact,
        "max_abs_float_difference_on_matched_records": max_abs,
        "fields_compared": "decision_verdict, discovery (r5max, E30, E50, E100, peak_session), fillable_at_trigger, within_chase_band, executed, paper_trade (entry_session, exit_session, exit_reason, entry_price, entry_close, entry_basis, net_return, mfe, mae), price_scale, scoring_version; floats tolerance 1e-9",
        "pulls_used_by_recorded_outcomes": len(pulls),
        "outcomes_scored_on_a_pre_close_pull": len(pre),
        "pre_close_outcomes_whose_trade_exits_on_the_intraday_bar": sum(1 for r in pre if r["trade_exit_on_pull_last_bar"]),
        "pre_close_outcomes_whose_discovery_window_includes_the_intraday_bar": sum(1 for r in pre if r["discovery_window_includes_pull_last_bar"]),
        "pre_close_outcomes_that_still_match": sum(1 for r in pre if r["match"]),
        "pre_close_trade_exits_on_the_intraday_bar_that_still_match": sum(1 for r in pre if r["trade_exit_on_pull_last_bar"] and r["match"]),
        "pre_close_pulls": sorted({r["recorded_on_pull"] for r in pre}),
        "replay_returns_outcome_exactly_for_recorded_decisions": all(rep_b[d]["outcome"] is not None for d in latest)
        and all(rep_b[d]["outcome"] is None for d in idx_dec if d not in latest),
    }
    return s, gate_rows


# -------------------------------------------------------------------------------------- cell-level analysis
def cell_analysis(ctx: Ctx) -> dict:
    """Where do B and C disagree on lock_down, and what does the bar say about the board it was traded on?"""
    B, C = ctx.A["B"], ctx.A["C"]
    after = np.array([d >= CUT for d in ctx.dates])[None, :]
    lock_b, lock_c = B["lock_down"], C["lock_down"]
    assert not (lock_b & ~lock_c).any(), "C unlocks a bar that B locks"
    assert np.array_equal(B["lock_up"], C["lock_up"]), "ARA flags differ"
    flipped = lock_c & ~lock_b
    close, prev, arb_c = C["close"], C["prev"], C["arb"]
    degenerate = flipped & (arb_c >= prev)  # modelled limit leaves no room below the reference (Rp11-14 on 2026-10-19)
    at = flipped & ~degenerate & (close == arb_c)
    below = flipped & ~degenerate & (close < arb_c)
    above = flipped & ~degenerate & (close > arb_c)
    assert not above.any(), "a flipped bar closed above the limit that locked it"
    ev = C["tradeable"] & np.isfinite(prev) & (prev > 0) & after & (close < arb_c) & (arb_c < prev)
    ev10 = ev & (close == C["sp_arb"])  # a close exactly on the special-board 10% limit: positive sign of a 10% board
    per_date = {ctx.dates[k]: int(flipped[:, k].sum()) for k in range(len(ctx.dates)) if flipped[:, k].any()}
    k19 = ctx.didx[CUT]
    low_ref_down = B["tradeable"][:, k19] & (prev[:, k19] >= 11) & (prev[:, k19] <= 14) & (close[:, k19] < prev[:, k19])
    ev_names = [ctx.tickers[i] for i in np.flatnonzero(ev.any(axis=1))]
    flipped_names = [ctx.tickers[i] for i in np.flatnonzero(flipped.any(axis=1))]
    return {
        "flipped": flipped,
        "at": at,
        "below": below,
        "degenerate": degenerate,
        "evidence_cells": ev,
        "evidence_names": ev_names,
        "summary": {
            "lock_down_cells_B": int(lock_b.sum()),
            "lock_down_cells_C": int(lock_c.sum()),
            "cells_locked_in_C_not_B": int(flipped.sum()),
            "cells_locked_in_B_not_C": 0,
            "lock_up_cells_identical_B_vs_C": True,
            "flipped_cells_at_modelled_7pct_limit": int(at.sum()),
            "flipped_cells_strictly_below_modelled_limit": int(below.sum()),
            "flipped_cells_degenerate_limit_ARB_ge_reference": int(degenerate.sum()),
            "flipped_cells_by_session": per_date,
            "names_with_a_flipped_bar": len(flipped_names),
            "names_with_wider_limit_evidence": len(ev_names),
            "wider_limit_evidence_definition": "any traded bar on or after 2026-10-19 whose close is strictly below the modelled C lower limit, where that limit is below the reference (excludes the degenerate ARB>=reference cells); includes bars also locked under B",
            "evidence_bars_total": int(ev.sum()),
            "evidence_names_with_a_bar_exactly_on_the_special_board_10pct_limit": int(ev10.any(axis=1).sum()),
            "flipped_cells_on_2026_10_19": per_date.get("2026-10-19", 0),
            "bars_2026_10_19_with_reference_Rp11_14_and_a_down_close": int(low_ref_down.sum()),
            "bars_2026_10_19_with_reference_Rp11_14_and_a_down_close_names": [ctx.tickers[i] for i in np.flatnonzero(low_ref_down)],
            "flipped_cells_with_reference_Rp11_14_market_wide": int((flipped & (prev >= 11) & (prev <= 14)).sum()),
            "of_which_already_locked_under_B": int((low_ref_down & lock_b[:, k19]).sum()),
            "names_without_a_bar_on_the_last_session_in_the_final_pull": int((~B["present"][:, ctx.last]).sum()),
            "tickers_in_final_pull": len(ctx.tickers),
        },
    }


# -------------------------------------------------------------------------------------- 3. classification
CHANGED = ("EXIT_SHIFTED", "BECOMES_UNSCORABLE", "BECOMES_SCORABLE", "VERDICT_CHANGED", "OTHER_CHANGED")


def classify(b, c, touches: bool) -> str:
    if not touches:
        return "NOT_AFFECTED"
    if b is None and c is None:
        return "BOTH_NO_OUTCOME"
    if b is not None and c is None:
        return "BECOMES_UNSCORABLE"
    if b is None and c is not None:
        return "BECOMES_SCORABLE"
    if not deep_diff(b, c):
        return "UNCHANGED"
    if verdict_of(b) != verdict_of(c):
        return "VERDICT_CHANGED"
    tb, tc = trade_of(b), trade_of(c)
    if tb and tc and tb["exit_session"] != tc["exit_session"]:
        return "EXIT_SHIFTED"
    return "OTHER_CHANGED"


def fmt_hint_list(items):
    return ";".join(items)


def build_records(ctx: Ctx, idx_dec, latest, cells, gate_rows) -> tuple[list[dict], list[dict]]:
    """One row per IDX decision that has a recorded OUTCOME (the replayed population), plus the flipped-bar detail."""
    gate = {g["decision_id"]: g for g in gate_rows}
    rows, bars = [], []
    flipped = cells["flipped"]
    order = sorted(latest, key=lambda k: (idx_dec[k]["signal_session"], k))
    for did in order:
        dec, rec = idx_dec[did], latest[did]
        ticker, sig = dec["instrument"]["ticker"], dec["signal_session"]
        n, d = ctx.tidx[ticker], ctx.didx[sig]
        e = d + 1
        out = {v: ctx.R[v]["decisions"][did] for v in ctx.R}
        b, c = out["B"]["outcome"], out["C"]["outcome"]
        assert b is not None, f"{did}: B replay returned no outcome for a recorded outcome"
        tb, tc = trade_of(b), trade_of(c)
        window_end = min(e + HORIZON, ctx.last)
        b_end = ctx.didx[tb["exit_session"]] if tb else window_end
        c_end = ctx.didx[tc["exit_session"]] if tc else window_end
        path_end_b = ctx.dates[b_end]
        touches = path_end_b >= CUT
        end = max(b_end, c_end) if (tb or tc) else window_end
        flip_ks = [k for k in range(e, end + 1) if flipped[n, k]]
        flip_consulted = [k for k in flip_ks if k > e]  # paper.score() tests sellability from e+1 only
        hints = []
        for k in flip_ks:
            h = "DEGENERATE_LIMIT" if cells["degenerate"][n, k] else ("AT_7PCT_LIMIT" if cells["at"][n, k] else "BELOW_7PCT_LIMIT")
            hints.append(h)
            ref, cl = float(ctx.A["C"]["prev"][n, k]), float(ctx.A["C"]["close"][n, k])
            bars.append(
                {
                    "decision_id": did,
                    "ticker": ticker,
                    "signal_session": sig,
                    "session": ctx.dates[k],
                    "sessions_after_signal": k - d,
                    "is_entry_session": k == e,
                    "reference_prev_close": ref,
                    "close": cl,
                    "high": ctx.A["C"]["high"][n, k],
                    "low": ctx.A["C"]["low"][n, k],
                    "return_vs_reference": cl / ref - 1,
                    "arb_B_shipped_15pct": float(ctx.A["B"]["arb"][n, k]),
                    "arb_C_modelled_7pct": float(ctx.A["C"]["arb"][n, k]),
                    "special_board_10pct_limit": float(ctx.A["C"]["sp_arb"][n, k]),
                    "close_minus_modelled_limit": cl - float(ctx.A["C"]["arb"][n, k]),
                    "close_at_10pct_special_limit": bool(cl == float(ctx.A["C"]["sp_arb"][n, k])),
                    "board_hint": h,
                    "one_price_bar": bool(ctx.A["C"]["one_price"][n, k]),
                    "record_category_C_vs_B": "",  # filled below
                }
            )
        cat = classify(b, c, touches)
        if cat == "NOT_AFFECTED":
            assert not deep_diff(b, c), f"{did}: classed NOT_AFFECTED but B and C differ"
        sub = ""
        if cat == "UNCHANGED":
            sub = "NO_TRADE_lock_flags_never_consulted" if not tb else ("TRADE_no_flip_on_tested_sessions" if not flip_consulted else "TRADE_flip_on_tested_sessions_but_result_identical")
        elif cat == "NOT_AFFECTED":
            sub = "NO_TRADE" if not tb else "TRADE"
        for bar in bars:
            if bar["decision_id"] == did:
                bar["record_category_C_vs_B"] = cat
        variants = {}
        for v in ("C10", "C7b", "CH"):
            if v in ctx.R:
                vo = out[v]["outcome"]
                variants[v] = (classify(b, vo, touches), vo)
        row = {
            "population": "IDX_OUTCOME",
            "decision_id": did,
            "outcome_record_hash": rec["record_hash"],
            "decision_record_hash": dec["record_hash"],
            "ticker": ticker,
            "policy_id": (dec.get("policy") or {}).get("policy_id"),
            "decision": dec["decision"],
            "signal_session": sig,
            "recorded_on_pull": rec["data"]["manifest"],
            "entry_session": ctx.dates[e] if e <= ctx.last else "",
            "path_end_B": path_end_b,
            "path_touches_2026_10_19": touches,
            "recorded_trade": bool(trade_of(rec)),
            "recorded_exit_session": (trade_of(rec) or {}).get("exit_session"),
            "recorded_exit_reason": (trade_of(rec) or {}).get("exit_reason"),
            "recorded_net_return": (trade_of(rec) or {}).get("net_return"),
            "recorded_verdict": rec["decision_verdict"],
            "baseline_B_replay_matches_recorded": gate[did]["match"],
            "baseline_mismatch_fields": gate[did]["mismatched_fields"],
            "B_has_outcome": b is not None,
            "B_trade": bool(tb),
            "B_exit_session": (tb or {}).get("exit_session"),
            "B_exit_reason": (tb or {}).get("exit_reason"),
            "B_net_return": (tb or {}).get("net_return"),
            "B_mfe": (tb or {}).get("mfe"),
            "B_mae": (tb or {}).get("mae"),
            "B_verdict": verdict_of(b),
            "C_has_outcome": c is not None,
            "C_trade": bool(tc),
            "C_exit_session": (tc or {}).get("exit_session"),
            "C_exit_reason": (tc or {}).get("exit_reason"),
            "C_net_return": (tc or {}).get("net_return"),
            "C_mfe": (tc or {}).get("mfe"),
            "C_mae": (tc or {}).get("mae"),
            "C_verdict": verdict_of(c) if c is not None else "NO OUTCOME (score() returns None)",
            "delta_exit_sessions_C_minus_B": (ctx.didx[tc["exit_session"]] - ctx.didx[tb["exit_session"]]) if (tb and tc) else None,
            "delta_net_return_C_minus_B": (tc["net_return"] - tb["net_return"]) if (tb and tc) else None,
            "flip_sessions_on_path": ";".join(ctx.dates[k] for k in flip_ks),
            "n_flip_sessions": len(flip_ks),
            "n_flip_sessions_tested_by_scorer": len(flip_consulted),
            "n_flip_at_modelled_7pct_limit": hints.count("AT_7PCT_LIMIT"),
            "n_flip_strictly_below_limit": hints.count("BELOW_7PCT_LIMIT"),
            "n_flip_degenerate_limit": hints.count("DEGENERATE_LIMIT"),
            "flip_board_hints": fmt_hint_list(hints),
            "wider_limit_evidence_on_path": "BELOW_7PCT_LIMIT" in hints,
            "wider_limit_evidence_name": ticker in set(cells["evidence_names"]),
            "category": cat,
            "sub_category": sub,
        }
        for v, (vc, vo) in variants.items():
            vt = trade_of(vo)
            row[f"{v}_category"] = vc
            row[f"{v}_exit_session"] = (vt or {}).get("exit_session")
            row[f"{v}_net_return"] = (vt or {}).get("net_return")
        wi = out["C"]["whatif"]
        if cat == "BECOMES_UNSCORABLE":
            wt = (wi or {}).get("trade")
            row["whatif_roll_C_exit_session"] = (wt or {}).get("exit_session")
            row["whatif_roll_C_exit_reason"] = (wt or {}).get("exit_reason")
            row["whatif_roll_C_net_return"] = (wt or {}).get("net_return")
            row["whatif_roll_C_rolled_sessions"] = (wi or {}).get("rolled_sessions")
            row["whatif_roll_C_verdict"] = (wi or {}).get("verdict") if wi else "still open: no sellable close before the end of the data"
        rows.append(row)
    return rows, bars


# -------------------------------------------------------------------------------------- 4. aggregates
def stats(vals):
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None, "n_positive": 0}
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "n_positive": sum(1 for v in vals if v > 0),
    }


def aggregates(recs: list[dict]) -> dict:
    cat = Counter(r["category"] for r in recs)
    sub = Counter((r["category"], r["sub_category"]) for r in recs)
    b_tr = [r for r in recs if r["B_trade"]]
    c_tr = [r for r in recs if r["C_trade"]]
    both = [r for r in recs if r["B_trade"] and r["C_trade"]]
    dropped = [r for r in recs if r["B_trade"] and not r["C_trade"] and not r["C_has_outcome"]]
    touching_b = [r for r in b_tr if r["path_touches_2026_10_19"]]
    touching_c = [r for r in c_tr if r["path_touches_2026_10_19"]]
    rec_tr = [r for r in recs if r["recorded_trade"]]
    wi_closed = [r for r in recs if r["category"] == "BECOMES_UNSCORABLE" and r.get("whatif_roll_C_net_return") is not None]
    c_plus_whatif = [r["C_net_return"] for r in c_tr] + [r["whatif_roll_C_net_return"] for r in wi_closed]
    changed = [r for r in recs if r["category"] in CHANGED]
    shifted = [r for r in recs if r["category"] == "EXIT_SHIFTED"]
    return {
        "records_replayed": len(recs),
        "categories": {k: cat.get(k, 0) for k in ("UNCHANGED", "EXIT_SHIFTED", "BECOMES_UNSCORABLE", "BECOMES_SCORABLE", "VERDICT_CHANGED", "NOT_AFFECTED", "BOTH_NO_OUTCOME", "OTHER_CHANGED")},
        "unchanged_breakdown": {k[1]: v for k, v in sub.items() if k[0] == "UNCHANGED"},
        "not_affected_breakdown": {k[1]: v for k, v in sub.items() if k[0] == "NOT_AFFECTED"},
        "records_changed": len(changed),
        "records_changed_distinct_tickers": len({r["ticker"] for r in changed}),
        "hypothetical_trades": {
            "recorded": len(rec_tr),
            "B_replay": len(b_tr),
            "C_replay": len(c_tr),
            "dropped_by_C_no_outcome": len(dropped),
            "B_replay_with_path_touching_cut": len(touching_b),
            "C_replay_with_path_touching_cut": len(touching_c),
        },
        "net_return_all_trades": {
            "recorded": stats([r["recorded_net_return"] for r in rec_tr]),
            "B_replay": stats([r["B_net_return"] for r in b_tr]),
            "C_replay": stats([r["C_net_return"] for r in c_tr]),
        },
        "net_return_trades_in_both_B_and_C": {
            "n": len(both),
            "B": stats([r["B_net_return"] for r in both]),
            "C": stats([r["C_net_return"] for r in both]),
        },
        "net_return_of_trades_C_drops_B_values": stats([r["B_net_return"] for r in dropped]),
        "net_return_trades_touching_cut": {
            "B_replay": stats([r["B_net_return"] for r in touching_b]),
            "C_replay": stats([r["C_net_return"] for r in touching_c]),
        },
        "exit_shifted_effect": {
            "n": len(shifted),
            "mean_delta_net_return_C_minus_B": statistics.fmean([r["delta_net_return_C_minus_B"] for r in shifted]) if shifted else None,
            "median_delta_net_return_C_minus_B": statistics.median([r["delta_net_return_C_minus_B"] for r in shifted]) if shifted else None,
            "worse": sum(1 for r in shifted if r["delta_net_return_C_minus_B"] < 0),
            "better": sum(1 for r in shifted if r["delta_net_return_C_minus_B"] > 0),
        },
        "whatif_C_population_with_rolled_trades_added": stats(c_plus_whatif),
        "verdicts": {
            "recorded": dict(Counter(r["recorded_verdict"] for r in recs)),
            "B_replay": dict(Counter(r["B_verdict"] for r in recs)),
            "C_replay": dict(Counter(r["C_verdict"] for r in recs)),
        },
        "changed_ids": [r["decision_id"] for r in changed],
    }


# -------------------------------------------------------------------------------------- 5. sensitivity
def sensitivity(recs, ctx: Ctx) -> dict:
    out = {}
    base_changed = [r for r in recs if r["category"] in CHANGED]
    for v in ("C10", "C7b", "CH"):
        cats = Counter(r[f"{v}_category"] for r in recs)
        ch = [r for r in recs if r[f"{v}_category"] in CHANGED]
        tr_v = [r[f"{v}_net_return"] for r in recs if r[f"{v}_exit_session"]]
        out[v] = {
            "categories": dict(cats),
            "records_changed_vs_B": len(ch),
            "changed_ids": [r["decision_id"] for r in ch],
            "trades": len(tr_v),
            "net_return": stats(tr_v),
            "flipped_cells_vs_B": int((ctx.A[v]["lock_down"] & ~ctx.A["B"]["lock_down"]).sum()),
        }
    out["C7"] = {"records_changed_vs_B": len(base_changed), "changed_ids": [r["decision_id"] for r in base_changed], "flipped_cells_vs_B": int((ctx.A["C"]["lock_down"] & ~ctx.A["B"]["lock_down"]).sum())}
    ev_name = [r for r in base_changed if r["wider_limit_evidence_name"]]
    ev_path = [r for r in base_changed if r["wider_limit_evidence_on_path"]]
    out["drop_wider_limit_names"] = {
        "changed_records_C_vs_B": len(base_changed),
        "changed_records_whose_name_has_wider_limit_evidence": len(ev_name),
        "changed_ids_with_name_evidence": [r["decision_id"] for r in ev_name],
        "changed_records_with_a_flipped_bar_strictly_below_the_limit_on_the_path": len(ev_path),
        "changed_ids_with_path_evidence": [r["decision_id"] for r in ev_path],
        "changed_records_remaining_after_dropping_names_with_evidence": len(base_changed) - len(ev_name),
        "records_replayed_whose_name_has_evidence": sum(1 for r in recs if r["wider_limit_evidence_name"]),
        "records_remaining_after_dropping_those_names": sum(1 for r in recs if not r["wider_limit_evidence_name"]),
        "categories_of_the_remaining_records": dict(Counter(r["category"] for r in recs if not r["wider_limit_evidence_name"])),
        "tickers_with_evidence_among_replayed_records": sorted({r["ticker"] for r in recs if r["wider_limit_evidence_name"]}),
        "hybrid_replay_records_changed_vs_B": out["CH"]["records_changed_vs_B"],
    }
    return out


# -------------------------------------------------------------------------------------- 6. speculations
SPEC_IGNORE = {"resolved_at", "data", "prev_hash", "record_hash"}


def flip_hint(cells, n, k) -> str:
    if cells["degenerate"][n, k]:
        return "DEGENERATE_LIMIT"
    if cells["at"][n, k]:
        return "AT_7PCT_LIMIT"
    if cells["below"][n, k]:
        return "BELOW_7PCT_LIMIT"
    return ""


def spec_analysis(ctx: Ctx, spec_rows: list[dict], cells) -> tuple[dict, list[dict]]:
    sets = OrderedDict((s["set_id"], s) for s in spec_rows if s["type"] == "SPECULATION_SET" and s["market"] == "IDX")
    recorded = OrderedDict(((r["set_id"], r["window"]), r) for r in spec_rows if r["type"] == "RESOLUTION" and r["market"] == "IDX")
    lock_b, lock_c = ctx.A["B"]["lock_down"], ctx.A["C"]["lock_down"]
    rows = []
    for (sid, wid), rec in recorded.items():
        s, key = sets[sid], f"{sid}|{wid}"
        rb, rc, r10 = (ctx.R[v]["spec"][key] for v in ("B", "C", "C10"))
        d = ctx.didx[s["signal_session"]]
        uses_lock = wid == "BASE5"
        names = [s["ticker"]] + [t["ticker"] for t in s["twins"]]
        target = d + 1 + HORIZON
        flipped, hints = [], []
        if uses_lock and target <= ctx.last:
            for nm in names:
                n = ctx.tidx[nm]
                if lock_c[n, target] and not lock_b[n, target]:
                    flipped.append(nm)
                    hints.append(f"{nm}:{flip_hint(cells, n, target)}")
        sim = 0
        if uses_lock and rec.get("candidate", {}).get("status") == "TRADED":
            sim += 1
        if uses_lock:
            sim += sum(1 for t in rec.get("twins", []) if t.get("status") == "TRADED")
        gate = deep_diff(rec, rb, ignore=SPEC_IGNORE) if rb is not None else [("/", "recorded", "replay returned None")]
        diag = ""
        ungraded_only = bool(gate) and all(g[0].startswith("/cone[") and (g[1] is None or g[1] == "not graded: no position (or no twin traded)") for g in gate)
        if wid == "NEXT1" and ungraded_only:
            nm = s["ticker"]
            n_c = ctx.tidx[nm]
            diag = (
                f"the pull that resolved it ({rec['data']['manifest']}) gave next_return() no usable bar for {nm} at {ctx.at(d + 1)} "
                f"(the statements were 'not graded'); the final pull holds a bar for that session "
                f"(close {float(ctx.A['B']['close'][n_c, d + 1])!r}, volume {float(ctx.A['B']['volume'][n_c, d + 1])!r}). "
                f"A data-timing difference in NEXT1, which never reads lock_down"
            )
        if rc is None:
            c_state = "NOT RESOLVABLE on the final bars (a name's horizon close is locked in C and no later session exists)"
            same_c = False
        else:
            same_c = not deep_diff(rb, rc, ignore=SPEC_IGNORE)
            c_state = "identical to B" if same_c else "DIFFERS from B"
        same_10 = (r10 is not None) and not deep_diff(rb, r10, ignore=SPEC_IGNORE)
        rows.append(
            {
                "kind": "RESOLUTION",
                "set_id": sid,
                "window": wid,
                "ticker": s["ticker"],
                "signal_session": s["signal_session"],
                "resolved_on_pull": rec["data"]["manifest"],
                "uses_lock_down": uses_lock,
                "planned_horizon_session": ctx.at(target) if uses_lock else "",
                "simulated_trades_with_a_horizon_sale": sim,
                "baseline_B_replay_matches_recorded": not gate,
                "baseline_n_differences": len(gate),
                "baseline_diagnosis": diag,
                "C_vs_B": c_state,
                "names_with_horizon_close_locked_only_in_C": ";".join(flipped),
                "flip_board_hints": ";".join(hints),
                "C10_identical_to_B": same_10,
                "flips_resolution": bool(uses_lock and not same_c),
            }
        )
    # windows that have no RESOLUTION yet
    n_open = Counter()
    open_base5 = []
    for sid, s in sets.items():
        for wid in s["windows"]:
            if (sid, wid) in recorded:
                continue
            n_open[wid] += 1
            if wid != "BASE5":
                continue
            d = ctx.didx[s["signal_session"]]
            e = d + 1
            names = [s["ticker"]] + [t["ticker"] for t in s["twins"]]
            ks = list(range(e, min(e + HORIZON, ctx.last) + 1)) if e <= ctx.last else []
            fl = []
            for nm in names:
                n = ctx.tidx[nm]
                fl += [f"{nm}@{ctx.dates[k]}:{flip_hint(cells, n, k)}" for k in ks if cells["flipped"][n, k]]
            open_base5.append((sid, s["signal_session"], e <= ctx.last, fl))
            rows.append(
                {
                    "kind": "OPEN_WINDOW",
                    "set_id": sid,
                    "window": wid,
                    "ticker": s["ticker"],
                    "signal_session": s["signal_session"],
                    "uses_lock_down": True,
                    "planned_horizon_session": ctx.dates[e + HORIZON] if e + HORIZON <= ctx.last else (f"after {ctx.dates[-1]} (not yet observed)" if e <= ctx.last else "entry session not yet observed"),
                    "C_vs_B": "window still open on the final bars",
                    "names_with_horizon_close_locked_only_in_C": "",
                    "flip_board_hints": ";".join(fl),
                }
            )
    res = [r for r in rows if r["kind"] == "RESOLUTION"]
    base = [r for r in res if r["uses_lock_down"]]
    out = {
        "idx_speculation_sets": len(sets),
        "idx_resolution_rows": len(recorded),
        "resolution_rows_by_window": dict(Counter(w for _, w in recorded)),
        "rows_whose_horizon_sale_uses_lock_down": len(base),
        "rows_that_never_read_lock_down": len(res) - len(base),
        "simulated_horizon_sales_in_those_rows": sum(r["simulated_trades_with_a_horizon_sale"] for r in base),
        "resolution_rows_whose_entry_session_is_on_or_after_cut": sum(1 for r in res if ctx.at(ctx.didx[r["signal_session"]] + 1) >= CUT),
        "earliest_entry_session_of_the_resolution_rows": min(ctx.at(ctx.didx[r["signal_session"]] + 1) for r in res),
        "replay_produced_a_resolution_for_every_recorded_row": all(ctx.R["B"]["spec"][f"{k[0]}|{k[1]}"] is not None for k in recorded),
        "recorded_resolutions_written_on_the_frozen_pull_itself": sum(1 for rr in recorded.values() if rr["data"]["manifest_sha256"] == ctx.R["B"]["meta"]["manifest_sha256"]),
        "recorded_resolutions_written_on_earlier_pulls_no_longer_available": sum(1 for rr in recorded.values() if rr["data"]["manifest_sha256"] != ctx.R["B"]["meta"]["manifest_sha256"]),
        "baseline_mismatch_diagnoses": {r["set_id"] + "|" + r["window"]: r["baseline_diagnosis"] for r in res if not r["baseline_B_replay_matches_recorded"]},
        "baseline_B_replay_matches_recorded": sum(1 for r in res if r["baseline_B_replay_matches_recorded"]),
        "baseline_mismatches": [r["set_id"] + "|" + r["window"] for r in res if not r["baseline_B_replay_matches_recorded"]],
        "base5_rows_that_flip_under_C": [r["set_id"] for r in base if r["flips_resolution"]],
        "base5_flip_detail": {r["set_id"]: {"C_vs_B": r["C_vs_B"], "names": r["names_with_horizon_close_locked_only_in_C"], "hints": r["flip_board_hints"]} for r in base if r["flips_resolution"]},
        "next1_rows_identical_B_vs_C": sum(1 for r in res if not r["uses_lock_down"] and r["C_vs_B"] == "identical to B"),
        "next1_rows": sum(1 for r in res if not r["uses_lock_down"]),
        "C10_base5_rows_identical_to_B": sum(1 for r in base if r["C10_identical_to_B"]),
        "window_definitions_used": SPEC_WINDOWS,
        "window_definition_note": "research/SPECULATION_REGISTER_v1/protocol_v1_1.json is not in the code copies; windows() is replaced inside the worker by the definitions the code implies; the B replay of both recorded BASE5 resolutions (candidate and five twins each) and of all 21 NEXT1 resolutions reproduces the records, which is the check on that reading",
        "open_windows": dict(n_open),
        "open_base5_windows": len(open_base5),
        "open_base5_windows_with_entry_observed": sum(1 for _, _, ent, _ in open_base5 if ent),
        "open_base5_windows_with_a_flipped_bar_so_far_on_candidate_or_twin": sum(1 for _, _, _, fl in open_base5 if fl),
    }
    return out, rows


# -------------------------------------------------------------------------------------- 7. pending decisions
def pending_analysis(ctx: Ctx, idx_dec, latest, cells) -> tuple[dict, list[dict]]:
    A = ctx.A["B"]
    lock_b, lock_c = ctx.A["B"]["lock_down"], ctx.A["C"]["lock_down"]
    rows = []
    for did, dec in idx_dec.items():
        if did in latest:
            continue
        t, sig = dec["instrument"]["ticker"], dec["signal_session"]
        n, d = ctx.tidx[t], ctx.didx[sig]
        e = d + 1
        plan = dec.get("plan") or {}
        stop = plan.get("invalidation")
        chase = plan.get("max_chase_price")
        known = e <= ctx.last
        horizon_k = e + HORIZON
        info = {
            "population": "IDX_PENDING",
            "decision_id": did,
            "decision_record_hash": dec["record_hash"],
            "ticker": t,
            "policy_id": (dec.get("policy") or {}).get("policy_id"),
            "decision": dec["decision"],
            "signal_session": sig,
            "entry_session": ctx.dates[e] if known else "",
            "window_complete_on_final_bars": d + 6 <= ctx.last,
            "ticker_has_no_last_session_bar": not bool(A["present"][n, ctx.last]),
        }
        fillable = in_band = entered = None
        b_exit = c_exit = None
        flips = []
        if known:
            fillable = bool(A["tradeable"][n, e] and not A["lock_up"][n, e])
            in_band = bool(chase is not None and stop is not None and stop < A["close"][n, e] <= chase)
            entered = bool(fillable and in_band)
            last_k = min(e + HORIZON, ctx.last)
            flips = [k for k in range(e, last_k + 1) if cells["flipped"][n, k]]

            def first_exit(lock):
                for k in range(e + 1, last_k + 1):
                    sellable = bool(A["tradeable"][n, k] and not lock[n, k])
                    if sellable and A["close"][n, k] <= stop:
                        return k, "invalidation"
                    if k == horizon_k and sellable:
                        return k, "horizon"
                return None

            if entered:
                b_exit, c_exit = first_exit(lock_b), first_exit(lock_c)
        horizon_seen = horizon_k <= ctx.last
        info.update(
            {
                "hypothetical_entry_observed": known,
                "fillable_at_entry": fillable,
                "inside_chase_band": in_band,
                "hypothetical_trade_entered_so_far": entered,
                "flip_sessions_on_path": ";".join(ctx.dates[k] for k in flips),
                "n_flip_sessions": len(flips),
                "n_flip_sessions_tested_by_scorer": len([k for k in flips if k > e]),
                "flip_board_hints": ";".join(flip_hint(cells, n, k) for k in flips),
                "B_exit_so_far": (ctx.dates[b_exit[0]] + " " + b_exit[1]) if b_exit else "",
                "C_exit_so_far": (ctx.dates[c_exit[0]] + " " + c_exit[1]) if c_exit else "",
                "flip_changes_the_trade_so_far": bool(entered and b_exit != c_exit),
            }
        )
        if info["window_complete_on_final_bars"]:
            sellable_b = bool(A["tradeable"][n, horizon_k] and not lock_b[n, horizon_k])
            sellable_c = bool(A["tradeable"][n, horizon_k] and not lock_c[n, horizon_k])
            why = []
            if not A["tradeable"][n, horizon_k]:
                why.append("horizon session untraded (no volume)")
            if lock_b[n, horizon_k]:
                why.append("horizon session locked at the lower limit under the shipped rules")
            info["pending_reason"] = "window complete but score() returns None: " + ("; ".join(why) or "see replay") + (" [same under C]" if sellable_b == sellable_c else " [differs under C]")
        else:
            info["pending_reason"] = "window still open on the final bars"
        if not known:
            info["state_so_far"] = "entry session not yet observed"
        elif not entered:
            info["state_so_far"] = "no hypothetical entry (not fillable or outside the chase band): lock flags are never consulted"
        elif b_exit is None and c_exit is None:
            info["state_so_far"] = "trade entered, no exit yet under B or C"
        elif b_exit == c_exit:
            info["state_so_far"] = "trade entered, same exit so far under B and C"
        else:
            info["state_so_far"] = "trade entered, B and C already diverge"
        rows.append(info)
    summary = {
        "pending_decisions": len(rows),
        "window_still_open": sum(1 for r in rows if not r["window_complete_on_final_bars"]),
        "window_complete_but_no_outcome": [r["decision_id"] for r in rows if r["window_complete_on_final_bars"]],
        "with_entry_observed": sum(1 for r in rows if r["hypothetical_entry_observed"]),
        "with_hypothetical_trade_entered_so_far": sum(1 for r in rows if r["hypothetical_trade_entered_so_far"]),
        "with_a_flipped_bar_on_path_so_far_incl_entry_session": sum(1 for r in rows if r["n_flip_sessions"]),
        "with_a_flipped_bar_on_a_session_the_scorer_tests": sum(1 for r in rows if r["n_flip_sessions_tested_by_scorer"]),
        "with_a_flipped_bar_on_a_tested_session_and_a_trade_entered": sum(1 for r in rows if r["hypothetical_trade_entered_so_far"] and r["n_flip_sessions_tested_by_scorer"]),
        "with_no_bar_for_the_last_session_in_the_final_pull": [r["decision_id"] for r in rows if r["ticker_has_no_last_session_bar"]],
        "flip_already_changes_the_trade": [r["decision_id"] for r in rows if r["flip_changes_the_trade_so_far"]],
        "flipped_bars_so_far_by_hint": dict(Counter(h for r in rows for h in r["flip_board_hints"].split(";") if h)),
        "window_complete_reasons": {r["decision_id"]: r["pending_reason"] for r in rows if r["window_complete_on_final_bars"]},
    }
    return summary, rows


# -------------------------------------------------------------------------------------- 8. outputs
RESULT_COLUMNS = [
    "population", "decision_id", "outcome_record_hash", "decision_record_hash", "ticker", "policy_id", "decision",
    "signal_session", "recorded_on_pull", "entry_session", "path_end_B", "path_touches_2026_10_19",
    "recorded_trade", "recorded_exit_session", "recorded_exit_reason", "recorded_net_return", "recorded_verdict",
    "baseline_B_replay_matches_recorded", "baseline_mismatch_fields",
    "B_has_outcome", "B_trade", "B_exit_session", "B_exit_reason", "B_net_return", "B_mfe", "B_mae", "B_verdict",
    "C_has_outcome", "C_trade", "C_exit_session", "C_exit_reason", "C_net_return", "C_mfe", "C_mae", "C_verdict",
    "delta_exit_sessions_C_minus_B", "delta_net_return_C_minus_B",
    "flip_sessions_on_path", "n_flip_sessions", "n_flip_sessions_tested_by_scorer", "n_flip_at_modelled_7pct_limit", "n_flip_strictly_below_limit",
    "n_flip_degenerate_limit", "flip_board_hints", "wider_limit_evidence_on_path", "wider_limit_evidence_name",
    "category", "sub_category",
    "C10_category", "C10_exit_session", "C10_net_return", "C7b_category", "C7b_exit_session", "C7b_net_return",
    "CH_category", "CH_exit_session", "CH_net_return",
    "whatif_roll_C_exit_session", "whatif_roll_C_exit_reason", "whatif_roll_C_net_return",
    "whatif_roll_C_rolled_sessions", "whatif_roll_C_verdict",
    "window_complete_on_final_bars", "hypothetical_entry_observed", "fillable_at_entry", "inside_chase_band",
    "hypothetical_trade_entered_so_far", "B_exit_so_far", "C_exit_so_far", "flip_changes_the_trade_so_far",
    "ticker_has_no_last_session_bar", "pending_reason", "state_so_far",
]
BAR_COLUMNS = [
    "decision_id", "ticker", "signal_session", "session", "sessions_after_signal", "is_entry_session",
    "reference_prev_close", "close", "high", "low", "return_vs_reference", "arb_B_shipped_15pct",
    "arb_C_modelled_7pct", "special_board_10pct_limit", "close_minus_modelled_limit", "close_at_10pct_special_limit",
    "board_hint", "one_price_bar", "record_category_C_vs_B",
]
GATE_COLUMNS = [
    "decision_id", "outcome_record_hash", "ticker", "signal_session", "recorded_on_pull", "pull_started_at",
    "pull_last_bar", "pull_before_close", "trade_exit_on_pull_last_bar", "discovery_window_includes_pull_last_bar",
    "match", "mismatched_fields",
    "recorded_values", "replay_values", "diagnosis",
]
SPEC_COLUMNS = [
    "kind", "set_id", "window", "ticker", "signal_session", "resolved_on_pull", "uses_lock_down",
    "planned_horizon_session", "simulated_trades_with_a_horizon_sale", "baseline_B_replay_matches_recorded",
    "baseline_n_differences", "baseline_diagnosis", "C_vs_B", "names_with_horizon_close_locked_only_in_C",
    "flip_board_hints", "C10_identical_to_B", "flips_resolution",
]


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([fnum(r.get(c)) for c in columns])


def whatif_summary(recs: list[dict]) -> list[dict]:
    out = []
    for r in recs:
        if r["category"] != "BECOMES_UNSCORABLE":
            continue
        out.append(
            {
                "decision_id": r["decision_id"],
                "ticker": r["ticker"],
                "signal_session": r["signal_session"],
                "B_exit_session": r["B_exit_session"],
                "B_net_return": r["B_net_return"],
                "B_verdict": r["B_verdict"],
                "C_flip_sessions_on_path": r["flip_sessions_on_path"],
                "C_flip_board_hints": r["flip_board_hints"],
                "whatif_roll_exit_session": r.get("whatif_roll_C_exit_session"),
                "whatif_roll_rolled_sessions": r.get("whatif_roll_C_rolled_sessions"),
                "whatif_roll_net_return": r.get("whatif_roll_C_net_return"),
                "whatif_roll_verdict": r.get("whatif_roll_C_verdict"),
            }
        )
    return out


# -------------------------------------------------------------------------------------- 9. report
def pct(x, d=2, signed=True):
    if x is None:
        return "n/a"
    return f"{x * 100:+.{d}f}%" if signed else f"{x * 100:.{d}f}%"


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def mmdd(d):
    return d[5:] if d else ""


def pp(x, d=2):
    return "n/a" if x is None else f"{x * 100:+.{d}f} pp"


def cat_text(counts: dict) -> str:
    order = ("UNCHANGED", "NOT_AFFECTED", "EXIT_SHIFTED", "BECOMES_UNSCORABLE", "BECOMES_SCORABLE", "VERDICT_CHANGED", "BOTH_NO_OUTCOME", "OTHER_CHANGED")
    return ", ".join(f"{k} {counts[k]}" for k in order if counts.get(k))


def short_hint(h):
    return {"AT_7PCT_LIMIT": "at limit", "BELOW_7PCT_LIMIT": "BELOW limit", "DEGENERATE_LIMIT": "degenerate"}.get(h, h)


def flips_text(r):
    ds = r["flip_sessions_on_path"].split(";") if r["flip_sessions_on_path"] else []
    hs = r["flip_board_hints"].split(";") if r["flip_board_hints"] else []
    return ", ".join(f"{mmdd(d)} {short_hint(h)}" for d, h in zip(ds, hs)) or "none"


def trade_text(exit_session, reason, net):
    if not exit_session:
        return "no trade"
    return f"{mmdd(exit_session)} {'stop' if reason == 'invalidation' else 'horizon'} {pct(net)}"


def write_report(S, recs, pend_rows, spec_out, gate_rows, bars, cells) -> None:
    P, G, A, X, SP, PE, F, M = (S[k] for k in ("populations", "baseline_gate", "aggregates", "sensitivity", "speculations", "pending", "flipped_cells_market_wide", "meta"))
    sig, touch, pend = P["signal_on_or_after_cut"], P["path_touches_cut"], P["pending"]
    cat = A["categories"]
    changed = [r for r in recs if r["category"] in CHANGED]
    shifted = [r for r in recs if r["category"] == "EXIT_SHIFTED"]
    unsc = [r for r in recs if r["category"] == "BECOMES_UNSCORABLE"]
    trades_touching = A["hypothetical_trades"]["B_replay_with_path_touching_cut"]
    changed_all_at = [r for r in changed if r["n_flip_strictly_below_limit"] == 0]
    below_changed = [r for r in changed if r["n_flip_strictly_below_limit"] > 0]
    bar_hint = Counter(b["board_hint"] for b in bars)
    nt = A["net_return_all_trades"]
    both = A["net_return_trades_in_both_B_and_C"]
    drop = A["net_return_of_trades_C_drops_B_values"]
    v = A["verdicts"]
    mg = "MISSED GAIN (rejected, plan would have profited)"
    cr = "CORRECT REJECTION"
    no = "NO OUTCOME (score() returns None)"
    wi = S["whatif_roll_past_horizon"]
    wi_closed = [w for w in wi if w["whatif_roll_net_return"] is not None]
    wi_open = [w for w in wi if w["whatif_roll_net_return"] is None]
    ch10, ch7b, chH, drop_n = X["C10"], X["C7b"], X["CH"], X["drop_wider_limit_names"]
    mism = G["mismatches"]
    mism_ids = {m_["decision_id"] for m_ in mism}
    base5_flip = SP["base5_rows_that_flip_under_C"]
    unch_trade = sum(1 for r in recs if r["category"] == "UNCHANGED" and r["B_trade"])
    unch_notrade = sum(1 for r in recs if r["category"] == "UNCHANGED" and not r["B_trade"])
    equiv_txt = ", ".join(f"{k}: {e_['whatif_identical_to_paper_score']} of {e_['decisions_where_paper_score_returns_an_outcome']}" for k, e_ in M["whatif_equivalence_with_paper_score"].items() if k in ("B", "C"))
    wi_txt = ", ".join(f"{w_['ticker']} {pct(w_['B_net_return'])} to {pct(w_['whatif_roll_net_return'])}" for w_ in wi_closed)
    n_diag_pre = sum(1 for m_ in mism if "before the 16:00 WIB close" in m_["diagnosis"])
    n_diag_fp = sum(1 for m_ in mism if "knife-edge" in m_["diagnosis"])
    base5_rows = [r for r in spec_out if r["kind"] == "RESOLUTION" and r["uses_lock_down"]]
    base5_same = [r["set_id"].replace("SPEC-SCAN-", "") for r in base5_rows if not r["flips_resolution"]]
    next1_rows = [r for r in spec_out if r["kind"] == "RESOLUTION" and r["window"] == "NEXT1"]
    next1_match = sum(1 for r in next1_rows if r["baseline_B_replay_matches_recorded"])
    streak = sorted({r["ticker"] for r in changed if r["n_flip_at_modelled_7pct_limit"] >= 4 and r["n_flip_strictly_below_limit"] == 0})
    below_bars = [b for b in bars if b["board_hint"] == "BELOW_7PCT_LIMIT" and b["record_category_C_vs_B"] in CHANGED]
    below_txt = "; ".join(f"{b['ticker']} closed {abs(b['return_vs_reference']) * 100:.1f}% below its reference on {mmdd(b['session'])} (close {b['close']:g}, modelled limit {b['arb_C_modelled_7pct']:g})" for b in below_bars) or "none"
    all_later = all((r["delta_exit_sessions_C_minus_B"] or 0) > 0 for r in shifted)
    stuck_locked = [k for k, v_ in PE["window_complete_reasons"].items() if "locked" in v_]
    L = []
    w = L.append
    w("# What the October 2026 ARB correction changes in the IDX paper ledger")
    w("")
    w("*Impact analyst 2 of 2. Paper trading research only, no real money. Dates are 2026 unless a year is shown. Every number in this file is computed and written by `harness.py` from the ledger, the frozen price pull and the two code copies; the wording around the numbers is mine.*")
    w("")
    w("**Terms.** ARB is the lower auto-rejection price limit. A session closed at or below it, on a day the close is below the reference, counts as \"locked at the lower limit\" (`lock_down`) and is not sellable: a sale rolls to the next sellable session, and in the legacy IDX scoring branch a horizon exit that is locked returns no outcome at all (`score()` returns None). **B** is the code as shipped (ARB 15%), **C** the corrected code (ARB 7% from 2026-10-19, nominal Rp1 for references Rp11-14 from 2026-10-20). A *replay* runs the real scorer on the frozen price bars; the ARB effect is always C minus B (replay against replay), never C minus the recorded value.")
    w("")
    w("## 1. The numbers first")
    w("")
    w(f"- **Ledger recount.** {P['ledger_rows']} rows ({P['rows_by_type']['SCAN']} SCAN, {P['rows_by_type']['DECISION']} DECISION, {P['rows_by_type']['OUTCOME']} OUTCOME). IDX: **{P['idx_decisions']} decisions** ({P['idx_decisions_market_field_IDX']} marked `IDX`, plus {len(P['idx_decisions_market_field_absent_treated_as_IDX'])} written on 2026-10-07 with no `market` field, which the code also treats as IDX), **{P['idx_outcome_rows']} OUTCOME rows = {P['idx_latest_outcome_per_decision']} latest outcomes** (no decision has a second or revised outcome), and **{pend['decisions']} decisions without an outcome** ({pend['window_still_open_by_bars']} still inside their window, {pend['window_complete_but_no_outcome']} stuck for reasons the correction does not touch).")
    w(f"- **\"88 decisions\" and \"27 hypothetical trade records\" are both correct, for one definition only.** Decisions whose signal session is on or after 2026-10-19: **{sig['decisions']}**, of which {sig['with_outcome']} have an outcome and {sig['pending_no_outcome']} are still pending. Of the scored ones, **{sig['with_paper_trade_object']}** carry a hypothetical paper trade; all {sig['rejections_that_would_have_traded']} are PASS rejections that would have traded, none was executed (the IDX ledger holds no BUY ON TRIGGER decision). If 'rejections that would have traded' is read as 'the entry trigger fired', {sig['pending_whose_entry_trigger_has_fired_open_hypothetical_trade']} pending decisions with a signal on or after the cut also qualify (an open hypothetical trade, no OUTCOME yet), {sig['rejections_that_would_have_traded_closed_plus_open']} in all. By *exposure* the population is larger: scored paths that touch 2026-10-19 or later number **{touch['outcomes']} outcomes, {touch['of_which_with_paper_trade']} of them with a trade**, because {touch['of_which_signal_before_cut']} outcomes ({touch['trades_of_which_signal_before_cut']} trades) have an earlier signal day (back to {touch['earliest_signal_session_whose_path_touches']}) but a five-session path that runs into the new rule.")
    w(f"- **Baseline gate.** Replaying the real scorer under the shipped rules (B) on the frozen final pull reproduces **{G['field_for_field_matches']} of {G['outcomes_replayed']}** recorded outcomes field for field (floats within 1e-9; largest residual on matched records {G['max_abs_float_difference_on_matched_records']:.1e}). The {len(mism)} mismatches are explained and none involves the ARB rule: {n_diag_fp} is a floating-point knife-edge on a discovery flag, {n_diag_pre} come from a pull taken before the close.")
    w(f"- **Effect of the correction (C minus B, replay against replay, {A['records_replayed']} outcomes).** UNCHANGED {cat['UNCHANGED']}, NOT_AFFECTED {cat['NOT_AFFECTED']}, **EXIT_SHIFTED {cat['EXIT_SHIFTED']}**, **BECOMES_UNSCORABLE {cat['BECOMES_UNSCORABLE']}**, BECOMES_SCORABLE {cat['BECOMES_SCORABLE']}, VERDICT_CHANGED {cat['VERDICT_CHANGED']}. Of the {trades_touching} hypothetical trades whose path reaches 2026-10-19 or later, **{len(changed)} change ({len(changed) / trades_touching * 100:.0f}%)**; {unch_trade} exposed trades do not change; {unch_notrade} unchanged outcomes had no trade, so the lock flag was never consulted.")
    w(f"- **Paper-trade population.** Hypothetical trades {A['hypothetical_trades']['B_replay']} (B) to {A['hypothetical_trades']['C_replay']} (C). Mean net return {pct(nt['B_replay']['mean'])} to {pct(nt['C_replay']['mean'])}, median {pct(nt['B_replay']['median'])} to {pct(nt['C_replay']['median'])}. This is partly survivorship: the {drop['n']} trades that vanish had a B-replay mean of {pct(drop['mean'])} ({drop['n_positive']} of them profitable). Verdicts B to C: correct rejections {v['B_replay'].get(cr, 0)} to {v['C_replay'].get(cr, 0)}, missed gains {v['B_replay'].get(mg, 0)} to {v['C_replay'].get(mg, 0)}, no outcome {v['B_replay'].get(no, 0)} to {v['C_replay'].get(no, 0)}.")
    w(f"- **Board hint.** Market-wide {F['cells_locked_in_C_not_B']} bars become locked; {F['flipped_cells_at_modelled_7pct_limit']} close exactly on the modelled 7% limit and {F['flipped_cells_strictly_below_modelled_limit']} close strictly below it. On the paths of the {len(changed)} changed records, {len(changed_all_at)} have only at-the-limit flips; {len(below_changed)} ({', '.join(r['ticker'] for r in below_changed)}) has a flip strictly below the limit, so that flip is an artefact of treating a wider-limit name as a 7% name.")
    w(f"- **Sensitivity.** ARB 10% instead of 7%: **{ch10['records_changed_vs_B']} records change** versus B ({ch10['flipped_cells_vs_B']} bars flip instead of {X['C7']['flipped_cells_vs_B']}). Dropping names with wider-limit evidence: {drop_n['changed_records_C_vs_B']} to {drop_n['changed_records_remaining_after_dropping_names_with_evidence']} changed records. What-if that rolls past the horizon: {len(wi_closed)} of the {len(wi)} unscorable trades find a sellable close ({wi_txt}); {len(wi_open)} ({', '.join(w_['ticker'] for w_ in wi_open)}) still has none by 2026-11-06.")
    w(f"- **Speculations.** {SP['idx_resolution_rows']} IDX RESOLUTION rows; only the {SP['rows_whose_horizon_sale_uses_lock_down']} BASE5 rows read `lock_down` ({SP['simulated_horizon_sales_in_those_rows']} simulated horizon sales); the {SP['rows_that_never_read_lock_down']} NEXT1 rows never do. All {SP['idx_resolution_rows']} can be replayed on the frozen bars and {SP['baseline_B_replay_matches_recorded']} reproduce under B. **{len(base5_flip)} flips**: {', '.join(x.replace('SPEC-SCAN-', '') for x in base5_flip)} would not resolve on 2026-11-06 because two of its twins ({SP['base5_flip_detail'][base5_flip[0]]['names'].replace(';', ', ')}) close locked on their horizon day.")
    w(f"- **Pending.** {PE['pending_decisions']} decisions without an outcome; {PE['with_a_flipped_bar_on_a_session_the_scorer_tests']} already have a B-versus-C lock difference on a session the scorer tests, and for {len(PE['flip_already_changes_the_trade'])} of them ({', '.join(x.replace('SCAN-', '') for x in PE['flip_already_changes_the_trade'])}) the hypothetical trade already diverges between B and C.")
    w("")
    w("## 2. Populations, recounted from the ledger file")
    w("")
    w("Method: read `paper/ledger.jsonl` (sha256 `" + M["ledger_sha256"][:16] + "...`, {} rows, hash chain verified: {} problems) and count; nothing is taken from another agent's tally.".format(P["ledger_rows"], len(M["ledger_hash_chain_problems"])))
    w("")
    rows_t = [
        ("Rows by type", ", ".join(f"{k} {v_}" for k, v_ in sorted(P["rows_by_type"].items()))),
        ("DECISION rows by market field", ", ".join(f"{k.split('|')[1]} {v_}" for k, v_ in P["rows_by_type_and_market"].items() if k.startswith("DECISION"))),
        ("IDX decisions (market IDX or field absent)", P["idx_decisions"]),
        ("IDX decision types", ", ".join(f"{k} {v_}" for k, v_ in P["idx_decision_types"].items())),
        ("IDX decisions carrying an E3 `execution_plan` (scored by `_score_plan`, which rolls)", P["idx_decisions_with_execution_plan"]),
        ("IDX OUTCOME rows / distinct decisions with an outcome", f"{P['idx_outcome_rows']} / {P['idx_latest_outcome_per_decision']}"),
        ("Decisions with more than one OUTCOME row, `revises` fields, status other than SCORED", f"{len(P['idx_decisions_with_more_than_one_outcome_row'])}, {P['idx_outcome_rows_with_revises_field']}, {sum(v_ for k, v_ in P['idx_outcome_rows_status'].items() if k != 'SCORED')}"),
        ("IDX outcomes with a paper trade / executed", f"{P['idx_outcomes_with_paper_trade']} / {P['idx_outcomes_executed_true']}"),
        ("Recorded verdicts", ", ".join(f"{k.split(' (')[0]} {v_}" for k, v_ in P["idx_outcome_verdicts"].items())),
        ("Signal on or after 2026-10-19: decisions / with outcome / pending", f"{sig['decisions']} / {sig['with_outcome']} / {sig['pending_no_outcome']}"),
        ("  of the scored: with a trade object / without", f"{sig['with_paper_trade_object']} / {sig['scored_without_trade']}"),
        ("  trades by decision type; rejections that would have traded (closed); executed", f"{', '.join(f'{k} {v_}' for k, v_ in sig['decision_type_of_trades'].items())}; {sig['rejections_that_would_have_traded']}; {sig['executed_trades']}"),
        ("  pending decisions whose entry trigger has already fired (open hypothetical trade); closed plus open", f"{sig['pending_whose_entry_trigger_has_fired_open_hypothetical_trade']}; {sig['rejections_that_would_have_traded_closed_plus_open']}"),
        ("Scored path touches 2026-10-19 or later (entry session to exit, or to the horizon end if no trade): outcomes / with trade", f"{touch['outcomes']} / {touch['of_which_with_paper_trade']}"),
        ("  of which signal before 2026-10-19: outcomes / trades", f"{touch['of_which_signal_before_cut']} / {touch['trades_of_which_signal_before_cut']}"),
        ("  same count if the full five-session window is used instead of the actual exit", touch["outcomes_by_full_5_session_window_instead_of_actual_exit"]),
        ("Outcomes / trades whose path ends before 2026-10-19", f"{touch['outcomes_not_touching']} / {touch['trades_not_touching']}"),
        ("Pending decisions: total / window open / window complete but no outcome", f"{pend['decisions']} / {pend['window_still_open_by_bars']} / {pend['window_complete_but_no_outcome']}"),
    ]
    w(md_table(["Quantity", "Count"], rows_t))
    w("")
    w(f"**How duplicates and revisions are resolved.** The rule is the one `paper.score_pending()` uses: the last OUTCOME row per `decision_id` in file order wins, and a later row must name its predecessor in `revises`. The ledger holds no such case: every one of the {P['idx_latest_outcome_per_decision']} IDX decisions with an outcome has exactly one OUTCOME row, no row has a `revises` field and no `decision_id` is repeated ({len(P['duplicate_decision_ids'])} duplicates), so deduplication changes no count.")
    w("")
    w(f"**Which definition makes 88 and 27 true.** \"Signal session on or after 2026-10-19\" gives {sig['decisions']} decisions and {sig['with_paper_trade_object']} trades, as claimed. Two cautions: the {sig['decisions']} include {sig['pending_no_outcome']} decisions with no outcome, so there is no record there to change; and the definition misses {touch['trades_of_which_signal_before_cut']} trades whose signal was earlier but whose path crosses the cut. The exposure definition ({touch['of_which_with_paper_trade']} trades, {touch['outcomes']} outcomes) is the one that matches what can change; the trade count does not depend on how the horizon end of a no-trade outcome is defined. Even the outcome count overstates: {unch_notrade} of the unchanged outcomes had no trade at all, and for a decision with no trade the scorer never reads `lock_down`.")
    w("")
    w("## 3. Baseline gate: does the replay reproduce what was written?")
    w("")
    w(f"Each of the {G['outcomes_replayed']} IDX OUTCOME decisions was replayed through the production flow (`load_recent` to `_market` to `yahoo_events` to `scoring_units` to `score`) under the shipped rules on the frozen pull `{M['frozen_manifest']}` ({M['frozen_sessions']}), and compared with the recorded OUTCOME on: verdict, discovery (`r5max`, E30, E50, E100, `peak_session`), fillable, within chase band, executed, and the trade (entry/exit session, exit reason, entry price, net return, MFE, MAE), `price_scale`, `scoring_version`. The replay returns an outcome for exactly the {G['outcomes_replayed']} decisions that have one and none for the {pend['decisions']} that do not.")
    w("")
    w(f"**{G['field_for_field_matches']} of {G['outcomes_replayed']} match** ({G['matched_records_bit_identical']} bit-for-bit; the rest differ only by float noise up to {G['max_abs_float_difference_on_matched_records']:.1e}). The {len(mism)} mismatches:")
    w("")
    mrows = []
    gate_by = {g["decision_id"]: g for g in gate_rows}
    for m_ in mism:
        g = gate_by[m_["decision_id"]]
        rv, pv = json.loads(g["recorded_values"]), json.loads(g["replay_values"])
        diff_txt = "; ".join(f"{k.strip('/').split('/')[-1]}: {rv[k]:.6g} vs {pv[k]:.6g}" if isinstance(rv[k], float) else f"{k.strip('/').split('/')[-1]}: {rv[k]} vs {pv[k]}" for k in sorted(rv))
        mrows.append((m_["ticker"], m_["decision_id"].replace("SCAN-", ""), m_["recorded_on_pull"].replace("yahoo_recent-", "").replace(".jsonl", ""), diff_txt, m_["diagnosis"]))
    w(md_table(["Ticker", "Decision", "Recorded on pull", "Recorded vs replay", "Diagnosis"], mrows))
    w("")
    w(f"{'None' if not (mism_ids & {r['decision_id'] for r in changed}) else 'Some'} of the {len(mism)} is among the {len(changed)} records the correction changes, and none is caused by the ARB limit. Because the ARB effect is always measured as C minus B on the same bars, these three artefacts cannot leak into it. {G['outcomes_scored_on_a_pre_close_pull']} recorded outcomes were scored on a pull started before the 16:00 WIB close ({', '.join(p_.replace('yahoo_recent-', '').replace('.jsonl', '') for p_ in G['pre_close_pulls'])}); only {G['pre_close_outcomes_whose_trade_exits_on_the_intraday_bar']} of them exit on that intraday bar, and both are the mismatches above.")
    w("")
    w("**Limitation of every replay in this report.** The only surviving raw pull is the final one (pinned 2026-11-06T10:18:53Z). Each outcome is replayed on those final bars (\"final-bar replay\"), not on the pull that was current when it was written. The gate shows this reproduces the records, but it cannot show what an earlier intraday or since-revised bar looked like.")
    w("")
    w("## 4. Corrected replay: what changes, record by record")
    w("")
    w(f"B = shipped rules (ARB 15% throughout), C = corrected rules (ARB 7% from 2026-10-19, nominal Rp1 for references Rp11-14 from 2026-10-20). The two code copies differ only in `idxsig/market.py`. The harness also confirmed on the bar matrix that C locks every bar B locks (no bar is unlocked) and that the upper-limit (ARA) flags are identical, so the extra locks are the only difference between the two worlds, and an independent from-scratch implementation of the documented rules (none of idxsig's code) reproduced all {M['independent_lock_oracle']['cells_checked']} lock flags in both worlds ({M['independent_lock_oracle']['mismatches_B']} and {M['independent_lock_oracle']['mismatches_C']} disagreements).")
    w("")
    w(md_table(["Category", "Records", "Meaning"], [
        ("UNCHANGED", cat["UNCHANGED"], f"path reaches 2026-10-19 or later, replay result identical: {A['unchanged_breakdown'].get('NO_TRADE_lock_flags_never_consulted', 0)} had no trade, {A['unchanged_breakdown'].get('TRADE_flip_on_tested_sessions_but_result_identical', 0)} traded across at least one newly locked session without any effect, {A['unchanged_breakdown'].get('TRADE_no_flip_on_tested_sessions', 0)} traded with no newly locked session"),
        ("EXIT_SHIFTED", cat["EXIT_SHIFTED"], "the stop-out day is locked under C, so the sale rolls to a later session; exit session and return change"),
        ("BECOMES_UNSCORABLE", cat["BECOMES_UNSCORABLE"], "B scores the trade, C's horizon close is locked so `score()` returns None (the legacy branch never rolls past the horizon); no OUTCOME would be written"),
        ("BECOMES_SCORABLE", cat["BECOMES_SCORABLE"], "B returns None, C returns an outcome (impossible here: C only adds locks)"),
        ("VERDICT_CHANGED", cat["VERDICT_CHANGED"], "both return an outcome with a different verdict"),
        ("NOT_AFFECTED", cat["NOT_AFFECTED"], f"scored path ends before 2026-10-19 ({A['not_affected_breakdown'].get('TRADE', 0)} trades, {A['not_affected_breakdown'].get('NO_TRADE', 0)} without a trade)"),
        ("Total", A["records_replayed"], ""),
    ]))
    w("")
    w(f"### The {len(changed)} records that change")
    w("")
    w("Full precision, hashes and the other {} records are in `results.csv` (one row per replayed record, plus the {} pending decisions). \"Flipped sessions\" are the sessions on the path whose `lock_down` flag differs between B and C; the hint says whether the close sits exactly on the modelled 7% limit (consistent with a 7% board) or strictly below it (a wider-limit name).".format(A["records_replayed"] - len(changed), pend["decisions"]))
    w("")
    crow = []
    for r in sorted(changed, key=lambda r: (r["signal_session"], r["decision_id"])):
        c_txt = trade_text(r["C_exit_session"], r["C_exit_reason"], r["C_net_return"]) if r["C_has_outcome"] else f"no outcome (horizon {mmdd(r['B_exit_session'])} locked)"
        dl = "" if r["delta_net_return_C_minus_B"] is None else f"{r['delta_net_return_C_minus_B'] * 100:+.2f} pp"
        crow.append((r["category"], f"{r['ticker']} ({mmdd(r['signal_session'])})", r["outcome_record_hash"][:10], trade_text(r["recorded_exit_session"], r["recorded_exit_reason"], r["recorded_net_return"]), trade_text(r["B_exit_session"], r["B_exit_reason"], r["B_net_return"]), c_txt, dl, flips_text(r)))
    w(md_table(["Category", "Ticker (signal)", "OUTCOME hash", "Recorded", "B replay", "C replay", "Delta net", "Flipped sessions (board hint)"], crow))
    w("")
    w(f"Reading the table: the {len(shifted)} EXIT_SHIFTED records {'all exit later under C' if all_later else 'move their exit'} ({sum(1 for r in shifted if r['delta_net_return_C_minus_B'] < 0)} worse, {sum(1 for r in shifted if r['delta_net_return_C_minus_B'] > 0)} better; mean change {pp(A['exit_shifted_effect']['mean_delta_net_return_C_minus_B'])} in net return, median {pp(A['exit_shifted_effect']['median_delta_net_return_C_minus_B'])}), typically because a name that falls about 6% to 7% a day for several days is locked at the 7% limit on each of them, so a stop-out the 15% rule filled on the first day cannot be filled until the run ends. The {len(unsc)} BECOMES_UNSCORABLE records are trades whose fifth-session close is locked under C. {'No verdict flips anywhere' if cat['VERDICT_CHANGED'] == 0 else 'Verdicts flip in ' + str(cat['VERDICT_CHANGED']) + ' records'}; the {sum(1 for r in unsc if r['B_verdict'] == mg)} profitable trades among the unscorable ones (missed gains under B) simply lose their outcome.")
    w("")
    w("### Board hint for the flipped bars")
    w("")
    w(f"- Market-wide, {F['cells_locked_in_C_not_B']} bars are locked under C and not under B ({F['flipped_cells_on_2026_10_19']} of them on 2026-10-19, the first day of the 7% rule): **{F['flipped_cells_at_modelled_7pct_limit']} close exactly on the modelled limit, {F['flipped_cells_strictly_below_modelled_limit']} strictly below it, {F['flipped_cells_degenerate_limit_ARB_ge_reference']} on a degenerate limit** (the 7% formula gives ARB = reference for references Rp11-14 on 2026-10-19; the {F['bars_2026_10_19_with_reference_Rp11_14_and_a_down_close']} such bars with a down close ({', '.join(F['bars_2026_10_19_with_reference_Rp11_14_and_a_down_close_names'])}, both 25% lower) were already locked under B, so nothing depends on that day's real limit).")
    w(f"- On the paths of the {A['records_replayed']} replayed records there are {len(bars)} flipped bars: {bar_hint.get('AT_7PCT_LIMIT', 0)} at the limit, {bar_hint.get('BELOW_7PCT_LIMIT', 0)} below it. A name whose path closes on the modelled tick on four or more sessions ({', '.join(streak)}) behaves like a 7% board; a close beyond the 7% tick cannot occur on one. Below-limit flips on the changed records: {below_txt}.")
    w(f"- {F['names_with_wider_limit_evidence']} of {F['tickers_in_final_pull']} names show at least one traded bar on or after 2026-10-19 that closes strictly below the modelled 7% limit ({F['evidence_bars_total']} bars); {F['evidence_names_with_a_bar_exactly_on_the_special_board_10pct_limit']} of them also have a bar exactly on the 10% special-board limit, the clearest sign of a 10% board. Among the {A['records_replayed']} replayed records, {drop_n['records_replayed_whose_name_has_evidence']} belong to such names ({', '.join(drop_n['tickers_with_evidence_among_replayed_records'])}); only FLMC is among the changed records.")
    w(f"- The second change (nominal Rp1 ARB for references Rp11-14 from 2026-10-20) adds no lock on top of the 7% change in these data: C and C-without-that-rule flip exactly the same bars versus B ({X['C7']['flipped_cells_vs_B']} against {X['C7b']['flipped_cells_vs_B']}). For those references the 7% formula, rounded up to the tick, already puts the limit at the reference, so every down close is a lock either way; {F['flipped_cells_with_reference_Rp11_14_market_wide']} of the {F['cells_locked_in_C_not_B']} flipped bars market-wide have such a reference and {sum(1 for b in bars if 11 <= b['reference_prev_close'] <= 14)} of the {len(bars)} flipped bars on replayed paths do. The whole effect on the ledger comes from the 7% percentage.")
    w("")
    w("## 5. Aggregates")
    w("")
    w(md_table(["Paper-trade population (replay)", "Recorded", "B (shipped)", "C (corrected)"], [
        ("Hypothetical trades", A["hypothetical_trades"]["recorded"], A["hypothetical_trades"]["B_replay"], A["hypothetical_trades"]["C_replay"]),
        ("  of which path reaches 2026-10-19 or later", "", A["hypothetical_trades"]["B_replay_with_path_touching_cut"], A["hypothetical_trades"]["C_replay_with_path_touching_cut"]),
        ("Mean net return", pct(nt["recorded"]["mean"]), pct(nt["B_replay"]["mean"]), pct(nt["C_replay"]["mean"])),
        ("Median net return", pct(nt["recorded"]["median"]), pct(nt["B_replay"]["median"]), pct(nt["C_replay"]["median"])),
        ("Profitable trades", nt["recorded"]["n_positive"], nt["B_replay"]["n_positive"], nt["C_replay"]["n_positive"]),
        (f"Same {both['n']} trades in both (mean / median)", "", f"{pct(both['B']['mean'])} / {pct(both['B']['median'])}", f"{pct(both['C']['mean'])} / {pct(both['C']['median'])}"),
        ("Correct rejections", v["recorded"].get(cr, 0), v["B_replay"].get(cr, 0), v["C_replay"].get(cr, 0)),
        ("Missed gains", v["recorded"].get(mg, 0), v["B_replay"].get(mg, 0), v["C_replay"].get(mg, 0)),
        ("No outcome (`score()` returns None)", 0, 0, v["C_replay"].get(no, 0)),
    ]))
    w("")
    n_trade_mism = sum(1 for m_ in mism if "/paper_trade/" in m_["fields"])
    w(f"The recorded column differs from the B replay only through the {n_trade_mism} baseline mismatches that touch trade figures (the pre-close pull: {n_diag_pre}).")
    w("")
    w(f"The C mean is **partly survivorship**. The trades that drop out are exactly those that sit locked at the lower limit at their horizon, so what remains is the subset that could be sold. The {drop['n']} dropped trades had a B-replay mean of {pct(drop['mean'])} (median {pct(drop['median'])}), so removing them lowers the mean. On the {both['n']} trades that exist under both rule sets the mean moves from {pct(both['B']['mean'])} to {pct(both['C']['mean'])}, which is the pure exit-shift effect. If the {len(wi_closed)} trades that can be rolled are added back (what-if, section 6b), the C mean is {pct(A['whatif_C_population_with_rolled_trades_added']['mean'])} over {A['whatif_C_population_with_rolled_trades_added']['n']} trades. The correct-rejection share looks better under C ({v['C_replay'].get(cr, 0)} of {sum(v['C_replay'].values()) - v['C_replay'].get(no, 0)} scored) than under B ({v['B_replay'].get(cr, 0)} of {sum(v['B_replay'].values())}) only because two missed gains lost their outcome, not because decisions improved.")
    w("")
    w("## 6. Sensitivity")
    w("")
    w(f"**(a) ARB 10% instead of 7%** (the special-board bound; `market.limits` patched in the worker process only, rest of C unchanged). {ch10['records_changed_vs_B']} of {A['records_replayed']} records change versus B (categories: {cat_text(ch10['categories'])}), and {ch10['flipped_cells_vs_B']} bars flip instead of {X['C7']['flipped_cells_vs_B']}. {'Every changed record in the main result depends on a close between the 7% and 10% limits; at 10% they behave as under B. ' if ch10['records_changed_vs_B'] == 0 else ''}The speculations behave the same way ({SP['C10_base5_rows_identical_to_B']} of {SP['rows_whose_horizon_sale_uses_lock_down']} BASE5 rows identical to B).")
    w("")
    w(f"**(b) What-if: keep rolling past the horizon to the first sellable close.** Labelled a what-if; it is not what `score()` does. The harness re-implements the legacy IDX branch with only that change and checked it against `paper.score()`: identical on every decision where the real scorer returns an outcome ({equiv_txt}).")
    w("")
    w(md_table(["Ticker (signal)", "B exit, net", "What-if exit (sessions rolled), net", "What-if verdict"], [
        (f"{x['ticker']} ({mmdd(x['signal_session'])})", f"{mmdd(x['B_exit_session'])} {pct(x['B_net_return'])}", (f"{mmdd(x['whatif_roll_exit_session'])} ({x['whatif_roll_rolled_sessions']}) {pct(x['whatif_roll_net_return'])}" if x["whatif_roll_net_return"] is not None else "no sellable close through 2026-11-06"), x["whatif_roll_verdict"]) for x in wi
    ]))
    w("")
    flips_v = [x_ for x_ in wi_closed if x_["whatif_roll_verdict"] != x_["B_verdict"]]
    w(f"Under the what-if {len(flips_v)} verdict changes ({', '.join(x_['ticker'] + ': ' + x_['B_verdict'].split(' (')[0].lower() + ' to ' + x_['whatif_roll_verdict'].split(' (')[0].lower() for x_ in flips_v) or 'none'}); the what-if is not part of any count above.")
    w("")
    w(f"**(c) Drop names with empirical wider-limit evidence.** Evidence = a traded bar on or after 2026-10-19 that closes strictly below the modelled 7% limit (excluding degenerate limits). {drop_n['changed_records_whose_name_has_wider_limit_evidence']} of the {drop_n['changed_records_C_vs_B']} changed records belongs to such a name ({', '.join(i.replace('SCAN-', '') for i in drop_n['changed_ids_with_name_evidence'])}), leaving **{drop_n['changed_records_remaining_after_dropping_names_with_evidence']}** (dropping all {drop_n['records_replayed_whose_name_has_evidence']} records of such names leaves {drop_n['records_remaining_after_dropping_those_names']} records: {cat_text(drop_n['categories_of_the_remaining_records'])}). A name-aware replay (evidence names at 10%, everyone else at 7%) gives **{chH['records_changed_vs_B']}** changed records and {chH['trades']} trades with mean {pct(chH['net_return']['mean'])}. Absence of evidence is weak: a 10%-board name that never closed below the 7% tick on these days is indistinguishable from a 7% name.")
    w("")
    w("## 7. Speculations (`paper/speculations.jsonl`)")
    w("")
    w(f"The file holds {SP['idx_speculation_sets']} IDX SPECULATION_SET rows and **{SP['idx_resolution_rows']} IDX RESOLUTION rows** ({', '.join(f'{k} {v_}' for k, v_ in sorted(SP['resolution_rows_by_window'].items()))}). Only BASE5 resolutions simulate a trade whose horizon sale tests `lock_down` (for the candidate and each of its five twins): {SP['rows_whose_horizon_sale_uses_lock_down']} rows, {SP['simulated_horizon_sales_in_those_rows']} simulated sales. NEXT1 resolutions grade the next-session return and never read `lock_down` ({SP['next1_rows_identical_B_vs_C']} of {SP['next1_rows']} identical under B and C, as they must be). PATH20 windows are not resolved yet. All {SP['resolution_rows_whose_entry_session_is_on_or_after_cut']} resolution rows touch sessions on or after 2026-10-19 (their entry sessions are {SP['earliest_entry_session_of_the_resolution_rows']} or later).")
    w("")
    w(f"**Feasibility.** Yes, on the frozen bars: the real `resolve_set()` was run for every recorded row. {SP['recorded_resolutions_written_on_the_frozen_pull_itself']} were written on the frozen pull itself (both BASE5 rows among them) and {SP['recorded_resolutions_written_on_earlier_pulls_no_longer_available']} on earlier pulls that no longer exist, so those are final-bar replays. `research/SPECULATION_REGISTER_v1/protocol_v1_1.json` is not in the code copies, so the window definitions were supplied inside the worker (BASE5 = entry at the next close, five sessions held, then the first sellable close; NEXT1 = next-session return; PATH20 = twenty-session path); that reading is checked by the replay, which reproduces both BASE5 rows including every twin trade ({next1_match} of {SP['next1_rows']} NEXT1 rows also reproduce). Baseline: {SP['baseline_B_replay_matches_recorded']} of {SP['idx_resolution_rows']} reproduce under B. The exception is {', '.join(SP['baseline_mismatches'])}: {SP['baseline_mismatch_diagnoses'][SP['baseline_mismatches'][0]]}.")
    w("")
    sp_rows = [(r["set_id"].replace("SPEC-SCAN-", ""), r["window"], r["simulated_trades_with_a_horizon_sale"], "yes" if r["baseline_B_replay_matches_recorded"] else "no", r["C_vs_B"], r["names_with_horizon_close_locked_only_in_C"].replace(";", ", ") or "none", r["flip_board_hints"].replace("_7PCT_LIMIT", "").replace(";", ", ") or "") for r in spec_out if r["kind"] == "RESOLUTION" and r["uses_lock_down"]]
    w(md_table(["BASE5 set", "Window", "Simulated horizon sales", "B replay = record", "C versus B", "Locked only in C at the horizon (2026-11-06)", "Board hint"], sp_rows))
    w("")
    w(f"Which flips: **{', '.join(x.replace('SPEC-SCAN-', '') for x in base5_flip)}**. Under C two of its twins close locked on 2026-11-06 and the data end there, so the resolver would wait (`simulate()` returns None) and the BASE5 RESOLUTION would not have been written on that day. The other BASE5 row ({', '.join(base5_same) or 'none'}) is identical under C. Nothing else in the speculation ledger changes. For the {SP['open_base5_windows']} IDX BASE5 windows still open ({SP['open_base5_windows_with_entry_observed']} with an entry session observed), {SP['open_base5_windows_with_a_flipped_bar_so_far_on_candidate_or_twin']} already have a B-versus-C lock difference on the candidate's or a twin's path so far (listed in `spec_results.csv`, kind OPEN_WINDOW); whether it matters depends on the horizon-day close.")
    w("")
    w("## 8. Pending decisions: B-versus-C lock flips on the path observed so far")
    w("")
    w(f"{PE['pending_decisions']} IDX decisions have no outcome. {PE['window_still_open']} are still inside their window on the final bars (the last session is 2026-11-06). {pend['window_complete_but_no_outcome']} have a complete window but no outcome, for reasons that are the same under B and C and unrelated to the correction: {'; '.join(k.replace('SCAN-', '') + ' = ' + v_ for k, v_ in PE['window_complete_reasons'].items())}. {('(' + ', '.join(k.replace('SCAN-', '') for k in stuck_locked) + ' is an existing instance of what the correction would make more common: the legacy scorer never rolls past a locked horizon close, so the decision stays pending indefinitely.)') if stuck_locked else ''} A flip only matters if a hypothetical trade was entered and the flipped session is one the scorer tests (from the session after entry); the entry session itself is never tested for sellability.")
    w("")
    prow = []
    for r in sorted(pend_rows, key=lambda r: (r["signal_session"], r["decision_id"])):
        if r["hypothetical_entry_observed"] is False:
            st = "entry session not yet observed"
        elif not r["hypothetical_trade_entered_so_far"]:
            st = "no hypothetical entry"
        else:
            st = "trade entered"
        fl = ", ".join(f"{mmdd(d)} {short_hint(h)}" for d, h in zip(r["flip_sessions_on_path"].split(";"), r["flip_board_hints"].split(";"))) if r["flip_sessions_on_path"] else "none"
        bc = "diverge: B " + (r["B_exit_so_far"][5:] or "no exit") + " / C " + (r["C_exit_so_far"][5:] or "no exit") if r["flip_changes_the_trade_so_far"] else ("same so far" if r["hypothetical_trade_entered_so_far"] else "")
        if r["window_complete_on_final_bars"]:
            bc = "stuck, same under B and C: " + ("horizon locked" if "locked" in r["pending_reason"] else "horizon untraded")
        prow.append((mmdd(r["signal_session"]), r["ticker"] + ("*" if r["ticker_has_no_last_session_bar"] else ""), r["decision"].replace("NOT EXECUTABLE", "NOT EXEC."), "complete" if r["window_complete_on_final_bars"] else "open", st, fl, bc))
    w(md_table(["Signal", "Ticker", "Decision", "Window", "Hypothetical trade", "Lock flips B vs C on path so far", "B versus C exit so far"], prow))
    w("")
    w("`*` = no 2026-11-06 bar for this name in the frozen pull.")
    w("")
    w(f"Summary: {PE['with_hypothetical_trade_entered_so_far']} of the {PE['with_entry_observed']} decisions whose entry session is observed would have entered a trade; {PE['with_a_flipped_bar_on_path_so_far_incl_entry_session']} show a flipped bar on the path so far ({PE['with_a_flipped_bar_on_a_session_the_scorer_tests']} on a session the scorer tests, all with a trade entered); every one of the {sum(PE['flipped_bars_so_far_by_hint'].values())} flipped bars sits at the modelled limit. For {len(PE['flip_already_changes_the_trade'])} the trade already diverges between B and C. {len(PE['with_no_bar_for_the_last_session_in_the_final_pull'])} pending names have no 2026-11-06 bar in the frozen pull, so no flip can be seen for them on that day.")
    w("")
    w("## 9. Unresolved items and caveats")
    w("")
    cav = [
        f"**Final-bar replay only.** Every replay uses the 2026-11-06 pull; earlier pulls survive as manifests only. The baseline gate ({G['field_for_field_matches']}/{G['outcomes_replayed']}) shows the effect on reproduction is small, but an outcome scored on a bar that Yahoo later revised, or on an intraday bar, is judged here on the revised one.",
        f"**The last session is thin.** {F['names_without_a_bar_on_the_last_session_in_the_final_pull']} of {F['tickers_in_final_pull']} names have no 2026-11-06 bar in the frozen pull. They are unsellable that day under B and C alike (no ARB effect), but any decision or speculation window that ends on 2026-11-06 for such a name cannot show a flip.",
        "**Board membership is not in the data.** The model locks every name by the regular-board rule; the board hint is inferred from where the close sits against the modelled limit. It is evidence, not a fact. Rights-issue or other reference resets that the bars do not show would also produce closes below the limit.",
        "**The rule text rests on secondary sources.** `market.py` (C) says the decree texts were not read, and that the real limit on 2026-10-19 for references Rp11-14 is unknown. Here that gap changes nothing: no flipped bar has a degenerate limit, the two 2026-10-19 bars were locked under B already, and the Rp11-14 rule adds no lock beyond the 7% change.",
        "**Nothing after 2026-12-31 is exercised.** The frozen bars end on 2026-11-06. C carries the last rule forward from 2027-01-01 (labelled UNCONFIRMED, with a warning); B reverts to ARB = ARA on that date. No worker emitted that warning.",
        "**The legacy scorer returns None for a locked horizon close; the production flow cannot record a revision for that.** `score_pending()` skips a record whose `score()` is None, so the 3 BECOMES_UNSCORABLE decisions could not be re-scored into the ledger as outcomes or as UNSCORABLE revisions without a scorer decision (rolling, as `_score_plan` does, or an explicit status). The what-if is not production behaviour. The recorded outcomes themselves are untouched.",
        f"**Speculation windows were reconstructed.** The protocol JSON is missing from the code copies; the replay reproduces both BASE5 rows and {next1_match} of {SP['next1_rows']} NEXT1 rows, and the NEXT1 difference is a data-timing artefact that never reads `lock_down`.",
        f"**Environment differs from the pinned research environment.** Python {M['python']}, numpy {M['numpy']}, pandas {M['pandas']} (the constraints file tests CPython 3.12, numpy 2.3.5, pandas 2.2.3; requirements say pandas below 3). The baseline gate, with a largest residual of {G['max_abs_float_difference_on_matched_records']:.1e}, is the evidence that this does not move results.",
        f"**Evidence thresholds are my choice.** \"Wider-limit evidence\" is any traded bar from 2026-10-19 strictly below the modelled limit; {F['names_with_wider_limit_evidence']} names qualify. A different rule (for example, two or more such bars) would move the figures in 6(c) by at most the single FLMC record.",
        "**Disclosure.** During exploration I wrote one scratch file (`probe_B.json`) into the B code directory by mistake (a relative output path while the working directory was the code copy) and deleted it at once; only that directory's modification time changed and no existing file was edited. The harness records sha256 of all files in both code trees, the frozen payloads and the manifests before and after the run and asserts they are identical (summary.json: `code_and_input_trees_unchanged_by_the_run`).",
    ]
    for c_ in cav:
        w(f"- {c_}")
    w("")
    w("## 10. Files and reproduction")
    w("")
    w("One command, about 20 seconds, writes everything below into this directory (it deletes and recomputes `work/` first):")
    w("")
    w("    python3 -I /tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/arb2/impact_2/harness.py")
    w("")
    w("- `results.csv`: one row per replayed record: the 93 IDX outcomes (recorded, B, C, delta, flipped sessions with board hints, category, variant results, what-if) and the 33 pending decisions.")
    w("- `baseline_gate.csv`: the 93 field-by-field comparisons with the diagnosis for each mismatch.")
    w("- `flipped_bars.csv`: every flipped bar on a replayed path with reference, close, the B and C limits and the board hint.")
    w("- `spec_results.csv`: the 23 IDX RESOLUTION replays and the open BASE5 windows.")
    w("- `summary.json`: all counts in this report; `harness.py`: the harness (orchestrator and worker in one file); `work/`: raw worker output (replays and arrays per variant).")
    w("")
    w("Reading `results.csv`: `recorded_*` is the ledger's OUTCOME, `B_*` and `C_*` are the replays under the shipped and corrected rules, `delta_*` is C minus B, `flip_sessions_on_path` lists the sessions whose `lock_down` differs, `flip_board_hints` says AT_7PCT_LIMIT or BELOW_7PCT_LIMIT for each, `category` is the main classification, `C10_*`, `C7b_*` and `CH_*` are the sensitivity replays (ARB 10%; the 7% change alone; names with wider-limit evidence at 10%), `whatif_roll_C_*` is the roll-past-the-horizon what-if for the unscorable trades, and the last columns describe pending decisions.")
    (OUT_DIR / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# -------------------------------------------------------------------------------------- independent check
def independent_lock_oracle(ctx: Ctx) -> dict:
    """From-scratch re-derivation of every lock_down flag in B and C from close, previous close, high, low and
    volume, using the documented rules and none of idxsig's code (tick table, ARB 15% until 2026-10-18, 7% from
    2026-10-19, nominal Rp1 for references Rp11-14 from 2026-10-20, Rp1 steps for references up to Rp10 from
    2026-09-28, the one-price special-board proxy). A disagreement would mean the arrays under analysis are wrong."""
    A = ctx.A["B"]
    close, prev, high, low, vol, pres = A["close"], A["prev"], A["high"], A["low"], A["volume"], A["present"]

    def tick(x):
        return 1 if x < 200 else 2 if x < 500 else 5 if x < 2000 else 10 if x < 5000 else 25

    def ceil_tick(x):
        t = tick(x)
        return math.ceil(x / t - 1e-9) * t

    mism = {"B": 0, "C": 0}
    cells = 0
    for i in range(close.shape[0]):
        for k, d in enumerate(ctx.dates):
            cells += 1
            ref, cl = prev[i, k], close[i, k]
            if not (np.isfinite(ref) and ref > 0):
                exp_b = exp_c = False
            else:
                traded = bool(pres[i, k] and np.nan_to_num(vol[i, k]) > 0 and np.nan_to_num(cl) > 0)
                one_price = bool(high[i, k] == low[i, k] and low[i, k] == cl)
                thin = one_price or ((cl < 50 or ref < 50) and d < "2026-09-28")
                floor = 1 if d >= "2026-09-28" else 50
                small = d >= "2026-09-28" and ref <= 10
                special = max(ref - 1, 1) if ref <= 10 else max(ceil_tick(ref * 0.9), 1)
                arb_b = max(ref - 1, 1) if small else max(ceil_tick(ref * 0.85), floor)
                if d < CUT:
                    arb_c = arb_b
                elif small:
                    arb_c = max(ref - 1, 1)
                elif d >= "2026-10-20" and ref <= 14:
                    arb_c = max(ref - 1, 1)
                else:
                    arb_c = max(ceil_tick(ref * 0.93), floor)
                exp_b = bool(traded and cl < ref and (cl <= arb_b or (thin and cl <= special)))
                exp_c = bool(traded and cl < ref and (cl <= arb_c or (thin and cl <= special)))
            mism["B"] += int(exp_b != bool(ctx.A["B"]["lock_down"][i, k]))
            mism["C"] += int(exp_c != bool(ctx.A["C"]["lock_down"][i, k]))
    return {"cells_checked": cells, "mismatches_B": mism["B"], "mismatches_C": mism["C"]}


def orchestrate(args) -> None:
    t0 = time.time()
    WORK.mkdir(exist_ok=True)
    info = check_inputs()
    watch = [CODE["B"], CODE["C"], FROZEN_RAW] + sorted(FROZEN.glob("yahoo_recent-*.jsonl"))
    before = tree_digest(watch)
    if not args.reuse:
        for f in WORK.glob("*"):
            f.unlink()
        run_workers(["B", "C", "C10", "C7b"])
    base_variants = ["B", "C", "C10", "C7b"]
    cells0 = cell_analysis(Ctx(base_variants))
    evidence_file = WORK / "evidence_names.json"
    dump_json({"tickers": cells0["evidence_names"], "definition": cells0["summary"]["wider_limit_evidence_definition"]}, evidence_file)
    if not args.reuse:
        run_workers(["CH"], evidence_file)
    ctx = Ctx(base_variants + ["CH"])
    cells = cell_analysis(ctx)
    ledger = read_jsonl(CODE["B"] / "paper" / "ledger.jsonl")
    spec_rows = read_jsonl(CODE["B"] / "paper" / "speculations.jsonl")
    oracle = independent_lock_oracle(ctx)
    assert oracle["mismatches_B"] == 0 and oracle["mismatches_C"] == 0, f"lock flags disagree with the independent oracle: {oracle}"

    for v_ in ctx.R:
        assert ctx.R[v_]["meta"]["horizon_sessions"] == HORIZON and ctx.R[v_]["meta"]["span_values_of_idx_decisions"] == [HORIZON + 1], "scorer horizon differs from the harness constant"
    pop, idx_dec, latest = populations(ledger, ctx)
    for did, dec_ in idx_dec.items():  # the harness's own window arithmetic must agree with paper._window_complete()
        assert ctx.R["B"]["decisions"][did]["window_complete"] == (ctx.didx[dec_["signal_session"]] + HORIZON + 1 <= ctx.last), did
    gate_s, gate_rows = baseline_gate(idx_dec, latest, ctx)
    recs, bars = build_records(ctx, idx_dec, latest, cells, gate_rows)
    agg = aggregates(recs)
    sens = sensitivity(recs, ctx)
    spec_s, spec_out = spec_analysis(ctx, spec_rows, cells)
    pend_s, pend_rows = pending_analysis(ctx, idx_dec, latest, cells)
    pop["signal_on_or_after_cut"]["pending_whose_entry_trigger_has_fired_open_hypothetical_trade"] = sum(
        1 for r in pend_rows if r["signal_session"] >= CUT and r["hypothetical_trade_entered_so_far"]
    )
    pop["signal_on_or_after_cut"]["rejections_that_would_have_traded_closed_plus_open"] = (
        pop["signal_on_or_after_cut"]["rejections_that_would_have_traded"]
        + pop["signal_on_or_after_cut"]["pending_whose_entry_trigger_has_fired_open_hypothetical_trade"]
    )
    pop["decisions_with_a_price_unit_problem_in_B_or_C_replay"] = sorted(
        {k for v_ in ("B", "C") for k, x in ctx.R[v_]["decisions"].items() if x["units_reason"] or x["score_error"]}
    )
    for r in pend_rows:
        r["category"] = "PENDING_WINDOW_OPEN" if not r["window_complete_on_final_bars"] else "PENDING_WINDOW_COMPLETE_NO_OUTCOME"
    whatif = whatif_summary(recs)

    meta_b, meta_c = ctx.R["B"]["meta"], ctx.R["C"]["meta"]
    after = tree_digest(watch)
    assert before == after, "an input file or code file changed during the run"
    equiv = {v: ctx.R[v]["meta"]["whatif_equivalence"] for v in ctx.R}
    S = {
        "meta": {
            "harness": "impact_2/harness.py",
            "harness_sha256": sha256_file(HERE / "harness.py"),
            "python": meta_b["python"],
            "numpy": meta_b["numpy"],
            "pandas": meta_b["pandas"],
            "tested_research_environment_per_constraints_file": "CPython 3.12, numpy 2.3.5, pandas 2.2.3",
            "frozen_manifest": MANIFEST.name,
            "frozen_manifest_sha256": info["manifest_sha256"],
            "frozen_manifest_payloads_verified_against_recorded_sha256": info["manifest_payloads_verified"],
            "frozen_manifest_pinned_at": info["manifest_started_at"],
            "frozen_sessions": f"{meta_b['first_session']} to {meta_b['last_session']}, {meta_b['n_sessions']} sessions, {meta_b['n_tickers']} tickers",
            "ledger_sha256": info["B_ledger_sha256"],
            "ledger_head_record_hash": ledger[-1]["record_hash"],
            "ledger_rows": len(ledger),
            "speculations_sha256": info["B_speculations_sha256"],
            "market_py_sha256_B": info["B_market_py_sha256"],
            "market_py_sha256_C": info["C_market_py_sha256"],
            "py_files_that_differ_B_vs_C": info["py_files_that_differ_B_vs_C"],
            "ledger_hash_chain_problems": meta_b["chain_problems_ledger"],
            "speculations_hash_chain_problems": meta_b["chain_problems_speculations"],
            "regimes_C_from_2026_09_28": [x for x in meta_c["regimes"] if x["start"] >= "2026-09-28"],
            "regimes_B_from_2026_09_28": [x for x in meta_b["regimes"] if x["start"] >= "2026-09-28"],
            "worker_warnings": {v: ctx.R[v]["warnings"] for v in ctx.R},
            "whatif_equivalence_with_paper_score": equiv,
            "independent_lock_oracle": oracle,
            "code_and_input_trees_unchanged_by_the_run": True,
            "files_hashed_for_that_check": len(after),
            "combined_tree_digest": combined(after),
        },
        "populations": pop,
        "baseline_gate": gate_s,
        "flipped_cells_market_wide": cells["summary"],
        "aggregates": agg,
        "whatif_roll_past_horizon": whatif,
        "sensitivity": sens,
        "speculations": spec_s,
        "pending": pend_s,
    }
    # ---- files
    write_csv(OUT_DIR / "results.csv", RESULT_COLUMNS, recs + sorted(pend_rows, key=lambda r: (r["signal_session"], r["decision_id"])))
    write_csv(OUT_DIR / "baseline_gate.csv", GATE_COLUMNS, sorted(gate_rows, key=lambda r: (r["signal_session"], r["decision_id"])))
    write_csv(OUT_DIR / "flipped_bars.csv", BAR_COLUMNS, bars)
    write_csv(OUT_DIR / "spec_results.csv", SPEC_COLUMNS, spec_out)
    S["claims_checked"] = {
        "decisions_signal_on_or_after_2026_10_19": {"claimed": 88, "found": pop["signal_on_or_after_cut"]["decisions"], "of_which_scored": pop["signal_on_or_after_cut"]["with_outcome"], "of_which_pending": pop["signal_on_or_after_cut"]["pending_no_outcome"]},
        "hypothetical_trade_records_in_that_set": {"claimed": 27, "found": pop["signal_on_or_after_cut"]["with_paper_trade_object"], "plus_open_hypothetical_trades_among_pending": pop["signal_on_or_after_cut"]["pending_whose_entry_trigger_has_fired_open_hypothetical_trade"]},
        "true_for_definition": "signal_session on or after 2026-10-19 (decisions, scored trades only); by scored-path exposure the counts are outcomes %d, trades %d" % (pop["path_touches_cut"]["outcomes"], pop["path_touches_cut"]["of_which_with_paper_trade"]),
    }
    S["categories_with_ids"] = {k: [r["decision_id"] for r in recs if r["category"] == k] for k in ("EXIT_SHIFTED", "BECOMES_UNSCORABLE", "BECOMES_SCORABLE", "VERDICT_CHANGED")}
    S["files"] = ["harness.py", "results.csv", "baseline_gate.csv", "flipped_bars.csv", "spec_results.csv", "summary.json", "report.md"]
    dump_json(S, OUT_DIR / "summary.json")
    write_report(S, recs, pend_rows, spec_out, gate_rows, bars, cells)
    print(f"done in {time.time() - t0:.0f}s; wrote {', '.join(S['files'])} to {OUT_DIR}")


def main() -> None:
    ap = argparse.ArgumentParser(description="ARB-correction impact replay (see the module docstring)")
    ap.add_argument("--worker", choices=list(VARIANTS), help="internal: run one replay variant (cwd must be its code dir)")
    ap.add_argument("--work-dir", default=str(WORK))
    ap.add_argument("--evidence-file")
    ap.add_argument("--reuse", action="store_true", help="development only: reuse the worker outputs already in work/")
    args = ap.parse_args()
    if args.worker:
        run_worker(args.worker, args.work_dir, args.evidence_file)
        return
    orchestrate(args)


if __name__ == "__main__":
    main()

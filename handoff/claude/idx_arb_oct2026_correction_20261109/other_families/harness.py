#!/usr/bin/env python3
"""Impact analyst 3 (addendum): the October-2026 IDX lower-limit (ARB) correction and the OTHER persisted record families.

ONE COMMAND:   python3 harness.py        (about 2 minutes, no network; writes next to this file)

What it does, end to end
  0. Preflight: the frozen price manifest and every raw payload it names (sha256); B and C code identical except
     idxsig/market.py; the committed paper/ snapshot identical to the copies inside the code dirs and to the base commit.
  1. Hermetic overlays (work/B, work/C): byte-identical copies of each variant's idxsig package, a copy of the committed
     paper/*.jsonl|md snapshot (so every ledger-reading function reads the copy, never a live file), a read-only symlink
     to the repository's research/ folder (protocols, warm start) and to the frozen raw Yahoo payloads. Hash/stat
     snapshots taken before and after prove that nothing in the two code dirs, the repository or the frozen inputs changed.
  2. Static census: every caller of lock_down / sellable / next_sellable / rolled_sessions / execute( / simulate( /
     resolve_set / score( / limits( / Market.build / from_panel; every persisted record family under paper/ with its IDX
     row count, whether and how it depends on the lock, and whether it can be replayed.
  3. Replay, one subprocess per variant (cwd = the overlay, sys.path.insert(0, ".")): the real paper.load_recent,
     paper._market, us_actions.yahoo_events on the FINAL PULL (2026-11-06, the only surviving raw pull) and the real
     catalysts.resolve_set (the 14 IDX_INDEX RUNUP rows: the priority), plus, as cross-checks of the earlier work,
     speculation.resolve_set (23 IDX rows) and paper.scoring_units/score (93 IDX ledger OUTCOME rows), under B (shipped
     rules) and C (corrected rules). These are FINAL-BAR REPLAYS: a rolled sale is resolved with the bars up to
     2026-11-06; a roll that runs past the last bar leaves the row pending.
  4. Baseline gate: the B replay must reproduce each recorded row, field by field (numbers within 1e-12, everything
     else exactly); every difference is diagnosed before any C number is read.
  5. The register's own statistics (catalysts.statistics / render) on the recorded rows, the B-replayed rows and the
     C-replayed rows, compared with the published line in paper/CATALYSTS.md.
  6. Second-order family learner_v2: re-forecast with the learner's own functions from each record's own ledger prefix
     under the recorded labels, the B-replayed labels and the C-replayed labels (two timing treatments).
  7. Writes results.csv, trades.csv, baseline_gate.csv, family_census.csv, lock_cells_changed.csv, learner_changes.csv,
     code_callers.txt, summary.json, run_meta.json, report.md (every number in the report comes from this run). Compares
     the deterministic outputs with those of the previous run in this folder and says so in the report.

Options: --keep-work (keep work/), --no-clean-check (skip the before/after tree snapshots).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad")
ARB2 = SCRATCH / "arb2"
CODE = {"B": ARB2 / "code_B" / "idx-signals", "C": ARB2 / "code_C" / "idx-signals"}
REPO = Path("/home/user/kod-arb-fix")
REPO_PAPER = REPO / "idx-signals" / "paper"
REPO_RESEARCH = REPO / "idx-signals" / "research"
BASE_COMMIT = "04927b3c4"
FROZEN = SCRATCH / "arb" / "frozen_inputs"
MANIFEST = FROZEN / "yahoo_recent-20261106T101853Z.jsonl"  # the final pull (920 tickers)
MANIFEST_SHA12 = "3a27d3445b3d"
RAW_ROOT = FROZEN / "yahoo_recent_raw"
ORIG_MANIFEST = FROZEN / "yahoo_recent-20261030T104351Z.jsonl"  # the pull the 14 RUNUP rows were written on (manifest only)
CUTOFF = "2026-10-19"  # first session of the new lower-limit regime
TOL = 1e-12  # numeric tolerance of the baseline gate
WORK = HERE / "work"
OUTD = WORK / "out"
IGNORE = {"resolved_at", "scored_at", "data", "prev_hash", "record_hash", "revises", "revision_reason"}  # stamps, never replayed
DET_FILES = ["results.csv", "trades.csv", "baseline_gate.csv", "family_census.csv", "lock_cells_changed.csv",
             "learner_changes.csv", "code_callers.txt", "summary.json"]  # deterministic outputs (compared between runs)
SCOPE = {"catalysts.jsonl": "catalyst_register_IDX", "speculations.jsonl": "speculation_register_IDX (cross-check)",
         "ledger.jsonl": "ledger_OUTCOME_IDX (cross-check)"}

# ====================================================================================================== utilities


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def flatten(x, path=""):
    if isinstance(x, dict):
        for k in sorted(x):
            yield from flatten(x[k], f"{path}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from flatten(v, f"{path}/{i}")
    else:
        yield path, x


def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def compare_records(a, b, ignore=IGNORE, tol=TOL) -> dict:
    """Field-by-field comparison of two records (recursive leaves). b None means 'no record'."""
    if b is None:
        return {"comparable": False, "n_leaves": 0, "n_numeric": 0, "max_abs_numeric": None, "n_numeric_diff": 0,
                "n_numeric_over_tol": 0, "numeric_diff_fields": [], "mismatch": ["<no replayed record>"], "missing": [], "mismatch_values": {}}
    fa = dict(flatten({k: v for k, v in a.items() if k not in ignore}))
    fb = dict(flatten({k: v for k, v in b.items() if k not in ignore}))
    n_num, mx, ndiff, nover, numfields, mismatch, missing, values = 0, 0.0, 0, 0, set(), [], [], {}
    for k in sorted(set(fa) | set(fb)):
        if k not in fa or k not in fb:
            missing.append(k)
            continue
        x, y = fa[k], fb[k]
        if _isnum(x) and _isnum(y):
            n_num += 1
            d = abs(float(x) - float(y))
            if d > 0:
                ndiff += 1
                numfields.add(re.sub(r"/\d+", "/#", k))
            mx = max(mx, d)
            if d > tol:
                nover += 1
                mismatch.append(k)
                values[k] = (x, y)
        elif x != y:
            mismatch.append(k)
            values[k] = (x, y)
    return {"comparable": True, "n_leaves": len(set(fa) | set(fb)), "n_numeric": n_num, "max_abs_numeric": mx,
            "n_numeric_diff": ndiff, "n_numeric_over_tol": nover, "numeric_diff_fields": sorted(numfields),
            "mismatch": mismatch, "missing": missing, "mismatch_values": values}


def fmt(x):
    if x is None:
        return ""
    if isinstance(x, float):
        return repr(x)
    return str(x)


def pct(x, nd=2):
    return "n/a" if x in (None, "") else f"{float(x):+.{nd}%}"


def write_csv(path, rows, cols):
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([fmt(r.get(c)) for c in cols])


def tree_snapshot(root: Path, sha: bool = True, skip_dirs=()) -> dict:
    """{relative path: (kind, size, mtime_ns, sha256|None)} of a tree (symlinked directories are not followed)."""
    snap, root = {}, Path(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for d in dirnames:
            p = Path(dirpath) / d
            snap[str(p.relative_to(root)) + "/"] = ("symlink" if p.is_symlink() else "dir", 0, 0, None)
        for f in filenames:
            p = Path(dirpath) / f
            st = p.lstat()
            snap[str(p.relative_to(root))] = ("file", st.st_size, st.st_mtime_ns, sha256_file(p) if (sha and p.is_file() and not p.is_symlink()) else None)
    return snap


def np_default(o):
    import numpy as np

    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def is_idx(row) -> bool:
    return (row.get("market") or "IDX") == "IDX"  # a ledger row without `market` is IDX (written before policy v3)


# =========================================================================================== census (static part)
CALLER_PATTERNS = ["lock_down", "sellable", "next_sellable", "rolled_sessions", r"\bexecute\(", r"\bsimulate\(", "resolve_set",
                   r"\bscore\(", r"\blimits\(", r"Market\.build", r"Market\.from_panel", r"\bfrom_panel\("]
ROLE_BY_FILE = {  # what each module does with the lock, from reading it
    "market.py": "DEFINES the limits (the only file B and C differ in)",
    "execution.py": "BUILDS lock_down (Market.build) and USES it in execute(): sellable = tradeable & ~lock_down, roll to next_sellable",
    "speculation.py": "USES lock_down in simulate() (sellable(k)); resolve_set writes speculations.jsonl RESOLUTION rows",
    "catalysts.py": "resolve_set() calls speculation.simulate for the candidate and twins; writes catalysts.jsonl RESOLUTION rows",
    "paper.py": "score(): the legacy loop uses lock_down; _score_plan() calls execution.execute; writes ledger.jsonl OUTCOME rows",
    "learner2.py": "no lock use; trains on the registers' graded statements (indirect)",
    "learner3.py": "no lock use; US only",
    "panel.py": "limits() for the panel quality summary (below_arb counts); not a paper/ record",
    "idx_events.py": "research event study (execute); results are not paper/ records",
    "event_study.py": "research event study (execute)", "backtest.py": "research backtest (Market.from_panel, execute)",
    "e1.py": "research E1 backtest", "e5.py": "research E5 backtest", "cli.py": "command wiring; corporate-action registry build; no lock use",
    "breakout.py": "research helper (Market)", "rules/__init__.py": "exposes lock_down to rule views; no rule file reads it",
}


def caller_scan(root: Path) -> tuple[list[str], dict]:
    pats = [(p, re.compile(p)) for p in CALLER_PATTERNS]
    lines, per_file = [], defaultdict(set)
    for path in sorted((root / "idxsig").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root / "idxsig").as_posix()
        for i, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for p, rx in pats:
                if rx.search(text):
                    lines.append(f"[{p}] idxsig/{rel}:{i}: {text.strip()}")
                    per_file[rel].add(p)
    return lines, {k: sorted(v) for k, v in per_file.items()}


def _walk_keys(x, keys, out):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in keys and isinstance(v, str):
                out.append(v[:10])
            else:
                _walk_keys(v, keys, out)
    elif isinstance(x, list):
        for v in x:
            _walk_keys(v, keys, out)
    return out


def session_fields(row) -> list[str]:
    """Every session date in a record (signal, entry, exit, scan session), recursively."""
    return _walk_keys(row, ("signal_session", "session", "entry_session", "exit_session", "time_exit_session"), [])


def exit_sessions(row) -> list[str]:
    return _walk_keys(row, ("exit_session",), [])


def build_census(paper: Path) -> list[dict]:
    """One row per (file, IDX record family) with counts computed from the committed snapshot."""
    led, spec, cat = (load_jsonl(paper / n) for n in ("ledger.jsonl", "speculations.jsonl", "catalysts.jsonl"))
    l1, l2, l3 = (load_jsonl(paper / n) for n in ("learner.jsonl", "learner_v2.jsonl", "learner_v3.jsonl"))
    book, acct, cacct, prem = (load_jsonl(paper / n) for n in ("paper_book.jsonl", "paper_account.jsonl", "crypto_account.jsonl", "premove_shadow.jsonl"))
    sens, micro = load_jsonl(paper / "sensors" / "sensors.jsonl"), load_jsonl(paper / "microstructure" / "crypto.jsonl")
    rows = []

    def add(file, family, sel, depends, kind, path, replay, touch=None, exposed=None, note=""):
        t = (lambda r: max(session_fields(r) or [""]) >= CUTOFF) if touch is None else touch
        rows.append({"file": file, "record_family": family, "idx_rows": len(sel), "idx_rows_touching_on_or_after_cutoff": sum(1 for r in sel if t(r)),
                     "idx_rows_exposed_to_lock": exposed(sel) if exposed else "", "depends_on_lock": depends, "dependence": kind,
                     "code_path": path, "replayable_from_final_pull": replay, "note": note})

    dec = {r["decision_id"]: r for r in led if r["type"] == "DECISION"}
    sold_late = lambda sel: sum(1 for r in sel if any(s >= CUTOFF for s in exit_sessions(r)))  # noqa: E731
    sel = lambda rs, typ, **kw: [r for r in rs if r["type"] == typ and is_idx(r) and all(r.get(k) == v for k, v in kw.items())]  # noqa: E731
    add("ledger.jsonl", "SCAN (market absent = IDX)", sel(led, "SCAN"), "no", "none",
        "paper.scan_frame and the rules read lock_up, never lock_down (grep); ARA is identical in B and C", "n/a (no lock dependence)")
    add("ledger.jsonl", "DECISION (market absent = IDX)", sel(led, "DECISION"), "no", "none",
        "paper._decide_v3 sizes on the hard-coded Policy.max_stop_distance 0.15 and prints '15% below the entry'; it never calls market.limits",
        "n/a", note="the 15% sizing constant and text are stale after 2026-10-19 but are policy constants, not market.py")
    add("ledger.jsonl", "OUTCOME (IDX)", sel(led, "OUTCOME"), "yes (direct)", "direct",
        "paper.score_pending -> paper.score -> the legacy v3 loop (sellable = tradeable & ~lock_down; used by all 93 recorded rows) or _score_plan -> execution.execute (roll to next_sellable; E3-plan decisions, none recorded)",
        "yes (replayed here as a cross-check of the earlier work)", touch=lambda r: max(session_fields(r) + session_fields(dec.get(r["decision_id"], {})) + [""]) >= CUTOFF, exposed=sold_late,
        note="'exposed' = a trade sold on or after 2026-10-19, the only place the lock can enter")
    add("speculations.jsonl", "SPECULATION_SET (IDX)", sel(spec, "SPECULATION_SET"), "no", "none", "speculation.build_set: twins and signal from the scan's features", "n/a")
    add("speculations.jsonl", "RESOLUTION BASE5 (IDX)", sel(spec, "RESOLUTION", window="BASE5"), "yes (direct)", "direct",
        "speculation.resolve_set -> simulate(): sellable(k) = tradeable & ~lock_down; x = first sellable session >= target, None (pending) if none",
        "yes (replayed here as a cross-check of the earlier work)", exposed=sold_late)
    add("speculations.jsonl", "RESOLUTION NEXT1 (IDX)", sel(spec, "RESOLUTION", window="NEXT1"), "no", "none",
        "path window: next_return() uses closes only", "yes (replayed here with the 23)", touch=lambda r: (r.get("resolved_at") or "")[:10] >= CUTOFF)
    for typ, dep, kind, path, rep in (
        ("BATCH", "no", "none", "catalysts.idx_index_batch: event list statuses", "n/a"),
        ("CATALYST_SET", "no", "none", "catalysts.idx_index_batch: twins by draw_twins from the scan's features", "n/a"),
        ("TAG", "no", "none", "catalysts.dilution_tags: EmitenNews headlines", "n/a"),
        ("RESOLUTION", "yes (direct)", "direct", "catalysts.resolve_set -> speculation.simulate for the candidate and each twin: sellable(k) = tradeable & ~lock_down; the sale rolls to the next sellable session",
         "yes (the priority of this addendum)"),
    ):
        add("catalysts.jsonl", f"{typ} (IDX_INDEX)", sel(cat, typ), dep, kind, path, rep, exposed=sold_late if typ == "RESOLUTION" else None,
            touch=(lambda r: (r.get("sealed_at") or r.get("made_at") or "")[:10] >= CUTOFF) if typ in ("BATCH", "TAG") else None)
    us_cat = [r for r in cat if not is_idx(r)]
    add("catalysts.jsonl", "US families (BATCH/CATALYST_SET/TAG)", us_cat, "no", "none", "US markets are built with price_limits=False: lock_down is all False", "n/a (IDX rows: 0)",
        note=f"the counted 'IDX rows' here are zero; the {len(us_cat)} US rows are listed for completeness only")
    rows[-1]["idx_rows"], rows[-1]["idx_rows_touching_on_or_after_cutoff"] = 0, 0
    has_label = lambda r: "IDX_INDEX:WITH_FLOW_RUNUP" in (r.get("training") or {}).get("live_rows", {})  # noqa: E731
    add("learner_v2.jsonl", "LEARNER2_FORECAST (SPEC_IDX)", [r for r in l2 if is_idx(r)], "yes (indirect: training labels)", "indirect (training labels)",
        "learner2.train -> live_rows -> outcomes() reads RESOLUTION cone outcomes: IDX_INDEX WITH_FLOW_RUNUP (shared RELATIVE slope) and SPEC_IDX BASE5 statements (anchors)",
        "yes (the learner's own _record() on each record's ledger prefix, with replayed labels)", exposed=lambda s: sum(1 for r in s if has_label(r)),
        note="'exposed' = the record's training rows include the 14 IDX_INDEX WITH_FLOW_RUNUP labels")
    n_non = [r for r in l2 if not is_idx(r)]
    rows.append({"file": "learner_v2.jsonl", "record_family": "LEARNER2_FORECAST (US/CRYPTO rows: not IDX)", "idx_rows": 0, "idx_rows_touching_on_or_after_cutoff": 0,
                 "idx_rows_exposed_to_lock": "", "depends_on_lock": "indirect only (shared slope)", "dependence": "indirect (shared slope)", "code_path": "the same labels reach US/CRYPTO forecasts through the shared RELATIVE slope",
                 "replayable_from_final_pull": "yes (same replay)", "note": f"{len(n_non)} non-IDX rows, {sum(1 for r in n_non if has_label(r))} of them trained on the IDX_INDEX labels"})
    add("learner_v3.jsonl", "LEARNER3_FORECAST (SPEC_US)", [r for r in l3 if is_idx(r)], "no", "none", "US only; trains on SPEC_US rows and its own forecasts", "n/a (IDX rows: 0)")
    add("learner.jsonl", "LEARNER_FORECAST (SEC13D)", [r for r in l1 if is_idx(r) and r.get("family") != "SEC13D"], "no", "none", "US SEC13D only", "n/a (IDX rows: 0)")
    idx_pat = re.compile(r"SCAN-\d{4}-")  # IDX set ids carry no market infix
    add("paper_book.jsonl", "BOOK_PLAN", [r for r in book if idx_pat.search(r.get("set_id", ""))], "no", "none", "US spikes only", "n/a (IDX rows: 0)")
    add("paper_account.jsonl", "ACCT_*", [r for r in acct if idx_pat.search(r.get("set_id", ""))], "no", "none", "exec_us on US bars only", "n/a (IDX rows: 0)")
    add("crypto_account.jsonl", "ACCT_* / CRYPTO_QUOTE", [r for r in cacct if idx_pat.search(r.get("set_id", ""))], "no", "none", "crypto", "n/a (IDX rows: 0)")
    add("premove_shadow.jsonl", "PREMOVE_SHADOW_*", [r for r in prem if idx_pat.search(json.dumps(r)[:400])], "no", "none", "crypto (Binance) only", "n/a (IDX rows: 0)")
    add("microstructure/crypto.jsonl", "TIMELINE/BOOK", [r for r in micro if idx_pat.search(r.get("scan_id", ""))], "no", "none", "crypto order books", "n/a (IDX rows: 0)")
    add("sensors/sensors.jsonl", "SENSOR_ALERT emitennews_dilution (IDX-related)", [r for r in sens if r.get("source") == "emitennews_dilution"], "no", "none", "news headlines, no prices", "n/a",
        touch=lambda r: (r.get("observed_at") or "")[:10] >= CUTOFF)
    scans = sorted(p.name for p in (paper / "scans").iterdir() if p.is_dir()) if (paper / "scans").exists() else []
    idx_scans = [n for n in scans if not n.startswith(("SCAN-US-", "SCAN-CRYPTO-"))]
    rows.append({"file": "scans/", "record_family": "scan directories (IDX = no market infix)", "idx_rows": len(idx_scans),
                 "idx_rows_touching_on_or_after_cutoff": sum(1 for n in idx_scans if re.search(r"(\d{4}-\d{2}-\d{2})", n).group(1) >= CUTOFF), "idx_rows_exposed_to_lock": "",
                 "depends_on_lock": "no", "dependence": "none", "code_path": "features.csv built by rules that read lock_up only", "replayable_from_final_pull": "n/a", "note": ""})
    for name, what in (("catalysts_form4/", "EDGAR Form 4 dumps (US)"), ("timestamps/", "RFC 3161 tokens"), ("sensors/raw/", "raw feed pulls"), ("microstructure/raw/", "crypto raw books")):
        rows.append({"file": name, "record_family": what, "idx_rows": 0, "idx_rows_touching_on_or_after_cutoff": 0, "idx_rows_exposed_to_lock": "", "depends_on_lock": "no",
                     "dependence": "none", "code_path": "no price or lock input", "replayable_from_final_pull": "n/a", "note": ""})
    for name in ("README.md", "CATALYSTS.md", "SPECULATIONS.md", "LEARNER_V2.md", "LEARNER_V3.md", "CALL_CERT.md", "PAPER_ACCOUNT.md", "PAPER_BOOK.md", "CRYPTO_ACCOUNT.md", "LEARNER.md", "PREMOVE_SHADOW.md"):
        rows.append({"file": name, "record_family": "derived report (rendered from the ledgers)", "idx_rows": "", "idx_rows_touching_on_or_after_cutoff": "", "idx_rows_exposed_to_lock": "",
                     "depends_on_lock": "only through the ledgers it renders", "dependence": "derived", "code_path": "catalysts.render / speculation render / learner render",
                     "replayable_from_final_pull": "the IDX_INDEX section of CATALYSTS.md is re-rendered here", "note": ""})
    return rows


# ================================================================================================ overlays and checks
def preflight() -> dict:
    info = {}
    sha = sha256_file(MANIFEST)
    assert sha.startswith(MANIFEST_SHA12), f"manifest sha {sha}"
    parsed = [json.loads(x) for x in MANIFEST.read_text(encoding="utf-8").splitlines() if x.strip()]
    header, recs = parsed[0], parsed[1:]
    assert len(recs) == 920 and header["n_files"] == 920 and header["ok"] == 920, "manifest is not the 920-ticker final pull"
    bad = []
    for r in recs:
        p = RAW_ROOT / Path(r["path"]).relative_to("data/raw/yahoo_recent")
        if not p.exists() or sha256_file(p) != r["sha256"]:
            bad.append(r["ticker"])
    assert not bad, f"raw payloads missing or hash mismatch: {bad[:5]} ({len(bad)})"
    info["manifest"] = {"file": MANIFEST.name, "sha256": sha, "n_tickers": len(recs), "coverage_window": header["coverage_window"], "finished_at": header["finished_at"],
                        "payloads_verified": len(recs), "first_date_sample": recs[0]["first_date"]}
    om = [json.loads(x) for x in ORIG_MANIFEST.read_text(encoding="utf-8").splitlines() if x.strip()]
    info["orig_manifest"] = {"file": ORIG_MANIFEST.name, "sha256": sha256_file(ORIG_MANIFEST), "coverage_window": om[0]["coverage_window"], "first_date_sample": om[1]["first_date"],
                             "raw_payloads_present": (RAW_ROOT / "20261030T104351Z").exists()}
    hashes = {v: {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted((root / "idxsig").rglob("*")) if p.is_file() and "__pycache__" not in p.parts} for v, root in CODE.items()}
    diff = sorted(k for k in set(hashes["B"]) | set(hashes["C"]) if hashes["B"].get(k) != hashes["C"].get(k))
    assert diff == ["idxsig/market.py"], f"B and C differ in {diff}"
    info["code"] = {"n_files": len(hashes["B"]), "differing_files": diff, "market_sha256": {v: hashes[v]["idxsig/market.py"] for v in "BC"}}
    ident = {}
    for name in ("ledger.jsonl", "speculations.jsonl"):
        shas = {v: sha256_file(CODE[v] / "paper" / name) for v in "BC"}
        shas["repo"] = sha256_file(REPO_PAPER / name)
        try:
            blob = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE_COMMIT}:idx-signals/paper/{name}"], capture_output=True, check=True).stdout
            shas["base_commit"] = hashlib.sha256(blob).hexdigest()
        except Exception as exc:  # noqa: BLE001 - git is optional evidence
            shas["base_commit"] = f"unavailable ({type(exc).__name__})"
        assert len({v for v in shas.values() if not v.startswith("unavailable")}) == 1, f"{name} differs: {shas}"
        ident[name] = shas
    info["paper_snapshot_identity"] = ident
    eq = {}
    for p in sorted(REPO_PAPER.glob("*.jsonl")):
        try:
            blob = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE_COMMIT}:idx-signals/paper/{p.name}"], capture_output=True, check=True).stdout
            eq[p.name] = hashlib.sha256(blob).hexdigest() == sha256_file(p)
        except Exception:  # noqa: BLE001
            eq[p.name] = None
    info["paper_jsonl_equal_to_base_commit"] = eq
    return info


def build_overlay(v: str) -> Path:
    base = WORK / v
    root = base / "idx-signals"
    (root / "paper").mkdir(parents=True)
    (root / "data" / "raw").mkdir(parents=True)
    shutil.copytree(CODE[v] / "idxsig", root / "idxsig", ignore=shutil.ignore_patterns("__pycache__"))
    for f in sorted(list(REPO_PAPER.glob("*.jsonl")) + list(REPO_PAPER.glob("*.md"))):
        shutil.copy2(f, root / "paper" / f.name)
    (root / "research").symlink_to(REPO_RESEARCH)
    (root / "data" / "raw" / "yahoo_recent").symlink_to(RAW_ROOT)
    for p in sorted((CODE[v] / "idxsig").rglob("*")):  # the copy is byte-identical
        if p.is_file() and "__pycache__" not in p.parts:
            assert sha256_file(p) == sha256_file(root / "idxsig" / p.relative_to(CODE[v] / "idxsig")), f"overlay copy differs: {p}"
    return root


def run_worker(kind: str, arg: str, cwd: Path) -> float:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "LC_ALL": "C.UTF-8", "HOME": str(WORK)}
    t0 = time.time()
    p = subprocess.run([sys.executable, "-I", "-B", str(HERE / "harness.py"), "--worker", kind, arg], cwd=cwd, env=env, capture_output=True, text=True)
    dt = time.time() - t0
    sys.stdout.write(f"  worker {kind} {Path(arg).name}: rc={p.returncode} in {dt:.1f}s\n")
    if p.returncode != 0:
        sys.stderr.write(p.stdout[-3000:] + "\n" + p.stderr[-6000:] + "\n")
        raise SystemExit(f"worker {kind} {arg} failed")
    return dt


# ============================================================================================ worker: replay (B or C)
def worker_replay(variant: str) -> None:
    """Runs inside work/<variant>/idx-signals with `import idxsig` resolving to that overlay's copy."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, ".")
    import warnings

    import numpy as np
    import pandas as pd

    import idxsig
    from idxsig import catalysts as cat
    from idxsig import market as mk
    from idxsig import paper, speculation as spec, us_actions

    cwd = Path.cwd().resolve()
    assert Path(idxsig.__file__).resolve() == cwd / "idxsig" / "__init__.py", idxsig.__file__
    assert Path(mk.__file__).resolve() == cwd / "idxsig" / "market.py"
    t0 = time.time()
    out = {"variant": variant, "idxsig_file": str(Path(idxsig.__file__).resolve()), "market_sha256": sha256_file(mk.__file__),
           "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}}
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        df, data = paper.load_recent(MANIFEST, "IDX", purpose="scoring")
        m = paper._market(df, "IDX")
        events = us_actions.yahoo_events(MANIFEST, market="IDX")
        out["data"] = {"manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"], "rows": int(len(df)), "tickers": int(m.shape[0]), "sessions": int(m.shape[1]),
                       "first_session": str(m.dates[0]), "last_session": str(m.dates[-1]), "split_events": int(len(events))}
        dates, tick = [str(x) for x in m.dates], [str(x) for x in m.tickers]
        tick_ix = {t: i for i, t in enumerate(tick)}
        # the limits as Market.build sees them, recomputed here to check the lock formula and to record the ARB prices
        ref = np.where(np.isfinite(m.prev) & (m.prev > 0), m.prev, np.nan)
        safe_ref = np.nan_to_num(ref, nan=1.0)
        day_grid = np.broadcast_to(m.dates.astype("datetime64[D]"), m.close.shape)
        ara, arb = mk.limits(safe_ref, day_grid)
        sp_ara, sp_arb = mk.special_limits(safe_ref)
        one_price = (m.high == m.low) & (m.low == m.close)
        thin = one_price | (((m.close < 50) | (ref < 50)) & (day_grid < np.datetime64("2026-09-28")))
        ld = m.tradeable & np.isfinite(ref) & (m.close < ref) & ((m.close <= arb) | (thin & (m.close <= sp_arb)))
        lu = m.tradeable & np.isfinite(ref) & ((m.close >= ara) | (thin & (m.close >= sp_ara)))
        out["lock_formula_reproduced"] = bool((ld == m.lock_down).all() and (lu == m.lock_up).all())
        OUTD.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(OUTD / f"panel_{variant}.npz", tickers=np.array(tick), dates=np.array(dates), close=m.close, prev=m.prev, high=m.high, low=m.low, volume=m.volume,
                            present=m.present, tradeable=m.tradeable, lock_down=m.lock_down, lock_up=m.lock_up, arb=arb, ara=ara, sp_arb=sp_arb, one_price=one_price)

        def cell(n: int, k: int) -> dict:
            f = lambda a: None if not np.isfinite(a[n, k]) else float(a[n, k])  # noqa: E731
            return {"date": dates[k], "present": bool(m.present[n, k]), "tradeable": bool(m.tradeable[n, k]), "close": f(m.close), "prev": f(m.prev), "high": f(m.high),
                    "low": f(m.low), "volume": f(m.volume), "lock_down": bool(m.lock_down[n, k]), "lock_up": bool(m.lock_up[n, k]), "arb": f(arb), "ara": f(ara),
                    "sp_arb": f(sp_arb), "one_price": bool(one_price[n, k])}

        def trade_diags(rec, hold):
            """For the candidate and each twin (record order): the target session's cell, the exit session's cell and the cells in between."""
            if rec is None or hold is None:
                return None
            names = [rec["ticker"]] + [t["ticker"] for t in rec["twins"]]
            trades = [rec["candidate"].get("trade")] + [t.get("trade") for t in rec["twins"]]
            diag = []
            for name, tr in zip(names, trades):
                if not tr:
                    diag.append(None)
                    continue
                n, e, x = tick_ix[name], dates.index(tr["entry_session"]), dates.index(tr["exit_session"])
                diag.append({"name": name, "entry_idx": e, "target_idx": e + hold, "exit_idx": x, "rolled": x - (e + hold), "target": cell(n, e + hold),
                             "exit": cell(n, x), "path": [cell(n, k) for k in range(e + hold, x + 1)]})
            return diag

        cats, specs, led = cat.cat_lines(), spec.spec_lines(), paper.ledger_lines()
        csets = {r["set_id"]: r for r in cats if r["type"] == "CATALYST_SET"}
        ssets = {r["set_id"]: r for r in specs if r["type"] == "SPECULATION_SET"}
        decs = {r["decision_id"]: r for r in led if r["type"] == "DECISION"}
        reps = []
        for i, r in enumerate(cats):
            if r["type"] == "RESOLUTION" and is_idx(r):
                s = csets[r["set_id"]]
                new = cat.resolve_set(s, r["window"], m, events, None)
                reps.append({"file": "catalysts.jsonl", "line": i + 1, "source": r, "replay": new, "diag": trade_diags(new, s["windows"][r["window"]].get("holding_sessions")),
                             "extra": {"ticker": r["ticker"], "signal_session": r["signal_session"]}})
        for i, r in enumerate(specs):
            if r["type"] == "RESOLUTION" and is_idx(r):
                new = spec.resolve_set(ssets[r["set_id"]], r["window"], m, events, None)
                w = spec.windows()[r["window"]]
                reps.append({"file": "speculations.jsonl", "line": i + 1, "source": r, "replay": new, "diag": trade_diags(new, w.get("holding_sessions") if w["kind"] == "plan" else None),
                             "extra": {"ticker": r["ticker"], "signal_session": r["signal_session"]}})
        for i, rec in enumerate(led):  # score_pending's own steps, per recorded OUTCOME: scoring_units -> score -> the fields it adds
            if rec["type"] != "OUTCOME" or not is_idx(rec):
                continue
            d = decs[rec["decision_id"]]
            tev = events[events["ticker"] == d["instrument"]["ticker"]] if len(events) else events
            units, reason, evidence = paper.scoring_units(d, m, tev, None)
            new = None
            if units is not None:
                try:
                    new = paper.score(d, m, price_units=units)
                except ValueError as exc:  # the recorded close does not reconcile in these units
                    reason = f"{exc} (rtol {paper.RECONCILE_RTOL})"
            if new is not None:
                new["status"] = "SCORED"
                new.pop("price_scale_note", None)
                new.update(scorer=paper.SCORER_ID, preprocessing=paper.SCORING_PREPROCESSING["IDX"],
                           units={"actions": (units or {}).get("actions", []), "evidence": evidence, "convention": (units or {}).get("convention")})
            tr = (rec.get("execution") or {}).get("paper_trade") or {}
            final = paper.session_close("IDX", tr["exit_session"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if tr.get("exit_session") else None
            reps.append({"file": "ledger.jsonl", "line": i + 1, "source": rec, "replay": new, "diag": None, "reason": reason if new is None else None,
                         "extra": {"ticker": d["instrument"]["ticker"], "signal_session": d["signal_session"], "decision": d["decision"],
                                   "plan_type": "E3 execution plan" if (d.get("plan") or {}).get("execution_plan") else "legacy v3 plan", "scored_at": rec["scored_at"],
                                   "exit_bar_final_utc": final, "scored_before_exit_bar_final": bool(final and rec["scored_at"] < final)}})
        out["replays"] = reps
        # the register's own statistics, on the recorded rows and on this variant's replayed rows
        repl = {(x["source"]["set_id"], x["source"]["window"]): x["replay"] for x in reps if x["file"] == "catalysts.jsonl"}
        recs_v = []
        for r in cats:
            if r["type"] == "RESOLUTION" and (r["set_id"], r["window"]) in repl:
                if repl[(r["set_id"], r["window"])] is not None:
                    recs_v.append(repl[(r["set_id"], r["window"])])
            else:
                recs_v.append(r)
        st_rec, st_var = cat.statistics(cats), cat.statistics(recs_v)
        txt_rec, txt_var = cat.render(st_rec, cats), cat.render(st_var, recs_v)

        def idx_block(text):
            ls, block = text.splitlines(), []
            for i, l in enumerate(ls):
                if l.startswith("## IDX_INDEX"):
                    j = i
                    while j < len(ls) and (j == i or not ls[j].startswith("## ")):
                        block.append(ls[j])
                        j += 1
                    break
            return [b for b in block if b.strip()] + [l for l in ls if l.startswith("| IDX_INDEX |")]

        def slim(st):
            f = st["families"]["IDX_INDEX"]
            return {"n_sets": f["n_sets"], "sessions": f["sessions"], "n_resolutions": f["n_resolutions"], "RUNUP": f["RUNUP"], "POST20": f["POST20"], "calibration": f["calibration"]}

        out["stats_recorded"], out["stats_variant"] = slim(st_rec), slim(st_var)
        out["lines_recorded"], out["lines_variant"] = idx_block(txt_rec), idx_block(txt_var)
        published = (cwd / "paper" / "CATALYSTS.md").read_text(encoding="utf-8")
        out["published_lines"] = idx_block(published)
        out["chain_problems"] = {n: paper.verify_chain(cwd / "paper" / n) for n in ("ledger.jsonl", "catalysts.jsonl", "speculations.jsonl", "learner_v2.jsonl")}
    out["warnings"] = [[w.category.__name__, str(w.message)[:200]] for w in wl]
    out["elapsed_s"] = round(time.time() - t0, 1)
    (OUTD / f"replay_{variant}.json").write_text(json.dumps(out, default=np_default, allow_nan=False), encoding="utf-8")


# ============================================================================================ worker: learner replay
def worker_learner(worlds_path: str) -> None:
    """Runs inside work/B/idx-signals: the learner's own _record() on each recorded forecast's ledger prefix, with changed labels."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, ".")
    from datetime import timedelta

    import idxsig
    from idxsig import catalysts as cr
    from idxsig import learner2 as L2
    from idxsig import speculation as spec

    cwd = Path.cwd().resolve()
    assert Path(idxsig.__file__).resolve() == cwd / "idxsig" / "__init__.py"
    cat, spc = cr.cat_lines(), spec.spec_lines()
    lrecs = L2.lines()
    proto, sha = L2.protocol()
    batch_times = sorted({f["made_at"] for f in lrecs})
    never = "9999-12-31T00:00:00Z"

    def avail(day: str) -> str:  # the first learner batch on or after `day`, minus one second (the routine resolves, then forecasts)
        t = next((t for t in batch_times if t[:10] >= day), None)
        return never if t is None else (datetime.fromisoformat(t.replace("Z", "+00:00")) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def apply(world):
        lists = {"catalysts.jsonl": list(cat), "speculations.jsonl": list(spc)}
        for mod in world["mods"]:
            lst = lists[mod["file"]]
            row = lst[mod["line"] - 1]
            assert row["record_hash"] == mod["record_hash"], (mod["file"], mod["line"])
            new = dict(row)
            new.update(mod.get("content") or {})
            if mod.get("pending"):
                new["resolved_at"] = never
            elif mod.get("availability") == "last_exit_day":
                new["resolved_at"] = avail(mod["last_exit_day"])
            lst[mod["line"] - 1] = new
        return lists["catalysts.jsonl"], lists["speculations.jsonl"]

    results = {}
    for world in json.loads(Path(worlds_path).read_text(encoding="utf-8"))["worlds"]:
        cat_w, spc_w = apply(world)
        ctxs, recs = {}, []
        for i, f in enumerate(lrecs):
            inp = f["inputs"]
            nc, ns = inp["catalysts"][0], inp["speculations"][0]
            assert L2._head(cat[:nc]) == inp["catalysts"] and L2._head(spc[:ns]) == inp["speculations"], f"learner record {i}: its ledger prefix is not a prefix of the snapshot"
            prefix = [L2.as_set(r) for r in cat_w[:nc]] + [L2.as_set(r) for r in spc_w[:ns]]
            s = next(r for r in prefix if r.get("type") == "CATALYST_SET" and r["set_id"] == f["set_id"])
            key = (json.dumps(inp, sort_keys=True), f["made_at"])
            if key not in ctxs:
                ctxs[key] = L2._context(prefix, lrecs[:i], f["made_at"])
            again = L2._record(s, f["made_at"], proto, sha, inp, ctxs[key])
            body = {k: v for k, v in f.items() if k not in ("record_hash", "prev_hash")}
            diff = [k for k in sorted(set(body) | set(again)) if not L2._same(body.get(k), again.get(k), L2.VERIFY_TOL)]
            mx_raw = mx_pub = mx_anc = mx_dev = 0.0
            n_raw = n_pub = calls = 0
            pub_changes = []
            for stmt, fc in f["forecasts"].items():
                a = again["forecasts"][stmt]
                d = abs(fc["raw"] - a["raw"])
                mx_raw, n_raw = max(mx_raw, d), n_raw + (d > L2.VERIFY_TOL)
                d = abs(fc["published"] - a["published"])
                mx_pub, n_pub = max(mx_pub, d), n_pub + (d > L2.VERIFY_TOL)
                if d > L2.VERIFY_TOL:
                    pub_changes.append([stmt, fc["published"], a["published"]])
                mx_anc = max(mx_anc, abs(fc["anchor"] - a["anchor"]))
                if "deviation" in fc and "deviation" in a:
                    mx_dev = max(mx_dev, abs(fc["deviation"] - a["deviation"]))
                calls += fc.get("call") != a.get("call")
            recs.append({"i": i, "record_hash": f["record_hash"], "set_id": f["set_id"], "family": f["family"], "market": f["market"], "ticker": f["ticker"],
                         "signal_session": f["signal_session"], "made_at": f["made_at"], "fields_differing": diff, "n_statements": len(f["forecasts"]),
                         "n_raw_changed": int(n_raw), "n_published_changed": int(n_pub), "max_abs_raw": mx_raw, "max_abs_published": mx_pub, "max_abs_anchor": mx_anc,
                         "max_abs_deviation": mx_dev, "call_changes": int(calls), "published_changes": pub_changes,
                         "live_rows_recorded": {k: v for k, v in f["training"]["live_rows"].items() if k.startswith(("IDX_INDEX", "SPEC_IDX"))},
                         "live_rows_replayed": {k: v for k, v in again["training"]["live_rows"].items() if k.startswith(("IDX_INDEX", "SPEC_IDX"))}})
        results[world["name"]] = recs
    (OUTD / "learner_results.json").write_text(json.dumps({"worlds": results, "batch_times": batch_times, "verify_tol": L2.VERIFY_TOL}, default=np_default, allow_nan=False), encoding="utf-8")


# =========================================================================================================== aggregate
def last_exit(rec):
    ex = []
    if rec is None or not isinstance(rec.get("candidate"), dict):
        return None
    for t in [rec["candidate"].get("trade")] + [t.get("trade") for t in rec.get("twins", [])]:
        if t:
            ex.append(t["exit_session"])
    return max(ex) if ex else None


def trade_list(rec):
    """[(role, name, trade|None, status)] for the candidate and each twin of a RESOLUTION record (None if pending)."""
    if rec is None or not isinstance(rec.get("candidate"), dict):
        return None
    out = [("candidate", rec["ticker"], rec["candidate"].get("trade"), rec["candidate"].get("status"))]
    return out + [("twin", t["ticker"], t.get("trade"), t.get("status")) for t in rec.get("twins", [])]


def paper_trade(o):
    return ((o or {}).get("execution") or {}).get("paper_trade")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", choices=["replay", "learner"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--no-clean-check", action="store_true")
    args = ap.parse_args()
    if args.worker == "replay":
        return worker_replay(args.arg)
    if args.worker == "learner":
        return worker_learner(args.arg)

    import numpy as np

    assert sys.version_info >= (3, 12), "the report templates use nested f-string quotes (Python 3.12+)"
    started, T0 = datetime.now(timezone.utc), time.time()
    prev_hashes = {f: sha256_file(HERE / f) for f in DET_FILES if (HERE / f).exists()}
    print("== preflight")
    pre = preflight()
    snaps_before = {}
    if not args.no_clean_check:
        snaps_before = {"code_B": tree_snapshot(CODE["B"]), "code_C": tree_snapshot(CODE["C"]), "repo_paper": tree_snapshot(REPO_PAPER, True, ("timestamps", "scans", "raw")),
                        "repo_research": tree_snapshot(REPO_RESEARCH, False), "frozen_top": {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in FROZEN.iterdir() if p.is_file()}}
    pycache_pre = sorted(f"{p} (mtime {datetime.fromtimestamp(p.stat().st_mtime, timezone.utc):%Y-%m-%dT%H:%M:%SZ})" for v in CODE.values() for p in v.rglob("__pycache__"))
    print("== overlays")
    if WORK.exists():
        shutil.rmtree(WORK)
    OUTD.mkdir(parents=True)
    roots = {v: build_overlay(v) for v in "BC"}
    print("== static census")
    callers, per_file = caller_scan(roots["B"])
    rules_reading = sorted(f for f, pats in per_file.items() if f.startswith("rules/") and f != "rules/__init__.py" and "lock_down" in pats)
    assert not rules_reading, f"a rule file reads lock_down: {rules_reading}"
    (HERE / "code_callers.txt").write_text(
        "# Callers of the lower-limit machinery in the shipped (B) idxsig package; the matching pattern is in brackets.\n# Role of each module, from reading it:\n"
        + "".join(f"#   {k}: {v}\n" for k, v in sorted(ROLE_BY_FILE.items()))
        + f"# No file under idxsig/rules/ other than rules/__init__.py (which only lists the field names a rule may see) mentions lock_down: {not rules_reading}.\n\n" + "\n".join(callers) + "\n", encoding="utf-8")
    census = build_census(REPO_PAPER)
    print("== replay workers (final-bar replay on the 2026-11-06 pull)")
    times = {v: run_worker("replay", v, roots[v]) for v in "BC"}
    R = {v: json.loads((OUTD / f"replay_{v}.json").read_text(encoding="utf-8")) for v in "BC"}
    P = {v: np.load(OUTD / f"panel_{v}.npz") for v in "BC"}

    # ---------------------------------------------------------------------------------- panel-level comparison
    arr_eq = lambda a, b: bool(np.array_equal(a, b, equal_nan=True)) if a.dtype.kind == "f" else bool(np.array_equal(a, b))  # noqa: E731
    same = {k: arr_eq(P["B"][k], P["C"][k]) for k in ("tickers", "dates", "close", "prev", "high", "low", "volume", "present", "tradeable", "lock_up", "ara", "sp_arb", "one_price")}
    assert all(same.values()), same
    ld = {v: P[v]["lock_down"] for v in "BC"}
    diff = ld["B"] != ld["C"]
    only_c, only_b = diff & ld["C"] & ~ld["B"], diff & ld["B"] & ~ld["C"]
    at_limit, below_limit = only_c & (P["C"]["close"] == P["C"]["arb"]), only_c & (P["C"]["close"] < P["C"]["arb"])
    tickers, dates = [str(x) for x in P["B"]["tickers"]], [str(x) for x in P["B"]["dates"]]
    lock_rows = []
    for i, j in zip(*np.nonzero(diff)):
        prev, close = float(P["B"]["prev"][i, j]), float(P["B"]["close"][i, j])
        lock_rows.append({"ticker": tickers[i], "session": dates[j], "prev_close": prev, "close": close, "change": close / prev - 1 if prev > 0 else None, "arb_B": float(P["B"]["arb"][i, j]),
                          "arb_C": float(P["C"]["arb"][i, j]), "locked_B": bool(ld["B"][i, j]), "locked_C": bool(ld["C"][i, j]), "close_at_C_limit": bool(close == P["C"]["arb"][i, j]),
                          "one_price_bar": bool(P["B"]["one_price"][i, j]), "reference_at_most_14": prev <= 14, "volume": float(P["B"]["volume"][i, j])})
    lock_rows.sort(key=lambda r: (r["session"], r["ticker"]))
    write_csv(HERE / "lock_cells_changed.csv", lock_rows, ["ticker", "session", "prev_close", "close", "change", "arb_B", "arb_C", "locked_B", "locked_C", "close_at_C_limit",
                                                         "one_price_bar", "reference_at_most_14", "volume"])
    by_session = Counter(r["session"] for r in lock_rows)
    panel = {"cells": int(ld["B"].size), "sessions": len(dates), "tickers": len(tickers), "lock_down_cells_B": int(ld["B"].sum()), "lock_down_cells_C": int(ld["C"].sum()),
             "cells_locked_only_under_C": int(only_c.sum()), "cells_locked_only_under_B": int(only_b.sum()), "lock_up_cells_differing": int((P["B"]["lock_up"] != P["C"]["lock_up"]).sum()),
             "common_arrays_identical": same, "changed_cells_by_session": dict(sorted(by_session.items())), "changed_cells_before_cutoff": int(sum(v for k, v in by_session.items() if k < CUTOFF)),
             "changed_cells_with_reference_at_most_14": int(sum(r["reference_at_most_14"] for r in lock_rows)), "changed_cells_close_at_C_limit": int(at_limit.sum()),
             "changed_cells_close_below_C_limit": int(below_limit.sum()), "lock_formula_reproduced": {v: R[v]["lock_formula_reproduced"] for v in "BC"},
             "warnings": {v: R[v]["warnings"] for v in "BC"}}

    # data-side check of the schedule: do closes bunch at the 7% limit price after 2026-10-19 (and not before)?
    def hand_arr(prev_, pct_):
        x = prev_ * (1 - pct_)
        tick = np.where(x < 200, 1, np.where(x < 500, 2, np.where(x < 2000, 5, np.where(x < 5000, 10, 25))))
        return np.maximum(np.ceil(x / tick - 1e-9) * tick, 1)

    dts = np.array(dates)
    with np.errstate(invalid="ignore"):
        ok_ = P["B"]["tradeable"] & np.isfinite(P["B"]["prev"]) & (P["B"]["prev"] > 14) & (P["B"]["close"] < P["B"]["prev"])
        l7, l15 = hand_arr(P["B"]["prev"], 0.07), hand_arr(P["B"]["prev"], 0.15)
        wins = {"15% limit in force, 2026-04-20 to 2026-09-25": (dts < "2026-09-28"), "15% limit in force, 2026-09-28 to 2026-10-16": (dts >= "2026-09-28") & (dts < CUTOFF),
                f"7% limit claimed, {CUTOFF} to {dates[-1]}": dts >= CUTOFF}
        bunch = {}
        for name, mk_ in wins.items():
            m_ = ok_ & mk_[None, :]
            ns = int(mk_.sum())
            at7, at15, below7 = int((m_ & (P["B"]["close"] == l7)).sum()), int((m_ & (P["B"]["close"] == l15)).sum()), int((m_ & (P["B"]["close"] < l7)).sum())
            bunch[name] = {"sessions": ns, "falling_cells": int(m_.sum()), "close_exactly_at_7pct_limit_price": at7, "per_session_at_7pct": at7 / ns, "close_exactly_at_15pct_limit_price": at15,
                           "close_below_7pct_limit_price": below7, "per_session_below_7pct": below7 / ns}
    panel["limit_bunching"] = bunch

    # ---------------------------------------------------------------------------------- per-record comparison
    recs = []
    for xb, xc in zip(R["B"]["replays"], R["C"]["replays"]):
        assert (xb["file"], xb["line"]) == (xc["file"], xc["line"]) and xb["source"]["record_hash"] == xc["source"]["record_hash"]
        src, rb, rc = xb["source"], xb["replay"], xc["replay"]
        recs.append({"file": xb["file"], "line": xb["line"], "src": src, "B": rb, "C": rc, "dB": xb["diag"], "dC": xc["diag"], "extra": xb["extra"], "reasonB": xb.get("reason"), "reasonC": xc.get("reason"),
                     "gate": compare_records(src, rb), "cvb": compare_records(rb, rc) if rb is not None else compare_records(src, rc)})
    rid = lambda r: r["src"].get("set_id") or r["src"]["decision_id"]  # noqa: E731
    reproduced = lambda r: r["gate"]["comparable"] and not r["gate"]["mismatch"] and not r["gate"]["missing"]  # noqa: E731
    c_changes = lambda r: r["C"] is None or bool(r["cvb"]["mismatch"] or r["cvb"]["missing"])  # noqa: E731
    status_text = lambda o, reason: o["status"] if o is not None else ("PENDING (a sale rolls past the last bar)" if not reason else f"UNSCORABLE: {reason}")  # noqa: E731

    def diagnose(r):
        if reproduced(r):
            return ""
        g, ex = r["gate"], r["extra"]
        mv = g["mismatch_values"]
        if ex.get("scored_before_exit_bar_final"):
            return f"recorded outcome scored at {ex['scored_at']}, before its exit session's bar was final ({ex['exit_bar_final_utc']}): the replay reads the settled close"
        if mv and all(k.startswith("/cone/") and x is None and y is not None for k, (x, y) in mv.items()) and all(k.startswith("/cone/") for k in g["missing"]):
            return "recorded statements are ungraded (outcome null) but the final pull grades them: a bar the resolving pull lacked"
        if mv and g["n_numeric_over_tol"] == 0 and all(isinstance(x, bool) and isinstance(y, bool) for x, y in mv.values()):
            return f"knife-edge threshold: every number agrees within 1e-12 but a boolean flips ({', '.join(list(mv)[:3])})"
        return "unexplained"

    def indep(v, name, e_idx, target_idx, cost_in, cost_out):
        """Exit session and net return recomputed from the saved panel arrays alone (first sellable session at or after the target on the
        reference chain), without calling speculation.simulate: an independent check of every replayed trade."""
        n = tickers.index(name)
        ok = P[v]["tradeable"][n] & ~P[v]["lock_down"][n]
        k = next((k for k in range(target_idx, len(dates)) if ok[k]), None)
        if k is None:
            return None, None
        close, prev = P[v]["close"][n], P[v]["prev"][n]
        with np.errstate(divide="ignore", invalid="ignore"):
            level = np.exp(np.cumsum(np.where(P[v]["present"][n] & (prev > 0) & (close > 0), np.log(close / prev), 0.0)))
        return dates[k], float((level[k] / level[e_idx]) * (1 - cost_out) / (1 + cost_in) - 1)

    def hand_limit(prev, pct_):
        """The lower-limit price by hand: reference x (1 - pct) rounded UP to the tick of that price (tick bands 1/2/5/10/25 at 200/500/2000/5000)."""
        x = prev * (1 - pct_)
        tick = 1 if x < 200 else 2 if x < 500 else 5 if x < 2000 else 10 if x < 5000 else 25
        return float(max(math.ceil(x / tick - 1e-9) * tick, 1))

    results_rows, trade_rows, gate_rows = [], [], []
    for r in recs:
        src, rb, rc, f = r["src"], r["B"], r["C"], r["file"]
        g = r["gate"]
        gate_rows.append({"scope": SCOPE[f], "source_file": f, "source_line": r["line"], "record_id": rid(r), "window": src.get("window", ""), "record_hash": src["record_hash"],
                          "replay_status_B": status_text(rb, r["reasonB"]), "leaves_compared": g["n_leaves"], "numeric_leaves": g["n_numeric"], "numeric_leaves_not_bit_identical": g["n_numeric_diff"],
                          "max_abs_numeric_diff": g["max_abs_numeric"], "numeric_leaves_over_1e-12": g["n_numeric_over_tol"],
                          "nonnumeric_or_missing_mismatches": len(g["mismatch"]) - g["n_numeric_over_tol"] + len(g["missing"]), "reproduced_within_1e-12": reproduced(r),
                          "differing_numeric_fields": ";".join(g["numeric_diff_fields"]), "mismatching_paths": ";".join((g["mismatch"] + g["missing"])[:6]), "diagnosis": diagnose(r)})
        base = {"scope": SCOPE[f], "source_file": f, "source_line": r["line"], "record_id": rid(r), "record_hash": src["record_hash"], "market": "IDX", "ticker": r["extra"]["ticker"],
                "signal_session": r["extra"]["signal_session"], "B_reproduces_recorded": reproduced(r), "B_max_abs_numeric_diff": g["max_abs_numeric"], "C_changes_row": c_changes(r),
                "status_recorded": src.get("status", ""), "status_B": status_text(rb, r["reasonB"]), "status_C": status_text(rc, r["reasonC"]),
                "C_leaves_changed_vs_B": (len(r["cvb"]["mismatch"]) + len(r["cvb"]["missing"])) if rc is not None else ""}
        if f == "ledger.jsonl":
            tr = {"rec": paper_trade(src), "B": paper_trade(rb), "C": paper_trade(rc)}
            both = rb is not None and rc is not None and tr["B"] and tr["C"]
            ex_chg = bool(both and (tr["B"]["exit_session"] != tr["C"]["exit_session"] or tr["B"]["exit_reason"] != tr["C"]["exit_reason"]))
            results_rows.append({**base, "record_type": "OUTCOME", "family": "LEDGER", "window": "", "direction": "", "n_trades": 1 if tr["rec"] else 0,
                                 "n_trades_exit_changed_C_vs_B": int(ex_chg) if rc is not None else "", "n_trades_return_changed_C_vs_B": int(bool(both and abs(tr["B"]["net_return"] - tr["C"]["net_return"]) > TOL)) if rc is not None else "",
                                 "cand_exit_recorded": (tr["rec"] or {}).get("exit_session", ""), "cand_exit_B": (tr["B"] or {}).get("exit_session", ""), "cand_exit_C": (tr["C"] or {}).get("exit_session", ""),
                                 "cand_net_recorded": (tr["rec"] or {}).get("net_return", ""), "cand_net_B": (tr["B"] or {}).get("net_return", ""), "cand_net_C": (tr["C"] or {}).get("net_return", ""),
                                 "verdict_recorded": src.get("decision_verdict", ""), "verdict_B": (rb or {}).get("decision_verdict", ""), "verdict_C": (rc or {}).get("decision_verdict", ""), "note": diagnose(r)})
            continue
        tl = {"rec": trade_list(src), "B": trade_list(rb), "C": trade_list(rc)}
        ex_chg, ret_chg, names = 0, 0, []
        if tl["B"] is not None and tl["C"] is not None:
            for (role, name, tb, _), (_, _, tc, _) in zip(tl["B"], tl["C"]):
                if (tb is None) != (tc is None) or (tb and tc and (tb["exit_session"] != tc["exit_session"] or tb["exit_reason"] != tc["exit_reason"])):
                    ex_chg += 1
                    ret_chg += int(bool(tb and tc and abs(tb["net_return"] - tc["net_return"]) > TOL))
                    names.append(f"{role}:{name}")
        cr_, cb_, cc_ = (x["candidate"].get("trade") if x and isinstance(x.get("candidate"), dict) else None for x in (src, rb, rc))
        flow = lambda o: None if o is None else next((c["outcome"] for c in o["cone"] if c["id"] == "WITH_FLOW_RUNUP"), None)  # noqa: E731
        signed = lambda o: None if o is None or not o.get("paired") else o["paired"]["diff"] * o.get("direction", 1)  # noqa: E731
        results_rows.append({**base, "record_type": "RESOLUTION", "family": src.get("family", "SPECULATION"), "window": src["window"], "direction": src.get("direction", 1),
                             "n_trades": len([t for t in (tl["rec"] or []) if t[2]]), "n_trades_exit_changed_C_vs_B": ex_chg if rc is not None else "", "n_trades_return_changed_C_vs_B": ret_chg if rc is not None else "",
                             "trades_changed_C_vs_B": ";".join(names), "C_last_exit_session": last_exit(rc) or "",
                             "cand_exit_recorded": cr_["exit_session"] if cr_ else "", "cand_exit_B": cb_["exit_session"] if cb_ else "", "cand_exit_C": cc_["exit_session"] if cc_ else "",
                             "cand_net_recorded": cr_["net_return"] if cr_ else "", "cand_net_B": cb_["net_return"] if cb_ else "", "cand_net_C": cc_["net_return"] if cc_ else "",
                             "paired_diff_recorded": (src.get("paired") or {}).get("diff", ""), "paired_diff_B": ((rb or {}).get("paired") or {}).get("diff", ""), "paired_diff_C": ((rc or {}).get("paired") or {}).get("diff", ""),
                             "signed_diff_recorded": signed(src), "signed_diff_B": signed(rb), "signed_diff_C": signed(rc),
                             "flow_outcome_recorded": flow(src), "flow_outcome_B": flow(rb), "flow_outcome_C": flow(rc),
                             "flow_outcome_flipped_C_vs_B": (flow(rb) is not None and flow(rc) is not None and flow(rb) != flow(rc)) if f == "catalysts.jsonl" else "", "note": diagnose(r)})
        if tl["rec"] is None or src["candidate"].get("status") == "PATH":
            continue
        for idx, (role, name, trec, srec) in enumerate(tl["rec"]):
            tb = tl["B"][idx][2] if tl["B"] else None
            tc = tl["C"][idx][2] if tl["C"] else None
            db = r["dB"][idx] if r["dB"] else None
            dc = r["dC"][idx] if r["dC"] else None
            tgb, tgc = (db["target"] if db else None), (dc["target"] if dc else None)
            chg = bool(tb and tc and (tb["exit_session"] != tc["exit_session"] or tb["exit_reason"] != tc["exit_reason"]))
            chk = {}
            for v, tr_, d_ in (("B", tb, db), ("C", tc, dc)):
                if tr_ and d_:
                    ex_, nt_ = indep(v, name, d_["entry_idx"], d_["target_idx"], tr_["cost_in"], tr_["cost_out"])
                    chk[f"indep_exit_{v}"], chk[f"indep_net_{v}"] = ex_, nt_
                    chk[f"indep_match_{v}"] = bool(ex_ == tr_["exit_session"] and nt_ is not None and abs(nt_ - tr_["net_return"]) <= TOL)
            if tgb and tgc and tgb["prev"] and tgb["prev"] > 14:
                chk["hand_arb_B"], chk["hand_arb_C"] = hand_limit(tgb["prev"], 0.15), hand_limit(tgb["prev"], 0.07)
                chk["hand_arb_match"] = bool(chk["hand_arb_B"] == tgb["arb"] and chk["hand_arb_C"] == tgc["arb"])
            trade_rows.append({
                "scope": SCOPE[f], "source_file": f, "source_line": r["line"], "record_id": rid(r), "record_hash": src["record_hash"], "window": src["window"], "set_ticker": src["ticker"],
                "direction": src.get("direction", 1), "role": role, "name": name, "status_recorded": srec, "entry_session": (trec or {}).get("entry_session", ""),
                "target_session": tgb["date"] if tgb else "", "exit_recorded": (trec or {}).get("exit_session", ""), "exit_reason_recorded": (trec or {}).get("exit_reason", ""),
                "gross_recorded": (trec or {}).get("gross_return", ""), "net_recorded": (trec or {}).get("net_return", ""), "exit_B": (tb or {}).get("exit_session", ""),
                "exit_reason_B": (tb or {}).get("exit_reason", ""), "gross_B": (tb or {}).get("gross_return", ""), "net_B": (tb or {}).get("net_return", ""),
                "exit_C": (tc or {}).get("exit_session", "") if rc is not None else "PENDING", "exit_reason_C": (tc or {}).get("exit_reason", ""), "gross_C": (tc or {}).get("gross_return", ""),
                "net_C": (tc or {}).get("net_return", ""), "exit_changed_C_vs_B": chg if rc is not None else "",
                "return_changed_C_vs_B": bool(tb and tc and abs(tb["net_return"] - tc["net_return"]) > TOL) if rc is not None else "",
                "net_change_C_minus_B": (tc["net_return"] - tb["net_return"]) if (tb and tc) else "", "target_prev_close": tgb["prev"] if tgb else "", "target_close": tgb["close"] if tgb else "",
                "target_change": (tgb["close"] / tgb["prev"] - 1) if tgb and tgb["prev"] else "", "target_arb_B": tgb["arb"] if tgb else "", "target_arb_C": tgc["arb"] if tgc else "",
                "target_locked_B": tgb["lock_down"] if tgb else "", "target_locked_C": tgc["lock_down"] if tgc else "", "target_close_at_C_limit": bool(tgc and tgc["close"] == tgc["arb"]) if tgc else "",
                "target_close_at_special_limit": bool(tgc and tgc["close"] == tgc["sp_arb"]) if tgc else "", "target_one_price_bar": tgb["one_price"] if tgb else "",
                "rolled_sessions_B": db["rolled"] if db else "", "rolled_sessions_C": dc["rolled"] if dc else "",
                "locked_sessions_rolled_over_C": ";".join(c["date"] for c in (dc["path"][:-1] if dc else [])), **chk})

    # ---------------------------------------------------------------------------------- catalyst register
    cat_recs = [r for r in recs if r["file"] == "catalysts.jsonl"]
    cat_rows = [x for x in results_rows if x["source_file"] == "catalysts.jsonl"]
    tr_cat = [t for t in trade_rows if t["source_file"] == "catalysts.jsonl"]
    gate_cat = [g for g in gate_rows if g["source_file"] == "catalysts.jsonl"]
    changed_tr = [t for t in tr_cat if t["exit_changed_C_vs_B"] is True]
    sg = lambda o: o["paired"]["diff"] * o["direction"]  # noqa: E731
    signed_v = {"rec": [sg(r["src"]) for r in cat_recs], "B": [sg(r["B"]) for r in cat_recs], "C": [sg(r["C"]) for r in cat_recs]}

    def meanshare(v):
        a = np.array(v, dtype=float)
        return {"n": int(len(a)), "mean": float(a.mean()), "share_positive": float((a > 0).mean()), "n_positive": int((a > 0).sum()), "sd": float(a.std(ddof=1)), "se": float(a.std(ddof=1) / math.sqrt(len(a)))}

    flips = [x for x in cat_rows if x["flow_outcome_flipped_C_vs_B"] is True]
    tmin = min(float(t["target_change"]) for t in changed_tr)
    tmax = max(float(t["target_change"]) for t in changed_tr)
    catalyst = {
        "rows": len(cat_rows), "lines": [x["source_line"] for x in cat_rows], "windows": dict(Counter(x["window"] for x in cat_rows)), "signal_sessions": sorted({x["signal_session"] for x in cat_rows}),
        "trade_slots": len(tr_cat), "baseline_rows_reproduced": sum(g["reproduced_within_1e-12"] for g in gate_cat),
        "baseline_rows_bit_identical": sum(1 for g in gate_cat if g["numeric_leaves_not_bit_identical"] == 0 and g["reproduced_within_1e-12"]),
        "baseline_max_abs_numeric_diff": max(g["max_abs_numeric_diff"] for g in gate_cat), "baseline_leaves": sum(g["leaves_compared"] for g in gate_cat),
        "baseline_numeric_leaves": sum(g["numeric_leaves"] for g in gate_cat), "baseline_numeric_not_bit_identical": sum(g["numeric_leaves_not_bit_identical"] for g in gate_cat),
        "baseline_nonnumeric_mismatches": sum(g["nonnumeric_or_missing_mismatches"] for g in gate_cat),
        "baseline_differing_numeric_fields": sorted({f for g in gate_cat for f in g["differing_numeric_fields"].split(";") if f}),
        "rows_pending_under_C": sum(1 for x in cat_rows if str(x["status_C"]).startswith("PENDING")), "rows_changed_under_C": sum(1 for x in cat_rows if x["C_changes_row"]),
        "rows_unchanged_under_C": sum(1 for x in cat_rows if not x["C_changes_row"]), "trade_slots_exit_changed": len(changed_tr),
        "trade_slots_return_changed": sum(1 for t in changed_tr if t["return_changed_C_vs_B"] is True), "candidates_changed": sum(1 for t in changed_tr if t["role"] == "candidate"),
        "twin_slots_changed": sum(1 for t in changed_tr if t["role"] == "twin"), "distinct_names_changed": len({t["name"] for t in changed_tr}),
        "rolled_sessions_C_distribution": dict(sorted(Counter(int(t["rolled_sessions_C"]) for t in changed_tr).items())),
        "changed_trades_move_range": [tmin, tmax], "changed_trades_close_at_C_limit": sum(1 for t in changed_tr if t["target_close_at_C_limit"] is True),
        "changed_trades_close_at_special_limit_not_C_limit": [(t["name"], t["target_change"]) for t in changed_tr if t["target_close_at_C_limit"] is not True and t["target_close_at_special_limit"] is True],
        "changed_trades_neither": [(t["name"], t["target_change"]) for t in changed_tr if t["target_close_at_C_limit"] is not True and t["target_close_at_special_limit"] is not True],
        "changed_trades_return_unchanged": [t["name"] for t in changed_tr if t["return_changed_C_vs_B"] is not True],
        "changed_row_tickers": [x["ticker"] for x in cat_rows if x["C_changes_row"]], "unchanged_row_tickers": [x["ticker"] for x in cat_rows if not x["C_changes_row"]],
        "last_exit_days_C": sorted({x["C_last_exit_session"] for x in cat_rows if x["C_changes_row"]}),
        "flow_outcomes_flipped": [x["ticker"] for x in flips], "flow_outcome_flip_detail": [{"ticker": x["ticker"], "B": x["flow_outcome_B"], "C": x["flow_outcome_C"], "signed_diff_B": x["signed_diff_B"], "signed_diff_C": x["signed_diff_C"]} for x in flips],
        "signed_diff": {k: meanshare(v) for k, v in signed_v.items()}, "stats_recorded": R["B"]["stats_recorded"], "stats_B": R["B"]["stats_variant"], "stats_C": R["C"]["stats_variant"],
        "lines_published": R["B"]["published_lines"], "lines_recorded_rows": R["B"]["lines_recorded"], "lines_B": R["B"]["lines_variant"], "lines_C": R["C"]["lines_variant"],
        "published_line_reproduced_from_recorded_rows": R["B"]["published_lines"] == R["B"]["lines_recorded"], "lines_B_equal_recorded_lines": R["B"]["lines_variant"] == R["B"]["lines_recorded"],
        "chain_problems": R["B"]["chain_problems"], "recorded_resolved_at_range": [min(r["src"]["resolved_at"] for r in cat_recs), max(r["src"]["resolved_at"] for r in cat_recs)],
        "recorded_rows_written_on_manifest_sha256": sorted({r["src"]["data"]["manifest_sha256"] for r in cat_recs})}
    catalyst["recorded_manifest_is_the_frozen_one"] = catalyst["recorded_rows_written_on_manifest_sha256"] == [pre["orig_manifest"]["sha256"]]
    plan_trades = [t for t in trade_rows if "indep_match_B" in t]
    catalyst["independent_roll_check"] = {"trades_checked": len(plan_trades), "catalyst_trades_checked": len(tr_cat), "match_B": sum(1 for t in plan_trades if t.get("indep_match_B") is True),
                                         "match_C": sum(1 for t in plan_trades if t.get("indep_match_C") is True), "trades_with_C_replay": sum(1 for t in plan_trades if "indep_match_C" in t)}
    hl = [t for t in trade_rows if "hand_arb_match" in t and t["source_file"] == "catalysts.jsonl"]
    catalyst["hand_limit_check"] = {"cells": len(hl), "match": sum(1 for t in hl if t["hand_arb_match"] is True)}
    catalyst["changed_trades"] = [{k: t[k] for k in ("record_id", "role", "name", "exit_B", "exit_C", "net_B", "net_C", "target_change", "target_close", "target_arb_B", "target_arb_C", "target_close_at_C_limit",
                                                    "rolled_sessions_C", "locked_sessions_rolled_over_C")} for t in changed_tr]

    # ---------------------------------------------------------------------------------- speculation and ledger cross-checks
    spec_recs = [r for r in recs if r["file"] == "speculations.jsonl"]
    spec_summary = {"rows": len(spec_recs), "by_window": dict(Counter(r["src"]["window"] for r in spec_recs)), "B_reproduced": sum(reproduced(r) for r in spec_recs),
                    "B_not_reproduced": [{"ticker": r["extra"]["ticker"], "window": r["src"]["window"], "signal_session": r["extra"]["signal_session"], "diagnosis": diagnose(r)} for r in spec_recs if not reproduced(r)],
                    "rows_changed_under_C": [{"ticker": r["extra"]["ticker"], "window": r["src"]["window"], "status_C": status_text(r["C"], r["reasonC"])} for r in spec_recs if c_changes(r)], "pending_detail": []}
    for r in spec_recs:
        if r["C"] is None:
            det = []
            for d in r["dB"] or []:
                if d is None:
                    continue
                n, k = tickers.index(d["name"]), dates.index(d["target"]["date"])
                if bool(ld["C"][n, k]) and k == len(dates) - 1:
                    det.append({"name": d["name"], "session": d["target"]["date"], "prev": d["target"]["prev"], "close": d["target"]["close"], "arb_B": float(P["B"]["arb"][n, k]), "arb_C": float(P["C"]["arb"][n, k])})
            spec_summary["pending_detail"].append({"record": rid(r), "window": r["src"]["window"], "locked_on_last_bar_under_C": det})
    led_recs = [r for r in recs if r["file"] == "ledger.jsonl"]
    both = [r for r in led_recs if r["B"] is not None and r["C"] is not None]
    ex_chg = [r for r in both if paper_trade(r["B"]) and paper_trade(r["C"]) and (paper_trade(r["B"])["exit_session"] != paper_trade(r["C"])["exit_session"] or paper_trade(r["B"])["exit_reason"] != paper_trade(r["C"])["exit_reason"])]
    ret_chg = [r for r in both if paper_trade(r["B"]) and paper_trade(r["C"]) and abs(paper_trade(r["B"])["net_return"] - paper_trade(r["C"])["net_return"]) > TOL]
    traded_both = [r for r in both if paper_trade(r["B"]) and paper_trade(r["C"])]
    ledger_summary = {
        "rows": len(led_recs), "traded_rows_recorded": sum(1 for r in led_recs if paper_trade(r["src"])), "B_reproduced": sum(reproduced(r) for r in led_recs),
        "B_not_reproduced": [{"ticker": r["extra"]["ticker"], "signal_session": r["extra"]["signal_session"], "diagnosis": diagnose(r)} for r in led_recs if not reproduced(r)],
        "plan_types": dict(Counter(r["extra"]["plan_type"] for r in led_recs)), "scored_before_exit_bar_final": [(r["extra"]["ticker"], r["extra"]["scored_at"], r["extra"]["exit_bar_final_utc"]) for r in led_recs if r["extra"]["scored_before_exit_bar_final"]],
        "rows_pending_under_C": [{"ticker": r["extra"]["ticker"], "signal_session": r["extra"]["signal_session"]} for r in led_recs if r["C"] is None],
        "rows_changed_under_C": sum(1 for r in led_recs if c_changes(r)), "trades_exit_changed": len(ex_chg), "trades_return_changed": len(ret_chg),
        "verdict_flips": [(r["extra"]["ticker"], r["B"]["decision_verdict"], r["C"]["decision_verdict"]) for r in both if r["B"]["decision_verdict"] != r["C"]["decision_verdict"]],
        "traded_rows_in_both": len(traded_both), "mean_net_B": float(np.mean([paper_trade(r["B"])["net_return"] for r in traded_both])) if traded_both else None,
        "mean_net_C": float(np.mean([paper_trade(r["C"])["net_return"] for r in traded_both])) if traded_both else None}

    # ---------------------------------------------------------------------------------- the learner (second-order) replay
    mods_b, mods_c, mods_alka = [], [], []
    keys = ("candidate", "twins", "paired", "cone", "status")
    for r in recs:
        if r["file"] == "ledger.jsonl" or r["src"]["window"] not in ("RUNUP", "BASE5", "POST20", "H20", "H60"):
            continue  # the learner trains on the registers' graded plan statements only
        key = {"file": r["file"], "line": r["line"], "record_hash": r["src"]["record_hash"]}
        if r["B"] is not None:
            mods_b.append({**key, "content": {k: r["B"][k] for k in keys}})
        if c_changes(r):
            if r["C"] is None:
                mods_alka.append({**key, "pending": True})
            else:
                mods_c.append({**key, "content": {k: r["C"][k] for k in keys}, "last_exit_day": last_exit(r["C"])})
    strip = lambda ms: [{k: v for k, v in m.items() if k != "last_exit_day"} for m in ms]  # noqa: E731
    worlds = [{"name": "W0_recorded_ledgers", "mods": []}, {"name": "WB_B_replayed_labels", "mods": mods_b}, {"name": "C_labels_only", "mods": strip(mods_c)},
              {"name": "C_alka_pending_only", "mods": mods_alka}, {"name": "C_all_recorded_timing", "mods": strip(mods_c) + mods_alka},
              {"name": "C_all_c_world_timing", "mods": [{**m, "availability": "last_exit_day"} for m in mods_c] + mods_alka}]
    (WORK / "learner_worlds.json").write_text(json.dumps({"worlds": worlds}, default=np_default), encoding="utf-8")
    print("== learner replay (second-order)")
    times["learner"] = run_worker("learner", str(WORK / "learner_worlds.json"), roots["B"])
    LR = json.loads((OUTD / "learner_results.json").read_text(encoding="utf-8"))

    def lsum(name, market=None):
        rs = [r for r in LR["worlds"][name] if market is None or r["market"] == market]
        return {"records": len(rs), "records_beyond_tolerance": sum(1 for r in rs if r["fields_differing"]), "records_raw_changed": sum(1 for r in rs if r["n_raw_changed"]),
                "records_published_changed": sum(1 for r in rs if r["n_published_changed"]), "records_call_changed": sum(1 for r in rs if r["call_changes"]),
                "max_abs_raw": max((r["max_abs_raw"] for r in rs), default=0.0), "max_abs_published": max((r["max_abs_published"] for r in rs), default=0.0),
                "median_abs_raw_over_changed": float(np.median([r["max_abs_raw"] for r in rs if r["n_raw_changed"]])) if any(r["n_raw_changed"] for r in rs) else 0.0}

    learner = {"worlds": {n: {m: lsum(n, None if m == "all" else m) for m in ("all", "IDX", "US", "CRYPTO")} for n in LR["worlds"]}, "n_records": len(LR["worlds"]["W0_recorded_ledgers"]), "tolerance": LR["verify_tol"],
               "idx_records_trained_on_runup_labels": sum(1 for r in LR["worlds"]["W0_recorded_ledgers"] if r["market"] == "IDX" and "IDX_INDEX:WITH_FLOW_RUNUP" in r["live_rows_recorded"]),
               "idx_published_changes": [{"made_at": r["made_at"], "ticker": r["ticker"], "changes": r["published_changes"]} for r in LR["worlds"]["C_all_recorded_timing"] if r["market"] == "IDX" and r["published_changes"]],
               "labels_changed_rows": [(m["file"], m["line"], m["last_exit_day"]) for m in mods_c], "alka_pending_rows": [(m["file"], m["line"]) for m in mods_alka],
               "alka_pending_resolved_at": [r["src"]["resolved_at"] for r in recs if r["file"] == "speculations.jsonl" and r["C"] is None]}
    if learner["idx_published_changes"] and learner["alka_pending_resolved_at"]:
        t1, t2 = (datetime.fromisoformat(x.replace("Z", "+00:00")) for x in (learner["alka_pending_resolved_at"][0], learner["idx_published_changes"][0]["made_at"]))
        learner["alka_minutes_before"] = (t2 - t1).total_seconds() / 60
    def fill(file, fam, rows_, changed, base, note):
        for r in census:
            if r["file"] == file and r["record_family"].startswith(fam):
                r.update(rows_replayed=rows_, rows_changed_by_correction=changed, baseline_B_reproduced=base, change_note=note)

    for win, fam in (("BASE5", "RESOLUTION BASE5"), ("NEXT1", "RESOLUTION NEXT1")):
        sr = [r for r in spec_recs if r["src"]["window"] == win]
        fill("speculations.jsonl", fam, len(sr), sum(1 for r in sr if c_changes(r)), f"{sum(reproduced(r) for r in sr)} of {len(sr)}", "pending under C: " + (", ".join(r["extra"]["ticker"] for r in sr if r["C"] is None) or "none"))
    fill("catalysts.jsonl", "RESOLUTION", catalyst["rows"], catalyst["rows_changed_under_C"], f"{catalyst['baseline_rows_reproduced']} of {catalyst['rows']}",
         f"{catalyst['trade_slots_exit_changed']} of {catalyst['trade_slots']} trades change exit; {len(catalyst['flow_outcomes_flipped'])} statement flips; published line moves")
    fill("ledger.jsonl", "OUTCOME", ledger_summary["rows"], ledger_summary["rows_changed_under_C"], f"{ledger_summary['B_reproduced']} of {ledger_summary['rows']}",
         f"{ledger_summary['trades_exit_changed']} exit changes, {len(ledger_summary['rows_pending_under_C'])} pending")
    wc = learner["worlds"]["C_all_recorded_timing"]
    fill("learner_v2.jsonl", "LEARNER2_FORECAST (SPEC_IDX)", wc["IDX"]["records"], wc["IDX"]["records_raw_changed"], f"{wc['IDX']['records'] - learner['worlds']['WB_B_replayed_labels']['IDX']['records_beyond_tolerance']} of {wc['IDX']['records']}",
         f"raw forecasts shift in {wc['IDX']['records_raw_changed']}, published in {wc['IDX']['records_published_changed']}, calls in {wc['IDX']['records_call_changed']}")
    fill("learner_v2.jsonl", "LEARNER2_FORECAST (US/CRYPTO", wc["US"]["records"] + wc["CRYPTO"]["records"], wc["US"]["records_raw_changed"] + wc["CRYPTO"]["records_raw_changed"],
         f"{wc['US']['records'] + wc['CRYPTO']['records'] - learner['worlds']['WB_B_replayed_labels']['US']['records_beyond_tolerance'] - learner['worlds']['WB_B_replayed_labels']['CRYPTO']['records_beyond_tolerance']} of {wc['US']['records'] + wc['CRYPTO']['records']}",
         "raw forecasts shift (shared slope); published and calls unchanged")
    write_csv(HERE / "family_census.csv", census, ["file", "record_family", "idx_rows", "idx_rows_touching_on_or_after_cutoff", "idx_rows_exposed_to_lock", "depends_on_lock", "dependence", "code_path",
                                                  "replayable_from_final_pull", "rows_replayed", "rows_changed_by_correction", "baseline_B_reproduced", "change_note", "note"])
    lA, lB_, lB0 = ({r["record_hash"]: r for r in LR["worlds"][n]} for n in ("C_all_recorded_timing", "C_all_c_world_timing", "WB_B_replayed_labels"))
    learner_rows = []
    for n, f in enumerate(load_jsonl(REPO_PAPER / "learner_v2.jsonl"), 1):
        a, b, b0 = lA[f["record_hash"]], lB_[f["record_hash"]], lB0[f["record_hash"]]
        learner_rows.append({"scope": "learner_v2 (second-order)", "source_file": "learner_v2.jsonl", "source_line": n, "record_type": "LEARNER2_FORECAST", "record_id": f["set_id"], "record_hash": f["record_hash"],
                             "family": f["family"], "market": f["market"], "ticker": f["ticker"], "signal_session": f["signal_session"], "made_at": f["made_at"], "B_reproduces_recorded": not b0["fields_differing"],
                             "B_max_abs_numeric_diff": b0["max_abs_raw"], "C_changes_row": bool(a["n_raw_changed"] or a["n_published_changed"] or a["call_changes"] or b["n_raw_changed"] or b["n_published_changed"] or b["call_changes"]),
                             "lrn_A_n_raw_changed": a["n_raw_changed"], "lrn_A_max_abs_raw": a["max_abs_raw"], "lrn_A_n_published_changed": a["n_published_changed"], "lrn_A_max_abs_published": a["max_abs_published"],
                             "lrn_A_call_changes": a["call_changes"], "lrn_B_n_raw_changed": b["n_raw_changed"], "lrn_B_max_abs_raw": b["max_abs_raw"], "lrn_B_n_published_changed": b["n_published_changed"],
                             "lrn_B_max_abs_published": b["max_abs_published"], "lrn_B_call_changes": b["call_changes"]})

    # ---------------------------------------------------------------------------------- files
    cols = ["scope", "source_file", "source_line", "record_type", "record_id", "record_hash", "family", "market", "ticker", "window", "signal_session", "made_at", "direction", "status_recorded", "status_B", "status_C",
            "B_reproduces_recorded", "B_max_abs_numeric_diff", "C_changes_row", "C_leaves_changed_vs_B", "n_trades", "n_trades_exit_changed_C_vs_B", "n_trades_return_changed_C_vs_B", "trades_changed_C_vs_B",
            "C_last_exit_session", "cand_exit_recorded", "cand_exit_B", "cand_exit_C", "cand_net_recorded", "cand_net_B", "cand_net_C", "paired_diff_recorded", "paired_diff_B", "paired_diff_C",
            "signed_diff_recorded", "signed_diff_B", "signed_diff_C", "flow_outcome_recorded", "flow_outcome_B", "flow_outcome_C", "flow_outcome_flipped_C_vs_B", "verdict_recorded", "verdict_B", "verdict_C",
            "lrn_A_n_raw_changed", "lrn_A_max_abs_raw", "lrn_A_n_published_changed", "lrn_A_max_abs_published", "lrn_A_call_changes", "lrn_B_n_raw_changed", "lrn_B_max_abs_raw", "lrn_B_n_published_changed",
            "lrn_B_max_abs_published", "lrn_B_call_changes", "note"]
    write_csv(HERE / "results.csv", [x for x in results_rows if x["source_file"] == "catalysts.jsonl"] + [x for x in results_rows if x["source_file"] == "speculations.jsonl"]
              + [x for x in results_rows if x["source_file"] == "ledger.jsonl"] + learner_rows, cols)
    write_csv(HERE / "trades.csv", trade_rows, ["scope", "source_file", "source_line", "record_id", "record_hash", "window", "set_ticker", "direction", "role", "name", "status_recorded", "entry_session",
                                                 "target_session", "exit_recorded", "exit_reason_recorded", "gross_recorded", "net_recorded", "exit_B", "exit_reason_B", "gross_B", "net_B", "exit_C", "exit_reason_C",
                                                 "gross_C", "net_C", "exit_changed_C_vs_B", "return_changed_C_vs_B", "net_change_C_minus_B", "target_prev_close", "target_close", "target_change",
                                                 "target_arb_B", "target_arb_C", "target_locked_B", "target_locked_C", "target_close_at_C_limit", "target_close_at_special_limit", "target_one_price_bar",
                                                 "rolled_sessions_B", "rolled_sessions_C", "locked_sessions_rolled_over_C", "indep_exit_B", "indep_net_B", "indep_match_B", "indep_exit_C", "indep_net_C", "indep_match_C", "hand_arb_B", "hand_arb_C", "hand_arb_match"])
    write_csv(HERE / "baseline_gate.csv", gate_rows, ["scope", "source_file", "source_line", "record_id", "window", "record_hash", "replay_status_B", "leaves_compared", "numeric_leaves", "numeric_leaves_not_bit_identical",
                                                      "max_abs_numeric_diff", "numeric_leaves_over_1e-12", "nonnumeric_or_missing_mismatches", "reproduced_within_1e-12", "differing_numeric_fields",
                                                      "mismatching_paths", "diagnosis"])
    lcols = ["world", "record_hash", "set_id", "family", "market", "ticker", "signal_session", "made_at", "n_statements", "n_raw_changed", "n_published_changed", "max_abs_raw", "max_abs_published", "max_abs_anchor",
             "max_abs_deviation", "call_changes", "fields_differing"]
    write_csv(HERE / "learner_changes.csv", [{"world": n, **{k: r[k] for k in lcols[1:-1]}, "fields_differing": ";".join(r["fields_differing"])} for n, rs in LR["worlds"].items() for r in rs], lcols)

    clean = {}
    if not args.no_clean_check:
        after = {"code_B": tree_snapshot(CODE["B"]), "code_C": tree_snapshot(CODE["C"]), "repo_paper": tree_snapshot(REPO_PAPER, True, ("timestamps", "scans", "raw")), "repo_research": tree_snapshot(REPO_RESEARCH, False),
                 "frozen_top": {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in FROZEN.iterdir() if p.is_file()}}
        clean = {k: snaps_before[k] == after[k] for k in snaps_before}
        assert all(clean.values()), f"a protected tree changed: {clean}"
    summary = {"preflight": pre, "panel": panel, "catalyst_register": catalyst, "speculation_crosscheck": spec_summary, "ledger_crosscheck": ledger_summary, "learner_v2": learner, "census": census,
               "callers_by_file": per_file, "rules_files_reading_lock_down": rules_reading, "tree_unchanged_after_run": clean, "cutoff": CUTOFF, "versions": R["B"]["versions"], "data": R["B"]["data"],
               "lock_cells_total": len(lock_rows)}
    (HERE / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=np_default, allow_nan=False) + "\n", encoding="utf-8")
    new_hashes = {f: sha256_file(HERE / f) for f in DET_FILES}
    repro = {"previous_run_present": bool(prev_hashes), "files": {f: (None if f not in prev_hashes else prev_hashes[f] == new_hashes[f]) for f in DET_FILES}}
    (HERE / "report.md").write_text(render_report(summary, cat_rows, tr_cat, census, repro, new_hashes), encoding="utf-8")
    (HERE / "run_meta.json").write_text(json.dumps({"started_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"), "elapsed_s": round(time.time() - T0, 1), "worker_seconds": {k: round(v, 1) for k, v in times.items()},
                                                    "command": " ".join([sys.executable] + sys.argv), "versions": R["B"]["versions"], "pycache_dirs_in_code_dirs_when_the_run_started": pycache_pre, "output_sha256": new_hashes, "reproduction_vs_previous_run": repro}, indent=1) + "\n", encoding="utf-8")
    if not args.keep_work:
        shutil.rmtree(WORK)
    print(f"== done in {time.time() - T0:.0f}s")
    print(json.dumps({"catalyst_rows": catalyst["rows"], "rows_changed_C": catalyst["rows_changed_under_C"], "trade_slots_exit_changed": catalyst["trade_slots_exit_changed"],
                      "signed_diff_B": catalyst["signed_diff"]["B"]["mean"], "signed_diff_C": catalyst["signed_diff"]["C"]["mean"], "share_B": catalyst["signed_diff"]["B"]["share_positive"],
                      "share_C": catalyst["signed_diff"]["C"]["share_positive"], "reproduction_vs_previous": repro}, indent=1))


# ============================================================================================================ report
def plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


def render_report(S: dict, cat_rows: list, tr_cat: list, census: list, repro: dict, hashes: dict) -> str:
    C, L, P, SP, LG = S["catalyst_register"], S["learner_v2"], S["panel"], S["speculation_crosscheck"], S["ledger_crosscheck"]
    sd, W = C["signed_diff"], L["worlds"]
    mf = S["preflight"]["manifest"]
    lo, hi = C["changed_trades_move_range"]
    unch = C["changed_trades_return_unchanged"]
    roll = ", ".join(f"{v} {'trade rolls' if v == 1 else 'trades roll'} {k} {'session' if int(k) == 1 else 'sessions'}" for k, v in C["rolled_sessions_C_distribution"].items())
    cnt = Counter(t["name"] for t in C["changed_trades"])
    multi_txt = "".join(f"; {n} is a twin of {c} sets" for n, c in cnt.items() if c > 1)
    clean = S["tree_unchanged_after_run"]
    IC = C["independent_roll_check"]
    b0, b1, b2 = list(P["limit_bunching"].values())
    cal_b, cal_c = C["stats_B"]["calibration"]["WITH_FLOW_RUNUP"], C["stats_C"]["calibration"]["WITH_FLOW_RUNUP"]
    flip = C["flow_outcome_flip_detail"][0]
    lines = []
    A = lines.append
    A("# IDX lower-limit correction: effect on the Catalyst Register and the other persisted record families (addendum)")
    A("")
    A(f"Paper trading only, no real money. Every count and statistic here comes from `harness.py`; statements about code paths and protocols come from reading the code (`code_callers.txt`) and are labelled as such. The harness replays the real functions of the shipped rules (B) and the corrected rules (C) on the only surviving raw pull "
      f"(`{mf['file']}`, sha256 `{mf['sha256'][:12]}`, {mf['n_tickers']} tickers, last bar {S['data']['last_session']}). That makes every result a *final-bar replay*: a sale that rolls is resolved with the bars up to "
      f"{S['data']['last_session']}, and a roll that runs past the last bar leaves the row pending. Nothing was edited: no ledger, no register, no code dir "
      + ("(hash snapshots of the two code dirs, the repository's paper/ and research/ and the frozen inputs, taken before and after the run, are identical)." if clean else "(tree snapshots were skipped in this run)."))
    A("")
    A("## The numbers")
    A("")
    A(f"- **Catalyst register: {C['rows']} IDX RESOLUTION rows** (`paper/catalysts.jsonl` lines {C['lines'][0]} to {C['lines'][-1]}), all `IDX_INDEX` window `RUNUP`: signal session {', '.join(C['signal_sessions'])}, buy the 2026-10-29 close, "
      f"sell the 2026-10-30 close. {C['trade_slots']} trades ({C['rows']} candidates, {C['trade_slots'] - C['rows']} twins). Every sale falls on 2026-10-30, after both October rule changes; the rows were written at {C['recorded_resolved_at_range'][0]}.")
    A(f"- **Baseline gate passed.** B replayed on the final pull reproduces **{C['baseline_rows_reproduced']} of {C['rows']}** recorded rows: {C['baseline_leaves']} leaves compared, every text, date, status, boolean and count identical, "
      f"{C['baseline_numeric_leaves'] - C['baseline_numeric_not_bit_identical']} of {C['baseline_numeric_leaves']} numeric leaves bit-identical and the other {C['baseline_numeric_not_bit_identical']} within {C['baseline_max_abs_numeric_diff']:.1e} "
      "(floating-point noise from a different window start, diagnosed below). The published `CATALYSTS.md` line is also reproduced by the register's own `statistics()` and `render()` from the recorded rows.")
    A(f"- **Under the corrected rules (C), {C['rows_changed_under_C']} of {C['rows']} rows change** ({', '.join(C['changed_row_tickers'])}); {C['rows_unchanged_under_C']} do not ({', '.join(C['unchanged_row_tickers'])}). "
      f"**{C['trade_slots_exit_changed']} of {C['trade_slots']} trades change their exit** ({C['candidates_changed']} candidates, {C['twin_slots_changed']} twin slots, {C['distinct_names_changed']} distinct names{multi_txt}) "
      f"and {C['trade_slots_return_changed']} change their return ({', '.join(unch)} sells the next day at an unchanged price). Each of them closed on 2026-10-30 between {abs(hi):.1%} and {abs(lo):.1%} below the previous close; "
      f"{C['changed_trades_close_at_C_limit']} of the {C['trade_slots_exit_changed']} closed exactly at the tick-rounded 7% limit price and {len(C['changed_trades_close_at_special_limit_not_C_limit'])} "
      f"({', '.join(n for n, _ in C['changed_trades_close_at_special_limit_not_C_limit'])}) exactly at the 10% special-board limit. The old 15% limit let all of them sell on 2026-10-30; the 7% limit locks them, so each sale rolls to the next sellable session ({roll}).")
    A(f"- **The data themselves show a binding 7% limit from {CUTOFF}**, independent of the decree texts (which I did not read). Among traded names with a reference above Rp14 that closed down, closes exactly at the tick-rounded 7% limit price run at "
      f"{b1['per_session_at_7pct']:.1f} per session in the 15%-limit sessions of 2026-09-28 to 2026-10-16 ({b0['per_session_at_7pct']:.1f} over the {b0['sessions']} sessions before) and at {b2['per_session_at_7pct']:.1f} per session from {CUTOFF}; "
      f"closes below that price fall from {b1['per_session_below_7pct']:.0f} to {b2['per_session_below_7pct']:.0f} per session; the 15% limit price itself is hit {b2['close_exactly_at_15pct_limit_price']} times from {CUTOFF}, against {b1['close_exactly_at_15pct_limit_price']} in the 15 sessions before.")
    A(f"- **The published line moves.** `paper/CATALYSTS.md` says *RUNUP: paired 14, mean signed diff +1.16%, share with the flow 64%*. Recomputed with the register's own code: recorded rows {pct(sd['rec']['mean'])} and {sd['rec']['share_positive']:.0%}; "
      f"B replay {pct(sd['B']['mean'])} and {sd['B']['share_positive']:.0%} (identical); **C replay {pct(sd['C']['mean'])} and {sd['C']['share_positive']:.0%}** ({sd['C']['n_positive']} of 14 sets with the flow, was {sd['B']['n_positive']} of 14). "
      f"One graded statement flips: {', '.join(C['flow_outcomes_flipped'])} `WITH_FLOW_RUNUP` goes {flip['B']} to {flip['C']}, so the calibration row's realised rate goes from {cal_b['realised_rate']:.2f} to {cal_c['realised_rate']:.2f}; "
      f"its Brier terms stay {cal_c['brier']:.3f} (prior 0.5 for every set). POST20 has no resolved row under either rule set.")
    wl, wa = W["C_labels_only"], W["C_alka_pending_only"]
    A(f"- **One other family has IDX values that depend on the lock and was not covered: `learner_v2.jsonl`** ({wl['IDX']['records']} IDX rows), through its training labels only. Re-forecast with the learner's own code from each record's own ledger prefix, "
      f"the single flipped label ({', '.join(C['flow_outcomes_flipped'])}) shifts the raw forecast probabilities of {wl['all']['records_raw_changed']} of {L['n_records']} records ({wl['IDX']['records_raw_changed']} of {wl['IDX']['records']} IDX records; US and crypto records share the slope) "
      f"by at most {wl['all']['max_abs_raw']:.4f} ({wl['IDX']['max_abs_raw']:.4f} on IDX records); published probabilities and calls do not change. Separately, the ALKA BASE5 speculation row stays pending under C, which moves the published `RUN30_5` and `PUMP30_5` "
      f"probability of {wa['IDX']['records_published_changed']} IDX forecasts by {wa['IDX']['max_abs_published']:.4f}.")
    A(f"- **Cross-check of the earlier work with the same machinery.** Speculation Register, {SP['rows']} IDX rows: B reproduces {SP['B_reproduced']}; under C {', '.join(f'{x['ticker']} {x['window']} is {x['status_C']}' for x in SP['rows_changed_under_C']) or 'nothing changes'}. "
      f"Ledger, {LG['rows']} IDX OUTCOME rows: B reproduces {LG['B_reproduced']}; C gives {LG['trades_exit_changed']} of them a different exit session and leaves {len(LG['rows_pending_under_C'])} pending. Details below.")
    A("- **No other family has IDX rows that depend on the lock** (table below): scans, decisions, sets, tags and batches, and the US, crypto, book and account ledgers are independent of `lock_down`.")
    A("")
    A("## Catalyst register, row by row")
    A("")
    A("Signed difference = (candidate net minus the twins' mean net) x direction; *with flow* = signed difference above zero (`WITH_FLOW_RUNUP`). Net returns are after the paper fees. `Line` is the line in `paper/catalysts.jsonl`; the hash is the row's `record_hash` (first 12 characters). "
      "Candidate and twin trades of every row, with exits and returns under both rule sets, are in the appendix and in `trades.csv`.")
    A("")
    A("| Line | Set | Record hash | Dir | Cand. net B | Cand. net C | Cand. exit C | Signed diff B | Signed diff C | With flow B | With flow C | Trades whose exit changes in C |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in cat_rows:
        chg = (" (" + r["trades_changed_C_vs_B"].replace("candidate:", "cand ").replace("twin:", "").replace(";", ", ") + ")") if r["trades_changed_C_vs_B"] else ""
        A(f"| {r['source_line']} | {r['ticker']} | `{r['record_hash'][:12]}` | {int(r['direction']):+d} | {pct(r['cand_net_B'])} | {pct(r['cand_net_C'])} | {r['cand_exit_C']} | {pct(r['signed_diff_B'])} | {pct(r['signed_diff_C'])} | "
          f"{'yes' if r['flow_outcome_B'] else 'no'} | {'yes' if r['flow_outcome_C'] else 'no'} | {r['n_trades_exit_changed_C_vs_B']} of {r['n_trades']}{chg} |")
    A("")
    A(f"The {C['trade_slots_exit_changed']} trades whose exit changes. Target session 2026-10-30 for all; ARB = the lower-limit price; the move is close over the previous close.")
    A("")
    A("| Set | Role | Name | Move | ARB B | ARB C | Close | Exit and net, B | Exit and net, C | Rolled |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for t in C["changed_trades"]:
        A(f"| {t['record_id'].split('-')[-1]} | {t['role']} | {t['name']} | {pct(t['target_change'])} | {t['target_arb_B']:g} | {t['target_arb_C']:g} | {t['target_close']:g} | {t['exit_B']}, {pct(t['net_B'])} | {t['exit_C']}, {pct(t['net_C'])} | {t['rolled_sessions_C']} |")
    A("")
    A("## Why the rows change")
    A("")
    A("`catalysts.resolve_set` runs `speculation.simulate` for the candidate and for each twin. `simulate` sells at the first session at or after the target where `tradeable and not lock_down`, and returns nothing (row pending) if there is none. "
      "`lock_down` is built in `Market.build`: the bar traded, the close is below the reference and at or below that day's lower limit (ARB). B keeps the 15% limit set on 2026-09-28; C applies 7% from 2026-10-19 and a nominal Rp1 limit for references Rp11 to 14 from 2026-10-20. "
      f"The upper limit (ARA, and so `lock_up` and every entry) is identical in B and C ({P['lock_up_cells_differing']} of {P['cells']:,} cells differ). The two rule sets differ only in lower-limit cells on or after 2026-10-19: {P['cells_locked_only_under_C']:,} cells are locked under C and not under B, "
      f"{P['cells_locked_only_under_B']} the other way, {P['changed_cells_before_cutoff']} before 2026-10-19 (`lock_cells_changed.csv`); {P['changed_cells_with_reference_at_most_14']} of them have a reference of Rp14 or less. "
      f"The lock formula was recomputed independently from the limit arrays and reproduces `Market.lock_down` and `lock_up` exactly under both rule sets, and the two limit prices were recomputed by hand (previous close x 0.85 and x 0.93, rounded up to the tick) "
      f"for the target cell of each of the {C['hand_limit_check']['cells']} catalyst trades: they match the code in {C['hand_limit_check']['match']} of {C['hand_limit_check']['cells']}. "
      f"The rows were resolved on 2026-10-30 at about 10:59 UTC, when none of these sales was locked under B. Under C, {C['rows_changed_under_C']} of the sets cannot resolve that day, because a sale rolls: they would have been written when the last rolled sale closed ({', '.join(C['last_exit_days_C'])}).")
    A("")
    A("## Baseline gate, and what the tiny differences are")
    A("")
    A(f"The 14 rows were written on the 2026-10-30 pull (manifest sha256 `{C['recorded_rows_written_on_manifest_sha256'][0][:12]}`; that manifest is kept in the frozen inputs and matches the hash recorded in the rows, but its raw payloads were not kept). The replay reads the 2026-11-06 pull, whose 200-day window starts later ({mf['first_date_sample']} against {S['preflight']['orig_manifest']['first_date_sample']}). "
      "The reference chain `level` is a cumulative sum of log returns from the first bar of the window, so `level[exit] / level[entry]` differs in the last bits. "
      f"The numeric fields that are not bit-identical are exactly {', '.join('`' + f + '`' for f in C['baseline_differing_numeric_fields'])}, never by more than {C['baseline_max_abs_numeric_diff']:.1e}. "
      f"Entry prices, sessions, exit reasons, costs, statuses, units, cone outcomes and Brier terms are identical ({C['baseline_nonnumeric_mismatches']} non-numeric mismatches). "
      f"The B-replayed rows and the recorded rows both render, with the register's own `render()`, to exactly the published IDX_INDEX lines "
      f"({'yes' if C['lines_B_equal_recorded_lines'] and C['published_line_reproduced_from_recorded_rows'] else 'NO'}); the four hash chains read here verify "
      f"({', '.join(k + ': ' + ('intact' if not v else 'BROKEN') for k, v in C['chain_problems'].items())}). "
      f"A first-principles recomputation of every replayed plan trade (the 84 catalyst trades and the 11 traded legs of the two BASE5 speculation rows) from the saved price and lock arrays alone, without calling `simulate` "
      f"(first sellable session at or after the target, reference-chain return, the recorded costs), agrees on exit session and net return for {IC['match_B']} of {IC['trades_checked']} trades under B and {IC['match_C']} of {IC['trades_with_C_replay']} under C.")
    A("")
    A("## Other persisted record families")
    A("")
    A("Counted from the committed snapshot (a ledger row without `market` is IDX). *Touching* = a session field (signal, entry, exit or scan session) on or after 2026-10-19. *Exposed* = a trade sold on or after that date, the only place the lock enters; "
      "for `learner_v2` it means the record was trained on the 14 `IDX_INDEX` labels. The depends / path / replay columns come from reading the code (`code_callers.txt`) and, where stated, from the replays here.")
    A("")
    A("| File | Record family | IDX rows | Touching | Exposed | Depends on the lock | Code path | Replayable from the final pull | Replay result (rows replayed, rows changed under C, B reproduces) |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in census:
        if r["idx_rows"] == "":
            continue
        A(f"| `{r['file']}` | {r['record_family']} | {r['idx_rows']} | {r['idx_rows_touching_on_or_after_cutoff']} | {r['idx_rows_exposed_to_lock']} | {r['depends_on_lock']} | {r['code_path']} | {r['replayable_from_final_pull']} | "
          + (f"{r['rows_replayed']} replayed, {r['rows_changed_by_correction']} changed, B reproduces {r['baseline_B_reproduced']}; {r['change_note']}" if r.get("rows_replayed") not in (None, "") else "") + " |")
    A("")
    A("The derived reports (`CATALYSTS.md`, `SPECULATIONS.md`, `LEARNER_V2.md`, `LEARNER_V3.md`, `CALL_CERT.md`, the account and book reports, `README.md`) are rendered from the ledgers and hold no value of their own; of them only the IDX_INDEX section of `CATALYSTS.md` is changed by this addendum's rows.")
    A("")
    A("## Second-order: learner_v2")
    A("")
    A("`learner_v2.jsonl` trains on every graded statement that the two registers resolved before each forecast. The 14 `IDX_INDEX WITH_FLOW_RUNUP` labels enter the slope shared by all relative statements (`BEATS_TWINS_k` and the like, in every family and market); the `SPEC_IDX` BASE5 labels enter the Speculation Register anchors. "
      "Each forecast record carries the ledger state it was computed from, so the learner's own `_record()` can be re-run per record with changed labels (first order: each record's earlier learner records stay as recorded). "
      "All 238 recorded forecasts are reproduced from the recorded ledgers (first row) and from the B-replayed labels (second row) before any C row is read.")
    A("")
    A("| Labels used | Records with raw forecasts changed (all / IDX) | Published changed (all / IDX) | Calls changed | Largest raw change | Largest published change |")
    A("|---|---|---|---|---|---|")
    names = {"W0_recorded_ledgers": "recorded ledgers (baseline)", "WB_B_replayed_labels": "B-replayed labels (baseline)", "C_labels_only": "C labels at the recorded timestamps (the ISAT flip)",
             "C_alka_pending_only": "ALKA BASE5 row absent (pending under C)", "C_all_recorded_timing": "both, recorded timestamps", "C_all_c_world_timing": "both, each changed label available only after its roll completes"}
    for k, nm in names.items():
        w = W[k]
        A(f"| {nm} | {w['all']['records_raw_changed']} / {w['IDX']['records_raw_changed']} | {w['all']['records_published_changed']} / {w['IDX']['records_published_changed']} | {w['all']['records_call_changed']} | {w['all']['max_abs_raw']:.5f} | {w['all']['max_abs_published']:.5f} |")
    A("")
    A(f"*Changed* means beyond the learner's own verification tolerance ({L['tolerance']:g}). Published probabilities stay at their anchors because the learner's gates are closed (alpha 0); the raw numbers are what the gate would pass through. "
      f"The only published changes are the {len(L['idx_published_changes'])} IDX forecasts sealed at {L['idx_published_changes'][0]['made_at'] if L['idx_published_changes'] else 'n/a'} ({', '.join(x['ticker'] for x in L['idx_published_changes'])}): "
      f"{', '.join(sorted({c[0] for x in L['idx_published_changes'] for c in x['changes']}))} move from {L['idx_published_changes'][0]['changes'][0][1]:.4f} to {L['idx_published_changes'][0]['changes'][0][2]:.4f}, "
      f"because the ALKA BASE5 row (recorded at {L['alka_pending_resolved_at'][0]}, {L['alka_minutes_before']:.0f} minutes before) would not exist yet under C and its `RUN30_5` label would be missing from the Speculation Register anchor.")
    A("")
    A("## Cross-checks of the earlier work (not the focus of this addendum)")
    A("")
    A(f"**Speculation Register, {SP['rows']} IDX rows** ({', '.join(f'{v} {k}' for k, v in SP['by_window'].items())}) with `speculation.resolve_set`. B reproduces {SP['B_reproduced']} of {SP['rows']}. "
      + "; ".join(f"{x['ticker']} {x['window']} (signal {x['signal_session']}) does not: {x['diagnosis']}" for x in SP["B_not_reproduced"]) + ". Under C: "
      + ("; ".join(f"{x['ticker']} {x['window']} is {x['status_C']}" for x in SP["rows_changed_under_C"]) or "no row changes") + ". "
      + " ".join(f"`{d['record']}`: " + "; ".join(f"{x['name']} closes {x['close']:g} from {x['prev']:g} on {x['session']}, the last bar, with ARB {x['arb_B']:g} under B and {x['arb_C']:g} under C" for x in d["locked_on_last_bar_under_C"]) + "." for d in SP["pending_detail"]))
    A("")
    A(f"**Ledger, {LG['rows']} IDX OUTCOME rows** (all use the {', '.join(k for k in LG['plan_types'])} loop in `paper.score`) with `paper.scoring_units` and `paper.score`, as `score_pending` does. B reproduces {LG['B_reproduced']} of {LG['rows']}; the others: "
      + "; ".join(f"{x['ticker']} (signal {x['signal_session']}): {x['diagnosis']}" for x in LG["B_not_reproduced"]) + ". "
      f"Under C {LG['rows_changed_under_C']} rows change relative to B: {LG['trades_exit_changed']} get a different exit session"
      + (" and return" if LG["trades_exit_changed"] == LG["trades_return_changed"] else f" ({LG['trades_return_changed']} a different return)") + f" ({len(LG['verdict_flips'])} verdict flips"
      + (": " + ", ".join(f"{t} {a} to {b}" for t, a, b in LG["verdict_flips"]) if LG["verdict_flips"] else "") + f") and {len(LG['rows_pending_under_C'])} stay pending ({', '.join(x['ticker'] for x in LG['rows_pending_under_C']) or 'none'}). "
      f"Mean net return over the {LG['traded_rows_in_both']} trades present under both: {pct(LG['mean_net_B'])} under B, {pct(LG['mean_net_C'])} under C. The earlier analysts' numbers were not read, so these are an independent count, not a comparison.")
    A("")
    A("## Caveats and unresolved items")
    A("")
    for c in caveats(S):
        A(f"- {c}")
    A("")
    A("## Reproduction")
    A("")
    if repro["previous_run_present"]:
        same = [f for f, v in repro["files"].items() if v is True]
        dif = [f for f, v in repro["files"].items() if v is False]
        A(f"This run was compared with the previous run in this folder: {len(same)} of {len(repro['files'])} deterministic outputs are byte-identical ({', '.join(same)})" + (f"; DIFFERENT: {', '.join(dif)}" if dif else "") + ". "
          "`run_meta.json` has the sha256 of each output.")
    else:
        A("No previous run was present to compare with; run the harness again and the report will state whether every output reproduces byte for byte.")
    A("")
    A("## Appendix: all 84 catalyst trades under B and C")
    A("")
    A("Exit session and net return after fees. *Same* means the exit and the return are unchanged in C.")
    A("")
    A("| Set | Role | Name | Exit B | Net B | Exit C | Net C | |")
    A("|---|---|---|---|---|---|---|---|")
    for t in tr_cat:
        mark = "same" if t["exit_changed_C_vs_B"] is False else ("**rolled**" if t["return_changed_C_vs_B"] is True else "rolled, same return")
        A(f"| {t['set_ticker']} | {t['role']} | {t['name']} | {t['exit_B']} | {pct(t['net_B'])} | {t['exit_C']} | {pct(t['net_C'])} | {mark} |")
    A("")
    A("## Files")
    A("")
    A("`harness.py` (one command), `results.csv` (one row per replayed record: 14 catalyst, 23 speculation, 93 ledger, 238 learner, with source line, record id and record hash), `trades.csv` (one row per replayed trade), `baseline_gate.csv` (field-by-field gate per record), "
      "`family_census.csv`, `lock_cells_changed.csv`, `learner_changes.csv`, `code_callers.txt`, `summary.json`, `run_meta.json`.")
    return "\n".join(lines) + "\n"


def caveats(S: dict) -> list[str]:
    C, SP, LG, P = S["catalyst_register"], S["speculation_crosscheck"], S["ledger_crosscheck"], S["panel"]
    sd = C["signed_diff"]
    return [
        f"**Final-bar replay, not a re-run of 2026-10-30.** Only the 2026-11-06 raw pull survives. Under C the {C['rows_changed_under_C']} changed sets could not have been written on 2026-10-30; the register would have written them on {' and '.join(C['last_exit_days_C'])}. "
        "The values here are what the register holds once the last roll closes.",
        "**The rule schedule is the one in `market.py` (C), and I did not verify it.** I did not check the 7% limit from 2026-10-19 or the Rp1 limit against decree texts; the module itself says the decrees were not read and that the real limit on 2026-10-19 for references Rp11 to 14 is unknown "
        f"(nothing here depends on that day). What the data say: closes bunch at the 7% limit price from {CUTOFF} (see the numbers above), {C['changed_trades_close_at_C_limit']} of the {C['trade_slots_exit_changed']} changed sales closed exactly at C's tick-rounded limit price, and across the panel "
        f"{P['changed_cells_close_at_C_limit']:,} of the {P['cells_locked_only_under_C']:,} cells that C locks and B does not close exactly at C's limit while {P['changed_cells_close_below_C_limit']} close below it (a regular-board name cannot do that under a 7% limit; those are 10%-board names, or names whose reference was reset). "
        "That corroborates the 7% schedule as the rule in force on 2026-10-30; it does not test the Rp11-14 rule, which nothing in this register uses.",
        "**Board membership is not in the data.** `limits()` models the regular boards for every name; a name on a 10% board is over-locked by a fall between 7% and 10%. In this register the only close below the 7% limit is "
        + (", ".join(f"{n} ({v:.1%})" for n, v in C["changed_trades_close_at_special_limit_not_C_limit"]) or "none") + ", which sits exactly at the 10% special-board limit and is locked on either reading.",
        "**The register is append-only and I changed no row.** A correction would be new RESOLUTION rows whose `revises` names the earlier hash. Because each learner forecast is verified against the ledger prefix it was made from, appended revisions would leave every existing forecast verifiable; "
        "only forecasts made after the revisions would train on the corrected labels. The learner results above are therefore what the forecasts would have been had the corrected labels existed at the time. Whether to append revisions, and a corrected `CATALYSTS.md` line, is the owner's decision.",
        f"**Descriptive only.** The register labels IDX_INDEX 'never tested'. The shift in the mean signed difference is {(sd['C']['mean'] - sd['B']['mean']) * 100:.2f} percentage points against a standard error of {sd['B']['se'] * 100:.2f} percentage points (14 sets, one index review, one signal session). The flipped {C['flow_outcomes_flipped'][0]} statement lands at "
        f"{pct(C['flow_outcome_flip_detail'][0]['signed_diff_C'])} signed difference (was {pct(C['flow_outcome_flip_detail'][0]['signed_diff_B'])}), so it is fragile.",
        "**The learner replay is first-order.** Each forecast is recomputed from its own recorded ledger prefix and the recorded earlier learner records; compounding through later forecasts' gates is not followed. The C-world timing (a changed label becomes available to the first learner batch on the calendar day of its last rolled sale, minus one second) is my assumption.",
        f"**Baseline differences in the cross-checks are data, not the lock.** Speculation Register: {', '.join(x['ticker'] + ' ' + x['window'] for x in SP['B_not_reproduced']) or 'none'}. Ledger: "
        + "; ".join(f"{x['ticker']}: {x['diagnosis']}" for x in LG["B_not_reproduced"]) + ". The raw 2026-11-05 payload did not survive, so the 'missing bar' reading of the Speculation Register row is an inference. "
        + (f"{len(LG['scored_before_exit_bar_final'])} ledger outcomes ({', '.join(t for t, _, _ in LG['scored_before_exit_bar_final'])}) were scored before their exit bar was final, a separate data-quality point outside this question." if LG["scored_before_exit_bar_final"] else ""),
        "**Decision text and sizing are stale after 2026-10-19 but do not read `market.py`.** DECISION rows size against the hard-coded `Policy.max_stop_distance` 0.15 and say 'locked at ARB, 15% below the entry'. The market.py correction cannot change them; PAPER-POLICY-v4 would need a new version.",
        "**POST20 windows of the same 14 sets are not resolvable yet** (signal 2026-10-28 plus 22 sessions, 2026-11-27 at the earliest), so they will be the first rows written under whichever rules are then in force.",
        "**Outside `paper/`:** `research/LLM_ARM_v1/calls*.jsonl` (5 IDX calls) hold forecasts only and persist no outcome; `llm_arm.workbench.resolve` imports BASE5 outcomes from the Speculation Register when it scores, so it inherits that register's numbers. "
        "`research/GUIDANCE_REVISION_v1/paper/ledger.jsonl` is US. The backtest runs under `results/` use 2023 windows and cannot touch sessions on or after 2026-10-19. These were read, not replayed.",
        ("**The code dirs, the repository and the frozen inputs were not touched.** The harness only hashes them and runs byte-identical overlay copies with bytecode writing off; snapshots of both code dirs, the repository's `paper/` and `research/` and the frozen inputs taken before and after the run are identical. "
         "Any `__pycache__` folders that already existed in the code dirs when the run started are listed in `run_meta.json` and were left as they were." if S["tree_unchanged_after_run"] else "Tree snapshots were skipped in this run."),
        f"**Environment.** python {S['versions']['python']}, numpy {S['versions']['numpy']}, pandas {S['versions']['pandas']}. The harness is deterministic; the Reproduction section says whether this run matched the previous one.",
    ]


if __name__ == "__main__":
    main()

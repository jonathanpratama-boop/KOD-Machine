#!/usr/bin/env python3
"""Impact analyst 3 (addendum): the October-2026 IDX lower-limit (ARB) correction and the OTHER persisted record families.

ONE COMMAND:   python3 harness.py            (about 1-2 minutes; writes next to this file; needs no network)

What it does, end to end
  0. Preflight: the frozen price manifest and every raw payload it names (sha256), B and C code identical except
     idxsig/market.py, the committed paper/ snapshot identical to the copies inside the code dirs.
  1. Hermetic overlays (work/B, work/C): byte-identical copies of the idxsig package of each variant, a copy of the
     committed paper/*.jsonl|md snapshot (so every ledger-reading function reads the copy), a read-only symlink to the
     repository's research/ folder (protocols, warm start) and to the frozen raw Yahoo payloads. Nothing is written
     into the two code dirs, the repository or the frozen inputs (hash/stat snapshots before and after prove it).
  2. Static census of the lock: every caller of lock_down / sellable / next_sellable / rolled_sessions / execute( /
     simulate( / resolve_set / score( / limits( / Market.build / from_panel, and every persisted record family under
     paper/ with its IDX row count, whether and how it depends on the lock, and whether it can be replayed.
  3. Replay, one subprocess per variant with cwd = the overlay and sys.path.insert(0, "."): the real
     paper.load_recent / paper._market / us_actions.yahoo_events on the FINAL PULL (2026-11-06, the only surviving raw
     pull) and the real catalysts.resolve_set (14 IDX_INDEX RUNUP rows, the priority) and speculation.resolve_set
     (the 23 IDX speculation rows, a cross-check of the earlier work) under B (shipped rules) and C (corrected rules).
     All are FINAL-BAR REPLAYS: a rolled sale is resolved with the bars up to 2026-11-06, a roll that runs past
     the last bar leaves the row pending.
  4. Baseline gate: the B replay must reproduce each recorded row, field by field (numbers within 1e-12, everything
     else exactly), before any C number is read.
  5. The register's own statistics (catalysts.statistics / render) recomputed on recorded rows, B-replayed rows and
     C-replayed rows, compared with the published line in paper/CATALYSTS.md.
  6. Second-order family: learner_v2 (its training rows are the registers' graded statements) is re-forecast with the
     learner's own functions from each record's own ledger prefix, under the recorded labels, the B-replayed labels
     and the C-replayed labels (two timing treatments); the baseline must reproduce all records.
  7. Writes results.csv, trades.csv, family_census.csv, lock_cells_changed.csv, learner_changes.csv, baseline_gate.csv,
     code_callers.txt, summary.json, report.md (every number in the report comes from this run).

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
IGNORE = {"resolved_at", "data", "prev_hash", "record_hash"}  # stamps and chain fields, never replayed
LEARNER_TOL = 2e-6  # learner2.VERIFY_TOL: the learner's own verification tolerance

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
    """Field-by-field comparison of two records (recursive leaves). None for b means 'no record'."""
    if b is None:
        return {"comparable": False, "n_leaves": 0, "n_numeric": 0, "max_abs_numeric": None, "n_numeric_diff": 0,
                "n_numeric_over_tol": 0, "numeric_diff_fields": [], "mismatch": ["<no replayed record>"], "missing": []}
    fa = dict(flatten({k: v for k, v in a.items() if k not in ignore}))
    fb = dict(flatten({k: v for k, v in b.items() if k not in ignore}))
    n_num, mx, ndiff, nover, numfields, mismatch, missing = 0, 0.0, 0, 0, set(), [], []
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
        elif x != y:
            mismatch.append(k)
    return {"comparable": True, "n_leaves": len(set(fa) | set(fb)), "n_numeric": n_num, "max_abs_numeric": mx,
            "n_numeric_diff": ndiff, "n_numeric_over_tol": nover, "numeric_diff_fields": sorted(numfields),
            "mismatch": mismatch, "missing": missing}


def fmt(x, nd=6):
    if x is None:
        return ""
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, float):
        return repr(x)
    return str(x)


def pct(x, nd=2):
    return "n/a" if x is None else f"{x:+.{nd}%}"


def write_csv(path, rows, cols):
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([fmt(r.get(c)) for c in cols])


def tree_snapshot(root: Path, sha: bool = True, skip_dirs=()) -> dict:
    """{relative path: (kind, size, mtime_ns, sha256|None)} of a tree (does not follow symlinked directories)."""
    snap = {}
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if (Path(dirpath) / d).name not in skip_dirs]
        for d in dirnames:
            p = Path(dirpath) / d
            st = p.lstat()
            snap[str(p.relative_to(root)) + "/"] = ("dir" if not p.is_symlink() else "symlink", 0, 0, None)
        for f in filenames:
            p = Path(dirpath) / f
            st = p.lstat()
            snap[str(p.relative_to(root))] = (
                "file", st.st_size, st.st_mtime_ns, sha256_file(p) if (sha and p.is_file() and not p.is_symlink()) else None)
    return snap


# =========================================================================================== census (static part)
CALLER_PATTERNS = [
    "lock_down", "sellable", "next_sellable", "rolled_sessions", r"\bexecute\(", r"\bsimulate\(", "resolve_set",
    r"\bscore\(", r"\blimits\(", r"Market\.build", r"Market\.from_panel", r"\bfrom_panel\(",
]
ROLE_BY_FILE = {  # what each module does with the lock, from reading it (see family_census.csv for the persisted side)
    "market.py": "DEFINES the limits (the only file B and C differ in)",
    "execution.py": "BUILDS lock_down (Market.build) and USES it in execute(): sellable = tradeable & ~lock_down",
    "speculation.py": "USES lock_down in simulate() (sellable(k)); resolve_set writes speculations.jsonl RESOLUTION rows",
    "catalysts.py": "resolve_set() calls speculation.simulate for the candidate and twins; writes catalysts.jsonl RESOLUTION rows",
    "paper.py": "score(): legacy loop uses lock_down; _score_plan() calls execution.execute; writes ledger.jsonl OUTCOME rows",
    "learner2.py": "no lock use; trains on the registers' graded statements (indirect)",
    "learner3.py": "no lock use; US only",
    "panel.py": "limits() for the panel quality summary (below_arb counts); not a paper/ record",
    "idx_events.py": "research event study (execute); results are not paper/ records",
    "event_study.py": "research event study (execute)",
    "backtest.py": "research backtest (Market.from_panel, execute)",
    "e1.py": "research E1 backtest", "e5.py": "research E5 backtest",
    "cli.py": "command wiring and corporate-action registry build; no lock use",
    "breakout.py": "research helper (Market)", "rules/__init__.py": "exposes lock_down to rule views; no rule reads it",
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


def session_fields(row) -> list[str]:
    """Every session-like date in a record (signal, entry, exit, scan session), recursively."""
    out = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("signal_session", "session", "entry_session", "exit_session", "time_exit_session") and isinstance(v, str):
                    out.append(v[:10])
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(row)
    return out


def exit_sessions(row) -> list[str]:
    out = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "exit_session" and isinstance(v, str):
                    out.append(v[:10])
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(row)
    return out


def is_idx(row) -> bool:
    return (row.get("market") or "IDX") == "IDX"


def build_census(paper: Path) -> list[dict]:
    """One row per (file, IDX record family) with counts computed from the committed snapshot."""
    led = load_jsonl(paper / "ledger.jsonl")
    spec = load_jsonl(paper / "speculations.jsonl")
    cat = load_jsonl(paper / "catalysts.jsonl")
    l1 = load_jsonl(paper / "learner.jsonl")
    l2 = load_jsonl(paper / "learner_v2.jsonl")
    l3 = load_jsonl(paper / "learner_v3.jsonl")
    book = load_jsonl(paper / "paper_book.jsonl")
    acct = load_jsonl(paper / "paper_account.jsonl")
    cacct = load_jsonl(paper / "crypto_account.jsonl")
    prem = load_jsonl(paper / "premove_shadow.jsonl")
    sens = load_jsonl(paper / "sensors" / "sensors.jsonl")
    micro = load_jsonl(paper / "microstructure" / "crypto.jsonl")
    rows = []

    def add(file, family, sel, depends, kind, path, replay, extra_touch=None, exposed=None, note=""):
        n = len(sel)
        touch = sum(1 for r in sel if (extra_touch(r) if extra_touch else max(session_fields(r) or [""]) >= CUTOFF))
        rows.append({"file": file, "record_family": family, "idx_rows": n, "idx_rows_touching_on_or_after_cutoff": touch,
                     "idx_rows_whose_exit_is_on_or_after_cutoff": exposed(sel) if exposed else "",
                     "depends_on_lock": depends, "dependence": kind, "code_path": path, "replayable_from_final_pull": replay,
                     "note": note})

    dec = {r["decision_id"]: r for r in led if r["type"] == "DECISION"}

    def outcome_touch(r):
        d = dec.get(r["decision_id"], {})
        return max(session_fields(r) + session_fields(d) + [""]) >= CUTOFF

    ex_exit = lambda sel: sum(1 for r in sel if any(s >= CUTOFF for s in exit_sessions(r)))  # noqa: E731
    add("ledger.jsonl", "SCAN (IDX; market absent = IDX)", [r for r in led if r["type"] == "SCAN" and is_idx(r)], "no", "none",
        "paper.scan_frame / rules read lock_up and never lock_down (grep); ARA is identical in B and C", "n/a (scan features were computed on each day's own pull; no lock dependence)")
    add("ledger.jsonl", "DECISION (IDX; market absent = IDX)", [r for r in led if r["type"] == "DECISION" and is_idx(r)], "no", "none",
        "paper._decide_v3 sizes on the hard-coded Policy.max_stop_distance 0.15 and prints '15% below the entry'; it never calls market.limits",
        "n/a", note="stale 15% text and sizing constant after 2026-10-19 are a policy constant, not market.py")
    add("ledger.jsonl", "OUTCOME (IDX)", [r for r in led if r["type"] == "OUTCOME" and is_idx(r)], "yes", "direct",
        "paper.score_pending -> paper.score -> _score_plan -> execution.execute (sellable = tradeable & ~lock_down; roll to next_sellable) | legacy loop sellable", "yes (covered by the earlier work)",
        extra_touch=outcome_touch, exposed=ex_exit)
    add("speculations.jsonl", "SPECULATION_SET (IDX)", [r for r in spec if r["type"] == "SPECULATION_SET" and is_idx(r)], "no", "none",
        "speculation.build_set: twins and signal from the scan's features", "n/a")
    add("speculations.jsonl", "RESOLUTION BASE5 (IDX)", [r for r in spec if r["type"] == "RESOLUTION" and is_idx(r) and r["window"] == "BASE5"], "yes", "direct",
        "speculation.resolve_set -> simulate(): sellable(k) = tradeable & ~lock_down; x = first sellable session >= target, None (pending) if none", "yes (cross-check here; covered by the earlier work)",
        exposed=ex_exit)
    add("speculations.jsonl", "RESOLUTION NEXT1/PATH20 (IDX)", [r for r in spec if r["type"] == "RESOLUTION" and is_idx(r) and r["window"] != "BASE5"], "no", "none",
        "path windows: next_return / path_statement use closes only", "yes (reproduced here as part of the 23)",
        extra_touch=lambda r: (r.get("resolved_at") or "")[:10] >= CUTOFF)
    for typ, dep, kind, path, rep in (
        ("BATCH", "no", "none", "catalysts.idx_index_batch: event list statuses", "n/a"),
        ("CATALYST_SET", "no", "none", "catalysts.idx_index_batch: twins by draw_twins from the scan features", "n/a"),
        ("TAG", "no", "none", "catalysts.dilution_tags: EmitenNews headlines", "n/a"),
        ("RESOLUTION", "yes", "direct",
         "catalysts.resolve_set -> speculation.simulate (candidate and each twin): sellable(k) = tradeable & ~lock_down; the sale rolls to the next sellable session",
         "yes (the priority of this addendum)"),
    ):
        sel = [r for r in cat if r["type"] == typ and is_idx(r)]
        add("catalysts.jsonl", f"{typ} (IDX_INDEX)", sel, dep, kind, path, rep, exposed=ex_exit if typ == "RESOLUTION" else None,
            extra_touch=(lambda r: (r.get("sealed_at") or r.get("made_at") or r.get("resolved_at") or "")[:10] >= CUTOFF) if typ in ("BATCH", "TAG") else None)
    add("catalysts.jsonl", "all US rows (BATCH/CATALYST_SET/TAG; no RESOLUTION yet)", [r for r in cat if not is_idx(r)], "no", "none",
        "US markets are built with price_limits=False: lock_down is all False", "n/a (IDX rows: 0)")
    lock_sensitive = ("IDX_INDEX:WITH_FLOW_RUNUP",)

    def l2_exposed(sel):
        return sum(1 for r in sel if any(k in (r.get("training") or {}).get("live_rows", {}) for k in lock_sensitive))

    add("learner_v2.jsonl", "LEARNER2_FORECAST (SPEC_IDX)", [r for r in l2 if is_idx(r)], "yes", "indirect (training labels)",
        "learner2.train -> live_rows -> outcomes() reads RESOLUTION cone outcomes: IDX_INDEX WITH_FLOW_RUNUP (shared RELATIVE slope) and SPEC_IDX BASE5 statements (anchors)",
        "yes (the learner's own _record() on each record's ledger prefix, with replayed labels)",
        exposed=lambda sel: sum(1 for r in sel if any(k in (r.get("training") or {}).get("live_rows", {}) for k in lock_sensitive)))
    add("learner_v2.jsonl", "LEARNER2_FORECAST (US and CRYPTO rows, for reference)", [r for r in l2 if not is_idx(r)], "indirect only", "indirect (shared slope)",
        "same labels reach US/CRYPTO forecasts through the shared RELATIVE slope", "yes (same replay)", exposed=l2_exposed)
    add("learner_v3.jsonl", "LEARNER3_FORECAST (SPEC_US)", [r for r in l3 if is_idx(r)], "no", "none", "US only; trains on SPEC_US rows and its own forecasts", "n/a (IDX rows: 0)")
    add("learner.jsonl", "LEARNER_FORECAST (SEC13D)", [r for r in l1 if is_idx(r) and r.get("family") != "SEC13D"], "no", "none", "US SEC13D only", "n/a (IDX rows: 0)")
    idx_pat = re.compile(r"SCAN-\d{4}-")  # IDX set ids carry no market infix
    add("paper_book.jsonl", "BOOK_PLAN", [r for r in book if idx_pat.search(r.get("set_id", ""))], "no", "none", "US spikes only", "n/a (IDX rows: 0)")
    add("paper_account.jsonl", "ACCT_* (US paper account)", [r for r in acct if idx_pat.search(r.get("set_id", ""))], "no", "none", "exec_us on US bars only", "n/a (IDX rows: 0)")
    add("crypto_account.jsonl", "ACCT_* / CRYPTO_QUOTE", [r for r in cacct if idx_pat.search(r.get("set_id", ""))], "no", "none", "crypto", "n/a (IDX rows: 0)")
    add("premove_shadow.jsonl", "PREMOVE_SHADOW_*", [r for r in prem if idx_pat.search(json.dumps(r)[:400])], "no", "none", "crypto (Binance) only", "n/a (IDX rows: 0)")
    add("microstructure/crypto.jsonl", "TIMELINE/BOOK", [r for r in micro if idx_pat.search(r.get("scan_id", ""))], "no", "none", "crypto order books", "n/a (IDX rows: 0)")
    add("sensors/sensors.jsonl", "SENSOR_ALERT emitennews_dilution (IDX-related)", [r for r in sens if r.get("source") == "emitennews_dilution"], "no", "none",
        "news headlines, no prices", "n/a", extra_touch=lambda r: (r.get("observed_at") or "")[:10] >= CUTOFF)
    scans = sorted(p.name for p in (paper / "scans").iterdir() if p.is_dir()) if (paper / "scans").exists() else []
    idx_scans = [n for n in scans if not n.startswith(("SCAN-US-", "SCAN-CRYPTO-"))]
    rows.append({"file": "scans/", "record_family": "scan directories (IDX = names without a market infix)", "idx_rows": len(idx_scans),
                 "idx_rows_touching_on_or_after_cutoff": sum(1 for n in idx_scans if re.search(r"(\d{4}-\d{2}-\d{2})", n).group(1) >= CUTOFF),
                 "idx_rows_whose_exit_is_on_or_after_cutoff": "", "depends_on_lock": "no", "dependence": "none",
                 "code_path": "features.csv built by rules that read lock_up only", "replayable_from_final_pull": "n/a", "note": ""})
    for name, what in (("catalysts_form4/", "EDGAR Form 4 dumps (US)"), ("timestamps/", "RFC 3161 tokens"), ("sensors/raw/", "raw feed pulls"), ("microstructure/raw/", "crypto raw books")):
        rows.append({"file": name, "record_family": what, "idx_rows": 0, "idx_rows_touching_on_or_after_cutoff": 0,
                     "idx_rows_whose_exit_is_on_or_after_cutoff": "", "depends_on_lock": "no", "dependence": "none",
                     "code_path": "no price or lock input", "replayable_from_final_pull": "n/a", "note": ""})
    for name in ("README.md", "CATALYSTS.md", "SPECULATIONS.md", "LEARNER_V2.md", "LEARNER_V3.md", "CALL_CERT.md", "PAPER_ACCOUNT.md", "PAPER_BOOK.md", "CRYPTO_ACCOUNT.md", "LEARNER.md", "PREMOVE_SHADOW.md"):
        rows.append({"file": name, "record_family": "derived report (rendered from the ledgers)", "idx_rows": "", "idx_rows_touching_on_or_after_cutoff": "",
                     "idx_rows_whose_exit_is_on_or_after_cutoff": "", "depends_on_lock": "only through the ledgers it renders",
                     "dependence": "derived", "code_path": "catalysts.render / speculation render / learner render",
                     "replayable_from_final_pull": "re-rendered for CATALYSTS.md in this harness", "note": ""})
    return rows


# ================================================================================================ overlays and checks
def preflight() -> dict:
    info = {}
    assert MANIFEST.exists(), MANIFEST
    sha = sha256_file(MANIFEST)
    assert sha.startswith(MANIFEST_SHA12), f"manifest sha {sha}"
    lines = [json.loads(x) for x in MANIFEST.read_text(encoding="utf-8").splitlines() if x.strip()]
    header, recs = lines[0], lines[1:]
    assert len(recs) == 920 and header["n_files"] == 920 and header["ok"] == 920, "manifest is not the 920-ticker final pull"
    raw_dir = RAW_ROOT / "20261106T101853Z"
    bad = []
    for r in recs:
        p = RAW_ROOT / Path(r["path"]).relative_to("data/raw/yahoo_recent")
        if not p.exists() or sha256_file(p) != r["sha256"]:
            bad.append(r["ticker"])
    assert not bad, f"raw payloads missing or hash mismatch: {bad[:5]} ({len(bad)})"
    info["manifest"] = {"file": MANIFEST.name, "sha256": sha, "n_tickers": len(recs), "coverage_window": header["coverage_window"],
                        "finished_at": header["finished_at"], "raw_dir": str(raw_dir), "payloads_verified": len(recs)}
    # the manifest of the pull the 14 rows were written on (raw payloads did not survive)
    om = ORIG_MANIFEST.read_text(encoding="utf-8").splitlines()
    oh = json.loads(om[0])
    info["orig_manifest"] = {"file": ORIG_MANIFEST.name, "sha256": sha256_file(ORIG_MANIFEST), "coverage_window": oh["coverage_window"],
                             "first_date_sample": json.loads(om[1])["first_date"], "raw_payloads_present": (RAW_ROOT / "20261030T104351Z").exists()}
    info["final_manifest_first_date_sample"] = recs[0]["first_date"]
    # code: B and C identical except market.py
    hashes = {}
    for v, root in CODE.items():
        hashes[v] = {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted((root / "idxsig").rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    diff = sorted(k for k in set(hashes["B"]) | set(hashes["C"]) if hashes["B"].get(k) != hashes["C"].get(k))
    assert diff == ["idxsig/market.py"], f"B and C differ in {diff}"
    info["code"] = {"n_files": len(hashes["B"]), "differing_files": diff, "market_sha256": {v: hashes[v]["idxsig/market.py"] for v in "BC"}}
    # paper snapshot: code dirs == repo working tree == base commit
    ok = {}
    for name in ("ledger.jsonl", "speculations.jsonl"):
        shas = {v: sha256_file(CODE[v] / "paper" / name) for v in "BC"}
        shas["repo"] = sha256_file(REPO_PAPER / name)
        try:
            blob = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE_COMMIT}:idx-signals/paper/{name}"], capture_output=True, check=True).stdout
            shas["base_commit"] = hashlib.sha256(blob).hexdigest()
        except Exception as exc:  # noqa: BLE001 - git is optional evidence
            shas["base_commit"] = f"unavailable ({type(exc).__name__})"
        ok[name] = shas
        assert len({v for k, v in shas.items() if not v.startswith("unavailable")}) == 1, f"{name} differs: {shas}"
    info["paper_snapshot_identity"] = ok
    committed = {}
    for p in sorted(REPO_PAPER.glob("*.jsonl")):
        try:
            blob = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE_COMMIT}:idx-signals/paper/{p.name}"], capture_output=True, check=True).stdout
            committed[p.name] = hashlib.sha256(blob).hexdigest() == sha256_file(p)
        except Exception:  # noqa: BLE001
            committed[p.name] = None
    info["paper_jsonl_equal_to_base_commit"] = committed
    return info


def build_overlay(v: str) -> Path:
    base = WORK / v
    root = base / "idx-signals"
    if base.exists():
        shutil.rmtree(base)
    (root / "paper").mkdir(parents=True)
    (root / "data" / "raw").mkdir(parents=True)
    shutil.copytree(CODE[v] / "idxsig", root / "idxsig", ignore=shutil.ignore_patterns("__pycache__"))
    for f in sorted(list(REPO_PAPER.glob("*.jsonl")) + list(REPO_PAPER.glob("*.md"))):
        shutil.copy2(f, root / "paper" / f.name)
    (root / "research").symlink_to(REPO_RESEARCH)
    (root / "data" / "raw" / "yahoo_recent").symlink_to(RAW_ROOT)
    for p in sorted((CODE[v] / "idxsig").rglob("*")):  # copy is byte-identical
        if p.is_file() and "__pycache__" not in p.parts:
            q = root / "idxsig" / p.relative_to(CODE[v] / "idxsig")
            assert sha256_file(p) == sha256_file(q), f"overlay copy differs: {p}"
    return root


def run_worker(kind: str, arg: str, cwd: Path) -> None:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "LC_ALL": "C.UTF-8", "HOME": str(WORK)}
    cmd = [sys.executable, "-I", "-B", str(HERE / "harness.py"), "--worker", kind, arg]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    sys.stdout.write(f"  worker {kind} {arg}: rc={p.returncode} in {time.time() - t0:.1f}s\n")
    if p.returncode != 0:
        sys.stderr.write(p.stdout[-3000:] + "\n" + p.stderr[-6000:] + "\n")
        raise SystemExit(f"worker {kind} {arg} failed")


# ============================================================================================ worker: replay (B or C)
def _np_default(o):
    import numpy as np

    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def worker_replay(variant: str) -> None:
    sys.dont_write_bytecode = True
    sys.path.insert(0, ".")
    import warnings

    import numpy as np

    import idxsig
    from idxsig import catalysts as cat
    from idxsig import market as mk
    from idxsig import paper, speculation as spec, us_actions

    cwd = Path.cwd().resolve()
    assert Path(idxsig.__file__).resolve() == cwd / "idxsig" / "__init__.py", idxsig.__file__
    assert Path(mk.__file__).resolve() == cwd / "idxsig" / "market.py"
    t0 = time.time()
    out = {"variant": variant, "idxsig_file": str(Path(idxsig.__file__).resolve()), "market_sha256": sha256_file(mk.__file__),
           "versions": {"python": sys.version.split()[0], "numpy": np.__version__}}
    import pandas as pd

    out["versions"]["pandas"] = pd.__version__
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        df, data = paper.load_recent(MANIFEST, "IDX", purpose="scoring")
        m = paper._market(df, "IDX")
        events = us_actions.yahoo_events(MANIFEST, market="IDX")
        out["data"] = {"manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"], "rows": int(len(df)),
                       "tickers": int(m.shape[0]), "sessions": int(m.shape[1]), "first_session": str(m.dates[0]), "last_session": str(m.dates[-1]),
                       "split_events": int(len(events))}
        dates = [str(x) for x in m.dates]
        tick = [str(x) for x in m.tickers]
        tick_ix = {t: i for i, t in enumerate(tick)}
        # the limits as Market.build sees them, recomputed here to check the lock formula and to record the ARB prices
        ref = np.where(np.isfinite(m.prev) & (m.prev > 0), m.prev, np.nan)
        safe_ref = np.nan_to_num(ref, nan=1.0)
        day_grid = np.broadcast_to(m.dates.astype("datetime64[D]"), m.close.shape)
        ara, arb = mk.limits(safe_ref, day_grid)
        sp_ara, sp_arb = mk.special_limits(safe_ref)
        one_price = (m.high == m.low) & (m.low == m.close)
        sub50 = ((m.close < 50) | (ref < 50)) & (day_grid < np.datetime64("2026-09-28"))
        thin = one_price | sub50
        ld = m.tradeable & np.isfinite(ref) & (m.close < ref) & ((m.close <= arb) | (thin & (m.close <= sp_arb)))
        lu = m.tradeable & np.isfinite(ref) & ((m.close >= ara) | (thin & (m.close >= sp_ara)))
        out["lock_formula_reproduced"] = bool((ld == m.lock_down).all() and (lu == m.lock_up).all())
        OUTD.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(OUTD / f"panel_{variant}.npz", tickers=np.array(tick), dates=np.array(dates), close=m.close, prev=m.prev, high=m.high,
                            low=m.low, volume=m.volume, present=m.present, tradeable=m.tradeable, lock_down=m.lock_down, lock_up=m.lock_up,
                            arb=arb, ara=ara, sp_arb=sp_arb, one_price=one_price)

        def cell(n: int, k: int) -> dict:
            f = lambda a: None if not np.isfinite(a[n, k]) else float(a[n, k])  # noqa: E731
            return {"date": dates[k], "present": bool(m.present[n, k]), "tradeable": bool(m.tradeable[n, k]), "close": f(m.close), "prev": f(m.prev),
                    "high": f(m.high), "low": f(m.low), "volume": f(m.volume), "lock_down": bool(m.lock_down[n, k]), "lock_up": bool(m.lock_up[n, k]),
                    "arb": f(arb), "ara": f(ara), "sp_arb": f(sp_arb), "one_price": bool(one_price[n, k])}

        def trade_diags(rec, hold):
            """For the candidate and each twin (same order as the record): the target session's cell and the exit session's cell."""
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
                target = e + hold
                diag.append({"name": name, "entry_idx": e, "target_idx": target, "exit_idx": x, "rolled": x - target, "target": cell(n, target),
                             "exit": cell(n, x), "path": [cell(n, k) for k in range(target, x + 1)]})
            return diag

        cats, specs = cat.cat_lines(), spec.spec_lines()
        csets = {r["set_id"]: r for r in cats if r["type"] == "CATALYST_SET"}
        ssets = {r["set_id"]: r for r in specs if r["type"] == "SPECULATION_SET"}
        reps = []
        for i, r in enumerate(cats):
            if r["type"] == "RESOLUTION" and is_idx(r):
                s = csets[r["set_id"]]
                new = cat.resolve_set(s, r["window"], m, events, None)
                hold = s["windows"][r["window"]].get("holding_sessions")
                reps.append({"file": "catalysts.jsonl", "line": i + 1, "source": r, "replay": new, "diag": trade_diags(new, hold)})
        for i, r in enumerate(specs):
            if r["type"] == "RESOLUTION" and is_idx(r):
                s = ssets[r["set_id"]]
                new = spec.resolve_set(s, r["window"], m, events, None)
                w = spec.windows()[r["window"]]
                reps.append({"file": "speculations.jsonl", "line": i + 1, "source": r, "replay": new,
                             "diag": trade_diags(new, w.get("holding_sessions") if w["kind"] == "plan" else None)})
        out["replays"] = reps
        # the register's own statistics, on recorded rows and on this variant's replayed rows
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
            ls = text.splitlines()
            block = []
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
        out["published_lines"] = idx_block((cwd / "paper" / "CATALYSTS.md").read_text(encoding="utf-8"))
        out["published_calibration_rows"] = [l for l in (cwd / "paper" / "CATALYSTS.md").read_text(encoding="utf-8").splitlines() if l.startswith("| IDX_INDEX |")]
        out["chain_problems"] = {n: paper.verify_chain(cwd / "paper" / n) for n in ("catalysts.jsonl", "speculations.jsonl", "learner_v2.jsonl")}
    out["warnings"] = [[w.category.__name__, str(w.message)[:200]] for w in wl]
    out["elapsed_s"] = round(time.time() - t0, 1)
    OUTD.mkdir(parents=True, exist_ok=True)
    (OUTD / f"replay_{variant}.json").write_text(json.dumps(out, default=_np_default, allow_nan=False), encoding="utf-8")


# ============================================================================================ worker: learner replay
def worker_learner(worlds_path: str) -> None:
    sys.dont_write_bytecode = True
    sys.path.insert(0, ".")
    from datetime import datetime, timedelta

    import numpy as np

    import idxsig
    from idxsig import catalysts as cr
    from idxsig import learner2 as L2
    from idxsig import speculation as spec

    cwd = Path.cwd().resolve()
    assert Path(idxsig.__file__).resolve() == cwd / "idxsig" / "__init__.py"
    spec_in = json.loads(Path(worlds_path).read_text(encoding="utf-8"))
    cat, spc = cr.cat_lines(), spec.spec_lines()
    lrecs = L2.lines()
    proto, sha = L2.protocol()
    batch_times = sorted({f["made_at"] for f in lrecs})

    def avail(day: str) -> str:
        t = next((t for t in batch_times if t[:10] >= day), None)
        if t is None:
            return "9999-12-31T00:00:00Z"
        return (datetime.fromisoformat(t.replace("Z", "+00:00")) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def apply(world):
        lists = {"catalysts.jsonl": list(cat), "speculations.jsonl": list(spc)}
        for mod in world["mods"]:
            lst = lists[mod["file"]]
            row = lst[mod["line"] - 1]
            assert row["record_hash"] == mod["record_hash"], (mod["file"], mod["line"])
            new = dict(row)
            if mod.get("content"):
                new.update(mod["content"])
            if mod.get("pending"):
                new["resolved_at"] = "9999-12-31T00:00:00Z"
            elif mod.get("availability") == "last_exit_day":
                new["resolved_at"] = avail(mod["last_exit_day"])
            lst[mod["line"] - 1] = new
        return lists["catalysts.jsonl"], lists["speculations.jsonl"]

    results = {}
    for world in spec_in["worlds"]:
        cat_w, spc_w = apply(world)
        ctxs, recs = {}, []
        for i, f in enumerate(lrecs):
            inp = f["inputs"]
            nc, ns = inp["catalysts"][0], inp["speculations"][0]
            assert L2._head(cat[:nc]) == inp["catalysts"] and L2._head(spc[:ns]) == inp["speculations"], f"ledger prefix of learner record {i} is not a prefix of the snapshot"
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
                calls += (fc.get("call") != a.get("call"))
            recs.append({"i": i, "record_hash": f["record_hash"], "set_id": f["set_id"], "family": f["family"], "market": f["market"], "ticker": f["ticker"],
                         "signal_session": f["signal_session"], "made_at": f["made_at"], "fields_differing": diff, "n_statements": len(f["forecasts"]),
                         "n_raw_changed": int(n_raw), "n_published_changed": int(n_pub), "max_abs_raw": mx_raw, "max_abs_published": mx_pub,
                         "max_abs_anchor": mx_anc, "max_abs_deviation": mx_dev, "call_changes": int(calls), "published_changes": pub_changes,
                         "live_rows_recorded": {k: v for k, v in f["training"]["live_rows"].items() if k.startswith(("IDX_INDEX", "SPEC_IDX"))},
                         "live_rows_replayed": {k: v for k, v in again["training"]["live_rows"].items() if k.startswith(("IDX_INDEX", "SPEC_IDX"))}})
        results[world["name"]] = recs
    (OUTD / "learner_results.json").write_text(json.dumps({"worlds": results, "mods": {w["name"]: w["mods"] for w in spec_in["worlds"]}, "batch_times": batch_times,
                                                          "verify_tol": L2.VERIFY_TOL}, default=_np_default, allow_nan=False), encoding="utf-8")


# =========================================================================================================== aggregate
def lastexit(rec) -> str | None:
    ex = []
    if rec is None:
        return None
    for t in [rec["candidate"].get("trade")] + [t.get("trade") for t in rec["twins"]]:
        if t:
            ex.append(t["exit_session"])
    return max(ex) if ex else None


def trade_list(rec):
    """[(role, name, trade|None, status)] for the candidate and each twin of a RESOLUTION record (or Nones if pending)."""
    if rec is None:
        return None
    out = [("candidate", rec["ticker"], rec["candidate"].get("trade"), rec["candidate"].get("status"))]
    out += [("twin", t["ticker"], t.get("trade"), t.get("status")) for t in rec["twins"]]
    return out


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

    T0 = time.time()
    print("== preflight")
    pre = preflight()
    snaps_before = {}
    if not args.no_clean_check:
        snaps_before = {"code_B": tree_snapshot(CODE["B"]), "code_C": tree_snapshot(CODE["C"]), "repo_paper": tree_snapshot(REPO_PAPER, sha=True, skip_dirs=("timestamps", "scans", "raw")),
                        "repo_research": tree_snapshot(REPO_RESEARCH, sha=False), "frozen_top": {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in FROZEN.iterdir() if p.is_file()}}
    print("== overlays")
    if WORK.exists():
        shutil.rmtree(WORK)
    OUTD.mkdir(parents=True)
    roots = {v: build_overlay(v) for v in "BC"}
    print("== static census")
    lines, per_file = caller_scan(roots["B"])
    (HERE / "code_callers.txt").write_text(
        "# Callers of the lower-limit machinery in the shipped (B) idxsig package; pattern in brackets.\n"
        "# Roles (from reading each module):\n" + "".join(f"#   {k}: {v}\n" for k, v in sorted(ROLE_BY_FILE.items())) + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    census = build_census(REPO_PAPER)
    write_csv(HERE / "family_census.csv", census, ["file", "record_family", "idx_rows", "idx_rows_touching_on_or_after_cutoff", "idx_rows_whose_exit_is_on_or_after_cutoff",
                                                  "depends_on_lock", "dependence", "code_path", "replayable_from_final_pull", "note"])
    print("== replay workers (final-bar replay on the 2026-11-06 pull)")
    for v in "BC":
        run_worker("replay", v, roots[v])
    R = {v: json.loads((OUTD / f"replay_{v}.json").read_text(encoding="utf-8")) for v in "BC"}
    P = {v: np.load(OUTD / f"panel_{v}.npz") for v in "BC"}

    # ------------------------------------------------------------------ panel-level lock comparison
    arr_eq = lambda a, b: bool(np.array_equal(a, b, equal_nan=True)) if a.dtype.kind == "f" else bool(np.array_equal(a, b))  # noqa: E731
    same_arrays = {k: arr_eq(P["B"][k], P["C"][k]) for k in ("tickers", "dates", "close", "prev", "high", "low", "volume", "present", "tradeable", "lock_up", "ara", "sp_arb", "one_price")}
    assert all(same_arrays.values()), same_arrays
    ld = {v: P[v]["lock_down"] for v in "BC"}
    diff = ld["B"] != ld["C"]
    only_c = diff & ld["C"] & ~ld["B"]
    only_b = diff & ld["B"] & ~ld["C"]
    ii, jj = np.nonzero(diff)
    tickers, dates = [str(x) for x in P["B"]["tickers"]], [str(x) for x in P["B"]["dates"]]
    lock_rows = []
    for i, j in zip(ii, jj):
        prev, close = float(P["B"]["prev"][i, j]), float(P["B"]["close"][i, j])
        lock_rows.append({"ticker": tickers[i], "session": dates[j], "prev_close": prev, "close": close, "change": close / prev - 1 if prev > 0 else None,
                          "arb_B": float(P["B"]["arb"][i, j]), "arb_C": float(P["C"]["arb"][i, j]), "locked_B": bool(ld["B"][i, j]), "locked_C": bool(ld["C"][i, j]),
                          "one_price_bar": bool(P["B"]["one_price"][i, j]), "reference_at_most_14": prev <= 14, "volume": float(P["B"]["volume"][i, j])})
    lock_rows.sort(key=lambda r: (r["session"], r["ticker"]))
    write_csv(HERE / "lock_cells_changed.csv", lock_rows, ["ticker", "session", "prev_close", "close", "change", "arb_B", "arb_C", "locked_B", "locked_C", "one_price_bar", "reference_at_most_14", "volume"])
    by_session = Counter(r["session"] for r in lock_rows)
    panel_sum = {"cells": int(ld["B"].size), "sessions": len(dates), "tickers": len(tickers), "lock_down_cells_B": int(ld["B"].sum()), "lock_down_cells_C": int(ld["C"].sum()),
                 "cells_locked_only_under_C": int(only_c.sum()), "cells_locked_only_under_B": int(only_b.sum()), "lock_up_cells_differing": int((P["B"]["lock_up"] != P["C"]["lock_up"]).sum()),
                 "common_arrays_identical": same_arrays, "changed_cells_by_session": dict(sorted(by_session.items())),
                 "changed_cells_before_cutoff": int(sum(v for k, v in by_session.items() if k < CUTOFF)),
                 "changed_cells_with_reference_at_most_14": int(sum(r["reference_at_most_14"] for r in lock_rows)),
                 "lock_formula_reproduced": {v: R[v]["lock_formula_reproduced"] for v in "BC"}, "warnings": {v: R[v]["warnings"] for v in "BC"}}

    # ------------------------------------------------------------------ per-record comparison
    pairs = {}
    for xb, xc in zip(R["B"]["replays"], R["C"]["replays"]):
        assert (xb["file"], xb["line"]) == (xc["file"], xc["line"]) and xb["source"]["record_hash"] == xc["source"]["record_hash"]
        pairs[(xb["file"], xb["line"])] = (xb, xc)
    results_rows, trade_rows, gate_rows = [], [], []
    for key, (xb, xc) in pairs.items():
        src, rb, rc = xb["source"], xb["replay"], xc["replay"]
        gate = compare_records(src, rb)
        c_vs_b = compare_records(rb, rc) if rb is not None else compare_records(src, rc)
        xb["gate"], xb["c_vs_b"] = gate, c_vs_b
        gate_rows.append({"scope": "catalyst_register" if xb["file"] == "catalysts.jsonl" else "speculation_register", "source_file": xb["file"], "source_line": xb["line"],
                          "record_id": src["set_id"], "window": src["window"], "record_hash": src["record_hash"], "replay_status_B": (rb or {}).get("status", "PENDING"),
                          "leaves_compared": gate["n_leaves"], "numeric_leaves": gate["n_numeric"], "numeric_leaves_not_bit_identical": gate["n_numeric_diff"],
                          "max_abs_numeric_diff": gate["max_abs_numeric"], "numeric_leaves_over_1e-12": gate["n_numeric_over_tol"], "nonnumeric_or_missing_mismatches": len(gate["mismatch"]) - gate["n_numeric_over_tol"] + len(gate["missing"]),
                          "reproduced_within_1e-12": gate["comparable"] and not gate["mismatch"] and not gate["missing"],
                          "differing_numeric_fields": ";".join(gate["numeric_diff_fields"]), "mismatching_paths": ";".join((gate["mismatch"] + gate["missing"])[:6])})
    cat_pairs = [(k, v) for k, v in pairs.items() if k[0] == "catalysts.jsonl"]
    spec_pairs = [(k, v) for k, v in pairs.items() if k[0] == "speculations.jsonl"]

    def flow_outcome(rec):
        if rec is None:
            return None
        return next((c["outcome"] for c in rec["cone"] if c["id"] == "WITH_FLOW_RUNUP"), None)

    def signed(rec):
        return None if rec is None or not rec.get("paired") else rec["paired"]["diff"] * rec.get("direction", 1)

    for (file, line), (xb, xc) in pairs.items():
        src, rb, rc = xb["source"], xb["replay"], xc["replay"]
        scope = "catalyst_register_IDX" if file == "catalysts.jsonl" else "speculation_register_IDX (cross-check of the earlier work)"
        tl = {"rec": trade_list(src), "B": trade_list(rb), "C": trade_list(rc)}
        n_tr = len([t for t in tl["rec"] if t[2]]) if tl["rec"] else 0
        ex_changed, ret_changed, changed_names = 0, 0, []
        if tl["B"] is not None and tl["C"] is not None:
            for (role, name, tb, sb), (_, _, tc, sc) in zip(tl["B"], tl["C"]):
                if (tb is None) != (tc is None) or (tb and tc and (tb["exit_session"] != tc["exit_session"] or tb["exit_reason"] != tc["exit_reason"])):
                    ex_changed += 1
                    ret_changed += int(bool(tb and tc and abs(tb["net_return"] - tc["net_return"]) > TOL))
                    changed_names.append(f"{role}:{name}")
        crec = src["candidate"].get("trade") if isinstance(src.get("candidate"), dict) else None
        cb_ = (rb or {}).get("candidate", {}).get("trade") if rb else None
        cc_ = (rc or {}).get("candidate", {}).get("trade") if rc else None
        row = {"scope": scope, "source_file": file, "source_line": line, "record_type": "RESOLUTION", "record_id": src["set_id"], "record_hash": src["record_hash"],
               "family": src.get("family", "SPECULATION"), "market": "IDX", "ticker": src["ticker"], "window": src["window"], "signal_session": src["signal_session"], "direction": src.get("direction", 1),
               "status_recorded": src["status"], "status_B": (rb or {}).get("status", "PENDING"), "status_C": (rc or {}).get("status", "PENDING (a sale rolls past the last bar)"),
               "n_trades": n_tr, "n_trades_exit_changed_C_vs_B": ex_changed if rc is not None else "", "n_trades_return_changed_C_vs_B": ret_changed if rc is not None else "",
               "trades_changed_C_vs_B": ";".join(changed_names), "C_changes_row": (rc is None) or bool(xb["c_vs_b"]["mismatch"] or xb["c_vs_b"]["missing"]),
               "cand_exit_recorded": crec["exit_session"] if crec else "", "cand_exit_B": cb_["exit_session"] if cb_ else "", "cand_exit_C": cc_["exit_session"] if cc_ else "",
               "cand_net_recorded": crec["net_return"] if crec else "", "cand_net_B": cb_["net_return"] if cb_ else "", "cand_net_C": cc_["net_return"] if cc_ else "",
               "paired_diff_recorded": (src.get("paired") or {}).get("diff", ""), "paired_diff_B": ((rb or {}).get("paired") or {}).get("diff", ""), "paired_diff_C": ((rc or {}).get("paired") or {}).get("diff", ""),
               "signed_diff_recorded": signed(src), "signed_diff_B": signed(rb), "signed_diff_C": signed(rc),
               "flow_outcome_recorded": flow_outcome(src), "flow_outcome_B": flow_outcome(rb), "flow_outcome_C": flow_outcome(rc),
               "flow_outcome_flipped_C_vs_B": (flow_outcome(rb) is not None and flow_outcome(rc) is not None and flow_outcome(rb) != flow_outcome(rc)) if file == "catalysts.jsonl" else ""}
        g = next(g for g in gate_rows if g["source_file"] == file and g["source_line"] == line)
        row["B_reproduces_recorded"] = g["reproduced_within_1e-12"]
        row["B_max_abs_numeric_diff"] = g["max_abs_numeric_diff"]
        row["C_leaves_changed_vs_B"] = len(xb["c_vs_b"]["mismatch"]) + len(xb["c_vs_b"]["missing"]) if rc is not None else ""
        row["C_last_exit_session"] = lastexit(rc) or ""
        results_rows.append(row)
        # trades
        if tl["rec"] is None or src.get("candidate", {}).get("status") == "PATH":
            continue
        for idx, (role, name, trec, srec) in enumerate(tl["rec"]):
            tb = tl["B"][idx][2] if tl["B"] else None
            tc = tl["C"][idx][2] if tl["C"] else None
            db = (xb["diag"] or [None] * 99)[idx] if xb["diag"] else None
            dc = (xc["diag"] or [None] * 99)[idx] if xc["diag"] else None
            tgt_b = db["target"] if db else None
            tgt_c = dc["target"] if dc else None
            gross_move = (tgt_b["close"] / tgt_b["prev"] - 1) if tgt_b and tgt_b["prev"] else None
            changed_exit = bool(tb and tc and (tb["exit_session"] != tc["exit_session"] or tb["exit_reason"] != tc["exit_reason"]))
            trade_rows.append({
                "scope": scope, "source_file": file, "source_line": line, "record_id": src["set_id"], "record_hash": src["record_hash"], "window": src["window"],
                "set_ticker": src["ticker"], "direction": src.get("direction", 1), "role": role, "name": name, "status_recorded": srec,
                "entry_session": (trec or {}).get("entry_session", ""), "target_session": tgt_b["date"] if tgt_b else "",
                "exit_recorded": (trec or {}).get("exit_session", ""), "exit_reason_recorded": (trec or {}).get("exit_reason", ""), "gross_recorded": (trec or {}).get("gross_return", ""), "net_recorded": (trec or {}).get("net_return", ""),
                "exit_B": (tb or {}).get("exit_session", ""), "exit_reason_B": (tb or {}).get("exit_reason", ""), "gross_B": (tb or {}).get("gross_return", ""), "net_B": (tb or {}).get("net_return", ""),
                "exit_C": (tc or {}).get("exit_session", "") if rc is not None else "PENDING", "exit_reason_C": (tc or {}).get("exit_reason", ""), "gross_C": (tc or {}).get("gross_return", ""), "net_C": (tc or {}).get("net_return", ""),
                "exit_changed_C_vs_B": changed_exit if rc is not None else "", "return_changed_C_vs_B": bool(tb and tc and abs(tb["net_return"] - tc["net_return"]) > TOL) if rc is not None else "",
                "net_change_C_minus_B": (tc["net_return"] - tb["net_return"]) if (tb and tc) else "",
                "target_prev_close": tgt_b["prev"] if tgt_b else "", "target_close": tgt_b["close"] if tgt_b else "", "target_change": gross_move if gross_move is not None else "",
                "target_arb_B": tgt_b["arb"] if tgt_b else "", "target_arb_C": tgt_c["arb"] if tgt_c else "", "target_locked_B": tgt_b["lock_down"] if tgt_b else "",
                "target_locked_C": tgt_c["lock_down"] if tgt_c else "", "target_one_price_bar": tgt_b["one_price"] if tgt_b else "",
                "rolled_sessions_B": db["rolled"] if db else "", "rolled_sessions_C": dc["rolled"] if dc else "",
                "locked_sessions_rolled_over_C": ";".join(c["date"] for c in (dc["path"][:-1] if dc else [])), "C_exit_session_cell_volume": (dc["exit"]["volume"] if dc else "")})

    # ------------------------------------------------------------------ catalyst register numbers
    cats_rec = [x for _, (x, _) in cat_pairs]
    gate_cat = [g for g in gate_rows if g["source_file"] == "catalysts.jsonl"]
    gate_spec = [g for g in gate_rows if g["source_file"] == "speculations.jsonl"]
    cat_B = [xb for _, (xb, _) in cat_pairs]
    cat_rows = [r for r in results_rows if r["source_file"] == "catalysts.jsonl"]
    tr_cat = [t for t in trade_rows if t["source_file"] == "catalysts.jsonl"]
    changed_trades = [t for t in tr_cat if t["exit_changed_C_vs_B"] is True]
    signed_v = {k: [signed(x["source"] if k == "rec" else (x["replay"] if k == "B" else pairs[(x["file"], x["line"])][1]["replay"])) for x in cat_B] for k in ("rec", "B", "C")}

    def meanshare(v):
        a = np.array(v, dtype=float)
        return {"n": int(len(a)), "mean": float(a.mean()), "share_positive": float((a > 0).mean()), "n_positive": int((a > 0).sum()), "sd": float(a.std(ddof=1)), "se": float(a.std(ddof=1) / math.sqrt(len(a)))}

    stat_sum = {k: meanshare(v) for k, v in signed_v.items()}
    flips = [r for r in cat_rows if r["flow_outcome_flipped_C_vs_B"] is True]
    cat_summary = {
        "rows": len(cat_rows), "windows": dict(Counter(r["window"] for r in cat_rows)), "signal_sessions": sorted({r["signal_session"] for r in cat_rows}),
        "trade_slots": len(tr_cat), "baseline_rows_reproduced_within_1e-12": sum(g["reproduced_within_1e-12"] for g in gate_cat),
        "baseline_rows_bit_identical": sum(1 for g in gate_cat if g["numeric_leaves_not_bit_identical"] == 0 and g["reproduced_within_1e-12"]),
        "baseline_max_abs_numeric_diff": max(g["max_abs_numeric_diff"] for g in gate_cat), "baseline_leaves_compared": sum(g["leaves_compared"] for g in gate_cat),
        "baseline_numeric_leaves": sum(g["numeric_leaves"] for g in gate_cat), "baseline_numeric_leaves_not_bit_identical": sum(g["numeric_leaves_not_bit_identical"] for g in gate_cat),
        "baseline_nonnumeric_mismatches": sum(g["nonnumeric_or_missing_mismatches"] for g in gate_cat),
        "baseline_differing_numeric_fields": sorted({f for g in gate_cat for f in g["differing_numeric_fields"].split(";") if f}),
        "rows_pending_under_C": sum(1 for r in cat_rows if str(r["status_C"]).startswith("PENDING")),
        "rows_changed_under_C": sum(1 for r in cat_rows if r["C_changes_row"]), "rows_unchanged_under_C": sum(1 for r in cat_rows if not r["C_changes_row"]),
        "trade_slots_exit_changed": len(changed_trades), "trade_slots_return_changed": sum(1 for t in changed_trades if t["return_changed_C_vs_B"] is True),
        "candidates_changed": sum(1 for t in changed_trades if t["role"] == "candidate"), "twin_slots_changed": sum(1 for t in changed_trades if t["role"] == "twin"),
        "distinct_names_changed": len({t["name"] for t in changed_trades}), "rolled_sessions_C_distribution": dict(sorted(Counter(int(t["rolled_sessions_C"]) for t in changed_trades).items())),
        "changed_row_tickers": [r["ticker"] for r in cat_rows if r["C_changes_row"]], "unchanged_row_tickers": [r["ticker"] for r in cat_rows if not r["C_changes_row"]],
        "flow_outcomes_flipped": [r["ticker"] for r in flips], "flow_outcome_flip_detail": [{"ticker": r["ticker"], "B": r["flow_outcome_B"], "C": r["flow_outcome_C"]} for r in flips],
        "signed_diff": stat_sum, "stats_recorded": R["B"]["stats_recorded"], "stats_B": R["B"]["stats_variant"], "stats_C": R["C"]["stats_variant"],
        "lines_published": R["B"]["published_lines"], "lines_recorded_rows": R["B"]["lines_recorded"], "lines_B": R["B"]["lines_variant"], "lines_C": R["C"]["lines_variant"],
        "published_calibration_rows": R["B"]["published_calibration_rows"], "chain_problems": R["B"]["chain_problems"],
        "changed_trades": [{k: t[k] for k in ("record_id", "role", "name", "exit_B", "exit_C", "net_B", "net_C", "target_change", "target_arb_B", "target_arb_C", "rolled_sessions_C", "locked_sessions_rolled_over_C")} for t in changed_trades],
        "lines_published_equal_recomputed_on_recorded_rows": R["B"]["published_lines"] == R["B"]["lines_recorded"] and R["B"]["published_calibration_rows"] == [l for l in R["B"]["lines_recorded"] if l.startswith("| IDX_INDEX |")],
        "lines_B_equal_recorded_lines": R["B"]["lines_variant"] == R["B"]["lines_recorded"]}
    # the 14 rows' own provenance
    orig_manifest_sha = pre["orig_manifest"]["sha256"]
    cat_summary["recorded_rows_written_on_manifest_sha256"] = sorted({x["source"]["data"]["manifest_sha256"] for x in cat_B})
    cat_summary["recorded_manifest_is_the_frozen_one"] = cat_summary["recorded_rows_written_on_manifest_sha256"] == [orig_manifest_sha]
    cat_summary["recorded_resolved_at_range"] = [min(x["source"]["resolved_at"] for x in cat_B), max(x["source"]["resolved_at"] for x in cat_B)]

    # ------------------------------------------------------------------ speculation cross-check numbers
    spec_rows = [r for r in results_rows if r["source_file"] == "speculations.jsonl"]
    spec_summary = {"rows": len(spec_rows), "by_window": dict(Counter(r["window"] for r in spec_rows)),
                    "B_reproduced_within_1e-12": sum(g["reproduced_within_1e-12"] for g in gate_spec), "B_not_reproduced": [(g["record_id"], g["window"], g["mismatching_paths"]) for g in gate_spec if not g["reproduced_within_1e-12"]],
                    "rows_changed_under_C": [(r["ticker"], r["window"], r["status_C"]) for r in spec_rows if r["C_changes_row"]],
                    "rows_pending_under_C": [(r["ticker"], r["window"], r["signal_session"]) for r in spec_rows if str(r["status_C"]).startswith("PENDING")]}
    # why ALKA BASE5 is pending under C: the twins locked on the last bar
    pend = [(x, pairs[(x["file"], x["line"])][1]) for x in R["B"]["replays"] if x["file"] == "speculations.jsonl" and pairs[(x["file"], x["line"])][1]["replay"] is None]
    spec_summary["pending_detail"] = []
    for xb, xc in pend:
        det = []
        for d in xb["diag"] or []:
            if d is None:
                continue
            t = d["target"]
            Pn = tickers.index(d["name"])
            kc = dates.index(t["date"])
            if bool(ld["C"][Pn, kc]) and kc == len(dates) - 1:
                det.append({"name": d["name"], "target_session": t["date"], "prev": t["prev"], "close": t["close"], "arb_C": float(P["C"]["arb"][Pn, kc]), "arb_B": float(P["B"]["arb"][Pn, kc])})
        spec_summary["pending_detail"].append({"record": xb["source"]["set_id"], "window": xb["source"]["window"], "locked_on_last_bar_under_C": det})

    # ------------------------------------------------------------------ the learner (second-order) replay
    cat_ledger, spc_ledger = load_jsonl(REPO_PAPER / "catalysts.jsonl"), load_jsonl(REPO_PAPER / "speculations.jsonl")
    mods_c_labels, mods_b, mods_alka = [], [], []
    for (file, line), (xb, xc) in pairs.items():
        src = xb["source"]
        sens = src["window"] in ("RUNUP", "BASE5", "POST20", "H20", "H60")  # windows whose statements the learner grades from plan trades
        if not sens:
            continue
        content_keys = ("candidate", "twins", "paired", "cone", "status")
        if xb["replay"] is not None:
            mods_b.append({"file": file, "line": line, "record_hash": src["record_hash"], "content": {k: xb["replay"][k] for k in content_keys}})
        changed = (xc["replay"] is None) or bool(xb["c_vs_b"]["mismatch"] or xb["c_vs_b"]["missing"])
        if not changed:
            continue
        if xc["replay"] is None:
            mods_alka.append({"file": file, "line": line, "record_hash": src["record_hash"], "pending": True})
        else:
            mods_c_labels.append({"file": file, "line": line, "record_hash": src["record_hash"], "content": {k: xc["replay"][k] for k in content_keys}, "last_exit_day": lastexit(xc["replay"])})
    worlds = [
        {"name": "W0_recorded_ledgers", "mods": []},
        {"name": "WB_B_replayed_labels", "mods": mods_b},
        {"name": "C_labels_only", "mods": [{k: v for k, v in m.items() if k != "last_exit_day"} for m in mods_c_labels]},
        {"name": "C_alka_pending_only", "mods": mods_alka},
        {"name": "C_all_recorded_timing", "mods": [{k: v for k, v in m.items() if k != "last_exit_day"} for m in mods_c_labels] + mods_alka},
        {"name": "C_all_c_world_timing", "mods": [{**m, "availability": "last_exit_day"} for m in mods_c_labels] + mods_alka},
    ]
    (WORK / "learner_worlds.json").write_text(json.dumps({"worlds": worlds}, default=_np_default), encoding="utf-8")
    print("== learner replay (second-order)")
    run_worker("learner", str(WORK / "learner_worlds.json"), roots["B"])
    LR = json.loads((OUTD / "learner_results.json").read_text(encoding="utf-8"))

    def lsum(name, market=None):
        recs = [r for r in LR["worlds"][name] if market is None or r["market"] == market]
        return {"records": len(recs), "records_beyond_tolerance": sum(1 for r in recs if r["fields_differing"]), "records_raw_changed": sum(1 for r in recs if r["n_raw_changed"]),
                "records_published_changed": sum(1 for r in recs if r["n_published_changed"]), "records_call_changed": sum(1 for r in recs if r["call_changes"]),
                "max_abs_raw": max((r["max_abs_raw"] for r in recs), default=0.0), "max_abs_published": max((r["max_abs_published"] for r in recs), default=0.0),
                "max_abs_anchor": max((r["max_abs_anchor"] for r in recs), default=0.0),
                "median_abs_raw_over_changed": float(np.median([r["max_abs_raw"] for r in recs if r["n_raw_changed"]])) if any(r["n_raw_changed"] for r in recs) else 0.0}

    lw = {name: {"all": lsum(name), "IDX": lsum(name, "IDX"), "US": lsum(name, "US"), "CRYPTO": lsum(name, "CRYPTO")} for name in LR["worlds"]}
    learner_summary = {"worlds": lw, "n_records": len(LR["worlds"]["W0_recorded_ledgers"]), "tolerance": LR["verify_tol"],
                       "idx_records_exposed_to_runup_labels": sum(1 for r in LR["worlds"]["W0_recorded_ledgers"] if r["market"] == "IDX" and "IDX_INDEX:WITH_FLOW_RUNUP" in r["live_rows_recorded"]),
                       "idx_published_changes_detail": [{"made_at": r["made_at"], "ticker": r["ticker"], "changes": r["published_changes"]} for r in LR["worlds"]["C_all_recorded_timing"] if r["market"] == "IDX" and r["published_changes"]],
                       "mods": {"C_labels_changed_rows": [(m["file"], m["line"], m["last_exit_day"]) for m in mods_c_labels], "alka_pending": [(m["file"], m["line"]) for m in mods_alka]}}
    # learner rows into results.csv
    lA, lB_ = {r["record_hash"]: r for r in LR["worlds"]["C_all_recorded_timing"]}, {r["record_hash"]: r for r in LR["worlds"]["C_all_c_world_timing"]}
    lB0 = {r["record_hash"]: r for r in LR["worlds"]["WB_B_replayed_labels"]}
    l2_lines = load_jsonl(REPO_PAPER / "learner_v2.jsonl")
    learner_rows = []
    for n, f in enumerate(l2_lines, 1):
        a, b, b0 = lA[f["record_hash"]], lB_[f["record_hash"]], lB0[f["record_hash"]]
        learner_rows.append({"scope": "learner_v2 (second-order: trains on graded statements)", "source_file": "learner_v2.jsonl", "source_line": n, "record_type": "LEARNER2_FORECAST", "record_id": f["set_id"],
                             "record_hash": f["record_hash"], "family": f["family"], "market": f["market"], "ticker": f["ticker"], "signal_session": f["signal_session"], "made_at": f["made_at"],
                             "B_reproduces_recorded": not b0["fields_differing"], "B_max_abs_numeric_diff": b0["max_abs_raw"],
                             "lrn_A_n_raw_changed": a["n_raw_changed"], "lrn_A_max_abs_raw": a["max_abs_raw"], "lrn_A_n_published_changed": a["n_published_changed"], "lrn_A_max_abs_published": a["max_abs_published"], "lrn_A_call_changes": a["call_changes"],
                             "lrn_B_n_raw_changed": b["n_raw_changed"], "lrn_B_max_abs_raw": b["max_abs_raw"], "lrn_B_n_published_changed": b["n_published_changed"], "lrn_B_max_abs_published": b["max_abs_published"], "lrn_B_call_changes": b["call_changes"],
                             "C_changes_row": bool(a["n_raw_changed"] or a["n_published_changed"] or a["call_changes"] or b["n_raw_changed"] or b["n_published_changed"] or b["call_changes"])})
    # ------------------------------------------------------------------ files
    cols = ["scope", "source_file", "source_line", "record_type", "record_id", "record_hash", "family", "market", "ticker", "window", "signal_session", "made_at", "direction",
            "status_recorded", "status_B", "status_C", "B_reproduces_recorded", "B_max_abs_numeric_diff", "C_changes_row", "C_leaves_changed_vs_B", "n_trades",
            "n_trades_exit_changed_C_vs_B", "n_trades_return_changed_C_vs_B", "trades_changed_C_vs_B", "C_last_exit_session",
            "cand_exit_recorded", "cand_exit_B", "cand_exit_C", "cand_net_recorded", "cand_net_B", "cand_net_C",
            "paired_diff_recorded", "paired_diff_B", "paired_diff_C", "signed_diff_recorded", "signed_diff_B", "signed_diff_C",
            "flow_outcome_recorded", "flow_outcome_B", "flow_outcome_C", "flow_outcome_flipped_C_vs_B",
            "lrn_A_n_raw_changed", "lrn_A_max_abs_raw", "lrn_A_n_published_changed", "lrn_A_max_abs_published", "lrn_A_call_changes",
            "lrn_B_n_raw_changed", "lrn_B_max_abs_raw", "lrn_B_n_published_changed", "lrn_B_max_abs_published", "lrn_B_call_changes"]
    write_csv(HERE / "results.csv", cat_rows + spec_rows + learner_rows, cols)
    tcols = ["scope", "source_file", "source_line", "record_id", "record_hash", "window", "set_ticker", "direction", "role", "name", "status_recorded", "entry_session", "target_session",
             "exit_recorded", "exit_reason_recorded", "gross_recorded", "net_recorded", "exit_B", "exit_reason_B", "gross_B", "net_B", "exit_C", "exit_reason_C", "gross_C", "net_C",
             "exit_changed_C_vs_B", "return_changed_C_vs_B", "net_change_C_minus_B", "target_prev_close", "target_close", "target_change", "target_arb_B", "target_arb_C", "target_locked_B",
             "target_locked_C", "target_one_price_bar", "rolled_sessions_B", "rolled_sessions_C", "locked_sessions_rolled_over_C", "C_exit_session_cell_volume"]
    write_csv(HERE / "trades.csv", trade_rows, tcols)
    write_csv(HERE / "baseline_gate.csv", gate_rows, ["scope", "source_file", "source_line", "record_id", "window", "record_hash", "replay_status_B", "leaves_compared", "numeric_leaves", "numeric_leaves_not_bit_identical",
                                                      "max_abs_numeric_diff", "numeric_leaves_over_1e-12", "nonnumeric_or_missing_mismatches", "reproduced_within_1e-12", "differing_numeric_fields", "mismatching_paths"])
    lcols = ["world", "record_hash", "set_id", "family", "market", "ticker", "signal_session", "made_at", "n_statements", "n_raw_changed", "n_published_changed", "max_abs_raw", "max_abs_published", "max_abs_anchor", "max_abs_deviation", "call_changes", "fields_differing"]
    lrows = []
    for name, recs in LR["worlds"].items():
        for r in recs:
            lrows.append({"world": name, **{k: r[k] for k in lcols[1:-1]}, "fields_differing": ";".join(r["fields_differing"])})
    write_csv(HERE / "learner_changes.csv", lrows, lcols)

    # ------------------------------------------------------------------ clean-tree check
    clean = {}
    if not args.no_clean_check:
        after = {"code_B": tree_snapshot(CODE["B"]), "code_C": tree_snapshot(CODE["C"]), "repo_paper": tree_snapshot(REPO_PAPER, sha=True, skip_dirs=("timestamps", "scans", "raw")),
                 "repo_research": tree_snapshot(REPO_RESEARCH, sha=False), "frozen_top": {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in FROZEN.iterdir() if p.is_file()}}
        clean = {k: snaps_before[k] == after[k] for k in snaps_before}
        clean["pycache_dirs_in_code_B"] = sorted(str(p) for p in (CODE["B"] / "idxsig").rglob("__pycache__"))
        assert all(v for k, v in clean.items() if isinstance(v, bool)), f"a protected tree changed: {clean}"

    summary = {"preflight": pre, "panel": panel_sum, "catalyst_register": cat_summary, "speculation_crosscheck": spec_summary, "learner_v2": learner_summary,
               "census": census, "census_callers_files": per_file, "tree_unchanged": clean, "cutoff": CUTOFF,
               "versions": R["B"]["versions"], "data_B": R["B"]["data"], "data_C": R["C"]["data"], "replay_seconds": {v: R[v]["elapsed_s"] for v in "BC"}}
    (HERE / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=_np_default, allow_nan=False) + "\n", encoding="utf-8")
    (HERE / "report.md").write_text(render_report(summary, cat_rows, tr_cat, spec_rows, census), encoding="utf-8")
    if not args.keep_work:
        shutil.rmtree(WORK)
    print(f"== done in {time.time() - T0:.0f}s")
    print(json.dumps({"catalyst_rows": cat_summary["rows"], "rows_changed_C": cat_summary["rows_changed_under_C"], "trade_slots_exit_changed": cat_summary["trade_slots_exit_changed"],
                      "signed_diff_B": cat_summary["signed_diff"]["B"]["mean"], "signed_diff_C": cat_summary["signed_diff"]["C"]["mean"],
                      "share_B": cat_summary["signed_diff"]["B"]["share_positive"], "share_C": cat_summary["signed_diff"]["C"]["share_positive"]}, indent=1))


# ============================================================================================================ report
def render_report(S: dict, cat_rows: list, tr_cat: list, spec_rows: list, census: list) -> str:
    C = S["catalyst_register"]
    sd = C["signed_diff"]
    L = S["learner_v2"]
    P = S["panel"]
    SP = S["speculation_crosscheck"]
    lines = []
    A = lines.append
    A("# IDX lower-limit correction: effect on the Catalyst Register and the other record families (addendum)")
    A("")
    A("Paper trading only, no real money. Everything below is a *final-bar replay*: the real functions of the shipped code (B) and the corrected code (C) run on the only surviving raw pull "
      f"(`{S['preflight']['manifest']['file']}`, sha256 `{S['preflight']['manifest']['sha256'][:12]}`, {S['preflight']['manifest']['n_tickers']} tickers, last bar {S['data_B']['last_session']}). "
      "Nothing was edited: no ledger, no register, no code dir.")
    A("")
    A("## The numbers")
    A("")
    A(f"- **Catalyst register: {C['rows']} IDX RESOLUTION rows**, all `IDX_INDEX` window `RUNUP` (signal 2026-10-28, buy the 2026-10-29 close, sell the 2026-10-30 close, one session). "
      f"{C['trade_slots']} trades (14 candidates, {C['trade_slots'] - 14} twins), every sale on 2026-10-30, after both October rule changes.")
    A(f"- **Baseline gate passed.** The B replay reproduces {C['baseline_rows_reproduced_within_1e-12']} of {C['rows']} recorded rows. {C['baseline_leaves_compared']} leaves compared per variant; every string, date, status, boolean and count identical; "
      f"{C['baseline_numeric_leaves'] - C['baseline_numeric_leaves_not_bit_identical']} of {C['baseline_numeric_leaves']} numeric leaves bit-identical, the rest differ by at most {C['baseline_max_abs_numeric_diff']:.1e} "
      "(floating-point noise, diagnosed below).")
    A(f"- **Under the corrected rules (C), {C['rows_changed_under_C']} of {C['rows']} rows change** ({', '.join(C['changed_row_tickers'])}); {C['rows_unchanged_under_C']} do not ({', '.join(C['unchanged_row_tickers'])}). "
      f"{C['trade_slots_exit_changed']} of {C['trade_slots']} trades change their exit ({C['candidates_changed']} candidates, {C['twin_slots_changed']} twin slots; {C['distinct_names_changed']} distinct names), "
      f"{C['trade_slots_return_changed']} of them change their return. Each one was closing 6.7% to 7.0% below the previous close on 2026-10-30, which the old 15% rule let sell and the 7% rule locks, so the sale rolls to the next sellable session "
      f"({', '.join(f'{k} session{'s' if int(k) > 1 else ''}: {v} trades' for k, v in C['rolled_sessions_C_distribution'].items())}).")
    A(f"- **The published line moves.** `paper/CATALYSTS.md` says: *RUNUP: paired 14, mean signed diff +1.16%, share with the flow 64%*. "
      f"Recomputed with the register's own `statistics()`/`render()`: recorded rows {pct(sd['rec']['mean'])} and {sd['rec']['share_positive']:.0%}; B replay {pct(sd['B']['mean'])} and {sd['B']['share_positive']:.0%} (identical); "
      f"**C replay {pct(sd['C']['mean'])} and {sd['C']['share_positive']:.0%}** ({sd['C']['n_positive']} of 14, was {sd['B']['n_positive']} of 14). "
      f"One graded statement flips: {', '.join(C['flow_outcomes_flipped'])} `WITH_FLOW_RUNUP` goes {C['flow_outcome_flip_detail'][0]['B']} to {C['flow_outcome_flip_detail'][0]['C']}, so the calibration row's realised rate moves from "
      f"{C['stats_B']['calibration']['WITH_FLOW_RUNUP']['realised_rate']:.2f} to {C['stats_C']['calibration']['WITH_FLOW_RUNUP']['realised_rate']:.2f}; the Brier terms stay {C['stats_C']['calibration']['WITH_FLOW_RUNUP']['brier']:.3f} (prior 0.5).")
    A(f"- **Only one other family has IDX values that depend on the lock and was not covered: `learner_v2.jsonl`** ({L['worlds']['W0_recorded_ledgers']['IDX']['records']} IDX rows), and only through its training labels. Replayed with the learner's own code, "
      f"the flipped label shifts the raw forecast probabilities of {L['worlds']['C_labels_only']['all']['records_raw_changed']} of {L['n_records']} forecast records (all families, {L['worlds']['C_labels_only']['IDX']['records_raw_changed']} of the {L['worlds']['C_labels_only']['IDX']['records']} IDX records) "
      f"by at most {L['worlds']['C_labels_only']['all']['max_abs_raw']:.4f}; published probabilities and calls do not change. A separate effect: the ALKA BASE5 speculation row cannot be resolved under C on the last bar (two twins are locked on 2026-11-06), "
      f"which moves {L['worlds']['C_alka_pending_only']['IDX']['records_published_changed']} IDX forecasts' published `RUN30_5`/`PUMP30_5` probability by {L['worlds']['C_alka_pending_only']['IDX']['max_abs_published']:.4f}.")
    A("- Every other family under `paper/` has no IDX row that depends on the lock (table below). Scans, decisions, sets, tags and the US, crypto and book/account ledgers are independent of `lock_down`.")
    A("")
    A("## Catalyst register, row by row")
    A("")
    A("Signed difference = (candidate net minus twins' mean net) x direction; `with flow` = signed difference above zero (`WITH_FLOW_RUNUP`). Source = line in `paper/catalysts.jsonl`, record hash prefix. Net returns after the paper fees.")
    A("")
    A("| Line | Set (ticker) | Record hash | Dir | Candidate net B | Candidate net C | Candidate exit C | Signed diff B | Signed diff C | with flow B | with flow C | Trades changed in C |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in cat_rows:
        A(f"| {r['source_line']} | {r['ticker']} | `{r['record_hash'][:12]}` | {r['direction']:+d} | {pct(r['cand_net_B'])} | {pct(r['cand_net_C'])} | {r['cand_exit_C']} | {pct(r['signed_diff_B'])} | {pct(r['signed_diff_C'])} | "
          f"{'yes' if r['flow_outcome_B'] else 'no'} | {'yes' if r['flow_outcome_C'] else 'no'} | {r['n_trades_exit_changed_C_vs_B']} of {r['n_trades']}{(' (' + r['trades_changed_C_vs_B'].replace('candidate:', 'cand ').replace('twin:', '') + ')') if r['trades_changed_C_vs_B'] else ''} |")
    A("")
    A("Trades whose exit changes (all sold on 2026-10-30 under B; the target session is 2026-10-30 for every trade):")
    A("")
    A("| Set | Role | Name | Move on 2026-10-30 | ARB B | ARB C | Close | Exit B / net B | Exit C / net C | Rolled |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for t in S["catalyst_register"]["changed_trades"]:
        tt = next(x for x in tr_cat if x["record_id"] == t["record_id"] and x["name"] == t["name"] and x["role"] == t["role"])
        A(f"| {t['record_id'].split('-')[-1]} | {t['role']} | {t['name']} | {pct(t['target_change'])} | {tt['target_arb_B']:g} | {tt['target_arb_C']:g} | {tt['target_close']:g} | {t['exit_B']} / {pct(t['net_B'])} | {t['exit_C']} / {pct(t['net_C'])} | {t['rolled_sessions_C']} |")
    A("")
    A("## Mechanism")
    A("")
    A(f"`catalysts.resolve_set` runs `speculation.simulate` for the candidate and each twin. `simulate` sells at the first session at or after the target where `tradeable and not lock_down`. `lock_down` (built in `Market.build`) is: the bar traded, the close is below the reference and at or below the day's ARB. "
      f"B keeps the 15% ARB from 2026-09-28; C applies 7% from 2026-10-19 (and a nominal Rp1 ARB for references Rp11 to 14 from 2026-10-20). ARA (and so `lock_up`) is identical in B and C ({P['lock_up_cells_differing']} cells differ), and the two markets differ only on lower-limit cells on or after 2026-10-19: "
      f"{P['cells_locked_only_under_C']} cells of {P['cells']} are locked under C but not B, {P['cells_locked_only_under_B']} the other way, {P['changed_cells_before_cutoff']} before 2026-10-19; {P['changed_cells_with_reference_at_most_14']} of them have a reference at or below Rp14 (the Rp11-14 rule), "
      "the rest are the 7% rule. See `lock_cells_changed.csv`. The 14 rows were resolved on 2026-10-30 at 10:59 UTC, when the sale on that day was not locked under B; under C nine of the sets could not have resolved that day and would have waited for the roll.")
    A("")
    A("## Baseline gate, diagnosis of the tiny differences")
    A("")
    A(f"The 14 rows were written on the 2026-10-30 pull (manifest sha256 `{C['recorded_rows_written_on_manifest_sha256'][0][:12]}`, which is the manifest file kept in the frozen inputs; its raw payloads were not kept). "
      f"The replay uses the 2026-11-06 pull, whose 200-day window starts later ({S['preflight']['final_manifest_first_date_sample']} against {S['preflight']['orig_manifest']['first_date_sample']}). "
      "The reference chain `level` is a cumulative sum of log returns from the first bar of the window, so `level[exit]/level[entry]` differs in the last bits. "
      f"The numeric leaves that are not bit-identical are exactly: {', '.join('`' + f + '`' for f in C['baseline_differing_numeric_fields'])}; the largest difference is {C['baseline_max_abs_numeric_diff']:.1e}. "
      "Entry prices, sessions, exit reasons, costs, statuses, units, cone outcomes and Brier terms are identical.")
    A("")
    A("## Other record families")
    A("")
    A("Counted from the committed snapshot (`market` absent = IDX in the ledger). `touching` = a session field (signal, entry, exit, scan) on or after 2026-10-19; `exit on/after` = a trade sold on or after that date (the only place the lock can enter).")
    A("")
    A("| File | Record family | IDX rows | Touching | Exit on/after | Depends on the lock | Path | Replayable |")
    A("|---|---|---|---|---|---|---|---|")
    for r in census:
        if r["idx_rows"] == "":
            continue
        A(f"| `{r['file']}` | {r['record_family']} | {r['idx_rows']} | {r['idx_rows_touching_on_or_after_cutoff']} | {r['idx_rows_whose_exit_is_on_or_after_cutoff']} | {r['depends_on_lock']} ({r['dependence']}) | {r['code_path']} | {r['replayable_from_final_pull']} |")
    A("")
    A("Derived reports (`CATALYSTS.md`, `SPECULATIONS.md`, `LEARNER_V2.md` and the other `.md` files) are rendered from the ledgers and carry the same numbers; only `CATALYSTS.md`'s IDX_INDEX section changes through this addendum's rows.")
    A("")
    A("## Second-order: learner_v2")
    A("")
    A("`learner_v2.jsonl` trains on every graded statement of the registers that resolved before each forecast. The `IDX_INDEX WITH_FLOW_RUNUP` labels (14 of them) feed the slope shared by all relative statements (`BEATS_TWINS_k` and so on, every family and market); the `SPEC_IDX` BASE5 labels feed the Speculation Register anchors. "
      "Each forecast record carries the ledger state it was computed from, so the learner's own `_record()` can be re-run per record with changed labels (first-order: each record's earlier learner records stay as recorded).")
    A("")
    A("| World | Records changed in raw forecasts (all / IDX) | Published changed (all / IDX) | Calls changed | Max raw change | Max published change |")
    A("|---|---|---|---|---|---|")
    names = {"W0_recorded_ledgers": "recorded ledgers (baseline: must reproduce)", "WB_B_replayed_labels": "B-replayed labels (baseline: must reproduce)", "C_labels_only": "C labels at the recorded timestamps",
             "C_alka_pending_only": "ALKA BASE5 row absent (pending under C)", "C_all_recorded_timing": "both, recorded timestamps", "C_all_c_world_timing": "both, labels available only after their roll completes"}
    for k, nm in names.items():
        w = L["worlds"][k]
        A(f"| {nm} | {w['all']['records_raw_changed']} / {w['IDX']['records_raw_changed']} | {w['all']['records_published_changed']} / {w['IDX']['records_published_changed']} | {w['all']['records_call_changed']} | {w['all']['max_abs_raw']:.5f} | {w['all']['max_abs_published']:.5f} |")
    A("")
    A(f"Changed means beyond the learner's own verification tolerance ({L['tolerance']:g}). The first two rows are the baseline gate for this family: every one of the {L['n_records']} recorded forecasts is reproduced from the recorded ledgers and from the B-replayed labels.")
    A("")
    A("## Cross-check of the earlier work: the 23 IDX speculation rows")
    A("")
    A(f"Replayed with `speculation.resolve_set` ({', '.join(f'{k} {v}' for k, v in SP['by_window'].items())}). B reproduces {SP['B_reproduced_within_1e-12']} of {SP['rows']}; "
      f"{'; '.join(f'{a} {b} differs in {c[:80]}' for a, b, c in SP['B_not_reproduced']) or 'none differ'}. Under C: {'; '.join(f'{a} {b} is {c}' for a, b, c in SP['rows_changed_under_C']) or 'no row changes'}.")
    for d in SP["pending_detail"]:
        A(f"The pending row `{d['record']}`: " + "; ".join(f"{x['name']} closes {x['close']:g} on {x['target_session']} from {x['prev']:g}, ARB {x['arb_B']:g} under B and {x['arb_C']:g} under C" for x in d["locked_on_last_bar_under_C"]) + ".")
    A("")
    A("## Caveats and unresolved")
    A("")
    for c in CAVEATS(S):
        A(f"- {c}")
    A("")
    A("## Files")
    A("")
    A("`harness.py` (one command), `results.csv` (one row per replayed record: 14 catalyst, 23 speculation, 238 learner), `trades.csv` (one row per replayed trade), `baseline_gate.csv`, `family_census.csv`, `lock_cells_changed.csv`, `learner_changes.csv`, `code_callers.txt`, `summary.json`.")
    return "\n".join(lines) + "\n"


def CAVEATS(S: dict) -> list[str]:
    C, L, SP = S["catalyst_register"], S["learner_v2"], S["speculation_crosscheck"]
    out = [
        "**Final-bar replay, not a re-run of 2026-10-30.** Only the 2026-11-06 raw pull survives; the rows were written on the 2026-10-30 pull. A rolled sale is resolved with the bars up to 2026-11-06. Under C the nine changed sets could not have been written on 2026-10-30 (their sales roll), so the register would have written them on 2026-11-02 or 2026-11-04; the learner results below treat that explicitly in the last world.",
        "**The rule schedule is the one in market.py (C), unverified by me.** I did not check the 7% from 2026-10-19 or the Rp1 ARB against decree texts; the module itself says the decrees were not read and that on 2026-10-19 the real limit for references Rp11-14 is unknown (nothing here depends on that day). The names that change here all closed 6.7% to 7.0% below the previous close, so the result depends on the 7% rule being right on 2026-10-30 and is sensitive to tick rounding of the limit price.",
        "**Board membership is not in the data.** `limits()` models the regular boards for every name; a name on a 10% board is over-locked by a 7% fall under C. I did not test which of the 15 names change because of that.",
        "**The register is append-only.** I changed no row. A correction would be new RESOLUTION rows whose `revises` names the earlier hash; whether to append them (and a corrected CATALYSTS.md line) is the owner's decision. The published line and calibration row would read as in the C column above.",
        "**Descriptive only.** The register labels IDX_INDEX 'never tested'; the shift in the mean signed difference is "
        f"{(C['signed_diff']['C']['mean'] - C['signed_diff']['B']['mean']) * 100:.2f} percentage points against a standard error of {C['signed_diff']['B']['se'] * 100:.2f}, with 14 sets from one index review and one signal session.",
        "**Learner replay is first-order.** Each forecast is recomputed from its own recorded ledger prefix and the recorded earlier learner records; compounding through later forecasts' gates is not followed. The timing treatment for C-world availability (a changed row becomes available to the first learner batch on the calendar day of its last roll session, minus one second) is my assumption.",
        "**Learner 'changed' is measured against the learner's own verification tolerance (2e-6);** the raw-probability shifts are small but would make `paper-verify` fail for those records if the labels were corrected in place, because verify retrains from the registers.",
        "**The Speculation Register cross-check is not the earlier analyst's number.** "
        + (f"B reproduces {SP['B_reproduced_within_1e-12']} of {SP['rows']} rows; the {len(SP['B_not_reproduced'])} that differ ({', '.join(f'{a} {b}' for a, b, _ in SP['B_not_reproduced'])}) differ in data, not in the lock: the recorded row left statements ungraded that the final pull grades, consistent with a bar present in the final pull and missing on the 2026-11-05 pull (the raw 2026-11-05 payload did not survive, so I cannot confirm it)." if SP["B_not_reproduced"] else "B reproduces all rows."),
        "**Decision text and sizing are stale after 2026-10-19 but do not read market.py.** DECISION rows size against the hard-coded `Policy.max_stop_distance` 0.15 and say 'locked at ARB, 15% below the entry'. The correction cannot change them; PAPER-POLICY-v4 would need a new version.",
        "**POST20 windows of the same 14 sets are not resolvable yet** (signal 2026-10-28 plus 22 sessions, 2026-11-27 at the earliest), so they will be the first rows to be written under whichever rules are in force.",
        "**Outside `paper/`:** `research/LLM_ARM_v1/calls*.jsonl` (5 IDX calls) hold forecasts only and persist no outcome; `llm_arm.workbench.resolve` imports BASE5 outcomes from the Speculation Register at scoring time, so it inherits that register's numbers. `research/GUIDANCE_REVISION_v1/paper/ledger.jsonl` is US. Backtest results under `results/` use 2023 windows and cannot touch sessions on or after 2026-10-19. Not examined in depth.",
        "**The ledger OUTCOME rows were not replayed here** (the earlier work covers them); the census only counts how many touch sessions on or after 2026-10-19.",
        "**Environment:** " + f"python {S['versions']['python']}, numpy {S['versions']['numpy']}, pandas {S['versions']['pandas']}; the replay is deterministic and was run twice (see the end of this report's source run).",
    ]
    return out


if __name__ == "__main__":
    main()

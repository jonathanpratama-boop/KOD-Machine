#!/usr/bin/env python3
"""LLM_ARM_v1 addendum 2: the LLM's vetoes on KOD's BUY_OK names. Read-only; descriptive.

Usage (from idx-signals/): python3 research/LLM_ARM_v1/veto_read.py [--root DIR] [--out OUT.json]
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIRST, LAST = "2026-11-05", "2026-11-12"
SEED, RESAMPLES, BAR = 20261113, 10_000, 0.05


def rows(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    return (statistics.fmean(a) - statistics.fmean(b)) / math.sqrt(va + vb) if va + vb > 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=HERE.parents[1])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    root = a.root.resolve()
    calls = [r for f in sorted(glob.glob(str(root / "research/LLM_ARM_v1/calls*.jsonl"))) for r in rows(f)]
    book = {r["set_id"]: r["verdict"] for r in rows(root / "paper/paper_book.jsonl") if r.get("type") == "BOOK_PLAN"}
    reg = rows(root / "paper/speculations.jsonl")
    base5 = defaultdict(list)
    for r in reg:
        if r.get("type") == "RESOLUTION" and r.get("window") == "BASE5":
            base5[r["set_id"]].append(r)
    pop = [c for c in calls if book.get(c["set"]) == "BUY_OK" and FIRST <= c["signal_session"] <= LAST]
    status, data = Counter(), []
    for c in pop:
        res = base5.get(c["set"], [])
        if not res:
            status["open"] += 1
            continue
        r = res[0]
        cand = r.get("candidate", {})
        if r.get("status") != "RESOLVED":
            status["unresolvable"] += 1
        elif cand.get("status") != "TRADED":
            status["not_traded"] += 1
        else:
            status["traded"] += 1
            group = "VETO" if c["call"] == "AVOID" else "KEEP"
            data.append((group, c["signal_session"], cand["trade"]["net_return"]))
    keep = [x for g, _, x in data if g == "KEEP"]
    veto = [x for g, _, x in data if g == "VETO"]
    allx = [x for _, _, x in data]
    by = defaultdict(list)
    for g, s, x in data:
        by[s].append((g, x))
    sessions = sorted(by)
    rng, diffs = random.Random(SEED), []
    for _ in range(RESAMPLES):
        pick = [by[sessions[rng.randrange(len(sessions))]] for _ in sessions] if sessions else []
        k = [x for grp in pick for g, x in grp if g == "KEEP"]
        v = [x for grp in pick for g, x in grp if g == "VETO"]
        if k and v:
            diffs.append(statistics.fmean(k) - statistics.fmean(v))
    gap = statistics.fmean(keep) - statistics.fmean(veto) if keep and veto else None
    p = sum(d <= 0 for d in diffs) / len(diffs) if diffs else None
    done = status["open"] == 0
    out = {
        "schema": "LLM_ARM_V1_VETO_READ_V1",
        "population": len(pop),
        "calls_in_population": dict(Counter(c["call"] for c in pop)),
        "status": dict(status),
        "complete": done,
        "kod_book_all_buy_ok": {"n": len(allx), "mean_net": statistics.fmean(allx) if allx else None},
        "keep_llm_filtered": {"n": len(keep), "mean_net": statistics.fmean(keep) if keep else None},
        "veto": {"n": len(veto), "mean_net": statistics.fmean(veto) if veto else None},
        "keep_minus_veto": gap,
        "p_one_sided_session_bootstrap": p,
        "welch_t": welch(keep, veto),
        "earns_prospective_test": bool(gap is not None and gap >= BAR and p is not None and p <= 0.05),
        "note": "descriptive read (addendum 2); final only when complete, or on 2026-11-27",
    }
    text = json.dumps(out, indent=1)
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

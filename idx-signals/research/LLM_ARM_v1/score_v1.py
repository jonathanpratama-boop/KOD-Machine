#!/usr/bin/env python3
"""LLM_ARM_v1 scoring, as PROTOCOL.md and ADDENDUM_1_SCORING.md define it. Read-only.

Usage (from idx-signals/):
    python3 research/LLM_ARM_v1/score_v1.py [--root DIR] [--out OUT.json]

DIR is the idx-signals directory whose ledgers are read (default: this repository's). Nothing is written except OUT.
The scored set is exactly what KOD's readiness audit (idxsig/llm_arm/audit.py) classes complete_BASE5_outcomes.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATEMENTS = ("RUN30_5", "FADE10_5", "BEATS_TWINS_5")
FIRST_LOOK = 60
SEED = 20261113
RESAMPLES = 10_000


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def t_one_sided_p(d):
    """One-sided p for mean(d) < 0, Student t with n-1 df (regularized incomplete beta, no SciPy)."""
    n = len(d)
    if n < 2:
        return None, None
    m, s = statistics.fmean(d), statistics.stdev(d)
    if s == 0:
        return (float("-inf") if m < 0 else float("inf")), (0.0 if m < 0 else 1.0)
    t = m / (s / math.sqrt(n))
    df = n - 1
    x = df / (df + t * t)
    tail = 0.5 * _betainc(df / 2, 0.5, x)  # P(T > |t|)
    return t, (tail if t < 0 else 1 - tail)


def _betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbeta) * _cf(a, b, x) / a
    return 1 - math.exp(lbeta) * _cf(b, a, 1 - x) / b


def _cf(a, b, x, eps=1e-14, iters=500):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, iters + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        delta = d * c
        h *= delta
        if abs(delta - 1) < eps:
            break
    return h


def cluster_upper95(d, clusters):
    """95% one-sided upper bound of mean(d), resampling whole clusters."""
    by = defaultdict(list)
    for v, c in zip(d, clusters):
        by[c].append(v)
    keys = sorted(by)
    rng = random.Random(SEED)
    means = []
    for _ in range(RESAMPLES):
        pick = [by[keys[rng.randrange(len(keys))]] for _ in keys]
        flat = [v for g in pick for v in g]
        means.append(statistics.fmean(flat))
    means.sort()
    return means[int(0.95 * RESAMPLES) - 1], len(keys)


def compare(llm, comp, clusters):
    d = [a - b for a, b in zip(llm, comp)]
    if not d:
        return {"n": 0}
    t, p = t_one_sided_p(d)
    up, k = cluster_upper95(d, clusters) if len(d) >= 2 else (None, None)
    gate = bool(d and statistics.fmean(d) < 0 and p is not None and p <= 0.05)
    robust = up is not None and up < 0
    return {
        "n": len(d),
        "mean_brier_llm": round(statistics.fmean(llm), 5),
        "mean_brier_comparator": round(statistics.fmean(comp), 5),
        "mean_difference": round(statistics.fmean(d), 5),
        "t": None if t is None else round(t, 3),
        "p_one_sided": None if p is None else round(p, 4),
        "beats_paired_one_sided_95": gate,
        "session_bootstrap_upper95": None if up is None else round(up, 5),
        "sessions": k,
        "robust_to_session_clustering": (gate == robust) if gate else None,
    }


def mean_or_none(xs):
    return None if not xs else round(statistics.fmean(xs), 5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=HERE.parents[1])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    root = a.root.resolve()
    sys.path.insert(0, str(root))
    from idxsig.llm_arm.audit import audit, load_jsonl  # KOD's own readiness rule decides what is scored

    call_files = sorted(glob.glob(str(root / "research/LLM_ARM_v1/calls*.jsonl")))
    reg_path, learner_path, book_path = (
        root / "paper/speculations.jsonl",
        root / "paper/learner_v2.jsonl",
        root / "paper/paper_book.jsonl",
    )
    calls = [r for f in call_files for r in load_jsonl(f)]
    register = load_jsonl(reg_path)
    readiness = audit(calls, register)
    sets = {r["set_id"]: r for r in register if r.get("type") == "SPECULATION_SET"}
    base5 = defaultdict(list)
    for r in register:
        if r.get("type") == "RESOLUTION" and r.get("window") == "BASE5":
            base5[r["set_id"]].append(r)
    learner = defaultdict(list)
    for r in rows(learner_path):
        if r.get("type") == "LEARNER2_FORECAST":
            learner[r["set_id"]].append(r)
    book = {r["set_id"]: r["verdict"] for r in rows(book_path) if r.get("type") == "BOOK_PLAN"}

    status = Counter()
    scored = []
    for c, detail in zip(calls, readiness["calls"]):
        if detail["issues"]:
            status["invalid_or_unlinked"] += 1
            continue
        res = base5.get(c["set"], [])
        if not res:
            status["pending"] += 1
            continue
        r = res[0]
        if r.get("status") != "RESOLVED":
            status["unresolvable"] += 1
            continue
        cone = {x["id"]: x for x in r["cone"]}
        if not all(isinstance(cone.get(n, {}).get("outcome"), bool) for n in STATEMENTS):
            status["resolved_without_outcomes"] += 1
            continue
        s = sets[c["set"]]
        prior = {x["id"]: x["prior"] for x in s["cone"]}
        lrec = [x for x in learner.get(c["set"], []) if x.get("made_at", "") < s["entry_cutoff"]]
        lpub = {n: lrec[-1]["forecasts"][n]["published"] for n in STATEMENTS} if lrec else None
        out = {n: 1.0 if cone[n]["outcome"] else 0.0 for n in STATEMENTS}
        cand = r.get("candidate", {})
        net = cand.get("trade", {}).get("net_return") if cand.get("status") == "TRADED" else None
        scored.append(
            {
                "call_id": c["call_id"],
                "set": c["set"],
                "market": c["market"],
                "signal_session": c["signal_session"],
                "call": c["call"],
                "agrees_with_kod": c["agrees_with_kod"],
                "book": book.get(c["set"]),
                "p": {n: c["p"][n] for n in STATEMENTS},
                "prior": prior,
                "learner": lpub,
                "outcome": out,
                "net_return": net,
                "brier_llm": statistics.fmean((c["p"][n] - out[n]) ** 2 for n in STATEMENTS),
                "brier_prior": statistics.fmean((prior[n] - out[n]) ** 2 for n in STATEMENTS),
                "brier_learner": None
                if lpub is None
                else statistics.fmean((lpub[n] - out[n]) ** 2 for n in STATEMENTS),
            }
        )
    status["scored"] = len(scored)
    # The scored set must equal KOD's own readiness count.
    assert len(scored) == readiness["counts"]["complete_BASE5_outcomes"], "scored set differs from KOD's audit"

    def block(sample):
        withl = [x for x in sample if x["brier_learner"] is not None]
        per = {
            n: {
                "brier_llm": mean_or_none([(x["p"][n] - x["outcome"][n]) ** 2 for x in sample]),
                "brier_prior": mean_or_none([(x["prior"][n] - x["outcome"][n]) ** 2 for x in sample]),
                "brier_learner": mean_or_none([(x["learner"][n] - x["outcome"][n]) ** 2 for x in withl]),
                "outcome_rate": mean_or_none([x["outcome"][n] for x in sample]),
                "mean_p_llm": mean_or_none([x["p"][n] for x in sample]),
                "mean_prior": mean_or_none([x["prior"][n] for x in sample]),
                "mean_learner": mean_or_none([x["learner"][n] for x in withl]),
            }
            for n in STATEMENTS
        }
        by_call = {}
        for label in ("BACK", "AVOID", "ABSTAIN"):
            g = [x for x in sample if x["call"] == label]
            traded = [x["net_return"] for x in g if x["net_return"] is not None]
            by_call[label] = {"calls": len(g), "traded": len(traded), "mean_net": mean_or_none(traded)}
        back, avoid = by_call["BACK"], by_call["AVOID"]
        back_beats = (
            None
            if back["traded"] == 0 or avoid["traded"] == 0
            else bool(back["mean_net"] > avoid["mean_net"])
        )
        by_book = {}
        for label in ("BUY_OK", "DONT_BUY"):
            for call in ("AVOID", "ABSTAIN", "BACK"):
                g = [x["net_return"] for x in sample if x["book"] == label and x["call"] == call and x["net_return"] is not None]
                if g:
                    by_book[f"{label}|{call}"] = {"traded": len(g), "mean_net": mean_or_none(g)}
        return {
            "n": len(sample),
            "vs_prior": compare(
                [x["brier_llm"] for x in sample], [x["brier_prior"] for x in sample], [x["signal_session"] for x in sample]
            ),
            "vs_learner": compare(
                [x["brier_llm"] for x in withl], [x["brier_learner"] for x in withl], [x["signal_session"] for x in withl]
            ),
            "per_statement": per,
            "by_call": by_call,
            "back_beats_avoid_net": back_beats,
            "back_vs_avoid_informative": back["traded"] >= 5,
            "by_book_and_call": by_book,
        }

    disagree = [x for x in scored if x["agrees_with_kod"] is False]
    all_calls_disagree = [c for c in calls if c.get("agrees_with_kod") is False]
    result = {
        "schema": "LLM_ARM_V1_SCORE_V1",
        "rule": "PROTOCOL.md + ADDENDUM_1_SCORING.md",
        "inputs": {
            "root": str(root),
            "calls": {Path(f).name: sha(f) for f in call_files},
            "speculations.jsonl": sha(reg_path),
            "learner_v2.jsonl": sha(learner_path),
            "paper_book.jsonl": sha(book_path),
        },
        "counts": dict(status),
        "all_calls": len(calls),
        "calls_by_label": dict(Counter(c["call"] for c in calls)),
        "disagreements_all": [
            {"call_id": c["call_id"], "call": c["call"], "kod_numeric": c.get("kod_numeric")} for c in all_calls_disagree
        ],
        "first_look": {
            "required": FIRST_LOOK,
            "scored": len(scored),
            "reached": len(scored) >= FIRST_LOOK,
            "kind": "FIRST_LOOK" if len(scored) >= FIRST_LOOK else "INTERIM_NOT_DECISIONAL",
        },
        "all_scored": block(scored),
        "disagreements_scored": block(disagree),
        "scored_calls": [
            {k: x[k] for k in ("call_id", "market", "signal_session", "call", "agrees_with_kod", "book", "net_return")}
            | {k: round(x[k], 5) if x[k] is not None else None for k in ("brier_llm", "brier_prior", "brier_learner")}
            for x in scored
        ],
    }
    text = json.dumps(result, indent=1)
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

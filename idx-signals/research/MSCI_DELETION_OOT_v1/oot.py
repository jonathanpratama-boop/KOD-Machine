"""MSCI_DELETION_OOT_v1: the frozen MSCI_DELETION_v1 rule, unchanged, on the reviews after KOD's sealed IDX holdout.

Reviews Feb 2025 .. Aug 2026 (implementation sessions 2025-02-28 .. 2026-08-31), priced on the same pinned IDX panel and
corporate-action registry, whose post-holdout segment (2025-02-24 .. 2026-10-06) KOD has used before for other questions
(IDX_INSIDER_NEWS_OOT, MOVERS_NOW_v1) but never for this one. Every function that decides events, execution, controls,
the account and the statistics is MSCI_DELETION_v1's frozen code, imported unchanged; only the window and the event table
differ. The sealed holdout's outcomes (the 2024 reviews) are never computed.

    python3 research/MSCI_DELETION_OOT_v1/oot.py --feasibility
    python3 research/MSCI_DELETION_OOT_v1/oot.py --freeze
    python3 research/MSCI_DELETION_OOT_v1/oot.py --run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "msci_deletion", ROOT / "research/MSCI_DELETION_v1/msci_deletion.py"
)
v1 = importlib.util.module_from_spec(_spec)
sys.modules["msci_deletion"] = v1
_spec.loader.exec_module(v1)
from idxsig import corporate_actions, idx_events, panel
from idxsig.provenance import sha256_file, utc_stamp

EVENTS = HERE / "events_all.csv"
PROTO, RUN, FEAS = HERE / "protocol.json", HERE / "run", HERE / "FEASIBILITY.json"
START, END = (
    "2025-02-24",
    "2026-10-06",
)  # the first session after the sealed holdout .. the panel's last session
SEALED = ("2024-01-02", "2025-02-21")
REVIEWS = ("Feb25", "May25", "Aug25", "Nov25", "Feb26", "May26", "Aug26")
GATES = {
    "O0_sample": "at least 15 scored deletion trades (with matched controls) from at least 4 reviews; else INCONCLUSIVE",
    "O1_net": "mean net trade return (v1's primary plan: implementation-close entry, hold 20, Stockbit-level costs) > 0",
    "O2_excess": "mean excess over matched controls > 0",
    "O3_account": "v1's account (slots fixed before the auction, each at most 25% and IDR 40m, cash otherwise) ends "
    "above its start",
    "verdict": "CONFIRMED if O0-O3 all pass; CONFIRMED_STRONG if, in addition, the review-cluster bootstrap one-sided "
    "95% lower bound of the mean excess is > 0; INCONCLUSIVE if O0 fails; otherwise NOT_CONFIRMED. One run; no other "
    "hold, entry, event set or window.",
}


def load_inputs():
    df, meta, _ = panel.load(v1.PANEL_MANIFEST)
    df = df[df["date"] <= pd.Timestamp(END)].copy()
    reg, rmeta = corporate_actions.load(v1.REGISTRY_MANIFEST, panel_sha256=meta["sha256"])
    return df, reg, {"panel_sha256": meta["sha256"], "registry_sha256": rmeta["sha256"]}


def oot_events(ev_all: pd.DataFrame, sessions: np.ndarray) -> pd.DataFrame:
    d = ev_all[
        (ev_all.side == "DEL") & ev_all.kind.isin(v1.DELETION_KINDS) & ev_all.review.isin(REVIEWS)
    ].copy()
    d["entry_session"] = [v1.implementation_session(sessions, x) for x in d.implementation_close]
    if (d.entry_session <= SEALED[1]).any():
        raise RuntimeError("an entry inside the sealed holdout")
    d["posted_wib"] = d.entry_session + " 09:00:00"
    return d.reset_index(drop=True)


def prepared(df, reg, ev_all):
    """Features for matching are computed on the whole panel up to END and then windowed, as in v1 and in
    IDX_INSIDER_NEWS_OOT, so trailing features at the first OOT sessions read prices from inside the sealed window; no
    return or outcome inside it is computed."""
    prep = idx_events.prepare(df, reg, START, END)
    if str(prep.m.dates.min()) < START or str(prep.m.dates.max()) > END:
        raise RuntimeError("the market window leaves the out-of-time segment")
    sessions = np.array(sorted(df.date.unique()), dtype="datetime64[D]")
    v1.exclude_review_names(prep, ev_all, sessions)
    return prep, sessions


def gates(r: dict) -> dict:
    p, a = r["primary"], r["account"]
    g = {
        "O0_sample": "PASS"
        if p["scored_with_controls"] >= 15 and len(p.get("by_review", {})) >= 4
        else "FAIL",
        "O1_net": "PASS" if (p.get("mean_net") or -1) > 0 else "FAIL",
        "O2_excess": "PASS" if (p.get("mean_excess") or -1) > 0 else "FAIL",
        "O3_account": "PASS" if a["end_equity"] > a["start"] else "FAIL",
    }
    if g["O0_sample"] == "FAIL":
        verdict = "INCONCLUSIVE"
    elif all(v == "PASS" for v in g.values()):
        lb = p.get("boot_excess", {}).get("lower_one_sided_95")
        verdict = "CONFIRMED_STRONG" if lb is not None and lb > 0 else "CONFIRMED"
    else:
        verdict = "NOT_CONFIRMED"
    return {"gates": g, "verdict": verdict}


def feasibility() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    df, reg, meta = load_inputs()
    ev_all = pd.read_csv(EVENTS)
    prep, sessions = prepared(df, reg, ev_all)
    ev = oot_events(ev_all, sessions)
    res = idx_events.run_events(prep, ev, v1.config(), draws=5, seed=v1.SEED)
    f = idx_events.filled(res)
    out = {
        "study": "MSCI_DELETION_OOT_v1",
        "computed_at": utc_stamp(),
        "what": "counts only; no return printed, saved or looked at",
        **meta,
        "deletion_events": len(ev),
        "by_kind": ev.kind.value_counts().to_dict(),
        "mapped_to_panel": len(res),
        "status_counts": idx_events.status_counts(res),
        "scored_with_controls": len(f),
        "reviews_with_a_scored_trade": int(f.review.nunique()),
        "entry_sessions": dict(zip(ev.review, ev.entry_session)),
    }
    FEAS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


PINS = (
    "research/MSCI_DELETION_OOT_v1/oot.py",
    "research/MSCI_DELETION_OOT_v1/build_events.py",
    "research/MSCI_DELETION_OOT_v1/collect.py",
    "research/MSCI_DELETION_OOT_v1/ticker_map.csv",
    "research/MSCI_DELETION_OOT_v1/events_all.csv",
    "research/MSCI_DELETION_OOT_v1/PROTOCOL.md",
    "research/MSCI_DELETION_OOT_v1/FEASIBILITY.json",
    "tests/test_msci_deletion_oot.py",
    "research/MSCI_DELETION_OOT_v1/report.py",
    "data/manifests/msci_lists_oot-20261101T002157Z.jsonl",
    *v1.PINS,
)


def frozen_fields() -> dict:
    return {
        "window": {
            "start": START,
            "end": END,
            "sealed_not_evaluated": list(SEALED),
            "reviews": list(REVIEWS),
        },
        "v1_frozen_fields": v1.frozen_fields(),
        "gates": GATES,
    }


def inputs_reproduce() -> None:
    man = ROOT / "data/manifests/msci_lists_oot-20261101T002157Z.jsonl"
    for line in man.read_text().splitlines()[1:]:
        r = json.loads(line)
        if sha256_file(ROOT / "data/raw" / r["file"]) != r["sha256"]:
            sys.exit(f"error: {r['file']} differs from its manifest")
    if subprocess.run(
        [sys.executable, str(HERE / "build_events.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    ).returncode:
        sys.exit("error: events_all.csv does not regenerate from the pinned PDFs")


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    v1.git_clean([*PINS, "idxsig"])
    inputs_reproduce()
    proto = {
        "study_id": "MSCI_DELETION_OOT_v1",
        "frozen_at": utc_stamp(),
        **frozen_fields(),
        "idxsig_tree": v1.idxsig_tree(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "window", "gates")}, indent=1))
    return 0


def run() -> int:
    if RUN.exists():
        sys.exit("error: run/ exists; MSCI_DELETION_OOT_v1 runs once")
    proto = json.loads(PROTO.read_text())
    v1.git_clean([*PINS, "research/MSCI_DELETION_OOT_v1/protocol.json", "idxsig"])
    if set(proto["pins"]) != set(PINS):
        sys.exit("error: protocol.json pins a different file set")
    for p, want in proto["pins"].items():
        if sha256_file(ROOT / p) != want:
            sys.exit(f"error: {p} changed since the freeze")
    for k, want in frozen_fields().items():
        if proto[k] != want:
            sys.exit(f"error: protocol.json '{k}' differs from this code")
    if proto["idxsig_tree"] != v1.idxsig_tree():
        sys.exit("error: the idxsig package changed since the freeze")
    inputs_reproduce()
    df, reg, meta = load_inputs()
    feas = json.loads(FEAS.read_text())
    if (meta["panel_sha256"], meta["registry_sha256"]) != (
        feas["panel_sha256"],
        feas["registry_sha256"],
    ):
        sys.exit("error: panel or registry differs from the feasibility run")
    ev_all = pd.read_csv(EVENTS)
    prep, sessions = prepared(df, reg, ev_all)
    ev = oot_events(ev_all, sessions)
    res = {
        "study": "MSCI_DELETION_OOT_v1",
        "ran_at": utc_stamp(),
        **meta,
        "protocol_sha256": sha256_file(PROTO),
        "versions": v1.versions(),
    }
    files = {}
    variants = {
        "primary": v1.config(),
        "S1_entry_next_session": v1.config(entry_lag=2),
        "S2_tick_cost": v1.config(tick_cost=True),
        **{f"descriptive_hold_{h}": v1.config(hold=h) for h in v1.DESCRIPTIVE_HOLDS},
    }
    for name, cfg in variants.items():
        out = idx_events.run_events(prep, ev, cfg, draws=v1.DRAWS, seed=v1.SEED)
        res[name] = v1.summarize(out)
        files[f"trades_{name}.csv"] = out
        if name == "primary":
            res["account"] = v1.account(out, REVIEWS)
            best = v1.best_review(out)
            res["account_without_best_review"] = {
                "review": best,
                **v1.account(out, REVIEWS, skip_review=best),
            }
    res.update(gates(res))
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RUN.mkdir()
    for name, frame in files.items():
        frame.to_csv(RUN / name, index=False)
    (RUN / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(res["verdict"], json.dumps(res["gates"], indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--feasibility", action="store_true")
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    return feasibility() if a.feasibility else freeze() if a.freeze else run()


if __name__ == "__main__":
    sys.exit(main())

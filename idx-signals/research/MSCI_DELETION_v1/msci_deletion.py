"""MSCI_DELETION_v1: buy IDX shares that MSCI deletes, in the closing auction where index trackers must sell them; hold 20 sessions.

Hypothesis (PROTOCOL.md): passive funds tracking MSCI Indonesia must sell a deleted name at the review's implementation close,
whatever the price. A spot buyer who supplies that liquidity at the close is paid by the price concession, which partly
reverses afterwards. Executed on KOD's audited IDX harness (idxsig.idx_events / execution: IDX lots, auto-rejection limits,
decision-time capacity FILL-C, Stockbit-level fees, registry-verified corporate actions) with each event's matched controls.

    python3 research/MSCI_DELETION_v1/msci_deletion.py --feasibility   # counts only, no return looked at
    python3 research/MSCI_DELETION_v1/msci_deletion.py --freeze
    python3 research/MSCI_DELETION_v1/msci_deletion.py --run

Timing: MSCI publishes a review after the European close (about 04:00-05:00 WIB the next morning), roughly ten IDX sessions
before the implementation close. The order is a buy in the closing auction of the implementation session (the last IDX
session on or before MSCI's implementation date), i.e. the same auction the trackers sell into; the exit is a sell in the
closing auction 20 sessions later. No price is used to choose events.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import corporate_actions, idx_events, panel
from idxsig.execution import ExecConfig
from idxsig.market import Fees
from idxsig.provenance import sha256_file, utc_stamp

PANEL_MANIFEST = ROOT / "data/manifests/panel-20261007T225823Z.json"
REGISTRY_MANIFEST = ROOT / "data/manifests/ca_registry-20261007T230210Z.json"
EVENTS = HERE / "events_all.csv"
PROTO, RUN, FEAS = HERE / "protocol.json", HERE / "run", HERE / "FEASIBILITY.json"
START, END = (
    "2019-10-01",
    "2023-12-29",
)  # END: the last IDX session before the sealed holdout (2024-01-02..2025-02-21)
HOLDOUT_FIRST = "2024-01-02"
DISCOVERY = (
    "Nov19",
    "Feb20",
    "May20",
    "Aug20",
    "Nov20",
    "Feb21",
    "May21",
    "Aug21",
    "Nov21",
    "Feb22",
    "May22",
    "Aug22",
    "Nov22",
)  # every scheduled review Nov 2019 .. Nov 2022
SCREEN = ("Feb23", "May23", "Aug23", "Nov23")
DELETION_KINDS = (
    "ST_EXIT",
    "ST_TO_SC",
    "SC_EXIT",
)  # SC_TO_ST is an upward migration (net buying): excluded
HOLD, ENTRY_LAG = 20, 1
DESCRIPTIVE_HOLDS = (5, 60)
DRAWS, SEED = 200, 20261101
BOOT = {"draws": 10_000, "seed": 20261102}
MAX_WEIGHT = 0.25
NOTIONAL = 40_000_000.0  # IDR: MAX_WEIGHT x START_CASH, the largest position the account takes; capacity checked at it
DECISION_SKIPS = (
    "SKIP_LOT",
    "SKIP_LIQUIDITY",
    "SKIP_CAPACITY_UNKNOWN",
)  # known before the auction: no slot
START_CASH = 160_000_000.0  # IDR, about 10,000 USD


def config(hold: int = HOLD, entry_lag: int = ENTRY_LAG, tick_cost: bool = False) -> ExecConfig:
    """The IDX event configuration of research/IDX_INSIDER_NEWS run_v2 (FILL-C, registry, Stockbit-level fees)."""
    return ExecConfig(
        holding_days=hold,
        entry_lag=entry_lag,
        notional=NOTIONAL,
        max_participation=0.10,
        fees=Fees(0.0015, 0.0025),
        data_end_exit="last_close",
        ca_mode="registry",
        fill_model="C",
        tick_cost=tick_cost,
    )


# ------------------------------------------------------------------------------------------------------------ inputs
def load_inputs():
    df, meta, _ = panel.load(
        PANEL_MANIFEST
    )  # the CSV is parsed whole; rows after END are dropped before any use
    keep = df["date"] <= pd.Timestamp(END)
    dropped = int((~keep).sum())
    df = df[keep].copy()
    reg, rmeta = corporate_actions.load(REGISTRY_MANIFEST, panel_sha256=meta["sha256"])
    return (
        df,
        reg,
        {
            "panel_sha256": meta["sha256"],
            "registry_sha256": rmeta["sha256"],
            "rows_after_end_dropped": dropped,
        },
    )


def implementation_session(sessions: np.ndarray, implementation_close: str) -> str:
    """The last IDX session on or before MSCI's implementation date (an IDX holiday moves it to the session before)."""
    day = np.datetime64(implementation_close, "D")
    k = int(np.searchsorted(sessions, day, side="right")) - 1
    if k < 0:
        raise ValueError("no session on or before the implementation date")
    return str(sessions[k])


def deletion_events(ev_all: pd.DataFrame, sessions: np.ndarray, reviews: tuple) -> pd.DataFrame:
    stray = set(ev_all[ev_all.side == "DEL"].review) - set(DISCOVERY) - set(SCREEN)
    if stray:
        raise RuntimeError(f"deletions in reviews outside both windows: {sorted(stray)}")
    d = ev_all[
        (ev_all.side == "DEL") & ev_all.kind.isin(DELETION_KINDS) & ev_all.review.isin(reviews)
    ].copy()
    d["entry_session"] = [implementation_session(sessions, x) for x in d.implementation_close]
    d["posted_wib"] = (
        d.entry_session + " 09:00:00"
    )  # at or before 14:30 on that session: bought at its close
    return d.reset_index(drop=True)


def exclude_review_names(prep, ev_all: pd.DataFrame, sessions: np.ndarray) -> None:
    """No name MSCI changed in a review (added or deleted, either segment) may serve as a matched control at that review's
    signal session."""
    tick = pd.Index(prep.m.tickers)
    for review, g in ev_all.groupby("review"):
        entry = implementation_session(sessions, g.implementation_close.iloc[0])
        posted = pd.Timestamp(entry + " 09:00:00")
        s = idx_events.signal_session(prep.m.dates, posted)
        if s is None:
            continue
        for t in g.ticker.astype(str).str.upper():
            n = tick.get_indexer([t])[0]
            if n >= 0:
                prep.evaluable[n, s] = False


# ------------------------------------------------------------------------------------------------------------ stats
def cluster_bootstrap(x: np.ndarray, groups) -> dict:
    x, g = np.asarray(x, float), np.asarray(groups)
    uniq = np.unique(g)
    if len(x) == 0:
        return {
            "mean": None,
            "lower_one_sided_95": None,
            "lower95": None,
            "upper95": None,
            "clusters": 0,
        }
    if len(uniq) < 2:
        return {
            "mean": float(x.mean()),
            "lower_one_sided_95": None,
            "lower95": None,
            "upper95": None,
            "clusters": len(uniq),
        }
    rng = np.random.default_rng(BOOT["seed"])
    members = [x[g == u] for u in uniq]
    d = np.array(
        [
            np.concatenate([members[k] for k in rng.integers(0, len(uniq), len(uniq))]).mean()
            for _ in range(BOOT["draws"])
        ]
    )
    return {
        "mean": float(x.mean()),
        "lower_one_sided_95": float(np.quantile(d, 0.05)),
        "lower95": float(np.quantile(d, 0.025)),
        "upper95": float(np.quantile(d, 0.975)),
        "clusters": len(uniq),
        **BOOT,
    }


def account(res: pd.DataFrame, reviews: tuple, skip_review: str | None = None) -> dict:
    """Each review: the slots are the deletions not skipped before the auction (DECISION_SKIPS); each slot gets
    min(MAX_WEIGHT, 1/slots, NOTIONAL/equity) of equity, so no position exceeds the size whose capacity the harness checked.
    A slot whose trade is not scored (not traded at the auction, corporate action, ...) stays in cash, as does the rest.
    Reviews never overlap (20 sessions < the gap between reviews), so the account compounds review by review.
    `skip_review` drops one review entirely (descriptive: the account without its best review)."""
    eq, curve, rows = START_CASH, [("start", START_CASH)], []
    for r in reviews:
        if r == skip_review:
            continue
        g = res[res.review == r]
        slots = int((~g.status.isin(DECISION_SKIPS)).sum())
        if not slots:
            continue
        w = min(MAX_WEIGHT, 1.0 / slots, NOTIONAL / eq)
        traded = g[g.net_return.notna()]
        for t in traded.itertuples():
            rows.append(
                {
                    "review": r,
                    "ticker": t.ticker,
                    "weight": w,
                    "net_return": t.net_return,
                    "pnl": eq * w * t.net_return,
                }
            )
        eq = eq * (1 + w * traded.net_return.sum())
        curve.append((r, eq))
    pnl = pd.DataFrame(rows, columns=["review", "ticker", "weight", "net_return", "pnl"])
    vals = np.array([v for _, v in curve])
    dd = float((vals / np.maximum.accumulate(vals) - 1).min()) if len(vals) else 0.0
    # G3's concentration check: trades ranked by IDR P&L in the compounded account; the residual is the sum of the
    # other trades' IDR P&L (no re-compounding)
    top3 = pnl.pnl.sort_values(ascending=False).head(3).clip(lower=0).sum() if len(pnl) else 0.0
    return {
        "start": START_CASH,
        "end_equity": float(eq),
        "net_return": float(eq / START_CASH - 1),
        "max_drawdown_at_review_exits": dd,
        "reviews_traded": int(len(curve) - 1),
        "trades": len(pnl),
        "pnl_without_top3": float(pnl.pnl.sum() - top3) if len(pnl) else 0.0,
        "mean_capital_per_review": float(pnl.groupby("review").weight.sum().mean())
        if len(pnl)
        else 0.0,
        "curve": [(k, float(v)) for k, v in curve],
    }


def best_review(res: pd.DataFrame) -> str | None:
    f = res[res.net_return.notna()]
    return None if not len(f) else str(f.groupby("review").net_return.mean().idxmax())


def summarize(res: pd.DataFrame) -> dict:
    f = idx_events.filled(res)
    out = {
        "mapped": len(res),
        "status": idx_events.status_counts(res),
        "scored_with_controls": len(f),
        "match_levels": {
            int(k): int(v) for k, v in f.match_level.value_counts().sort_index().items()
        },
    }
    if len(f):
        out.update(
            mean_net=float(f.net_return.mean()),
            median_net=float(f.net_return.median()),
            win_rate=float((f.net_return > 0).mean()),
            worst_net=float(f.net_return.min()),
            best_net=float(f.net_return.max()),
            mean_control=float(f.control_mean.mean()),
            mean_excess=float(f.excess.mean()),
            boot_net=cluster_bootstrap(f.net_return.to_numpy(), f.review),
            boot_excess=cluster_bootstrap(f.excess.to_numpy(), f.review),
            by_kind={
                k: {
                    "n": len(g),
                    "mean_net": float(g.net_return.mean()),
                    "mean_excess": float(g.excess.mean()),
                }
                for k, g in f.groupby("kind")
            },
            by_review={
                k: {
                    "n": len(g),
                    "mean_net": float(g.net_return.mean()),
                    "mean_excess": float(g.excess.mean()),
                }
                for k, g in f.groupby("review", sort=False)
            },
        )
    return out


GATES = {
    "G0_sample": "discovery: at least 30 scored deletion trades (with matched controls) from at least 6 reviews; else "
    "INCONCLUSIVE",
    "G1_net_edge": "discovery mean net trade return (hold 20, fees 0.15%/0.25%) > 0 and its review-cluster bootstrap "
    "one-sided 95% lower bound > 0",
    "G2_vs_matched_controls": "discovery mean excess (net minus the event's matched-control mean under the same plan) > 0 "
    "and its review-cluster bootstrap one-sided 95% lower bound > 0",
    "G3_account": "discovery account (equal weight per review, at most 25% per name, cash otherwise) ends above start and "
    "its P&L without the 3 largest winning trades is > 0",
    "G4_stress": "discovery mean net trade return > 0 with entry one session after the implementation close (S1) and "
    "with one tick per side added to costs (S2)",
    "G5_screen_2023": "with at least 5 scored 2023 deletion trades their mean net return must be >= 0 (fewer: "
    "uninformative, flagged, does not block)",
    "verdict": "PROMISING (a candidate for validation, never proof) only if G0-G5 all pass; INCONCLUSIVE if G0 fails; "
    "otherwise FAIL. Where this text and the code differ, this file's code governs.",
}


def gates(r: dict) -> dict:
    d, g = r["discovery"], {}
    p = d["primary"]
    g["G0_sample"] = (
        "PASS" if p["scored_with_controls"] >= 30 and len(p.get("by_review", {})) >= 6 else "FAIL"
    )
    bn, be = p.get("boot_net", {}), p.get("boot_excess", {})
    g["G1_net_edge"] = (
        "PASS" if (bn.get("mean") or 0) > 0 and (bn.get("lower_one_sided_95") or -1) > 0 else "FAIL"
    )
    g["G2_vs_matched_controls"] = (
        "PASS" if (be.get("mean") or 0) > 0 and (be.get("lower_one_sided_95") or -1) > 0 else "FAIL"
    )
    a = d["account"]
    g["G3_account"] = (
        "PASS" if a["end_equity"] > a["start"] and a["pnl_without_top3"] > 0 else "FAIL"
    )
    s1, s2 = d["S1_entry_next_session"], d["S2_tick_cost"]
    g["G4_stress"] = (
        "PASS" if (s1.get("mean_net") or -1) > 0 and (s2.get("mean_net") or -1) > 0 else "FAIL"
    )
    sc = r["screen_2023"]["primary"]
    if sc["scored_with_controls"] < 5:
        g["G5_screen_2023"] = "PASS (uninformative: fewer than 5 trades)"
    else:
        g["G5_screen_2023"] = "PASS" if sc["mean_net"] >= 0 else "FAIL"
    if g["G0_sample"] == "FAIL":
        verdict = "INCONCLUSIVE"
    elif all(v.startswith("PASS") for v in g.values()):
        verdict = "PROMISING"
    else:
        verdict = "FAIL"
    return {"gates": g, "verdict": verdict}


# ------------------------------------------------------------------------------------------------------------ modes
def prepared(df, reg, ev_all):
    prep = idx_events.prepare(df, reg, START, END)
    if prep.m.dates.max() > np.datetime64(END) or df["date"].max() > pd.Timestamp(END):
        raise RuntimeError("a session after END reached the market")
    sessions = np.array(sorted(df.date.unique()), dtype="datetime64[D]")
    exclude_review_names(prep, ev_all, sessions)
    return prep, sessions


def feasibility() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists; feasibility is a pre-freeze step")
    df, reg, meta = load_inputs()
    ev_all = pd.read_csv(EVENTS)
    prep, sessions = prepared(df, reg, ev_all)
    out = {
        "study": "MSCI_DELETION_v1",
        "computed_at": utc_stamp(),
        "what": "event and status counts only; the harness "
        "computes returns internally and none is printed, saved or looked at",
        **meta,
    }
    for name, reviews in (("discovery", DISCOVERY), ("screen_2023", SCREEN)):
        ev = deletion_events(ev_all, sessions, reviews)
        res = idx_events.run_events(prep, ev, config(), draws=5, seed=SEED)
        f = idx_events.filled(res)
        out[name] = {
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
    "research/MSCI_DELETION_v1/msci_deletion.py",
    "research/MSCI_DELETION_v1/build_events.py",
    "research/MSCI_DELETION_v1/collect.py",
    "research/MSCI_DELETION_v1/ticker_map.csv",
    "research/MSCI_DELETION_v1/events_all.csv",
    "research/MSCI_DELETION_v1/PROTOCOL.md",
    "research/MSCI_DELETION_v1/FEASIBILITY.json",
    "research/MSCI_DELETION_v1/report.py",
    "tests/test_msci_deletion.py",
    "data/manifests/msci_lists-20261031T235555Z.jsonl",
    "data/manifests/panel-20261007T225823Z.json",
    "data/manifests/ca_registry-20261007T230210Z.json",
    "idxsig/idx_events.py",
    "idxsig/execution.py",
    "idxsig/controls.py",
    "idxsig/market.py",
    "idxsig/panel.py",
    "idxsig/corporate_actions.py",
    "idxsig/provenance.py",
    "idxsig/__init__.py",
    "idxsig/quality.py",
    "idxsig/sources/__init__.py",
    "idxsig/sources/idx_mirror.py",
)


def idxsig_tree() -> str:
    """Git tree hash of idx-signals/idxsig at HEAD: the whole harness package, pinned at the freeze."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD:idx-signals/idxsig"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def inputs_reproduce() -> None:
    """The pinned PDFs match their manifest and events_all.csv regenerates from them byte for byte."""
    man = ROOT / "data/manifests/msci_lists-20261031T235555Z.jsonl"
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


def git_clean(paths) -> None:
    for p in paths:
        if subprocess.run(
            ["git", "ls-files", "--error-unmatch", p], cwd=ROOT, capture_output=True, check=False
        ).returncode:
            sys.exit(f"error: {p} is not committed")
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        sys.exit(f"error: uncommitted changes in pinned files:\n{dirty}")


def versions() -> dict:
    return {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}


def frozen_fields() -> dict:
    return {
        "windows": {
            "start": START,
            "end": END,
            "holdout_first_not_read": HOLDOUT_FIRST,
            "discovery_reviews": list(DISCOVERY),
            "screen_reviews": list(SCREEN),
        },
        "deletion_kinds": list(DELETION_KINDS),
        "hold": HOLD,
        "entry_lag": ENTRY_LAG,
        "descriptive_holds": list(DESCRIPTIVE_HOLDS),
        "draws": DRAWS,
        "seed": SEED,
        "bootstrap": BOOT,
        "max_weight": MAX_WEIGHT,
        "start_cash_idr": START_CASH,
        "exec_config": {k: str(v) for k, v in config().__dict__.items()},
        "gates": GATES,
        "versions": versions(),
    }


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    git_clean([*PINS, "idxsig"])
    inputs_reproduce()
    proto = {
        "study_id": "MSCI_DELETION_v1",
        "frozen_at": utc_stamp(),
        **frozen_fields(),
        "idxsig_tree": idxsig_tree(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "hold", "gates")}, indent=1))
    return 0


def run() -> int:
    if RUN.exists():
        sys.exit("error: run/ exists; MSCI_DELETION_v1 runs once")
    proto = json.loads(PROTO.read_text())
    git_clean([*PINS, "research/MSCI_DELETION_v1/protocol.json"])
    if set(proto["pins"]) != set(PINS):
        sys.exit("error: protocol.json pins a different file set")
    for p, want in proto["pins"].items():
        if sha256_file(ROOT / p) != want:
            sys.exit(f"error: {p} changed since the freeze")
    for k, want in frozen_fields().items():
        if proto[k] != want:
            sys.exit(f"error: protocol.json '{k}' differs from this code")
    git_clean(["idxsig"])
    if proto["idxsig_tree"] != idxsig_tree():
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
    res, files = (
        {
            "study": "MSCI_DELETION_v1",
            "ran_at": utc_stamp(),
            **meta,
            "protocol_sha256": sha256_file(PROTO),
            "versions": versions(),
        },
        {},
    )
    variants = {
        "primary": config(),
        "S1_entry_next_session": config(entry_lag=2),
        "S2_tick_cost": config(tick_cost=True),
        **{f"descriptive_hold_{h}": config(hold=h) for h in DESCRIPTIVE_HOLDS},
    }
    for period, reviews in (("discovery", DISCOVERY), ("screen_2023", SCREEN)):
        ev = deletion_events(ev_all, sessions, reviews)
        res[period] = {}
        for name, cfg in variants.items():
            out = idx_events.run_events(prep, ev, cfg, draws=DRAWS, seed=SEED)
            res[period][name] = summarize(out)
            files[f"{period}/trades_{name}.csv"] = out
            if name == "primary":
                res[period]["account"] = account(out, reviews)
                best = best_review(out)
                res[period]["account_without_best_review"] = {
                    "review": best,
                    **account(out, reviews, skip_review=best),
                }
    res.update(gates(res))
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RUN.mkdir()
    for name, frame in files.items():
        p = RUN / name
        p.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(p, index=False)
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

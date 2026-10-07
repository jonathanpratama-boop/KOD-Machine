"""Prospective paper-only testing of the frozen E1 detector. No orders, ever.

After each IDX session closes, `paper-scan` pulls the last ~200 days of daily bars for every
active name (Yahoo, manifest-logged), runs the frozen detector on the session that just
closed, and appends to paper/ledger.jsonl:

  SCAN       one per session, always: coverage, every flag of the decision detector and of
             the benchmark detectors, and the outcome NO SIGNAL when nothing qualifies.
  DECISION   one per qualifying candidate, decided by POLICY before the next session's close:
             BUY ON TRIGGER (paper), PASS, or NOT EXECUTABLE, each with thesis, falsifiable
             prediction, trigger, chase limit, invalidation, sizing formula and scenarios,
             maximum planned loss, horizon and expiry, or the exact reason it is not a trade.
  OUTCOME    appended by `paper-score` once a decision's window has ended: discovery scored
             apart from the decision and its execution.

Each line carries the hash of the previous line (a chain) and is stamped by two RFC 3161
authorities; the commit that adds it is pushed so GitHub's own workflow-run record dates it.
Nothing is ever rewritten: corrections are new lines.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import market as mkt
from .execution import Market
from .provenance import PKG_ROOT, read_manifest, rel, sha256_file, utc_stamp
from .rules import CausalSource
from .rules import moonshot_e1 as family

PAPER = PKG_ROOT / "paper"
LEDGER = PAPER / "ledger.jsonl"
SCANS = PAPER / "scans"
TOKENS = PAPER / "timestamps"
POLICY_ID = "PAPER-POLICY-v1"
HISTORY_DAYS = 200
MIN_HISTORY = 20
BENCHMARKS = ("F2_IGNITION_D", "F1_ARA")  # logged every scan, never decided on


@dataclass(frozen=True)
class Policy:
    """Frozen decision policy. A change is a new POLICY_ID; old decisions keep theirs."""

    equity_idr: float = 100_000_000.0       # hypothetical account; the real budget is unknown
    risk_fractions: tuple = (0.005, 0.01)   # scenarios: 0.5% and 1% of equity at risk per trade
    max_position_fraction: float = 0.20     # at most 20% of equity in one name
    max_adv_participation: float = 0.10     # at most 10% of the 20-session median traded value
    chase_limit: float = 0.10               # no fill above signal close x 1.10
    max_stop_distance: float = 0.15         # invalidation no further than 15% below entry (IDX ARB)
    fee_buy: float = 0.0015
    fee_sell: float = 0.0025
    horizon_sessions: int = 5
    min_validated_lift_p: float = 0.05      # paper BUY only if validation beat matched random at this level


POLICY = Policy()


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_default)


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if math.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def policy_record() -> dict:
    return {"policy_id": POLICY_ID, **{k: getattr(POLICY, k) for k in POLICY.__dataclass_fields__}}


def policy_sha() -> str:
    return hashlib.sha256(_canonical(policy_record()).encode()).hexdigest()


def detector_identity() -> dict:
    return {"rule_id": family.RULE_ID, "version": family.VERSION, "selected": family.SELECTED,
            "module_sha256": sha256_file(Path(family.__file__)), "benchmarks": list(BENCHMARKS)}


def ledger_lines(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def verify_chain(path: Path = LEDGER) -> list[str]:
    problems, prev = [], None
    for i, rec in enumerate(ledger_lines(path)):
        body = {k: v for k, v in rec.items() if k != "record_hash"}
        if hashlib.sha256(_canonical(body).encode()).hexdigest() != rec.get("record_hash"):
            problems.append(f"line {i + 1}: record_hash does not match its content")
        if rec.get("prev_hash") != prev:
            problems.append(f"line {i + 1}: prev_hash breaks the chain")
        prev = rec.get("record_hash")
    return problems


def append(records: list[dict], path: Path = LEDGER, timestamper=None) -> list[dict]:
    """Chain, hash, stamp and append. Returns the stored records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ledger_lines(path)
    if verify_chain(path):
        raise RuntimeError(f"{path.name} chain is broken; refusing to append")
    prev = existing[-1]["record_hash"] if existing else None
    out = []
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            body = {**rec, "prev_hash": prev}
            body["record_hash"] = hashlib.sha256(_canonical(body).encode()).hexdigest()
            fh.write(_canonical(body) + "\n")
            prev = body["record_hash"]
            out.append(body)
    if timestamper is not None:
        TOKENS.mkdir(parents=True, exist_ok=True)
        for body in out:
            for stamp in timestamper.stamp(body["record_hash"].encode()):
                (TOKENS / f"{body['record_hash']}.{stamp.authority}.tsr").write_bytes(stamp.token)
    return out


# ---------------------------------------------------------------------------------- data
def load_recent(manifest: Path) -> tuple[pd.DataFrame, dict]:
    from .panel import _yahoo_frame

    header, records = read_manifest(manifest)
    frames, status = [], {}
    for r in records:
        status[r["ticker"]] = r["http_status"]
        if r["http_status"] != 200 or not r.get("rows"):
            continue
        payload = json.loads((PKG_ROOT / r["path"]).read_text(encoding="utf-8"))
        frames.append(_yahoo_frame(r["ticker"], payload))
    df = pd.concat(frames, ignore_index=True)
    df = df[df["close"] > 0]
    return df, {"manifest": manifest.name, "manifest_sha256": sha256_file(manifest), "header": header,
                "http_status": status}


def _market(df: pd.DataFrame) -> Market:
    # Sessions: dates on which at least 50 names traded (holiday stubs dropped, as in the panel).
    traded = df[df["volume"] > 0].groupby("date")["ticker"].nunique()
    df = df[df["date"].isin(traded[traded >= 50].index)]
    return Market.from_panel(df)


# ---------------------------------------------------------------------------------- scan
def scan(manifest: Path, now: datetime | None = None, validation: dict | None = None) -> dict:
    """Evaluate the session that last closed. Returns {"scan": record, "decisions": [...], "features": DataFrame}."""
    df, data = load_recent(manifest)
    return scan_frame(df, data, now, validation)


def scan_frame(df: pd.DataFrame, data: dict, now: datetime | None = None, validation: dict | None = None) -> dict:
    if family.SELECTED is None:
        raise RuntimeError("no frozen detector (moonshot_e1.SELECTED is None)")
    now = now or datetime.now(timezone.utc)
    m = _market(df)
    d = m.shape[1] - 1
    session = str(m.dates[d])
    view = CausalSource(m).view(d)
    f = family.features(view.close, view.prev, view.high, view.low, view.volume, view.present, view.tradeable,
                        view.lock_up)
    flags = family.family_flags(f)
    tick = view.tickers
    history = np.cumsum(view.present, axis=1)[:, d]
    fresh = view.present[:, d]
    eligible = view.tradeable[:, d] & (history > MIN_HISTORY)
    value = np.where(view.tradeable, view.value, np.nan)
    adv = pd.DataFrame(value[:, max(0, d - 19): d + 1].T).median().to_numpy()
    feats = pd.DataFrame({
        "ticker": tick, "session": session, "fresh": fresh, "eligible": eligible,
        "close": view.close[:, d], "previous": view.prev[:, d], "high": view.high[:, d], "low": view.low[:, d],
        "volume": view.volume[:, d], "adv20_value": adv,
        **{k: f[k][:, d] for k in ("ret1", "rel1", "ret5", "ret20", "volr", "cpos", "dd60")},
        "ara": f["ara"][:, d], "brk60": f["brk60"][:, d],
        **{name: flags[name][:, d] & eligible for name, _ in family.FAMILY},
    }).sort_values("ticker").reset_index(drop=True)
    chosen = feats[feats[family.SELECTED]].sort_values(["volr", "ticker"], ascending=[False, True])
    requested = len(data["http_status"])
    ok = sum(1 for s in data["http_status"].values() if s == 200)
    scan_id = f"SCAN-{session}-{family.SELECTED}"
    record = {
        "type": "SCAN", "scan_id": scan_id, "session": session, "discovered_at": utc_stamp(now),
        "cutoff": f"close of IDX session {session} (bars fetched after the close)",
        "detector": detector_identity(), "policy": {"policy_id": POLICY_ID, "sha256": policy_sha()},
        "data": {"source": "yahoo_chart_v8", "manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"],
                 "requested": requested, "http_ok": ok, "fresh_for_session": int(fresh.sum()),
                 "eligible": int(eligible.sum()), "not_scanned": requested - int(fresh.sum())},
        "flags": {name: sorted(feats.loc[feats[name], "ticker"].tolist()) for name in (family.SELECTED, *BENCHMARKS)},
        "candidates_ranked": chosen["ticker"].tolist(),
        "ranking": "volume ratio (volr), descending; ties by ticker",
        "result": "NO SIGNAL" if chosen.empty else f"{len(chosen)} CANDIDATE(S)",
        "validation_evidence": validation,
    }
    decisions = [decide(row, rank + 1, scan_id, session, now, validation) for rank, row in
                 enumerate(chosen.itertuples(index=False))]
    primary = next((x for x in decisions if x["decision"] == "BUY ON TRIGGER"), None)
    for x in decisions:
        x["primary"] = x is primary
    return {"scan": record, "decisions": decisions, "features": feats, "market": m}


def _next_session(day: str) -> str:
    """Next weekday. IDX holidays are not modelled: if it is a holiday, the expiry moves to the
    next session that actually trades, and the outcome record says so."""
    return str(np.busday_offset(np.datetime64(day, "D"), 1, roll="forward"))


def decide(row, rank: int, scan_id: str, session: str, now: datetime, validation: dict | None) -> dict:
    p = POLICY
    close, low = float(row.close), float(row.low)
    tick = float(mkt.tick_size(np.array([close]))[0])
    chase = math.floor(close * (1 + p.chase_limit) / tick) * tick
    stop = max(low, close * (1 - p.max_stop_distance))
    stop = math.floor(stop / tick) * tick
    entry_ref = close  # sizing reference; the paper fill is the next session's close
    per_share_risk = entry_ref - stop + entry_ref * (p.fee_buy + p.fee_sell)
    adv = float(row.adv20_value) if np.isfinite(row.adv20_value) else 0.0
    cap_value = min(p.max_position_fraction * p.equity_idr, p.max_adv_participation * adv)
    scenarios = []
    for r in p.risk_fractions:
        budget = r * p.equity_idr
        shares = math.floor(min(budget / per_share_risk, cap_value / entry_ref) / mkt.LOT_SIZE) * mkt.LOT_SIZE \
            if per_share_risk > 0 else 0
        scenarios.append({"risk_fraction": r, "risk_budget_idr": budget, "shares": int(shares),
                          "lots": int(shares // mkt.LOT_SIZE), "position_idr": shares * entry_ref,
                          "max_planned_loss_idr": round(shares * per_share_risk)})
    reasons = []
    if not scenarios[-1]["shares"]:
        reasons.append(f"no whole lot fits: risk/lot Rp{per_share_risk * mkt.LOT_SIZE:,.0f}, position cap "
                       f"Rp{cap_value:,.0f} (10% of 20-session median value Rp{adv:,.0f})")
    if close < 50:
        reasons.append("priced below Rp50: special-board / full-call-auction rules, outside the modelled market")
    validated = bool(validation and validation.get("p_one_sided_vs_matched") is not None
                     and validation["p_one_sided_vs_matched"] < p.min_validated_lift_p
                     and (validation.get("lift_vs_matched_random") or 0) > 1)
    if reasons:
        decision, why = "NOT EXECUTABLE", "; ".join(reasons)
    elif not validated:
        decision, why = "PASS", ("the detector's validation did not beat matched random controls at p < "
                                 f"{p.min_validated_lift_p}; no edge to underwrite a paper position")
    else:
        decision, why = "BUY ON TRIGGER", "validated detector, executable size within the risk budget"
    expiry = _next_session(session)
    precision = (validation or {}).get("precision")
    return {
        "type": "DECISION", "decision_id": f"{scan_id}-{row.ticker}", "scan_id": scan_id, "rank": rank,
        "instrument": {"ticker": row.ticker, "yahoo_symbol": f"{row.ticker}.JK", "venue": "IDX (Indonesia Stock Exchange)",
                       "currency": "IDR", "lot_size": mkt.LOT_SIZE},
        "discovered_at": utc_stamp(now), "decided_at": utc_stamp(now), "signal_session": session,
        "verified_price": {"close": close, "session": session, "source": "Yahoo daily bar (official close)",
                           "note": "last completed session; no live quote was taken"},
        "evidence": {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in {
            "ret1": float(row.ret1), "rel1": float(row.rel1), "ret5": float(row.ret5), "ret20": float(row.ret20),
            "volr": float(row.volr), "cpos": float(row.cpos), "dd60": float(row.dd60), "ara": bool(row.ara),
            "previous": float(row.previous), "high": float(row.high), "low": low, "volume": float(row.volume),
            "adv20_value": adv}.items()},
        "thesis": (f"{family.SELECTED} fired at the close of {session}: "
                   + dict(family.FAMILY)[family.SELECTED] + ". Historically (E1 validation, 2023) such flags were "
                   "followed by a +30% repricing within 5 sessions more often than matched names."),
        "prediction": {"statement": f"max close over the next {p.horizon_sessions} sessions >= 1.30 x {close:g}",
                       "falsified_if": f"no close in the next {p.horizon_sessions} sessions reaches {close * 1.3:g}",
                       "historical_frequency": precision,
                       "note": "an empirical frequency from the validation period, not a calibrated probability"},
        "decision": decision, "reason": why,
        "plan": {
            "entry_trigger": f"paper buy at the official close of {expiry} if that close is <= Rp{chase:g} (chase limit) "
                             f"and > Rp{stop:g}, the name traded, and the close is not locked at ARA",
            "max_chase_price": chase, "invalidation": stop,
            "invalidation_rule": "exit at the first close at or below the invalidation level",
            "exit": f"close of the {p.horizon_sessions}th session after entry, or invalidation; a sale rolls while "
                    f"locked at ARB",
            "sizing_formula": ("shares = floor(min(R x equity / (entry - stop + entry x fees), min(20% x equity, "
                               "10% x 20-session median value) / entry) / 100) x 100"),
            "scenarios": scenarios, "equity_assumption_idr": p.equity_idr,
            "equity_note": "hypothetical; the real risk budget is unknown, so sizes are labelled scenarios",
            "horizon_sessions": p.horizon_sessions, "expiry": f"close of {expiry}; unfilled by then = expired",
            "liquidity": {"adv20_value_idr": adv, "position_cap_idr": cap_value},
            "catalyst": "none identified: a tape-only detector (no news or filing was read)",
            "would_change_decision": ["the next session opens locked at ARA (no sellers): unfillable",
                                      "a suspension or UMA notice from IDX before the entry close",
                                      "news of a rights issue or dilutive placement"],
        } if decision != "NOT EXECUTABLE" else {"reason": why, "horizon_sessions": p.horizon_sessions},
        "policy": {"policy_id": POLICY_ID, "sha256": policy_sha()},
        "detector": detector_identity(),
    }


# ---------------------------------------------------------------------------------- score
def score(decision: dict, m: Market) -> dict | None:
    """Score one decision on bars that now cover its window, or None if the window is still open."""
    p = POLICY
    tickers = list(m.tickers)
    t = decision["instrument"]["ticker"]
    if t not in tickers:
        return None
    n = tickers.index(t)
    dates = m.dates.astype(str)
    if decision["signal_session"] not in dates:
        return None
    d = int(np.flatnonzero(dates == decision["signal_session"])[0])
    if d + 1 + p.horizon_sessions >= len(dates):
        return None
    close = m.close[n]
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(m.present[n] & (m.prev[n] > 0) & (close > 0), np.log(close / m.prev[n]), 0.0)
    level = np.exp(np.cumsum(logret))
    fwd = level[d + 1: d + 1 + p.horizon_sessions] / level[d] - 1
    r5max = float(np.nanmax(fwd))
    discovery = {"r5max": r5max, **{f"E{int(x * 100)}": r5max >= x for x in (0.3, 0.5, 1.0)},
                 "peak_session": str(m.dates[d + 1 + int(np.nanargmax(fwd))])}
    e = d + 1
    entry_close = float(close[e])
    plan = decision.get("plan", {})
    fillable = bool(m.tradeable[n, e] and not m.lock_up[n, e])
    in_band = "max_chase_price" in plan and plan["invalidation"] < entry_close <= plan["max_chase_price"]
    stop = plan.get("invalidation")
    exit_idx, exit_reason = None, None
    path = []
    if fillable and in_band:
        for k in range(e + 1, min(e + 1 + p.horizon_sessions, len(dates))):
            path.append(float(level[k] / level[e] - 1))
            sellable = m.tradeable[n, k] and not m.lock_down[n, k]
            if sellable and close[k] <= stop:
                exit_idx, exit_reason = k, "invalidation"
                break
            if k == e + p.horizon_sessions and sellable:
                exit_idx, exit_reason = k, "horizon"
        if exit_idx is None:
            return None  # still held (or rolling on an ARB lock)
    trade = None
    if exit_idx is not None:
        gross = float(level[exit_idx] / level[e] - 1)
        net = (1 + gross) * (1 - p.fee_sell) / (1 + p.fee_buy) - 1
        trade = {"entry_session": str(m.dates[e]), "entry_close": entry_close, "exit_session": str(m.dates[exit_idx]),
                 "exit_reason": exit_reason, "net_return": net, "mfe": max(path), "mae": min(path)}
    executed = decision["decision"] == "BUY ON TRIGGER" and trade is not None
    would_have = trade["net_return"] if trade else None
    if decision["decision"] == "BUY ON TRIGGER":
        verdict = ("NOT FILLED" if trade is None else ("PROFIT" if trade["net_return"] > 0 else "LOSS"))
    else:
        verdict = ("CORRECT REJECTION" if would_have is None or would_have <= 0 else "MISSED GAIN (rejected, plan would have profited)")
    return {"type": "OUTCOME", "decision_id": decision["decision_id"], "scored_at": utc_stamp(),
            "discovery": discovery, "execution": {"fillable_at_trigger": fillable, "within_chase_band": bool(in_band),
                                                    "paper_trade": trade, "executed": executed},
            "decision_verdict": verdict}


def commit_and_push(paths: list[Path], message: str, trailer: str = "") -> str:
    def git(*args):
        return subprocess.run(["git", *args], cwd=PKG_ROOT, check=True, capture_output=True, text=True).stdout

    git("add", "--", *[str(p) for p in paths])
    git("commit", "-q", "-m", message + (f"\n\n{trailer}" if trailer else ""), "--", *[str(p) for p in paths])
    head = git("rev-parse", "HEAD").strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    try:
        git("push", "-q", "origin", branch)
    except subprocess.CalledProcessError as exc:  # recorded, not fatal: the receipt simply comes later
        print(f"warning: push failed: {exc.stderr.strip()}", file=sys.stderr)
    return head


# ---------------------------------------------------------------------------------- glue
def active_tickers() -> list[str]:
    import csv

    from .panel import load

    df, _, _ = load()
    last = df.groupby("ticker")["date"].max()
    tickers = set(last[last == df["date"].max()].index)
    with (PKG_ROOT / "data" / "universe" / "extra_tickers.csv").open(newline="", encoding="utf-8") as fh:
        tickers |= {r["ticker"].strip().upper() for r in csv.DictReader(fh) if r["ticker"].strip()}
    return sorted(tickers)


def validation_evidence() -> dict | None:
    """The E30 block of the frozen detector's validation result, if it exists and matches."""
    path = PKG_ROOT / "research" / "E1" / "validation" / "result.json"
    if not path.exists():
        return None
    res = json.loads(path.read_text(encoding="utf-8"))
    if res.get("rule") != family.SELECTED:
        return None
    return {"source": rel(path), "source_sha256": sha256_file(path), "rule": res["rule"],
            **{k: res["E30"].get(k) for k in ("precision", "precision_lo95", "precision_hi95", "base_rate",
                                               "lift_vs_base", "lift_vs_matched_random", "p_one_sided_vs_matched")}}


def record_scan(out: dict, timestamper=None) -> list[Path]:
    scan_dir = SCANS / out["scan"]["scan_id"]
    scan_dir.mkdir(parents=True, exist_ok=False)
    feat_path = scan_dir / "features.csv"
    with feat_path.open("x", encoding="utf-8", newline="") as fh:
        out["features"].to_csv(fh, index=False, float_format="%.6g", lineterminator="\n")
    out["scan"]["features_file"] = rel(feat_path)
    out["scan"]["features_sha256"] = sha256_file(feat_path)
    stored = append([out["scan"], *out["decisions"]], timestamper=timestamper)
    tokens = [TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [feat_path, LEDGER, *[t for t in tokens if t.exists()]]


def score_pending(manifest: Path, timestamper=None) -> tuple[list[Path], list[dict]]:
    lines = ledger_lines()
    done = {r["decision_id"] for r in lines if r["type"] == "OUTCOME"}
    pending = [r for r in lines if r["type"] == "DECISION" and r["decision_id"] not in done]
    if not pending:
        return [], []
    df, data = load_recent(manifest)
    m = _market(df)
    outcomes = [o for o in (score(r, m) for r in pending) if o is not None]
    for o in outcomes:
        o["data"] = {"manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"]}
    if not outcomes:
        return [], []
    stored = append(outcomes, timestamper=timestamper)
    tokens = [TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [LEDGER, *[t for t in tokens if t.exists()]], outcomes


def verify_all() -> list[str]:
    problems = verify_chain()
    for rec in ledger_lines():
        if rec["type"] == "SCAN" and rec.get("features_file"):
            path = PKG_ROOT / rec["features_file"]
            if not path.exists() or sha256_file(path) != rec["features_sha256"]:
                problems.append(f"{rec['scan_id']}: features file missing or changed")
    sys.path.insert(0, str(PKG_ROOT.parent / "kod-machine"))
    try:
        from kod.timestamp import RFC3161Timestamper

        checker = RFC3161Timestamper()
        for token in sorted(TOKENS.glob("*.tsr")) if TOKENS.exists() else []:
            record_hash, authority, _ = token.name.split(".")
            try:
                checker.verify(authority, token.read_bytes(), record_hash.encode())
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{token.name}: {exc}")
    except ImportError:
        problems.append("kod-machine timestamp module not found; tokens not checked")
    return problems

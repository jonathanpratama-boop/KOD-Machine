"""Speculation Register v1 (research/SPECULATION_REGISTER_v1/PROTOCOL.md). Paper only, no orders.

Speculative design applied to the paper ledger: for every candidate the frozen detectors produce, seal,
before the entry, a set of speculations about its future, then grade them when the future arrives.

  SPECULATION_SET  one per DECISION, sealed before the entry cutoff: the cone (dated, falsifiable
                   statements with the prior the frozen evidence gives each), the frozen plan (BASE5),
                   five matched twins drawn from the same scan, a tag. Binds the decision's and the
                   scan's record hashes and the scan's frozen features file.
  RESOLUTION       one per (set, window) once the bars cover the window: BASE5 carries the candidate's
                   trade under the frozen plan, each twin's trade under the same plan, the paired
                   difference and the five-session statements; PATH20 carries the twenty-session path
                   statements for the candidate and the twins. Each statement has its Brier term.

The register carries no alternative plan: the owner retired the crypto and US entries (handoff/decisions,
2026-10-17 and 2026-10-22) and allowed descriptive logging only. The records live in paper/speculations.jsonl,
a hash chain of the ledger's kind (paper.append), stamped by the same RFC 3161 authorities and pushed.
Nothing is ever edited; a correction is a new RESOLUTION whose `revises` names the earlier one. The
register never changes a paper decision or the policy.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import paper
from .multiple_testing import holm
from .profiles import PROFILES
from .provenance import PKG_ROOT, sha256_file, utc_stamp

PROTOCOL_DIR = PKG_ROOT / "research" / "SPECULATION_REGISTER_v1"
PROTOCOL_JSON = PROTOCOL_DIR / "protocol.json"
SPEC_LEDGER = paper.PAPER / "speculations.jsonl"
REPORT = paper.PAPER / "SPECULATIONS.md"
REGISTER_VERSION = "spec-register-v1"
RESOLVER_ID = "spec-resolve-v1"
WINDOW_ORDER = ("BASE5", "PATH20")
PLAN = "BASE5"
TWINS = 5
MIN_POOL = 5
RUNNING_MIN_N = 20
DATA_END_GRACE = 10  # sessions the market must run past a target before a vanished name is sold at its last close
REDENOMINATION = 10.0  # crypto: a close/previous ratio beyond this (or its inverse) is a redenomination, not a move
RECONCILE_RTOL = paper.RECONCILE_RTOL
# Trade dispersion of the 2023 validation runs (results/runs/<id>/trades.csv.gz, scored trades), used only to
# project the sessions a look needs until the register has ten resolved sessions of its own.
VALIDATION_SD = {"IDX": (0.1967, "20261009T050040Z_MOONSHOT_E1_D1_v1.1"),
                 "US": (0.3429, "20261008T115656Z_MOONSHOT_E2_US_D1_v1"),
                 "CRYPTO": (0.3486, "20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1")}


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8")), sha256_file(PROTOCOL_JSON)


def windows() -> dict:
    return protocol()[0]["windows"]


def spec_lines(path: Path | None = None) -> list[dict]:
    return paper.ledger_lines(SPEC_LEDGER if path is None else path)


def window_length(w: dict) -> int:
    """Sessions after the signal the bars must cover before the window can resolve (rolls aside)."""
    if w["kind"] == "path":
        return int(w["horizon"])
    return int(w["entry_window"]) + int(w["holding_sessions"])


# ------------------------------------------------------------------------------------- sealing
def entry_cutoff(market: str, signal_session: str) -> datetime:
    """The moment after which a set for this signal would no longer be a speculation."""
    nxt = paper._next_session(signal_session, market)
    hour, minute = {"IDX": (1, 45), "US": (13, 30), "CRYPTO": (2, 0)}[market]
    return datetime.fromisoformat(nxt).replace(hour=hour, minute=minute, tzinfo=timezone.utc)


def scan_features(scan: dict) -> pd.DataFrame:
    path = PKG_ROOT / scan["features_file"]
    return pd.read_csv(path, dtype={"ticker": str}, keep_default_na=False, na_values=[""],
                       compression="gzip" if path.suffix == ".gz" else None)


def _bucket(values: pd.Series, n: int) -> np.ndarray:
    pct = pd.to_numeric(values, errors="coerce").rank(pct=True).to_numpy()
    return np.where(np.isfinite(pct), np.minimum(np.ceil(pct * n) - 1, n - 1), -1).astype(int)


def twin_seed(decision_id: str) -> int:
    return int(hashlib.sha256(f"KOD-SPEC-REGISTER-v1:{decision_id}".encode()).hexdigest()[:8], 16)


def draw_twins(feats: pd.DataFrame, candidate: str, candidates: list[str], selected: str, market: str, seed: int,
               k: int = TWINS, min_pool: int = MIN_POOL) -> tuple[list[dict], str]:
    """Five matched names from the scan's own features (protocol: Twins). Returns (twins, match level)."""
    prof = PROFILES[market]
    f = feats.copy()
    for col in ("fresh", "eligible", selected):
        f[col] = f[col].astype(str).str.lower().isin(("true", "1"))
    close = pd.to_numeric(f["close"], errors="coerce")
    ok = f["fresh"] & f["eligible"] & ~f[selected] & ~f["ticker"].isin(candidates) & (close > 0)
    if market == "IDX":
        ok &= close >= 50
    pool = f[ok | (f["ticker"] == candidate)].copy()
    if candidate not in set(pool["ticker"]):
        raise ValueError(f"{candidate} is not in the scan's features")
    pool["band"] = prof.band(pd.to_numeric(pool["close"], errors="coerce").to_numpy(float))
    pool["liq"] = _bucket(pool["adv20_value"], 5)
    pool["mom"] = _bucket(pool["ret20"], 3)
    pool["dd"] = _bucket(pool["dd60"], 3)
    me = pool[pool["ticker"] == candidate].iloc[0]
    others = pool[pool["ticker"] != candidate]
    levels = (("band", "liq", "mom", "dd"), ("band", "liq", "mom"), ("band", "liq"), ("band",), ())
    chosen, level_name = others, "same session only"
    for keys in levels:
        sub = others
        for key in keys:
            sub = sub[sub[key] == me[key]]
        if len(sub) >= min_pool or not keys:
            chosen, level_name = sub, ("+".join(keys) if keys else "same session only")
            break
    names = sorted(chosen["ticker"].tolist())
    rng = np.random.default_rng(seed)
    picked = list(rng.choice(names, size=min(k, len(names)), replace=False)) if names else []
    rows = chosen.set_index("ticker").loc[picked]
    twins = []
    for t, r in rows.iterrows():
        twins.append({"ticker": t, "close": float(r["close"]), "previous": _num(r["previous"]),
                      "adv20_value": _num(r["adv20_value"]), "ret20": _num(r["ret20"]), "dd60": _num(r["dd60"]),
                      "volr": _num(r["volr"]), "band": int(r["band"]), "liquidity_quintile": int(r["liq"]),
                      "momentum_tercile": int(r["mom"]), "drawdown_tercile": int(r["dd"])})
    return twins, level_name


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def tag(market: str, scan: dict, ledger: list[dict]) -> dict:
    sel = scan["detector"]["selected"]
    earlier = [r for r in ledger if r["type"] == "SCAN" and r.get("market", "IDX") == market
               and r["session"] < scan["session"] and r["detector"]["selected"] == sel]
    counts = [len(r["flags"].get(sel, [])) for r in sorted(earlier, key=lambda r: r["session"])[-20:]]
    today = len(scan["flags"].get(sel, []))
    median = float(np.median(counts)) if counts else None
    return {"flags_today": today, "earlier_scans": len(counts), "trailing_median": median,
            "hot_day": (today > median) if len(counts) >= 10 else None}


def running_prior(market: str, statement_id: str, specs: list[dict]) -> tuple[float, int]:
    outcomes = [c["outcome"] for r in specs if r["type"] == "RESOLUTION" and r["market"] == market
                for c in r.get("cone", []) if c["id"] == statement_id and c.get("outcome") is not None]
    if len(outcomes) < RUNNING_MIN_N:
        return 0.5, len(outcomes)
    return float(np.mean(outcomes)), len(outcomes)


def pending_decisions(market: str, now: datetime, ledger: list[dict] | None = None,
                      specs: list[dict] | None = None) -> list[tuple[dict, dict]]:
    """Decisions of the market's protocol detector with no set yet whose entry cutoff is still ahead."""
    proto, _ = protocol()
    ledger = paper.ledger_lines() if ledger is None else ledger
    specs = spec_lines() if specs is None else specs
    sealed = {r["decision_id"] for r in specs if r["type"] == "SPECULATION_SET"}
    scans = {r["scan_id"]: r for r in ledger if r["type"] == "SCAN"}
    out = []
    for r in ledger:
        if r["type"] != "DECISION" or r.get("market", "IDX") != market or r["decision_id"] in sealed:
            continue
        if r["decision"] in proto["markets"][market]["excluded_decisions"]:
            continue
        if r["detector"]["selected"] != proto["markets"][market]["selected"]:
            continue
        if now >= entry_cutoff(market, r["signal_session"]):
            continue
        out.append((r, scans[r["scan_id"]]))
    return out


def build_set(decision: dict, scan: dict, feats: pd.DataFrame, ledger: list[dict], specs: list[dict],
              now: datetime, quotes: dict | None = None) -> dict:
    proto, proto_sha = protocol()
    market = decision.get("market", "IDX")
    sel = scan["detector"]["selected"]
    ticker = decision["instrument"]["ticker"]
    cutoff = entry_cutoff(market, decision["signal_session"])
    if now >= cutoff:
        raise ValueError(f"{decision['decision_id']}: the entry cutoff {utc_stamp(cutoff)} has passed; not a speculation")
    row = feats[feats["ticker"] == ticker]
    if row.empty:
        raise ValueError(f"{ticker} is not in {scan['features_file']}")
    row = row.iloc[0]
    recorded = float(decision["verified_price"]["close"])
    if not math.isclose(float(row["close"]), recorded, rel_tol=1e-6):
        raise ValueError(f"{ticker}: features close {row['close']} differs from the decision's {recorded}")
    twins, level = draw_twins(feats, ticker, list(scan["candidates_ranked"]), sel, market, twin_seed(decision["decision_id"]))
    quotes = quotes or {}
    if market == "CRYPTO":
        for tw in twins:
            q = quotes.get(tw["ticker"])
            tw["quote"] = float(q[0]) if q else None
            tw["quote_time"] = q[1] if q else None
    cone = []
    for st in proto["cone"]:
        if st["prior"] == "running":
            prior, n = running_prior(market, st["id"], specs)
            source = f"register running base rate (n {n}; 0.5 below {RUNNING_MIN_N})"
        else:
            prior, source = float(st["prior"][market]), st["prior_source"]
        cone.append({"id": st["id"], "statement": st["statement"], "prior": prior, "prior_source": source,
                     "resolves_with": st["resolves_with"]})
    q = quotes.get(ticker) if market == "CRYPTO" else None
    entry = {"IDX": {"basis": "close", "session": paper._next_session(decision["signal_session"], "IDX"),
                     "text": "the next session's closing auction, if traded and not locked at ARA"},
             "US": {"basis": "open", "session": paper._next_session(decision["signal_session"], "US"),
                    "text": "the next session's opening print"},
             "CRYPTO": {"basis": "quote", "session": paper._next_session(decision["signal_session"], "CRYPTO"),
                        "quote": float(q[0]) if q else None, "quote_time": q[1] if q else None,
                        "quote_source": "Binance spot ticker price at sealing time",
                        "decision_quote": decision["verified_price"].get("quote"),
                        "text": "the Binance spot quote taken at sealing time (the harness used the next day's open)"}}[market]
    return {
        "type": "SPECULATION_SET", "register": REGISTER_VERSION, "market": market,
        "set_id": f"SPEC-{decision['decision_id']}", "decision_id": decision["decision_id"],
        "decision_record_hash": decision["record_hash"], "decision": decision["decision"],
        "scan_id": scan["scan_id"], "scan_record_hash": scan["record_hash"],
        "features_file": scan["features_file"], "features_sha256": scan["features_sha256"],
        "ticker": ticker, "signal_session": decision["signal_session"], "sealed_at": utc_stamp(now),
        "entry_cutoff": utc_stamp(cutoff), "entry": entry,
        "signal": {k: _num(row[k]) for k in ("close", "previous", "high", "low", "volume", "adv20_value", "ret1",
                                             "ret5", "ret20", "volr", "cpos", "dd60")},
        "twins": twins, "twins_match_level": level, "twins_seed": twin_seed(decision["decision_id"]),
        "tag": tag(market, scan, ledger),
        "cone": cone, "windows": list(WINDOW_ORDER), "plan": PLAN,
        "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
        "detector": decision["detector"], "policy": decision.get("policy"),
    }


def seal(market: str, now: datetime | None = None, timestamper=None, quotes=None) -> tuple[list[Path], list[dict]]:
    """Seal a set for every pending decision of the market. Returns (files written, sets)."""
    now = now or datetime.now(timezone.utc)
    ledger, specs = paper.ledger_lines(), spec_lines()
    pending = pending_decisions(market, now, ledger, specs)
    if not pending:
        return [], []
    feats_cache = {}
    for _, scan in pending:
        feats_cache.setdefault(scan["scan_id"], scan_features(scan))
    live = {}
    if market == "CRYPTO" and quotes is not None:
        names = set()
        for decision, scan in pending:
            tw, _ = draw_twins(feats_cache[scan["scan_id"]], decision["instrument"]["ticker"],
                               list(scan["candidates_ranked"]), scan["detector"]["selected"], market,
                               twin_seed(decision["decision_id"]))
            names |= {decision["instrument"]["ticker"], *(t["ticker"] for t in tw)}
        live = quotes(sorted(names))
    records = [build_set(decision, scan, feats_cache[scan["scan_id"]], ledger, specs, now, live)
               for decision, scan in pending]
    stored = paper.append(records, path=SPEC_LEDGER, timestamper=timestamper)
    tokens = [paper.TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [SPEC_LEDGER, *[t for t in tokens if t.exists()]], stored


# ---------------------------------------------------------------------------------- simulation
def _level(m, n: int) -> np.ndarray:
    close, prev = m.close[n], m.prev[n]
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(m.present[n] & (prev > 0) & (close > 0), np.log(close / prev), 0.0)
    return np.exp(np.cumsum(logret))


def redenominated(m, n: int, d: int, horizon: int, market: str) -> bool:
    """Crypto only: a close/previous ratio beyond REDENOMINATION (or its inverse) in d+1..d+horizon."""
    if market != "CRYPTO":
        return False
    hi = min(d + horizon, m.shape[1] - 1)
    close, prev, present = m.close[n, d + 1: hi + 1], m.prev[n, d + 1: hi + 1], m.present[n, d + 1: hi + 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(present & (prev > 0), close / prev, 1.0)
    return bool(np.any((ratio > REDENOMINATION) | (ratio < 1 / REDENOMINATION)))


def simulate(m, n: int, d: int, plan: dict, market: str, quote: float | None = None, unit_factor=None) -> dict | None:
    """One name (row n) under the frozen plan from signal session d. None while the window is still open (a
    roll past the bars); otherwise {"status": TRADED | NOT_FILLABLE | REDENOMINATION, "trade": {...} | None}."""
    prof = PROFILES[market]
    last = m.shape[1] - 1
    close, present, volume = m.close[n], m.present[n], m.volume[n]
    level = _level(m, n)
    dates = m.dates.astype(str)
    hold = int(plan["holding_sessions"])
    e = d + int(plan["entry_window"])
    if e > last:
        return None
    if redenominated(m, n, d, e - d + hold, market):
        return {"status": "REDENOMINATION", "trade": None,
                "reason": f"a close/previous ratio beyond {REDENOMINATION:g}x inside the window: a redenomination, not a move"}

    def sellable(k):
        if market == "IDX":
            return bool(m.tradeable[n, k] and not m.lock_down[n, k])
        return bool(present[k] and close[k] > 0)

    def factor(k):
        return float(unit_factor(k)) if unit_factor else 1.0

    if market == "IDX":
        ok, price, basis = bool(m.tradeable[n, e] and not m.lock_up[n, e]), float(close[e]), "close"
    elif market == "US":
        o = float(m.open[n, e])
        ok = bool(present[e] and np.isfinite(o) and o > 0 and np.nan_to_num(volume[e]) > 0)
        price, basis = o, "open"
    else:
        ok, price, basis = bool(quote is not None and quote > 0), float(quote or 0), "quote"
    if not ok:
        return {"status": "NOT_FILLABLE", "trade": None,
                "reason": {"IDX": "not traded or locked at ARA on the entry session",
                           "US": "no opening print on the entry session",
                           "CRYPTO": "no quote at sealing time"}[market]}
    target, reason = e + hold, "horizon"
    x = next((k for k in range(target, last + 1) if sellable(k)), None)
    if x is None:
        present_idx = np.flatnonzero(present)
        traded_idx = np.flatnonzero(m.tradeable[n])
        if len(present_idx) and present_idx[-1] < target and last >= target + DATA_END_GRACE and len(traded_idx) \
                and traded_idx[-1] >= e:
            x, reason = int(traded_idx[-1]), "data end"
        else:
            return None
    gross = float(level[x] / level[e] - 1) if market == "IDX" else float(close[x] / price - 1)
    if market == "IDX":
        fee_in, fee_out = paper.POLICY.fee_buy, paper.POLICY.fee_sell
    else:
        entry_traded = price if basis == "quote" else price * factor(e)
        exit_traded = float(close[x]) * factor(x)
        fee_in = prof.fee_buy + float(prof.per_side_cost(np.array([entry_traded]))[0])
        fee_out = prof.fee_sell + float(prof.per_side_cost(np.array([exit_traded]))[0])
    net = (1 + gross) * (1 - fee_out) / (1 + fee_in) - 1
    # The path of closes after the entry, as paper-score records it: from the session after a closing-auction
    # entry (IDX), from the entry session itself after an opening or quote entry (its close comes later).
    if market == "IDX":
        path = [float(level[k] / level[e] - 1) for k in range(e + 1, x + 1) if present[k]]
    else:
        path = [float(close[k] / price - 1) for k in range(e, x + 1) if present[k] and close[k] > 0]
    return {"status": "TRADED", "trade": {
        "entry_session": str(dates[e]), "entry_price": price, "entry_basis": basis, "entry_lag_sessions": e - d,
        "exit_session": str(dates[x]), "exit_reason": reason + (f" (rolled {x - target})" if x > target and reason != "data end" else ""),
        "gross_return": gross, "net_return": float(net), "cost_in": float(fee_in), "cost_out": float(fee_out),
        "mfe": max(path) if path else 0.0, "mae": min(path) if path else 0.0, "sessions_held": x - e}}


def path_statement(m, n: int, d: int, horizon: int, multiple: float) -> bool | None:
    level = _level(m, n)
    hi = min(d + horizon, m.shape[1] - 1)
    if hi < d + horizon:
        return None
    seg = level[d + 1: hi + 1][m.present[n, d + 1: hi + 1]]
    return bool(len(seg) and seg.max() / level[d] >= multiple)


def statement_outcome(sid: str, m, n: int, d: int, result: dict | None, twin_nets: list[float]) -> bool | None:
    """One statement for one name. `result` is the name's BASE5 simulation (None for a path-only name)."""
    net = (result or {}).get("trade", {}) if result else {}
    net = net.get("net_return") if net else None
    if sid == "RUN30_5":
        return path_statement(m, n, d, 5, 1.30)
    if sid == "RUN30_20":
        return path_statement(m, n, d, 20, 1.30)
    if sid == "DOUBLE_20":
        return path_statement(m, n, d, 20, 2.00)
    if sid == "FADE10_5":
        return None if net is None else bool(net <= -0.10)
    if sid == "GAIN0_5":
        return None if net is None else bool(net > 0)
    if sid == "BEATS_TWINS_5":
        return None if (net is None or not twin_nets) else bool(net > float(np.median(twin_nets)))
    return None


def cone_outcomes(statements: list[dict], window_id: str, m, d: int, candidate: tuple[int, dict | None],
                  twins: list[tuple[int, dict | None]]) -> list[dict]:
    """Grade the statements of `window_id` for the candidate (row, BASE5 result) and each twin (row, result)."""
    n, cres = candidate
    twin_nets = [r["trade"]["net_return"] for _, r in twins if r and r.get("trade")]
    out = []
    for st in statements:
        if st["resolves_with"] != window_id:
            continue
        o = statement_outcome(st["id"], m, n, d, cres, twin_nets)
        rec = {"id": st["id"], "prior": st["prior"], "outcome": o,
               "brier": None if o is None else float((st["prior"] - float(o)) ** 2)}
        if o is None:
            rec["note"] = "not graded: no position (or no twin traded)"
        tw = []
        for tn, tres in twins:
            others = [r["trade"]["net_return"] for k, r in twins if k != tn and r and r.get("trade")]
            tw.append(statement_outcome(st["id"], m, tn, d, tres, others))
        known = [x for x in tw if x is not None]
        rec["twins_rate"] = float(np.mean(known)) if known else None
        rec["twins_graded"] = len(known)
        out.append(rec)
    return out


# ---------------------------------------------------------------------------------- resolution
def due(market: str, today: str | None = None, specs: list[dict] | None = None) -> list[tuple[str, str]]:
    """(set_id, window) pairs whose window can have ended by `today` (calendar check, no data pull)."""
    specs = spec_lines() if specs is None else specs
    today = np.datetime64(today or datetime.now(timezone.utc).date().isoformat(), "D")
    done = {(r["set_id"], r["window"]) for r in specs if r["type"] == "RESOLUTION"}
    out = []
    for s in specs:
        if s["type"] != "SPECULATION_SET" or s["market"] != market:
            continue
        sig = np.datetime64(s["signal_session"], "D")
        elapsed = int((today - sig).astype(int)) if market == "CRYPTO" else int(np.busday_count(sig, today))
        for wid, w in windows().items():
            if (s["set_id"], wid) in done:
                continue
            if elapsed >= window_length(w) + (1 if market == "CRYPTO" else 0):
                out.append((s["set_id"], wid))
    return out


def _units_for(name: str, signal_session: str, recorded_close: float, m, events: pd.DataFrame, verify, market: str):
    """((row, signal index, unit factor) or None, units record, reason). Reconciles the recorded close as
    paper-score does: units from split records (SEC-corroborated for US), never from a price ratio."""
    tickers = list(m.tickers)
    if name not in tickers:
        return None, None, "no bars for the name in the scoring pull"
    n = tickers.index(name)
    dates = m.dates.astype(str)
    if signal_session not in dates:
        return None, None, "the signal session is not in the scoring bars"
    d = int(np.flatnonzero(dates == signal_session)[0])
    shim = {"market": market, "signal_session": signal_session, "instrument": {"ticker": name}}
    ev = events[events["ticker"] == name] if len(events) else events
    units, reason, evidence = paper.scoring_units(shim, m, ev, verify)
    if units is None:
        return None, None, reason
    from .price_units import split_conversion_factor

    def uf(k):
        return split_conversion_factor(str(dates[k]), units["actions"], units["adjustment_reference"],
                                       coverage_complete=units.get("coverage_complete", False))

    cd = float(m.close[n, d])
    if not (recorded_close > 0 and np.isfinite(cd) and cd > 0 and np.isclose(cd * uf(d), recorded_close, rtol=RECONCILE_RTOL)):
        return None, None, f"recorded signal close {recorded_close:g} does not reconcile with the scoring bars (rtol {RECONCILE_RTOL})"
    return (n, d, uf if market != "CRYPTO" else None), {"actions": units["actions"], "evidence": evidence,
                                                         "convention": units["convention"]}, None


def resolve_set(s: dict, window_id: str, m, events: pd.DataFrame, verify=None) -> dict | None:
    """One RESOLUTION for (set, window), or None while the window is still open."""
    w = windows()[window_id]
    market = s["market"]
    dates = m.dates.astype(str)
    if s["signal_session"] not in dates:
        return None
    d0 = int(np.flatnonzero(dates == s["signal_session"])[0])
    if d0 + window_length(w) > m.shape[1] - 1:
        return None
    base = {"type": "RESOLUTION", "register": REGISTER_VERSION, "resolver": RESOLVER_ID, "market": market,
            "set_id": s["set_id"], "window": window_id, "ticker": s["ticker"], "signal_session": s["signal_session"],
            "resolved_at": utc_stamp(), "preprocessing": paper.SCORING_PREPROCESSING[market], "protocol": s["protocol"]}
    located, units, reason = _units_for(s["ticker"], s["signal_session"], float(s["signal"]["close"]), m, events, verify, market)
    if located is None:
        return {**base, "status": "UNRESOLVABLE", "reason": reason}
    n, d, uf = located
    plan = windows()[PLAN]
    if w["kind"] == "path":
        if redenominated(m, n, d, int(w["horizon"]), market):
            return {**base, "status": "UNRESOLVABLE", "reason": "redenomination inside the window"}
        cand = None
    else:
        cand = simulate(m, n, d, plan, market, quote=s["entry"].get("quote") if market == "CRYPTO" else None, unit_factor=uf)
        if cand is None:
            return None
        if cand["status"] == "REDENOMINATION":
            return {**base, "status": "UNRESOLVABLE", "reason": cand["reason"]}
    twins, graded = [], []
    for tw in s["twins"]:
        loc, tunits, treason = _units_for(tw["ticker"], s["signal_session"], float(tw["close"]), m, events, verify, market)
        if loc is None:
            twins.append({"ticker": tw["ticker"], "status": "DROPPED", "reason": treason, "trade": None})
            continue
        tn, td, tuf = loc
        if w["kind"] == "path":
            if redenominated(m, tn, td, int(w["horizon"]), market):
                twins.append({"ticker": tw["ticker"], "status": "DROPPED", "reason": "redenomination inside the window", "trade": None})
                continue
            twins.append({"ticker": tw["ticker"], "status": "PATH", "trade": None})
            graded.append((tn, None))
            continue
        res = simulate(m, tn, td, plan, market, quote=tw.get("quote") if market == "CRYPTO" else None, unit_factor=tuf)
        if res is None:
            return None  # a twin still rolling: wait for the whole set
        if res["status"] == "REDENOMINATION":
            twins.append({"ticker": tw["ticker"], "status": "DROPPED", "reason": res["reason"], "trade": None})
            continue
        twins.append({"ticker": tw["ticker"], **res, **({"units": tunits} if tunits and tunits["actions"] else {})})
        graded.append((tn, res))
    paired = None
    if cand and cand["trade"]:
        twin_nets = [r["trade"]["net_return"] for _, r in graded if r and r.get("trade")]
        if twin_nets:
            paired = {"candidate_net": cand["trade"]["net_return"], "twins_traded": len(twin_nets),
                      "twins_mean_net": float(np.mean(twin_nets)), "twins_median_net": float(np.median(twin_nets)),
                      "diff": float(cand["trade"]["net_return"] - np.mean(twin_nets))}
    return {**base, "status": "RESOLVED",
            **({"candidate": {**cand, "units": units}} if cand is not None else {"candidate": {"status": "PATH", "units": units}}),
            "twins": twins, "paired": paired, "cone": cone_outcomes(s["cone"], window_id, m, d, (n, cand), graded)}


def resolve_pending(manifest: Path, market: str, timestamper=None, verify=None) -> tuple[list[Path], list[dict]]:
    specs = spec_lines()
    todo = due(market, specs=specs)
    if not todo:
        return [], []
    sets = {r["set_id"]: r for r in specs if r["type"] == "SPECULATION_SET"}
    df, data = paper.load_recent(manifest, market, purpose="scoring")
    m = paper._market(df, market)
    events = pd.DataFrame()
    if market in ("US", "IDX"):
        from . import us_actions

        events = us_actions.yahoo_events(manifest, market=market)
    out = []
    for set_id, wid in todo:
        rec = resolve_set(sets[set_id], wid, m, events, verify)
        if rec is None:
            continue
        rec["data"] = {"manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"]}
        out.append(rec)
    if not out:
        return [], []
    stored = paper.append(out, path=SPEC_LEDGER, timestamper=timestamper)
    tokens = [paper.TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [SPEC_LEDGER, *[t for t in tokens if t.exists()]], out


# ---------------------------------------------------------------------------------- statistics
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    max_iter, eps, fpmin = 300, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for mm in range(1, max_iter + 1):
        m2 = 2 * mm
        aa = mm * (b - mm) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + mm) * (qab + mm) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def t_sf(t: float, df: int) -> float:
    """One-sided P(T >= t) for Student's t with df degrees of freedom (stdlib only)."""
    if df < 1 or not math.isfinite(t):
        return float("nan")
    x = df / (df + t * t)
    tail = 0.5 * _betainc(df / 2.0, 0.5, x)
    return tail if t >= 0 else 1.0 - tail


def plan_statistics(resolutions: list[dict]) -> dict:
    """Per-session paired test for one market's BASE5 RESOLVED records with a paired difference."""
    paired = [r for r in resolutions if r.get("status") == "RESOLVED" and r.get("paired")]
    traded = [r for r in resolutions if r.get("status") == "RESOLVED" and (r.get("candidate") or {}).get("trade")]
    by_session = {}
    for r in paired:
        by_session.setdefault(r["signal_session"], []).append(r["paired"]["diff"])
    session_means = np.array([np.mean(v) for _, v in sorted(by_session.items())])
    n_sess = len(session_means)
    out = {"n_resolved": sum(r.get("status") == "RESOLVED" for r in resolutions),
           "n_unresolvable": sum(r.get("status") == "UNRESOLVABLE" for r in resolutions),
           "n_traded": len(traded), "n_paired": len(paired), "n_sessions": n_sess,
           "n_not_fillable": sum((r.get("candidate") or {}).get("status") == "NOT_FILLABLE" for r in resolutions),
           "mean_net": float(np.mean([r["candidate"]["trade"]["net_return"] for r in traded])) if traded else None,
           "median_net": float(np.median([r["candidate"]["trade"]["net_return"] for r in traded])) if traded else None,
           "mean_twins_net": float(np.mean([r["paired"]["twins_mean_net"] for r in paired])) if paired else None,
           "mean_diff": float(np.mean([r["paired"]["diff"] for r in paired])) if paired else None,
           "sd_diff_sets": float(np.std([r["paired"]["diff"] for r in paired], ddof=1)) if len(paired) > 1 else None,
           "sd_session": float(np.std(session_means, ddof=1)) if n_sess > 1 else None,
           "t": None, "p_one_sided": None}
    if n_sess >= 2 and out["sd_session"] and out["sd_session"] > 0:
        t = float(session_means.mean() / (out["sd_session"] / math.sqrt(n_sess)))
        out["t"], out["p_one_sided"] = t, float(t_sf(t, n_sess - 1))
    return out


def look_status(stats: dict, rule: dict) -> dict:
    looks = rule["looks"]
    reached = [n for n in looks if stats["n_paired"] >= n and stats["n_sessions"] >= rule["min_sessions"]]
    return {"looks": looks, "reached": reached[-1] if reached else None,
            "next": next((n for n in looks if n not in reached), None)}


def statistics(specs: list[dict] | None = None, ledger: list[dict] | None = None) -> dict:
    proto, proto_sha = protocol()
    specs = spec_lines() if specs is None else specs
    ledger = paper.ledger_lines() if ledger is None else ledger
    rule = proto["decision_rule"]
    sets = [r for r in specs if r["type"] == "SPECULATION_SET"]
    res = [r for r in specs if r["type"] == "RESOLUTION"]
    markets = {}
    for mk in ("IDX", "US", "CRYPTO"):
        msets = [s for s in sets if s["market"] == mk]
        mres = [r for r in res if r["market"] == mk]
        sessions = sorted({s["signal_session"] for s in msets})
        first = sessions[0] if sessions else None
        scans_since = [r for r in ledger if r["type"] == "SCAN" and r.get("market", "IDX") == mk
                       and first is not None and r["session"] >= first]
        rate = (len(msets) / len(scans_since)) if scans_since else None
        st = plan_statistics([r for r in mres if r["window"] == PLAN])
        st["look"] = look_status(st, rule)
        st["p_holm"] = float(holm([st["p_one_sided"]])[0]) if st["p_one_sided"] is not None else None
        at_look = st["look"]["reached"] is not None
        eligible = (at_look and st["p_holm"] is not None and st["p_holm"] < 0.05 and st["t"] is not None
                    and st["t"] >= 3.0 and st["mean_net"] is not None and st["mean_net"] > 0)
        if not at_look:
            st["verdict"] = "accumulating (no look reached)"
        elif eligible:
            st["verdict"] = f"ELIGIBLE FOR OWNER REVIEW at the n>={st['look']['reached']} look"
        elif st["look"]["reached"] >= rule["looks"][-1]:
            st["verdict"] = "FAIL at the final look"
        else:
            st["verdict"] = f"not eligible at the n>={st['look']['reached']} look; continues"
        sd_v, run_v = VALIDATION_SD[mk]
        sets_per_session = (len(msets) / len(sessions)) if sessions else None
        if st["n_sessions"] >= 10 and st["sd_session"]:
            sd_s, sd_src = st["sd_session"], "register per-session sd"
        elif sets_per_session:
            sd_s = sd_v * math.sqrt(2) / math.sqrt(sets_per_session)
            sd_src = f"validation trade sd {sd_v} (run {run_v}), paired, / sqrt(sets per session)"
        else:
            sd_s, sd_src = None, "no sessions yet"
        st["projection"] = {"sd_session": sd_s, "sd_source": sd_src,
                            "sessions_for_t3": ({f"{int(e * 100)}pt": int(math.ceil((3.0 * sd_s / e) ** 2)) for e in (0.02, 0.05, 0.10)}
                                                if sd_s else None),
                            "sessions_to_next_look": (None if st["look"]["next"] is None or not rate else
                                                      int(math.ceil(max(0, st["look"]["next"] - st["n_paired"]) / rate)))}
        n_path = sum(r["window"] == "PATH20" and r.get("status") == "RESOLVED" for r in mres)
        cone = {}
        for c in proto["cone"]:
            graded = [x for r in mres for x in r.get("cone", []) if x["id"] == c["id"] and x.get("outcome") is not None]
            if graded:
                outcomes = np.array([float(x["outcome"]) for x in graded])
                priors = np.array([float(x["prior"]) for x in graded])
                running = np.array([outcomes[:i].mean() if i >= RUNNING_MIN_N else 0.5 for i in range(len(outcomes))])
                tw = [x["twins_rate"] for x in graded if x.get("twins_rate") is not None]
                cone[c["id"]] = {"n": len(graded), "realised_rate": float(outcomes.mean()), "mean_prior": float(priors.mean()),
                                 "twins_rate": float(np.mean(tw)) if tw else None,
                                 "brier": float(((priors - outcomes) ** 2).mean()), "brier_uninformed": float(((0.5 - outcomes) ** 2).mean()),
                                 "brier_running": float(((running - outcomes) ** 2).mean())}
            else:
                cone[c["id"]] = {"n": 0}
        markets[mk] = {"n_sets": len(msets), "sessions": len(sessions), "first_session": first,
                       "last_session": sessions[-1] if sessions else None, "sets_per_scan": rate,
                       "twins_per_set": float(np.mean([len(s["twins"]) for s in msets])) if msets else None,
                       "plan": st, "n_path20_resolved": n_path, "cone": cone}
    return {"protocol": {"id": proto["protocol_id"], "sha256": proto_sha}, "register": REGISTER_VERSION,
            "generated_at": utc_stamp(), "n_sets": len(sets), "n_resolutions": len(res), "markets": markets}


# ---------------------------------------------------------------------------------- report
def _pct(x, digits=2):
    return "n/a" if x is None else f"{x:+.{digits}%}"


def card(s: dict) -> str:
    """One sealed set as a postcard from the future."""
    e = s["entry"]
    t = s["tag"]
    lines = [f"### {s['market']} {s['ticker']} ({s['signal_session']}) - sealed {s['sealed_at']}, cutoff {s['entry_cutoff']}",
             f"Decision `{s['decision_id']}` ({s['decision']}), bound to ledger record `{s['decision_record_hash'][:12]}`; "
             f"set `{s.get('record_hash', '')[:12]}`.",
             f"Signal close {s['signal']['close']:g} (reference {s['signal']['previous']}); entry: {e['text']}"
             + (f"; quote {e['quote']:g} at {e['quote_time']}" if e.get("quote") else "") + ".",
             f"Tag: {t['flags_today']} flags today vs trailing median {t['trailing_median']} -> hot_day = {t['hot_day']}.",
             f"Twins ({s['twins_match_level']}): " + ", ".join(f"{x['ticker']} {x['close']:g}" for x in s["twins"]) + ".",
             "", "| Statement | Prior | Resolves with |", "|---|---:|---|"]
    for c in s["cone"]:
        lines.append(f"| {c['id']}: {c['statement']} | {c['prior']:.3f} | {c['resolves_with']} |")
    lines += ["", f"Plan: {PLAN} ({windows()[PLAN]['what']}); path window PATH20.", ""]
    return "\n".join(lines)


def render(stats: dict, specs: list[dict] | None = None) -> str:
    specs = spec_lines() if specs is None else specs
    sets = [r for r in specs if r["type"] == "SPECULATION_SET"]
    res = [r for r in specs if r["type"] == "RESOLUTION"]
    w = windows()
    out = [f"# Speculation Register ({stats['protocol']['id']}, protocol sha256 {stats['protocol']['sha256'][:12]})",
           "", f"Generated {stats['generated_at']} from `paper/speculations.jsonl`: {stats['n_sets']} sets sealed, "
           f"{stats['n_resolutions']} resolutions. Paper only; no orders. The register never changes a decision and runs "
           "no variant of a retired entry.", "",
           "Windows: " + "; ".join(f"**{k}**: {v['what']}" for k, v in w.items()) + ".", ""]
    for mk, m in stats["markets"].items():
        out += [f"## {mk}: {m['n_sets']} sets over {m['sessions']} signal sessions"
                + (f" ({m['first_session']} .. {m['last_session']}, {m['sets_per_scan']:.2f} sets per scan)" if m["n_sets"] else ""), ""]
        if not m["n_sets"]:
            out += ["No set sealed yet.", ""]
            continue
        a = m["plan"]
        t_txt = "n/a" if a["t"] is None else "%.2f" % a["t"]
        p_txt = "n/a" if a["p_holm"] is None else "%.3f" % a["p_holm"]
        out += ["| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
                f"| {PLAN} | {a['n_resolved']} | {a['n_traded']} | {a['n_paired']} | {a['n_sessions']} | {_pct(a['mean_net'])} | "
                f"{_pct(a['median_net'])} | {_pct(a['mean_twins_net'])} | {_pct(a['mean_diff'])} | {t_txt} | {p_txt} | "
                f"{a['look']['reached'] or '-'} / next {a['look']['next']} | {a['verdict']} |", ""]
        p = a["projection"]
        s3 = p["sessions_for_t3"] or {}
        sd_txt = "n/a" if p["sd_session"] is None else "%.3f" % p["sd_session"]
        nxt = "n/a" if p["sessions_to_next_look"] is None else p["sessions_to_next_look"]
        out += ["Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 "
                "points per set, and sessions to the next look at the current candidate rate.", "",
                "| sd per session (source) | 2pt | 5pt | 10pt | to next look |", "|---|---:|---:|---:|---:|",
                f"| {sd_txt} ({p['sd_source']}) | {s3.get('2pt', 'n/a')} | {s3.get('5pt', 'n/a')} | {s3.get('10pt', 'n/a')} | {nxt} |", "",
                f"PATH20 windows resolved: {m['n_path20_resolved']}.", "",
                "| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |",
                "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for sid, c in m["cone"].items():
            if c["n"]:
                tw = "n/a" if c["twins_rate"] is None else "%.3f" % c["twins_rate"]
                out.append(f"| {sid} | {c['n']} | {c['realised_rate']:.3f} | {tw} | {c['mean_prior']:.3f} | {c['brier']:.4f} | "
                           f"{c['brier_uninformed']:.4f} | {c['brier_running']:.4f} |")
            else:
                out.append(f"| {sid} | 0 | | | | | | |")
        out.append("")
    latest = {}
    for s in sets:
        latest.setdefault(s["market"], []).append(s)
    if sets:
        out += ["## Latest sealed sets (postcards from the future)", ""]
        for mk, group in latest.items():
            last_session = max(s["signal_session"] for s in group)
            for s in group:
                if s["signal_session"] == last_session:
                    out.append(card(s))
    if res:
        out += ["## Latest resolutions", "", "| Set | Window | Status | Candidate | Net | Twins mean | Diff | Cone (candidate / twins' rate) |",
                "|---|---|---|---|---:|---:|---:|---|"]
        for r in res[-40:]:
            c = r.get("candidate") or {}
            tr = c.get("trade") or {}
            pr = r.get("paired") or {}
            cone = ", ".join(f"{x['id']}={'?' if x['outcome'] is None else int(x['outcome'])}"
                             + ("" if x.get("twins_rate") is None else f"/{x['twins_rate']:.2f}") for x in r.get("cone", []))
            out.append(f"| {r['set_id'].replace('SPEC-SCAN-', '')} | {r['window']} | {r['status']}{(' (' + r['reason'] + ')') if r.get('reason') else ''} | "
                       f"{c.get('status', '')} | {_pct(tr.get('net_return'))} | {_pct(pr.get('twins_mean_net'))} | {_pct(pr.get('diff'))} | {cone} |")
        out.append("")
    return "\n".join(out) + "\n"


def write_report() -> Path:
    specs = spec_lines()
    REPORT.write_text(render(statistics(specs), specs), encoding="utf-8")
    return REPORT


# ---------------------------------------------------------------------------------- verify
def verify() -> list[str]:
    problems = []
    if not SPEC_LEDGER.exists():
        return problems
    problems += [f"speculations.jsonl: {p}" for p in paper.verify_chain(SPEC_LEDGER)]
    _, proto_sha = protocol()
    ledger = paper.ledger_lines()
    decisions = {r["decision_id"]: r for r in ledger if r["type"] == "DECISION"}
    scans = {r["scan_id"]: r for r in ledger if r["type"] == "SCAN"}
    sets, seen = {}, set()
    for r in spec_lines():
        if r["type"] == "SPECULATION_SET":
            sid = r["set_id"]
            if sid in sets:
                problems.append(f"{sid}: sealed twice")
            sets[sid] = r
            if r["sealed_at"] >= r["entry_cutoff"]:
                problems.append(f"{sid}: sealed at {r['sealed_at']}, after its cutoff {r['entry_cutoff']}")
            dec = decisions.get(r["decision_id"])
            if dec is None or dec["record_hash"] != r["decision_record_hash"]:
                problems.append(f"{sid}: decision record hash not in the ledger")
            sc = scans.get(r["scan_id"])
            if sc is None or sc["record_hash"] != r["scan_record_hash"] or sc["features_sha256"] != r["features_sha256"]:
                problems.append(f"{sid}: scan record or features hash does not match the ledger")
            if r["protocol"]["sha256"] != proto_sha:
                problems.append(f"{sid}: protocol sha256 differs from research/SPECULATION_REGISTER_v1/protocol.json")
        elif r["type"] == "RESOLUTION":
            key = (r["set_id"], r["window"])
            if r["set_id"] not in sets:
                problems.append(f"{r['set_id']}/{r['window']}: resolution without a set")
            if r["window"] not in WINDOW_ORDER:
                problems.append(f"{r['set_id']}/{r['window']}: unknown window")
            if key in seen and not r.get("revises"):
                problems.append(f"{r['set_id']}/{r['window']}: resolved twice without `revises`")
            seen.add(key)
        else:
            problems.append(f"unknown record type {r['type']!r}")
    return problems

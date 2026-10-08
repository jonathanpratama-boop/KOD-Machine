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
POLICY_ID = "PAPER-POLICY-v3"
# v1 (first scan, 2026-10-08): invalidation = max(signal-day low, close x 0.85). On a one-price
#    ARA bar the low equals the close, so the stop sat at the entry price (GTBO, 2026-10-07).
# v2: invalidation at least 5% below the close (and at most 15%); max planned loss states that a
#    gap through the stop (up to the ARB limit) is not covered.
# v3: v2's rules extended to US equities (entry at the next open) and crypto (entry at the live
#    quote taken at decision time), with per-market hypothetical accounts and the E2 cost tiers.
#    IDX decisions are unchanged in substance.
# Preprocessing of the bars a live decision is made from. The global (US / crypto) legacy step
# deletes a bar that reverts the next session; at decision time that next bar is already known
# (it is never after the decision), so live decisions stay causal. It is pinned by name here so
# that the research panel's causal-close-v2 (global_panel._finish) cannot change live inputs
# silently; a switch would be a new policy version.
PREPROCESSING = {"IDX": "idx-yahoo-recent-v1", "US": "global-close-legacy-v1", "CRYPTO": "global-close-legacy-v1"}
HISTORY_DAYS = 200
MIN_HISTORY = 20
BENCHMARKS = ("F2_IGNITION_D", "F1_ARA")  # logged every scan, never decided on


@dataclass(frozen=True)
class Policy:
    """Frozen decision policy. A change is a new POLICY_ID; old decisions keep theirs."""

    equity_idr: float = 100_000_000.0       # hypothetical account; the real budget is unknown
    equity_usd: float = 10_000.0            # US hypothetical account
    equity_usdt: float = 10_000.0           # crypto hypothetical account
    risk_fractions: tuple = (0.005, 0.01)   # scenarios: 0.5% and 1% of equity at risk per trade
    max_position_fraction: float = 0.20     # at most 20% of equity in one name
    max_adv_participation: float = 0.10     # at most 10% of the 20-session median traded value
    chase_limit: float = 0.10               # no fill above signal close x 1.10
    max_stop_distance: float = 0.15         # invalidation no further than 15% below entry (IDX ARB)
    min_stop_distance: float = 0.05         # and no nearer than 5% (a one-price bar's low is its close)
    fee_buy: float = 0.0015
    fee_sell: float = 0.0025
    horizon_sessions: int = 5
    min_validated_lift_p: float = 0.05      # paper BUY needs detection AND the executable plan to beat matched
                                            # random in validation at this level (one-sided)


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


def _detector(market: str = "IDX") -> dict:
    """The frozen decision detector and the benchmark rules logged beside it, per market."""
    if market == "IDX":
        return {"module": family, "selected": family.SELECTED, "rule_id": family.RULE_ID, "version": family.VERSION,
                "args": ("close", "prev", "high", "low", "volume", "present", "tradeable", "lock_up"),
                "benchmarks": BENCHMARKS, "evidence": "E1 validation, 2023"}
    from .rules import moonshot_g

    return {"module": moonshot_g, "selected": moonshot_g.selected(market), "rule_id": f"MOONSHOT_E2_{market}_D1",
            "version": moonshot_g.VERSION, "args": moonshot_g.FEATURE_ARGS,
            "benchmarks": ("G5_IGNITION_D", "G1_RET20_CLOSEHIGH"), "evidence": f"E2 {market} validation, 2023"}


def detector_identity(market: str = "IDX") -> dict:
    det = _detector(market)
    return {"rule_id": det["rule_id"], "version": det["version"], "selected": det["selected"],
            "module_sha256": sha256_file(Path(det["module"].__file__)), "benchmarks": list(det["benchmarks"])}


def _equity(market: str) -> float:
    return {"IDX": POLICY.equity_idr, "US": POLICY.equity_usd, "CRYPTO": POLICY.equity_usdt}[market]


def _tick(price: float, market: str) -> float:
    if market == "IDX":
        return float(mkt.tick_size(np.array([price]))[0])
    if market == "US":
        return 0.01 if price >= 1 else 0.0001
    return 10.0 ** (math.floor(math.log10(price)) - 4) if price > 0 else 1e-8


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
def load_recent(manifest: Path, market: str = "IDX", purpose: str = "decision") -> tuple[pd.DataFrame, dict]:
    """purpose="decision": the pinned live preprocessing (PREPROCESSING). purpose="scoring": US and
    crypto bars through the causal step, so a later bar can never delete the signal-day bar."""
    header, records = read_manifest(manifest)
    if market == "IDX":
        from .panel import _yahoo_frame

        frames, status = [], {}
        for r in records:
            status[r["ticker"]] = r["http_status"]
            if r["http_status"] != 200 or not r.get("rows"):
                continue
            payload = json.loads((PKG_ROOT / r["path"]).read_text(encoding="utf-8"))
            frames.append(_yahoo_frame(r["ticker"], payload))
        df = pd.concat(frames, ignore_index=True)
        df = df[df["close"] > 0]
    else:
        from . import global_panel

        raw, _ = global_panel.load_us(manifest) if market == "US" else global_panel.load_crypto(manifest)
        df, _ = (global_panel._finish_legacy_v1(raw) if purpose == "decision" else global_panel._finish(raw))
        key = "ticker" if market == "US" else "symbol"
        status = {r[key]: r["http_status"] for r in records if key in r and not str(r[key]).startswith("_")}
    return df, {"manifest": manifest.name, "manifest_sha256": sha256_file(manifest), "header": header,
                "http_status": status}


def _market(df: pd.DataFrame, market: str = "IDX") -> Market:
    if market != "IDX":  # global_panel._finish already dropped non-session dates
        return Market.from_panel(df, price_limits=False)
    # Sessions: dates on which at least 50 names traded (holiday stubs dropped, as in the panel).
    traded = df[df["volume"] > 0].groupby("date")["ticker"].nunique()
    df = df[df["date"].isin(traded[traded >= 50].index)]
    return Market.from_panel(df)


# ---------------------------------------------------------------------------------- scan
def scan(manifest: Path, now: datetime | None = None, validation: dict | None = None, market: str = "IDX",
         quotes=None) -> dict:
    """Evaluate the session that last closed. Returns {"scan": record, "decisions": [...], "features": DataFrame}."""
    df, data = load_recent(manifest, market)
    return scan_frame(df, data, now, validation, market, quotes)


def scan_frame(df: pd.DataFrame, data: dict, now: datetime | None = None, validation: dict | None = None,
               market: str = "IDX", quotes=None) -> dict:
    """quotes: crypto only, a callable (tickers -> {ticker: (price, time)}) for live prices at decision time."""
    det = _detector(market)
    sel, module = det["selected"], det["module"]
    if sel is None:
        raise RuntimeError(f"no frozen detector for {market}")
    now = now or datetime.now(timezone.utc)
    m = _market(df, market)
    d = m.shape[1] - 1
    session = str(m.dates[d])
    view = CausalSource(m).view(d)
    f = module.features(*[getattr(view, a) for a in det["args"]])
    flags = module.family_flags(f)
    tick = view.tickers
    history = np.cumsum(view.present, axis=1)[:, d]
    fresh = view.present[:, d]
    eligible = view.tradeable[:, d] & (history > MIN_HISTORY)
    value = np.where(view.tradeable, view.value, np.nan)
    adv = pd.DataFrame(value[:, max(0, d - 19): d + 1].T).median().to_numpy()
    zeros = np.zeros(len(tick), dtype=bool)
    feats = pd.DataFrame({
        "ticker": tick, "session": session, "fresh": fresh, "eligible": eligible,
        "close": view.close[:, d], "previous": view.prev[:, d], "high": view.high[:, d], "low": view.low[:, d],
        "open": view.open[:, d], "volume": view.volume[:, d], "adv20_value": adv,
        **{k: f[k][:, d] for k in ("ret1", "rel1", "ret5", "ret20", "volr", "cpos", "dd60")},
        "ara": f["ara"][:, d] if "ara" in f else zeros, "brk60": f["brk60"][:, d],
        **({"gap": f["gap"][:, d]} if "gap" in f else {}),
        **{name: flags[name][:, d] & eligible for name, _ in module.FAMILY},
    }).sort_values("ticker").reset_index(drop=True)
    chosen = feats[feats[sel]].sort_values(["volr", "ticker"], ascending=[False, True])
    requested = len(data["http_status"])
    ok = sum(1 for s in data["http_status"].values() if s == 200)
    scan_id = f"SCAN-{session}-{sel}" if market == "IDX" else f"SCAN-{market}-{session}-{sel}"
    cutoff = {"IDX": f"close of IDX session {session} (bars fetched after the close)",
              "US": f"close of US session {session} (bars fetched after the close)",
              "CRYPTO": f"end of UTC day {session} (bars fetched after 00:00 UTC)"}[market]
    record = {
        "type": "SCAN", "market": market, "scan_id": scan_id, "session": session, "discovered_at": utc_stamp(now),
        "cutoff": cutoff, "detector": detector_identity(market),
        "policy": {"policy_id": POLICY_ID, "sha256": policy_sha()}, "preprocessing": PREPROCESSING[market],
        "data": {"source": "binance_spot_klines_1d" if market == "CRYPTO" else "yahoo_chart_v8",
                 "manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"],
                 "requested": requested, "http_ok": ok, "fresh_for_session": int(fresh.sum()),
                 "eligible": int(eligible.sum()), "not_scanned": requested - int(fresh.sum())},
        "flags": {name: sorted(feats.loc[feats[name], "ticker"].tolist()) for name in (sel, *det["benchmarks"])},
        "candidates_ranked": chosen["ticker"].tolist(),
        "ranking": "volume ratio (volr), descending; ties by ticker",
        "result": "NO SIGNAL" if chosen.empty else f"{len(chosen)} CANDIDATE(S)",
        "validation_evidence": validation,
    }
    live = quotes(chosen["ticker"].tolist()) if (quotes and market == "CRYPTO" and not chosen.empty) else {}
    decisions = [decide(row, rank + 1, scan_id, session, now, validation, market, live.get(row.ticker))
                 for rank, row in enumerate(chosen.itertuples(index=False))]
    primary = next((x for x in decisions if x["decision"] == "BUY ON TRIGGER"), None)
    for x in decisions:
        x["primary"] = x is primary
    return {"scan": record, "decisions": decisions, "features": feats, "market": m}


def _next_session(day: str, market: str = "IDX") -> str:
    """Next weekday (IDX, US) or next day (crypto). Exchange holidays are not modelled: if it is
    one, the trigger moves to the next session that actually trades, and the outcome says so."""
    if market == "CRYPTO":
        return str(np.datetime64(day, "D") + 1)
    return str(np.busday_offset(np.datetime64(day, "D"), 1, roll="forward"))


def decide(row, rank: int, scan_id: str, session: str, now: datetime, validation: dict | None,
           market: str = "IDX", quote=None) -> dict:
    from .profiles import PROFILES

    p = POLICY
    prof = PROFILES[market]
    det = _detector(market)
    sel = det["selected"]
    cur = prof.currency.lower()
    sym = {"IDX": "Rp", "US": "$", "CRYPTO": ""}[market]
    lot = prof.lot_size
    close, low = float(row.close), float(row.low)
    quote_price = float(quote[0]) if quote else None
    tick = _tick(close, market)
    chase = math.floor(close * (1 + p.chase_limit) / tick) * tick
    stop = min(max(low, close * (1 - p.max_stop_distance)), close * (1 - p.min_stop_distance))
    stop = math.floor(stop / tick) * tick
    entry_ref = quote_price if (market == "CRYPTO" and quote_price) else close
    if market == "IDX":
        fee_in, fee_out = p.fee_buy, p.fee_sell
    else:
        tier = float(prof.per_side_cost(np.array([entry_ref]))[0])
        fee_in, fee_out = prof.fee_buy + tier, prof.fee_sell + tier
    per_share_risk = entry_ref - stop + entry_ref * (fee_in + fee_out)
    adv = float(row.adv20_value) if np.isfinite(row.adv20_value) else 0.0
    equity = _equity(market)
    cap_value = min(p.max_position_fraction * equity, p.max_adv_participation * adv)
    scenarios = []
    for r in p.risk_fractions:
        budget = r * equity
        units = (budget / per_share_risk if per_share_risk > 0 else 0)
        units = min(units, cap_value / entry_ref)
        shares = math.floor(units / lot) * lot if market != "CRYPTO" else math.floor(units * 1e6) / 1e6
        scenarios.append({"risk_fraction": r, f"risk_budget_{cur}": budget, "shares": shares,
                          "lots": int(shares // lot) if market != "CRYPTO" else None,
                          f"position_{cur}": shares * entry_ref,
                          f"max_planned_loss_{cur}": round(shares * per_share_risk) if market == "IDX"
                          else round(shares * per_share_risk, 2)})
    reasons = []
    if not scenarios[-1]["shares"]:
        unit = "whole lot" if market == "IDX" else ("share" if market == "US" else "position")
        reasons.append(f"no {unit} fits: risk/{'lot' if market == 'IDX' else 'unit'} {sym}{per_share_risk * lot:,.4g}, "
                       f"position cap {sym}{cap_value:,.0f} (10% of 20-session median value {sym}{adv:,.0f})")
    if market == "IDX" and close < 50:
        reasons.append("priced below Rp50: special-board / full-call-auction rules, outside the modelled market")
    if market == "CRYPTO" and quote_price is None:
        reasons.append("no live quote could be taken at decision time, so there is no verified price to act on")
    if market == "CRYPTO" and quote_price is not None and quote_price > chase:
        reasons.append(f"the live quote {quote_price:g} is already above the chase limit {chase:g}")
    detected = bool(validation and validation.get("p_one_sided_vs_matched") is not None
                    and validation["p_one_sided_vs_matched"] < p.min_validated_lift_p
                    and (validation.get("lift_vs_matched_random") or 0) > 1)
    trading = (validation or {}).get("trading") or {}
    tradeable_edge = bool(trading.get("p_one_sided") is not None and trading["p_one_sided"] < p.min_validated_lift_p)
    entry_words = {"IDX": "buy at the next close", "US": "buy at the next open",
                   "CRYPTO": "buy at the next day's open"}[market]
    if reasons:
        decision, why = "NOT EXECUTABLE", "; ".join(reasons)
    elif not detected:
        decision, why = "PASS", ("the detector's validation did not beat matched random controls at p < "
                                 f"{p.min_validated_lift_p}; no edge to underwrite a paper position")
    elif not tradeable_edge:
        why = ("detection is validated (E30 precision {:.1%} vs {:.1%} for matched names), but the executable plan "
               "({}, hold {} sessions) did not beat matched random entries in validation: average net {} vs {} "
               "(run {}).").format(
                   validation.get("precision") or 0,
                   (validation.get("precision") or 0) / (validation.get("lift_vs_matched_random") or 1),
                   entry_words, p.horizon_sessions,
                   "n/a" if trading.get("avg_net_return") is None else f"{trading['avg_net_return']:+.2%}",
                   "n/a" if trading.get("matched_random_avg_net_return") is None
                   else f"{trading['matched_random_avg_net_return']:+.2%}",
                   trading.get("run_id", "none"))
        why += (" Fills come mostly when the continuation fails; the names still locked at ARA cannot be bought."
                if market == "IDX" else " Most flagged names fade after the spike (median 5-session return about "
                                        "-10% in validation) while a minority runs much further.")
        decision = "PASS"
    else:
        decision, why = "BUY ON TRIGGER", "validated detector, executable size within the risk budget"
    nxt = _next_session(session, market)
    precision = (validation or {}).get("precision")
    if market == "IDX":
        instrument = {"ticker": row.ticker, "yahoo_symbol": f"{row.ticker}.JK", "venue": prof.venue,
                      "currency": "IDR", "lot_size": lot}
        verified = {"close": close, "session": session, "source": "Yahoo daily bar (official close)",
                    "note": "last completed session; no live quote was taken"}
        trigger = (f"paper buy at the official close of {nxt} if that close is <= Rp{chase:g} (chase limit) "
                   f"and > Rp{stop:g}, the name traded, and the close is not locked at ARA")
        expiry = f"close of {nxt}; unfilled by then = expired"
        change = ["the next session opens locked at ARA (no sellers): unfillable",
                  "a suspension or UMA notice from IDX before the entry close",
                  "news of a rights issue or dilutive placement"]
    elif market == "US":
        instrument = {"ticker": row.ticker, "yahoo_symbol": row.ticker, "venue": prof.venue, "currency": "USD",
                      "lot_size": lot}
        verified = {"close": close, "session": session, "source": "Yahoo daily bar (consolidated close)",
                    "note": "last completed session; no live quote was taken (decision made after the close)"}
        trigger = (f"paper buy at the official opening print of {nxt} if it is <= ${chase:g} (chase limit) and "
                   f"> ${stop:g}")
        expiry = f"open of {nxt}; outside the band at the open = expired"
        change = ["a trading halt or delisting notice before the open",
                  "an offering, ATM or reverse-split announcement (dilution)",
                  "a pre-market price already beyond the chase limit"]
    else:
        instrument = {"ticker": row.ticker, "pair": f"{row.ticker}USDT", "venue": prof.venue, "currency": "USDT",
                      "lot_size": "fractional"}
        verified = {"close": close, "session": session, "source": "Binance daily kline (UTC close)",
                    "quote": quote_price, "quote_time": quote[1] if quote else None,
                    "quote_source": "Binance spot ticker price at decision time"}
        trigger = (f"paper buy at the decision-time quote {quote_price:g} USDT (verified live price)"
                   if quote_price else "no live quote: not executable")
        expiry = "the decision-time quote only; no later fill"
        change = ["a delisting or monitoring-tag announcement by Binance", "an exploit, unlock or depeg headline",
                  "the quote moving above the chase limit before execution"]
    return {
        "type": "DECISION", "market": market, "decision_id": f"{scan_id}-{row.ticker}", "scan_id": scan_id,
        "rank": rank, "instrument": instrument,
        "discovered_at": utc_stamp(now), "decided_at": utc_stamp(now), "signal_session": session,
        "verified_price": verified,
        "evidence": {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in {
            "ret1": float(row.ret1), "rel1": float(row.rel1), "ret5": float(row.ret5), "ret20": float(row.ret20),
            "volr": float(row.volr), "cpos": float(row.cpos), "dd60": float(row.dd60), "ara": bool(row.ara),
            "previous": float(row.previous), "high": float(row.high), "low": low, "volume": float(row.volume),
            "adv20_value": adv}.items()},
        "thesis": (f"{sel} fired at the close of {session}: " + dict(det["module"].FAMILY)[sel]
                   + f". Historically ({det['evidence']}) such flags were followed by a +30% repricing within 5 "
                   "sessions more often than matched names."),
        "prediction": {"statement": f"max close over the next {p.horizon_sessions} sessions >= 1.30 x {close:g}",
                       "falsified_if": f"no close in the next {p.horizon_sessions} sessions reaches {close * 1.3:g}",
                       "historical_frequency": precision,
                       "note": "an empirical frequency from the validation period, not a calibrated probability"},
        "decision": decision, "reason": why,
        "plan": {
            "entry_trigger": trigger, "max_chase_price": chase, "invalidation": stop,
            "invalidation_rule": "exit at the first close at or below the invalidation level",
            "gap_risk": "max planned loss assumes the exit fills at the invalidation level; a gap through it makes "
                        "the loss larger" + (", up to 15% per session while locked at ARB" if market == "IDX" else ""),
            "exit": f"close of the {p.horizon_sessions}th session after entry, or invalidation"
                    + ("; a sale rolls while locked at ARB" if market == "IDX" else ""),
            "sizing_formula": ("shares = floor(min(R x equity / (entry - stop + entry x fees), min(20% x equity, "
                               "10% x 20-session median value) / entry) / 100) x 100" if market == "IDX" else
                               "units = min(R x equity / (entry - stop + entry x costs), min(20% x equity, 10% x "
                               "20-session median value) / entry)" + (", whole shares" if market == "US" else
                                                                      ", to 1e-6 units")),
            "costs_per_side": [fee_in, fee_out], "scenarios": scenarios, f"equity_assumption_{cur}": equity,
            "equity_note": "hypothetical; the real risk budget is unknown, so sizes are labelled scenarios",
            "horizon_sessions": p.horizon_sessions, "expiry": expiry,
            "liquidity": {f"adv20_value_{cur}": adv, f"position_cap_{cur}": cap_value},
            "catalyst": "none identified: a tape-only detector (no news or filing was read)",
            "would_change_decision": change,
        } if decision != "NOT EXECUTABLE" else {"reason": why, "horizon_sessions": p.horizon_sessions},
        "policy": {"policy_id": POLICY_ID, "sha256": policy_sha()}, "preprocessing": PREPROCESSING[market],
        "detector": detector_identity(market),
    }


# ---------------------------------------------------------------------------------- score
def score(decision: dict, m: Market, *, price_units: dict | None = None) -> dict | None:
    """Score one decision on bars that now cover its window, or None if the window is still open."""
    from .profiles import PROFILES

    p = POLICY
    market = decision.get("market", "IDX")
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
    plan = decision.get("plan", {})
    # The plan's prices are in the units of the decision day. If the name split (or reverse
    # split) since, the source has rescaled its whole history: put the plan into today's units
    # by the ratio of the signal-day close now to the close recorded then.
    recorded = float(decision["verified_price"].get("close") or 0)
    scale = float(close[d] / recorded) if recorded > 0 and np.isfinite(close[d]) and close[d] > 0 else 1.0
    unit_factor = None
    if price_units is not None:
        from .price_units import split_conversion_factor
        convention = price_units.get("convention")
        if not ((market in ("US", "IDX") and convention == "SPLIT_ONLY")
                or (market == "CRYPTO" and convention == "UNADJUSTED" and not price_units.get("actions"))):
            raise ValueError("Verified scoring needs split-only units (US, IDX) or unadjusted units (crypto)")
        def unit_factor(k):
            return split_conversion_factor(str(dates[k]), price_units["actions"],
                                           price_units["adjustment_reference"],
                                           coverage_complete=price_units.get("coverage_complete", False))
        signal_factor = unit_factor(d)
        if not np.isfinite(recorded) or recorded <= 0 or not np.isclose(close[d] * signal_factor, recorded,
                                                                         rtol=price_units.get("rtol", 1e-6), atol=1e-8):
            raise ValueError("Recorded signal price does not reconcile to verified split schedule")
        scale = 1.0 / signal_factor
    if market == "IDX":
        entry_price, first = float(close[e]), e + 1
        fillable = bool(m.tradeable[n, e] and not m.lock_up[n, e])
        fee_in, fee_out = p.fee_buy, p.fee_sell
    else:
        prof = PROFILES[market]
        quote = decision["verified_price"].get("quote") if market == "CRYPTO" else None
        entry_price = quote * scale if quote else float(m.open[n, e])
        first = e
        fillable = bool(np.isfinite(entry_price) and entry_price > 0)
        # cost tier at the price actually paid (decision-day units), not the rescaled one
        cost_price = entry_price * unit_factor(e) if unit_factor else entry_price / scale
        tier = float(prof.per_side_cost(np.array([cost_price]))[0]) if fillable else 0.0
        fee_in, fee_out = prof.fee_buy + tier, prof.fee_sell + tier
    in_band = ("max_chase_price" in plan
               and plan["invalidation"] * scale < entry_price <= plan["max_chase_price"] * scale)
    stop = plan["invalidation"] * scale if "invalidation" in plan else None
    exit_idx, exit_reason = None, None
    path = []
    if fillable and in_band:
        for k in range(first, min(e + 1 + p.horizon_sessions, len(dates))):
            rel_k = float(level[k] / level[e] - 1) if market == "IDX" else float(close[k] / entry_price - 1)
            path.append(rel_k)
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
        gross = float(level[exit_idx] / level[e] - 1) if market == "IDX" else float(close[exit_idx] / entry_price - 1)
        if unit_factor and market != "IDX":  # IDX fees are flat: no tier to re-price
            exit_as_traded = float(close[exit_idx]) * unit_factor(exit_idx)
            fee_out = prof.fee_sell + float(prof.per_side_cost(np.array([exit_as_traded]))[0])
        net = (1 + gross) * (1 - fee_out) / (1 + fee_in) - 1
        trade = {"entry_session": str(m.dates[e]), "entry_price": float(entry_price),
                 **({"entry_close": float(entry_price)} if market == "IDX" else {}),
                 "entry_basis": {"IDX": "close", "US": "open", "CRYPTO": "decision-time quote"}[market],
                 "exit_session": str(m.dates[exit_idx]), "exit_reason": exit_reason, "net_return": net,
                 "mfe": max(path), "mae": min(path)}
        if unit_factor and market != "IDX":
            trade.update(entry_price_as_traded=entry_price * unit_factor(e),
                         exit_price_as_traded=exit_as_traded,
                         entry_cost_rate=fee_in, exit_cost_rate=fee_out)
    executed = decision["decision"] == "BUY ON TRIGGER" and trade is not None
    would_have = trade["net_return"] if trade else None
    if decision["decision"] == "BUY ON TRIGGER":
        verdict = ("NOT FILLED" if trade is None else ("PROFIT" if trade["net_return"] > 0 else "LOSS"))
    else:
        verdict = ("CORRECT REJECTION" if would_have is None or would_have <= 0 else "MISSED GAIN (rejected, plan would have profited)")
    return {"type": "OUTCOME", "market": market, "decision_id": decision["decision_id"], "scored_at": utc_stamp(),
            "discovery": discovery, "execution": {"fillable_at_trigger": fillable, "within_chase_band": bool(in_band),
                                                    "paper_trade": trade, "executed": executed},
            "scoring_version": (("verified-us-units-v1" if market == "US" else "verified-units-v1") if unit_factor
                                else "legacy-signal-scale-v1 (forensic only: infers units from a price ratio; "
                                     "never used to record)"),
            "decision_verdict": verdict, "price_scale": scale,
            **({"price_scale_note": "the source rescaled this name's history since the decision (split or "
                                    "adjustment); plan prices were multiplied by price_scale"}
               if abs(scale - 1) > 0.01 else {})}


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
def active_tickers(market: str = "IDX") -> list[str]:
    """IDX: names in the latest recorded scan (works from a fresh clone), plus the panel's active
    names when the panel is present, plus data/universe/extra_tickers.csv. US: the latest US scan,
    else the latest US panel's active names. Crypto is taken live from Binance at fetch time."""
    import csv

    tickers: set[str] = set()
    prefix = "SCAN-2" if market == "IDX" else f"SCAN-{market}-"
    scans = sorted(SCANS.glob(f"{prefix}*/features.csv*")) if SCANS.exists() else []
    if scans:
        tickers |= set(pd.read_csv(scans[-1], usecols=["ticker"], dtype={"ticker": str}, keep_default_na=False)["ticker"])
    if market == "IDX":
        try:
            from .panel import load

            df, _, _ = load()
            last = df.groupby("ticker")["date"].max()
            tickers |= set(last[last == df["date"].max()].index)
        except (FileNotFoundError, RuntimeError):
            pass
        with (PKG_ROOT / "data" / "universe" / "extra_tickers.csv").open(newline="", encoding="utf-8") as fh:
            tickers |= {r["ticker"].strip().upper() for r in csv.DictReader(fh) if r["ticker"].strip()}
    elif market == "US" and not tickers:
        from . import global_panel

        df, _ = global_panel.load(global_panel.latest("US"))
        last = df.groupby("ticker")["date"].max()
        tickers |= set(last[last == df["date"].max()].index)
    return sorted(tickers)


def binance_quotes(tickers: list[str]) -> dict:
    """Live spot prices for <TICKER>USDT, with the time they were taken."""
    import urllib.request
    from urllib.parse import quote as quote_url

    out = {}
    for t in tickers:
        url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={quote_url(t)}USDT"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                        timeout=20) as resp:
                out[t] = (float(json.loads(resp.read())["price"]), utc_stamp())
        except Exception:  # noqa: BLE001 - recorded as a missing quote, decided NOT EXECUTABLE
            continue
    return out


VALIDATION_WINDOW = ("2023-01-02", "2023-12-29")
VALIDATION_WINDOWS = {"IDX": VALIDATION_WINDOW, "US": ("2023-01-01", "2023-12-31"),
                      "CRYPTO": ("2023-01-01", "2023-12-31")}


def validation_evidence(market: str = "IDX") -> dict | None:
    """Detection (E1/E2 validation, E30) and trading (idxsig harness over the validation window)
    evidence for the market's frozen detector."""
    det = _detector(market)
    path = (PKG_ROOT / "research" / "E1" / "validation" / "result.json" if market == "IDX"
            else PKG_ROOT / "research" / "E2" / market / "validation" / "result.json")
    if not path.exists():
        return None
    res = json.loads(path.read_text(encoding="utf-8"))
    if res.get("rule") != det["selected"]:
        return None
    out = {"source": rel(path), "source_sha256": sha256_file(path), "rule": res["rule"],
           **{k: res["E30"].get(k) for k in ("precision", "precision_lo95", "precision_hi95", "base_rate",
                                              "lift_vs_base", "lift_vs_matched_random", "p_one_sided_vs_matched")}}
    trading = None
    index = PKG_ROOT / "results" / "RUNS.jsonl"
    for line in index.read_text(encoding="utf-8").splitlines() if index.exists() else []:
        run = json.loads(line)
        if det["rule_id"] not in run.get("dir", ""):
            continue
        summary = json.loads((PKG_ROOT / run["dir"] / "summary.json").read_text(encoding="utf-8"))
        cfg = summary["config"]
        if (cfg["start"], cfg["end"]) != VALIDATION_WINDOWS[market] or "Selected: " + det["selected"] not in summary["rule"]["text"]:
            continue
        mr = summary["random_matched"]["avg_net_return"] or {}
        trading = {"run_id": summary["run_id"], "scored_trades": summary["rule_trades"]["scored"],
                   "fill_rate": summary["rule_trades"]["fill_rate"], "avg_net_return": mr.get("observed"),
                   "matched_random_avg_net_return": mr.get("random_mean"), "p_one_sided": mr.get("p_value_one_sided"),
                   "status_counts": summary["rule_trades"]["status_counts"]}
    out["trading"] = trading
    return out


def already_scanned(session: str, market: str = "IDX") -> bool:
    sel = _detector(market)["selected"]
    return any(r["type"] == "SCAN" and r.get("market", "IDX") == market and r["session"] == session
               and r["detector"]["selected"] == sel for r in ledger_lines())


def record_scan(out: dict, timestamper=None) -> list[Path]:
    scan_dir = SCANS / out["scan"]["scan_id"]
    scan_dir.mkdir(parents=True, exist_ok=False)
    if out["scan"].get("market", "IDX") == "IDX":
        feat_path = scan_dir / "features.csv"
        with feat_path.open("x", encoding="utf-8", newline="") as fh:
            out["features"].to_csv(fh, index=False, float_format="%.6g", lineterminator="\n")
    else:  # thousands of names a day: gzip (fixed mtime, so the bytes depend only on the content)
        import gzip
        import io

        feat_path = scan_dir / "features.csv.gz"
        text = io.StringIO()
        out["features"].to_csv(text, index=False, float_format="%.6g", lineterminator="\n")
        with feat_path.open("xb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
            gz.write(text.getvalue().encode("utf-8"))
    out["scan"]["features_file"] = rel(feat_path)
    out["scan"]["features_sha256"] = sha256_file(feat_path)
    stored = append([out["scan"], *out["decisions"]], timestamper=timestamper)
    tokens = [TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [feat_path, LEDGER, *[t for t in tokens if t.exists()]]


SCORER_ID = "paper-score-v2"
# v2 (2026-10-08, before any outcome was recorded): units from the provider's split records,
# each corroborated by an SEC filing for US names, never from a change in price ratios; the
# recorded signal-day close must reconcile with the scoring data in those units (rtol 1e-3);
# entry and exit cost tiers at their own sessions; scoring bars use the causal preprocessing.
# A decision whose units cannot be established is recorded UNSCORABLE with the reason.
SCORING_PREPROCESSING = {"IDX": "idx-yahoo-recent-v1", "US": "causal-close-v2", "CRYPTO": "causal-close-v2"}
RECONCILE_RTOL = 1e-3


def _window_complete(decision: dict, m: Market) -> bool:
    tickers, dates = list(m.tickers), m.dates.astype(str)
    if decision["instrument"]["ticker"] not in tickers or decision["signal_session"] not in dates:
        return False
    d = int(np.flatnonzero(dates == decision["signal_session"])[0])
    return d + 1 + POLICY.horizon_sessions < len(dates)


def scoring_units(decision: dict, m: Market, events: pd.DataFrame, verify=None) -> tuple[dict | None, str | None, list]:
    """(price_units for score(), reason it cannot be scored, evidence). `events`: the provider's
    split records for this name in the scoring pull; `verify(event) -> status, evidence` checks
    one against SEC (US). Units come from records, never from a change in price ratios."""
    market = decision.get("market", "IDX")
    last = str(m.dates[-1])
    if market == "CRYPTO":
        return {"convention": "UNADJUSTED", "actions": [], "adjustment_reference": last, "coverage_complete": True,
                "rtol": RECONCILE_RTOL}, None, []
    after = events[events["effective_session"] > decision["signal_session"]] if len(events) else events
    evidence, actions = [], []
    for ev in after.itertuples(index=False):
        if market != "US":
            return None, (f"provider records a {ev.provider_ratio} split effective {ev.effective_session} and there is "
                          f"no independent {market} corporate-action source to corroborate it"), evidence
        status, found = verify(ev) if verify else ("NOT_CHECKED", [])
        evidence.append({"effective_session": ev.effective_session, "ratio": ev.provider_ratio, "status": status,
                         "filings": found})
        if status not in ("VERIFIED", "RATIO_CONFIRMED"):
            return None, (f"split record {ev.provider_ratio} effective {ev.effective_session} is not corroborated "
                          f"by an SEC filing ({status})"), evidence
        actions.append({"effective_session": ev.effective_session, "new_shares": ev.numerator,
                        "old_shares": ev.denominator})
    return {"convention": "SPLIT_ONLY", "actions": actions, "adjustment_reference": last, "coverage_complete": True,
            "rtol": RECONCILE_RTOL}, None, evidence


def due(market: str, today: str | None = None, rescore: dict | None = None) -> list[str]:
    """Decisions of `market` without an outcome (or asked to be rescored) whose window can have
    ended by `today`: entry the session after the signal, then the horizon. Lets paper-score skip
    a data pull when nothing can be scored yet."""
    today = np.datetime64(today or datetime.now(timezone.utc).date().isoformat(), "D")
    rescore = rescore or {}
    done = {r["decision_id"] for r in ledger_lines() if r["type"] == "OUTCOME"}
    # exit = signal + 1 (entry) + horizon sessions. IDX/US routines run after that session's close,
    # so it is complete on its own date; crypto's run at 00:23 UTC sees only the day before.
    need = 1 + POLICY.horizon_sessions + (1 if market == "CRYPTO" else 0)
    out = []
    for r in ledger_lines():
        if r["type"] != "DECISION" or r.get("market", "IDX") != market:
            continue
        if r["decision_id"] in done and r["decision_id"] not in rescore:
            continue
        sig = np.datetime64(r["signal_session"], "D")
        elapsed = (int((today - sig).astype(int)) if market == "CRYPTO"
                   else int(np.busday_count(sig, today)))
        if elapsed >= need:
            out.append(r["decision_id"])
    return out


def score_pending(manifest: Path, timestamper=None, market: str = "IDX", verify=None,
                  rescore: dict | None = None) -> tuple[list[Path], list[dict]]:
    """Score every decision of `market` whose window has ended and that has no outcome yet.
    rescore {decision_id: reason}: score these again and append the result as a revision that
    links the latest earlier outcome (records are never edited)."""
    lines = ledger_lines()
    latest = {}
    for r in lines:
        if r["type"] == "OUTCOME":
            latest[r["decision_id"]] = r
    rescore = rescore or {}
    pending = [r for r in lines if r["type"] == "DECISION" and r.get("market", "IDX") == market
               and (r["decision_id"] not in latest or r["decision_id"] in rescore)]
    if not pending:
        return [], []
    df, data = load_recent(manifest, market, purpose="scoring")
    m = _market(df, market)
    events = pd.DataFrame()
    if market in ("US", "IDX"):
        from . import us_actions

        events = us_actions.yahoo_events(manifest)
    outcomes = []
    for r in pending:
        if not _window_complete(r, m):
            continue
        ticker_events = events[events["ticker"] == r["instrument"]["ticker"]] if len(events) else events
        units, reason, evidence = scoring_units(r, m, ticker_events, verify)
        out = None
        if units is not None:
            try:
                out = score(r, m, price_units=units)
            except ValueError as exc:  # recorded close does not reconcile in these units
                reason = f"{exc} (rtol {RECONCILE_RTOL})"
        if out is None and reason is None:
            continue
        if out is None:
            out = {"type": "OUTCOME", "market": market, "decision_id": r["decision_id"], "scored_at": utc_stamp(),
                   "status": "UNSCORABLE", "reason": reason}
        else:
            out["status"] = "SCORED"
            out.pop("price_scale_note", None)
        out.update(scorer=SCORER_ID, preprocessing=SCORING_PREPROCESSING[market],
                   units={"actions": (units or {}).get("actions", []), "evidence": evidence,
                          "convention": (units or {}).get("convention")})
        if r["decision_id"] in latest:
            out["revises"] = latest[r["decision_id"]]["record_hash"]
            out["revision_reason"] = rescore[r["decision_id"]]
        outcomes.append(out)
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

"""Descriptive group context, deliberately separate from strategy permission.

Groups are BTC, ETH and past-turnover tiers within the supplied crypto universe.
They describe this recorded coverage, not all markets or actual dollar transfers.
No predictive connections or pump/manipulation diagnoses are produced.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from statistics import median

from .runtime.data import SnapshotError, parse_time, utc_text


def _numeric(value):
    return None if value is None else float(Decimal(str(value)))


def _median(values):
    usable = [x for x in values if x is not None]
    return float(median(usable)) if usable else None


def _consecutive(previous: dict, current: dict) -> bool:
    return parse_time(current["open_time"]) - parse_time(previous["open_time"]) == timedelta(days=1)


def build_context(snapshot: dict, as_of: str) -> dict:
    cutoff = parse_time(as_of, "as_of")
    if snapshot.get("validation", {}).get("status") != "VALIDATED":
        raise SnapshotError("market context requires a validated recorded snapshot")
    if parse_time(snapshot["as_of"]) != cutoff:
        raise SnapshotError("context cutoff must equal the validated snapshot cutoff")
    by_instrument = defaultdict(list)
    for bar in snapshot["bars"]:
        if parse_time(bar["received_at"]) > cutoff or parse_time(bar["close_time"]) > cutoff:
            raise SnapshotError("future bar reached context builder")
        duration = parse_time(bar["close_time"]) - parse_time(bar["open_time"])
        if not timedelta(hours=23, minutes=59) <= duration <= timedelta(days=1):
            raise SnapshotError("context v1 accepts daily bars only")
        by_instrument[bar["instrument_id"]].append(bar)
    members, eligible = [], []
    warnings = []
    for instrument in snapshot["instruments"]:
        ident = instrument["instrument_id"]
        rows = sorted(by_instrument[ident], key=lambda x: x["open_time"])
        member = {"instrument_id": ident, "symbol": instrument["symbol"], "venue": instrument["venue"],
                  "base_asset": instrument["base_asset"], "quote_asset": instrument["quote_asset"],
                  "group_id": None, "return_1d": None, "relative_volume": None,
                  "prior_median_quote_turnover": None, "close": None, "bar_close_time": None,
                  "status": "NO_BARS", "bar_count": len(rows), "evidence_ids": []}
        if instrument["asset_class"].lower() not in ("crypto", "cryptocurrency"):
            member["status"] = "UNSUPPORTED_ASSET_CLASS"
        elif instrument["quote_asset"] != "USDT":
            member["status"] = "UNSUPPORTED_QUOTE_CURRENCY"
        elif rows:
            last = rows[-1]
            member.update(close=last["close"], bar_close_time=last["close_time"],
                          evidence_ids=sorted({r["evidence_id"] for r in rows[-21:]}), status="OBSERVED")
            if cutoff - parse_time(last["close_time"]) > timedelta(hours=48):
                member["status"] = "STALE_BARS"
            else:
                # Do not bridge a missing day or count yesterday's return as today's.
                if len(rows) >= 2 and _consecutive(rows[-2], last):
                    member["return_1d"] = float(Decimal(last["close"]) / Decimal(rows[-2]["close"]) - 1)
                else:
                    member["status"] = "INSUFFICIENT_RETURN_HISTORY"
                prior = rows[-21:-1]
                contiguous = len(prior) == 20 and all(_consecutive(a, b) for a, b in zip(rows[-21:-1], rows[-20:]))
                volumes = [_numeric(r.get("quote_volume")) for r in prior]
                # Require a complete trailing window; missing volume is not zero.
                if contiguous and all(v is not None for v in volumes):
                    turnover = _median(volumes)
                    member["prior_median_quote_turnover"] = turnover
                    if turnover and turnover > 0 and last.get("quote_volume") is not None:
                        member["relative_volume"] = _numeric(last["quote_volume"]) / turnover
                eligible.append(member)
        members.append(member)
    # Establish membership from data before the latest signal bar, never its spike.
    alts = sorted([m for m in eligible if m["base_asset"] not in ("BTC", "ETH") and
                   m["prior_median_quote_turnover"] is not None],
                  key=lambda m: (-m["prior_median_quote_turnover"], m["instrument_id"]))
    for rank, member in enumerate(alts):
        bucket = min(2, (rank * 3) // max(1, len(alts)))
        member["group_id"] = ("ALT_HIGH_TURNOVER", "ALT_MID_TURNOVER", "ALT_LOW_TURNOVER")[bucket]
    for m in eligible:
        if m["base_asset"] in ("BTC", "ETH"):
            m["group_id"] = m["base_asset"]
        elif m["group_id"] is None:
            m["group_id"] = "ALT_INSUFFICIENT_HISTORY"
    names = {"BTC": "Bitcoin", "ETH": "Ethereum", "ALT_HIGH_TURNOVER": "Alts: higher prior turnover",
             "ALT_MID_TURNOVER": "Alts: middle prior turnover", "ALT_LOW_TURNOVER": "Alts: lower prior turnover",
             "ALT_INSUFFICIENT_HISTORY": "Alts: insufficient turnover history"}
    groups = []
    for gid, name in names.items():
        group = [m for m in members if m["group_id"] == gid]
        if not group:
            continue
        returns = [m["return_1d"] for m in group if m["return_1d"] is not None]
        groups.append({"id": gid, "name": name, "member_ids": [m["instrument_id"] for m in group],
                       "return_1d": sum(returns) / len(returns) if returns else None,
                       "breadth": sum(x > 0 for x in returns) / len(returns) if returns else None,
                       "relative_volume": _median([m["relative_volume"] for m in group]),
                       "coverage": {"members": len(group), "return_observations": len(returns),
                                    "volume_observations": sum(m["relative_volume"] is not None for m in group)},
                       "as_of": utc_text(cutoff), "membership_basis": "previous 20 completed daily bars, excluding signal bar"})
    if len(alts) < 9:
        warnings.append("Small covered altcoin universe: turnover tiers have few peers and are descriptive only.")
    if any(m["status"] != "OBSERVED" for m in members):
        warnings.append("Some instruments lack current comparable observations; missing values remain null.")
    return {"schema_version": "KOD_MARKET_CONTEXT_V1", "as_of": utc_text(cutoff),
            "evidence_kind": snapshot["evidence_kind"], "snapshot_sha256": snapshot["snapshot_sha256"],
            "groups": groups, "members": members, "warnings": warnings, "descriptive_only": True,
            "predictive_edges": [], "coverage": {"instruments": len(members), "observed": len(eligible)},
            "interpretation": "Relative price/turnover context in supplied USDT coverage; no actual money-flow or prediction claim."}


def discover_candidates(snapshot: dict, context: dict, as_of: str) -> list[dict]:
    """Return a deterministic observational radar, not entries or financial advice.

    A 3% daily absolute move or 2x prior volume is a transparent display threshold,
    not a tested strategy. Other observed instruments remain in context.members.
    """
    cutoff = utc_text(parse_time(as_of))
    if context.get("as_of") != cutoff or snapshot.get("as_of") != cutoff:
        raise SnapshotError("discovery inputs have different cutoffs")
    candidates = []
    for member in context["members"]:
        move, volume = member["return_1d"], member["relative_volume"]
        if move is None or not (abs(move) >= .03 or (volume is not None and volume >= 2)):
            continue
        peers = [m for m in context["members"] if m["group_id"] == member["group_id"] and
                 m["instrument_id"] != member["instrument_id"] and m["return_1d"] is not None]
        breadth = sum(m["return_1d"] > 0 for m in peers) / len(peers) if peers else None
        peer_return = _median([m["return_1d"] for m in peers])
        flag = "UNKNOWN"
        if move > 0 and peers:
            flag = "PEER_SUPPORTED" if breadth >= .5 and peer_return > 0 else "ISOLATED"
        candidates.append({"candidate_id": f"TAPE:{member['instrument_id']}:{cutoff}",
                           "instrument_id": member["instrument_id"], "symbol": member["symbol"],
                           "venue": member["venue"], "state": "DETECTED", "family": "TAPE",
                           "as_of": cutoff, "return_1d": move, "relative_volume": volume,
                           "group_id": member["group_id"], "peer_participation": flag,
                           "peer_count": len(peers), "peer_breadth": breadth,
                           "peer_return_1d": peer_return, "evidence_ids": member["evidence_ids"],
                           "entry_permission": False, "mechanism": "UNKNOWN",
                           "research_status": "DESCRIPTIVE_ONLY", "blockers": ["No validated entry policy attached"],
                           "detection_reason": "absolute daily move >=3% or relative turnover >=2x",
                           "explanation": "Isolation is a descriptive observation, not a manipulation diagnosis."})
    return sorted(candidates, key=lambda x: (-abs(x["return_1d"]), x["instrument_id"]))

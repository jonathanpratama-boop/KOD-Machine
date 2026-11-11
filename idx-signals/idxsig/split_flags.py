"""SPLIT_ARTIFACT_V11: a descriptive tag ledger for US speculation sets.

The live US scan treats close / previous - 1 >= 0.30 as a spike. Around a reverse split the provider often keeps the
last pre-split close, so the recorded ratio equals the split ratio and a non-event is recorded as a spike
(research/US_SPLIT_ARTIFACTS_v1: 9 of 134 sets, 2026-10-27 to 2026-11-09).

This module only DESCRIBES. It appends SPLIT_FLAG records to its own hash-chained ledger (paper/split_flags.jsonl)
and changes no detector, cone, plan, decision, cutoff or existing ledger line. The rule is the disclosed addendum
v1.1 of that audit, unchanged: a provider split event effective in (signal_session - 10 days, signal_session] whose
division of the recorded ratio brings it closer to no move and leaves it below +30%.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import paper
from .provenance import PKG_ROOT, read_manifest, utc_stamp

NY = ZoneInfo("America/New_York")
RULE_ID = "SPLIT_ARTIFACT_V11"
THRESHOLD = 0.30
LOOKBACK_DAYS = 10
INDETERMINATE_RATIO = 4.0
FLAGS_LEDGER = paper.PAPER / "split_flags.jsonl"
FLAG_VALUES = ("ARTIFACT_V11", "INDETERMINATE", "NOT_FLAGGED", "NOT_ASSESSED")
RECORD_TYPE = "SPLIT_FLAG"


def provider_splits(payload) -> list[dict]:
    """Provider split events of a Yahoo chart payload; [] for anything missing or malformed."""
    try:
        raw = payload["chart"]["result"][0]["events"]["splits"]
        out = []
        for e in raw.values():
            n, d = float(e["numerator"]), float(e["denominator"])
            when = datetime.fromtimestamp(int(e["date"]), timezone.utc).astimezone(NY).date()
            if not (math.isfinite(n) and math.isfinite(d)):
                continue
            ratio = e.get("splitRatio")
            out.append(
                {
                    "effective_session": when.isoformat(),
                    "numerator": n,
                    "denominator": d,
                    "provider_ratio": ratio if isinstance(ratio, str) else None,
                }
            )
        return out
    except (TypeError, KeyError, IndexError, AttributeError, ValueError, OverflowError, OSError):
        return []


def classify(recorded_ratio: float, events: list[dict], signal_session: str) -> dict | None:
    """The addendum-v1.1 test. recorded_ratio is signal close / signal previous. Returns the hit or None."""
    try:
        r = float(recorded_ratio)
        lo = (date.fromisoformat(signal_session) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(r) and r > 0):
        return None
    for e in sorted(events, key=lambda x: x["effective_session"], reverse=True):
        if not lo < e["effective_session"] <= signal_session:
            continue
        n, d = e["numerator"], e["denominator"]
        if not n or not d or n < 0 or d < 0:
            continue
        k = d / n
        adjusted = r / k
        if adjusted - 1 < THRESHOLD and abs(math.log(adjusted)) < abs(math.log(r)):
            return {**e, "k": k, "split_adjusted_ret1": round(adjusted - 1, 4)}
    return None


def label(recorded_ratio: float, hit: dict | None) -> str:
    if hit:
        return "ARTIFACT_V11"
    return "INDETERMINATE" if recorded_ratio >= INDETERMINATE_RATIO else "NOT_FLAGGED"


def _ratio(set_rec: dict) -> float | None:
    s = set_rec.get("signal") or {}
    try:
        close, prev = float(s["close"]), float(s["previous"])
    except (KeyError, TypeError, ValueError):
        return None
    return close / prev if close > 0 and prev > 0 else None


def flag_record(set_rec: dict, payload, basis: str, assessed_at: str) -> dict:
    """The unsealed SPLIT_FLAG record of one set. payload None means no provider data was available."""
    ratio = _ratio(set_rec)
    hit, flag = None, "NOT_ASSESSED"
    if payload is not None and ratio is not None:
        hit = classify(ratio, provider_splits(payload), set_rec["signal_session"])
        flag = label(ratio, hit)
    split = ""
    if hit:
        shown = hit["provider_ratio"] or f"{hit['numerator']:g}:{hit['denominator']:g}"
        split = f"{hit['effective_session']} {shown}"
    return {
        "type": RECORD_TYPE,
        "rule": RULE_ID,
        "set_id": set_rec["set_id"],
        "ticker": set_rec["ticker"],
        "market": set_rec["market"],
        "signal_session": set_rec["signal_session"],
        "recorded_ret1": None if ratio is None else round(ratio - 1, 4),
        "flag": flag,
        "split": split,
        "split_adjusted_ret1": hit["split_adjusted_ret1"] if hit else None,
        "basis": basis,
        "assessed_at": assessed_at,
    }


def _is_set(r: dict) -> bool:
    return r.get("market") == "US" and "decision" in r


def pending(specs: list[dict], flags: list[dict]) -> list[dict]:
    done = {r["set_id"] for r in flags if r.get("type") == RECORD_TYPE}
    return [r for r in specs if _is_set(r) and r["set_id"] not in done]


def _flags(flags):
    return paper.ledger_lines(FLAGS_LEDGER) if flags is None else flags


def flagged_set_ids(flags: list[dict] | None = None, labels=("ARTIFACT_V11",)) -> set[str]:
    return {
        r["set_id"]
        for r in _flags(flags)
        if r.get("type") == RECORD_TYPE and r.get("flag") in labels
    }


def verify(flags: list[dict] | None = None, specs: list[dict] | None = None) -> list[str]:
    on_disk = flags is None
    problems = (
        [f"split_flags chain: {p}" for p in paper.verify_chain(FLAGS_LEDGER)]
        if on_disk and FLAGS_LEDGER.exists()
        else []
    )
    flags = _flags(flags)
    if specs is None:
        from . import speculation

        specs = speculation.spec_lines()
    sealed = {r["set_id"] for r in specs if _is_set(r)}
    seen = set()
    for i, r in enumerate(flags, 1):
        where = f"split_flags line {i}"
        if r.get("type") != RECORD_TYPE:
            problems.append(f"{where}: unknown record type {r.get('type')!r}")
            continue
        if r.get("rule") != RULE_ID:
            problems.append(f"{where}: rule {r.get('rule')!r} is not {RULE_ID}")
        if r.get("flag") not in FLAG_VALUES:
            problems.append(f"{where}: invalid flag {r.get('flag')!r}")
        if r.get("set_id") in seen:
            problems.append(f"{where}: set {r.get('set_id')} is flagged twice")
        seen.add(r.get("set_id"))
        if r.get("set_id") not in sealed:
            problems.append(f"{where}: {r.get('set_id')} is not a sealed US set")
    return problems


def _payload(record: dict):
    if record.get("http_status") != 200 or not record.get("path"):
        return None
    try:
        return json.loads((PKG_ROOT / record["path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def flag_pending(manifest: Path, timestamper=None, now: datetime | None = None) -> list[dict]:
    """Flag every unflagged US set from the provider events in `manifest` (the pull the scan just made).
    A set whose ticker has no readable payload is recorded NOT_ASSESSED rather than silently skipped."""
    from . import speculation

    todo = pending(speculation.spec_lines(), paper.ledger_lines(FLAGS_LEDGER))
    if not todo:
        return []
    _, records = read_manifest(manifest)
    by_ticker = {r["ticker"]: r for r in records}
    stamp = utc_stamp() if now is None else now.strftime("%Y-%m-%dT%H:%M:%SZ")
    basis = f"provider events in pull {Path(manifest).name}"
    new = [
        flag_record(s, _payload(by_ticker[s["ticker"]]) if s["ticker"] in by_ticker else None, basis, stamp)
        for s in todo
    ]
    return paper.append(new, path=FLAGS_LEDGER, timestamper=timestamper)


def backfill_from_audit(csv_path: Path, basis: str, timestamper=None) -> list[dict]:
    """One-time: flag the sets already assessed by research/US_SPLIT_ARTIFACTS_v1 (results/sets_v11.csv) from the
    audit's own classification, labelled as such. Sets that are not sealed US sets or already flagged are skipped."""
    from . import speculation

    specs = {r["set_id"]: r for r in speculation.spec_lines() if _is_set(r)}
    done = {r["set_id"] for r in paper.ledger_lines(FLAGS_LEDGER) if r.get("type") == RECORD_TYPE}
    stamp, new = utc_stamp(), []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            s = specs.get(row["set_id"])
            if s is None or row["set_id"] in done:
                continue
            adj = row.get("split_adjusted_ret1")
            new.append(
                {
                    "type": RECORD_TYPE,
                    "rule": RULE_ID,
                    "set_id": s["set_id"],
                    "ticker": s["ticker"],
                    "market": s["market"],
                    "signal_session": s["signal_session"],
                    "recorded_ret1": round(float(row["recorded_ret1"]), 4),
                    "flag": row["v11_class"],
                    "split": row.get("split") or "",
                    "split_adjusted_ret1": float(adj) if adj not in (None, "") else None,
                    "basis": basis,
                    "assessed_at": stamp,
                }
            )
    return paper.append(new, path=FLAGS_LEDGER, timestamper=timestamper) if new else []

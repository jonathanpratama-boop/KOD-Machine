"""SPLIT_UNITS_V1 assessments of US speculation sets, with revisions (research/SPLIT_REVISIONS_v1).

A second descriptive ledger, paper/split_assessments.jsonl, beside the SPLIT_ARTIFACT_V11 tag ledger. The V11 ledger,
its rule and its code are untouched: they record what was tagged at the time. This ledger differs in two ways.

- Its rule (idxsig/split_units.py) asks which session supplied the previous close, so a genuine move after a split is
  not called an artifact.
- A set may be assessed more than once. Its first record is the assessment made from the scan's own pull at sealing;
  each later record is a reassessment from a later pull and names the record it supersedes. Nothing is ever edited.

Readers keep two histories apart: what was tagged before a set's entry cutoff, and what current evidence establishes.
A correction found later is not a filter that was available before the trade.

This module only DESCRIBES. It changes no detector, cone, plan, decision, cutoff or existing ledger line.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from . import paper, split_flags, split_units
from .provenance import read_manifest, utc_stamp

LEDGER = paper.PAPER / "split_assessments.jsonl"
RECORD_TYPE = "SPLIT_ASSESSMENT"
RULE_ID = split_units.RULE_ID
PULL_ROLES = ("seal", "later")
CHANGE_FIELDS = ("assessment", "split", "previous_session", "units", "evidence_gap")
# Classes whose finding rests on a split the response listed (contract addendum 2, point 1). A later response that
# lists no readable split cannot confirm or contradict such a finding (contract addendum 3).
EVENT_BASED = frozenset(
    {
        "ARTIFACT_CONFIRMED",
        "ARTIFACT_PROBABLE",
        "REAL_MOVE_UNITS_CONTAMINATED",
        "SPLIT_IN_WINDOW_UNRESOLVED",
        "REAL_MOVE_UNITS_UNVERIFIED",
        "REAL_MOVE_AFTER_SPLIT",
    }
)
EVIDENCE_GAPS = ("SPLIT_EVENTS_ABSENT", "SPLIT_EVENTS_MALFORMED")


def _is_set(r: dict) -> bool:
    return r.get("market") == "US" and "decision" in r


def _own(records) -> list[dict]:
    return [r for r in records if r.get("type") == RECORD_TYPE]


def _records(records):
    return paper.ledger_lines(LEDGER) if records is None else records


def _v11(v11_flags):
    return paper.ledger_lines(split_flags.FLAGS_LEDGER) if v11_flags is None else v11_flags


def _nothing_checked() -> dict:
    return split_units.classify(None, None, None, [], [])


def _reaches_back(priced, signal_session) -> bool:
    """Whether a priced bar lies in the reference window before the signal session."""
    try:
        s_day = date.fromisoformat(signal_session)
    except (TypeError, ValueError):
        return False
    for day, _ in priced:
        try:
            gap = (s_day - date.fromisoformat(day)).days
        except (TypeError, ValueError):
            continue
        if 0 < gap <= split_units.REFERENCE_LOOKBACK_DAYS:
            return True
    return False


def split_event_coverage(payload) -> str:
    """What a provider chart payload says about splits (contract addendum 3): "LISTED" when it holds a split-event
    block whose every entry `split_flags.provider_splits` can read and that lists at least one split; "ABSENT" when
    there is no such block or it lists nothing; "MALFORMED" when a block is there but cannot be read in full."""
    try:
        result = payload["chart"]["result"][0]
    except (TypeError, KeyError, IndexError):
        return "ABSENT"
    if not isinstance(result, dict) or result.get("events") is None:
        return "ABSENT"
    events = result["events"]
    if not isinstance(events, dict):
        return "MALFORMED"
    splits = events.get("splits")
    if splits is None:
        return "ABSENT"
    if not isinstance(splits, dict):
        return "MALFORMED"
    if not splits:
        return "ABSENT"
    return "LISTED" if len(split_flags.provider_splits(payload)) == len(splits) else "MALFORMED"


def _when(text):
    """An ISO timestamp as an aware datetime, or None."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def assessment_record(
    set_rec: dict,
    payload,
    basis: str,
    assessed_at: str,
    *,
    prior: dict | None = None,
    seal: dict | None = None,
    pull_role: str = "later",
    retrieved_on: str | None = None,
    sources=(),
    finding: dict | None = None,
) -> dict:
    """The unsealed SPLIT_ASSESSMENT record of one set. payload None means no provider data was available.
    `finding` is the set's standing assessment, if any: when it rests on a listed split and this response lists no
    readable split, the response is an incomplete refresh, recorded NOT_ASSESSABLE with its evidence gap."""
    sig = set_rec.get("signal") or {}
    ratio = split_flags._ratio(set_rec)
    recorded_previous = None
    if seal and seal.get("pull_role") == "seal" and seal.get("previous_session"):
        recorded_previous = seal["previous_session"]
    bars = split_units.payload_bars(payload) if payload is not None else []
    priced = [(day, px) for day, px in bars if isinstance(px, (int, float)) and not isinstance(px, bool) and px > 0]
    gap = None
    coverage = split_event_coverage(payload) if priced else None
    if not priced:
        # Contract addendum 1: a response that holds no bar with a price is not evidence. Nothing was checked.
        ans, events = _nothing_checked(), []
    elif finding and finding.get("assessment") in EVENT_BASED and coverage != "LISTED":
        # Contract addendum 3: the standing finding rests on a listed split and this response lists none it can read.
        # Missing evidence is not contrary evidence: record the incomplete refresh; standing() keeps the finding.
        ans, events = _nothing_checked(), []
        gap = "SPLIT_EVENTS_MALFORMED" if coverage == "MALFORMED" else "SPLIT_EVENTS_ABSENT"
    else:
        events = split_flags.provider_splits(payload)
        ans = split_units.classify(
            sig.get("close"),
            sig.get("previous"),
            set_rec.get("signal_session"),
            events,
            bars,
            recorded_previous,
            retrieved_on,
        )
        if ans["class"] == "NO_ACTION_FOUND" and not _reaches_back(priced, set_rec.get("signal_session")):
            # Contract addendum 2: "nothing found" in a response that shows no bar before the signal session is an
            # absence nobody could have seen. The other classes rest on a listed split or on the size of the move.
            ans, events = _nothing_checked(), []
    split = ""
    used = ans["event"]
    if used:
        ratio_text = next(
            (
                e.get("provider_ratio")
                for e in events
                if e["effective_session"] == used["effective_session"]
                and e["numerator"] == used["numerator"]
                and e["denominator"] == used["denominator"]
            ),
            None,
        )
        shown = ratio_text or f"{used['numerator']:g}:{used['denominator']:g}"
        split = f"{used['effective_session']} {shown}"
    return {
        "type": RECORD_TYPE,
        "rule": RULE_ID,
        "set_id": set_rec["set_id"],
        "ticker": set_rec["ticker"],
        "market": set_rec["market"],
        "signal_session": set_rec["signal_session"],
        "recorded_ret1": None if ratio is None else round(ratio - 1, 4),
        "assessment": ans["class"],
        "group": ans["group"],
        "split": split,
        "split_adjusted_ret1": ans["adjusted_ret1"],
        "previous_session": ans["previous_session"],
        "previous_session_source": ans["previous_session_source"],
        "units": ans["units"],
        "later_factor": ans["later_factor"],
        "evidence_gap": gap,
        "pull_role": pull_role,
        "supersedes": prior["record_hash"] if prior else None,
        "basis": basis,
        "sources": list(sources),
        "assessed_at": assessed_at,
    }


def latest(records) -> dict[str, dict]:
    """Set id to the set's last assessment, in ledger order."""
    out = {}
    for r in _own(records):
        out[r["set_id"]] = r
    return out


def standing(records) -> dict[str, dict]:
    """Set id to the set's standing assessment: its last record that is not NOT_ASSESSABLE, or, for a set whose
    records are all NOT_ASSESSABLE, its last record. A night without evidence never displaces a finding
    (contract addendum 2)."""
    out = {}
    for r in _own(records):
        if r.get("assessment") != "NOT_ASSESSABLE" or out.get(r["set_id"], r).get("assessment") == "NOT_ASSESSABLE":
            out[r["set_id"]] = r
    return out


def seal_assessments(records) -> dict[str, dict]:
    """Set id to the set's first assessment, for sets whose first assessment came from the scan's own pull."""
    first = {}
    for r in _own(records):
        first.setdefault(r["set_id"], r)
    return {sid: r for sid, r in first.items() if r.get("pull_role") == "seal"}


def pending(specs: list[dict], records: list[dict]) -> list[dict]:
    done = {r["set_id"] for r in _own(records)}
    return [s for s in specs if _is_set(s) and s["set_id"] not in done]


def changed(new: dict, old: dict) -> bool:
    return any(new.get(k) != old.get(k) for k in CHANGE_FIELDS)


def propose_assessments(
    specs, records, payloads, basis, assessed_at, *, seal_session=None, retrieved_on=None
) -> list[dict]:
    """One unsealed record for every pending set. A set with no payload is recorded NOT_ASSESSABLE, never skipped."""
    return [
        assessment_record(
            s,
            payloads.get(s["ticker"]),
            basis,
            assessed_at,
            pull_role="seal" if seal_session is not None and s["signal_session"] == seal_session else "later",
            retrieved_on=retrieved_on,
        )
        for s in pending(specs, records)
    ]


def propose_reassessments(
    specs, records, payloads, basis, assessed_at, *, window_days=None, today=None, retrieved_on=None, sources=None
) -> list[dict]:
    """Unsealed records for the already-assessed sets whose assessment differs on this pull. A set with no payload
    is skipped: no evidence is not new evidence."""
    current, seals, findings, out = latest(records), seal_assessments(records), standing(records), []
    for s in specs:
        if not _is_set(s) or s["set_id"] not in current:
            continue
        if window_days is not None and today is not None:
            try:
                age = (date.fromisoformat(today) - date.fromisoformat(s["signal_session"])).days
            except (TypeError, ValueError):
                continue
            if age > window_days:
                continue
        payload = payloads.get(s["ticker"])
        if payload is None:
            continue
        old = current[s["set_id"]]
        new = assessment_record(
            s,
            payload,
            basis,
            assessed_at,
            prior=old,
            seal=seals.get(s["set_id"]),
            pull_role="later",
            retrieved_on=retrieved_on,
            sources=(sources or {}).get(s["set_id"], ()),
            finding=findings.get(s["set_id"]),
        )
        if changed(new, old):
            out.append(new)
    return out


def removed_set_ids(view: str, records=None, v11_flags=None, cutoffs=None) -> set[str]:
    """The sets a view leaves out.

    "corrected": current evidence classes the set as an artifact (its standing assessment; the V11 tag when the set
    has no assessment that carries evidence). "at_the_time": the latest record about the set made before its entry
    cutoff was an artifact. A NOT_ASSESSABLE record counts in neither view.
    """
    records, v11_flags = _own(_records(records)), _v11(v11_flags)
    tags = [r for r in v11_flags if r.get("type") == split_flags.RECORD_TYPE]
    if view == "corrected":
        current = standing(records)
        out = {sid for sid, r in current.items() if r.get("group") == "ARTIFACT"}
        out |= {
            r["set_id"]
            for r in tags
            if r.get("flag") == "ARTIFACT_V11"
            and current.get(r["set_id"], {"assessment": "NOT_ASSESSABLE"}).get("assessment") == "NOT_ASSESSABLE"
        }
        return out
    if view == "at_the_time":
        best = {}
        evidence = [r for r in records if r.get("assessment") != "NOT_ASSESSABLE"]
        for rank, rows, is_artifact in (
            (0, tags, lambda r: r.get("flag") == "ARTIFACT_V11"),
            (1, evidence, lambda r: r.get("group") == "ARTIFACT"),
        ):
            for r in rows:
                cutoff = _when((cutoffs or {}).get(r.get("set_id")))
                at = _when(r.get("assessed_at"))
                if cutoff is None or at is None or not at < cutoff:
                    continue
                key = (at, rank)
                if r["set_id"] not in best or key >= best[r["set_id"]][0]:
                    best[r["set_id"]] = (key, is_artifact(r))
        return {sid for sid, (_, artifact) in best.items() if artifact}
    raise ValueError(f"unknown view {view!r}")


def unresolved_set_ids(records=None) -> set[str]:
    return {sid for sid, r in standing(_records(records)).items() if r.get("group") == "UNRESOLVED"}


def verify(records: list[dict] | None = None, specs: list[dict] | None = None) -> list[str]:
    on_disk = records is None
    problems = (
        [f"split_assessments chain: {p}" for p in paper.verify_chain(LEDGER)] if on_disk and LEDGER.exists() else []
    )
    records = _records(records)
    if specs is None:
        from . import speculation

        specs = speculation.spec_lines()
    sealed = {r["set_id"] for r in specs if _is_set(r)}
    last = {}
    for i, r in enumerate(records, 1):
        where = f"split_assessments line {i}"
        if r.get("type") != RECORD_TYPE:
            problems.append(f"{where}: unknown record type {r.get('type')!r}")
            continue
        sid = r.get("set_id")
        if r.get("rule") != RULE_ID:
            problems.append(f"{where}: rule {r.get('rule')!r} is not {RULE_ID}")
        if r.get("assessment") not in split_units.GROUP:
            problems.append(f"{where}: invalid assessment {r.get('assessment')!r}")
        elif r.get("group") != split_units.GROUP[r["assessment"]]:
            problems.append(f"{where}: group {r.get('group')!r} is not the group of {r['assessment']}")
        gap = r.get("evidence_gap")
        if gap is not None and (gap not in EVIDENCE_GAPS or r.get("assessment") != "NOT_ASSESSABLE"):
            problems.append(f"{where}: evidence_gap {gap!r} on a {r.get('assessment')!r} record")
        if r.get("pull_role") not in PULL_ROLES:
            problems.append(f"{where}: invalid pull_role {r.get('pull_role')!r}")
        if sid not in sealed:
            problems.append(f"{where}: {sid} is not a sealed US set")
        prev = last.get(sid)
        if prev is None:
            if r.get("supersedes") is not None:
                problems.append(f"{where}: the first assessment of {sid} supersedes {r.get('supersedes')!r}")
        else:
            if r.get("supersedes") != prev.get("record_hash"):
                problems.append(f"{where}: {sid} does not supersede its previous assessment")
            if r.get("pull_role") == "seal":
                problems.append(f"{where}: {sid} has a second assessment marked as the scan's own pull")
            if not changed(r, prev):
                problems.append(f"{where}: {sid} is reassessed with no change")
        last[sid] = r
    return problems


def _payload_map(manifest: Path) -> dict:
    _, rows = read_manifest(manifest)
    return {r["ticker"]: split_flags._payload(r) for r in rows}


def _stamp(now):
    return utc_stamp() if now is None else now.strftime("%Y-%m-%dT%H:%M:%SZ")


def assess_pending(
    manifest: Path, timestamper=None, now: datetime | None = None, *, seal_session=None, sources=None
) -> list[dict]:
    """Assess every set that has no assessment yet, from the pull in `manifest`. Sets of `seal_session` are marked as
    assessed from the scan's own pull. `sources` maps set id to strings stored on that set's record."""
    from . import speculation

    specs, records = speculation.spec_lines(), paper.ledger_lines(LEDGER)
    if not pending(specs, records):
        return []
    stamp = _stamp(now)
    new = propose_assessments(
        specs,
        records,
        _payload_map(manifest),
        f"provider pull {Path(manifest).name}",
        stamp,
        seal_session=seal_session,
        retrieved_on=stamp[:10],
    )
    for r in new:
        r["sources"] = list((sources or {}).get(r["set_id"], ()))
    return paper.append(new, path=LEDGER, timestamper=timestamper) if new else []


def reassess(
    manifest: Path, timestamper=None, now: datetime | None = None, *, window_days=None, sources=None
) -> list[dict]:
    """Reassess the already-assessed sets from the pull in `manifest`; append only what changed."""
    from . import speculation

    stamp = _stamp(now)
    new = propose_reassessments(
        speculation.spec_lines(),
        paper.ledger_lines(LEDGER),
        _payload_map(manifest),
        f"provider pull {Path(manifest).name}",
        stamp,
        window_days=window_days,
        today=stamp[:10],
        retrieved_on=stamp[:10],
        sources=sources,
    )
    return paper.append(new, path=LEDGER, timestamper=timestamper) if new else []


def entry_cutoffs(specs: list[dict] | None = None) -> dict[str, str]:
    """Set id to entry cutoff, for sealed US sets."""
    if specs is None:
        from . import speculation

        specs = speculation.spec_lines()
    return {s["set_id"]: s.get("entry_cutoff") for s in specs if _is_set(s) and s.get("entry_cutoff")}

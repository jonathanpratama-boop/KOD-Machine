"""Display-only input warning around the frozen PAPER_BOOK_v1 renderer.

The pinned book implementation, decisions and historical ledger remain intact.

Secondary view (added 2026-11-11, research/US_SPLIT_ARTIFACTS_v1 proposal 2): when some planned spikes carry the
descriptive SPLIT_ARTIFACT_V11 tag (idxsig/split_flags.py), the report ends with the same four books recomputed
without them. It is disclosure only: the frozen verdict above it is unchanged, and with no tagged spike the output
is byte-identical to the frozen renderer plus the banner.

Revisions (added 2026-11-12, research/SPLIT_REVISIONS_v1): once a planned spike has a SPLIT_UNITS_V1 assessment
(idxsig/split_assessments.py), the secondary section shows the books three ways, side by side: as frozen, as known at
the time (without the sets whose artifact tag was recorded before their entry cutoff), and corrected (without the sets
that current evidence classes as artifacts). A book with no assessed spike is rendered exactly as before.
"""

from . import paper, paper_book as book, paper_input_health, split_assessments, split_flags

HEADING = (
    "## Secondary view: sets tagged SPLIT_ARTIFACT_V11 excluded "
    "(display only, the frozen verdict above is unchanged)"
)


def _money(x):
    return f"${x:+,.0f}"


HEADING_ASSESSED = (
    "## Secondary view: split-unit assessments "
    "(display only, the frozen verdict above is unchanged)"
)
VIEWS = (("as_frozen", "As frozen"), ("at_the_time", "Known at the time"), ("corrected", "Corrected"))


def views(rows, records, v11_flags, cutoffs):
    """The book's rows under the three views. Rows keep their order."""
    then = split_assessments.removed_set_ids("at_the_time", records, v11_flags, cutoffs)
    now = split_assessments.removed_set_ids("corrected", records, v11_flags, cutoffs)
    return {
        "as_frozen": list(rows),
        "at_the_time": [r for r in rows if r["set_id"] not in then],
        "corrected": [r for r in rows if r["set_id"] not in now],
    }


def _assessed_view(rows, records, v11_flags, cutoffs):
    """The section shown once a planned spike has an assessment."""
    current = split_assessments.standing(records)
    tags = {r["set_id"]: r for r in v11_flags if r.get("type") == split_flags.RECORD_TYPE}
    removed_then = split_assessments.removed_set_ids("at_the_time", records, v11_flags, cutoffs)
    removed_now = split_assessments.removed_set_ids("corrected", records, v11_flags, cutoffs)
    in_book = {r["set_id"] for r in rows}
    confirmed = sum(1 for s in in_book if current.get(s, {}).get("assessment") == "ARTIFACT_CONFIRMED")
    probable = sum(1 for s in in_book if current.get(s, {}).get("assessment") == "ARTIFACT_PROBABLE")
    unresolved = {s for s in in_book - removed_now if current.get(s, {}).get("group") == "UNRESOLVED"}
    unsupported = {
        s for s in in_book if tags.get(s, {}).get("flag") == "ARTIFACT_V11" and s in current and s not in removed_now
    }
    listed = [
        r
        for r in rows
        if r["set_id"] in removed_now
        or r["set_id"] in removed_then
        or r["set_id"] in unresolved
        or r["set_id"] in unsupported
        or tags.get(r["set_id"], {}).get("flag") in ("ARTIFACT_V11", "INDETERMINATE")
    ]
    out = [
        HEADING_ASSESSED,
        "",
        f"{len(removed_now & in_book)} of {len(rows)} planned spikes are split artifacts on current evidence "
        f"({confirmed} confirmed, {probable} probable): a reverse split left the previous close in pre-split units, "
        "so the recorded +30% day did not happen. "
        f"{len(unresolved)} are unresolved and stay in every view. "
        f"{len(unsupported)} carried an artifact tag that current evidence does not support. "
        f"Ledgers: `paper/split_flags.jsonl` (rule `{split_flags.RULE_ID}`, the tag at the time) and "
        f"`paper/split_assessments.jsonl` (rule `{split_assessments.RULE_ID}`, research/SPLIT_REVISIONS_v1).",
        "",
        "| Spike | Session | Tag at the time | Tag recorded before entry cutoff | Current assessment | Assessed |",
        "|---|---|---|---|---|---|",
    ]
    for r in listed:
        sid = r["set_id"]
        tag, cur = tags.get(sid), current.get(sid)
        cutoff = split_assessments._when(cutoffs.get(sid))
        tagged_at = split_assessments._when((tag or {}).get("assessed_at"))
        before = "-" if not tag else ("yes" if cutoff and tagged_at and tagged_at < cutoff else "no")
        out.append(
            f"| {r['ticker']} | {r['session']} | {tag['flag'] if tag else 'none'} | {before} | "
            f"{cur['assessment'] if cur else 'none'} | {(cur or {}).get('assessed_at', '')[:10] or '-'} |"
        )
    out += [
        "",
        "The same books three ways. As frozen counts every planned spike. Known at the time leaves out only the "
        "spikes whose artifact tag was recorded before their entry cutoff: it is what a filter could have done on "
        "the day. Corrected leaves out the spikes that current evidence classes as artifacts: it uses evidence that "
        "arrived later and is not a filter that was available before the trade. This is a disclosure, not a second "
        "verdict: the planned look and the bounds above are computed on every planned spike, as frozen.",
        "",
        "| Book | View | Positions | Closed | Wins | P&L | Average trade |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    by_view = views(rows, records, v11_flags, cutoffs)
    for b in book.BOOKS:
        for key, label in VIEWS:
            s = book.book_summary(by_view[key], b)
            avg = "-" if s["average"] is None else f"{s['average']:+.2%}"
            out.append(
                f"| {b} | {label} | {s['positions']} | {s['closed']} | {s['wins']} | {_money(s['pnl'])} | {avg} |"
            )
    return "\n\n" + "\n".join(out) + "\n"


def secondary_view(rows):
    """The appended section, or "" when no row of the book is tagged or assessed."""
    records = paper.ledger_lines(split_assessments.LEDGER)
    assessed = split_assessments.latest(records)
    if any(r["set_id"] in assessed for r in rows):
        return _assessed_view(
            rows, records, paper.ledger_lines(split_flags.FLAGS_LEDGER), split_assessments.entry_cutoffs()
        )
    tagged = split_flags.flagged_set_ids()
    hit = [r for r in rows if r["set_id"] in tagged]
    if not hit:
        return ""
    kept = [r for r in rows if r["set_id"] not in tagged]
    names = ", ".join(f"{r['ticker']} ({r['session']})" for r in hit)
    out = [
        HEADING,
        "",
        f"{len(hit)} of {len(rows)} planned spikes were recorded as +30% days only because a reverse split "
        "left the last pre-split close in the provider's data (`paper/split_flags.jsonl`, rule "
        f"`{split_flags.RULE_ID}`, research/US_SPLIT_ARTIFACTS_v1). Tagged: {names}.",
        "",
        "The same books without them. This is a disclosure, not a second verdict: the planned look and "
        "the bounds above are computed on every planned spike, as frozen.",
        "",
        "| Book | Positions | Closed | Wins | P&L | Average trade |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for b in book.BOOKS:
        s = book.book_summary(kept, b)
        avg = "-" if s["average"] is None else f"{s['average']:+.2%}"
        out.append(
            f"| {b} | {s['positions']} | {s['closed']} | {s['wins']} | {_money(s['pnl'])} | {avg} |"
        )
    return "\n\n" + "\n".join(out) + "\n"


def render(rows, *, input_health=None):
    status = paper_input_health.unassessed() if input_health is None else input_health
    text = paper_input_health.add_banner(book.render(rows), status)
    return text + secondary_view(rows)


def write_report(*, input_health=None):
    input_health = paper_input_health.load() if input_health is None else input_health
    book.REPORT.write_text(render(book.trades(), input_health=input_health), encoding="utf-8")
    return book.REPORT

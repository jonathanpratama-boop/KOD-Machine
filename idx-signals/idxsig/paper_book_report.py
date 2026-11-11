"""Display-only input warning around the frozen PAPER_BOOK_v1 renderer.

The pinned book implementation, decisions and historical ledger remain intact.

Secondary view (added 2026-11-11, research/US_SPLIT_ARTIFACTS_v1 proposal 2): when some planned spikes carry the
descriptive SPLIT_ARTIFACT_V11 tag (idxsig/split_flags.py), the report ends with the same four books recomputed
without them. It is disclosure only: the frozen verdict above it is unchanged, and with no tagged spike the output
is byte-identical to the frozen renderer plus the banner.
"""

from . import paper_book as book, paper_input_health, split_flags

HEADING = (
    "## Secondary view: sets tagged SPLIT_ARTIFACT_V11 excluded "
    "(display only, the frozen verdict above is unchanged)"
)


def _money(x):
    return f"${x:+,.0f}"


def secondary_view(rows):
    """The appended section, or "" when no row of the book is tagged."""
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

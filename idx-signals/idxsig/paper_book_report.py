"""Display-only input warning around the frozen PAPER_BOOK_v1 renderer.

The pinned book implementation, decisions and historical ledger remain intact.
"""

from . import paper_book as book, paper_input_health


def render(rows, *, input_health=None):
    status = paper_input_health.unassessed() if input_health is None else input_health
    return paper_input_health.add_banner(book.render(rows), status)


def write_report(*, input_health=None):
    input_health = paper_input_health.load() if input_health is None else input_health
    book.REPORT.write_text(render(book.trades(), input_health=input_health), encoding="utf-8")
    return book.REPORT

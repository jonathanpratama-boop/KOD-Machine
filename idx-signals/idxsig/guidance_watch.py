"""Forward watch for full-year revenue guidance revisions (E10's event, prospective, paper only).

Pure functions, no network and no prices; a script feeds them SEC files. Nothing here trades: a RAISE it reports is
a candidate for a paper decision under a frozen paper policy, and that policy exists only if E10's recorded
historical test passes.

  1. form_index_8k(text): the 8-K / 8-K/A rows of an EDGAR daily form index (form.YYYYMMDD.idx).
  2. header_items(raw): the item codes in a full submission's SEC header ("ITEM INFORMATION" lines).
  3. revisions(state, release): compare a release's guidance (idxsig.guidance_v2, the audited extraction) with the
     issuer's latest earlier guidance of the same kind for the same fiscal year, exactly as research/E10/
     feasibility_a1.py does (5..200 days apart, +-50% mismatch guard), and return the events and the updated state.
"""

from __future__ import annotations

import re
from datetime import datetime

from idxsig import guidance_v2

ITEM_NAMES = {"Results of Operations and Financial Condition": "2.02"}
ITEM_LINE = re.compile(rb"ITEM INFORMATION:\s*([^\r\n]+)")
INDEX_ROW = re.compile(
    r"^(8-K(?:/A)?)\s+(.+?)\s+(\d{1,10})\s+(\d{8}|\d{4}-\d{2}-\d{2})\s+(edgar/data/\S+)\s*$"
)
MIN_GAP_DAYS = 5


def form_index_8k(text: str) -> list[dict]:
    """8-K and 8-K/A rows of a daily form index: form, company, cik, date filed, path of the full submission."""
    out = []
    for line in text.splitlines():
        m = INDEX_ROW.match(line.strip())
        if m:
            form, company, cik, filed, path = m.groups()
            filed = filed if "-" in filed else f"{filed[:4]}-{filed[4:6]}-{filed[6:]}"
            out.append(
                {
                    "form": form,
                    "company": company.strip(),
                    "cik": int(cik),
                    "filed": filed,
                    "path": path,
                }
            )
    return out


def header_items(raw: bytes) -> set[str]:
    """Item codes named in the header of a full submission text (only those this watch needs are mapped)."""
    head = raw[:20000]
    items = set()
    for m in ITEM_LINE.finditer(head):
        name = m.group(1).decode("utf-8", errors="replace").strip()
        if name in ITEM_NAMES:
            items.add(ITEM_NAMES[name])
    return items


def _key(cik: int, fy: int, kind: str) -> str:
    return f"{cik}|{fy}|{kind}"


def revisions(
    state: dict, cik: int, ticker: str, accession: str, acceptance_ny: str, texts: list[str]
) -> tuple[list[dict], dict]:
    """Events this release makes against `state` ({key: latest guidance}), and the state after it.

    One event per release, as in feasibility_a1.py: the latest fiscal year, dollar before growth. A change beyond
    +-50% is reported with class MISMATCH and is not a trade candidate."""
    found = guidance_v2.release_guidance(texts)
    t = datetime.fromisoformat(acceptance_ny)
    state = dict(state)
    events = []
    for (fy, kind), g in found.items():
        k = _key(cik, fy, kind)
        prev = state.get(k)
        if prev is not None:
            days = (t - datetime.fromisoformat(prev["acceptance_ny"])).days
            if MIN_GAP_DAYS <= days <= guidance_v2.v1.MAX_GAP_DAYS:
                old = guidance_v2.Guidance(fy, kind, prev["low"], prev["high"], prev["sentence"])
                ch = guidance_v2.level_change(g, old)
                if ch is not None:
                    cls = "MISMATCH" if abs(ch) > guidance_v2.MAX_CHANGE else guidance_v2.label(ch)
                    events.append(
                        {
                            "accession": accession,
                            "cik": cik,
                            "ticker": ticker,
                            "acceptance_ny": acceptance_ny,
                            "fiscal_year": fy,
                            "kind": kind,
                            "prior_accession": prev["accession"],
                            "old_mid": old.mid,
                            "new_mid": g.mid,
                            "level_change": ch,
                            "class": cls,
                            "old_sentence": prev["sentence"],
                            "new_sentence": g.sentence,
                        }
                    )
        state[k] = {
            "accession": accession,
            "acceptance_ny": acceptance_ny,
            "low": g.low,
            "high": g.high,
            "sentence": g.sentence,
        }
    events.sort(key=lambda e: (-e["fiscal_year"], e["kind"] != "dollar"))
    return events[:1], state

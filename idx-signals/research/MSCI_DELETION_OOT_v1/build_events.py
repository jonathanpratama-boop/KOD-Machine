"""MSCI_DELETION_OOT_v1: build events_all.csv for the reviews after the sealed IDX holdout (no price is read).

The parsing and classification are MSCI_DELETION_v1's (its frozen build_events.py helpers are imported unchanged): the
"MSCI INDONESIA INDEX" block of each public list, checked against MSCI's per-country summary row; announcement and
implementation dates from the press release; migrations matched on the IDX code from this study's ticker_map.csv.

    python3 research/MSCI_DELETION_OOT_v1/build_events.py [--check]      # from idx-signals/
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = ROOT / "data/manifests/msci_lists_oot-20261101T002157Z.jsonl"
_spec = importlib.util.spec_from_file_location(
    "v1_build_events", ROOT / "research/MSCI_DELETION_v1/build_events.py"
)
v1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v1)


def indonesia_block(doc: str) -> tuple[list[str], list[str]]:
    """Like v1's parser, but a block may continue after a page footer ('Page N ... MSCI ...'), where the column offset can
    shift: rows are split on runs of 2+ spaces, and a row that starts with deep indentation holds a deletion only."""
    lines = doc.splitlines()
    k = next((i for i, x in enumerate(lines) if x.strip() == "MSCI INDONESIA INDEX"), None)
    if k is None:
        return [], []
    head = lines[k + 1]
    if "Additions" not in head or "Deletions" not in head:
        raise ValueError("unexpected Indonesia block header")
    col = head.index("Deletions")
    adds, dels, i = [], [], k + 2
    while i < len(lines):
        x = lines[i]
        if not x.strip():
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(
                r"^\s*Page \d+\s", lines[j]
            ):  # page footer: the block continues after it
                i = j + 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines) and re.match(
                    r"^MSCI .* INDEX$", lines[i].strip()
                ):  # the next country's block
                    break
                continue
            break
        if len(x) - len(x.lstrip()) >= col - 4:  # deletion column only
            d = x.strip()
            if d != "None":
                dels.append(d)
        else:
            parts = re.split(r"\s{2,}", x.strip())
            if parts[0] != "None":
                adds.append(parts[0])
            if len(parts) > 1 and parts[1] != "None":
                dels.append(parts[1])
        i += 1
    return adds, dels


def main() -> int:
    recs = [json.loads(x) for x in MANIFEST.read_text().splitlines()[1:]]
    tmap = pd.read_csv(HERE / "ticker_map.csv")
    name2tick = dict(zip(tmap.msci_name, tmap.ticker))
    bad = [t for t in name2tick.values() if not re.fullmatch(r"[A-Z]{4}", str(t))]
    if bad:
        sys.exit(f"error: ticker_map.csv holds codes that are not IDX codes: {bad}")
    rows, unmapped = [], set()
    for review in dict.fromkeys(r["review"] for r in recs):
        files = {r["segment"]: ROOT / "data/raw" / r["file"] for r in recs if r["review"] == review}
        ann, impl = v1.pr_dates(v1.text(files["PR"]))
        blocks = {}
        for seg in ("ST", "SC"):
            doc = v1.text(files[seg])
            adds, dels = indonesia_block(doc)
            if (v1.indonesia_summary(doc) or (0, 0)) != (len(adds), len(dels)):
                sys.exit(
                    f"error: {review} {seg}: parsed Indonesia changes differ from MSCI's summary row"
                )
            blocks[seg] = (adds, dels)
        (st_add, st_del), (sc_add, sc_del) = blocks["ST"], blocks["SC"]
        for seg, adds, dels, other_adds in (
            ("ST", st_add, st_del, sc_add),
            ("SC", sc_add, sc_del, st_add),
        ):
            for side, names in (("ADD", adds), ("DEL", dels)):
                for n in names:
                    if n not in name2tick:
                        unmapped.add(n)
                    kind = "ADD"
                    if side == "DEL":
                        moved = name2tick.get(n) in {name2tick.get(x) for x in other_adds}
                        kind = (
                            ("ST_TO_SC" if moved else "ST_EXIT")
                            if seg == "ST"
                            else ("SC_TO_ST" if moved else "SC_EXIT")
                        )
                    rows.append(
                        {
                            "review": review,
                            "segment": seg,
                            "side": side,
                            "kind": kind,
                            "msci_name": n,
                            "ticker": name2tick.get(n, ""),
                            "announce_date": ann,
                            "implementation_close": impl,
                        }
                    )
    if unmapped:
        sys.exit(f"error: MSCI names without a ticker in ticker_map.csv: {sorted(unmapped)}")
    ev = pd.DataFrame(rows)
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        return 0 if ev.to_csv(index=False) == (HERE / "events_all.csv").read_text() else 1
    ev.to_csv(HERE / "events_all.csv", index=False)
    print(ev.groupby(["review", "segment", "side"]).size().unstack(fill_value=0).to_string())
    print(ev[ev.side == "DEL"].kind.value_counts().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())

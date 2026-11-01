"""MSCI_DELETION_OOT_v1 data: MSCI's public review lists and press releases for the reviews after KOD's sealed IDX holdout
(Feb 2025 .. Aug 2026), pinned in their own manifest. The 2024 reviews fall inside the sealed holdout and are not fetched.
Nothing here reads a price.

    python3 research/MSCI_DELETION_OOT_v1/collect.py        # from idx-signals/
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import utc_stamp

OUT = ROOT / "data/raw/msci"
REVIEWS = ("Feb25", "May25", "Aug25", "Nov25", "Feb26", "May26", "Aug26")
URL = {
    "ST": "https://app2.msci.com/eqb/gimi/stdindex/MSCI_{r}_STPublicList.pdf",
    "SC": "https://app2.msci.com/eqb/gimi/smallcap/MSCI_{r}_SCPublicList.pdf",
    "PR": "https://app2.msci.com/eqb/pressreleases/archive/MSCI_{r}_QIRPR.pdf",
}


def get(url: str) -> bytes:
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KOD-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if k == 3:
                raise
            time.sleep(2**k)
    raise RuntimeError("unreachable")


def main() -> int:
    if list((ROOT / "data/manifests").glob("msci_lists_oot-*.jsonl")):
        sys.exit("error: an OOT manifest exists already")
    started = utc_stamp().replace("-", "").replace(":", "")
    OUT.mkdir(parents=True, exist_ok=True)
    recs = []
    for r in REVIEWS:
        for seg, pat in URL.items():
            url = pat.format(r=r)
            body = get(url)
            if not body.startswith(b"%PDF"):
                raise RuntimeError(f"{url}: not a PDF")
            dest = OUT / (f"MSCI_{r}_QIRPR.pdf" if seg == "PR" else f"MSCI_{r}_{seg}PublicList.pdf")
            dest.write_bytes(body)
            recs.append(
                {
                    "review": r,
                    "segment": seg,
                    "url": url,
                    "file": str(dest.relative_to(ROOT / "data/raw")),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                }
            )
    man = ROOT / "data/manifests" / f"msci_lists_oot-{started}.jsonl"
    with man.open("x") as fh:
        fh.write(
            json.dumps(
                {
                    "type": "header",
                    "study": "MSCI_DELETION_OOT_v1",
                    "started": started,
                    "source": "MSCI public review lists (app2.msci.com/eqb)",
                    "files": len(recs),
                }
            )
            + "\n"
        )
        for x in recs:
            fh.write(json.dumps(x) + "\n")
    print(man.name, len(recs))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Turn full SEC companyfacts / submissions responses into the bounded offline fixtures in this folder (no network).

    python3 examples/companyfacts/trim.py <raw-dir> <fetch_log.json>

companyfacts: only the concepts KOD maps (kod/workstation/companyfacts.py CONCEPTS) are kept, each with its complete units arrays, so every JSON pointer
(/facts/<taxonomy>/<tag>/units/<unit>/<index>) is the same as in the full response. submissions: identity fields and the 10-K, 10-Q (and amendments) and 8-K
rows of filings.recent. The SHA-256 and size of each full response are recorded in SOURCES.json; the trimmed bytes are what the tests read.
"""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from kod.workstation.companyfacts import CONCEPTS  # noqa: E402

FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A", "8-K", "8-K/A"}
FIELDS = ("accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "form", "primaryDocument", "items")


def write(path, obj):
    path.write_bytes(gzip.compress(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode(), 9, mtime=0))


def main(raw_dir, log_path):
    raw_dir, log = Path(raw_dir), json.loads(Path(log_path).read_text())
    sources = []
    for ticker in sorted(k for k in log if "_" not in k):
        folder = HERE / ticker
        folder.mkdir(exist_ok=True)
        facts = json.loads((raw_dir / f"{ticker}_companyfacts.json").read_bytes())
        kept = {"cik": facts["cik"], "entityName": facts["entityName"], "facts": {}}
        for (taxonomy, tag) in sorted(CONCEPTS):
            if tag in facts["facts"].get(taxonomy, {}):
                kept["facts"].setdefault(taxonomy, {})[tag] = facts["facts"][taxonomy][tag]
        write(folder / "companyfacts.json.gz", kept)
        subs = json.loads((raw_dir / f"{ticker}_submissions.json").read_bytes())
        recent = subs["filings"]["recent"]
        rows = [i for i, form in enumerate(recent["form"]) if form in FORMS]
        trimmed = {k: subs.get(k) for k in ("cik", "name", "tickers", "exchanges", "sic", "sicDescription", "fiscalYearEnd", "entityType")}
        trimmed["filings"] = {"recent": {f: [recent[f][i] for i in rows] for f in FIELDS}}
        write(folder / "submissions.json.gz", trimmed)
        for kind, key in (("companyfacts", ticker), ("submissions", ticker + "_submissions")):
            entry = log[key]
            sources.append({"ticker": ticker, "kind": kind, "url": entry["url"], "observed_at": entry["observed_at"], "full_response_bytes": entry["bytes"],
                            "full_response_sha256": entry["sha256"], "fixture": f"{ticker}/{kind}.json.gz",
                            "fixture_sha256": hashlib.sha256((folder / f"{kind}.json.gz").read_bytes()).hexdigest()})
    (HERE / "SOURCES.json").write_text(json.dumps(sources, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])

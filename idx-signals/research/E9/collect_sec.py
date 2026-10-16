"""E9 step 2: fetch SEC EDGAR submissions for every issuer with an attempted signal (no price is read).

- Ticker -> CIK from https://www.sec.gov/files/company_tickers.json ("." read as "-").
- For each CIK: https://data.sec.gov/submissions/CIK##########.json plus every chunk file whose filing-date
  range overlaps 2020-06-01..2023-01-31.
- Every response is cached under data/raw/sec/<stamp>/ (gitignored) and listed with its sha256 in
  data/manifests/sec_submissions-<stamp>.jsonl. The User-Agent declares the owner's contact, read from
  the environment variable KOD_SEC_CONTACT; the address is never written to a file.

Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/E9/collect_sec.py
"""
import concurrent.futures as cf
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import catalyst  # noqa: E402
from idxsig.us_actions import SecClient, cik_map  # noqa: E402

E9 = ROOT / "research" / "E9"
SPAN = ("2020-06-01", "2023-01-31")


def main() -> int:
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    client = SecClient(f"KOD-Machine research {contact}", ROOT / "data" / "raw" / "sec" / stamp)
    sig = pd.read_csv(E9 / "entries" / "signals.csv", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    tickers = sorted(sig.loc[sig.j >= 0, "ticker"].unique())
    cmap = cik_map(client)
    rows = [{"ticker": t, "cik": cmap.get(t.upper().replace(".", "-"))} for t in tickers]
    ciks = sorted({r["cik"] for r in rows if r["cik"]})
    print(f"{len(tickers)} tickers, {len(ciks)} CIKs mapped", flush=True)

    def fetch(cik):
        st, body = client.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        if st != 200:
            return {"cik": cik, "main_status": st, "chunks_needed": None, "chunks_ok": 0}
        names = catalyst.chunk_names(body, *SPAN)
        ok = sum(client.get(f"https://data.sec.gov/submissions/{n}")[0] == 200 for n in names)
        return {"cik": cik, "main_status": st, "chunks_needed": len(names), "chunks_ok": ok, "chunk_names": names}

    status = []
    with cf.ThreadPoolExecutor(4) as ex:
        for k, r in enumerate(ex.map(fetch, ciks), 1):
            status.append(r)
            if k % 250 == 0:
                print(f"{k}/{len(ciks)}", flush=True)
    out = E9 / "sec"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / f"cik_map-{stamp}.csv", index=False)
    (out / f"fetch_status-{stamp}.json").write_text(json.dumps(status, indent=1))
    man = ROOT / "data" / "manifests" / f"sec_submissions-{stamp}.jsonl"
    with man.open("x") as f:
        f.write(json.dumps({"manifest": man.name, "source": "sec_edgar_submissions", "purpose": "E9 catalyst split",
                            "user_agent": "KOD-Machine research <owner-supplied contact; not recorded>",
                            "span": SPAN, "n_files": len(client.records)}) + "\n")
        for r in client.records:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    bad = [s for s in status if s["main_status"] != 200 or s["chunks_ok"] != s["chunks_needed"]]
    print(json.dumps({"stamp": stamp, "tickers": len(tickers), "ciks": len(ciks),
                      "unmapped_tickers": sum(1 for r in rows if not r["cik"]), "fetch_failures": len(bad),
                      "requests": len(client.records)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

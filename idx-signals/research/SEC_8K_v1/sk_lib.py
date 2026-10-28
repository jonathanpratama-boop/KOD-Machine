"""SEC_8K_v1 shared pieces: filing rows from an EDGAR submissions JSON, and the event table built from them."""
import json

import pandas as pd

SPAN = ("2020-12-01", "2023-09-29")
FORMS = {"8-K", "SC 13D", "SC 13D/A", "SC 13G", "S-3", "S-1", "424B5", "424B4", "424B3", "S-8", "DEF 14A", "NT 10-Q", "NT 10-K"}
ITEMS = ["1.01", "1.02", "1.03", "2.01", "2.02", "2.03", "2.04", "2.05", "2.06", "3.01", "3.02", "3.03", "4.01", "4.02", "5.01", "5.02", "5.03",
         "5.07", "7.01", "8.01"]


def rows(sub: dict) -> list[dict]:
    rec = sub["filings"]["recent"] if "recent" in sub.get("filings", {}) else sub
    n = len(rec["form"])
    acc = rec.get("acceptanceDateTime", [""] * n)
    items = rec.get("items", [""] * n)
    return [{"accession": rec["accessionNumber"][i], "form": rec["form"][i], "filing_date": rec["filingDate"][i], "acceptance": acc[i], "items": items[i] or ""}
            for i in range(n) if rec["form"][i] in FORMS and SPAN[0] <= rec["filingDate"][i] <= SPAN[1]]


def kinds(form: str, items: str) -> list[str]:
    if form == "8-K":
        its = {x.strip() for x in items.split(",")}
        return [f"8K_{i}" for i in ITEMS if i in its]
    if form.startswith("424B"):
        return ["OFFERING_424B"]
    return [form.replace(" ", "_").replace("/", "_")]


def events(filings: pd.DataFrame) -> pd.DataFrame:
    """One event per (ticker, kind, filing date); a kind repeated for the same name within 20 calendar days keeps the first.
    Stage 1 = filings 2021-01-04 .. 2022-12-30, stage 2 = 2023-01-03 .. 2023-09-29."""
    out = [{"ticker": r.ticker, "cik": r.cik, "public_date": r.filing_date, "kind": k, "accession": r.accession, "acceptance": r.acceptance}
           for r in filings.itertuples() for k in kinds(r.form, r.items)]
    ev = pd.DataFrame(out).drop_duplicates(["ticker", "kind", "public_date"]).sort_values(["ticker", "kind", "public_date"])
    d = pd.to_datetime(ev.public_date)
    keep, last = [], {}
    for (t, k), dd in zip(zip(ev.ticker, ev.kind), d):
        p = last.get((t, k))
        keep.append(p is None or (dd - p).days > 20)
        if keep[-1]:
            last[(t, k)] = dd
    ev = ev[keep].copy()
    ev["stage"] = 0
    ev.loc[ev.public_date.between("2021-01-04", "2022-12-30"), "stage"] = 1
    ev.loc[ev.public_date.between("2023-01-03", "2023-09-29"), "stage"] = 2
    return ev[ev.stage > 0].reset_index(drop=True)


def load_sub(body: bytes) -> dict:
    return json.loads(body)

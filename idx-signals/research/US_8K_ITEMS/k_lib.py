"""US_8K_ITEMS shared code (PROTOCOL.md): the event table from the 8-K list. Pure functions."""
import pandas as pd

ITEMS = ["1.01", "1.02", "2.02", "2.03", "3.02", "5.02", "5.07", "7.01", "8.01"]
CHAIN_DAYS, CHAIN_START = 30, "2020-07-01"
STAGES = {1: ("2021-01-04", "2022-12-30"), 2: ("2023-01-03", "2023-09-29")}


def build_events(f: pd.DataFrame) -> pd.DataFrame:
    """f: cik, ticker, accession, filing_date, items. One row per (filing, listed item of the nine); chained per issuer and item; staged by filing date."""
    rows = []
    for cik, tk, acc, d, items in zip(f.cik, f.ticker, f.accession, f.filing_date, f["items"].fillna("")):
        for it in {s.strip() for s in str(items).split(",")} & set(ITEMS):
            rows.append((it, cik, tk, acc, d))
    e = pd.DataFrame(rows, columns=["item", "cik", "ticker", "accession", "public_date"])
    e = e[e.public_date >= CHAIN_START].sort_values(["public_date", "cik", "item", "accession"]).reset_index(drop=True)
    last, keep = {}, []
    for it, cik, d in zip(e["item"], e.cik, pd.to_datetime(e.public_date)):
        prev = last.get((cik, it))
        ok = prev is None or (d - prev).days >= CHAIN_DAYS
        if ok:
            last[(cik, it)] = d
        keep.append(ok)
    e = e[keep].copy()
    e["stage"] = 0
    for k, (a, b) in STAGES.items():
        e.loc[(e.public_date >= a) & (e.public_date <= b), "stage"] = k
    return e[e.stage > 0].reset_index(drop=True)

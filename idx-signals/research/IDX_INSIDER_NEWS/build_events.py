"""IDX_INSIDER_NEWS step 5: build events.csv, the event table the study runs on, from labels.csv and articles.csv.gz. An article is an
event if the labeller called it INSIDER_BUY with confidence high or medium, it has an issuer ticker, and it was posted between
2021-02-15 and 2023-11-30 (WIB). No price is read. Refuses to overwrite.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/build_events.py"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FIRST, LAST = "2021-02-15", "2023-11-30"


def build(labels: pd.DataFrame, articles: pd.DataFrame) -> pd.DataFrame:
    a = articles.reset_index().rename(columns={"index": "item"})
    m = labels.merge(a[["item", "url", "title", "posted_wib", "html_sha256"]], on="item", how="left")
    day = m.posted_wib.str[:10]
    keep = ((m.cls == "INSIDER_BUY") & m.confidence.isin(["high", "medium"]) & m.issuer_ticker.notna() & (day >= FIRST) & (day <= LAST))
    ev = m[keep].sort_values(["posted_wib", "issuer_ticker"]).rename(columns={"issuer_ticker": "ticker"})
    return ev[["item", "ticker", "posted_wib", "title", "url", "buyer", "transaction_date", "confidence", "html_sha256"]].reset_index(drop=True)


def main() -> int:
    out = HERE / "events.csv"
    if out.exists():
        sys.exit("error: events.csv exists")
    ev = build(pd.read_csv(HERE / "labels.csv"), pd.read_csv(HERE / "articles.csv.gz"))
    ev.to_csv(out, index=False)
    print(f"{len(ev)} events -> {out.name}; by year: {ev.groupby(ev.posted_wib.str[:4]).size().to_dict()}; tickers: {ev.ticker.nunique()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

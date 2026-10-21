"""IDX_INSIDER_NEWS_OOT labelling and audit tools: test 23's batching, label collection, audit sampling and audit scoring on this study's files,
and the event builder with this study's window. Nothing about a price is read.
Usage (from idx-signals/), subcommands:
  tools.py batches --out DIR [--size 100]
  tools.py collect --answers DIR --batches DIR --out labels.csv
  tools.py audit-sample --labels labels.csv --blind blind.json --key key.csv
  tools.py audit-score --key key.csv --answers a.json b.json --out AUDIT.json
  tools.py events --labels labels.csv --out events.csv
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from oot_common import FIRST, HERE, LAST, load_old


def window_items(articles: pd.DataFrame) -> list[dict]:
    """The labelling items (title, posting time, first 700 characters): articles posted FIRST .. LAST (WIB)."""
    day = articles.posted_wib.fillna("").str[:10]
    inside = articles[(day >= FIRST) & (day <= LAST)]
    return load_old("make_batches").items(inside)


def build_events(labels: pd.DataFrame, articles: pd.DataFrame) -> pd.DataFrame:
    """INSIDER_BUY with confidence high or medium, an issuer ticker, posted FIRST .. LAST (WIB); no price is read."""
    a = articles.reset_index().rename(columns={"index": "item"})
    m = labels.merge(a[["item", "url", "title", "posted_wib", "html_sha256"]], on="item", how="left")
    day = m.posted_wib.str[:10]
    keep = (m.cls == "INSIDER_BUY") & m.confidence.isin(["high", "medium"]) & m.issuer_ticker.notna() & (day >= FIRST) & (day <= LAST)
    ev = m[keep].sort_values(["posted_wib", "issuer_ticker"]).rename(columns={"issuer_ticker": "ticker"})
    return ev[["item", "ticker", "posted_wib", "title", "url", "buyer", "transaction_date", "confidence", "html_sha256"]].reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("batches"); p.add_argument("--out", required=True); p.add_argument("--size", type=int, default=100)
    p = sub.add_parser("collect"); p.add_argument("--answers", required=True); p.add_argument("--batches", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("audit-sample"); p.add_argument("--labels", required=True); p.add_argument("--blind", required=True); p.add_argument("--key", required=True)
    p = sub.add_parser("audit-score"); p.add_argument("--key", required=True); p.add_argument("--answers", nargs=2, required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("events"); p.add_argument("--labels", required=True); p.add_argument("--out", required=True)
    args = ap.parse_args()
    articles = pd.read_csv(HERE / "articles.csv.gz")

    if args.cmd == "batches":
        its = window_items(articles)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for k in range(0, len(its), args.size):
            (out / f"batch_{k // args.size:03d}.json").write_text(json.dumps(its[k:k + args.size], ensure_ascii=False, indent=0))
        print(f"{len(its)} items in {-(-len(its) // args.size)} batches -> {out}")
    elif args.cmd == "collect":
        cl = load_old("collect_labels")
        expected = {it["item"] for f in Path(args.batches).glob("batch_*.json") for it in json.loads(f.read_text())}
        try:
            df = cl.merge(Path(args.answers), expected)
        except ValueError as exc:
            print("error:", exc)
            return 1
        if Path(args.out).exists():
            sys.exit("error: output exists")
        df.to_csv(args.out, index=False)
        print(f"{len(df)} labels -> {args.out}; classes: {df['cls'].value_counts().to_dict()}")
    elif args.cmd == "audit-sample":
        ase = load_old("audit_sample")
        labels = pd.read_csv(args.labels)
        s = ase.draw(labels)
        by_item = {it["item"]: it for it in window_items(articles)}
        blind = [{"item": int(r.audit_item), "title": by_item[r.item]["title"], "posted_wib": by_item[r.item]["posted_wib"],
                  "body": by_item[r.item]["body"]} for r in s.itertuples()]
        Path(args.blind).write_text(json.dumps(blind, ensure_ascii=False, indent=0))
        s[["audit_item", "item", "cls", "issuer_ticker", "confidence"]].to_csv(args.key, index=False)
        print(f"{len(blind)} items -> {args.blind}; key -> {args.key}")
    elif args.cmd == "audit-score":
        asc = load_old("audit_score")
        key = pd.read_csv(args.key)
        answers = []
        for p_ in args.answers:
            a = json.loads(Path(p_).read_text())
            rows = a["answers"] if isinstance(a, dict) else a
            answers.append((a.get("reviewer", Path(p_).stem) if isinstance(a, dict) else Path(p_).stem, pd.DataFrame(rows).rename(columns={"item": "audit_item"})))
        res = asc.score(key, answers)
        if Path(args.out).exists():
            sys.exit("error: output exists")
        Path(args.out).write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: res[k] for k in ("lower_precision", "audit_go", "kappa_between_reviewers")}, indent=1))
    else:
        out = Path(args.out)
        if out.exists():
            sys.exit("error: events.csv exists")
        ev = build_events(pd.read_csv(args.labels), articles)
        ev.to_csv(out, index=False)
        print(f"{len(ev)} events -> {out.name}; by year: {ev.groupby(ev.posted_wib.str[:4]).size().to_dict()}; tickers: {ev.ticker.nunique()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

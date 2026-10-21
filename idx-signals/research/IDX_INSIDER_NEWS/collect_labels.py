"""IDX_INSIDER_NEWS labelling, step 2: merge the labellers' answer files (one JSON list per batch, an object per item with item,
cls, issuer_ticker, buyer, transaction_date, confidence) into labels.csv, checking every item is answered exactly once with a
valid class and confidence. Usage: python3 collect_labels.py --answers <dir with labels_batch_*.json> --out labels.csv"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

CLASSES = {"INSIDER_BUY", "OPTION_OR_RIGHTS_EXERCISE", "OUTSIDE_INVESTOR_BUY", "COMPANY_ACQUIRES_STAKE", "BUYBACK", "SELL",
           "DENIAL_OR_RUMOR", "MARKET_FLOW", "OTHER"}
CONF = {"high", "medium", "low"}


def merge(answer_dir: Path, expected: set[int] | None = None) -> pd.DataFrame:
    rows, problems = [], []
    for f in sorted(answer_dir.glob("labels_batch_*.json")):
        for a in json.loads(f.read_text()):
            if a.get("cls") not in CLASSES or a.get("confidence") not in CONF:
                problems.append(f"{f.name} item {a.get('item')}: bad class or confidence")
            t = a.get("issuer_ticker")
            if t is not None and not (isinstance(t, str) and len(t) == 4 and t.isalpha() and t.isupper()):
                problems.append(f"{f.name} item {a.get('item')}: bad ticker {t!r}")
            rows.append({"item": int(a["item"]), "cls": a.get("cls"), "issuer_ticker": t, "buyer": a.get("buyer"),
                         "transaction_date": a.get("transaction_date"), "confidence": a.get("confidence"), "batch": f.name})
    df = pd.DataFrame(rows)
    if len(df) and df["item"].duplicated().any():
        problems.append(f"{int(df['item'].duplicated().sum())} items answered twice")
    if expected is not None:
        missing = expected - set(df["item"]) if len(df) else expected
        if missing:
            problems.append(f"{len(missing)} items not answered")
    if problems:
        raise ValueError("; ".join(problems[:10]) + (f" ... ({len(problems)} problems)" if len(problems) > 10 else ""))
    return df.sort_values("item").reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batches", help="the batch directory, to check coverage")
    args = ap.parse_args()
    expected = None
    if args.batches:
        expected = {it["item"] for f in Path(args.batches).glob("batch_*.json") for it in json.loads(f.read_text())}
    try:
        df = merge(Path(args.answers), expected)
    except ValueError as exc:
        print("error:", exc)
        return 1
    out = Path(args.out)
    if out.exists():
        sys.exit("error: output exists")
    df.to_csv(out, index=False)
    print(f"{len(df)} labels -> {out}; classes: {df['cls'].value_counts().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

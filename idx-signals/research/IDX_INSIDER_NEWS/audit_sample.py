"""IDX_INSIDER_NEWS audit, step 1 (LABELING.md): draw 45 items the labeller called INSIDER_BUY and 45 it called anything else
(seed 20261022), write the blind file reviewers see (item number, title, posting time, first 700 characters; no class) and the
key (kept out of the reviewers' reach). Usage: python3 audit_sample.py --labels labels.csv --blind <out.json> --key <out.csv>"""
import argparse
import json
from pathlib import Path

import pandas as pd

from make_batches import items

HERE = Path(__file__).resolve().parent
SEED, N_EACH = 20261022, 45


def draw(labels: pd.DataFrame) -> pd.DataFrame:
    ins = labels[labels.cls == "INSIDER_BUY"].sample(N_EACH, random_state=SEED)
    oth = labels[labels.cls != "INSIDER_BUY"].sample(N_EACH, random_state=SEED)
    s = pd.concat([ins, oth]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    s["audit_item"] = range(1, len(s) + 1)
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--blind", required=True)
    ap.add_argument("--key", required=True)
    args = ap.parse_args()
    labels = pd.read_csv(args.labels)
    s = draw(labels)
    by_item = {it["item"]: it for it in items(pd.read_csv(HERE / "articles.csv.gz"))}
    blind = [{"item": int(r.audit_item), "title": by_item[r.item]["title"], "posted_wib": by_item[r.item]["posted_wib"],
              "body": by_item[r.item]["body"]} for r in s.itertuples()]
    Path(args.blind).write_text(json.dumps(blind, ensure_ascii=False, indent=0))
    s[["audit_item", "item", "cls", "issuer_ticker", "confidence"]].to_csv(args.key, index=False)
    print(f"{len(blind)} items -> {args.blind}; key -> {args.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

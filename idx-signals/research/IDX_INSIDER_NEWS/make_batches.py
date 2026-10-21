"""IDX_INSIDER_NEWS labelling, step 1: split articles.csv.gz into batch files for the labellers (LABELING.md: title, posting
time, first 700 characters of the body; nothing else). Usage: python3 make_batches.py --out <dir> [--size 100]"""
import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BODY = 700


def items(df: pd.DataFrame) -> list[dict]:
    ok = df[(~df.failed.astype(bool)) & df.posted_wib.notna() & df.title.notna()]
    return [{"item": int(i), "title": r.title, "posted_wib": r.posted_wib[:16].replace("T", " "), "body": (r.body_head or "")[:BODY]}
            for i, r in ok.iterrows()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=100)
    args = ap.parse_args()
    df = pd.read_csv(HERE / "articles.csv.gz")
    its = items(df)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for k in range(0, len(its), args.size):
        (out / f"batch_{k // args.size:03d}.json").write_text(json.dumps(its[k:k + args.size], ensure_ascii=False, indent=0))
    print(f"{len(its)} items in {-(-len(its) // args.size)} batches -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

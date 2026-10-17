"""E10 audit, step 1 (AUDIT_PROCEDURE.md): write the reviewer's file from feasibility/audit_sample.csv, keeping only
what a reviewer may see. No ticker, accession, date, price or return.

Usage (from idx-signals/): python3 research/E10/audit_blind.py --out <path outside the repo>
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

E10 = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    s = pd.read_csv(E10 / "feasibility" / "audit_sample.csv")
    items = [{"item": i + 1, "fiscal_year": int(r.fiscal_year), "kind": r.kind, "assigned_direction": r["class"],
              "earlier_sentence": r.old_sentence, "later_sentence": r.new_sentence,
              "extracted_earlier_midpoint": float(r.old_mid), "extracted_later_midpoint": float(r.new_mid)}
             for i, (_, r) in enumerate(s.iterrows())]
    Path(args.out).write_text(json.dumps({"units": "dollar midpoints in USD millions; growth as a fraction (0.12 = 12%)",
                                          "items": items}, indent=1) + "\n")
    print(f"{len(items)} items -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

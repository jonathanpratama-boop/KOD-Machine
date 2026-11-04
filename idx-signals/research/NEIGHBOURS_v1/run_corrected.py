"""Additive causal repair. Never overwrites or silently reruns the original result.

python run_corrected.py --rows /path/to/rows.csv.gz --output /new/run/directory
No data download is performed. Read CORRECTION_2026-11-04.md before interpreting outputs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from idxsig.research_evaluation import NEIGHBOUR_MODELS, write_corrected_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = write_corrected_run(pd.read_csv(args.rows, parse_dates=["date"]), args.output,
                                 NEIGHBOUR_MODELS, source_paths=(args.rows,))
    print(f"Corrected research written: {result['rows_test']} prediction rows; promotion disabled")


if __name__ == "__main__":
    main()

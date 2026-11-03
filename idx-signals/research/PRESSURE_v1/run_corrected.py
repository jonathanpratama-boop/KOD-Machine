"""Additive causal repair; explicit existing inputs, new immutable output directory.

python run_corrected.py --rows /path/to/rows.csv.gz --taker /path/to/taker.csv.gz --output /new/run
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from idxsig.research_evaluation import PRESSURE_MODELS, add_pressure_features, write_corrected_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--taker", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = pd.read_csv(args.rows, parse_dates=["date"])
    taker = pd.read_csv(args.taker, parse_dates=["date"])
    result = write_corrected_run(add_pressure_features(rows, taker), args.output,
                                 PRESSURE_MODELS, source_paths=(args.rows, args.taker))
    print(f"Corrected research written: {result['rows_test']} prediction rows; promotion disabled")


if __name__ == "__main__":
    main()

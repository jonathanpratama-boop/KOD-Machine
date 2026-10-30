"""PREMOVE_SHADOW_v1: fit the shuffled-sequence control arm, once, on the 2020-2021 training rows (2022 calibration).

    python3 fit_control.py --panel <collection>/panel.csv.gz --collection <collection>/COLLECTION.json

The recipe is PR #19's sequence recipe unchanged (idxsig.premove_core.fit_model: summary features + 8 PCA components,
ridge 1, temperature chosen on 2022 by multiclass log loss) on rows whose 20-day windows were shuffled by
idxsig.premove_shadow.shuffle_windows. The same run refits the summary and sequence recipes on this re-collected
vintage and reports how closely they match PR #19's frozen models (the frozen ones are the trial's arms either way).
Writes control_model.json once. No 2023 or later row is read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import premove  # noqa: E402
from idxsig.premove_core import TARGETS, build_examples, fit_model  # noqa: E402
from idxsig.premove_shadow import FROZEN, shuffle_windows  # noqa: E402
from idxsig.provenance import sha256_file, utc_stamp  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "control_model.json"
TRAIN, CALIBRATION = ("2020-01-01", "2021-12-31"), ("2022-01-01", "2022-12-31")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--collection", required=True, type=Path)
    args = ap.parse_args()
    if OUT.exists():
        sys.exit("error: control_model.json exists; the control is fitted once")
    collection = json.loads(args.collection.read_text())
    panel_sha = sha256_file(args.panel)
    if collection.get("panel_sha256") != panel_sha:
        sys.exit("error: panel does not match its collection manifest")
    panel = pd.read_csv(args.panel)
    panel = panel[panel["date"] <= CALIBRATION[1]]  # nothing after 2022 is read
    examples = build_examples(panel)
    frame = examples.frame
    train = premove.period(frame, *TRAIN, known=True)
    calib = premove.period(frame, *CALIBRATION, known=True)
    frozen = json.loads(FROZEN.read_text())

    def fit(rows, seq):
        model = fit_model(rows, examples.feature_columns, seq, pca_components=8, ridge=1.0)
        if not all(model.converged):
            raise RuntimeError("fit did not converge")
        return model

    reproduction = {}
    for name, seq in (("summary", ()), ("sequence", examples.sequence_columns)):
        m = fit(train, seq)
        ref = np.asarray(frozen[name]["coefficients"])
        reproduction[name] = {"max_abs_coefficient_difference": float(np.abs(m.coefficients - ref).max()),
                              "reference_max_abs_coefficient": float(np.abs(ref).max())}
    shuffled_train = shuffle_windows(train)
    control = fit(shuffled_train, examples.sequence_columns)
    temperature, losses = premove.calibrate(control.predict(shuffle_windows(calib)), calib.loc[:, TARGETS].to_numpy())
    OUT.write_text(json.dumps({
        "arm": "shuffled", "fitted_at": utc_stamp(),
        "recipe": "PR #19 sequence recipe (premove_core.fit_model, 8 PCA components, ridge 1) on rows whose 20-day "
                  "windows were shuffled per row (premove_shadow.shuffle_windows); temperature by 2022 log loss",
        "train": {"period": TRAIN, "rows": int(len(train)),
                  "class_counts": {t: int(train[t].sum()) for t in TARGETS}},
        "calibration": {"period": CALIBRATION, "rows": int(len(calib)), "temperature": temperature,
                        "candidate_log_losses": losses},
        "panel": {"file": args.panel.name, "sha256": panel_sha, "collection_sha256": sha256_file(args.collection),
                  "collected_at": collection.get("collected_at"),
                  "same_bytes_as_pr19_input": panel_sha == "f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766", "pairs": int(panel["ticker"].nunique())},
        "reproduction_of_frozen_arms_on_this_vintage": reproduction,
        "model": control.record(),
    }, indent=1) + "\n")
    print(json.dumps({"rows": len(train), "temperature": temperature, "reproduction": reproduction}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

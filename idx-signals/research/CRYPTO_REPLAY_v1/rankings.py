"""CRYPTO_REPLAY_v1 step 1: rebuild the frozen 2023 rankings of PREMOVE_SEQUENCE_v1 and verify them, with no fitting.

The run's forecasts.csv.gz and shortlists.csv.gz are not in this repository (README: they sit in the owner's external
archive KOD-premove-results-20261030.tar.gz, sha256 cbdc58fd...). This script recomputes them from the same panel
(sha256 f1dfd57d..., checked) with the run's FROZEN coefficients (models.json) and calibration temperatures
(summary.json), and the shuffled control's frozen coefficients (PREMOVE_SHADOW_v1/control_model.json, fitted on
2020-2022 only). Nothing is fitted or tuned. The rebuild must reproduce summary.json exactly: the probability metrics
of both models on the 117,371 labelled rows and every shortlist count (alerts, hits, false alerts, censored,
episodes) for summary and sequence in both populations; otherwise the replay stops.

    python3 research/CRYPTO_REPLAY_v1/rankings.py --panel data/raw/premove/vintage-20261030/panel.csv.gz
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import premove, premove_shadow
from idxsig.premove_core import TARGETS, build_examples, prepare_panel
from idxsig.provenance import sha256_file, utc_stamp

RUN = ROOT / "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z"
PANEL_SHA256 = "f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766"
OUT = HERE / "rankings"
ARMS = ("summary", "sequence", "shuffled")


def ranked(pool: pd.DataFrame, arm: str, k: int = 5) -> pd.DataFrame:
    """premove.shortlist's rule for a model arm: highest upside probability, ties by ticker, top k per day."""
    p = pool.copy()
    p["rank_score"] = p[f"{arm}_up"]
    chosen = (
        p.sort_values(
            ["date", "rank_score", "ticker"], ascending=[True, False, True], kind="stable"
        )
        .groupby("date", sort=True)
        .head(k)
        .copy()
    )
    chosen["rank"] = chosen.groupby("date").cumcount() + 1
    chosen["method"] = arm
    return chosen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    args = ap.parse_args()
    manifest = json.loads((RUN / "MANIFEST.json").read_text())
    present = {}
    for name, entry in manifest["files"].items():
        path = RUN / name
        present[name] = (
            {"present": True, "sha256_matches": sha256_file(path) == entry["sha256"]}
            if path.exists()
            else {"present": False, "expected_sha256": entry["sha256"]}
        )
    if not all(v["sha256_matches"] for v in present.values() if v["present"]):
        sys.exit("error: a run artifact differs from MANIFEST.json")
    if sha256_file(args.panel) != PANEL_SHA256:
        sys.exit("error: the panel is not the run's input (sha256 mismatch)")

    summary = json.loads((RUN / "summary.json").read_text())
    protocol = json.loads((ROOT / "research/PREMOVE_SEQUENCE_v1/protocol.json").read_text())
    examples = build_examples(prepare_panel(pd.read_csv(args.panel), market="CRYPTO"))
    test = premove.period(examples.frame, *protocol["periods"]["test"])
    arms = premove_shadow.load_arms()  # refuses if any PREMOVE_SHADOW_v1 pin differs
    temps = premove_shadow.temperatures()
    shuffled_frame = premove_shadow.shuffle_windows(test)
    for arm, model in arms.items():
        frame = shuffled_frame if arm == "shuffled" else test
        p = premove.probabilities(model.predict(frame), temps[arm])
        for k, label in enumerate(("up", "down", "neither")):
            test[f"{arm}_{label}"] = p[:, k]

    checks = {}
    labelled = test.label_known
    y = test.loc[labelled, TARGETS].to_numpy()
    for arm in ("summary", "sequence"):
        got = premove.probability_metrics(
            test.loc[labelled, [f"{arm}_up", f"{arm}_down", f"{arm}_neither"]].to_numpy(), y
        )
        want = summary["probability_metrics"][arm]
        checks[f"probability_metrics/{arm}"] = {
            "rebuilt": got,
            "published": want,
            "match": got["n"] == want["n"]
            and all(
                abs(got[k] - want[k]) <= 1e-12 for k in ("log_loss", "brier_multiclass", "up_brier")
            ),
        }
    lists = []
    for population in ("all", "early"):
        pool = test if population == "all" else test.loc[(test.ret1 < 0.10) & (test.ret5 < 0.20)]
        pool = pool.copy()
        pool["episode_id"] = premove.episodes(pool)
        for arm in ARMS:
            chosen = ranked(pool, arm)
            if arm in ("summary", "sequence"):
                official = premove.shortlist(pool, arm, protocol["evaluation"]["top_k"])
                same_rows = (
                    official[["date", "ticker", "rank"]]
                    .reset_index(drop=True)
                    .equals(chosen[["date", "ticker", "rank"]].reset_index(drop=True))
                )
                metrics, _ = premove.alert_metrics(pool, official)
                want = summary["shortlists"][population][arm]
                checks[f"shortlist/{population}/{arm}"] = {
                    "same_rows_as_premove_shortlist": bool(same_rows),
                    "rebuilt": metrics,
                    "published": want,
                    "match": bool(same_rows) and metrics == want,
                }
            chosen["population"] = population
            lists.append(chosen)
    ok = all(c["match"] for c in checks.values())
    OUT.mkdir(exist_ok=True)
    cols = [
        "date",
        "ticker",
        "population",
        "method",
        "rank",
        "rank_score",
        "ret1",
        "ret5",
        "label_known",
        "up_first",
        "entry_date",
        "entry_open",
        "summary_up",
        "sequence_up",
        "shuffled_up",
    ]
    shortlists = pd.concat(lists, ignore_index=True)[cols]
    shortlists.to_csv(OUT / "shortlists_2023.csv.gz", index=False)
    forecasts = test[["date", "ticker", "summary_up", "sequence_up", "shuffled_up"]].sort_values(
        ["date", "ticker"]
    )
    digest = pd.util.hash_pandas_object(forecasts.round(15), index=False).values
    (OUT / "VERIFY.json").write_text(
        json.dumps(
            {
                "made_at": utc_stamp(),
                "verdict": "REBUILT RANKINGS MATCH THE PUBLISHED RUN"
                if ok
                else "MISMATCH: replay must not proceed",
                "run_artifacts": present,
                "panel_sha256": PANEL_SHA256,
                "test_rows": len(test),
                "labelled_rows": int(labelled.sum()),
                "decision_days": int(test.date.nunique()),
                "temperatures": temps,
                "checks": checks,
                "forecasts_rows_digest": str(int(np.bitwise_xor.reduce(digest.astype(np.uint64)))),
                "shortlists_sha256": sha256_file(OUT / "shortlists_2023.csv.gz"),
                "code_sha256": {
                    "rankings.py": sha256_file(Path(__file__)),
                    "premove.py": sha256_file(ROOT / "idxsig/premove.py"),
                    "premove_core.py": sha256_file(ROOT / "idxsig/premove_core.py"),
                    "premove_shadow.py": sha256_file(ROOT / "idxsig/premove_shadow.py"),
                },
                "note": "premove.py and premove_core.py differ in bytes from the run's recorded hashes only by formatting "
                "(commit 5534f49); their syntax trees are identical to commit 8c73b3a, whose files carry the recorded hashes.",
            },
            indent=1,
            default=str,
        )
        + "\n"
    )
    print(json.dumps({k: v["match"] for k, v in checks.items()}, indent=1))
    print("VERDICT:", "MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

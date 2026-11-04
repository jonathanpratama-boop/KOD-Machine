"""Post-run cross-check: corrected pick means averaged per rebalance, as the original runners did.

Written after the corrected results had been read, to explain one difference that REPORT.md
shows. It is not part of README.md's reading rule and changes no verdict.

The original runners (../NEIGHBOURS_v1/run.py, ../PRESSURE_v1/run.py) take one mean per
rebalance date and then average those means, so every rebalance weighs the same. The
corrected evaluator (idxsig.research_evaluation.score_picks) averages over all observed
picks, so a rebalance with more picks weighs more. The two agree for a method that picks five
coins at every rebalance. They differ for `all` (every eligible coin) and `strong_group` (one
to five coins).

For each pick method this prints the per-pick mean recorded in the corrected RESULT.json, the
per-rebalance mean recomputed from the corrected scored_selections.csv, and the original
per-rebalance mean copied from the frozen RESULT.json. Unknown outcomes stay out of each
rebalance's observed mean, as they stay out of the per-pick mean. A rebalance with no observed
pick is counted and left out of the average. Nothing is filled.

scored_selections.csv is not committed (it exceeds README.md's size limit). Each file read
must match the sha256 that its run's manifest.json pinned, and the per-pick mean recomputed
from it must equal the one in RESULT.json; otherwise the script stops.

    python3 idx-signals/research/RESEARCH_CORRECTIONS_20261104/per_rebalance.py [--outputs DIR]

DIR holds <study>/scored_selections.csv. The default is this folder, where a run writes them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
STUDIES = ("NEIGHBOURS_v1", "PRESSURE_v1")
SCORED = "scored_selections.csv"


def verified_bytes(path: Path, manifest: Path) -> bytes:
    if not path.is_file():
        raise SystemExit(
            f"missing {path}: {SCORED} is not committed; pass --outputs with a folder that "
            "holds the run outputs, or rerun the README.md command into a new folder"
        )
    pinned = json.loads(manifest.read_text())[SCORED]
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != pinned:
        raise SystemExit(f"{path}: sha256 {actual} differs from {pinned} pinned by {manifest}")
    return data


def observed_by_rebalance(data: bytes) -> dict[str, dict[str, list[float]]]:
    """Method -> rebalance date -> observed 3-day returns; an UNKNOWN pick adds no value."""
    picks: dict[str, dict[str, list[float]]] = {}
    for line, row in enumerate(csv.DictReader(io.StringIO(data.decode())), start=2):
        values = picks.setdefault(row["method"], {}).setdefault(row["date"], [])
        if row["outcome_state"] == "KNOWN":
            value = float(row["fwd3"])
            if not math.isfinite(value):
                raise SystemExit(
                    f"{SCORED} line {line}: KNOWN outcome {row['fwd3']!r} is not finite"
                )
            values.append(value)
        elif row["outcome_state"] != "UNKNOWN" or row["fwd3"] != "":
            raise SystemExit(
                f"{SCORED} line {line}: outcome_state {row['outcome_state']!r} "
                f"with fwd3 {row['fwd3']!r} is neither KNOWN nor an empty UNKNOWN"
            )
    return picks


def summary(method: str, rebalances: dict[str, list[float]], recorded: float) -> dict:
    observed = [v for values in rebalances.values() for v in values]
    if not observed:
        raise SystemExit(f"{method}: no observed pick, so no mean exists")
    per_pick = math.fsum(observed) / len(observed)
    if not math.isclose(per_pick, recorded, rel_tol=1e-9, abs_tol=1e-12):
        raise SystemExit(
            f"{method}: per-pick mean {per_pick!r} differs from RESULT.json {recorded!r}"
        )
    means = [math.fsum(v) / len(v) for v in rebalances.values() if v]
    return {
        "per_pick": recorded,
        "per_rebalance": math.fsum(means) / len(means),
        "rebalances": len(rebalances),
        "without_observed_pick": len(rebalances) - len(means),
    }


def pct(x: float | None) -> str:
    return "not recorded" if x is None else f"{100 * x:+.2f}%"


def row(*cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outputs", type=Path, default=HERE)
    args = parser.parse_args()
    for study in STUDIES:
        corrected = json.loads((HERE / study / "RESULT.json").read_text())["decisions"]
        original = json.loads((RESEARCH / study / "RESULT.json").read_text())["decisions"]
        data = verified_bytes(args.outputs / study / SCORED, HERE / study / "manifest.json")
        picks = observed_by_rebalance(data)
        if set(picks) != set(corrected):
            raise SystemExit(f"{study}: methods {sorted(picks)} differ from RESULT.json")
        names = ("Picks", "Per pick (corrected)", "Per rebalance (corrected)")
        names += ("Original per rebalance", "Rebalances", "Rebalances without an observed pick")
        print(f"### {study}\n\n{row(*names)}\n|---|---:|---:|---:|---:|---:|")
        for method in sorted(picks):
            s = summary(method, picks[method], corrected[method]["gross_observed_mean"])
            before = original.get(method, {}).get("gross_mean")
            means = (pct(s["per_pick"]), pct(s["per_rebalance"]), pct(before))
            print(row(method, *means, s["rebalances"], s["without_observed_pick"]))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Sharpe-kill ablation driver (reused-data diagnostic). Network absent.

Runs TREND_V2_SHARED in both frozen partitions of the published daily replay, using the engine in --engine.
It calls the engine's own replay.run_case() exactly as replay.main() does, for this one policy, with the same
partitions, inputs check (history_inputs.checked_local: 220 pinned archive hashes) and journal checks
(ReplayWriter.finish() replays every journal and compares state hashes). The canonical run's clearance gate is
not used, because this is a labelled diagnostic, not the canonical run.

  python3 run_challenger.py --engine challenger_engine --inputs DIR --output-dir NEW_DIR --label challenger

With --engine pointing at the published engine directory, this must reproduce the published TREND_V2_SHARED
journals byte for byte (the harness equivalence check recorded in FREEZE.json).
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

POLICY = "TREND_V2_SHARED"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--label", required=True)
    args = p.parse_args()
    engine = args.engine.resolve()
    sys.path.insert(0, str(engine))
    import daily_core as c
    import replay as r
    from history_inputs import checked_local
    for module in (c, r):
        if Path(module.__file__).resolve().parent != engine:
            raise SystemExit(f"engine import mismatch: {module.__file__}")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    pins = c.bundle_pins()
    history, quality = checked_local(args.inputs)
    r.save(args.output_dir / "INPUT_VALIDATION.json", quality)
    results = {}
    for partition, (start, end) in r.PARTITIONS.items():
        print("Running", args.label, partition, POLICY, flush=True)
        out = args.output_dir / f"{partition}_{POLICY}.jsonl"
        res = r.run_case(history, start, end, POLICY, out, quality["snapshot_sha256"])
        results[partition] = res
        r.save(args.output_dir / f"{partition}_{POLICY}_summary.json", res)
    r.save(args.output_dir / "RUN.json", {
        "label": args.label,
        "classification": "REUSED_DATA_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION",
        "engine_dir": str(engine),
        "source_pins": pins,
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_snapshot_sha256": quality["snapshot_sha256"],
        "partitions": r.PARTITIONS,
        "policy": POLICY,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    print("done", args.label, {k: v["journal"]["journal_sha256"][:16] for k, v in results.items()}, flush=True)


if __name__ == "__main__":
    main()

"""Verify the original E2-US inputs and run artifacts against their frozen hashes.

Checks, without modifying anything:
  1. yahoo_us-20261008T001812Z.jsonl: the manifest's own hash equals the one the panel manifest
     recorded as its input; every record's file exists with the recorded size and SHA-256.
  2. us_universe-20261008T001213Z.jsonl: the listing snapshot files.
  3. panel_us-20261008T004105Z: the panel file's SHA-256, and the hash the run recorded.
  4. results/runs/20261008T060443Z_MOONSHOT_E2_US_D1_v1: every file against RUNS.jsonl.

    python3 research/E2/repair/verify_inputs.py [--out FILE]

Exit status 0 only if nothing is missing or mismatched.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import read_manifest, sha256_file  # noqa: E402

RAW_MANIFEST = "yahoo_us-20261008T001812Z.jsonl"
UNIVERSE_MANIFEST = "us_universe-20261008T001213Z.jsonl"
PANEL_MANIFEST = "panel_us-20261008T004105Z.json"
RUN_ID = "20261008T060443Z_MOONSHOT_E2_US_D1_v1"


def check_records(manifest: Path) -> dict:
    header, records = read_manifest(manifest)
    missing, mismatched, size_mismatch, ok = [], [], [], 0
    for r in records:
        if not r.get("sha256"):
            continue
        path = ROOT / r["path"]
        if not path.exists():
            missing.append(r["path"])
            continue
        if "bytes" in r and path.stat().st_size != r["bytes"]:
            size_mismatch.append(r["path"])
        if sha256_file(path) != r["sha256"]:
            mismatched.append(r["path"])
        else:
            ok += 1
    statuses = {}
    for r in records:
        statuses[str(r.get("http_status", "n/a"))] = statuses.get(str(r.get("http_status", "n/a")), 0) + 1
    return {"manifest": manifest.name, "manifest_sha256": sha256_file(manifest), "header_n_files": header.get("n_files"),
            "records": len(records), "hashed_records": sum(1 for r in records if r.get("sha256")),
            "verified": ok, "missing": missing, "hash_mismatch": mismatched, "size_mismatch": size_mismatch,
            "http_status_counts": statuses}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write the report here (exclusive create)")
    args = ap.parse_args(argv)
    manifests = ROOT / "data" / "manifests"
    panel_meta = json.loads((manifests / PANEL_MANIFEST).read_text(encoding="utf-8"))
    report = {"raw": check_records(manifests / RAW_MANIFEST), "universe": check_records(manifests / UNIVERSE_MANIFEST)}
    report["raw"]["matches_panel_input_hash"] = (
        report["raw"]["manifest_sha256"] == panel_meta["inputs"][RAW_MANIFEST]["sha256"])
    panel_path = ROOT / panel_meta["panel"]
    panel_sha = sha256_file(panel_path) if panel_path.exists() else None
    run_line = next(json.loads(x) for x in (ROOT / "results" / "RUNS.jsonl").read_text().splitlines()
                    if json.loads(x)["run_id"] == RUN_ID)
    report["panel"] = {"manifest": PANEL_MANIFEST, "manifest_sha256": sha256_file(manifests / PANEL_MANIFEST),
                       "path": panel_meta["panel"], "exists": panel_path.exists(),
                       "bytes": panel_path.stat().st_size if panel_path.exists() else None,
                       "sha256": panel_sha, "recorded_sha256": panel_meta["sha256"],
                       "matches_manifest": panel_sha == panel_meta["sha256"],
                       "matches_run_record": panel_sha == run_line["panel_sha256"],
                       "rows": panel_meta["rows"], "tickers": panel_meta["tickers"], "sessions": panel_meta["sessions"]}
    run_dir = ROOT / run_line["dir"]
    report["run"] = {"run_id": RUN_ID, "code_commit": run_line["code_commit"],
                     "files": {name: {"recorded": sha, "actual": sha256_file(run_dir / name) if (run_dir / name).exists() else None}
                               for name, sha in run_line["files"].items()}}
    for f in report["run"]["files"].values():
        f["ok"] = f["recorded"] == f["actual"]
    problems = (len(report["raw"]["missing"]) + len(report["raw"]["hash_mismatch"]) + len(report["raw"]["size_mismatch"])
                + len(report["universe"]["missing"]) + len(report["universe"]["hash_mismatch"])
                + (not report["raw"]["matches_panel_input_hash"]) + (not report["panel"]["matches_manifest"])
                + (not report["panel"]["matches_run_record"]) + sum(not f["ok"] for f in report["run"]["files"].values()))
    report["problems"] = int(problems)
    report["verdict"] = "ALL ORIGINAL INPUTS PRESENT AND MATCHING" if not problems else "MISSING OR MISMATCHED INPUTS"
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "x", encoding="utf-8") as fh:
            fh.write(text)
    summary = {k: report["raw"][k] for k in ("records", "verified", "matches_panel_input_hash")}
    print(json.dumps({"raw": summary, "raw_missing": len(report["raw"]["missing"]),
                      "raw_mismatch": len(report["raw"]["hash_mismatch"]),
                      "universe_verified": report["universe"]["verified"], "panel_ok": report["panel"]["matches_manifest"],
                      "run_files_ok": all(f["ok"] for f in report["run"]["files"].values()),
                      "verdict": report["verdict"]}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

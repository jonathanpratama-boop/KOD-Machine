"""Run E6 Stage 1 (discovery, information gate) once. Refuses a dirty tree and an existing output.

Usage (from idx-signals/): python3 research/E6/run_discovery.py data/manifests/binance_1h-20261015T182940Z.jsonl
Writes research/E6/discovery/{summary.json, flags.csv.gz}.
"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import e6  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

OUT = ROOT / "research" / "E6" / "discovery"


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(manifest):
    if git("status", "--porcelain", "--", "idxsig", "research/E6", "tests/test_e6.py"):
        sys.exit("error: commit idxsig/, research/E6 and tests first so the results name the code that produced them")
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; discovery runs once")
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    h, meta = e6.load_manifest(Path(manifest))
    summary, table = e6.run_stage1(h, meta)
    summary.update({"protocol_id": "KOD-CRYPTO-E6-v1", "protocol_sha256": sha256_file(e6.PROTOCOL),
                    "manifest": meta["manifest"], "manifest_sha256": sha256_file(Path(manifest)),
                    "symbols_loaded": meta["symbols_loaded"], "last_hour_read": meta["last_hour"],
                    "code_commit": git("rev-parse", "HEAD"), "started": started,
                    "finished": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "claims": json.loads(e6.PROTOCOL.read_text())["claims"]})
    OUT.mkdir(parents=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    table.drop(columns=["coin", "day"]).to_csv(OUT / "flags.csv.gz", index=False)
    print(json.dumps({k: summary[k] for k in ("decision_days", "eligible_coin_days", "gates")}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])

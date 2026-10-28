"""Run E8 discovery (KOD-CRYPTO-E8-v1) once. Refuses a dirty tree and an existing output.

Usage (from idx-signals/): python3 research/E8/run_discovery.py data/manifests/binance_1h-20261015T182940Z.jsonl
Writes research/E8/discovery/{summary.json, events.csv.gz}. The regenerated warning list must equal the
committed feasibility_v1.1 list exactly, or the run stops before any outcome is computed.
"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import e8  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

E8 = ROOT / "research" / "E8"
OUT = E8 / "discovery"


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(manifest):
    if git("status", "--porcelain", "--", "idxsig", "research/E8", "tests/test_e8.py"):
        sys.exit("error: commit idxsig/, research/E8 and tests first so the result names the code that produced it")
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; discovery runs once")
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    h, meta = e8.load(Path(manifest))
    f = e8.features(h)
    L, P = e8.peer_events(h, f)
    sym = np.array(h.symbols)
    want = pd.read_csv(E8 / "feasibility_v1.1" / "peer_events.csv.gz")[["t", "peer", "leader"]]
    got = P.assign(peer=sym[P["peer"]], leader=sym[P["leader"]])[["t", "peer", "leader"]]
    if not want.reset_index(drop=True).equals(got.reset_index(drop=True)):
        sys.exit("error: warning list differs from feasibility_v1.1; no outcome computed")
    df = e8.score(h, f, P)
    rep = e8.report(df)
    dec = e8.gates(rep)
    summary = {"protocol_id": "KOD-CRYPTO-E8-v1", "stage": "discovery",
               "protocol_sha256": sha256_file(E8 / "protocol.json"),
               "manifest": meta["manifest"], "manifest_sha256": sha256_file(Path(manifest)),
               "last_hour_read": meta["last_hour"], "code_commit": git("rev-parse", "HEAD"),
               "warning_list_matches_feasibility_v1_1": True, "leader_triggers": int(len(L)),
               "report": rep, **dec, "started": started,
               "finished": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "claims": json.loads((E8 / "protocol.json").read_text())["claims"]}
    OUT.mkdir(parents=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    df.assign(peer=sym[df["peer"]], leader=sym[df["leader"]]).to_csv(OUT / "events.csv.gz", index=False)
    print(json.dumps({k: summary[k] for k in ("gates", "decision", "high_win_rate")}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])

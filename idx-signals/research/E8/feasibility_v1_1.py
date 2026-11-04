"""E8 feasibility re-run under FEASIBILITY_AMENDMENT_1.md (partial-correlation link, asset-backed tokens
excluded). Same script, spec and GO/NO-GO conditions as research/E8/feasibility.py; output goes to
research/E8/feasibility_v1.1/ and the original feasibility/ stays untouched. Computes no outcome.

Usage (from idx-signals/): python3 research/E8/feasibility_v1_1.py data/manifests/binance_1h-20261015T182940Z.jsonl
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import feasibility  # noqa: E402

feasibility.OUT = HERE / "feasibility_v1.1"

if __name__ == "__main__":
    feasibility.main(sys.argv[1])
    out = feasibility.OUT / "FEASIBILITY.json"
    res = json.loads(out.read_text())
    res["amendment"] = {"file": "research/E8/FEASIBILITY_AMENDMENT_1.md",
                        "sha256": feasibility.sha256_file(HERE / "FEASIBILITY_AMENDMENT_1.md")}
    out.write_text(json.dumps(res, indent=2, default=str))

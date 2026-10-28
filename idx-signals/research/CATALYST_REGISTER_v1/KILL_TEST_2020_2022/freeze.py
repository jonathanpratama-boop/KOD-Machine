"""KILL_TEST_2020_2022: write PINS.json, the sha256 of everything run.py depends on (PROTOCOL.md, protocol.json, the
code, events.csv.gz, the panel manifest and the harness modules it calls); run.py refuses to run if any differs.
Refuses over an existing PINS.json unless --replace (allowed only while no results/RESULT.json exists, e.g. after a
reviewed change to a pinned harness module).
Usage (from idx-signals/): python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/freeze.py [--replace]
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REL = "research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022"
PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
FILES = [f"{REL}/{n}" for n in ("PROTOCOL.md", "protocol.json", "kt_lib.py", "run.py", "collect.py", "events.csv.gz")] + [
    PROTOCOL["panel_manifest"],
    *(f"idxsig/{m}.py" for m in ("catalysts", "catalyst", "event_study", "idx_events", "execution", "controls", "market",
                                 "profiles", "backtest", "global_panel"))]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out = HERE / "PINS.json"
    if out.exists() and "--replace" not in sys.argv[1:]:
        sys.exit("error: PINS.json exists")
    if (HERE / "results" / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; the pins are final")
    meta = json.loads((ROOT / PROTOCOL["panel_manifest"]).read_text(encoding="utf-8"))
    if meta["sha256"] != PROTOCOL["panel_sha256"]:
        sys.exit("error: the panel manifest does not name the protocol's panel")
    pins = {"protocol_id": PROTOCOL["protocol_id"], "panel_sha256": meta["sha256"],
            "files": {p: sha(ROOT / p) for p in FILES}}
    out.write_text(json.dumps(pins, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(pins, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

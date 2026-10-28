"""KILL_TEST_2020_2022 (code v2, ADDENDUM_1.md): write PINS_v2.json, the sha256 of everything run_v2.py depends on
(PROTOCOL.md, protocol.json, ADDENDUM_1.md, the v2 code, events.csv.gz, the panel manifest and the harness modules it
calls); run_v2.py refuses to run if any differs. Refuses over an existing PINS_v2.json, and once results/RESULT.json
exists. research/ is append-only, so a committed PINS_v2.json is final.
Usage (from idx-signals/): python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/freeze_v2.py
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REL = "research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022"
PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
FILES = [f"{REL}/{n}" for n in ("PROTOCOL.md", "protocol.json", "kt_lib_v2.py", "run_v2.py", "ADDENDUM_1.md", "collect.py", "events.csv.gz")] + [
    PROTOCOL["panel_manifest"],
    *(f"idxsig/{m}.py" for m in ("catalysts", "catalyst", "event_study", "idx_events", "execution", "controls", "market",
                                 "profiles", "backtest", "global_panel"))]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out = HERE / "PINS_v2.json"
    if out.exists():
        sys.exit("error: PINS_v2.json exists")
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

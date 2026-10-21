"""IDX_INSIDER_NEWS_OOT step 7: write PINS.json (sha256 of events.csv, the panel, the registry and the code that runs), the inputs run.py
refuses to run without. Every code hash must already appear in PROTOCOL.md, which was committed before anything was fetched.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/freeze.py"""
import hashlib
import json
import sys

from oot_common import HERE, ROOT, load_old

CODE = ["idxsig/idx_events.py", "idxsig/execution.py", "idxsig/controls.py", "idxsig/market.py", "research/IDX_INSIDER_NEWS/run_v2.py"]


def main() -> int:
    out = HERE / "PINS.json"
    if out.exists():
        sys.exit("error: PINS.json exists")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    protocol = (HERE / "PROTOCOL.md").read_text()
    code = {p: sha(ROOT / p) for p in CODE}
    missing = [p for p, h in code.items() if h not in protocol]
    if missing:
        sys.exit(f"error: code differs from the hashes in PROTOCOL.md: {missing}")
    r2 = load_old("run_v2")
    _, _, meta = r2.load_inputs()
    pins = {"events_csv": sha(HERE / "events.csv"), "panel": meta["panel_sha256"], "registry": meta["registry_sha256"], "code": code}
    out.write_text(json.dumps(pins, indent=1) + "\n")
    print(json.dumps(pins, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

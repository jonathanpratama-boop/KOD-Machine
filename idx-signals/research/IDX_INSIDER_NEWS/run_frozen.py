"""IDX_INSIDER_NEWS: the single recorded run of PROTOCOL.md. Pins the three inputs by sha256 (events.csv, the IDX panel, the corporate-action
registry) and calls run_v2.main(), which refuses a second run. run_v2.py is committed and cannot be edited, so the pins live here.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/run_frozen.py
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "events_csv": "bb28119fa7653da8baf3523157fd9378ef9c8f7a40b61fef1822958fd301c9dd",
    "panel": "9d3a0718c95f9e885c4f8310cf68bf5e75021c366c454f73389d7fae75c02877",
    "registry": "659da375e4586deab958e22dc242d7be6966ebc226bfefe8ce7ce85eb51f1e6c",
}

if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("idxnews_run_v2", HERE / "run_v2.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    run.EXPECTED = EXPECTED
    sys.exit(run.main())

"""IDX_INSIDER_NEWS: the corrected run of PROTOCOL.md under ADDENDUM_1.md (the recorded run in results/ lost 75 control means to a NaN sum in
idxsig.idx_events). Same code and pins as run_frozen.py, writing results_corrected/. Refuses to start without the corrected aggregation and
refuses a second run.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/run_corrected.py
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
EXPECTED = {
    "events_csv": "bb28119fa7653da8baf3523157fd9378ef9c8f7a40b61fef1822958fd301c9dd",
    "panel": "9d3a0718c95f9e885c4f8310cf68bf5e75021c366c454f73389d7fae75c02877",
    "registry": "659da375e4586deab958e22dc242d7be6966ebc226bfefe8ce7ce85eb51f1e6c",
}

if __name__ == "__main__":
    from idxsig import idx_events

    if not hasattr(idx_events, "mean_over_scored"):
        sys.exit("error: idxsig.idx_events lacks the corrected control-mean aggregation")
    spec = importlib.util.spec_from_file_location("idxnews_run_v2", HERE / "run_v2.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    run.EXPECTED = EXPECTED
    run.OUT = HERE / "results_corrected"
    sys.exit(run.main())

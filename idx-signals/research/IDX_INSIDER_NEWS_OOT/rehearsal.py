"""IDX_INSIDER_NEWS_OOT rehearsal: run.py pointed at test 23's own window, events and panel (in a temporary directory, nothing of this study
is touched) must reproduce test 23's corrected result exactly. Run before the real run; writes rehearsal/REHEARSAL.json.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/rehearsal.py"""
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

from oot_common import HERE, OLD, ROOT, load_old


def main() -> int:
    out = HERE / "rehearsal" / "REHEARSAL.json"
    if out.exists():
        sys.exit("error: rehearsal/REHEARSAL.json exists")
    spec = importlib.util.spec_from_file_location("idxnews_oot_run", HERE / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    r2 = load_old("run_v2")
    tmp = Path(tempfile.mkdtemp(prefix="oot_rehearsal_"))
    try:
        shutil.copy(OLD / "events.csv", tmp / "events.csv")
        pins = {"events_csv": r2.sha_file(OLD / "events.csv"), "panel": None, "registry": None, "code": {}}
        _, _, meta = r2.load_inputs()
        pins["panel"], pins["registry"] = meta["panel_sha256"], meta["registry_sha256"]
        pins["code"] = {p: run.sha_file(ROOT / p) for p in ("idxsig/idx_events.py", "idxsig/execution.py", "idxsig/controls.py", "idxsig/market.py",
                                                             "research/IDX_INSIDER_NEWS/run_v2.py")}
        (tmp / "PINS.json").write_text(json.dumps(pins))
        run.HERE, run.OUT = tmp, tmp / "results"
        run.START, run.END, run.FIRST, run.LAST, run.SEALED_END = "2021-01-22", "2023-12-29", "2021-02-15", "2023-11-30", "2020-12-31"
        run.main()
        got = json.loads((tmp / "results" / "RESULT.json").read_text())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ref = json.loads((OLD / "results_corrected" / "RESULT.json").read_text())
    keys = ("n", "mean_net", "winsorised_net", "median_net", "hit_rate", "mean_control", "mean_excess", "t_excess", "lo95_excess", "hi95_excess", "clusters")
    diffs = {k: [got["primary_hold_20"][k], ref["primary_hold_20"][k]] for k in keys if abs(got["primary_hold_20"][k] - ref["primary_hold_20"][k]) > 1e-12}
    grid_diffs = [(a["hold"], k) for a, b in zip(got["grid"], ref["grid"]) for k in ("n", "mean_net", "mean_excess", "t_excess") if abs(a[k] - b[k]) > 1e-12]
    rec = {"reproduces_test_23_corrected_run": not diffs and not grid_diffs and got["verdict"] == "PASS", "primary_differences": diffs,
           "grid_differences": grid_diffs, "n": got["primary_hold_20"]["n"], "t_excess": got["primary_hold_20"]["t_excess"]}
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 0 if rec["reproduces_test_23_corrected_run"] else 1


if __name__ == "__main__":
    sys.exit(main())

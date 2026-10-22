"""US_INSIDER_BUY rehearsal on the real US panel with PLACEBO events (random tickers, random dates in the Stage 1 window, random role and size labels): the run's whole computation
(run.compute) and the verifier's independent trade recomputation (verify.check_trades) must agree on every scored trade of every hold, and the mean excess of random events must be
about zero with the gates failing. Nothing here is a hypothesis test and no Form 4 is used. Writes rehearsal/REHEARSAL.json.
Usage (from idx-signals/): python3 research/US_INSIDER_BUY/rehearsal.py"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from idxsig import event_study as es, global_panel  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(f"uib_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    out = HERE / "rehearsal" / "REHEARSAL.json"
    if out.exists():
        sys.exit("error: rehearsal/REHEARSAL.json exists")
    run, ver = load("run"), load("verify")
    df, meta = global_panel.load(run.PANEL_MANIFEST)
    prep = es.prepare_us(df, run.START, run.END)
    rng = np.random.default_rng(20261022)
    names = df.groupby("ticker").size()
    names = names[names >= 600].index.to_numpy()
    n = 2500
    dates = pd.Timestamp("2021-01-04") + pd.to_timedelta(rng.integers(0, 720, n), unit="D")
    officer = rng.random(n) < 0.7
    ev = pd.DataFrame({"ticker": rng.choice(names, n), "public_date": dates.strftime("%Y-%m-%d"), "stage": 1, "top_exec": rng.random(n) < 0.35,
                       "total_value": np.exp(rng.uniform(np.log(50_000), np.log(3_000_000), n)), "officer": officer, "director": ~officer | (rng.random(n) < 0.3),
                       "lag_days": rng.integers(0, 6, n)})
    t0 = time.time()
    res, results = run.compute(prep, ev, 1, {}, go_check=False)
    seconds = time.time() - t0
    n_checked, worst, bad = {}, 0.0, []
    for h, r in results.items():
        k, w, b = ver.check_trades(r, ROOT / meta["panel"], h)
        n_checked[h], worst, bad = k, max(worst, w), bad + [f"hold {h}: {m}" for m in b]
    rec = {"placebo_events": n, "scored": res["events"]["scored"], "status_counts": res["events"]["status_counts"], "trades_recomputed_by_hold": n_checked,
           "max_abs_net_return_difference": worst, "verifier_mismatches": bad[:10], "n_mismatches": len(bad), "placebo_excess": res["excess"],
           "gates": res["gates"], "verdict": res["verdict"], "seconds": round(seconds)}
    rec["machinery_ok"] = bool(not bad and n_checked[60] > 1000 and worst < 1e-9 and res["verdict"] == "FAIL" and abs(res["excess"]["t"]) < 3.0)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(json.dumps(rec, indent=1, default=float))
    return 0 if rec["machinery_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

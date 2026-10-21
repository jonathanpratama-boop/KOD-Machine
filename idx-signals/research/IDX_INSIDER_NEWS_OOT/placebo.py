"""IDX_INSIDER_NEWS_OOT, post-hoc calibration of the instrument (written and run AFTER the registered result; it cannot change the verdict).
Question: in the TIER_3 window (Yahoo, survivor-only, no market-cap bucket), does the harness give an excess near zero for events that carry no
information? Each real event keeps its posting time; its ticker is replaced by a random name that could be bought at that session (traded, at
least 60 sessions of history). The same configuration, 200 -> 100 control draws, the same statistics. K random replacements per window. The same
is done on test 23's window (TIER_1) for comparison. Reports the mean of the mean excess over the K replacements, its spread, and how often
t >= 1.65 or t <= -1.65 occurs. Nothing here is registered or counted.
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/placebo.py"""
import json
import sys

import numpy as np
import pandas as pd

from oot_common import END, HERE, OLD, ROOT, START, load_old

sys.path.insert(0, str(ROOT))
from idxsig import idx_events  # noqa: E402

K, DRAWS = 8, 100
WINDOWS = {"tier3_2025_26": (START, END, HERE / "events.csv"), "tier1_2021_23": ("2021-01-22", "2023-12-29", OLD / "events.csv")}


def main() -> int:
    out = HERE / "placebo" / "PLACEBO.json"
    if out.exists():
        sys.exit("error: placebo/PLACEBO.json exists")
    r2 = load_old("run_v2")
    df, reg, _ = r2.load_inputs()
    res = {}
    for name, (start, end, path) in WINDOWS.items():
        prep = idx_events.prepare(df, reg, start, end)
        ev = pd.read_csv(path)
        sig = np.array([-1 if (s := idx_events.signal_session(prep.m.dates, pd.Timestamp(p))) is None else s for p in ev.posted_wib])
        rows = []
        for k in range(K):
            rng = np.random.default_rng(20261100 + k)
            tick = []
            for s in sig:
                pool = np.flatnonzero(prep.evaluable[:, s]) if s >= 0 else np.array([], dtype=int)
                tick.append(prep.m.tickers[rng.choice(pool)] if len(pool) else None)
            plc = ev.assign(ticker=tick).dropna(subset=["ticker"])
            r = idx_events.run_events(prep, plc, r2.config(r2.PRIMARY), draws=DRAWS, seed=r2.SEED + k)
            f = idx_events.filled(r)
            st = r2.summarize(f, r2.BOOT_SEED + k)
            rows.append({"n": st["n"], "mean_net": st["mean_net"], "mean_control": st["mean_control"], "mean_excess": st["mean_excess"], "t_excess": st["t_excess"]})
        t = pd.DataFrame(rows)
        res[name] = {"replacements": K, "mean_n": float(t.n.mean()), "mean_of_mean_excess": float(t.mean_excess.mean()), "sd_of_mean_excess": float(t.mean_excess.std(ddof=1)),
                     "mean_of_mean_net": float(t.mean_net.mean()), "mean_of_mean_control": float(t.mean_control.mean()),
                     "share_t_ge_1.65": float((t.t_excess >= 1.65).mean()), "share_t_le_-1.65": float((t.t_excess <= -1.65).mean()), "per_replacement": rows}
        print(name, {k: round(v, 4) for k, v in res[name].items() if k not in ("per_replacement", "replacements")}, flush=True)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

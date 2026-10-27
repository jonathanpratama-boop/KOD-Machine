"""SEC_8K_v1: `--stage 1` (discovery, filings 2021-01-04 .. 2022-12-30): every filing kind with >= 100 scored events at hold 60, 200 matched control draws, week-cluster
bootstrap t; a kind is selected if |t| clears Bonferroni over (kinds x 2 holds) at 5% two-sided AND |mean excess| >= 2% at hold 60 AND hold 20 has the same sign.
Writes stage1.csv and selection.json. `--stage 2` (holdout, filings 2023-01-03 .. 2023-09-29) runs only the selected kinds once; a kind PASSES if its hold-60 mean
excess has the selected sign with t >= 1.65 in that direction and |mean| >= 1%. Writes stage2.csv and RESULT.json. Each stage runs once.
Usage (from idx-signals/): python3 research/SEC_8K_v1/run.py --stage 1"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "US_INSIDER_BUY"))
from idxsig import event_study as es, global_panel  # noqa: E402
import ib_stats as st  # noqa: E402
import sk_lib  # noqa: E402

PANEL = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
HOLDS, MIN_N, DRAWS, SEED = (20, 60), 100, 200, 20261027


def boot(f: pd.DataFrame) -> dict:
    w = st.week_id(f.entry_date)
    return st.Boot(w, 10_000, 20261203).mean(f.excess, w)


def run_kind(prep, g: pd.DataFrame) -> dict:
    row = {"kind": g.kind.iloc[0]}
    for h in HOLDS:
        f = st.scored(es.run_events(prep, g, es.us_config(h), draws=DRAWS, seed=SEED))
        b = boot(f) if len(f) >= 10 else {"n": len(f), "mean": float("nan"), "t": float("nan")}
        row.update({f"n{h}": b["n"], f"mean{h}": b["mean"], f"t{h}": b["t"], f"median{h}": float(f.excess.median()) if len(f) else float("nan"),
                    f"wins{h}": st.winsor_mean(f.excess) if len(f) >= 10 else float("nan")})
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    stage = ap.parse_args().stage
    out = HERE / f"stage{stage}.csv"
    if out.exists():
        sys.exit(f"error: {out.name} exists; this stage runs once")
    ev = sk_lib.events(pd.read_csv(HERE / "filings.csv.gz", dtype={"ticker": str, "items": str}, keep_default_na=False))
    ev = ev[ev.stage == stage]
    df, meta = global_panel.load(PANEL)
    prep = es.prepare_us(df, "2020-06-01", "2023-12-29")
    if stage == 2:
        sel = json.loads((HERE / "selection.json").read_text())
        ev = ev[ev.kind.isin(sel["selected"])]
    rows = [run_kind(prep, g) for _, g in ev.groupby("kind") if len(g) >= (MIN_N if stage == 1 else 1)]
    t = pd.DataFrame(rows).sort_values("t60")
    t.to_csv(out, index=False)
    if stage == 1:
        t = t[t.n60 >= MIN_N]
        m = 2 * len(t)
        z = float(norm.ppf(1 - 0.025 / m))
        ok = (t.t60.abs() >= z) & (t.mean60.abs() >= 0.02) & ((t.mean20 > 0) == (t.mean60 > 0))
        sel = {"tests": m, "bonferroni_z": z, "selected": t[ok].kind.tolist(), "sign": {k: (1 if v > 0 else -1) for k, v in zip(t[ok].kind, t[ok].mean60)},
               "panel_sha256": meta["sha256"]}
        (HERE / "selection.json").write_text(json.dumps(sel, indent=1) + "\n")
        print(t.round(4).to_string(index=False)); print(json.dumps(sel, indent=1))
    else:
        sign = sel["sign"]
        verdict = {r.kind: bool(sign[r.kind] * r.t60 >= 1.65 and sign[r.kind] * r.mean60 >= 0.01) for r in t.itertuples()}
        res = {"experiment": "SEC_8K_v1", "stage": 2, "label": "historical research only; survivor-only prices", "per_kind": verdict,
               "table": t.to_dict("records"), "panel_sha256": meta["sha256"]}
        (HERE / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
        print(t.round(4).to_string(index=False)); print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

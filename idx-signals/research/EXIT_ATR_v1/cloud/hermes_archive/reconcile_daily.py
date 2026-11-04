"""EXIT-ATR-v1 data check: is a crypto panel rebuilt from the 2026-10-13 Binance pull equivalent to E2's
pinned panel (2026-10-08, sha256 3dc12749...) over the E2 discovery period?

E2's pinned panel and its raw files are not on this machine. This script reruns E2's own discovery code
(e1.Study with the E2 protocol, the CRYPTO profile and the moonshot_g family, exactly as `idxsig
e2-discovery` builds it) on the rebuilt panel. It writes ONLY to research/EXIT_ATR_v1/data_check/
e2_discovery_repro/ and never to research/E2/. It then compares the result with E2's committed discovery
outputs:
  summary.json eligible_ticker_days; detector_selection.csv (every rule's flag and hit counts);
  episodes_E30/E50/E100.csv (exact rows).
No return or trading outcome is computed. No 2023+ data is used (the Study cuts the market at the
validation end, and discovery covers 2020-07-01..2022-12-31).
Usage (from idx-signals/): ../.venv/bin/python research/EXIT_ATR_v1/reconcile_daily.py data/manifests/<rebuilt panel>.json
"""
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import os

HERE = Path(__file__).resolve().parents[2]  # this branch's idx-signals/: E2's committed outputs, our outputs
# E2's discovery code (commit a155cf0, panel-global-v1) runs from a detached worktree; default is this branch.
ROOT = Path(os.environ.get("KOD_CODE_ROOT", HERE)).resolve()
sys.path.insert(0, str(ROOT))
from idxsig import e1, global_panel  # noqa: E402
from idxsig.profiles import PROFILES  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

E2 = HERE / "research" / "E2" / "CRYPTO" / "discovery"
OUT = HERE / "research" / "EXIT_ATR_v1" / "data_check"


def main(manifest: Path) -> int:
    df, meta = global_panel.load(manifest)
    proto_path = ROOT / "research" / "E2" / "protocol.json"
    study = e1.Study(df, meta, protocol_path=proto_path, profile=PROFILES["CRYPTO"], family_module=moonshot_g)
    rep_dir = OUT / "e2_discovery_repro"
    summary = e1.run_discovery(study, rep_dir)
    orig = json.loads((E2 / "summary.json").read_text())
    checks = {"eligible_ticker_days": {"e2": orig["eligible_ticker_days"], "rebuilt": summary.get("eligible_ticker_days")}}
    sel_o = pd.read_csv(E2 / "detector_selection.csv")
    sel_r = pd.read_csv(rep_dir / "detector_selection.csv")
    cols = ["rule", "flags", "E30_hits", "E50_hits", "E100_hits"]
    m = sel_o[cols].merge(sel_r[cols], on="rule", suffixes=("_e2", "_rebuilt"), how="outer")
    checks["detector_selection"] = m.to_dict(orient="records")
    sel_equal = all(int(r[f"{c}_e2"]) == int(r[f"{c}_rebuilt"]) for r in checks["detector_selection"] for c in cols[1:])
    ep = {}
    for k in ("E30", "E50", "E100"):
        a = pd.read_csv(E2 / f"episodes_{k}.csv")
        b = pd.read_csv(rep_dir / f"episodes_{k}.csv")
        same_cols = list(a.columns) == list(b.columns)
        ep[k] = {"e2_rows": len(a), "rebuilt_rows": len(b), "same_columns": same_cols,
                 "identical_rows": bool(same_cols and len(a) == len(b) and a.astype(str).equals(b.astype(str)))}
        if same_cols and {"ticker", "date"} <= set(a.columns):
            ka = set(zip(a["ticker"], a["date"].astype(str)))
            kb = set(zip(b["ticker"], b["date"].astype(str)))
            ep[k].update({"only_in_e2": sorted(ka - kb)[:20], "only_in_rebuilt": sorted(kb - ka)[:20],
                          "n_only_in_e2": len(ka - kb), "n_only_in_rebuilt": len(kb - ka)})
    checks["episodes"] = ep
    verdict = (checks["eligible_ticker_days"]["e2"] == checks["eligible_ticker_days"]["rebuilt"] and sel_equal
               and all(v["identical_rows"] for v in ep.values()))
    result = {
        "question": "Is the rebuilt panel equivalent to E2's pinned panel over E2 discovery?",
        "verdict": "EQUIVALENT_FOR_DISCOVERY" if verdict else "NOT_EQUIVALENT",
        "rebuilt_panel_manifest": manifest.name, "rebuilt_panel_sha256": meta["sha256"],
        "rebuilt_manifest_sha256": sha256_file(manifest), "e2_pinned_panel_sha256": orig["panel_sha256"],
        "checks": checks,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "note": "Reproduction of E2's committed discovery outputs, not a byte match of the pinned panel. No returns computed.",
    }
    (OUT / "RECONCILE_DAILY.json").write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: result[k] for k in ("verdict", "rebuilt_panel_sha256")}, indent=1),
          json.dumps(checks["eligible_ticker_days"]), json.dumps({k: {x: v[x] for x in ("e2_rows", "rebuilt_rows", "identical_rows")} for k, v in ep.items()}))
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))

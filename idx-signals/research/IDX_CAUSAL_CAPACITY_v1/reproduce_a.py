"""Step 1 of PROTOCOL.md: rerun fill model A in memory on the current code and check it reproduces
the evidence run 20261008T000401Z_MOONSHOT_E1_D1_v1.1. Writes nothing to results/runs/.

    python3 research/IDX_CAUSAL_CAPACITY_v1/reproduce_a.py   (from idx-signals/)"""

import gzip
import io
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from idxsig import corporate_actions  # noqa: E402
from idxsig.backtest import RunConfig, run  # noqa: E402
from idxsig.panel import load  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

EVIDENCE = ROOT / "results" / "runs" / "20261008T000401Z_MOONSHOT_E1_D1_v1.1"
STATS = ("rule_trades", "random", "random_matched", "signals", "universe", "by_year")


def config(fill_model: str, recorded: dict) -> RunConfig:
    c = recorded["config"]
    return RunConfig(market="IDX", rule_id=c["rule_id"], start=c["start"], end=c["end"],
                     holding_days=c["holding_days"], entry_lag=c["entry_lag"], notional=c["notional"],
                     max_participation=c["max_participation"], fee_buy=c["fee_buy"], fee_sell=c["fee_sell"],
                     overlap=c["overlap"], random_draws=c["random_draws"], seed=c["seed"],
                     data_end_exit=c["data_end_exit"], ca_mode=c["ca_mode"], lookahead_cuts=c["lookahead_cuts"],
                     controls_version=c["controls_version"], fill_model=fill_model)


def inputs(recorded: dict):
    manifest = ROOT / "data" / "manifests" / ("panel-" + Path(recorded["panel"]["panel"]).name.split("panel-")[1]
                                              .replace(".csv.gz", ".json"))
    df, meta, _ = load(manifest)
    meta["_manifest_sha256"] = sha256_file(manifest)
    assert meta["sha256"] == recorded["panel"]["panel_sha256"], "panel differs from the evidence run"
    reg = corporate_actions.load(ROOT / "data" / "manifests" /
                                 recorded["corporate_action_model"]["registry_manifest"],
                                 panel_sha256=meta["sha256"])
    assert reg[1]["sha256"] == recorded["corporate_action_model"]["registry_sha256"], "registry differs"
    return df, meta, reg


def main() -> int:
    recorded = json.loads((EVIDENCE / "summary.json").read_text())
    df, meta, reg = inputs(recorded)
    out = run(config("A", recorded), df, meta, ca_registry=reg)
    buf = io.StringIO()
    out["trades"].to_csv(buf, index=False, float_format="%.10g")
    trades_equal = buf.getvalue() == gzip.decompress((EVIDENCE / "trades.csv.gz").read_bytes()).decode()
    stats = {k: out["summary"][k] == recorded[k] for k in STATS}
    result = {"evidence_run": EVIDENCE.name, "trades_csv_identical": trades_equal, "summary_sections_equal": stats,
              "reproduced": trades_equal and all(stats.values())}
    (Path(__file__).parent / "reproduce_a.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["reproduced"] else 1


if __name__ == "__main__":
    sys.exit(main())

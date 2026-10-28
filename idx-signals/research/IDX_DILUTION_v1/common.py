"""IDX_DILUTION_v1 inputs and execution plan (same plan as IDX_INSIDER_NEWS: 10M IDR, 10% participation, fees 0.15%/0.25%, registry corporate actions)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import corporate_actions, panel  # noqa: E402
from idxsig.execution import ExecConfig  # noqa: E402
from idxsig.market import Fees  # noqa: E402
from idxsig.provenance import MANIFESTS  # noqa: E402

PANEL_MANIFEST = MANIFESTS / "panel-20261007T225823Z.json"
REGISTRY_MANIFEST = MANIFESTS / "ca_registry-20261007T230210Z.json"


def load_inputs():
    df, meta, _ = panel.load(PANEL_MANIFEST)
    reg, rmeta = corporate_actions.load(REGISTRY_MANIFEST, panel_sha256=meta["sha256"])
    return df, reg, {"panel_sha256": meta["sha256"], "registry_sha256": rmeta["sha256"]}


def config(hold: int) -> ExecConfig:
    return ExecConfig(holding_days=hold, entry_lag=1, notional=10_000_000.0, max_participation=0.10, fees=Fees(0.0015, 0.0025),
                      data_end_exit="last_close", ca_mode="registry", fill_model="C")

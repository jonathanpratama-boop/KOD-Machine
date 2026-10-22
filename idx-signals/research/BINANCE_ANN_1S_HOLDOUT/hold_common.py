"""Shared constants and helpers of BINANCE_ANN_1S_HOLDOUT (see PROTOCOL.md and AUTHORIZATION.md)."""
import hashlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
M1 = ROOT / "research" / "BINANCE_ANN_1M"          # the minute study: event rule, announcements, cluster_boot
S1 = ROOT / "research" / "BINANCE_ANN_1S"          # the seconds study: analyse, cell_stats, fetch helpers
WINDOW_START, WINDOW_END = "2024-01-01", "2026-10-01"   # articles released 2024-01-01 00:00 UTC .. 2026-09-30 23:59:59 UTC
AUTH_PHRASE = "Unseal crypto holdout for the Binance test"
GO_MIN_ELIGIBLE, GO_MIN_FILLABLE = 40, 30
SEED, HURDLE_T = 20261122, 1.65                     # bootstrap seed base; one-sided 5% (a replication of one pre-specified effect)
PINNED_CODE = ("research/BINANCE_ANN_1M/feasibility.py", "research/BINANCE_ANN_1M/run.py", "research/BINANCE_ANN_1S/run.py",
               "research/BINANCE_ANN_1S/fetch_ticks.py")
PINNED_INPUT = "research/BINANCE_ANN_1M/announcements.csv.gz"


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def require_authorization() -> None:
    """The 2024+ crypto holdout opens only with the owner's recorded selection."""
    f = HERE / "AUTHORIZATION.md"
    if not f.exists() or AUTH_PHRASE not in f.read_text():
        sys.exit("error: AUTHORIZATION.md quoting the owner's selection is required to open the 2024+ crypto holdout")


def require_pinned_code() -> None:
    """Every pinned file must hash to a value written in PROTOCOL.md (committed before any 2024+ datum was read)."""
    protocol = (HERE / "PROTOCOL.md").read_text()
    bad = [p for p in (*PINNED_CODE, PINNED_INPUT) if sha_file(ROOT / p) not in protocol]
    if bad:
        sys.exit(f"error: these files differ from the hashes in PROTOCOL.md: {bad}")

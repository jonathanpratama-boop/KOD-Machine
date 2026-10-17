"""E10 step 4, the single recorded run named in PROTOCOL.md: run_full.py unchanged except for one fix, found by
tests/test_e10_verify.py before any price was read. run_test.load_panel returns the session dates as numpy strings,
which pandas 3 refuses in pd.Timestamp (run_full.py builds each trade's ISO week that way, and would stop on the first
trade), so the dates are handed over as Python strings. Nothing else differs.

Usage (from idx-signals/): python3 research/E10/run_e10.py
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("e10_full", Path(__file__).resolve().parent / "run_full.py")
full = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(full)
_load_panel = full.core.load_panel


def load_panel():
    dates, tickers, ti, m = _load_panel()
    return dates.astype(object), tickers, ti, m


def main() -> int:
    full.core.load_panel = load_panel
    return full.main()


if __name__ == "__main__":
    sys.exit(main())

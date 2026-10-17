"""E10 step 4 under FEASIBILITY_AMENDMENT_1.md, the single recorded run named in PROTOCOL.md: run_e10.py (run_full.py
with its one date fix), reading the amended events and releases from feasibility_a1/ in place of feasibility/.
Nothing else differs.

Usage (from idx-signals/): python3 research/E10/run_a1.py
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd

_spec = importlib.util.spec_from_file_location("e10_recorded", Path(__file__).resolve().parent / "run_e10.py")
recorded = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recorded)
full = recorded.full


class _Pandas:
    """pandas as run_full.py sees it, with files under feasibility/ read from feasibility_a1/."""

    def __getattr__(self, name):
        return getattr(pd, name)

    @staticmethod
    def read_csv(path, *args, **kwargs):
        p = Path(path)
        if p.parent == full.E10 / "feasibility":
            p = full.E10 / "feasibility_a1" / p.name
        return pd.read_csv(p, *args, **kwargs)


def main() -> int:
    full.pd = _Pandas()
    return recorded.main()


if __name__ == "__main__":
    sys.exit(main())

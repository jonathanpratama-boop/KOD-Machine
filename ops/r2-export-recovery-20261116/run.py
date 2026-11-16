"""Keep the existing provider correction and add the ledger export fallback."""
import importlib.util
from pathlib import Path
import sys

PREVIOUS = Path('/var/lib/kod-research-r2-ops/repairs/provider-recovery-20261116')
sys.path.insert(0, str(PREVIOUS))
spec = importlib.util.spec_from_file_location('existing_provider_runtime', PREVIOUS/'run.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)

from research_r2 import engine  # noqa: E402 - load the existing runtime first
from export_recovery import install  # noqa: E402 - prior runtime establishes imports
install(engine)

if __name__ == '__main__':
    raise SystemExit(previous.module.main())

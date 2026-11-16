"""Launch the existing KOD runtime with the reviewed transient-error overlay."""
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, '/opt/kod/research-r2')
from broad_observer import runtime
from provider_recovery import install

original = Path('/var/lib/kod-research-r2-ops/repairs/simple-runtime-20261107/run.py')
spec = importlib.util.spec_from_file_location('existing_simple_runtime', original)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
install(runtime)

if __name__ == '__main__':
    raise SystemExit(module.main())

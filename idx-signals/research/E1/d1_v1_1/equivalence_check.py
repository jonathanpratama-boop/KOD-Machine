"""v1 vs v1.1 on the E1 study arrays: every family flag identical."""
import importlib.util, json, subprocess, sys, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, ".")
import numpy as np
from idxsig import e1
from idxsig.panel import load
from idxsig.rules import moonshot_e1 as new
src = subprocess.run(["git", "show", "29e32e4:idx-signals/idxsig/rules/moonshot_e1.py"], capture_output=True, text=True, check=True).stdout
spec = importlib.util.spec_from_loader("moonshot_e1_v1", loader=None); old = importlib.util.module_from_spec(spec); exec(src, old.__dict__)
df, meta, _ = load()
st = e1.Study(df, meta); m = st.m
args = (m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
fo, fn = old.family_flags(old.features(*args)), new.family_flags(new.features(*args))
res = {k: bool(np.array_equal(fo[k], fn[k])) for k in fo}
import hashlib
res["v1_module_sha256"] = hashlib.sha256(src.encode()).hexdigest()
res["v1_1_module_sha256"] = hashlib.sha256(open(new.__file__, "rb").read()).hexdigest()
res["sessions_compared"] = int(m.shape[1]); res["names_compared"] = int(m.shape[0])
print(json.dumps(res, indent=2))

"""BINANCE_ANN_1S_HOLDOUT rehearsal: run.py's core, pointed at test 22's own stored trades with test 22's seed and hurdle (in memory; nothing of this study is
touched and no 2024+ datum is read), must reproduce test 22's recorded result exactly, and verify.py must pass on it. Run before the real run; writes
rehearsal/REHEARSAL.json. Usage (from idx-signals/): python3 research/BINANCE_ANN_1S_HOLDOUT/rehearsal.py"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from hold_common import HERE, S1, load


def main() -> int:
    out = HERE / "rehearsal" / "REHEARSAL.json"
    if out.exists():
        sys.exit("error: rehearsal/REHEARSAL.json exists")
    run = load(HERE / "run.py", "holdout_run")
    ver = load(HERE / "verify.py", "holdout_verify")
    got = run.core(S1 / "ticks", seed=20261023, hurdle=3.0, check_go=False)
    res = got["res"]
    ref = json.loads((S1 / "results" / "RESULT.json").read_text())
    pairs = {
        "usable_event": (res["events"]["usable_event"], ref["events"]["usable_event"]), "usable_placebo": (res["events"]["usable_placebo"], ref["events"]["usable_placebo"]),
        "R_60": (res["reaction"]["R_60"], ref["reaction"]["R_60"]), "R_1": (res["reaction"]["R_1"], ref["reaction"]["R_1"]),
        "n_g1": (res["gate_cell_L2_H300"]["n"], ref["gate_cell_L2_H300"]["n"]), "mean_net_g1": (res["gate_cell_L2_H300"]["mean_net"], ref["gate_cell_L2_H300"]["mean_net"]),
        "t_net_g1": (res["gate_cell_L2_H300"]["t_net"], ref["gate_cell_L2_H300"]["t_net"]),
        "winsorised_g1": (res["gate_cell_L2_H300"]["winsorised_net"], ref["gate_cell_L2_H300"]["winsorised_net"]),
        "mean_net_g2": (res["gate_cell_L5_H300"]["mean_net"], ref["gate_cell_L5_H300"]["mean_net"]), "placebo_net_t": (res["placebo_L2_H300"]["net_t"], ref["placebo_L2_H300"]["net_t"]),
        "p_one_sided": (res["p_one_sided_G1"], ref["p_one_sided_G1"])}
    diffs = {k: [a, b] for k, (a, b) in pairs.items() if abs(a - b) > 1e-12}
    tmp = Path(tempfile.mkdtemp(prefix="holdout_rehearsal_"))
    (tmp / "RESULT.json").write_text(json.dumps(res, default=float))
    summary, bad = ver.verify(tmp, S1 / "ticks", 3.0, None)
    rec = {"reproduces_test_22": not diffs and res["verdict"] == "PASS", "differences": diffs, "verifier_mismatches": bad, "verifier_verdict": summary["verdict"],
           "n": res["gate_cell_L2_H300"]["n"], "t_net": res["gate_cell_L2_H300"]["t_net"]}
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 0 if rec["reproduces_test_22"] and not bad else 1


if __name__ == "__main__":
    sys.exit(main())

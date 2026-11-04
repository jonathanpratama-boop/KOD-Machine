"""Run INSIDE a checkout of 52507b7 (audit_gaps.py does this) with the current results/ copied in.
Prints JSON: what the pre-fix code does on today's recorded runs and on a losing example."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from idxsig import paper  # the pre-fix module

ev = paper.validation_evidence("IDX")
src = Path(paper.__file__).read_text()
pred = re.search(r"tradeable_edge = (bool\(.*?\))\n", src).group(1)
losing = {"p_one_sided": 0.01, "avg_net_return": -0.02, "matched_random_avg_net_return": -0.05}
print(json.dumps({
    "idx_evidence_run_chosen_by_old_lookup": (ev.get("trading") or {}).get("run_id"),
    "old_tradeable_edge_predicate": pred,
    "old_predicate_on_a_losing_strategy_beating_a_worse_baseline": eval(pred, {"trading": losing,
                                                                             "p": paper.POLICY}),
}))

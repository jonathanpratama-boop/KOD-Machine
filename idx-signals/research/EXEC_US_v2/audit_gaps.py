"""The audit findings on the execution/data path, each checked by its regression tests on the code
BEFORE the fix and on the code NOW. A finding counts as fixed only if a test fails before and
passes now. "Fails before" is split into an assertion failure (old code ran and was wrong) and an
error (old code lacked the check altogether, e.g. an import or attribute error).

Before = 52507b7 (the start of PR #3) for the PR #3 fixes, d62de40 (PR #3 before this milestone)
for the EXEC-US-v2 fixes. The current tests are copied into a scratch checkout of the old commit
and run there; nothing in the repository is changed.

    python3 research/EXEC_US_v2/audit_gaps.py   (from idx-signals/, needs git history)"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PKG = HERE.parents[1]
REPO = PKG.parent
PR3_START, PR3_HEAD = "52507b7c02934457f495f92e78f5f562fb441d95", "d62de40c4b3f91140279276a64dcf5a7bccfe47a"
UP, CT, FC = "tests.test_us_pipeline", "tests.test_contract", "tests.test_fill_c"

FINDINGS = {
    "input_hash_binding_and_complete_reconciliation": [
        (PR3_START, f"{UP}.Verification.test_missing_record_is_unresolved_not_accepted"),
        (PR3_START, f"{UP}.Verification.test_duplicate_records_are_unresolved"),
        (PR3_START, f"{UP}.Verification.test_record_from_a_different_payload_is_unresolved"),
        (PR3_START, f"{UP}.Verification.test_inputs_are_bound_by_hash_not_name")],
    "evidence_restricted_to_permitted_research_dates": [
        (PR3_START, f"{UP}.Verification.test_share_count_records_inside_the_window_are_not_accepted"),
        (PR3_START, f"{UP}.Verification.test_share_counts_refused_for_a_panel_reading_past_their_window"),
        (PR3_HEAD, f"{CT}.SameContractBothWays.test_research_window_is_enforced")],
    "consistent_share_units_in_capacity": [
        (PR3_START, f"{UP}.Capacity.test_forward_and_reverse_splits_keep_capacity_in_entry_units"),
        (PR3_START, f"{UP}.Capacity.test_a_split_between_signal_and_entry_converts_the_shares"),
        (PR3_HEAD, f"{CT}.Units.test_split_between_decision_and_execution")],
    "explicitly_pinned_approval_evidence": [
        (PR3_START, f"{UP}.Approval.test_changed_config_or_other_execution_is_not_approved"),
        (PR3_START, f"{UP}.Approval.test_appending_a_run_does_not_change_the_evidence")],
    "positive_net_separate_from_significance": [
        (PR3_START, f"{UP}.Approval.test_a_losing_strategy_beating_a_worse_baseline_is_not_approved"),
        (PR3_START, f"{UP}.Approval.test_positive_but_not_above_baseline_is_not_approved")],
    "planned_order_separate_from_realized_fill (Hermes)": [
        (PR3_HEAD, f"{CT}.Liquidity.test_entry_session_volume_bounds_the_fill"),
        (PR3_HEAD, f"{CT}.Liquidity.test_no_trade_on_the_entry_session")],
    "one_sizing_contract_for_replay_and_paper (Hermes)": [
        (PR3_HEAD, f"{CT}.SameContractBothWays.test_forward_scoring_equals_replay_on_identical_inputs"),
        (PR3_HEAD, f"{CT}.Capital.test_simultaneous_signals_share_cash_by_priority_without_leverage")],
}


def run(cwd: Path, test: str) -> dict:
    p = subprocess.run([sys.executable, "-m", "unittest", test], cwd=cwd, capture_output=True, text=True,
                       timeout=600)
    tail = p.stderr.strip().splitlines()
    if p.returncode == 0:
        return {"result": "PASS"}
    kind = "ERROR" if "errors=" in (tail[-1] if tail else "") else "FAIL"
    why = next((ln.strip() for ln in reversed(tail) if ln.strip().startswith(("AssertionError", "ImportError",
               "ModuleNotFoundError", "AttributeError", "TypeError", "KeyError", "ValueError"))), tail[-1] if tail else "")
    return {"result": kind, "why": why[:300]}


def checkout(commit: str, root: Path) -> Path:
    dest = root / commit[:7]
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(dest), commit], check=True)
    for f in ("test_us_pipeline.py", "test_contract.py", "test_fill_c.py", "support.py", "test_corporate_actions.py"):
        shutil.copy(PKG / "tests" / f, dest / "idx-signals" / "tests" / f)
    return dest / "idx-signals"


def old_code_witness(tree: Path) -> dict:
    """The pre-fix code itself, on today's recorded runs (results/ copied in) and on a losing example."""
    shutil.rmtree(tree / "results")
    shutil.copytree(PKG / "results", tree / "results")
    shutil.copy(HERE / "witness_old.py", tree / "witness_old.py")
    p = subprocess.run([sys.executable, "witness_old.py"], cwd=tree, capture_output=True, text=True, timeout=600)
    return json.loads(p.stdout) if p.returncode == 0 else {"error": p.stderr[-500:]}


def legacy_sizing_witness() -> dict:
    """Hermes: on the legacy paths, the same thin name is rejected by backtest fill model C but cut
    down by the paper plan (exec_us.make_plan, PAPER-POLICY-v4). EXEC-US-v2 has one rule (cut down,
    reject only below one share) used by both its replay and its forward scoring."""
    sys.path.insert(0, str(PKG))
    import numpy as np
    from idxsig import contract, exec_us
    from idxsig.execution import STATUS, ExecConfig, execute
    from tests.support import flat_market, rebuild
    from tests.test_corporate_actions import registry

    t, d, a = flat_market(volume=5_000.0)            # 20-session median 5,000 shares at Rp1,000
    m = rebuild(t, d, a)
    m = m.with_registry(registry(m))
    c = execute(m, np.array([0]), np.array([4]), ExecConfig(holding_days=4, notional=10_000_000.0, ca_mode="registry",
                                                            fill_model="C"))  # 10,000 shares wanted, cap 500
    v1 = exec_us.make_plan(100.0, 95.0, 5_000.0)     # paper v4 plan on the same 5,000-share median
    v2 = contract.plan_order(100.0, 95.0, 5_000.0 * 100.0, 10_000.0)
    return {"backtest_fill_C": STATUS[c["status"][0]], "paper_v4_plan": {"status": v1["status"], "shares": v1["shares"],
            "capacity_unit": "shares"}, "exec_us_v2_plan": {"outcome": v2["outcome"], "shares": v2["shares"],
            "capacity_unit": "USD traded value", "binding_limit": v2["binding_limit"]}}


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="audit_gaps_", dir=REPO.parent))
    trees = {}
    try:
        for commit in {c for v in FINDINGS.values() for c, _ in v}:
            trees[commit] = checkout(commit, tmp)
        out, ok = {"_witnesses": {"old_code_52507b7": old_code_witness(trees[PR3_START]),
                                  "legacy_sizing_paths_now": legacy_sizing_witness()}}, True
        for finding, tests in FINDINGS.items():
            rows = []
            for before, test in tests:
                b, n = run(trees[before], test), run(PKG, test)
                fixed = b["result"] != "PASS" and n["result"] == "PASS"
                ok &= fixed
                rows.append({"test": test, "before_commit": before[:7], "before": b, "now": n["result"],
                             "fails_before_passes_now": fixed})
            out[finding] = {"tests": rows, "status": "FIXED" if all(r["fails_before_passes_now"] for r in rows)
                            else "CHECK"}
        (HERE / "audit_gaps.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out["_witnesses"], indent=1))
        for f, v in out.items():
            if f.startswith("_"):
                continue
            print(f"{v['status']:6} {f}")
            for r in v["tests"]:
                print(f"       before {r['before_commit']} {r['before']['result']:5} now {r['now']:5} {r['test'].split('.')[-1]}"
                      + (f"   [{r['before'].get('why', '')[:90]}]" if r["before"]["result"] != "PASS" else ""))
        return 0 if ok else 1
    finally:
        for commit in trees:
            subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(tmp / commit[:7])],
                           capture_output=True)
        subprocess.run(["git", "-C", str(REPO), "worktree", "prune"], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

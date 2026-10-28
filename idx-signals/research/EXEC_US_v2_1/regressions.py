"""Ace's five findings on 21eb6aa, each reproduced by a regression test: the tests are run against
the v2 code (a scratch checkout of 21eb6aa with the current tests copied in) and against the
current code. Writes regressions.json. Nothing in the repository is changed.

    python3 research/EXEC_US_v2_1/regressions.py   (from idx-signals/, needs git history)"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PKG = HERE.parents[1]
REPO = PKG.parent
V2 = "21eb6aa961710227313278ac97b2cf15a5a08576"
T = "tests.test_contract"
FINDINGS = {
    "P1 saved orders keyed by row number": [f"{T}.AceReview.test_saved_orders_follow_the_ticker_not_the_row",
                                            f"{T}.AceReview.test_a_rolling_window_download_is_not_already_processed"],
    "P1 split re-adjustment corrupts holdings": [f"{T}.AceReview.test_a_split_readjusted_download_keeps_the_holding"],
    "P2 exit cost taken at the entry tier": [f"{T}.AceReview.test_planned_risk_covers_the_exit_cost_tier_at_the_stop"],
    "P2 exits fill on zero-volume sessions": [f"{T}.AceReview.test_no_exit_on_a_session_without_trades"],
}
# The demo finding is about the v2 demo script, not the contract: its evidence is the recorded v2
# trace (sessions it actually processed) against the v2.1 trace, plus the window test on v2.1's demo.


def run(cwd: Path, test: str) -> dict:
    p = subprocess.run([sys.executable, "-m", "unittest", test], cwd=cwd, capture_output=True, text=True, timeout=600)
    if p.returncode == 0:
        return {"result": "PASS"}
    lines = [ln.strip() for ln in p.stderr.splitlines() if ln.strip()]
    why = next((ln for ln in reversed(lines) if ln.startswith(("AssertionError", "ValueError", "AttributeError",
                                                                "FileNotFoundError", "KeyError", "TypeError"))), lines[-1])
    return {"result": "FAIL" if "failures=" in lines[-1] else "ERROR", "why": why[:300]}


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="v2_regressions_", dir=REPO.parent))
    dest = tmp / "v2"
    try:
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(dest), V2], check=True)
        old = dest / "idx-signals"
        shutil.copy(PKG / "tests" / "test_contract.py", old / "tests" / "test_contract.py")
        out, ok = {"v2_commit": V2}, True
        for finding, tests in FINDINGS.items():
            rows = []
            for test in tests:
                before, now = run(old, test), run(PKG, test)
                rows.append({"test": test, "at_21eb6aa": before, "now": now["result"]})
                ok &= before["result"] != "PASS" and now["result"] == "PASS"
            out[finding] = rows
        v2_demo = (old / "research" / "EXEC_US_v2" / "demo.py").read_text()
        v2_trace = json.loads((old / "research" / "EXEC_US_v2" / "trace.json").read_text())
        v2_sessions = sorted({e["session"] for e in v2_trace["events"]})
        v21 = json.loads((HERE / "trace.json").read_text())["sessions_processed"]
        window_now = run(PKG, f"{T}.DemoWindow.test_demo_window_ends_on_the_declared_session")["result"]
        out["P2 demo replays one session too many"] = {
            "v2_demo_line": next(ln.strip() for ln in v2_demo.splitlines() if "full.slice(lo, hi + 1)" in ln),
            "v2_declared": v2_trace["sessions"], "v2_processed": [v2_sessions[0], v2_sessions[-1], len(v2_sessions)],
            "v2_1_processed": [v21[0], v21[-1], len(v21)], "window_test_now": window_now,
            "note": "bounds() already returns an exclusive end; v2 added one more and processed 2023-10-23"}
        ok &= len(v2_sessions) == 21 and len(v21) == 20 and window_now == "PASS"
        (HERE / "regressions.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out, indent=1))
        return 0 if ok else 1
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(dest)], capture_output=True)
        subprocess.run(["git", "-C", str(REPO), "worktree", "prune"], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

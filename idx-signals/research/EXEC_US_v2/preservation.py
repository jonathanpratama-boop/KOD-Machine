"""Content proof that merge d62de40 preserved both parents (PR #3 head and its base).

For every path either parent changed relative to their merge base:
  * changed on one side only  -> the merge must hold that side's exact bytes;
  * changed on both sides     -> every line either side added must be in the merge, and every
                                 line both sides kept from the merge base must still be there.
Every recorded artifact (results/runs, research, paper ledger and scans, KOD registry) must be
byte-identical to the parent that holds it. Parent order and the append-only guard are not used.

    python3 research/EXEC_US_v2/preservation.py   (from idx-signals/, needs git history)"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

MERGE, PR_HEAD, BASE = "d62de40c4b3f91140279276a64dcf5a7bccfe47a", "7774442f0df8960ccfe17311ac1f8561d497f13a", \
    "c09a27ac94fccf6a33f12a0ee07e33f88238ace5"
ARTIFACTS = ("idx-signals/results/", "idx-signals/research/", "idx-signals/paper/", "kod-machine/registry/",
             "kod-machine/research/", "kod-machine/var/")


# Lines that only enumerate the fill models (a comment, a choices tuple, a help string): each side
# listed its own new model, the merge lists all of them. They are accepted only if the merged code
# actually accepts every model (fill_models_accepted below).
COMBINED = ("fill_model", "fill-model", "mixed units; reproduction only)", "open entries)", "help=\"A: original",
            "(open entries); C: FILL-C-v1")
MODELS = ("A", "B", "B2", "C")


def fill_models_accepted() -> dict:
    """Run the merged code: the CLI parser and ExecConfig validation must accept every model."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import numpy as np
    from idxsig import cli
    from idxsig.execution import ExecConfig, execute
    from tests.support import flat_market, rebuild
    from tests.test_corporate_actions import registry, reset_market

    out = {}
    for model in MODELS:
        try:
            cli_ok = True
            cli.main(["run", "--rule", "NO_SUCH_RULE", "--fill-model", model])
        except SystemExit as exc:  # argparse rejects an unknown choice with exit code 2
            cli_ok = exc.code != 2
        except KeyError:  # parsed; then the (deliberately unknown) rule is refused
            cli_ok = True
        cfg = {"A": dict(), "B": dict(entry_price="open", units="as_traded"),
               "B2": dict(entry_price="open", units="as_traded"), "C": dict(ca_mode="registry")}[model]
        t, d, a = flat_market()
        a["open"] = a["close"].copy()
        m = rebuild(t, d, a).with_units(np.ones((3, 20)))
        if model == "C":
            m = m.with_registry(registry(m))
        try:
            r = execute(m, np.array([0]), np.array([2]), ExecConfig(holding_days=4, fill_model=model, **cfg))
            exec_ok = bool(r["status"][0] == 0)
        except ValueError:
            exec_ok = False
        out[model] = {"cli_accepts": cli_ok, "execute_runs_and_exits": exec_ok}
    return out


def git(*a) -> bytes:
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout


def tree(ref) -> dict:
    out = {}
    for line in git("ls-tree", "-r", "-z", "--full-tree", ref).split(b"\0"):
        if line:
            meta, path = line.split(b"\t", 1)
            out[path.decode()] = meta.split()[2].decode()
    return out


def lines(blob):
    return [] if blob is None else git("cat-file", "-p", blob).decode("utf-8", "replace").splitlines()


def main() -> int:
    mb = git("merge-base", PR_HEAD, BASE).decode().strip()
    t = {"mb": tree(mb), "pr": tree(PR_HEAD), "base": tree(BASE), "merge": tree(MERGE)}
    report = {"merge": MERGE, "pr_head": PR_HEAD, "base": BASE, "merge_base": mb, "one_side": {}, "both_sides": {},
              "artifacts_checked": 0, "problems": []}
    paths = set(t["pr"]) | set(t["base"]) | set(t["mb"])
    for p in sorted(paths):
        ch = {s: t[s].get(p) != t["mb"].get(p) for s in ("pr", "base")}
        if not any(ch.values()):
            if t["merge"].get(p) != t["mb"].get(p):
                report["problems"].append(f"{p}: changed by the merge though neither side changed it")
            continue
        if ch["pr"] != ch["base"]:
            side = "pr" if ch["pr"] else "base"
            ok = t["merge"].get(p) == t[side].get(p)
            report["one_side"][p] = side
            if not ok:
                report["problems"].append(f"{p}: {side}'s version not kept byte-identical")
            continue
        if t["pr"].get(p) == t["base"].get(p):  # same change on both sides
            if t["merge"].get(p) != t["pr"].get(p):
                report["problems"].append(f"{p}: identical change on both sides not kept")
            continue
        m, base0 = set(lines(t["merge"].get(p))), lines(t["mb"].get(p))
        info = {}
        for side in ("pr", "base"):
            added = [ln for ln in lines(t[side].get(p)) if ln not in set(base0)]
            missing = [ln for ln in added if ln not in m]
            info[f"{side}_added_lines"], info[f"{side}_added_missing"] = len(added), missing
            unexplained = [ln for ln in missing if not any(k in ln for k in COMBINED)]
            info[f"{side}_combined_by_hand"] = len(missing) - len(unexplained)
            if unexplained:
                report["problems"].append(f"{p}: {len(unexplained)} line(s) added by {side} missing from the merge")
        kept = set(lines(t["pr"].get(p))) & set(lines(t["base"].get(p))) & set(base0)
        info["common_lines_missing"] = sorted(kept - m)
        if info["common_lines_missing"]:
            report["problems"].append(f"{p}: lines kept by both sides missing from the merge")
        report["both_sides"][p] = info
    for side in ("pr", "base"):
        for p, blob in t[side].items():
            if p.startswith(ARTIFACTS) and t["mb"].get(p) != blob or p.startswith(ARTIFACTS) and p not in t["mb"]:
                report["artifacts_checked"] += 1
                if t["merge"].get(p) != blob and p not in report["both_sides"]:
                    report["problems"].append(f"{p}: {side}'s recorded artifact differs in the merge")
    runs = [ln for ln in lines(t["merge"]["idx-signals/results/RUNS.jsonl"])]
    for side in ("pr", "base"):
        ids = [json.loads(ln)["run_id"] for ln in lines(t[side]["idx-signals/results/RUNS.jsonl"])]
        merged = [json.loads(ln)["run_id"] for ln in runs]
        report[f"runs_index_{side}_all_present"] = all(i in merged for i in ids)
        if not report[f"runs_index_{side}_all_present"]:
            report["problems"].append(f"RUNS.jsonl: a run of {side} missing")
    report["fill_models_accepted"] = fill_models_accepted()
    for model, ok in report["fill_models_accepted"].items():
        if not all(ok.values()):
            report["problems"].append(f"fill model {model} not accepted by the merged code: {ok}")
    report["merge_tree_sha256"] = hashlib.sha256(json.dumps(t["merge"], sort_keys=True).encode()).hexdigest()
    report["result"] = "PRESERVED" if not report["problems"] else "PROBLEMS"
    out = Path(__file__).with_name("preservation.json")
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("result", "artifacts_checked", "problems")}, indent=1),
          "\nboth-sides:", {p: {k: (v if not isinstance(v, list) else len(v)) for k, v in i.items()}
                            for p, i in report["both_sides"].items()}, "\none-side files:", len(report["one_side"]))
    return 0 if not report["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())

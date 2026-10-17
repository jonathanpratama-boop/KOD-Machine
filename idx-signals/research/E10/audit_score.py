"""E10 audit, step 2 (AUDIT_PROCEDURE.md): score the two reviewers' saved answers into audit/AUDIT.json.

Each answer file is JSON: {"reviewer": str, "answers": [{"item": int, "q1_same_measure": bool, "q2_direction": bool,
"q3_numbers": bool, "note": str}, ...]} covering every item of the blind file.

Usage (from idx-signals/): python3 research/E10/audit_score.py --blind <blind file> --answers <a.json> <b.json>
"""
import argparse
import json
import sys
from pathlib import Path

E10 = Path(__file__).resolve().parent
GO = {"RAISE": 0.85, "CUT": 0.80}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind", required=True)
    ap.add_argument("--answers", nargs=2, required=True)
    args = ap.parse_args()
    items = {it["item"]: it for it in json.loads(Path(args.blind).read_text())["items"]}
    reviewers = []
    for path in args.answers:
        a = json.loads(Path(path).read_text())
        got = {x["item"]: x for x in a["answers"]}
        if set(got) != set(items):
            sys.exit(f"error: {path} does not answer every item exactly once")
        reviewers.append((a["reviewer"], got))
    out = {"procedure": "research/E10/AUDIT_PROCEDURE.md", "items": len(items), "reviewers": [], "disagreements": []}
    lower = {}
    for name, got in reviewers:
        per = {}
        for cls in GO:
            ids = [i for i, it in items.items() if it["assigned_direction"] == cls]
            ok = [i for i in ids if got[i]["q1_same_measure"] and got[i]["q2_direction"]]
            per[cls] = {"n": len(ids), "correct": len(ok), "precision": len(ok) / len(ids) if ids else None,
                        "wrong_items": sorted(set(ids) - set(ok))}
            lower[cls] = min(lower.get(cls, 1.0), per[cls]["precision"] if ids else 0.0)
        q3 = sum(bool(x["q3_numbers"]) for x in got.values()) / len(got)
        out["reviewers"].append({"reviewer": name, "by_class": per, "q3_numbers_rate": q3,
                                 "answers": [got[i] for i in sorted(got)]})
    (a_name, a), (b_name, b) = reviewers
    for i in sorted(items):
        va = bool(a[i]["q1_same_measure"] and a[i]["q2_direction"])
        vb = bool(b[i]["q1_same_measure"] and b[i]["q2_direction"])
        if va != vb:
            out["disagreements"].append({"item": i, a_name: va, b_name: vb})
    out["go_precision"] = lower
    out["audit_go"] = all(lower[c] >= GO[c] for c in GO)
    (E10 / "audit").mkdir(exist_ok=True)
    (E10 / "audit" / "AUDIT.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("go_precision", "audit_go", "disagreements")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

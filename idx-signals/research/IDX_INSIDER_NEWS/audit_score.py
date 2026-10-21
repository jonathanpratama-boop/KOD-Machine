"""IDX_INSIDER_NEWS audit, step 2 (LABELING.md): score two reviewers' blind labels against the labeller's. Each answers file is the
reviewers' JSON list (audit item, cls, issuer_ticker). Writes AUDIT.json. Usage:
python3 audit_score.py --key key.csv --answers a.json b.json --out AUDIT.json"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

GO_PRECISION = 0.85


def kappa(a: pd.Series, b: pd.Series) -> float:
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = float((a.values == b.values).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def score(key: pd.DataFrame, answers: list[tuple[str, pd.DataFrame]]) -> dict:
    out = {"items": int(len(key)), "reviewers": [], "go_precision_threshold": GO_PRECISION}
    merged = []
    for name, ans in answers:
        m = key.merge(ans.rename(columns={"cls": "r_cls", "issuer_ticker": "r_ticker"}), on="audit_item", how="left")
        if m["r_cls"].isna().any():
            raise ValueError(f"{name} did not answer every item")
        merged.append((name, m))
        ins = m[m.cls == "INSIDER_BUY"]
        oth = m[m.cls != "INSIDER_BUY"]
        agree = ins[(ins.r_cls == "INSIDER_BUY") & (ins.issuer_ticker.fillna("") == ins.r_ticker.fillna(""))]
        out["reviewers"].append({
            "reviewer": name, "labelled_insider_buy": int(len(ins)), "confirmed_with_same_ticker": int(len(agree)),
            "precision": len(agree) / len(ins), "class_confirmed_only": float((ins.r_cls == "INSIDER_BUY").mean()),
            "missed_share_among_others": float((oth.r_cls == "INSIDER_BUY").mean()),
            "kappa_vs_labeller": kappa(m.cls, m.r_cls), "wrong_items": sorted(int(i) for i in set(ins.audit_item) - set(agree.audit_item))})
    (na, ma), (nb, mb) = merged
    out["kappa_between_reviewers"] = kappa(ma.r_cls, mb.r_cls)
    out["lower_precision"] = min(r["precision"] for r in out["reviewers"])
    out["audit_go"] = bool(out["lower_precision"] >= GO_PRECISION)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--answers", nargs=2, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    key = pd.read_csv(args.key)
    answers = []
    for p in args.answers:
        a = json.loads(Path(p).read_text())
        rows = a["answers"] if isinstance(a, dict) else a
        answers.append((a.get("reviewer", Path(p).stem) if isinstance(a, dict) else Path(p).stem,
                        pd.DataFrame(rows).rename(columns={"item": "audit_item"})))
    res = score(key, answers)
    if Path(args.out).exists():
        sys.exit("error: output exists")
    Path(args.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("lower_precision", "audit_go", "kappa_between_reviewers")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

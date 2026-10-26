"""LEAD_LADDER_INTL_v1 addendum 2: final verdict with G6 (lift >= 1.5 x the rehearsal lift of the same cell)."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RATIO = 1.5


def main():
    res = json.loads((HERE / "results" / "summary.json").read_text())["result"]
    reh = {p["id"]: p for p in json.loads((HERE / "rehearsal" / "summary.json").read_text())["result"]["primary"]}
    cells = []
    for p in res["primary"]:
        base = reh[p["id"]]["lift"]
        g6 = p.get("lift") is not None and base is not None and p["lift"] >= RATIO * base
        status = p["status"] if p["status"] != "PASS" else ("PASS" if g6 else "FAIL")
        cells.append({"id": p["id"], "lift": p.get("lift"), "placebo_lift": base, "G6": bool(g6),
                      "status_G1_G5": p["status"], "status": status})
    st = [c["status"] for c in cells]
    verdict = "REPLICATED_SCREEN" if "PASS" in st else ("NOT_TESTABLE" if all(s == "NOT_TESTABLE" for s in st) else "NOT_REPLICATED")
    out = {"rule": f"ADDENDUM_2: G1-G5 and lift >= {RATIO} x rehearsal lift", "primary": cells, "verdict": verdict,
           "verdict_G1_G5_only": res["verdict"]}
    with (HERE / "results" / "placebo_gate.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    sys.exit(main())

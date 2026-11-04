"""CALL_CERT_v1: one run of protocol.json. Fits v2.4's features out of time, certifies four calling rules on 2022 with
Learn then Test (idxsig/risk_control.py), checks them on 2023, writes results/RESULT.json and the trial result file.
Refuses to run twice."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import learner3, risk_control as rc  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

_spec = importlib.util.spec_from_file_location("ta_run", ROOT / "research" / "TA_HISTORY_v1" / "run.py")
ta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ta)  # the same fit() and design() as TA_HISTORY_v1, imported, not copied

PROTO = json.loads((HERE / "protocol.json").read_text())
RES = HERE / "results"
TRIALS = ROOT / "research" / "QUANT_GRADE" / "trials"
FEATURES = list(learner3.FEATURES)
STATEMENTS = {"NEXT_DUMP10_1": "y_NEXT_DUMP10_1", "DUMP10_5": "y_DUMP10_5"}
SHARES = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
DELTA, MIN_CALLS, BROKEN_P = 0.05, 10, 0.0125


def window(g: pd.DataFrame, lo: str, hi: str) -> pd.DataFrame:
    return g[(g["session"] >= lo) & (g["session"] <= hi)]


def predict(g: pd.DataFrame, spec: dict, col: str):
    tr, te = window(g, *spec["fit"]), window(g, *spec["predict"])
    Xa, Xb = ta.design(tr, te, FEATURES)
    beta = ta.fit(Xa, tr[col].to_numpy(float))
    return 1 / (1 + np.exp(-(Xb @ beta))), te[col].to_numpy(int), tr[col].to_numpy(float)


def naive(scores, wrong, thresholds, alpha):
    ok = [t for t in thresholds if sum(1 for s in scores if s >= t) >= MIN_CALLS
          and np.mean([w for s, w in zip(scores, wrong) if s >= t]) <= alpha]
    return max(ok, key=lambda t: sum(1 for s in scores if s >= t)) if ok else None


def main() -> int:
    if (RES / "RESULT.json").exists():
        sys.exit("error: CALL_CERT_v1 has been run; one look only")
    e = PROTO["events"]
    path = ROOT / e["file"]
    if sha256_file(path) != e["sha256"]:
        raise RuntimeError("event file hash differs from the protocol")
    ev = pd.read_csv(path, dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    result, verdicts = {"protocol": PROTO["protocol_id"], "events": len(ev), "tests": {}}, {}
    for stmt, col in STATEMENTS.items():
        g = ev[ev[col].notna()]
        p22, y22, yfit = predict(g, PROTO["fits"]["calibration"], col)
        p23, y23, _ = predict(g, PROTO["fits"]["test"], col)
        base_fit = float(np.mean(yfit))
        for call in ("DUMP", "SAFE"):
            alpha = 0.5 if call == "DUMP" else 0.5 * base_fit
            s22 = p22 if call == "DUMP" else 1 - p22
            s23 = p23 if call == "DUMP" else 1 - p23
            w22 = (1 - y22) if call == "DUMP" else y22
            w23 = (1 - y23) if call == "DUMP" else y23
            ths = [float(np.quantile(s22, 1 - f)) for f in SHARES]
            cert = rc.certify(s22.tolist(), w22.tolist(), ths, alpha, DELTA, MIN_CALLS)
            check = rc.realised(s23.tolist(), w23.tolist(), cert["chosen"], alpha)
            nv = naive(s22.tolist(), w22.tolist(), ths, alpha)
            nv23 = rc.realised(s23.tolist(), w23.tolist(), nv, alpha)
            if cert["chosen"] is None:
                verdict = "CANNOT CERTIFY"
            elif check["calls"] and check["losing_rate"] <= alpha:
                verdict = "HOLDS"
            elif check["calls"] and check["p_exceeds_alpha"] <= BROKEN_P:
                verdict = "BROKEN"
            elif not check["calls"]:
                verdict = "HOLDS (no 2023 calls)"
            else:
                verdict = "ABOVE ALPHA, NOT SIGNIFICANT"
            key = f"{call} on {stmt}"
            verdicts[key] = verdict
            result["tests"][key] = {
                "alpha": alpha, "delta": DELTA, "base_rate_fit_2020_21": base_fit,
                "base_rate_2022": float(np.mean(y22)), "base_rate_2023": float(np.mean(y23)),
                "n_2022": int(len(y22)), "n_2023": int(len(y23)),
                "sequence_2022": [{**r, "share": SHARES[i]} for i, r in enumerate(cert["tested"])],
                "certified_shares": [SHARES[ths.index(t)] for t in cert["certified"]],
                "chosen_threshold": cert["chosen"],
                "chosen_share_2022": (SHARES[ths.index(cert["chosen"])] if cert["chosen"] is not None else None),
                "check_2023": {**check, "share_of_events": (check["calls"] / len(y23) if len(y23) else None)},
                "naive_threshold": nv, "naive_2023": nv23, "verdict": verdict}
    result["verdicts"] = verdicts
    RES.mkdir(exist_ok=True)
    (RES / "RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    trial = {"id": "CALL_CERT_v1_result", "experiment": "CALL_CERT_v1", "date": "2026-10-29",
             "hypothesis": json.loads((TRIALS / "CALL_CERT_v1.json").read_text())["hypothesis"],
             "one_sided_p": None, "p_source": "research/CALL_CERT_v1/results/RESULT.json (exact binomial, fixed-sequence Learn then Test)",
             "variants_searched": 4, "outcome": "; ".join(f"{k}: {v}" for k, v in verdicts.items()),
             "counted": True, "registered": "2026-10-29", "note": "the result of the PENDING registration CALL_CERT_v1.json: one trial"}
    (TRIALS / "CALL_CERT_v1_result.json").write_text(json.dumps(trial, indent=1) + "\n")
    print(json.dumps(verdicts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

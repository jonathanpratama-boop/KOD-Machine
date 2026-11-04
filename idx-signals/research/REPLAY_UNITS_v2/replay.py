"""RECENT_REPLAY_v1, step 2: the one read of the outcomes, under protocol.json.

LEARNER v2.4 as it would have run, session by session, over the events build.py wrote: at each session the learner is
refit on the pinned warm start plus every replay outcome it would have known at that evening's forecast (resolved
by the previous session's close), the running base rate and the feature centres follow the same rule, and every
forecast is made before its own outcome is read. Then the registered statistic (research/LEARNER_v2/protocol_v2_4.json
"claim": AUC over NEXT_DUMP10_1 pairs, bootstrap over signal sessions, z against 0.5 at the looks), the Brier gains,
and the certified next-day dump calls (idxsig.call_cert) with their realised losing rate.

    python3 run.py

Writes results/RESULT.json and REPORT.md once; refuses to run again.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
from idxsig import call_cert, learner3, risk_control  # noqa: E402
from idxsig import learner2 as L2  # noqa: E402
from idxsig import speculation as spec  # noqa: E402
from idxsig.learner2 import Row  # noqa: E402
from idxsig.provenance import MANIFESTS, sha256_file, utc_stamp  # noqa: E402

HERE = Path(__file__).resolve().parent
# `python3 run.py` is the one counted run. A dry run of the mechanics names another protocol and results directory
# (outside research/), e.g. `python3 run.py /tmp/x/protocol.json /tmp/x/results`.
PROTO = json.loads((Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "protocol.json").read_text(encoding="utf-8"))
RESULTS = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "results"
H, C = learner3.HEADLINE, learner3.COMPANION
TASK = {s: f"{learner3.FAMILY}:{s}" for s in learner3.STATEMENTS}
BASE = {s: learner3.STATEMENTS[s][0] for s in learner3.STATEMENTS}   # NEXT_DUMP10_1 -> DOWN10_1, DUMP10_5 -> FADE10_5
FADE_PRIOR_US = 0.403  # the register's frozen US prior for FADE10_5 (KOD-SPEC-REGISTER-v1.1)


def check_pins() -> None:
    for path, want in PROTO["code_pins"].items():
        got = sha256_file(ROOT / path)
        if got != want:
            raise RuntimeError(f"{path} changed since the freeze: {got} != {want}")
    for path, want in PROTO["data_pins"].items():
        got = sha256_file(ROOT / path)
        if got != want:
            raise RuntimeError(f"{path} changed since the freeze: {got} != {want}")


def own(happened, twins_rate):
    """learner2.own_move on a cone record: False when the move did not happen; True when it did and fewer than half of
    the graded twins made it; None (ungraded) when it did and no twin was graded."""
    if happened is None:
        return None
    if not happened:
        return 0
    return None if twins_rate is None else int(twins_rate < L2.OWN_MOVE)


def outcomes_of(m, n: int, d: int, tw_idx: list[int], cone: list[dict], plan: dict) -> dict:
    """Both statements for one event: the raw move, its twins' rate, the own-move label, the session it resolved."""
    last = m.shape[1] - 1
    out = {}
    nxt = spec.cone_outcomes(cone, "NEXT1", m, d, (n, None), [(i, None) for i in tw_idx]) if d + 1 <= last else []
    rec = next((c for c in nxt if c["id"] == BASE[H]), None)
    out[H] = (None if rec is None else {"raw": rec["outcome"], "twins_rate": rec["twins_rate"],
                                         "y": own(rec["outcome"], rec["twins_rate"]), "resolved": str(m.dates[d + 1])})
    cres = spec.simulate(m, n, d, plan, "US")
    if cres is None:
        out[C] = None
    else:
        tres = [spec.simulate(m, i, d, plan, "US") for i in tw_idx]
        base = spec.cone_outcomes(cone, "BASE5", m, d, (n, cres), list(zip(tw_idx, tres)))
        rec = next((c for c in base if c["id"] == BASE[C]), None)
        exit_session = ((cres.get("trade") or {}).get("exit_session")) or str(m.dates[min(d + 6, last)])
        out[C] = (None if rec is None else {"raw": rec["outcome"], "twins_rate": rec["twins_rate"],
                                             "y": own(rec["outcome"], rec["twins_rate"]), "resolved": exit_session,
                                             "entry_status": cres.get("status")})
    return out


def fit(rows: list[Row]):
    model = L2.Model("PATH", rows, share=learner3.share_group)
    bench = L2.Model("PATH", [r._replace(x=r.x[learner3.BENCH_IDX]) for r in rows], share=learner3.share_group)
    return model, bench


def main() -> int:
    if (RESULTS / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this study runs once")
    check_pins()
    proto24, sha24 = learner3.protocol()
    if sha24 != PROTO["learner"]["protocol_sha256"]:
        raise RuntimeError("protocol_v2_4.json differs from the pinned one")
    # the register's statements with numeric priors (as a sealed US set carries them; the Brier beside each raw
    # outcome is not used here, the label is the own-move rule below)
    cone = [{**st, "prior": (0.5 if st["prior"] == "running" else float(st["prior"]["US"]))}
            for st in spec.protocol()[0]["cone"]]
    plan = spec.windows()["BASE5"]
    lo, hi = PROTO["range"]
    ev = pd.read_csv(ROOT / PROTO["events"], dtype={"ticker": str, "session": str, "twins": str}, keep_default_na=False)
    ev = ev[(ev["session"] >= lo) & (ev["session"] <= hi)].sort_values(["session", "ticker"]).reset_index(drop=True)
    m, *_ = build.market(MANIFESTS / PROTO["manifest"])
    tickers, dates = list(m.tickers.astype(str)), list(m.dates.astype(str))
    idx = {t: i for i, t in enumerate(tickers)}
    didx = {s: i for i, s in enumerate(dates)}

    # 1. outcomes, read once, kept beside each event (never shown to a forecast made before they resolved)
    events = []
    for r in ev.itertuples(index=False):
        n, d = idx[r.ticker], didx[r.session]
        tw = [idx[t] for t in r.twins.split("|") if t in idx]
        x = np.array([float(getattr(r, k)) for k in learner3.FEATURES])
        events.append({"set_id": r.set_id, "ticker": r.ticker, "session": r.session, "d": d, "x": x,
                       "features": {k: float(getattr(r, k)) for k in learner3.FEATURES},
                       "outcomes": outcomes_of(m, n, d, tw, cone, plan)})

    # 2. the learner, session by session, as the US routine runs it (forecast, then that session's scoring)
    history = list(learner3.history_rows())
    cc = call_cert.models()
    hist_cal = list(zip(cc["cal_p"], cc["cal_y"]))
    forecasts = {}
    sessions = sorted({e["session"] for e in events})
    for s in sessions:
        d = didx[s]
        known = []   # (event, statement) resolved by the previous session's close
        for e in events:
            if e["session"] >= s or e["set_id"] not in forecasts:
                continue
            for stmt, o in e["outcomes"].items():
                if o is not None and o["y"] is not None and didx.get(o["resolved"], 10 ** 9) <= d - 1:
                    known.append((e, stmt, o))
        raw_down = [o["raw"] for e, stmt, o in known if stmt == H and o["raw"] is not None]
        p0_down = float(np.mean(raw_down)) if len(raw_down) >= spec.RUNNING_MIN_N else 0.5
        live = [Row("PATH", TASK[stmt], TASK[stmt], e["x"], float(forecasts[e["set_id"]][stmt]["p0"]), float(o["y"]), 1.0)
                for e, stmt, o in known]
        model, bench = fit(history + live)
        by_task: dict[str, list[Row]] = {}
        for r in live:
            by_task.setdefault(r.task, []).append(r)
        state = L2.State({"PATH": model}, {t: L2.anchor_fit(rs) for t, rs in sorted(by_task.items())}, {})
        earlier = [e["x"] for e in events if e["session"] < s]
        centres = {} if not earlier else {TASK[st]: np.mean(earlier, axis=0) for st in learner3.STATEMENTS}
        cal_prior = [(forecasts[e["set_id"]]["cert_score"], o["y"]) for e, stmt, o in known if stmt == H]
        cert = call_cert.certificate(hist_cal + cal_prior)
        for e in events:
            if e["session"] != s:
                continue
            sdict = {"cone": [{"id": BASE[H], "prior": p0_down}, {"id": BASE[C], "prior": FADE_PRIOR_US}]}
            fc = learner3.forecast_set(sdict, e["x"], state, bench, {}, centres)
            score = call_cert.score(e["features"])
            forecasts[e["set_id"]] = {**fc, "cert_score": score, "cert_threshold": cert["chosen"],
                                      "cert_call": cert["chosen"] is not None and score >= cert["chosen"],
                                      "n_live_rows": len(live), "p0_down": p0_down}

    # 3. pairs and the registered statistic
    pairs = []
    for e in events:
        f = forecasts[e["set_id"]]
        for stmt, o in e["outcomes"].items():
            if o is None or o["y"] is None:
                continue
            pairs.append({"set_id": e["set_id"], "event_key": e["set_id"], "statement": stmt, "kind": "PATH",
                          "family": learner3.FAMILY, "session": e["session"], "window": learner3.STATEMENTS[stmt][1],
                          "resolved_at": f"{o['resolved']}T21:00:00Z", "y": float(o["y"]), "anchor": f[stmt]["anchor"],
                          "raw": f[stmt]["raw"], "bench": f[stmt]["bench"], "published": f[stmt]["raw"], "call": {}, "w": 1.0})
    claim = learner3.claim(pairs, proto24["claim"])
    per = {}
    for stmt in learner3.STATEMENTS:
        sp = [p for p in pairs if p["statement"] == stmt]
        y = np.array([p["y"] for p in sp])
        days = learner3.BLOCKS[learner3.STATEMENTS[stmt][2]][0]

        def gain(key, against):
            obs = learner3.observations(sp, "9999-12-31T00:00:00Z", days, key, against)
            if len(obs) < 2:
                return None
            g = np.array([o[0] for o in obs])
            return {"mean": float(g.mean()), "se": float(g.std(ddof=1) / np.sqrt(len(g))), "blocks": len(obs)}
        per[stmt] = {"n": len(sp), "rate": float(y.mean()) if len(sp) else None,
                     "auc": learner3._auc(np.array([p["raw"] for p in sp]), y) if len(sp) else None,
                     "auc_bench": learner3._auc(np.array([p["bench"] for p in sp]), y) if len(sp) else None,
                     "brier_gain_vs_base": gain("raw", "anchor"), "bench_gain_vs_base": gain("bench", "anchor"),
                     "brier_gain_vs_bench": gain("raw", "bench")}
    months = {}
    for p in [p for p in pairs if p["statement"] == H]:
        months.setdefault(p["session"][:7], []).append(p)
    by_month = {k: {"n": len(v), "rate": float(np.mean([p["y"] for p in v])),
                    "auc": learner3._auc(np.array([p["raw"] for p in v]), np.array([p["y"] for p in v]))}
                for k, v in sorted(months.items())}

    # 4. the certified calls
    calls = [(e, forecasts[e["set_id"]]) for e in events if forecasts[e["set_id"]]["cert_call"]]
    graded = [(e, f) for e, f in calls if e["outcomes"][H] is not None and e["outcomes"][H]["y"] is not None]
    wrong = sum(1 for e, f in graded if e["outcomes"][H]["y"] == 0)
    cert_out = {"calls": len(calls), "graded": len(graded), "wrong": wrong,
                "losing_rate": (wrong / len(graded)) if graded else None, "certified_bound": call_cert.ALPHA,
                "p_losing_rate_at_or_above_bound": (risk_control.p_value(wrong, len(graded), call_cert.ALPHA) if graded else None),
                "share_of_events": len(calls) / len(events) if events else None,
                "calls_list": [{"ticker": e["ticker"], "session": e["session"], "score": round(f["cert_score"], 4),
                                "threshold": round(f["cert_threshold"], 4) if f["cert_threshold"] is not None else None,
                                "dumped": (e["outcomes"][H] or {}).get("y")} for e, f in calls]}

    rows_out = [{"set_id": e["set_id"], "ticker": e["ticker"], "session": e["session"],
                 **{f"{stmt}_raw": forecasts[e["set_id"]][stmt]["raw"] for stmt in learner3.STATEMENTS},
                 **{f"{stmt}_bench": forecasts[e["set_id"]][stmt]["bench"] for stmt in learner3.STATEMENTS},
                 **{f"{stmt}_anchor": forecasts[e["set_id"]][stmt]["anchor"] for stmt in learner3.STATEMENTS},
                 **{f"{stmt}_y": (e["outcomes"][stmt] or {}).get("y") for stmt in learner3.STATEMENTS},
                 **{f"{stmt}_raw_move": (e["outcomes"][stmt] or {}).get("raw") for stmt in learner3.STATEMENTS},
                 "cert_score": forecasts[e["set_id"]]["cert_score"], "cert_call": forecasts[e["set_id"]]["cert_call"],
                 "n_live_rows_at_forecast": forecasts[e["set_id"]]["n_live_rows"]} for e in events]
    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows_out).to_csv(RESULTS / "forecasts.csv.gz", index=False)
    result = {"study": PROTO["study_id"], "ran_at": utc_stamp(), "range": PROTO["range"], "events": len(events),
              "sessions": len(sessions), "pairs": len(pairs), "claim": claim, "statements": per, "by_month": by_month,
              "certified_calls": cert_out,
              "raw_dump_rate_next_session": float(np.mean([e["outcomes"][H]["raw"] for e in events
                                                           if e["outcomes"][H] is not None and e["outcomes"][H]["raw"] is not None])),
              "ungraded": {stmt: sum(1 for e in events if e["outcomes"][stmt] is None or e["outcomes"][stmt]["y"] is None)
                           for stmt in learner3.STATEMENTS},
              "entry_status": dict(Counter((e["outcomes"][C] or {}).get("entry_status") for e in events)),
              "forecasts_file": "results/forecasts.csv.gz"}
    (RESULTS / "RESULT.json").write_text(json.dumps(result, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("by_month",)}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

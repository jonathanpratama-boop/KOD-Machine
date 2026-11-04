"""KILL_TEST_2020_2022: the one-shot run of PROTOCOL.md (code v2, ADDENDUM_1.md). Checks PINS_v2.json, refuses if results/RESULT.json (or the trial
file) exists, loads the pinned US repair panel, applies the funnel and the three abstention rules, then the GO rule on
counts before any return is read; only on GO the mean excess of the FIRE events with its week-cluster bootstrap t and
the verdict. Writes results/RESULT.json, the executed events, and the counted trial file.
Usage (from idx-signals/): python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import kt_lib_v2 as kt  # noqa: E402  (ADDENDUM_1: v1 kt_lib.py and run.py must not be run)
from idxsig import event_study as es, global_panel  # noqa: E402

PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
PANEL_MANIFEST = ROOT / PROTOCOL["panel_manifest"]
OUT = HERE / "results"
TRIAL_ID = "CATALYST_REGISTER_v1_SEC13D_KILL_TEST_2020_2022"
TRIAL = ROOT / "research" / "QUANT_GRADE" / "trials" / f"{TRIAL_ID}.json"
START, END = "2020-06-01", "2022-12-30"  # signal sessions from 2020-06-30; no event scored past 2022-12-30
HOLD = PROTOCOL["plan"]["hold"]
CTRL = PROTOCOL["controls"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_pins() -> dict:
    pins = json.loads((HERE / "PINS_v2.json").read_text(encoding="utf-8"))
    bad = [p for p, h in pins["files"].items() if sha(ROOT / p) != h]
    if bad:
        sys.exit(f"error: files differ from PINS_v2.json: {bad}")
    if pins["panel_sha256"] != PROTOCOL["panel_sha256"]:
        sys.exit("error: the pinned panel is not the protocol's")
    return pins


def bars(df: pd.DataFrame, tickers):
    """(adjusted close, as-traded close) by (ticker, ISO day), from the panel's close and unit_factor."""
    d = df[df["ticker"].isin(set(tickers))]
    d = d.assign(day=d["date"].dt.strftime("%Y-%m-%d"))
    d = d[(d["day"] >= START) & (d["day"] <= END)]
    traded = d["close"] * d["unit_factor"].fillna(1.0)
    look = dict(zip(zip(d["ticker"], d["day"]), zip(d["close"].astype(float), traded.astype(float))))
    return lambda t, day: look.get((t, day))


def execute(prep, ev: pd.DataFrame) -> pd.DataFrame:
    """idxsig.event_study.run_events at the protocol's plan and controls; public_date is the signal session, so the
    harness buys at the open of the entry session."""
    res = es.run_events(prep, ev.assign(public_date=ev["signal_session"]), es.us_config(hold=HOLD), draws=CTRL["draws"],
                        seed=CTRL["seed"], controls_version=CTRL["version"], overlap=CTRL["overlap"])
    if not (res["signal_date"] == res["signal_session"]).all():
        sys.exit("error: a harness signal session differs from the protocol's")
    entered = res["entry_date"] != ""
    if not (res.loc[entered, "entry_date"] == res.loc[entered, "entry_session"]).all():
        sys.exit("error: a harness entry differs from the protocol's entry session")
    return res


def counts(ev: pd.DataFrame) -> dict:
    return {"filings": int(len(ev)), "drops": {k: int((ev["drop"] == k).sum()) for k in kt.DROPS},
            "classified": int((ev["drop"] == "").sum()), "FIRE": int((ev["cls"] == "FIRE").sum()),
            "ABSTAIN": int((ev["cls"] == "ABSTAIN").sum()),
            "rules": {k: int(ev[k].sum()) for k in ("DILUTION_RECENT", "MOVED_ALREADY", "MICROCAP", "MV_UNKNOWN")},
            "position": {k: int(v) for k, v in ev.loc[ev["drop"] == "", "position"].value_counts().items()}}


def trial(res: dict) -> dict:
    v = res["verdict"]
    p = res.get("primary", {}).get("p_one_sided")
    base = {"id": TRIAL_ID, "experiment": "CATALYST_REGISTER_v1", "date": res["run_at"][:10],
            "hypothesis": ("kill test: original Schedule 13D filings that the SEC13D abstention rule lets fire (2020-07 to "
                           "2022-11 entries) beat matched random entries over 20 sessions, bought at the open of the first "
                           "session whose 09:15 New York is after acceptance; survivor-only prices (can fail, cannot confirm)"),
            "one_sided_p": p, "variants_searched": 1, "counted": True, "registered": PROTOCOL["frozen"]}
    if v == "INCONCLUSIVE":
        return {**base, "p_source": "none: the GO rule failed, no return was read",
                "outcome": f"INCONCLUSIVE: {res['go']['scored_fire']} scored FIRE events, fewer than {kt.GO_MIN}",
                "note": "research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/results/RESULT.json; counts only."}
    pr = res["primary"]
    return {**base, "p_source": (f"research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/results/RESULT.json primary.p_one_sided "
                                 f"(ISO-week cluster bootstrap t {pr['t']:.2f}, {kt.RESAMPLES} resamples), normal one-sided"),
            "outcome": v + (" (advise the owner to stop the prospective SEC13D family)" if v == "KILL"
                            else " (not a confirmation: survivor-only prices bias it upward)"),
            "note": (f"FIRE scored {pr['n']}: mean excess {pr['mean']:+.4f} (se {pr['se']:.4f}, 95% {pr['lo95']:+.4f} to "
                     f"{pr['hi95']:+.4f}), median {pr['median']:+.4f}, win rate {pr['win_rate']:.3f}. "
                     "Descriptive classes in RESULT.json.")}


def main() -> int:
    if (OUT / "RESULT.json").exists() or TRIAL.exists():
        sys.exit("error: results/RESULT.json or the trial file exists; this test runs once")
    pins = check_pins()
    df, meta = global_panel.load(PANEL_MANIFEST)
    if meta["sha256"] != PROTOCOL["panel_sha256"] or meta["_manifest_sha256"] != pins["files"][PROTOCOL["panel_manifest"]]:
        sys.exit("error: the panel differs from the protocol or PINS_v2.json")
    sessions = np.array(sorted(df["date"].dt.strftime("%Y-%m-%d").unique()))
    sessions = sessions[sessions <= END]
    raw = pd.read_csv(HERE / "events.csv.gz", dtype=str, keep_default_na=False, na_values=[""])
    raw["subject_cik"] = pd.to_numeric(raw["subject_cik"])
    ev = kt.funnel(raw, sessions, set(df["ticker"].unique()))
    ev = kt.classify(ev, bars(df, ev.loc[ev["drop"] == "", "ticker"]))
    n = counts(ev)
    cls = ev[ev["drop"] == ""].reset_index(drop=True)

    prep = es.prepare_us(df, START, END, controls_version=CTRL["version"])
    if str(prep.m.dates[-1]) > END:
        sys.exit("error: the window reaches past 2022-12-30")
    OUT.mkdir(exist_ok=True)
    ev.drop(columns=["coverage", "dilution", "opforms", "shares"]).assign(
        coverage=[json.dumps(c, default=float) if c else "" for c in ev["coverage"]]).to_csv(OUT / "funnel.csv.gz", index=False)
    fire_ev = cls[cls["cls"] == "FIRE"].reset_index(drop=True)
    fire = execute(prep, fire_ev) if len(fire_ev) else pd.DataFrame(columns=["status", "control_n", "excess", "coverage"])
    f = kt.scored(fire)  # counts only until the GO rule has been applied
    go = {"scored_fire": int(len(f)), "need": kt.GO_MIN, "go": kt.go(len(f)),
          "status": {k: int(v) for k, v in fire["status"].value_counts().items()}}
    res = {"experiment": "KILL_TEST_2020_2022", "protocol": {"id": PROTOCOL["protocol_id"], "sha256": pins["files"][
        "research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/protocol.json"]},
           "label": "historical, one shot; survivor-only prices (can fail, cannot confirm); paper only",
           "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "window": [START, END],
           "panel": {"manifest": PROTOCOL["panel_manifest"], "sha256": meta["sha256"]}, "pins": pins, "funnel": n, "go": go}
    if not go["go"]:
        res["verdict"] = "INCONCLUSIVE"
    else:
        res["primary"] = kt.describe(f)
        res["verdict"] = kt.verdict(len(f), res["primary"]["mean"])
        every = execute(prep, cls)
        s = kt.scored(every)
        res["descriptive"] = {"ABSTAIN": kt.describe(s[s["cls"] == "ABSTAIN"]), "ALL": kt.describe(s),
                              "FIRE_in_joint_run": kt.describe(s[s["cls"] == "FIRE"]),
                              **{k: kt.describe(s[s[k]]) for k in ("DILUTION_RECENT", "MOVED_ALREADY", "MICROCAP", "MV_UNKNOWN")},
                              "status_all": es.status_counts(every)}
        every.drop(columns=["coverage"]).to_csv(OUT / "events_all.csv", index=False)
        fire.drop(columns=["coverage"]).to_csv(OUT / "events_fire.csv", index=False)
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    TRIAL.write_text(json.dumps(trial(res), indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: res.get(k) for k in ("funnel", "go", "primary", "verdict")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

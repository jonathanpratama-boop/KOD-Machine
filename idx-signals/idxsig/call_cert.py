"""Certified dump calls beside LEARNER v2.4: the shadow report research/CALL_CERT_v1 asked for (paper/CALL_CERT.md).

CALL_CERT_v1 found one call that can be certified: "this spiking stock closes 10% lower at the next session, on its own"
(NEXT_DUMP10_1), certified right at least half the time by Learn then Test, and the certificate held out of time. This
module runs that same procedure next to the live challenger without touching it:

- the scorer is CALL_CERT_v1's model (penalised logistic regression on v2.4's 33 features, TA_HISTORY_v1's fit), fitted
  on the whole pinned warm start (2020-2023);
- each live call reads the 33 features v2.4 already sealed in its own forecast record (paper/learner_v3.jsonl), so the
  shadow call is a deterministic function of a hash-chained record;
- the bar for a forecast is certified on calibration scores resolved before that forecast was made: the 2022 and 2023
  scores of models that never saw those years, plus every live forecast resolved before it, each live score coming from
  the warm-start model (it never saw a live outcome). 2023 alone does not certify (the strictest 1%: 15 calls, 4 wrong,
  p 0.059), so both out-of-time years are pooled; that choice was made before any live outcome existed;
- the report shows each call, its outcome when resolved, and the realised losing rate beside the certified level, with
  the binomial p-value that the true rate exceeds it.

Nothing here changes v2.4's forecasts, calls, gate or ledger; the report is rewritten from the ledgers each time.
"""
from __future__ import annotations

import gzip
import importlib.util
import csv
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import learner3, paper, risk_control as rc
from .provenance import PKG_ROOT, sha256_file, utc_stamp

STATEMENT = "NEXT_DUMP10_1"
ALPHA, DELTA, MIN_CALLS = 0.5, 0.05, 10
SHARES = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
CALIBRATION = ((("2020-01-02", "2021-12-31"), ("2022-01-01", "2022-12-31")),   # (fit, scored) pairs: each year scored
               (("2020-01-02", "2022-12-31"), ("2023-01-01", "2023-12-29")))   # by a model that never saw it
LIVE_FIT = ("2020-01-02", "2023-12-29")
REPORT = paper.PAPER / "CALL_CERT.md"
STUDY = "research/CALL_CERT_v1"


def _ta():
    spec = importlib.util.spec_from_file_location("ta_run", PKG_ROOT / "research" / "TA_HISTORY_v1" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=1)
def _history() -> pd.DataFrame:
    if sha256_file(learner3.HISTORY) != learner3.HISTORY_SHA256:
        raise RuntimeError("the warm start does not match its pinned sha256")
    ev = pd.read_csv(learner3.HISTORY, dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    return ev[ev[f"y_{STATEMENT}"].notna()].reset_index(drop=True)


def _window(g: pd.DataFrame, span: tuple[str, str]) -> pd.DataFrame:
    return g[(g["session"] >= span[0]) & (g["session"] <= span[1])]


@lru_cache(maxsize=1)
def models() -> dict:
    """The calibration scores (2022 and 2023, each from a model fitted only on earlier years) and the live scorer
    (fit 2020-2023)."""
    ta, ev, cols, col = _ta(), _history(), list(learner3.FEATURES), f"y_{STATEMENT}"
    cal_p, cal_y = [], []
    for fit_span, score_span in CALIBRATION:
        tr, te = _window(ev, fit_span), _window(ev, score_span)
        Xa, Xb = ta.design(tr, te, cols)
        b = ta.fit(Xa, tr[col].to_numpy(float))
        cal_p += (1 / (1 + np.exp(-(Xb @ b)))).tolist()
        cal_y += te[col].to_numpy(int).tolist()
    live_tr = _window(ev, LIVE_FIT)
    a = live_tr[cols].to_numpy(float)
    mu, sd = np.nanmean(a, axis=0), np.nanstd(a, axis=0)
    mu, sd = np.where(np.isfinite(mu), mu, 0.0), np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
    Xl = np.c_[np.ones(len(a)), np.nan_to_num((a - mu) / sd)]
    beta = ta.fit(Xl, live_tr[col].to_numpy(float))
    return {"cal_p": cal_p, "cal_y": cal_y, "mu": mu, "sd": sd, "beta": beta}


def score(features: dict) -> float:
    m = models()
    x = np.array([float(features.get(k, np.nan)) for k in learner3.FEATURES])
    z = np.r_[1.0, np.nan_to_num((x - m["mu"]) / m["sd"])]
    return float(1 / (1 + np.exp(-(z @ m["beta"]))))


def certificate(cal: list[tuple[float, int]]) -> dict:
    """Learn then Test on (score, outcome) calibration pairs: DUMP call when score >= threshold, wrong when no dump."""
    s = [p for p, _ in cal]
    w = [1 - y for _, y in cal]
    ths = [float(np.quantile(s, 1 - f)) for f in SHARES]
    out = rc.certify(s, w, ths, ALPHA, DELTA, MIN_CALLS)
    out["n_calibration"] = len(cal)
    return out


def rows(records: list[dict] | None = None, lrecs: list[dict] | None = None, asof: str | None = None) -> list[dict]:
    """One row per live v2.4 forecast: shadow score, the bar certified from what had resolved before it, the call, and
    the outcome when it has resolved by `asof`."""
    from . import learner2 as L2
    records = L2.all_records() if records is None else records
    lrecs = learner3.lines() if lrecs is None else lrecs
    asof = asof or utc_stamp()
    outc = learner3.outcomes(records, asof)
    m = models()
    hist = list(zip(m["cal_p"], m["cal_y"]))
    live, seen = [], set()
    for f in sorted((f for f in lrecs if f.get("type") == learner3.RECORD), key=lambda f: f["made_at"]):
        if f["set_id"] in seen or STATEMENT not in f.get("forecasts", {}):
            continue
        seen.add(f["set_id"])
        o = learner3.outcome_of(outc, f["set_id"], STATEMENT)
        live.append({"set_id": f["set_id"], "ticker": f.get("ticker"), "session": f["signal_session"], "made_at": f["made_at"],
                     "score": score(f.get("features", {})), "v24_raw": f["forecasts"][STATEMENT]["raw"],
                     "y": (None if o is None or o[1] > asof else int(o[0])), "resolved_at": (None if o is None else o[1])})
    for r in live:
        prior = [(q["score"], q["y"]) for q in live
                 if q["y"] is not None and q["resolved_at"] is not None and q["resolved_at"] < r["made_at"]]
        cert = certificate(hist + prior)
        r["threshold"], r["n_calibration"], r["n_live_calibration"] = cert["chosen"], cert["n_calibration"], len(prior)
        r["call"] = cert["chosen"] is not None and r["score"] >= cert["chosen"]
    return live


def summary(live: list[dict]) -> dict:
    calls = [r for r in live if r["call"]]
    res = [r for r in calls if r["y"] is not None]
    wrong = sum(1 - r["y"] for r in res)
    n = len(res)
    return {"forecasts": len(live), "calls": len(calls), "resolved_calls": n, "wrong": wrong,
            "losing_rate": (wrong / n if n else None),
            "p_exceeds_alpha": (1.0 - rc.binom_cdf(wrong - 1, n, ALPHA) if n else None),
            "base_rate_live": (float(np.mean([r["y"] for r in live if r["y"] is not None]))
                               if any(r["y"] is not None for r in live) else None)}


def render(live: list[dict], asof: str) -> str:
    s = summary(live)
    m = models()
    cert = certificate(list(zip(m["cal_p"], m["cal_y"])))
    lr = "no resolved call yet" if s["losing_rate"] is None else (
        f"{s['wrong']} wrong of {s['resolved_calls']} ({s['losing_rate']:.1%}); p that the true rate exceeds 50%: "
        f"{s['p_exceeds_alpha']:.3f}")
    out = [f"# Certified dump calls (shadow, beside LEARNER v2.4)", "",
           f"Generated {asof} from paper/learner_v3.jsonl and the registers. Method and history check: `{STUDY}` "
           "(the certificate held on 2023: 44 calls, right 70.5%). This report changes nothing in v2.4.", "",
           "## The three plain answers", "",
           "- **What is predicted:** for a US stock that just closed +30% or more, that it closes at least 10% lower at the "
           "next session while most of its twins do not. A call is made only when the shadow score clears a bar certified "
           "by Learn then Test.",
           "- **What counts as success:** the calls are wrong at most half the time (certified level 50%, confidence 95%); "
           "the realised losing rate stays at or under it.",
           f"- **Evidence so far:** {s['forecasts']} live forecasts, {s['calls']} calls, {lr}.", "",
           "## The bar", "",
           f"- From history alone (2022 and 2023 scores of models that never saw those years, {cert['n_calibration']} events): "
           + (f"threshold {cert['chosen']:.3f}" if cert["chosen"] is not None else "nothing certifies") + ".",
           "- Each live forecast uses the bar certified from history plus every live outcome resolved before it was made; "
           "the bar moves as outcomes resolve (the history check found the 2022 bar fired 3.1% of 2023's events, not 1%).",
           "- 2023 on its own does not certify (strictest 1%: 15 calls, 4 wrong, p 0.059 against 0.05); pooled with 2022 it "
           "does, at about the top 5% of spikes. Expect few calls.",
           "", "## Live forecasts", "",
           "| Signal session | Ticker | Shadow score | Bar | Call | v2.4 raw | Outcome |", "|---|---|---|---|---|---|---|"]
    for r in sorted(live, key=lambda r: (r["session"], r["ticker"] or ""), reverse=True):
        outcome = "pending" if r["y"] is None else ("dumped" if r["y"] else "did not dump")
        bar = "none certified" if r["threshold"] is None else f"{r['threshold']:.3f}"
        out.append(f"| {r['session']} | {r['ticker']} | {r['score']:.3f} | {bar} | {'**DUMP**' if r['call'] else '-'} | "
                   f"{r['v24_raw']:.3f} | {outcome} |")
    if not live:
        out.append("| - | - | - | - | - | - | no live forecast yet |")
    out += ["", "## Limits", "",
            "- The bound treats events as independent; spikes cluster, so it is optimistic, and the realised rate is the check.",
            "- History prices are survivor-only; the live record is the honest one.",
            "- A shadow report: no order, no change to the frozen challenger."]
    return "\n".join(out) + "\n"


def write_report(asof: str | None = None) -> Path:
    asof = asof or utc_stamp()
    REPORT.write_text(render(rows(asof=asof), asof), encoding="utf-8")
    return REPORT

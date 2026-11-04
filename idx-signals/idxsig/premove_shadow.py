"""PREMOVE_SHADOW_v1: the prospective shadow trial of the pre-move benchmark (research/PREMOVE_SHADOW_v1).

Three frozen arms rank the same crypto candidates every day, before any outcome exists:

- summary   the default research baseline (PR #19's frozen summary model)
- sequence  the research challenger (PR #19's frozen sequence model)
- shuffled  the control: the sequence recipe fitted on 2020-2021 with each row's 20-day window shuffled
            (return, range and volume of one day kept together), so it keeps the sequence values but not their order

Daily (`forecast`): from the crypto routine's own Binance pull, the last completed UTC day is scored by all three
arms; each arm's five-name shortlist for the early population (and for all candidates) and every eligible
candidate's upside probability are sealed in the hash-chained ledger paper/premove_shadow.jsonl, externally
timestamped. Later (`score`): once five more daily bars exist, the labels of that day's candidates are appended.
`report` reads the ledger; the verdict is computed once, at the frozen end of the trial (protocol.json).
Paper only: no orders, no retuning, no performance-based stopping.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import paper
from .global_panel import LEVERAGED, STABLE
from .premove_core import TARGETS, FittedModel, build_examples
from .provenance import PKG_ROOT, read_manifest, sha256_file, utc_stamp

STUDY = PKG_ROOT / "research" / "PREMOVE_SHADOW_v1"
PROTOCOL = STUDY / "protocol.json"
FROZEN = PKG_ROOT / "research" / "PREMOVE_SEQUENCE_v1" / "runs" / "20261030T024900Z" / "models.json"
CONTROL = STUDY / "control_model.json"
LEDGER = paper.PAPER / "premove_shadow.jsonl"
REPORT = paper.PAPER / "PREMOVE_SHADOW.md"
ARMS = ("summary", "sequence", "shuffled")
POPULATIONS = ("early", "all")
TOP_K = 5
HORIZON = 5
LOOKBACK = 20
FORECAST, RESOLUTION = "PREMOVE_SHADOW_FORECAST", "PREMOVE_SHADOW_RESOLUTION"


# ------------------------------------------------------------------------------------------------ models
def model_from_record(record: dict) -> FittedModel:
    def arr(name):
        return np.asarray(record[name], dtype=float)

    return FittedModel(
        feature_columns=tuple(record["feature_columns"]),
        sequence_columns=tuple(record["sequence_columns"]),
        mean=arr("mean"),
        scale=arr("scale"),
        sequence_mean=arr("sequence_mean"),
        sequence_scale=arr("sequence_scale"),
        components=arr("components"),
        coefficients=arr("coefficients"),
        constants=np.array([np.nan if v is None else v for v in record["constants"]], dtype=float),
        iterations=tuple(record["iterations"]),
        converged=tuple(record["converged"]),
        objectives=tuple(record["objectives"]),
    )


def load_arms() -> dict[str, FittedModel]:
    proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for path, want in proto["pins"].items():
        if sha256_file(PKG_ROOT / path) != want:
            raise RuntimeError(f"{path} differs from the frozen trial; refusing to forecast")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    control = json.loads(CONTROL.read_text(encoding="utf-8"))
    return {
        "summary": model_from_record(frozen["summary"]),
        "sequence": model_from_record(frozen["sequence"]),
        "shuffled": model_from_record(control["model"]),
    }


# ------------------------------------------------------------------------------------------------ control
def _row_seed(ticker: str, day) -> int:
    key = f"PREMOVE_SHADOW_v1|{ticker}|{pd.Timestamp(day).date().isoformat()}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def shuffle_windows(frame: pd.DataFrame, lookback: int = LOOKBACK) -> pd.DataFrame:
    """Each row's 20 lag positions in its own random order (seeded by ticker and date), the same order for its
    return, range and volume, so every day keeps its three observations together but the window loses its order."""
    out = frame.copy()
    kinds = ("return", "range", "volume")
    blocks = {k: out[[f"seq_{k}_{lag:02d}" for lag in range(lookback)]].to_numpy(dtype=float, copy=True) for k in kinds}
    for i, (ticker, day) in enumerate(zip(out["ticker"], out["date"])):
        order = np.random.default_rng(_row_seed(ticker, day)).permutation(lookback)
        for k in kinds:
            blocks[k][i] = blocks[k][i][order]
    for k in kinds:
        out[[f"seq_{k}_{lag:02d}" for lag in range(lookback)]] = blocks[k]
    return out


def score_pool(arms: dict[str, FittedModel], pool: pd.DataFrame, temperatures: dict[str, float]) -> pd.DataFrame:
    """Upside probability of every candidate under each arm, at the arm's frozen calibration temperature."""
    from .premove import probabilities

    scored = pool.copy()
    shuffled = shuffle_windows(pool)
    for name, model in arms.items():
        frame = shuffled if name == "shuffled" else pool
        p = probabilities(model.predict(frame), temperatures[name])
        scored[f"{name}_up"] = p[:, TARGETS.index("up_first")]
    return scored


def temperatures() -> dict[str, float]:
    """PR #19's calibrated temperatures (summary.json) and the control's (control_model.json)."""
    calib = json.loads((FROZEN.parent / "summary.json").read_text(encoding="utf-8"))["calibration"]
    control = json.loads(CONTROL.read_text(encoding="utf-8"))["calibration"]["temperature"]
    return {"summary": float(calib["summary"]["temperature"]), "sequence": float(calib["sequence"]["temperature"]),
            "shuffled": float(control)}


def shortlist(scored: pd.DataFrame, arm: str, k: int = TOP_K) -> pd.DataFrame:
    """The benchmark's rule: highest upside probability, ties by ticker."""
    return scored.sort_values([f"{arm}_up", "ticker"], ascending=[False, True], kind="stable").head(k)


def early(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[(frame.ret1 < 0.10) & (frame.ret5 < 0.20)]


# ------------------------------------------------------------------------------------------------ live data
def live_panel(manifest: Path) -> tuple[pd.DataFrame, dict]:
    """The crypto routine's Binance USDT pull as the benchmark's panel; a bar still open at download is incomplete."""
    header, records = read_manifest(manifest)
    rows = []
    for rec in records:
        base, symbol = rec.get("base_asset"), rec.get("symbol", "")
        if rec.get("http_status") != 200 or not symbol.endswith("USDT") or not base:
            continue
        if base in STABLE or LEVERAGED.search(base):
            continue
        downloaded = datetime.fromisoformat(rec["downloaded_at"].replace("Z", "+00:00"))
        for k in json.loads((PKG_ROOT / rec["path"]).read_text(encoding="utf-8")):
            opened = datetime.fromtimestamp(k[0] / 1000, timezone.utc)
            closes = datetime.fromtimestamp((k[6] + 1) / 1000, timezone.utc)
            rows.append(
                {
                    "date": opened.date().isoformat(),
                    "ticker": symbol,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "value": float(k[7]),
                    "complete_bar": bool(closes <= downloaded),
                }
            )
    return pd.DataFrame(rows), {"manifest": manifest.name, "manifest_sha256": sha256_file(manifest),
                                "pairs": int(len({r["ticker"] for r in rows}))}


def _r(x) -> float | None:
    return None if x is None or not math.isfinite(float(x)) else round(float(x), 6)


# ------------------------------------------------------------------------------------------------ forecast
def forecast(manifest: Path, now: datetime | None = None, records: list[dict] | None = None) -> dict | None:
    """One sealed record for the last completed UTC day, or None when that day is already sealed."""
    now = now or datetime.now(timezone.utc)
    proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    decision = (now.astimezone(timezone.utc).date() - timedelta(days=1)).isoformat()
    if not (proto["trial"]["first_decision"] <= decision <= proto["trial"]["last_decision"]):
        return None
    records = paper.ledger_lines(LEDGER) if records is None and LEDGER.exists() else (records or [])
    if any(r["type"] == FORECAST and r["decision_date"] == decision for r in records):
        return None
    arms = load_arms()
    panel, data = live_panel(manifest)
    examples = build_examples(panel)
    frame = examples.frame
    day = frame.loc[(frame.date == pd.Timestamp(decision)) & frame.eligible & frame.complete_bar]
    if day.empty:
        raise RuntimeError(f"no eligible completed bars for {decision} in {manifest.name}")
    scored = score_pool(arms, day, temperatures())
    shortlists = {
        pop: {
            arm: [{"ticker": r.ticker, "rank": i + 1, "p_up": _r(getattr(r, f"{arm}_up")),
                   "barrier_up": _r(r.barrier_up_fraction)}
                  for i, r in enumerate(shortlist(early(scored) if pop == "early" else scored, arm).itertuples())]
            for arm in ARMS
        }
        for pop in POPULATIONS
    }
    candidates = {
        r.ticker: {"early": bool(r.ret1 < 0.10 and r.ret5 < 0.20), **{a: _r(getattr(r, f"{a}_up")) for a in ARMS}}
        for r in scored.itertuples()
    }
    return {
        "type": FORECAST,
        "trial": proto["trial_id"],
        "protocol_sha256": sha256_file(PROTOCOL),
        "decision_date": decision,
        "made_at": utc_stamp(now),
        "entry": f"open of {(date.fromisoformat(decision) + timedelta(days=1)).isoformat()} UTC (label reference only)",
        "data": data,
        "eligible": int(len(scored)),
        "eligible_early": int(len(early(scored))),
        "shortlists": shortlists,
        "candidates": candidates,
    }


# ------------------------------------------------------------------------------------------------ outcomes
def score(manifest: Path, records: list[dict] | None = None) -> list[dict]:
    """Labels for every sealed day whose five outcome bars are complete in this pull (one resolution per day)."""
    records = paper.ledger_lines(LEDGER) if records is None else records
    done = {r["decision_date"] for r in records if r["type"] == RESOLUTION}
    due = [r for r in records if r["type"] == FORECAST and r["decision_date"] not in done]
    if not due:
        return []
    panel, data = live_panel(manifest)
    complete = panel.loc[panel.complete_bar, "date"]
    last_complete = complete.max() if len(complete) else None
    frame = build_examples(panel).frame
    out = []
    for f in sorted(due, key=lambda r: r["decision_date"]):
        end = (date.fromisoformat(f["decision_date"]) + timedelta(days=HORIZON)).isoformat()
        if last_complete is None or last_complete < end:
            continue
        rows = frame.loc[frame.date == pd.Timestamp(f["decision_date"])].set_index("ticker")
        labels = {}
        for ticker in f["candidates"]:
            if ticker not in rows.index or not bool(rows.at[ticker, "label_known"]):
                labels[ticker] = None
                continue
            r = rows.loc[ticker]
            labels[ticker] = {
                "class": next(t for t in TARGETS if r[t] == 1),
                "first_hit_date": None if pd.isna(r.first_hit_date) else str(pd.Timestamp(r.first_hit_date).date()),
            }
        out.append(
            {
                "type": RESOLUTION,
                "trial": f["trial"],
                "decision_date": f["decision_date"],
                "forecast_record_hash": f["record_hash"],
                "resolved_at": utc_stamp(),
                "data": data,
                "labels": labels,
                "unknown": sum(v is None for v in labels.values()),
            }
        )
    return out


# ------------------------------------------------------------------------------------------------ analysis
def daily_table(records: list[dict], population: str = "early") -> pd.DataFrame:
    """One row per resolved day and arm: alerts, known hits, censored, the hit rate (censored count as non-hits)."""
    res = {r["decision_date"]: r for r in records if r["type"] == RESOLUTION}
    rows = []
    for f in records:
        if f["type"] != FORECAST or f["decision_date"] not in res:
            continue
        labels = res[f["decision_date"]]["labels"]
        for arm in ARMS:
            picks = [p["ticker"] for p in f["shortlists"][population][arm]]
            known = [labels.get(t) for t in picks]
            hits = sum(1 for k in known if k and k["class"] == "up_first")
            rows.append({"date": f["decision_date"], "arm": arm, "alerts": len(picks), "hits": hits,
                         "censored": sum(k is None for k in known), "hit_rate": hits / len(picks) if picks else np.nan,
                         "episodes": [f"{t}|{k['first_hit_date']}" for t, k in zip(picks, known)
                                      if k and k["class"] == "up_first"]})
    return pd.DataFrame(rows)


def paired_block_bootstrap(a: pd.Series, b: pd.Series, *, block: int, draws: int, seed: int) -> dict:
    """Difference of mean daily hit rates (a - b) with a moving calendar-block bootstrap over paired days."""
    d = (a - b).dropna().to_numpy()
    n = len(d)
    if n < block:
        return {"days": n, "diff": float(d.mean()) if n else None, "lo95": None, "hi95": None}
    rng = np.random.default_rng(seed)
    starts = n - block + 1
    k = math.ceil(n / block)
    means = np.array([np.concatenate([d[s:s + block] for s in rng.integers(0, starts, k)])[:n].mean()
                      for _ in range(draws)])
    return {"days": n, "diff": float(d.mean()), "lo95": float(np.quantile(means, 0.025)),
            "hi95": float(np.quantile(means, 0.975))}


def analyse(records: list[dict]) -> dict:
    proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    bs = proto["analysis"]["bootstrap"]
    out = {"populations": {}}
    for pop in POPULATIONS:
        t = daily_table(records, pop)
        if t.empty:
            out["populations"][pop] = {"resolved_days": 0}
            continue
        wide = t.pivot(index="date", columns="arm", values="hit_rate").sort_index()
        per_arm = {}
        for arm in ARMS:
            a = t[t.arm == arm]
            eps = {e for row in a.episodes for e in row}
            per_arm[arm] = {"alerts": int(a.alerts.sum()), "hits": int(a.hits.sum()), "censored": int(a.censored.sum()),
                            "hit_rate": float(a.hits.sum() / a.alerts.sum()), "distinct_episodes": len(eps)}
        out["populations"][pop] = {
            "resolved_days": int(len(wide)),
            "arms": per_arm,
            "sequence_minus_summary": paired_block_bootstrap(wide["sequence"], wide["summary"], **bs),
            "sequence_minus_shuffled": paired_block_bootstrap(wide["sequence"], wide["shuffled"], **bs),
        }
    return out


def verdict(records: list[dict], today: str | None = None) -> dict:
    """The frozen decision rule, applied only once the trial's last outcome is due; before that, accumulating."""
    proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    today = today or datetime.now(timezone.utc).date().isoformat()
    a = analyse(records)
    if today < proto["trial"]["final_outcomes_due"]:
        return {"status": "accumulating", "analysis": a}
    e = a["populations"]["early"]
    h = proto["promotion_hurdle"]
    primary, control = e["sequence_minus_summary"], e["sequence_minus_shuffled"]
    promoted = bool(primary["diff"] is not None and primary["lo95"] is not None
                    and primary["diff"] >= h["min_difference"] and primary["lo95"] > 0
                    and e["arms"]["sequence"]["distinct_episodes"] > e["arms"]["summary"]["distinct_episodes"])
    order = bool(control["lo95"] is not None and control["lo95"] > 0)
    return {"status": "final", "analysis": a, "sequence_promoted": promoted,
            "temporal_order_supported": promoted and order,
            "default": "sequence" if promoted else "summary"}


# ------------------------------------------------------------------------------------------------ report
def render(records: list[dict]) -> str:
    proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    v = verdict(records)
    forecasts = [r for r in records if r["type"] == FORECAST]
    lines = [
        "# PREMOVE_SHADOW_v1: prospective shadow trial (paper only)", "",
        f"Generated {utc_stamp()} from `paper/premove_shadow.jsonl`. Protocol `research/PREMOVE_SHADOW_v1/protocol.json`.", "",
        "**What are we predicting?** Each day, which five crypto pairs (not already up 10% today or 20% this week) will "
        "close above a volatility-scaled barrier (at least +10%) before closing below the mirror barrier, within 5 days.", "",
        "**What counts as success?** At the frozen end of the trial, the sequence arm beats the summary arm's early hit "
        f"rate by at least {proto['promotion_hurdle']['min_difference']:.0%} with a paired 95% interval above zero, and "
        "catches more distinct episodes. Order matters only if it also beats the shuffled control.", "",
        f"**What evidence so far?** {len(forecasts)} days sealed, "
        f"{v['analysis']['populations']['early'].get('resolved_days', 0)} resolved. Status: {v['status']}. "
        "No decision is taken before the end.", "",
        f"Trial: decisions {proto['trial']['first_decision']} to {proto['trial']['last_decision']}, final outcomes due "
        f"{proto['trial']['final_outcomes_due']}.", "",
    ]
    e = v["analysis"]["populations"]["early"]
    if e.get("arms"):
        lines += ["| Arm (early population) | Alerts | Upside hits | Censored | Hit rate | Distinct episodes |",
                  "|---|---:|---:|---:|---:|---:|"]
        for arm in ARMS:
            s = e["arms"][arm]
            lines.append(f"| {arm} | {s['alerts']} | {s['hits']} | {s['censored']} | {s['hit_rate']:.2%} | {s['distinct_episodes']} |")
        lines.append("")
    if forecasts:
        f = forecasts[-1]
        lines += [f"Latest sealed day {f['decision_date']} ({f['eligible_early']} early candidates):", ""]
        for arm in ARMS:
            lines.append(f"- {arm}: " + ", ".join(p["ticker"] for p in f["shortlists"]["early"][arm]))
        lines.append("")
    return "\n".join(lines)


def write_report(records: list[dict] | None = None) -> Path:
    records = paper.ledger_lines(LEDGER) if records is None else records
    REPORT.write_text(render(records), encoding="utf-8")
    return REPORT


def verify() -> list[str]:
    if not LEDGER.exists():
        return []
    problems = [f"premove_shadow.jsonl: {p}" for p in paper.verify_chain(LEDGER)]
    recs = paper.ledger_lines(LEDGER)
    by_hash = {r["record_hash"]: r for r in recs}
    seen = set()
    for r in recs:
        if r["type"] == FORECAST:
            if r["decision_date"] in seen:
                problems.append(f"{r['decision_date']}: sealed twice")
            seen.add(r["decision_date"])
            if r["made_at"][:10] <= r["decision_date"]:
                problems.append(f"{r['decision_date']}: sealed before the day closed")
        elif r["type"] == RESOLUTION:
            f = by_hash.get(r["forecast_record_hash"])
            if f is None or f["decision_date"] != r["decision_date"]:
                problems.append(f"{r['decision_date']}: resolution does not point at its forecast")
            elif r["resolved_at"] < f["made_at"]:
                problems.append(f"{r['decision_date']}: resolved before it was forecast")
    return problems

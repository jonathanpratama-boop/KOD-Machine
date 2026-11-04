"""LEARNER_v1 (research/LEARNER_v1/protocol.json): a self-learning layer beside the frozen catalyst families.

It learns, from resolved outcomes only, how far each sealed set's own features should move the sealed prior of each
cone statement, and of a joint TRIANGULATED statement (the stated catalyst happened AND the stock beat its twins). It
speaks with the confidence it has earned: its published forecast is its raw forecast shrunk toward the sealed prior by
alpha, which grows only as its own earlier forecasts beat the priors on outcomes that resolved after them. Every
forecast is sealed before the set's entry cutoff and records the hash of the weights it used; verify() retrains from the
resolutions dated before the forecast and must reproduce that hash. It changes nothing in any family.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import catalysts as cr
from . import paper
from . import speculation as spec
from .provenance import PKG_ROOT, sha256_file, utc_stamp

PROTOCOL_JSON = PKG_ROOT / "research" / "LEARNER_v1" / "protocol.json"
LEDGER = paper.PAPER / "learner.jsonl"
REPORT = paper.PAPER / "LEARNER.md"
VERSION = "LEARNER-v1"
FAMILIES = ("SEC13D", "SEC13D_V2", "DILUTION_8K", "FORM4", "FORM4_SHARP", "IDX_INDEX")
TRIANGLES = {
    "SEC13D_V2": ("MECH_13DA_UP_60", "BEATS_TWINS_20"),
    "FORM4_SHARP": ("MECH_SECOND_BUY_20", "BEATS_TWINS_60"),
}
TRI = "TRIANGULATED"
LAMBDA, MIN_ROWS, CLIP = 20.0, 20, (0.01, 0.99)
N_FULL, SKILL_FULL = 300, 0.05
FEATURE_NAMES = (
    *[f"fam_{f}" for f in FAMILIES],
    "fire",
    "ret1",
    "ret5",
    "ret20",
    "dd60",
    "log_volr",
    "cpos",
    "log_adv",
    "log_close",
    "log_value",
    "has_value",
    "top_exec",
    "owners",
    "lag",
    "pct_inc",
    "has_pct",
    "strong_intent",
    "during",
    "log_mv",
    "has_mv",
    "dilution_recent",
    "microcap",
    "direction",
)


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8")), sha256_file(PROTOCOL_JSON)


def lines(path: Path | None = None) -> list[dict]:
    p = LEDGER if path is None else path
    return paper.ledger_lines(p) if p.exists() else []


# ------------------------------------------------------------------------------- features (sealed fields only)
def _num(x, default=0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _clip(v, lo, hi):
    return max(lo, min(hi, v))


def features(s: dict) -> np.ndarray:
    sig, cov, ev = s.get("signal") or {}, s.get("coverage") or {}, s.get("event") or {}
    inp, rules = cov.get("inputs") or {}, cov.get("rules") or {}
    value = inp.get("total_value")
    pct = (
        ((inp.get("pct_increase") or {}).get("max"))
        if isinstance(inp.get("pct_increase"), dict)
        else None
    )
    mv = inp.get("market_value_usd")
    x = [1.0 if s.get("family") == f else 0.0 for f in FAMILIES]
    x += [1.0 if cov.get("class") == "FIRE" else 0.0]
    x += [_clip(_num(sig.get(k)), -1, 1) for k in ("ret1", "ret5", "ret20", "dd60")]
    x += [
        _clip(math.log(max(_num(sig.get("volr"), 1.0), 1e-3)), -3, 3) / 3,
        _clip(_num(sig.get("cpos"), 0.5), 0, 1),
    ]
    x += [
        math.log10(max(_num(sig.get("adv20_value")), 0) + 1) / 10,
        math.log10(max(_num(sig.get("close"), 1.0), 1e-4)) / 3,
    ]
    x += [
        math.log10(max(_num(value), 0) + 1) / 7 if value is not None else 0.0,
        1.0 if value is not None else 0.0,
    ]
    x += [
        1.0 if inp.get("top_exec") else 0.0,
        min(_num(inp.get("n_owners")), 5) / 5,
        _clip(_num(inp.get("lag_days")), 0, 30) / 30,
    ]
    x += [_clip(_num(pct), 0, 5) / 5 if pct is not None else 0.0, 1.0 if pct is not None else 0.0]
    x += [
        1.0 if (ev.get("strong_intent") or {}).get("strong") else 0.0,
        1.0 if ev.get("position") == "DURING" else 0.0,
    ]
    x += [
        math.log10(max(_num(mv), 1.0)) / 10 if mv is not None else 0.0,
        1.0 if mv is not None else 0.0,
    ]
    x += [
        1.0 if rules.get("DILUTION_RECENT") else 0.0,
        1.0 if rules.get("MICROCAP") else 0.0,
        float(int(s.get("direction", 1))),
    ]
    return np.array(x, dtype=float)


def _logit(p: float) -> float:
    p = _clip(p, *CLIP)
    return math.log(p / (1 - p))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


# ------------------------------------------------------------------------------- training data (resolved before asof)
def _outcomes(records: list[dict], asof: str) -> dict[tuple[str, str], tuple[bool, float]]:
    """(set_id, statement) -> (outcome, sealed prior) for every graded cone statement resolved before asof; a later
    revision of the same (set, window) replaces an earlier one."""
    out: dict[tuple[str, str], tuple[bool, float]] = {}
    for r in records:
        if r["type"] != "RESOLUTION" or not r.get("cone") or (r.get("resolved_at") or "9") >= asof:
            continue
        for c in r["cone"]:
            if c.get("outcome") is not None:
                out[(r["set_id"], c["id"])] = (bool(c["outcome"]), float(c["prior"]))
    return out


def _sealed_priors(s: dict) -> dict[str, float]:
    pri = {c["id"]: float(c["prior"]) for c in s.get("cone", [])}
    tri = TRIANGLES.get(s.get("family"))
    if tri and all(t in pri for t in tri):
        pri[TRI] = pri[tri[0]] * pri[tri[1]]
    return pri


def training_rows(
    records: list[dict], asof: str
) -> dict[str, list[tuple[np.ndarray, float, float]]]:
    sets = {
        r["set_id"]: r
        for r in records
        if r["type"] == "CATALYST_SET" and r.get("family") in FAMILIES
    }
    outc = _outcomes(records, asof)
    rows: dict[str, list] = {}
    for (sid, stmt), (y, prior) in outc.items():
        if sid in sets:
            rows.setdefault(stmt, []).append((features(sets[sid]), _logit(prior), float(y)))
    for sid, s in sets.items():
        tri = TRIANGLES.get(s["family"])
        if not tri or (sid, tri[0]) not in outc or (sid, tri[1]) not in outc:
            continue
        a, b = outc[(sid, tri[0])], outc[(sid, tri[1])]
        rows.setdefault(TRI, []).append((features(s), _logit(a[1] * b[1]), float(a[0] and b[0])))
    return rows


def fit(rows: list[tuple[np.ndarray, float, float]]) -> np.ndarray | None:
    """L2-penalised logistic regression with the prior's logit as an offset (IRLS); None below MIN_ROWS rows."""
    if len(rows) < MIN_ROWS:
        return None
    X = np.array([np.concatenate([[1.0], r[0]]) for r in rows])
    off = np.array([r[1] for r in rows])
    y = np.array([r[2] for r in rows])
    w = np.zeros(X.shape[1])
    pen = LAMBDA * np.eye(X.shape[1])
    for _ in range(50):
        p = _sigmoid(off + X @ w)
        W = p * (1 - p)
        grad = X.T @ (y - p) - pen @ w
        H = X.T @ (X * W[:, None]) + pen
        step = np.linalg.solve(H, grad)
        w = w + step
        if float(np.max(np.abs(step))) < 1e-10:
            break
    return w


def train(records: list[dict], asof: str) -> tuple[dict[str, np.ndarray | None], dict]:
    rows = training_rows(records, asof)
    models = {k: fit(v) for k, v in sorted(rows.items())}
    blob = {k: (None if m is None else [round(float(x), 8) for x in m]) for k, m in models.items()}
    info = {
        "rows": {k: len(v) for k, v in sorted(rows.items())},
        "weights_sha256": hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest(),
    }
    return models, info


def raw_forecast(model: np.ndarray | None, x: np.ndarray, prior: float) -> float:
    if model is None:
        return _clip(prior, *CLIP)
    return float(_clip(_sigmoid(_logit(prior) + float(np.concatenate([[1.0], x]) @ model)), *CLIP))


# ------------------------------------------------------------------------------- earned confidence
def forward_pairs(records: list[dict], lrecs: list[dict], asof: str) -> list[dict]:
    """Every (earlier forecast, statement) whose outcome resolved after the forecast and before asof."""
    outc = _outcomes(records, asof)
    resolved_at = {}
    for r in records:
        if r["type"] == "RESOLUTION" and r.get("resolved_at"):
            for c in r.get("cone", []):
                resolved_at[(r["set_id"], c["id"])] = r["resolved_at"]
    out = []
    for f in lrecs:
        if f.get("type") != "LEARNER_FORECAST" or f["made_at"] >= asof:
            continue
        sid = f["set_id"]
        for stmt, fc in f["forecasts"].items():
            if stmt == TRI:
                tri = TRIANGLES.get(f["family"])
                if not tri or (sid, tri[0]) not in outc or (sid, tri[1]) not in outc:
                    continue
                when = max(resolved_at[(sid, tri[0])], resolved_at[(sid, tri[1])])
                y = outc[(sid, tri[0])][0] and outc[(sid, tri[1])][0]
            elif (sid, stmt) in outc:
                when, y = resolved_at[(sid, stmt)], outc[(sid, stmt)][0]
            else:
                continue
            if when <= f["made_at"]:
                continue
            out.append(
                {
                    "set_id": sid,
                    "statement": stmt,
                    "family": f["family"],
                    "session": f.get("signal_session"),
                    "y": float(y),
                    **{k: fc[k] for k in ("prior", "raw", "published")},
                }
            )
    return out


def alpha_from(pairs: list[dict]) -> tuple[float, dict]:
    n = len(pairs)
    if not n:
        return 0.0, {"n": 0, "skill": None}
    b_raw = float(np.mean([(p["raw"] - p["y"]) ** 2 for p in pairs]))
    b_pri = float(np.mean([(p["prior"] - p["y"]) ** 2 for p in pairs]))
    skill = 1 - b_raw / b_pri if b_pri > 0 else 0.0
    return float(min(1.0, n / N_FULL) * _clip(skill / SKILL_FULL, 0.0, 1.0)), {
        "n": n,
        "skill": skill,
    }


def published(prior: float, raw: float, alpha: float) -> float:
    return float(_clip(_sigmoid(_logit(prior) + alpha * (_logit(raw) - _logit(prior))), *CLIP))


# ------------------------------------------------------------------------------- forecasting
def forecast_records(
    now: datetime, records: list[dict] | None = None, lrecs: list[dict] | None = None
) -> list[dict]:
    """One LEARNER_FORECAST for every sealed set still before its entry cutoff that has none yet."""
    proto, sha = protocol()
    records = cr.cat_lines() if records is None else records
    lrecs = lines() if lrecs is None else lrecs
    asof = utc_stamp(now.astimezone(timezone.utc))
    done = {f["set_id"] for f in lrecs if f.get("type") == "LEARNER_FORECAST"}
    todo = [
        s
        for s in records
        if s["type"] == "CATALYST_SET"
        and s.get("family") in FAMILIES
        and s["entry_cutoff"] > asof
        and s["set_id"] not in done
    ]
    if not todo:
        return []
    models, info = train(records, asof)
    alpha, fwd = alpha_from(forward_pairs(records, lrecs, asof))
    n_res = sum(r["type"] == "RESOLUTION" and (r.get("resolved_at") or "9") < asof for r in records)
    out = []
    for s in todo:
        x = features(s)
        fc = {}
        for stmt, prior in _sealed_priors(s).items():
            raw = raw_forecast(models.get(stmt), x, prior)
            fc[stmt] = {
                "prior": round(_clip(prior, *CLIP), 6),
                "raw": round(raw, 6),
                "published": round(published(prior, raw, alpha), 6),
            }
        out.append(
            {
                "type": "LEARNER_FORECAST",
                "learner": VERSION,
                "protocol": {"id": proto["protocol_id"], "sha256": sha},
                "set_id": s["set_id"],
                "set_record_hash": s["record_hash"],
                "family": s["family"],
                "signal_session": s["signal_session"],
                "entry_cutoff": s["entry_cutoff"],
                "made_at": asof,
                "trained": {"resolutions_before": int(n_res), **info},
                "alpha": round(alpha, 6),
                "forward": fwd,
                "forecasts": fc,
            }
        )
    return out


def append(recs: list[dict], timestamper=None) -> tuple[list[Path], list[dict]]:
    stored = paper.append(recs, path=LEDGER, timestamper=timestamper)
    tokens = [
        paper.TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")
    ]
    return [LEDGER, *[t for t in tokens if t.exists()]], stored


# ------------------------------------------------------------------------------- scoring and report
def statistics(
    records: list[dict] | None = None, lrecs: list[dict] | None = None, asof: str | None = None
) -> dict:
    proto, _ = protocol()
    records = cr.cat_lines() if records is None else records
    lrecs = lines() if lrecs is None else lrecs
    asof = asof or utc_stamp()
    pairs = forward_pairs(records, lrecs, asof)
    alpha, fwd = alpha_from(pairs)
    per = {}
    for stmt in sorted({p["statement"] for p in pairs}):
        ps = [p for p in pairs if p["statement"] == stmt]
        per[stmt] = {
            "n": len(ps),
            **{
                f"brier_{k}": float(np.mean([(p[k] - p["y"]) ** 2 for p in ps]))
                for k in ("prior", "raw", "published")
            },
            "rate": float(np.mean([p["y"] for p in ps])),
        }
    bins = []
    for lo in np.arange(0, 1, 0.1):
        b = [
            p
            for p in pairs
            if lo <= p["published"] < lo + 0.1 or (lo >= 0.9 and p["published"] == 1.0)
        ]
        if b:
            bins.append(
                {
                    "from": round(float(lo), 1),
                    "n": len(b),
                    "mean_forecast": float(np.mean([p["published"] for p in b])),
                    "realised": float(np.mean([p["y"] for p in b])),
                }
            )
    # the claim: per-session mean Brier improvement of the published forecast over the sealed prior
    by_session: dict[str, list[float]] = {}
    for p in pairs:
        by_session.setdefault(p["session"] or "?", []).append(
            (p["prior"] - p["y"]) ** 2 - (p["published"] - p["y"]) ** 2
        )
    sm = np.array([np.mean(v) for _, v in sorted(by_session.items())])
    claim = {
        "n_paired": len(pairs),
        "n_sessions": len(sm),
        "mean_diff": float(sm.mean()) if len(sm) else None,
        "t": None,
        "p_one_sided": None,
    }
    if len(sm) >= 2 and float(np.std(sm, ddof=1)) > 0:
        t = float(sm.mean() / (np.std(sm, ddof=1) / math.sqrt(len(sm))))
        claim["t"], claim["p_one_sided"] = t, float(spec.t_sf(t, len(sm) - 1))
    design = {
        "looks": {
            "n": proto["claim"]["looks"],
            "t_min": proto["claim"]["t_min"],
            "min_sessions": proto["claim"]["min_sessions"],
        }
    }
    claim["look"] = cr.prereg_verdict(claim, claim["mean_diff"], 1.0, design=design)
    return {
        "alpha": alpha,
        "forward": fwd,
        "per_statement": per,
        "reliability": bins,
        "claim": claim,
        "earned_vs_lucky": earned_vs_lucky(records, asof),
        "forecasts": sum(f.get("type") == "LEARNER_FORECAST" for f in lrecs),
    }


def earned_vs_lucky(records: list[dict], asof: str) -> dict:
    """A gain (GAIN0_k true) is EARNED when the set also beat its twins over k sessions and, for a family with a
    mechanism statement, the mechanism happened; otherwise LUCKY."""
    outc = _outcomes(records, asof)
    fam = {r["set_id"]: r.get("family") for r in records if r["type"] == "CATALYST_SET"}
    earned, lucky, why = 0, 0, {"market_or_sector_carried_it": 0, "stated_catalyst_never_came": 0}
    for (sid, stmt), (y, _) in outc.items():
        if not stmt.startswith("GAIN0_") or not y:
            continue
        k = stmt.split("_")[-1]
        beat = outc.get((sid, f"BEATS_TWINS_{k}"))
        mech = TRIANGLES.get(fam.get(sid))
        mech_ok = True if not mech else (outc.get((sid, mech[0])) or (None,))[0]
        if beat is None or (mech and mech_ok is None):
            continue
        if beat[0] and mech_ok:
            earned += 1
        else:
            lucky += 1
            why["market_or_sector_carried_it" if not beat[0] else "stated_catalyst_never_came"] += 1
    return {"earned": earned, "lucky": lucky, "lucky_reasons": why}


def render(st: dict) -> str:
    c = st["claim"]
    out = [
        "# Learner (LEARNER-v1)",
        "",
        "Self-learning beside the frozen families: it learns from resolved outcomes only, speaks with the confidence it has "
        "earned, and is credited for a catalyst call only when the stock beat its twins and the stated catalyst happened.",
        "",
        f"- Forecasts sealed: {st['forecasts']}; forward-scored pairs: {st['forward']['n']}",
        f"- Earned confidence (alpha): {st['alpha']:.2f} (0 = still publishing the sealed priors; 1 = proven)",
        f"- Claim (published beats the sealed priors, per-session Brier): {c['n_paired']} pairs, "
        f"t {c['t'] if c['t'] is None else round(c['t'], 2)}: **{c['look']['verdict']}**",
        f"- Gains earned vs lucky: {st['earned_vs_lucky']['earned']} earned, {st['earned_vs_lucky']['lucky']} lucky "
        f"({st['earned_vs_lucky']['lucky_reasons']})",
        "",
        "| Statement | n | Brier prior | Brier raw | Brier published | Rate |",
        "|---|---|---|---|---|---|",
    ]
    for k, v in st["per_statement"].items():
        out.append(
            f"| {k} | {v['n']} | {v['brier_prior']:.4f} | {v['brier_raw']:.4f} | {v['brier_published']:.4f} | {v['rate']:.2f} |"
        )
    out += [
        "",
        "Reliability (published): "
        + (
            "; ".join(
                f"{b['from']:.1f}+ n {b['n']}: said {b['mean_forecast']:.2f}, "
                f"happened {b['realised']:.2f}"
                for b in st["reliability"]
            )
            or "none yet"
        ),
    ]
    return "\n".join(out) + "\n"


def write_report() -> Path:
    REPORT.write_text(render(statistics()), encoding="utf-8")
    return REPORT


# ------------------------------------------------------------------------------- verify
def verify(lrecs_path: Path | None = None, records: list[dict] | None = None) -> list[str]:
    path = LEDGER if lrecs_path is None else lrecs_path
    if not path.exists():
        return []
    problems = [f"learner.jsonl: {p}" for p in paper.verify_chain(path)]
    _, sha = protocol()
    records = cr.cat_lines() if records is None else records
    sets = {r["set_id"]: r for r in records if r["type"] == "CATALYST_SET"}
    seen = set()
    for f in paper.ledger_lines(path):
        if f.get("type") != "LEARNER_FORECAST":
            problems.append(f"learner.jsonl: unknown record type {f.get('type')!r}")
            continue
        sid = f["set_id"]
        if sid in seen:
            problems.append(f"{sid}: forecast twice")
        seen.add(sid)
        if f["protocol"]["sha256"] != sha:
            problems.append(
                f"{sid}: learner protocol sha256 differs from research/LEARNER_v1/protocol.json"
            )
        s = sets.get(sid)
        if s is None or s.get("record_hash") != f["set_record_hash"]:
            problems.append(f"{sid}: forecast binds no sealed set with that hash")
            continue
        if f["made_at"] >= s["entry_cutoff"]:
            problems.append(
                f"{sid}: forecast made at {f['made_at']}, after the set's cutoff {s['entry_cutoff']}"
            )
        _, info = train(records, f["made_at"])
        if info["weights_sha256"] != f["trained"]["weights_sha256"]:
            problems.append(
                f"{sid}: weights do not reproduce from the resolutions before {f['made_at']} (possible peeking)"
            )
    return problems

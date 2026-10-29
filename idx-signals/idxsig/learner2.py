"""LEARNER_v2 (research/LEARNER_v2/protocol.json): the self-learning layer, rebuilt so that it can only earn credit for
telling sets apart, never for base rates, the market or luck.

- Anchor. Every statement is judged against a climatology twin of the learner: the same Bayesian fit with an intercept
  only, so the anchor learns how often each statement comes true for each family. The learner's forecast is the
  anchor moved by the set's own features (centred slopes): its average equals the anchor, so its only possible edge
  is discrimination.
- Skill statements only. RELATIVE (graded against the twins), MECHANISM (the stated catalyst happens) and
  TRIANGULATED (both). Absolute statements (GAIN0, FADE10, RUN30), which a rising market makes true, are forecast with
  the anchor alone and never scored as skill.
- One model per kind, hierarchical: RELATIVE statements share one slope vector plus a deviation per statement; the
  mechanism and triangulated statements have their own slopes. Laplace posterior, so every forecast carries an
  uncertainty and a call needs the learner to be sure, not just to lean.
- Warm start. research/LEARNER_v2/warmstart/events.csv.gz (5,587 events with signal dates before 2024, pinned by
  sha256) enters the fit with its own intercepts (history's base rates never reach the live anchor) and a total weight
  of at most 300 live outcomes per kind.
- Earned confidence. The published forecast moves from the anchor by alpha per kind; alpha is the lower edge of a
  time-uniform confidence sequence on the learner's forward Brier gain over the anchor, so checking it every day does
  not let luck open it; it also closes when the recent record turns non-positive.
- No peeking, provably. Every forecast is sealed before the set's entry cutoff with its features, anchors, raw and
  published values; paper-verify retrains from the resolutions dated before the forecast and must reproduce them.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import numpy as np

from . import catalysts as cr
from . import paper
from . import speculation as spec
from .provenance import PKG_ROOT, sha256_file, utc_stamp

PROTOCOL_JSON = PKG_ROOT / "research" / "LEARNER_v2" / "protocol.json"
HISTORY = PKG_ROOT / "research" / "LEARNER_v2" / "warmstart" / "events.csv.gz"
HISTORY_SHA256 = "1eff13dabff91e2a41ae654ba9da645d87c6cf94a7efd67cbbf808d338fc9a13"
LEDGER = paper.PAPER / "learner_v2.jsonl"
REPORT = paper.PAPER / "LEARNER_V2.md"
VERSION = "LEARNER-v2"
RECORD = "LEARNER2_FORECAST"
FAMILIES = ("SEC13D", "SEC13D_V2", "DILUTION_8K", "FORM4", "FORM4_SHARP", "IDX_INDEX")
GROUP = {"SEC13D": "13D", "SEC13D_V2": "13D", "FORM4": "F4", "FORM4_SHARP": "F4", "DILUTION_8K": "DIL",
         "IDX_INDEX": "IDX"}
TRI = "TRIANGULATED"
TRIANGLES = {"SEC13D_V2": ("MECH_13DA_UP_60", "BEATS_TWINS_60"), "FORM4_SHARP": ("MECH_SECOND_BUY_20", "BEATS_TWINS_60")}
SKILL_KINDS = ("RELATIVE", "MECHANISM", "TRIANGULATED")
NOT_SHARED = frozenset({"REVERSAL_POST20"})  # relative, but true when the stock goes against the call's direction
FX = {"US": 1.0, "IDX": 1 / 16000.0, "CRYPTO": 1.0}  # to US dollars, for the liquidity and size features
CLIP = (0.01, 0.99)
LAMBDA_SHARED, LAMBDA_TASK, LAMBDA_OWN, LAMBDA_ICPT = 16.0, 25.0, 16.0, 1 / 1.5 ** 2
MAX_IT, TOL = 50, 1e-10
N_CAP = 300  # history's total weight per kind, in live outcomes
WINDOW_DAYS = 90  # the triangulation counts
GATE = {"delta": 0.05, "t_star": 250, "t_min": 30, "recent": 120, "skill_full": 0.02}
CALL = {"margin": 0.4, "z": 1.645}
HIST_TASKS = {  # (source, outcome column) -> (kind, the live statement whose slopes it informs)
    ("kill13d", "bt20"): ("RELATIVE", "SEC13D:BEATS_TWINS_20"),
    ("form4", "bt20"): ("RELATIVE", "FORM4:BEATS_TWINS_20"),
    ("form4", "bt60"): ("RELATIVE", "FORM4_SHARP:BEATS_TWINS_60"),
    ("dil302", "ltt20"): ("RELATIVE", "DILUTION_8K:LOSES_TO_TWINS_20"),
    ("form4", "second_buy_20"): ("MECHANISM", "FORM4_SHARP:MECH_SECOND_BUY_20"),
    ("form4", "tri60"): ("TRIANGULATED", "FORM4_SHARP:TRIANGULATED"),
}
FEATURES = ("s_ret1", "s_ret5", "s_ret20", "s_dd60", "log_volr", "s_cpos", "log_adv", "fire", "dilution_recent",
            "moved_already", "microcap", "has_mv", "log_mv", "during", "top_exec", "log_value", "owners", "lag",
            "has_pct", "pct_inc", "strong_intent", "intent_words", "has_stake", "stake", "repeat", "corroborate",
            "conflict")
LABELS = {
    "s_ret1": "signal-day move in the call's direction", "s_ret5": "5-session move in the call's direction",
    "s_ret20": "20-session move in the call's direction", "s_dd60": "distance from the 60-session high, in the call's direction",
    "log_volr": "volume against its 20-session median", "s_cpos": "close near the day's high, in the call's direction",
    "log_adv": "traded value (liquidity)", "fire": "the family fired (no abstention rule)",
    "dilution_recent": "a recent dilution filing", "moved_already": "already moved 15% before entry",
    "microcap": "microcap or size unknown", "has_mv": "market value known", "log_mv": "market value",
    "during": "filed during the signal session", "top_exec": "a top executive bought", "log_value": "purchase size",
    "owners": "several insiders on one filing", "lag": "days from trade to filing", "has_pct": "holdings increase known",
    "pct_inc": "holdings increase", "strong_intent": "the activist states strong intent",
    "intent_words": "intent words in Item 4", "has_stake": "stake size known", "stake": "stake size (% of class)",
    "repeat": "same-source events on the issuer in 90 days", "corroborate": "other sources agreeing in 90 days",
    "conflict": "other sources disagreeing in 90 days"}


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8")), sha256_file(PROTOCOL_JSON)


def lines(path: Path | None = None) -> list[dict]:
    p = LEDGER if path is None else path
    return paper.ledger_lines(p) if p.exists() else []


def _logit(p: float) -> float:
    p = min(max(p, CLIP[0]), CLIP[1])
    return math.log(p / (1 - p))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def _prob(z: float) -> float:
    return float(min(max(_sigmoid(z), CLIP[0]), CLIP[1]))


def _num(v, default: float | None = 0.0) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ------------------------------------------------------------------------------- statements
def kind_of(stmt: str) -> str | None:
    if stmt == TRI:
        return "TRIANGULATED"
    if stmt.startswith("MECH_"):
        return "MECHANISM"
    if cr.is_relative(stmt):
        return "RELATIVE"
    return None  # absolute: a rising market makes it true; anchor only


@lru_cache(maxsize=1)
def _frozen_priors() -> dict[str, dict]:
    reg, _ = cr.protocol()
    out = {f: {c["id"]: c["prior"] for c in spec_["cone"]} for f, spec_ in reg["families"].items()}
    out.update({f: {c["id"]: c["prior"] for c in p["cone"]} for f, (p, _) in cr.extra_families().items()})
    return out


def base_prior(family: str, stmt: str) -> float:
    """The family's frozen prior for a statement (0.5 where the protocol says "running"); TRIANGULATED: the product."""
    if stmt == TRI:
        a, b = TRIANGLES[family]
        return base_prior(family, a) * base_prior(family, b)
    v = _frozen_priors().get(family, {}).get(stmt)
    return float(v) if isinstance(v, (int, float)) else 0.5


def statements(s: dict) -> list[tuple[str, str]]:
    """(statement, the window that resolves it) for a set, TRIANGULATED last where the family has one."""
    out = [(c["id"], c["resolves_with"]) for c in s.get("cone", [])]
    tri = TRIANGLES.get(s.get("family"))
    if tri and all(t in {c for c, _ in out} for t in tri):
        out.append((TRI, "TRI"))
    return out


def event_key(s: dict) -> str:
    """The underlying event: a child family's set and its parent's set describe one filing."""
    return (s.get("parent") or {}).get("set_id") or s["set_id"]


# ------------------------------------------------------------------------------- features (sealed fields only)
def features(s: dict, tri: tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    """The set's own sealed fields, scaled to about unit size. Price features are signed by the call's direction
    (positive = the stock already moved the way the call says); a field a family does not record is 0."""
    sig, cov, ev = s.get("signal") or {}, s.get("coverage") or {}, s.get("event") or {}
    inp, rules = cov.get("inputs") or {}, cov.get("rules") or {}
    d = -1.0 if int(s.get("direction", 1) or 1) < 0 else 1.0
    fx = FX.get(s.get("market", "US"), 1.0)
    mv, value = _num(inp.get("market_value_usd"), None), _num(inp.get("total_value"), None)
    lag, owners = _num(inp.get("lag_days"), None), _num(inp.get("n_owners"), None)
    pct = (inp.get("pct_increase") or {}).get("max") if isinstance(inp.get("pct_increase"), dict) else None
    pct = _num(pct, None)
    stake = _num((ev.get("cover_page") or {}).get("max_percent"), None)
    words = (ev.get("item4") or {}).get("intent_words") or []
    x = {
        "s_ret1": _clip(d * _num(sig.get("ret1")) / 0.10, -3, 3),
        "s_ret5": _clip(d * _num(sig.get("ret5")) / 0.20, -3, 3),
        "s_ret20": _clip(d * _num(sig.get("ret20")) / 0.30, -3, 3),
        "s_dd60": _clip(d * _num(sig.get("dd60")) / 0.30, -3, 3),
        "log_volr": _clip(math.log(max(_num(sig.get("volr"), 1.0), 1e-3)), -3, 3),
        "s_cpos": _clip(d * (_num(sig.get("cpos"), 0.5) - 0.5) * 2, -1, 1),
        "log_adv": _clip(math.log10(max(_num(sig.get("adv20_value")) * fx, 1.0)) - 6.5, -3, 3),
        "fire": float(cov.get("class") == "FIRE"),
        "dilution_recent": float(bool(rules.get("DILUTION_RECENT"))),
        "moved_already": float(bool(rules.get("MOVED_ALREADY"))),
        "microcap": float(bool(rules.get("MICROCAP"))),
        "has_mv": float(mv is not None and mv > 0),
        "log_mv": _clip(math.log10(mv * fx) - 9, -3, 3) if mv else 0.0,
        "during": float(ev.get("position") == "DURING"),
        "top_exec": float(bool(inp.get("top_exec"))),
        "log_value": _clip(math.log10(value) - 5, -2, 3) if value and value > 0 else 0.0,
        "owners": _clip((owners or 1) - 1, 0, 4) / 4 if owners is not None else 0.0,
        "lag": _clip(lag, 0, 30) / 30 if lag is not None else 0.0,
        "has_pct": float(pct is not None),
        "pct_inc": _clip(pct, 0, 5) / 5 if pct is not None else 0.0,
        "strong_intent": float(bool((ev.get("strong_intent") or {}).get("strong"))),
        "intent_words": min(len(words), 5) / 5,
        "has_stake": float(stake is not None),
        "stake": _clip(stake / 20, 0, 2) if stake is not None else 0.0,
        "repeat": min(tri[0], 3) / 3, "corroborate": min(tri[1], 3) / 3, "conflict": min(tri[2], 3) / 3,
    }
    return np.array([x[k] for k in FEATURES], dtype=float)


def tri_counts(records: list[dict]) -> dict[str, tuple[int, int, int]]:
    """Per set: distinct earlier events (ledger order) on the same market and ticker with a signal session in the 90
    calendar days up to its own: from its own source (repeat), from another source with the same direction
    (corroborate) or the opposite (conflict). Only what was sealed before the set, so the value never changes."""
    seen: dict[tuple[str, str], list[tuple[str, str, int, str]]] = {}
    out = {}
    for r in records:
        if r.get("type") != "CATALYST_SET" or r.get("family") not in FAMILIES:
            continue
        key, g, d = event_key(r), GROUP[r["family"]], -1 if int(r.get("direction", 1) or 1) < 0 else 1
        k = (r.get("market", "US"), str(r.get("ticker")))
        lo = (date.fromisoformat(r["signal_session"]) - timedelta(days=WINDOW_DAYS)).isoformat()
        rep, cor, con = set(), set(), set()
        for ek, eg, ed, sess in seen.get(k, []):
            if ek == key or not (lo <= sess <= r["signal_session"]):
                continue
            (rep if eg == g else cor if ed == d else con).add(ek)
        out[r["set_id"]] = (len(rep), len(cor), len(con))
        seen.setdefault(k, []).append((key, g, d, r["signal_session"]))
    return out


# ------------------------------------------------------------------------------- rows
class Row(NamedTuple):
    kind: str
    task: str  # the live statement whose slopes the row informs, "FAMILY:STATEMENT"
    icpt: str  # its intercept: the live statement, or the history source
    x: np.ndarray
    p0: float
    y: float
    w: float


def outcomes(records: list[dict], asof: str) -> dict[tuple[str, str], tuple[bool, str]]:
    """(set, statement) -> (outcome, resolved_at) for every graded statement resolved before asof; a later revision
    of the same (set, window) replaces an earlier one."""
    out: dict[tuple[str, str], tuple[bool, str]] = {}
    for r in records:
        if r.get("type") != "RESOLUTION" or not r.get("cone") or (r.get("resolved_at") or "9") >= asof:
            continue
        for c in r["cone"]:
            if c.get("outcome") is not None:
                out[(r["set_id"], c["id"])] = (bool(c["outcome"]), r["resolved_at"])
    return out


def outcome_of(outc: dict, set_id: str, family: str, stmt: str) -> tuple[bool, str] | None:
    if stmt != TRI:
        return outc.get((set_id, stmt))
    a, b = TRIANGLES[family]
    oa, ob = outc.get((set_id, a)), outc.get((set_id, b))
    if oa is None or ob is None:
        return None
    return oa[0] and ob[0], max(oa[1], ob[1])


def live_rows(records: list[dict], asof: str) -> list[Row]:
    """Every graded statement of every sealed set, resolved before asof, each underlying event weighted once per
    statement (a parent set and its child of the same filing share the weight)."""
    sets = [r for r in records if r.get("type") == "CATALYST_SET" and r.get("family") in FAMILIES]
    outc, tri = outcomes(records, asof), tri_counts(records)
    raw = []
    for s in sets:
        x = None
        for stmt, _ in statements(s):
            o = outcome_of(outc, s["set_id"], s["family"], stmt)
            if o is None:
                continue
            x = features(s, tri.get(s["set_id"], (0, 0, 0))) if x is None else x
            raw.append((event_key(s), stmt, Row(kind_of(stmt) or "ABSOLUTE", f"{s['family']}:{stmt}",
                                                 f"{s['family']}:{stmt}", x, base_prior(s["family"], stmt),
                                                 float(o[0]), 1.0)))
    n = Counter((k, st) for k, st, _ in raw)
    return [r._replace(w=1.0 / n[(k, st)]) for k, st, r in raw]


@lru_cache(maxsize=1)
def history_rows() -> tuple[Row, ...]:
    """The pinned warm start, through the same features() as a live set; each kind's rows share a total weight of at
    most N_CAP. Refuses a file that differs from the pinned hash."""
    if sha256_file(HISTORY) != HISTORY_SHA256:
        raise RuntimeError(f"{HISTORY.name} does not match the pinned sha256: the warm start is not the frozen one")
    with gzip.open(HISTORY, "rt", encoding="utf-8", newline="") as fh:  # the stdlib reader: every value a string, so
        records = list(csv.DictReader(fh))  # no pandas version can parse a flag or a number differently
    rows = []
    for r in records:
        ps = {"family": r["family"], "direction": int(r["direction"]), "market": "US",
              "signal": {k: r[k] for k in ("ret1", "ret5", "ret20", "dd60", "volr", "cpos", "close", "adv20_value")},
              "coverage": {"class": r["cls"],
                           "rules": {k: r[k] == "True" for k in ("DILUTION_RECENT", "MOVED_ALREADY", "MICROCAP")
                                     if r["source"] == "kill13d"},
                           "inputs": ({"top_exec": r["top_exec"] == "True", "total_value": r["total_value"],
                                       "n_owners": r["n_owners"], "lag_days": r["lag_days"]} if r["source"] == "form4" else {})},
              "event": {"position": r["position"]}}
        x = features(ps, tuple(int(float(r[k])) for k in ("repeat_90d", "corroborate_90d", "conflict_90d")))
        for (src, col), (kind, task) in HIST_TASKS.items():
            if r["source"] == src and _num(r.get(col), None) is not None:
                rows.append(Row(kind, task, f"hist:{src}:{col}", x, 0.5, float(r[col]), 1.0))
    n = Counter(r.kind for r in rows)
    return tuple(r._replace(w=min(1.0, N_CAP / n[r.kind])) for r in rows)


# ------------------------------------------------------------------------------- the model
class Model:
    """One kind's penalised logistic model: logit p = logit(p0) + intercept[icpt] + (x - centre[task]) . slope[task],
    slope[task] = shared + own[task] (RELATIVE statements other than REVERSAL_POST20 share), with the Laplace
    covariance at the maximum a posteriori."""

    def __init__(self, kind: str, rows: list[Row]):
        self.kind = kind
        D = len(FEATURES)
        self.tasks = sorted({r.task for r in rows})
        self.icpts = sorted({r.icpt for r in rows})
        self.shared = {t: kind == "RELATIVE" and t.split(":", 1)[1] not in NOT_SHARED for t in self.tasks}
        self.nb = D if any(self.shared.values()) else 0
        T, I = len(self.tasks), len(self.icpts)
        X = np.array([r.x for r in rows])
        w0 = np.array([r.w for r in rows])
        y = np.array([r.y for r in rows])
        off = np.array([_logit(r.p0) for r in rows])
        ti = np.array([self.tasks.index(r.task) for r in rows])
        ii = np.array([self.icpts.index(r.icpt) for r in rows])
        self.kind_centre = (w0[:, None] * X).sum(0) / w0.sum()
        self.centre = {t: (w0[ti == k, None] * X[ti == k]).sum(0) / w0[ti == k].sum() for k, t in enumerate(self.tasks)}
        Z = X - np.array([self.centre[self.tasks[k]] for k in ti])
        lam = np.concatenate([np.full(self.nb, LAMBDA_SHARED),
                              *[np.full(D, LAMBDA_TASK if self.shared[t] else LAMBDA_OWN) for t in self.tasks],
                              np.full(I, LAMBDA_ICPT)])
        P = len(lam)
        groups = {}
        for j, key in enumerate(zip(ti, ii)):
            groups.setdefault(key, []).append(j)
        groups = {k: np.array(v) for k, v in sorted(groups.items())}
        theta = np.zeros(P)
        for _ in range(MAX_IT):
            eta = off + self._linear(theta, Z, ti, ii)
            p = _sigmoid(eta)
            r, h = w0 * (y - p), w0 * p * (1 - p)
            g, H = -lam * theta, np.diag(lam)
            for (tk, ik), idx in groups.items():
                Zg, rg, hg = Z[idx], r[idx], h[idx]
                gz, Szz, Sz = Zg.T @ rg, (Zg * hg[:, None]).T @ Zg, Zg.T @ hg
                own, a = slice(self.nb + tk * D, self.nb + (tk + 1) * D), self.nb + T * D + ik
                blocks = [own] + ([slice(0, self.nb)] if self.shared[self.tasks[tk]] and self.nb else [])
                for b1 in blocks:
                    g[b1] += gz
                    H[b1, a] += Sz
                    H[a, b1] += Sz
                    for b2 in blocks:
                        H[b1, b2] += Szz
                g[a] += rg.sum()
                H[a, a] += hg.sum()
            step = np.linalg.solve(H, g)
            theta = theta + step
            if float(np.max(np.abs(step))) < TOL:
                break
        self.theta, self.cov = theta, np.linalg.inv(H)
        self.n_rows = {t: float(w0[ti == k].sum()) for k, t in enumerate(self.tasks)}

    def _linear(self, theta, Z, ti, ii):
        D, T = len(FEATURES), len(self.tasks)
        own = theta[self.nb:self.nb + T * D].reshape(T, D)
        slope = own[ti]
        if self.nb:
            share = np.array([self.shared[t] for t in self.tasks])[ti]
            slope = slope + share[:, None] * theta[:self.nb][None, :]
        return theta[self.nb + T * D:][ii] + np.einsum("ij,ij->i", Z, slope)

    def slope(self, task: str) -> tuple[np.ndarray, np.ndarray]:
        """The task's slope vector and its covariance (a task the fit has not seen: the shared part, or zero)."""
        D = len(FEATURES)
        sel = []
        if task in self.tasks:
            k = self.tasks.index(task)
            sel.append(np.arange(self.nb + k * D, self.nb + (k + 1) * D))
        shared = self.shared.get(task, self.kind == "RELATIVE" and task.split(":", 1)[1] not in NOT_SHARED)
        if self.nb and shared:
            sel.append(np.arange(0, self.nb))
        if not sel:
            return np.zeros(D), np.zeros((D, D))
        w = sum(self.theta[s] for s in sel)
        c = sum(self.cov[np.ix_(a, b)] for a in sel for b in sel)
        return w, c

    def deviation(self, task: str, x: np.ndarray, centre: np.ndarray | None = None) -> tuple[float, float, np.ndarray]:
        """The logit move from the anchor for a set with features x, measured from `centre` (the live population's
        mean; else the training rows'), its posterior sd, and each feature's part."""
        w, c = self.slope(task)
        z = x - (self.centre.get(task, self.kind_centre) if centre is None else centre)
        parts = z * w
        return float(parts.sum()), float(math.sqrt(max(float(z @ c @ z), 0.0))), parts


def anchor_fit(rows: list[Row]) -> float:
    """The climatology twin: the same prior and weights, an intercept only. Returns the intercept."""
    if not rows:
        return 0.0
    o = np.array([_logit(r.p0) for r in rows])
    w, y = np.array([r.w for r in rows]), np.array([r.y for r in rows])
    a = 0.0
    for _ in range(MAX_IT):
        p = _sigmoid(o + a)
        step = float((w * (y - p)).sum() - LAMBDA_ICPT * a) / float((w * p * (1 - p)).sum() + LAMBDA_ICPT)
        a += step
        if abs(step) < TOL:
            break
    return a


class State(NamedTuple):
    models: dict
    anchors: dict  # task -> intercept
    info: dict


def train(records: list[dict], asof: str) -> State:
    live = live_rows(records, asof)
    rows = list(history_rows()) + [r for r in live if r.kind in SKILL_KINDS]
    models = {}
    for k in SKILL_KINDS:
        kr = [r for r in rows if r.kind == k]
        models[k] = Model(k, kr) if kr else None
    by_task: dict[str, list[Row]] = {}
    for r in live:
        by_task.setdefault(r.task, []).append(r)
    anchors = {t: anchor_fit(rs) for t, rs in sorted(by_task.items())}
    fp = hashlib.sha256(json.dumps({k: None if m is None else [float(f"{v:.6g}") for v in m.theta]
                                    for k, m in models.items()}, sort_keys=True).encode()).hexdigest()
    info = {"live_rows": {t: round(sum(r.w for r in rs), 4) for t, rs in sorted(by_task.items())},
            "history_rows": dict(sorted(Counter(r.kind for r in history_rows()).items())),
            "fingerprint": fp}
    return State(models, anchors, info)


def live_centres(records: list[dict], asof: str) -> dict[str, np.ndarray]:
    """Per statement, the mean features of every live set sealed by asof, resolved or not: the reference a forecast is
    measured from. Features only, no outcome, so the learner's average move over the live population is zero by
    construction and a shift between history and the live sets cannot move every forecast the same way."""
    tri = tri_counts(records)
    acc: dict[str, list[np.ndarray]] = {}
    for s in records:
        if (s.get("type") != "CATALYST_SET" or s.get("family") not in FAMILIES
                or (s.get("sealed_at") or "") > asof):
            continue
        x = features(s, tri.get(s["set_id"], (0, 0, 0)))
        for stmt, _ in statements(s):
            if kind_of(stmt):
                acc.setdefault(f"{s['family']}:{stmt}", []).append(x)
    return {t: np.mean(v, axis=0) for t, v in sorted(acc.items())}


def anchor_prob(state: State, task: str, p0: float) -> float:
    return _prob(_logit(p0) + state.anchors.get(task, 0.0))


# ------------------------------------------------------------------------------- earned confidence
def forward_pairs(records: list[dict], lrecs: list[dict], asof: str) -> list[dict]:
    """Every (earlier forecast, skill statement) whose outcome resolved after the forecast and before asof, each
    underlying event weighted once per statement."""
    outc = outcomes(records, asof)
    out = []
    for f in lrecs:
        if f.get("type") != RECORD or f["made_at"] >= asof:
            continue
        for stmt, fc in f["forecasts"].items():
            if fc["kind"] not in SKILL_KINDS:
                continue
            o = outcome_of(outc, f["set_id"], f["family"], stmt)
            if o is None or o[1] <= f["made_at"]:
                continue
            out.append({"set_id": f["set_id"], "event_key": f["event_key"], "statement": stmt, "kind": fc["kind"],
                        "family": f["family"], "session": f["signal_session"], "window": fc["window"],
                        "resolved_at": o[1], "y": float(o[0]), "anchor": fc["anchor"], "raw": fc["raw"],
                        "published": fc["published"], "call": fc.get("call") or {}})
    n = Counter((p["event_key"], p["statement"]) for p in out)
    for p in out:
        p["w"] = 1.0 / n[(p["event_key"], p["statement"])]
    return out


def observations(pairs: list[dict], key: str = "raw") -> list[tuple[float, float]]:
    """(weighted mean Brier gain of `key` over the anchor, weighted mean anchor Brier) per (signal session, window,
    resolution time), in the order they resolved. The weights are counted inside the observation (one underlying event
    once per statement), so an observation never changes once it exists: a pair resolved later forms a new one."""
    groups: dict[tuple, list[dict]] = {}
    for p in pairs:
        groups.setdefault((p["resolved_at"], p["session"], p["window"]), []).append(p)
    out = []
    for k in sorted(groups):
        ps = groups[k]
        n = Counter((p["event_key"], p["statement"]) for p in ps)
        w = [1.0 / n[(p["event_key"], p["statement"])] for p in ps]
        out.append((sum(wi * ((p["anchor"] - p["y"]) ** 2 - (p[key] - p["y"]) ** 2) for wi, p in zip(w, ps)) / sum(w),
                    sum(wi * (p["anchor"] - p["y"]) ** 2 for wi, p in zip(w, ps)) / sum(w)))
    return out


def confidence_lowers(d: list[float], delta: float = GATE["delta"], t_star: int = GATE["t_star"]) -> np.ndarray:
    """The lower edge of the asymptotic confidence sequence for the mean after each observation (Waudby-Smith et al.,
    time-uniform central limit theory): valid at every t at once, so a daily look does not inflate the chance that
    luck clears zero. NaN before two observations."""
    a = np.asarray(d, dtype=float)
    t = np.arange(1, len(a) + 1, dtype=float)
    s1, s2 = np.cumsum(a), np.cumsum(a * a)
    mean = s1 / t
    sd = np.sqrt(np.clip((s2 - t * mean ** 2) / np.maximum(t - 1, 1), 0, None))
    rho2 = (-2 * math.log(delta) + math.log(-2 * math.log(delta) + 1)) / t_star
    radius = sd * np.sqrt(2 * (t * rho2 + 1) / (t * t * rho2) * np.log(np.sqrt(t * rho2 + 1) / delta))
    return np.where(t >= 2, mean - radius, np.nan)


def gate(pairs: list[dict], kind: str) -> tuple[float, dict]:
    """alpha for one kind. Proof: the running maximum, from t_min observations on, of the confidence sequence's lower
    edge (the running intersection of a confidence sequence is one too, so the 5% guarantee holds and proven skill
    stays proven while the bound's own noise wanders). Loss: the recent record, which follows the edge as it decays."""
    obs = observations([p for p in pairs if p["kind"] == kind])
    d = [o[0] for o in obs]
    info = {"observations": len(obs), "mean_gain": float(np.mean(d)) if d else None, "lower": None,
            "skill_lower": None, "recent_skill": None}
    if len(obs) < GATE["t_min"]:
        return 0.0, info
    b = float(np.mean([o[1] for o in obs]))
    lower = float(np.max(confidence_lowers(d)[GATE["t_min"] - 1:]))
    recent = float(np.mean(d[-GATE["recent"]:])) / b if b > 0 else 0.0
    skill_lower = lower / b if b > 0 else 0.0
    info.update({"lower": lower, "skill_lower": skill_lower, "recent_skill": recent})
    if skill_lower <= 0 or recent <= 0:
        return 0.0, info
    return float(_clip(min(skill_lower, recent) / GATE["skill_full"], 0.0, 1.0)), info


def gates(records: list[dict], lrecs: list[dict], asof: str) -> dict[str, tuple[float, dict]]:
    pairs = forward_pairs(records, lrecs, asof)
    return {k: gate(pairs, k) for k in SKILL_KINDS}


# ------------------------------------------------------------------------------- forecasting
def call_of(dev: float, sd: float, alpha: float) -> dict:
    """BACK when the learner puts the set clearly above its anchor and is 95% sure it is above; AVOID the mirror.
    Live only when the published forecast (alpha x the move) also clears the margin; otherwise a shadow call."""
    m, z = CALL["margin"], CALL["z"]
    side = "BACK" if dev >= m and dev - z * sd > 0 else "AVOID" if dev <= -m and dev + z * sd < 0 else None
    return {"side": side, "live": bool(side and abs(alpha * dev) >= m)}


def forecast_set(s: dict, tri: tuple[int, int, int], state: State, gate_alpha: dict[str, float],
                 centres: dict[str, np.ndarray] | None = None) -> tuple[dict, list]:
    x = features(s, tri)
    centres = centres or {}
    out = {}
    for stmt, window in statements(s):
        task, kind, p0 = f"{s['family']}:{stmt}", kind_of(stmt), base_prior(s["family"], stmt)
        anchor = anchor_prob(state, task, p0)
        fc = {"kind": kind or "ABSOLUTE", "window": window, "p0": round(p0, 6), "anchor": round(anchor, 6)}
        if kind is None:
            out[stmt] = {**fc, "raw": round(anchor, 6), "published": round(anchor, 6)}
            continue
        m = state.models.get(kind)
        dev, sd, parts = (0.0, 0.0, np.zeros(len(FEATURES))) if m is None else m.deviation(task, x, centres.get(task))
        raw = _prob(_logit(anchor) + dev)
        dev = _logit(raw) - _logit(anchor)  # after the probability clip
        alpha = gate_alpha.get(kind, 0.0)
        order = np.argsort(-np.abs(parts))[:3]
        why = [{"feature": FEATURES[j], "label": LABELS[FEATURES[j]], "logit": round(float(parts[j]), 4)}
               for j in order if abs(parts[j]) >= 0.01]
        lo, hi = _prob(_logit(anchor) + dev - CALL["z"] * sd), _prob(_logit(anchor) + dev + CALL["z"] * sd)
        out[stmt] = {**fc, "raw": round(raw, 6), "raw_90": [round(lo, 6), round(hi, 6)], "deviation": round(dev, 6),
                     "sd": round(sd, 6), "alpha": round(alpha, 6),
                     "published": round(_prob(_logit(anchor) + alpha * dev), 6), "call": call_of(dev, sd, alpha),
                     "why": why}
    return out, [round(float(v), 6) for v in x]


def forecast_records(now: datetime, records: list[dict] | None = None, lrecs: list[dict] | None = None) -> list[dict]:
    """One LEARNER2_FORECAST for every sealed set still before its entry cutoff that has none yet."""
    proto, sha = protocol()
    records = cr.cat_lines() if records is None else records
    lrecs = lines() if lrecs is None else lrecs
    asof = utc_stamp(now.astimezone(timezone.utc))
    done = {f["set_id"] for f in lrecs if f.get("type") == RECORD}
    todo = [s for s in records if s.get("type") == "CATALYST_SET" and s.get("family") in FAMILIES
            and s["entry_cutoff"] > asof and s["set_id"] not in done]
    if not todo:
        return []
    return [_record(s, asof, records, lrecs, proto, sha) for s in todo]


def _record(s, asof, records, lrecs, proto, sha, state=None, g=None) -> dict:
    state = state or train(records, asof)
    g = g or gates(records, lrecs, asof)
    tri = tri_counts(records).get(s["set_id"], (0, 0, 0))
    fc, x = forecast_set(s, tri, state, {k: v[0] for k, v in g.items()}, live_centres(records, asof))
    n_res = sum(r.get("type") == "RESOLUTION" and (r.get("resolved_at") or "9") < asof for r in records)
    return {"type": RECORD, "learner": VERSION, "protocol": {"id": proto["protocol_id"], "sha256": sha},
            "history": {"file": str(HISTORY.relative_to(PKG_ROOT)), "sha256": HISTORY_SHA256},
            "set_id": s["set_id"], "set_record_hash": s["record_hash"], "event_key": event_key(s), "family": s["family"],
            "market": s.get("market", "US"), "ticker": s.get("ticker"), "signal_session": s["signal_session"],
            "entry_cutoff": s["entry_cutoff"], "made_at": asof,
            "training": {"resolutions_before": int(n_res), **state.info},
            "gate": {k: {"alpha": round(v[0], 6), **{kk: (None if vv is None else round(vv, 6) if isinstance(vv, float) else vv)
                                                       for kk, vv in v[1].items()}} for k, v in g.items()},
            "triangulation": dict(zip(("repeat", "corroborate", "conflict"), tri)),
            "features": dict(zip(FEATURES, x)), "forecasts": fc}


def append(recs: list[dict], timestamper=None) -> tuple[list[Path], list[dict]]:
    stored = paper.append(recs, path=LEDGER, timestamper=timestamper)
    tokens = [paper.TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [LEDGER, *[t for t in tokens if t.exists()]], stored


# ------------------------------------------------------------------------------- scoring and report
def _wilson(k: float, n: float, z: float = 1.96) -> list[float] | None:
    if n <= 0:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 4), round(c + h, 4)]


def call_statistics(pairs: list[dict], records: list[dict]) -> dict:
    """Calls scored forward: hit rate against the anchor's rate on the same pairs, the paired excess return of the
    matching window, and why each hit was earned or each miss looked lucky."""
    diff = {(r["set_id"], r["window"]): (r.get("paired") or {}).get("diff") for r in records
            if r.get("type") == "RESOLUTION" and r.get("status") == "RESOLVED"}
    outc = {}
    for r in records:
        if r.get("type") == "RESOLUTION":
            for c in r.get("cone") or []:
                if c.get("outcome") is not None:
                    outc[(r["set_id"], c["id"])] = bool(c["outcome"])
    out = {}
    for mode in ("live", "shadow"):
        for side in ("BACK", "AVOID"):
            ps = [p for p in pairs if p["call"].get("side") == side and (p["call"].get("live") or mode == "shadow")]
            if not ps:
                continue
            w = sum(p["w"] for p in ps)
            hit = sum(p["w"] * (p["y"] if side == "BACK" else 1 - p["y"]) for p in ps)
            base = sum(p["w"] * (p["anchor"] if side == "BACK" else 1 - p["anchor"]) for p in ps)
            ex = [diff.get((p["set_id"], p["window"])) for p in ps if p["kind"] == "RELATIVE"]
            ex = [e for e in ex if e is not None]
            luck = Counter()
            for p in ps:
                mech = TRIANGLES.get(p["family"])
                h = p["y"] if side == "BACK" else 1 - p["y"]
                if p["kind"] == "RELATIVE" and side == "BACK":
                    k = p["statement"].rsplit("_", 1)[-1]
                    if h and mech:
                        luck["earned_catalyst_came" if outc.get((p["set_id"], mech[0])) else "beat_twins_no_catalyst"] += 1
                    elif h:
                        luck["beat_twins"] += 1
                    elif outc.get((p["set_id"], f"GAIN0_{k}")):
                        luck["rose_with_market_but_lost_to_twins"] += 1
                    else:
                        luck["miss"] += 1
                else:
                    luck["hit" if h else "miss"] += 1
            out[f"{mode}_{side}"] = {"n": round(w, 3), "hit_rate": round(hit / w, 4), "anchor_rate": round(base / w, 4),
                                     "lift": round((hit - base) / w, 4), "hit_rate_95": _wilson(hit, w),
                                     "mean_excess_vs_twins": round(float(np.mean(ex)), 5) if ex else None,
                                     "n_excess": len(ex), "why": dict(sorted(luck.items()))}
    return out


def statistics(records: list[dict] | None = None, lrecs: list[dict] | None = None, asof: str | None = None) -> dict:
    proto, _ = protocol()
    records = cr.cat_lines() if records is None else records
    lrecs = lines() if lrecs is None else lrecs
    asof = asof or utc_stamp()
    pairs = forward_pairs(records, lrecs, asof)
    per = {}
    for stmt in sorted({(p["family"], p["statement"]) for p in pairs}):
        ps = [p for p in pairs if (p["family"], p["statement"]) == stmt]
        w = sum(p["w"] for p in ps)
        per[":".join(stmt)] = {"n": round(w, 3), "rate": sum(p["w"] * p["y"] for p in ps) / w,
                               **{f"brier_{k}": sum(p["w"] * (p[k] - p["y"]) ** 2 for p in ps) / w
                                  for k in ("anchor", "raw", "published")}}
    by_session: dict[str, list[tuple[float, float]]] = {}
    for p in pairs:
        by_session.setdefault(p["session"], []).append((p["w"], (p["anchor"] - p["y"]) ** 2 - (p["raw"] - p["y"]) ** 2))
    sm = np.array([sum(w * d for w, d in v) / sum(w for w, _ in v) for _, v in sorted(by_session.items())])
    claim = {"n_paired": len(pairs), "n_sessions": len(sm), "mean_gain": float(sm.mean()) if len(sm) else None,
             "t": None, "p_one_sided": None}
    if len(sm) >= 2 and float(np.std(sm, ddof=1)) > 0:
        t = float(sm.mean() / (np.std(sm, ddof=1) / math.sqrt(len(sm))))
        claim["t"], claim["p_one_sided"] = t, float(spec.t_sf(t, len(sm) - 1))
    c = proto["claim"]
    design = {"looks": {"n": c["looks"], "t_min": c["t_min"], "min_sessions": c["min_sessions"]}}
    claim["look"] = cr.prereg_verdict(claim, claim["mean_gain"], 1.0, design=design)
    bins = []
    for lo in np.arange(0, 1, 0.1):
        b = [p for p in pairs if lo <= p["raw"] < lo + 0.1]
        if b:
            bins.append({"from": round(float(lo), 1), "n": len(b), "said": float(np.mean([p["raw"] for p in b])),
                         "happened": float(np.mean([p["y"] for p in b]))})
    return {"asof": asof, "forecasts": sum(f.get("type") == RECORD for f in lrecs), "pairs": len(pairs),
            "gates": {k: gate(pairs, k) for k in SKILL_KINDS}, "claim": claim, "per_statement": per,
            "calls": call_statistics(pairs, records), "reliability": bins, "beliefs": beliefs(train(records, asof))}


def beliefs(state: State, top: int = 8) -> dict[str, list[dict]]:
    """What the learner believes now: each kind's strongest slopes (the shared one for RELATIVE), mean and sd."""
    out = {}
    for k, m in state.models.items():
        if m is None:
            continue
        for name, (w, c) in ([(k, (m.theta[:m.nb], m.cov[:m.nb, :m.nb]))] if m.nb else
                             [(f"{k} ({t})", m.slope(t)) for t in m.tasks]):
            sd = np.sqrt(np.clip(np.diag(c), 0, None))
            order = np.argsort(-np.abs(w) / np.where(sd > 0, sd, 1))[:top]
            out[name] = [{"feature": FEATURES[j], "label": LABELS[FEATURES[j]], "slope": round(float(w[j]), 4),
                          "sd": round(float(sd[j]), 4)} for j in order]
    return out


def _fmt(v) -> str:
    return "n/a" if v is None else f"{v:.4f}"


def render(st: dict) -> str:
    c = st["claim"]
    out = ["# Learner v2 (LEARNER-v2)", "",
           "Judged against a climatology twin of itself (how often each statement comes true per family), on skill "
           "statements only: beating the twins, the stated catalyst happening, and both. Confidence opens only when a "
           "time-uniform lower bound on its forward gain is above zero.", "",
           f"- As of {st['asof']}: {st['forecasts']} forecasts sealed, {st['pairs']} forward-scored pairs",
           f"- Claim (raw beats the anchor, per-session Brier gain): {c['n_paired']} pairs, {c['n_sessions']} sessions, "
           f"t {None if c['t'] is None else round(c['t'], 2)}: **{c['look']['verdict']}**", "",
           "| Kind | Earned confidence (alpha) | Observations | Mean gain | Lower bound | Recent skill |", "|---|---|---|---|---|---|"]
    for k, (a, info) in st["gates"].items():
        out.append(f"| {k} | {a:.2f} | {info['observations']} | {_fmt(info['mean_gain'])} | {_fmt(info['lower'])} | "
                   f"{_fmt(info['recent_skill'])} |")
    out += ["", "| Statement | n | Rate | Brier anchor | Brier raw | Brier published |", "|---|---|---|---|---|---|"]
    for k, v in st["per_statement"].items():
        out.append(f"| {k} | {v['n']} | {v['rate']:.2f} | {v['brier_anchor']:.4f} | {v['brier_raw']:.4f} | "
                   f"{v['brier_published']:.4f} |")
    out += ["", "Calls (forward): " + ("; ".join(f"{k} n {v['n']}: hit {v['hit_rate']:.2f} vs anchor {v['anchor_rate']:.2f} "
                                                f"({v['why']})" for k, v in st["calls"].items()) or "none scored yet")]
    out += ["", "Reliability (raw): " + ("; ".join(f"{b['from']:.1f}+ n {b['n']}: said {b['said']:.2f}, happened "
                                                    f"{b['happened']:.2f}" for b in st["reliability"]) or "none yet")]
    out += ["", "## What it believes now", ""]
    for k, bs in st["beliefs"].items():
        out.append(f"- **{k}**: " + "; ".join(f"{b['label']} {b['slope']:+.3f} (sd {b['sd']:.3f})" for b in bs))
    return "\n".join(out) + "\n"


def write_report() -> Path:
    REPORT.write_text(render(statistics()), encoding="utf-8")
    return REPORT


# ------------------------------------------------------------------------------- verify
def verify(path: Path | None = None, records: list[dict] | None = None, tol: float = 1e-6) -> list[str]:
    """The chain; one forecast per set, bound to the sealed set, made before its cutoff; and every number reproduced by
    retraining on the resolutions dated before the forecast (a learner that saw a later outcome cannot pass)."""
    path = LEDGER if path is None else path
    if not path.exists():
        return []
    problems = [f"{path.name}: {p}" for p in paper.verify_chain(path)]
    proto, sha = protocol()
    records = cr.cat_lines() if records is None else records
    sets = {r["set_id"]: r for r in records if r.get("type") == "CATALYST_SET"}
    lrecs = paper.ledger_lines(path)
    seen, trained, gated = set(), {}, {}
    res = [(r.get("resolved_at") or "9", (r.get("record_hash"), r.get("set_id"), r.get("window"), r.get("resolved_at")))
           for r in records if r.get("type") == "RESOLUTION"]
    for f in lrecs:
        if f.get("type") != RECORD:
            problems.append(f"{path.name}: unknown record type {f.get('type')!r}")
            continue
        sid = f["set_id"]
        if sid in seen:
            problems.append(f"{sid}: forecast twice")
        seen.add(sid)
        if f["protocol"]["sha256"] != sha:
            problems.append(f"{sid}: learner protocol sha256 differs from research/LEARNER_v2/protocol.json")
        if f["history"]["sha256"] != HISTORY_SHA256:
            problems.append(f"{sid}: warm start sha256 differs from the pinned one")
        s = sets.get(sid)
        if s is None or s.get("record_hash") != f["set_record_hash"]:
            problems.append(f"{sid}: forecast binds no sealed set with that hash")
            continue
        if f["made_at"] >= s["entry_cutoff"]:
            problems.append(f"{sid}: forecast made at {f['made_at']}, after the set's cutoff {s['entry_cutoff']}")
        # the training depends only on the resolutions before the forecast; the gates also on the forecasts before it
        key = tuple(sorted((h for t, h in res if t < f["made_at"]), key=repr))
        if key not in trained:
            trained[key] = train(records, f["made_at"])
        gkey = (key, sum(x.get("type") == RECORD and x["made_at"] < f["made_at"] for x in lrecs))
        if gkey not in gated:
            gated[gkey] = gates(records, lrecs, f["made_at"])
        state, g = trained[key], gated[gkey]
        again = _record(s, f["made_at"], records, lrecs, proto, sha, state, g)
        bad = [stmt for stmt, fc in f["forecasts"].items()
               if stmt not in again["forecasts"]
               or any(abs(fc[k] - again["forecasts"][stmt][k]) > tol for k in ("anchor", "raw", "published"))
               or (fc.get("call") or {}) != (again["forecasts"][stmt].get("call") or {})]
        if bad or set(again["forecasts"]) != set(f["forecasts"]):
            problems.append(f"{sid}: forecasts do not reproduce from the resolutions before {f['made_at']} "
                            f"(possible peeking): {', '.join(bad) or 'statement list'}")
        if any(abs(f["gate"][k]["alpha"] - again["gate"][k]["alpha"]) > tol for k in SKILL_KINDS):
            problems.append(f"{sid}: earned confidence does not reproduce from the forecasts and outcomes before it")
    return problems

"""LEARNER_v2.1 (research/LEARNER_v2/protocol_v2_1.json): the self-learning layer, rebuilt so that it can only earn
credit for telling sets apart, never for base rates, the market or luck; and graded on its thesis, whatever the move.

- Anchor. Every statement is judged against a climatology twin of the learner: the same Bayesian fit with an intercept
  only, so the anchor learns how often each statement comes true for each family. The learner's forecast is the
  anchor moved by the set's own features (centred slopes): its average equals the anchor, so its only possible edge
  is discrimination.
- Skill statements only. RELATIVE (graded against the twins), MECHANISM (the stated catalyst happens), TRIANGULATED
  (both) and PATH (v2.1, on the owner's "I dont care if its gonna be a pump and dump. I just care if it gets it right,
  and its thesis on even a pump and dump or whatnot is right"): the stock's own pump (PUMP30_k, PUMP100_k), dump
  (DUMP10_k) or pump and dump (PUMP_AND_DUMP_k), each true only when fewer than half of its twins made the same move.
  The raw moves (GAIN0, FADE10, RUN30, DOUBLE), which a market-wide move makes true, get the anchor alone.
- Theses. Every call states what will happen in words built from its statement; a call is right only when the whole
  statement came true, and the report shows calls that came partly true and moves the market made too.
- Two registers: the Catalyst Register's families and the Speculation Register's sets (families SPEC_<market>).
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
import re
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

PROTOCOL_JSON = PKG_ROOT / "research" / "LEARNER_v2" / "protocol_v2_2.json"
HISTORY = PKG_ROOT / "research" / "LEARNER_v2" / "warmstart" / "events.csv.gz"
HISTORY_SHA256 = "1eff13dabff91e2a41ae654ba9da645d87c6cf94a7efd67cbbf808d338fc9a13"
LEDGER = paper.PAPER / "learner_v2.jsonl"
REPORT = paper.PAPER / "LEARNER_V2.md"
VERSION = "LEARNER-v2.2"
RECORD = "LEARNER2_FORECAST"
SPEC_FAMILIES = ("SPEC_IDX", "SPEC_US", "SPEC_CRYPTO")  # the Speculation Register's sets, by market
FAMILIES = ("SEC13D", "SEC13D_V2", "DILUTION_8K", "FORM4", "FORM4_SHARP", "IDX_INDEX", *SPEC_FAMILIES)
GROUP = {"SEC13D": "13D", "SEC13D_V2": "13D", "FORM4": "F4", "FORM4_SHARP": "F4", "DILUTION_8K": "DIL",
         "IDX_INDEX": "IDX", **{f: "SPEC" for f in SPEC_FAMILIES}}
TRI = "TRIANGULATED"
TRIANGLES = {"SEC13D_V2": ("MECH_13DA_UP_60", "BEATS_TWINS_60"), "FORM4_SHARP": ("MECH_SECOND_BUY_20", "BEATS_TWINS_60")}
SKILL_KINDS = ("RELATIVE", "MECHANISM", "TRIANGULATED", "PATH")
OWN_MOVE = 0.5  # a move is the stock's own when fewer than this share of its twins made the same move
BASE_OF = {"PUMP30": "RUN30", "PUMP100": "DOUBLE", "DUMP10": "FADE10"}  # each move statement and the raw move it filters
_PATH_BASE = re.compile(r"^(RUN30|DOUBLE|FADE10)_(\d+)$")
_PATH_ID = re.compile(r"^(PUMP30|PUMP100|DUMP10|PUMP_AND_DUMP)_(\d+)$")
NOT_SHARED = frozenset({"REVERSAL_POST20"})  # relative, but true when the stock goes against the call's direction
FX = {"US": 1.0, "IDX": 1 / 16000.0, "CRYPTO": 1.0}  # to US dollars, for the liquidity and size features
CLIP = (0.01, 0.99)
LAMBDA_SHARED, LAMBDA_TASK, LAMBDA_OWN, LAMBDA_ICPT = 16.0, 25.0, 16.0, 1 / 1.5 ** 2
MAX_IT, TOL = 50, 1e-10
N_CAP = 300  # history's total weight per kind, in live outcomes
WINDOW_DAYS = 90  # the triangulation counts
GATE = {"delta": 0.05, "t_star_weeks": 52, "t_min": 30, "recent_weeks": 52, "recent_min": 8, "z_open": 1.645,
        "z_stay": 0.842, "skill_full": 0.02}
CLASS_OF = {"BASE5": "5", "H20": "20", "PATH20": "20", "M20": "20", "RUNUP": "20", "POST20": "20", "H60": "60", "M60": "60",
            "TRI": "60"}  # a statement's horizon class, by the window that resolves it
BLOCKS = {"5": (1, 1), "20": (1, 3), "60": (4, 2)}  # horizon class -> (weeks per observation, lag in observations)
CLAIM_BLOCK = (4, 2)  # the claim pools every class in 4-week blocks
EPOCH = date(2000, 1, 3)  # a Monday: blocks of weeks are counted from it
VERIFY_TOL = 2e-6  # twice the 1e-6 rounding step of the stored numbers
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
UNSIGNED = {"s_ret1": "signal-day move", "s_ret5": "5-session move", "s_ret20": "20-session move",
            "s_dd60": "distance from the 60-session high", "s_cpos": "close near the day's high"}
_SIGNED = [FEATURES.index(f) for f in UNSIGNED]
THESIS = {  # what a BACK call says will happen; an AVOID says it will not
    "BEATS_TWINS": "it beats its twins over {k} sessions",
    "LOSES_TO_TWINS": "it loses to its twins over {k} sessions",
    "PUMP30": "it closes at least 30% above the signal close within {k} sessions, and most of its twins do not",
    "PUMP100": "it closes at twice the signal close or more within {k} sessions, and most of its twins do not",
    "DUMP10": "its {k}-session plan loses at least 10%, and most of its twins do not",
    "PUMP_AND_DUMP": ("a pump and dump: it closes at least 30% above the signal close within {k} sessions and its "
                      "plan still ends at least 10% down, each when most of its twins do not")}
FIXED_THESIS = {
    "MECH_SECOND_BUY_20": "another insider buys within 20 sessions",
    "MECH_13DA_UP_60": "the activist files a 13D amendment raising the stake within 60 days",
    "WITH_FLOW_RUNUP": "it moves with the index flow before the effective date, against its twins",
    "REVERSAL_POST20": "it reverses against the index flow in the 20 sessions after, against its twins",
    "TRIANGULATED": "the stated catalyst comes and it beats its twins"}


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8")), sha256_file(PROTOCOL_JSON)


def lines(path: Path | None = None) -> list[dict]:
    p = LEDGER if path is None else path
    return paper.ledger_lines(p) if p.exists() else []


def as_set(r: dict) -> dict:
    """A Speculation Register set read as a set of family SPEC_<market> (a long call); any other record unchanged."""
    if r.get("type") == "SPECULATION_SET":
        return {**r, "type": "CATALYST_SET", "family": f"SPEC_{r.get('market', 'US')}", "direction": 1}
    return r


def all_records() -> list[dict]:
    """What the learner reads: the Catalyst Register, then the Speculation Register (sets and resolutions)."""
    return [as_set(r) for r in cr.cat_lines()] + [as_set(r) for r in spec.spec_lines()]


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
    if _PATH_ID.match(stmt):
        return "PATH"
    if cr.is_relative(stmt):
        return "RELATIVE"
    return None  # a raw move (GAIN0, FADE10, RUN30, DOUBLE): a market-wide move makes it true; anchor only


@lru_cache(maxsize=1)
def _frozen_priors() -> dict[str, dict]:
    reg, _ = cr.protocol()
    out = {f: {c["id"]: c["prior"] for c in spec_["cone"]} for f, spec_ in reg["families"].items()}
    out.update({f: {c["id"]: c["prior"] for c in p["cone"]} for f, (p, _) in cr.extra_families().items()})
    sp, _ = spec.protocol()
    for m in ("IDX", "US", "CRYPTO"):
        out[f"SPEC_{m}"] = {c["id"]: (c["prior"].get(m) if isinstance(c["prior"], dict) else c["prior"]) for c in sp["cone"]}
    return out


def base_prior(family: str, stmt: str) -> float:
    """The family's frozen prior for a statement (0.5 where the protocol says "running"); TRIANGULATED: the product."""
    if stmt == TRI:
        a, b = TRIANGLES[family]
        return base_prior(family, a) * base_prior(family, b)
    m = _PATH_ID.match(stmt)
    if m and m[1] == "PUMP_AND_DUMP":
        return base_prior(family, f"RUN30_{m[2]}") * base_prior(family, f"FADE10_{m[2]}")
    if m:
        return base_prior(family, f"{BASE_OF[m[1]]}_{m[2]}")
    v = _frozen_priors().get(family, {}).get(stmt)
    return float(v) if isinstance(v, (int, float)) else 0.5


def statements(s: dict) -> list[tuple[str, str]]:
    """(statement, the window that resolves it) for a set: its cone; TRIANGULATED where the family has one; each raw
    move's twin-filtered statement (PUMP30_k, PUMP100_k, DUMP10_k); PUMP_AND_DUMP_k where RUN30_k and FADE10_k share a
    window."""
    # only the windows this protocol names (CLASS_OF): a register may add windows later for a later learner version
    out = [(c["id"], c["resolves_with"]) for c in s.get("cone", []) if c["resolves_with"] in CLASS_OF]
    ids = dict(out)
    tri = TRIANGLES.get(s.get("family"))
    if tri and all(t in ids for t in tri):
        out.append((TRI, "TRI"))
    moves = [(_PATH_BASE.match(sid), w) for sid, w in ids.items()]
    out += [(f"{ {v: k for k, v in BASE_OF.items()}[m[1]] }_{m[2]}", w) for m, w in moves if m]
    out += [(f"PUMP_AND_DUMP_{m[2]}", w) for m, w in moves if m and m[1] == "RUN30" and ids.get(f"FADE10_{m[2]}") == w]
    return out


def thesis(stmt: str, side: str) -> str:
    """The call in words: what a BACK says will happen, or what an AVOID says will not."""
    m = re.match(r"^(.*)_(\d+)$", stmt)
    text = FIXED_THESIS.get(stmt) or (THESIS[m[1]].format(k=m[2]) if m and m[1] in THESIS else stmt)
    return text if side == "BACK" else f"not: {text}"


def view(x: np.ndarray, kind: str | None, direction: int) -> np.ndarray:
    """A move statement (PATH) is about the price, not the call: for a short call its price features are read unsigned."""
    if kind != "PATH" or direction >= 0:
        return x
    y = x.copy()
    y[_SIGNED] *= -1
    return y


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
    (corroborate) or the opposite (conflict). Only sets sealed before it (by sealed_at, across both registers), so the
    value never changes."""
    seen: dict[tuple[str, str], list[tuple[str, str, int, str]]] = {}
    out = {}
    sets = [r for r in records if r.get("type") == "CATALYST_SET" and r.get("family") in FAMILIES]
    for r in sorted(sets, key=lambda r: r.get("sealed_at") or ""):  # stable: ties keep ledger order
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


def outcomes(records: list[dict], asof: str) -> dict[tuple[str, str], tuple]:
    """(set, statement) -> (outcome, resolved_at, the twins' rate of the same statement or None) for every graded
    statement resolved before asof; a later revision of the same (set, window) replaces an earlier one."""
    latest: dict[tuple, dict] = {}
    for r in records:
        if r.get("type") == "RESOLUTION" and (r.get("resolved_at") or "9") < asof:
            latest[(r["set_id"], r.get("window"))] = r  # an UNRESOLVABLE or ungraded revision clears what it replaces
    out: dict[tuple[str, str], tuple] = {}
    for (sid, _), r in latest.items():
        for c in r.get("cone") or []:
            if c.get("outcome") is not None:
                out[(sid, c["id"])] = (bool(c["outcome"]), r["resolved_at"], c.get("twins_rate"))
    return out


def own_move(outc: dict, set_id: str, base: str) -> tuple[bool, str] | None:
    """A raw move as the stock's own: false when it did not happen; true when it did and fewer than half of the twins
    made it; ungraded when it did and no twin was graded."""
    o = outc.get((set_id, base))
    if o is None:
        return None
    if not o[0]:
        return False, o[1]
    return None if o[2] is None else (o[2] < OWN_MOVE, o[1])


def outcome_of(outc: dict, set_id: str, family: str, stmt: str) -> tuple[bool, str] | None:
    """(outcome, when it became known): a cone statement as graded; TRIANGULATED and PUMP_AND_DUMP_k once both of their
    parts are; a move statement through own_move."""
    m = _PATH_ID.match(stmt)
    if stmt == TRI and family not in TRIANGLES:
        return None
    if stmt == TRI or (m and m[1] == "PUMP_AND_DUMP"):
        a, b = (TRIANGLES[family] if stmt == TRI else (None, None))
        oa = outc.get((set_id, a)) if stmt == TRI else own_move(outc, set_id, f"RUN30_{m[2]}")
        ob = outc.get((set_id, b)) if stmt == TRI else own_move(outc, set_id, f"FADE10_{m[2]}")
        if oa is None or ob is None:
            return None
        return oa[0] and ob[0], max(oa[1], ob[1])
    if m:
        return own_move(outc, set_id, f"{BASE_OF[m[1]]}_{m[2]}")
    o = outc.get((set_id, stmt))
    return None if o is None else (o[0], o[1])


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
            kind = kind_of(stmt)
            raw.append((event_key(s), stmt, Row(kind or "ABSOLUTE", f"{s['family']}:{stmt}", f"{s['family']}:{stmt}",
                                                 view(x, kind, int(s.get("direction", 1) or 1)),
                                                 base_prior(s["family"], stmt), float(o[0]), 1.0)))
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
def share_group(task: str) -> str | None:
    """The slope block a statement shares across families: RIGHT for every relative statement that is true when the
    call is right (REVERSAL_POST20 excepted); PUMP, DUMP or PUMP_AND_DUMP for the moves; none for the mechanisms and
    TRIANGULATED, which are different events in each family."""
    stmt = task.split(":", 1)[1]
    k = kind_of(stmt)
    if k == "RELATIVE":
        return None if stmt in NOT_SHARED else "RIGHT"
    if k == "PATH":
        return {"PUMP30": "PUMP", "PUMP100": "PUMP", "DUMP10": "DUMP", "PUMP_AND_DUMP": "PUMP_AND_DUMP"}[_PATH_ID.match(stmt)[1]]
    return None


class Model:
    """One kind's penalised logistic model: logit p = logit(p0) + intercept[icpt] + (x - centre[task]) . slope[task],
    slope[task] = shared[share group] + own[task], with the Laplace covariance at the maximum a posteriori."""

    def __init__(self, kind: str, rows: list[Row]):
        self.kind = kind
        D = len(FEATURES)
        self.tasks = sorted({r.task for r in rows})
        self.icpts = sorted({r.icpt for r in rows})
        self.group = {t: share_group(t) for t in self.tasks}
        self.groups = sorted({g for g in self.group.values() if g})
        self.nb = D * len(self.groups)
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
                              *[np.full(D, LAMBDA_TASK if self.group[t] else LAMBDA_OWN) for t in self.tasks],
                              np.full(I, LAMBDA_ICPT)])
        P = len(lam)
        groups = {}
        for j, key in enumerate(zip(ti, ii)):
            groups.setdefault(key, []).append(j)
        groups = {k: np.array(v) for k, v in sorted(groups.items())}
        theta = np.zeros(P)

        def objective(th):
            eta_ = off + self._linear(th, Z, ti, ii)
            return float((w0 * (y * eta_ - np.logaddexp(0.0, eta_))).sum() - 0.5 * (lam * th * th).sum())

        for _ in range(MAX_IT):
            eta = off + self._linear(theta, Z, ti, ii)
            p = _sigmoid(eta)
            r, h = w0 * (y - p), w0 * p * (1 - p)
            g, H = -lam * theta, np.diag(lam)
            for (tk, ik), idx in groups.items():
                Zg, rg, hg = Z[idx], r[idx], h[idx]
                gz, Szz, Sz = Zg.T @ rg, (Zg * hg[:, None]).T @ Zg, Zg.T @ hg
                own, a = slice(self.nb + tk * D, self.nb + (tk + 1) * D), self.nb + T * D + ik
                grp = self.group[self.tasks[tk]]
                blocks = [own] + ([self._gslice(grp)] if grp else [])
                for b1 in blocks:
                    g[b1] += gz
                    H[b1, a] += Sz
                    H[a, b1] += Sz
                    for b2 in blocks:
                        H[b1, b2] += Szz
                g[a] += rg.sum()
                H[a, a] += hg.sum()
            step = np.linalg.solve(H, g)
            if float(np.max(np.abs(step))) < TOL:
                break
            base, t = objective(theta), 1.0
            while objective(theta + t * step) < base - 1e-10 * (1 + abs(base)) and t > 1e-10:  # step-halving: never
                t /= 2  # move downhill by more than rounding noise
            theta = theta + t * step
        else:
            raise RuntimeError(f"{kind} model did not converge in {MAX_IT} iterations")
        self.theta, self.cov = theta, np.linalg.inv(H)
        self.n_rows = {t: float(w0[ti == k].sum()) for k, t in enumerate(self.tasks)}

    def _gslice(self, grp: str) -> slice:
        D, k = len(FEATURES), self.groups.index(grp)
        return slice(k * D, (k + 1) * D)

    def _linear(self, theta, Z, ti, ii):
        D, T = len(FEATURES), len(self.tasks)
        slope = theta[self.nb:self.nb + T * D].reshape(T, D)[ti]
        if self.nb:
            shared = np.array([theta[self._gslice(self.group[t])] if self.group[t] else np.zeros(D) for t in self.tasks])
            slope = slope + shared[ti]
        return theta[self.nb + T * D:][ii] + np.einsum("ij,ij->i", Z, slope)

    def slope(self, task: str) -> tuple[np.ndarray, np.ndarray]:
        """The task's slope vector and its covariance (a task the fit has not seen: its group's part, or zero)."""
        D = len(FEATURES)
        sel = []
        if task in self.tasks:
            k = self.tasks.index(task)
            sel.append(np.arange(self.nb + k * D, self.nb + (k + 1) * D))
        grp = self.group.get(task, share_group(task))
        if grp in self.groups:
            g = self._gslice(grp)
            sel.append(np.arange(g.start, g.stop))
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
    def objective(a_):
        return float((w * (y * (o + a_) - np.logaddexp(0.0, o + a_))).sum() - 0.5 * LAMBDA_ICPT * a_ * a_)

    a = 0.0
    for _ in range(MAX_IT):
        p = _sigmoid(o + a)
        step = float((w * (y - p)).sum() - LAMBDA_ICPT * a) / float((w * p * (1 - p)).sum() + LAMBDA_ICPT)
        if abs(step) < TOL:
            return a
        t, base = 1.0, objective(a)
        while objective(a + t * step) < base - 1e-10 * (1 + abs(base)) and t > 1e-10:
            t /= 2
        a += t * step
    raise RuntimeError(f"anchor did not converge in {MAX_IT} iterations")


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
    info = {"live_rows": {t: round(sum(r.w for r in rs), 4) for t, rs in sorted(by_task.items())},
            "history_rows": dict(sorted(Counter(r.kind for r in history_rows()).items()))}
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
                acc.setdefault(f"{s['family']}:{stmt}", []).append(view(x, kind_of(stmt), int(s.get("direction", 1) or 1)))
    return {t: np.mean(v, axis=0) for t, v in sorted(acc.items())}


def anchor_prob(state: State, task: str, p0: float) -> float:
    return _prob(_logit(p0) + state.anchors.get(task, 0.0))


# ------------------------------------------------------------------------------- earned confidence
def forward_pairs(records: list[dict], lrecs: list[dict], asof: str) -> list[dict]:
    """Every (earlier forecast, skill statement) whose outcome resolved after the forecast and before asof, each
    underlying event weighted once per statement."""
    outc = outcomes(records, asof)
    sets = {r["set_id"]: r for r in records if r.get("type") == "CATALYST_SET"}
    out, seen = [], set()
    for f in lrecs:
        if f.get("type") != RECORD or f["made_at"] >= asof:
            continue
        s = sets.get(f["set_id"])
        if (f["set_id"] in seen or s is None or s.get("record_hash") != f["set_record_hash"]
                or f["made_at"] >= s["entry_cutoff"]):
            continue  # a duplicate, unbound or late forecast is never scored
        seen.add(f["set_id"])
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


def block_of(ts: str, weeks: int) -> int:
    """The block of `weeks` ISO weeks (counted from EPOCH) that a UTC timestamp falls in."""
    return (date.fromisoformat(ts[:10]) - EPOCH).days // (7 * weeks)


def block_end(block: int, weeks: int) -> str:
    """The Monday 00:00 UTC that ends a block."""
    return f"{(EPOCH + timedelta(days=7 * weeks * (block + 1))).isoformat()}T00:00:00Z"


def observations(pairs: list[dict], asof: str, weeks: int = 1, key: str = "raw") -> list[tuple[float, float, int]]:
    """One observation per block of `weeks` ISO weeks of resolution that has ended by asof: the mean Brier gain of `key`
    over the anchor, the mean anchor Brier and the number of pairs, over the pairs that resolved in it. An underlying
    event counts once per statement over the whole sequence (where it first resolved), so a parent and its child never
    count twice, and a block never changes once it has ended. Many sets resolving on one day, which share one market,
    make one observation, not many."""
    seen, blocks = set(), {}
    for p in sorted(pairs, key=lambda p: (p["resolved_at"], p["set_id"], p["statement"])):
        k = (p["event_key"], p["statement"])
        if k in seen:
            continue
        seen.add(k)
        b = block_of(p["resolved_at"], weeks)
        if block_end(b, weeks) <= asof:
            blocks.setdefault(b, []).append(p)
    return [(float(np.mean([(p["anchor"] - p["y"]) ** 2 - (p[key] - p["y"]) ** 2 for p in ps])),
             float(np.mean([(p["anchor"] - p["y"]) ** 2 for p in ps])), len(ps)) for _, ps in sorted(blocks.items())]


def long_run_sd(a: np.ndarray, lag: int) -> float:
    """The standard deviation of a mean's terms when neighbouring observations share up to `lag` steps of overlapping
    windows: the truncated long-run variance (the exact weights for overlap of that length) with the small-sample
    correction n / (n - 2 lag - 1) for autocovariances around an estimated mean, never below the plain sample sd.
    Measured on zero-mean overlapping noise, a one-sided 5% test with it rejects 5 to 6% of the time where the
    Newey-West (Bartlett) version rejects 8 to 17%."""
    a = np.asarray(a, dtype=float)
    n = len(a)
    if n < 2:
        return float("nan")
    c = a - a.mean()
    s = float(c @ c) / n
    for k in range(1, min(lag, n - 1) + 1):
        s += 2 * float(c[k:] @ c[:-k]) / n
    s *= n / max(n - 2 * lag - 1, 1)
    return math.sqrt(max(s, float(c @ c) / (n - 1)))


def confidence_lowers(d: list[float], lag: int = 0, delta: float = GATE["delta"], t_star: float = 52) -> np.ndarray:
    """The lower edge of the asymptotic confidence sequence for the mean after each observation (Waudby-Smith et al.,
    time-uniform central limit theory), with the long-run sd: valid at every t at once, so a weekly look does not
    inflate the chance that luck clears zero. NaN before two observations."""
    a = np.asarray(d, dtype=float)
    rho2 = (-2 * math.log(delta) + math.log(-2 * math.log(delta) + 1)) / t_star
    out = np.full(len(a), np.nan)
    for i in range(1, len(a)):
        t = i + 1
        sd = long_run_sd(a[:t], lag)
        out[i] = a[:t].mean() - sd * math.sqrt(2 * (t * rho2 + 1) / (t * t * rho2) * math.log(math.sqrt(t * rho2 + 1) / delta))
    return out


def gate_path(d: np.ndarray, weeks: int, lag: int) -> list[tuple[float, bool, float]]:
    """(proof, open, recent lower bound) after each observation from t_min on, in one causal pass: each step uses only
    the observations up to it, so the path equals checking the gate every time.
    Proof: the running maximum of the confidence sequence's lower edge (its running intersection is a confidence
    sequence too, so luck clears zero at most 5% of the time however often it is checked).
    Present: the last year (at least recent_min observations) must show skill. The gate opens when their one-sided
    95% lower bound is above zero and stays open while their 80% bound is, so it closes when the skill fades, and a real
    but noisy edge does not flicker."""
    d = np.asarray(d, dtype=float)
    lowers = confidence_lowers(d, lag, t_star=GATE["t_star_weeks"] / weeks)
    n_recent = max(GATE["recent_min"], math.ceil(GATE["recent_weeks"] / weeks))
    best, opened, out = -math.inf, False, []
    for t in range(GATE["t_min"] - 1, len(d)):
        best = max(best, float(lowers[t]))
        rec = d[max(0, t + 1 - n_recent): t + 1]
        se = long_run_sd(rec, lag) / math.sqrt(len(rec))
        opened = best > 0 and float(rec.mean() - (GATE["z_stay"] if opened else GATE["z_open"]) * se) > 0
        out.append((best, opened, float(rec.mean() - GATE["z_stay"] * se)))
    return out


def gate(pairs: list[dict], key: str, asof: str) -> tuple[float, dict]:
    """alpha for one gate, "KIND/CLASS" (a skill kind and a horizon class), from its observations: 0 below t_min
    observations or while closed; otherwise min(proof, recent lower bound) / mean anchor Brier / skill_full, clipped to
    0..1."""
    kind, cls = key.split("/")
    weeks, lag = BLOCKS[cls]
    obs = observations([p for p in pairs if p["kind"] == kind and CLASS_OF.get(p["window"], "20") == cls], asof, weeks)
    d = np.array([o[0] for o in obs], dtype=float)
    info = {"observations": len(obs), "mean_gain": float(d.mean()) if len(d) else None, "lower": None,
            "skill_lower": None, "recent_lower": None, "open": False}
    if len(d) < GATE["t_min"]:
        return 0.0, info
    b = float(np.mean([o[1] for o in obs]))
    best, opened, recent = gate_path(d, weeks, lag)[-1]
    info.update({"lower": best, "skill_lower": best / b if b > 0 else None, "recent_lower": recent, "open": opened})
    if not opened or b <= 0:
        return 0.0, info
    return float(_clip(min(best, recent) / b / GATE["skill_full"], 0.0, 1.0)), info


GATES = ("RELATIVE/5", "RELATIVE/20", "RELATIVE/60", "MECHANISM/20", "MECHANISM/60", "TRIANGULATED/60", "PATH/5", "PATH/20")


def gate_key(kind: str, window: str) -> str:
    return f"{kind}/{CLASS_OF.get(window, '20')}"


def gates(records: list[dict], lrecs: list[dict], asof: str) -> dict[str, tuple[float, dict]]:
    pairs = forward_pairs(records, lrecs, asof)
    return {k: gate(pairs, k, asof) for k in GATES}


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
        xv = view(x, kind, int(s.get("direction", 1) or 1))
        dev, sd, parts = (0.0, 0.0, np.zeros(len(FEATURES))) if m is None else m.deviation(task, xv, centres.get(task))
        raw = _prob(_logit(anchor) + dev)
        dev = _logit(raw) - _logit(anchor)  # after the probability clip
        alpha = gate_alpha.get(gate_key(kind, window), 0.0)
        order = np.argsort(-np.abs(parts))[:3]
        labels = {**LABELS, **UNSIGNED} if kind == "PATH" else LABELS
        why = [{"feature": FEATURES[j], "label": labels[FEATURES[j]], "logit": round(float(parts[j]), 4)}
               for j in order if abs(parts[j]) >= 0.01]
        call = call_of(dev, sd, alpha)
        if call["side"]:
            call["thesis"] = thesis(stmt, call["side"])
        lo, hi = _prob(_logit(anchor) + dev - CALL["z"] * sd), _prob(_logit(anchor) + dev + CALL["z"] * sd)
        out[stmt] = {**fc, "raw": round(raw, 6), "raw_90": [round(lo, 6), round(hi, 6)], "deviation": round(dev, 6),
                     "sd": round(sd, 6), "alpha": round(alpha, 6),
                     "published": round(_prob(_logit(anchor) + alpha * dev), 6), "call": call, "why": why}
    return out, [round(float(v), 6) for v in x]


def _head(lines: list[dict]) -> list:
    """A ledger state: its number of lines and the hash of the last one."""
    return [len(lines), lines[-1].get("record_hash") if lines else None]


def forecast_records(now: datetime, records: list[dict] | None = None, lrecs: list[dict] | None = None) -> list[dict]:
    """One LEARNER2_FORECAST for every sealed set still before its entry cutoff that has none yet. Each records the
    ledger state it was computed from, so verify can retrain on exactly that state."""
    proto, sha = protocol()
    if records is None:
        cat, spc = cr.cat_lines(), spec.spec_lines()
        records = [as_set(r) for r in cat] + [as_set(r) for r in spc]
        inputs = {"catalysts": _head(cat), "speculations": _head(spc)}
    else:
        inputs = {"records": _head(records)}
    lrecs = lines() if lrecs is None else lrecs
    asof = utc_stamp(now.astimezone(timezone.utc))
    done = {f["set_id"] for f in lrecs if f.get("type") == RECORD}
    todo = [s for s in records if s.get("type") == "CATALYST_SET" and s.get("family") in FAMILIES
            and s["entry_cutoff"] > asof and s["set_id"] not in done]
    if not todo:
        return []
    ctx = _context(records, lrecs, asof)
    return [_record(s, asof, proto, sha, inputs, ctx) for s in todo]


def _context(records: list[dict], lrecs: list[dict], asof: str) -> dict:
    """Everything a batch of forecasts at asof shares: the training, the gates, the triangulation counts, the live
    centres and the number of resolutions seen."""
    return {"state": train(records, asof), "gates": gates(records, lrecs, asof), "tri": tri_counts(records),
            "centres": live_centres(records, asof),
            "n_res": sum(r.get("type") == "RESOLUTION" and (r.get("resolved_at") or "9") < asof for r in records)}


def _record(s: dict, asof: str, proto: dict, sha: str, inputs: dict, ctx: dict) -> dict:
    state, g, n_res = ctx["state"], ctx["gates"], ctx["n_res"]
    tri = ctx["tri"].get(s["set_id"], (0, 0, 0))
    fc, x = forecast_set(s, tri, state, {k: v[0] for k, v in g.items()}, ctx["centres"])
    return {"type": RECORD, "learner": VERSION, "protocol": {"id": proto["protocol_id"], "sha256": sha},
            "history": {"file": str(HISTORY.relative_to(PKG_ROOT)), "sha256": HISTORY_SHA256},
            "set_id": s["set_id"], "set_record_hash": s["record_hash"], "event_key": event_key(s), "family": s["family"],
            "market": s.get("market", "US"), "ticker": s.get("ticker"), "signal_session": s["signal_session"],
            "entry_cutoff": s["entry_cutoff"], "made_at": asof, "inputs": inputs,
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


def thesis_parts(full: dict, p: dict) -> list[tuple[str, bool | None]]:
    """The parts a call's thesis needed: both parts of TRIANGULATED or PUMP_AND_DUMP_k; for a single move, the move
    itself and that it was the stock's own (most twins did not make it); otherwise the statement."""
    stmt, sid = p["statement"], p["set_id"]
    m = _PATH_ID.match(stmt)
    if stmt == TRI:
        a, b = TRIANGLES[p["family"]]
        return [("the catalyst came", (full.get((sid, a)) or (None,))[0]), ("it beat its twins", (full.get((sid, b)) or (None,))[0])]
    if m and m[1] == "PUMP_AND_DUMP":
        return [("its own pump", (own_move(full, sid, f"RUN30_{m[2]}") or (None,))[0]),
                ("its own dump", (own_move(full, sid, f"FADE10_{m[2]}") or (None,))[0])]
    if m:
        o = full.get((sid, f"{BASE_OF[m[1]]}_{m[2]}"))
        return [("the move happened", None if o is None else o[0]),
                ("most twins did not make it", None if o is None or o[2] is None else o[2] < OWN_MOVE)]
    return [("the statement", p["y"] == 1.0)]


def thesis_grade(full: dict, p: dict, side: str) -> str:
    """RIGHT when the whole thesis came true (for an AVOID: when the statement did not); PARTLY when some of its parts
    did; MARKET_MADE_IT when the move happened but most twins made it too (no credit); else WRONG."""
    if side == "AVOID":
        return "right" if p["y"] == 0.0 else "wrong"
    if p["y"] == 1.0:
        return "right"
    parts = thesis_parts(full, p)
    m = _PATH_ID.match(p["statement"])
    if m and m[1] != "PUMP_AND_DUMP" and parts[0][1] and parts[1][1] is False:
        return "market_made_it"
    return "partly" if any(v is True for _, v in parts) else "wrong"


def call_statistics(pairs: list[dict], records: list[dict]) -> dict:
    """Calls scored forward: hit rate against the anchor's rate on the same pairs, the paired excess return of the
    matching window, whether each thesis came true in full, partly, or only because the market moved, and why each
    relative hit was earned or each miss looked lucky."""
    full = outcomes(records, "9999-12-31T23:59:59Z")
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
            grades = Counter(thesis_grade(full, p, side) for p in ps)
            out[f"{mode}_{side}"] = {"n": round(w, 3), "hit_rate": round(hit / w, 4), "anchor_rate": round(base / w, 4),
                                     "lift": round((hit - base) / w, 4), "hit_rate_95": _wilson(hit, w),
                                     "mean_excess_vs_twins": round(float(np.mean(ex)), 5) if ex else None,
                                     "n_excess": len(ex), "theses": dict(sorted(grades.items())),
                                     "why": dict(sorted(luck.items()))}
    return out


def statistics(records: list[dict] | None = None, lrecs: list[dict] | None = None, asof: str | None = None) -> dict:
    proto, _ = protocol()
    records = all_records() if records is None else records
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
    blocks = observations(pairs, asof, CLAIM_BLOCK[0])
    sm = np.array([o[0] for o in blocks])
    claim = {"n_paired": int(sum(o[2] for o in blocks)), "n_sessions": len(sm), "unit": "4-week block of resolution",
             "mean_gain": float(sm.mean()) if len(sm) else None, "t": None, "p_one_sided": None}
    if len(sm) >= 2 and long_run_sd(sm, CLAIM_BLOCK[1]) > 0:
        t = float(sm.mean() / (long_run_sd(sm, CLAIM_BLOCK[1]) / math.sqrt(len(sm))))
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
            "coverage": coverage(records, lrecs, asof), "gates": {k: gate(pairs, k, asof) for k in GATES},
            "claim": claim, "per_statement": per, "calls": call_statistics(pairs, records), "reliability": bins,
            "beliefs": beliefs(train(records, asof))}


def coverage(records: list[dict], lrecs: list[dict], asof: str) -> dict:
    """Every set whose cutoff passed after the learner's first forecast should have a forecast; a gap is listed, so a
    learner cannot be judged only on the sets it chose to forecast. Also the forecasts without an external timestamp."""
    made = [f for f in lrecs if f.get("type") == RECORD]
    if not made:
        return {"due": 0, "forecast": 0, "missing": [], "without_timestamp": 0}
    start, done = min(f["made_at"] for f in made), {f["set_id"] for f in made}
    due = [s["set_id"] for s in records if s.get("type") == "CATALYST_SET" and s.get("family") in FAMILIES
           and start < s["entry_cutoff"] <= asof]
    missing = sorted(set(due) - done)
    stamped = sum(any((paper.TOKENS / f"{f['record_hash']}.{a}.tsr").exists() for a in ("freetsa", "sectigo"))
                  for f in made if f.get("record_hash"))
    return {"due": len(due), "forecast": len(due) - len(missing), "missing": missing[:20],
            "without_timestamp": len(made) - stamped}


def beliefs(state: State, top: int = 8) -> dict[str, list[dict]]:
    """What the learner believes now: the strongest slopes of each shared block (RIGHT, PUMP, DUMP, PUMP_AND_DUMP) and
    of each statement with slopes of its own, mean and sd."""
    out = {}
    for k, m in state.models.items():
        if m is None:
            continue
        labels = {**LABELS, **UNSIGNED} if k == "PATH" else LABELS
        blocks = [(f"{k} {g} (shared)", (m.theta[m._gslice(g)], m.cov[m._gslice(g), m._gslice(g)])) for g in m.groups]
        blocks += [(f"{k} ({t})", m.slope(t)) for t in m.tasks if not m.group[t]]
        for name, (w, c) in blocks:
            sd = np.sqrt(np.clip(np.diag(c), 0, None))
            order = np.argsort(-np.abs(w) / np.where(sd > 0, sd, 1))[:top]
            out[name] = [{"feature": FEATURES[j], "label": labels[FEATURES[j]], "slope": round(float(w[j]), 4),
                          "sd": round(float(sd[j]), 4)} for j in order]
    return out


def _fmt(v) -> str:
    return "n/a" if v is None else f"{v:.4f}"


def render(st: dict) -> str:
    c = st["claim"]
    cv = st["coverage"]
    out = ["# Learner v2.2 (LEARNER-v2.2)", "",
           "Judged against a climatology twin of itself (how often each statement comes true per family), on skill "
           "statements only: beating the twins, the stated catalyst happening, both, and the stock's own pump, dump or "
           "pump and dump (each only when most of its twins did not make the same move). A call is right only when its "
           "whole thesis came true. Confidence opens only when a time-uniform lower bound on its weekly forward gain is "
           "above zero and the last half-year still shows skill.", "",
           f"- As of {st['asof']}: {st['forecasts']} forecasts sealed, {st['pairs']} forward-scored pairs",
           f"- Coverage: {cv['forecast']} of {cv['due']} sets due since the first forecast"
           + (f" (missing: {', '.join(cv['missing'])})" if cv["missing"] else "")
           + f"; forecasts without an external timestamp: {cv['without_timestamp']}",
           f"- Claim (raw beats the anchor, Brier gain per 4-week block, overlap-robust t): {c['n_paired']} pairs, "
           f"{c['n_sessions']} blocks, t {None if c['t'] is None else round(c['t'], 2)}: **{c['look']['verdict']}**", "",
           "| Gate (kind/horizon) | Earned confidence (alpha) | Observations | Mean gain | Proof (lower bound) | Recent lower bound |",
           "|---|---|---|---|---|---|"]
    for k, (a, info) in st["gates"].items():
        out.append(f"| {k} | {a:.2f} | {info['observations']} | {_fmt(info['mean_gain'])} | {_fmt(info['lower'])} | "
                   f"{_fmt(info['recent_lower'])} |")
    out += ["", "| Statement | n | Rate | Brier anchor | Brier raw | Brier published |", "|---|---|---|---|---|---|"]
    for k, v in st["per_statement"].items():
        out.append(f"| {k} | {v['n']} | {v['rate']:.2f} | {v['brier_anchor']:.4f} | {v['brier_raw']:.4f} | "
                   f"{v['brier_published']:.4f} |")
    out += ["", "Calls (forward): " + ("; ".join(f"{k} n {v['n']}: hit {v['hit_rate']:.2f} vs anchor {v['anchor_rate']:.2f}, "
                                                f"theses {v['theses']} ({v['why']})" for k, v in st["calls"].items())
                                     or "none scored yet")]
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
def _same(a, b, tol: float) -> bool:
    """Equal, with numbers within tol (the stored ones are rounded to 1e-6)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y, tol) for x, y in zip(a, b))
    return a == b


def _timestamp_checker():
    import sys

    root = str(PKG_ROOT.parent / "kod-machine")
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from kod.timestamp import RFC3161Timestamper
    except ImportError:
        return None
    return RFC3161Timestamper()


def verify(path: Path | None = None, records: list[dict] | None = None, tol: float = VERIFY_TOL) -> list[str]:
    """The chain; one forecast per set; and every forecast reproduced, field by field, by retraining on exactly the
    ledger state it records (a learner that saw a later outcome, or a record edited afterwards, cannot pass), bound to
    a set sealed in that state, made before the set's cutoff, and externally timestamped before it where a token
    exists."""
    path = LEDGER if path is None else path
    if not path.exists():
        return []
    problems = [f"{path.name}: {p}" for p in paper.verify_chain(path)]
    proto, sha = protocol()
    if records is None:
        cat, spc = cr.cat_lines(), spec.spec_lines()
    lrecs = paper.ledger_lines(path)
    seen, ctxs, checker = set(), {}, None
    for i, f in enumerate(lrecs):
        if f.get("type") != RECORD:
            problems.append(f"{path.name}: unknown record type {f.get('type')!r}")
            continue
        sid = f["set_id"]
        if sid in seen:
            problems.append(f"{sid}: forecast twice")
        seen.add(sid)
        if f["protocol"]["sha256"] != sha:
            problems.append(f"{sid}: learner protocol sha256 differs from {PROTOCOL_JSON.relative_to(PKG_ROOT)}")
        if f["history"]["sha256"] != HISTORY_SHA256:
            problems.append(f"{sid}: warm start sha256 differs from the pinned one")
        inp = f.get("inputs") or {}
        if records is None:
            nc, ns = (inp.get("catalysts") or [None])[0], (inp.get("speculations") or [None])[0]
            ok = (isinstance(nc, int) and isinstance(ns, int) and nc <= len(cat) and ns <= len(spc)
                  and _head(cat[:nc]) == inp["catalysts"] and _head(spc[:ns]) == inp["speculations"])
            prefix = [as_set(r) for r in cat[:nc]] + [as_set(r) for r in spc[:ns]] if ok else None
        else:
            n = (inp.get("records") or [None])[0]
            ok = isinstance(n, int) and n <= len(records) and _head(records[:n]) == inp["records"]
            prefix = records[:n] if ok else None
        if prefix is None:
            problems.append(f"{sid}: the ledger state it records is not a state the registers passed through")
            continue
        s = next((r for r in prefix if r.get("type") == "CATALYST_SET" and r["set_id"] == sid), None)
        if s is None or s.get("record_hash") != f["set_record_hash"]:
            problems.append(f"{sid}: forecast binds no sealed set with that hash")
            continue
        if f["made_at"] >= s["entry_cutoff"]:
            problems.append(f"{sid}: forecast made at {f['made_at']}, after the set's cutoff {s['entry_cutoff']}")
        key = (json.dumps(inp, sort_keys=True), f["made_at"])
        if key not in ctxs:
            ctxs[key] = _context(prefix, lrecs[:i], f["made_at"])
        again = _record(s, f["made_at"], proto, sha, inp, ctxs[key])
        body = {k: v for k, v in f.items() if k not in ("record_hash", "prev_hash")}
        diff = [k for k in sorted(set(body) | set(again)) if not _same(body.get(k), again.get(k), tol)]
        if diff:
            problems.append(f"{sid}: does not reproduce from the ledger state it records (possible peeking or an "
                            f"edit): {', '.join(diff)}")
        tokens = [(a, paper.TOKENS / f"{f.get('record_hash')}.{a}.tsr") for a in ("freetsa", "sectigo")]
        for a, tok in tokens:
            if not tok.exists():
                continue
            checker = checker or _timestamp_checker()
            try:
                when = utc_stamp(checker.verify(a, tok.read_bytes(), f["record_hash"].encode())) if checker else None
            except Exception:  # noqa: BLE001 - paper.verify_all reports a token that does not verify
                continue
            if when and when >= s["entry_cutoff"]:
                problems.append(f"{sid}: {a} timestamp {when} is not before the set's cutoff {s['entry_cutoff']}")
            break
    return problems

"""ATTENTION_HISTORY_v1: one run of protocol.json. Computes the ATTN block for every event from the hashed r/wallstreetbets
day files, fits BASE and BASE + ATTN in each fold exactly as TA_HISTORY_v1 does, scores once, and writes
results/attention.csv.gz, results/RESULT.json and the trial result file. Refuses to run twice."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import learner3  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

_spec = importlib.util.spec_from_file_location("ta_run", ROOT / "research" / "TA_HISTORY_v1" / "run.py")
ta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ta)  # TA_HISTORY_v1's fit(), design() and auc(), imported, not copied

PROTO = json.loads((HERE / "protocol.json").read_text())
RES = HERE / "results"
TRIALS = ROOT / "research" / "QUANT_GRADE" / "trials"
WSB = ROOT / "data" / "raw" / "reddit" / "wsb"
BASE = list(learner3.FEATURES)
ATTN = ["wsb_pre5", "wsb_day", "wsb_surge", "wsb_any"]
BLOCKS = {"BASE": BASE, "ATTN": BASE + ATTN}
STATEMENTS = {"NEXT_DUMP10_1": "y_NEXT_DUMP10_1", "DUMP10_5": "y_DUMP10_5"}
B, SEED = 2000, 20261029
STOP = set(PROTO["matching"]["stoplist"])
CLOSE_UTC_HOUR = 20


def shouting(title: str) -> bool:
    letters = [c for c in title if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) > len(letters) / 2


def names(title: str, ticker: str) -> bool:
    """protocol.json "matching": whole token, case-sensitive, optional $; $ required for short tickers, the stoplist and
    shouting titles."""
    t = re.escape(ticker)
    if len(ticker) <= 2 or ticker in STOP or shouting(title):
        return re.search(rf"(?<![A-Za-z0-9])\${t}(?![A-Za-z0-9])", title) is not None
    return re.search(rf"(?<![A-Za-z0-9])\$?{t}(?![A-Za-z0-9])", title) is not None


def load_posts(manifest: dict) -> list[tuple[int, str]]:
    posts = []
    for d, h in sorted(manifest["days"].items()):
        p = WSB / f"{d}.jsonl.gz"
        if hashlib.sha256(p.read_bytes()).hexdigest() != h:
            raise RuntimeError(f"{p.name} differs from the manifest")
        with gzip.open(p, "rt", encoding="utf-8") as f:
            posts += [(r["t"], r["title"]) for r in map(json.loads, f)]
    return posts


def attention(ev: pd.DataFrame, posts: list[tuple[int, str]]) -> pd.DataFrame:
    """Counts per event from the posts naming its ticker; only posts before d 20:00 UTC are read."""
    want = set(ev["ticker"])
    token = re.compile(r"(?<![A-Za-z0-9])\$?([A-Z][A-Z0-9.]{0,5})(?![A-Za-z0-9])")
    by_ticker: dict[str, list[int]] = {}
    for t, title in posts:
        for cand in {m.group(1) for m in token.finditer(title)} & want:
            if names(title, cand):
                by_ticker.setdefault(cand, []).append(t)
    for k in by_ticker:
        by_ticker[k] = np.array(sorted(by_ticker[k]))
    rows = []
    for r in ev.itertuples(index=False):
        d = date.fromisoformat(r.session)
        day0 = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
        close = day0 + CLOSE_UTC_HOUR * 3600
        ts = by_ticker.get(r.ticker, np.array([], dtype=int))

        def count(a, b):
            return int(np.searchsorted(ts, b, "left") - np.searchsorted(ts, a, "left"))
        pre5, today, m30 = count(day0 - 5 * 86400, day0), count(day0, close), count(day0 - 30 * 86400, day0) / 30
        rows.append({"wsb_pre5": float(np.log1p(pre5)), "wsb_day": float(np.log1p(today)),
                     "wsb_surge": float(np.log((today + 1) / (m30 + 1))),
                     "wsb_any": float(count(day0 - 5 * 86400, close) > 0)})
    return pd.DataFrame(rows, index=ev.index)


def main() -> int:
    if (RES / "RESULT.json").exists():
        sys.exit("error: ATTENTION_HISTORY_v1 has been run; one look only")
    e = PROTO["events"]
    path = ROOT / e["file"]
    if sha256_file(path) != e["sha256"]:
        raise RuntimeError("event file hash differs from the protocol")
    manifest = json.loads((RES / "REDDIT_MANIFEST.json").read_text())
    ev = pd.read_csv(path, dtype={"ticker": str, "session": str}, keep_default_na=False, na_values=[""])
    posts = load_posts(manifest)
    att = attention(ev, posts)
    ev = pd.concat([ev, att], axis=1)
    ev[["ticker", "session", *ATTN]].to_csv(RES / "attention.csv.gz", index=False)
    yr = ev["session"].str[:4]
    result = {"protocol": PROTO["protocol_id"], "events": len(ev), "posts_read": len(posts),
              "coverage_any_by_year": {y: float(ev.loc[yr == y, "wsb_any"].mean()) for y in sorted(yr.unique())},
              "statements": {}}
    rng = np.random.default_rng(SEED)
    for stmt, col in STATEMENTS.items():
        res, folds = {"folds": {}}, {}
        for name, f in PROTO["folds"].items():
            if name == "note":
                continue
            g = ev[ev[col].notna()]
            tr = g[(g["session"] >= f["fit"][0]) & (g["session"] <= f["fit"][1])]
            te = g[(g["session"] >= f["score"][0]) & (g["session"] <= f["score"][1])]
            y_tr, y_te = tr[col].to_numpy(float), te[col].to_numpy(float)
            preds, coefs = {}, {}
            for blk, cols in {**BLOCKS, "ATTN_ALONE": ATTN}.items():
                Xa, Xb = ta.design(tr, te, cols)
                beta = ta.fit(Xa, y_tr)
                preds[blk] = 1 / (1 + np.exp(-(Xb @ beta)))
                coefs[blk] = dict(zip(cols, beta[1:].round(4).tolist()))
            weeks = pd.to_datetime(te["session"]).dt.strftime("%G-W%V").to_numpy()
            cl = pd.factorize(weeks)[0]
            members = [np.flatnonzero(cl == c) for c in range(cl.max() + 1)]
            folds[name] = (y_te, {b: preds[b] for b in BLOCKS}, members)
            res["folds"][name] = {"n_fit": len(tr), "n_score": len(te), "rate_score": float(y_te.mean()),
                                  "auc": {b: ta.auc(p, y_te)[0] for b, p in preds.items()},
                                  "brier": {b: float(np.mean((p - y_te) ** 2)) for b, p in preds.items()},
                                  "coefficients": {k: v for k, v in coefs["ATTN"].items() if k in ATTN},
                                  "coverage_any_score": float(te["wsb_any"].mean())}

        def pooled(sel=None):
            num = {b: 0.0 for b in BLOCKS}; den = {b: 0.0 for b in BLOCKS}; br = {b: 0.0 for b in BLOCKS}; nb = 0
            for name, (y, preds, members) in folds.items():
                idx = np.arange(len(y)) if sel is None else sel[name]
                for b, p in preds.items():
                    a, w = ta.auc(p[idx], y[idx])
                    if w:
                        num[b] += a * w; den[b] += w
                    br[b] += float(np.sum((p[idx] - y[idx]) ** 2))
                nb += len(idx)
            return {b: num[b] / den[b] for b in BLOCKS}, {b: br[b] / nb for b in BLOCKS}

        a0, b0 = pooled()
        boot = []
        for _ in range(B):
            sel = {name: np.concatenate([mem[c] for c in rng.integers(0, len(mem), len(mem))]) for name, (_, _, mem) in folds.items()}
            boot.append(pooled(sel)[0])
        d = np.array([x["ATTN"] - x["BASE"] for x in boot])
        res["pooled_auc"], res["pooled_brier"] = a0, b0
        res["delta"] = {"delta_auc": a0["ATTN"] - a0["BASE"], "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                        "p_one_sided": float((np.sum(d <= 0) + 1) / (B + 1)), "brier_gain_over_base": b0["BASE"] - b0["ATTN"]}
        result["statements"][stmt] = res
    ps = {st: result["statements"][st]["delta"]["p_one_sided"] for st in STATEMENTS}
    order, adj, run = sorted(ps, key=ps.get), {}, 0.0
    for i, st in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[st]))
        adj[st] = run
    result["decision"] = {f"ATTN on {st}": {"holm_p": adj[st], "brier_gain_over_base": result["statements"][st]["delta"]["brier_gain_over_base"],
                                            "verdict": "ADDS" if adj[st] <= 0.05 and result["statements"][st]["delta"]["brier_gain_over_base"] > 0 else "DOES NOT ADD"}
                          for st in STATEMENTS}
    (RES / "RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    trial = {"id": "ATTENTION_HISTORY_v1_result", "experiment": "ATTENTION_HISTORY_v1", "date": datetime.now(timezone.utc).date().isoformat(),
             "hypothesis": json.loads((TRIALS / "ATTENTION_HISTORY_v1.json").read_text())["hypothesis"],
             "one_sided_p": min(adj.values()), "p_source": "research/ATTENTION_HISTORY_v1/results/RESULT.json decision (Holm over two; week-cluster bootstrap)",
             "variants_searched": 2, "outcome": "; ".join(f"{k} {v['verdict']}" for k, v in result["decision"].items()),
             "counted": True, "registered": "2026-10-29", "note": "the result of the PENDING registration ATTENTION_HISTORY_v1.json: one trial"}
    (TRIALS / "ATTENTION_HISTORY_v1_result.json").write_text(json.dumps(trial, indent=1) + "\n")
    print(json.dumps(result["decision"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

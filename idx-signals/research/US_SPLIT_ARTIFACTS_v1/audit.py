"""US_SPLIT_ARTIFACTS_v1: classify every sealed US Speculation Register set by RULE.md (frozen 2026-11-10).

Usage (from this directory):
    python3 audit.py --input-root /path/to/checkout/idx-signals --calls-dir /path/to/LLM_ARM_v1 \
        --cache /path/to/scratch/cache --out results

Reads no outcome: the provider request ends before the next session, and the downstream map prints
record types and ids only. Raw provider and SEC responses stay in --cache (not committed: Yahoo terms);
their SHA-256 values are written to results/evidence_manifest.json.
SEC requests declare a contact from KOD_SEC_CONTACT (read from the environment, never written out).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from classify import CLASSES, classify, window_events

NY = ZoneInfo("America/New_York")
CHART = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={p1}&period2={p2}&interval=1d&events=splits"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (idx-signals research harness)", "Accept": "application/json"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(url: str, cache: Path) -> tuple[int, bytes, bool]:
    key = sha(url.encode())[:32]
    body_p, meta_p = cache / f"{key}.bin", cache / f"{key}.json"
    if body_p.exists() and meta_p.exists():
        return json.loads(meta_p.read_text())["status"], body_p.read_bytes(), True
    status, body = 0, b""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=HEADERS), timeout=30
            ) as r:
                status, body = r.status, r.read()
            break
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            status, body = 0, b""
        time.sleep(2 * 2**attempt)
    cache.mkdir(parents=True, exist_ok=True)
    body_p.write_bytes(body)
    meta_p.write_text(
        json.dumps({"url": url, "status": status, "at": datetime.now(timezone.utc).isoformat()})
    )
    time.sleep(0.4)
    return status, body, False


def ny_day(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).astimezone(NY).date().isoformat()


def provider_view(body: bytes, signal_day: str) -> dict:
    """Splits and the two closes the rule needs. Bars after signal_day are never requested; any present
    are ignored."""
    res = json.loads(body)["chart"]["result"][0]
    stamps = res.get("timestamp") or []
    closes = ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    bars = [
        (ny_day(t), c) for t, c in zip(stamps, closes) if c is not None and ny_day(t) <= signal_day
    ]
    events = [
        {
            "effective_session": ny_day(int(e["date"])),
            "numerator": float(e["numerator"]),
            "denominator": float(e["denominator"]),
            "provider_ratio": e.get("splitRatio"),
        }
        for e in ((res.get("events") or {}).get("splits") or {}).values()
    ]
    sig = [c for d, c in bars if d == signal_day]
    prev = [(d, c) for d, c in bars if d < signal_day]
    return {
        "events": sorted(events, key=lambda e: e["effective_session"]),
        "signal_close": sig[-1] if sig else None,
        "prev_day": prev[-1][0] if prev else None,
        "prev_close": prev[-1][1] if prev else None,
    }


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", required=True)
    ap.add_argument("--calls-dir", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--no-sec", action="store_true")
    a = ap.parse_args()
    root, out, cache = Path(a.input_root), Path(a.out), Path(a.cache)
    out.mkdir(parents=True, exist_ok=True)

    spec_p = root / "paper/speculations.jsonl"
    recs = load_jsonl(spec_p)
    sets = [r for r in recs if r.get("market") == "US" and "decision" in r]
    inputs = {
        "speculations.jsonl": {"sha256": sha(spec_p.read_bytes()), "lines": len(recs)},
    }

    # SEC verifier from the repository (us-actions-v2), cache in scratch
    sec = None
    if not a.no_sec and os.environ.get("KOD_SEC_CONTACT"):
        sys.path.insert(0, str(root))
        from idxsig import us_actions

        client = us_actions.SecClient(
            user_agent=f"KOD research harness {os.environ['KOD_SEC_CONTACT']}",
            out_dir=cache / "sec",
        )
        sec = (us_actions, client, us_actions.cik_map(client))

    rows, evidence = [], []
    for s in sets:
        t, day = s["ticker"], s["signal_session"]
        d0 = date.fromisoformat(day)
        p1 = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp()) - 20 * 86400
        p2 = (
            int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp())
            + 86400
            + 5 * 3600
        )
        url = CHART.format(symbol=t.replace(".", "-"), p1=p1, p2=p2)
        status, body, cached = fetch(url, cache / "yahoo")
        evidence.append(
            {"set_id": s["set_id"], "url": url, "http_status": status, "sha256": sha(body)}
        )
        sig = s["signal"]
        row = {
            "set_id": s["set_id"],
            "ticker": t,
            "signal_session": day,
            "recorded_previous": sig.get("previous"),
            "recorded_close": sig.get("close"),
            "recorded_ret1": round(sig.get("ret1"), 4),
            "recorded_volr": round(sig.get("volr"), 3),
            "fetch_status": status,
        }
        view, ok = None, status == 200
        if ok:
            try:
                view = provider_view(body, day)
            except (KeyError, IndexError, TypeError, ValueError):
                ok = False
        adj, win, statuses = None, [], []
        if ok and view["signal_close"] and view["prev_close"]:
            adj = view["signal_close"] / view["prev_close"] - 1
            win = window_events(view["events"], view["prev_day"], day)
            for ev in win:
                st = "NOT_CHECKED"
                if sec is not None:
                    us_actions, client, ciks = sec
                    kind = us_actions.classify_ratio(ev["numerator"], ev["denominator"])
                    v = us_actions.verify_event(
                        client,
                        ciks,
                        t,
                        ev["effective_session"],
                        ev["numerator"],
                        ev["denominator"],
                        kind,
                    )
                    st = v["status"]
                    ev["sec_evidence"] = [
                        {k: x[k] for k in ("accession", "form", "file_date", "url", "finding")}
                        for x in v.get("evidence", [])
                    ]
                statuses.append(st)
                ev["sec_status"] = st
        cls = classify(win, adj, statuses, ok)
        recorded_ratio = sig["close"] / sig["previous"] if sig.get("previous") else None
        row.update(
            {
                "prev_bar": view["prev_day"] if view else None,
                "adj_ret1": None if adj is None else round(adj, 4),
                "units_ratio": None
                if adj is None or recorded_ratio is None
                else round(recorded_ratio / (1 + adj), 3),
                "window_splits": ";".join(
                    f"{e['effective_session']} {e['provider_ratio']} SEC={e['sec_status']}"
                    for e in win
                ),
                "class": cls,
            }
        )
        row["_win"] = win
        rows.append(row)
        print(
            f"{day} {t:6s} rec {row['recorded_ret1']:+9.2%} adj "
            f"{'   n/a' if adj is None else f'{adj:+8.2%}'}  {cls}  {row['window_splits']}",
            flush=True,
        )

    # ---- downstream map (ids and record types only)
    flagged = {r["set_id"]: r for r in rows if r["class"].startswith("ARTIFACT")}
    files = {
        "ledger": root / "paper/ledger.jsonl",
        "speculations": spec_p,
        "paper_book": root / "paper/paper_book.jsonl",
        "paper_account": root / "paper/paper_account.jsonl",
        "learner_v3": root / "paper/learner_v3.jsonl",
        "learner_v2": root / "paper/learner_v2.jsonl",
        "catalysts": root / "paper/catalysts.jsonl",
    }
    for f in sorted(Path(a.calls_dir).glob("calls*.jsonl")):
        files[f"llm_arm/{f.name}"] = f
    for k, p in files.items():
        inputs.setdefault(k, {"sha256": sha(p.read_bytes()), "path": str(p.name)})
    downstream = {sid: {} for sid in flagged}
    for name, p in files.items():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            for sid in flagged:
                dec = sid.removeprefix("SPEC-")
                if f'"{sid}"' in line or f'"{dec}"' in line:
                    r = json.loads(line)
                    label = (
                        r.get("type") or r.get("kind") or ("CALL" if "call_id" in r else "RECORD")
                    )
                    if r.get("window"):
                        label += f" {r['window']} {r.get('status', '')}".rstrip()
                    if r.get("type") == "BOOK_PLAN":
                        label += f" {r.get('verdict')}"
                    downstream[sid].setdefault(name, []).append(label)

    # ---- unresolvable resolutions: later splits? (events only)
    unres = []
    now = int(time.time())
    for r in recs:
        if (
            r.get("market") == "US"
            and r.get("type") == "RESOLUTION"
            and r.get("status") != "RESOLVED"
        ):
            d0 = date.fromisoformat(r["signal_session"])
            p1 = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp())
            url = CHART.format(symbol=r["ticker"].replace(".", "-"), p1=p1, p2=now)
            status, body, _ = fetch(url, cache / "yahoo_events")
            evs = []
            if status == 200:
                try:
                    res = json.loads(body)["chart"]["result"][0]
                    evs = sorted(
                        f"{ny_day(int(e['date']))} {e.get('splitRatio')}"
                        for e in ((res.get("events") or {}).get("splits") or {}).values()
                        if ny_day(int(e["date"])) > r["signal_session"]
                    )
                except (KeyError, IndexError, TypeError, ValueError):
                    status = -1
            del body  # price arrays discarded unread
            unres.append(
                {
                    "set_id": r["set_id"],
                    "window": r["window"],
                    "status": r["status"],
                    "fetch_status": status,
                    "splits_after_signal": evs,
                }
            )

    # ---- write
    cols = [c for c in rows[0] if not c.startswith("_")]
    with open(out / "sets.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["signal_session"], x["ticker"])):
            w.writerow({c: r[c] for c in cols})
    counts = {c: sum(1 for r in rows if r["class"] == c) for c in CLASSES}
    summary = {
        "study": "US_SPLIT_ARTIFACTS_v1",
        "rule_sha256": sha((Path(__file__).parent / "RULE.md").read_bytes()),
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "population": len(rows),
        "counts": counts,
        "stop_rule": "CLOSED_AS_ISOLATED" if counts["ARTIFACT_CONFIRMED"] < 3 else "CONTINUE",
        "sec_checked": sec is not None,
        "artifacts": {
            sid: {
                "ticker": flagged[sid]["ticker"],
                "signal_session": flagged[sid]["signal_session"],
                "class": flagged[sid]["class"],
                "recorded_ret1": flagged[sid]["recorded_ret1"],
                "adj_ret1": flagged[sid]["adj_ret1"],
                "window_splits": flagged[sid]["_win"],
                "downstream": {k: sorted(v) for k, v in downstream[sid].items()},
            }
            for sid in sorted(flagged)
        },
        "unexplained_gap": [
            {k: r[k] for k in ("set_id", "recorded_ret1", "adj_ret1", "units_ratio")}
            for r in rows
            if r["class"] == "UNEXPLAINED_GAP"
        ],
        "unknown": [
            {k: r[k] for k in ("set_id", "fetch_status")} for r in rows if r["class"] == "UNKNOWN"
        ],
        "unresolvable_resolutions": unres,
        "inputs": inputs,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=False) + "\n")
    (out / "evidence_manifest.json").write_text(json.dumps(evidence, indent=1) + "\n")
    print(json.dumps(counts), summary["stop_rule"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

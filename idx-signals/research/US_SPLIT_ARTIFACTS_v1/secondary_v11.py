"""ADDENDUM_1 secondary classification (v1.1) from the v1 run's cached provider responses.

Usage (from this directory, after audit.py):
    python3 secondary_v11.py --input-root .../idx-signals --calls-dir .../LLM_ARM_v1 --cache .../cache
Reads only events and the recorded signal fields; prints record types and ids, never an outcome.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def v11(r: float, events: list[dict], signal_day: str) -> dict | None:
    lo = (date.fromisoformat(signal_day) - timedelta(days=10)).isoformat()
    for e in sorted(events, key=lambda x: x["effective_session"], reverse=True):
        if not lo < e["effective_session"] <= signal_day:
            continue
        k = e["denominator"] / e["numerator"]
        if r > 0 and r / k - 1 < 0.30 and abs(math.log(r / k)) < abs(math.log(r)):
            return {**e, "k": k, "split_adjusted_ret1": round(r / k - 1, 4)}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", required=True)
    ap.add_argument("--calls-dir", required=True)
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    root, cache = Path(a.input_root), Path(a.cache)
    urls = {e["set_id"]: e["url"] for e in json.load(open("results/evidence_manifest.json"))}
    sets = {
        r["set_id"]: r
        for r in map(json.loads, (root / "paper/speculations.jsonl").read_text().splitlines())
        if r.get("market") == "US" and "decision" in r
    }
    v1 = {r["set_id"]: r for r in csv.DictReader(open("results/sets.csv"))}
    sec = {}
    for r in v1.values():  # SEC tiers found by the v1 run, per event
        for part in filter(None, r["window_splits"].split(";")):
            day, ratio, st = part.split(" ")
            sec[(r["set_id"], day)] = st.removeprefix("SEC=")
    out = []
    for sid, s in sets.items():
        key = hashlib.sha256(urls[sid].encode()).hexdigest()[:32]
        body = json.loads((cache / "yahoo" / f"{key}.bin").read_bytes() or b"{}")
        res = ((body.get("chart") or {}).get("result") or [None])[0] or {}
        events = [
            {
                "effective_session": datetime.fromtimestamp(int(e["date"]), timezone.utc)
                .astimezone(NY)
                .date()
                .isoformat(),
                "numerator": float(e["numerator"]),
                "denominator": float(e["denominator"]),
                "provider_ratio": e.get("splitRatio"),
            }
            for e in ((res.get("events") or {}).get("splits") or {}).values()
        ]
        sig = s["signal"]
        r = sig["close"] / sig["previous"]
        hit = v11(r, events, s["signal_session"])
        cls = "ARTIFACT_V11" if hit else ("INDETERMINATE" if r >= 4.0 else "NOT_FLAGGED")
        out.append(
            {
                "set_id": sid,
                "ticker": s["ticker"],
                "signal_session": s["signal_session"],
                "recorded_ret1": round(r - 1, 4),
                "v1_class": v1[sid]["class"],
                "v11_class": cls,
                "split": f"{hit['effective_session']} {hit['provider_ratio']}" if hit else "",
                "split_adjusted_ret1": hit["split_adjusted_ret1"] if hit else "",
                "sec_tier": sec.get((sid, hit["effective_session"]), "NOT_IN_V1_WINDOW")
                if hit
                else "",
            }
        )

    flagged = {o["set_id"] for o in out if o["v11_class"] == "ARTIFACT_V11"}
    files = {
        k: root / f"paper/{k}.jsonl"
        for k in (
            "ledger",
            "speculations",
            "paper_book",
            "paper_account",
            "learner_v3",
            "catalysts",
        )
    }
    for f in sorted(Path(a.calls_dir).glob("calls*.jsonl")):
        files[f"llm_arm/{f.name}"] = f
    down = {sid: {} for sid in flagged}
    for name, p in files.items():
        for line in p.read_text().splitlines():
            for sid in flagged:
                if f'"{sid}"' in line or f'"{sid.removeprefix("SPEC-")}"' in line:
                    rec = json.loads(line)
                    lab = rec.get("type") or (
                        "CALL " + rec["call"] if "call_id" in rec else "RECORD"
                    )
                    if rec.get("window"):
                        lab += f" {rec['window']} {rec.get('status', '')}"
                    if rec.get("type") == "BOOK_PLAN":
                        lab += f" {rec.get('verdict')}"
                    down[sid].setdefault(name, []).append(lab.strip())
    for o in out:
        o["downstream"] = json.dumps(down.get(o["set_id"], {}), sort_keys=True)
    cols = list(out[0])
    with open("results/sets_v11.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for o in sorted(out, key=lambda x: (x["signal_session"], x["ticker"])):
            w.writerow(o)
    counts = {}
    for o in out:
        counts[o["v11_class"]] = counts.get(o["v11_class"], 0) + 1
    print(json.dumps(counts))
    for o in sorted(out, key=lambda x: (x["signal_session"], x["ticker"])):
        if o["v11_class"] != "NOT_FLAGGED":
            print(
                o["signal_session"],
                o["ticker"],
                o["v11_class"],
                o["recorded_ret1"],
                o["split"],
                o["split_adjusted_ret1"],
                o["sec_tier"],
                o["downstream"],
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""ATTENTION_HISTORY_v1 build: download r/wallstreetbets post times and titles, one UTC day at a time, from the Arctic Shift
archive (protocol.json "reddit"). Resumable: a finished day is a gzipped file under data/raw/reddit/wsb/ and is never
fetched again. Reads no price and no outcome. `python3 build.py` downloads; `python3 build.py --manifest` hashes the
finished days into results/REDDIT_MANIFEST.json (run.py refuses to run without it)."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "raw" / "reddit" / "wsb"
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
UA = {"User-Agent": "KOD-Machine-research/1.0 (paper research, one request at a time)"}
FIRST, LAST = date(2019, 11, 1), date(2023, 12, 29)
PAUSE = 0.4


def get(params: dict) -> list[dict]:
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                body = json.load(r)
            if body.get("error"):
                raise RuntimeError(body["error"])
            return body.get("data") or []
        except Exception as e:  # rate limit, timeout or a transient error: back off and retry
            wait = min(300, 5 * 2 ** k)
            print(f"  retry {k + 1} in {wait}s: {str(e)[:80]}", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}")


def day(d: date) -> Path:
    path = OUT / f"{d.isoformat()}.jsonl.gz"
    if path.exists():
        return path
    t0 = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    t1 = t0 + 86400
    seen, rows, after = set(), [], t0 - 1
    while True:
        page = get({"subreddit": "wallstreetbets", "after": after, "before": t1, "sort": "asc", "limit": 100,
                    "fields": "id,created_utc,title"})
        time.sleep(PAUSE)
        new = [p for p in page if p.get("id") not in seen]
        for p in new:
            seen.add(p["id"])
            rows.append({"id": p["id"], "t": int(p["created_utc"]), "title": p.get("title") or ""})
        if len(page) < 100:
            break
        last = max(int(p["created_utc"]) for p in page)
        after = last if new else last + 1  # a full page inside one second: step past it
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda r: (r["t"], r["id"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.rename(path)
    return path


def manifest() -> int:
    days, missing = {}, []
    d = FIRST
    while d <= LAST:
        p = OUT / f"{d.isoformat()}.jsonl.gz"
        if p.exists():
            days[d.isoformat()] = hashlib.sha256(p.read_bytes()).hexdigest()
        else:
            missing.append(d.isoformat())
        d += timedelta(days=1)
    if missing:
        sys.exit(f"error: {len(missing)} days not downloaded yet (first {missing[0]})")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "REDDIT_MANIFEST.json").write_text(json.dumps(
        {"source": API, "subreddit": "wallstreetbets", "first": FIRST.isoformat(), "last": LAST.isoformat(),
         "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "days": days}, indent=0) + "\n")
    print(f"manifest: {len(days)} days")
    return 0


def main() -> int:
    if "--manifest" in sys.argv:
        return manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    d = FIRST
    while d <= LAST:
        p = OUT / f"{d.isoformat()}.jsonl.gz"
        fresh = not p.exists()
        day(d)
        if fresh:
            n = sum(1 for _ in gzip.open(p, "rt"))
            print(f"{d} {n} posts", flush=True)
        d += timedelta(days=1)
    print("BUILD DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

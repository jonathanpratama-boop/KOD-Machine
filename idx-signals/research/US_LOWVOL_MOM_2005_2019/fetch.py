"""Pull Yahoo daily bars 2004-01-01..2019-12-31 for the tickers of the 2026-10-08 US pull (PROTOCOL.md).
Raw response bytes are hashed; files are stored gzipped. Resumable. Usage (from idx-signals/):
    python3 research/US_LOWVOL_MOM_2005_2019/fetch.py
"""
import gzip
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import rel, sha256_bytes, utc_stamp  # noqa: E402
from idxsig.sources import yahoo  # noqa: E402

LIST = ROOT / "data" / "manifests" / "yahoo_us-20261008T001812Z.jsonl"
OUT = ROOT / "data" / "raw" / "yahoo_us_2005"
P1 = int(datetime(2004, 1, 1, tzinfo=timezone.utc).timestamp())
P2 = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp())


def main() -> int:
    tickers = sorted({json.loads(l)["ticker"] for l in LIST.read_text().splitlines() if l.strip().startswith("{")})
    OUT.mkdir(parents=True, exist_ok=True)
    progress = OUT / "_progress.jsonl"
    done = {json.loads(l)["ticker"] for l in progress.read_text().splitlines()} if progress.exists() else set()
    todo = [t for t in tickers if t not in done]
    print(f"{len(tickers)} tickers, {len(todo)} to fetch", flush=True)
    lock, count = threading.Lock(), [len(done)]
    prog = progress.open("a")

    def one(t):
        status, body, url = yahoo.fetch_one(t, P2, p1=P1, suffix="")
        if status == 200:
            (OUT / f"{t}.json.gz").write_bytes(gzip.compress(body))
        rec = {"ticker": t, "source_url": url, "http_status": status, "bytes": len(body),
               "sha256": sha256_bytes(body), "downloaded_at": utc_stamp()}
        with lock:
            prog.write(json.dumps(rec, sort_keys=True) + "\n")
            prog.flush()
            count[0] += 1
            if count[0] % 250 == 0:
                print(f"{count[0]}/{len(tickers)} {t} {status}", flush=True)
        time.sleep(0.1)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(one, todo))
    prog.close()
    recs = [json.loads(l) for l in progress.read_text().splitlines()]
    man = ROOT / "data" / "manifests" / f"yahoo_us_2005-{utc_stamp().replace(':', '').replace('-', '')}.jsonl"
    man.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n")
    print(f"done: {sum(r['http_status'] == 200 for r in recs)} ok, {sum(r['http_status'] == 404 for r in recs)} not found "
          f"-> {rel(man)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

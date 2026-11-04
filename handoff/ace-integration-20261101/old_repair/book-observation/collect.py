"""Bounded public depth observations only; no order, account or reference API."""
import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "kod-crypto-repair/idx-signals"))
from idxsig.microstructure import book_metrics

PAIRS = ("BTCUSDT", "ETHUSDT", "BEAMXUSDT")
SETS, INTERVAL, TIMEOUT = 60, 120, 20
ENDPOINT = "https://data-api.binance.vision/api/v3/depth"
MAX_GETS = SETS * len(PAIRS)


def utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def save(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def metrics(raw):
    body = json.loads(raw)
    for name, ascending in (("asks", True), ("bids", False)):
        rows = body[name]
        if not rows or len(rows) > 100:
            raise ValueError("empty or unexpected depth")
        previous = None
        for row in rows:
            if not isinstance(row, list) or len(row) != 2:
                raise ValueError("invalid level")
            p, q = map(float, row)
            if not math.isfinite(p) or not math.isfinite(q) or p <= 0 or q < 0:
                raise ValueError("nonfinite or negative level")
            if previous is not None and (p <= previous if ascending else p >= previous):
                raise ValueError("duplicate or unsorted levels")
            previous = p
    out = book_metrics(body, sizes=(100., 1000.))
    if out is None or out["best_bid"] >= out["best_ask"]:
        raise ValueError("missing usable side or crossed/locked book")
    out.update(last_update_id=body.get("lastUpdateId"),
               interpretation="Displayed-book sweep only; not eligibility, guaranteed execution, order, signal or profit.",
               fee_assumption_per_side=0.001,
               sweep_convention="BUY spends target quote amount; SELL quantity equals target quote amount divided by observed mid. Partial VWAP describes only displayed fill and can understate full-order cost.")
    return out


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "KOD-public-book-observation/1"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=TIMEOUT) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def retry_after(headers, now):
    raw = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    if raw is None:
        return None
    try:
        seconds = int(raw)
        return now + max(0, seconds)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                return None
            return max(now, parsed.timestamp())
        except (TypeError, ValueError, OverflowError):
            return None


def run(out, *, clock=time.time, sleep=time.sleep, getter=fetch, start=None):
    out.mkdir(parents=True, exist_ok=False)
    (out / "raw").mkdir()
    start = clock() if start is None else start
    deadline = start + SETS * INTERVAL
    source = Path(__file__).read_bytes()
    protocol = {
        "purpose": "execution-assumption observation only; no signal, eligibility check, strategy training or P&L experiment",
        "start_utc": utc(start), "deadline_utc": utc(deadline), "sample_sets": SETS,
        "interval_seconds": INTERVAL, "pairs": list(PAIRS), "max_gets": MAX_GETS,
        "request_timeout_seconds": TIMEOUT, "depth_levels": 100, "endpoint": ENDPOINT,
        "target_notionals_usdt": [100, 1000], "hypothetical_fee_per_side": 0.001,
        "collector_sha256": hashlib.sha256(source).hexdigest(),
        "microstructure_sha256": hashlib.sha256((HERE.parent / 'kod-crypto-repair/idx-signals/idxsig/microstructure.py').read_bytes()).hexdigest(),
        "rules": "Fixed slots, no backfill, no retries or host switches. 429 honors Retry-After; absent/invalid header stops. Access denial stops. Missing samples explicitly recorded. No api.binance.com or referencePrice access."
    }
    save(out / "protocol.json", protocol)
    requests, successes, stopped, cooldown = 0, 0, None, 0
    rows = []

    def record(row):
        rows.append(row)
        with (out / "observations.jsonl").open("a") as handle:
            handle.write(json.dumps(row, allow_nan=False) + "\n")

    for slot in range(SETS):
        due = start + slot * INTERVAL
        if not stopped and clock() < due:
            sleep(due - clock())
        for pair in PAIRS:
            row = {"slot": slot, "symbol": pair, "scheduled_utc": utc(due)}
            now = clock()
            why = stopped or ("DEADLINE" if now >= deadline else
                              "RATE_LIMIT_COOLDOWN" if now < cooldown else
                              "MISSED_SLOT" if now >= due + INTERVAL else None)
            if why:
                record({**row, "status": "MISSING", "reason": why})
                continue
            if requests >= MAX_GETS:
                stopped = "REQUEST_BUDGET"
                record({**row, "status": "MISSING", "reason": stopped})
                continue
            url = f"{ENDPOINT}?symbol={pair}&limit=100"
            requests += 1
            row.update(url=url, request_start_utc=utc(now), request_number=requests)
            # Record admission before sending; interrupted calls remain auditable.
            with (out / "attempts.jsonl").open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            try:
                code, headers, raw = getter(url)
                received = clock()
                raw_path = f"raw/{slot:03d}-{pair}.json"
                (out / raw_path).write_bytes(raw)
                row.update(http_status=code, received_utc=utc(received), raw_path=raw_path,
                           raw_sha256=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw),
                           retry_after=next((v for k, v in headers.items() if k.lower() == "retry-after"), None))
                if code == 200:
                    row.update(status="OBSERVED", metrics=metrics(raw))
                    successes += 1
                elif code == 429:
                    cooldown = retry_after(headers, received)
                    if cooldown is None:
                        stopped, cooldown = "RATE_LIMIT_NO_VALID_RETRY_AFTER", float("inf")
                    else:
                        row["cooldown_until_utc"] = utc(cooldown)
                    row.update(status="FAILED", reason="RATE_LIMIT")
                else:
                    row.update(status="FAILED", reason=f"HTTP_{code}")
                    if 300 <= code < 500:
                        stopped = f"SOURCE_UNAVAILABLE_OR_ACCESS_DENIED_HTTP_{code}"
            except Exception as exc:
                row.update(status="FAILED", received_utc=utc(clock()), reason=f"{type(exc).__name__}: {exc}"[:300])
                if isinstance(exc, PermissionError) or isinstance(getattr(exc, "reason", None), PermissionError):
                    stopped = "NETWORK_PERMISSION_DENIED"
            record(row)
        save(out / "status.json", {"state": "STOPPED" if stopped else "RUNNING", "completed_sets": slot + 1,
                                  "requests": requests, "successful_books": successes, "deadline_utc": utc(deadline),
                                  "stop_reason": stopped, "last_update_utc": utc(clock())})
    summary = {"state": "STOPPED" if stopped else "COMPLETE", "requests": requests, "successful_books": successes,
               "scheduled_samples": SETS * len(PAIRS), "failed": sum(r["status"] == "FAILED" for r in rows),
               "missing": sum(r["status"] == "MISSING" for r in rows), "stop_reason": stopped,
               "finished_utc": utc(clock()), "deadline_utc": utc(deadline),
               "meaning": "Public displayed-book observations only, no eligibility, orders, guaranteed fills or profit claims."}
    save(out / "status.json", summary)
    save(out / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.out), indent=2), flush=True)

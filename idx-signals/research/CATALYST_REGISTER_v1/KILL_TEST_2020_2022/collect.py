"""KILL_TEST_2020_2022 collection (PROTOCOL.md 'Running it'): SEC only, no price. Writes events.csv.gz (one row per
original SC 13D: header fields, SEC tickers, the rule inputs, the collection-stage drop reason) and COLLECT.json (every
request as url, HTTP status, sha256; the funnel counts). Responses are parsed in memory and never written to disk.

The declared contact is read from KOD_SEC_CONTACT (passed inline on the command line) and never written anywhere.
Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/collect.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kt_lib as kt  # noqa: E402
from idxsig import catalyst as e9  # noqa: E402
from idxsig import catalysts as cr  # noqa: E402
from idxsig import us_actions  # noqa: E402

PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
CHUNKS_FROM = kt.OPFORMS_FROM  # chunk files overlapping the oldest date a rule reads (550 days before 2020-04-01)
EVENTS, LOG = HERE / "events.csv.gz", HERE / "COLLECT.json"
RETRY = (429, 500, 502, 503, 504)
WORKERS = 4  # concurrent requests; the shared rate limit still allows one start per 0.21 s


class Client:
    """us_actions.SecClient's User-Agent, rate limit (one request start per 0.21 s) and retry rules, without its
    disk cache: every response is hashed and logged, and only its parsed content is kept. Thread-safe."""

    def __init__(self, user_agent: str, min_interval: float = 0.21):
        self.user_agent, self.min_interval, self._last, self.log = user_agent, min_interval, 0.0, []
        self._lock = threading.Lock()

    def _wait(self) -> None:
        with self._lock:  # one request start per min_interval across all threads
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def _open(self, url: str, consume):
        status, out, digest, size = 0, None, hashlib.sha256(b"").hexdigest(), 0
        for attempt in range(5):
            self._wait()
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "identity"})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    status = resp.status
                    out, digest, size = consume(resp)
                break
            except urllib.error.HTTPError as exc:
                status, body = exc.code, exc.read()
                out, digest, size = None, hashlib.sha256(body).hexdigest(), len(body)
                if exc.code not in RETRY:
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                status, out = 0, None
            time.sleep(2 * 2 ** attempt)
        with self._lock:
            self.log.append([url, status, digest, size])
        return status, out

    def get(self, url: str) -> tuple[int, bytes]:
        def whole(resp):
            body = resp.read()
            return body, hashlib.sha256(body).hexdigest(), len(body)

        status, body = self._open(url, whole)
        return status, (body or b"") if status == 200 else b""

    def lines(self, url: str, keep) -> tuple[int, list[str]]:
        """Stream a text file, hashing every byte and keeping only the lines `keep` accepts."""
        def stream(resp):
            h, kept, size = hashlib.sha256(), [], 0
            for raw in resp:
                h.update(raw)
                size += len(raw)
                line = raw.decode("latin-1")
                if keep(line):
                    kept.append(line)
            return kept, h.hexdigest(), size

        status, kept = self._open(url, stream)
        return status, (kept or []) if status == 200 else []


def subject_inputs(client: Client, cik: int) -> dict:
    """The subject's submissions (recent block plus the chunk files overlapping CHUNKS_FROM..EVIDENCE_TO) reduced to
    the rule inputs, and its dei:EntityCommonStockSharesOutstanding facts."""
    st, main = client.get(cr.SUBMISSIONS_URL.format(cik=cik))
    out = {"submissions_status": st, "dilution": "", "opforms": "", "shares": "", "concept_status": None}
    if st == 200:
        try:
            names = e9.chunk_names(main, CHUNKS_FROM, kt.EVIDENCE_TO)
            chunks = []
            for n in names:
                cst, body = client.get(f"https://data.sec.gov/submissions/{n}")
                if cst != 200:
                    out["submissions_status"] = f"chunk {n}: HTTP {cst}"
                    break
                chunks.append(body)
            else:
                out["dilution"], out["opforms"] = kt.encode_filings(e9.parse_submissions(main, chunks))
        except (ValueError, KeyError) as exc:
            out["submissions_status"] = f"unparseable: {type(exc).__name__}"
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityCommonStockSharesOutstanding.json"
    cst, body = client.get(url)
    out["concept_status"] = cst
    if cst == 200:
        try:
            facts = json.loads(body).get("units", {}).get("shares", [])
            out["shares"] = kt.encode_shares([{"end": f["end"], "val": float(f["val"]), "filed": f.get("filed", "")}
                                              for f in facts if f.get("val")])
        except (ValueError, KeyError) as exc:
            out["concept_status"] = f"unparseable: {type(exc).__name__}"
    return out


def dump(out: dict) -> str:
    """COLLECT.json with one request per line."""
    log = out["requests"]["log"]
    head = json.dumps({**out, "requests": {**out["requests"], "log": "@LOG@"}}, indent=1)
    rows = ",\n".join(json.dumps(r) for r in log)
    return head.replace('"@LOG@"', "[\n" + rows + "\n  ]") + "\n"


def main() -> int:
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT (the declared SEC contact) on the command line")
    if EVENTS.exists() or LOG.exists():
        sys.exit("error: events.csv.gz or COLLECT.json exists; the collection runs once")
    ua = f"KOD-Machine research {contact}"
    if ua == us_actions.DEFAULT_USER_AGENT:
        sys.exit("error: a declared contact is required")
    return collect(Client(ua), EVENTS, LOG)


def collect(client, events_path: Path, log_path: Path) -> int:
    """The whole collection with a given client (Client, or a test's fake with get, lines and log)."""
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    say = lambda *a: print(*a, file=sys.stderr, flush=True)  # noqa: E731

    # 1. the quarterly indexes, streamed, keeping only SC 13D rows
    rows, quarters = [], {}
    for q in PROTOCOL["filings"]["quarters"]:
        st, lines = client.lines(kt.quarter_url(q), kt.is_13d_line)
        parsed = [kt.parse_form_line(x) for x in lines]
        quarters[q] = {"http_status": st, "sc13d_rows": len(lines), "originals": len(kt.originals(parsed))}
        rows += parsed
        say(q, quarters[q])
        if st != 200 or not lines:
            sys.exit(f"error: {kt.quarter_url(q)}: HTTP {st}, {len(lines)} SC 13D rows; the list would be incomplete, nothing written")
    filings = kt.originals(rows)
    say("original SC 13D filings:", len(filings))

    # 2. each filing's header
    def one_header(item):
        i, f = item
        st, body = client.get(kt.header_url(f["index_cik"], f["accession"]))
        if i % 500 == 0:
            say(f"headers {i}/{len(filings)}")
        return {**f, "header_status": st, **kt.parse_header(body if st == 200 else None)}

    with ThreadPoolExecutor(WORKERS) as pool:
        recs = list(pool.map(one_header, enumerate(filings)))
    ev = pd.DataFrame(recs)
    ev["index_ciks"] = ev["index_ciks"].map(lambda c: ";".join(str(x) for x in c))
    ev["filed_by"] = ev["filed_by"].map(lambda xs: ";".join(x.replace(";", ",") for x in xs))

    # 3. the SEC ticker map, once
    st, tm = client.get(cr.TICKERS_URL)
    if st != 200:
        sys.exit(f"error: company_tickers_exchange.json HTTP {st}; nothing written")
    by_cik, _ = cr.ticker_maps(tm)
    ev["tickers"] = ev["subject_cik"].map(lambda c: ";".join(by_cik.get(int(c), [])) if pd.notna(c) else "")

    # 4. the collection-stage funnel (the panel ticker test and the entry window are run.py's)
    has_header = ev["accepted"].notna() & ev["subject_cik"].notna()
    ev["repeat_of"] = kt.repeats(ev)
    drop = pd.Series("", index=ev.index, dtype=object)
    drop[~has_header] = "SKIP_NO_HEADER"
    drop[(drop == "") & (ev["date_filed"] < kt.SEED_ONLY_BEFORE)] = "SKIP_SEED_ONLY"
    drop[(drop == "") & (ev["tickers"] == "")] = "SKIP_NO_TICKER"
    drop[(drop == "") & (ev["repeat_of"] != "")] = "SKIP_REPEAT_90D"

    # 5. the subjects still in the funnel: submissions (and chunks) and the shares concept
    ciks = sorted({int(c) for c in ev.loc[drop == "", "subject_cik"]})
    say("subjects to read:", len(ciks))
    def one_subject(item):
        i, cik = item
        if i % 250 == 0:
            say(f"subjects {i}/{len(ciks)}")
        return cik, subject_inputs(client, cik)

    with ThreadPoolExecutor(WORKERS) as pool:
        inputs = dict(pool.map(one_subject, enumerate(ciks)))
    for col in ("submissions_status", "concept_status", "dilution", "opforms", "shares"):
        ev[col] = [inputs.get(int(c), {}).get(col) if pd.notna(c) else None for c in ev["subject_cik"]]
    day = ev["accepted"].map(lambda s: datetime.fromisoformat(s).astimezone(kt.NY).date().isoformat() if isinstance(s, str) else "")
    live = drop == ""
    ok = [kt.operating(d or "", o or "", dd) if lv else False
          for d, o, dd, lv in zip(ev["dilution"], ev["opforms"], day, live)]
    drop[live & ~pd.Series(ok, index=ev.index)] = "SKIP_NOT_OPERATING"
    ev["drop_reason"] = drop
    ev["subject_cik"] = ev["subject_cik"].astype("Int64")
    cols = ["accession", "date_filed", "index_cik", "index_ciks", "header_status", "accepted", "subject_cik", "subject_name",
            "filed_by", "tickers", "repeat_of", "submissions_status", "concept_status", "dilution", "opforms", "shares",
            "drop_reason"]
    with gzip.GzipFile(events_path, "wb", mtime=0) as fh:
        fh.write(ev[cols].to_csv(index=False).encode())

    scored_window = has_header & (ev["date_filed"] >= kt.SEED_ONLY_BEFORE)
    funnel = {"filings_original_sc13d": int(len(ev)),
              "seed_only_filed_before_2020_07_01": int((ev["date_filed"] < kt.SEED_ONLY_BEFORE).sum()),
              "originals_filed_from_2020_07_01": int((ev["date_filed"] >= kt.SEED_ONLY_BEFORE).sum()),
              "with_header": int(has_header.sum()),
              "in_window_with_header": int(scored_window.sum()),
              "in_window_with_sec_ticker": int((scored_window & (ev["tickers"] != "")).sum()),
              "repeats_dropped": int((drop == "SKIP_REPEAT_90D").sum()),
              "not_operating_dropped": int((drop == "SKIP_NOT_OPERATING").sum()),
              "operating_kept": int((drop == "").sum()),
              "drop_reasons": {k: int(v) for k, v in drop.value_counts().items()}}
    log = client.log
    failures = [r for r in log if r[1] != 200]
    out = {"protocol": {"id": PROTOCOL["protocol_id"], "sha256": cr.sha256_file(HERE / "protocol.json")},
           "started_at": started, "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "user_agent": "KOD-Machine research <declared contact, not recorded>", "reads_prices": False,
           "quarters": quarters, "ticker_map_sha256": hashlib.sha256(tm).hexdigest(), "subjects_read": len(ciks),
           "header_failures": int((ev["header_status"] != 200).sum()),
           "header_unparsed": int(((ev["header_status"] == 200) & ~has_header).sum()),
           "submissions_failures": int(sum(1 for v in inputs.values() if v["submissions_status"] != 200)),
           "concept_status": {str(k): int(v) for k, v in pd.Series([v["concept_status"] for v in inputs.values()]).value_counts().items()},
           "funnel": funnel, "events_sha256": cr.sha256_file(events_path),
           "requests": {"n": len(log), "non_200": len(failures), "fields": ["url", "http_status", "sha256", "bytes"], "log": log}}
    log_path.write_text(dump(out), encoding="utf-8")
    say(json.dumps({k: out[k] for k in ("quarters", "header_failures", "header_unparsed", "submissions_failures", "funnel")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

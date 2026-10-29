"""PATH_HISTORY_v1 collection: the free US data of block E_US, for the US event stocks only. Reads no outcome.

- EDGAR (the machine's SecClient, the declared contact from KOD_SEC_CONTACT, never written to a file): the ticker map,
  each event stock's submissions and the chunk files overlapping 2016-12..2023-12, kept to the forms block E_US reads;
  the XBRL frames of dei:EntityCommonStockSharesOutstanding, calendar 2019Q1..2023Q3.
- FINRA Reg SHO consolidated daily short-sale files for every US session of the panel, kept to the event stocks.

Outputs (committed): data/us_filings.csv.gz, data/us_shares.csv.gz, data/us_short.csv.gz, data/COLLECT.json (every
response's URL, status and sha256). Raw EDGAR bodies are cached under data/raw/path_history (not committed).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import catalyst as e9  # noqa: E402
from idxsig import catalysts as cr  # noqa: E402
from idxsig import global_panel  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "data"
RAW = ROOT / "data" / "raw" / "path_history"
PROTO = json.loads((HERE / "protocol.json").read_text())
FORMS = {"8-K", "8-K/A", "6-K", "6-K/A", "S-1", "S-1/A", "S-1MEF", "F-1", "F-1/A", "S-3", "F-3", "S-3ASR",
         "424B1", "424B3", "424B4", "424B5"}
SPAN = ("2016-12-01", "2023-12-31")
QUARTERS = [f"CY{y}Q{q}I" for y in range(2019, 2024) for q in range(1, 5)][:-1]  # 2019Q1..2023Q3
FINRA = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{day}.txt"


def us_events() -> tuple[set[str], list[str]]:
    d = PROTO["data"]["US"]
    df, meta = global_panel.load(ROOT / d["manifest"])
    assert meta["sha256"] == d["panel_sha256"]
    lo, hi = d["rows_read"]
    df = df[(df["date"] >= lo) & (df["date"] <= hi)]
    m = Market.from_panel(df, price_limits=False)
    f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
    flag = moonshot_g.family_flags(f)["G2_RET30"] & m.tradeable & (np.cumsum(m.present, axis=1) > 20)
    flag[:, -21:] = False
    tickers = {str(m.tickers[i]) for i in np.flatnonzero(flag.any(axis=1))}
    return tickers, [str(x) for x in m.dates.astype("datetime64[D]")]


def edgar(tickers: set[str], log=print) -> dict:
    client = cr.sec_client(RAW / "sec")
    st, body = client.get(cr.TICKERS_URL)
    if st != 200:
        raise RuntimeError(f"ticker map HTTP {st}")
    _, by_ticker = cr.ticker_maps(body)
    ciks = {t: by_ticker[t] for t in sorted(tickers) if t in by_ticker}
    log(f"EDGAR: {len(ciks)} of {len(tickers)} event stocks map to a CIK")

    def one(item):
        t, cik = item
        st, main = client.get(cr.SUBMISSIONS_URL.format(cik=cik))
        if st != 200 or not main:
            return t, cik, None
        chunks = []
        for name in e9.chunk_names(main, *SPAN):
            s2, b2 = client.get(f"https://data.sec.gov/submissions/{name}")
            if s2 == 200 and b2:
                chunks.append(b2)
        try:
            fr = e9.parse_submissions(main, chunks)
        except (ValueError, KeyError):
            return t, cik, None
        fr = fr[fr["form"].str.upper().isin(FORMS) & (fr["filingDate"] >= SPAN[0]) & (fr["filingDate"] <= SPAN[1])]
        return t, cik, fr[["form", "filingDate", "accessionNumber"]].assign(ticker=t, cik=cik)

    rows, missing = [], []
    with ThreadPoolExecutor(4) as ex:
        for i, (t, cik, fr) in enumerate(ex.map(one, ciks.items())):
            if fr is None:
                missing.append(t)
            elif len(fr):
                rows.append(fr)
            if (i + 1) % 200 == 0:
                log(f"  submissions {i + 1}/{len(ciks)}")
    filings = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["form", "filingDate", "accessionNumber", "ticker", "cik"])
    filings.sort_values(["ticker", "filingDate", "accessionNumber"]).to_csv(OUT / "us_filings.csv.gz", index=False)
    shares = []
    for q in QUARTERS:
        st, body = client.get(f"https://data.sec.gov/api/xbrl/frames/dei/EntityCommonStockSharesOutstanding/shares/{q}.json")
        if st != 200:
            log(f"  frame {q}: HTTP {st}")
            continue
        for r in json.loads(body)["data"]:
            if int(r["cik"]) in set(ciks.values()):
                shares.append({"frame": q, "cik": int(r["cik"]), "end": r["end"], "val": r["val"], "accn": r["accn"]})
    pd.DataFrame(shares).to_csv(OUT / "us_shares.csv.gz", index=False)
    return {"ticker_map": cr.TICKERS_URL, "mapped": len(ciks), "event_stocks": len(tickers),
            "submissions_failed": sorted(missing), "filings_kept": int(len(filings)), "share_points": len(shares),
            "responses": [{k: r[k] for k in ("url", "http_status", "sha256")} for r in client.records]}


def finra(tickers: set[str], days: list[str], log=print) -> dict:
    want = {t.replace("-", "."): t for t in tickers} | {t: t for t in tickers}

    def one(day):
        url = FINRA.format(day=day.replace("-", ""))
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "KOD-Machine research"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return day, url, 404, None, []
                body = None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                body = None
            time.sleep(2 * 2 ** attempt)
        if body is None:
            return day, url, 0, None, []
        out = []
        for line in body.decode("utf-8", "replace").splitlines()[1:]:
            p = line.split("|")
            if len(p) >= 5 and p[1] in want and p[4].isdigit():
                out.append({"date": day, "ticker": want[p[1]], "short_volume": int(p[2] or 0), "total_volume": int(p[4])})
        return day, url, 200, hashlib.sha256(body).hexdigest(), out

    rows, files = [], []
    with ThreadPoolExecutor(4) as ex:
        for i, (day, url, st, sha, out) in enumerate(ex.map(one, days)):
            files.append({"url": url, "http_status": st, "sha256": sha})
            rows += out
            if (i + 1) % 200 == 0:
                log(f"  FINRA {i + 1}/{len(days)}")
    pd.DataFrame(rows).to_csv(OUT / "us_short.csv.gz", index=False)
    return {"files": files, "rows": len(rows), "missing_days": [f["url"] for f in files if f["http_status"] != 200]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tickers, days = us_events()
    print(f"US event stocks: {len(tickers)}; sessions {days[0]}..{days[-1]} ({len(days)})", flush=True)
    rec = {"protocol": "KOD-PATH-HISTORY-v1", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rec["finra"] = finra(tickers, days, log=lambda s: print(s, flush=True))
    rec["edgar"] = edgar(tickers, log=lambda s: print(s, flush=True))
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (OUT / "COLLECT.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("done", {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk not in ("responses", "files")}) for k, v in rec.items()})


if __name__ == "__main__":
    main()

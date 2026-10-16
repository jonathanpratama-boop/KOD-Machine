"""E9 feasibility (research/E9/FEASIBILITY_SPEC.md): counts and checks only, no forward return.

Reads the shared entry list, the cached SEC submissions (collect_sec.py), the panel's session calendar and
trailing closes (bars at or before each signal only), and fetches the 20 EDGAR SGML headers for the
acceptance-time check plus eToro's public instrument list. Writes research/E9/feasibility/{FEASIBILITY.json,
classes.csv.gz}. Runs once.

Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/E9/feasibility.py <sec stamp>
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import catalyst  # noqa: E402
from idxsig.us_actions import SecClient  # noqa: E402

E9 = ROOT / "research" / "E9"
OUT = E9 / "feasibility"
PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
ETORO_URL = "https://api.etorostatic.com/sapi/instrumentsmetadata/V1.1/instruments/bulk?bulkNumber=1&totalBulks=1"
SCORED = ("EXITED", "EXIT_DATA_END")
SEED = 20261017


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(t: str) -> str:
    return str(t).upper().replace(".", "-").strip()


def etoro_symbols(stamp: str) -> tuple[set, dict]:
    d = ROOT / "data" / "raw" / "etoro" / stamp
    d.mkdir(parents=True, exist_ok=True)
    body = urllib.request.urlopen(urllib.request.Request(ETORO_URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=90).read()
    (d / "instruments.json").write_bytes(body)
    data = json.loads(body)["InstrumentDisplayDatas"]
    us = {norm(x["SymbolFull"]) for x in data
          if x["InstrumentTypeID"] == 5 and x["ExchangeID"] in (4, 5) and not x.get("IsInternalInstrument")}
    man = ROOT / "data" / "manifests" / f"etoro_instruments-{stamp}.jsonl"
    with man.open("x") as f:
        f.write(json.dumps({"manifest": man.name, "source": "eToro public static instrument list", "url": ETORO_URL,
                            "note": "current listing only: names eToro dropped earlier are absent"}) + "\n")
        f.write(json.dumps({"path": f"data/raw/etoro/{stamp}/instruments.json", "sha256": sha(body), "bytes": len(body),
                            "downloaded_at": datetime.now(timezone.utc).isoformat(), "us_stocks": len(us)}) + "\n")
    return us, {"manifest": man.name, "sha256": sha(body), "us_stocks_listed": len(us)}


def sgml_acceptance(client: SecClient, cik: int, acc: str) -> str | None:
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{acc}-index-headers.html"
    st, body = client.get(url)
    m = re.search(rb"<ACCEPTANCE-DATETIME>\s*(\d{14})", body) if st == 200 else None
    return m.group(1).decode() if m else None


def main(sec_stamp: str) -> int:
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; the check runs once")
    contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
    if "@" not in contact:
        sys.exit("error: set KOD_SEC_CONTACT")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cache = SecClient(f"KOD-Machine research {contact}", ROOT / "data" / "raw" / "sec" / sec_stamp, offline=True)
    online = SecClient(f"KOD-Machine research {contact}", ROOT / "data" / "raw" / "sec" / stamp)

    sig = pd.read_csv(E9 / "entries" / "signals.csv", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    A = sig[sig.j >= 0].copy()
    cmap = pd.read_csv(E9 / "sec" / f"cik_map-{sec_stamp}.csv", dtype={"ticker": str}, keep_default_na=False,
                       na_values=[""]).set_index("ticker")["cik"]
    status = {s["cik"]: s for s in json.loads((E9 / "sec" / f"fetch_status-{sec_stamp}.json").read_text())}
    A["cik"] = A.ticker.map(cmap)

    # session calendar and trailing volatility (bars at or before the signal session only)
    P = pd.read_csv(PANEL, usecols=["date", "ticker", "close"], dtype={"ticker": str}, keep_default_na=False,
                    na_values=[""], parse_dates=["date"])
    P = P[(P.date >= "2020-03-01") & (P.date <= "2023-01-31")]
    cal = np.array(sorted(P.date.unique()))
    pos = {d: i for i, d in enumerate(cal)}
    sd = pd.to_datetime(A.signal_date)
    A["prev_session"] = [str(pd.Timestamp(cal[pos[d] - 1]).date()) for d in sd]
    A["entry_session"] = [str(pd.Timestamp(cal[pos[d] + 1]).date()) if pos[d] + 1 < len(cal) else "" for d in sd]
    if not (A.entry_date.eq(A.entry_session) | A.entry_date.eq("")).all():
        sys.exit("error: an entry date is not the next panel session")
    P = P.sort_values(["ticker", "date"])
    P["r"] = P.groupby("ticker").close.pct_change()
    P["vol20"] = P.groupby("ticker").r.transform(lambda s: s.rolling(20, min_periods=15).std())
    vol = P.set_index(["ticker", "date"]).vol20
    A["vol20"] = [vol.get((t, d), np.nan) for t, d in zip(A.ticker, sd)]

    # filings per CIK from the cache
    frames, missing = {}, []
    for cik in sorted({int(c) for c in A.cik.dropna()}):
        st, body = cache.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        names = (status.get(cik) or {}).get("chunk_names") or []
        chunks = [cache.get(f"https://data.sec.gov/submissions/{n}")[1] for n in names]
        if st != 200 or any(not c for c in chunks):
            missing.append(cik)
            continue
        frames[cik] = catalyst.parse_submissions(body, chunks)

    # acceptance-time check on 20 filings that fall in event windows (+-1 day either convention)
    pool = []
    for r in A[A.cik.notna()].itertuples():
        f = frames.get(int(r.cik))
        if f is None or not r.entry_session:
            continue
        lo, hi = catalyst.window(r.prev_session, r.entry_session)
        day = f.acceptanceDateTime.str[:10]
        near = f[(day >= str((lo - pd.Timedelta(days=1)).date())) & (day <= str((hi + pd.Timedelta(days=1)).date()))]
        pool += [(int(r.cik), a, v) for a, v in zip(near.accessionNumber, near.acceptanceDateTime) if v]
    pool = sorted(set(pool))
    pick = [pool[i] for i in np.random.default_rng(SEED).choice(len(pool), size=min(20, len(pool)), replace=False)]
    check = []
    for cik, acc, val in pick:
        hdr = sgml_acceptance(online, cik, acc)
        ny = catalyst.acceptance_ny(val, "ny").strftime("%Y%m%d%H%M%S")
        utc = catalyst.acceptance_ny(val, "utc").strftime("%Y%m%d%H%M%S")
        check.append({"cik": cik, "accession": acc, "json": val, "sgml": hdr, "match_ny": hdr == ny, "match_utc": hdr == utc})
    n_ny, n_utc = sum(c["match_ny"] for c in check), sum(c["match_utc"] for c in check)
    convention = "ny" if n_ny == len(check) else "utc" if n_utc == len(check) else None
    accept_ok = len(check) == 20 and max(n_ny, n_utc) >= 19

    # classes (only with a passing convention)
    conv = convention or ("ny" if n_ny >= n_utc else "utc")
    out = []
    for r in A.itertuples():
        base = {"j": r.j, "ticker": r.ticker, "signal_date": r.signal_date, "status": r.status, "cik": r.cik}
        if pd.isna(r.cik):
            out.append({**base, "class": "NO_CIK"})
            continue
        f = frames.get(int(r.cik))
        if f is None or not r.entry_session:
            out.append({**base, "class": "NO_SEC_DATA" if f is None else "NO_ENTRY_SESSION"})
            continue
        lo, hi = catalyst.window(r.prev_session, r.entry_session)
        c = catalyst.classify(f, lo, hi, conv)
        out.append({**base, **c, "later_documented_4d": catalyst.later_documentation(f, hi, 4, conv),
                    "earliest_fetched_filing": f.filingDate.min()})
    K = pd.DataFrame(out)
    K["prev_session"], K["entry_session"], K["vol20"] = A.prev_session.values, A.entry_session.values, A.vol20.values
    us, et = etoro_symbols(stamp)
    K["etoro_listed_now"] = K.ticker.map(norm).isin(us)
    iso = pd.to_datetime(K.signal_date).dt.isocalendar()
    K["week"] = iso.year.astype(int) * 100 + iso.week.astype(int)
    K["year"] = K.signal_date.str[:4]
    K["entered"] = K.status.isin(SCORED)
    # coverage of the window: fetched filings must start before the window (else the issuer was new)
    K["window_covered"] = K.earliest_fetched_filing.fillna("9999") <= K.prev_session

    E = K[K.entered]
    def by(df, col):
        return {str(k): int(v) for k, v in df[col].value_counts().sort_index().items()}
    counts = {"attempted": int(len(K)), "attempted_by_class": by(K, "class"), "entered_by_class": by(E, "class"),
              "entered_weeks_by_class": {c: int(E[E["class"] == c].week.nunique()) for c in catalyst.CLASSES},
              "entered_by_year_and_class": {y: by(g, "class") for y, g in E.groupby("year")},
              "entered_distinct_tickers_by_class": {c: int(E[E["class"] == c].ticker.nunique()) for c in catalyst.CLASSES},
              "documented_8k_item_families": pd.Series(";".join(E[E["class"] == "DOCUMENTED"].items_8k.fillna("")).split(";"))
                  .replace("", np.nan).dropna().value_counts().head(15).to_dict(),
              "documented_forms": pd.Series(";".join(E[E["class"] == "DOCUMENTED"].forms.fillna("")).split(";"))
                  .replace("", np.nan).dropna().value_counts().head(15).to_dict(),
              "undocumented_later_documented_4d": int(E[(E["class"] == "UNDOCUMENTED")].later_documented_4d.sum()),
              "entered_window_not_covered": int((~E.window_covered).sum()),
              "etoro_listed_now_share_entered": float(E.etoro_listed_now.mean()),
              "etoro_listed_now_entered_by_class": by(E[E.etoro_listed_now], "class")}
    mapped = A.cik.notna().mean()
    ok_ciks = sum(1 for c, s in status.items() if s["main_status"] == 200 and s["chunks_ok"] == s["chunks_needed"])
    fetch_rate = ok_ciks / max(1, len(status))
    # minimum detectable difference DOCUMENTED - UNDOCUMENTED (80% power, one-sided 2.5%), trailing vol only
    sig5 = float(np.sqrt(np.nanmean((E.vol20 * np.sqrt(5)) ** 2)))
    mde = {}
    for rho in (0.05, 0.2):
        terms = 0.0
        for c in ("DOCUMENTED", "UNDOCUMENTED"):
            g = E[E["class"] == c]
            m = g.week.value_counts().to_numpy()
            de = 1 + ((m ** 2).sum() / max(1, m.sum()) - 1) * rho
            terms += de / max(1, len(g))
        mde[f"rho_{rho}"] = float((1.959964 + 0.841621) * sig5 * np.sqrt(terms))
    conds = {"mapped >= 90% of attempted": bool(mapped >= 0.90),
             "SEC fetch complete for >= 98% of mapped CIKs": bool(fetch_rate >= 0.98),
             "acceptance-time check passes (>= 19 of 20)": bool(accept_ok),
             "entered DOCUMENTED >= 150": counts["entered_by_class"].get("DOCUMENTED", 0) >= 150,
             "entered UNDOCUMENTED >= 150": counts["entered_by_class"].get("UNDOCUMENTED", 0) >= 150,
             "DOCUMENTED weeks >= 50": counts["entered_weeks_by_class"]["DOCUMENTED"] >= 50,
             "UNDOCUMENTED weeks >= 50": counts["entered_weeks_by_class"]["UNDOCUMENTED"] >= 50}
    res = {"spec": "research/E9/FEASIBILITY_SPEC.md", "stage": "feasibility: counts only, no forward return",
           "sec_cache_stamp": sec_stamp, "check_stamp": stamp, "mapped_share": float(mapped),
           "ciks": len(status), "ciks_fetch_complete": ok_ciks, "fetch_complete_share": fetch_rate,
           "ciks_missing_from_cache": missing, "acceptance_check": {"convention": convention, "n": len(check),
                                                                    "match_ny": n_ny, "match_utc": n_utc, "rows": check},
           "etoro": et, "counts": counts,
           "power": {"sigma_5d_rms_from_trailing_20d_vol": sig5, "mde_doc_minus_undoc": mde},
           "go_conditions": conds, "decision": "GO" if all(conds.values()) else "NO-GO"}
    OUT.mkdir(parents=True)
    K.drop(columns=["vol20"]).to_csv(OUT / "classes.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    (OUT / "FEASIBILITY.json").write_text(json.dumps(res, indent=1, default=str))
    man = ROOT / "data" / "manifests" / f"sec_headers-{stamp}.jsonl"
    with man.open("x") as f:
        f.write(json.dumps({"manifest": man.name, "purpose": "E9 acceptance-time check",
                            "user_agent": "KOD-Machine research <owner-supplied contact; not recorded>",
                            "n_files": len(online.records)}) + "\n")
        for r in online.records:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("mapped_share", "fetch_complete_share", "acceptance_check", "counts",
                                          "power", "go_conditions", "decision")}, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

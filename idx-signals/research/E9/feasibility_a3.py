"""E9 feasibility under amendment 3 (research/E9/FEASIBILITY_AMENDMENT_3.md): counts and checks only, no forward
return. As feasibility_a2.py, except that every acceptance time that can change a class comes from the filing's
own SGML header (<ACCEPTANCE-DATETIME>, New York time), and header coverage (at least 98% of the needed headers)
replaces the 20-filing convention check. eToro's list is the one the first check fetched, hash-checked.

Reads the shared entry list, the cached SEC submissions (collect_sec.py), the panel's session calendar and
trailing closes (bars at or before each signal only), and fetches the needed EDGAR headers. Writes
research/E9/feasibility_a3/{FEASIBILITY.json, classes.csv.gz, headers.csv.gz}. Runs once.

Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/E9/feasibility_a3.py <sec stamp>
"""
import concurrent.futures as cf
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import catalyst  # noqa: E402
from idxsig.us_actions import SecClient  # noqa: E402

E9 = ROOT / "research" / "E9"
OUT = E9 / "feasibility_a3"
PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
ETORO_STAMP = "20261016T190421Z"
SCORED = ("EXITED", "EXIT_DATA_END")
RELEVANT = catalyst.DILUTION_FORMS | catalyst.INFO_FORMS
LATER_DAYS = 4         # the hindsight diagnostic, as before: an information filing within 4 days after the cutoff
LATER_FETCH_DAYS = 5   # filing dates whose headers it needs: the entry session through 5 calendar days after


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(t: str) -> str:
    return str(t).upper().replace(".", "-").strip()


def etoro_symbols() -> tuple[set, dict]:
    """The list the first check fetched, checked against its manifest (amendment 3, point 5)."""
    body = (ROOT / "data" / "raw" / "etoro" / ETORO_STAMP / "instruments.json").read_bytes()
    man = [json.loads(x) for x in (ROOT / "data" / "manifests" / f"etoro_instruments-{ETORO_STAMP}.jsonl").read_text().splitlines()]
    if sha(body) != man[1]["sha256"]:
        sys.exit("error: the eToro list differs from its manifest")
    data = json.loads(body)["InstrumentDisplayDatas"]
    us = {norm(x["SymbolFull"]) for x in data
          if x["InstrumentTypeID"] == 5 and x["ExchangeID"] in (4, 5) and not x.get("IsInternalInstrument")}
    return us, {"manifest": man[0]["manifest"], "sha256": man[1]["sha256"], "us_stocks_listed": len(us)}


def header_url(cik: int, acc: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{acc}-index-headers.html"


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

    # session calendar and trailing volatility (bars at or before the signal session only), as feasibility_a2.py
    P = pd.read_csv(PANEL, usecols=["date", "ticker", "close"], dtype={"ticker": str}, keep_default_na=False,
                    na_values=[""], parse_dates=["date"])
    P = P[(P.date >= "2020-03-01") & (P.date <= "2023-01-31")]
    cal = np.array(sorted(P.date.unique()))
    pos = {d: i for i, d in enumerate(cal)}
    sd = pd.to_datetime(A.signal_date)
    A["prev_session"] = [str(pd.Timestamp(cal[pos[d] - 1]).date()) for d in sd]
    A["entry_session"] = [str(pd.Timestamp(cal[pos[d] + 1]).date()) if pos[d] + 1 < len(cal) else "" for d in sd]
    if not (A.entry_date.fillna("").eq(A.entry_session) | A.entry_date.isna()).all():
        sys.exit("error: an entry date is not the next panel session")
    P = P.sort_values(["ticker", "date"])
    P["r"] = P.groupby("ticker").close.pct_change()
    P["vol20"] = P.groupby("ticker").r.transform(lambda s: s.rolling(20, min_periods=15).std())
    vol = P.set_index(["ticker", "date"]).vol20
    A["vol20"] = [vol.get((t, d), np.nan) for t, d in zip(A.ticker, sd)]

    # filings per CIK from the cache, as feasibility_a2.py
    frames, missing = {}, []
    for cik in sorted({int(c) for c in A.cik.dropna()}):
        st, body = cache.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        names = (status.get(cik) or {}).get("chunk_names") or []
        chunks = [cache.get(f"https://data.sec.gov/submissions/{n}")[1] for n in names]
        if st != 200 or any(not c for c in chunks):
            missing.append(cik)
            continue
        frames[cik] = catalyst.parse_submissions(body, chunks)
    span = {c: f[(f.filingDate >= "2020-06-01") & (f.filingDate <= "2023-01-31")] for c, f in frames.items()}
    no_time = {"filings_in_span": int(sum(len(f) for f in span.values())),
               "without_acceptance_time": int(sum((f.acceptanceDateTime == "").sum() for f in span.values()))}

    # the headers a class can depend on (amendment 3, point 1) and the diagnostic's (point 2)
    def ranges(f, r):
        fu = f.form.str.upper()
        e5 = str((pd.Timestamp(r.entry_session) + pd.Timedelta(days=LATER_FETCH_DAYS)).date())
        w = fu.isin(RELEVANT) & (f.filingDate >= r.prev_session) & (f.filingDate <= r.entry_session)
        late = fu.isin(catalyst.INFO_FORMS) & (f.filingDate >= r.entry_session) & (f.filingDate <= e5)
        return w, late

    need = {}
    for r in A[A.cik.notna()].itertuples():
        f = frames.get(int(r.cik))
        if f is None or not r.entry_session:
            continue
        w, late = ranges(f, r)
        for a in f.accessionNumber[w]:
            need.setdefault((int(r.cik), a), set()).add("window")
        for a in f.accessionNumber[late]:
            need.setdefault((int(r.cik), a), set()).add("later")
    print(f"{len(need)} headers needed", flush=True)

    def fetch(key):
        cik, acc = key
        st, body = online.get(header_url(cik, acc))
        return key, st, catalyst.header_acceptance(body) if st == 200 else None

    got = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for k, (key, st, hdr) in enumerate(ex.map(fetch, sorted(need)), 1):
            got[key] = (st, hdr)
            if k % 500 == 0:
                print(f"{k}/{len(need)}", flush=True)
    by_cik = {}
    for (cik, acc), (st, hdr) in got.items():
        if hdr:
            by_cik.setdefault(cik, {})[acc] = hdr
    for cik, f in frames.items():
        f["acceptanceHeader"] = f.accessionNumber.map(by_cik.get(cik, {})).fillna("").astype(str)

    # the JSON defect, described (amendment 3, point 6; never a decision input)
    rows, per_cik = [], {}
    for (cik, acc), (st, hdr) in sorted(got.items()):
        f = frames[cik]
        js = f.loc[f.accessionNumber == acc, "acceptanceDateTime"].iloc[0]
        match = [cv for cv in ("ny", "utc", "double")
                 if hdr and js and catalyst.acceptance_ny(js, cv).strftime("%Y%m%d%H%M%S") == hdr]
        conv = match[0] if match else ("none" if hdr else "no_header")
        rows.append({"cik": cik, "accessionNumber": acc, "http_status": st, "acceptance_header": hdr or "",
                     "json_acceptance": js, "json_convention": conv, "needed_for": ";".join(sorted(need[(cik, acc)]))})
        if hdr:
            per_cik.setdefault(cik, set()).add(conv)
    H = pd.DataFrame(rows)
    json_defect = {"headers_by_json_convention": {k: int(v) for k, v in H.json_convention.value_counts().items()},
                   "ciks_with_headers": len(per_cik),
                   "ciks_one_convention": sum(1 for v in per_cik.values() if len(v) == 1),
                   "ciks_mixed": sum(1 for v in per_cik.values() if len(v) > 1)}

    # classes from header times; a signal missing a needed header is NO_HEADER (point 3)
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
        w, _ = ranges(f, r)
        lost = [a for a in f.accessionNumber[w] if not got.get((int(r.cik), a), (0, None))[1]]
        if lost:
            out.append({**base, "class": "NO_HEADER", "missing_headers": ";".join(lost)})
            continue
        lo, hi = catalyst.window(r.prev_session, r.entry_session)
        c = catalyst.classify(f, lo, hi, "header")
        out.append({**base, **c, "later_documented_4d": catalyst.later_documentation(f, hi, LATER_DAYS, "header"),
                    "relevant_filings_dated_in_range": int(w.sum()), "earliest_fetched_filing": f.filingDate.min()})
    K = pd.DataFrame(out)
    K["prev_session"], K["entry_session"], K["vol20"] = A.prev_session.values, A.entry_session.values, A.vol20.values
    us, et = etoro_symbols()
    K["etoro_listed_now"] = K.ticker.map(norm).isin(us)
    iso = pd.to_datetime(K.signal_date).dt.isocalendar()
    K["week"] = iso.year.astype(int) * 100 + iso.week.astype(int)
    K["year"] = K.signal_date.str[:4]
    K["entered"] = K.status.isin(SCORED)
    K["window_covered"] = K.earliest_fetched_filing.fillna("9999") <= K.prev_session
    first = pd.read_csv(E9 / "feasibility" / "classes.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    if not (first.j.to_numpy() == K.j.to_numpy()).all():
        sys.exit("error: the first check's rows do not line up")

    E = K[K.entered]

    def by(df, col):
        return {str(k): int(v) for k, v in df[col].value_counts().sort_index().items()}
    classes = catalyst.CLASSES
    counts = {"attempted": int(len(K)), "attempted_by_class": by(K, "class"), "entered_by_class": by(E, "class"),
              "entered_weeks_by_class": {c: int(E[E["class"] == c].week.nunique()) for c in classes},
              "entered_by_year_and_class": {y: by(g, "class") for y, g in E.groupby("year")},
              "entered_distinct_tickers_by_class": {c: int(E[E["class"] == c].ticker.nunique()) for c in classes},
              "documented_8k_item_families": pd.Series(";".join(E[E["class"] == "DOCUMENTED"].items_8k.fillna("")).split(";"))
                  .replace("", np.nan).dropna().value_counts().head(15).to_dict(),
              "documented_forms": pd.Series(";".join(E[E["class"] == "DOCUMENTED"].forms.fillna("")).split(";"))
                  .replace("", np.nan).dropna().value_counts().head(15).to_dict(),
              "dilution_forms": pd.Series(";".join(E[E["class"] == "DILUTION"].forms.fillna("")).split(";"))
                  .replace("", np.nan).dropna().value_counts().head(15).to_dict(),
              "undocumented_later_documented_4d": int(E[(E["class"] == "UNDOCUMENTED")].later_documented_4d.astype(bool).sum()),
              "entered_window_not_covered_by_class": by(E[~E.window_covered], "class"),
              "etoro_listed_now_share_entered": float(E.etoro_listed_now.mean()),
              "etoro_listed_now_entered_by_class": by(E[E.etoro_listed_now], "class"),
              "entered_class_vs_first_check_invalid": {f"{a}->{b}": int(n) for (a, b), n in
                                                       pd.crosstab(first["class"][K.entered.to_numpy()],
                                                                   K["class"][K.entered]).stack().items() if n}}
    mapped = A.cik.notna().mean()
    ok_ciks = sum(1 for c, s in status.items() if s["main_status"] == 200 and s["chunks_ok"] == s["chunks_needed"])
    fetch_rate = ok_ciks / max(1, len(status))
    needed_w = [k for k, v in need.items() if "window" in v]
    needed_l = [k for k, v in need.items() if v == {"later"}]
    header_rate = sum(1 for k in needed_w if got[k][1]) / max(1, len(needed_w))
    headers = {"needed_window": len(needed_w), "retrieved_window": sum(1 for k in needed_w if got[k][1]),
               "needed_later_only": len(needed_l), "retrieved_later_only": sum(1 for k in needed_l if got[k][1]),
               "coverage_window": header_rate, "http_status": {str(k): int(v) for k, v in H.http_status.value_counts().items()}}
    # minimum detectable difference DOCUMENTED - UNDOCUMENTED (80% power, one-sided 2.5%), trailing vol only
    sig5 = float(np.sqrt(np.nanmean((E.vol20 * np.sqrt(5)) ** 2)))
    sig5_median = float(np.nanmedian(E.vol20 * np.sqrt(5)))
    mde = {}
    for rho in (0.05, 0.2):
        terms = 0.0
        for c in ("DOCUMENTED", "UNDOCUMENTED"):
            g = E[E["class"] == c]
            m = g.week.value_counts().to_numpy()
            de = 1 + ((m ** 2).sum() / max(1, m.sum()) - 1) * rho
            terms += de / max(1, len(g))
        mde[f"rho_{rho}"] = float((1.959964 + 0.841621) * sig5 * np.sqrt(terms))
        mde[f"rho_{rho}_at_median_vol"] = float((1.959964 + 0.841621) * sig5_median * np.sqrt(terms))
    conds = {"mapped >= 90% of attempted": bool(mapped >= 0.90),
             "SEC fetch complete for >= 98% of mapped CIKs": bool(fetch_rate >= 0.98),
             "headers retrieved for >= 98% of the needed filings": bool(header_rate >= 0.98),
             "entered DOCUMENTED >= 150": counts["entered_by_class"].get("DOCUMENTED", 0) >= 150,
             "entered UNDOCUMENTED >= 150": counts["entered_by_class"].get("UNDOCUMENTED", 0) >= 150,
             "DOCUMENTED weeks >= 50": counts["entered_weeks_by_class"]["DOCUMENTED"] >= 50,
             "UNDOCUMENTED weeks >= 50": counts["entered_weeks_by_class"]["UNDOCUMENTED"] >= 50}
    res = {"spec": "research/E9/FEASIBILITY_SPEC.md",
           "amendments": [f"research/E9/FEASIBILITY_AMENDMENT_{i}.md" for i in (1, 2, 3)],
           "first_check": "research/E9/feasibility/FEASIBILITY.json (NO-GO on the JSON acceptance time; classes invalid)",
           "stage": "feasibility: counts only, no forward return", "filing_times": no_time,
           "sec_cache_stamp": sec_stamp, "header_stamp": stamp, "mapped_share": float(mapped),
           "ciks": len(status), "ciks_fetch_complete": ok_ciks, "fetch_complete_share": fetch_rate,
           "ciks_missing_from_cache": missing, "headers": headers, "json_acceptance_defect": json_defect,
           "etoro": et, "counts": counts,
           "power": {"sigma_5d_rms_from_trailing_20d_vol": sig5, "sigma_5d_median": sig5_median, "mde_doc_minus_undoc": mde},
           "go_conditions": conds, "decision": "GO" if all(conds.values()) else "NO-GO"}
    OUT.mkdir(parents=True)
    K.drop(columns=["vol20"]).to_csv(OUT / "classes.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    H.to_csv(OUT / "headers.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    (OUT / "FEASIBILITY.json").write_text(json.dumps(res, indent=1, default=str))
    man = ROOT / "data" / "manifests" / f"sec_headers-{stamp}.jsonl"
    with man.open("x") as f:
        f.write(json.dumps({"manifest": man.name, "purpose": "E9 acceptance times from SGML headers (amendment 3)",
                            "user_agent": "KOD-Machine research <owner-supplied contact; not recorded>",
                            "n_files": len(online.records)}) + "\n")
        for r in online.records:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("mapped_share", "fetch_complete_share", "headers", "json_acceptance_defect",
                                          "counts", "power", "go_conditions", "decision")}, indent=1, default=str)[:7000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

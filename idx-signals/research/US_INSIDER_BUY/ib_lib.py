"""US_INSIDER_BUY shared code (see PROTOCOL.md): the reader of the SEC Insider Transactions Data Sets (Form 4 open-market purchases by officers and directors) and the event
table. Pure functions: no network, no prices."""
import re
import zipfile

import numpy as np
import pandas as pd

MIN_VALUE, CHAIN_DAYS, CHAIN_START = 50_000.0, 90, "2020-07-01"
STAGES = {1: ("2021-01-04", "2022-12-30"), 2: ("2023-01-03", "2023-09-29")}
QUARTERS = [f"{y}q{q}" for y in range(2020, 2024) for q in range(1, 5) if (y, q) >= (2020, 3)]
URL = "https://www.sec.gov/files/structureddata/data/form-345/{quarter}_form345.zip"
LINE_COLUMNS = ["accession", "filing_date", "issuer_cik", "symbol", "security_title", "trans_date", "shares", "price", "value", "aff10b5one", "n_owners", "officer",
                "director", "tenpct", "top_exec"]
EVENT_COLUMNS = ["ticker", "cik", "accession", "public_date", "stage", "total_value", "n_lines", "n_owners", "officer", "director", "top_exec", "symbol", "trans_first",
                 "trans_last", "lag_days"]

_INCLUDE = re.compile(r"\b(common|ordinary|class [a-z]|capital stock|shares?|stock)\b", re.I)
_EXCLUDE = re.compile(r"\b(preferred|warrants?|options?|notes?|debentures?|convertible|bonds?|depositary|units?|rights?)\b", re.I)
_TOP = re.compile(r"\b(CEO|CFO|CHIEF EXECUTIVE|CHIEF FINANCIAL)\b|(?<!VICE[ -])\bPRESIDENT\b", re.I)
_FLAGGED = {"1", "TRUE", "Y", "YES"}


def is_common(title: str) -> bool:
    """The protocol's title rule: names common equity and none of the excluded instruments."""
    title = title or ""
    return bool(_INCLUDE.search(title)) and not _EXCLUDE.search(title)


def _table(z: zipfile.ZipFile, name: str, needed: list[str]) -> pd.DataFrame:
    member = next((m for m in z.namelist() if m.upper().endswith(name)), None)
    if member is None:
        raise KeyError(f"{name} is not in the archive ({z.namelist()})")
    with z.open(member) as fh:
        df = pd.read_csv(fh, sep="\t", dtype=str, keep_default_na=False, quoting=3, encoding_errors="replace", low_memory=False)
    df.columns = [c.strip().upper() for c in df.columns]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"{name}: no column {missing} (has {list(df.columns)})")
    return df


def _date(s: pd.Series) -> pd.Series:
    """'02-JAN-2020' (the data sets' format); anything else the general parser reads; NaT if neither."""
    d = pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")
    miss = d.isna() & (s.str.strip() != "")
    if miss.any():
        d[miss] = pd.to_datetime(s[miss], errors="coerce")
    return d


def parse_quarter(z: zipfile.ZipFile) -> tuple[pd.DataFrame, dict]:
    """The purchase lines of one quarter's archive (Form 4, code P, acquired, common equity, positive shares and price) with the filing's issuer, dates and owner flags, and the
    funnel counts."""
    sub = _table(z, "SUBMISSION.TSV", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERCIK"])
    own = _table(z, "REPORTINGOWNER.TSV", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP"])
    trn = _table(z, "NONDERIV_TRANS.TSV", ["ACCESSION_NUMBER", "SECURITY_TITLE", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
    n = {"submissions": len(sub), "owners": len(own), "nonderiv_lines": len(trn)}
    f4 = sub[sub["DOCUMENT_TYPE"].str.strip() == "4"]
    n["form4_submissions"] = len(f4)
    t = trn[trn["ACCESSION_NUMBER"].isin(set(f4["ACCESSION_NUMBER"]))]
    n["form4_lines"] = len(t)
    t = t[t["TRANS_CODE"].str.strip().str.upper() == "P"]
    n["code_P"] = len(t)
    t = t[t["TRANS_ACQUIRED_DISP_CD"].str.strip().str.upper() == "A"]
    n["code_P_acquired"] = len(t)
    t = t[t["SECURITY_TITLE"].map(is_common)]
    n["common_equity"] = len(t)
    shares = pd.to_numeric(t["TRANS_SHARES"], errors="coerce")
    price = pd.to_numeric(t["TRANS_PRICEPERSHARE"], errors="coerce")
    ok = (shares > 0) & (price > 0)
    t = t[ok].assign(shares=shares[ok], price=price[ok])
    t["value"] = t["shares"] * t["price"]
    n["positive_shares_and_price"] = len(t)

    rel = own["RPTOWNER_RELATIONSHIP"].str.upper()
    title = own["RPTOWNER_TITLE"].fillna("") if "RPTOWNER_TITLE" in own else pd.Series("", index=own.index)
    officer, director = rel.str.contains("OFFICER"), rel.str.contains("DIRECTOR")
    o = pd.DataFrame({"ACCESSION_NUMBER": own["ACCESSION_NUMBER"], "owner": own["RPTOWNERCIK"], "officer": officer, "director": director,
                      "tenpct": rel.str.contains("TENPERCENT|10%"), "top_exec": officer & title.map(lambda s: bool(_TOP.search(s)))})
    flags = o.groupby("ACCESSION_NUMBER").agg(n_owners=("owner", "nunique"), officer=("officer", "any"), director=("director", "any"), tenpct=("tenpct", "any"),
                                              top_exec=("top_exec", "any"))
    keep = ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERCIK"] + [c for c in ("ISSUERTRADINGSYMBOL", "AFF10B5ONE") if c in f4]
    lines = t.merge(f4[keep], on="ACCESSION_NUMBER", how="inner").merge(flags, left_on="ACCESSION_NUMBER", right_index=True, how="left")
    for c in ("officer", "director", "tenpct", "top_exec"):
        lines[c] = lines[c].fillna(False).astype(bool)
    lines["n_owners"] = lines["n_owners"].fillna(0).astype(int)
    out = pd.DataFrame({
        "accession": lines["ACCESSION_NUMBER"], "filing_date": _date(lines["FILING_DATE"]).dt.strftime("%Y-%m-%d"),
        "issuer_cik": pd.to_numeric(lines["ISSUERCIK"], errors="coerce"),
        "symbol": lines["ISSUERTRADINGSYMBOL"].str.strip() if "ISSUERTRADINGSYMBOL" in lines else "",
        "security_title": lines["SECURITY_TITLE"].str.strip(), "trans_date": _date(lines["TRANS_DATE"]).dt.strftime("%Y-%m-%d"),
        "shares": lines["shares"], "price": lines["price"], "value": lines["value"],
        "aff10b5one": lines["AFF10B5ONE"].str.strip().str.upper() if "AFF10B5ONE" in lines else "",
        "n_owners": lines["n_owners"], "officer": lines["officer"], "director": lines["director"], "tenpct": lines["tenpct"], "top_exec": lines["top_exec"]})
    bad = out["filing_date"].isna() | out["issuer_cik"].isna()
    n["dropped_unparsable_filing_date_or_cik"] = int(bad.sum())
    out = out[~bad].copy()
    out["issuer_cik"] = out["issuer_cik"].astype("int64")
    n["lines_out"] = len(out)
    return out.reset_index(drop=True)[LINE_COLUMNS], n


def purchase_filings(lines: pd.DataFrame, min_value: float = MIN_VALUE) -> pd.DataFrame:
    """One row per Form 4 that is a *purchase filing*: an officer or director among its owners, no 10b5-1 flag, purchase lines totalling at least `min_value`."""
    if not len(lines):
        return pd.DataFrame(columns=["accession", "filing_date", "issuer_cik", "symbol", "total_value", "n_lines", "trans_first", "trans_last", "n_owners", "officer",
                                     "director", "top_exec", "aff10b5one"])
    f = lines.groupby("accession", sort=False).agg(
        filing_date=("filing_date", "first"), issuer_cik=("issuer_cik", "first"), symbol=("symbol", "first"), total_value=("value", "sum"), n_lines=("value", "size"),
        trans_first=("trans_date", "min"), trans_last=("trans_date", "max"), n_owners=("n_owners", "first"), officer=("officer", "first"), director=("director", "first"),
        top_exec=("top_exec", "first"), aff10b5one=("aff10b5one", "first")).reset_index()
    ok = (f["officer"] | f["director"]) & ~f["aff10b5one"].isin(_FLAGGED) & (f["total_value"] >= min_value)
    return f[ok].reset_index(drop=True)


def chain_events(f: pd.DataFrame, days: int = CHAIN_DAYS) -> pd.DataFrame:
    """Per issuer, in filing-date order: a filing is an event unless the issuer already has an event less than `days` days earlier."""
    f = f.sort_values(["filing_date", "issuer_cik", "accession"]).reset_index(drop=True)
    last, keep = {}, np.zeros(len(f), dtype=bool)
    for i, (cik, d) in enumerate(zip(f["issuer_cik"], pd.to_datetime(f["filing_date"]))):
        prev = last.get(cik)
        if prev is None or (d - prev).days >= days:
            keep[i] = True
            last[cik] = d
    return f[keep].reset_index(drop=True)


def build_events(lines: pd.DataFrame, cikmap: pd.Series) -> tuple[pd.DataFrame, dict]:
    """The event table (columns EVENT_COLUMNS) of the stage windows and the funnel counts. `cikmap` maps an issuer CIK (int) to its panel ticker."""
    f = purchase_filings(lines)
    funnel = {"purchase_lines": int(len(lines)), "purchase_filings": int(len(f))}
    f = f[f["filing_date"] >= CHAIN_START]
    f = f.assign(ticker=f["issuer_cik"].map(cikmap))
    funnel["purchase_filings_from_chain_start"] = int(len(f))
    f = f[f["ticker"].notna()]
    funnel["with_panel_ticker"] = int(len(f))
    ev = chain_events(f)
    funnel["events_all_dates"] = int(len(ev))
    ev["stage"] = 0
    for k, (a, b) in STAGES.items():
        ev.loc[(ev["filing_date"] >= a) & (ev["filing_date"] <= b), "stage"] = k
    ev = ev[ev["stage"] > 0].copy()
    ev["public_date"], ev["cik"] = ev["filing_date"], ev["issuer_cik"]
    ev["lag_days"] = (pd.to_datetime(ev["filing_date"]) - pd.to_datetime(ev["trans_last"])).dt.days
    funnel["events_by_stage"] = {str(k): int(v) for k, v in ev.groupby("stage").size().items()}
    return ev[EVENT_COLUMNS].reset_index(drop=True), funnel

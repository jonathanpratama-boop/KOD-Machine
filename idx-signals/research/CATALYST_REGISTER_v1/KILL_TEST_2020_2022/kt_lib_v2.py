"""KILL_TEST_2020_2022 (PROTOCOL.md, protocol.json): the rules as pure functions. No network, no price file.

collect.py parses EDGAR with these functions and writes events.csv.gz; run.py applies the funnel, the timing, the
three abstention rules, the GO rule, the week-cluster bootstrap and the verdict with them. The live register's
helpers (idxsig.catalysts: is_operating, dilution_filings, market_value, coverage) are reused unchanged, so the
2020-2022 rules are the live rules evaluated with the panel's sessions.
"""
from __future__ import annotations

import html
import math
import re
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from idxsig import catalyst as e9  # noqa: E402
from idxsig import catalysts as cr  # noqa: E402

NY = cr.NY
FORM = "SC 13D"
SEED_ONLY_BEFORE, ENTRY_FROM, ENTRY_TO = "2020-07-01", "2020-07-01", "2022-11-30"
REPEAT_DAYS, OPERATING_DAYS, DILUTION_SESSIONS = 90, 550, 20
MOVED_ALREADY, MICROCAP_USD = 1.15, 50e6
GO_MIN = 300
RESAMPLES, BOOT_SEED = 10_000, 20261203
DILUTION_FROM, OPFORMS_FROM, EVIDENCE_TO = "2020-01-01", "2018-06-01", "2022-12-31"
INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}/form.idx"
HEADER_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{acc}-index-headers.html"
# the funnel, in the protocol's order; run.py reports one count per step
DROPS = ("SKIP_NO_HEADER", "SKIP_SEED_ONLY", "SKIP_OUTSIDE_WINDOW", "SKIP_NO_TICKER", "SKIP_REPEAT_90D",
         "SKIP_NOT_OPERATING", "SKIP_NO_SIGNAL_BAR")


# ------------------------------------------------------------------------------- form.idx
_LINE = re.compile(r"^(?P<form>\S+(?: \S+)*?)\s{2,}(?P<name>.*?)\s+(?P<cik>\d+)\s+(?P<date>\d{4}-\d{2}-\d{2})\s+"
                   r"(?P<path>edgar/data/\d+/(?P<acc>\d{10}-\d{2}-\d{6})\.txt)\s*$")


def quarter_url(quarter: str) -> str:
    return INDEX_URL.format(year=quarter[:4], q=quarter[-1])


def is_13d_line(line: str) -> bool:
    """Cheap pre-filter while streaming: an 'SC 13D' row (originals and amendments; parse_form_line decides)."""
    return line.startswith("SC 13D")


def parse_form_line(line: str) -> dict | None:
    """One form.idx row as {form, name, cik, date_filed, accession}, or None for a header or malformed line."""
    m = _LINE.match(line.rstrip("\r\n"))
    if not m:
        return None
    return {"form": m["form"], "name": m["name"].strip(), "cik": int(m["cik"]), "date_filed": m["date"],
            "accession": m["acc"]}


def originals(rows: list[dict]) -> list[dict]:
    """Original 'SC 13D' filings (not SC 13D/A, not 13G), one per accession, with every CIK form.idx lists for it."""
    out: dict[str, dict] = {}
    for r in rows:
        if r is None or r["form"] != FORM:
            continue
        rec = out.setdefault(r["accession"], {"accession": r["accession"], "date_filed": r["date_filed"],
                                              "index_cik": r["cik"], "index_ciks": []})
        rec["index_ciks"].append(r["cik"])
    return sorted(out.values(), key=lambda r: (r["date_filed"], r["accession"]))


def header_url(cik: int, accession: str) -> str:
    return HEADER_URL.format(cik=int(cik), acc_nodash=accession.replace("-", ""), acc=accession)


# ------------------------------------------------------------------------------- -index-headers.html
_TOP = re.compile(r"^(?P<head>[A-Z][A-Z /-]*):[ \t]*$", re.M)


def _sections_text(text: str) -> list[tuple[str, str]]:
    """The text header's top-level sections ('SUBJECT COMPANY:', 'FILED BY:', ...) as (heading, body)."""
    heads = list(_TOP.finditer(text))
    return [(h["head"], text[h.end():(heads[i + 1].start() if i + 1 < len(heads) else len(text))])
            for i, h in enumerate(heads)]


def parse_header(body: bytes | None) -> dict:
    """ACCEPTANCE-DATETIME (New York) and the SUBJECT COMPANY's CENTRAL INDEX KEY and name; the filers' names.
    Reads the SGML block (<SUBJECT-COMPANY> ... <CIK>) and falls back to the text block ('SUBJECT COMPANY:' ...
    'CENTRAL INDEX KEY:'), so the subject is found whichever order FILED BY and SUBJECT COMPANY come in."""
    raw = (body or b"").decode("utf-8", "replace")
    text = html.unescape(raw)
    acc = e9.header_acceptance(text.encode())
    accepted = e9.acceptance_ny(acc, "header").isoformat() if acc else None
    subject, name, filers = None, None, []
    m = re.search(r"<SUBJECT-COMPANY>(.*?)</SUBJECT-COMPANY>", text, re.S)
    if m:
        c, n = re.search(r"<CIK>\s*(\d+)", m.group(1)), re.search(r"<CONFORMED-NAME>([^\n<]*)", m.group(1))
        subject, name = (int(c.group(1)) if c else None), (n.group(1).strip() if n else None)
        filers = [x.strip() for f in re.findall(r"<FILED-BY>(.*?)</FILED-BY>", text, re.S)
                  for x in re.findall(r"<CONFORMED-NAME>([^\n<]*)", f)]
    else:
        for head, sec in _sections_text(text):
            c = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", sec)
            n = re.search(r"COMPANY CONFORMED NAME:\s*([^\n]*)", sec)
            if head == "SUBJECT COMPANY" and subject is None and c:
                subject, name = int(c.group(1)), (n.group(1).strip() if n else None)
            elif head == "FILED BY" and n:
                filers.append(n.group(1).strip())
    return {"accepted": accepted, "subject_cik": subject, "subject_name": name, "filed_by": filers}


# ------------------------------------------------------------------------------- compact rule inputs
def encode_filings(filings: pd.DataFrame | None) -> tuple[str, str]:
    """(dilution, opforms): every is_dilution filing dated DILUTION_FROM..EVIDENCE_TO as 'form|date|items', and
    every operating or fund report dated OPFORMS_FROM..EVIDENCE_TO as 'form|date', each ';'-joined (form|date|accession|items
    for the dilution list)."""
    if filings is None or not len(filings):
        return "", ""
    f = filings[(filings["filingDate"] >= OPFORMS_FROM) & (filings["filingDate"] <= EVIDENCE_TO)]
    dil = [f"{r.form}|{r.filingDate}|{r.accessionNumber}|{r.items.replace(';', ',')}" for r in f.itertuples()
           if r.filingDate >= DILUTION_FROM and e9.is_dilution(r.form, r.items)]
    forms = f["form"].str.upper()
    op = [f"{r.form}|{r.filingDate}" for r in f[forms.isin(cr.OPERATING_FORMS | cr.FUND_FORMS)].itertuples()]
    return ";".join(sorted(dil, key=lambda s: s.split("|")[1])), ";".join(sorted(op, key=lambda s: s.split("|")[1]))


def decode_filings(dilution: str, opforms: str) -> pd.DataFrame:
    """The stored lists back into the columns catalysts.is_operating and catalysts.dilution_filings read."""
    rows = []
    for k, x in enumerate(filter(None, str(dilution or "").split(";"))):
        form, day, acc, items = (x.split("|") + ["", "", ""])[:4]
        rows.append({"form": form, "filingDate": day, "items": items, "accessionNumber": acc})
    for k, x in enumerate(filter(None, str(opforms or "").split(";"))):
        form, day = (x.split("|") + [""])[:2]
        rows.append({"form": form, "filingDate": day, "items": "", "accessionNumber": f"op-{k}"})
    return pd.DataFrame(rows, columns=["form", "filingDate", "items", "accessionNumber"])


def encode_shares(points: list[dict]) -> str:
    """dei:EntityCommonStockSharesOutstanding facts filed up to EVIDENCE_TO as 'end|filed|val', ';'-joined."""
    pts = sorted((p for p in points if (p.get("filed") or "") <= EVIDENCE_TO and p.get("val")),
                 key=lambda p: (p["end"], p.get("filed") or ""))
    return ";".join(f"{p['end']}|{p.get('filed') or ''}|{float(p['val']):.0f}" for p in pts)


def decode_shares(s: str) -> list[dict]:
    out = []
    for x in filter(None, str(s or "").split(";")):
        end, filed, val = x.split("|")
        out.append({"end": end, "filed": filed, "val": float(val)})
    return out


# ------------------------------------------------------------------------------- funnel rules
def repeats(ev: pd.DataFrame, days: int = REPEAT_DAYS) -> pd.Series:
    """The earlier original on the same subject whose filing date is at most `days` calendar days before this one's
    (from the list itself, whatever that earlier filing's own fate), else ''. Calendar days on the SEC filing date, as
    catalysts.earlier_13d counts them live. Order is (acceptance, accession): the first one wins."""
    out = pd.Series("", index=ev.index, dtype=object)
    ok = ev[ev["subject_cik"].notna() & ev["accepted"].notna()]
    t = [datetime.fromisoformat(s).timestamp() for s in ok["accepted"]]
    d = [datetime.fromisoformat(str(x)[:10]).date() for x in ok["date_filed"]]
    for _, g in ok.assign(_t=t, _d=d).sort_values(["_t", "accession"]).groupby("subject_cik", sort=False):
        dates, accs = g["_d"].tolist(), g["accession"].tolist()
        for i in range(1, len(g)):
            prior = [accs[j] for j in range(i) if (dates[i] - dates[j]).days <= days]
            if prior:
                out[g.index[i]] = prior[-1]
    return out


def operating(dilution: str, opforms: str, day: str) -> bool:
    """catalysts.is_operating on the stored forms, `day` the acceptance date (New York)."""
    return cr.is_operating(decode_filings(dilution, opforms), day)


def first_panel_ticker(tickers: str, panel: set[str]) -> str | None:
    """The first of the subject's SEC tickers (SEC order) that is in the pinned panel."""
    return next((t for t in str(tickers or "").split(";") if t and t in panel), None)


# ------------------------------------------------------------------------------- timing
def _ny(day: str, hh: int, mm: int) -> datetime:
    return datetime.combine(datetime.fromisoformat(day).date(), time(hh, mm), tzinfo=NY)


def entry_session(accepted: datetime, sessions) -> str | None:
    """The first panel session whose 09:15 New York is after `accepted` (sessions sorted, ISO dates)."""
    s = np.asarray(sessions, dtype=str)
    i = int(np.searchsorted(s, accepted.astimezone(NY).date().isoformat(), side="left"))
    while i < len(s) and _ny(s[i], 9, 15) <= accepted:
        i += 1
    return str(s[i]) if i < len(s) else None


def prev_session(day: str, sessions) -> str | None:
    s = np.asarray(sessions, dtype=str)
    i = int(np.searchsorted(s, day, side="left"))
    return str(s[i - 1]) if i >= 1 else None


def position(accepted: datetime, signal: str, previous: str) -> str:
    """DURING (after the close of the session before the signal session, up to the signal session's 16:00 close),
    AFTER (after it); LATE (at or before that previous close) cannot occur with the entry rule above."""
    if accepted <= _ny(previous, 16, 0):
        return "LATE"
    return "DURING" if accepted <= _ny(signal, 16, 0) else "AFTER"


# ------------------------------------------------------------------------------- coverage class
def rules(dilution: str, opforms: str, shares: str, signal: str, accepted: datetime, pos: str, close: float,
          previous_close: float, close_traded: float) -> dict:
    """The live register's coverage class (catalysts.coverage) with its inputs, evaluated with data public by the
    acceptance date: DILUTION_RECENT (is_dilution filings from the 19th weekday before the signal session to the
    acceptance date), MOVED_ALREADY (DURING: signal close / previous close >= 1.15; AFTER: ratio 1), MICROCAP
    (latest shares fact filed by the acceptance date x the as-traded signal close < USD 50M; none: MV_UNKNOWN).
    `close` and `previous_close` are the panel's (split-adjusted) closes, `close_traded` the as-traded signal close."""
    day = accepted.astimezone(NY).date().isoformat()
    dil = cr.dilution_filings(decode_filings(dilution, opforms), signal, day)
    ratio = close / previous_close if pos == "DURING" else 1.0
    mv, point = cr.market_value(decode_shares(shares), close_traded, day)
    cov = cr.coverage(dil, ratio, mv)
    cov["inputs"] = {"dilution_filings": dil, "pre_entry_move": ratio - 1, "market_value_usd": mv, "shares_fact": point}
    return cov


# ------------------------------------------------------------------------------- the funnel, in the protocol's order
def funnel(ev: pd.DataFrame, sessions, panel: set[str]) -> pd.DataFrame:
    """Each filing's drop reason ('' = classified), first match wins: no header; filed before 2020-07-01 (seeds the
    repeat rule only); entry session outside 2020-07-01..2022-11-30; no SEC ticker in the panel; an original on the
    same subject in the 90 days before; not an operating issuer. Adds ticker, the sessions and the position."""
    ev = ev.copy()
    has = ev["accepted"].notna() & ev["subject_cik"].notna()
    acc = [datetime.fromisoformat(a) if h else None for a, h in zip(ev["accepted"], has)]
    ev["entry_session"] = [entry_session(a, sessions) if a else None for a in acc]
    ev["signal_session"] = [prev_session(e, sessions) if e else None for e in ev["entry_session"]]
    ev["previous_session"] = [prev_session(s, sessions) if s else None for s in ev["signal_session"]]
    ev["position"] = [position(a, s, p) if a and s and p else None
                      for a, s, p in zip(acc, ev["signal_session"], ev["previous_session"])]
    ev["ticker"] = [first_panel_ticker(t, panel) for t in ev["tickers"].fillna("")]
    ev["repeat_of"] = repeats(ev)
    day = [a.astimezone(NY).date().isoformat() if a else "" for a in acc]
    in_window = ev["entry_session"].astype(object).fillna("").astype(str).between(ENTRY_FROM, ENTRY_TO) & ev["signal_session"].notna()
    drop = pd.Series("", index=ev.index, dtype=object)

    def mark(code, mask):
        drop[(drop == "") & mask] = code

    mark("SKIP_NO_HEADER", ~has)
    mark("SKIP_SEED_ONLY", ev["date_filed"].astype(str) < SEED_ONLY_BEFORE)
    mark("SKIP_OUTSIDE_WINDOW", ~in_window)
    mark("SKIP_NO_TICKER", ev["ticker"].isna())
    mark("SKIP_REPEAT_90D", ev["repeat_of"] != "")
    live = drop == ""
    ok = [operating(d, o, dd) if lv else True
          for d, o, dd, lv in zip(ev["dilution"].fillna(""), ev["opforms"].fillna(""), day, live)]
    mark("SKIP_NOT_OPERATING", ~pd.Series(ok, index=ev.index))
    ev["drop"] = drop
    return ev


def classify(ev: pd.DataFrame, bar) -> pd.DataFrame:
    """The coverage class of every filing the funnel kept. `bar(ticker, day)` gives (adjusted close, as-traded
    close) or None; a filing without the signal session's bar (or, DURING, the previous session's) is dropped as
    SKIP_NO_SIGNAL_BAR, since its rules cannot be evaluated."""
    ev = ev.copy()
    out = []
    for r in ev.itertuples():
        if r.drop:
            out.append((r.drop, None))
            continue
        sig = bar(r.ticker, r.signal_session)
        prev = bar(r.ticker, r.previous_session) if r.position == "DURING" else (sig[0], sig[1]) if sig else None
        if sig is None or prev is None or not (sig[0] > 0 and prev[0] > 0):
            out.append(("SKIP_NO_SIGNAL_BAR", None))
            continue
        out.append(("", rules(r.dilution if isinstance(r.dilution, str) else "", r.opforms if isinstance(r.opforms, str) else "",
                              r.shares if isinstance(r.shares, str) else "", r.signal_session,
                              datetime.fromisoformat(r.accepted), r.position, sig[0], prev[0], sig[1])))
    ev["drop"] = [d for d, _ in out]
    ev["coverage"] = [c for _, c in out]
    ev["cls"] = [c["class"] if c else "" for c in ev["coverage"]]
    for rule in ("DILUTION_RECENT", "MOVED_ALREADY", "MICROCAP"):
        ev[rule] = [bool(c["rules"][rule]) if c else False for c in ev["coverage"]]
    ev["MV_UNKNOWN"] = [bool(c and c["inputs"]["market_value_usd"] is None) for c in ev["coverage"]]
    return ev


# ------------------------------------------------------------------------------- statistic and verdict
def week_id(days) -> np.ndarray:
    iso = pd.to_datetime(pd.Series(list(days))).dt.isocalendar()
    return (iso.year.astype(int) * 100 + iso.week.astype(int)).to_numpy()


class Boot:
    """Week-cluster bootstrap (research/US_INSIDER_BUY/ib_stats.Boot's construction): one fixed draw of resampled
    ISO weeks serves every statistic."""

    def __init__(self, weeks, resamples: int = RESAMPLES, seed: int = BOOT_SEED):
        self.weeks = np.array(sorted({int(w) for w in weeks}))
        self.pick = np.random.default_rng(seed).integers(0, len(self.weeks), size=(resamples, len(self.weeks)))

    def mean(self, v, w) -> dict:
        v, w = np.asarray(v, float), np.asarray(w, dtype=np.int64)
        i = np.searchsorted(self.weeks, w)
        if len(w) and not (self.weeks[np.minimum(i, len(self.weeks) - 1)] == w).all():
            raise ValueError("a week outside the bootstrap's week set")
        n = len(self.weeks)
        s, c = np.bincount(i, v, minlength=n), np.bincount(i, minlength=n).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            st = s[self.pick].sum(1) / c[self.pick].sum(1)
        st = st[np.isfinite(st)]
        se = float(st.std(ddof=1)) if len(st) > 1 else float("nan")
        t = float(v.mean() / se) if math.isfinite(se) and se > 1e-12 else float("nan")
        return {"n": int(len(v)), "weeks": int(len(np.unique(w))), "mean": float(v.mean()), "se": se, "t": t,
                "p_one_sided": p_one_sided(t), "lo95": float(np.percentile(st, 2.5)), "hi95": float(np.percentile(st, 97.5))}


def p_one_sided(t: float) -> float:
    """Normal one-sided p for 'mean excess > 0' (US_INSIDER_BUY's convention)."""
    return 0.5 * math.erfc(t / math.sqrt(2)) if math.isfinite(t) else float("nan")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def scored(res: pd.DataFrame) -> pd.DataFrame:
    """The statistic's sample: status EXITED with at least one scored control."""
    return res[(res["status"] == "EXITED") & (res["control_n"] >= 1) & res["excess"].notna()]


def go(n_scored_fire: int) -> bool:
    """The GO rule, on counts only: at least GO_MIN scored FIRE events."""
    return n_scored_fire >= GO_MIN


def verdict(n_scored_fire: int, mean_excess: float | None) -> str:
    if not go(n_scored_fire):
        return "INCONCLUSIVE"
    if mean_excess is None or not math.isfinite(mean_excess):
        return "INCONCLUSIVE"
    return "KILL" if mean_excess <= 0 else "NOT_KILLED"


def describe(f: pd.DataFrame) -> dict:
    """Mean with the bootstrap t over the sample's own ISO weeks, win rate with its Wilson interval, median."""
    if len(f) < 2:
        return {"n": int(len(f))}
    k = int((f["excess"] > 0).sum())
    w = week_id(f["entry_date"])
    return {**Boot(w).mean(f["excess"], w), "median": float(f["excess"].median()),
            "win_rate": k / len(f), "win_rate_wilson95": wilson(k, len(f)),
            "mean_net": float(f["net_return"].mean()), "mean_control": float(f["control_mean"].mean())}

"""Intraday data probe (PROBE_SPEC.md): coverage, identity, quote freshness and official halts for sample.csv.
Never computes a price change or a return.

  python3 research/INTRADAY_PROBE/probe.py --halts      Nasdaq halt history for the sample dates (no keys)
  python3 research/INTRADAY_PROBE/probe.py --alpaca     needs APCA_API_KEY_ID / APCA_API_SECRET_KEY in the
                                                        environment (never written anywhere)
Writes research/INTRADAY_PROBE/out/{halts.csv, coverage.csv, identity.csv, SUMMARY.json}.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
NY = ZoneInfo("America/New_York")
DATA = "https://data.alpaca.markets/v2/stocks"
ASSETS = "https://paper-api.alpaca.markets/v2/assets"
HALTS = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts&haltdate={}"


def get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                return e.code, e.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2 ** attempt)
    return 0, b""


def halts(dates: list[str]) -> pd.DataFrame:
    rows = []
    for d in dates:
        status, body = get(HALTS.format(datetime.strptime(d, "%Y-%m-%d").strftime("%m%d%Y")))
        items = re.findall(r"<item>(.*?)</item>", body.decode("utf-8", "replace"), re.S) if status == 200 else []
        field = lambda it, k: (re.search(rf"<ndaq:{k}>(.*?)</ndaq:{k}>", it, re.S) or [None, ""])[1].strip()  # noqa
        rows += [{"date": d, "symbol": field(it, "IssueSymbol"), "reason": field(it, "ReasonCode"),
                  "halt_time": field(it, "HaltTime"), "resume_quote": field(it, "ResumptionQuoteTime"),
                  "resume_trade": field(it, "ResumptionTradeTime"), "http": status} for it in items]
        if not items:
            rows.append({"date": d, "symbol": None, "reason": "NO RECORD", "http": status})
    return pd.DataFrame(rows)


def window(d: str, minutes: int) -> tuple[str, str]:
    start = datetime.fromisoformat(f"{d}T09:30:00").replace(tzinfo=NY)
    return start.isoformat(), (start + timedelta(minutes=minutes)).isoformat()


def paged(url: str, key: str, headers: dict) -> tuple[int, list]:
    out, token = [], None
    while True:
        status, body = get(url + (f"&page_token={token}" if token else ""), headers)
        if status != 200:
            return status, out
        js = json.loads(body)
        out += js.get(key) or []
        token = js.get("next_page_token")
        if not token:
            return 200, out


def longest_gap_s(times: list[str], start: str, end: str) -> float | None:
    ts = sorted(pd.to_datetime([start] + times + [end], utc=True))
    return float(max((b - a).total_seconds() for a, b in zip(ts, ts[1:]))) if len(ts) > 1 else None


def alpaca(sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    key, secret = os.environ.get("APCA_API_KEY_ID", ""), os.environ.get("APCA_API_SECRET_KEY", "")
    if not key or not secret:
        sys.exit("error: set APCA_API_KEY_ID and APCA_API_SECRET_KEY in the environment")
    h = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    cov = []
    for r in sample.itertuples():
        s60, e60 = window(r.date, 60)
        s390, e390 = window(r.date, 390)
        q = lambda path, s, e, feed, extra="": (f"{DATA}/{urllib.parse.quote(r.ticker)}/{path}?start="  # noqa
                                               f"{urllib.parse.quote(s)}&end={urllib.parse.quote(e)}&feed={feed}"
                                               f"&limit=10000{extra}")
        st_sip1, sip1 = paged(q("bars", s60, e60, "sip", "&timeframe=5Min"), "bars", h)
        st_sipd, sipd = paged(q("bars", s390, e390, "sip", "&timeframe=5Min"), "bars", h)
        st_iex1, iex1 = paged(q("bars", s60, e60, "iex", "&timeframe=5Min"), "bars", h)
        st_tr, trades = paged(q("trades", s60, e60, "iex"), "trades", h)
        st_qt, quotes = paged(q("quotes", s60, e60, "iex"), "quotes", h)
        cov.append({"date": r.date, "ticker": r.ticker, "group": r.group,
                    "http": max(st_sip1, st_sipd, st_iex1, st_tr, st_qt),
                    "sip_first_hour_bars": len(sip1), "sip_session_bars": len(sipd), "iex_first_hour_bars": len(iex1),
                    "iex_trades_first_hour": len(trades),
                    "iex_longest_trade_gap_s": longest_gap_s([t["t"] for t in trades], s60, e60),
                    "iex_quote_updates_first_hour": len(quotes),
                    "iex_longest_quote_age_s": longest_gap_s([x["t"] for x in quotes], s60, e60)})
    ident = []
    for tk in sorted(sample.ticker.unique()):
        status, body = get(f"{ASSETS}/{urllib.parse.quote(tk)}", h)
        js = json.loads(body) if status == 200 else {}
        ident.append({"ticker": tk, "http": status, "status": js.get("status"), "name": js.get("name"),
                      "class": js.get("class"), "exchange": js.get("exchange"), "tradable": js.get("tradable")})
    return pd.DataFrame(cov), pd.DataFrame(ident)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--halts", action="store_true")
    ap.add_argument("--alpaca", action="store_true")
    args = ap.parse_args()
    sample = pd.read_csv(HERE / "sample.csv", dtype={"ticker": str})
    OUT.mkdir(exist_ok=True)
    summary_path = OUT / "SUMMARY.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    if args.halts:
        hl = halts(sorted(sample.date.unique()))
        hl.to_csv(OUT / "halts.csv", index=False)
        names = set(sample.ticker)
        summary["halts"] = {"dates_with_records": int(hl[hl.reason != "NO RECORD"].date.nunique()),
                            "dates": int(sample.date.nunique()), "halts": int((hl.reason != "NO RECORD").sum()),
                            "sampled_names_halted": hl[hl.symbol.isin(names)][["date", "symbol", "reason"]]
                            .to_dict(orient="records")}
    if args.alpaca:
        cov, ident = alpaca(sample)
        cov.to_csv(OUT / "coverage.csv", index=False)
        ident.to_csv(OUT / "identity.csv", index=False)
        traded = cov[cov.sip_session_bars > 0]
        summary["alpaca"] = {
            "pairs": int(len(cov)), "pairs_with_any_sip_bar": int(len(traded)),
            "sip_first_hour_complete_share": float((traded.sip_first_hour_bars == 12).mean()) if len(traded) else None,
            "by_group": {g: {"pairs": int(len(x)), "any_sip": int((x.sip_session_bars > 0).sum()),
                             "median_iex_trades_first_hour": float(x.iex_trades_first_hour.median()),
                             "median_longest_quote_age_s": float(x.iex_longest_quote_age_s.median())
                             if x.iex_longest_quote_age_s.notna().any() else None}
                         for g, x in cov.groupby("group")}}
    summary_path.write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

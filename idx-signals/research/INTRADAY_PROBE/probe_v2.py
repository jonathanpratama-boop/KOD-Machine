"""Intraday data probe, corrected (PROBE_CORRECTION_1.md). Coverage, dated identity and quote freshness for
sample.csv; never computes a price change or a return. Each run writes a new out/run-<UTC stamp>/ directory.

Usage (from idx-signals/): APCA_API_KEY_ID=... APCA_API_SECRET_KEY=... python3 research/INTRADAY_PROBE/probe_v2.py
(keys only from the environment; never written anywhere)
"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import probe as v1  # noqa: E402  (frozen helpers: get, NY, DATA, ASSETS)

PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
FIRST_HOUR, SESSION = 60, 390
MATCH_TOL = 0.02


def bounds(d: str, minutes: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(datetime.fromisoformat(f"{d}T09:30:00").replace(tzinfo=v1.NY))
    return start, start + timedelta(minutes=minutes)


def in_window(stamps: list[str], start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    """Timestamps with start <= t < end (the bar stamped at `end` belongs to the next window)."""
    ts = pd.to_datetime(stamps, utc=True)
    return [t for t in ts if start <= t < end]


def longest_gap_s(ts: list[pd.Timestamp], start: pd.Timestamp, end: pd.Timestamp) -> float:
    pts = sorted([start, *ts, end])
    return float(max((b - a).total_seconds() for a, b in zip(pts, pts[1:])))


def fetch(path: str, ticker: str, d: str, minutes: int, feed: str, headers: dict, extra: str = "") -> dict:
    """All pages of one endpoint; status per page kept, `complete` only if every page returned 200."""
    start, end = bounds(d, minutes)
    url = (f"{v1.DATA}/{urllib.parse.quote(ticker)}/{path}?start={urllib.parse.quote(start.isoformat())}"
           f"&end={urllib.parse.quote(end.isoformat())}&feed={feed}&asof={d}&limit=10000{extra}")
    key = {"bars": "bars", "trades": "trades", "quotes": "quotes"}[path]
    items, statuses, token = [], [], None
    while True:
        status, body = v1.get(url + (f"&page_token={token}" if token else ""), headers)
        statuses.append(status)
        if status != 200:
            break
        js = json.loads(body)
        items += js.get(key) or []
        token = js.get("next_page_token")
        if not token:
            break
    return {"items": items, "statuses": statuses, "complete": all(s == 200 for s in statuses)}


def expected(sample: pd.DataFrame) -> pd.DataFrame:
    """Panel rows for the sampled (date, ticker): traded that day per the panel, and its as-traded close."""
    p = pd.read_csv(PANEL, usecols=["date", "ticker", "close", "unit_factor"], dtype={"ticker": str},
                    keep_default_na=False, na_values=[""])
    p = p[p.date.isin(set(sample.date))]
    p["traded_close"] = p.close * p.unit_factor
    return sample.merge(p[["date", "ticker", "traded_close"]], on=["date", "ticker"], how="left")


def summarise(cov: pd.DataFrame) -> dict:
    panel = cov[cov.group != "identity"]
    exp = panel[panel.expected_to_trade]
    ident = cov[cov.group == "identity"]
    return {
        "pairs": int(len(cov)),
        "panel_pairs_expected_to_trade": int(len(exp)),
        "sip_first_hour_complete_share_of_expected": float((exp.sip_first_hour_bars == 12).mean()) if len(exp) else None,
        "panel_pairs_expected_but_no_sip_data": int((exp.sip_session_bars == 0).sum()),
        "endpoints_incomplete": int((~cov[[c for c in cov if c.endswith("_complete")]].all(axis=1)).sum()),
        "identity_match_panel": cov.identity.value_counts().to_dict(),
        "identity_set": {"DATA": int((ident.sip_session_bars > 0).sum()),
                         "NO DATA": int((ident.sip_session_bars == 0).sum())},
        "by_group": {g: {"pairs": int(len(x)),
                         "median_iex_trades_first_hour": float(x.iex_trades_first_hour.median()),
                         "median_longest_trade_gap_s": float(x.iex_longest_trade_gap_s.median()),
                         "median_longest_quote_age_s": float(x.iex_longest_quote_age_s.median())}
                     for g, x in cov.groupby("group")},
        "halts": "see out/SUMMARY.json (b89c51a): 11 of 12 dates with records; 2022-06-03 UNKNOWN",
    }


def main() -> int:
    key, secret = os.environ.get("APCA_API_KEY_ID", ""), os.environ.get("APCA_API_SECRET_KEY", "")
    if not key or not secret:
        sys.exit("error: set APCA_API_KEY_ID and APCA_API_SECRET_KEY in the environment")
    h = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    run = HERE / "out" / f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    run.mkdir(parents=True, exist_ok=False)
    sample = expected(pd.read_csv(HERE / "sample.csv", dtype={"ticker": str}))
    rows = []
    for r in sample.itertuples():
        s1, e1 = bounds(r.date, FIRST_HOUR)
        sS, eS = bounds(r.date, SESSION)
        ep = {"sip_hour": fetch("bars", r.ticker, r.date, FIRST_HOUR, "sip", h, "&timeframe=5Min"),
              "sip_day": fetch("bars", r.ticker, r.date, SESSION, "sip", h, "&timeframe=5Min"),
              "iex_trades": fetch("trades", r.ticker, r.date, FIRST_HOUR, "iex", h),
              "iex_quotes": fetch("quotes", r.ticker, r.date, FIRST_HOUR, "iex", h)}
        day = [b for b in ep["sip_day"]["items"] if sS <= pd.Timestamp(b["t"]) < eS]
        trades = in_window([t["t"] for t in ep["iex_trades"]["items"]], s1, e1)
        quotes = in_window([q["t"] for q in ep["iex_quotes"]["items"]], s1, e1)
        ref = r.traded_close
        last = float(day[-1]["c"]) if day else None
        if r.group == "identity":
            identity = "UNVERIFIED" if day else "UNKNOWN"
        elif not day:
            identity = "NO DATA"
        else:
            identity = "MATCH" if abs(last / ref - 1) <= MATCH_TOL else "MISMATCH"
        row = {"date": r.date, "ticker": r.ticker, "group": r.group,
               "expected_to_trade": bool(pd.notna(ref)) if r.group != "identity" else None,
               "sip_first_hour_bars": len(in_window([b["t"] for b in ep["sip_hour"]["items"]], s1, e1)),
               "sip_session_bars": len(day), "identity": identity,
               "iex_trades_first_hour": len(trades), "iex_longest_trade_gap_s": longest_gap_s(trades, s1, e1),
               "iex_quote_updates_first_hour": len(quotes), "iex_longest_quote_age_s": longest_gap_s(quotes, s1, e1)}
        for name, e in ep.items():
            row[f"{name}_statuses"] = ",".join(map(str, e["statuses"]))
            row[f"{name}_pages"] = len(e["statuses"])
            row[f"{name}_complete"] = e["complete"]
        rows.append(row)
    cov = pd.DataFrame(rows)
    cov.to_csv(run / "coverage.csv", index=False)
    ident = []
    for tk in sorted(sample.ticker.unique()):
        status, body = v1.get(f"{v1.ASSETS}/{urllib.parse.quote(tk)}", h)
        js = json.loads(body) if status == 200 else {}
        ident.append({"ticker": tk, "http": status, "status_today": js.get("status"), "name_today": js.get("name"),
                      "class_today": js.get("class"), "exchange_today": js.get("exchange")})
    pd.DataFrame(ident).to_csv(run / "assets_today.csv", index=False)
    summary = summarise(cov)
    (run / "SUMMARY.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

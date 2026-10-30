"""LEARNER v2.4 (KOD-LEARNER-v2.4, research/LEARNER_v2/protocol_v2_4.json): the one live challenger. v2.4 is v2.3 with
the chart block of research/TA_HISTORY_v1 and supersedes it before v2.3 sealed any forecast (ADDENDUM_4.md).

One question, decided from research/PATH_HISTORY_v1 before any live outcome existed: for a US stock that just closed
30% or more higher (the Speculation Register's SPEC_US sets, sealed under register v1.1 so that the next session's
close is recorded), will it close at least 10% lower at the next session, when fewer than half of its twins do
(NEXT_DUMP10_1)? Its companion is the same question over the 5-session plan (DUMP10_5, which LEARNER v2.2 also
forecasts, so the two versions are compared on the same sets).

Beside v2.2, which keeps running untouched: its own ledger (paper/learner_v3.jsonl), its own protocol and warm start,
and v2.2's model, anchor, gate and call code imported as a library. What is new:

- features from three free sources beside the sealed set: the scan's own feature frame (the opening gap, the market's
  day, how many stocks spiked), the scan's price pull (volatility before the spike, the spike in units of it, earlier
  spikes, the up-streak, distance from the 120-session high, listing age) and EDGAR and FINRA before the entry open
  (an 8-K that day, offerings, a shelf, a 424B5, a reverse split, short-sale volume, turnover against shares
  outstanding), each with its provenance (manifest, payload and response hashes) in the forecast;
- a warm start from the history study's US events, through the same feature code, capped as v2.2's is;
- a pre-declared benchmark beside every forecast: the same model on volatility and market context only, so the
  learner's extra information can be measured against it;
- one gate for the headline (daily blocks of resolution: the question resolves every session) with its own 5%
  budget; the companion's gate is monitoring, not a claim;
- training rows take their features from the learner's own earlier forecasts (hash-chained), so verify retrains from
  the registers and this ledger alone; a new forecast's features are recomputed by verify wherever the raw inputs
  are still present and taken as recorded (and counted) where they are not.

Everything v2.2 never does, v2.3 never does: no outcome is computed here (the register grades), no tuning on running
numbers, no holdout, no orders.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import catalyst as e9
from . import catalysts as cr
from . import learner2 as L2
from . import paper
from . import learner_evaluation as evaluation
from . import speculation as spec
from .execution import Market
from .learner2 import Row, _clip, _logit, _num, _prob, _same, anchor_fit, call_of
from .provenance import MANIFESTS, PKG_ROOT, RAW, sha256_bytes, sha256_file, utc_stamp
from .rules import moonshot_g

PROTOCOL_JSON = PKG_ROOT / "research" / "LEARNER_v2" / "protocol_v2_4.json"  # supersedes v2.3 (ADDENDUM_4.md)
HISTORY = PKG_ROOT / "research" / "LEARNER_v2" / "warmstart_v4" / "events_us.csv.gz"
HISTORY_SHA256 = "e13eae758ee610bc6caec87e65ebdc86924ea17dd3026c6660983075cad68faf"  # research/LEARNER_v2/warmstart_v4/BUILD.json
LEDGER = paper.PAPER / "learner_v3.jsonl"
REPORT = paper.PAPER / "LEARNER_V3.md"
VERSION = "LEARNER-v2.4"
RECORD = "LEARNER3_FORECAST"
FAMILY = "SPEC_US"
REGISTER_PROTOCOLS = ("KOD-SPEC-REGISTER-v1.1",)  # sets whose cone has the next session's close
HEADLINE, COMPANION = "NEXT_DUMP10_1", "DUMP10_5"
STATEMENTS = {HEADLINE: ("DOWN10_1", "NEXT1", "1"), COMPANION: ("FADE10_5", "BASE5", "5")}  # -> (base, window, class)
THESIS = {HEADLINE: "it closes at least 10% below the signal close at the next session, when most of its twins do not",
          COMPANION: "its 5-session plan ends at least 10% down, when most of its twins do not"}
BLOCKS = {"1": (1, 1), "5": (7, 1)}  # horizon class -> (days per observation, lag in observations)
GATES = ("PATH/1", "PATH/5")
CLAIM_GATE = "PATH/1"
GATE = L2.GATE
CALL = L2.CALL
N_CAP = 300  # history's total weight per statement, in live outcomes
LOOKBACK = 120  # sessions of bars the live pull always covers (a 200-day pull): every bar feature stays inside it
EDGAR_YEARS = 3
FINRA_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{day}.txt"
FRAMES_URL = "https://data.sec.gov/api/xbrl/frames/dei/EntityCommonStockSharesOutstanding/shares/{frame}.json"
NEWS_FORMS = {"8-K", "8-K/A", "6-K", "6-K/A"}
OFFER_FORMS = {"S-1", "S-1/A", "S-1MEF", "F-1", "F-1/A", "S-3", "F-3", "S-3ASR", "424B1", "424B3", "424B4", "424B5"}
SHELF_FORMS = {"S-3", "F-3", "S-3ASR"}
ALL_FORMS = NEWS_FORMS | OFFER_FORMS
EPOCH = L2.EPOCH
VERIFY_TOL = L2.VERIFY_TOL

P0 = ("s_ret1", "s_ret5", "s_ret20", "s_dd60", "log_volr", "s_cpos", "log_adv")
P1 = ("gap", "vol20_pre", "spike_z", "log_price", "spikes60", "streak", "dist_high120", "age120", "breadth", "mkt_ret")
E_US = ("filing_8k", "offering90", "shelf3y", "b5_12m", "revsplit6m", "short_ratio", "short_abn", "log_turnover",
        "log_shares", "has_edgar", "has_short", "has_shares")
CHART = ("rsi14", "macd_hist", "stoch_k14", "bollinger_b")  # v2.4 (research/TA_HISTORY_v1: the block adds)
# (mean, sd) of each raw chart indicator over the 6,225 warm-start events (features only, no outcome), frozen: a live
# value is scaled as (raw - mean) / sd, clipped to +-4, so the history rows and the live sets share one scale
CHART_SCALE = {"rsi14": (66.780278, 16.715989), "macd_hist": (0.020247, 0.051156), "stoch_k14": (0.713125, 0.239647),
               "bollinger_b": (1.077134, 0.417362)}
FEATURES = P0 + P1 + E_US + CHART
BENCH = ("vol20_pre", "spike_z", "s_ret1", "mkt_ret", "breadth")  # the pre-declared volatility-and-context benchmark
BENCH_IDX = [FEATURES.index(k) for k in BENCH]
LABELS = {**{k: L2.LABELS[k] for k in P0},
          "gap": "opening gap (the move came at the open)", "vol20_pre": "volatility before the spike",
          "spike_z": "the spike in units of that volatility", "log_price": "price level",
          "spikes60": "earlier spikes in the last 60 sessions", "streak": "consecutive up closes",
          "dist_high120": "distance below the 120-session high", "age120": "listing age (capped at 120 sessions)",
          "breadth": "how many stocks spiked that day", "mkt_ret": "the market's own move that day",
          "filing_8k": "an 8-K (or 6-K) that day or the day before", "offering90": "an offering filing in the last 90 days",
          "shelf3y": "a shelf registration in the last 3 years", "b5_12m": "a 424B5 prospectus supplement in the last year",
          "revsplit6m": "a reverse split in the last 6 months", "short_ratio": "FINRA short-sale share of volume that day",
          "short_abn": "that share against its 20-session median", "log_turnover": "volume against shares outstanding",
          "log_shares": "shares outstanding", "has_edgar": "EDGAR filings were read", "has_short": "FINRA data was read",
          "has_shares": "a share count was found", "rsi14": "RSI(14)", "macd_hist": "MACD histogram",
          "stoch_k14": "close within its 14-session high-low range (Stochastic %K)", "bollinger_b": "Bollinger %B(20, 2)"}


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8")), sha256_file(PROTOCOL_JSON)


def lines(path: Path | None = None) -> list[dict]:
    path = LEDGER if path is None else path
    return paper.ledger_lines(path) if path.exists() else []


def share_group(task: str) -> str | None:
    """Both statements share one DUMP slope block (each keeps its own deviation and intercept)."""
    return "DUMP"


# ------------------------------------------------------------------------------- features
def frame_features(s: dict, frame: pd.DataFrame) -> dict:
    """From the scan's own feature frame (committed, hash-bound to the scan): the sealed set's price features as v2.2
    reads them, the opening gap, the market's median day return and how many stocks the detector flagged."""
    x = L2.features({**s, "direction": 1})
    out = dict(zip(L2.FEATURES[:len(P0)], (float(v) for v in x[:len(P0)])))
    row = frame[frame["ticker"].astype(str) == str(s["ticker"])]
    if row.empty:
        raise ValueError(f"{s['ticker']} is not in the scan's feature frame")
    row = row.iloc[0]
    fresh = frame["fresh"].astype(str).str.lower().isin(("true", "1"))
    ret1 = pd.to_numeric(frame.loc[fresh, "ret1"], errors="coerce")
    flagged = frame["G2_RET30"].astype(str).str.lower().isin(("true", "1")) if "G2_RET30" in frame else pd.Series(False, index=frame.index)
    gap = _num(row.get("gap"), None)
    close = _num(row.get("close"), None)
    out.update({"gap": _clip((gap or 0.0) / 0.30, -3, 3),
                "log_price": _clip(math.log10(close) - 0.5, -3, 3) if close and close > 0 else 0.0,
                "breadth": _clip(math.log1p(int(flagged.sum())) / 3.0, 0, 2),
                "mkt_ret": _clip(float(ret1.median()) / 0.03, -3, 3) if ret1.notna().any() else 0.0})
    return out


@lru_cache(maxsize=4)
def _market(manifest_name: str) -> tuple[Market, np.ndarray]:
    """The scan's price pull as the scan saw it (decision preprocessing), with the detector's flags."""
    df, _ = paper.load_recent(MANIFESTS / manifest_name, "US", purpose="decision")
    m = paper._market(df, "US")
    f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
    flag = moonshot_g.family_flags(f)["G2_RET30"] & m.tradeable
    return m, flag


def bar_features(m: Market, flag: np.ndarray, n: int, d: int) -> dict:
    """From one name's bars through session d, every lookback inside LOOKBACK sessions so that a 200-day live pull
    and the full history panel give the same numbers."""
    lo = max(0, d - LOOKBACK + 1)
    present = m.present[n, lo: d + 1]
    close, prev = m.close[n, lo: d + 1], m.prev[n, lo: d + 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(present & (prev > 0) & (close > 0), np.log(close / prev), np.nan)
        ret1 = np.where(present & (prev > 0), close / prev - 1, np.nan)
        level = np.exp(np.nancumsum(np.nan_to_num(logret)))
    k = d - lo  # the signal session inside the slice
    pre = logret[max(0, k - 20): k]
    pre = pre[np.isfinite(pre)]
    vol = float(np.std(pre, ddof=1)) if len(pre) >= 15 else None
    r1 = float(ret1[k]) if np.isfinite(ret1[k]) else 0.0
    spike_z = min(r1 / vol, 50.0) if vol and vol > 0 else None
    spikes = int(flag[n, max(0, d - 60): d].sum())
    streak = 0
    for j in range(k, -1, -1):
        if present[j] and np.isfinite(ret1[j]) and ret1[j] > 0:
            streak += 1
        else:
            break
    lv = level[:k + 1][present[:k + 1]]
    dist = float(level[k] / lv.max() - 1) if len(lv) and lv.max() > 0 else 0.0
    out = {"vol20_pre": _clip((vol or 0.0) / 0.10, 0, 5), "spike_z": _clip((spike_z or 0.0) / 10.0, 0, 5),
           "spikes60": min(spikes, 3) / 3.0, "streak": min(streak, 10) / 10.0, "dist_high120": _clip(dist / 0.5, -2, 0),
           "age120": int(present.sum()) / float(LOOKBACK)}
    raw = chart_raw(m, n, d)
    for key, v in raw.items():
        sc = CHART_SCALE.get(key)
        out[key] = 0.0 if (v is None or sc is None) else _clip((v - sc[0]) / sc[1], -4, 4)
    return out


def chart_raw(m: Market, n: int, d: int) -> dict:
    """The four chart indicators of TA_HISTORY_v1 at the close of d, on the reference chain, inside the same LOOKBACK
    window: RSI(14) (Wilder), the MACD(12, 26, 9) histogram over the level, Stochastic %K(14) on highs and lows
    scaled onto the chain, Bollinger %B(20, 2). None where fewer than 30 sessions are present."""
    lo = max(0, d - LOOKBACK + 1)
    present = m.present[n, lo: d + 1]
    close, prev = m.close[n, lo: d + 1], m.prev[n, lo: d + 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(present & (prev > 0) & (close > 0), np.log(close / prev), 0.0)
        level = np.exp(np.cumsum(logret))
        hi = np.where(present & (close > 0), m.high[n, lo: d + 1] / close, np.nan) * level
        lw = np.where(present & (close > 0), m.low[n, lo: d + 1] / close, np.nan) * level
    out = dict.fromkeys(CHART)
    if int(present.sum()) < 30 or not present[-1]:
        return out
    c = pd.Series(level[present])
    diff = c.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
    dn = (-diff.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
    out["rsi14"] = float(100.0 if dn == 0 else 100 - 100 / (1 + up / dn))
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    out["macd_hist"] = float((macd - macd.ewm(span=9, adjust=False).mean()).iloc[-1] / c.iloc[-1])
    h14, l14 = hi[present][-14:], lw[present][-14:]
    span = float(np.nanmax(h14) - np.nanmin(l14)) if np.isfinite(h14).any() and np.isfinite(l14).any() else 0.0
    out["stoch_k14"] = float((c.iloc[-1] - np.nanmin(l14)) / span) if span > 0 else None
    ma, sd = float(c.iloc[-20:].mean()), float(c.iloc[-20:].std())
    out["bollinger_b"] = float((c.iloc[-1] - (ma - 2 * sd)) / (4 * sd)) if sd > 0 else None
    return out


def edgar_features(filings: pd.DataFrame | None, shares: list[dict], short: pd.Series | None, session: str,
                   prev_session: str, vol_traded: float | None, splits: list[tuple[str, float]]) -> dict:
    """From filings dated up to the session (forms and dates only), XBRL share counts, FINRA's daily short-sale share
    and the name's split events. `splits`: (effective session, numerator / denominator)."""
    d = date.fromisoformat(session)
    out = {k: 0.0 for k in E_US}
    if filings is not None and len(filings):
        out["has_edgar"] = 1.0
        fd, form = filings["filingDate"].astype(str), filings["form"].astype(str).str.upper()
        out["filing_8k"] = float((form.isin(NEWS_FORMS) & fd.isin([prev_session, session])).any())
        out["offering90"] = float((form.isin(OFFER_FORMS) & (fd > (d - timedelta(days=90)).isoformat()) & (fd <= session)).any())
        out["shelf3y"] = float((form.isin(SHELF_FORMS) & (fd > (d - timedelta(days=3 * 365)).isoformat()) & (fd <= session)).any())
        out["b5_12m"] = float(((form == "424B5") & (fd > (d - timedelta(days=365)).isoformat()) & (fd <= session)).any())
    elif filings is not None:
        out["has_edgar"] = 1.0
    out["revsplit6m"] = float(any((d - timedelta(days=180)).isoformat() < eff <= session and ratio <= 1 / 1.5
                                  for eff, ratio in splits))
    cand = [p for p in shares if p["end"] <= (d - timedelta(days=LOOKBACK)).isoformat() and float(p["val"]) > 0]
    if cand:
        last = max(cand, key=lambda p: p["end"])
        if not any(last["end"] < eff <= session for eff, _ in splits):
            out["has_shares"] = 1.0
            out["log_shares"] = _clip(math.log10(float(last["val"])) - 7.5, -3, 3)
            if vol_traded and vol_traded > 0:
                out["log_turnover"] = _clip(math.log10(vol_traded / float(last["val"])) + 1.5, -3, 3)
    if short is not None and session in short.index:
        out["has_short"] = 1.0
        r = float(short.loc[session])
        out["short_ratio"] = _clip((r - 0.4) / 0.2, -3, 3)
        before = short[short.index < session].tail(20)
        if len(before) >= 5:
            out["short_abn"] = _clip((r - float(before.median())) / 0.15, -3, 3)
    return out


def vector(parts: dict) -> np.ndarray:
    return np.array([float(parts[k]) for k in FEATURES], dtype=float)


# ------------------------------------------------------------------------------- live data, with provenance
class Context:
    """The free data a batch of forecasts reads, fetched once with the declared SEC contact and hashed."""

    def __init__(self, asof: str, log=None):
        self.asof, self.log = asof, (log or (lambda s: None))
        self.day_dir = RAW / "sec" / f"learner3-{asof[:10]}"
        self.client = None
        self.ticker_map = None
        self.frames: dict[str, list[dict]] = {}
        self.responses: dict[str, str] = {}

    def _client(self):
        if self.client is None:
            self.client = cr.sec_client(self.day_dir)
            st, body = self.client.get(cr.TICKERS_URL)
            self._note(cr.TICKERS_URL, st, body)
            if st != 200:
                raise RuntimeError(f"EDGAR ticker map: HTTP {st}")
            self.ticker_map = cr.ticker_maps(body)[1]
        return self.client

    def _note(self, url: str, status: int, body: bytes) -> None:
        self.responses[url] = f"{status}:{sha256_bytes(body)}"

    def filings(self, ticker: str, session: str) -> tuple[pd.DataFrame | None, int | None]:
        c = self._client()
        cik = self.ticker_map.get(ticker.upper().replace(".", "-"))
        if cik is None:
            return None, None
        st, main = c.get(cr.SUBMISSIONS_URL.format(cik=cik))
        self._note(cr.SUBMISSIONS_URL.format(cik=cik), st, main)
        if st != 200 or not main:
            return None, cik
        start = (date.fromisoformat(session) - timedelta(days=EDGAR_YEARS * 365)).isoformat()
        chunks = []
        for name in e9.chunk_names(main, start, session):
            url = f"https://data.sec.gov/submissions/{name}"
            s2, b2 = c.get(url)
            self._note(url, s2, b2)
            if s2 == 200 and b2:
                chunks.append(b2)
        try:
            fr = e9.parse_submissions(main, chunks)
        except (ValueError, KeyError):
            return None, cik
        fr = fr[fr["form"].str.upper().isin(ALL_FORMS) & (fr["filingDate"] >= start) & (fr["filingDate"] <= session)]
        return fr[["form", "filingDate"]].reset_index(drop=True), cik

    def shares(self, cik: int | None, session: str) -> list[dict]:
        """dei:EntityCommonStockSharesOutstanding points for the CIK from the two calendar quarters that ended at
        least LOOKBACK days before the session."""
        if cik is None:
            return []
        d = date.fromisoformat(session) - timedelta(days=LOOKBACK)
        out = []
        for back in (0, 1):
            q = (d.month - 1) // 3 + 1 - back
            y = d.year
            if q <= 0:
                q, y = q + 4, y - 1
            frame = f"CY{y}Q{q}I"
            if frame not in self.frames:
                url = FRAMES_URL.format(frame=frame)
                st, body = self._client().get(url)
                self._note(url, st, body)
                self.frames[frame] = json.loads(body)["data"] if st == 200 and body else []
            out += [{"end": r["end"], "val": r["val"], "frame": frame} for r in self.frames[frame] if int(r["cik"]) == int(cik)]
        return out

    def short(self, ticker: str, sessions: list[str]) -> pd.Series | None:
        """FINRA's consolidated daily short-sale share of volume for the name over `sessions` (files cached by day)."""
        out = {}
        for day in sessions:
            rows = _finra_day(day, self.log)
            if rows is None:
                continue
            self.responses[FINRA_URL.format(day=day.replace("-", ""))] = rows[0]
            r = rows[1].get(ticker.upper())
            if r and r[1] > 0:
                out[day] = r[0] / r[1]
        return pd.Series(out, dtype=float) if out else None


def _finra_day(day: str, log=None) -> tuple[str, dict] | None:
    """(sha256, {symbol: (short volume, total volume)}) for one FINRA daily file, cached under data/raw/finra."""
    cache = RAW / "finra" / f"CNMSshvol{day.replace('-', '')}.txt"
    if not cache.exists():
        url = FINRA_URL.format(day=day.replace("-", ""))
        body = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "KOD-Machine research"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(2 * 2 ** attempt)
        if body is None:
            return None
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(body)
    body = cache.read_bytes()
    table = {}
    for line in body.decode("utf-8", "replace").splitlines()[1:]:
        p = line.split("|")
        if len(p) < 5:
            continue
        try:  # volumes are integers in the 2020-2023 files and fractional (consolidated across venues) from 2026
            table[p[1].replace(".", "-")] = (float(p[2] or 0), float(p[4]))
        except ValueError:
            continue
    return sha256_bytes(body), table


def set_features(s: dict, scan: dict, ctx: Context) -> tuple[np.ndarray, dict]:
    """The feature vector of a sealed set and the provenance of everything it was read from."""
    frame = spec.scan_features(scan)
    parts = frame_features(s, frame)
    manifest = scan["data"]["manifest"]
    m, flag = _market(manifest)
    tickers = list(m.tickers.astype(str))
    dates = list(m.dates.astype(str))
    if s["ticker"] not in tickers or s["signal_session"] not in dates:
        raise ValueError(f"{s['ticker']} {s['signal_session']}: not in the scan's price pull {manifest}")
    n, d = tickers.index(s["ticker"]), dates.index(s["signal_session"])
    parts.update(bar_features(m, flag, n, d))
    _, records = paper.read_manifest(MANIFESTS / manifest)
    rec = next((r for r in records if r.get("ticker") == s["ticker"]), {})
    splits = _splits(rec)
    filings, cik = ctx.filings(s["ticker"], s["signal_session"])
    shares = ctx.shares(cik, s["signal_session"])
    short = ctx.short(s["ticker"], dates[max(0, d - 20): d + 1])
    vol = float(m.volume[n, d]) if np.isfinite(m.volume[n, d]) else None
    parts.update(edgar_features(filings, shares, short, s["signal_session"], dates[d - 1] if d else s["signal_session"],
                                vol, splits))
    prov = {"frame": {"file": scan["features_file"], "sha256": scan["features_sha256"]},
            "manifest": {"file": manifest, "sha256": scan["data"]["manifest_sha256"]},
            "payload": {"path": rec.get("path"), "sha256": rec.get("sha256")},
            "cik": cik, "responses": dict(sorted(ctx.responses.items()))}
    return vector(parts), prov


def _splits(rec: dict) -> list[tuple[str, float]]:
    """A name's split events from its cached Yahoo payload: (effective New York session, numerator / denominator)."""
    path = rec.get("path")
    if not path or not (PKG_ROOT / path).exists():
        return []
    from .us_actions import NEW_YORK

    payload = json.loads((PKG_ROOT / path).read_text(encoding="utf-8"))["chart"]["result"][0]
    out = []
    for ev in ((payload.get("events") or {}).get("splits") or {}).values():
        local = datetime.fromtimestamp(int(ev["date"]), timezone.utc).astimezone(NEW_YORK)
        out.append((local.date().isoformat(), float(ev["numerator"]) / float(ev["denominator"])))
    return out


# ------------------------------------------------------------------------------- outcomes and rows
def outcomes(records: list[dict], asof: str) -> dict:
    return L2.outcomes(records, asof)


def outcome_of(outc: dict, set_id: str, stmt: str) -> tuple[bool, str] | None:
    """A statement as the stock's own move of its register base statement (learner2.own_move)."""
    return L2.own_move(outc, set_id, STATEMENTS[stmt][0])


@lru_cache(maxsize=1)
def history_rows() -> tuple[Row, ...]:
    """The pinned warm start (research/LEARNER_v2/warmstart_v3): the history study's US events through this module's
    feature code, each statement's rows sharing a total weight of at most N_CAP."""
    if sha256_file(HISTORY) != HISTORY_SHA256:
        raise RuntimeError(f"{HISTORY.name} does not match the pinned sha256: the warm start is not the frozen one")
    with gzip.open(HISTORY, "rt", encoding="utf-8", newline="") as fh:
        records = list(csv.DictReader(fh))
    rows = []
    for r in records:
        x = np.array([float(r[k]) for k in FEATURES])
        for stmt in STATEMENTS:
            y = _num(r.get(f"y_{stmt}"), None)
            if y is not None:
                rows.append(Row("PATH", f"{FAMILY}:{stmt}", "hist:path_history_v1", x, 0.5, float(y), 1.0))
    n = Counter(r.task for r in rows)
    return tuple(r._replace(w=min(1.0, N_CAP / n[r.task])) for r in rows)


def live_rows(records: list[dict], lrecs: list[dict], asof: str) -> list[Row]:
    """Every graded statement of every set this learner forecast, resolved before asof, with the features the forecast
    recorded (hash-chained), one row per set and statement."""
    outc = outcomes(records, asof)
    rows, seen = [], set()
    for f in lrecs:
        if f.get("type") != RECORD or f["made_at"] >= asof or f["set_id"] in seen:
            continue
        seen.add(f["set_id"])
        x = np.array([float(f["features"][k]) for k in FEATURES])
        for stmt, fc in f["forecasts"].items():
            o = outcome_of(outc, f["set_id"], stmt)
            if o is None:
                continue
            rows.append(Row("PATH", f"{FAMILY}:{stmt}", f"{FAMILY}:{stmt}", x, float(fc["p0"]), float(o[0]), 1.0))
    return rows


class State(L2.State):
    pass


def train(records: list[dict], lrecs: list[dict], asof: str) -> tuple[L2.State, L2.Model | None]:
    """(the learner's state, the benchmark model): the same rows, priors and penalties; the benchmark sees only the
    BENCH columns."""
    live = live_rows(records, lrecs, asof)
    rows = list(history_rows()) + live
    model = L2.Model("PATH", rows, share=share_group) if rows else None
    bench = L2.Model("PATH", [r._replace(x=r.x[BENCH_IDX]) for r in rows], share=share_group) if rows else None
    by_task: dict[str, list[Row]] = {}
    for r in live:
        by_task.setdefault(r.task, []).append(r)
    anchors = {t: anchor_fit(rs) for t, rs in sorted(by_task.items())}
    info = {"live_rows": {t: round(sum(r.w for r in rs), 4) for t, rs in sorted(by_task.items())},
            "history_rows": {t: round(sum(r.w for r in history_rows() if r.task == t), 4) for t in sorted({r.task for r in history_rows()})}}
    return L2.State({"PATH": model}, anchors, info), bench


def live_centres(lrecs: list[dict], asof: str) -> dict[str, np.ndarray]:
    """Per statement, the mean recorded features of every forecast made before asof (strictly: a batch never centres
    on itself, so verify and the forecast agree): the reference a forecast is measured from, features only, so the
    learner's average move over the live population is zero by construction."""
    acc: dict[str, list[np.ndarray]] = {}
    for f in lrecs:
        if f.get("type") == RECORD and f["made_at"] < asof:
            x = np.array([float(f["features"][k]) for k in FEATURES])
            for stmt in f["forecasts"]:
                acc.setdefault(f"{FAMILY}:{stmt}", []).append(x)
    return {t: np.mean(v, axis=0) for t, v in sorted(acc.items())}


# ------------------------------------------------------------------------------- earned confidence
def forward_pairs(records: list[dict], lrecs: list[dict], asof: str) -> list[dict]:
    outc = outcomes(records, asof)
    resolutions = paper.latest_resolutions(records, asof=asof)
    sets = {r["set_id"]: r for r in records if r.get("type") == "CATALYST_SET"}
    out, seen = [], set()
    for f in lrecs:
        if f.get("type") != RECORD or f["made_at"] >= asof:
            continue
        s = sets.get(f["set_id"])
        if f["set_id"] in seen or s is None or s.get("record_hash") != f["set_record_hash"] or f["made_at"] >= s["entry_cutoff"]:
            continue
        seen.add(f["set_id"])
        for stmt, fc in f["forecasts"].items():
            o = outcome_of(outc, f["set_id"], stmt)
            if o is None or o[1] <= f["made_at"]:
                continue
            out.append({"set_id": f["set_id"], "event_key": f["set_id"], "statement": stmt, "kind": "PATH",
                        "family": FAMILY, "session": f["signal_session"], "window": STATEMENTS[stmt][1],
                        "resolved_at": o[1], "y": float(o[0]), "anchor": fc["anchor"], "raw": fc["raw"],
                        "forecast_record_hash": f.get("record_hash"),
                        "resolution_record_hash": (resolutions.get(paper.resolution_key({**s, "window": STATEMENTS[stmt][1]}))
                                                   or resolutions.get((f["set_id"], STATEMENTS[stmt][1]), {})).get("record_hash"),
                        "bench": fc["bench"], "published": fc["published"], "call": fc.get("call") or {}, "w": 1.0})
    return out


def block_of(ts: str, days: int) -> int:
    return (date.fromisoformat(ts[:10]) - EPOCH).days // days


def block_end(block: int, days: int) -> str:
    return f"{(EPOCH + timedelta(days=days * (block + 1))).isoformat()}T00:00:00Z"


def observations(pairs: list[dict], asof: str, days: int, key: str = "raw", against: str = "anchor") -> list[tuple[float, float, int]]:
    """One observation per block of `days` of resolution that has ended by asof: the mean Brier gain of `key` over
    `against`, the mean `against` Brier and the number of pairs; a set counts once per statement."""
    seen, blocks = set(), {}
    for p in sorted(pairs, key=lambda p: (p["resolved_at"], p["set_id"], p["statement"])):
        k = (p["set_id"], p["statement"])
        if k in seen:
            continue
        seen.add(k)
        b = block_of(p["resolved_at"], days)
        if block_end(b, days) <= asof:
            blocks.setdefault(b, []).append(p)
    return [(float(np.mean([(p[against] - p["y"]) ** 2 - (p[key] - p["y"]) ** 2 for p in ps])),
             float(np.mean([(p[against] - p["y"]) ** 2 for p in ps])), len(ps)) for _, ps in sorted(blocks.items())]


def gate(pairs: list[dict], key: str, asof: str) -> tuple[float, dict]:
    """alpha for "PATH/<class>": 0 below t_min populated blocks or while closed; otherwise min(proof, recent lower
    bound) / mean anchor Brier / skill_full, clipped to 0..1 (learner2's gate, on daily or weekly blocks)."""
    cls = key.split("/")[1]
    days, lag = BLOCKS[cls]
    obs = observations([p for p in pairs if STATEMENTS[p["statement"]][2] == cls], asof, days)
    d = np.array([o[0] for o in obs], dtype=float)
    info = {"observations": len(obs), "mean_gain": float(d.mean()) if len(d) else None, "lower": None,
            "skill_lower": None, "recent_lower": None, "open": False}
    if len(d) < GATE["t_min"]:
        return 0.0, info
    b = float(np.mean([o[1] for o in obs]))
    best, opened, recent = L2.gate_path(d, days / 7.0, lag)[-1]
    info.update({"lower": best, "skill_lower": best / b if b > 0 else None, "recent_lower": recent, "open": opened})
    if not opened or b <= 0:
        return 0.0, info
    return float(_clip(min(best, recent) / b / GATE["skill_full"], 0.0, 1.0)), info


def gates(records: list[dict], lrecs: list[dict], asof: str) -> dict[str, tuple[float, dict]]:
    pairs = forward_pairs(records, lrecs, asof)
    return {k: gate(pairs, k, asof) for k in GATES}


# ------------------------------------------------------------------------------- forecasting
def forecast_set(s: dict, x: np.ndarray, state: L2.State, bench: L2.Model | None, gate_alpha: dict[str, float],
                 centres: dict[str, np.ndarray]) -> dict:
    priors = {c["id"]: float(c["prior"]) for c in s.get("cone", [])}
    out = {}
    for stmt, (base, window, cls) in STATEMENTS.items():
        task = f"{FAMILY}:{stmt}"
        p0 = priors.get(base, 0.5)
        anchor = L2.anchor_prob(state, task, p0)
        m = state.models.get("PATH")
        centre = centres.get(task)
        dev, sd, parts = (0.0, 0.0, np.zeros(len(FEATURES))) if m is None else m.deviation(task, x, centre)
        bdev = 0.0 if bench is None else bench.deviation(task, x[BENCH_IDX], None if centre is None else centre[BENCH_IDX])[0]
        raw = _prob(_logit(anchor) + dev)
        dev = _logit(raw) - _logit(anchor)
        braw = _prob(_logit(anchor) + bdev)
        alpha = gate_alpha.get(f"PATH/{cls}", 0.0)
        order = np.argsort(-np.abs(parts))[:3]
        why = [{"feature": FEATURES[j], "label": LABELS[FEATURES[j]], "logit": round(float(parts[j]), 6)}
               for j in order if abs(parts[j]) >= 0.01]  # 6 decimals, like every stored number, so VERIFY_TOL covers a boundary flip
        call = call_of(dev, sd, alpha)
        if call["side"]:
            call["thesis"] = THESIS[stmt] if call["side"] == "BACK" else f"not: {THESIS[stmt]}"
            call["reads"] = "AVOID the stock" if call["side"] == "BACK" else "the stock holds"
        lo, hi = _prob(_logit(anchor) + dev - CALL["z"] * sd), _prob(_logit(anchor) + dev + CALL["z"] * sd)
        out[stmt] = {"kind": "PATH", "window": window, "base": base, "p0": round(p0, 6), "anchor": round(anchor, 6),
                     "raw": round(raw, 6), "raw_90": [round(lo, 6), round(hi, 6)], "deviation": round(dev, 6),
                     "sd": round(sd, 6), "bench": round(braw, 6), "alpha": round(alpha, 6),
                     "published": round(_prob(_logit(anchor) + alpha * dev), 6), "call": call, "why": why}
    return out


def eligible(records: list[dict]) -> list[dict]:
    return [s for s in records if s.get("type") == "CATALYST_SET" and s.get("family") == FAMILY
            and (s.get("protocol") or {}).get("id") in REGISTER_PROTOCOLS]


def forecast_records(now: datetime, records: list[dict] | None = None, lrecs: list[dict] | None = None,
                     ctx: Context | None = None, log=None) -> tuple[list[dict], list[str]]:
    """One LEARNER3_FORECAST for every eligible set still before its cutoff that has none yet, and notes on any set
    skipped. Each records the ledger states it was computed from, its features and their provenance."""
    proto, sha = protocol()
    if records is None:
        cat, spc = cr.cat_lines(), spec.spec_lines()
        records = [L2.as_set(r) for r in cat] + [L2.as_set(r) for r in spc]
        inputs = {"catalysts": L2._head(cat), "speculations": L2._head(spc)}
    else:
        inputs = {"records": L2._head(records)}
    lrecs = lines() if lrecs is None else lrecs
    asof = utc_stamp(now.astimezone(timezone.utc))
    done = {f["set_id"] for f in lrecs if f.get("type") == RECORD}
    todo = [s for s in eligible(records) if s["entry_cutoff"] > asof and s["set_id"] not in done]
    if not todo:
        return [], []
    scans = {r["scan_id"]: r for r in paper.ledger_lines() if r["type"] == "SCAN"}
    ctx = ctx or Context(asof, log)
    state, bench = train(records, lrecs, asof)
    g = gates(records, lrecs, asof)
    centres = live_centres(lrecs, asof)
    out, notes = [], []
    for s in todo:
        scan = scans.get(s["scan_id"])
        if scan is None:
            notes.append(f"{s['set_id']}: its scan is not in the ledger; skipped")
            continue
        try:
            x, prov = set_features(s, scan, ctx)
        except (ValueError, RuntimeError, KeyError, FileNotFoundError) as exc:
            notes.append(f"{s['set_id']}: features could not be read ({exc}); skipped")
            continue
        out.append(_record(s, asof, proto, sha, inputs, state, bench, g, centres, x, prov))
    return out, notes


def _record(s, asof, proto, sha, inputs, state, bench, g, centres, x, prov) -> dict:
    fc = forecast_set(s, x, state, bench, {k: v[0] for k, v in g.items()}, centres)
    return {"type": RECORD, "learner": VERSION, "protocol": {"id": proto["protocol_id"], "sha256": sha},
            "history": {"file": str(HISTORY.relative_to(PKG_ROOT)) if HISTORY.is_relative_to(PKG_ROOT) else HISTORY.name,
                        "sha256": HISTORY_SHA256},
            "set_id": s["set_id"], "set_record_hash": s["record_hash"], "family": FAMILY, "market": "US",
            "ticker": s.get("ticker"), "signal_session": s["signal_session"], "entry_cutoff": s["entry_cutoff"],
            "made_at": asof, "inputs": inputs, "training": state.info,
            "gate": {k: {"alpha": round(v[0], 6), **{kk: (None if vv is None else round(vv, 6) if isinstance(vv, float) else vv)
                                                       for kk, vv in v[1].items()}} for k, v in g.items()},
            "features": {k: round(float(v), 6) for k, v in zip(FEATURES, x)}, "provenance": prov, "forecasts": fc}


def append(recs: list[dict], timestamper=None) -> tuple[list[Path], list[dict]]:
    stored = paper.append(recs, path=LEDGER, timestamper=timestamper)
    tokens = [paper.TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")]
    return [LEDGER, *[t for t in tokens if t.exists()]], stored


def one_line(r: dict) -> str:
    h = r["forecasts"][HEADLINE]
    c = h["call"]
    tail = (f"; {'LIVE' if c['live'] else 'shadow'} {c['reads']}: {c['thesis']}" if c["side"] else "; no call")
    why = "; ".join(f"{w['label']} {w['logit']:+.2f}" for w in h["why"])
    return (f"{r['ticker']} ({r['signal_session']}): dump tomorrow {h['raw']:.2f} (base {h['anchor']:.2f}, benchmark "
            f"{h['bench']:.2f}, published {h['published']:.2f}){tail}" + (f" [{why}]" if why else ""))


# ------------------------------------------------------------------------------- verification
def recompute_features(f: dict) -> np.ndarray | None:
    """The forecast's features again from the raw inputs it names, where they are still present here; None where
    they are not (then the recorded features are taken as recorded)."""
    prov = f.get("provenance") or {}
    payload = (prov.get("payload") or {}).get("path")
    manifest = (prov.get("manifest") or {}).get("file")
    day_dir = RAW / "sec" / f"learner3-{f['made_at'][:10]}"
    if not (payload and (PKG_ROOT / payload).exists() and manifest and (MANIFESTS / manifest).exists() and day_dir.exists()):
        return None
    scans = {r["scan_id"]: r for r in paper.ledger_lines() if r["type"] == "SCAN"}
    sets = {r["set_id"]: r for r in spec.spec_lines() if r["type"] == "SPECULATION_SET"}
    s, scan = sets.get(f["set_id"]), None
    if s is not None:
        scan = scans.get(s["scan_id"])
    if s is None or scan is None:
        return None
    ctx = Context(f["made_at"])
    ctx.client = cr.sec_client(day_dir)
    ctx.client.offline = True
    st, body = ctx.client.get(cr.TICKERS_URL)
    if st != 200:
        return None
    ctx.ticker_map = cr.ticker_maps(body)[1]
    x, _ = set_features(L2.as_set(s), scan, ctx)
    return x


def verify(path: Path | None = None, records: list[dict] | None = None, tol: float = VERIFY_TOL) -> list[str]:
    """The chain; one forecast per eligible set; every forecast reproduced, field by field, by retraining on exactly
    the ledger states it records with the features it recorded; those features recomputed from the raw inputs where
    they are present; the set sealed under a register version with the next session's close; made before the cutoff
    and externally timestamped before it where a token exists."""
    path = LEDGER if path is None else path
    proto, sha = protocol()
    if not path.exists():
        return evaluation.verify(claim_fn=claim, proto=proto, proto_sha=sha)
    problems = [f"{path.name}: {p}" for p in paper.verify_chain(path)]
    proto, sha = protocol()
    if records is None:
        cat, spc = cr.cat_lines(), spec.spec_lines()
    lrecs = paper.ledger_lines(path)
    evaluation_records = records if records is not None else [L2.as_set(r) for r in cat + spc]
    problems += evaluation.verify(claim_fn=claim, proto=proto, proto_sha=sha, records=evaluation_records, forecasts=lrecs,
                                  pair_fn=forward_pairs, headline=HEADLINE)
    seen, checker, unverified = set(), None, 0
    for i, f in enumerate(lrecs):
        if f.get("type") != RECORD:
            problems.append(f"{path.name}: unknown record type {f.get('type')!r}")
            continue
        sid = f["set_id"]
        if sid in seen:
            problems.append(f"{sid}: forecast twice")
        seen.add(sid)
        if f["protocol"]["sha256"] != sha:
            problems.append(f"{sid}: learner protocol sha256 differs from {PROTOCOL_JSON.relative_to(PKG_ROOT)}")
        if f["history"]["sha256"] != HISTORY_SHA256:
            problems.append(f"{sid}: warm start sha256 differs from the pinned one")
        inp = f.get("inputs") or {}
        if records is None:
            nc, ns = (inp.get("catalysts") or [None])[0], (inp.get("speculations") or [None])[0]
            ok = (isinstance(nc, int) and isinstance(ns, int) and nc <= len(cat) and ns <= len(spc)
                  and L2._head(cat[:nc]) == inp["catalysts"] and L2._head(spc[:ns]) == inp["speculations"])
            prefix = [L2.as_set(r) for r in cat[:nc]] + [L2.as_set(r) for r in spc[:ns]] if ok else None
        else:
            n = (inp.get("records") or [None])[0]
            ok = isinstance(n, int) and n <= len(records) and L2._head(records[:n]) == inp["records"]
            prefix = records[:n] if ok else None
        if prefix is None:
            problems.append(f"{sid}: the ledger state it records is not a state the registers passed through")
            continue
        s = next((r for r in prefix if r.get("type") == "CATALYST_SET" and r["set_id"] == sid), None)
        if s is None or s.get("record_hash") != f["set_record_hash"]:
            problems.append(f"{sid}: forecast binds no sealed set with that hash")
            continue
        if s not in eligible([s]):
            problems.append(f"{sid}: the set was not sealed under a register version with the next session's close")
        if f["made_at"] >= s["entry_cutoff"]:
            problems.append(f"{sid}: forecast made at {f['made_at']}, after the set's cutoff {s['entry_cutoff']}")
        state, bench = train(prefix, lrecs[:i], f["made_at"])
        g = gates(prefix, lrecs[:i], f["made_at"])
        centres = live_centres(lrecs[:i], f["made_at"])
        x = np.array([float(f["features"][k]) for k in FEATURES])
        again = _record(s, f["made_at"], proto, sha, inp, state, bench, g, centres, x, f.get("provenance"))
        body = {k: v for k, v in f.items() if k not in ("record_hash", "prev_hash")}
        diff = [k for k in sorted(set(body) | set(again)) if not _same(body.get(k), again.get(k), tol)]
        if diff:
            problems.append(f"{sid}: does not reproduce from the ledger states it records (possible peeking or an "
                            f"edit): {', '.join(diff)}")
        if records is None:
            try:
                x2 = recompute_features(f)
            except Exception:  # noqa: BLE001 - a raw input that cannot be read counts as absent
                x2 = None
            if x2 is None:
                unverified += 1
            elif not np.allclose(x2, x, atol=tol):
                bad = [k for k, a, b in zip(FEATURES, x, x2) if abs(a - b) > tol]
                problems.append(f"{sid}: recorded features differ from the raw inputs it names: {', '.join(bad)}")
        tokens = [(a, paper.TOKENS / f"{f.get('record_hash')}.{a}.tsr") for a in ("freetsa", "sectigo")]
        for a, tok in tokens:
            if not tok.exists():
                continue
            checker = checker or L2._timestamp_checker()
            try:
                when = utc_stamp(checker.verify(a, tok.read_bytes(), f["record_hash"].encode())) if checker else None
            except Exception:  # noqa: BLE001 - paper.verify_all reports a token that does not verify
                continue
            if when and when >= s["entry_cutoff"]:
                problems.append(f"{sid}: {a} timestamp {when} is not before the set's cutoff {s['entry_cutoff']}")
            break
    verify.unverified_features = unverified
    return problems


# ------------------------------------------------------------------------------- scoring and report
def _auc(p: np.ndarray, y: np.ndarray) -> float | None:
    pos, neg = int(y.sum()), int(len(y) - y.sum())
    if pos == 0 or neg == 0:
        return None
    r = pd.Series(p).rank(method="average").to_numpy()
    return float((r[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def claim(pairs: list[dict], rule: dict, seed: int = 20261029) -> dict:
    """The headline claim: AUC of the raw forecasts over resolved NEXT_DUMP10_1 pairs, its standard error from a
    bootstrap over signal sessions, z against 0.5, read at the pre-registered looks."""
    hp = [p for p in pairs if p["statement"] == HEADLINE]
    y = np.array([p["y"] for p in hp]); p_raw = np.array([p["raw"] for p in hp]); p_b = np.array([p["bench"] for p in hp])
    sessions = sorted({p["session"] for p in hp})
    out = {"n_pairs": len(hp), "n_sessions": len(sessions), "auc": _auc(p_raw, y) if len(hp) else None,
           "auc_bench": _auc(p_b, y) if len(hp) else None, "se": None, "z": None, "look": None, "verdict": "accumulating"}
    if len(hp) >= 20 and len(sessions) >= 5 and out["auc"] is not None:
        rng = np.random.default_rng(seed)
        by = {s: np.flatnonzero(np.array([p["session"] for p in hp]) == s) for s in sessions}
        draws = []
        for _ in range(1000):
            idx = np.concatenate([by[s] for s in rng.choice(sessions, len(sessions))])
            a = _auc(p_raw[idx], y[idx])
            if a is not None:
                draws.append(a)
        if len(draws) > 10:
            out["se"] = float(np.std(draws, ddof=1))
            out["z"] = (out["auc"] - 0.5) / out["se"] if out["se"] > 0 else None
    looks, zmin, mins = rule["looks"], rule["z_min"], rule["min_sessions"]
    reached = [k for k, n in enumerate(looks) if len(hp) >= n and len(sessions) >= mins[k]]
    if reached:
        k = reached[-1]
        out["look"] = looks[k]
        ok = out["z"] is not None and out["z"] >= zmin[k]
        out["verdict"] = (f"SKILL at the n>={looks[k]} look (z {out['z']:.2f} >= {zmin[k]})" if ok
                          else f"not shown at the n>={looks[k]} look" + (" (final)" if k == len(looks) - 1 else "; continues"))
    return out


def statistics(records: list[dict] | None = None, lrecs: list[dict] | None = None, asof: str | None = None) -> dict:
    proto, sha = protocol()
    if records is None:
        records = L2.all_records()
    lrecs = lines() if lrecs is None else lrecs
    asof = asof or utc_stamp()
    pairs = forward_pairs(records, lrecs, asof)
    g = gates(records, lrecs, asof)
    per = {}
    for stmt in STATEMENTS:
        sp = [p for p in pairs if p["statement"] == stmt]
        y = np.array([p["y"] for p in sp])
        days = BLOCKS[STATEMENTS[stmt][2]][0]
        def gain(key, against):
            obs = observations(sp, asof, days, key, against)
            d = np.array([o[0] for o in obs])
            return {"blocks": len(obs), "mean": float(d.mean()) if len(d) else None,
                    "se": float(L2.long_run_sd(d, 1) / math.sqrt(len(d))) if len(d) >= 2 else None}
        per[stmt] = {"n": len(sp), "rate": float(y.mean()) if len(sp) else None,
                     "auc": _auc(np.array([p["raw"] for p in sp]), y) if len(sp) else None,
                     "auc_bench": _auc(np.array([p["bench"] for p in sp]), y) if len(sp) else None,
                     "brier_gain_vs_anchor": gain("raw", "anchor"), "bench_gain_vs_anchor": gain("bench", "anchor"),
                     "brier_gain_vs_bench": gain("raw", "bench"), "calls": _calls(sp)}
    v22 = _v22_comparison(pairs)
    return {"protocol": {"id": proto["protocol_id"], "sha256": sha}, "learner": VERSION, "generated_at": asof,
            "outcome_view": {"semantics": paper.RESOLUTION_VIEW, "cutoff": asof},
            "n_forecasts": sum(f.get("type") == RECORD for f in lrecs), "n_pairs": len(pairs),
            "gates": {k: {"alpha": v[0], **v[1]} for k, v in g.items()}, "claim": evaluation.official(pairs, sha, asof, proto=proto, claim_fn=claim,
                records=records, forecasts=lrecs, pair_fn=forward_pairs, headline=HEADLINE),
            "descriptive_claim": {**claim(pairs, proto["claim"]), "verdict": "descriptive only; see frozen claim"},
            "statements": per, "v2_2_on_DUMP10_5": v22, "coverage": coverage(records, lrecs, asof),
            "features_unverifiable_here": getattr(verify, "unverified_features", None)}


def _calls(sp: list[dict]) -> dict:
    out = {"shadow": {"n": 0, "right": 0}, "live": {"n": 0, "right": 0}}
    for p in sp:
        c = p.get("call") or {}
        if not c.get("side"):
            continue
        k = "live" if c.get("live") else "shadow"
        out[k]["n"] += 1
        out[k]["right"] += int((p["y"] == 1.0) == (c["side"] == "BACK"))
    return out


def _v22_comparison(pairs: list[dict]) -> dict:
    """v2.2's raw DUMP10_5 forecasts on the same sets: a paired Brier difference (v2.3 minus v2.2, positive is better)."""
    v2 = {f["set_id"]: f["forecasts"].get(COMPANION, {}).get("raw") for f in L2.lines() if f.get("type") == L2.RECORD}
    both = [(p, v2[p["set_id"]]) for p in pairs if p["statement"] == COMPANION and v2.get(p["set_id"]) is not None]
    if not both:
        return {"n": 0}
    d = np.array([(v - p["y"]) ** 2 - (p["raw"] - p["y"]) ** 2 for p, v in both])
    return {"n": len(both), "mean_gain": float(d.mean()), "se": float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else None,
            "auc_v2_2": _auc(np.array([v for _, v in both]), np.array([p["y"] for p, _ in both])),
            "auc_v2_3": _auc(np.array([p["raw"] for p, _ in both]), np.array([p["y"] for p, _ in both]))}


def coverage(records: list[dict], lrecs: list[dict], asof: str) -> dict:
    done = {f["set_id"] for f in lrecs if f.get("type") == RECORD}
    due = [s["set_id"] for s in eligible(records) if s["entry_cutoff"] <= asof and s["set_id"] not in done
           and (s.get("sealed_at") or "") >= "2026-10-29T23:00:00Z"]
    return {"due_without_forecast": due, "n_due_without_forecast": len(due)}


def render(st: dict, lrecs: list[dict] | None = None) -> str:
    lrecs = lines() if lrecs is None else lrecs
    c = st["claim"]
    g = st["gates"][CLAIM_GATE]
    h = st["statements"][HEADLINE]
    out = [f"# {VERSION}: the one live challenger ({st['protocol']['id']}, protocol sha256 {st['protocol']['sha256'][:12]})", "",
           f"Generated {st['generated_at']}. Paper only; no orders.", "",
           "## The three plain answers", "",
           "**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower "
           "at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)", "",
           f"**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others "
           f"(AUC above 0.5, z >= {_fmt_zmin()} at the first look of {_fmt_looks(st)} resolved pairs), with the Brier gain over "
           "the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks "
           "published confidence needs 30 populated sessions of resolution.", "",
           f"**What evidence so far?** {st['n_forecasts']} forecasts sealed; {h['n']} headline outcomes resolved"
           + (f"; AUC {h['auc']:.3f} (benchmark {h['auc_bench']:.3f})" if h["auc"] is not None else "")
           + (f"; gate {'open' if g['open'] else 'closed'}, alpha {g['alpha']:.2f}, {g['observations']} of 30 sessions"
              if g["observations"] is not None else "")
           + f". Claim: {c['verdict']}" + (f" (z {c['z']:.2f}, n {c['n_pairs']})" if c["z"] is not None else "") + ".", ""]
    recs = [r for r in lrecs if r.get("type") == RECORD]
    if recs:
        last = max(r["signal_session"] for r in recs)
        out += [f"## Latest sets ({last})", ""]
        out += ["- " + one_line(r) for r in recs if r["signal_session"] == last]
        out.append("")
    out += ["## Appendix", "", "| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |",
            "|---|---:|---:|---:|---:|---|---|---|---|---|"]
    for stmt, p in st["statements"].items():
        def g_(x):
            return "n/a" if x["mean"] is None else f"{x['mean']:+.4f} ({'n/a' if x['se'] is None else f'{x['se']:.4f}'}; {x['blocks']} blocks)"
        out.append(f"| {stmt} | {p['n']} | {'n/a' if p['rate'] is None else f'{p['rate']:.3f}'} | "
                   f"{'n/a' if p['auc'] is None else f'{p['auc']:.3f}'} | {'n/a' if p['auc_bench'] is None else f'{p['auc_bench']:.3f}'} | "
                   f"{g_(p['brier_gain_vs_anchor'])} | {g_(p['bench_gain_vs_anchor'])} | {g_(p['brier_gain_vs_bench'])} | "
                   f"{p['calls']['shadow']['right']}/{p['calls']['shadow']['n']} | {p['calls']['live']['right']}/{p['calls']['live']['n']} |")
    out += ["", "Gates (confidence): " + "; ".join(f"**{k}** alpha {v['alpha']:.2f}, {v['observations']} observations, "
                                                   f"{'open' if v['open'] else 'closed'}" for k, v in st["gates"].items()) + ".", ""]
    v = st["v2_2_on_DUMP10_5"]
    if v.get("n"):
        out += [f"v2.2 against v2.3 on DUMP10_5, the same {v['n']} sets: paired Brier gain of v2.3 {v['mean_gain']:+.4f} "
                f"(se {'n/a' if v['se'] is None else f'{v['se']:.4f}'}); AUC v2.2 {v['auc_v2_2']} vs v2.3 {v['auc_v2_3']}.", ""]
    cov = st["coverage"]
    if cov["n_due_without_forecast"]:
        out += [f"Due sets without a forecast: {cov['n_due_without_forecast']} ({', '.join(cov['due_without_forecast'][:10])}).", ""]
    if st.get("features_unverifiable_here"):
        out += [f"Forecasts whose features could not be recomputed here (raw inputs absent): {st['features_unverifiable_here']}.", ""]
    return "\n".join(out) + "\n"


def _fmt_zmin() -> str:
    try:
        return str(protocol()[0]["claim"]["z_min"][0])
    except Exception:  # noqa: BLE001
        return "the pre-registered floor"


def _fmt_looks(st: dict) -> str:
    try:
        return "/".join(str(n) for n in protocol()[0]["claim"]["looks"])
    except Exception:  # noqa: BLE001
        return "the pre-registered"


def write_report() -> Path:
    REPORT.write_text(render(statistics()), encoding="utf-8")
    return REPORT



def freeze_evaluations(asof: str | None = None) -> list[dict]:
    """Explicit mutation; reports never create or replace planned decisions."""
    proto, sha = protocol()
    return evaluation.freeze(L2.all_records(), lines(), asof or utc_stamp(), proto, sha,
                             forward_pairs, claim, HEADLINE)

"""Daily panels for markets other than IDX: US equities (Yahoo) and crypto (Binance spot).

Same column set as the IDX panel, but prices stay floats (crypto trades at 1e-8) and come
split-adjusted from the source, so `previous` is simply the prior close (no reference-price
resets). Each build writes a new gzip file and a JSON manifest naming its inputs, QA and
quality tiers; nothing is overwritten.

QA, recorded in the manifest:
  - rows without a positive close are dropped;
  - a one-day spike that fully reverts (close more than 3x the prior close and the next close
    back below a third of it, or the mirror image) is a bad print and is dropped, because a
    fake +200% day would otherwise become a "moonshot";
  - crypto: the current UTC day (still forming) is dropped; stablecoins, fiat pairs and
    leveraged tokens are excluded from the universe.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .provenance import MANIFESTS, PANEL_DIR, PKG_ROOT, check_files, read_manifest, rel, sha256_file, utc_stamp

COLUMNS = ["date", "ticker", "source", "previous", "open", "high", "low", "close", "volume", "value", "frequency",
           "listed_shares", "tradable_shares"]
FORMAT = "panel-global-v1"
STABLE = {"USDC", "BUSD", "TUSD", "USDP", "PAX", "DAI", "FDUSD", "USDD", "UST", "USTC", "SUSD", "PYUSD", "AEUR",
          "EUR", "GBP", "AUD", "TRY", "BRL", "RUB", "UAH", "NGN", "ZAR", "BIDR", "IDRT", "BVND", "USDS", "USDSB",
          "EURI", "XUSD", "USD1", "BFUSD", "USDE"}
LEVERAGED = re.compile(r"(UP|DOWN|BULL|BEAR)$")
MIN_TRADED = 50


def _spikes(df: pd.DataFrame) -> pd.Series:
    """True on rows that are one-day spikes reverting the next day."""
    g = df.groupby("ticker")["close"]
    prev, nxt = g.shift(1), g.shift(-1)
    up = (df["close"] > 3 * prev) & (nxt < df["close"] / 3)
    down = (df["close"] < prev / 3) & (nxt > df["close"] * 3)
    return (up | down).fillna(False)


def _finish(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df[df["close"] > 0].sort_values(["ticker", "date"]).reset_index(drop=True)
    spikes = _spikes(df)
    dropped = df.loc[spikes, ["ticker", "date", "close"]]
    df = df[~spikes].reset_index(drop=True)
    df["previous"] = df.groupby("ticker")["close"].shift(1)
    traded_value = df["quote_volume"] if "quote_volume" in df else df["close"] * df["volume"]  # Binance reports it
    df["value"] = traded_value.where(df["volume"] > 0, 0.0)
    for col in ("frequency", "listed_shares", "tradable_shares"):
        df[col] = np.nan
    traded = df[df["volume"] > 0].groupby("date")["ticker"].nunique()
    sessions = traded[traded >= MIN_TRADED].index
    stubs = sorted(set(df["date"]) - set(sessions))
    df = df[df["date"].isin(sessions)].reset_index(drop=True)
    qa = {"spike_rows_dropped": int(len(dropped)),
          "spike_examples": [{"ticker": r.ticker, "date": str(r.date.date()), "close": float(r.close)}
                             for r in dropped.head(20).itertuples()],
          "non_session_dates_dropped": [str(d.date()) for d in stubs][:50], "non_session_dates_count": len(stubs)}
    return df[COLUMNS], qa


def load_us(manifest: Path) -> tuple[pd.DataFrame, dict]:
    _, records = read_manifest(manifest)
    frames = []
    for rec in records:
        if rec.get("http_status") != 200 or not rec.get("rows"):
            continue
        result = json.loads((PKG_ROOT / rec["path"]).read_text(encoding="utf-8"))["chart"]["result"][0]
        stamps = result.get("timestamp") or []
        if not stamps:
            continue
        q = result["indicators"]["quote"][0]
        offset = result["meta"].get("gmtoffset", -14400)
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(np.array(stamps) + offset, unit="s").normalize(),
            "ticker": rec["ticker"], "source": "yahoo",
            "open": pd.to_numeric(pd.Series(q.get("open")), errors="coerce"),
            "high": pd.to_numeric(pd.Series(q.get("high")), errors="coerce"),
            "low": pd.to_numeric(pd.Series(q.get("low")), errors="coerce"),
            "close": pd.to_numeric(pd.Series(q.get("close")), errors="coerce"),
            "volume": pd.to_numeric(pd.Series(q.get("volume")), errors="coerce").fillna(0.0),
        }).dropna(subset=["close"]).drop_duplicates("date", keep="last"))
    return pd.concat(frames, ignore_index=True), {"loaded_tickers": len(frames)}


def load_crypto(manifest: Path, now: datetime | None = None) -> tuple[pd.DataFrame, dict]:
    header, records = read_manifest(manifest)
    cutoff_ms = int((now or datetime.fromisoformat(header["finished_at"].replace("Z", "+00:00"))).timestamp() * 1000)
    frames, excluded = [], []
    for rec in records:
        if rec.get("symbol", "").startswith("_") or rec.get("http_status") != 200 or not rec.get("rows"):
            continue
        base = rec["base_asset"]
        if base in STABLE or LEVERAGED.search(base):
            excluded.append(rec["symbol"])
            continue
        rows = json.loads((PKG_ROOT / rec["path"]).read_text(encoding="utf-8"))
        rows = [r for r in rows if r[6] < cutoff_ms]  # close time before the pull: complete days only
        if not rows:
            continue
        a = np.array([[float(x) for x in r[:6]] + [float(r[7])] for r in rows])
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(a[:, 0], unit="ms").normalize(), "ticker": base, "source": "binance",
            "open": a[:, 1], "high": a[:, 2], "low": a[:, 3], "close": a[:, 4],
            "volume": a[:, 5], "quote_volume": a[:, 6], "status": rec["status"],
        }))
    df = pd.concat(frames, ignore_index=True)
    statuses = df.groupby("ticker")["status"].first()
    # traded value in USDT: Binance reports it directly
    df = df.drop(columns="status")
    dup = df.duplicated(["ticker", "date"])
    if dup.any():
        raise RuntimeError(f"{int(dup.sum())} duplicate (base, date) rows: two USDT pairs share a base asset")
    return df, {"excluded_stable_or_leveraged": sorted(excluded), "delisted_in_universe":
                sorted(statuses[statuses != "TRADING"].index)}


def build(market: str, manifest: Path, log=print) -> Path:
    problems = check_files(manifest)
    if problems:
        raise RuntimeError(f"{manifest.name}: {len(problems)} files differ from the manifest, e.g. {problems[:3]}")
    if market == "US":
        df, extra = load_us(manifest)
        survivorship = ("survivor-only: the universe is the Nasdaq Trader listing snapshot of the download day; "
                        "names delisted earlier are absent")
        tiers_label = "US_SURVIVOR"
    elif market == "CRYPTO":
        df, extra = load_crypto(manifest)
        survivorship = ("Binance USDT pairs including delisted ones still described by exchangeInfo "
                        f"({len(extra['delisted_in_universe'])} delisted/halted bases); pairs Binance dropped from "
                        "exchangeInfo entirely are absent")
        tiers_label = "CRYPTO_BINANCE"
    else:
        raise ValueError(market)
    panel, qa = _finish(df)
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    path = PANEL_DIR / f"panel_{market.lower()}-{stamp}.csv.gz"
    out = panel.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.10g")
    first, last = panel["date"].min().date().isoformat(), panel["date"].max().date().isoformat()
    meta = {
        "format": FORMAT, "market": market, "panel": rel(path), "sha256": sha256_file(path), "built_at": utc_stamp(),
        "inputs": {manifest.name: {"sha256": sha256_file(manifest), "path": rel(manifest)}},
        "rows": int(len(panel)), "tickers": int(panel["ticker"].nunique()), "sessions": int(panel["date"].nunique()),
        "first_session": first, "last_session": last, "source_boundary": last,
        "default_start": (panel["date"].min() + timedelta(days=120)).date().isoformat(),
        "survivorship": survivorship,
        "quality_tiers": [{"tier": tiers_label, "from": first, "to": last, "source": "yahoo" if market == "US" else "binance",
                           "survivorship": survivorship, "corporate_actions": "split-adjusted by the source"}],
        "known_limitations": [
            survivorship,
            "prices are split-adjusted by the source, not dividend-adjusted",
            "daily bars only: no intraday path, no halts (US LULD) or order-book depth",
            "costs are assumed per price tier (profiles.py), not measured spreads",
        ] + (["sessions are UTC days; the asset trades 24/7"] if market == "CRYPTO" else []),
        "qa": qa, **{k: v for k, v in extra.items() if k != "loaded_tickers"},
    }
    mpath = MANIFESTS / f"panel_{market.lower()}-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    log(f"{market} panel {rel(path)} rows {meta['rows']} tickers {meta['tickers']} sessions {meta['sessions']}")
    return mpath


def latest(market: str) -> Path:
    found = sorted(MANIFESTS.glob(f"panel_{market.lower()}-*.json"))
    if not found:
        raise FileNotFoundError(f"no {market} panel; run `python -m idxsig build-global-panel --market {market}`")
    return found[-1]


def load(manifest: Path) -> tuple[pd.DataFrame, dict]:
    meta = json.loads(Path(manifest).read_text(encoding="utf-8"))
    path = PKG_ROOT / meta["panel"]
    if sha256_file(path) != meta["sha256"]:
        raise RuntimeError(f"{meta['panel']} does not match the hash in {Path(manifest).name}")
    # Tickers are literal strings: pandas would read the Nasdaq symbol "NA" (and "NAN", "NULL") as missing.
    df = pd.read_csv(path, parse_dates=["date"], dtype={"ticker": str, "source": str}, keep_default_na=False,
                     na_values=[""])
    meta["_manifest"] = Path(manifest).name
    meta["_manifest_sha256"] = sha256_file(manifest)
    return df, meta

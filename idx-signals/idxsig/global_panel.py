"""Daily panels for markets other than IDX: US equities (Yahoo) and crypto (Binance spot).

Same column set as the IDX panel, but prices stay floats (crypto trades at 1e-8) and come
split-adjusted from the source, so `previous` is simply the prior close (no reference-price
resets). Each build writes a new gzip file and a JSON manifest naming its inputs, QA and
quality tiers; nothing is overwritten.

QA, recorded in the manifest:
  - rows without a positive close are dropped;
  - large moves are preserved: a later reversal is not contemporaneous proof of a bad print;
  - old future-informed deletion remains available only as _finish_legacy_v1 for forensic reproduction;
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

from .provenance import MANIFESTS, PANEL_DIR, PKG_ROOT, check_files, read_manifest, rel, sha256_file, utc_stamp, write_csv_gz_exclusive

COLUMNS = ["date", "ticker", "source", "previous", "open", "high", "low", "close", "volume", "value", "frequency",
           "listed_shares", "tradable_shares"]
FORMAT = "panel-global-v2"
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


def _finish_legacy_v1(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
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


def _finish(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Causal close-time preprocessing; never remove a row using future returns.

    This repairs temporal preprocessing only. Provider vintages, price units,
    universe selection and the close-time coverage heuristic remain separate
    validity requirements. Legacy v1 is explicit forensic reproduction only.
    """
    df = df[df["close"] > 0].sort_values(["ticker", "date"]).reset_index(drop=True)
    df["previous"] = df.groupby("ticker")["close"].shift(1)
    traded_value = df["quote_volume"] if "quote_volume" in df else df["close"] * df["volume"]
    df["value"] = traded_value.where(df["volume"] > 0, 0.0)
    for col in ("frequency", "listed_shares", "tradable_shares"):
        df[col] = np.nan
    traded = df[df["volume"] > 0].groupby("date")["ticker"].nunique()
    sessions = traded[traded >= MIN_TRADED].index
    stubs = sorted(set(df["date"]) - set(sessions))
    df = df[df["date"].isin(sessions)].reset_index(drop=True)
    qa = {"preprocessing_version": "causal-close-v2", "spike_rows_dropped": 0,
          "large_move_policy": "preserve; reversion is not proof of a bad print",
          "non_session_dates_dropped": [str(d.date()) for d in stubs][:50],
          "non_session_dates_count": len(stubs)}
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
    write_csv_gz_exclusive(path, out, index=False, float_format="%.10g")  # fails, touching nothing, if the stamp is taken
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


REPAIR_FORMAT = "panel-global-v3-reconciled"
# v2 (panels built before 2026-10-09) checked the schedule by file hash and raw-manifest NAME and
# looked only at the statuses of the records present. v3 binds every input by sha256, requires
# exactly one matching verification record per relevant provider event (a missing one is
# UNRESOLVED_NO_RECORD), enforces the share-count research window, and labels the quarantine as
# outcome-dependent. Earlier panel manifests keep their format and remain reproducible.


def build_us_repair(raw_manifest: Path, schedule_manifest: Path, end: str, coverage_manifest: Path | None = None,
                    log=print) -> Path:
    """E2-US repair panel (research/E2/repair): the original Yahoo payloads, causal preprocessing
    (_finish: no row is removed because of a later bar), nothing after `end` read into the panel,
    and three measurement columns no rule can see:

      unit_factor          adjusted -> as-traded price factor (us_actions.unit_factors) from the
                           provider's split records; later records restore earlier units only
      qa_reverting_spike   the legacy bad-print test (reverts the next session), kept as a flag
                           known one session later, never used to delete or as a decision input
    The manifest lists names whose split records effective after the window's first session
    lack SEC corroboration (unit_quarantine); a run decides whether to leave them out.
    """
    from . import us_actions

    problems = check_files(raw_manifest)
    if problems:
        raise RuntimeError(f"{raw_manifest.name}: {len(problems)} files differ from the manifest, e.g. {problems[:3]}")
    smeta = json.loads(Path(schedule_manifest).read_text(encoding="utf-8"))
    if smeta.get("version") != us_actions.VERSION:
        raise ValueError("split schedule uses an older verifier; recheck it with us-actions first")
    coverage = None
    if coverage_manifest is not None:
        coverage = json.loads(Path(coverage_manifest).read_text(encoding="utf-8"))
        if coverage.get("version") != us_actions.VERSION:
            raise ValueError("split coverage uses an older verifier; rerun us-coverage first")
    us_actions.check_bound_inputs(raw_manifest, smeta, coverage)
    sched_path = PKG_ROOT / smeta["schedule"]
    sched = pd.read_csv(sched_path, dtype={"ticker": str}, keep_default_na=False, na_values=[""])

    raw, _ = load_us(raw_manifest)
    raw = raw[raw["date"] <= pd.Timestamp(end)]
    panel, qa = _finish(raw)
    panel["qa_reverting_spike"] = _spikes(panel).to_numpy()

    events = us_actions.yahoo_events(raw_manifest)
    factor = np.ones(len(panel))
    for ticker, rows in panel.groupby("ticker").indices.items():
        ev = events[events["ticker"] == ticker]
        if len(ev):
            factor[rows] = us_actions.unit_factors(panel["date"].to_numpy()[rows].astype("datetime64[D]"), ev)
    panel["unit_factor"] = factor
    first_session = panel["date"].min()
    window_first = smeta["effective_after"]
    # A schedule may declare a wider research acceptance (share-count corroboration for records
    # after the window); never anything outside RESEARCH_ACCEPTED.
    accepted = tuple(sorted(set(smeta.get("accepted_statuses", us_actions.ACCEPTED)) & set(us_actions.RESEARCH_ACCEPTED)))
    share_window = (smeta.get("share_count_corroboration") or {}).get("window_end")
    recon = us_actions.reconcile_schedule(events, sched, window_first, set(panel["ticker"]), accepted, end,
                                          share_window)
    bad = recon[~recon["accepted"]]
    quarantine = {t: sorted(set(g["status"])) for t, g in bad.groupby("ticker")}
    trigger = {t: str(g["effective_session"].min()) for t, g in bad.groupby("ticker")}
    if coverage is not None:
        jumps = pd.read_csv(PKG_ROOT / coverage["rows"], dtype={"ticker": str}, keep_default_na=False, na_values=[""])
        flagged = jumps[jumps["status"].isin(us_actions.COVERAGE_QUARANTINE)]
        for t, g in flagged.groupby("ticker"):
            quarantine[t] = sorted(set(quarantine.get(t, [])) | set(g["status"]))
            trigger[t] = min(trigger.get(t, "9999"), str(g["date"].min()))
    in_panel = set(panel["ticker"])
    quarantine = {t: v for t, v in quarantine.items() if t in in_panel}
    reason_counts = {}
    for statuses in quarantine.values():
        for s_ in statuses:
            reason_counts[s_] = reason_counts.get(s_, 0) + 1

    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    path = PANEL_DIR / f"panel_us_repair-{stamp}.csv.gz"
    out = panel.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out["qa_reverting_spike"] = out["qa_reverting_spike"].astype(int)
    import gzip
    import io

    text = io.StringIO()
    out.to_csv(text, index=False, float_format="%.10g", lineterminator="\n")
    with path.open("xb") as fh, gzip.GzipFile(filename="", fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(text.getvalue().encode("utf-8"))  # no file name or time in the header: content-addressed
    last = panel["date"].max().date().isoformat()
    survivorship = ("survivor-only: the universe is the Nasdaq Trader listing snapshot of 2026-10-08; names "
                    "delisted earlier are absent")
    meta = {
        "format": REPAIR_FORMAT, "market": "US", "panel": rel(path), "sha256": sha256_file(path),
        "built_at": utc_stamp(), "preprocessing": qa.get("preprocessing_version"),
        "inputs": {raw_manifest.name: {"sha256": sha256_file(raw_manifest), "path": rel(raw_manifest)},
                   Path(schedule_manifest).name: {"sha256": sha256_file(Path(schedule_manifest)),
                                                  "path": rel(Path(schedule_manifest)),
                                                  "rows_sha256": smeta["schedule_sha256"]},
                   **({Path(coverage_manifest).name: {"sha256": sha256_file(Path(coverage_manifest)),
                                                      "path": rel(Path(coverage_manifest)),
                                                      "rows_sha256": coverage["rows_sha256"]}} if coverage else {})},
        "reconciliation": {"version": us_actions.RECONCILE_VERSION, "events_relevant": int(len(recon)),
                           "status_counts": recon["status"].value_counts().to_dict(),
                           "share_count_window_end": share_window,
                           "rule": "every provider split event of a panel name effective after "
                                   f"{window_first} needs exactly one verification record with the same key and "
                                   "payload sha256; otherwise UNRESOLVED_* and the name is quarantined"},
        "rows": int(len(panel)), "tickers": int(panel["ticker"].nunique()), "sessions": int(panel["date"].nunique()),
        "first_session": first_session.date().isoformat(), "last_session": last, "source_boundary": last,
        "read_through": end, "default_start": (first_session + timedelta(days=120)).date().isoformat(),
        "survivorship": survivorship,
        "quality_tiers": [{"tier": "US_SURVIVOR", "from": first_session.date().isoformat(), "to": last,
                           "source": "yahoo", "survivorship": survivorship,
                           "corporate_actions": "split-adjusted by the source; as-traded units via unit_factor"}],
        "known_limitations": [
            survivorship,
            "prices are split-adjusted by the source, not dividend-adjusted; unit_factor restores as-traded levels "
            "from the provider's split records (convention checked against FMP and SEC: research/E2/repair)",
            "daily bars only: no intraday path, no halts (US LULD) or order-book depth",
            "costs are assumed per price tier (profiles.py), not measured spreads",
        ],
        "unit_coverage": ({"manifest": Path(coverage_manifest).name, "status_counts": coverage.get("status_counts"),
                           "jump_threshold": coverage.get("jump_threshold"), "window": coverage.get("window")}
                          if coverage else None),
        "unit_schedule": {"manifest": Path(schedule_manifest).name, "version": smeta.get("version"),
                          "accepted_statuses": sorted(accepted), "effective_after": window_first,
                          "share_count_corroboration": smeta.get("share_count_corroboration"),
                          "status_counts": smeta.get("status_counts")},
        "unit_quarantine": {"tickers": quarantine, "reason_counts": reason_counts,
                            "outcome_dependent": {
                                "flag": True,
                                "first_trigger_session": {t: trigger[t] for t in sorted(quarantine)},
                                "triggered_after_read_through": sorted(t for t in quarantine if trigger[t] > end),
                                "note": "exclusion is decided by corporate-action records dated after the signals "
                                        "it removes (often after the research window); excluded names were worse "
                                        "on average (research/E2/repair_v3/SELECTION_NOTE.md). Report runs with and "
                                        "without the quarantine, never the quarantined run alone."},
                            "rule": "a name with any provider split record effective after "
                                    f"{window_first} that SEC filings do not corroborate (status not in "
                                    f"{sorted(accepted)}), or a jump inside the window that SEC filings tie "
                                    f"to a split the provider did not record (statuses {list(us_actions.COVERAGE_QUARANTINE)})"},
        "qa": {"preprocessing_version": qa.get("preprocessing_version"), "spike_rows_dropped": 0,
               "qa_reverting_spike_rows": int(panel["qa_reverting_spike"].sum()),
               "non_session_dates_count": qa.get("non_session_dates_count"),
               "note": "counts only: no price examples are written to this manifest"},
    }
    mpath = MANIFESTS / f"panel_us_repair-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    log(f"US repair panel {rel(path)} rows {meta['rows']} tickers {meta['tickers']} quarantined {len(quarantine)}")
    return mpath

"""Canonical daily panel: one row per (ticker, session), prices as traded.

Sessions up to the last mirror date come from the IDX daily stock summary mirror. Later
sessions come from Yahoo with the split adjustment undone. Every input file is checked
against its manifest hash before use. The panel file is written deterministically
(gzip mtime 0, integer columns), so its SHA-256 identifies the exact data a run used.

Panel format v2 adds IDX's daily share counts (`listed_shares`, `tradable_shares`) in the
mirror era; Yahoo carries none, so they are empty after the boundary. They feed the
corporate-action registry (a split multiplies the share count by its ratio on the day the
reference resets) and the market-cap control. A v1 panel loads with them empty.

Coverage eras (also written into the panel manifest; quality tiers in quality.py):

  idx_mirror  2019-07-29 .. 2025-02-21  names delisted after ~2021-01 are present up to
                                         their last session; names delisted between
                                         2019-07 and the mirror's first snapshot are not.
  yahoo       2025-02-24 .. latest      survivor-only: a name delisted after 2025-02-21
                                         stops at 2025-02-21 in this panel.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import market, quality
from .provenance import (
    MANIFESTS,
    PANEL_DIR,
    PKG_ROOT,
    check_files,
    latest_manifest,
    read_manifest,
    rel,
    sha256_file,
    utc_stamp,
    write_csv_gz_exclusive,
)

PANEL_FORMAT = "panel-v2"
COLUMNS = ["date", "ticker", "source", "previous", "open", "high", "low", "close", "volume", "value", "frequency",
           "listed_shares", "tradable_shares"]
INT_COLUMNS = ["previous", "open", "high", "low", "close", "volume", "value", "frequency", "listed_shares",
               "tradable_shares"]
V2_COLUMNS = ("listed_shares", "tradable_shares")
MIN_TRADED_PER_SESSION = 50  # a date with fewer traded names is a holiday stub, not a session
# A date is a session only if IDX itself priced the next day off it: among names whose close
# moved that day, at least this share must have the next reference price equal to that close.
# (The pinned mirror has a Saturday, 2021-05-22, with ~110 tiny trades that IDX's next
# reference ignores for every name; kept, it creates 61 false corporate actions.)
MIN_REFERENCE_CONFIRMED = 0.5


def load_mirror(manifest: Path) -> pd.DataFrame:
    _, records = read_manifest(manifest)
    frames = []
    for rec in records:
        if "ticker" not in rec:
            continue
        df = pd.read_csv(
            PKG_ROOT / rec["path"],
            usecols=["date", "previous", "open_price", "high", "low", "close", "volume", "value", "frequency",
                     "listed_shares", "tradeble_shares"],
        )
        df["ticker"] = rec["ticker"]
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"].str[:10])
    df = df.rename(columns={"open_price": "open", "tradeble_shares": "tradable_shares"})
    for col in V2_COLUMNS:
        df[col] = df[col].where(df[col] > 0)
    traded = df["volume"] > 0
    # IDX publishes an opening price only for names with a pre-opening auction; 0 means none.
    df["open"] = df["open"].where(df["open"] > 0)
    # On a day without trades IDX reports high/low 0 and carries the reference as close.
    for col in ("high", "low"):
        df[col] = df[col].where(traded)
    df["source"] = "idx_mirror"
    return df[COLUMNS]


def _yahoo_frame(ticker: str, payload: dict) -> pd.DataFrame:
    result = payload["chart"]["result"][0]
    stamps = result.get("timestamp") or []
    if not stamps:
        return pd.DataFrame(columns=COLUMNS)
    offset = result["meta"].get("gmtoffset", 25200)
    quote = result["indicators"]["quote"][0]
    df = pd.DataFrame({
        "date": pd.to_datetime(np.array(stamps) + offset, unit="s").normalize(),
        "open": pd.to_numeric(pd.Series(quote.get("open")), errors="coerce"),
        "high": pd.to_numeric(pd.Series(quote.get("high")), errors="coerce"),
        "low": pd.to_numeric(pd.Series(quote.get("low")), errors="coerce"),
        "close": pd.to_numeric(pd.Series(quote.get("close")), errors="coerce"),
        "volume": pd.to_numeric(pd.Series(quote.get("volume")), errors="coerce"),
    })
    df = df.dropna(subset=["close"]).drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    splits = sorted(
        (pd.Timestamp(datetime.fromtimestamp(s["date"] + offset, timezone.utc).date()), s["numerator"] / s["denominator"])
        for s in ((result.get("events") or {}).get("splits") or {}).values()
        if s.get("denominator")
    )
    # Yahoo divides prices before each split date by the split ratio; undo it.
    factor = np.ones(len(df))
    day_ratio = np.ones(len(df))
    for when, ratio in splits:
        factor[(df["date"] < when).to_numpy()] *= ratio
        hit = (df["date"] >= when).to_numpy()
        if hit.any():
            day_ratio[np.argmax(hit)] *= ratio
    for col in ("open", "high", "low", "close"):
        df[col] = (df[col] * factor).round()
    df["volume"] = (df["volume"] / factor).round()
    prior = df["close"].shift(1)
    reference = prior / day_ratio
    df["previous"] = np.where(day_ratio != 1, np.round(reference / market.tick_size(reference)) * market.tick_size(reference), prior)
    traded = df["volume"] > 0
    for col in ("open", "high", "low"):
        df[col] = df[col].where(traded)
    df["value"] = (df["close"] * df["volume"]).where(traded, 0)
    df["frequency"] = np.nan
    df["listed_shares"] = np.nan
    df["tradable_shares"] = np.nan
    df["ticker"] = ticker
    df["source"] = "yahoo"
    return df[COLUMNS]


def load_yahoo(manifest: Path) -> pd.DataFrame:
    _, records = read_manifest(manifest)
    frames = []
    for rec in records:
        if rec.get("http_status") != 200 or not rec.get("rows"):
            continue
        payload = json.loads((PKG_ROOT / rec["path"]).read_text(encoding="utf-8"))
        frames.append(_yahoo_frame(rec["ticker"], payload))
    return pd.concat(frames, ignore_index=True)


STITCH_TOLERANCE = 0.02  # Yahoo vs IDX close on the last common date before the switch


def _rebase_first_rows(yahoo: pd.DataFrame, mirror: pd.DataFrame,
                       boundary: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Chain each name's first Yahoo session to its last IDX close, so the source switch is
    not mistaken for a corporate action. A split on that first session is kept. A name whose
    Yahoo close disagrees with IDX on the last common date keeps no Yahoo segment: its
    coverage ends at the boundary rather than carrying a price level we cannot trust."""
    y = yahoo.sort_values(["ticker", "date"]).copy()
    y["yahoo_prior_close"] = y.groupby("ticker")["close"].shift(1)
    common = mirror[["ticker", "date", "close"]].merge(
        y.loc[y["date"] <= boundary, ["ticker", "date", "close"]], on=["ticker", "date"], suffixes=("_idx", "_yahoo")
    )
    last_common = common.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    gap = (last_common["close_yahoo"] / last_common["close_idx"] - 1).abs()
    dropped = {t: {"date": str(last_common.loc[t, "date"].date()), "idx_close": float(last_common.loc[t, "close_idx"]),
                   "yahoo_close": float(last_common.loc[t, "close_yahoo"])}
               for t in sorted(gap[gap > STITCH_TOLERANCE].index)}
    after = y[(y["date"] > boundary) & ~y["ticker"].isin(dropped)].copy()
    first = after.groupby("ticker").head(1)
    last_idx = mirror[mirror["date"] <= boundary].sort_values("date").groupby("ticker")["close"].last()
    anchor = first["ticker"].map(last_idx)
    ratio = first["previous"] / first["yahoo_prior_close"]
    rebased = (anchor * ratio).where(anchor.notna() & ratio.notna(), first["previous"])
    after.loc[first.index, "previous"] = rebased
    return after[COLUMNS], dropped


def _overlap_qa(mirror: pd.DataFrame, yahoo: pd.DataFrame, boundary: pd.Timestamp) -> dict:
    m = mirror[(mirror["volume"] > 0)][["ticker", "date", "close", "volume"]]
    y = yahoo[(yahoo["date"] <= boundary) & (yahoo["volume"] > 0)][["ticker", "date", "close", "volume"]]
    both = m.merge(y, on=["ticker", "date"], suffixes=("_idx", "_yahoo"))
    if both.empty:
        return {"rows_compared": 0}
    diff = (both["close_yahoo"] - both["close_idx"]).abs()
    tick = market.tick_size(both["close_idx"].to_numpy())
    rel_diff = diff / both["close_idx"]
    return {
        "rows_compared": int(len(both)),
        "tickers_compared": int(both["ticker"].nunique()),
        "close_exact_share": round(float((diff == 0).mean()), 4),
        "close_within_1_tick_share": round(float((diff <= tick).mean()), 4),
        "close_off_by_more_than_2pct_share": round(float((rel_diff > 0.02).mean()), 4),
        "volume_within_1pct_share": round(float(((both["volume_yahoo"] / both["volume_idx"] - 1).abs() <= 0.01).mean()), 4),
    }


def _limit_qa(panel: pd.DataFrame) -> list[dict]:
    """Closes outside the regular-board limits, per regime. Corporate-action days excluded."""
    p = panel.sort_values(["ticker", "date"])
    prior = p.groupby("ticker")["close"].shift(1)
    t = p[(p["volume"] > 0) & (p["previous"] > 0) & prior.notna()].copy()
    t = t[((t["previous"] / prior.loc[t.index]) - 1).abs() <= 0.005]
    days = t["date"].to_numpy().astype("datetime64[D]")
    ara, arb = market.limits(t["previous"].to_numpy(float), days)
    t["regime"] = market.regime_index(days)
    t["above"] = t["close"].to_numpy() > ara
    t["below"] = t["close"].to_numpy() < arb
    t["sub50"] = (t["close"] < 50) | (t["previous"] < 50)
    rows = []
    for idx, g in t.groupby("regime"):
        bad = g[g["above"] | g["below"]]
        rows.append({
            "regime": market.REGIMES[idx].label,
            "start": market.REGIMES[idx].start.isoformat(),
            "rows": int(len(g)),
            "above_ara": int(g["above"].sum()),
            "below_arb": int(g["below"].sum()),
            "violations_priced_below_rp50": int(bad["sub50"].sum()),
            "violations_other": int((~bad["sub50"]).sum()),
            "other_violation_dates": sorted({d.date().isoformat() for d in bad.loc[~bad["sub50"], "date"]})[:10],
        })
    return rows


def _reference_ignored_dates(mirror: pd.DataFrame) -> dict:
    p = mirror.sort_values(["ticker", "date"])
    nxt = p.groupby("ticker")["previous"].shift(-1)
    prior = p.groupby("ticker")["close"].shift(1)
    sel = (p["volume"] > 0) & nxt.notna() & prior.notna() & (p["close"] != prior)
    share = (nxt[sel] == p.loc[sel, "close"]).groupby(p.loc[sel, "date"]).agg(["mean", "size"])
    bad = share[share["mean"] < MIN_REFERENCE_CONFIRMED]
    return {d.date().isoformat(): {"names_checked": int(r["size"]), "next_reference_equals_close": round(float(r["mean"]), 4)}
            for d, r in bad.iterrows()}


def build(mirror_manifest: Path | None = None, yahoo_manifest: Path | None = None, log=print) -> Path:
    mirror_manifest = Path(mirror_manifest or latest_manifest("idx_mirror"))
    yahoo_manifest = Path(yahoo_manifest or latest_manifest("yahoo"))
    for manifest in (mirror_manifest, yahoo_manifest):
        problems = check_files(manifest)
        if problems:
            raise RuntimeError(f"{manifest.name}: {len(problems)} files differ from the manifest, e.g. {problems[:3]}")
    log("loading idx_mirror")
    mirror = load_mirror(mirror_manifest)
    log("loading yahoo")
    yahoo = load_yahoo(yahoo_manifest)
    ignored = _reference_ignored_dates(mirror)
    mirror = mirror[~mirror["date"].dt.strftime("%Y-%m-%d").isin(ignored)]
    boundary = mirror["date"].max()
    qa_overlap = _overlap_qa(mirror, yahoo, boundary)
    after, stitch_dropped = _rebase_first_rows(yahoo, mirror, boundary)
    panel = pd.concat([mirror, after], ignore_index=True)
    traded_per_day = panel[panel["volume"] > 0].groupby("date")["ticker"].nunique()
    sessions = traded_per_day[traded_per_day >= MIN_TRADED_PER_SESSION].index
    dropped_dates = sorted(set(panel["date"]) - set(sessions))
    panel = panel[panel["date"].isin(sessions)]
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    for col in INT_COLUMNS:
        panel[col] = panel[col].round().astype("Int64")
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    path = PANEL_DIR / f"panel-{stamp}.csv.gz"
    out = panel.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    write_csv_gz_exclusive(path, out, index=False)  # fails, touching nothing, if the stamp is taken

    last = panel.groupby("ticker")["date"].max()
    first = panel.groupby("ticker")["date"].min()
    end = panel["date"].max()
    _, mirror_records = read_manifest(mirror_manifest)
    _, yahoo_records = read_manifest(yahoo_manifest)
    yahoo_ok = {r["ticker"] for r in yahoo_records if r.get("http_status") == 200 and r.get("rows")}
    yahoo_missing = sorted({r["ticker"] for r in yahoo_records} - yahoo_ok)
    manifest = {
        "format": PANEL_FORMAT,
        "columns": COLUMNS,
        "panel": rel(path),
        "sha256": sha256_file(path),
        "built_at": utc_stamp(),
        "inputs": {
            m.name: {"sha256": sha256_file(m), "path": rel(m)} for m in (mirror_manifest, yahoo_manifest)
        },
        "rows": int(len(panel)),
        "tickers": int(panel["ticker"].nunique()),
        "sessions": int(panel["date"].nunique()),
        "first_session": panel["date"].min().date().isoformat(),
        "last_session": end.date().isoformat(),
        "source_boundary": boundary.date().isoformat(),
        "eras": [
            {
                "source": "idx_mirror",
                "from": panel["date"].min().date().isoformat(),
                "to": boundary.date().isoformat(),
                "survivorship": "names delisted after ~2021-01 present to their last session; names delisted 2019-07..~2021-01 absent",
            },
            {
                "source": "yahoo",
                "from": (boundary + timedelta(days=1)).date().isoformat(),
                "to": end.date().isoformat(),
                "survivorship": "survivor-only: names delisted after the boundary stop at the boundary",
            },
        ],
        "tickers_ending_before_boundary": {t: d.date().isoformat() for t, d in sorted(last.items()) if d < boundary},
        "tickers_ending_at_boundary": sorted(t for t, d in last.items() if d == boundary),
        "tickers_listed_after_boundary": {t: d.date().isoformat() for t, d in sorted(first.items()) if d > boundary},
        "mirror_tickers": len([r for r in mirror_records if "ticker" in r]),
        "yahoo_not_found_or_empty": yahoo_missing,
        "dropped_non_session_dates": [d.date().isoformat() for d in dropped_dates][:50],
        "dropped_non_session_dates_count": len(dropped_dates),
        "dropped_dates_ignored_by_idx_reference": ignored,
        "qa_overlap_idx_vs_yahoo": qa_overlap,
        "yahoo_segment_dropped_stitch_mismatch": stitch_dropped,
        "qa_limit_violations": _limit_qa(panel),
        "market_regimes": market.regime_labels(),
        "quality_tiers": quality.tiers(panel["date"].min().date().isoformat(), boundary.date().isoformat(),
                                       end.date().isoformat()),
        "share_counts": {
            "rows_with_listed_shares": int(panel["listed_shares"].notna().sum()),
            "note": "IDX listed_shares / tradeble_shares, mirror era only. tradable_shares is NOT free float: "
                    "it equals listed_shares for most names, including ones with a known controlling holder.",
        },
    }
    mpath = MANIFESTS / f"panel-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log(f"panel {rel(path)} rows {len(panel)} tickers {manifest['tickers']} sessions {manifest['sessions']}")
    return mpath


def load(panel_manifest: Path | None = None) -> tuple[pd.DataFrame, dict, Path]:
    panel_manifest = Path(panel_manifest or latest_manifest("panel", ".json"))
    meta = json.loads(panel_manifest.read_text(encoding="utf-8"))
    path = PKG_ROOT / meta["panel"]
    if not path.exists():
        raise FileNotFoundError(f"{meta['panel']} is missing; rebuild it with `python -m idxsig build-panel`")
    if sha256_file(path) != meta["sha256"]:
        raise RuntimeError(f"{meta['panel']} does not match the hash in {panel_manifest.name}")
    df = pd.read_csv(path, dtype={c: "Int64" for c in INT_COLUMNS}, parse_dates=["date"])
    for col in V2_COLUMNS:  # a v1 panel has no share counts
        if col not in df:
            df[col] = pd.array([pd.NA] * len(df), dtype="Int64")
    meta.setdefault("format", "panel-v1")
    return df, meta, panel_manifest

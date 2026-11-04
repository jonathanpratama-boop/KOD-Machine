"""Corporate-action registry: what each reference-price reset was, and how sure we are.

A reference-price reset (IDX's `previous` differing from the prior close) tells us that
something changed the share basis, not what. A 1:5 split and a rights issue both reset
the reference, but a split hands holders five shares for one, while a rights issue hands
them rights they must pay to exercise. Scaling shares through a rights issue as if it were
a split would credit holders with free shares. So the execution model (ca_mode="registry",
the default) scales held shares only for actions the registry marks as share-scaling AND
verified:

  STOCK_SPLIT, REVERSE_SPLIT, STOCK_DIVIDEND   with VERIFIED_PRIMARY or VERIFIED_CORROBORATED

A trade held across a verified RIGHTS_ISSUE is CORP_ACTION_RIGHTS_ISSUE; across any other
reset (unresolved, single-source, or missing from the registry) it is CORP_ACTION_UNRESOLVED.
Neither is scored, for the rule and the baselines alike.

How a reset is verified, in order:

  VERIFIED_PRIMARY       a primary source (issuer / exchange / KSEI announcement) entered in
                         data/corporate_actions/manual.csv with its URL and retrieval time.
  VERIFIED_CORROBORATED  (mirror era) IDX's listed share count moved by the same ratio as the
                         reference on the same day (or the next session), and Yahoo does not
                         contradict it; or the share count's first move came later (within
                         SHARE_LAG_MAX sessions; IDX's register often lags) by that ratio AND a
                         Yahoo split event agrees, two independent confirmations.
                         The ratio applied is the declared one (Yahoo's numerator:denominator)
                         when Yahoo agrees, else the share register's measured ratio; never the
                         reset snapped to a nearby fraction, which can be up to 1% off. Shares x r with price / r means holders received shares
                         without paying for them, whatever the action is called; a rights issue
                         cannot do that, because its new shares are paid for and list weeks
                         later. Integer ratios are labelled splits / reverse splits; other
                         ratios STOCK_DIVIDEND (bonus or stock dividend; the label is inferred,
                         the economics are measured). Where share counts are missing, an integer
                         reset that a Yahoo split event matches is also corroborated.
  UNVERIFIED_SINGLE_SOURCE  after the mirror ends the reset is itself derived from Yahoo's
                         split event, so Yahoo cannot corroborate it. Not scaled.
  NO_PRICE_RESET         a Yahoo split event with no reset in the exchange data. Not applied.
  UNRESOLVED             everything else, including resets whose sources disagree. Not scaled.

Each registry is a new file (data/corporate_actions/ca_registry-<stamp>.csv) with a manifest
naming the exact panel it was built from; a run refuses a registry built for another panel.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .provenance import (
    DATA,
    MANIFESTS,
    PKG_ROOT,
    latest_manifest,
    read_manifest,
    rel,
    sha256_file,
    utc_stamp,
)

REGISTRY_VERSION = "ca-registry-v1"
ACTION_TYPES = (
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "RIGHTS_ISSUE",
    "STOCK_DIVIDEND",
    "OTHER_REFERENCE_RESET",
    "UNKNOWN",
)
SCALABLE = ("STOCK_SPLIT", "REVERSE_SPLIT", "STOCK_DIVIDEND")
VERIFIED = ("VERIFIED_PRIMARY", "VERIFIED_CORROBORATED")
STATUSES = VERIFIED + ("UNVERIFIED_SINGLE_SOURCE", "NO_PRICE_RESET", "UNRESOLVED")
COLUMNS = [
    "ticker",
    "effective_date",
    "action_type",
    "ratio",
    "observed_reset_ratio",
    "listed_shares_ratio",
    "listed_shares_lag",
    "source",
    "source_timestamp",
    "verification_status",
    "evidence",
    "notes",
]
CA_DIR = DATA / "corporate_actions"
MANUAL = CA_DIR / "manual.csv"
MANUAL_COLUMNS = [
    "ticker",
    "effective_date",
    "action_type",
    "ratio",
    "source",
    "source_timestamp",
    "notes",
]
RATIO_TOLERANCE = 0.01
SHARE_LAG_MAX = (
    20  # sessions after the reset in which a register update still counts (with Yahoo agreeing)
)


class RegistryMismatch(RuntimeError):
    pass


def _integer_like(r: float) -> bool:
    return (r >= 2 and abs(r - round(r)) < 1e-6) or (
        0 < r <= 0.5 and abs(1 / r - round(1 / r)) < 1e-6
    )


def _close(a: float, b: float) -> bool:
    return bool(np.isfinite(a) and np.isfinite(b) and b != 0 and abs(a / b - 1) < RATIO_TOLERANCE)


def yahoo_events(manifest: Path) -> pd.DataFrame:
    _, records = read_manifest(manifest)
    rows = []
    for rec in records:
        if rec.get("http_status") != 200 or not rec.get("splits"):
            continue
        result = json.loads((PKG_ROOT / rec["path"]).read_text(encoding="utf-8"))["chart"][
            "result"
        ][0]
        offset = result["meta"].get("gmtoffset", 25200)
        for event in ((result.get("events") or {}).get("splits") or {}).values():
            if not event.get("denominator"):
                continue
            rows.append(
                {
                    "ticker": rec["ticker"],
                    "effective_date": datetime.fromtimestamp(event["date"] + offset, timezone.utc)
                    .date()
                    .isoformat(),
                    "yahoo_ratio": event["numerator"] / event["denominator"],
                    "yahoo_text": event.get("splitRatio", ""),
                    "yahoo_downloaded_at": rec["downloaded_at"],
                }
            )
    return empty_events() if not rows else pd.DataFrame(rows)


def empty_events() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["ticker", "effective_date", "yahoo_ratio", "yahoo_text", "yahoo_downloaded_at"]
    )


def read_manual(path: Path = MANUAL) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=MANUAL_COLUMNS)
    lines = [
        x for x in Path(path).read_text(encoding="utf-8").splitlines() if not x.startswith("#")
    ]
    df = pd.read_csv(io.StringIO("\n".join(lines)), dtype=str).fillna("")
    if list(df.columns) != MANUAL_COLUMNS:
        raise ValueError(f"{path}: columns must be {MANUAL_COLUMNS}")
    for _, row in df.iterrows():
        where = f"{Path(path).name}: {row['ticker']} {row['effective_date']}"
        if row["action_type"] not in ACTION_TYPES:
            raise ValueError(f"{where}: unknown action_type {row['action_type']!r}")
        if not row["source"].startswith(("http://", "https://")) or not row["source_timestamp"]:
            raise ValueError(
                f"{where}: a primary source URL and the time it was retrieved are required"
            )
        if row["action_type"] in SCALABLE and not row["ratio"]:
            raise ValueError(
                f"{where}: a share-scaling action needs its ratio (new shares per old share)"
            )
    return df


def classify(
    market, boundary: str, events: pd.DataFrame, manual: pd.DataFrame, exchange_timestamp: str
) -> pd.DataFrame:
    """One row per reference reset in `market`, plus one per Yahoo event with no reset."""
    boundary_day = np.datetime64(boundary, "D")
    by_key = {(r["ticker"], r["effective_date"]): r for _, r in events.iterrows()}
    manual_keys = {(r["ticker"], r["effective_date"]): r for _, r in manual.iterrows()}
    shares = market.listed_shares
    rows, matched = [], set()
    for n, d in zip(*np.nonzero(market.ca_ratio != 1)):
        ticker, day = str(market.tickers[n]), str(market.dates[d])
        ratio = float(market.ca_ratio[n, d])
        before = np.flatnonzero(market.present[n, :d])
        prior_close = float(market.close[n, before[-1]]) if len(before) else float("nan")
        raw = prior_close / float(market.prev[n, d])
        prior_shares = shares[n, :d][np.isfinite(shares[n, :d])]
        base = float(prior_shares[-1]) if len(prior_shares) else float("nan")
        after = shares[n, d : d + SHARE_LAG_MAX + 1]
        moved = (
            np.flatnonzero(np.isfinite(after) & (np.abs(after / base - 1) > 1e-9))
            if np.isfinite(base)
            else []
        )
        shares_known = bool(np.isfinite(base) and np.isfinite(after).any())
        lag = int(moved[0]) if len(moved) else -1
        share_ratio = (
            float(after[lag] / base) if lag >= 0 else (1.0 if shares_known else float("nan"))
        )
        share_match = lag in (0, 1) and _close(share_ratio, ratio)
        lagged_match = lag > 1 and _close(share_ratio, ratio)
        y = by_key.get((ticker, day))
        if y is not None:
            matched.add((ticker, day))
        agrees = y is not None and _close(float(y["yahoo_ratio"]), ratio)
        contradicts = y is not None and not agrees
        integer = _integer_like(ratio)
        scaled_type = (
            "REVERSE_SPLIT" if ratio < 1 else ("STOCK_SPLIT" if integer else "STOCK_DIVIDEND")
        )
        in_idx_era = market.dates[d] <= boundary_day
        evidence = f"IDX reference {market.prev[n, d]:.0f} vs prior close {prior_close:.0f} (ratio {raw:.6g})"
        if shares_known:
            evidence += f"; IDX listed shares x{share_ratio:.6g}" + (
                f" {lag} sessions later"
                if lag > 0
                else ""
                if lag == 0
                else f" within {SHARE_LAG_MAX} sessions"
            )
        if y is not None:
            evidence += f"; Yahoo split {y['yahoo_text']}"
        row = {
            "ticker": ticker,
            "effective_date": day,
            "ratio": ratio,
            "observed_reset_ratio": raw,
            "listed_shares_ratio": share_ratio,
            "listed_shares_lag": lag if lag >= 0 else np.nan,
            "source_timestamp": exchange_timestamp,
            "evidence": evidence,
        }
        verified_ratio = (
            float(y["yahoo_ratio"]) if agrees else (share_ratio if share_match else ratio)
        )
        if not in_idx_era:
            row.update(
                action_type=scaled_type if integer else "UNKNOWN",
                verification_status="UNVERIFIED_SINGLE_SOURCE",
                source="yahoo split event (reference derived from it)",
                source_timestamp=y["yahoo_downloaded_at"] if y is not None else "",
                notes="after the mirror ends the reset is derived from Yahoo, so Yahoo cannot corroborate it",
            )
        elif share_match and not contradicts:
            row.update(
                action_type=scaled_type,
                verification_status="VERIFIED_CORROBORATED",
                ratio=verified_ratio,
                source="IDX reference reset + IDX listed_shares"
                + (" + Yahoo split event" if agrees else ""),
                notes="share count and reference moved by the same ratio: holders received shares without "
                "paying"
                + (
                    "; label inferred (bonus shares or stock dividend)"
                    if scaled_type == "STOCK_DIVIDEND"
                    else ""
                ),
            )
        elif lagged_match and agrees:
            row.update(
                action_type=scaled_type,
                verification_status="VERIFIED_CORROBORATED",
                ratio=verified_ratio,
                source="IDX reference reset + IDX listed_shares (lagged) + Yahoo split event",
                notes=f"IDX's share register moved by the reset ratio {lag} sessions later and Yahoo lists the "
                f"split on the reset date",
            )
        elif share_match or (shares_known and agrees):
            row.update(
                action_type="UNKNOWN",
                verification_status="UNRESOLVED",
                source="IDX + Yahoo (disagree)",
                notes="the IDX share count and Yahoo's split event disagree on this reset",
            )
        elif shares_known and integer:
            row.update(
                action_type="UNKNOWN",
                verification_status="UNRESOLVED",
                source="IDX reference reset",
                notes=f"integer ratio, but the share count did not move by it within {SHARE_LAG_MAX} sessions "
                f"and no second source confirms a split",
            )
        elif shares_known:
            row.update(
                action_type="OTHER_REFERENCE_RESET",
                verification_status="UNRESOLVED",
                source="IDX reference reset",
                notes="share count did not move with the reference: not a free distribution; consistent with a "
                "rights issue (paid, new shares list after exercise). Only a primary source can say",
            )
        elif integer and agrees:
            row.update(
                action_type=scaled_type,
                verification_status="VERIFIED_CORROBORATED",
                ratio=verified_ratio,
                source="IDX reference reset + Yahoo split event",
                notes="no share counts here; exchange reset and Yahoo agree on an integer ratio",
            )
        else:
            row.update(
                action_type="UNKNOWN" if integer else "OTHER_REFERENCE_RESET",
                verification_status="UNRESOLVED",
                source="IDX reference reset",
                notes="no second source",
            )
        override = manual_keys.get((ticker, day))
        if override is not None:
            row.update(
                action_type=override["action_type"],
                verification_status="VERIFIED_PRIMARY",
                ratio=float(override["ratio"]) if override["ratio"] else ratio,
                source=override["source"],
                source_timestamp=override["source_timestamp"],
                notes=f"primary source; automatic reading was {row['action_type']}/{row['verification_status']}"
                + (f"; {override['notes']}" if override["notes"] else ""),
            )
        rows.append(row)
    first = str(market.dates[0])
    for (ticker, day), y in sorted(by_key.items()):
        if (ticker, day) in matched or day < first or day > str(market.dates[-1]):
            continue
        rows.append(
            {
                "ticker": ticker,
                "effective_date": day,
                "action_type": "STOCK_SPLIT" if y["yahoo_ratio"] > 1 else "REVERSE_SPLIT",
                "ratio": float(y["yahoo_ratio"]),
                "observed_reset_ratio": np.nan,
                "listed_shares_ratio": np.nan,
                "listed_shares_lag": np.nan,
                "source": "Yahoo split event",
                "source_timestamp": y["yahoo_downloaded_at"],
                "verification_status": "NO_PRICE_RESET",
                "evidence": f"Yahoo split {y['yahoo_text']}; the exchange data shows no reference reset that day",
                "notes": "not applied: prices are continuous in the exchange data",
            }
        )
    return (
        pd.DataFrame(rows, columns=COLUMNS)
        .sort_values(["effective_date", "ticker"])
        .reset_index(drop=True)
    )


def summarize(df: pd.DataFrame) -> dict:
    applied = df["verification_status"].isin(VERIFIED) & df["action_type"].isin(SCALABLE)
    return {
        "rows": int(len(df)),
        "by_status": {
            k: int(v) for k, v in df["verification_status"].value_counts().sort_index().items()
        },
        "by_type": {k: int(v) for k, v in df["action_type"].value_counts().sort_index().items()},
        "share_scaled": int(applied.sum()),
    }


def build(
    market, panel_meta: dict, yahoo_manifest: Path | None = None, manual_path: Path = MANUAL
) -> tuple[pd.DataFrame, dict]:
    yahoo_manifest = Path(
        yahoo_manifest or MANIFESTS / next(k for k in panel_meta["inputs"] if k.startswith("yahoo"))
    )
    mirror_manifest = MANIFESTS / next(
        k for k in panel_meta["inputs"] if k.startswith("idx_mirror")
    )
    mirror_header, _ = read_manifest(mirror_manifest)
    manual = read_manual(manual_path)
    df = classify(
        market,
        panel_meta["source_boundary"],
        yahoo_events(yahoo_manifest),
        manual,
        mirror_header["downloaded_at"],
    )
    summary = {
        **summarize(df),
        "manual_entries": int(len(manual)),
        "inputs": {
            "panel": panel_meta["panel"],
            "panel_sha256": panel_meta["sha256"],
            "panel_format": panel_meta.get("format", "panel-v1"),
            "idx_mirror_manifest": mirror_manifest.name,
            "yahoo_manifest": yahoo_manifest.name,
            "yahoo_manifest_sha256": sha256_file(yahoo_manifest),
            "manual": rel(manual_path) if Path(manual_path).exists() else None,
            "manual_sha256": sha256_file(manual_path) if Path(manual_path).exists() else None,
        },
    }
    return df, summary


def write(df: pd.DataFrame, summary: dict) -> Path:
    CA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    path = CA_DIR / f"ca_registry-{stamp}.csv"
    buf = io.StringIO()
    df.to_csv(
        buf, index=False, float_format="%.10g", quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
    )
    with path.open("x", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())
    manifest = {
        "registry_version": REGISTRY_VERSION,
        "registry": rel(path),
        "sha256": sha256_file(path),
        "built_at": utc_stamp(),
        **summary,
        "action_types": list(ACTION_TYPES),
        "statuses": list(STATUSES),
        "share_scaling": {"applied_for": list(SCALABLE), "only_if": list(VERIFIED)},
    }
    mpath = MANIFESTS / f"ca_registry-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return mpath


def load(
    manifest: Path | None = None, panel_sha256: str | None = None
) -> tuple[pd.DataFrame, dict]:
    manifest = Path(manifest or latest_manifest("ca_registry", ".json"))
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    path = PKG_ROOT / meta["registry"]
    if sha256_file(path) != meta["sha256"]:
        raise RegistryMismatch(f"{meta['registry']} does not match the hash in {manifest.name}")
    if panel_sha256 is not None and meta["inputs"]["panel_sha256"] != panel_sha256:
        raise RegistryMismatch(
            f"{manifest.name} was built for panel {meta['inputs']['panel_sha256'][:12]}, not "
            f"{panel_sha256[:12]}; run `python -m idxsig build-ca-registry` for this panel"
        )
    df = pd.read_csv(
        path,
        dtype={"ticker": str, "effective_date": str, "source_timestamp": str},
        keep_default_na=False,
        na_values={
            c: [""]
            for c in ("ratio", "observed_reset_ratio", "listed_shares_ratio", "listed_shares_lag")
        },
    )
    meta["_manifest"] = manifest.name
    meta["_manifest_sha256"] = sha256_file(manifest)
    return df, meta


def scaling_arrays(
    market, registry: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """(share factor, rights count, unresolved count) as cumulative (ticker x session) arrays.

    Every reset in `market` is looked up in the registry. A reset with no registry row is
    unresolved: the registry must explain a reset before shares are scaled through it."""
    rows = {
        (r.ticker, r.effective_date): r
        for r in registry.itertuples(index=False)
        if r.verification_status != "NO_PRICE_RESET"
    }
    scale = np.ones(market.shape)
    rights = np.zeros(market.shape, dtype=np.int64)
    unresolved = np.zeros(market.shape, dtype=np.int64)
    counts = {
        "resets": 0,
        "share_scaled": 0,
        "rights_issue": 0,
        "unresolved": 0,
        "missing_from_registry": 0,
        "registry_rows_without_reset": 0,
    }
    seen = set()
    for n, d in zip(*np.nonzero(market.ca_ratio != 1)):
        key = (str(market.tickers[n]), str(market.dates[d]))
        seen.add(key)
        counts["resets"] += 1
        r = rows.get(key)
        if r is None:
            counts["missing_from_registry"] += 1
            unresolved[n, d] = 1
        elif r.verification_status in VERIFIED and r.action_type in SCALABLE:
            scale[n, d] = float(r.ratio)
            counts["share_scaled"] += 1
        elif r.verification_status in VERIFIED and r.action_type == "RIGHTS_ISSUE":
            rights[n, d] = 1
            counts["rights_issue"] += 1
        else:
            unresolved[n, d] = 1
    counts["unresolved"] = int(unresolved.sum())
    lo, hi = str(market.dates[0]), str(market.dates[-1])
    counts["registry_rows_without_reset"] = sum(
        1 for k in rows if k not in seen and lo <= k[1] <= hi
    )
    return (
        np.cumprod(scale, axis=1),
        np.cumsum(rights, axis=1),
        np.cumsum(unresolved, axis=1),
        counts,
    )

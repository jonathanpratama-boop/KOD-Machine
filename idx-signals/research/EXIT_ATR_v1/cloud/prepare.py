"""EXIT-ATR-v1 (cloud) step 1: eligibility of every shared entry, BEFORE any exit or return is computed.

Reads entries/ (E2 harness 21345b1 on E2's original panel), E2's original daily panel (hash-checked) and the
E6 hourly archive through 2022-12-31 23:00 only. Writes eligibility/{ELIGIBILITY.json, eligibility.csv.gz}.
It reads no exit price and computes no return: for each entry only its window (entry day 00:00 to the original
exit day 23:00), hourly bar presence in that window, the ATR known at the signal close, and flags.
Usage (from idx-signals/): python3 research/EXIT_ATR_v1/cloud/prepare.py
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig import e6, exit_atr  # noqa: E402

CLOUD = ROOT / "research" / "EXIT_ATR_v1" / "cloud"
ENT, OUT = CLOUD / "entries", CLOUD / "eligibility"
PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_crypto-20261008T003354Z.json"
HOURLY_MANIFEST = ROOT / "data" / "manifests" / "binance_1h-20261015T182940Z.jsonl"
LAST_HOUR = pd.Timestamp("2022-12-31 23:00", tz="UTC")
SCORED = ("EXITED", "EXIT_DATA_END")
# Source-confirmed unit/asset changes (hermes_archive/data_check/unit_changes_confirmed.json): UTC days from the
# last bar before the halt through the first bar after it. A trade touching one is excluded from both arms.
EVENTS = {"COCOS": ("2021-01-19", "2021-01-23"), "BTCST": ("2021-03-15", "2021-03-19"),
          "DREP": ("2021-03-29", "2021-04-02"), "SUN": ("2021-06-14", "2021-06-18"),
          "VIDT": ("2022-10-31", "2022-11-09"), "LUNA": ("2022-05-13", "2022-05-31")}
UNRESOLVED = {"UNFI": "2022-06-07"}  # kept in the main analysis; excluded only in one sensitivity


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_panel():
    meta = json.loads(PANEL_MANIFEST.read_text())
    path = ROOT / meta["panel"]
    if sha256(path) != meta["sha256"]:
        raise SystemExit(f"panel hash mismatch: {path}")
    P = pd.read_csv(path, usecols=["date", "ticker", "open", "high", "low", "close"], parse_dates=["date"],
                    dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    return P, meta


def entries():
    s = pd.read_csv(ENT / "signals.csv", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    s = s[s.j >= 0].assign(arm="signal", draw=-1)
    c = pd.read_csv(ENT / "controls.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    c = c.assign(arm="control")
    cols = ["arm", "j", "draw", "ticker", "signal_date", "status", "entry_date", "exit_date_original", "entry_price"]
    return pd.concat([s[cols], c[cols]], ignore_index=True)


def atr_table(P: pd.DataFrame, keys: pd.DataFrame) -> pd.Series:
    """ATR at each (ticker, signal_date) from the 15 panel bars s-14..s."""
    out = {}
    by = {t: g.set_index("date").sort_index() for t, g in P[P.ticker.isin(keys.ticker.unique())].groupby("ticker")}
    for t, sd in keys[["ticker", "signal_date"]].drop_duplicates().itertuples(index=False):
        g = by.get(t)
        d = pd.Timestamp(sd)
        if g is None:
            out[(t, sd)] = np.nan
            continue
        w = g.loc[d - pd.Timedelta(days=14): d]
        consecutive = len(w) == 15 and (w.index == pd.date_range(d - pd.Timedelta(days=14), d, freq="D")).all()
        a = exit_atr.atr_at_signal(w.high.to_numpy(), w.low.to_numpy(), w.close.to_numpy(), bool(consecutive))
        out[(t, sd)] = np.nan if a is None else a
    return pd.Series(out)


def touches(ticker, a, b, table):
    if ticker not in table:
        return False
    lo, hi = (pd.Timestamp(x) for x in table[ticker])
    return (a <= hi) & (b >= lo)


def main() -> int:
    P, pmeta = load_panel()
    E = entries()
    E["entered"] = E.status.isin(SCORED + ("INCOMPLETE",))
    E["scored_A"] = E.status.isin(SCORED)
    E["sd"] = pd.to_datetime(E.signal_date)
    E["ed"] = pd.to_datetime(E.entry_date.where(E.entered))
    E["xd"] = pd.to_datetime(E.exit_date_original.where(E.scored_A))
    E["symbol"] = E.ticker + "USDT"

    A = atr_table(P, E[E.scored_A])
    E["atr"] = [A.get((t, s), np.nan) if sc else np.nan for t, s, sc in zip(E.ticker, E.signal_date, E.scored_A)]
    E["atr_valid"] = np.isfinite(E.atr)

    h, hmeta = e6.load_manifest(HOURLY_MANIFEST, last_hour=LAST_HOUR)
    idx = {s: i for i, s in enumerate(h.symbols)}
    start = h.start
    E["has_symbol"] = E.symbol.isin(idx)
    E["h0"] = ((E.ed.dt.tz_localize("UTC") - start) / pd.Timedelta("1h")).fillna(-1).astype(int)
    E["h1"] = ((E.xd.dt.tz_localize("UTC") - start) / pd.Timedelta("1h") + 23).fillna(-1).astype(int)
    pres_cum = np.concatenate([np.zeros((h.present.shape[0], 1), dtype=np.int64), np.cumsum(h.present, axis=1)], axis=1)
    sel = E.scored_A & E.has_symbol
    rows = E.loc[sel, "symbol"].map(idx).to_numpy()
    h0, h1 = E.loc[sel, "h0"].to_numpy(), E.loc[sel, "h1"].to_numpy()
    if (h1 >= h.present.shape[1]).any():
        raise SystemExit("a window ends after 2022-12-31 23:00")
    E["expected_hours"] = np.where(E.scored_A, E.h1 - E.h0 + 1, 0)
    E["present_hours"] = 0
    E.loc[sel, "present_hours"] = pres_cum[rows, h1 + 1] - pres_cum[rows, h0]
    E["entry_bar"] = False
    E.loc[sel, "entry_bar"] = h.present[rows, h0]
    last = np.full(len(rows), -1)
    for k, (r, a, b) in enumerate(zip(rows, h0, h1)):
        w = np.flatnonzero(h.present[r, a:b + 1])
        last[k] = a + w[-1] if len(w) else -1
    E["last_present_hour"] = -1
    E.loc[sel, "last_present_hour"] = last
    E["coverage"] = np.select([~E.scored_A, ~E.has_symbol, E.present_hours == E.expected_hours, E.last_present_hour < E.h1],
                              ["NOT_SCORED", "NO_HOURLY_SYMBOL", "COMPLETE", "TRUNCATED"], "GAPS")
    a_day = E.sd - pd.Timedelta(days=14)
    E["unit_change"] = [bool(sc) and bool(touches(t, a, b, EVENTS)) for t, a, b, sc in zip(E.ticker, a_day, E.xd, E.scored_A)]
    E["unresolved_unfi"] = [bool(sc) and t in UNRESOLVED and a <= pd.Timestamp(UNRESOLVED[t]) <= b
                            for t, a, b, sc in zip(E.ticker, a_day, E.xd, E.scored_A)]
    E["eligible"] = E.scored_A & E.has_symbol & E.entry_bar & E.atr_valid & ~E.unit_change
    E["excluded_reason"] = np.select(
        [~E.entered, ~E.scored_A, ~E.has_symbol, ~E.entry_bar, E.unit_change, ~E.atr_valid],
        ["NOT_FILLED", "INCOMPLETE_BOUNDARY", "NO_HOURLY_SYMBOL", "NO_ENTRY_BAR", "UNIT_OR_ASSET_CHANGE", "ATR_WARMUP"], "")

    def counts(arm):
        x = E[E.arm == arm]
        return {"attempted": int(len(x)), "by_status": x.status.value_counts().to_dict(),
                "scored_by_original_model": int(x.scored_A.sum()),
                "coverage_of_scored": x[x.scored_A].coverage.value_counts().to_dict(),
                "excluded_by_first_reason": x[~x.eligible].excluded_reason.value_counts().to_dict(),
                "atr_invalid_among_scored": int((x.scored_A & ~x.atr_valid).sum()),
                "unit_change_among_scored": int((x.scored_A & x.unit_change).sum()),
                "unit_change_and_atr_invalid": int((x.scored_A & x.unit_change & ~x.atr_valid).sum()),
                "unresolved_unfi_among_eligible": int((x.eligible & x.unresolved_unfi).sum()),
                "eligible": int(x.eligible.sum()), "eligible_distinct_coins": int(x[x.eligible].ticker.nunique()),
                "eligible_coverage": x[x.eligible].coverage.value_counts().to_dict(),
                "eligible_by_entry_year": x[x.eligible].ed.dt.year.value_counts().sort_index().to_dict()}

    ctl_ok = E[(E.arm == "control") & E.eligible].groupby("j").size()
    sig = E[(E.arm == "signal") & E.eligible]
    res = {"stage": "eligibility only: no exit price read, no return computed",
           "panel": {"file": pmeta["panel"], "sha256": pmeta["sha256"], "rows": int(pmeta.get("rows", len(P)))},
           "hourly": {"manifest": HOURLY_MANIFEST.name, "manifest_sha256": sha256(HOURLY_MANIFEST),
                      "last_hour_read": str(LAST_HOUR), "symbols_loaded": hmeta["symbols_loaded"]},
           "entries": {f: sha256(ENT / f) for f in ("signals.csv", "controls.csv.gz", "entries_meta.json")},
           "signals": counts("signal"), "controls": counts("control"),
           "eligible_signals_with_no_eligible_control": int((~sig.j.isin(ctl_ok.index)).sum()),
           "eligible_controls_per_eligible_signal": {"median": float(ctl_ok.reindex(sig.j).fillna(0).median()),
                                                     "min": int(ctl_ok.reindex(sig.j).fillna(0).min())},
           "atr_over_entry_price_eligible_signals": {q: float(np.percentile((sig.atr / sig.entry_price), p))
                                                     for q, p in (("p10", 10), ("median", 50), ("p90", 90))},
           "initial_stop_at_or_below_zero_eligible": {"signals": int((E.eligible & (E.arm == "signal") & (E.entry_price - 3 * E.atr <= 0)).sum()),
                                                      "controls": int((E.eligible & (E.arm == "control") & (E.entry_price - 3 * E.atr <= 0)).sum())}}
    OUT.mkdir(parents=True, exist_ok=True)
    E.drop(columns=["sd", "ed", "xd"]).to_csv(OUT / "eligibility.csv.gz", index=False, float_format="%.12g",
                                              compression={"method": "gzip", "mtime": 0})
    (OUT / "ELIGIBILITY.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

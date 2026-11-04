"""EXIT-ATR-v1 step 3c/3d: unit-change CANDIDATES and missing-hour classes, for every window the test uses.

No return is computed. Outputs (data_check/):
  unit_candidates.csv: price discontinuities that MAY be unit changes. A candidate is any jump between consecutive
    available hourly bars (close before -> open after, across a gap or not) or consecutive daily bars (close -> open,
    close -> close) with ratio >= 5x or <= 1/5. near_power_of_ten marks ratios within 5% of 10^k, |k| >= 1.
    A candidate is NOT a confirmed unit change. Confirmation comes only from an exchange announcement
    (unit_changes_confirmed.json, written by hand with sources). Real crashes can look like candidates.
  missing_runs.csv: every run of missing hours for traded symbols over 2020-07..2022-12, with the share of listed
    symbols missing in the same hours. EXCHANGE_WIDE = median share missing >= 50% across the run's hours.
    Otherwise SYMBOL_GAP_LONG (>= 12 h; a halt only if an announcement confirms it) or SYMBOL_GAP_SHORT (< 12 h).
  trade_flags.csv.gz: per entered trade, which candidates and missing-run classes fall inside its ATR window
    (s-14..s, daily) and its hold window (entry 00:00 .. planned exit 23:00, hourly).
Usage (from idx-signals/): ../.venv/bin/python research/EXIT_ATR_v1/anomalies.py <panel .csv.gz>
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[2]
DC = HERE / "research" / "EXIT_ATR_v1" / "data_check"
MAN = HERE / "data" / "manifests" / "binance_1h-20261015T182940Z.jsonl"
FIRST, LAST = "2020-07", "2022-12"
H0 = int(np.datetime64("2020-07-01T00", "h").astype(np.int64))
H1 = int(np.datetime64("2022-12-31T23", "h").astype(np.int64))
JUMP = 5.0
TOL = np.log10(1.05)


def load_all_hourly():
    recs = [json.loads(x) for x in MAN.read_text().splitlines()[1:]]
    files = {}
    for r in recs:
        if FIRST <= r["month"] <= LAST:
            files.setdefault(r["symbol"], []).append(r["file"])
    out = {}
    for s, fs in files.items():
        parts = []
        for f in sorted(fs):
            with zipfile.ZipFile(HERE / "data" / "raw" / f) as z:
                raw = z.read(z.namelist()[0])
            df = pd.read_csv(io.BytesIO(raw), header=None, usecols=range(5), names=["t", "open", "high", "low", "close"])
            if not str(df.iloc[0, 0]).isdigit():
                df = df.iloc[1:]
            parts.append(df.astype(float))
        h = pd.concat(parts, ignore_index=True)
        unit = 1000 if h["t"].max() < 1e14 else 1_000_000
        h["hour"] = (h["t"] // (3600 * unit)).astype(np.int64)
        out[s] = h.drop_duplicates("hour").sort_values("hour").reset_index(drop=True)
    return out


def near_pow10(r):
    lg = np.log10(r)
    k = np.round(lg)
    return (np.abs(lg - k) < TOL) & (np.abs(k) >= 1)


def main(panel_path: Path) -> int:
    H = load_all_hourly()
    n_h = H1 - H0 + 1
    syms = sorted(H)
    pres = np.zeros((len(syms), n_h), dtype=bool)
    listed = np.zeros((len(syms), n_h), dtype=bool)
    for i, s in enumerate(syms):
        hrs = H[s]["hour"].to_numpy() - H0
        hrs = hrs[(hrs >= 0) & (hrs < n_h)]
        pres[i, hrs] = True
        if len(hrs):
            listed[i, hrs.min(): hrs.max() + 1] = True
    share_missing = 1 - pres.sum(0) / np.maximum(listed.sum(0), 1)

    T = pd.read_csv(DC / "coverage.csv.gz", parse_dates=["entry_date", "planned_exit"])
    traded = set(T.ticker + "USDT")
    runs, cands = [], []
    for i, s in enumerate(syms):
        if s not in traded:
            continue
        p, li = pres[i], listed[i]
        miss = li & ~p
        if miss.any():
            d = np.diff(np.concatenate([[0], miss.astype(int), [0]]))
            for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
                med = float(np.median(share_missing[a:b]))
                cls = "EXCHANGE_WIDE" if med >= 0.5 else ("SYMBOL_GAP_LONG" if b - a >= 12 else "SYMBOL_GAP_SHORT")
                runs.append({"symbol": s, "start": str(np.datetime64(int(a + H0), "h")), "hours": int(b - a),
                             "median_share_of_symbols_missing": round(med, 3), "class": cls})
        h = H[s]
        h = h[(h.hour >= H0) & (h.hour <= H1)]
        prev_close, nxt_open = h.close.to_numpy()[:-1], h.open.to_numpy()[1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = nxt_open / prev_close
        gap_h = np.diff(h.hour.to_numpy()) - 1
        hit = np.flatnonzero((r >= JUMP) | (r <= 1 / JUMP))
        for k in hit:
            cands.append({"symbol": s, "source": "hourly", "before": str(np.datetime64(int(h.hour.iloc[k]), "h")),
                          "after": str(np.datetime64(int(h.hour.iloc[k + 1]), "h")), "missing_hours_between": int(gap_h[k]),
                          "price_before": float(prev_close[k]), "price_after": float(nxt_open[k]), "ratio": float(r[k]),
                          "near_power_of_ten": bool(near_pow10(np.array([r[k]]))[0])})
    P = pd.read_csv(panel_path, usecols=["date", "ticker", "open", "close", "previous"], parse_dates=["date"])
    P = P[(P.date >= "2020-06-01") & (P.date <= "2022-12-31") & P.ticker.isin({t[:-4] for t in traded})]
    for col in ("open", "close"):
        with np.errstate(divide="ignore", invalid="ignore"):
            r = P[col] / P["previous"]
        sel = P[(r >= JUMP) | (r <= 1 / JUMP)]
        for row, rr in zip(sel.itertuples(index=False), r[sel.index]):
            cands.append({"symbol": row.ticker + "USDT", "source": f"daily_{col}_vs_prev_close", "before": "",
                          "after": str(row.date.date()), "missing_hours_between": None, "price_before": float(row.previous),
                          "price_after": float(getattr(row, col)), "ratio": float(rr), "near_power_of_ten": bool(near_pow10(np.array([rr]))[0])})
    R = pd.DataFrame(runs)
    C = pd.DataFrame(cands)

    # flags per trade: candidate dates inside the ATR window [s-14, s] or the hold window [entry, planned_exit]
    T["sym"] = T.ticker + "USDT"
    sd = pd.to_datetime(T.signal_date)
    C["day"] = pd.to_datetime(C.after.str[:10])
    flag_cols = {"cand_in_atr_window": [], "cand_in_hold_window": [], "cand_near_pow10_any": []}
    by_sym = {s: g for s, g in C.groupby("symbol")} if len(C) else {}
    for s, a, e, x in zip(T.sym, sd, T.entry_date, T.planned_exit):
        g = by_sym.get(s)
        if g is None:
            for k in flag_cols:
                flag_cols[k].append(False)
            continue
        atr = (g.day >= a - pd.Timedelta(days=14)) & (g.day <= a)
        hold = (g.day >= e) & (g.day <= x)
        flag_cols["cand_in_atr_window"].append(bool(atr.any()))
        flag_cols["cand_in_hold_window"].append(bool(hold.any()))
        flag_cols["cand_near_pow10_any"].append(bool(((atr | hold) & g.near_power_of_ten).any()))
    for k, v in flag_cols.items():
        T[k] = v
    R["s"] = pd.to_datetime(R.start)
    R["e"] = R.s + pd.to_timedelta(R.hours, unit="h")
    gcls = {c: [] for c in ("EXCHANGE_WIDE", "SYMBOL_GAP_LONG", "SYMBOL_GAP_SHORT")}
    rb = {s: g for s, g in R.groupby("symbol")}
    for s, e, x in zip(T.sym, T.entry_date, T.planned_exit + pd.Timedelta(hours=23)):
        g = rb.get(s)
        for c in gcls:
            gcls[c].append(bool(g is not None and ((g["class"] == c) & (g.s <= x) & (g.e > e)).any()))
    for c, v in gcls.items():
        T["gap_" + c.lower()] = v
    C.drop(columns=["day"]).to_csv(DC / "unit_candidates.csv", index=False)
    R.drop(columns=["s", "e"]).to_csv(DC / "missing_runs.csv", index=False)
    T.drop(columns=["sym"]).to_csv(DC / "trade_flags.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    used = T[T.atr_valid | T.cand_in_atr_window]
    summ = {
        "unit_candidates": int(len(C)), "unit_candidates_near_power_of_ten": int(C.near_power_of_ten.sum()) if len(C) else 0,
        "candidate_symbols": sorted(C.symbol.unique().tolist()) if len(C) else [],
        "near_pow10_list": C[C.near_power_of_ten][["symbol", "source", "before", "after", "missing_hours_between", "ratio"]].to_dict("records") if len(C) else [],
        "trades_with_candidate": {arm: {"atr_window": int(g.cand_in_atr_window.sum()), "hold_window": int(g.cand_in_hold_window.sum()),
                                        "near_pow10": int(g.cand_near_pow10_any.sum())} for arm, g in T.groupby("arm")},
        "missing_runs": R["class"].value_counts().to_dict(),
        "trades_with_gap_class": {arm: {c: int(g["gap_" + c.lower()].sum()) for c in gcls} for arm, g in T.groupby("arm")},
        "symbol_gap_long_list": R[R["class"] == "SYMBOL_GAP_LONG"][["symbol", "start", "hours", "median_share_of_symbols_missing"]].to_dict("records"),
    }
    (DC / "ANOMALIES.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("near_pow10_list", "symbol_gap_long_list")}, indent=1, default=str))
    print("NEAR POWER OF TEN:", json.dumps(summ["near_pow10_list"], default=str))
    print("SYMBOL_GAP_LONG:", json.dumps(summ["symbol_gap_long_list"][:40], default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))

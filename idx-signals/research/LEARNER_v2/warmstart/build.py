"""LEARNER_v2 warm start: the historical events the learner starts from, written once and pinned.

Three committed event studies of this lab, all with signal dates before 2024-01-01 (the sealed US holdout, 2024 onward,
is never loaded: the price panel stops at 2023-12-29):

- kill13d: KILL_TEST_2020_2023 (original Schedule 13D filings, FIRE and ABSTAIN), 20-session excess over matched controls;
- form4:   US_INSIDER_BUY stage 1 (open-market insider purchases), 20- and 60-session excess; the second-buy mechanism
           from the same study's committed purchase list;
- dil302:  US_8K_ITEMS stage 1, Item 3.02 (unregistered equity sales, the dilution family's event), 20-session excess.

For each event it records the fields the live learner's features() reads from a sealed set, computed the way the live
scan computes them: the signal session's ret1, ret5, ret20, dd60, volr and cpos from idxsig.rules.moonshot_g.features
on the US repair panel, the 20-session median traded value, and the issuer's other register-like events in the 90
calendar days up to the signal date. Outcomes are the analogues of the live statements: excess > 0 for BEATS_TWINS,
excess < 0 for the dilution family's LOSES_TO_TWINS_20 (the live statements compare with the twins' median, these
studies with the controls' mean: an analogue, which is why the learner gives history its own intercepts and a capped
weight). Survivor-only prices: names delisted before 2026-10 are absent.

Run once: python3 research/LEARNER_v2/warmstart/build.py. Refuses to overwrite events.csv.gz.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from idxsig import global_panel  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
KILL = ROOT / "research" / "CATALYST_REGISTER_v1" / "KILL_TEST_2020_2023" / "results" / "events_all.csv"
F4_DIR = ROOT / "research" / "US_INSIDER_BUY"
F4_20, F4_60 = F4_DIR / "results_stage1" / "events_hold20.csv", F4_DIR / "results_stage1" / "events_hold60.csv"
F4_EVENTS, F4_PURCHASES = F4_DIR / "events.csv", F4_DIR / "form4_purchases.csv.gz"
DIL_20 = ROOT / "research" / "US_8K_ITEMS" / "results_stage1" / "events_3.02_hold20.csv"
DIL_EVENTS = ROOT / "research" / "US_8K_ITEMS" / "events.csv"
OUT, BUILD = HERE / "events.csv.gz", HERE / "BUILD.json"
LAST_DATE = "2023-12-31"
WINDOW_DAYS = 90
SECOND_BUY_SESSIONS = 20


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def signal_features(m: Market) -> dict[str, np.ndarray]:
    f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
    value = np.where(m.tradeable, m.value, np.nan)
    # the live scan: the median of the last 20 sessions' traded value, the signal session included
    adv = pd.DataFrame(value.T).rolling(20, min_periods=1).median().to_numpy().T
    return {**{k: f[k] for k in ("ret1", "ret5", "ret20", "dd60", "volr", "cpos")}, "close": m.close, "adv20_value": adv}


def attach(ev: pd.DataFrame, m: Market, feats: dict[str, np.ndarray]) -> pd.DataFrame:
    ti = pd.Index(m.tickers).get_indexer(ev["ticker"])
    di = pd.Index(m.dates.astype(str)).get_indexer(ev["signal_date"])
    ok = (ti >= 0) & (di >= 0)
    ev = ev[ok].copy()
    ti, di = ti[ok], di[ok]
    for k, a in feats.items():
        ev[k] = a[ti, di]
    return ev


def counts(ev: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    """repeat_90d (same source), corroborate_90d (another source, same direction), conflict_90d (opposite direction):
    distinct events on the same ticker with a date in [signal_date - 90 days, signal_date], this event excluded."""
    by = {t: g for t, g in pool.groupby("ticker")}
    rep, cor, con = [], [], []
    for r in ev.itertuples():
        g = by.get(r.ticker)
        if g is None:
            rep.append(0), cor.append(0), con.append(0)
            continue
        lo = (pd.Timestamp(r.signal_date) - pd.Timedelta(days=WINDOW_DAYS)).date().isoformat()
        w = g[(g["date"] >= lo) & (g["date"] <= r.signal_date) & (g["accession"] != r.accession)]
        rep.append(int((w["source"] == r.source).sum()))
        other = w[w["source"] != r.source]
        cor.append(int((other["direction"] == r.direction).sum()))
        con.append(int((other["direction"] != r.direction).sum()))
    ev = ev.copy()
    ev["repeat_90d"], ev["corroborate_90d"], ev["conflict_90d"] = rep, cor, con
    return ev


def second_buy(ev: pd.DataFrame, purchases: pd.DataFrame, dates: np.ndarray) -> pd.Series:
    """The live MECH_SECOND_BUY_20 rule on the study's purchase list: another purchase filing on the same issuer with a
    filing date after this event's and on or before the 20th session after the signal session."""
    sessions = dates.astype(str)
    by = {c: g for c, g in purchases.groupby("issuer_cik")}
    out = []
    for r in ev.itertuples():
        d = int(np.searchsorted(sessions, r.signal_date))
        if d + SECOND_BUY_SESSIONS >= len(sessions):
            out.append(np.nan)  # the window passes the panel's end: not graded
            continue
        end = sessions[d + SECOND_BUY_SESSIONS]
        g = by.get(r.cik)
        hit = g is not None and bool(((g["filing_date"] > r.public_date) & (g["filing_date"] <= end)
                                      & (g["accession"] != r.accession)).any())
        out.append(float(hit))
    return pd.Series(out, index=ev.index)


def main() -> int:
    if OUT.exists():
        sys.exit(f"error: {OUT.name} exists; the warm start is built once")
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in (KILL, F4_20, F4_60, F4_EVENTS, F4_PURCHASES, DIL_20, DIL_EVENTS)}
    df, meta = global_panel.load(PANEL_MANIFEST)
    if str(df["date"].max().date()) > LAST_DATE:
        sys.exit("error: the panel reaches the sealed holdout")
    m = Market.from_panel(df, price_limits=False)  # as the live US scan (paper._market)
    feats = signal_features(m)

    k = pd.read_csv(KILL, low_memory=False, dtype={"accession": str})
    k = k[(k["status"] == "EXITED") & k["excess"].notna()]
    kill = pd.DataFrame({"source": "kill13d", "accession": k["accession"], "ticker": k["ticker"], "cik": k["subject_cik"],
                         "public_date": k["public_date"], "signal_date": k["signal_date"], "family": "SEC13D",
                         "direction": 1, "position": k["position"], "cls": k["cls"],
                         **{c: k[c].astype(bool) for c in ("DILUTION_RECENT", "MOVED_ALREADY", "MICROCAP", "MV_UNKNOWN")},
                         "bt20": (k["excess"] > 0).astype(float)})

    a = pd.read_csv(F4_20, low_memory=False, dtype={"accession": str})
    b = pd.read_csv(F4_60, low_memory=False, dtype={"accession": str})[["accession", "status", "excess"]]
    a = a.merge(b, on="accession", how="left", suffixes=("", "_60"))
    a = a[(a["status"] == "EXITED") & a["excess"].notna()]
    form4 = pd.DataFrame({"source": "form4", "accession": a["accession"], "ticker": a["ticker"], "cik": a["cik"],
                          "public_date": a["public_date"], "signal_date": a["signal_date"], "family": "FORM4",
                          "direction": 1, "position": "AFTER", "cls": "FIRE", "top_exec": a["top_exec"].astype(bool),
                          "total_value": a["total_value"], "n_owners": a["n_owners"], "lag_days": a["lag_days"],
                          "bt20": (a["excess"] > 0).astype(float),
                          "bt60": np.where((a["status_60"] == "EXITED") & a["excess_60"].notna(),
                                           (a["excess_60"] > 0).astype(float), np.nan)})

    d = pd.read_csv(DIL_20, low_memory=False, dtype={"accession": str})
    d = d[(d["status"] == "EXITED") & d["excess"].notna()]
    dil = pd.DataFrame({"source": "dil302", "accession": d["accession"], "ticker": d["ticker"], "cik": d["cik"],
                        "public_date": d["public_date"], "signal_date": d["signal_date"], "family": "DILUTION_8K",
                        "direction": -1, "position": "AFTER", "cls": "FIRE", "ltt20": (d["excess"] < 0).astype(float)})

    ev = pd.concat([kill, form4, dil], ignore_index=True)
    if ev["signal_date"].max() > LAST_DATE:
        sys.exit("error: an event's signal date reaches the sealed holdout")
    ev = attach(ev, m, feats)

    # the pool for the 90-day counts: every event of the three studies (all stages), dated by filing
    f4e = pd.read_csv(F4_EVENTS, low_memory=False, dtype={"accession": str})
    d8e = pd.read_csv(DIL_EVENTS, low_memory=False, dtype={"accession": str})
    d8e = d8e[d8e["item"].astype(str) == "3.02"] if "item" in d8e.columns else d8e.iloc[0:0]
    pool = pd.concat([
        pd.DataFrame({"source": "kill13d", "accession": k["accession"], "ticker": k["ticker"], "date": k["public_date"], "direction": 1}),
        pd.DataFrame({"source": "form4", "accession": f4e["accession"], "ticker": f4e["ticker"], "date": f4e["public_date"], "direction": 1}),
        pd.DataFrame({"source": "dil302", "accession": d8e["accession"], "ticker": d8e["ticker"], "date": d8e["public_date"], "direction": -1}),
    ], ignore_index=True)
    pool = pool[pool["date"] <= LAST_DATE].dropna(subset=["ticker"])
    ev = counts(ev, pool)

    purchases = pd.read_csv(F4_PURCHASES, low_memory=False, usecols=["accession", "filing_date", "issuer_cik"],
                            dtype={"accession": str})
    is4 = ev["source"] == "form4"
    ev.loc[is4, "second_buy_20"] = second_buy(ev[is4], purchases, m.dates)
    ev["tri60"] = np.where(is4 & ev["second_buy_20"].notna() & ev["bt60"].notna(),
                           ((ev["second_buy_20"] == 1) & (ev["bt60"] == 1)).astype(float), np.nan)
    ev = ev.sort_values(["signal_date", "source", "accession"]).reset_index(drop=True)
    ev.to_csv(OUT, index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.10g")
    summary = {
        "built_by": "research/LEARNER_v2/warmstart/build.py", "panel": {"manifest": PANEL_MANIFEST.name, "sha256": meta["sha256"]},
        "inputs": inputs, "code": {"research/LEARNER_v2/warmstart/build.py": sha(Path(__file__)),
                                   "idxsig/rules/moonshot_g.py": sha(ROOT / "idxsig" / "rules" / "moonshot_g.py")},
        "rows": {s: int((ev["source"] == s).sum()) for s in ("kill13d", "form4", "dil302")},
        "outcomes": {c: {"graded": int(ev[c].notna().sum()), "rate": float(ev[c].mean())}
                     for c in ("bt20", "bt60", "ltt20", "second_buy_20", "tri60")},
        "signal_dates": [str(ev["signal_date"].min()), str(ev["signal_date"].max())],
        "dropped_not_in_panel": int(len(kill) + len(form4) + len(dil) - len(ev)),
        "events_csv_gz": sha(OUT)}
    BUILD.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

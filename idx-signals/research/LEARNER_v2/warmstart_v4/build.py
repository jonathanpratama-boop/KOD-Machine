"""LEARNER v2.4 warm start (v2.3s build with the chart block): the history study's US events (research/PATH_HISTORY_v1, 2020-2023, sealed holdout never
read) through idxsig.learner3 feature code, so the warm start and the live forecasts are the same functions on
the same definitions. Built once; refuses to overwrite. Writes events_us.csv.gz and BUILD.json (inputs by sha256,
the output's sha256 to pin in learner3.HISTORY_SHA256 and protocol_v2_3.json).

Labels: y_NEXT_DUMP10_1 = the study's NEXT_DUMP10 (the next session's close 10% lower, on its own),
y_DUMP10_5 = the study's DUMP10_5 (the 5-session plan 10% down, on its own); None where ungraded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig import global_panel, learner3  # noqa: E402
from idxsig.e1 import _dense  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.learner2 import _clip  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

HERE = Path(__file__).resolve().parent
STUDY = ROOT / "research" / "PATH_HISTORY_v1"
OUT = HERE / "events_us.csv.gz"
PROTO = json.loads((STUDY / "protocol.json").read_text())


def us_market() -> tuple[Market, np.ndarray]:
    d = PROTO["data"]["US"]
    df, meta = global_panel.load(ROOT / d["manifest"])
    assert meta["sha256"] == d["panel_sha256"]
    lo, hi = d["rows_read"]
    df = df[(df["date"] >= lo) & (df["date"] <= hi)].copy()
    m = Market.from_panel(df, price_limits=False)
    m = m.with_units(_dense(m, df, "unit_factor", 1.0))
    f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
    flag = moonshot_g.family_flags(f)["G2_RET30"] & m.tradeable
    return m, flag


def main() -> int:
    if OUT.exists():
        sys.exit(f"error: {OUT.name} exists; the warm start is built once")
    inputs = {str(p.relative_to(ROOT)): sha256_file(p) for p in (
        STUDY / "results" / "events.csv.gz", STUDY / "data" / "us_filings.csv.gz", STUDY / "data" / "us_shares.csv.gz",
        STUDY / "data" / "us_short.csv.gz", ROOT / "idxsig" / "learner3.py")}
    ev = pd.read_csv(STUDY / "results" / "events.csv.gz", dtype={"ticker": str, "session": str, "prev_session": str},
                     keep_default_na=False, na_values=[""])
    ev = ev[ev["market"] == "US"].reset_index(drop=True)
    fil = pd.read_csv(STUDY / "data" / "us_filings.csv.gz", dtype={"ticker": str, "form": str, "filingDate": str})
    by_t = {t: g[["form", "filingDate"]].reset_index(drop=True) for t, g in fil.groupby("ticker")}
    cik_of = fil.groupby("ticker")["cik"].first().to_dict()
    sh = pd.read_csv(STUDY / "data" / "us_shares.csv.gz", dtype={"end": str})
    sh_by = {int(c): [{"end": r.end, "val": r.val} for r in g.itertuples()] for c, g in sh.groupby("cik")}
    sv = pd.read_csv(STUDY / "data" / "us_short.csv.gz", dtype={"ticker": str, "date": str})
    sv = sv[sv["total_volume"] > 0].assign(ratio=lambda x: x["short_volume"] / x["total_volume"])
    sv_by = {t: g.sort_values("date").set_index("date")["ratio"] for t, g in sv.groupby("ticker")}
    m, flag = us_market()
    tickers, dates = list(m.tickers.astype(str)), list(m.dates.astype(str))
    uf = m.unit_factor
    rows, skipped = [], 0
    for r in ev.itertuples(index=False):
        if r.ticker not in tickers or r.session not in dates:
            skipped += 1
            continue
        n, d = tickers.index(r.ticker), dates.index(r.session)
        parts = {k: float(getattr(r, k)) for k in learner3.P0}
        gap = float(r.gap) if pd.notna(r.gap) else 0.0
        parts.update({"gap": _clip(gap / 0.30, -3, 3),
                      "log_price": _clip(np.log10(float(r.price_traded)) - 0.5, -3, 3) if float(r.price_traded) > 0 else 0.0,
                      "breadth": _clip(float(r.breadth) / 3.0, 0, 2),  # the study stored log1p(count)
                      "mkt_ret": _clip(float(r.mkt_ret) / 0.03, -3, 3) if pd.notna(r.mkt_ret) else 0.0})
        parts.update(learner3.bar_features(m, flag, n, d))
        splits = [(dates[k], float(uf[n, k - 1] / uf[n, k])) for k in range(max(1, d - 503), d + 1)
                  if abs(uf[n, k] / uf[n, k - 1] - 1) > 0.01]
        filings = by_t.get(r.ticker)
        shares = sh_by.get(int(cik_of[r.ticker]), []) if r.ticker in cik_of else []
        short = sv_by.get(r.ticker)
        vol = float(r.vol_traded) if pd.notna(r.vol_traded) else None
        parts.update(learner3.edgar_features(filings if filings is not None else (pd.DataFrame(columns=["form", "filingDate"]) if r.ticker in cik_of else None),
                                             shares, short, r.session, r.prev_session, vol, splits))
        row = {"ticker": r.ticker, "session": r.session, **{k: round(float(parts[k]), 6) for k in learner3.FEATURES},
               "y_NEXT_DUMP10_1": ("" if pd.isna(r.S_NEXT_DUMP10) else int(r.S_NEXT_DUMP10)),
               "y_DUMP10_5": ("" if pd.isna(r.S_DUMP10_5) else int(r.S_DUMP10_5))}
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    meta = {"built_at": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "inputs": inputs, "events": len(out),
            "skipped_not_in_panel": skipped, "output": str(OUT.relative_to(ROOT)), "sha256": sha256_file(OUT),
            "labels": {"y_NEXT_DUMP10_1": int(out["y_NEXT_DUMP10_1"].replace("", np.nan).astype(float).notna().sum()),
                       "y_DUMP10_5": int(out["y_DUMP10_5"].replace("", np.nan).astype(float).notna().sum())},
            "rates": {"y_NEXT_DUMP10_1": float(out["y_NEXT_DUMP10_1"].replace("", np.nan).astype(float).mean()),
                      "y_DUMP10_5": float(out["y_DUMP10_5"].replace("", np.nan).astype(float).mean())},
            "coverage": {k: float(out[k].mean()) for k in ("has_edgar", "has_short", "has_shares", "filing_8k", "offering90", "revsplit6m")}}
    (HERE / "BUILD.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({k: v for k, v in meta.items() if k != "inputs"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

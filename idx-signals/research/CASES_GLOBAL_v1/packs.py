"""CASES_GLOBAL_v1 packs: J, J-3, the move, and (US) the issuer's SEC filings 30 days before J through J."""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import catalyst  # noqa: E402
from idxsig.us_actions import SecClient  # noqa: E402

PANELS = {"US": "panel_us-20261008T004105Z.csv.gz", "CRYPTO": "panel_crypto-20261008T003354Z.csv.gz"}
sel = json.loads((HERE / "selection.json").read_text())["cases"]
STAMP = "20261016T185931Z"
cmap = pd.read_csv(ROOT / "research/E9/sec" / f"cik_map-{STAMP}.csv", dtype={"ticker": str}, keep_default_na=False)
cik = {t: int(c) for t, c in zip(cmap.ticker, cmap.cik) if str(c).strip()}
status = {r["cik"]: r for r in json.loads((ROOT / "research/E9/sec" / f"fetch_status-{STAMP}.json").read_text())}
cache = SecClient("offline", ROOT / "data/raw/sec" / STAMP, offline=True)
out = []
for market in sorted({c["market"] for c in sel}):
    cases = [c for c in sel if c["market"] == market]
    if market in PANELS:
        path = ROOT / "data/panel" / PANELS[market]
    else:
        path = sorted((ROOT / "data/panel").glob(f"panel_intl_{market.lower()}-*.csv.gz"))[-1]
    want = {c["ticker"] for c in cases}
    df = pd.concat(ch[ch["ticker"].isin(want)] for ch in pd.read_csv(path, usecols=["date", "ticker", "close", "previous", "volume"],
                                                                       dtype={"ticker": str}, keep_default_na=False, na_values=[""], chunksize=500_000))
    df["date"] = df["date"].astype(str)
    for c in cases:
        g = df[df["ticker"] == c["ticker"]].sort_values("date").reset_index(drop=True)
        i = int(g.index[g["date"] == c["t_date"]][0])
        r = g["close"] / g["previous"]
        J = next((j for j in range(i + 1, min(i + 6, len(g))) if r[j] >= 1.10), i + 1)
        info = {**c, "J_date": g["date"][J], "J3_date": g["date"][J - 3], "t_close": float(g["close"][i]),
                "move_t_to_peak_pct": round(100 * (g["close"][i + 1: i + 6].max() / g["close"][i] - 1), 1),
                "J_day_pct": round(100 * (r[J] - 1), 1)}
        if market == "US":
            k = cik.get(c["ticker"])
            if k is None:
                info["sec"] = "issuer not in the archived submissions"
            else:
                st, body = cache.get(f"https://data.sec.gov/submissions/CIK{k:010d}.json")
                names = (status.get(k) or {}).get("chunk_names") or []
                chunks = [cache.get(f"https://data.sec.gov/submissions/{n}")[1] for n in names]
                f = catalyst.parse_submissions(body, chunks)
                lo = (pd.Timestamp(info["J_date"]) - pd.Timedelta(days=30)).date().isoformat()
                w = f[(f["filingDate"] >= lo) & (f["filingDate"] <= info["J_date"])]
                info["sec"] = [{"filingDate": a, "acceptance": b, "form": fm, "items": it, "doc": d}
                               for a, b, fm, it, d in zip(w["filingDate"], w["acceptanceDateTime"], w["form"],
                                                          w.get("items", [""] * len(w)), w.get("primaryDocDescription", [""] * len(w)))]
        out.append(info)
(HERE / "packs.json").open("x").write(json.dumps(out, indent=1, default=str) + "\n")
for o in out:
    sec = o.get("sec")
    print(o["market"], o["ticker"], "J", o["J_date"], "J-3", o["J3_date"], "move", o["move_t_to_peak_pct"], "Jday", o["J_day_pct"],
          ("SEC " + (sec if isinstance(sec, str) else ", ".join(f"{s['filingDate']} {s['form']}" for s in sec))) if sec is not None else "")

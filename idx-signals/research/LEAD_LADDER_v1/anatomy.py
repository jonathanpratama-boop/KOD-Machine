"""LEAD_LADDER_v1 catalyst anatomy (PROTOCOL.md; descriptive, not gated).

US FAST_UP and SLOW_UP episodes whose issuer is in E9's archived SEC submissions (data/raw/sec/20261016T185931Z,
issuers with a G2_RET30 signal 2020-07..2023), and one matched control per episode from the same covered issuers
(the lead-3 void pool, restricted to covered names, one seeded draw). Each is classed over the calendar window from
30 days before the lead-3 session to the session after t:

  PRIOR    a filing dated on or before the lead-3 session (at most 30 days earlier): a public tell >= 3 sessions out
  LATE     no PRIOR filing, but one dated after the lead-3 session and up to t + 1
  NONE     no filing in the window

The difference between episodes and controls in the PRIOR share is the only number read. Written after the
recorded run; reads no return.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from idxsig import catalyst  # noqa: E402
from idxsig.us_actions import SecClient  # noqa: E402

STAMP = "20261016T185931Z"
LEAD = 3
SEED = 20261026
FORM_GROUPS = {"8-K": "8-K", "8-K/A": "8-K", "4": "FORM 4", "4/A": "FORM 4", "10-Q": "10-Q/10-K", "10-K": "10-Q/10-K",
               "10-Q/A": "10-Q/10-K", "10-K/A": "10-Q/10-K", "S-1": "OFFERING", "S-3": "OFFERING", "424B4": "OFFERING",
               "424B5": "OFFERING", "424B3": "OFFERING", "S-1/A": "OFFERING", "S-3/A": "OFFERING", "SC 13D": "OWNER 13D/G",
               "SC 13G": "OWNER 13D/G", "SC 13G/A": "OWNER 13D/G", "SC 13D/A": "OWNER 13D/G", "6-K": "6-K"}


def filings_by_ticker() -> dict[str, pd.DataFrame]:
    cmap = pd.read_csv(ROOT / "research" / "E9" / "sec" / f"cik_map-{STAMP}.csv", dtype={"ticker": str},
                       keep_default_na=False)
    status = {r["cik"]: r for r in json.loads((ROOT / "research" / "E9" / "sec" / f"fetch_status-{STAMP}.json").read_text())}
    cache = SecClient("offline", ROOT / "data" / "raw" / "sec" / STAMP, offline=True)
    out = {}
    for t, cik in zip(cmap.ticker, cmap.cik):
        if not str(cik).strip():
            continue
        cik = int(cik)
        st, body = cache.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        names = (status.get(cik) or {}).get("chunk_names") or []
        chunks = [cache.get(f"https://data.sec.gov/submissions/{n}")[1] for n in names]
        if st != 200 or any(not c for c in chunks):
            continue
        f = catalyst.parse_submissions(body, chunks)
        out[t] = f[["filingDate", "form"]].assign(filingDate=pd.to_datetime(f["filingDate"]))
    return out


def classify(f: pd.DataFrame | None, u3: pd.Timestamp, t1: pd.Timestamp) -> tuple[str, list[str]]:
    if f is None:
        return "NONE", []
    w = f[(f.filingDate >= u3 - pd.Timedelta(days=30)) & (f.filingDate <= t1)]
    prior = w[w.filingDate <= u3]
    if len(prior):
        return "PRIOR", sorted({FORM_GROUPS.get(x, "OTHER") for x in prior.form})
    if len(w):
        return "LATE", []
    return "NONE", []


def main():
    import run

    lad, study, _ = run.build("US")
    tickers = np.asarray(study.m.tickers).astype(str)
    filings = filings_by_ticker()
    covered = np.isin(tickers, list(filings))
    dates = pd.DatetimeIndex(lad.dates.astype("datetime64[ns]"))
    rng = np.random.default_rng(SEED)
    rows = []
    for kind in ("FAST_UP", "SLOW_UP"):
        n_ev, t_ev = lad.events(kind)
        for n, t in zip(n_ev, t_ev):
            u = t - LEAD
            if not covered[n] or u < 0 or not lad.elig[n, u] or lad.ext[n, u] or t + 1 >= len(dates):
                continue
            pool, _ = lad.pool(n, u, t, kind, True)
            pool = pool[covered[pool]]
            if not len(pool):
                continue
            c = int(rng.choice(pool))
            for role, name in (("episode", n), ("control", c)):
                cls, forms = classify(filings.get(tickers[name]), dates[u], dates[t + 1])
                rows.append({"kind": kind, "role": role, "ticker": tickers[name], "t_date": str(dates[t].date()),
                             "u3_date": str(dates[u].date()), "class": cls, "prior_forms": "|".join(forms)})
    df = pd.DataFrame(rows)
    summary = {"stamp_sec": STAMP, "lead": LEAD, "covered_issuers": int(covered.sum()), "by_kind": {}}
    for kind, g in df.groupby("kind"):
        k = {}
        for role, h in g.groupby("role"):
            n = len(h)
            k[role] = {"n": n, **{c: round(float((h["class"] == c).mean()), 4) for c in ("PRIOR", "LATE", "NONE")},
                       "prior_by_form": {fg: round(float(h["prior_forms"].str.contains(fg, regex=False).mean()), 4)
                                         for fg in sorted(set(FORM_GROUPS.values()) | {"OTHER"})}}
        e, c = k["episode"], k["control"]
        diff = e["PRIOR"] - c["PRIOR"]
        se = float(np.sqrt(e["PRIOR"] * (1 - e["PRIOR"]) / e["n"] + c["PRIOR"] * (1 - c["PRIOR"]) / c["n"]))
        k["prior_share_difference"] = {"episode_minus_control": round(diff, 4), "approx_95": [round(diff - 1.96 * se, 4),
                                                                                             round(diff + 1.96 * se, 4)]}
        summary["by_kind"][kind] = k
    out = HERE / "anatomy"
    out.mkdir(exist_ok=False)
    with (out / "classes.csv").open("x", encoding="utf-8", newline="") as fh:
        df.to_csv(fh, index=False, lineterminator="\n")
    with (out / "summary.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

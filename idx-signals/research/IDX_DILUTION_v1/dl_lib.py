"""IDX_DILUTION_v1: events where IDX's listed-share count rises, from the panel only. A rise is seen at the close of the session it first appears
(posted 16:00 WIB that day, so the harness buys at the next session's close). Splits are excluded: a rise of 30% or more whose raw close-to-close
ratio is within 15% (log) of 1/(1+rise) is a split, not an issue. A name's next event must come at least 20 sessions after its last one."""
import numpy as np
import pandas as pd


def events(df: pd.DataFrame, min_rise: float = 0.01) -> pd.DataFrame:
    d = df.dropna(subset=["listed_shares"]).sort_values(["ticker", "date"]).copy()
    g = d.groupby("ticker")
    d["rise"] = g.listed_shares.pct_change()
    d["raw"] = d.close / g.close.shift(1)
    split = (d.rise >= 0.3) & (np.abs(np.log(d.raw * (1 + d.rise))) < 0.15)
    e = d[(d.rise >= min_rise) & ~split & d.rise.notna()].copy()
    e["n"] = e.groupby("ticker").cumcount()
    out, last = [], {}
    sess = {t: s.reset_index(drop=True) for t, s in d.groupby("ticker").date}
    for r in e.itertuples():
        idx = int(np.searchsorted(sess[r.ticker].values, np.datetime64(r.date)))
        if r.ticker in last and idx - last[r.ticker] < 20:
            continue
        last[r.ticker] = idx
        out.append({"ticker": r.ticker, "date": r.date.strftime("%Y-%m-%d"), "posted_wib": r.date.strftime("%Y-%m-%d") + " 16:00", "rise": r.rise,
                    "shares_before": r.listed_shares / (1 + r.rise), "close": r.close})
    return pd.DataFrame(out)

"""SLOW_10K: the five-way version of tenk_lib.buckets for the descriptive tables (Q1 and Q5 are exactly tenk_lib's: at or below the 20th / at or above the 80th
percentile of the similarities of filings with a strictly earlier filing date within the previous 365 days; Q2-Q4 split the middle at the 40th and 60th percentiles)."""
import numpy as np
import pandas as pd

from tenk_lib import MIN_TRAILING, TRAILING_DAYS


def buckets5(f: pd.DataFrame) -> pd.Series:
    f = f.reset_index(drop=True)
    date = f["filing_date"].to_numpy("datetime64[D]")
    sim = f["cosine"].to_numpy(float)
    ok = np.isfinite(sim)
    out = np.full(len(f), "", dtype=object)
    for i in np.flatnonzero(ok):
        window = ok & (date < date[i]) & (date >= date[i] - np.timedelta64(TRAILING_DAYS, "D"))
        if window.sum() < MIN_TRAILING:
            continue
        p20, p40, p60, p80 = np.percentile(sim[window], [20, 40, 60, 80])
        out[i] = "Q1" if sim[i] <= p20 else "Q5" if sim[i] >= p80 else "Q2" if sim[i] <= p40 else "Q3" if sim[i] <= p60 else "Q4"
    return pd.Series(out, index=f.index)

"""IDX_INSIDER_NEWS_OOT step 6, counts only: of the audited INSIDER_BUY events, how many map to the panel and can be bought under the
harness (hold 20). Prints status counts and event counts; no return, control value or price is printed or saved (the harness computes
returns internally; they are not looked at). Also checks that the window constants follow from the panel calendar. GO rule (PROTOCOL.md):
at least 100 events with status EXITED. Writes feasibility/FEASIBILITY.json (refuses to overwrite).
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS_OOT/feasibility.py"""
import json
import sys

import numpy as np
import pandas as pd

from oot_common import END, FIRST, HERE, LAST, ROOT, SEALED_END, START, last_posting_date, load_old

sys.path.insert(0, str(ROOT))
from idxsig import idx_events  # noqa: E402

GO_MIN_EXITED = 100


def main() -> int:
    out = HERE / "feasibility" / "FEASIBILITY.json"
    if out.exists():
        sys.exit("error: feasibility/FEASIBILITY.json exists")
    r2 = load_old("run_v2")
    events = pd.read_csv(HERE / "events.csv")
    df, reg, meta = r2.load_inputs()
    sessions = np.array(sorted(df.date.unique()), dtype="datetime64[D]")
    post = sessions[sessions > np.datetime64(SEALED_END)]
    calendar = {"START": (START, str(post[0])), "FIRST": (FIRST, str(post[5])), "LAST": (LAST, last_posting_date(post)), "END": (END, str(post[-1]))}
    bad = {k: v for k, v in calendar.items() if v[0] != v[1]}
    if bad:
        sys.exit(f"error: the window constants do not follow from the panel calendar: {bad}")
    prep = idx_events.prepare(df, reg, START, END)
    res = idx_events.run_events(prep, events, r2.config(r2.PRIMARY), draws=5, seed=r2.SEED)
    ex = res[res.status == "EXITED"]
    half = lambda s: s.str[:4] + np.where(s.str[5:7].astype(int) <= 6, "H1", "H2")  # noqa: E731
    counts = {
        "events_in_table": int(len(events)), "tickers_in_table": int(events.ticker.nunique()),
        "events_by_half_year": {k: int(v) for k, v in events.groupby(half(events.posted_wib)).size().items()},
        "mapped_to_panel": int(len(res)), "not_in_panel": int(len(events) - len(res)),
        "status_counts": idx_events.status_counts(res), "exited": int(len(ex)),
        "exited_by_half_year": {k: int(v) for k, v in ex.groupby(half(ex.posted_wib)).size().items()},
        "exited_without_any_scored_control_draw": int((ex.control_n == 0).sum()),
        "match_levels_of_exited": {int(k): int(v) for k, v in ex.match_level.value_counts().sort_index().items()},
        "distinct_posting_days_exited": int(ex.posted_wib.str[:10].nunique()),
        "go_rule": f"EXITED events at hold 20 >= {GO_MIN_EXITED} (fixed in PROTOCOL.md before this run)", "go": bool(len(ex) >= GO_MIN_EXITED),
    }
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(counts, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

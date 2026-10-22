"""BINANCE_ANN_1S_HOLDOUT step 1, counts only: which announcements dated 2024-01-01 .. 2026-09-30 are 'launch of a token's USDT-margined
Binance futures perpetual' events under the rule of BINANCE_ANN_1M/feasibility.py (loaded unchanged): a first archived perpetual day 0-7 days
after the article, a spot USDT pair of at least 30 days and a median daily quote volume of at least USD 1,000,000 over the 30 sessions before.
Reads titles and times, daily quote volumes and the futures archive's file names; no trade and no return. Needs AUTHORIZATION.md.
Writes feasibility/{events.csv, FEASIBILITY.json} (refuses to overwrite). GO rule: at least 40 eligible events.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1S_HOLDOUT/events.py
"""
import json
import sys
import time

import numpy as np
import pandas as pd

from hold_common import GO_MIN_ELIGIBLE, HERE, M1, WINDOW_END, WINDOW_START, load, require_authorization, require_pinned_code


def main() -> int:
    require_authorization()
    require_pinned_code()
    out_dir = HERE / "feasibility"
    if (out_dir / "FEASIBILITY.json").exists():
        sys.exit("error: feasibility/FEASIBILITY.json exists")
    fm = load(M1 / "feasibility.py", "ann1m_feasibility")
    ann = pd.read_csv(M1 / "announcements.csv.gz")
    ann["t"] = pd.to_datetime(ann.release_ms, unit="ms", utc=True)
    lo, hi = pd.Timestamp(WINDOW_START, tz="UTC"), pd.Timestamp(WINDOW_END, tz="UTC")
    ann = ann[(ann.t >= lo) & (ann.t < hi)].sort_values("t")
    launches = ann[ann.title.map(fm.is_launch)].copy()
    launches["tokens"] = launches.title.map(fm.tokens)
    daily = fm.load_daily()
    perp_cache: dict[str, str | None] = {}
    rows, no_token, no_pair = [], [], []
    for r in launches.itertuples():
        if not r.tokens:
            no_token.append(r.title)
        for tok in r.tokens:
            pair = fm.pair_for(tok, daily)
            perp = tok + "USDT"
            if pair is not None and perp not in perp_cache:
                perp_cache[perp] = fm.perp_first_date(perp)
                time.sleep(0.2)
            d0 = perp_cache.get(perp)
            lag = (pd.Timestamp(d0, tz="UTC") - r.t.normalize()).days if d0 else None
            rec = {"article_id": r.id, "t_ms": r.release_ms, "t": r.t.isoformat(), "title": r.title, "token": tok, "pair": pair, "perp": perp,
                   "perp_first_day": d0, "days_to_perp": lag}
            if pair is None:
                no_pair.append(tok)
            else:
                d = daily[pair]
                before = d[d.date < r.t.normalize()]
                rec["age_days"] = int((r.t.normalize() - d.date.iloc[0]).days)
                rec["adv30_usdt"] = float(before.qv.tail(fm.ADV_DAYS).median()) if len(before) >= fm.ADV_DAYS else np.nan
            rows.append(rec)
    ev = pd.DataFrame(rows)
    ev["launch_ok"] = ev.days_to_perp.between(0, fm.LAUNCH_WITHIN_DAYS)
    ev["eligible"] = (ev.launch_ok & ev.pair.notna() & (ev.age_days >= fm.MIN_AGE_DAYS) & (ev.adv30_usdt >= fm.MIN_ADV_USDT)).fillna(False)
    ev["event_key"] = ev.article_id.astype(str) + "|" + ev.token
    out_dir.mkdir(exist_ok=True)
    ev.to_csv(out_dir / "events.csv", index=False)
    el = ev[ev.eligible]
    day = pd.to_datetime(el.t_ms, unit="ms", utc=True)
    counts = {
        "launch_articles_in_window": int(len(launches)), "articles_without_a_token": len(no_token), "token_rows": int(len(ev)),
        "with_usdt_spot_pair": int(ev.pair.notna().sum()), "perp_first_day_found": int(ev.perp_first_day.notna().sum()),
        "perp_started_0_to_7_days_after_article": int((ev.launch_ok & ev.pair.notna()).sum()),
        "and_spot_age_ok": int((ev.launch_ok & (ev.age_days >= fm.MIN_AGE_DAYS)).sum()), "eligible_events": int(len(el)),
        "eligible_by_year": {str(k): int(v) for k, v in el.groupby(day.dt.year).size().items()},
        "eligible_distinct_days": int(day.dt.date.nunique()), "eligible_median_adv30_usdt": float(el.adv30_usdt.median()) if len(el) else None,
        "go_rule": f"eligible events >= {GO_MIN_ELIGIBLE} (fixed in PROTOCOL.md before this run)", "go": bool(len(el) >= GO_MIN_ELIGIBLE),
    }
    (out_dir / "FEASIBILITY.json").write_text(json.dumps({"counts": counts, "articles_without_a_token": no_token,
                                                          "tokens_without_spot_pair": sorted(set(no_pair))}, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

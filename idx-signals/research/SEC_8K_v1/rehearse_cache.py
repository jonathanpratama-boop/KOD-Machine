"""Plumbing rehearsal only: builds events from E9's cached submissions (1,235 issuers picked because they rallied; biased, never a result) and runs
hold 60 on Stage 1 to check the pipeline end to end. Writes nothing into the study folder except rehearsal/."""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from idxsig import event_study as es, global_panel  # noqa: E402
import sk_lib  # noqa: E402

CACHE = ROOT / "data" / "raw" / "sec" / "20261016T185931Z"
cmap = pd.read_csv(HERE.parent / "SLOW_10K" / "filings.csv.gz", usecols=["cik", "ticker"], dtype={"ticker": str}, keep_default_na=False).drop_duplicates("cik").set_index("cik").ticker
recs = []
for meta in CACHE.glob("*.json"):
    url = json.loads(meta.read_text())["url"]
    if "/CIK" not in url:
        continue
    cik = int(url.split("CIK")[1][:10])
    if cik not in cmap.index:
        continue
    recs += [{**r, "cik": cik, "ticker": cmap[cik]} for r in sk_lib.rows(json.loads(meta.with_suffix(".bin").read_bytes()))]
ev = sk_lib.events(pd.DataFrame(recs))
print(len(recs), "rows;", len(ev), "events;", ev.groupby("stage").size().to_dict())
df, _ = global_panel.load(ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json")
prep = es.prepare_us(df, "2020-06-01", "2023-12-29")
s1 = ev[ev.stage == 1]
out = []
for k, g in s1.groupby("kind"):
    if len(g) < 30:
        continue
    r = es.run_events(prep, g, es.us_config(60), draws=50, seed=20261007)
    f = r[r.excess.notna()]
    out.append({"kind": k, "n": len(f), "mean": f.excess.mean(), "t": f.excess.mean() / f.excess.std() * len(f) ** 0.5 if len(f) > 2 else float("nan")})
(HERE / "rehearsal").mkdir(exist_ok=True)
t = pd.DataFrame(out).sort_values("t")
t.to_csv(HERE / "rehearsal" / "cache_stage1_hold60.csv", index=False)
print(t.round(4).to_string(index=False))

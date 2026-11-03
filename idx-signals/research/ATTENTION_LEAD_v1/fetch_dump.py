"""ATTENTION_LEAD_v1 bulk fetch (ADDENDUM_2): stream Wikimedia monthly pageview_complete user dumps, keep only en.wikipedia
lines for the articles in articles.csv, stop each stream once past the en.wikipedia section. Resumable per month (raw/).
Then: validate against pv_raw.jsonl (API) and write pageviews.csv.gz + fetch_manifest_dump.json."""
import calendar, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"; RAW.mkdir(exist_ok=True)
art = pd.read_csv(HERE / "articles.csv")
art["key"] = art.title.str.replace(" ", "_")
(RAW / "titles.txt").write_text("\n".join(sorted(set(art.key))) + "\n")
MONTHS = [f"{y}{m:02d}" for y in range(2020, 2024) for m in range(1, 13) if (y, m) >= (2020, 6)]
AWK = r'''BEGIN{FS=" "} NR==FNR{t[$0]=1; next}
$1=="en.wikipedia"{seen=1; if($2 in t) print; next}
seen && $1>"en.wikipedia"{print "#END"; exit}'''

def month(ym):
    out = RAW / f"{ym}.txt"
    if out.exists() and out.read_text()[-5:] == "#END\n": return ym, "cached"
    url = f"https://dumps.wikimedia.org/other/pageview_complete/monthly/{ym[:4]}/{ym[:4]}-{ym[4:]}/pageviews-{ym}-user.bz2"
    for attempt in range(4):
        cmd = f"set -o pipefail; curl -sS --fail --retry 3 '{url}' | bzip2 -dc | LC_ALL=C awk '{AWK}' {RAW/'titles.txt'} - > {out}.part"
        subprocess.run(["bash", "-c", cmd])
        p = Path(f"{out}.part")
        if p.exists() and p.read_text()[-5:] == "#END\n": p.rename(out); return ym, "ok"
    return ym, "FAIL"

with ThreadPoolExecutor(4) as ex:
    for ym, s in ex.map(month, MONTHS): print(ym, s, flush=True)

rows = []
for ym in MONTHS:
    y, m = int(ym[:4]), int(ym[4:])
    for line in (RAW / f"{ym}.txt").read_text().splitlines():
        if line == "#END": continue
        f = line.split(" ")
        enc, i = f[5] if len(f) > 5 else "", 0
        while i < len(enc):
            d = ord(enc[i]) - 64; j = i + 1
            while j < len(enc) and enc[j].isdigit(): j += 1
            if 1 <= d <= calendar.monthrange(y, m)[1]: rows.append((f[1], f"{y}-{m:02d}-{d:02d}", int(enc[i+1:j])))
            i = j
dv = pd.DataFrame(rows, columns=["key", "date", "views"]).groupby(["key", "date"], as_index=False).views.sum()
pv = art[["ticker", "key"]].merge(dv, on="key")[["ticker", "date", "views"]]

# validation gate against the API records
api = [json.loads(l) for l in (HERE / "pv_raw.jsonl").open()]
a = pd.DataFrame([(x["ticker"], f"{d[:4]}-{d[4:6]}-{d[6:8]}", v) for x in api if x["status"] == 200 for d, v in x["items"]],
                 columns=["ticker", "date", "api"])
cmp_ = a.merge(pv, on=["ticker", "date"], how="left").fillna({"views": 0})
match = float((cmp_.api == cmp_.views).mean()) if len(cmp_) else float("nan")
man = {"source": "pageview_complete monthly user dumps", "months": MONTHS, "articles": int(art.key.nunique()),
       "articles_found": int(pv.ticker.nunique()), "rows": len(pv), "validation_article_days": len(cmp_),
       "validation_exact_match": match, "validation_articles": int(a.ticker.nunique()),
       "within_1pct": float(((cmp_.api - cmp_.views).abs() <= 0.01 * cmp_.api.clip(lower=1)).mean()) if len(cmp_) else None}
(HERE / "fetch_manifest_dump.json").write_text(json.dumps(man, indent=1) + "\n")
print(json.dumps(man, indent=1))
if not match >= 0.95: print("VALIDATION GATE FAILED: not writing pageviews.csv.gz"); sys.exit(1)
pv.to_csv(HERE / "pageviews.csv.gz", index=False, compression="gzip")
print("wrote pageviews.csv.gz", len(pv))

"""ATTENTION_LEAD_v1 resumable page-view fetch (fetch.py hit Wikimedia's rate limit at 8 parallel requests and was killed
before writing anything). One request at a time, honours Retry-After on 429, appends each article to pv_raw.jsonl so a
restart resumes. When all articles are done, writes pageviews.csv.gz and fetch_manifest.json. Same URLs and fields as fetch.py."""
import hashlib, json, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
UA = "KOD-Machine-research/1.0 (paper research; generic client)"
RAW = HERE / "pv_raw.jsonl"
m = pd.read_csv(HERE / "articles.csv")
done = {json.loads(l)["ticker"] for l in RAW.open()} if RAW.exists() else set()
gap = 1.0
for r in m.itertuples():
    if r.ticker in done: continue
    t = urllib.parse.quote(r.title.replace(" ", "_"), safe="")
    u = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{t}/daily/20200601/20231231"
    while True:
        time.sleep(gap)
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as resp:
                s, body = resp.status, resp.read(); gap = max(0.5, gap * 0.9); break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                gap = min(30, gap * 2); time.sleep(float(e.headers.get("Retry-After") or 10)); continue
            s, body = e.code, b""; break
        except Exception:
            time.sleep(10); continue
    items = [(it["timestamp"][:8], it["views"]) for it in json.loads(body).get("items", [])] if s == 200 else []
    with RAW.open("a") as f:
        f.write(json.dumps({"ticker": r.ticker, "url": u, "status": s, "sha256": hashlib.sha256(body).hexdigest(), "items": items}) + "\n")
    done.add(r.ticker)
    if len(done) % 100 == 0: print(len(done), "of", len(m), "gap", round(gap, 2), flush=True)
recs = [json.loads(l) for l in RAW.open()]
pv = pd.DataFrame([(x["ticker"], d, v) for x in recs for d, v in x["items"]], columns=["ticker", "date", "views"])
pv.to_csv(HERE / "pageviews.csv.gz", index=False, compression="gzip")
(HERE / "fetch_manifest.json").write_text(json.dumps({"articles": len(m), "requests": len(recs), "ok": sum(x["status"] == 200 for x in recs),
    "rows": len(pv), "log": [{k: x[k] for k in ("ticker", "url", "status", "sha256")} for x in recs]}) + "\n")
print("done", len(pv), "rows")

"""ATTENTION_LEAD_v1 fetch: Wikidata ticker->enwiki article map, then Wikimedia daily page views 2020-06-01..2023-12-31.
Writes articles.csv and pageviews.csv.gz (ticker, date, views) plus fetch_manifest.json. Usage: python3 fetch.py"""
import concurrent.futures as cf, gzip, hashlib, json, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UA = "KOD-Machine-research/1.0 (paper research; generic client)"
Q = """SELECT ?t ?title WHERE { ?c p:P414 ?st . ?st ps:P414 ?ex ; pq:P249 ?t . VALUES ?ex { wd:Q82059 wd:Q13677 }
?a schema:about ?c ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title . }"""

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return 404, b""
            time.sleep(2 * 2 ** k)
        except Exception:
            time.sleep(2 * 2 ** k)
    return 0, b""

def main():
    st, b = get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(Q))
    rows = [(x["t"]["value"].strip().upper().replace(".", "-"), x["title"]["value"]) for x in json.loads(b)["results"]["bindings"]]
    m = pd.DataFrame(rows, columns=["ticker", "title"]).drop_duplicates().sort_values(["ticker", "title"]).drop_duplicates("ticker")
    panel = set(pd.read_csv(ROOT / "data/panel/panel_us_repair-20261008T114805Z.csv.gz", usecols=["ticker"]).ticker.astype(str))
    m = m[m.ticker.isin(panel)].reset_index(drop=True)
    m.to_csv(HERE / "articles.csv", index=False)
    print("wikidata", len(rows), "in panel", len(m), flush=True)
    log, out = [], []
    def one(r):
        t = urllib.parse.quote(r.title.replace(" ", "_"), safe="")
        u = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{t}/daily/20200601/20231231"
        s, body = get(u); time.sleep(0.05)
        return r.ticker, u, s, body
    with cf.ThreadPoolExecutor(8) as ex:
        for k, (tk, u, s, body) in enumerate(ex.map(one, m.itertuples()), 1):
            log.append({"url": u, "status": s, "sha256": hashlib.sha256(body).hexdigest()})
            if s == 200:
                for it in json.loads(body).get("items", []):
                    out.append((tk, it["timestamp"][:8], it["views"]))
            if k % 500 == 0: print(k, len(out), flush=True)
    pv = pd.DataFrame(out, columns=["ticker", "date", "views"])
    pv.to_csv(HERE / "pageviews.csv.gz", index=False, compression="gzip")
    (HERE / "fetch_manifest.json").write_text(json.dumps({"articles": len(m), "requests": len(log), "ok": sum(x["status"] == 200 for x in log), "rows": len(pv), "log": log}) + "\n")
    print("done", len(pv), "rows;", sum(x["status"] == 200 for x in log), "of", len(log), "ok")
main()

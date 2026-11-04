"""Read-only live rate check: what each sensor would have caught on recent EDGAR days. Writes nothing to any ledger."""
import sys, json, collections
sys.path.insert(0, "/home/user/KOD-Machine/idx-signals")
from datetime import datetime, timezone
from idxsig import catalysts as cr, fam_form4 as f4, fam_form4_sharp as fs, paper, speculation as spec

client = cr.sec_client()
ledger = paper.ledger_lines()
scan = cr._scan_for(ledger, "US", "2026-10-28")
universe = set(cr._universe(spec.scan_features(scan))["ticker"])
st, tm = client.get(cr.TICKERS_URL); by_cik, _ = cr.ticker_maps(tm)
out = {}
for day in ("2026-10-26", "2026-10-27", "2026-10-28"):
    log, purchases, counts, reasons, unread, dig, rows = f4.read_filings(client, [day], today="2026-10-29")
    ev = f4.group_events(purchases)
    inu = [e for e in ev if any(t in universe for t in by_cik.get(e["issuer_cik"], []))]
    sharp = [e for e in inu if fs.sharp(e["top_exec"], e["total_value"])["sharp"]]
    hi = []
    out[day] = {"index": log[0]["status"], "form4_filings": log[0].get("form4_filings"), "purchase_events": len(ev),
                "in_scan_universe": len(inu), "sharp_before_dilution_and_routine": len(sharp),
                "not_purchase": reasons, "unreadable": len(unread),
                "events": [(e["symbol"], round(e["total_value"]), e["top_exec"], e["n_owners"]) for e in inu]}
    print(day, json.dumps({k: v for k, v in out[day].items() if k != "events"}), flush=True)
    for e in out[day]["events"]: print("   ", e)
# 8-K Item 3.02 and 13D originals over the feeds' recent pages
pages8k, n302 = [], []
for k in range(9):
    s_, b = client.get(f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&start={100*k}&count=100&output=atom")
    import re
    for e in re.findall(r"<entry>(.*?)</entry>", b.decode("utf-8", "replace"), re.S):
        upd = re.search(r"<updated>(.*?)</updated>", e).group(1); summ = re.search(r"<summary[^>]*>(.*?)</summary>", e, re.S)
        if summ and "Item 3.02" in summ.group(1) and "(Filer)" in e: n302.append(upd[:10])
        pages8k.append(upd)
print("8-K feed span", min(pages8k), "to", max(pages8k), "| Item 3.02 filer entries by day:", dict(collections.Counter(n302)))
ents = []
for k in range(5):
    s_, b = client.get(cr.FEED_URL.format(start=100*k)); ents += cr.parse_feed(b)
orig = cr.originals(ents)
print("13D feed span", min(e["accepted"] for e in ents), "to", max(e["accepted"] for e in ents),
      "| originals by day:", dict(collections.Counter(o["accepted"][:10] for o in orig)))
json.dump(out, open("/tmp/claude-0/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/scratchpad/live/rates.json", "w"), indent=1, default=str)

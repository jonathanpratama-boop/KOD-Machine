"""Fetch the ETHUSDT spot 1d monthly archives pinned in FRESH_EYES_v1's manifest, verify each sha256, and also fetch
months published after the pin (recorded in a separate manifest). Usage: python3 fetch_pinned.py MANIFEST RAW_DIR OUT_MANIFEST"""
import hashlib, json, sys, time, urllib.request
from pathlib import Path
man, raw, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
BASE = "https://data.binance.vision/"
def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "KOD-research"}), timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return 404, b""
        except Exception:
            pass
        time.sleep(2 * 2 ** i)
    return 0, b""
rows = [json.loads(l) for l in open(man) if '"ETHUSDT' in l or 'ETHUSDT/' in l]
rows = [r for r in rows if "/ETHUSDT/1d/" in r["key"]]
ok = bad = 0
for r in rows:
    st, b = get(BASE + r["key"])
    dst = raw / r["key"]; dst.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(b).hexdigest()
    if st == 200 and h == r["sha256"]:
        dst.write_bytes(b); ok += 1
    else:
        bad += 1; print("MISMATCH", r["key"], st, h[:12], r["sha256"][:12])
print("pinned files:", len(rows), "verified:", ok, "failed:", bad)
last = max(r["key"] for r in rows)  # ...ETHUSDT-1d-YYYY-MM.zip
y, m = map(int, last.rsplit("-1d-", 1)[1][:7].split("-"))
ext = []
while True:
    m += 1
    if m == 13: y, m = y + 1, 1
    key = f"data/spot/monthly/klines/ETHUSDT/1d/ETHUSDT-1d-{y:04d}-{m:02d}.zip"
    st, b = get(BASE + key)
    if st != 200: break
    dst = raw / key; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b)
    ext.append({"key": key, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
out.write_text("".join(json.dumps(e) + "\n" for e in ext))
print("months after the pin:", [e["key"].rsplit("-1d-", 1)[1][:7] for e in ext])

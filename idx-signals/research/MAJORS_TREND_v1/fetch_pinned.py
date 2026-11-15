"""Fetch the spot 1d monthly archives pinned in FRESH_EYES_v1's manifest for the given symbols and verify each sha256.
Usage: python3 fetch_pinned.py MANIFEST RAW_DIR SYMBOL [SYMBOL ...]"""
import hashlib, json, sys, time, urllib.request
from pathlib import Path
man, raw, syms = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
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
rows = [json.loads(l) for l in open(man) if l.strip()]
tot = {}
for s in syms:
    sel = [r for r in rows if f"/{s}/1d/" in r["key"]]
    ok = bad = 0
    for r in sel:
        st, b = get(BASE + r["key"])
        h = hashlib.sha256(b).hexdigest()
        if st == 200 and h == r["sha256"]:
            dst = raw / r["key"]; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b); ok += 1
        else:
            bad += 1; print("MISMATCH", r["key"], st, h[:12], r["sha256"][:12])
    tot[s] = (len(sel), ok, bad)
print(json.dumps(tot))

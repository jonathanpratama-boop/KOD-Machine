"""Holdout data fetch for COMBO_HOLDOUT_v1 (frozen protocol on GitHub, branch hermes/ignition-combo-holdout-v1, ac14151).
Refresh the Binance spot listing, fix the universe (exclusions fixed below, before any outcome), and write URL lists for
1h klines 2022-11..2026-10 (Nov-Dec 2022 = warm-up only) and 1d klines 2023-01..2026-10 (2017-08..2022-12 daily already
on disk from the same source). Writes raw_holdout/universe_holdout.json."""
import re, subprocess, json, os
ROOT = os.path.dirname(os.path.abspath(__file__)); RH = os.path.join(ROOT, "raw_holdout"); os.makedirs(RH, exist_ok=True)
syms, marker = [], ""
while True:
    url = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/spot/monthly/klines/&delimiter=/" + (f"&marker={marker}" if marker else "")
    x = subprocess.run(["curl", "-s", url], capture_output=True, text=True).stdout
    syms += re.findall(r"<Prefix>data/spot/monthly/klines/([^/]+)/</Prefix>", x)
    m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
    if "<IsTruncated>true" not in x or not m: break
    marker = m.group(1)
usdt = sorted({s for s in syms if s.endswith("USDT")})
LEV = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")
STABLE_BASES = {"USDC", "BUSD", "TUSD", "FDUSD", "USDP", "PAX", "DAI", "EUR", "GBP", "AUD", "SUSD", "UST", "USDS", "USDSB",
                "AEUR", "EURI", "PAXG", "XUSD", "USD1", "BFUSD", "RLUSD", "TRY", "BRL", "USDE", "PYUSD", "USTC", "ZAR", "UAH",
                "NGN", "RUB", "IDRT", "BIDR", "BVND", "VAI", "XAUT"}
def excluded(s):
    base = s[:-4]
    return s.endswith(LEV) or base in STABLE_BASES or (base.endswith("USD") and len(base) <= 6)
uni = [s for s in usdt if not excluded(s)]
json.dump({"listing_symbols": len(syms), "usdt": len(usdt), "universe": uni, "excluded": [s for s in usdt if excluded(s)],
           "stable_bases": sorted(STABLE_BASES)}, open(os.path.join(RH, "universe_holdout.json"), "w"), indent=1)
months = [(y, m) for y in range(2022, 2027) for m in range(1, 13) if (2022, 11) <= (y, m) <= (2026, 10)]
with open(os.path.join(RH, "urls_1h.txt"), "w") as f:
    for s in uni:
        for y, m in months: f.write(f"https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{y}-{m:02d}.zip\n")
with open(os.path.join(RH, "urls_1d.txt"), "w") as f:
    for s in uni:
        for y, m in months:
            if (y, m) >= (2023, 1): f.write(f"https://data.binance.vision/data/spot/monthly/klines/{s}/1d/{s}-1d-{y}-{m:02d}.zip\n")
print(len(syms), len(usdt), len(uni))

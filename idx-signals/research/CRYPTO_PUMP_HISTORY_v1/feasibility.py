"""CRYPTO_PUMP_HISTORY_v1 feasibility: counts only, no price read, no feature computed. Unions the three lists, lists the
Binance archive's hourly kline months for every BTC pair, and reports events per year, candidate pairs per event month
and how many events have archive bars. Writes results/FEASIBILITY.json."""
from __future__ import annotations

import collections
import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import events as E  # noqa: E402

LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="


def listing(prefix: str) -> list[str]:
    keys, marker = [], ""
    while True:
        url = LIST + prefix + (f"&marker={marker}" if marker else "")
        for k in range(6):
            try:
                body = urllib.request.urlopen(url, timeout=60).read().decode()
                break
            except Exception:
                if k == 5:
                    raise
                time.sleep(3 * (k + 1))
        keys += re.findall(r"<Key>([^<]+)</Key>", body) + re.findall(r"<Prefix>([^<]+)</Prefix>", body)
        if "<IsTruncated>true" not in body:
            return keys
        marker = re.findall(r"<NextMarker>([^<]+)</NextMarker>", body)[0]


def main() -> int:
    syms = sorted({k.split("/")[-2] for k in listing("data/spot/monthly/klines/") if k.endswith("/") and k.split("/")[-2].endswith("BTC")})
    def months(s):
        ks = listing(f"data/spot/monthly/klines/{s}/1h/")
        return s, sorted({m.group(1) for k in ks for m in [re.search(r"-1h-(\d{4}-\d{2})\.zip$", k)] if m})
    with cf.ThreadPoolExecutor(4) as ex:
        avail = dict(ex.map(months, syms))
    ev = E.events()
    per_month = collections.Counter(m for s, ms in avail.items() for m in ms)
    with_bars = [e for e in ev if e["date"][:7] in set(avail.get(e["pair"], []))]
    out = {"btc_pairs_in_archive": len(syms), "pairs_with_hourly": sum(bool(v) for v in avail.values()),
           "events_union": len(ev), "events_with_hourly_month": len(with_bars),
           "events_by_year": dict(sorted(collections.Counter(e["date"][:4] for e in ev).items())),
           "events_by_source_count": dict(collections.Counter(len(e["sources"]) for e in ev)),
           "distinct_pumped_pairs": len({e["pair"] for e in ev}),
           "repeat_pumped_pairs": sum(1 for c in collections.Counter(e["pair"] for e in ev).values() if c > 1),
           "missing_pairs": sorted({e["pair"] for e in ev} - {s for s, v in avail.items() if v}),
           "candidates_per_event_month": {k: per_month[k] for k in sorted({e["date"][:7] for e in ev})},
           "hourly_files": sum(len(v) for v in avail.values()),
           "first_event": ev[0]["time"].isoformat(), "last_event": ev[-1]["time"].isoformat(),
           "hour_of_day": dict(sorted(collections.Counter(e["time"].hour for e in ev).items()))}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "FEASIBILITY.json").write_text(json.dumps(out, indent=1) + "\n")
    (HERE / "results" / "archive_months.json").write_text(json.dumps(avail) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "candidates_per_event_month"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

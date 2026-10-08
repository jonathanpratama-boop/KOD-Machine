"""Price facts for KOD-R-ZEAL-20250312, as defined in 01_protocol/protocol.json (fact_definitions).

Measures reuse E1-SIGNALS-v1 (idx-signals/research/E1/protocol.json), computed at the close of the
last Copenhagen session at or before each information set's cutoff, from the pinned series only:

  ret5, ret20  close_t / close_{t-k} - 1
  rngr         ((high - low) / previous close) / median of the same over t-20..t-1
  vol20        std of daily log returns over t-19..t
  price_already_repriced     ret20 >= +30%
  volume_creep_before_story  median volume t-4..t / median volume t-24..t-5 >= 1.5
  price_quiet_vs_own_range   median rngr over t-4..t <= 1.0 and |ret5| <= 2 * vol20 * sqrt(5)

Run from anywhere: python3 price_facts.py  ->  writes price_facts.json next to this file.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = HERE.parent / "01_protocol" / "pin" / "ZEAL.CO.json"
PIN_SHA = "a20b3934ebc11a3f4d44e9e11d73e5636ecf3543994ce58ad5b10d6b40598b8b"
SETS = {  # set -> cutoff (UTC); Copenhagen closes 17:00 CET = 16:00Z in Feb/Mar 2025
    "T-30D": "2025-02-09T16:00:00Z",
    "T-72H": "2025-03-08T16:00:00Z",
    "T-24H": "2025-03-10T16:00:00Z",
    "DECISION": "2025-03-11T16:00:00Z",
}


def bars() -> list[dict]:
    raw = PIN.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN_SHA:
        raise SystemExit("pinned price file does not match its sha256")
    r = json.loads(raw)["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = []
    for i, ts in enumerate(r["timestamp"]):
        row = {k: q[k][i] for k in ("open", "high", "low", "close", "volume")}
        if None in row.values():
            continue
        row["date"] = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
        out.append(row)
    return out


def measures(b: list[dict], t: int) -> dict:
    c = [x["close"] for x in b]
    rng = [(b[i]["high"] - b[i]["low"]) / b[i - 1]["close"] for i in range(1, len(b))]  # rng[i-1] is bar i
    rng_at = lambda i: rng[i - 1]  # noqa: E731
    rngr = [rng_at(i) / statistics.median(rng_at(j) for j in range(i - 20, i)) for i in range(t - 4, t + 1)]
    logret = [math.log(c[i] / c[i - 1]) for i in range(t - 19, t + 1)]
    vol20 = statistics.stdev(logret)
    ret5, ret20 = c[t] / c[t - 5] - 1, c[t] / c[t - 20] - 1
    v_recent = statistics.median(b[i]["volume"] for i in range(t - 4, t + 1))
    v_base = statistics.median(b[i]["volume"] for i in range(t - 24, t - 4))
    creep = v_recent / v_base
    quiet_band = 2 * vol20 * math.sqrt(5)
    return {
        "session": b[t]["date"], "close": c[t], "ret5": ret5, "ret20": ret20, "vol20": vol20,
        "median_rngr_5": statistics.median(rngr), "volume_ratio_5_vs_20": creep,
        "median_volume_5": v_recent, "median_volume_prior_20": v_base, "quiet_band_abs_ret5": quiet_band,
        "facts": {
            "price_already_repriced": ret20 >= 0.30,
            "volume_creep_before_story": creep >= 1.5,
            "price_quiet_vs_own_range": statistics.median(rngr) <= 1.0 and abs(ret5) <= quiet_band,
        },
    }


def main() -> None:
    b = bars()
    out = {"source": str(PIN.relative_to(HERE.parent)), "sha256": PIN_SHA, "definitions": __doc__.split("\n\n")[1], "sets": {}}
    for name, cutoff in SETS.items():
        day = cutoff[:10]
        t = max(i for i, x in enumerate(b) if x["date"] <= day)
        out["sets"][name] = {"cutoff": cutoff, **measures(b, t)}
    (HERE / "price_facts.json").write_text(json.dumps(out, indent=2) + "\n")
    for name, s in out["sets"].items():
        print(name, s["session"], f"close {s['close']:.1f} ret5 {s['ret5']:+.1%} ret20 {s['ret20']:+.1%} "
              f"rngr5 {s['median_rngr_5']:.2f} volx {s['volume_ratio_5_vs_20']:.2f} band {s['quiet_band_abs_ret5']:.1%}",
              s["facts"])


if __name__ == "__main__":
    main()

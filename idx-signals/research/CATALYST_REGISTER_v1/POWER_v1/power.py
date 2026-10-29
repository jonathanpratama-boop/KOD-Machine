"""POWER_v1: the arithmetic of time to an answer, from numbers the lab already holds (ADDENDUM_3.md).

time_to_answer = pairs_needed / events_per_year,   pairs_needed = (t_min x sd / edge)^2

sd is measured from test 26's scored events (research/US_INSIDER_BUY/results_stage1/events_hold{20,60}.csv, pinned
by sha256 below): a design-stage read of the spread of a test already reported, not a new effect estimate. Event rates
are the lab's own counts. Writes POWER.md beside this file. Usage (from idx-signals/): python3 research/CATALYST_REGISTER_v1/POWER_v1/power.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FILES = {20: ("research/US_INSIDER_BUY/results_stage1/events_hold20.csv", "7daf3c3997bad56f43579e48a10fc4faee321fa0b89d8c8d6042dc85ca5a7fab"),
         60: ("research/US_INSIDER_BUY/results_stage1/events_hold60.csv", "93b9e1de0e1e145261042619e4aae2ebc35f51f3cecb8fa81799a11922488a8e")}
T_MIN = 3.0            # the lab's standing floor
T_CONVENTIONAL = 2.33  # one-sided p = 0.01, for the cost comparison only
RATES = {  # events per year, from the lab's own counts
    "SEC13D (FIRE)": (125, "302 FIRE events over 2020-07..2022-11 in KILL_TEST_2020_2022 (2.42 years)"),
    "DILUTION_8K": (779, "1,558 Item 3.02 events over 2021-2022 in US_8K_ITEMS (test 27)"),
    "FORM4": (1482, "2,964 scored purchase events over 2021-2022 in US_INSIDER_BUY (test 26)"),
    "FORM4 above USD 20": (748, "1,496 of test 26's events in price band 3"),
    "DOCUMENT_CLASS (pooled)": (125 + 779 + 1482, "the three parents together"),
}
EDGES = (0.005, 0.010, 0.015, 0.020, 0.030)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def winsor(v, pct):
    lo, hi = np.percentile(v, [pct, 100 - pct])
    return np.clip(v, lo, hi)


def spread_table() -> tuple[list[str], dict]:
    rows, sd = ["| Hold | Subset | n | mean excess | sd of excess |", "|---|---|---|---|---|"], {}
    for hold, (rel, pin) in FILES.items():
        p = ROOT / rel
        got = sha(p)
        if got != pin:
            raise SystemExit(f"{rel}: sha256 {got} differs from the pin {pin}")
        d = pd.read_csv(p, low_memory=False).dropna(subset=["excess"])
        e = d["excess"].astype(float).values
        subsets = [("all events", e), ("winsorised 5%", winsor(e, 5)), ("top-executive buyers", d.loc[d["top_exec"].astype(bool), "excess"].astype(float).values)]
        for b in sorted(d["price_band"].unique()):
            subsets.append((f"price band {int(b)}", d.loc[d["price_band"] == b, "excess"].astype(float).values))
        for name, v in subsets:
            rows.append(f"| {hold} | {name} | {len(v):,} | {v.mean():+.2%} | {v.std(ddof=1):.3f} |")
            sd[(hold, name)] = (float(v.mean()), float(v.std(ddof=1)), int(len(v)))
    return rows, sd


def pairs(sd_: float, edge: float, t: float = T_MIN) -> int:
    return int(np.ceil((t * sd_ / edge) ** 2))


def main() -> int:
    rows, sd = spread_table()
    s20 = sd[(20, "all events")][1]
    s20_hi = sd[(20, "price band 3")][1]
    out = ["# POWER_v1: how long until a family can answer", "",
           "`pairs_needed = (t_min x sd / edge)^2`, `years = pairs_needed / events_per_year`. sd is the spread of one set's "
           "paired excess, measured below; edge is the true mean excess, which nobody knows and which the table therefore "
           "scans. t_min is 3.0, the lab's standing floor.", "",
           "## Spread, measured (test 26's scored events; a design read, not a new effect read)", "", *rows, "",
           f"Hit rate at hold 20 in test 26: 46.5% beside a mean excess of +1.0%. The edge is a minority of large winners.", "",
           "## Pairs needed at t >= 3.0", "",
           "| Edge | sd 0.156 (hold 20, all) | sd 0.098 (hold 20, above USD 20) | sd 0.308 (hold 60, all) |", "|---|---|---|---|"]
    s60 = sd[(60, "all events")][1]
    for e in EDGES:
        out.append(f"| {e:.1%} | {pairs(s20, e):,} | {pairs(s20_hi, e):,} | {pairs(s60, e):,} |")
    out += ["", f"At the conventional one-sided 0.01 (t 2.33) the same rows need {(T_CONVENTIONAL / T_MIN) ** 2:.0%} of these pairs; "
            "the t >= 3.0 floor is kept, so the difference is a stated cost.", "",
            "## Years to an answer at t >= 3.0 (hold 20, sd 0.156, except the above-20 row at sd 0.098)", "",
            "| Family | Events a year | " + " | ".join(f"edge {e:.1%}" for e in EDGES) + " |",
            "|---|---|" + "---|" * len(EDGES)]
    for name, (rate, src) in RATES.items():
        s_ = s20_hi if "above USD 20" in name else s20
        out.append(f"| {name} | {rate:,} | " + " | ".join(f"{pairs(s_, e) / rate:.1f}" for e in EDGES) + " |")
    out += ["", "Sources of the rates:", *[f"- {k}: {v[1]}" for k, v in RATES.items()], "",
            "## Reading it", "",
            "- The published activist-filing drift is one to three percent per event. SEC13D alone cannot answer in under "
            "a decade at any edge in that range; the kill test is what can retire it quickly.",
            "- FORM4 answers in about a year if its edge is near the 1% test 26 found, and in months only if the edge is "
            "larger than that.",
            "- Pooling (DOCUMENT_CLASS) is the only free lever on the rate; price is the cheapest lever on the spread.",
            "- The per-session statistic the registers use clusters sets by signal session, so with many events a day "
            "the number of sessions, not the number of sets, bounds the t; min_sessions in the looks covers that.",
            "", "Pinned inputs: " + ", ".join(f"`{rel}` {pin[:12]}" for rel, pin in FILES.values()) + "."]
    (HERE / "POWER.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

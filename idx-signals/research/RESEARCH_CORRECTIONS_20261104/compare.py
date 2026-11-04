"""Original against corrected NEIGHBOURS_v1 and PRESSURE_v1 numbers, read by README.md's rule.

Reads only the two frozen original RESULT.json files and the two corrected-run RESULT.json
files in this folder. It computes no new statistic. Every number is copied from a RESULT.json;
the only derived values are the verdicts (README.md's rule applied to a copied interval) and
the year counts (comparisons of two copied means). The first run writes comparison.json; a
later run fails if a fresh comparison differs from that file, then prints the same tables.

    python3 idx-signals/research/RESEARCH_CORRECTIONS_20261104/compare.py   (from the repo root)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
HORIZONS = ("fwd3", "fwd1", "fwd5")
YEARS = tuple(str(y) for y in range(2021, 2027))
STUDIES = {
    "NEIGHBOURS_v1": {
        "models": ("A", "B", "C"),
        "pairs": (("B", "A"), ("C", "B")),
        "original_verdicts": {
            "B-A": "neighbours_add_information",
            "C-B": "next_stop_adds_information",
        },
        "original_years": {"B-A": "years_B_beats_A", "C-B": "years_C_beats_B"},
    },
    "PRESSURE_v1": {
        "models": ("A", "P"),
        "pairs": (("P", "A"),),
        "original_verdicts": {"P-A": None},
        "original_years": {"P-A": "years_P_beats_A"},
    },
}


def load(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"missing result file: {path}")
    return json.loads(path.read_text())


def verdict(lo95, hi95) -> str:
    """README.md: CONFIRMED unless the interval lies entirely above zero; none: NOT DETERMINED."""
    if lo95 is None or hi95 is None:
        return "NOT DETERMINED"
    return "CHANGED" if lo95 > 0 else "CONFIRMED"


def original_ic(original: dict, horizon: str, model: str) -> float:
    value = original["ic"][horizon][model]
    return value["mean"] if isinstance(value, dict) else value


def original_difference(study: str, original: dict, horizon: str, pair: str) -> dict:
    diffs = original["ic_diff"]
    record = diffs[horizon] if study == "PRESSURE_v1" else diffs[f"{horizon}_{pair}"]
    return {k: record[k] for k in ("mean", "lo95", "hi95")}


def original_verdict(study: str, original: dict, pair: str) -> str:
    """PRESSURE_v1 records its verdict as a string; NEIGHBOURS_v1 as one boolean per pair."""
    key = STUDIES[study]["original_verdicts"][pair]
    value = original["reading"] if key is None else original["reading"][key]
    if value not in (False, "NO INCREMENTAL VALUE"):
        raise SystemExit(f"{study} {pair}: original verdict {value!r} is not the recorded null")
    return "NO INCREMENTAL VALUE"


def original_years(study: str, original: dict, pair: str) -> int:
    key = STUDIES[study]["original_years"][pair]
    return original[key] if study == "PRESSURE_v1" else original["reading"][key]


def corrected_years(decisions: dict, model: str, baseline: str) -> dict:
    """Years whose observed top-5 mean beats the baseline's; flags unknown picks and no mean."""
    beats, unknown, undetermined = 0, [], []
    for year in YEARS:
        m, b = decisions[model]["by_year"][year], decisions[baseline]["by_year"][year]
        if m["unknown"] or b["unknown"]:
            unknown.append(year)
        if m["gross_observed_mean"] is None or b["gross_observed_mean"] is None:
            undetermined.append(year)
        elif m["gross_observed_mean"] > b["gross_observed_mean"]:
            beats += 1
    return {
        "years_beating": beats,
        "years_with_unknown_picks": unknown,
        "years_without_observed_mean": undetermined,
    }


def compare(study: str, original: dict, corrected: dict) -> dict:
    spec = STUDIES[study]
    out = {
        "rows_test": {"original": original.get("rows_test"), "corrected": corrected["rows_test"]},
        "days_test": {"original": original.get("days_test"), "corrected": corrected["days_test"]},
        "promotion": corrected["promotion"],
        "evaluator_version": corrected["evaluator_version"],
        "evaluator_sha256": corrected["evaluator_sha256"],
        "inputs": corrected["inputs"],
        "training": corrected["training"],
        "comparisons": {},
        "ic": {},
        "ic_differences": {},
        "information_denominators": {},
        "decisions": {},
    }
    for model, baseline in spec["pairs"]:
        pair = f"{model}-{baseline}"
        record = corrected["ic_differences"][f"fwd3_{pair}"]
        out["comparisons"][pair] = {
            "original": {
                **original_difference(study, original, "fwd3", pair),
                "verdict": original_verdict(study, original, pair),
                "years_beating": original_years(study, original, pair),
            },
            "corrected": {**record, **corrected_years(corrected["decisions"], model, baseline)},
            "verdict": verdict(record["lo95"], record["hi95"]),
        }
    for horizon in HORIZONS:
        info = corrected["information"][horizon]
        out["ic"][horizon] = {
            m: {
                "original": original_ic(original, horizon, m),
                "corrected": info["mean_daily_rank_correlation"][m],
            }
            for m in spec["models"]
        }
        out["information_denominators"][horizon] = {
            k: info[k]
            for k in ("eligible_rows", "known_rows", "unknown_rows", "days_with_nonconstant_target")
        }
        for model, baseline in spec["pairs"]:
            pair = f"{model}-{baseline}"
            out["ic_differences"][f"{horizon}_{pair}"] = {
                "original": original_difference(study, original, horizon, pair),
                "corrected": corrected["ic_differences"][f"{horizon}_{pair}"],
            }
    for method, record in corrected["decisions"].items():
        before = original["decisions"].get(method)
        out["decisions"][method] = {
            "original": None
            if before is None
            else {
                "rebalances": before.get("n_rebalances"),
                "gross_mean": before["gross_mean"],
                "net_0.004": before["net_0.4pct"],
                "net_0.02": before["net_2pct_etoro"],
                "by_year_gross": before["by_year_gross"],
            },
            "corrected": {k: v for k, v in record.items() if k != "metric"},
        }
    return out


def recorded(x) -> str:
    return "not recorded" if x is None else str(x)


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:+.2f}%"


def num(x) -> str:
    return "n/a" if x is None else f"{x:+.4f}"


def interval(r: dict) -> str:
    return f"{num(r['mean'])} ({num(r['lo95'])} .. {num(r['hi95'])})"


def days(r: dict) -> str:
    return f"{r['known_days']} / {r['unknown_days']}"


def row(*cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def header(*names: str, align: str) -> list[str]:
    """A Markdown table header; align has one character per column, l(eft) or r(ight)."""
    return ["", row(*names), "|" + "".join("---|" if a == "l" else "---:|" for a in align)]


def tables(study: str, c: dict) -> list[str]:
    models = STUDIES[study]["models"]
    sides = [(m, side) for m in models for side in ("original", "corrected")]
    side_names = [f"{m} {side}" for m, side in sides]
    lines = [f"### {study}"]

    lines += header("", "Original", "Corrected", align="lrr")
    for label, key in (("Test rows", "rows_test"), ("Test days", "days_test")):
        lines.append(row(label, recorded(c[key]["original"]), c[key]["corrected"]))

    names = ("3-day comparison", "Original mean (95%)", "Corrected mean (95%)")
    lines += header(*names, "Known / unknown IC days", "Verdict", align="lllll")
    for pair, r in c["comparisons"].items():
        k = r["corrected"]
        lines.append(row(pair, interval(r["original"]), interval(k), days(k), r["verdict"]))

    names = ("Top 5 beats baseline's top 5", "Original years", "Corrected years")
    lines += header(*names, "Corrected years with unknown picks", align="lrrl")
    for pair, r in c["comparisons"].items():
        k = r["corrected"]
        before, after = r["original"]["years_beating"], k["years_beating"]
        flagged = ", ".join(k["years_with_unknown_picks"]) or "none"
        lines.append(row(pair, f"{before} of 6", f"{after} of 6", flagged))

    lines += header("Horizon", *side_names, align="l" + "r" * len(sides))
    for h, ic in c["ic"].items():
        lines.append(row(h, *(num(ic[m][side]) for m, side in sides)))

    names = ("IC difference", "Original mean (95%)", "Corrected mean (95%)")
    lines += header(*names, "Known / unknown IC days", align="llll")
    for key, r in c["ic_differences"].items():
        k = r["corrected"]
        lines.append(row(key, interval(r["original"]), interval(k), days(k)))

    names = ("Horizon", "Eligible rows", "Known outcome", "Unknown outcome", "Days with an IC")
    lines += header(*names, align="lrrrr")
    keys = ("eligible_rows", "known_rows", "unknown_rows", "days_with_nonconstant_target")
    for h, r in c["information_denominators"].items():
        lines.append(row(h, *(r[k] for k in keys)))

    names = ("Picks", "Original gross", "Corrected gross (observed)", "Corrected net 0.4%")
    names += ("Corrected net 2%", "Selected", "Known", "Unknown", "Rebalances", "Status")
    lines += header(*names, align="lrrrrrrrrl")
    for method, r in c["decisions"].items():
        o, k = r["original"], r["corrected"]
        before = "not recorded" if o is None else pct(o["gross_mean"])
        net = k["net_observed_means"]
        cells = (pct(k["gross_observed_mean"]), pct(net["0.004"]), pct(net["0.02"]))
        counts = (k["selected_picks"], k["known_picks"], k["unknown_picks"], k["rebalances"])
        lines.append(row(method, before, *cells, *counts, k["status"]))

    lines += header("Year (top 5, gross)", *side_names, align="l" + "r" * len(sides))
    for year in YEARS:
        cells = []
        for m in models:
            k = c["decisions"][m]["corrected"]["by_year"][year]
            mark = f" ({k['unknown']} unknown)" if k["unknown"] else ""
            cells.append(pct(c["decisions"][m]["original"]["by_year_gross"][year]))
            cells.append(pct(k["gross_observed_mean"]) + mark)
        lines.append(row(year, *cells))

    names = ("Refit", "Training rows (known label)", "Training rows (unknown label)")
    lines += header(*names, "Prediction rows", align="lrrr")
    keys = ("train_rows_known", "train_rows_unknown", "prediction_rows")
    for t in c["training"]:
        lines.append(row(t["refit_at"][:10], *(t[k] for k in keys)))
    return lines + [""]


def main() -> int:
    sources = {}
    comparison = {"reading_rule": "README.md", "sources": sources, "studies": {}}
    for study in STUDIES:
        paths = (RESEARCH / study / "RESULT.json", HERE / study / "RESULT.json")
        for path in paths:
            name = str(path.relative_to(RESEARCH.parent.parent))
            sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        comparison["studies"][study] = compare(study, *(load(p) for p in paths))
    payload = json.dumps(comparison, indent=1, allow_nan=False) + "\n"
    target = HERE / "comparison.json"
    if target.exists():
        if target.read_text() != payload:
            raise SystemExit("comparison.json differs from a fresh comparison of the results")
        print("comparison.json matches a fresh comparison", file=sys.stderr)
    else:
        target.write_text(payload)
    for study, c in comparison["studies"].items():
        print("\n".join(tables(study, c)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

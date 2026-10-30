"""Fixed-budget, chronological pre-move discovery benchmark.

Run with python -m idxsig.premove --input panel.csv.gz --source-manifest COLLECTION.json.
This extends E2/E5 with sequence features and comparable alert-budget metrics.
It does not claim profit, untouched historical evidence, or a deployed policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from .premove_core import TARGETS, build_examples, fit_model, prepare_panel
from .provenance import PKG_ROOT, build_stamp, publish_bytes, sha256_file, utc_stamp, write_csv_gz_exclusive

PROTOCOL = PKG_ROOT / "research/PREMOVE_SEQUENCE_v1/protocol.json"
METHODS = ("simple", "g2", "summary", "sequence")
TEMPERATURES = (.5, 1., 2., 4.)


def period(frame, start, end, *, known=False):
    """Cut decision dates; fitting additionally purges cross-boundary labels."""
    selected = frame.date.between(pd.Timestamp(start), pd.Timestamp(end)) & frame.eligible
    if known:
        selected &= frame.label_known & (frame.label_end_date <= pd.Timestamp(end))
    return frame.loc[selected].copy()


def probabilities(raw, temperature=1.0):
    raw = np.asarray(raw, dtype=float)
    if raw.ndim != 2 or raw.shape[1] != 3 or not np.isfinite(raw).all() or (raw < 0).any():
        raise ValueError("invalid three-class probabilities")
    if not np.allclose(raw.sum(axis=1), 1, atol=1e-8) or not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("invalid probability sum or temperature")
    logits = np.log(np.clip(raw, 1e-12, 1)) / temperature
    logits -= logits.max(axis=1, keepdims=True)
    values = np.exp(logits)
    return values / values.sum(axis=1, keepdims=True)


def probability_metrics(p, y):
    if len(p) == 0:
        return {"n": 0, "log_loss": None, "brier_multiclass": None, "up_brier": None}
    p = probabilities(p)
    y = np.asarray(y, dtype=float)
    if y.shape != p.shape or not np.isin(y, [0, 1]).all() or not np.all(y.sum(axis=1) == 1):
        raise ValueError("expected known one-hot labels")
    return {"n": len(p), "log_loss": float(-(y * np.log(np.clip(p, 1e-12, 1))).sum(axis=1).mean()),
            "brier_multiclass": float(((p - y) ** 2).sum(axis=1).mean()),
            "up_brier": float(((p[:, 0] - y[:, 0]) ** 2).mean())}


def calibrate(raw, y):
    if not len(raw):
        raise ValueError("empty calibration set")
    losses = {str(t): probability_metrics(probabilities(raw, t), y)["log_loss"] for t in TEMPERATURES}
    best = min(TEMPERATURES, key=lambda t: (losses[str(t)], t))
    return best, losses


def shortlist(pool, method, k=5):
    """All current eligible candidates compete; future completeness is irrelevant."""
    if method not in METHODS or type(k) is not int or k < 1:
        raise ValueError("invalid shortlist method or budget")
    pool = pool.copy()
    if pool.duplicated(["date", "ticker"]).any():
        raise ValueError("duplicate candidate")
    pool["simple_score"] = .5 * pool.groupby("date").baseline_volume.rank(pct=True) + .5 * pool.groupby("date").baseline_volatility.rank(pct=True)
    if method == "simple":
        pool["rank_score"] = pool.simple_score
    elif method == "g2":
        pool["rank_score"] = 2 * pool.baseline_g2 + pool.simple_score
    else:
        pool["rank_score"] = pool[f"{method}_up"]
    if not np.isfinite(pool.rank_score).all():
        raise ValueError("non-finite ranking score")
    chosen = pool.sort_values(["date", "rank_score", "ticker"], ascending=[True, False, True], kind="stable").groupby("date", sort=True).head(k).copy()
    chosen["rank"] = chosen.groupby("date").cumcount() + 1
    chosen["method"] = method
    return chosen


def episodes(pool, horizon=5):
    """Assign positive windows to anchored, non-chaining event clusters."""
    ids = pd.Series(index=pool.index, dtype="object")
    positive = pool.loc[pool.label_known & (pool.up_first == 1)]
    for ticker, group in positive.groupby("ticker", sort=True):
        anchor = None
        event = None
        for index, row in group.sort_values(["first_hit_date", "date"]).iterrows():
            hit = pd.Timestamp(row.first_hit_date)
            if pd.isna(hit):
                raise ValueError("positive label has no first-hit date")
            if anchor is None or (hit - anchor).days > horizon:
                anchor = hit
                event = f"{ticker}|{anchor.date().isoformat()}"
            ids.loc[index] = event
    return ids


def alert_metrics(pool, selected):
    known = selected.label_known.astype(bool)
    positives = known & (selected.up_first == 1)
    n, n_known, hits = len(selected), int(known.sum()), int(positives.sum())
    all_events = set(pool.episode_id.dropna())
    event_dates = pool.dropna(subset=["episode_id"]).groupby("episode_id").first_hit_date.min()
    anchors = selected.episode_id.map(event_dates)
    timely = positives & (selected.date < anchors)
    caught = set(selected.loc[timely, "episode_id"].dropna())
    first_alerts = selected.loc[timely].groupby("episode_id").date.min()
    lead = (event_dates.reindex(first_alerts.index) - first_alerts).dt.days
    daily = selected.assign(hit=positives.astype(int), unknown=(~known).astype(int)).groupby("date").agg(
        selected=("ticker", "size"), hits=("hit", "sum"), censored=("unknown", "sum"))
    # Calendar days without any eligible names are retained as no-selection days.
    calendar = pd.date_range(pool.date.min(), pool.date.max(), freq="D") if len(pool) else pd.DatetimeIndex([])
    daily = daily.reindex(calendar, fill_value=0).rename_axis("date")
    result = {"candidate_windows": len(pool), "selected": n, "known_selected": n_known, "up_hits": hits,
              "false_alerts_known": n_known - hits, "censored_selected": n - n_known,
              "precision_lower_bound": hits / n if n else None,
              "precision_upper_bound": (hits + n - n_known) / n if n else None,
              "precision_known": hits / n_known if n_known else None,
              "known_episodes": len(all_events), "episodes_caught": len(caught),
              "episodes_missed": len(all_events - caught),
              "positive_alerts_after_episode_started": int((positives & ~timely).sum()),
              "episode_recall_known": len(caught) / len(all_events) if all_events else None,
              "median_earliest_alert_lead_days": float(lead.median()) if len(lead) else None,
              "mean_earliest_alert_lead_days": float(lead.mean()) if len(lead) else None,
              "calendar_days": len(calendar), "days_with_selection": int((daily.selected > 0).sum())}
    return result, daily


def paired_bootstrap(a, b, *, seed=20261030, draws=400, block=10):
    """Paired contiguous day blocks; censored selections remain in denominator."""
    a, b = a.align(b, join="outer", axis=0, fill_value=0)
    def rate(x):
        return x[:, 0].sum() / x[:, 1].sum() if x[:, 1].sum() else np.nan
    x, y = a[["hits", "selected"]].to_numpy(), b[["hits", "selected"]].to_numpy()
    if not len(x) or not x[:, 1].sum() or not y[:, 1].sum():
        return {"delta": None, "lower95": None, "upper95": None, "draws": 0}
    rng, estimates = np.random.default_rng(seed), []
    width = min(block, len(x))
    for _ in range(draws):
        starts = rng.integers(0, len(x) - width + 1, size=int(np.ceil(len(x) / width)))
        index = np.concatenate([np.arange(s, s + width) for s in starts])[:len(x)]
        value = rate(x[index]) - rate(y[index])
        if np.isfinite(value):
            estimates.append(value)
    low, high = np.quantile(estimates, [.025, .975]) if estimates else (np.nan, np.nan)
    return {"delta": float(rate(x) - rate(y)), "lower95": float(low) if np.isfinite(low) else None,
            "upper95": float(high) if np.isfinite(high) else None, "draws": len(estimates), "block_days": width, "seed": seed}


def evaluate(examples, protocol):
    frame = examples.frame
    periods = protocol["periods"]
    train = period(frame, *periods["train"], known=True)
    calibration = period(frame, *periods["calibration"], known=True)
    test = period(frame, *periods["test"])
    if min(len(train), len(calibration), len(test)) == 0:
        raise ValueError("train, calibration and test must each contain eligible rows")
    records, calibration_details = {}, {}
    for name, seq in (("summary", ()), ("sequence", examples.sequence_columns)):
        model = fit_model(train, examples.feature_columns, seq, pca_components=8, ridge=protocol["models"]["ridge"])
        record = model.record()
        if not all(record.get("converged", [True])):
            raise ValueError(f"{name} fit did not converge; no benchmark verdict published")
        temperature, losses = calibrate(model.predict(calibration), calibration.loc[:, TARGETS].to_numpy())
        test_probabilities = probabilities(model.predict(test), temperature)
        for k, target in enumerate(TARGETS):
            test[f"{name}_{('up', 'down', 'neither')[k]}"] = test_probabilities[:, k]
        records[name] = record
        calibration_details[name] = {"temperature": temperature, "candidate_log_losses": losses}
    labelled = test.label_known
    y = test.loc[labelled, TARGETS].to_numpy()
    distribution = train.loc[:, TARGETS].mean().to_numpy()
    prob_metrics = {"train_base_rate": probability_metrics(np.tile(distribution, (len(y), 1)), y)}
    for name in ("summary", "sequence"):
        prob_metrics[name] = probability_metrics(test.loc[labelled, [f"{name}_up", f"{name}_down", f"{name}_neither"]].to_numpy(), y)
    evaluations, selections, days, differences = {}, [], [], {}
    for population in ("all", "early"):
        pool = test.copy() if population == "all" else test.loc[(test.ret1 < .10) & (test.ret5 < .20)].copy()
        pool["episode_id"] = episodes(pool)
        evaluations[population] = {}
        daily_by_method = {}
        for method in METHODS:
            selected = shortlist(pool, method, protocol["evaluation"]["top_k"])
            metrics, daily = alert_metrics(pool, selected)
            evaluations[population][method] = metrics
            daily_by_method[method] = daily
            selected["population"] = population
            selections.append(selected)
            days.append(daily.assign(population=population, method=method).reset_index())
        differences[population] = {f"sequence_minus_{baseline}": paired_bootstrap(daily_by_method["sequence"], daily_by_method[baseline])
                                   for baseline in ("simple", "summary")}
    counts = {name: {"rows": len(part), "first_decision": str(part.date.min().date()),
                     "last_decision": str(part.date.max().date()),
                     "last_label_end": str(part.label_end_date.max().date()),
                     "class_counts": {target: int(part[target].sum()) for target in TARGETS}}
              for name, part in (("train", train), ("calibration", calibration))}
    summary = {"protocol_id": protocol["protocol_id"], "created_at": utc_stamp(), "fit_periods": counts,
               "test": {"eligible_rows": len(test), "known_rows": int(labelled.sum()), "censored_rows": int((~labelled).sum()),
                        "tickers": int(test.ticker.nunique()), "decision_days": int(test.date.nunique())},
               "calibration": calibration_details, "probability_metrics": prob_metrics,
               "shortlists": evaluations, "paired_precision_differences": differences,
               "interpretation": "Retrospective chronological model test on previously studied history. No profitability, live performance or untouched-holdout claim."}
    return summary, records, test, pd.concat(selections, ignore_index=True), pd.concat(days, ignore_index=True)


def render_report(summary):
    def pct(value):
        return "n/a" if value is None else f"{value * 100:.2f}%"
    lines = ["# Pre-move sequence benchmark", "", summary["interpretation"], "",
             "Four methods share each population's daily candidate pool and five-name budget. Unknown future outcomes remain selectable.", "",
             "| Population | Method | Alerts | Up hits | Known false alerts | Censored | Precision lower bound | Episodes caught / known | Median lead days |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for pop, methods in summary["shortlists"].items():
        for method, m in methods.items():
            lines.append(f"| {pop} | {method} | {m['selected']} | {m['up_hits']} | {m['false_alerts_known']} | {m['censored_selected']} | {pct(m['precision_lower_bound'])} | {m['episodes_caught']} / {m['known_episodes']} | {m['median_earliest_alert_lead_days']} |")
    lines += ["", "## Paired uncertainty", "", "Ten-day moving-block bootstrap; differences in daily shortlist hit rate, percentage points. These intervals are not profit intervals.", ""]
    for pop, comparisons in summary["paired_precision_differences"].items():
        for name, d in comparisons.items():
            lines.append(f"- {pop}, {name}: {pct(d['delta'])}; 95% interval [{pct(d['lower95'])}, {pct(d['upper95'])}].")
    lines += ["", "## What the result does and does not establish", "",
              "The sequence model adds eight train-fitted PCA components of recent return/range/volume sequences to a fourteen-feature summary baseline. This is a lightweight learned-sequence challenger, not Kronos or a rerun of E5's full feature model.", "",
              "The early population excludes names already up 10% today or 20% over five days. G2 cannot trigger in that population, so its fixed-budget ranking reduces to the simple comparator there.", "",
              "Targets use the next open and future closes. Intra-day path order, slippage, stops, transaction costs and executable profits are not evaluated. Missing and truncated terminal bars censor outcomes; recall covers only observable episodes. Extreme raw price changes are preserved and may include corporate unit changes.", "",
              "The universe is recovered from today's archive catalog. Removed/unavailable instruments and source revisions can bias results. Train/calibration/test periods are chronologically separated, but 2023 has been used in earlier KOD research. A new prospective run is needed before claiming independent confirmation.", ""]
    return "\n".join(lines)


def write_run(out, summary, models, forecasts, selections, daily, *, input_path, source_manifest, protocol_path=PROTOCOL):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    summary = dict(summary)
    summary["provenance"] = {"input_sha256": sha256_file(input_path), "input_name": Path(input_path).name,
                             "source_manifest_sha256": sha256_file(source_manifest),
                             "protocol_sha256": sha256_file(protocol_path),
                             "code_sha256": {p.name: sha256_file(p) for p in (Path(__file__), Path(__file__).with_name("premove_core.py"))},
                             "python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}
    publish_bytes(out / "summary.json", (json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    publish_bytes(out / "models.json", (json.dumps(models, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    publish_bytes(out / "REPORT.md", render_report(summary).encode())
    forecast_columns = ["date", "ticker", "label_known", *TARGETS, "first_hit_date", "first_hit_step", "label_end_date",
                        "ret1", "ret5", "barrier_up_fraction", "baseline_volume", "baseline_volatility", "baseline_g2",
                        "summary_up", "summary_down", "summary_neither", "sequence_up", "sequence_down", "sequence_neither"]
    write_csv_gz_exclusive(out / "forecasts.csv.gz", forecasts[forecast_columns], index=False)
    write_csv_gz_exclusive(out / "shortlists.csv.gz", selections[[*forecast_columns, "population", "method", "rank", "rank_score", "episode_id"]], index=False)
    write_csv_gz_exclusive(out / "daily.csv.gz", daily, index=False)
    publish_bytes(out / "SOURCE.json", Path(source_manifest).read_bytes())
    entries = {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}
    publish_bytes(out / "MANIFEST.json", (json.dumps({"schema": "KOD-PREMOVE-RUN-v1", "files": entries}, sort_keys=True, indent=2) + "\n").encode())
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        protocol = json.loads(PROTOCOL.read_text())
        source = json.loads(args.source_manifest.read_text())
        expected = source.get("panel_sha256") or source.get("panel", {}).get("sha256")
        if not expected or sha256_file(args.input) != expected:
            raise ValueError("input must match the source manifest's panel hash")
        data = prepare_panel(pd.read_csv(args.input), market="CRYPTO")
        if data.date.max() >= pd.Timestamp("2024-01-01") or data.date.min() < pd.Timestamp("2020-01-01"):
            raise ValueError("benchmark input must stay within 2020-2023; existing later holdout remains unopened")
        print(f"Building examples: {len(data):,} bars, {data.ticker.nunique()} instruments", flush=True)
        examples = build_examples(data)
        print(f"Fitting and evaluating: {int(examples.frame.eligible.sum()):,} eligible decisions", flush=True)
        results = evaluate(examples, protocol)
        out = args.out or PROTOCOL.parent / "runs" / build_stamp()
        write_run(out, *results, input_path=args.input, source_manifest=args.source_manifest)
        print(out / "REPORT.md")
        print(render_report(results[0]))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

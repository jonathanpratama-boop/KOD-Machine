"""Causal, additive evaluation for the NEIGHBOURS/PRESSURE daily research arms.

Eligibility, feature ranks, predictions and selections never depend on the availability
of future outcomes. Labels are joined only for training after their maturity boundary,
or for scoring an already frozen selection. This is research, not an execution engine.
Original experiment runners and published results are deliberately left untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "CAUSAL-DAILY-RESEARCH-v1"
COIN_A = ("ret1", "ret3", "ret7", "ret20", "volr", "hi60", "vol20")
DAY_A = ("btc7", "breadth")
PEER_FEATURES = ("p_ret1", "p_ret3", "p_ret7", "p_part", "rel7")
STATION_FEATURES = tuple(f"st{s}_r{h}" for s in range(1, 6) for h in (1, 3))
PRESSURE_FEATURES = ("tb1", "tb5", "tbz")


@dataclass(frozen=True)
class ModelSpec:
    name: str
    coin_features: tuple[str, ...]
    day_features: tuple[str, ...] = DAY_A
    station_features: tuple[str, ...] = ()


NEIGHBOUR_MODELS = (
    ModelSpec("A", COIN_A),
    ModelSpec("B", COIN_A + PEER_FEATURES),
    ModelSpec("C", COIN_A + PEER_FEATURES, DAY_A, STATION_FEATURES),
)
PRESSURE_MODELS = (ModelSpec("A", COIN_A), ModelSpec("P", COIN_A + PRESSURE_FEATURES))


def _frame(rows: pd.DataFrame) -> pd.DataFrame:
    if not {"date", "ticker"}.issubset(rows.columns):
        raise ValueError("date and ticker are required")
    d = rows.copy()
    d["date"] = pd.to_datetime(d.date, utc=True, errors="raise").dt.tz_localize(None)
    if d.date.isna().any() or (d.date != d.date.dt.normalize()).any():
        raise ValueError("date must be a complete UTC calendar-day key")
    if d.ticker.isna().any() or not d.ticker.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("ticker must be a nonempty string")
    if d.duplicated(["date", "ticker"]).any():
        raise ValueError("duplicate date/ticker")
    return d.sort_values(["date", "ticker"], kind="stable").reset_index(drop=True)


def _numbers(series: pd.Series, name: str) -> np.ndarray:
    a = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
    if np.isinf(a).any():
        raise ValueError(f"infinite {name}")
    return a


def prepare_features(rows: pd.DataFrame, models=NEIGHBOUR_MODELS) -> pd.DataFrame:
    """Freeze as-of membership and ranks without consulting a forward-return column.

    `peers_ok` is the original shared as-of model eligibility rule. Missing feature
    values retain the original protocol's neutral rank, with missingness retained
    separately. This does not turn a missing observation into a measured zero.
    """
    d = _frame(rows)
    if "peers_ok" not in d:
        raise ValueError("as-of peers_ok eligibility is required")
    if not d.peers_ok.map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("peers_ok must contain booleans, not missing or inferred labels")
    d = d.loc[d.peers_ok].copy().reset_index(drop=True)
    if d.empty:
        raise ValueError("no as-of eligible rows")
    cols = sorted({c for m in models for c in m.coin_features})
    for c in sorted({c for m in models for c in (*m.coin_features, *m.day_features, *m.station_features)}):
        if c not in d:
            raise ValueError(f"missing feature {c}")
        d[c] = _numbers(d[c], c)
    for c in cols:
        d[c + "_missing"] = d[c].isna()
        d[c + "_rk"] = (d.groupby("date")[c].rank(pct=True) - 0.5).fillna(0.0)
    if any(m.station_features for m in models):
        if "station" not in d or not d.station.isin(range(1, 6)).all():
            raise ValueError("station must be in 1..5")
    return d


def matured_training_mask(d: pd.DataFrame, before, horizon_days=5, label="fwd3") -> np.ndarray:
    """Labels must have finished strictly before the year's refit, not on it."""
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or horizon_days < 3:
        raise ValueError("horizon_days must conservatively cover the three-day target")
    cutoff = pd.Timestamp(before)
    if cutoff.tzinfo is not None:
        cutoff = cutoff.tz_convert("UTC").tz_localize(None)
    if label not in d:
        raise ValueError(f"missing training label {label}")
    labels = _numbers(d[label], label)
    return ((d.date + pd.Timedelta(days=horizon_days) < cutoff) & np.isfinite(labels)).to_numpy()


def _standardized(d, cols, train):
    if not cols:
        return np.empty((len(d), 0))
    x = d[list(cols)]
    mu = x.loc[train].mean().fillna(0.0)
    sd = x.loc[train].std().replace(0, 1).fillna(1.0)
    return ((x - mu) / sd).fillna(0.0).to_numpy(float)


def _design(d, spec, train):
    blocks = [d[[c + "_rk" for c in spec.coin_features]].to_numpy(float)]
    blocks.append(_standardized(d, spec.day_features, train))
    if spec.station_features:
        z = _standardized(d, spec.station_features, train)
        blocks.extend(z * (d.station.to_numpy() == s)[:, None] for s in range(1, 6))
    x = np.column_stack([np.ones(len(d)), *blocks])
    if not np.isfinite(x).all():
        raise ValueError("nonfinite design matrix")
    return x


def freeze_predictions(rows, models=NEIGHBOUR_MODELS, years=range(2021, 2027), alpha=10.0):
    """Fit past matured labels, then return an outcome-free prediction table.

    Cross-sectional target centering uses the known matured training labels only.
    Missing target rows may be omitted from a fit, never from signal-day ranks or picks.
    The conservative five-day refit embargo is the original ADDENDUM_1 rule.
    """
    if isinstance(alpha, bool) or not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be finite and positive")
    years = tuple(sorted(set(years)))
    names = [m.name for m in models]
    if not names or len(names) != len(set(names)):
        raise ValueError("model names must be nonempty and unique")
    d = prepare_features(rows, models)
    preds = pd.DataFrame({"date": d.date, "ticker": d.ticker})
    for c in ("station", "ret7"):
        if c in d:
            preds[c] = d[c]
    for m in models:
        preds["p" + m.name] = np.nan
    audit = []
    for year in years:
        cutoff = pd.Timestamp(year=year, month=1, day=1)
        train = matured_training_mask(d, cutoff)
        test = (d.date.dt.year == year).to_numpy()
        if not test.any():
            continue
        if train.sum() < 2:
            raise ValueError(f"insufficient matured training rows before {year}")
        t = d.loc[train, ["date", "fwd3"]].copy()
        group = t.groupby("date").fwd3
        mean = group.transform("mean")
        y = (t.fwd3 - mean).clip(group.transform(lambda s: s.quantile(.01)) - mean,
                                 group.transform(lambda s: s.quantile(.99)) - mean).to_numpy(float)
        if not np.isfinite(y).all():
            raise ValueError("nonfinite training target")
        for spec in models:
            x = _design(d, spec, train)
            regularizer = alpha * np.eye(x.shape[1])
            regularizer[0, 0] = 0.0
            beta = np.linalg.solve(x[train].T @ x[train] + regularizer, x[train].T @ y)
            prediction = x[test] @ beta
            if not np.isfinite(prediction).all():
                raise ValueError("nonfinite prediction")
            preds.loc[test, "p" + spec.name] = prediction
        before = d.date + pd.Timedelta(days=5) < cutoff
        audit.append({"fit_year": year, "train_rows_known": int(train.sum()),
                      "train_rows_unknown": int((before & d.fwd3.isna()).sum()),
                      "last_training_label_maturity": (d.loc[train, "date"].max() + pd.Timedelta(days=5)).isoformat(),
                      "refit_at": cutoff.isoformat(), "prediction_rows": int(test.sum())})
    out = preds.loc[preds.date.dt.year.isin(list(years))].reset_index(drop=True)
    if out.empty or not np.isfinite(out[["p" + n for n in names]].to_numpy(float)).all():
        raise ValueError("empty or nonfinite prediction output")
    return out, audit


def select_picks(predictions, model_names, top_k=5, every=3, seed=20261103):
    """Select before label join; an unknown future can win a slot and is not replaced."""
    p = _frame(predictions)
    if any(c.startswith("fwd") for c in p.columns):
        raise ValueError("selection accepts an outcome-free prediction table")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in (top_k, every)):
        raise ValueError("positive selection parameters required")
    score_cols = ["p" + m for m in model_names]
    if not np.isfinite(p[score_cols].to_numpy(float)).all():
        raise ValueError("nonfinite selection score")
    rng = np.random.default_rng(seed)
    picks = []
    for date in sorted(p.date.unique())[::every]:
        x = p[p.date == date]
        if len(x) < 10:
            continue
        chosen = {m: x.sort_values(["p" + m, "ticker"], ascending=[False, True], kind="stable").head(top_k)
                  for m in model_names}
        chosen["random5"] = x.iloc[rng.choice(len(x), min(top_k, len(x)), replace=False)]
        chosen["all"] = x
        if {"station", "ret7"}.issubset(x.columns):
            strongest = x.groupby("station").ret7.median().sort_values(ascending=False, kind="stable").index[0]
            chosen["strong_group"] = x[x.station == strongest].sort_values(["ret7", "ticker"], ascending=[False, True], kind="stable").head(top_k)
        for method, frame in chosen.items():
            for ticker in frame.ticker:
                picks.append({"date": date, "ticker": ticker, "method": method, "weight": 1.0 / len(frame)})
    return pd.DataFrame(picks, columns=["date", "ticker", "method", "weight"])


def _nullable_mean(x):
    values = np.asarray(x, dtype=float)
    known = values[np.isfinite(values)]
    return float(known.mean()) if len(known) else None


def score_picks(picks, outcomes, round_trip_costs=(0.004, 0.02)):
    """No unknown result is filled with zero or silently removed from denominators."""
    if not all(np.isfinite(c) and 0 <= c < 1 for c in round_trip_costs):
        raise ValueError("costs must be finite round-trip fractions")
    o = _frame(outcomes)
    if "fwd3" not in o:
        raise ValueError("fwd3 is required for scoring")
    o["fwd3"] = _numbers(o.fwd3, "fwd3")
    s = picks.merge(o[["date", "ticker", "fwd3"]], on=["date", "ticker"], how="left", validate="many_to_one")
    s["outcome_state"] = np.where(s.fwd3.notna(), "KNOWN", "UNKNOWN")
    report = {}
    for method, g in s.groupby("method", sort=True):
        missing = int(g.fwd3.isna().sum())
        mean = _nullable_mean(g.fwd3)
        report[method] = {"selected_picks": len(g), "known_picks": len(g) - missing,
                          "unknown_picks": missing, "censored_picks": 0,
                          "rebalances": int(g.date.nunique()),
                          "status": "INCOMPLETE" if missing else "COMPLETE",
                          "metric": "arithmetic mean per observed pick; not compounded portfolio return",
                          "gross_observed_mean": mean,
                          "net_observed_means": {str(c): None if mean is None else mean - c for c in round_trip_costs},
                          "full_selection_mean": None if missing else mean,
                          "by_year": {str(year): {"selected": len(y), "known": int(y.fwd3.notna().sum()),
                                                  "unknown": int(y.fwd3.isna().sum()), "gross_observed_mean": _nullable_mean(y.fwd3)}
                                      for year, y in g.groupby(g.date.dt.year)}}
    return report, s


def information_report(predictions, outcomes, model_names):
    """Descriptive IC on observed outcomes; its changing denominator is explicit."""
    o = _frame(outcomes)
    cols = [f"fwd{h}" for h in (1, 3, 5)]
    for col in cols:
        o[col] = _numbers(o[col], col)
    p = predictions.merge(o[["date", "ticker", *cols]], on=["date", "ticker"], how="left", validate="one_to_one")
    result = {}
    daily = []
    for horizon in cols:
        scores = {m: [] for m in model_names}
        known_days = 0
        for date, g in p.groupby("date"):
            k = g[g[horizon].notna()]
            record = {"date": date.isoformat(), "horizon": horizon, "eligible_rows": len(g), "known_rows": len(k)}
            has_ic = len(k) >= 3 and k[horizon].nunique() > 1
            known_days += int(has_ic)
            for m in model_names:
                value = k["p" + m].rank().corr(k[horizon].rank()) if has_ic and k["p" + m].nunique() > 1 else np.nan
                record[m] = None if not np.isfinite(value) else float(value)
                scores[m].append(value)
            daily.append(record)
        result[horizon] = {"eligible_rows": len(p), "known_rows": int(p[horizon].notna().sum()),
                           "unknown_rows": int(p[horizon].isna().sum()), "days_with_nonconstant_target": known_days,
                           "mean_daily_rank_correlation": {m: _nullable_mean(v) for m, v in scores.items()}}
    return result, daily


def paired_information_differences(daily, model_names, block_days=20, draws=5000, seed=20261103):
    """Calendar-block bootstrap keeps missing IC days in the original time positions."""
    rng = np.random.default_rng(seed)
    table = pd.DataFrame(daily)
    result = {}
    for horizon, h in table.groupby("horizon"):
        h = h.sort_values("date")
        for prior, current in zip(model_names, model_names[1:]):
            v = (pd.to_numeric(h[current]) - pd.to_numeric(h[prior])).to_numpy(float)
            known = np.isfinite(v)
            record = {"mean": _nullable_mean(v), "known_days": int(known.sum()),
                      "unknown_days": int((~known).sum()), "lo95": None, "hi95": None}
            if len(v) >= block_days and known.any():
                samples = []
                nblocks = int(np.ceil(len(v) / block_days))
                for _ in range(draws):
                    starts = rng.integers(0, len(v) - block_days + 1, nblocks)
                    indices = np.concatenate([np.arange(i, i + block_days) for i in starts])[:len(v)]
                    value = _nullable_mean(v[indices])
                    if value is not None:
                        samples.append(value)
                if samples:
                    record["lo95"], record["hi95"] = map(float, np.percentile(samples, [2.5, 97.5]))
            result[f"{horizon}_{current}-{prior}"] = record
    return result


def add_pressure_features(rows, taker):
    """Calendar-day rolling windows; absent archive days stay absent, not compressed."""
    d = _frame(rows)
    t = _frame(taker)
    pieces = []
    for ticker, g in t.groupby("ticker"):
        x = g.set_index("date")[["quote_vol", "taker_buy_quote"]].copy()
        for c in x:
            x[c] = _numbers(x[c], c)
        if (x.quote_vol.dropna() < 0).any() or (x.taker_buy_quote.dropna() < 0).any() or (x.taker_buy_quote > x.quote_vol).any():
            raise ValueError("invalid taker volumes")
        x = x.reindex(pd.date_range(x.index.min(), x.index.max(), freq="D"))
        quote = x.quote_vol.where(x.quote_vol > 0)
        x["tb1"] = x.taker_buy_quote / quote - 0.5
        x["tb5"] = x.taker_buy_quote.rolling(5, min_periods=4).sum() / quote.rolling(5, min_periods=4).sum()
        x["tbz"] = (2 * x.taker_buy_quote - x.quote_vol).rolling(3, min_periods=3).sum() / quote.rolling(20, min_periods=15).median()
        x["ticker"] = ticker
        x.index.name = "date"
        pieces.append(x.reset_index()[["date", "ticker", *PRESSURE_FEATURES]])
    if not pieces:
        raise ValueError("no taker observations")
    return d.merge(pd.concat(pieces, ignore_index=True), on=["date", "ticker"], how="left", validate="one_to_one")


def write_corrected_run(rows, output_dir, models=NEIGHBOUR_MODELS, source_paths=(), years=range(2021, 2027)):
    """Write a new immutable run directory; never overwrite an original experiment."""
    destination = Path(output_dir)
    if destination.exists():
        raise FileExistsError("corrected output directory already exists")
    predictions, training = freeze_predictions(rows, models, years)
    names = [m.name for m in models]
    picks = select_picks(predictions, names)
    destination.mkdir(parents=True, exist_ok=False)
    # These artifacts are written before attaching any future outcome to selections.
    predictions.to_csv(destination / "predictions.csv", index=False)
    picks.to_csv(destination / "selections.csv", index=False)
    decisions, scored = score_picks(picks, rows)
    information, daily_ic = information_report(predictions, rows, names)
    differences = paired_information_differences(daily_ic, names)
    scored.to_csv(destination / "scored_selections.csv", index=False)
    result = {"evaluator_version": VERSION, "evidence_level": "RETROSPECTIVE_CORRECTED_RESEARCH",
              "promotion": "DISABLED_PENDING_REVIEW", "rows_test": len(predictions),
              "days_test": int(predictions.date.nunique()), "training": training,
              "parameters": {"alpha": 10.0, "primary_horizon_days": 3,
                             "diagnostic_horizons_days": [1, 5], "maturity_embargo_days": 5,
                             "top_k": 5, "rebalance_every_signal_days": 3,
                             "assumed_round_trip_costs": [0.004, 0.02],
                             "models": [{"name": m.name, "coin_features": list(m.coin_features),
                                         "day_features": list(m.day_features), "station_features": list(m.station_features)} for m in models]},
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "decisions": decisions, "information": information, "ic_differences": differences, "daily_ic": daily_ic,
              "limitations": ["Previously inspected history; no fresh holdout claim",
                              "Mean-per-pick statistics are not shared-account or executable profits",
                              "Missing future outcomes remain unknown; observed-only means may be biased"],
              "inputs": [{"path": str(p), "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in source_paths]}
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    (destination / "RESULT.json").write_text(payload)
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir()) if p.is_file()}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return result

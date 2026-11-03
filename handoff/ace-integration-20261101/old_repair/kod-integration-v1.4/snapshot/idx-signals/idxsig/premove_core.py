"""Causal daily pre-move examples and a small train-only sequence ranker.

Targets use the next session's open and future closes. Inputs use decision-close
information only. Extreme returns are preserved; no future-informed cleaning or
redenomination inference is performed. Forecast scores are normalized one-v-rest
logistic outputs, not a claim of calibrated market probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

TARGETS = ("up_first", "down_first", "neither")
SUMMARY_FEATURES = (
    "ret1",
    "ret5",
    "ret20",
    "rel1",
    "vol20",
    "range_ratio",
    "close_position",
    "drawdown60",
    "volume_ratio",
    "volume_creep",
    "volatility_ratio",
    "up_fraction5",
    "log_value20",
    "age_log",
)
REQUIRED = ("date", "ticker", "open", "high", "low", "close", "volume", "value")


@dataclass
class Examples:
    frame: pd.DataFrame
    feature_columns: tuple[str, ...]
    sequence_columns: tuple[str, ...]


def prepare_panel(df: pd.DataFrame, market="CRYPTO") -> pd.DataFrame:
    if market not in ("CRYPTO", "US"):
        raise ValueError("market must be CRYPTO or US")
    if not isinstance(df, pd.DataFrame) or any(c not in df for c in REQUIRED):
        raise ValueError("panel requires date,ticker,open,high,low,close,volume,value")
    frame = df.loc[:, REQUIRED].copy()
    if frame.empty:
        raise ValueError("empty panel")
    if "complete_bar" in df:
        if not df["complete_bar"].map(lambda x: isinstance(x, (bool, np.bool_))).all():
            raise ValueError("complete_bar must contain boolean values without missing values")
        frame["complete_bar"] = df["complete_bar"].astype(bool)
    else:
        frame["complete_bar"] = True
    frame["date"] = pd.to_datetime(frame["date"], utc=True, errors="raise").dt.tz_localize(None)
    if frame["date"].isna().any() or (frame["date"] != frame["date"].dt.normalize()).any():
        raise ValueError("panel dates must be daily session dates")
    if (
        frame["ticker"].isna().any()
        or not frame["ticker"].map(lambda x: isinstance(x, str) and bool(x.strip())).all()
    ):
        raise ValueError("invalid ticker")
    if frame.duplicated(["date", "ticker"]).any():
        raise ValueError("duplicate ticker/session")
    for column in REQUIRED[2:]:
        if frame[column].map(lambda x: isinstance(x, (bool, np.bool_))).any():
            raise ValueError("boolean market value")
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
        values = frame[column].to_numpy()
        if np.isinf(values).any() or (values[np.isfinite(values)] < 0).any():
            raise ValueError("negative or infinite market value")
    known = frame[["open", "high", "low", "close"]].notna().all(axis=1)
    if (
        (frame.loc[known, "low"] > frame.loc[known, ["open", "close"]].min(axis=1))
        | (frame.loc[known, "high"] < frame.loc[known, ["open", "close"]].max(axis=1))
    ).any():
        raise ValueError("inconsistent OHLC")
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    frame.attrs["market"] = market
    return frame


def build_examples(
    df: pd.DataFrame,
    horizon=5,
    lookback=20,
    threshold_floor=0.10,
    vol_multiplier=3.0,
    min_value20=100_000.0,
) -> Examples:
    for name, value in (("horizon", horizon), ("lookback", lookback)):
        if type(value) is not int or not 1 <= value <= 60:
            raise ValueError(f"{name} must be an integer from 1 to 60")
    for name, value, positive in (
        ("threshold_floor", threshold_floor, True),
        ("vol_multiplier", vol_multiplier, True),
        ("min_value20", min_value20, False),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            or (positive and value == 0)
        ):
            raise ValueError(f"invalid {name}")
    market = df.attrs.get("market", "CRYPTO")
    panel = prepare_panel(df, market)
    calendar = (
        pd.date_range(panel.date.min(), panel.date.max(), freq="D")
        if market == "CRYPTO"
        else pd.DatetimeIndex(sorted(panel.date.unique()))
    )
    seq_cols = tuple(
        f"seq_{kind}_{lag:02d}" for kind in ("return", "range", "volume") for lag in range(lookback)
    )
    frames = []
    for ticker, source in panel.groupby("ticker", sort=True):
        source = source.set_index("date")
        bars = source.reindex(calendar)
        present = pd.Series(calendar.isin(source.index), index=calendar)
        complete = bars["complete_bar"].eq(True)
        c, o, h, lo, v, q = (bars[k] for k in ("close", "open", "high", "low", "volume", "value"))
        valid = (
            present
            & complete
            & (bars[["open", "high", "low", "close", "volume"]] > 0).all(axis=1)
            & q.notna()
        )
        prev = c.shift(1)
        lr = np.log(c.where(c > 0) / prev.where(prev > 0))
        vol20 = lr.rolling(20, min_periods=20).std(ddof=1)
        vol60 = lr.rolling(60, min_periods=45).std(ddof=1)
        volume_median = v.shift(1).rolling(20, min_periods=20).median()
        volume_ratio = v / volume_median.where(volume_median > 0)
        ranges = (h - lo) / prev.where(prev > 0)
        range_med = ranges.shift(1).rolling(20, min_periods=20).median()
        value20 = q.shift(1).rolling(20, min_periods=20).median()
        f = pd.DataFrame(index=calendar)
        f["ticker"] = ticker
        f["complete_bar"] = complete
        f["ret1"] = c / prev - 1
        f["ret5"] = c / c.shift(5) - 1
        f["ret20"] = c / c.shift(20) - 1
        f["vol20"] = vol20
        f["range_ratio"] = ranges / range_med.where(range_med > 0)
        spread = h - lo
        f["close_position"] = ((c - lo) / spread.where(spread > 0)).where(spread != 0, 0.5)
        f["drawdown60"] = c / c.rolling(60, min_periods=60).max() - 1
        f["volume_ratio"] = volume_ratio
        oldvol = v.shift(5).rolling(20, min_periods=20).median()
        f["volume_creep"] = v.rolling(5, min_periods=5).median() / oldvol.where(oldvol > 0)
        f["volatility_ratio"] = lr.rolling(10, min_periods=10).std(ddof=1) / vol60.where(vol60 > 0)
        # Zero volatility is a known constant path, not missing history.
        f.loc[vol60 == 0, "volatility_ratio"] = 0.0
        f.loc[range_med == 0, "range_ratio"] = 0.0
        f["up_fraction5"] = (
            (lr > 0).astype(float).where(lr.notna()).rolling(5, min_periods=5).mean()
        )
        f["median_value20"] = value20
        f["log_value20"] = np.log1p(value20)
        f["age_log"] = np.log1p(present.cumsum())
        f["baseline_g2"] = (f.ret1 >= 0.30).astype(float)
        f["baseline_volume"] = volume_ratio
        f["baseline_volatility"] = vol20
        streams = {"return": lr, "range": ranges, "volume": np.log1p(volume_ratio)}
        for kind, series in streams.items():
            for lag in range(lookback):
                f[f"seq_{kind}_{lag:02d}"] = series.shift(lag)
        known_history = valid.rolling(60, min_periods=60).sum() == 60
        f["eligible"] = known_history & (value20 >= min_value20)
        f["entry_open"] = o.shift(-1)
        f["entry_date"] = pd.Series(calendar, index=calendar).shift(-1)
        f["label_end_date"] = pd.Series(calendar, index=calendar).shift(-horizon)
        b = np.maximum(
            math.log1p(threshold_floor), vol_multiplier * vol20.to_numpy() * math.sqrt(horizon)
        )
        f["barrier_log"] = b
        f["barrier_up_fraction"] = np.expm1(np.minimum(b, 700))
        future = np.column_stack([c.shift(-j).to_numpy() for j in range(1, horizon + 1)])
        future_valid = np.column_stack(
            [valid.shift(-j, fill_value=False).to_numpy() for j in range(1, horizon + 1)]
        )
        entry = f.entry_open.to_numpy()
        future_log = np.log(future / entry[:, None])
        up = future_log >= b[:, None]
        down = future_log <= -b[:, None]
        up_step = np.where(up.any(axis=1), up.argmax(axis=1) + 1, horizon + 1)
        down_step = np.where(down.any(axis=1), down.argmax(axis=1) + 1, horizon + 1)
        known = future_valid.all(axis=1) & np.isfinite(entry) & (entry > 0) & np.isfinite(b)
        f["label_known"] = known
        f["up_first"] = np.where(known, up_step < down_step, np.nan)
        f["down_first"] = np.where(known, down_step < up_step, np.nan)
        f["neither"] = np.where(
            known, (up_step == horizon + 1) & (down_step == horizon + 1), np.nan
        )
        steps = np.minimum(up_step, down_step)
        f["first_hit_step"] = np.where(known & (steps <= horizon), steps, np.nan)
        dates = np.full(len(f), np.datetime64("NaT"), dtype="datetime64[ns]")
        for j in range(1, horizon + 1):
            hits = known & (steps == j)
            shifted = pd.Series(calendar, index=calendar).shift(-j).to_numpy()
            dates[hits] = shifted[hits]
        f["first_hit_date"] = dates
        # Keep ineligible rows for diagnostics, but never synthesize listed rows.
        frames.append(f.loc[present].rename_axis("date").reset_index())
    frame = (
        pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)
    )
    market_ret = frame.groupby("date")["ret1"].transform("median")
    frame["rel1"] = frame.ret1 - market_ret
    cols = list(SUMMARY_FEATURES) + list(seq_cols)
    frame["eligible"] &= np.isfinite(frame[cols]).all(axis=1)
    frame.attrs.update(
        market=market,
        horizon=horizon,
        target="next-open to future-close first passage; symmetric log barriers",
    )
    return Examples(frame, SUMMARY_FEATURES, seq_cols)


def _matrix(frame, columns):
    try:
        result = frame.loc[:, columns].to_numpy(dtype=float)
    except (KeyError, TypeError, ValueError):
        raise ValueError("missing or invalid model feature") from None
    if not np.isfinite(result).all():
        raise ValueError("non-finite model features")
    return result


def _scale_fit(x):
    with np.errstate(over="ignore", invalid="ignore"):
        mean = x.mean(axis=0)
        scale = x.std(axis=0)
    if not np.isfinite(mean).all() or not np.isfinite(scale).all():
        raise ValueError("feature scaling overflow")
    scale = np.where(scale > 1e-12, scale, 1.0)
    return mean, scale


@dataclass
class FittedModel:
    feature_columns: tuple[str, ...]
    sequence_columns: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    sequence_mean: np.ndarray
    sequence_scale: np.ndarray
    components: np.ndarray
    coefficients: np.ndarray
    constants: np.ndarray
    iterations: tuple[int, ...]
    converged: tuple[bool, ...]
    objectives: tuple[float, ...]

    def _design(self, frame):
        x = (_matrix(frame, self.feature_columns) - self.mean) / self.scale
        if self.sequence_columns:
            seq = (_matrix(frame, self.sequence_columns) - self.sequence_mean) / self.sequence_scale
            x = np.column_stack([x, seq @ self.components.T])
        return np.column_stack([np.ones(len(frame)), x])

    def predict(self, frame):
        x = self._design(frame)
        values = 1 / (1 + np.exp(-np.clip(x @ self.coefficients.T, -30, 30)))
        for k, value in enumerate(self.constants):
            if np.isfinite(value):
                values[:, k] = value
        return values / values.sum(axis=1, keepdims=True)

    def record(self):
        return {
            "recipe": "PCA-OVR-ridge-v1",
            "targets": list(TARGETS),
            "feature_columns": list(self.feature_columns),
            "sequence_columns": list(self.sequence_columns),
            **{
                name: getattr(self, name).tolist()
                for name in (
                    "mean",
                    "scale",
                    "sequence_mean",
                    "sequence_scale",
                    "components",
                    "coefficients",
                )
            },
            "constants": [float(v) if np.isfinite(v) else None for v in self.constants],
            "iterations": list(self.iterations),
            "converged": list(self.converged),
            "objectives": list(self.objectives),
        }


def fit_model(train, feature_columns, sequence_columns=(), pca_components=8, ridge=1.0):
    """Fit scaling, optional PCA and OVR logistic exclusively on supplied train rows."""
    if train.empty:
        raise ValueError("empty training rows")
    if type(pca_components) is not int or pca_components < 1:
        raise ValueError("pca_components must be a positive integer")
    if (
        isinstance(ridge, bool)
        or not isinstance(ridge, (int, float))
        or not math.isfinite(ridge)
        or ridge <= 0
    ):
        raise ValueError("ridge must be finite and positive")
    feature_columns, sequence_columns = tuple(feature_columns), tuple(sequence_columns)
    if not feature_columns or len(set(feature_columns + sequence_columns)) != len(
        feature_columns + sequence_columns
    ):
        raise ValueError("feature columns must be nonempty and distinct")
    x = _matrix(train, feature_columns)
    mean, scale = _scale_fit(x)
    x = (x - mean) / scale
    sm, ss, components = np.empty(0), np.empty(0), np.empty((0, 0))
    if sequence_columns:
        seq = _matrix(train, sequence_columns)
        sm, ss = _scale_fit(seq)
        seq = (seq - sm) / ss
        # Feature covariance avoids allocating a full tall SVD for a large panel.
        eigenvalues, eigenvectors = np.linalg.eigh(seq.T @ seq / len(seq))
        count = min(pca_components, len(sequence_columns), max(1, len(train) - 1))
        components = eigenvectors[:, np.argsort(eigenvalues)[::-1][:count]].T
        # Canonical signs make persisted PCA records deterministic.
        for row in components:
            if row[np.argmax(np.abs(row))] < 0:
                row *= -1
        x = np.column_stack([x, seq @ components.T])
    x = np.column_stack([np.ones(len(train)), x])
    y = _matrix(train, TARGETS)
    if not np.isin(y, [0, 1]).all() or not np.all(y.sum(axis=1) == 1):
        raise ValueError("training targets must be known one-hot outcomes")
    coefficients, constants, iterations, converged, objectives = [], [], [], [], []
    penalty = np.eye(x.shape[1]) * ridge
    penalty[0, 0] = 0
    for k in range(3):
        target = y[:, k]
        base = float(target.mean())
        beta = np.zeros(x.shape[1])
        if base in (0.0, 1.0):
            coefficients.append(beta)
            constants.append(base)
            iterations.append(0)
            converged.append(True)
            objectives.append(0.0)
            continue
        beta[0] = math.log(base / (1 - base))

        def objective(candidate):
            z = x @ candidate
            return float(
                np.sum(np.logaddexp(0, z) - target * z) + 0.5 * candidate @ penalty @ candidate
            )

        initial_objective = objective(beta)
        objective_value = initial_objective
        for iteration in range(1, 51):
            probability = 1 / (1 + np.exp(-np.clip(x @ beta, -30, 30)))
            weight = np.maximum(probability * (1 - probability), 1e-10)
            gradient = x.T @ (probability - target) + penalty @ beta
            hessian = x.T @ (weight[:, None] * x) + penalty
            step = np.linalg.solve(hessian, gradient)
            length = np.linalg.norm(step)
            if length > 10:
                step *= 10 / length
            for _ in range(25):
                candidate = beta - step
                candidate_objective = objective(candidate)
                if (
                    math.isfinite(candidate_objective)
                    and candidate_objective <= objective_value + 1e-10
                ):
                    break
                step *= 0.5
            else:
                raise ValueError("logistic objective did not decrease")
            beta = candidate
            objective_value = candidate_objective
            if not np.isfinite(beta).all():
                raise ValueError("logistic fit became non-finite")
            if np.max(np.abs(step)) < 1e-7:
                break
        coefficients.append(beta)
        constants.append(np.nan)
        iterations.append(iteration)
        probability = 1 / (1 + np.exp(-np.clip(x @ beta, -30, 30)))
        final_gradient = x.T @ (probability - target) + penalty @ beta
        converged.append(bool(np.max(np.abs(final_gradient)) / len(train) < 1e-6))
        objectives.append(objective_value)
        if not math.isfinite(objective_value) or objective_value > initial_objective + 1e-8:
            raise ValueError("logistic objective is invalid")
    return FittedModel(
        feature_columns,
        sequence_columns,
        mean,
        scale,
        sm,
        ss,
        components,
        np.array(coefficients),
        np.array(constants),
        tuple(iterations),
        tuple(converged),
        tuple(objectives),
    )

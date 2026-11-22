"""Prepare frozen Kronos pilot inputs and separately stored outcomes from public archives."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FEATURES = ["open", "high", "low", "close", "volume", "amount"]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_time(value):
    """Binance switched spot archive timestamps from ms to us on 2025-01-01."""
    n = int(value)
    return pd.to_datetime(n, unit="us" if abs(n) >= 10**14 else "ms", utc=True)


def causal_context(frame, trigger, decision, bars=168):
    trigger, decision = pd.Timestamp(trigger), pd.Timestamp(decision)
    expected = pd.date_range(end=trigger, periods=bars, freq="h")
    context = frame.loc[frame.index.isin(expected)].sort_index().copy()
    if len(context) != bars or not context.index.equals(expected):
        raise ValueError("missing_or_duplicate_context_hours")
    if not (context.close_time < decision).all():
        raise ValueError("context_contains_unclosed_candle")
    if not (context.index < decision).all():
        raise ValueError("context_contains_future_candle")
    values = context[FEATURES].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, :4] <= 0).any() or (values[:, 4:] < 0).any():
        raise ValueError("invalid_context_values")
    if (context.high < context[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("invalid_context_high")
    if (context.low > context[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("invalid_context_low")
    context.index.name = "timestamps"
    return context


def fetch_bytes(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(0.3 * (attempt + 1))


def download_archive(key, archive_dir):
    symbol, month = key
    filename = f"{symbol}-1h-{month}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{filename}"
    record = {"symbol": symbol, "month": month, "url": url}
    dest = archive_dir / filename
    checksum_dest = archive_dir / (filename + ".CHECKSUM")
    try:
        checksum_bytes = checksum_dest.read_bytes() if checksum_dest.exists() else fetch_bytes(url + ".CHECKSUM")
        expected = checksum_bytes.decode().split()[0].lower()
        raw = dest.read_bytes() if dest.exists() else fetch_bytes(url)
        actual = sha256(raw)
        if actual != expected:
            raise ValueError("archive_checksum_mismatch")
        if not dest.exists():
            dest.write_bytes(raw)
        if not checksum_dest.exists():
            checksum_dest.write_bytes(checksum_bytes)
        record.update(status="ok", sha256=actual, bytes=len(raw), path=str(dest))
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    return key, record


def read_archive(path):
    with zipfile.ZipFile(path) as zipped:
        members = [x for x in zipped.namelist() if x.endswith(".csv")]
        if len(members) != 1:
            raise ValueError("archive_requires_one_csv")
        raw = zipped.read(members[0])
    return parse_kline_csv(raw)


def parse_kline_csv(raw):
    frame = pd.read_csv(io.BytesIO(raw), header=None)
    if frame.shape[1] != 12:
        raise ValueError("unexpected_kline_column_count")
    frame.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "amount", "trades", "taker_base", "taker_quote", "ignore"]
    frame.index = pd.DatetimeIndex([archive_time(v) for v in frame.open_time], name="timestamps")
    frame["close_time"] = pd.DatetimeIndex([archive_time(v) for v in frame.close_time])
    for name in FEATURES:
        frame[name] = pd.to_numeric(frame[name], errors="raise")
    return frame[FEATURES + ["close_time"]]


def required_months(row):
    trigger = pd.Timestamp(row.trigger_hour)
    start = trigger - pd.Timedelta(hours=167)
    end = trigger + pd.Timedelta(hours=26)
    months = pd.period_range(start.tz_localize(None).to_period("M"), end.tz_localize(None).to_period("M"), freq="M")
    return [(row.sym, str(month)) for month in months]


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, allow_nan=False, sort_keys=True) + "\n" for row in rows))


def prepare(cohort_path, data_dir):
    data_dir = Path(data_dir).resolve()
    archive_dir, input_dir = data_dir / "archive", data_dir / "inputs"
    archive_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    cohort = pd.read_csv(cohort_path)
    keys = sorted({key for row in cohort.itertuples() for key in required_months(row)})
    archives = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(download_archive, key, archive_dir) for key in keys]
        for i, future in enumerate(as_completed(futures), 1):
            key, record = future.result()
            archives[key] = record
            if i % 20 == 0 or i == len(keys):
                print(f"archives {i}/{len(keys)}", flush=True)
    (data_dir / "archive_manifest.json").write_text(json.dumps([archives[k] for k in keys], indent=2) + "\n")
    frames, inputs, outcomes = {}, [], []
    for row in cohort.itertuples():
        trigger = pd.Timestamp(row.trigger_hour)
        decision = trigger + pd.Timedelta(hours=1)
        entry = decision + pd.Timedelta(hours=1)
        exit_time = entry + pd.Timedelta(hours=24)
        record = dict(event_id=row.event_id, symbol=row.sym, trigger_hour=trigger.isoformat(),
                      decision_time=decision.isoformat(), entry_time=entry.isoformat(), exit_time=exit_time.isoformat(),
                      input_path=None, input_sha256=None, last_observed_close=None, status="failed", error=None)
        outcome = dict(event_id=row.event_id, actual_gross_return=None, actual_forecast_target_return=None, status="failed", error=None)
        frame = None
        try:
            monthly_frames = []
            for key in required_months(row):
                a = archives[key]
                if a["status"] != "ok":
                    raise ValueError(f"missing_archive:{key}:{a['error']}")
                if key not in frames:
                    frames[key] = read_archive(a["path"])
                monthly_frames.append(frames[key])
            frame = pd.concat(monthly_frames).sort_index()
            if frame.index.duplicated().any():
                raise ValueError("duplicate_archive_timestamps")
            context = causal_context(frame, trigger, decision)
            dest = input_dir / (sha256(row.event_id.encode()) + ".csv")
            context.to_csv(dest, index=True)
            record.update(input_path=str(dest), input_sha256=sha256(dest.read_bytes()),
                          last_observed_close=float(context.iloc[-1]["close"]), status="ready")
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        try:
            if frame is None:
                raise ValueError("no_archive_frame")
            entry_open = float(frame.loc[entry, "open"])
            exit_open = float(frame.loc[exit_time, "open"])
            last_close = float(frame.loc[trigger, "close"])
            if not np.isfinite([entry_open, exit_open, last_close]).all() or min(entry_open, exit_open, last_close) <= 0:
                raise ValueError("invalid_outcome_price")
            outcome.update(actual_gross_return=exit_open / entry_open - 1,
                           actual_forecast_target_return=exit_open / last_close - 1, status="ok")
        except Exception as exc:
            outcome["error"] = f"{type(exc).__name__}: {exc}"
        inputs.append(record)
        outcomes.append(outcome)
    write_jsonl(data_dir / "input_manifest.jsonl", inputs)
    write_jsonl(data_dir / "outcomes.jsonl", outcomes)
    summary = {"events": len(inputs), "ready_inputs": sum(x["status"] == "ready" for x in inputs),
               "available_outcomes": sum(x["status"] == "ok" for x in outcomes),
               "archives": len(keys), "failed_archives": sum(x["status"] != "ok" for x in archives.values())}
    (data_dir / "preparation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, default=HERE / "cohort.csv")
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.cohort, args.data_dir), sort_keys=True))

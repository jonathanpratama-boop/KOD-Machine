"""Optional CoinGlass crypto context with raw evidence and explicit availability.

Vendor indicators and derivatives data are research inputs, not changes to a
frozen strategy. A historical API timestamp never substitutes for observation
time. Reading a saved snapshot performs no network requests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path

from .provenance import DATA, build_stamp, publish_bytes, sha256_bytes
from .sources.coinglass import CoinGlassClient, CoinGlassError, validate_request

SCHEMA = "KOD-COINGLASS-CONTEXT-v1"
DEFAULT_DATASETS = ("price", "open_interest", "funding", "liquidations", "long_short", "rsi", "macd")
INTERVAL_MS = {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
               "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000,
               "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000,
               "1d": 86_400_000, "1w": 604_800_000}
FIELDS = {"price": ("open", "high", "low", "close", "volume_usd"),
          "open_interest": ("open", "high", "low", "close"),
          "funding": ("open", "high", "low", "close"),
          "liquidations": ("long_liquidation_usd", "short_liquidation_usd"),
          "long_short": ("global_account_long_percent", "global_account_short_percent",
                         "global_account_long_short_ratio"),
          "rsi": ("rsi_value",), "macd": ("macd_value",), "ma": ("ma_value",),
          "ema": ("ema_value",), "boll": ("mb_value", "ub_value", "lb_value"),
          "atr": ("avg_true_range_value",)}
UNITS = {"price": "quote price; volume_usd is USD", "open_interest": "USD",
         "funding": "provider-native rate; scale not asserted", "liquidations": "USD",
         "long_short": "account percentages and ratio; not position notionals",
         "rsi": "0-100", "macd": "provider MACD value; not signal/histogram",
         "ma": "price", "ema": "price", "boll": "price", "atr": "price"}


def _moment(value=None):
    if value is None:
        return datetime.now(timezone.utc)
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("time must include a UTC offset, for example 2026-10-30T00:00:00Z")
    return dt.astimezone(timezone.utc)


def _stamp(value=None):
    return _moment(value).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _json(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()


def _number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric observation")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("observation is not numeric") from None
    if not math.isfinite(result):
        raise ValueError("non-finite observation")
    return result


def normalize_history(endpoint, data, params, observed_at):
    """Convert documented fields; retain nulls and reject ambiguous/malformed bars.

    `time` is conservatively treated as period start. time+interval must be no
    later than both retrieval and the requested cutoff. No missing bars are filled.
    """
    if endpoint not in FIELDS or not isinstance(data, list):
        raise ValueError("expected a supported history endpoint and a list of rows")
    step = INTERVAL_MS[params["interval"]]
    observed_ms = int(_moment(observed_at).timestamp() * 1000)
    rows = {}
    ignored = 0
    for source in data:
        if not isinstance(source, dict):
            raise ValueError("history row must be an object")
        for key in ("symbol", "exchange", "interval"):
            if key in source and source[key] != params[key]:
                raise ValueError(f"response {key} differs from requested {key}")
        t = source.get("time")
        # v4 documents milliseconds. Do not silently interpret seconds as ms.
        if type(t) is not int or not 946684800000 <= t < 4102444800000:
            raise ValueError("history time must be a millisecond timestamp between 2000 and 2100")
        if any(field not in source for field in FIELDS[endpoint]):
            raise ValueError(f"{endpoint} response is missing documented fields")
        if t < params.get("start_time", 0) or t > params.get("end_time", observed_ms) or t + step > observed_ms:
            ignored += 1
            continue
        values = {field: _number(source[field]) for field in FIELDS[endpoint]}
        present = {k: v for k, v in values.items() if v is not None}
        if endpoint != "funding" and endpoint != "macd" and any(v < 0 for v in present.values()):
            raise ValueError(f"negative {endpoint} observation")
        if endpoint in ("price", "open_interest", "funding"):
            o, h, lo, c = (values[k] for k in ("open", "high", "low", "close"))
            if all(v is not None for v in (o, h, lo, c)) and not lo <= min(o, c) <= max(o, c) <= h:
                raise ValueError("inconsistent OHLC observation")
            if endpoint == "price" and any(v is not None and v <= 0 for v in (o, h, lo, c)):
                raise ValueError("price must be positive")
        if endpoint == "rsi" and present.get("rsi_value", 0) > 100:
            raise ValueError("RSI outside 0-100")
        if endpoint == "long_short":
            lp, sp = values["global_account_long_percent"], values["global_account_short_percent"]
            if any(v is not None and v > 100 for v in (lp, sp)):
                raise ValueError("account percentage outside 0-100")
            if lp is not None and sp is not None and abs(lp + sp - 100) > 0.2:
                raise ValueError("account percentages do not sum to 100")
        row = {"time": t, "bar_end": t + step, **values}
        if t in rows and rows[t] != row:
            raise ValueError("conflicting duplicate history timestamps")
        rows[t] = row
    ordered = [rows[t] for t in sorted(rows)]
    gaps = sum(max(0, (b["time"] - a["time"]) // step - 1) for a, b in zip(ordered, ordered[1:]))
    units = "coin" if endpoint == "open_interest" and params.get("unit") == "coin" else UNITS[endpoint]
    return {"rows": ordered, "discarded_outside_window_or_unclosed": ignored,
            "missing_intervals_between_rows": gaps, "units": units}


def _parameters(symbol, exchange, interval, limit, datasets, end=None):
    if interval not in INTERVAL_MS:
        raise ValueError("unsupported interval")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer from 1 to 1000")
    datasets = tuple(datasets)
    if not datasets or len(set(datasets)) != len(datasets) or any(d not in FIELDS for d in datasets):
        raise ValueError("datasets must be distinct supported history endpoint names")
    cutoff = _moment(end)
    now = _moment()
    if cutoff > now:
        raise ValueError("end cannot be in the future")
    step = INTERVAL_MS[interval]
    # Bound on bar START, deliberately one whole period before the cutoff.
    end_ms = int(cutoff.timestamp() * 1000) - step
    start_ms = end_ms - limit * step + 1
    common = {"symbol": symbol, "exchange": exchange, "interval": interval, "limit": limit,
              "start_time": start_ms, "end_time": end_ms}
    requests = {}
    for name in datasets:
        params = dict(common)
        if name == "open_interest":
            params["unit"] = "usd"
        if name in ("rsi", "ma", "ema", "boll", "atr"):
            params["window"] = 14 if name in ("rsi", "atr") else 20
        if name in ("rsi", "ma", "ema", "boll", "macd"):
            params["series_type"] = "close"
        if name == "boll":
            params["mult"] = 2
        if name == "macd":
            params.update(fast_window=12, slow_window=26, signal_window=9)
        validate_request(name, params)
        requests[name] = params
    return {**common, "datasets": list(datasets), "cutoff": _stamp(cutoff)}, requests


def capture(client=None, *, symbol="BTCUSDT", exchange="Binance", interval="4h", limit=200,
            datasets=DEFAULT_DATASETS, end=None, root=DATA):
    """Fetch one bounded window; partial access is a recorded outcome, never zero.

    Each invocation publishes a new manifest last. Paid raw responses stay under
    data/raw (git ignored). This is not a full-history/pagination API.
    """
    settings, requests = _parameters(symbol, exchange, interval, limit, datasets, end)
    client = CoinGlassClient() if client is None else client
    root = Path(root).resolve()
    snapshot_id = build_stamp()
    directory = root / "raw" / "coinglass" / snapshot_id
    files, results = [], {}
    started = _stamp()
    for name, params in requests.items():
        try:
            response = client.request(name, **params)
        except CoinGlassError as exc:
            results[name] = {"status": "unavailable", "reason": exc.kind, "message": str(exc), "params": params}
            continue
        # Network metadata has a small allowlisted schema; headers are never saved.
        metadata = {k: response.metadata[k] for k in
                    ("endpoint", "path", "params", "requested_at", "observed_at", "http_status", "attempts", "provider_code", "sha256")}
        if metadata["params"] != params or metadata["endpoint"] != name:
            raise ValueError("client response identity mismatch")
        if sha256_bytes(response.raw) != metadata["sha256"]:
            raise ValueError("client response bytes do not match metadata")
        envelope = json.loads(response.raw)
        if str(envelope.get("code")) != "0" or envelope.get("data") != response.data:
            raise ValueError("client data does not match its raw response")
        raw_path = directory / f"{name}.json"
        publish_bytes(raw_path, response.raw)
        files.append({"path": raw_path.relative_to(root.parent).as_posix(), "sha256": metadata["sha256"], "kind": "raw", "endpoint": name})
        try:
            normalized = normalize_history(name, response.data, params, metadata["observed_at"])
        except (ValueError, TypeError, KeyError) as exc:
            results[name] = {"status": "invalid", "reason": "schema", "message": str(exc), "metadata": metadata}
            continue
        results[name] = {"status": "ok" if normalized["rows"] else "empty", "metadata": metadata, **normalized}
    document = {"schema": SCHEMA, "snapshot_id": snapshot_id, "settings": settings,
                "requested_at": started, "observed_at": _stamp(), "datasets": results}
    normalized_path = directory / "context.json"
    payload = _json(document)
    publish_bytes(normalized_path, payload)
    files.append({"path": normalized_path.relative_to(root.parent).as_posix(), "sha256": sha256_bytes(payload), "kind": "normalized"})
    manifest = root / "manifests" / f"coinglass-{snapshot_id}.jsonl"
    header = {"manifest": manifest.name, "schema": SCHEMA, "provider": "CoinGlass v4", "n_files": len(files),
              "observed_at": document["observed_at"], "snapshot_id": snapshot_id, "settings": settings,
              "path_base": "parent of data directory", "availability": "actual retrieval time; no backdated availability"}
    content = "\n".join(json.dumps(x, sort_keys=True, allow_nan=False) for x in [header, *files]) + "\n"
    publish_bytes(manifest, content.encode())
    return manifest


def load_snapshot(manifest):
    """Verify hashes, identity and raw-to-normalized replay before consuming data."""
    manifest = Path(manifest).resolve()
    entries = [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    if not entries or entries[0].get("schema") != SCHEMA:
        raise ValueError("not a supported CoinGlass snapshot")
    header, records = entries[0], entries[1:]
    if header["n_files"] != len(records):
        raise ValueError("manifest file count mismatch")
    root = manifest.parent.parent
    paths = set()
    raw = {}
    document = None
    for record in records:
        path = (root.parent / record["path"]).resolve()
        if not path.is_relative_to(root / "raw" / "coinglass") or path in paths:
            raise ValueError("invalid or duplicate snapshot path")
        paths.add(path)
        content = path.read_bytes()
        if sha256_bytes(content) != record["sha256"]:
            raise ValueError("CoinGlass snapshot hash mismatch")
        if record["kind"] == "normalized":
            if document is not None:
                raise ValueError("multiple normalized documents")
            document = json.loads(content)
        elif record["kind"] == "raw":
            if record["endpoint"] in raw:
                raise ValueError("duplicate raw endpoint")
            raw[record["endpoint"]] = (json.loads(content), record["sha256"])
        else:
            raise ValueError("unknown manifest entry")
    if document is None or document.get("schema") != SCHEMA or document["snapshot_id"] != header["snapshot_id"]:
        raise ValueError("snapshot identity mismatch")
    if document["settings"] != header["settings"] or document["observed_at"] != header["observed_at"]:
        raise ValueError("snapshot context mismatch")
    settings = document["settings"]
    if set(document["datasets"]) != set(settings["datasets"]):
        raise ValueError("snapshot dataset membership mismatch")
    observed = _moment(document["observed_at"])
    for name, result in document["datasets"].items():
        if result["status"] == "unavailable":
            if name in raw:
                raise ValueError("unavailable endpoint has raw data")
            continue
        if result["status"] not in ("ok", "empty", "invalid") or name not in raw:
            raise ValueError("invalid endpoint status or missing raw data")
        meta = result["metadata"]
        params = meta["params"]
        validate_request(name, params)
        if any(params.get(k) != settings[k] for k in ("symbol", "exchange", "interval", "limit", "start_time", "end_time")):
            raise ValueError("endpoint context differs from snapshot")
        if _moment(meta["requested_at"]) > _moment(meta["observed_at"]) or _moment(meta["observed_at"]) > observed:
            raise ValueError("invalid response observation ordering")
        payload, sha = raw[name]
        if str(payload.get("code")) != "0" or sha != meta["sha256"] or meta["endpoint"] != name:
            raise ValueError("invalid provider envelope or raw identity")
        if result["status"] == "invalid":
            continue
        replay = normalize_history(name, payload["data"], params, meta["observed_at"])
        if any(replay[k] != result[k] for k in replay) or (result["status"] == "ok") != bool(replay["rows"]):
            raise ValueError("normalized observations do not reproduce from raw data")
    if set(raw) != {n for n, r in document["datasets"].items() if r["status"] != "unavailable"}:
        raise ValueError("unexpected raw endpoint")
    return document


def latest_context(manifest, *, asof=None, max_age_intervals=2):
    """Values plus readiness flags; unavailable, null and stale are not zero."""
    if type(max_age_intervals) is not int or max_age_intervals < 1:
        raise ValueError("max_age_intervals must be a positive integer")
    document = load_snapshot(manifest)
    cutoff = _moment(asof)
    cutoff_ms = int(cutoff.timestamp() * 1000)
    available = _moment(document["observed_at"]) <= cutoff
    step = INTERVAL_MS[document["settings"]["interval"]]
    context = {}
    for name, result in document["datasets"].items():
        item = {"status": result["status"], "units": result.get("units", UNITS[name]),
                "params": result.get("metadata", {}).get("params", result.get("params"))}
        if not available:
            item["status"] = "not_yet_observed"
        elif result["status"] in ("ok", "empty"):
            rows = [r for r in result["rows"] if r["bar_end"] <= cutoff_ms]
            if not rows:
                item["status"] = "empty"
            else:
                latest = rows[-1]
                age = cutoff_ms - latest["bar_end"]
                item.update(status="stale" if age > max_age_intervals * step else "ready",
                            time=latest["time"], bar_end=latest["bar_end"], age_seconds=age / 1000,
                            values={k: latest[k] for k in FIELDS[name]},
                            observed_at=result["metadata"]["observed_at"],
                            missing_intervals=result["missing_intervals_between_rows"])
                if any(v is None for v in item["values"].values()) and item["status"] == "ready":
                    item["status"] = "incomplete"
        else:
            item.update(reason=result.get("reason"), message=result.get("message"))
        context[name] = item
    return {"schema": SCHEMA, "manifest": str(Path(manifest)), "snapshot_id": document["snapshot_id"],
            "settings": document["settings"], "observed_at": document["observed_at"], "asof": _stamp(cutoff),
            "all_requested_ready": all(r["status"] == "ready" for r in context.values()), "datasets": context}


def history_frame(manifest, *, asof=None):
    """Outer-join explicit period timestamps for research; never forward-fill gaps.

    Column names are endpoint.field. The entire snapshot must already have been
    observed at asof; attrs retain provenance and retrospective availability.
    """
    import pandas as pd

    document = load_snapshot(manifest)
    cutoff = _moment(asof)
    if _moment(document["observed_at"]) > cutoff:
        raise ValueError("snapshot had not been observed at asof")
    parts = []
    for name, result in document["datasets"].items():
        if result["status"] != "ok":
            continue
        frame = pd.DataFrame(result["rows"]).set_index("time")
        frame = frame[frame["bar_end"] <= int(cutoff.timestamp() * 1000)]
        parts.append(frame.rename(columns={c: f"{name}.{c}" for c in frame.columns}))
    out = pd.concat(parts, axis=1).sort_index() if parts else pd.DataFrame()
    out.index.name = "time"
    out.attrs.update(schema=SCHEMA, observed_at=document["observed_at"], manifest=str(Path(manifest)),
                     settings=document["settings"], units={name: result.get("units", UNITS[name])
                                                          for name, result in document["datasets"].items()},
                     endpoint_parameters={name: result.get("metadata", {}).get("params", result.get("params"))
                                          for name, result in document["datasets"].items()},
                     endpoint_status={name: result["status"] for name, result in document["datasets"].items()},
                     availability="historical bars retrieved at observed_at; not vintage point-in-time evidence")
    return out

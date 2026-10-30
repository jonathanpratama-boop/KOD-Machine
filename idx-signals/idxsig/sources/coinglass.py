"""Bounded CoinGlass v4 transport. Credentials are never part of recorded metadata.

Pacing is per client instance, not a distributed account quota. Applications sharing
one account must coordinate their combined request budget. No network access occurs
at import time. CoinGlass funding values retain the provider's native units.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import os
import re
import threading
import time
from typing import Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_URL = "https://open-api-v4.coinglass.com"
API_KEY_ENV = "COINGLASS_API_KEY"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RETRY_DELAY = 30.0
INTERVALS = ("1m", "3m", "5m", "15m", "30m", "1h", "4h", "6h", "8h", "12h", "1d", "1w")
COMMON = frozenset(("exchange", "symbol", "interval", "limit", "start_time", "end_time"))
REQUIRED = frozenset(("exchange", "symbol", "interval"))


@dataclass(frozen=True)
class Endpoint:
    path: str
    parameters: frozenset[str]
    required: frozenset[str] = REQUIRED
    shape: str = "rows"


ENDPOINTS = {
    "supported_coins": Endpoint("/api/futures/supported-coins", frozenset(), frozenset(), "coins"),
    "supported_pairs": Endpoint(
        "/api/futures/supported-exchange-pairs", frozenset(("exchange",)), frozenset(), "pairs"
    ),
    "price": Endpoint("/api/futures/price/history", COMMON),
    "open_interest": Endpoint("/api/futures/open-interest/history", COMMON | {"unit"}),
    "funding": Endpoint("/api/futures/funding-rate/history", COMMON),
    "liquidations": Endpoint("/api/futures/liquidation/history", COMMON),
    "long_short": Endpoint("/api/futures/global-long-short-account-ratio/history", COMMON),
    "rsi": Endpoint("/api/futures/indicators/rsi", COMMON | {"window", "series_type"}),
    "macd": Endpoint(
        "/api/futures/indicators/macd",
        COMMON | {"fast_window", "slow_window", "signal_window", "series_type"},
    ),
    "ma": Endpoint("/api/futures/indicators/ma", COMMON | {"window", "series_type"}),
    "ema": Endpoint("/api/futures/indicators/ema", COMMON | {"window", "series_type"}),
    "boll": Endpoint("/api/futures/indicators/boll", COMMON | {"window", "mult", "series_type"}),
    "atr": Endpoint("/api/futures/indicators/avg-true-range", COMMON | {"window"}),
}


class CoinGlassError(RuntimeError):
    """Safe error: never contains response bodies, credentials or request headers."""

    def __init__(
        self, kind: str, message: str, *, http_status=None, provider_code=None, retry_after=None
    ):
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.provider_code = provider_code
        self.retry_after = retry_after


@dataclass(frozen=True)
class CoinGlassResponse:
    data: object
    raw: bytes
    metadata: dict


def validate_request(endpoint_name: str, params: Mapping) -> dict:
    """Validate and copy a request before constructing any network URL."""
    if not isinstance(endpoint_name, str) or endpoint_name not in ENDPOINTS:
        raise CoinGlassError("configuration", "unknown CoinGlass endpoint name")
    endpoint = ENDPOINTS[endpoint_name]
    if not isinstance(params, Mapping) or not set(params).issubset(endpoint.parameters):
        raise CoinGlassError("configuration", "unsupported CoinGlass request parameter")
    if endpoint.required - set(params):
        raise CoinGlassError(
            "configuration", "CoinGlass history requires exchange, symbol and interval"
        )
    out = dict(params)
    for name, value in out.items():
        if name in ("exchange", "symbol"):
            if not isinstance(value, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9 ._:/-]{0,79}", value
            ):
                raise CoinGlassError("configuration", f"invalid CoinGlass {name}")
        elif name == "interval":
            if value not in INTERVALS:
                raise CoinGlassError("configuration", "unsupported CoinGlass interval")
        elif name == "unit":
            if value not in ("usd", "coin"):
                raise CoinGlassError(
                    "configuration", "CoinGlass open-interest unit must be usd or coin"
                )
        elif name == "series_type":
            if value not in ("open", "high", "low", "close"):
                raise CoinGlassError("configuration", "invalid CoinGlass indicator series_type")
        elif name == "mult":
            if (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise CoinGlassError(
                    "configuration", "CoinGlass Bollinger multiplier must be finite and positive"
                )
        else:
            # Integer-only parameters reject bools, float truncation and NaN.
            maximum = 253402300799999 if name in ("start_time", "end_time") else 1000
            minimum = 0 if name in ("start_time", "end_time") else 1
            if type(value) is not int or not minimum <= value <= maximum:
                raise CoinGlassError("configuration", f"invalid CoinGlass {name}")
    if "start_time" in out and "end_time" in out and out["start_time"] >= out["end_time"]:
        raise CoinGlassError(
            "configuration", "CoinGlass start_time must precede end_time (milliseconds)"
        )
    if endpoint_name == "macd" and out.get("fast_window", 12) >= out.get("slow_window", 26):
        raise CoinGlassError("configuration", "MACD fast_window must be smaller than slow_window")
    return out


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _transport(url: str, headers: dict, timeout: float) -> tuple[int, Mapping, bytes]:
    """Single HTTP attempt; redirects cannot carry the authentication header elsewhere."""
    opener = build_opener(_NoRedirects())
    request = Request(url, headers=headers, method="GET")
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        if response.geturl() != url:
            raise CoinGlassError("security", "CoinGlass redirect refused")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise CoinGlassError("schema", "CoinGlass response exceeds the supported size")
        return int(response.code), dict(response.headers), raw


def _now():
    return datetime.now(timezone.utc)


def _invalid_constant(value):
    raise ValueError("non-finite JSON number")


def _contains_secret(value, secret: str) -> bool:
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(
            _contains_secret(k, secret) or _contains_secret(v, secret) for k, v in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret(v, secret) for v in value)
    return False


def _stamp(moment: datetime) -> str:
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise CoinGlassError(
            "configuration", "CoinGlass clock must return a timezone-aware datetime"
        )
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _retry_after(headers: Mapping, now: datetime) -> float | None:
    value = next((v for k, v in headers.items() if str(k).lower() == "retry-after"), None)
    if value is None:
        return None
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = (parsedate_to_datetime(str(value)) - now).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


def _failure(status: int, code: str | None, message: object, retry_after=None) -> CoinGlassError:
    # The provider message is used only for classification; never reproduce it.
    hint = message.lower() if isinstance(message, str) else ""
    codes = {str(status), code}
    if "429" in codes or "rate limit" in hint or "too many request" in hint:
        kind, safe = "rate", "CoinGlass request quota reached; retry later"
    elif re.search(r"\b(upgrade|subscription|permissions?|plan)\b", hint):
        kind, safe = "plan", "CoinGlass endpoint or interval is unavailable on this API plan"
    elif "401" in codes or any(
        s in hint for s in ("invalid api", "invalid key", "api key expired", "api key is invalid")
    ):
        kind, safe = "unauthorized", "CoinGlass authentication failed; check COINGLASS_API_KEY"
    elif "403" in codes or "405" in codes:
        kind, safe = "plan", "CoinGlass endpoint or interval is unavailable on this API plan"
    elif "400" in codes or "422" in codes:
        kind, safe = "schema", "CoinGlass rejected the request parameters"
    else:
        kind, safe = "provider", "CoinGlass could not supply this response"
    return CoinGlassError(
        kind, safe, http_status=status, provider_code=code, retry_after=retry_after
    )


class CoinGlassClient:
    """Fixed-host API client. Inject transport(url, headers, timeout) for offline tests."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 25.0,
        max_attempts: int = 3,
        requests_per_minute: float = 30.0,
        transport: Callable | None = None,
        sleep: Callable = time.sleep,
        monotonic: Callable = time.monotonic,
        clock: Callable = _now,
    ):
        key = os.environ.get(API_KEY_ENV) if api_key is None else api_key
        if (
            not isinstance(key, str)
            or not key
            or len(key) > 1024
            or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in key)
        ):
            raise CoinGlassError("unauthorized", "Set COINGLASS_API_KEY to a valid API key")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (float, int))
            or not math.isfinite(timeout)
            or not 0 < timeout <= 25
        ):
            raise CoinGlassError(
                "configuration", "CoinGlass timeout must be finite, positive and at most 25 seconds"
            )
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise CoinGlassError("configuration", "CoinGlass max_attempts must be between 1 and 3")
        if (
            isinstance(requests_per_minute, bool)
            or not isinstance(requests_per_minute, (float, int))
            or not math.isfinite(requests_per_minute)
            or requests_per_minute <= 0
        ):
            raise CoinGlassError(
                "configuration", "CoinGlass requests_per_minute must be finite and positive"
            )
        self._key, self.timeout, self.max_attempts = key, float(timeout), max_attempts
        self._spacing = 60.0 / requests_per_minute
        self._transport, self._sleep, self._monotonic, self._clock = (
            transport or _transport,
            sleep,
            monotonic,
            clock,
        )
        self._last_attempt = None
        self._lock = threading.Lock()

    def request(self, endpoint_name: str, **params) -> CoinGlassResponse:
        params = validate_request(endpoint_name, params)
        if _contains_secret(params, self._key):
            raise CoinGlassError("security", "credential-like request parameter refused")
        endpoint = ENDPOINTS[endpoint_name]
        url = BASE_URL + endpoint.path + ("?" + urlencode(sorted(params.items())) if params else "")
        requested_at = _stamp(self._clock())
        for attempt in range(1, self.max_attempts + 1):
            with self._lock:
                if self._last_attempt is not None:
                    self._sleep(max(0.0, self._spacing - (self._monotonic() - self._last_attempt)))
                self._last_attempt = self._monotonic()
                try:
                    status, headers, raw = self._transport(
                        url,
                        {
                            "Accept": "application/json",
                            "CG-API-KEY": self._key,
                            "User-Agent": "KOD-Machine CoinGlass adapter v1",
                        },
                        self.timeout,
                    )
                except CoinGlassError:
                    raise
                except Exception:
                    error = CoinGlassError("transport", "CoinGlass network request failed")
                    status, headers, raw = 0, {}, None
            observed = self._clock()
            if raw is not None:
                if (
                    not isinstance(raw, bytes)
                    or len(raw) > MAX_RESPONSE_BYTES
                    or type(status) is not int
                    or not 100 <= status <= 599
                ):
                    raise CoinGlassError("schema", "invalid CoinGlass HTTP response")
                if self._key.encode() in raw:
                    raise CoinGlassError(
                        "security", "CoinGlass response reflected a credential; response discarded"
                    )
                if 300 <= status < 400:
                    raise CoinGlassError(
                        "security", "CoinGlass redirect refused", http_status=status
                    )
                delay = _retry_after(headers, observed)
                try:
                    payload = json.loads(raw, parse_constant=_invalid_constant)
                except (ValueError, UnicodeError):
                    payload = None
                if payload is not None and _contains_secret(payload, self._key):
                    raise CoinGlassError(
                        "security", "CoinGlass response reflected a credential; response discarded"
                    )
                if isinstance(payload, dict):
                    value = payload.get("code")
                    code = (
                        str(value)
                        if type(value) in (str, int) and re.fullmatch(r"\d{1,6}", str(value))
                        else None
                    )
                    message = payload.get("msg", payload.get("message"))
                else:
                    code, message = None, None
                if status == 200 and code == "0":
                    data = payload.get("data")
                    valid = isinstance(data, list) and all(isinstance(row, dict) for row in data)
                    if endpoint.shape == "coins":
                        valid = isinstance(data, list) and all(isinstance(row, str) for row in data)
                    elif endpoint.shape == "pairs":
                        valid = isinstance(data, dict) and all(
                            isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
                            for rows in data.values()
                        )
                    if not valid:
                        raise CoinGlassError(
                            "schema",
                            "CoinGlass response data has an unexpected shape",
                            http_status=status,
                            provider_code=code,
                        )
                    return CoinGlassResponse(
                        data,
                        raw,
                        {
                            "endpoint": endpoint_name,
                            "path": endpoint.path,
                            "params": params,
                            "requested_at": requested_at,
                            "observed_at": _stamp(observed),
                            "http_status": status,
                            "provider_code": code,
                            "attempts": attempt,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        },
                    )
                if status == 200 and code is None:
                    raise CoinGlassError(
                        "schema", "CoinGlass response has no valid result code", http_status=status
                    )
                error = _failure(status, code, message, delay)
            retryable = error.kind in ("rate", "transport") or (
                error.kind == "provider"
                and (
                    status == 408
                    or status >= 500
                    or error.provider_code in ("408", "500", "502", "503", "504")
                )
            )
            if (
                not retryable
                or attempt == self.max_attempts
                or (error.retry_after is not None and error.retry_after > MAX_RETRY_DELAY)
            ):
                raise error from None
            self._sleep(max(float(attempt), error.retry_after or 0.0))
        raise AssertionError("unreachable")

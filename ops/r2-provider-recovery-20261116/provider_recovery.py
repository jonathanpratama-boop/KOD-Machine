"""Runtime-only correction for a transient Binance 5xx response.

The frozen capture modules and study configuration remain byte-identical.
The adapter still receives the original failed response and archives it as an
error. Genuine access/rate restrictions retain their existing stop behavior.
"""
import time


def install(runtime, *, monotonic=time.monotonic, sleep=time.sleep):
    def market_transport(self, url, timeout, max_bytes):
        self._gate()
        started = monotonic()
        with self.lock:
            delay = max(0.0, getattr(self, '_transient_retry_at', 0.0) - started)
        if delay >= timeout:
            raise TimeoutError('Transient provider backoff; no request sent')
        if delay:
            sleep(delay)
            self._gate()
        remaining = timeout - (monotonic() - started)
        if remaining <= 0:
            raise TimeoutError('Transient provider backoff exhausted timeout; no request sent')
        result = self.network(url, remaining, max_bytes)
        headers = {str(k).lower(): v for k, v in result.get('headers', {}).items()}
        weights = [headers[k] for k in ('x-mbx-used-weight-1m', 'x-mbx-used-weight') if k in headers]
        try:
            weight = max(int(x) for x in weights) if weights else None
        except (ValueError, TypeError):
            weight = None
        status = result.get('status')
        transient = isinstance(status, int) and 500 <= status <= 599
        reason = None
        if status in (403, 418, 429, 451) or 'retry-after' in headers:
            reason = 'PROVIDER_ACCESS_OR_RATE_STOP'
        elif weight is None and not transient:
            reason = 'SHARED_WEIGHT_TELEMETRY_UNAVAILABLE'
        elif weight is not None and weight >= 300:
            reason = 'CONSERVATIVE_SHARED_IP_WEIGHT_CEILING'
        if reason:
            runtime._atomic(self.root / 'PROVIDER_STOP.json', {
                'reason': reason, 'at': runtime.iso(self.clock()),
                'http_status': status, 'reported_weight': weight,
                'scope': 'new observer only', 'url': url,
            })
        with self.lock:
            if transient and not reason:
                failures = min(6, getattr(self, '_transient_failures', 0) + 1)
                self._transient_failures = failures
                self._transient_retry_at = monotonic() + min(60, 2 ** failures)
            elif not reason:
                self._transient_failures = 0
                self._transient_retry_at = 0.0
        return result

    runtime.RestLanes._market_transport = market_transport
    return market_transport

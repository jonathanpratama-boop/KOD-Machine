"""E10 step 1, resumed. collect.py stopped after 2,731 filings on a truncated response (http.client.IncompleteRead
while reading an ~85 MB submission), which its retry loop did not catch. collect.py is frozen, so this wrapper runs it
unchanged except for one thing: a truncated or dropped transfer is retried like any other network error, and recorded
with status 0 if it keeps failing. Same stamp, same outputs; filings already saved are skipped, and the filing list is
rebuilt from the cached submissions.

Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/E10/collect_resume.py --stamp <collector stamp>
"""
import http.client
import importlib.util
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_spec = importlib.util.spec_from_file_location("e10_collect", Path(__file__).resolve().parent / "collect.py")
collect = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collect)


class Fetcher(collect.Fetcher):
    def get(self, url: str) -> tuple[int, bytes]:
        status, body = 0, b""
        for attempt in range(5):
            with self.lock:
                wait = self.interval - (time.monotonic() - self.last)
                if wait > 0:
                    time.sleep(wait)
                self.last = time.monotonic()
            req = urllib.request.Request(url, headers={"User-Agent": self.agent, "Accept-Encoding": "identity"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return resp.status, resp.read()
            except urllib.error.HTTPError as exc:
                status, body = exc.code, exc.read()
                if exc.code not in (429, 500, 502, 503, 504):
                    return status, body
            except (urllib.error.URLError, http.client.HTTPException, OSError):
                status, body = 0, b""
            time.sleep(2 * 2 ** attempt)
        return status, body


collect.Fetcher = Fetcher

if __name__ == "__main__":
    sys.exit(collect.main())

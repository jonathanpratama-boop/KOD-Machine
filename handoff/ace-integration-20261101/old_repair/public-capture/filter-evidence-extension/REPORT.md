# Bounded reference-evidence capture: stopped, not bypassed

Exactly two public unauthenticated requests were attempted on 2026-10-31:

1. BTCUSDT `/api/v3/avgPrice`: HTTP 200, requested 18:55:06.457641 UTC,
   received 18:55:10.708503 UTC. Returned `mins=5`, average `77652.55718748`,
   and last-trade timestamp `1793472910188`.
2. BTCUSDT `/api/v3/referencePrice`: HTTP 404 HTML, requested 18:55:10.708973
   UTC, received 18:55:13.569640 UTC.

Both used only `https://data-api.binance.vision`. No credentials or account/order
requests. No alternative host, retry, refreshed depth or second symbol request
followed the failed endpoint. Six GETs were allowed; only two were used.

The capture script's terminal message is a JSON decoding error because the 404
body is HTML, but `requests.json` retains the decisive HTTP status and raw-body
hash. This is **not** the documented structured error -2043 (no reference price).
Do not infer absent reference from it. Raw errors and original outcomes remain
unchanged rather than rewriting history to obscure the distinction.

Current filter documentation gives a non-null overriding reference precedence
over an average. As that overriding reference's state could not be established,
the new extension cannot honestly mark these real inputs eligible. No public
COMPLETE/PARTIAL result was produced; successful paths remain fixture-verified.

The extension's simulated account-count API is explicitly hypothetical and is
never represented as actual account evidence. No simulated-count assumption was
used to override this missing public reference evidence. The earlier full-filter
rejection artifacts are unchanged in the parent directory.

See `requests.json`, the two raw response files and `MANIFEST.json` for provenance.

## Separately authorized documented-host fallback

The parent authorized exactly one request to the documented public endpoint on
`api.binance.com` after the data-only host's endpoint-unavailable 404. That request
ran 18:56:49.777205–18:56:53.950347 UTC and returned **HTTP 451**, with the message
“Service unavailable from a restricted location…” referring to Binance eligibility.
No further request was made after this explicit restriction. No alternate host,
proxy, retry or bypass followed it. Total extension GETs are **three**.

`documented-fallback.json` and `BTCUSDT-referencePrice-official-response.txt`
preserve the URL, times, exact response and SHA-256. The average observation does
not establish overriding-reference absence; the real-input result stays blocked.

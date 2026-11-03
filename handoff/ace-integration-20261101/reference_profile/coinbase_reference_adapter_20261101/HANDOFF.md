# Coinbase USD reference adapter: implemented, reviewed, route blocked

## Actual outcome — 2026-11-01 UTC

The single authorized bounded attempt stopped at its FIRST metadata request:
`GET https://api.exchange.coinbase.com/products/BTC-USD`.

- Run start:11:07:21.693402Z.
- Request start:11:07:21.697271Z; transport failure:11:07:26.707576Z.
- Final outcome:11:07:26.709469Z, `BLOCKED_REFERENCE_ROUTE_STOPPED`.
- **One attempted GET / maximum eight; zero HTTP responses received.** No retry,
  redirect, alternate source, authentication, real order or scheduled job occurred.
- Transport raised `URLError`. No HTTP status or body was received, so a Coinbase
  denial versus managed connectivity failure is **not established**. Potentially
  credential-bearing transport detail was intentionally omitted from logs.
- No product metadata, candles or books were received. Input exposure list is empty.
- No account was initialized; no signal/decision/fill exists. Cash, holdings and NAV
  are **not applicable**, not a fabricated USD1000 account or CASH signal.

The reviewed source and policy remain unchanged after failure. No output-driven
relaxation or alternate-route attempt was made. The single-attempt permission is
exhausted. Do not rerun to work around this failure; any later attempt requires a
separate authorized plan through an approved managed route.

## Completed engineering

An OFF-by-default, GET-only Coinbase Exchange BTC-USD/ETH-USD reference adapter and
one-shot orchestrator reuse the reviewed v2 paper-account mechanics. Original v1/v2
records and synthetic default remain untouched. Source/spec pins must match the
independent clearance before any public path initializes. There is no order endpoint.

**48 combined mocked tests** pass in normal Python and `-O` (27 author +21 independent),
with network connections blocked during review. The unchanged original v2 separately
passes its30 tests in each mode; these are not extra integration tests. Reviews found
and fixed source-sequence regression, naive HTTP Date, public-call gating, managed
routing hygiene and endpoint-specific source-age/closed-candle semantics BEFORE the
only public attempt. See `../coinbase-independent-audit/REVIEW.md` and final logs.

The source profile is USD reference data, **not Binance/USDT or eToro execution**.
Shared-cash down-normalization is a NEW portfolio contract versus the separately
backtested per-asset0/1 rule. Fees1%, slippage0.1%, tax0%, top-depth fraction10% are
named research assumptions, not actual user/venue terms. Neither mocked tests nor
this blocked request establish market performance, a90-day history or readiness
for unattended deployment.

## Evidence paths / hashes

Local attempt evidence: `../coinbase_reference_capture_20261101T1107/`
- `outcome.json`: `fb99c44dce6433c5d9be8e07c3de1bb9cf2c992b135fedbca7d5d61d20db091d`
- `responses/01_error.json`: `fd298ee3736c16934732bc21f3584271c293b297d611bf81239b4366041a257e`
- `input_exposure.json`: `b04f9a89a349150e2b14944236a6527c16555886918e6490c61ce380114b943a`
- `run_manifest.json`: `56b2dc9a226d048328f079d605b617d107ab3eebf77591deb7ebc8f3585e197c`

Independent report SHA256:
`00f1e8e2712a3d8f13f6f7253e2e317d33349368729f1ab2713c22c58c958631`.
Exact eight source/spec pins: `SOURCE_PINS.json` and the preserved run manifest.
Original synthetic v2 remains `dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3`.

## Remaining gate

**Operational access, not an accounting-code failure, blocked this attempt.**
The reviewed adapter has only mocked end-to-end evidence; real-source schema,
clock, freshness and reference-fill eligibility remain unobserved. No Mac/Claude,
workflow, schedule, remote repository or private-account integration occurred.
Use the README for the bounded contract and unsupported behaviors; preserve all
attempt evidence unchanged. No automatic follow-up network work is authorized.

## Reproduce later only in a separately authorized connected environment

Copy this directory and its sibling `coinbase-independent-audit` unchanged. Use a
supported POSIX Python environment with its normal approved managed routing; do not
change proxy/security settings, substitute endpoints, or reuse today's output path.
First verify source clearance locally (no network):

```sh
PYTHONPATH=coinbase_reference_adapter_20261101 python -c \
 'import run_once; run_once.check_clearance("coinbase-independent-audit/REVIEW_CLEARANCE.json"); print("exact pins verified")'
```

Only AFTER separate authorization for a new bounded attempt, run the same reviewed
adapter once, with a new local evidence directory:

```sh
python coinbase_reference_adapter_20261101/run_once.py \
  --public-once \
  --review-clearance coinbase-independent-audit/REVIEW_CLEARANCE.json \
  --output-dir NEW_AUTHORIZED_LOCAL_EVIDENCE_DIRECTORY
```

This command is a later handoff, not a queued retry or instruction to bypass today's
failure. It remains capped at8 GETs, stops on refusal/input failure, and creates no
account until all pre-decision inputs validate. No synthetic fallback is fresh data.

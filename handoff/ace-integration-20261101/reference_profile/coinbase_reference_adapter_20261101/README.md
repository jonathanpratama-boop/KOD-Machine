# Coinbase Exchange USD reference adapter — OFF by default

This is an independently versioned **reference paper simulation**, not a trading
venue recommendation, a live bot, an executable broker quote, or a new historical
backtest. It makes no authenticated/private request and contains no order API.
No scheduled process is installed. The original synthetic-only v2 account remains
byte-identical and refuses this evidence. The v1 ledger is never opened or changed.

## What is implemented

`adapter.py` allows only public GET metadata, 40-day UTC candles and level1 books
for BTC-USD/ETH-USD at the official Coinbase Exchange hostname. Raw response bytes,
hashes, source and local receipt clocks and quantities survive normalization.
Unknown publication times stay unknown. A conservative local receipt-time rule
makes these bars usable only for this prospective latest-day decision, not past
executions. Public top-of-book sizes are indicative, not promised fills.

`paper_reference_core.py` is the reviewed v2 account with a narrow profile seam,
not a second backtest engine. See `CORE_PROFILE_DIFF.patch` and the exact vendored
original. It retains the v2 shared-cash allocation, holdings-based rebalance,
initial-equity peak, persistent kills, unknown-NAV propagation, append-only replay,
transaction lock and durability barriers. Changes bind USD/source identity,
validated receipts, minimum notional and adverse tick-rounded scenario prices.

The **portfolio contract differs from the original independent per-asset T1 rule**:
raw per-coin targets are normalized down if their sum exceeds1, within shared cash.
Neither old per-asset results nor the synthetic tests validate this new feed/portfolio
contract's profitability. Fees1%/side, slippage0.1%, tax0%, liquidity fraction10% are
named modeling assumptions, NOT verified applicable venue or user terms.

## Offline checks (no network)

```sh
python -m unittest discover -s coinbase_reference_adapter_20261101/tests -v
python -O -m unittest discover -s coinbase_reference_adapter_20261101/tests -v
```

The fabricated candle/quote tapes test bookkeeping and source semantics only.
A rising mock may produce simulated buys; a falling mock stays cash. The actual
one-shot cycle must not force either outcome. No daily NAV is backfilled at midday;
90-day Sharpe needs91 clean consecutive daily marks and is uncomputed here.

## One bounded capture, only after independent clearance

The default does nothing. Reviewer clearance binds the exact eight source/spec files
reported by `run_once.pins()`. Any edit makes that approval stale. After explicit
clearance, the authorized operator can run once in a **new** local directory:

```sh
python coinbase_reference_adapter_20261101/run_once.py \
  --public-once \
  --review-clearance PATH_TO_REVIEWER_CLEARANCE.json \
  --output-dir NEW_LOCAL_RUN_DIRECTORY
```

Requests: two metadata, two minimal warm-up, two pre-decision books; and only if
intents exist, wait6 seconds and request at most two post-decision books. Eight
maximum. No retries, redirects, alternate hosts, subscriptions, login or recurring
polling. Source/access refusal stops the entire route. Reusing a run directory is
refused. Retain it unchanged for replay/audit; do not restart to bypass a refusal.

Outputs: `run_manifest.json`, `responses/*_response.bin`, `*_receipt.json`, any
`*_error.json`, `input_exposure.json`, `outcome.json`; a ledger is initialized only
after all warm-up/product/prequote checks pass. A failed route may correctly have
**no account and no signal**. A valid cash signal has no fills and no invented trade.
An eligible reference fill uses only post-intent local request/source observations.

## Limits / unsupported deployment behaviors

- Source may omit required flags/time/size/rules or reject this environment; that
  blocks the route. Never substitute defaults, a proxy, Binance USDT or eToro data.
- HTTP Date and local monotonic checks detect coarse clock/latency problems; they
  do not cryptographically attest first publication, synchronized clocks, or feeds.
- Forty current candles are minimal prospective warm-up exposure, **not untouched
  historical holdout evidence**. Their requested/returned epochs are recorded.
- The one-shot new USD1000 reference account is not a user's balance. No funding,
  FX conversion, actual tax, minimum-account or platform eligibility claim is made.
- No schedule, continuous marks, ongoing liquidation runner, stop-fill guarantee,
  account migration, cloud/Mac integration or multi-host coordination is supplied.
  If holding marks age past5 seconds, whole NAV becomes unknown, not last-price NAV.
- If a persistent kill occurs, remaining holdings stay held until later eligible
  observations support a simulated sell; a snapshot does not guarantee liquidation.
- Unknown marks block risk-increasing buys. Missing cycles/daily samples remain gaps;
  they are not repaired by retrospective prices. Re-evaluate live deployment only
  under a separate reviewed integration plan, never infer it from this one-shot run.

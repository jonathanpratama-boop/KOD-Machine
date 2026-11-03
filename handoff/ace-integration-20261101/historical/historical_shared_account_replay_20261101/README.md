# Daily shared-account replay (separate exploratory approximation)

This is not a live bot, public-data retry, quote reconstruction, venue recommendation
or clean confirmation. Read PROTOCOL_v1.md and its pre-outcome ADDENDUM_1 first.
Original v2 synthetic and Coinbase source profiles remain unchanged.

## Data and model

Only the already downloaded, pinned BTCUSDT/ETHUSDT spot daily ZIP archives are
eligible. The daily CSVs from the earlier reproduction are returns, not OHLC inputs;
they are NOT used as prices. `history_inputs.py` revalidates all220 original ZIP
hashes and3332 bars/asset using explicit checks that survive Python `-O`.

Daily opening reference prices are NOT BBOs. Previous-day closes are assumed known
at00:01; decisions then wait until the FOLLOWING day's open (full-session lag).
Volume-based capacity is synthetic and fixed at intent creation from then-available
observations. No historical publication timestamp or actual executable depth exists.
The original quote-account mechanics are reused through the narrow diff in
CORE_PROFILE_DIFF.patch: shared cash, Decimal fees/sizing, holdings, normalized
allocation, persistent risk rules and deterministic replay. BUY budgets are fixed
at decision and affordable units use future modeled fill price; SELL units are fixed
at decision. Fees0.1% and slip0.05% per side are assumptions, not actual venue terms.

Independent development and validation accounts each start10000. Development begins
2017-09-26 after40 strictly earlier closes, because inputs do not support warm-up at
the old Aug17 study boundary. Validation begins2023-01-01 with earlier2022 warm-up.
No reset after kill WITHIN an account. Four predeclared policies: shared trend,
risk-overlaid50/50 buy-once, conventional50/50 buy-and-hold WITHOUT kills, and cash.
The conventional benchmark has a deliberately different risk policy, clearly labeled.

A kill does not erase positions or guarantee a25% loss ceiling: liquidation needs a
strictly later opening reference and sufficient synthetic capacity. A preplanned
terminal exit is charged normally; any residual holdings remain and are reported.
Intraday drawdown, spread/order queues, actual liquidity/minimums/taxes/arrival
latency remain unsupported. This cannot validate full operational system behavior.

## Reproduction

No-network synthetic tests:

```sh
python -m unittest discover -s historical_shared_account_replay_20261101/tests -v
python -O -m unittest discover -s historical_shared_account_replay_20261101/tests -v
```

Historical outcomes are OFF by default, until independent exact-source clearance:

```sh
python historical_shared_account_replay_20261101/replay.py \
  --run-reviewed-historical \
  --clearance historical-independent-audit/REVIEW_CLEARANCE.json \
  --inputs fresh_eyes_reproduction_20261101 \
  --output-dir NEW_CANONICAL_LOCAL_OUTPUT_DIRECTORY
```

This reads only existing local files and cannot download anything. It refuses an
existing output directory. Before results it saves source/protocol pins and checks
all input bytes. Every account has an append-only event chain, complete daily NAV,
fees/cash/holdings reconciliation and a separate deterministic core replay. A linear
new-file writer uses existing KOD event_hash/verify_chain primitives rather than
quadratic per-append full-journal scans; final replay validates every result/state.
If interrupted or failed, preserve partial output and report it; no silent overwrite
or strategy change. No automatic retry, remote push, scheduling or real order path.

Do not publish raw archives or per-day account evidence as untouched holdout data.
Results are retrospective on reused inputs. Growth differences do not establish an
edge or transfer the old per-asset backtest to this new portfolio/execution policy.

# TREND_CORE local v2 candidate — offline only

**New paper portfolio contract, not the T1c per-asset 0/1 backtest.** This implements
the missing account mechanics using synthetic observations; it neither establishes
an edge nor starts a forward trial. No market feed, private account, credentials,
network requests, financial orders or active workflow are used by the entrypoints.

## Run

Python 3.12 on Linux/macOS (uses POSIX `fcntl`). Standard library only.

```sh
cd trend_core_paper_v2_candidate_20261101
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python demo.py --output-dir /tmp/trend-v2-synthetic-demo
# Same inputs, same journal: safe identical retries, not another set of fills.
python demo.py --output-dir /tmp/trend-v2-synthetic-demo
```

The demo writes only the explicitly selected local directory. It deliberately
creates synthetic losses to exercise kill and partial-liquidation behavior. Its
NAV changes are NOT a market-performance result. Tests use temporary journals.
Do not edit source after creating a journal: replay checks exact code/protocol pins.
Use a fresh candidate version and separate account, not a silent journal migration.

## Files and reuse

- `PAPER_PROTOCOL_v2_CANDIDATE.md`: saved before fixtures; original remains unchanged.
- `PROTOCOL_ADDENDUM_1.md`: fail-closed aggregate-NAV guard discovered in synthetic audit.
- `paper_candidate.py`: spot quote-event adapter, deterministic event reducer, journal.
- `vendor/paper_cash_accounting.py`: byte-identical existing local `paper_cash_v1`
  Decimal sizing, liquidation and append/hash primitives; hash checked before import.
- `SOURCE_PINS.json`: reused-source rationale and exact preserved v1 hashes.
- `v1/`: unchanged protocol/pins/logger/four signal rows; separate duplicate-audit JSON.
- `fixtures.py`, `tests/`, `demo.py`: synthetic acceptance inputs, never market bars.

Cash convention is explicit: total includes reserved, free=total-reserved. Holdings
are real within the simulation: an intent is not a fill. Unknown held marks make
NAV unknown. Quote quantity must be supplied; missing size is never infinite depth.
Fees/slippage are named scenario assumptions, not verified venue rates.

## API / exact next integration seam (not performed)

1. Import `Ledger` into a separately reviewed offline integration task. Initialize
   one new account path with required initial cash/scenario. Do NOT point it at an
   existing KOD/v1 journal. Commands use semantic operation IDs; replay rejects
   conflicting retries. Every writer must use `Ledger.transact`; a side writer
   bypassing advisory locks is unsupported.
2. Preserve v1 originals. Reference `v1/DUPLICATE_AUDIT_METADATA.json` in an `audit`
   command; never turn those late signal observations into midnight executions.
3. Submit synthetic `observe` evidence, then `decision` with 40 consecutive completed
   closes and receipt/source hashes, then eligible future `observe` evidence for
   simulated fills. Use `fixtures.py` solely as the input-schema example, NOT a source
   of production prices. A stale decision, unknown NAV or missing quote must not be
   replaced by a guessed price. `advance` processes expiry without inventing fills.
4. `daily` records a UTC-boundary NAV only within scenario grace; misses/unknowns
   remain unknown. `missed` records process/data gaps with receipt time. Restart from
   the same journal; do not initialize away a persistent kill. Cash at risk remains
   held after kill until later quantity-supported sell observations arrive.
5. An actual captured-source adapter is deliberately **not implemented**. Current
   API rejects evidence kind other than `synthetic`, wrong venue/product/symbol,
   future receipts and crossed quotes. To support a real forward paper trial, first
   implement and independently review: trusted actual receipt clock, persist raw
   source bytes before decision, independently anchored hashes/receipts, venue symbol
   and instrument filters, quantity/lot/min-notional applicability, source errors and
   disconnects, scheduler missed-cycle detection, durable storage/locking and recovery,
   monitoring, latest-completed-cycle/stale-signal policy, and exact observed-vs-executable quote semantics.
   The current offline producer requires a completed causal signal date but does not
   impose an additional maximum signal-age rule; do not present this as production
   schedule freshness enforcement. A captured best quote
   is still not proof that a real order would fill; quote size is only a simulation
   cap. No broker/order-submission adapter belongs in this candidate.
6. Only after independent synthetic parity/acceptance and a separate activation
   decision should a new dated paper-only workflow be proposed. Nothing here edits,
   dispatches, pauses or replaces existing workflows or Moonshot/Claude tasks. Do not
   copy the old workflow's next-midnight fill assumption or [skip ci] integrity gap.

## Explicit unsupported behavior

No live trading; no backdated fills; no CFD/perpetual/leverage/short exposure; no
infinite-liquidity assumption; no unknown-mark-at-cost fallback; no automatic kill
reset; no automatic journal truncation after a torn write; no mutation of v1;
no historical strategy reruns; no equivalence to the backtested SMA candidate.
The adapter is a functioning offline account slice, not production certification.

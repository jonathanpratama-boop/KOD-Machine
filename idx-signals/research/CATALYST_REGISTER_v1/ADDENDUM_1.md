# Addendum 1 (2026-10-28, before the first SEC13D batch): two record-keeping fixes in `idxsig/catalysts.py`

Found by an independent read-only review of the branch, each confirmed by a second reviewer who tried to refute it.
Neither changes a rule, prior, window, abstention rule, look or any sealed record, so `protocol.json` stays as frozen
(its sha256 is bound into the 14 IDX_INDEX sets already sealed). Both affect only records not yet written: no SEC13D
batch and no DILUTION_RECENT tag existed when this was committed.

1. **Coverage gap on the first batch.** `protocol.json` defines a gap against the previous batch's newest entry. The
   first SEC13D batch has no previous batch, so as written it could never record a gap. If its feed read stopped (the
   5-page cap, or an empty feed) before reaching `window_start`, unlisted filings would have been missed silently. The
   code now compares the first batch with `window_start`, and any batch that reads no entries at all records a gap. This
   keeps the protocol's own rule, "missed filings are never backfilled", and the module's "a missing event is a recorded
   gap and never a quiet omission". Later batches compare with the previous batch exactly as before.
2. **Reasons on unknown DILUTION_RECENT tags.** When `company_tickers_exchange.json` could not be read, a US tag recorded
   `value: null` with the reason "no CIK in company_tickers_exchange", which claims more than was known. When the
   submissions could not be read, it gave no reason. The reason now says `company_tickers_exchange unavailable (HTTP
   <status>)` or `EDGAR submissions CIK <cik> unavailable`. The value stays `null` (unknown), as the protocol says.

Tests: `tests/test_catalysts.py` gains one batch test (a first batch that does not reach the window start, and one that
reads nothing, both record a gap) and two tag assertions (an unreadable ticker map, unreadable submissions).

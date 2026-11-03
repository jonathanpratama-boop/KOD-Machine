# CRYPTO_ACCOUNT_v1 — Correction 3 (rules v1.3)

Local successor candidate; not published, activated or deployed. Extends the
reviewed local v1.2 candidate without modifying its protocol, patches or archive.

## Confirmed input defect

`book_ticker` tested positive bid and ask >= bid, but positive infinity could pass.
`fetch_quotes` trusted injected getter results without checking them at all.
Offline full-cycle reproductions showed malformed quote records appended for
NaN, positive/negative infinity, zero/negative and crossed prices. Some malformed
feeds produced paper fills; an infinite ask reserved 962.50 in the synthetic
10,000 account. These are fixture results, not claims about production records.

With a fixture open position and a new independent decision, an infinite bid/ask
was committed before sizing raised `OverflowError: cannot convert float infinity
to integer`. The ledger grew from five records to six, ending in an invalid quote.

## Minimal correction

A shared validator rejects Boolean/null/non-numeric inputs, preserves legitimate
numeric-string parsing, converts prices to float and requires finite positive bid,
finite ask and ask >= bid. Both the HTTP parser and the injected getter boundary
use it. The existing fetch exception path records CRYPTO_QUOTE_ERROR instead of
CRYPTO_QUOTE, and the existing v1.2 eligibility gate declines new orders without
reserving cash. No strategy, sizing, settlement or position rules are changed.
Existing valid positions continue to use their last real recorded quote.

New records identify v1.3. The verifier retains the same failed-fetch eligibility
check for both v1.2 and v1.3 orders. Historical protocols/records are not rewritten;
this repair does not sanitize earlier corrupted records, inspect production
ledgers or assert that none exist. Earlier code pins intentionally remain the
historical versions, with the new source hash recorded only in protocol_v1_3.json.

## Offline verification

Eight new tests exercise invalid injected books, the actual mocked HTTP parser,
HTTP infinity through the full cycle, recent-cache fallback rejection, position
preservation/no mid-cycle crash, valid finite locked quotes, numeric strings, and
unrelated valid-symbol progress while another position has an invalid fetch.
The initial six tests produced 15 failed subcases and one error before the fix;
the expanded final eight tests also fail against unchanged v1.2 source (trace
preserved separately). After correction: eight pass; 81 combined account/
feasibility/adjacent tests pass with socket connections blocked.
No network requests, production ledger edits, real orders or remote writes.

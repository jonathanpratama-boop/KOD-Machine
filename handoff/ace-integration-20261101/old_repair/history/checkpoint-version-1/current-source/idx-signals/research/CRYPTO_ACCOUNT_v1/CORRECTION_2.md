# CRYPTO_ACCOUNT_v1 — Correction 2 (rules v1.2)

Local amendment candidate prepared 2026-10-31; not published or activated.
Source inspected: `41b8eb398b900da4cf251efe3971e31dae044ec9`.

## Defect and reproduction

v1.1's `fresh_quote` returned a cached quote within five minutes before checking
recorded fetch errors. A failed current request with a one-minute-old cache
therefore created an ACCT_ORDER and reservation (not a backdated fill), despite
the v1.1 documentation promising NO_FRESH_QUOTE. The added full-cycle regression
uses `fetch_quotes` with a getter that raises ConnectionError, not a fabricated
success. It fails on the unchanged source with ACCT_ORDER and passes on v1.2.

## Correction

Before allowing a new order, require the most recent quote/failure event as of
the decision clock to be a successful quote, still within the existing five-minute
age limit. Event timestamps determine recency; ledger sequence resolves
same-second ties. Future events cannot block or authorize the decision. A later
successful observation restores eligibility for a new independent decision; an
already declined decision is never retried or rewritten.

Existing pending reservations and open positions are retained on failure. Valid
recorded observations still settle existing orders under unchanged v1.1 rules;
otherwise pending orders wait or expire, and positions wait for a real exit
observation. No synthetic replacement price, fill, cancellation, or exit is added.
The verifier applies the new eligibility check only to v1.2 orders, using their
preceding ledger records, never later same-second events.

## Preservation and verification

The v1/v1.1 protocol files and all frozen US account files remain byte-identical.
New records declare CRYPTO_ACCOUNT_v1.2. Historical records and research experiments
are not edited. No production ledger was accessed for this local repair, so this
is not a claim about how many live records were affected.

Run from idx-signals:
`python -m unittest tests.test_crypto_account tests.test_paper_account tests.test_paper_book tests.test_paper_account_report`

43 tests pass: 22 crypto tests and 21 adjacent account/book/report tests, including
US frozen fingerprint checks. The regression covers recent cache plus actual fetch
failure, preserved pending/open state, same-second failure/recovery, future error,
recovery without retrying a declined decision, and version-aware verification.
All inputs are synthetic; no network requests, real-money orders, CI, publication,
merge, deployment, or 2024 research data access.

## Remaining simulation limits (not changed here)

Fractional quantity sizing still ignores exchange tick/lot/min-notional filters.
The adapter records bid/ask prices but not displayed quantity/depth and assumes a
whole-order fill at the first qualifying ask, without partial fills or queue/latency
modelling. Address these in a separately reviewed paper-only execution amendment,
not by changing frozen historical protocols or treating testnet as production depth.

# Independent local review evidence

Reviewer: /root/review_quote_failure_patch
Review date: 2026-10-31 UTC. Scope: local synthetic paper simulation only. No network requests, remote writes, production ledger inspection, activation, or frozen-file changes. Test runs prohibited socket.socket.connect. This summary records completed work; no new tests were run to produce it.

## Failed-current-fetch gate v1.2

Artifact: crypto-failed-fetch-v1.2.patch; local commit f2062b56d28cc42ba11133be3475a15ba7115c58.

Independently ran 43 crypto and adjacent account/book/report tests: all passed. Replaced only fresh_quote in memory with the local parent implementation: the one-minute-cache/current-fetch-failure regression failed as expected, producing ACCT_ORDER instead of ACCT_DECLINE NO_FRESH_QUOTE. All v1.2 protocol pins matched at review time.

Reviewed timestamp ordering, ledger-order same-second ties, future-event exclusion, recovery without retrying a declined decision, preservation of pending/open positions, version-aware verification, and four-file patch scope. No actionable defect found. Remote provenance was not independently rechecked; no production/history claims.

## Disconnected execution-feasibility estimator

Initial commit a455362e7723121c3a7e9095afc6c9f88204424a; artifact paper-execution-feasibility-v1.patch.

Independently ran 63 combined tests: all passed. Ran 23 additional checks covering NaN/sNaN/positive and negative infinity/negative price, depth and fees; bid sorting and duplicate levels; SELL fee arithmetic. All passed. Reviewed LIMIT/IOC semantics, disabled price components, explicitly unsupported zero lot step, notional normalization, partial/unfilled depth and quote-currency fees. No actionable defect within documented typed-input estimator scope. Not exchange parity, cash sufficiency, shared liquidity allocation, or guaranteed execution.

### Filter-evidence extension

Commit 319012922c2d0f23e91398f8d01c0cafe7288a7e; artifact paper-execution-filter-evidence.patch.

Independently ran 73 combined tests: all passed. Ran 21 additional adverse-input checks: null/empty/unknown/present/HTTP-error/raw-error-code override states reject; null/naive/future reference timestamps reject; exchange-wide count filters, MAX_POSITION, PERCENT_PRICE and unknown filters reject. All passed.

Reviewed explicit plain LIMIT/IOC applicability; reference interval, age and ordering; absence versus unknown override evidence; symbol-specific simulated total count +1 and algo count +0; unsupported filters; assumptions labeling. No actionable defect found. Evidence is supplied by caller, not independently authenticated. No live eligibility established. No attempt to retry or bypass the reported official-endpoint HTTP 451.

## Quote-input validation v1.3

Commit 99ee3ab6c175241313810bfd57b0e1c4ddb82a3f; artifact crypto-quote-validation-v1.3.patch.

Independently ran 81 combined tests: all passed. All v1.3 protocol pins matched. Reviewed shared validation before quote append at HTTP and injected-getter boundaries; malformed values becoming CRYPTO_QUOTE_ERROR; recent-cache gate; preservation of existing positions; unrelated valid-symbol progress; unchanged historical protocols. Clear for stated quote-input scope. Does not sanitize historical records or replace float arithmetic. Finite extreme quote smoke checks were not general arithmetic validation.

### Separate policy-reference boundary finding (not cleared by quote guard)

Loaded exact committed v1.3 source into an in-memory module, with temporary ledgers and valid finite book 99/100. BUY candidate verified_price.quote=+Inf raised ValueError converting NaN quantity to integer; 'garbage' raised float-conversion ValueError. Each had appended CRYPTO_QUOTE before failure. True authorized ACCT_ORDER at limit 1.01, quantity 952.01827875, reserve 962.50.

Static upstream inspection: paper.binance_quotes and policy functions use float conversion without strict finite/Boolean validation. Nonnumeric data normally becomes missing quote; +Inf normally becomes NOT EXECUTABLE through zero-size/finite-chase guards. Thus those malformed BUY reproductions do not establish ordinary scan reachability. Boolean true becomes numeric 1.0 upstream. candidates() only filters market/type/session, providing no account-side numeric schema guarantee.

Reported recommendation: narrow guarded positive finite non-Boolean policy-reference parsing, invalid-reference decline, and continued processing of other candidates. This reviewer has NOT independently tested or accepted any later implementation of that fix, CAS/concurrency changes, or successors after 99ee3ab.

# KOD engineering checkpoint — 2026-10-31 19:09 UTC

LOCAL CANDIDATES ONLY. Not pushed, merged, deployed, integrated or activated.
No real-money trades, private exchange account access, credentials, production
ledger changes, historical market dataset access or profit claims.

## Provenance and safe application

Repository: jonathanpratama-boop/KOD-Machine.
Upstream default branch inspected: claude/idx-signals-test-repo-ds0jw7.
Initial upstream source commit: 41b8eb398b900da4cf251efe3971e31dae044ec9.
Rechecked moving upstream head: 5eae447c1c16dcff3daf02da6bd6ee836069eaae.
At recheck, crypto account source, tests and v1.1 protocol blobs were unchanged.
No later-head compatibility is asserted; recheck before applying.

Local files were assembled from selected official connected-repository file
responses, NOT a complete repository clone. Local snapshot baseline:
248b5d2f49985618dfdd8485c7816da3962f9e7a. This synthetic selected-source git
history MUST NEVER BE PUSHED. No .git directory is included. On a normal complete
checkout, review then apply ONLY the three patches in this order:

1. crypto-failed-fetch-v1.2.patch
   local commit f2062b56d28cc42ba11133be3475a15ba7115c58
2. paper-execution-feasibility-v1.patch
   local commit a455362e7723121c3a7e9095afc6c9f88204424a
3. paper-execution-filter-evidence.patch
   local commit 319012922c2d0f23e91398f8d01c0cafe7288a7e

Current final source/tests/specs are included for inspection. They are not a
standalone replacement repository; existing project dependencies are required.
Historical protocol files are supplied solely as unchanged provenance evidence.
No historical protocol or existing US account/research engine was rewritten.

## Reviewed changes and verification

- Crypto v1.2: a failed current fetch cannot authorize a new order/reservation
  using a recent cached quote; valid existing pending/open state is preserved.
  The actual failed-fetch regression failed old code and passed repaired code.
  43 focused/adjacent tests passed, including frozen US account fingerprints.
- Disconnected Decimal LIMIT/IOC estimator: explicit timestamped filters/books,
  bounded displayed-depth partial fills, conservative rounding and stated fees.
  20 new tests; 63 combined passed.
- Filter evidence extension: recorded inapplicable-filter reasons; exact-interval
  fresh average with observed absence of overriding reference; simulated account
  counts explicitly labeled, never actual-account verification. Missing evidence
  and unknown filters fail closed. 10 new tests; 73 combined passed.
- Final 73-test run prohibited socket connections. Compilation, diff whitespace
  checks and frozen protocol pins passed. Independent review reported 21 extra
  adverse checks on the extension; its separate review scripts are not bundled.

Run from idx-signals in a complete checkout after reviewing/applying patches:
python -m unittest tests.test_paper_execution_filter_evidence tests.test_paper_execution_feasibility tests.test_crypto_account tests.test_paper_account tests.test_paper_book tests.test_paper_account_report

These are focused checks, not a claim that the complete repository suite or CI
ran. No remote CI was triggered by these local changes.

## Public observation and hard limit

Initial capture: four unauthenticated public GETs returned exchange filters and
100-level books for BTCUSDT, ETHUSDT and BEAMXUSDT. All six 100/1,000-USDT synthetic
requests rejected with full filters intact. An initial adapter Decimal-scale
rejection and the offline sizing correction are both preserved, not overwritten.

Extension capture: avgPrice HTTP 200; data-only referencePrice HTTP 404; separately
authorized documented official-host referencePrice fallback HTTP 451 restricted
location. THREE extension GETs total, then ALL ACCESS STOPPED. No geographic,
policy or technical bypass, no further host switch, no retries. Real-reference
state remains UNKNOWN; no real-market eligibility/fill success is claimed.

Public responses/provenance contain only public metadata, market data and error
bodies. They include request-start/receive UTC times and SHA-256. Original capture
manifests and rejection reports remain intact; a later addendum records the
explicitly authorized fallback and terminal 451. No private account data.

The estimator is a feasibility estimate, not exchange acceptance or guaranteed
liquidity. COMPLETE on fixtures means displayed depth under declared assumptions;
it is not a BUY signal, strategy result, validation of profitability or real fill.
Do not sum independent uses of the same book as if liquidity were reserved.

## Offline recovery amendment and incomplete observation

The bounded book observer was subsequently stopped by explicit runtime network
policy after 4 attempts: 3 successful books, 1 failed sample, 176 scheduled
observations missing. The intended two-hour campaign did NOT complete. No resume,
escalation workaround, alternative source or deadline extension was attempted.
The original collector source/protocol remain pinned and unchanged; raw journals,
policy error, original stale RUNNING status and reconciliation history are retained.

A new read-only status reader prevents stale RUNNING heartbeats from implying
current activity: UNKNOWN/STALE without verified liveness/termination; BLOCKED for
explicit runtime policy termination. Nine status tests plus ten collector tests
passed with networking prohibited. See book-observation/STATUS_READER_AMENDMENT.md.
The three earlier reviewed patches remain byte-identical. No production changes.

## Integrity and contents

CHECKSUMS.json hashes every payload file except itself. ZIP excludes .git,
credentials, local helper/auth metadata, internal notes, unrelated tasks, resumes,
large datasets and caches. Only this task's reviewed engineering and sanitized
public-capture evidence are included. Keep its Library identity when replacing a
later checkpoint; do not publish this synthetic local history.

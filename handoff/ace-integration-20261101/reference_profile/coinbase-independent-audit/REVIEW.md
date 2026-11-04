# Independent Coinbase reference adapter review

2026-11-01 UTC. Reviewer: audit_account_concurrency. Local mocked review only; no public request, trading endpoint, credential access, raw market dataset, or outcome study.

## Result
Clear for the technical scope of ONE bounded prospective public-reference capture, subject to separate parent authorization and managed network policy. This is not production, broker-execution, profitability, historical backtest, or full engine-integration clearance. The reviewer did not perform that capture.

Final combined suite: **48 tests = 27 author + 21 independent**, passing normal Python and `python -O`, with socket connection functions blocked. Evidence: combined-normal.txt and combined-optimized.txt. The separate unchanged synthetic-v2 suite also passed **30 tests** in each mode (original30-regression.txt and original30-optimized-regression.txt); these are separate suites, not 69 distinct integration tests. Initial-results.txt and independent-normal.txt are superseded development logs containing corrected reviewer-fixture expectations, not final acceptance evidence.

Run `python coinbase-independent-audit/run_combined.py` and the same command with `python -O`. Independent sources are test_independent.py (15 tests) and test_freshness.py (6 tests). Candidate source pins are recorded in REVIEW_CLEARANCE.json.

## Material corrections verified
- Source sequence OR source observation time regression rejects atomically, before ledger changes or fills. Equal sequence with a nondecreasing source time remains permitted.
- Naive HTTP Date cannot inherit local executor timezone: explicit aware GMT is required.
- Direct programmatic use of the default public client requires the same exact-source clearance as the CLI, before transport/output initialization.
- The temporary proposed empty ProxyHandler was withdrawn before any public request. Final urllib opener retains default managed routing and verified TLS, adding only redirect refusal and origin Authorization/Cookie rejection. The independent mocked netrc guard and handler inspection pass; no proxy environment values, settings, or credentials were inspected. Transport exceptions omit potentially sensitive text (author regression included).

## Scope checked
Separate USD/BTC-USD/ETH-USD profile, not the synthetic Binance-USDT profile. Exact host/path/query GET allowlist; no order/account/auth route; no redirect, retry or alternate host; eight-request bound; timeout and bounded response reads; 401/403/429 stop and preserve available evidence. No fallback follows refusal. One-shot inputs are current reference observations, not reconstructed historical fill quotes. A partial run refusal preserves already-held paper positions rather than inventing rollback.

Candle schema close index 4, reverse response sorting, 40 closed contiguous UTC daily buckets, duplicate/gap rejection and unknown first-publication time checked. Product identity, status, increments, tick, minimum notional and liquidity fail closed. Raw receipt reparse binds normalized source/policy fields. A later local receipt cannot relabel a pre-intent source observation or pre-intent request into an eligible fill. Shared cash, explicit assumed fee/slippage accounting, source pins and mixed-profile journal rejection exercised.

Original paper_candidate.py and vendor copy retain SHA256 dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3. Accounting core retains SHA256 29688797f6738e4aa02ca87403a5a90d60dec0bca54cffab36a4a4a7e266f8a6. AST comparison confirms inherited account_view, reserve, cancel_pending, kill, liquidations, risk, expire, sharpe_status and Ledger unchanged. These checks support reuse of previously tested mechanics, not a claim every adapter state path has been exhaustively tested.

## Limits
Only synthetic/mocked data was used. No claim that Coinbase currently returns every required field: absent fields must stop. Fees/slippage and displayed-depth participation are named research assumptions, not venue fees or actual executable liquidity. Local receipt/body hashes do not establish externally authenticated first publication or immutable preregistration. Unknown first publication stays unknown. No historical daily NAV is fabricated, and the one-shot run cannot establish a Sharpe history or profitability. Filesystem durability remains the inherited bounded POSIX design, not power-loss proof. The clearance file is a local review artifact, not a security/authentication token or permission to bypass network restrictions. Parent go is still required; this review does not authorize access outside the selected managed route.

## Endpoint freshness amendment independently reviewed
The prior clearance was explicitly disabled during this pre-capture amendment. No public request preceded either policy. Books keep their strict 2-second RTT, supplied Age=0, 5-second source/receipt clock and at-use freshness requirements. Products and completed candles permit RTT up to 5 seconds and effective receipt age up to 300 seconds. Source age is max(apparent Date age, supplied Age plus measured response delay); metadata use adds local residence. This neither sums Date age and Age (double counting) nor omits transit/residence (understatement). Independent exact-boundary cases confirm 120+3+177=300 accepts, 300.001 rejects, and Age299+RTT5 rejects at receipt.

Absent Age is explicitly preserved as absent; Date-derived age and transit still constrain acceptance, but complete cache history/first publication remains unknown. Supplied Age must be ASCII integer delta-seconds; malformed, fractional, signed and nonfinite fields reject. Case-insensitive duplicate headers reject; new captures preserve original header pairs and validation rejects dictionary/pair disagreement. Candle HTTP Date must not precede the final selected daily close, even if receipt occurs after that close. Six independent amendment tests pass in both Python modes alongside all existing tests. freshness-prefinal.txt records the pre-fix interim failures and is superseded by final combined logs.

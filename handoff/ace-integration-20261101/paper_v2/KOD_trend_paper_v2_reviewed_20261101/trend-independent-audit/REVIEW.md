# Independent TREND_CORE paper-v2 candidate review

**Final assessment: no remaining blocker found in this bounded offline synthetic-account review after three repairs. Not profitability, full-engine integration, venue calibration, Mac validation or live-readiness certification. Publication/activation remains on hold.**

## Exact evidence and identity

- **30 tests pass normal and `-O`: 18 author + 12 independent.** Main-process sockets blocked. Logs: `combined-normal.txt`, `combined-optimized.txt`; repeat with `python run_combined.py` from this review directory.
- **Two additional bounded OS-process race cases** (not counted as unit tests): duplicate BTC observation commits one row/one fill; distinct BTC/ETH observations commit two rows/two fills. Four spawned children exit0; real flock, explicit pipe gates/timeouts/cleanup, temporary journals, no network. Cash/reservations stay nonnegative, gross/NAV<=1 and deterministic replay verifies. Receipt: `multiprocess-results.jsonl`; script `multiprocess.py`.
- Final paper_candidate.py SHA256: `dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3`.
- Original protocol SHA256 remains `94a6508600ae50766c7ab9efdd74bb069e41076c575a94f68b0f58f31be5b22c`; addendum SHA256 `e371b30f1f536b75732879e12cf941f445fdaa41b79f5b72b6148daa553ecf95`.
- Vendored accounting bytes equal the existing paper_cash_v1/accounting.py exactly; SHA256 `29688797f6738e4aa02ca87403a5a90d60dec0bca54cffab36a4a4a7e266f8a6`. Import verifies this identity before execution. Reused Decimal sizing/fees/liquidation/hash primitives are real reuse, not merely a naming claim.

## Concrete defects found and repaired by author

1. **BUY with unknown aggregate NAV:** after BTC fill00:01:05, ETH quote00:04 executed roughly4999.99 cash of ETH while held BTC mark was stale and NAV/drawdown unknown. BUY now waits for complete fresh aggregate NAV; pending reservation/expiry survive, then a later eligible quote can fill. SELL/unwind remains independent. A dated addendum records this increased-risk boundary correction without rewriting the original protocol.
2. **Cross-symbol sell-before-buy violation:** during BTC-overweight/ETH-buy rebalance, ETH quote first spent residual0.02 and IOC-completed the buy; BTC's later sale released roughly2490 cash with no buy remaining. Sorting only a single quote's intents was insufficient. BUY now waits for all pending sells; later BUY observation uses actual realized cash, not assumed sale proceeds.
3. **Success without recovered durability barrier:** complete append followed by injected fsync error left a valid row; exact retry previously returned success without any successful fsync. Retry now syncs verified existing file and parent directory before returning success; new appends also sync the parent. No duplicate event is written. Injected partial append separately proves torn-tail refusal, preservation of existing bytes, and no automatic truncation.

## Mechanics independently checked

Shared total cash includes reservations exactly once; actual holdings change only on fills. Fees equal rounded scenario fee on actual slipped fill notional and cash equals initial plus recorded fill cash changes. Raw targets1/1 normalize to0.5/0.5 rather than allocating each coin a separate account. Combined gross<=1 and no negative cash hold in tested tapes.

Strict quote-after-intent/source-availability gates, instrument/venue/product restrictions, missing top-of-book quantity refusal and sub-precision rounding pass. Unknown held marks propagate to whole NAV. Kill uses initial-equity peak, persists through retries/restart/audit metadata/new decisions, never fills at its triggering quote, and partial liquidation leaves real residual holdings/new future-only intents. Missing daily marks remain unknown; 90 returns require91 consecutive complete marks. Author's reducer fixture verifies negative trailing Sharpe kills before25% drawdown, including explicit zero-variance conventions.

Replay checks chain, input digest, semantic ID, pinned code/protocol, reconstructed result and state digest. Same payload retries deduplicate; conflicting payloads fail without changing bytes. Whole read/replay/validate/append is under a process lock, so a separate CAS is not needed for API writers. Manual wrong input-digest/recomputed-chain probe is rejected.

## Preservation and limits

All four original v1 signal rows match the supplied Git blob and per-line hashes. Separate metadata correctly maps duplicates3→1 and4→2; no deletion, in-place reclassification or conversion into fills. Remote retrieval provenance belongs to the author; this review independently recomputed local pinned-byte identity.

The original candidate protocol was present in the initial reviewed tree before author fixtures appeared; its original bytes remain unchanged. That supports local sequencing, **not immutable/external preregistration proof**. Corrections/addenda are openly dated and pinned.

No raw market data/outcomes, remote edits, CI, credentials, financial trades or Mac access occurred. All prices/depth/fees/precision are supplied synthetic assumptions. Venue lot/min-notional rules are not verified; missing scenario precision rejects, but explicit scenario precision is not exchange evidence. Local hash/receipt timestamps do not certify actual availability. Tests run on this Linux executor; no physical power-loss, filesystem corruption/load test or Mac storage validation. POSIX file/directory fsync and advisory locks still require supported storage and all writers using the API; torn-tail recovery remains manual. No new general historical backtester or strategy-return claim is established.

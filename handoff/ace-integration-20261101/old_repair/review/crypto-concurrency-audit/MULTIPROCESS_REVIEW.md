# Bounded actual multiprocess validation

Candidate: isolated `b40e0e6` archive. Script: `multiprocess_cas.py`; final outputs: `multiprocess-results.jsonl`.

Two independent spawned OS processes share a temporary ledger. Parent/child pipes gate both workers after decision computation and before publication, ensuring both propose the final available slot before either can commit. No Manager or socket-based coordination service. Two seed orders reserve approximately 100 of the 150 total planned-risk allowance. Cases use duplicate C/C and disjoint C/D candidates. Finite 105/106 books keep orders unfilled. Both workers use the real `paper.append` process lock and expected-head CAS. Socket connects are prohibited. A local fake timestamper writes clearly labeled NOT-RFC3161 test tokens only inside the temporary directory; no receipt authority is contacted. Readiness/completion/join waits are bounded, with terminate/kill cleanup if necessary.

## Final validation results

Both cases passed all assertions and all four child processes exited 0:

- Exactly 3 orders (cap 3).
- Planned risk 149.99999988 (cap 150).
- Cash 10000; reserved 2887.49999772; free cash 7112.50000228, all nonnegative.
- No duplicate decision IDs.
- Hash-chain verification and account verification both empty/clean.
- Actual stale-head conflicts observed in both processes/cases.
- Duplicate loser recomputed to no events; disjoint loser recomputed to DECLINE.
- All ledger rows received fake local test tokens; no receipt warning.

## Observed liveness qualification

The initial harness required both cycles to return normally. Its duplicate case passed, but the disjoint loser encountered the designed `StaleHeadConflict: crypto account phase contention: retry budget exhausted` as the winning process continued to append observations and a mark. The harness then aborted instead of reporting final invariants. This is an expected fail-closed outcome under the configured three-attempt budget, not evidence of an unsafe append. The temporary initial ledger was cleaned up, so no final-state claims are made about that aborted harness case.

The harness was corrected to treat explicit retry exhaustion as a reported terminal fail-closed outcome (still requiring all safety invariants, clean child shutdown and at least one real conflict), not as silent success or an automatic business retry. The final bounded rerun completed normally in both cases. No candidate implementation was changed. Under different scheduling, retry exhaustion remains possible even with only two overlapping cycles; safe completion is not guaranteed by a bounded optimistic retry budget. A runner should surface that state and arrange a later whole-cycle invocation if authorized, rather than blindly resending old proposals.

This closes the prior lack of any OS-process overlap test. It remains two targeted race scenarios, not stress/load testing or production validation.

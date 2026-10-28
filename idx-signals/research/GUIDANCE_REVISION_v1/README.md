# Guidance revision: first paper-decision milestone

**Recorded 17 October 2026 at 07:19:29 UTC / 14:19:29 WIB. Decision: STAY IN CASH.**

This is the completed first operational milestone of GUIDANCE-REVISION-v1, not a completed profitability experiment. The fixed seven-issuer cohort had no Item 2.02 8-K reported in the captured SEC metadata over 10–17 October. All seven observations were retained. No issuer was substituted to force a positive signal.

| Item | Result |
|---|---|
| Protocol frozen | 17 October 2026, 07:12:24 UTC |
| Cohort | AAL, MATX, ACU, Abbott/ABT, AEP, AXP, AMD |
| SEC submissions requests | 7 successful HTTP 200 responses, identity and raw hashes checked |
| Current earnings events | 0 under the frozen Item 2.02 / seven-day selection rule |
| Current paper decisions | 7 NO_SIGNAL / NO_CURRENT_EVENT; aggregate STAY_IN_CASH |
| Filled exposure | USD0 |
| Shadow account | USD10,000 cash; an explicit research assumption, not the owner's account balance |
| Historical extraction fixture | Original AMD 2021 releases reproduce 37% to 50% growth guidance: +9.489% forecast revenue level |
| Guidance-specific tests | 14 pass |
| Repository tests | 257 pass with Python 3.12 and the existing calendar dependency 4.5.6 |
| Decision read-back | PASS: protocol/code/evidence hashes, source inventory, IDs and ledger chain |

## What was built

`idxsig/guidance.py` adds source-bound guidance comparisons, UTC/New York clock handling, exchange-session scheduling, a separate paper decision/fill transition, risk sizing, observed-quote valuation/exit and duplicate-resistant chained recording. It reuses the existing KOD paper-ledger convention. It does not change the daily paper policy or production ledger.

The policy uses one numeric, comparable annual-revenue revision. It does not require a preceding +30% price move. The paper entry is at a future regular-session 09:45 ET with fresh broker bid/ask and verified product/protection. Its exit is an observed 5% stop or the twentieth session close. Primary model costs are USD2 commission each side plus 0.10% execution stress each side; the observed spread is already in bid/ask. Maximum notional is 10% of shadow equity, planned loss including modeled fees is at most 0.5%, and only one position is allowed in this first cohort.

The frozen module handles unchanged/lowered/incomparable/absent guidance explicitly. It rejects future information, mismatched security identities, stale/crossed/wide entry quotes, premature/late entries and cash/risk breaches. A gap exit uses the observed bid, not an assumed stop fill; wide adverse exit spreads do not erase a losing exit.

Extraction is a structured, cited review of source text. There is no autonomous language-model extractor or API charge. Numeric direction and relative forecast change are calculated by the code; semantic comparability and the most recent prior disclosure still require review. A current release explicitly citing its previous guidance is strong prior-binding evidence; otherwise the reviewer must check intervening updates, including non-Item-2.02 disclosures. Missing proof stays REVIEW_REQUIRED.

## Evidence locations

- `PROTOCOL.md`, `protocol.json`, `FREEZE.json`: fixed question, cohort, policy and local freeze. This is not an external timestamp receipt.
- `data/inventory.json`, `data/sec/`: actual current acquisition responses and per-issuer records. No historical stock-price panel was loaded.
- `data/broker_reference.json`: reference-only broker lookup. Its Friday closing quotes were not converted into fills.
- `fixtures/`: compressed, original SEC bytes for the previously reviewed AMD example, with original and compressed hashes. The ten original manual classifications are retained as context, not an independently measured accuracy benchmark.
- `IMPLEMENTATION_FREEZE.json`: exact module/test/input identities at the first decision.
- `paper/DECISION.json`: aggregate paper decision and individual result references.
- `paper/ledger.jsonl`: immutable snapshot of all seven current records, distinct from the daily production ledger.
- `paper/AMD_FIXTURE.json`: historical source-to-feature result, excluded from the current cohort and all prospective performance claims.
- `paper/VERIFICATION.json`: saved acceptance checks.

The research directory is immutable once committed. Future runs must use new dated directories; do not append to or overwrite this committed first snapshot. The `append_once` helper can maintain an operational journal elsewhere, but no scheduled collector or continuing operational journal was deployed in this milestone.

## Verification

From `idx-signals/`, with Python >=3.10, the core repository dependencies and this directory's `requirements.txt` installed:

```sh
python3 -m unittest tests.test_guidance_revision -v
python3 research/GUIDANCE_REVISION_v1/run_first_decision.py --verify
```

The first run used the existing G3 Python 3.9 environment for collection and focused tests. The broad suite exposed two pre-existing Python-3.10 annotation requirements, so final checks used the bundled Python 3.12 runtime with isolated copies of existing pure-Python calendar dependencies. The broad suite passed all 257 tests. Existing synthetic E9 test output is test-fixture output, not a new strategy result.

`collect.py` is the bounded bootstrap acquisition script for this saved cohort. Its cache and selection cutoff are intentionally tied to this first freeze; it is not a live refresh command. `run_first_decision.py` refuses to overwrite the recorded decision. Use `--verify` to reproduce acceptance checks without rerunning acquisition or changing the ledger.

## What this result does and does not establish

The current observation is a valid zero-exposure decision for a narrow, declared cohort. It says nothing about earnings events outside those seven issuers, about guidance communicated in other filing items, or about the completeness/latency of the SEC feed beyond its captured response. The first cohort is an operational reuse of the access sample, not a representative moonshot population.

The AMD fixture proves the source-binding and arithmetic path on a known example. It is historical, source-reviewed evidence, not a timely detection, current recommendation, simulated fill or positive return. No strategy performance or probability has been estimated.

One broker lookup resolved `ABT` to Arcblock, a crypto asset, rather than Abbott Laboratories. That identity is explicitly unverified for Abbott; a matching ticker alone cannot admit a stock trade. Product type, exact account costs and stop support also require verification before any future paper fill. The existing closing quotes are stale for a new entry.

The 5% stop is a planned price distance, not a guarantee of a 5% realized-loss cap. Gap and monitoring risks remain. The module's valuation helper is not an order book or a continuously running monitor. Position-state arguments must come from the retained research account state; a caller cannot treat a prior PAPER_WAIT as an already executed trade.

## Exact next step

At the next real earnings event for this fixed cohort, save a new dated acquisition packet using the existing SEC client. Review the current revenue forecast against the latest comparable prior and bind exact source spans. Invoke the frozen `revision` and `decide` functions with actual source, retrieval and review times. Record the result in a new immutable run snapshot; never rerun today's snapshot to overwrite NO_SIGNAL. A qualified event can produce PAPER_WAIT for its specified entry minute. Only a fresh, account-eligible quote and verified protection can subsequently produce a paper fill.

That is the next research observation. Another strategy, expanded universe, paid provider, parameter search or agent panel is not needed to continue this operational cohort. Profitability remains untested and needs new outcomes over time.

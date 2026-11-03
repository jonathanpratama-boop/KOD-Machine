# FRESH_EYES_v1 independent code/aggregate audit

Audit cutoff: 2026-11-01 ~09:36 UTC. Read-only remote inspection; local synthetic checks only.
Repository: jonathanpratama-boop/KOD-Machine. Default branch: claude/idx-signals-test-repo-ds0jw7.
Pinned inspected HEAD: 48d18b8ecae67bdeeb07a47f1772903a5381782b.

## Bottom line

ETH SMA10/40 is a promising historical long/flat candidate, not demonstrated independent or prospective trading alpha. BTC SMA10/40 is WEAK under the registered gate. The report has factual contradictions, previously disclosed implementation deviations, and additional reproducible code defects. Do not use this audit as authority to rerun consumed/previously sealed data or to modify the remote.

## Material findings

1. **eToro claim reverses its own numbers.** `backtests/RESULT.md:21-24` and `FRESH_EYES_VERDICT.md` say the SMA rule no longer beats buy-and-hold on Sharpe for either coin at eToro costs. Published ETH SMA10/40 actually exceeds both gates in BOTH periods: dev Sharpe 1.132 vs 0.764 and DD −69.12% vs −93.97%; validation Sharpe 0.932 vs 0.653 and DD −42.26% vs −67.55%. BTC validation is 0.854 vs 1.162. This invalidates the specific claim that costs force a venue switch; it does not establish live profitability on either venue.

2. **Point-in-time T3 universe has a future-lifetime filter.** `run_t2_t3_t4.py:70` excludes series with fewer than 100 total loaded bars, although the frozen eligibility gate is 90. Synthetic test appending a 100th bar on 2010-04-10 changes the already-past 2010-04-05 universe from 20 to 21. Historical effect unmeasured. Remove the total-lifetime filter in a successor implementation; eligibility must be determined from the prefix available at each decision.

3. **Drawdown omits starting capital.** `lib.py:118-123` sets the running high-water mark from first post-return wealth, not initial wealth 1. Synthetic returns [-60%,+10%] report MaxDD 0%, correctly −60%. Historical effect unmeasured. Include initial wealth before cumulative maximum and test first-day losses.

4. **T3 transaction costs ignore weight drift.** `run_t2_t3_t4.py:118-120` compares new target weights to prior target weights, not actual pretrade holdings/NAV. Two retained equally weighted names with unequal returns are assigned zero rebalance cost despite requiring trades to restore equal weights. Synthetic fixture reproduces. Funding is also summed against initial weights rather than explicit position notional at each settlement; hedge/margin accounting is absent. Preserve originals; successor needs a holdings/cash accounting model.

5. **Known T3/T4 defects remain in published code/JSON.** `AUDIT.md` discloses frozen zero-volume post-delisting bars and T4a being a subset of an already-blocked z2 run. `run_t2_t3_t4.py:173-195` still implements that T4 selection; a synthetic z2 event followed by z3 event reproduces the lost z3 signal. Corrected historical summaries exist in prose only; the separate auditor's scratch code/results are not published in this folder. I did not reproduce its raw-data correction runs. Declaring these defects verdict-preserving relies on that audit, not this independent replication. Explicit known settlement/delisting handling is needed; retroactively choosing a last close does not guarantee an executable fill.

6. **T3 annual sign table is wrong.** `RESULT.md:52-53` says 29%/43%; aggregateJSON annual signs and `share_years_positive` give 3/7=42.9% long-short and 4/7=57.1% long-only. Both still fail the 70% gate.

7. **Historical validation is not untouched confirmation.** The protocol was frozen on 2026-11-01 after its entire 2017–Sep2026 history existed and explicitly acknowledges previously consumed 2024+ data. Its statement that this is a 'genuine out-of-time check' should distinguish a chronological retrospective split from a clean prospective/untouched confirmation. Rules may be causal and literature-chosen, yet winner selection and inference remain exposed to prior knowledge and multiple comparisons. The report's two PASSes are correlated ETH variants; BTC SMA is WEAK. T4 side-specific gates also create more comparisons than a simple count of twelve rule variants conveys.

8. **Lab-history premise is false.** `US_INSIDER_BUY/PROTOCOL.md:48` and `SLOW_10K/PROTOCOL.md:38` both specify primary 60-session holds, with 20/120 descriptive holds. SLOW_10K line11 specifies a 3%, 60-session spread gate. These directly contradict the new protocol/verdict claim that forty-odd prior tests all sought +30% within 1–5 sessions. Reframe as separate hypotheses, not a disproven all-one-class history.

9. **Exit conclusions exceed the experiment.** T5 tests four daily-close/next-open policies on Donchian entries for two assets, not all trailing-stop designs. Fixed-stop reference is the signal close instead of execution open (`run_t1_t5.py:37,43`, already disclosed in the source audit). Time exits can immediately reenter on a contemporaneous breakout (`:38-43`). The experiment supports only the particular four policies tested; 'never a tight trail' or a general superiority claim is not established.

## Positives independently verified

- Correct one-bar target shift and open-to-open attribution, with entry and exit side charges, on a six-bar synthetic fixture.
- Seven T1/T5 signal constructors are prefix-causal on 600 synthetic bars; SMA 40/SMA 200 warmups remain flat until enough history.
- All eight T1 PASS/WEAK/FAIL labels exactly recompute from the published rounded aggregates.
- T1 aggregate CAGR/total/yearly compounding are internally consistent within rounding tolerance.
- Frozen protocol/PINS bytes are unchanged between 5b3d7c2cb785ecd2b43c8a034e8128d3f760caba and inspected HEAD. Protocol SHA256 matches 177e7ccd3ee26b8ecfbeff34d059b43d32bc55cd992cdb64ad792ebe8a170173.
- Git history puts protocol commit 08:46:05Z before engine/results 0282666 at 09:06:28Z, then audit/report e6a6b5f at 09:26:14Z. This verifies commit order and integrity, not that no calculations had occurred before the freeze.
- Spot 1d manifest metadata contains 963 records, fetched 08:43:49–08:44:13Z, with BTC/ETH archives ending 2026-09. This supports the disclosed lack of October data; underlying bars were not opened. T1 aggregate validation has 1368 return days, consistent with 2023-01-01..2026-09-29.

## Minimal repair without overwriting frozen originals

1. Append an errata document with exact report corrections and candidate-not-confirmed classification; preserve the frozen protocol, original JSON and report versions.
2. Add a versioned successor implementation plus synthetic regression tests for initial-equity DD, prefix-only universe eligibility, drift-adjusted turnover, independent threshold sampling, missing/delisted inputs and explicit cost conventions.
3. Publish source and machine-readable artifacts for any already-performed corrections, clearly separating original vs corrected results and all protocol deviations. No new historical outcome run is authorized by this audit.
4. Register prospective evaluation of the ACTUAL portfolio/risk/execution contract separately. Per-coin 0/1 SMA results do not validate volatility targeting, pooled BTC/ETH allocation, caps or kill rules.

## Verification boundaries

No raw 2024+ datasets/bars read; no market outcome backtest rerun; no trades, credentials, remote changes, CI dispatch or external messages. Only source code, documents, aggregate JSON, manifest metadata and synthetic fixtures were inspected. Historical corrected T3/T4 values, placebo distributions, real-data signal causality and published empirical Sharpe/DD are not independently reproduced here. The code and aggregate checks do not prove live profitability or execution feasibility.

Local reproducibility: `python fresh_eyes_audit_20261101/synthetic_checks.py` writes `synthetic_results.json`. It imports the inspected source functions but monkeypatches all data loaders for synthetic fixtures; it never invokes live data fetching.

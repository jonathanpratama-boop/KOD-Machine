# Dashboard source refresh and completed supplement

Owner-directed repair, 13 November 2026. Default base b836c8d516275d37b6dee3f6990d206b15868278.

The published dashboard refreshed cloud results while carrying an old research snapshot. The source build now runs hourly in a separate service, records each source revision, and preserves the previous snapshot and its original date on failure. The page retains its single-page layout and displays separate research and cloud clocks. The corrected paper-book section copies the authoritative published table, with missing results shown as unavailable rather than zero.

The existing supplementary collector had actually completed all 196 slots on 9 November. Its publication was stale after a reporting timeout. The full frozen combined verifier completed in 74.73 seconds: 224/224 combined references (196 supplementary plus 28 original), zero issues, and 6,750 complete unique minute bars per coin with no gaps or conflicts. The terminal report was published through its existing backup writer at supplement-30m-v1 commit 3bde2f4e7849df6d8e579b14daf9baa1304d510c. This does not mean the ongoing R2 experiment has complete historical coverage.

## Required review

1. Independent tests: a separate agent authored refresh, failure preservation, source clock, optional branch, empty-data, corrected-table and publication-throttle regressions. All 25 refresh/publication tests pass. They now run in CI. Pinned ruff passes.
2. Real input: the builder successfully read current KOD/default and named research branches; the first actual publication c27a6cefa45686b6f889ef857b565467ac448d16 contains 62 studies and source b836c8d. The separately published supplement was verified against all frozen raw files, not only a health summary.
3. Look-ahead: these are display and publication fixes. Each source date is retained, corrected results are labeled as later evidence, and no signal, entry, exit or frozen outcome is changed.
4. Architect review: owner-directed Codex integration, separate adversarial test review, and all required checks on the final candidate before merge.
5. Trading relevance: the user can see actual research progress and corrections. Freshness and completed data collection are not evidence of profit.
6. Failure reporting: failed builds retain last good data and publish STALE with error and original source time. Missing optional studies are shown individually. External R2 stopped-alert delivery remains unverified; this repair sends no synthetic notification.

## Deployment

The hourly source service and existing publisher were updated after independent review. A real publication was observed with distinct source time 07:51:37Z and cloud time 07:51:55Z. The main R2 collector remained active with the same PID 95200 throughout. No collector limit, quota, protocol, schedule, or execution rule was changed. The source refresh will be forced once after the split-assessment merge so the corrected results are visible.

The imported dashboard files retain source provenance in tools/status/IMPORT_PROVENANCE.json. Raw market-response evidence stays outside public Git according to the existing data-retention convention.

## Structured acceptance answers

The answers below provide the repository-required fields for the evidence described above.

## Q1.

Answer: yes
Evidence: Independent reviewer authored six evidence-continuity cases before the repair; 215 targeted split tests passed. Dashboard parser and publication regressions were separately authored and all 30 pass.

## Q2.

Answer: yes
Evidence: Saved real split fixtures plus 164 current responses verified against their manifest. The actual published paper-book fragment, live source build, and all supplement captures were checked; details are in handoff/evidence/2026-11-13-split-closeout/.

## Q3.

Answer: n.a.
Evidence: This merge repairs measurement and publication, with no new trading study. The corrected view explicitly uses later evidence; historical cutoff views retain their original clocks and frozen outcomes are unchanged.

## Q4.

Answer: yes
Architect: Codex (Astra), owner-directed integration on 13 November 2026
Evidence: Owner explicitly requested Codex to perform the repair and integration. Independent acceptance verified all 366 timestamp receipts and all 12 report rows; all required PR checks passed on 435100c7a05a22e84f26d1c2f9581a1d834396c6.

## Q5.

Answer: no
Evidence: No live allocation is proposed. Corrected spike outcomes remain negative in a small sample. Accurate split labels, visible source dates and actual results improve the owner's research decision; they do not establish profitable execution.

## Q6.

Answer: no
Evidence: Build failures retain the previous snapshot and show STALE with the error; incomplete inputs remain visible. External R2 stopped-alert delivery is still unverified, and no notification receipt is claimed.

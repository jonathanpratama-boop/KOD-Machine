# Development reader check, 16 November 2026

**Decision: hold the unattended reader.** The repaired adapter passed five controls, but neither complete real-disclosure pair produced a correct, source-bound extraction. The API is connected; extraction reliability is not established. No new paper strategy or scheduled model job was started. The existing cloud timing study continues separately.

## What was tested

Seven development cases: two complete real company-disclosure pairs, four fictional controls, and one previously inspected headerless-excerpt control. Expected facts and source hashes were recorded before the calls. These are inspected development data, not an untouched validation sample. Source preparation and review were supervised by Codex, not independently reviewed by another agent or a person.

- Ribbon: complete July and October press-release bodies, all financial tables and footnotes. Original HTML retained; rendering preserves column positions, including the quarterly versus full-year split.
- Mattel: complete February and April release PDFs. Ordinary PDF text extraction omitted the guidance tables because they were images. All pages were then read with local OCR, observations/coordinates retained, and the relevant tables visually checked against the PDF pages.
- Fictional controls: clear revision, unchanged forecast, missing operating profit with distracting EBITDA/net income, and an accounting-definition change.
- Headerless control: missing currency/scale and ambiguous extra numbers must not be guessed from issuer identity or the old golden labels.

Each case received one attempt per code version. The second development pass used the same source packets and expected facts after the first pass failed. Both versions, requests, first responses and usage remain retained. No response was silently repaired, replaced or counted as an independent event.

## Results

| Case | First pass | After focused repair |
| --- | --- | --- |
| Ribbon complete disclosures | Failed | Failed |
| Mattel complete disclosures / accounting recast | Failed | Failed |
| Fictional clear revision | Failed | Passed |
| Fictional unchanged forecast | Failed | Passed |
| Fictional missing operating profit | Passed | Passed |
| Fictional accounting-definition change | Failed | Passed |
| Headerless source control | Failed | Passed |

**1/7 then 5/7. The real-company result is 0/2 in both passes.** Five passing controls are not an estimate of production accuracy. The adapter accepted three bound candidates in the first pass, but two were semantically wrong. This confirms that numeric source binding alone does not certify interpretation. All outputs remained below the existing fact-qualification gate.

The second Ribbon response still omitted operating profit, copied the wrong spread and supplied reconstructed rather than exact source quotes. Mattel's second response found the operating-profit ranges but rewrote their context quotes and did not identify the prior accounting definition. Both were rejected; neither is a usable automated observation.

## Repairs and checks

The original schema allowed contradictory point/center/range fields. Each numeric form now has a separate schema alternative: required evidence is non-null and unused slots must be null. Period-kind and accounting-basis codes are also constrained to supported values.

The transport had alphabetically sorted schema keys, placing `center` before `form`. It now preserves schema order and retains the exact wire request with its own hash. The second pass also used explicit low reasoning effort and clearer complete-number examples. These changes were made together; the improvement cannot be attributed to any single change.

The local binder also rejects using the same source number as both a center and its spread. It continues to reject invented/ambiguous quotes and partial numeric tokens. It does not relax evidence checks to make the model pass.

Validation: **61 targeted tests passed**: 31 existing independently authored fact tests, 23 existing independently authored mocked reader tests, and seven new regressions written alongside this repair. Changed Python passed Ruff. The new tests are not independent validation.

Fourteen API calls in these two passes used 219,547 input tokens and 7,408 output tokens. Estimated list-price usage was **$0.1871**, accounting for returned cached-token usage. This is a token-based estimate, not an invoice. The earlier one-call connection test is separate and is not included. [Pinned model pricing reference](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

## A separately checked source comparison

This is a **supervised table extraction by Codex**, not a passing model output and not a qualified trading signal.

| Ribbon full-year 2026 outlook | July release | October release |
| --- | ---: | ---: |
| Revenue midpoint, USD millions | 825 | 814 |
| Stated revenue spread, USD millions | +/-15 | +/-7 |
| GAAP operating profit/loss, USD millions | -9.8 | -18.8 |
| Implied operating margin, midpoint convention | -1.188% | -2.310% |

Revenue midpoint decreased 1.33%; implied operating margin decreased 1.12 percentage points. The operating-loss figures are the GAAP reconciliation row, not the EBITDA total. The compared annual period ends 31 December 2026. This shows a weaker forecast in the supplied pair; it says nothing about subsequent returns or whether the market missed it.

Sources: [July 28 release](https://www.prnewswire.com/news-releases/ribbon-communications-inc-reports-second-quarter-2026-financial-results-302836894.html), [October 27 release](https://www.prnewswire.com/news-releases/ribbon-communications-inc-reports-third-quarter-2026-financial-results-302921179.html). Complete intervening-prior history, full fiscal-period identity and perimeter comparability remain unqualified. The supervised record retains the source spans and unknown attestations; it was not admitted to a ledger or promoted to FACTS_READY.

Mattel's accounting control uses [the prior release PDF](https://s21.q4cdn.com/605014885/files/doc_financials/2025/q4/Mattel-Reports-Fourth-Quarter-2025-Financial-Results.pdf) and [the recast release PDF](https://s21.q4cdn.com/605014885/files/doc_financials/2026/q1/Mattel-Reports-First-Quarter-2026-Financial-Results.pdf). Original files, rendered/OCR sources, both model-response sets and the supervised Ribbon comparison remain in the owner's local evaluation folder; they are not bulk-published in this public repository. [Machine-readable evaluation receipt](DEVELOPMENT_EVAL_20261116.json) contains expectations, hashes, counts, usage and the limitations.

## Next decision

Keep the reader in supervised development. The next repair should target selecting existing table-cell evidence instead of asking the model to reproduce long formatted quotes. It must still verify the correct year, metric, units and accounting definition; making quote matching easier alone would not fix Ribbon's semantic errors. A reliable complete-source result, prior-history handling and fair non-LLM comparisons are still needed before freezing a prospective trading test. No price test or new dashboard is justified by this check.

Read-only cloud verification at 09:12:57 UTC found R2 RUNNING with the same process and restart count as after the earlier repair. Its one independent event and original gaps were preserved. No cloud configuration changed during this reader evaluation.

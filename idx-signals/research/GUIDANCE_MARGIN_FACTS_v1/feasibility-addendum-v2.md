# Source-feasibility addendum: corrected hash sample

16 November 2026. This addendum corrects the initial Phase 1 stopping decision. It preserves the original report and all observations. No price series, forward returns, sealed outcomes, trades or paid model runs were requested.

## Correction

The first sample used the oldest 20 CIKs. Its zero among 17 read releases was a source-bounded observation, not adequate evidence to terminate the wider feasibility check. My recommendation to stop Phase 1 there was premature. A reviewer identified that selection problem; the parent authorized one corrected, fixed 40-issuer hash sample before retrieval. There was no search over sampling salts, no replacement of inconvenient issuers and no expansion after this sample.

The original seven-issuer cohort is contained within the original 20, not additional evidence. The corrected 40 exclude those original 20. Search-selected Mobileye/Garmin/Mattel/Gildan fixtures remain outside all rate calculations.

## Corrected evidence

The first half is in `census-v2-first20.json`; the second half is in `census-v2-last20.json`. Combined roster identities were checked against `source-census-v2-roster.json`.

| Measure | First 20 | Last 20 | Corrected sample |
|---|---:|---:|---:|
| Selected issuers, none replaced | 20 | 20 | 40 |
| In-window earnings releases found and read | 13 | 19 | 32 |
| Earnings enumeration incomplete / calendar-only status | 7 | 1 | 8 |
| Explicit as-reported revenue + operating-profit pairs reconstructed | 1 | 1 | 2 |
| Component-derived pair, outside the explicit-pair count | 0 | 1 | 1 |
| Fully admitted live research events | 0 | 0 | 0 |

The explicit pairs are **not two clean eligible signals**. KTOS has a changed consolidation perimeter and unresolved latest-prior completeness. RBBN has unresolved latest-prior completeness and no historical KOD receipt. The observed source yield is two explicit as-reported pairs among 32 read releases (6.25%); it is not an estimate of profitable signals, all-market coverage or a yearly event rate. Eight unresolved issuer histories cannot be treated as negative cases.

The sample inherits the historical E10 universe's selection, survival and liquidity limits. The six-week window falls in earnings season. It provides a materially better availability check than the oldest-CIK sample, but does not establish a dependable live arrival rate.

## What the numbers actually expose

**Kratos, 5 November:** the headline emphasizes higher guidance and EBITDA. The detailed table gives FY2026 revenue of $1,780–1,810m and GAAP operating income of $2–7m. The 4 August table gave revenue of $1,750–1,810m and operating income of $16–22m. Revenue midpoint rises 0.8427%; implied operating margin falls from 1.0674% to 0.2507%, a decline of 0.8167 percentage points. An extractor reading only the headline or the EBITDA row would miss this disagreement.

That is a useful source fact, not a trade. The company acquired Jetset on 9 October. Forecast amortization changes from $43–46m to $55–58m and stock compensation from $60–64m to $66–68m. No complete constant-perimeter or causal bridge was verified. Therefore this cannot pass the unchanged-perimeter rule merely because both rows say GAAP. Complete intervening-guidance enumeration and historical first receipt also remain unknown. [November SEC exhibit](https://www.sec.gov/Archives/edgar/data/1069258/000106925826000085/ktos202609278kexhibit991.htm), [August SEC exhibit](https://www.sec.gov/Archives/edgar/data/1069258/000106925826000075/ktos202606288kexhibit991.htm), [acquisition disclosure](https://www.sec.gov/Archives/edgar/data/1069258/000162828026065829/kratos-424b3october2026.htm).

**Ribbon, 27 October:** the other reviewer reconstructed explicit GAAP FY2026 operating-loss forecasts in the reconciliation, alongside revenue guidance. Revenue midpoint falls from $825m to $814m; operating loss worsens from $9.8m to $18.8m. This is a source-positive comparison with prior completeness still provisional. It is not evidence that the market overlooked it. Details and primary URLs are in the second-half record.

**Adeia, 2 November:** complete forecast revenue and operating-expense rows permit an accounting identity, giving operating-profit midpoints $115m previously and $109m currently. This is kept separate because the frozen source definition required an explicit operating-profit/margin forecast. It is not silently added to the strict sample.

**Oracle, 28 October:** an investor-day release contains FY2030 revenue of $225bn-plus and non-GAAP operating margin of 40%-plus. This was recorded despite not being an earnings release. Open-ended thresholds and an unbound prior are not midpoint revisions. It remains a source-labelling ambiguity, not an invented zero or an accepted signal.

## Unresolved first-half histories

- ACA: exact-CIK filing confirms its 23 October merger and delisting. The acquirer's financial release is not substituted. Pre-merger disclosure enumeration remains incomplete.
- SLNH, HPQ and MDT: issuer notices place their regular earnings after 15 November. These are calendar observations, not exhaustive proof of no interim guidance.
- MOV: the IR archive rendered controls without news entries. The located August release is outside the window. Enumeration remains unknown.
- ORCL: investor-day source inspected; no in-window earnings release located. Complete earnings/interim-event enumeration was not established.
- DVLT: two issuer archive pages cover the window without an earnings release; a management disclosure says the earnings date will be announced. SEC completeness remains unknown.

LZB is the second-half calendar/coverage unknown. All eight remain in the 40-row denominator.

## Implication for the revamp

The correct conclusion is narrower than the initial stop: **the proposed fact is extractable, but a complete, timely, sufficiently frequent live input has not yet been demonstrated.** The corrected sample discovered real source pairs and a concrete extraction failure mode: headline improvements can coexist with weaker GAAP operating-profit guidance. It does not show that this disagreement predicts returns, that an LLM is needed to find it, or that it improves on a mechanical table comparison.

This supports preserving a narrow source-extraction candidate and its rejection rules. It does not support paid unattended research, a live strategy account, a profitability tile or a new broad backtest now. A no-build decision at this point must be described as an operational evidence limit, not a failed economic hypothesis. The parent owns the conditional build/hold decision. The corrected census is complete; no further sample expansion is proposed here.

## Provenance and clocks

The first-half archive contains exact returned web-tool response text under `sources/v2-first20/`, with URLs and line locators. These are not original issuer HTML bytes or proof of historical receipt. Date-only publication evidence was sufficient to locate the releases in the census window. Conference-call time is never used as release time. KTOS's filing-index attempts failed; that failure is recorded.

Second-half records separately preserve newly found issuer-authorized newswire publication clocks. A publisher clock is still not proven earliest public availability and not KOD's historical receipt. No continuous feed completeness, capture delay or end-to-end processing latency was measured.

Search results incidentally included acquisition consideration, financing prices, a few quote snippets and market-data navigation. None was used to choose issuers, assess future returns or classify the hypothesis. The evidence is source-development work, not an untouched validation sample.

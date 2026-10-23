# Analyst-task evaluation: report of 23 October 2026

The task set and scoring rules are described in [README.md](README.md). Both measurements below use the same task file (SHA-256 `752d60a0…`) and the
same runner. Each was run twice on fresh workspaces, and in each case the two runs produced identical outputs:

- **Before the repairs:** the code as it stood when the evaluation was first written (commit `2307e86`). Its output hash is not quoted: that code recorded issuer identities on the wall clock, so its outputs vary
  with the time of day. Its scores do not.
- **After the repairs:** this branch. Answer hash `6370ddb6…`, identical across separate processes and hash seeds; the full record is in
  `results.json`.

## Result

| | Before the repairs | After them |
|---|---|---|
| Tasks passed | 8 of 13 | 9 of 13 |
| The 2 tasks overlapping no development test (T1, T3) | 1 of 2 | 1 of 2 |
| Checks: correct / allowed unavailable / missed / material errors | 75 / 0 / 11 / 6 | 81 / 1 / 10 / 0 |
| Distinct cited observations resolved in the verified SEC responses | 108, all match | 106, all match |
| Time to answer all 13 tasks (one run) | about 4 s | about 4 s |

All six material errors before the repairs were in one task, T4c (Costco's 16-week quarter). After the repairs, every remaining miss is a withheld
answer; no wrong number or status is shown.

## Per task, after the repairs

| Task | Outcome | Answer |
|---|---|---|
| T1 TXN Q3 2024 vs year ago | correct | Revenue 4,151m vs 4,532m: −8.41%. Operating margin −4.31 pp. Net income −20.30%. Diluted EPS −20.54%. Quarter on quarter +8.61%. The year-ago figures are those presented in the same 10-Q. |
| T2 Costco FY2024 profit and cash | correct | Revenue 254,453m. Operating income 9,285m. Cash from operations 153.9% of net income. Capex 1.85% of revenue. Cash from operations minus capex 6,629m. |
| T3 TXN Q3 2024 vs its outlook | **4 missed** | The period, revenue 4,151m and its currency are correct. Missed: diluted EPS (its column period is stated only in a caption), both outlook comparisons (the outlook sentence is in a form KOD does not read), and the caveat that EPS included 3 cents outside the original guidance. |
| T4a NVIDIA capex | **2 missed** | Cash conversion of 87.94% is correct. Capex intensity (2.48%) and cash from operations minus capex (60,853m) are reported missing, because NVIDIA tags capex as `PaymentsToAcquireProductiveAssets`, which KOD does not map. |
| T4b JPMorgan revenue | **2 missed** | Net income −17.42% is correct, from the same 10-Q. Revenue −10.53% is reported missing, because JPMorgan tags quarterly net revenue as `RevenuesNetOfInterestExpense`, which KOD does not map. The operating margin is withheld, but for that revenue gap rather than because a bank reports no operating income, so it counts as a miss. |
| T4c Costco 16-week quarter | correct (repaired; a regression check now) | Q4 FY2024 revenue 79,697m, derived. +0.96% against the 17-week year-ago quarter, shown with "112 vs 119 days; not like for like". Quarter on quarter (16 against 12 weeks) is withheld, with the lengths named. |
| T5 TXN assumption to review | correct | Not triggered at 89.76 per share; triggered at 65.22 after the margin cut. The trace names `operating_margin 0.40 → 0.30`. The runner's separate implementation agrees. |
| T6 Costco decision reopened | correct | The packet reproduces before and after the synthetic amendment, its SHA-256 verifies, and the dossier at its cutoff is unchanged. At 10 March 2025 the latest view shows the amendment. At 1 June 2025 it shows the 10-Q that re-presented 254,453m, and lists the amendment as a revision. |
| T7 JPMorgan Q1 2012 restatement | correct | As first reported: 5,383m and 1.31, with the 10-Q/A revision to 4,924m and 1.19 listed. The latest view shows 4,924m. Before the amendment (1 August 2012) it shows 5,383m and no revision. |
| T8 bank | correct | Business type not supported (SIC 6021). The model and the three cash-flow ratios are not applicable, with the bank named as the reason. |
| T9 Apple split | correct | Diluted EPS +34.4% (1.68 vs the split-adjusted 1.25 in the same 10-Q). Diluted shares −3.96%. |
| H1 hostile release | correct | Q2 2025 revenue CAD 97,433 thousand; net income 9,955 thousand; EPS 0.39. The six-month columns are not used. The year-ago quarter is 85,210 thousand: +14.34%. |
| H2 hostile release | **2 missed** | KOD leaves the period unresolved: its rule is that the release must state the period, or the analyst records it. The columns ("Q2 2025", "Q2 2024") and the year-ago sentence do identify the quarter, so this counts as a miss. With the analyst's period record, revenue CAD 97,433 thousand is correct. The note lists the column figures without calling either current or prior. |

## Repairs made after the first measurement

The T4c failure and an independent four-lens review of the evaluation, its runner, the code and the documentation led to the following repairs. Each
has a regression test in `workstation_tests/test_gate_d.py` or `workstation_tests/test_review_g.py`.

**Week-based fiscal quarters (Costco):**

- Year-to-date figures of 24 and 36 weeks are now inputs, so the 16- or 17-week fourth quarter is derived.
- A fourth quarter the 10-K reports directly (fiscal 2010–2020) is used as reported, with its same-filing year-ago comparative.
- A quarter is never listed twice for one end date.

**Comparisons:**

- Quarter-on-quarter growth across quarters whose lengths differ by more than 15% is withheld, with the lengths named.
- The period-length note and a new note when the two sides use different XBRL concepts now appear wherever the change appears: the dossier page,
  the calculation page, the Markdown export, thesis condition traces and the decision packet. The comparison basis appears on the dossier page, the
  calculation page and the Markdown export, not in thesis traces or packets.

**Other findings of the review:**

- A price correction for the same trading day was chosen by an id hash. The most recently recorded eligible price is now used.
- Reverse valuation could report "solved" outside its tolerance. It now reports `not_converged` in that case.
- A malformed SEC response crashed the filed-history refresh. It is now a failed job.
- One refresh recorded two success jobs; it now records one.
- The last-year-growth suggestion lacked its observations.
- A later rename of the watchlist entry changed an earlier observed-mode dossier. It no longer does.

**A second review round:**

- Costco's reported 16- against 17-week fourth quarters were refused as different period kinds. They now compare, with the length note; the values
  match the raw filings (fiscal 2012–2018).
- Two reported quarters with one end date (a mis-tagged start in one 10-Q) were chosen by input order. Information time was affected: an earlier
  view could differ depending on whether later filings were held. The quarter the year-to-date periods support is now kept. A full-versus-truncated
  fixture sweep of all eight companies (185 cutoffs) gives identical results.
- A price correction could not be reverted, and a later-recorded intraday quote replaced the day's close. Corrections now apply within one series;
  across series, the later-published price is used.
- The refresh failure message said nothing was recorded, although the downloaded bytes are kept. The wording is now accurate.
- The concept note's wording was imprecise; it now names the current and prior concepts.
- The issuer identity was recorded on the wall clock, which made the evaluation's outputs depend on the time of day. It is now recorded on the
  caller's clock.

**A third review round:**

- The duplicate-quarter rule of the second round treated a six- or nine-month gap between year-to-date periods as a quarter that "replaced" a reported
  one, and removed genuine reported quarters with nothing in their place. Texas Instruments' quarter-on-quarter growth at November 2009 (+17.22%),
  Costco's diluted EPS and share-count changes at August 2010, and changes for Apple, JPMorgan, Plug Power and NVIDIA in 2009–2012 became "missing".
  Now only quarter-length spans count as supported, and a reported quarter is removed only when a supported reported quarter or, for an additive
  flow, a derived one takes its place. A sweep of all eight companies at 68 cutoffs in both views against `2307e86` differs only for Costco, and the
  full-versus-truncated sweep is still identical.
- The HTML dossier's subtitle used the current name in observed mode; it now uses the name recorded by the cutoff.
- The refresh failure message no longer says downloaded bytes were kept when none were saved.

## Changes to the task set

Each change corrects an error in an expectation or a check. None was made to match KOD's output.

| Task | First draft | Corrected | Found by |
|---|---|---|---|
| T5 | 85.84 per share | 85.81 for the same inputs (arithmetic slip) | first run |
| T5 | Bridge used cash and cash equivalents only (3,200m) and noncurrent debt only (12,846m) | Cash and short-term investments 7,580m; total long-term debt 13,596m. Expected 89.76 and 65.22 | review |
| T6 | At 1 June 2025 the latest view should show the synthetic 999,999m | The 10-Q filed 2025-03-13 re-presents 254,453m. Checked at 10 March (amendment shown) and 1 June (superseded, listed as a revision) | first run |
| T4a | NVIDIA capex ratios "missing" (the concept stops in 2020) | NVIDIA moved capex to `PaymentsToAcquireProductiveAssets`: 2.48% and 60,853m expected | review |
| T4b | JPMorgan revenue change "missing" | `RevenuesNetOfInterestExpense`: −10.53% expected | review |
| H2 | Expected `PERIOD_UNRESOLVED`, described as a release stating no period | The column labels and the year-ago sentence identify Q2 2025. Expected Q2 2025, with a check of the analyst's period record | review |
| T2, T5, T6, H1, H2 | Not marked as overlapping | Marked, naming the development tests | review |
| T3, T4c, H1, T6 | Weaker checks | Guidance actuals, period and currency; all rows must agree; "not like for like" required; H1 growth; T6 revision listed | review |
| T4b | The operating margin allowed to be "missing" for any reason | No longer allowed: KOD withholds it for a revenue gap, not for the bank reason, so it is a miss (also in the measurement of `2307e86`) | third review |

The runner was also strengthened after the review:
- Allowed outcomes are named per check, and the reason is checked.
- The citation check covers every input and field, and requires the stored responses to match the verified fixtures.
- Every fixture's SHA-256 is enforced.
- Reproducibility hashes every output.
- A task without checks fails.
- The model check implements the full formula.
- CI fails on regressions against `results.json`, and a missing baseline fails unless `--no-baseline` is given.
- Misspelled expectation keys are refused, and a cell or change listed twice is a material error.
- A withholding with a different unavailable status than expected is a miss.
- One run reports reproducibility as not compared.

The first draft's runner also counted history cells reported as `reported` or `derived` as missing; that was fixed before either measurement above.

## Defects found and not repaired

These are the next acceptance work (see `DOSSIER_PROGRESS.md`). They are left unrepaired here so the next measurement of them stays independent.

1. **Release reader coverage (T3).** These release-reader limits are withheld rather than misread:
   - A column period stated only in a caption above the table ("… For Three Months Ended September 30, …") is not linked to the columns.
   - The outlook reader does not recognise "TI's third quarter outlook is for revenue in the range of $3.94 billion to $4.26 billion and earnings per share
     between $1.24 and $1.48."
   - Statements that a result includes items outside the original guidance are not shown next to the comparison.
2. **Concept coverage (T4a, T4b).** `PaymentsToAcquireProductiveAssets` (NVIDIA's capex since November 2020) and `RevenuesNetOfInterestExpense` (bank net
   revenue) are not mapped. Mapping them needs care:
   - The first can include intangibles.
   - The second must not be mixed with `Revenues` inside one derived quarter.
   - The trimmed fixtures must be rebuilt from the full responses.
3. **A fallback basis label (Costco, fiscal 2018).** Concept precedence keeps one revenue concept per period across filings. The year-ago fourth
   quarter therefore comes from the 2017 10-K's `Revenues`, labelled "not presented in the current filing", although the 2018 10-K presents it under
   `RevenueFromContractWithCustomerExcludingAssessedTax`. The value is right; the label is wrong.
4. **A mis-tagged 10-Q (Costco, June 2010).** It tags both quarter starts a week early. The current quarter is now derived (84 days), but the year-ago
   quarter cannot be (its year-to-date periods start on different days), so the change carries a "84 vs 92 days; not like for like" note although both
   quarters are 12 weeks. The value is right; the note is wrong.
5. **Stated-period rule (H2).** KOD will not infer the reported quarter from column labels. Whether it should, when a year-ago sentence corroborates them,
   is an owner decision.

## What this evaluation does not show

- **Scale.** Thirteen tasks are a small sample. The figures describe these tasks, not a general accuracy rate.
- **Independence.** Only two tasks (T1, T3) exercise nothing a development test already covers.
- **Workflow speed.** The time per task measures KOD answering a fully specified question. It does not measure an analyst finding the answer through the
  interface; the browser journey (`workstation_tests/browser_journey.py`) covers that path.

# Analyst-task evaluation: report of 23 October 2026

The task set and scoring rules are described in [README.md](README.md). The full results are in `results.json`:

- tasks file SHA-256 `4c59bf89…`;
- two fresh-workspace runs;
- answer hash `212f54bf…` in both runs.

## Result

| | Before the repair below | After it |
|---|---|---|
| Tasks passed | 11 of 13 | 12 of 13 |
| Tasks not overlapping development tests, passed | 5 of 6 | 5 of 6 |
| Checks: correct / allowed unavailable / missed / material errors | 77 / 0 / 5 / 5 | 83 / 0 / 4 / 0 |
| Citations resolved against the preserved SEC responses | 138, all match | 148, all match |
| Two fresh runs give identical answers | yes | yes |
| Time to answer all 13 tasks (one run) | about 4 s | about 4 s |

Both columns use the same task file and runner. The two corrections described under "Expectation and runner errors" were made before the "before" column
was measured.

## Per task, after the repair

| Task | Outcome | Answer |
|---|---|---|
| T1 TXN Q3 2024 vs year ago | correct | Revenue 4,151m vs 4,532m: −8.41%. Operating margin −4.31 pp. Net income −20.30%. Diluted EPS −20.54%. Quarter on quarter +8.61%. Year-ago figures are taken from the same 10-Q. |
| T2 Costco FY2024 profit and cash | correct | Revenue 254,453m. Operating income 9,285m. Cash from operations 153.9% of net income. Capex 1.85% of revenue. Cash from operations minus capex 6,629m. |
| T3 TXN Q3 2024 vs its outlook | **4 missed, no error** | Revenue 4,151m and net income 1,362m were read correctly. Diluted EPS was not read: its column period is stated only in a caption the parser does not link to the table, so it was withheld and reported as an issue. The outlook sentence ("TI's third quarter outlook is for revenue in the range of …") is not a form the outlook reader knows, so no guidance comparison was made and none was invented. The release's caveat that EPS included a 3-cent benefit outside the original guidance is not shown. |
| T4a NVIDIA capex | correct | Capex intensity and cash from operations minus capex are reported missing; the reason names capex. Cash conversion is 87.94%. |
| T4b JPMorgan revenue | correct | Revenue change is reported missing because the series ends 2014-12-31. Net income Q2 2025 vs Q2 2024 is −17.42%, from the same 10-Q. |
| T4c Costco 16-week quarter | correct (repaired) | Q4 FY2024 revenue is 79,697m, derived. It is +0.96% against the 17-week year-ago quarter, with "112 vs 119 days" shown. Quarter on quarter is +36.2%, with "112 vs 84 days; not like for like" shown. |
| T5 TXN assumption to review | correct | The condition was not triggered at 85.81 per share. After the margin cut it is triggered at 61.27. The trace names `operating_margin 0.40 → 0.30`, and the runner's independent arithmetic agrees. |
| T6 Costco decision reopened | correct | The packet reproduces before and after the synthetic amendment, its SHA-256 verifies, and the dossier at its cutoff is byte-identical. The later views show the amendment and its supersession by the next real 10-Q. |
| T7 JPMorgan Q1 2012 restatement | correct | As reported, 5,383m / 1.31, with the 10-Q/A revision to 4,924m / 1.19 listed. The latest view shows 4,924m. At 1 August 2012, before the amendment, the latest view shows 5,383m and no revision. |
| T8 bank | correct | Business type is not supported (SIC 6021). The model is not applicable, and the three cash-flow ratios are not applicable. |
| T9 Apple split | correct | Diluted EPS +34.4% (1.68 vs the split-adjusted 1.25 in the same 10-Q). Diluted shares −3.96%. |
| H1 hostile release | correct | Q2 2025 revenue is CAD 97,433 thousand; net income 9,955 thousand; EPS 0.39. The six-month columns are not used. The year-ago quarter is 85,210 thousand. |
| H2 hostile release | correct | The period is unresolved and no figures are shown. |

## Defect found and repaired: Costco's 16-week fourth quarter (material error)

The defect appeared at 15 November 2024. The dossier named the quarter ended 2024-05-12 as Costco's latest quarter, although the 10-K for the year ended
2024-09-01 had been filed. It then reported "latest-quarter" revenue growth of +9.07% and +0.12% quarter on quarter. Those figures belong to the third
quarter, so they answered a different question from the one asked.

Cause: Costco counts its year in weeks. Its year-to-date periods are 24 and 36 weeks (168 and 252 days), outside the 6- and 9-month bands the quarter builder
accepted. Its fourth quarter is 16 weeks (17 in a 53-week year). As a result the fourth quarter was never derived.

Repair (`kod/workstation/quarters.py`):

- Year-to-date inputs may be any whole number of weeks between 16 and 40.
- A difference ending a fiscal year may be a quarter of 15 to 18 weeks.
- Stored period identifiers are unchanged.
- The existing period-length note now shows wherever a change is shown: the page, the calculation page and the Markdown export. A Gate D review finding
  said it was only in the JSON.

Regression test: `test_a_sixteen_week_fourth_quarter_is_derived_and_its_length_shown`. Because the repair was made after T4c failed, T4c now serves as a
regression check and no longer measures independent performance.

## Defects found and not repaired (release reader coverage)

T3 shows that a release laid out differently from the development examples can go mostly unread. Nothing wrong is shown, and the issues are listed in the
note:

1. A column period stated only in a caption above the table ("Consolidated Statements of Income For Three Months Ended September 30,") is not linked to the
   columns, so those values are withheld (`COLUMN_DURATION_UNKNOWN`).
2. The outlook reader recognises "outlook for the third quarter of fiscal 2025 …" and similar forms, but not "TI's third quarter outlook is for revenue in
   the range of $3.94 billion to $4.26 billion and earnings per share between $1.24 and $1.48."
3. Statements that the actual result includes items outside the original guidance are not surfaced next to the comparison.

These are left as they are on purpose. A repair tuned to the one release that exposed them would make T3 a development example. They are the next
acceptance task (see `DOSSIER_PROGRESS.md`): extend the reader, then measure it on a new set of releases from issuers it has not seen.

## Expectation and runner errors (corrected, not product defects)

- **T5:** the first draft expected 85.84 per share before the revision. The correct arithmetic gives 85.81. The runner's independent re-implementation of
  the formula and KOD both gave 85.8147.
- **T6:** the first draft expected the latest view on 1 June 2025 to show the synthetic restated revenue. Costco's real 10-Q filed 2025-03-13 re-presents
  fiscal 2024 revenue at 254,453m after the synthetic amendment, so the latest view correctly shows 254,453m. The task now checks that view at 10 March 2025
  (the amendment is shown) and at 1 June 2025 (it has been superseded).
- **Runner:** history cells report `reported` or `derived` rather than `ok`. The first runner counted them as missing. This was fixed before either column
  above was measured.

## What this evaluation does not show

- **Scale.** Thirteen tasks are a small sample. The figures above describe these tasks, not a general accuracy rate.
- **Coverage of releases.** Only one previously unseen issuer's releases were tried (TI), and the result was mostly unreadable. Release coverage beyond the
  development layouts is the main weakness found.
- **Workflow speed.** The time per task measures KOD answering a fully specified question. It does not measure an analyst finding the answer through the
  interface; the browser journey (`workstation_tests/browser_journey.py`) covers that path.
- **Overlap with the development tests.** Seven tasks reuse a mechanism a development test already exercises (the `overlaps_development` field). Six do not.

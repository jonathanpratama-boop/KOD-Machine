# Analyst-task evaluation

A fixed set of analyst questions with expected answers prepared by hand. It is separate from the development tests and from the four demo releases
(NVIDIA, AMD, Apple, Microsoft). The runner asks the questions through the same functions the workstation uses, on a fresh offline workspace. It scores
each answer against the expectation.

    cd kod-machine
    python3 evaluation/run_eval.py --runs 2                  # prints the scored table; compares with results.json
    python3 evaluation/run_eval.py --runs 2 --no-baseline --out evaluation/results.json   # record a new baseline

The run fails (exit status 1) in any of these cases:

- a material error;
- outputs that differ between two fresh runs;
- a task without checks;
- a regression against the recorded baseline `results.json`: a check that was correct or allowed there and is not now;
- a missing baseline, unless `--no-baseline` is given;
- an expectation key the runner does not know (a misspelling would otherwise skip its check).

CI runs it in the workstation job.

No network is used. The inputs are the preserved SEC responses under `examples/companyfacts/` and the two Texas Instruments releases (with their filing
headers) under `fixtures/txn/`. The runner checks every one of those files against the SHA-256 recorded for it, and refuses to run if any differs. The
results of the run described in the report are in [REPORT.md](REPORT.md) and `results.json`.

## Selection

The build instruction names six task types:

| Type | What the analyst asks | Tasks |
|---|---|---|
| 1 | Current vs prior period on a compatible basis | T1 (TXN Q3 2024), T4c (Costco's 16-week quarter), T9 (Apple 4-for-1 split), H1, H2 |
| 2 | Did revenue turn into profit and cash | T2 (Costco FY2024) |
| 3 | Actual vs the company's own earlier outlook | T3 (TXN Q3 2024 vs the outlook in its Q2 release) |
| 4 | Coverage limits, amendments, unsupported businesses | T4a (NVIDIA capex), T4b (JPMorgan revenue), T7 (JPMorgan Q1 2012 restatement), T8 (bank) |
| 5 | An assumption change reaching a thesis condition, with the dependency shown | T5 (TXN) |
| 6 | Reopen an earlier decision exactly as it was, after later data arrives | T6 (Costco, with a synthetic later amendment) |

11 tasks use real filings; H1 and H2 are synthetic releases. T6 adds a synthetic later amendment to real filings.

- **New companies and periods.** No task uses the four demo releases. The two TI releases (T3) were downloaded for this evaluation, and KOD had never
  parsed them before its first run.
- **Overlap is declared, not hidden.** Only T1 and T3 exercise nothing a development test already exercises. Each of the other eleven names, in
  `overlaps_development`, the test that covers the same mechanism, company or cutoff:
  - The development tests already cover the bank rule, a series that stops, a split, unequal period lengths, the assumption trace, packet reproduction,
    and the Gate A release defects.
  - Some overlaps arose after the first run. The repair that T4c led to added a Costco test at T2's and T6's cutoff.
  - The report gives the score of the two non-overlapping tasks separately.
- **Hostile variants.** H1 (dated columns in ascending order, three- and six-month columns side by side, thousands, Canadian dollars) and H2 (no period
  stated in the headline) are synthetic releases. T6 adds a synthetic later 10-K/A. T4c and T9 are real hostile cases: a 16-week fiscal quarter, and a
  4-for-1 split.
- **An unsupported business type.** T8 (JPMorgan, SIC 6021).
- **An amendment and restatement.** T7: JPMorgan's 10-Q/A of 9 August 2012 restated first-quarter 2012 net income from 5,383m to 4,924m.

## Expected answers

Each task's `sources` field cites what the expected answer was read from: the accession, the XBRL concept and the period, or the exact sentence of a
release. The arithmetic was done with Python decimals outside KOD.

The expected answer is what a careful analyst would conclude from the documents. It is not what KOD can do. For example, NVIDIA tags capex, and JPMorgan
tags quarterly net revenue, under concepts KOD does not map. Those concepts are cited from the full SEC responses (identified by `full_response_sha256` in
`examples/companyfacts/SOURCES.json`) because the trimmed fixtures keep only the mapped concepts. So KOD answering "missing" there is a miss, not a
correct answer.

The runner also checks three things beyond the stated values:

- **Citations.** For every supported change in a dossier task, every observation behind it must be in the dossier. Its JSON pointer must then resolve,
  in the stored SEC response, to the same concept, value, accession, form, filing date and period. The stored response must be byte-identical to the
  verified fixture. The report gives the number of distinct observations checked.
- **Model arithmetic.** In T5 the runner computes the per-share values with its own Decimal implementation of the formula in [MODEL.md](../MODEL.md):
  yearly paths, the tax floor, the terminal value and the full equity bridge. It is not imported from KOD.
- **Reproducibility.** The SHA-256 of every output each task produced (dossiers, analyses, reviews, packets, notes) is compared between runs, not only the
  scores.

## Allowed unavailable outcomes

A check may name the statuses KOD may withhold with (`allowed_statuses`) and, where it matters, the words the reason must contain (`reason_contains`).
Withholding for another reason is a material error. Any other withholding is a miss. Examples:
- Costco's quarter-on-quarter growth across a 16-week and a 12-week quarter: withheld, provided the reason names the lengths.
- Every operating-company ratio for a bank (T8), which must be "not applicable", with a reason naming the bank.

## Outcomes and scoring

- **correct**
- **allowed_unavailable:** withheld, with a status and reason the task allows.
- **missed:** withheld or not found, where the documents hold an answer. Withholding with another unavailable status than the expected one (for example "missing" where "not applicable" is
  expected) is also a miss.
- **material_error:** any of these:
  - a wrong value or status presented as an answer;
  - an answer given where none should be;
  - a withholding for a reason other than the allowed one;
  - a citation that does not resolve;
  - a cell or change listed twice for one period;
  - a task that crashed or has no checks.

A task passes when every check is correct or allowed unavailable. The runner records the time each task takes.

## Rules for changing this set

- **Expected answers change only for an error in the expectation itself, never because KOD answers differently.** Every such change is listed in the
  report under "Changes to the task set".
- **A task whose failure led to a code repair no longer measures independent performance.** It stays as a regression check and is marked as overlapping
  development. The next independent measurement needs new tasks prepared before any code change.

# Analyst-task evaluation

A fixed set of analyst questions with expected answers prepared by hand. It is separate from the development tests and from the four demo releases (NVIDIA, AMD,
Apple, Microsoft). The runner asks the questions through the same functions the workstation uses, on a fresh offline workspace. It scores each answer
against the expectation.

    cd kod-machine
    python3 evaluation/run_eval.py --runs 2                 # prints the scored table; exit 1 on any material error or a non-reproducible answer
    python3 evaluation/run_eval.py --runs 2 --out evaluation/results.json

No network is used. The inputs are the preserved SEC responses under `examples/companyfacts/` and the two Texas Instruments releases under
`fixtures/txn/`; `fixtures/txn/SOURCES.json` records their URLs, sizes, SHA-256 and retrieval times. The runner refuses a fixture whose bytes no longer
match. Results of the run described in the report are in [REPORT.md](REPORT.md) and `results.json`.

## Selection

The build instruction names six task types. Each type has at least one task, and some have several:

| Type | What the analyst asks | Tasks |
|---|---|---|
| 1 | Current vs prior period on a compatible basis | T1 (TXN Q3 2024), T4c (Costco's 16-week quarter), T9 (Apple 4-for-1 split), H1, H2 |
| 2 | Did revenue turn into profit and cash | T2 (Costco FY2024) |
| 3 | Actual vs the company's own earlier outlook | T3 (TXN Q3 2024 vs the outlook in its Q2 release) |
| 4 | What cannot be answered, and why; amendments; unsupported businesses | T4a (NVIDIA capex), T4b (JPMorgan revenue), T7 (JPMorgan Q1 2012 restatement), T8 (bank) |
| 5 | An assumption change reaching a thesis condition, with the dependency shown | T5 (TXN) |
| 6 | Reopen an earlier decision exactly as it was, after later data arrives | T6 (Costco, with a synthetic later amendment) |

How the tasks were chosen:

- **New companies and periods.** No task uses the four demo releases. The development tests use TXN only for 2009–2010 capex and Costco only for 2014–2015
  revenue concepts. T1, T2, T3, T5 and T6 use periods and documents no development test reads. The two TI releases (T3) were downloaded for this
  evaluation and had never been parsed by KOD before its first run.
- **Overlap is declared, not hidden.** Some real cases reuse a mechanism a development test already exercises at another company or date. Examples: the
  bank rule, a series that stops, a split, unequal period lengths. Each such task names the test in `overlaps_development`, and the report gives its
  score separately.
- **Hostile variants.** H1 and H2 are synthetic releases built to break specific rules. H1 has dated columns in ascending order, three- and six-month
  columns side by side, a thousands scale and Canadian dollars. H2 states no period except a year-ago comparison. T6 adds a synthetic later 10-K/A that
  restates a figure fourfold. T4c and T9 are real hostile cases: a 16-week fiscal quarter, and a 4-for-1 split.
- **An unsupported business type.** T8 (JPMorgan, SIC 6021).
- **An amendment and restatement.** T7: JPMorgan's 10-Q/A of 9 August 2012 restated first-quarter 2012 net income from 5,383m to 4,924m. T6 adds a
  synthetic one.

## Expected answers

Each task's `sources` field cites what the expected answer was read from: the accession, the XBRL concept and the period, or the exact sentence of a
release. The arithmetic was done with Python decimals outside KOD. The expected answer is what a careful analyst would conclude from the cited documents. It
is not what KOD happens to output. Where KOD's documented policy is the careful answer, the policy is what is expected. H2 is an example: a release that
does not state its period gets no figures until the analyst records the period.

The runner also checks two things beyond the stated values:

- **Citations.** Every observation behind every supported change is resolved by its JSON pointer in the stored SEC response. The value, accession and
  period end must match. 148 citations are checked per run.
- **Model arithmetic.** In T5 the runner computes the per-share value again with its own implementation of the formula in [MODEL.md](../MODEL.md).
  This is written separately and not imported from KOD.

## Allowed unavailable outcomes

`allowed_unavailable` in each task lists what KOD may withhold without being wrong. Examples: NVIDIA's capex ratios (the concept stops in 2020),
JPMorgan's revenue change (the concept stops in 2014), every operating-company ratio for a bank, and every figure of a release with no stated period. T4c
also allows Costco's quarter-on-quarter and year-on-year growth to be withheld as not like for like, provided the reason names the period lengths.

## Outcomes and scoring

Each check has one of four outcomes:

- **correct**
- **allowed_unavailable:** withheld, and the task allows it.
- **missed:** withheld, or not found, where the documents hold an answer.
- **material_error:** a wrong number or status presented as an answer, or an answer given where none should be.

A task passes when every check is correct or allowed unavailable. Each run records the time per task. Two runs on separate fresh workspaces must produce
answers with the same SHA-256 (timings excluded).

## Rules for changing this set

- **Expected answers change only for an error in the expectation itself, never because KOD answers differently.** The report records each such change with
  its reason.
- **A task whose failure led to a code repair no longer measures independent performance.** It stays in the set as a regression check, and the report says
  so. The next independent measurement needs new tasks.

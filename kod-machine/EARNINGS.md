# Earnings research note

Give KOD a company and its official earnings press release; get back a readable Markdown note whose every figure points to the exact table row it came from. This builds on the [analyst workbench](WORKBENCH.md) and uses its cutoff, citation and consensus rules. It needs only Python's standard library. It is a research aid: no recommendation, no forecast, no entry permission, and it never opens the KOD database, ledger or registry.

## Run it

From `kod-machine/`, on the frozen real example (NVIDIA, third quarter of fiscal 2025, released 2024-11-20, with the previous quarter's release for comparison):

```sh
python3 -m kod.earnings --company "NVIDIA Corporation" --ticker NVDA --venue XNAS \
  --document examples/earnings_demo/current_q3fy25pr.htm \
  --source-url https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm \
  --sec-headers examples/earnings_demo/current_0001045810-24-000315-index-headers.html \
  --retrieved-at 2026-10-22T14:40:11Z \
  --comparison-document examples/earnings_demo/prior_q2fy25pr.htm \
  --comparison-source-url https://www.sec.gov/Archives/edgar/data/1045810/000104581024000262/q2fy25pr.htm \
  --comparison-sec-headers examples/earnings_demo/prior_0001045810-24-000262-index-headers.html \
  --comparison-retrieved-at 2026-10-22T14:40:12Z \
  --as-of 2024-11-20T22:00:00Z --mode public --out-dir examples/earnings_demo/output
```

The result, `examples/earnings_demo/output/note.md` (readable) and `note.json` (the same facts plus the workbench report), is committed. Re-running reproduces it byte for byte.

For a live filing, give the SEC URL and your contact instead of local files (the contact goes only into the request header and is never stored):

```sh
KOD_SEC_CONTACT=you@example.com python3 -m kod.earnings --company "NVIDIA Corporation" --ticker NVDA \
  --document https://www.sec.gov/Archives/edgar/data/<cik>/<accession-no-dashes>/<exhibit-99-1>.htm \
  --comparison-document https://www.sec.gov/Archives/edgar/data/<cik>/<earlier-accession>/<earlier-exhibit>.htm
```

The files are saved under `<out-dir>/sources/`, the SEC acceptance time is read from the filing's own header, and the retrieval time is the moment of the run. Without `--as-of` the cutoff is now, in `observed` mode.

## What you supply

| Option | Meaning |
|---|---|
| `--company`, `--ticker`, `--venue` | identity shown in the note (venue is optional) |
| `--document` | the earnings release: a local `.htm` file or an https URL |
| `--source-url` | public URL of a local file, used as its citation |
| `--published-at` / `--sec-headers` | publication time: an explicit ISO time, or the SEC `-index-headers.html` file (acceptance time). If neither is available the time is **unknown**; download time is never substituted |
| `--retrieved-at` | when you actually downloaded a local file. Omit it and the load time is used and labelled as such. Never backdate |
| `--comparison-document` (+ the same `--comparison-*` options) | an earlier release whose outlook covers this period |
| `--consensus` | optional JSON list of dated consensus estimates (below) |
| `--as-of`, `--mode` | information cutoff. `observed` also requires retrieval before the cutoff; `public` is a historical reconstruction by publication time only and is labelled so |
| `--currency` | record the reporting currency (ISO 4217 code) where the release does not state it. A statement in the release that contradicts it is reported as a conflict and the affected figures get no currency |
| `--period` | record the reported quarter (one of the release's own column labels) where the release does not state it. It never overrules the release: a contradicting record withholds the result |
| `--decision-note` | why the `--currency` / `--period` record is right; kept with the note as the analyst's provenance |

## What is supported

One document type: an official earnings press release in **HTML** (for SEC filers, the 8-K Exhibit 99.1 `.htm`). Three table layouts are read, each checked on a real release (NVIDIA, AMD, Apple, Microsoft; frozen under `examples/earnings_demo/`):

- **Period-labelled columns**, such as `Q3 FY25 | Q2 FY25 | Q3 FY24 | Q/Q | Y/Y` (NVIDIA) or `Q3 2024 | Q3 2023 | Y/Y | Q2 2024 | Q/Q` (AMD). Column meaning always comes from the header cells, one to one with the row's values; the basis (`GAAP` / `Non-GAAP`) from a heading in or just above the table.
- **Dated columns under a duration heading**, such as `Three Months Ended` / `Twelve Months Ended` over `September 28, 2024 | September 30, 2023 | ...` (Apple). Quarter and 12-month columns are never compared with each other.
- **Periods down the rows, metrics across the top** (Microsoft's summary: rows `2024 As Reported (GAAP)`, columns Revenue, Operating Income, Net Income, Diluted EPS).

Recognised rows: revenue (net sales), gross margin (%), operating expenses, operating income, net income, diluted EPS. A basis the release does not state is `UNSTATED`, not guessed. The company outlook is read from two wordings: "Revenue is expected to be $X billion, plus or minus Y%" with "GAAP and non-GAAP <gross margins|operating expenses> are expected to be A and B, respectively" (NVIDIA), and "For the <n>th quarter of <year>, <Company> expects revenue to be approximately $X billion, plus or minus $Y million" with "<Non-GAAP|GAAP> gross margin is expected to be approximately Z%" (AMD). An earlier release that is supplied also fills a sequential prior-quarter comparison the current release does not print, labelled with that source. Anything else is left unknown and listed under "Conflicts, unknowns and limitations": PDFs, other table layouts, segment tables, reconciliations and management commentary are not read; unsupported input stops with a message saying what to provide. Rebuild the extra examples with `python3 examples/earnings_demo/more/regenerate.py`.

## How the current period, columns and currency are decided

- **Table geometry.** Each table is laid out as a grid that honours `rowspan`/`colspan`; overlapping or out-of-bounds spans reject the table (listed under limitations), never guessed. A value is read from the column its cell actually occupies, and its evidence names the original cells (`row`, `cell`, covered `columns`) of the value, its header and its row label. A duration heading (`Three Months Ended`, `Years Ended`, `Nine months ended`) applies only to the columns beneath its own span and only within its own header block. Rows of plain counts are never taken as year headers. Percent cells are never amounts. Only span-free tables whose value count matches may fall back to printed order, flagged `ALIGNED_BY_PRINTED_ORDER`.
- **Current period.** The quarter comes from the release's own statement: a headline such as "Reports Third Quarter 2024 Results" (or a fiscal form such as "Third Quarter Fiscal 2025"), or a "quarter ended <date>" sentence, matched to a column. Year-ago and comparison sentences ("compared with third quarter 2023", "up from ... in the quarter ended September 30, 2023") and future sentences ("fourth quarter results will be released on ...") are ignored. Column order never matters. If the release does not establish the quarter, or its signals conflict, the result is `PERIOD_UNRESOLVED`: no figures, comparisons or guidance are shown until you record `--period`.
- **Comparisons.** A prior-period comparison needs a period that is genuinely earlier and of the same duration, basis, unit and currency. A future column is never called prior; a quarter is never compared with a year.
- **Reporting currency.** In order of scope: a currency symbol in the cell (`C$`, `€`, `RMB`), the table's caption or symbols, a document statement ("All amounts are in Canadian dollars"), then your `--currency`. A currency merely mentioned (notes denominated in euros, sales in Canadian dollars) is not a reporting statement. A bare `$` with no statement is assumed USD and flagged `ASSUMED_FROM_$_SIGN`; `¥` alone is ambiguous and leaves the currency unresolved. Figures in different or unknown currencies are never compared. The security's listing currency is never used.
- **Cutoff.** If the cutoff precedes the release's availability, nothing parsed from it appears, not even its period label.

## The note

Facts first (the release's headline paragraph quoted verbatim, then a table: value, unit, basis, period and the exact table row), then three comparisons that are never mixed:

- **A. Actual vs prior-period actual**: the comparative columns of the same release, checked against the changes the release itself prints, and against the earlier release if supplied.
- **B. Actual vs earlier company guidance**: the comparison release's outlook for this period; metric, basis, period, unit and currency must agree (no conversions other than the stated billion-to-million), and that release must have been published strictly earlier.
- **C. Actual vs consensus**: `CONSENSUS UNKNOWN` unless you supply dated estimates. Then the workbench's rules apply: same metric, period, unit and currency, and the estimate published strictly before the result; conflicting estimates are reported as a conflict, not averaged.

Then the company's own outlook, conflicts and limitations, deterministic questions for the analyst, and the sources with SHA-256 hashes and times. Interpretation is deliberately empty: materiality, causes, market expectations and price reaction are left to you. If the cutoff precedes the release's publication, the note shows no figures at all.

A consensus file is a JSON list of `{"metric": "revenue", "basis": "GAAP", "period": "Q3 FY25", "value": "34000", "unit": "millions", "currency": "USD", "published_at": "...Z", "observed_at": "...Z", "publisher": "...", "source_url": "https://...", "text": "<passage from the source>", "quote": "<exact words of the figure inside text>"}`. Use only estimates you are permitted to use; KOD sources none itself.

## Limits

Times and quotes are assertions: the tool does not authenticate a source or prove what KOD possessed at a past time (a document downloaded today with an older publication date supports a historical reconstruction only). The demonstration is one event; it shows the workflow works on that layout, not that it is faster than other methods or that it predicts anything. Run `python3 -m unittest tests.test_earnings tests.test_earnings_repairs tests.test_earnings_gate_a tests.test_earnings_review`.

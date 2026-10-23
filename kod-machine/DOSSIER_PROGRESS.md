# Company Decision Dossier: progress and resume checkpoint

Not frozen. Updated at each completed gate of the Company Decision Dossier build (owner's instruction of 2026-10-23). It records what is done, how it was checked
and how to resume. "Implemented" means code plus the tests named here; it does not mean live-validated coverage, a profitable method or a team/commercial release.

## Where things are

| Item | Value |
| --- | --- |
| Repository | jonathanpratama-boop/KOD-Machine |
| Base (default branch) | `claude/idx-signals-test-repo-ds0jw7` at `0281272cd3a95594ab4696a303d7a5169c01719b` (merge of PR 12) |
| Working branch | `claude/kod-decision-dossier-20261023` |
| Current gate | none: all gates A–G done; the draft PR awaits the owner's review |
| Completed gates | A, B, C, D, E, F, G |

Resume from a fresh clone:

```sh
git fetch origin claude/kod-decision-dossier-20261023 && git checkout claude/kod-decision-dossier-20261023 && cd kod-machine && python3 -m unittest && python3 -m unittest discover -s workstation_tests
```

## Gate A: parser repairs (done)

The appendix in the build instruction was run unchanged against `0281272` before any edit; its output reproduced all four defects (ascending columns chose Q3 2023 and called Q3 2024 "prior" at -16.67%; the 3-month heading spread over annual columns and produced a -70% quarter-versus-year change; explicit Canadian-dollar text became USD; a header with no accession supplied an exact acceptance time). After the repairs:

| Appendix case | Result now |
| --- | --- |
| ascending_quarters | current Q3 2024, revenue 120; YoY vs Q3 2023 +20% (revenue and EPS) |
| unequal_colspan_durations | one 3-month column and three 12-month columns read by span; the release never states its quarter, so the result is `PERIOD_UNRESOLVED` and no comparison is made |
| explicit_cad | revenue and EPS in CAD, basis `TABLE_STATEMENT` |
| header_no_accession | `published_at` none; the acceptance time is kept as an assertion |

Behaviour (code in `kod/earnings.py`, parser version `KOD-EARNINGS-PARSER-v3`; workstation boundary in `kod/workstation/services.py`):

- Table layout grid with rowspan/colspan placement, overlap and bound checks, header ancestry and original cell coordinates on every fact; printed-order fallback only for span-free tables, flagged.
- Current period from release evidence (headline statement, "quarter ended" sentences matched to a column); comparison and future sentences excluded; conflicting or absent evidence gives `PERIOD_UNRESOLVED`; an analyst record never overrules the release. Withheld by cutoff shows nothing parsed from the release.
- Comparisons only to genuinely earlier periods of the same duration, basis, unit and currency.
- Reporting currency from cell symbol, table caption, document statement or an analyst record; `$` alone assumed USD and flagged; listing currency never used.
- SEC header tied to a document only when every stated accession agrees with the URL's filing folder, the CIKs agree and the acceptance times are consistent; dot-segment URLs refused; v1-stored acceptance times re-checked at note time.
- An independent adversarial review (three reviewers: periods, currency, geometry; plus a workstation reviewer) reported 31 findings. All were fixed and each reproduced input is a regression test.

Demo notes regenerated (`examples/earnings_demo/output`, `more/*/output`). Semantic differences from the pre-repair output: AMD's net income now carries its GAAP basis and millions scale (was UNSTATED/unscaled) and printed gross-margin percentages are listed as other-period figures; Microsoft's full income statement is now read (revenue, operating income, net income, EPS as UNSTATED basis, same values as its GAAP summary row) and its comparisons gain YoY and sequential rows from it. NVIDIA and Apple: no change in facts, comparisons or guidance.

## Gate B: identity, observations, lineage, cutoff-aware queries, migration (done)

- `kod/workstation/migrations.py`: ordered migrations under `PRAGMA user_version`, each in its own transaction, checksummed, with a safety copy of a populated database before upgrading. v1 → v2 adds the tables below; nothing is rebuilt or deleted.
- `identity.py`: issuer / instrument / listing kept apart from the v1 watchlist row; the v1 security ID stays the listing ID (`security_identity` mapping); identifier aliases with observation basis and unknown historical validity; metric catalog v1 (kind: flow, instant, per_share, ratio, count).
- `financials.py`: immutable `financial_observations` (triggers refuse update/delete); content-addressed IDs; raw text and canonical Decimal; unit, scale, currency, basis, period start/end/instant, duration kind; accession, form, filed date; evidence locator; parser and mapping versions. `FinancialRepository.observations(security, metric, policy)` filters eligibility first, then `resolve(..., "as_reported" | "latest")` selects; conflicts and corroboration are reported.
- `policy.py`: `AsOfPolicy` with `KOD-ASOF-v1-strict` (exact times only, the note behaviour) and `KOD-ASOF-v1-day-end` (a filing date counts from midnight New York after that day).
- `calculations.py`: calculation records with formula/version, input observation IDs, assumption IDs, cutoff policy, status, unit, warnings; dependency DAG with cycle refusal; staleness when an input is superseded; explicit recompute and difference view.
- Migration of a real populated v1 workspace (fixture `workstation_tests/fixtures/v1_workspace.sql.gz`, made by the v1 code at `0281272` from the four demo companies): notes, sources, annotation versions and links retained; backup and restore after migration verified.

## Gate C: SEC companyfacts and filing chronology (done)

- `companyfacts.py`: 17 reviewed concepts; Decimal-exact parsing; JSON pointer evidence; periods from the fact's own dates, never fy/fp or array position; availability = filing date; coverage report (absent metrics, unmapped units, business type from SIC: banks, insurers and REITs outside the operating-company model); filing chronology with amendments.
- `quarters.py`: Q4 = annual − nine months only for additive flows with aligned periods, both inputs recorded; never for EPS, share counts or balances; TTM needs four contiguous non-overlapping quarters of a flow.
- Release-to-10-Q reconciliation within printed rounding; non-GAAP not compared with GAAP.
- Offline fixtures: real SEC companyfacts and submissions responses for NVDA, AMD, AAPL, MSFT, TXN, COST, JPM and PLUG, retrieved 2026-10-23 06:08–06:10 UTC from `data.sec.gov` with a declared contact, trimmed to the mapped concepts with JSON pointers unchanged. Full-response SHA-256, size and fixture SHA-256 are in `examples/companyfacts/SOURCES.json`; `trim.py` rebuilds the fixtures from full responses. Covered cases include Apple's FY2008 10-K/A restatement (as-reported 4,834m vs latest 6,119m by cutoff), Plug Power sign and scale disagreements, JPMorgan as an unsupported bank, and Costco's missing operating-expense concept.

## Gate D: dossier, comparisons and archive search (done)

- `dossier.py` (`KOD-DOSSIER-v1`): one read model behind the page, the Markdown and the JSON. It holds:
  - coverage (eligible observations by provider, absent metrics, business type, policy note);
  - quarterly, annual and balance history with the status of every cell (reported, derived, not derivable, conflicted, suspect);
  - release reconciliation, revisions beyond rounding, conflicts, research questions and the filing chronology;
  - a catalog of nine changes, each with a recorded calculation.
- Comparisons:
  - The year-ago figure is the one presented in the same filing, or for a derived quarter in the same two filings.
  - Per-share and share-count changes are withheld without one.
  - No derivation across accounting vintages, from negatively tagged capex, or giving a negative capex.
  - Scale errors (100x) are marked suspect and not used.
  - The latest quarter is taken across revenue, net income and EPS; a series that stops is reported missing.
  - Quarter on quarter is withheld across a basis change.
  - Unequal period lengths are noted on the page, the calculation page and the export.
  - Rounding is decided by inferred precision, at least a cent per share.
- Information time:
  - Eligibility is applied before anything is selected, and nothing about ineligible records is reported.
  - In observed mode a held record counts from max(observed, recorded) time; one interpretation per source.
  - The identity and submissions response are chosen by the cutoff in observed mode.
  - SEC's `frame` field is left out.
  - Outputs at an earlier cutoff are byte-identical after later data arrives (tested). The public-mode exceptions are documented in DATA_SOURCES.md.
- `search.py`: deterministic passages (`KOD-PASSAGES-v2`) and the workbench's BM25 over distinct passages eligible at the cutoff. It has filters for
  company, period and source type, counts of what was excluded, and snippets highlighted on the ranking's own tokens.
- Two independent adversarial reviews (semantics, information time, web, search) found 26 issues in total, all fixed, each with a regression test. Their
  verifiers then found two more: a negative derived capex quarter, and the period-length note shown only in JSON. Both are fixed and tested.

## Gate E: driver model, prices, assumptions, sensitivity, reverse valuation (done)

- `model.py`: the `KOD-FCFF-v1` formula, limits, statuses, the grid and the reverse solve, all documented in [MODEL.md](MODEL.md).
  - Assumptions are validated completely.
  - Treatments must be declared.
  - The equity bridge needs dated amounts and a selected share count, otherwise the result is enterprise value only.
  - Banks, insurers and REITs are not applicable.
- `scenarios.py`: immutable assumption versions with rationale and supersession. Recorded runs carry the version's own time. The changed fields are listed,
  and market context uses the latest eligible raw close.
- `prices.py`: manual prices and strict whole-file CSV import, each with its declared source, session, time zone, adjustment and coverage. A close counts
  from midnight after the trading day.
- Migration v3 adds the assumption and price tables with immutability triggers.

## Gate F: thesis conditions, review trace, decision packets (done)

- `thesis.py`:
  - A typed JSON expression tree, validated, never evaluated as code.
  - Operands are a change, the latest margin, a metric, a scenario, the latest eligible price or a constant.
  - Three-valued: a data gap gives unresolved.
- `decisions.py`:
  - Thesis versions and recorded reviews. The trace runs from the changed assumption to the version, the scenario result and the condition.
  - Decision packets are stored once with their SHA-256, carry a hindsight note when recorded after the cutoff, and reproduce on demand.
  - Markdown and JSON exports are made from the stored packet.
- Migration v4 adds the thesis, review and packet tables with immutability triggers.

## Gate G: evaluation, review, drills, journey, CI (done)

- Analyst-task evaluation (`evaluation/`):
  - 13 tasks over the six task types: 11 use real filings, and H1 and H2 are synthetic releases (T6 adds a synthetic amendment to real filings).
  - Hand-made expectations citing accession, concept and period.
  - Two previously unseen TI releases downloaded with recorded hashes.
  - JPMorgan's real Q1 2012 10-Q/A restatement, and a bank.
  - The runner checks every fixture hash and every citation, recomputes the model separately, and compares the outputs of two fresh runs.
  - CI fails on a material error or a regression against `results.json`.
- Results, with the same task file and runner for both runs (see `evaluation/REPORT.md`):
  - **Code at `2307e86`:** 8 of 13 tasks; 6 material errors, all in Costco's 16-week quarter.
  - **This branch:** 9 of 13 tasks; 0 material errors.
- The 9 remaining misses are all withheld answers:
  - TI's release: an outlook phrasing, a caption-only column period, a guidance caveat.
  - Two XBRL concepts KOD does not map: NVIDIA's capex as `PaymentsToAcquireProductiveAssets`, bank net revenue as `RevenuesNetOfInterestExpense`.
  - KOD's rule that the reported period must be stated or recorded (H2).
- An independent four-lens review of this gate (expectations, runner, code, docs; each finding verified by a separate agent) confirmed 40 of its 44
  findings and refuted 4. All confirmed findings are fixed except one low-severity point: the TI caveat check accepts the phrase anywhere in the note. The fixes
  cover:
  - **Expectation errors:** T4a, T4b, H2, the T5 bridge and the overlap flags.
  - **Runner weaknesses**, as listed in the report.
  - **Product defects:** Costco's reported long quarters, a same-end duplicate quarter, quarter-on-quarter growth across unequal lengths, notes missing
    from thesis traces, packets and Markdown, the price-correction order, the reverse-solve tolerance, refresh errors and a duplicate job, suggestion
    provenance, and the observed-mode name.
  - **Doc overstatements.**

  Regression tests are in `workstation_tests/test_review_g.py`.
- Migration and restore drill (`workstation_tests/migration_drill.py`) on a real populated v1 workspace, run through the command line. It checks:
  - upgrade v1 → v4 with a safety copy;
  - v1 records unchanged and still rendering;
  - filed history, a scenario, a thesis and a packet added;
  - backup, then restore into a new directory;
  - the packet's SHA-256 verifies and it reproduces after the restore.
- Browser journey (`workstation_tests/browser_journey.py`, Playwright and Chromium, real local server, fresh offline demo), at desktop and phone width:
  - inbox → company → dossier → change → calculation → evidence;
  - search → passage;
  - model from history → scenario → what-if → reverse;
  - thesis → revised assumption → condition triggered, with the trace;
  - packet → reproduce → exports.
- Live check: one filed-history refresh of TXN through KOD's own SEC adapter on 2026-10-23 (two requests, 2,418 observations). The outputs were not
  committed.

## Checks at this checkpoint

Run on commit `59c0dab` (2026-10-23):

| Command (directory) | Result |
| --- | --- |
| `python3 tools/check_append_only.py --all` (root) | Append-only: OK |
| `python3 -m unittest` (kod-machine) | 254 tests OK |
| `python3 -m kod verify` (kod-machine) | OK. Three warnings that cases KOD-R-NVDA-20230524, KOD-R-SMCI-202408 and KOD-S-PIPELINE-001 have no external timestamp; identical at the base `0281272` (the gate A–C checkpoint listed two of them) |
| `python3 -m unittest discover -s workstation_tests -v` (kod-machine) | 189 tests OK |
| `python3 -m unittest` (idx-signals) | 435 tests OK |
| `python3 -m idxsig rules` / `verify-runs` (idx-signals) | OK (USER_RULE pending, unchanged) / verify-runs: OK |
| `python3 -m pip_audit -r kod-machine/requirements-workstation.txt --progress-spinner off` (pip-audit 2.10.1) | No known vulnerabilities found |
| `python3 -m kod.workstation demo --data-dir <fresh>` | 4 historical notes replayed; schema v0 → v4 |
| `python3 evaluation/run_eval.py --runs 2` | 12 of 13 tasks; 0 material errors; 148 citations; both runs identical |
| `workstation_tests/migration_drill.py` on the populated v1 workspace | 21 of 21 checks |
| `workstation_tests/browser_journey.py` (Chromium 1194) | 21 of 21 steps |
| Before/after sweep of the quarter change: 8 companies × 68 cutoffs × 2 views | Differences only in Costco (its week-based quarters now derived) and Plug Power capex (negative derived quarters now refused); the other six companies are identical |

## Decisions

- Period resolution withholds rather than guesses; the analyst can record a period that must agree with the release.
- Date-only filing availability is admitted only by the separately named day-end policy; the strict policy (existing note behaviour) is unchanged.
- Companyfacts fixtures are trimmed copies of real responses, not synthesized values.
- The dossier shows a change only when it is computed on a compatible basis. Otherwise it reports the change missing, incompatible or not applicable,
  with the reason; it never substitutes a nearby figure.
- In public mode, a later submissions response or identity correction may change an earlier view (documented). Decision packets freeze what was used.
- The evaluation's expected answers change only for an error in the expectation, recorded in its report. A task whose failure led to a repair becomes a
  regression check.
- The release reader's gaps exposed by T3 (TI) are left unrepaired, so the next measurement of the reader stays independent.

## Remaining dependencies and open items

- **Next acceptance task.** Extend the release reader to column periods stated in a caption and to "<ordinal> quarter outlook is for …" sentences.
  Map `PaymentsToAcquireProductiveAssets` as capex and `RevenuesNetOfInterestExpense` as bank net revenue, with the care noted in the evaluation report;
  this needs the fixtures rebuilt from the full responses. Then measure on a new evaluation set prepared beforehand, with releases from at least five
  issuers KOD has not seen.
- **Owner decision.** Should KOD infer the reported quarter from column labels when a year-ago sentence corroborates them (evaluation task H2)? It does
  not today.
- **Live SEC collection.** It was exercised once, for one company (TXN, 2026-10-23).
- **Not implemented (see DATA_SOURCES.md):** segment data, consensus, price feeds, options flow, macro vintages.
- **Owner's review.** The draft PR waits for it; nothing is merged or deployed automatically.
- **Earlier PRs.** Old open PRs from the earlier stack are not touched; this branch starts from the merged default.

# Company Decision Dossier: progress and resume checkpoint

Not frozen. Updated at each completed gate of the Company Decision Dossier build (owner's instruction of 2026-10-23). It records what is done, how it was checked
and how to resume. "Implemented" means code plus the tests named here; it does not mean live-validated coverage, a profitable method or a team/commercial release.

## Where things are

| Item | Value |
| --- | --- |
| Repository | jonathanpratama-boop/KOD-Machine |
| Base (default branch) | `claude/idx-signals-test-repo-ds0jw7` at `0281272cd3a95594ab4696a303d7a5169c01719b` (merge of PR 12) |
| Working branch | `claude/kod-decision-dossier-20261023` |
| Current gate | D (longitudinal dossier, comparisons, archive search) |
| Completed gates | A, B, C |

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

## Checks at this checkpoint

Run on the working tree of this checkpoint (2026-10-23):

| Command (directory) | Result |
| --- | --- |
| `python3 tools/check_append_only.py --all` (root) | Append-only: OK |
| `python3 -m unittest` (kod-machine) | 254 tests OK (includes 24 review regressions in `tests/test_earnings_review.py`) |
| `python3 -m kod verify` (kod-machine) | OK; two existing warnings that cases KOD-R-SMCI-202408 and KOD-S-PIPELINE-001 have no external timestamp |
| `python3 -m unittest discover -s workstation_tests` (kod-machine) | 114 tests OK (includes 8 review regressions in `test_review.py`) |
| `python3 -m unittest` (idx-signals) | 435 tests OK |
| `python3 -m idxsig rules` / `verify-runs` (idx-signals) | OK (USER_RULE pending, unchanged) / verify-runs: OK |

## Decisions

- Period resolution withholds rather than guesses; the analyst can record a period that must agree with the release.
- Date-only filing availability is admitted only by the separately named day-end policy; the strict policy (existing note behaviour) is unchanged.
- Companyfacts fixtures are trimmed copies of real responses, not synthesized values.

## Remaining dependencies and open items

- Gates D–G not yet done (dossier, driver model, thesis conditions and decision packets, challenge corpus, browser journey, draft PR).
- Live SEC collection through the application's own refresh path has not been exercised in this build.
- Old open PRs from the earlier stack are not touched; this branch starts from the merged default.

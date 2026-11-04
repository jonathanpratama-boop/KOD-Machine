# Timing integration: changes and verification

Baseline: `c2e9c54ba85c591c2ed5628295159335667a1b84` on
`claude/idx-signals-test-repo-ds0jw7`. Work is isolated on
`astra/timing-integration-20261104`. This is an engineering release for paper
operations. No live order, new recurring task or historical strategy trial was
started. Original research outcomes are not replaced by synthetic test results.

## Problems corrected

| Problem | Implemented correction | Verification / compatibility |
| --- | --- | --- |
| Mixed millisecond/microsecond Binance archive timestamps could reinterpret older rows as 1970 | Normalize each timestamp by its own supported unit with exact integer arithmetic; apply the sealed-date guard before archive loading | Mixed-unit, boundary and malformed-value regressions; original research outputs unchanged |
| Scaled futures names could be mistaken for spot identities | Explicit dated symbol mapping, including the documented `1000SHIBUSDT` multiplier; unknown aliases remain unknown | Symbol and timestamp regressions; no generic prefix stripping |
| Rate limits or access refusals could trigger repeated requests | Stop immediately for explicit provider blocks in affected adapters; retain failure evidence in finite intraday capture | Mocked 418/429 and 403/451 regressions; no alternate-host bypass |
| Sitemap modification dates could be treated as publication or include future entries | Preserve source modification separately, leave publication unknown and reject future modification times at the cutoff | Synthetic source-clock regressions |
| Control selection could use a future-complete ranking population | Add an explicit past-only control helper without changing original experiments or their recorded outcomes | Synthetic causal regression; no corrected market-outcome rerun |
| Frozen-path guard could mishandle unusual filenames or silently unavailable old blobs | NUL-delimited Git paths, strict old-blob failure, complete registry protection and explicit append-log exceptions | Guard regression suite; hooks enabled for each local commit |
| Source directory `idxsig/runtime/` could be hidden by an overly broad ignore pattern | Anchor generated runtime output exclusion to repository `/runtime/` | New source modules are tracked normally; generated root data remains excluded |
| Repeated paper runs could attach an old intent's decision to a later fill | Preserve per-intent identity and first observed decision; attach only genuinely new intents/fills using exact before/after differences | Retry, old-intent, missing-clock and fill-link regressions |
| External timestamp verification could bind the final fill run instead of the original decision batch | Retain `decision_run_id` separately from the final `run_id`; verify the original sealed payload against the decision | Fully mocked external authority; enabled-anchor regression; no market request |
| Scheduler declaration could be confused with actual start | Add start/completion artifacts to the existing daily workflow with an explicitly inferred slot basis | Schedule, manual invocation, retry, missing-start and clock-reversal tests; original cron unchanged |
| Old labels and aliases could become ambiguous during future cleanup | Preserve all original names now; add an empty, append-only, dated ID alias registry and resolver | Alias collision/cycle/as-of regressions; no invented historical migrations |

Detailed research-claim corrections and the actual Hermes/Claude branch gaps are
in [PATCHES_RESEARCH.md](PATCHES_RESEARCH.md) and [BRANCH_GAPS.md](BRANCH_GAPS.md).
The inspected INFO_MAGNET branch remains NOT RUN. The broad statement that no
possible news or timing edge exists is not established by the narrower studies.

## Integrated additions

The immutable timing journal surrounds the existing runtime rather than rewriting
its economic records. It links requested membership, actual processing stages,
raw intraday responses, source failures, paper decisions/fills, prepared events,
cost assumptions and shadow quote checks. The `/timing` page reads a verified
derived board and never triggers collection. Existing backup/restore includes
these artifacts; verification checks both the journal and its linked objects.

`TIMING_CAPTURE_v1` was committed before any prospective collection. This pass
uses synthetic demonstrations and recorded-input engineering tests only. The
protocol's thirty-attempt diagnostic cohort has not begun. A first public capture
is documented in [TIMING_BUILD.md](TIMING_BUILD.md); it is not claimed to have run.

No earlier-entry detector has been enabled. No live entry permission is granted.
The change makes avoidable delay measurable and keeps timing evidence attached
to the right decision. Whether an earlier feasible decision improves net returns
remains a separate, unproven research question.

## Release evidence

Final counts and tree checks will be recorded here after the complete release
gate and mechanical-only tidy. Intermediate failures were used to repair actual
integration defects and hydrate missing original test fixtures; an incomplete
checkout was not counted as a successful full test run.

See [TIDY_REPORT.md](TIDY_REPORT.md) for source-pin preservation and before/after
equivalence, [HISTORY_INTEGRITY.md](HISTORY_INTEGRITY.md) for explicit archival
verification coverage, and [FUTURE_RISKS.md](FUTURE_RISKS.md) for remaining limits.

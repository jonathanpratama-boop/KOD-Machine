# Analyst evidence workbench

This is an opt-in Python tool for organizing a supplied document bundle into source-linked event cards. It supports explicit security identities, cutoff-aware search, duplicate coverage, corrections and reported-versus-consensus comparisons. It is inspired by the connected research workflow examined in the Bloomberg study; it does not reproduce Bloomberg's proprietary models.

The workbench is a derived research view. It grants no entry permission, creates no calibration cases, and does not open the KOD database or write to the frozen registry. It needs Python's standard library, no API key and no network access.

## Run the working example

From `kod-machine/`:

```sh
python3 -m kod.workbench --input examples/workbench_demo.json --as-of 2026-10-22T08:00:00Z --query revenue
python3 -m kod.workbench --input examples/workbench_demo.json --as-of 2026-10-22T08:00:00Z --query revenue --format markdown
python3 -m kod.workbench --input examples/workbench_demo.json --as-of 2026-10-22T08:00:00Z --security-id SYN-DEMO-ID
python3 -m unittest tests.test_workbench
```

The example is entirely **SYNTHETIC**. Names, venues, documents and figures are invented. At 08:00 UTC, the supplied bundle includes quarterly revenue of USD120 million and a prior consensus of USD130 million, duplicate reporting and a separate financing disclosure. The later correction, a notice observed after the cutoff and an undated article must be excluded. These are program demonstrations, not historical investment results.

## The two result lists

`search_results` ranks events matching the query with deterministic lexical relevance. Empty queries show eligible events. `primary_disclosures` shows eligible primary disclosures independently of query matching, ordered by publication time. Both lists respect the selected security filter and the display limit. Their total counts remain visible.

This preserves a route to a thinly covered primary disclosure even when other stories dominate a query. It does not assess that disclosure's economic materiality. Search relevance is not an opportunity score or return forecast. The supplied bundle is the only coverage universe; the tool makes no claim to have scanned an exchange, the web or a complete news feed.

## Supply your own bundle

The input is one JSON object with:

| Field | Meaning |
|---|---|
| `schema_version` | Exactly `KOD-WORKBENCH-v1`. |
| `synthetic` | Boolean indicating whether the bundle is invented. This is a caller declaration. |
| `securities` | Explicit security master entries: `security_id`, `issuer_id`, `ticker`, `venue`, `currency`. |
| `documents` | Source documents with the fields below. |

Each document supplies `document_id`, `event_id`, a list of known `security_ids`, `source_kind` (`PRIMARY` or `SECONDARY`), `publisher`, `source_url`, `source_family` (or null), `published_at` (or null), `observed_at` (or null), `title` and `text`. Use an explicit `replaces_document_id` only for a correction or replacement, and retain the predecessor in the bundle. Observations are optional.

The mapping is explicit: matching ticker strings are insufficient to join instruments. Documents group together only when their event IDs and security sets match. Event IDs, source kinds, family labels and security mappings are supplied assertions; the tool does not independently establish them.

`source_family` records declared content lineage, such as a shared issuer release used by multiple publishers. Different publisher names do not become independent confirmations. Identical normalized title/body content is deduplicated for coverage and ranking while its citations remain visible. Unknown lineage remains unknown.

## Time and correction rules

All supplied timestamps must include a timezone. Observation cannot precede publication when both are supplied. The default `--mode observed` requires both publication and observation at or before `--as-of`. Missing or future times appear as explicit exclusions; observation time never substitutes for unknown publication time. Comparisons preserve timestamp precision.

`--mode public` permits historical reconstruction from publication metadata, including documents observed later. Its output is labelled accordingly. It does not establish what KOD actually possessed at that time. Neither mode independently authenticates supplied dates or proves that today's text is the historical version. KOD's existing evidence verification and timestamp mechanisms continue to serve that separate purpose.

A correction supersedes only the eligible predecessors connected through its explicit replacement chain. A future correction cannot rewrite an earlier view. Contradictory current sources remain visible and block their affected calculation. For example, the demo's post-09:01 correction changes the primary revenue figure while an unlinked old reprint still carries the original number. The workbench must expose that conflict rather than guess how the reprint should be treated.

## Numeric observations

An observation has `metric`, `role` (`ACTUAL`, `CONSENSUS` or `PRIOR`), `value` as a finite decimal string, `unit`, `currency` (or null), `period` and `source_quote`. The quote must occur exactly in its document text. That check establishes a traceable passage, not whether a human extracted the figure correctly.

Actual-versus-consensus comparisons require matching metric, unit, currency and period, with a supplied consensus publication strictly preceding the earliest current actual publication. A same-time or later consensus cannot establish a pre-release expectation and leaves the comparison `INSUFFICIENT_DATA`. This ordering is based on supplied metadata, not independent historical verification. The program performs no FX conversion or automatic scaling. Distinct current values for a role produce `DATA_CONFLICT` for that comparison. Missing counterparts produce `INSUFFICIENT_DATA`; unrelated comparisons can still be calculated.

For compatible observations:

```text
difference = actual - consensus
difference_pct = 100 * difference / abs(consensus)
```

The absolute denominator makes the convention explicit when consensus is negative. Zero consensus yields an unknown percentage, not infinity or zero. The percentage is descriptive arithmetic; its sign does not decide whether an investment is attractive. A `PRIOR` observation is preserved for context and is not silently substituted for consensus.

## Output, safety and limits

JSON output includes the cutoff and mode, bundle identity, eligibility counts, excluded IDs/reasons, search totals, event cards, source citations, content hashes, correction links and calculation evidence. Markdown is an optional readable view of the same report. Output goes to stdout; redirect it to a separate file if needed.

The tool does not fetch or parse live websites, infer entities from ambiguous names, generate free-form investment conclusions, price securities, train a ranking model or execute trades. It has no scheduled task or network side effect. Supplied content hashes help identify the input text; they do not by themselves establish source authenticity or historical availability.

The input bundle must be prepared from sources you are permitted to use. For a real workflow evaluation, freeze the corpus and rubric, include unsuccessful tasks, and measure completion, time, factual accuracy and citation support against the current workflow. No real productivity or return advantage is established by the included tests.

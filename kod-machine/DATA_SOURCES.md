# Workstation data sources and availability

This document describes implemented capabilities, not a list of proposed integrations. KOD Workstation currently uses saved HTML releases and a bounded, explicit SEC adapter. There is no comprehensive free financial-data feed behind the interface.

## Implemented inputs

| Input | Implemented behavior | Coverage limit |
| --- | --- | --- |
| Local earnings HTML | Preserve exact bytes, citation, identity assertion, timestamps and extraction outcome. Optional saved SEC filing headers are preserved as separately linked evidence. | Supported summary-table layouts only; no PDF extraction, universal issuer-site crawler or arbitrary segment-table parser. |
| Frozen historical demo | Replay NVIDIA, AMD, Apple and Microsoft releases and earlier comparisons from the repository's verified manifests. | Historical 2024 examples, not latest/current earnings or a representative universal-layout guarantee. |
| SEC ticker mapping | Explicit online lookup uses `https://www.sec.gov/files/company_tickers_exchange.json`; the web workflow preserves the mapping response behind a resolved identity. | Current SEC listing metadata, not a point-in-time security master, corporate-action history or non-US universe. Missing/ambiguous matches are refused. |
| SEC recent submissions | Manual watchlist refresh reads `https://data.sec.gov/submissions/CIK##########.json`, verifies the CIK, retains the response and saves filing events idempotently. | Only the response's `filings.recent` section and forms `8-K`, `8-K/A`, `10-Q`, `10-Q/A`, `10-K`, `10-K/A`. Older-history chunks and other forms are not collected. |
| Explicit SEC exhibit URL | Fetch a user-selected approved SEC URL, retain its bytes, attempt to retrieve the related filing header when applicable, then pass it to the same ingestion service. | Not automatic exhibit discovery. Unsupported HTML remains stored; a filing event is not automatically an extracted earnings release. |
| SEC companyfacts (XBRL) | Explicit `refresh_companyfacts` per company, or offline import of a preserved response (`import_companyfacts`). Each mapped value becomes an immutable observation with its original tag, unit array, exact number (Decimal from the JSON text), accession, form, filed date and a JSON pointer into the retained response. Seventeen reviewed concepts are mapped (`kod/workstation/companyfacts.py`); a coverage report lists absent catalog metrics, unmapped units and the business type from the SIC code. | Whole-entity standard-taxonomy facts only: no segments or custom KPIs. Availability is the filing date (date precision), so the strict exact-time policy (`KOD-ASOF-v1-strict`) excludes these values; `KOD-ASOF-v1-day-end` admits them from midnight New York time after the filing day. A response downloaded today supports historical reconstruction from accessions; it is not proof the same payload existed earlier. Banks, insurers and REITs are marked outside the operating-company model. Offline fixtures: eight companies under `examples/companyfacts/`. |

The adapter does not collect Form 4 transactions, congressional trading, institutional holdings, options flow, analyst estimates or prices. An empty inbox can mean never checked, a missing configuration, a failed request or no newly supported events; inspect Data and health before interpreting it.

## Requests and operational limits

Remote acquisition is in `kod/workstation/sources.py`; the domain/store/research service performs no network fetching. Importing the package does not start collection. The user must request lookup, import or refresh, and offline mode disables those application actions.

Set `KOD_SEC_CONTACT` to your real contact email to identify SEC requests. The value is used in the request User-Agent, not saved in the database or presented in the UI. It is not an API key and does not guarantee upstream access.

The client currently implements:

- HTTPS allowlisting for `www.sec.gov`, `sec.gov` and `data.sec.gov`, with no URL credentials, custom ports, query strings or fragments. Normal DNS resolution must return public destinations; redirects are validated again.
- A 12 MiB response limit, 20-second request timeout with an 8-second connection timeout, at most four attempts and at most two redirects.
- A conservative process-wide request-start interval of 0.5 seconds; bounded retry handling for network failures and selected transient HTTP statuses. The limiter is not a distributed multi-host service.
- Per-company POSIX advisory refresh locks, so overlapping local web/CLI refreshes of the same company are refused.
- Explicit failed/not-configured job results. A failed refresh does not erase previously stored research or become a successful empty result.

There is no background scheduler, streaming feed, complete HTTP conditional cache/ETag implementation, distributed retry queue or service-level freshness guarantee. Persisted source reuse is not the same as a production HTTP cache. The current adapter is tested with frozen responses and injected transports; this build does not establish that live SEC access works in every deployment.

## Provenance and time semantics

Each preserved document records the company/listing identity, provider, URL, raw byte count and SHA-256, source-version identity, extraction status, association status, publication basis and observation history. Notes reference actual stored document/source-version IDs and record the application version and earnings-parser fingerprint. A changed source or parser can produce a new version without overwriting earlier raw evidence or notes.

Three times must not be conflated:

| Field/concept | Meaning |
| --- | --- |
| Publication / availability | When the selected evidence establishes that this source was available. A filing acceptance time is SEC filing availability, not necessarily the issuer's earliest public announcement. |
| Observation / retrieval | When this installation loaded the source, or an explicitly supplied preserved retrieval time. Supplied retrieval times are labeled as such; loading a historical document today is not evidence of historical possession. |
| Note cutoff | The user-selected information boundary used to decide whether a source is eligible for that note. |

Timezone-aware timestamps are normalized to UTC. An exact SEC acceptance time comes only from a filing's own `-index-headers.html` (New York clock, daylight-saving rules applied), which an exhibit import fetches; the header's accession number must match the exhibit's folder. A header is tied to a document only when every accession it states (title, `ACCESSION NUMBER`, SGML tags, file names) is the same and equals the source URL's filing folder; two accessions refuse the header; inconsistent acceptance times, no accession or a non-SEC URL leave the acceptance time as an assertion only. URLs with `.` or `..` path segments are refused everywhere. Documents saved under the earlier rule are re-checked when a note is generated. The `acceptanceDateTime` field of the SEC submissions feed is **not** used as a publication time: on the eight 2024 earnings filings in `examples/earnings_demo` it ran 4–5 hours later than each filing's own header, which moves after-close filings to the next day. Filing-list refreshes therefore record the filing date with date precision and keep the raw feed value only for reference. A user-supplied date without an intraday time is retained with date precision and no invented midnight timestamp. Missing precise availability stays unknown.

Observed mode requires known source availability **and** recorded observation by the cutoff. Public reconstruction mode checks publication availability but explicitly does not claim possession then. Ineligible financial facts, comparisons and guidance are withheld. Historical reconstruction is not a contemporaneous trading receipt.

### Identity is an assertion with a scope

Manual uploads and direct exhibit imports are labeled `user_asserted`; a plausible URL is not authentication of the supplied bytes. SEC mapping/submissions associations come from the corresponding fetched metadata and are labeled accordingly, not promoted into a blanket authenticity claim for all documents.

The service rejects inconsistent selected-company CIKs, SEC archive URL CIKs and supplied header CIKs. It checks them again when generating a note, including documents uploaded before the company acquired a known CIK. Cross-company documents and preserved-header references cannot silently be used for another company's note. Documents without independently identifying metadata remain assertions.

Hashes detect changed bytes relative to the stored record. They do not prove issuer authorship, the truth of financial figures, an independently trusted timestamp, a right to redistribute content, or complete market coverage.

## Financial interpretation boundaries

The existing deterministic earnings engine extracts supported metrics and keeps periods, units and accounting basis explicit. It compares like periods where possible, distinguishes issuer guidance from prior results, retains conflicts and issue flags, and does not invent unavailable guidance.

Listing/trading currency is not reporting currency. The reporting currency comes from the release's own evidence (cell symbol, table caption, document statement) or an analyst record kept with its provenance; a dollar-sign assumption remains flagged and an unknown currency blocks comparisons. See [EARNINGS.md](EARNINGS.md). A parsed layout is not assurance that every possible metric or non-GAAP reconciliation has been captured. Read the cited table and issues for material decisions.

`CONSENSUS UNKNOWN` is deliberate: no analyst-consensus dataset is integrated. Beating the issuer's own earlier guidance is not an analyst-consensus beat. No price reaction, total return, valuation multiple, fair value, signal quality or trading conclusion is computed by the workstation.

## Not integrated: free-first roadmap, not current functionality

| Candidate | Current status / prerequisite |
| --- | --- |
| Free/delayed end-of-day prices or uploaded price CSV | Not implemented. A future adapter needs explicit provider/feed, symbol and venue mapping, adjustment policy, timestamps, delay/coverage labels, and lawful storage/export rules. |
| FRED / ALFRED macro data | Not implemented. Future use requires access setup where applicable and explicit vintage/revision handling; latest values must not leak into historical decisions. |
| RSS/news/issuer investor-relations collection | Not implemented. Non-SEC web pages can be supplied as local HTML, but there is no general remote crawler. |
| Alpaca or another free-tier market feed | Not implemented. Free access must not be presented as consolidated-market coverage, unrestricted redistribution or unlimited historical access. Confirm the selected product's current terms and entitlements first. |
| Unusual Whales | Not implemented; no X scraping or paid-feed reconstruction. Public commentary is commentary, not authenticated exchange-level flow or a guaranteed predictive signal. Any future API/content use needs explicit access, lawful storage/display/export rights, timestamps, coverage and clear separation from primary evidence. |
| Analyst consensus / estimates | Not implemented; cannot be manufactured from issuer guidance or headlines. A licensed or otherwise lawful source and point-in-time estimates history would be needed. |

Free-first means preferring accessible, inspectable primary evidence within its limits. It does not mean all desired data is free, current, complete, commercially redistributable or suitable for backtesting. Ingesting a file does not establish redistribution rights. Review current source terms, privacy obligations and intended deployment before sharing a workspace or exporting third-party content to others.

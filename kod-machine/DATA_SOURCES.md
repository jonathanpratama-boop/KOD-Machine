# Workstation data sources and availability

This document describes implemented capabilities, not a list of proposed integrations. KOD Workstation currently uses saved HTML releases, a bounded, explicit SEC adapter and prices you enter or import yourself. There is no comprehensive free financial-data feed behind the interface.

## Implemented inputs

| Input | Implemented behavior | Coverage limit |
| --- | --- | --- |
| Local earnings HTML | Preserve exact bytes, citation, identity assertion, timestamps and extraction outcome. Optional saved SEC filing headers are preserved as separately linked evidence. | Supported summary-table layouts only; no PDF extraction, universal issuer-site crawler or arbitrary segment-table parser. |
| Frozen historical demo | Replay NVIDIA, AMD, Apple and Microsoft releases and earlier comparisons from the repository's verified manifests. | Historical 2024 examples, not latest/current earnings or a representative universal-layout guarantee. |
| SEC ticker mapping | Explicit online lookup uses `https://www.sec.gov/files/company_tickers_exchange.json`; the web workflow preserves the mapping response behind a resolved identity. | Current SEC listing metadata, not a point-in-time security master, corporate-action history or non-US universe. Missing/ambiguous matches are refused. |
| SEC recent submissions | Manual watchlist refresh reads `https://data.sec.gov/submissions/CIK##########.json`, verifies the CIK, retains the response and saves filing events idempotently. | Only the response's `filings.recent` section and forms `8-K`, `8-K/A`, `10-Q`, `10-Q/A`, `10-K`, `10-K/A`. Older-history chunks and other forms are not collected. |
| Explicit SEC exhibit URL | Fetch a user-selected approved SEC URL, retain its bytes, attempt to retrieve the related filing header when applicable, then pass it to the same ingestion service. | Not automatic exhibit discovery. Unsupported HTML remains stored; a filing event is not automatically an extracted earnings release. |
| SEC companyfacts (XBRL) | Explicit `refresh_companyfacts` per company, or offline import of a preserved response (`import_companyfacts`). Each mapped value becomes an immutable observation with its original tag, unit array, exact number (Decimal from the JSON text), accession, form, filed date and a JSON pointer into the retained response. Seventeen reviewed concepts are mapped (`kod/workstation/companyfacts.py`); a coverage report lists absent catalog metrics, unmapped units and the business type from the SIC code. | Whole-entity standard-taxonomy facts only: no segments or custom KPIs. Availability is the filing date (date precision), so the strict exact-time policy (`KOD-ASOF-v1-strict`) excludes these values; `KOD-ASOF-v1-day-end` admits them from midnight New York time after the filing day. A response downloaded today supports historical reconstruction from accessions; it is not proof the same payload existed earlier. Banks, insurers and REITs are marked outside the operating-company model. Offline fixtures: eight companies under `examples/companyfacts/`. |
| Prices you supply | A close entered by hand or a strict local CSV (`date,open,high,low,close,volume`), each declaring listing currency, source name, session, time zone, adjustment (`raw`, `split_adjusted`, `total_return`) and the feed's coverage. A CSV is accepted whole or not at all: one bad row rejects the file and every problem is listed. A daily close counts as available from midnight after its trading day in the stated time zone. Every import is immutable; a correction is a new import. | No price feed, scraper or broker connection. Prices are the user's input with the user's stated source; KOD does not verify them against an exchange. Missing volume stays missing. |

The SEC adapter does not collect Form 4 transactions, congressional trading, institutional holdings, options flow, analyst estimates or prices. An empty inbox can mean never checked, a missing configuration, a failed request or no newly supported events; inspect Data and health before interpreting it.

## Provider capabilities

The upstream statements in this table are SEC's own, read from its pages on 2026-10-23:

- "Accessing EDGAR Data" (last updated 26 June 2024): <https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data>
- "EDGAR Application Programming Interfaces" (last updated 8 April 2025): <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>
- "Privacy and Security Policy" (last updated 29 November 2023): <https://www.sec.gov/about/privacy-information>

Re-check them before relying on them; terms change.

| Provider | Data KOD uses | Coverage | Access and authentication | Upstream latency | Time precision KOD uses | Rate limit | Revisions | Retention | Export | Attribution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SEC submissions API (`data.sec.gov/submissions`) | Filing events (8-K, 10-Q, 10-K and amendments), business classification (SIC), filing chronology | US SEC filers; only the `filings.recent` section | No API key. A declared User-Agent with a real contact (`KOD_SEC_CONTACT`) | SEC: updated in real time, typical delay under a second, longer at peak times | Filing date (date precision). `acceptanceDateTime` is kept for reference only, not used as a publication time (see below) | SEC: at most 10 requests per second in total. KOD starts at most one request per 0.5 s | Each refresh is preserved as a new response. Amendments are separate filings | Raw bytes kept locally by SHA-256, never overwritten | Backups carry the bytes. Dossier and packet exports cite the accession and URL | "U.S. SEC, EDGAR" with the URL |
| SEC XBRL companyfacts API (`data.sec.gov/api/xbrl/companyfacts`) | 17 mapped whole-entity concepts as immutable observations | Facts as tagged in 10-K, 10-Q, 8-K, 20-F, 40-F, 6-K and amendments. No segments or custom tags | As above | SEC: real time, typical delay under a minute | Filing date (date precision). The strict policy excludes these values; the day-end policy admits them from midnight New York time after the filing day | As above | Every disclosure of a value is kept with its accession, form and filing date. The as-reported and latest views are both offered. SEC's `frame` field is assigned from the latest filing, so it is left out of cutoff-bound outputs | Full response preserved | Dossier JSON and Markdown cite a JSON pointer into the preserved response | As above |
| SEC EDGAR archives (`www.sec.gov/Archives`) | An exhibit you choose (an earnings release) and its `-index-headers.html` | One document per explicit request. No discovery or crawling | As above | SEC: a submission begun after 5:30 p.m. ET is disseminated the next business day; indexes are rebuilt nightly | Exact acceptance time from the filing's own header (seconds, New York time converted to UTC) | As above | A changed document is a new source version | As above | Notes and packets cite the document URL and SHA-256 | As above |
| SEC ticker mapping (`company_tickers_exchange.json`) | Ticker, CIK and exchange for an explicit lookup | Current listings only; not point in time | As above | Not stated by SEC | None (current metadata) | As above | Replaced on the next lookup; the preserved response stays | As above | Identity records cite the response | As above |
| Your saved HTML releases | Any release you upload, with an optional filing header | Supported summary-table layouts only (see the evaluation report for a layout that fails) | None | Not applicable | What you state (exact time or a date), or the header's acceptance time | None | A changed file is a new source version | Stored by SHA-256 | Notes cite the file. Redistribution rights are yours to establish | The issuer, as you cite it |
| Prices you supply (manual or CSV) | Daily closes and optional open, high, low and volume | Whatever you import, labelled with the coverage you declare | None | Not applicable | The trading date; available from midnight after the trading day in the stated time zone | None | Immutable imports; a correction is a new import, and the price used is the one available at the cutoff | Stored in the workspace | Scenario and packet pages show each price with its declared source. Redistribution rights are yours | The source you declare |

SEC's website policy says that information on sec.gov "is considered public information and may be copied or further distributed by users of the web site
without the SEC's permission" and asks for citation of the SEC as the source. Documents inside a filing, such as an issuer's press release, are the
issuer's content. KOD does not assert redistribution rights for them. No other provider is integrated (see the last section), so no other terms were
checked.

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

The two modes differ in what may change an earlier view later.

- **Observed mode.** A dossier at an earlier cutoff uses only what this workspace held by then: the SEC submissions response and the issuer mapping recorded by
  the cutoff, and each source's interpretation recorded by then. A later download or re-interpretation leaves it byte-identical.
- **Public mode.** The dossier reconstructs publication from today's archive. It uses the earliest preserved submissions response for the business
  classification, labelled "current SEC submissions metadata observed …; not a historical classification". It also uses the current issuer mapping. So
  adding a company's first submissions response, or correcting its identity, can change a public-mode dossier at an earlier cutoff. For example, a bank's
  cash-flow ratios become "not applicable" once its SIC code is known.

A decision packet stores the dossier it was built from, so a recorded decision never changes.

### Identity is an assertion with a scope

Manual uploads and direct exhibit imports are labeled `user_asserted`; a plausible URL is not authentication of the supplied bytes. SEC mapping/submissions associations come from the corresponding fetched metadata and are labeled accordingly, not promoted into a blanket authenticity claim for all documents.

The service rejects inconsistent selected-company CIKs, SEC archive URL CIKs and supplied header CIKs. It checks them again when generating a note, including documents uploaded before the company acquired a known CIK. Cross-company documents and preserved-header references cannot silently be used for another company's note. Documents without independently identifying metadata remain assertions.

Hashes detect changed bytes relative to the stored record. They do not prove issuer authorship, the truth of financial figures, an independently trusted timestamp, a right to redistribute content, or complete market coverage.

## Financial interpretation boundaries

The existing deterministic earnings engine extracts supported metrics and keeps periods, units and accounting basis explicit. It compares like periods where possible, distinguishes issuer guidance from prior results, retains conflicts and issue flags, and does not invent unavailable guidance.

Listing/trading currency is not reporting currency. The reporting currency comes from the release's own evidence (cell symbol, table caption, document statement) or an analyst record kept with its provenance; a dollar-sign assumption remains flagged and an unknown currency blocks comparisons. See [EARNINGS.md](EARNINGS.md). A parsed layout is not assurance that every possible metric or non-GAAP reconciliation has been captured. Read the cited table and issues for material decisions.

`CONSENSUS UNKNOWN` is deliberate: no analyst-consensus dataset is integrated. Beating the issuer's own earlier guidance is not an analyst-consensus beat. The driver model ([MODEL.md](MODEL.md)) computes what an analyst's own assumptions imply; it is not a fair value, a forecast KOD makes or a recommendation. No price reaction, total return, signal quality or trading conclusion is computed by the workstation.

## Not integrated: free-first roadmap, not current functionality

| Candidate | Current status / prerequisite |
| --- | --- |
| A free or delayed end-of-day price feed | Not implemented (you can enter prices or import a CSV yourself; see above). A feed adapter would need an explicit provider, symbol and venue mapping, adjustment policy, timestamps, delay and coverage labels, and lawful storage and export rules. |
| FRED / ALFRED macro data | Not implemented. Future use requires access setup where applicable and explicit vintage/revision handling; latest values must not leak into historical decisions. |
| RSS/news/issuer investor-relations collection | Not implemented. Non-SEC web pages can be supplied as local HTML, but there is no general remote crawler. |
| Alpaca or another free-tier market feed | Not implemented. Free access must not be presented as consolidated-market coverage, unrestricted redistribution or unlimited historical access. Confirm the selected product's current terms and entitlements first. |
| Unusual Whales | Not implemented; no X scraping or paid-feed reconstruction. Public commentary is commentary, not authenticated exchange-level flow or a guaranteed predictive signal. Any future API/content use needs explicit access, lawful storage/display/export rights, timestamps, coverage and clear separation from primary evidence. |
| Analyst consensus / estimates | Not implemented; cannot be manufactured from issuer guidance or headlines. A licensed or otherwise lawful source and point-in-time estimates history would be needed. |

Free-first means preferring accessible, inspectable primary evidence within its limits. It does not mean all desired data is free, current, complete, commercially redistributable or suitable for backtesting. Ingesting a file does not establish redistribution rights. Review current source terms, privacy obligations and intended deployment before sharing a workspace or exporting third-party content to others.

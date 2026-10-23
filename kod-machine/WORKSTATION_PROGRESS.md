# Workstation implementation progress

## Scope

This iteration implements a P0 local analyst workspace around the existing KOD earnings engine. The useful end-to-end path is: select a company, preserve evidence, inspect extraction/availability, generate a source-linked note, record a separate research view, and recover the workspace after restart or backup restoration.

“Implemented” below describes code and local validation scope. It does not mean company-grade operations, Bloomberg-equivalent coverage, live SEC validation, a profitable strategy, or permission to trade. No existing historical research result or governance approval is upgraded by the new interface.

## P0 implemented

| Area | Implemented |
| --- | --- |
| Four views | Event inbox, company workspace, research note, and data/source health. Explicit empty, unsupported, not-configured and failure states are represented. |
| Watchlist identity | Ticker, issuer name/CIK, venue and listing currency; manual assertions distinguished from metadata-resolved identity. Removing a listing from the watchlist retains research. |
| Evidence persistence | Separate runtime SQLite database; immutable content-addressed bytes; document/source versions and observation history; idempotent ingestion and events. |
| Source association | Selected-company ownership checks and SEC URL/header CIK consistency, rechecked against the current company identity at note generation. A user-supplied URL is not treated as authentication. |
| Earnings workflow | Existing deterministic parser/analyser/rendering engine reused through the service; supported HTML retained and parsed, unsupported HTML retained with an explicit status. |
| Financial safeguards | Explicit periods, units and accounting basis; ambiguity/conflict flags; no invented guidance/consensus; reporting-currency assumptions not silently replaced by listing currency. |
| Time-aware notes | Observed versus public reconstruction modes; timezone-aware cutoffs; date-only and unknown publication times remain distinguishable; ineligible financial information withheld. |
| Research record | Saved note JSON and Markdown with source IDs, raw hashes and parser fingerprint; versioned thesis/invalidation/review annotations separate from extracted facts; Markdown/JSON exports. |
| Offline replay | Four preserved real 2024 company examples using the normal ingestion/note path, with manifest hashes and saved SEC header evidence. |
| Bounded SEC adapter | Explicit ticker lookup, recent-submissions event refresh and user-selected SEC URL import; allowlisting, request/response bounds, retries, same-company refresh lock and recorded job outcomes. |
| Recovery | SQLite-consistent backup with referenced evidence and hash manifest; validated restore into a new target only; persistent notes/annotations and last-success health after restart. |
| Local web boundaries | Fixed loopback CLI binding; local Host/Origin checks; signed CSRF tokens; body limits; escaped templates and raw-HTML-disabled Markdown; saved sources displayed as text. |

The earnings repairs and tests also cover the demonstrated AMD header-alignment/period-label failure, Apple share-count/EPS and table-currency pitfalls, and Microsoft's transposed layout. Four companies are useful regression cases, not proof that all issuers or all releases work.

## Architecture

```text
kod/workstation/domain.py     Validation, identity/time conventions, stable hashes
kod/workstation/store.py      SQLite transactions, evidence objects, notes, jobs, recovery
kod/workstation/services.py   Ingestion and note use cases over the existing earnings engine
kod/workstation/sources.py    Optional, explicit bounded SEC acquisition
kod/workstation/web.py        Optional FastAPI/Jinja interface and local web protections
kod/workstation/cli.py        Demo, serve, refresh, backup and restore commands
kod/workstation/demo.py       Hash-verified replay of preserved historical examples
```

The domain/store/service layer is standard-library Python. FastAPI, Uvicorn, Jinja, HTTPX, multipart handling and Markdown rendering are optional, pinned application dependencies. The service does not fetch the network; acquisition hands it bytes and metadata. Runtime state is separate from the append-only legacy evidence and registries.

This separation is intentional: parsing and time eligibility can be tested without an online provider or a browser; network errors do not erase preserved notes; web code does not need to own the financial calculations. A future source adapter must preserve the same identity, time, evidence and failure semantics rather than bypassing them.

## Validation status

The build includes dedicated `workstation_tests` covering persistent user journeys, source/CIK association, observed/public cutoffs and withholding, idempotency, conflicts, annotations, jobs/health, restart, backup/restore integrity, source boundaries and local web behavior. Additional earnings regressions live with the legacy KOD tests. The four-company CLI replay is an independent integration check over preserved source bytes.

Run the new application's suite from `kod-machine`:

```sh
python3 -m unittest discover -s workstation_tests -v
python3 -m kod.workstation demo --data-dir ../runtime/workstation-validation
```

At integration handoff, 65 workstation tests and 101 focused earnings/workbench tests passed. The CLI demo → backup → restore → replay journey passed and retained the same four note IDs. All four views were inspected in a desktop browser. The configured GitHub workflow adds Python 3.12 workstation tests, offline replay and a known-advisory dependency audit, while retaining the existing KOD/IDX checks. Full repository results are recorded against each committed revision in [draft PR #12](https://github.com/jonathanpratama-boop/KOD-Machine/pull/12); passing isolated workstation tests must not be substituted for those checks.

The initial dependency scan flagged known advisories in the older Starlette and python-multipart pins. FastAPI/Starlette and python-multipart were updated together; all 65 workstation tests passed again, and `pip-audit -r requirements-workstation.txt` reported no known vulnerabilities in the resolved application dependencies at build time. Dependency auditing is a known-advisory check, not penetration testing, a guarantee against undisclosed vulnerabilities or approval to expose the local application publicly.

The local build workspace was assembled for implementation and is not a complete historical repository checkout. Legacy registry/history-dependent tests, `kod verify`, GitHub receipt validation and `tools/check_append_only.py --all` require the actual repository data/history and, where applicable, configured CI access. Their result must come from a full checkout/real repository CI, not be inferred from passing isolated workstation tests. No SEC contact was configured during this build, and live SEC access remains unverified. Offline fixtures and mocked HTTP tests do not establish live connectivity.

## P1 and later: not shipped

- Price CSV ingestion, price charts, returns, corporate-action adjustments, live/delayed quote feeds and consolidated-market coverage.
- SEC Company Facts/XBRL fundamentals, older submissions-history downloads, automatic earnings-exhibit discovery and universal issuer-website/PDF parsing.
- Macro/RSS/news providers, FRED/ALFRED vintages, social/X collection and licensed Unusual Whales data.
- Analyst consensus, price targets, valuation models, portfolio/risk aggregation or cross-asset analytics.
- Automated polling, scheduled jobs/alerts, durable background workers, distributed rate limiting or a production HTTP cache.
- Multi-user authentication, authorization, tenant isolation, hosted deployment, encryption/key management, service-level objectives, operational monitoring and disaster-recovery drills.
- Brokerage integration, order execution, buy/sell recommendations, automatic strategy promotion or evidence that a strategy has a tradable edge.

Existing IDX/regional research and governance infrastructure are preserved, but are not wired into a universal workstation data model by this change. Other repository work is not a hidden provider integration.

## Known limits and next acceptance gates

1. **Extraction remains narrow.** Unsupported HTML is an ordinary retained-source outcome. PDFs, unusual tables, segments, amended/non-GAAP subtleties and new issuers need source-backed regressions and review before expanding coverage.
2. **Availability is evidence-dependent.** SEC filing acceptance is not necessarily earliest issuer publication. Supplied timestamps and manually associated files are labeled assertions. Historical public reconstruction must not be marketed as contemporaneous possession.
3. **SEC coverage is recent and manual.** Only six supported filing-form variants from recent submissions are collected. An event does not guarantee automatic extraction, and missing/failed access is not proof of no filings. Validate real SEC access separately with a configured contact before relying on it.
4. **The runtime is private local state.** SQLite/object hashes and validated backups improve recoverability, but do not provide a trusted timestamp authority, multi-user audit security, encrypted storage or enterprise operations. POSIX refresh locks also limit platform portability.
5. **Commercial use needs further decisions.** Define users, entitlements, data/display/export rights, target platforms, threat model, data-retention policy, support ownership and measurable acceptance criteria before hosting or sharing it as a company tool.

The next practical gate is independent analyst review of unfamiliar company releases, plus a clean-checkout CI pass, actual configured-source smoke test, and a restore drill on another fresh directory. Only after those pass should additional providers or deployment complexity be added. Setup and exact recovery commands are in [WORKSTATION.md](WORKSTATION.md); implemented data coverage is in [DATA_SOURCES.md](DATA_SOURCES.md).

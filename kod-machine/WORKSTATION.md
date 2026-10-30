# KOD Workstation

KOD Workstation is a local, single-user research application around KOD's deterministic earnings-note engine. It preserves source evidence, turns supported earnings releases into cutoff-aware notes, builds a company dossier from filed SEC history, and records assumptions, thesis conditions and decisions so that each can be reopened exactly as it was. It keeps your views separate from extracted facts. It is not a live market-data terminal or a trade-execution system, and it covers far less data than a commercial terminal.

## Requirements and setup

Use Python 3.12 and a virtual environment. The configured CI target is Linux with Python 3.12. Manual SEC refresh uses POSIX `fcntl` locks; use Linux or macOS for that path. Native Windows refresh is not supported by this implementation.

From the repository root:

```sh
python3 -m venv .venv-workstation
. .venv-workstation/bin/activate
python3 -m pip install -r kod-machine/requirements-workstation.txt
cd kod-machine
python3 -m kod.workstation demo --serve
```

Open <http://127.0.0.1:8765>. Stop the server with Ctrl-C. Optional web dependencies are pinned in `requirements-workstation.txt`; the persistent store, domain model and research service use the Python standard library. Installing the optional application does not replace the existing KOD or IDX requirements.

The default runtime directory is `runtime/workstation` at the repository root, separate from the legacy registries and evidence. Override it with `--data-dir PATH` on each command or `KOD_WORKSTATION_DATA_DIR`. Keep runtime data outside `kod-machine/var`, `kod-machine/registry`, the source/test/example directories, and `idx-signals`; protected legacy locations are refused.

## Historical, offline demo

The demo replays preserved NVIDIA, AMD, Apple and Microsoft earnings releases from 2024, including their earlier comparison releases and saved SEC filing headers. It verifies the fixture hashes and uses the same ingestion and note-generation service as uploaded documents. It does not fetch current releases or fabricate a current market feed.

```sh
python3 -m kod.workstation demo --data-dir ../runtime/workstation-demo
python3 -m kod.workstation serve --offline --data-dir ../runtime/workstation-demo
```

Or seed and serve in one command:

```sh
python3 -m kod.workstation demo --serve --data-dir ../runtime/workstation-demo --port 8765
```

`demo --serve` always serves offline. `serve --offline` disables remote ticker lookup, URL import and SEC refresh in the application. Saved sources, uploads, notes, annotations and exports remain usable. Replaying the same fixtures with the same parser is idempotent: it does not create duplicate source versions or notes. A parser change is recorded through its fingerprint and can produce a new derived version.

The example notes use historical **public reconstruction** cutoffs. The preserved retrieval timestamps are later than the 2024 releases; the demo does not claim that this installation possessed the documents in 2024.

## Application views

| View | What you can do |
| --- | --- |
| Evidence Workbench `/investigate` | One explicit UTC cutoff across independent ledger cases, observed-mode company dossiers, source search and frozen population research. |
| Population evidence `/research/{study_id}` | Inspect preserved sequence, E6 discovery and execution studies with denominators, baselines, uncertainty, failed gates and assumptions. No reruns or inferred case membership. |
| Frozen event replay `/replay` | Choose an immutable ledger case and UTC cutoff, inspect evidence actually available to KOD and its recorded call, then reveal the outcome separately. Read-only; see below. |
| Event inbox `/` | Add explicit watchlist identities, inspect saved filing/release events, filter by company, category, status, text and publication date, and open saved notes. Removing a watchlist entry retains its evidence and notes. |
| Company workspace `/company/{id}` | Inspect identity and filing history, preserve HTML releases, supply optional filing headers, inspect extraction status, and choose parsed releases for a note. Online mode also offers explicit SEC lookup/import/refresh. |
| Research note `/note/{id}` | Read extracted figures, comparisons, guidance, issues and evidence; record thesis, invalidation and review conditions as versioned user annotations; export Markdown or JSON. |
| Company dossier `/company/{id}/dossier` | The longitudinal history of filed figures, supported changes with their calculations, revisions and conflicts, research questions and the filing chronology, at a chosen cutoff, mode, policy and view. Every number opens its calculation and its source (a release table cell or a JSON pointer into the preserved SEC response). Export as Markdown or JSON. |
| Archive search `/search` | Ranked search over the passages of preserved sources eligible at the cutoff, filtered by company, period and source type; each result opens the passage in context. |
| Driver model `/company/{id}/model` | Save versioned assumption sets (bear/base/bull), run them, open a sensitivity grid, what-if cells and a reverse valuation; enter or import prices. See [MODEL.md](MODEL.md). |
| Thesis `/company/{id}/thesis` | Save a thesis with structured review conditions and see each condition triggered, not triggered or unresolved at the cutoff, with its trace. |
| Decision packets `/packet/{id}` | Record a decision packet from the form at the foot of the dossier page (question, choice, rationale, review date); it freezes everything it rested on. Reopen it, check that it reproduces, export it as Markdown or JSON. |
| Data and health `/health` | Inspect source coverage, the last attempt and last successful refresh separately, and recent job outcomes. Never checked, not configured, failed and successful-with-no-new-events are different states. |

### Make a note from your own source

1. Add the company with a ticker, name, venue, listing currency and, where known, the issuer's CIK. A manual identity is user asserted.
2. Upload a saved `.html` or `.htm` earnings release in its company workspace. The web release limit is 8 MiB; an optional saved SEC header is limited to 1 MiB. Provide the original URL for citation. Uploading a URL as text does not fetch it or authenticate the file.
3. Supply a timezone-aware availability timestamp, such as `2024-10-31T20:30:25Z`, or the saved filing's `index-headers.html`. Date-only availability is retained as a date, not invented as midnight. Unknown precise availability prevents cutoff-aware financial use.
4. Inspect whether extraction is `parsed` or `unsupported`. Unsupported HTML is retained for inspection but cannot be selected as parsed financial data. PDFs, arbitrary page layouts and general segment-table extraction are not supported.
5. Select the current release and optional earlier release, choose a cutoff and availability rule, then generate a note. Review the source citations and issue flags before relying on a number.

Observed mode requires both publication/availability and recorded observation by the cutoff. Public mode reconstructs publication availability without claiming historical possession. A missing or ineligible source is withheld, not silently treated as zero. Listing currency is not assumed to be reporting currency; any dollar-sign assumption remains an explicit extraction flag. Analyst consensus is not sourced and stays `CONSENSUS UNKNOWN`.

User annotations are your views, not extracted facts. Saving one creates another annotation version; it does not rewrite the generated note.

## Company decision dossier

### Filed history

The dossier reads SEC companyfacts observations. First add the company with its CIK, from the event inbox's watchlist form or the online SEC ticker
lookup; the command line has no add command. To load filed history offline, import a preserved response. The repository holds eight under
`examples/companyfacts/`, and `SOURCES.json` there records each URL and retrieval time:

```sh
python3 -m kod.workstation import-companyfacts --data-dir ../runtime/workstation --ticker TXN \
  --companyfacts examples/companyfacts/TXN/companyfacts.json.gz --source-url https://data.sec.gov/api/xbrl/companyfacts/CIK0000097476.json \
  --observed-at 2026-10-23T06:10:14Z --submissions examples/companyfacts/TXN/submissions.json.gz \
  --submissions-url https://data.sec.gov/submissions/CIK0000097476.json
```

One `--observed-at` applies to both responses. Give the later of the two retrieval times (here the submissions response, 06:10:14Z), never an earlier
one. Online, with `KOD_SEC_CONTACT` set, you can instead use the company page's "Refresh filed history" button, or the command line:

```sh
python3 -m kod.workstation refresh --filed-history --data-dir ../runtime/workstation --ticker TXN
```

Each refresh makes two SEC requests under the company's refresh lock and is recorded as one job with its outcome. A failed request or an unreadable response is recorded as failed, not as an empty success. The demo (`demo`) also imports the
filed history of NVIDIA, AMD, Apple, Microsoft and JPMorgan from the preserved responses.

### Reading a dossier

```sh
python3 -m kod.workstation dossier --data-dir ../runtime/workstation --ticker TXN --as-of 2024-11-01T00:00:00Z --mode public
python3 -m kod.workstation dossier --data-dir ../runtime/workstation --ticker TXN --as-of 2024-11-01T00:00:00Z --mode public --view latest --format json
```

Archive search reads the text of preserved documents such as earnings releases and saved HTML, not the SEC JSON responses. Try it on the demo
workspace:

```sh
python3 -m kod.workstation search --data-dir ../runtime/workstation-demo "data center revenue" --as-of 2024-11-21T00:00:00Z --mode public
```

**Cutoff and mode.** Observed mode uses only what this workspace held by the cutoff. Public mode reconstructs what had been published, from today's
archive, without claiming the workspace held it then.

**Policy.** `day-end` admits a filing dated D from midnight New York time after D. `strict` admits only exact times; under it, SEC companyfacts values,
which carry a filing date only, are never eligible.

**View.**
- `as_reported`: each figure as first disclosed.
- `latest`: each figure as most recently disclosed by the cutoff, with every revision listed.

**Supported changes.** A change is shown only on a basis that is stated with it:
- The year-ago figure is taken, when the filing presents it, from the same filing as the current figure; for a derived quarter, from the same two filings.
  This keeps stock splits and restatements on both sides.
- Otherwise a flow is compared with the year-ago figure's own disclosure, and the comparison basis says so. Per-share and share-count changes are
  withheld in that case.
- If the two sides are tagged with different XBRL concepts, that is noted with the change.
- A quarter is never derived across accounting vintages, from a negatively tagged capex figure, or as a negative capex.
- Figures 100 times away from other disclosures are marked suspect and not used.
- Periods of unequal length (13 vs 14 weeks, Costco's 16- against 17-week fourth quarters) are noted wherever the change is shown. Quarter-on-quarter
  growth across quarters whose lengths differ by more than 15% is withheld.
- A series that stops earlier than the others is reported missing, with its last quarter named.

What changes over time, and what never does, is set out in [DATA_SOURCES.md](DATA_SOURCES.md) under "Provenance and time semantics".

### Assumptions, theses and decisions

- **Driver model.** Assumption sets, sensitivity grids, reverse valuation and prices are described in [MODEL.md](MODEL.md).
- **Thesis conditions.** These are typed JSON expressions, built with the form or entered as JSON. They are never evaluated as code.
  - A comparison has the form `{"op": "<", "left": <operand>, "right": <operand>}`, and comparisons combine with `all`, `any` and `not`.
  - An operand is a dossier change, the latest operating margin, a catalog metric, a scenario's value, the latest eligible raw close, or a constant with
    its unit (and currency for money).
  - Units must match, and nothing is converted.
  - A missing, conflicted or not-applicable input makes a condition **unresolved**, never false.
  - The trace of a condition that depends on a scenario names the assumption version, the version it replaced and exactly which assumptions changed.
- **Decision packets.** A packet freezes, under its SHA-256, everything the decision rested on:
  - the dossier read model at its cutoff;
  - the thesis version and its evaluations;
  - the full assumption versions;
  - the price used;
  - the calculation and evidence ids, and the open conflicts.

  It adds your choice, rationale, review date and condition, and an optional resolution rule. A packet recorded after its cutoff carries a hindsight
  note. Reopening shows the stored packet. "Reproduce" rebuilds it from the workspace and lists any difference; a later filing never changes a packet. The
  Markdown and JSON exports are made from the stored packet only.

## Explicit SEC access

SEC requests require a real contact email in the local environment. Replace the example below with your actual contact; the application does not save it in research records.

```sh
export KOD_SEC_CONTACT='you@example.com'
python3 -m kod.workstation serve --data-dir ../runtime/workstation
```

Add a company with its CIK first, or use the online SEC ticker lookup. To manually refresh one existing watchlist company or all of them:

```sh
python3 -m kod.workstation refresh --data-dir ../runtime/workstation --ticker AMD
python3 -m kod.workstation refresh --data-dir ../runtime/workstation
```

Refresh collects supported events from the SEC's **recent submissions** response. It does not download all historical filing chunks, find every earnings exhibit, or generate a note automatically. Open the relevant official filing and select/import the desired exhibit yourself. There is no scheduler or background monitoring promise. See [DATA_SOURCES.md](DATA_SOURCES.md) for exact coverage and request boundaries.

On 23 October 2026 one live filed-history refresh of Texas Instruments through this adapter succeeded: two requests, 1.6 seconds, 2,418 observations recorded, and an observed-mode dossier built from them. That is a single check, not a service-level guarantee. The adapter's tests use frozen responses and injected transports, and a successful offline demo is not proof of live connectivity.

## Persistence, restart and recovery

Runtime state consists of `workstation.sqlite3` and immutable, SHA-256-addressed evidence under `objects/`. SQLite connections enable foreign keys; the store uses WAL and transactional writes. Source observations, source versions, events, generated notes, annotation versions and job health survive a normal restart.

Restart using the same directory:

```sh
python3 -m kod.workstation serve --offline --data-dir ../runtime/workstation
```

After a server restart, reload old browser forms if their CSRF token has expired. Do not delete the runtime directory to resolve an extraction or network error; saved research remains useful offline.

### Upgrading an existing workspace

Opening a workspace applies its pending schema migrations in order (`kod/workstation/migrations.py`; the version is SQLite's `user_version`). Before migrating a populated database a consistent safety copy is written to `migration-backups/` beside it, each migration runs in its own transaction, and its checksum is recorded. A failed migration rolls back and leaves the workspace at its previous version; nothing is rebuilt or deleted. After upgrading a v1 workspace, record financial observations for its preserved releases:

```sh
python3 -m kod.workstation reindex --data-dir ../runtime/workstation
```

Then make a backup and test a restore as below. Existing security IDs, documents, notes and annotation versions keep their IDs; issuer and listing identities are added beside them, and a current ticker is never backdated.

Create a consistent backup with its referenced raw evidence. The destination must not already exist:

```sh
python3 -m kod.workstation backup --data-dir ../runtime/workstation --to ../runtime/workstation-backup-20261023
```

Restore verifies the backup manifest, database integrity, foreign keys and referenced evidence hashes. It restores into a **new** directory only; it refuses to overwrite an existing directory, even an empty one:

```sh
python3 -m kod.workstation restore --from ../runtime/workstation-backup-20261023 --data-dir ../runtime/workstation-restored
python3 -m kod.workstation serve --offline --data-dir ../runtime/workstation-restored
```

Keep the original data until you have opened the restored workspace and checked the expected notes and sources. Copy a completed backup to your normal protected backup location. Do not back up only the active SQLite file, omit `objects/`, or edit a backup manifest to bypass a verification failure. A refused or corrupted backup needs investigation, not forced restoration.

## Security and deployment boundary

The CLI binds to `127.0.0.1` only. The web application checks local Host and mutation Origin headers, signs CSRF form tokens, bounds request bodies, escapes template text, renders note Markdown without raw HTML, and serves saved source HTML as plain text rather than executing it. Remote fetching is restricted to approved SEC HTTPS hosts with bounded responses and redirects.

These are local-use safeguards, **not** a multi-user security model. There are no user accounts, role-based permissions, tenant isolation, encrypted-at-rest storage or production authentication. Anyone with access to the runtime files or this local process can access the research. Do not expose it through a public host, reverse proxy or tunnel as a company service. Use an appropriate private machine and protect its filesystem and backups.

No orders, brokerage access, paid model calls or automated buy/sell recommendations are implemented. The driver model shows what your own assumptions imply; it is not a valuation conclusion of KOD's. Source hashes demonstrate byte integrity, not publisher authenticity or legal redistribution rights. The existing KOD registries, governance checks and historical research are not rewritten by workstation activity.

## Checks

From `kod-machine`, run the optional application's tests and a fresh offline replay:

```sh
python3 -m unittest discover -s workstation_tests -v
python3 -m kod.workstation demo --data-dir ../runtime/workstation-check
python3 evaluation/run_eval.py --runs 2
```

`evaluation/run_eval.py` answers the analyst-task set in [evaluation/](evaluation/README.md) and fails on any material error. Two further checks need
more setup and are not part of CI:

```sh
# A real browser through the whole journey, at desktop and phone width (needs Playwright for Python and a Chromium build):
python3 workstation_tests/browser_journey.py --out ../runtime/journey
# Upgrade, extend, back up and restore a populated version-1 workspace (copied first; the original is never touched):
python3 workstation_tests/migration_drill.py --v1 <v1 workspace directory> --work <empty directory>
```

Use a fresh check directory when independently testing replay or recovery. The repository workflow also runs the legacy tests, append-only checks and `kod verify` in a complete history checkout. See [WORKSTATION_PROGRESS.md](WORKSTATION_PROGRESS.md) for build scope and validation limits.



## Evidence Workbench: one investigation, separate claims

Open **Evidence Workbench** (`/investigate`) from the existing workstation navigation.
A single timezone-qualified cutoff travels into three complementary views:

- **Time:** replay a frozen ledger case without displaying a later call or outcome.
- **Evidence:** choose an explicit company identity and open its existing dossier or source
  search in strict, observed mode. Supported calculations remain source-linked; missing data
  stays missing. The company catalog is navigation, not a historical membership assertion.
- **Population:** inspect a pinned research artifact rather than judging a method from one
  interesting event. Sequence comparisons show hits, known false alerts, censoring and missed
  episodes; E6 retains failed discovery gates; the execution study separates hit rate, net
  return, fills, liquidation and assumed short-side access.

These are not silently joined by ticker. Choosing a company does not establish that a ledger
case belongs to it, and a population result does not establish that the selected case was in
that population. The execution study is not a backtest of the sequence model.

### Read-model invariants and limits

The adapters are small read-only modules: `replay.py` owns frozen ledger chronology and
`research.py` owns pinned research-artifact validation. Existing dossier, search, calculation,
scenario and decision-packet engines remain in place. There is no new service, model fitting,
provider request or execution path.

Research computation time and capture time are displayed separately. Historical as-of views
require both; earlier views contain no metrics, raw results or direct artifact links. Exact
source bytes are packaged with a SHA-256 manifest and pinned upstream commit. Original
research files, ledger records and policy thresholds are not edited. These hashes establish
local consistency, not independent scientific validation or external timestamp authority.

The research adapter does not bundle every original input dataset or execute reproduction
commands. It exposes this gap alongside the pinned source rather than claiming the result
was rerun. Raw preserved result fields remain inspectable after availability. See
[research adapter contracts](RESEARCH_ADAPTER.md) for the packaged studies and validation.

This workbench is research evidence, not a live terminal, a claim of prospective prediction,
or permission to trade. Responsive layouts are provided, but browser visual validation must
be performed in an environment where Chromium can run; rendered HTTP and chronology tests
alone are not a desktop/mobile screenshot review.

## Frozen event replay

Choose **Event replay** in the workstation navigation, or open `/replay`.
This reads the existing `kod-machine/var/kod.db` ledger in SQLite read-only mode;
it does not migrate it, write to it, run a detector, contact a provider or place orders.
The workstation's separate runtime database is unchanged by replay requests.

1. Select a frozen case, then a timezone-aware UTC cutoff or one of its recorded milestones.
2. Inspect eligible evidence and facts. Publication, retrieval and ledger recording must all
   precede the cutoff. A published document retrieved later is **not** shown as known to KOD
   at publication. Unknown chronology is withheld. Facts also need their frozen citations.
3. Read the original call and hash-bound detector evaluations only once the case was recorded.
   These are saved outputs, never a recalculation. Legacy cards without hash-bound evaluations
   show no invented detector results.
4. Reveal the outcome explicitly. It is absent from the default response and must itself have
   been recorded by the selected cutoff. Changing case or time returns to the hidden state.
5. Try a minimum evidence grade in the separate sandbox. This filters the eligible evidence
   count only; it neither changes the original snapshot nor recalculates its prediction.

### A real preserved example, not a backdated forecast

Select `KOD-R-ZEAL-20250312`. At its historical decision cutoff
`2025-03-11T16:00:00Z`, the replay correctly withholds the later KOD reconstruction.
At its actual ledger open `2026-10-08T12:44:07Z`, the preserved retrospective call and
eligible evidence can be inspected. At a later cutoff such as `2026-10-30T00:00:00Z`,
the recorded outcome can be revealed separately. This case was selected retrospectively;
it is not evidence of an advance prediction. The other seed cards are also explicitly
retrospective or simulated. No prospective prediction is fabricated to fill this gap.

The snapshot identity is deterministic and independent of the sandbox filter or outcome
reveal. Local card, information-set and evidence-object hashes are checked; this view does
not independently verify timestamp receipts or archived source bytes. A matching hash is
local consistency, not proof of contemporaneous possession. Missing or inconsistent archives
produce an unavailable state rather than an empty success.

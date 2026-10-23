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
| Event inbox `/` | Add explicit watchlist identities, inspect saved filing/release events, filter by company, category, status, text and publication date, and open saved notes. Removing a watchlist entry retains its evidence and notes. |
| Company workspace `/company/{id}` | Inspect identity and filing history, preserve HTML releases, supply optional filing headers, inspect extraction status, and choose parsed releases for a note. Online mode also offers explicit SEC lookup/import/refresh. |
| Research note `/note/{id}` | Read extracted figures, comparisons, guidance, issues and evidence; record thesis, invalidation and review conditions as versioned user annotations; export Markdown or JSON. |
| Company dossier `/company/{id}/dossier` | The longitudinal history of filed figures, supported changes with their calculations, revisions and conflicts, research questions and the filing chronology, at a chosen cutoff, mode, policy and view. Every number opens its calculation and its source (a release table cell or a JSON pointer into the preserved SEC response). Export as Markdown or JSON. |
| Archive search `/search` | Ranked search over the passages of preserved sources eligible at the cutoff, filtered by company, period and source type; each result opens the passage in context. |
| Driver model `/company/{id}/model` | Save versioned assumption sets (bear/base/bull), run them, open a sensitivity grid, what-if cells and a reverse valuation; enter or import prices. See [MODEL.md](MODEL.md). |
| Thesis `/company/{id}/thesis` | Save a thesis with structured review conditions and see each condition triggered, not triggered or unresolved at the cutoff, with its trace. |
| Decisions `/company/{id}/decisions`, `/packet/{id}` | Record a decision packet (question, choice, rationale, review date) that freezes everything it rested on; reopen it and check that it reproduces. |
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

The dossier reads SEC companyfacts observations. To load them offline, import a preserved response; the repository holds eight under
`examples/companyfacts/`, and `SOURCES.json` there records each URL and retrieval time:

```sh
python3 -m kod.workstation import-companyfacts --data-dir ../runtime/workstation --ticker TXN \
  --companyfacts examples/companyfacts/TXN/companyfacts.json.gz --source-url https://data.sec.gov/api/xbrl/companyfacts/CIK0000097476.json \
  --observed-at 2026-10-23T06:09:01Z --submissions examples/companyfacts/TXN/submissions.json.gz \
  --submissions-url https://data.sec.gov/submissions/CIK0000097476.json
```

Never give an `--observed-at` earlier than the real retrieval. Online, with `KOD_SEC_CONTACT` set, you can instead use the company page's "Refresh filed
history" button, or the command line:

```sh
python3 -m kod.workstation refresh --filed-history --data-dir ../runtime/workstation --ticker TXN
```

Each refresh makes two SEC requests under the company's refresh lock, and is recorded as a job with its outcome. The demo (`demo`) also imports the
filed history of NVIDIA, AMD, Apple, Microsoft and JPMorgan from the preserved responses.

### Reading a dossier

```sh
python3 -m kod.workstation dossier --data-dir ../runtime/workstation --ticker TXN --as-of 2024-11-01T00:00:00Z --mode public
python3 -m kod.workstation dossier --data-dir ../runtime/workstation --ticker TXN --as-of 2024-11-01T00:00:00Z --mode public --view latest --format json
python3 -m kod.workstation search --data-dir ../runtime/workstation "data center revenue" --as-of 2024-11-21T00:00:00Z --mode public
```

**Cutoff and mode.** Observed mode uses only what this workspace held by the cutoff. Public mode reconstructs what had been published, from today's
archive, without claiming the workspace held it then.

**Policy.** `day-end` admits a filing dated D from midnight New York time after D. `strict` admits only exact times; under it, SEC companyfacts values,
which carry a filing date only, are never eligible.

**View.**
- `as_reported`: each figure as first disclosed.
- `latest`: each figure as most recently disclosed by the cutoff, with every revision listed.

**Supported changes.** A change is shown only on a compatible basis:
- The year-ago figure is the one presented in the same filing. For a derived quarter, it comes from the same two filings. This keeps stock splits and
  restatements on both sides.
- Per-share and share-count changes are withheld without a same-filing comparative.
- A quarter is never derived across accounting vintages, from a negatively tagged capex figure, or as a negative capex.
- Figures 100 times away from other disclosures are marked suspect and not used.
- Periods of unequal length (13 vs 14 weeks, Costco's 16-week fourth quarter) are noted wherever the change is shown.
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

# KOD Workstation

KOD Workstation is a local, single-user research application around KOD's deterministic earnings-note engine. It preserves source evidence, turns supported earnings releases into cutoff-aware notes, and keeps your annotations separately from extracted facts. It is not a Bloomberg replacement, a live market-data terminal, or a trade-execution system.

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

## Four application views

| View | What you can do |
| --- | --- |
| Event inbox `/` | Add explicit watchlist identities, inspect saved filing/release events, filter by company, category, status, text and publication date, and open saved notes. Removing a watchlist entry retains its evidence and notes. |
| Company workspace `/company/{id}` | Inspect identity and filing history, preserve HTML releases, supply optional filing headers, inspect extraction status, and choose parsed releases for a note. Online mode also offers explicit SEC lookup/import/refresh. |
| Research note `/note/{id}` | Read extracted figures, comparisons, guidance, issues and evidence; record thesis, invalidation and review conditions as versioned user annotations; export Markdown or JSON. |
| Data and health `/health` | Inspect source coverage, the last attempt and last successful refresh separately, and recent job outcomes. Never checked, not configured, failed and successful-with-no-new-events are different states. |

### Make a note from your own source

1. Add the company with a ticker, name, venue, listing currency and, where known, the issuer's CIK. A manual identity is user asserted.
2. Upload a saved `.html` or `.htm` earnings release in its company workspace. The web release limit is 8 MiB; an optional saved SEC header is limited to 1 MiB. Provide the original URL for citation. Uploading a URL as text does not fetch it or authenticate the file.
3. Supply a timezone-aware availability timestamp, such as `2024-10-31T20:30:25Z`, or the saved filing's `index-headers.html`. Date-only availability is retained as a date, not invented as midnight. Unknown precise availability prevents cutoff-aware financial use.
4. Inspect whether extraction is `parsed` or `unsupported`. Unsupported HTML is retained for inspection but cannot be selected as parsed financial data. PDFs, arbitrary page layouts and general segment-table extraction are not supported.
5. Select the current release and optional earlier release, choose a cutoff and availability rule, then generate a note. Review the source citations and issue flags before relying on a number.

Observed mode requires both publication/availability and recorded observation by the cutoff. Public mode reconstructs publication availability without claiming historical possession. A missing or ineligible source is withheld, not silently treated as zero. Listing currency is not assumed to be reporting currency; any dollar-sign assumption remains an explicit extraction flag. Analyst consensus is not sourced and stays `CONSENSUS UNKNOWN`.

User annotations are your views, not extracted facts. Saving one creates another annotation version; it does not rewrite the generated note.

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

Live SEC access has not been independently validated during this build. The source adapter is covered with frozen and injected-transport tests; a successful offline demo is not proof of live connectivity.

## Persistence, restart and recovery

Runtime state consists of `workstation.sqlite3` and immutable, SHA-256-addressed evidence under `objects/`. SQLite connections enable foreign keys; the store uses WAL and transactional writes. Source observations, source versions, events, generated notes, annotation versions and job health survive a normal restart.

Restart using the same directory:

```sh
python3 -m kod.workstation serve --offline --data-dir ../runtime/workstation
```

After a server restart, reload old browser forms if their CSRF token has expired. Do not delete the runtime directory to resolve an extraction or network error; saved research remains useful offline.

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

No orders, brokerage access, paid model calls, valuation conclusions or automated buy/sell recommendations are implemented. Source hashes demonstrate byte integrity, not publisher authenticity or legal redistribution rights. The existing KOD registries, governance checks and historical research are not rewritten by workstation activity.

## Checks

From `kod-machine`, run the optional application's tests and a fresh offline replay:

```sh
python3 -m unittest discover -s workstation_tests -v
python3 -m kod.workstation demo --data-dir ../runtime/workstation-check
```

Use a fresh check directory when independently testing replay or recovery. The repository workflow also runs the legacy tests, append-only checks and `kod verify` in a complete history checkout. See [WORKSTATION_PROGRESS.md](WORKSTATION_PROGRESS.md) for build scope and validation limits.

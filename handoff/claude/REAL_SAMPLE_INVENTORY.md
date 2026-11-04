# Real-sample inventory: parsers of outside data

Read-only survey for `handoff/KOD_FIX_PLAN.md` Fix 1 item 4, taken at commit `dcbd30f29` (branch
`fix/1-clock-parser-v2`) on 2026-11-04. It adds no fixture. The one real fixture added so far, the chrony
line, came with that commit's parser fix.

**Result.** 3 of the 37 parser rows below have a real captured sample in their unit tests (1, B1, B5).
The other 34 are tested only with synthetic data, or not tested at all, so the Fix 1 owner check ("zero
parsers without a real sample") is **not met**. For 9 of the 34, exact real bytes already exist in this
repository or in the production commissioning bundle, so a fixture needs no new capture; one more has
re-serialized bytes only (see "Sourceable now").

## Method

- **Scope:** `idx-signals/idxsig` and `kod-machine/kod`. A parser of outside data turns bytes from a third
  party (an HTTP response, a downloaded file, or a local tool's output) into values KOD uses.
- **Finding the parsers:** every external host named in the two packages; every module that makes a
  network request or runs an outside tool; every source named in Fix 1 item 4.
- **Test files:** the files in `idx-signals/tests`, `kod-machine/tests` and `kod-machine/workstation_tests`
  whose import statements name the module (read from the syntax tree). This does not claim which
  functions a test reaches.
- **Real or synthetic:** every read of a repository file by a test file was listed (searches for
  `Path(__file__)`, `parents[`, `PKG_ROOT`, `fixtures/`, `examples/`, `registry/`, `gzip.open`,
  `read_bytes`, and relative `open`/`Path` literals). Only the first four paths under "Real samples in
  tests" are captured outside bytes read by unit tests. Everything else is **synthetic**: the test builds
  the payload in code or writes it to a temporary directory.
- **Real bytes elsewhere:** captured data in the repository that no test reads. Existence and the link from
  its log or manifest were checked; the content was not re-verified against the source.

## Real samples in tests

| Path | What it is | Read by |
|---|---|---|
| `idx-signals/tests/fixtures/real/chronyc_tracking_20261104T123000Z.txt` | Exact `chronyc -c tracking` stdout from the production server, 2026-11-04T12:30:00Z (see the README beside it) | `idx-signals/tests/test_chrony_tracking.py` |
| `kod-machine/tests/fixtures/releases_v2/` | 9 issuers' SEC earnings-release exhibits (gzip of the bytes as served) and filing index headers; `SOURCES.json` records URL, size, SHA-256 and retrieval time | `kod-machine/tests/test_earnings_reader_v2.py` |
| `kod-machine/examples/earnings_demo/` | NVIDIA Q3 and Q2 FY2025 earnings releases and their index headers; `SOURCES.json` as above | `kod-machine/tests/test_earnings.py`; `workstation_tests/test_gate_a.py`, `test_gate_b.py`, `test_gate_c.py`, `test_review.py`, `test_web.py` |
| `kod-machine/examples/companyfacts/<TICKER>/` | SEC XBRL companyfacts and submissions responses for AAPL, AMD, COST, JPM, MSFT, NVDA, PLUG, TXN, **trimmed** by `trim.py` to the mapped concepts and filing rows; the full responses' size and SHA-256 are in `SOURCES.json` | `workstation_tests/test_gate_c.py`, `test_gate_d.py`, `test_gate_e.py`, `test_gate_f.py`, `test_review_g.py` |
| `kod-machine/evaluation/fixtures/txn/` | SEC releases and headers for the analyst-task evaluation | `kod-machine/evaluation/run_eval.py` with its default `tasks.json`, which `checks.yml` runs (`--runs 2`); not a unit test. `evaluation/holdout_v1/fixtures/` (6 issuers) is read only with `--tasks holdout_v1/tasks.json`, which no workflow runs |

## idx-signals/idxsig

| # | Source | Module: function | Test files | Real sample in tests | Real bytes elsewhere |
|---|---|---|---|---|---|
| 1 | chrony `chronyc -c tracking` | `runtime/chrony.py`: `read_tracking_v2` (called by `runtime/timing.py`: `clock_observation`; re-read by `runtime/timing_evidence.py`: `verify_linked_evidence`) | `test_chrony_tracking.py` (through `runtime.timing`) | **Yes**: `tests/fixtures/real/chronyc_tracking_20261104T123000Z.txt` | n/a |
| 2 | Binance spot `api.binance.com`: `/api/v3/time`, `exchangeInfo`, `klines`, `ticker/bookTicker`, `depth` (intraday capture) | `runtime/intraday.py`: `fetch_public`, `collect_intraday`, `load_intraday` | `test_intraday_capture.py`, `test_timing_evidence.py`, `test_timing_integration.py` | No (`test_intraday_capture.py`: "no public requests and no real outcome data") | Not in the repository. The production commissioning bundle (outside it) holds 8 received responses from 2026-11-04T12:30Z: klines 2, bookTicker 2, depth 2, time 1, exchangeInfo 1 |
| 3 | Binance spot `api.binance.com`: `exchangeInfo`, daily `klines`, `ticker/bookTicker` (runtime paper cycle) | `runtime/collect.py`: `_fetch`, `collect_binance_spot`; `runtime/data.py`: `load_recorded_snapshot` | collect: `test_runtime_coordinator.py`, `test_runtime_data_context.py`; data: those two and `test_intraday_capture.py`, `test_market_time.py`, `test_runtime_integrity.py`, `test_timing_integration.py` | No | None |
| 4 | Binance `data-api.binance.vision` daily `klines` and `exchangeInfo` (panel download) | `sources/binance.py`: `fetch`, `_symbol`, `_get`; `global_panel.py`: `load_crypto` | binance: `test_binance_blocks.py`, `test_source_resume_repair.py`; global_panel: `test_causal_panel.py`, `test_e9_pipeline.py`, `test_markets.py`, `test_paper_markets.py`, `test_split_verification.py`, `test_storage_repair.py` | No | None: `data/manifests/binance-*.jsonl` record metadata and hashes; `idx-signals/data/raw/` is git-ignored |
| 5 | Binance `data-api.binance.vision` `depth`, `time`, 1m `klines` | `microstructure.py`: `fetch_depth`, `fetch_minutes`, `_get`, `book_metrics` | `test_microstructure.py`, `test_source_clock_and_blocks.py` | No | `idx-signals/paper/microstructure/raw/`: 7 `<SYMBOL>.depth.<timestamp>.json.gz` (the parsed response re-serialized with `json.dumps`, **not** the exact bytes) and 25 `*.minutes.csv.gz` (bars converted to CSV), referenced by `paper/microstructure/crypto.jsonl` |
| 6 | Binance `data-api.binance.vision` `ticker/price` | `paper.py`: `binance_quotes` | `paper.py` is imported by 28 test files; none names `binance_quotes` | No | None |
| 7 | Binance `data-api.binance.vision` `ticker/bookTicker` | `crypto_account.py`: `fetch_quotes` (byte-pinned file) | `test_crypto_account.py`, `test_crypto_account_concurrency.py`, `test_crypto_policy_price_validation.py`, `test_crypto_quote_validation.py`, `test_crypto_valuation_asof.py` | No | None |
| 8 | Binance announcements, `www.binance.com/bapi` CMS list | `sensors.py`: `binance_listings` | `test_sensors.py` | No | `idx-signals/paper/sensors/raw/20261027T074803Z/` and `.../20261027T074820Z/binance_listings.json.gz`: exact response bytes (gzip), SHA-256 in `paper/sensors/sensors.jsonl` |
| 9 | Binance public archive timestamps (millisecond to microsecond switch in 2025) | `market_time.py`: `binance_time_unit`, `binance_datetime`, `binance_datetimes`, `binance_bar_end` | `test_market_time.py` ("synthetic data only") | No | None. The archive downloaders are outside these packages (see below) |
| 10 | CoinGlass `open-api-v4.coinglass.com` | `sources/coinglass.py`: `validate_request`, `CoinGlassClient.request`; `coinglass.py`: `normalize_history`, `capture`, `load_snapshot`, `latest_context`, `history_frame` | `test_coinglass_client.py`, `test_coinglass_context.py` | No | None |
| 11 | SEC EDGAR: Schedule 13D current feed (Atom), `company_tickers_exchange.json`, submissions JSON, 13D `primary_doc.xml` | `catalysts.py`: `parse_feed`, `ticker_maps`, `submissions`, `sec13d_batch` | `test_catalysts.py`, `test_document_class.py`, `test_fam_dilution8k.py`, `test_fam_form4.py`, `test_outcome_repair.py`, `test_sensor_v2.py`, `test_stabilization.py` | No (`test_catalysts.py`: "Synthetic data only, no network") | None |
| 12 | EmitenNews sitemap `www.emitennews.com/sitemap-{year}.xml` (catalyst dilution tags) | `catalysts.py`: `dilution_tags` | as row 11 | No | The same document type is retained by row 24 |
| 13 | SEC submissions JSON, main file and chunk files | `catalyst.py`: `parse_submissions`, `filings_frame` | `test_catalyst.py` ("Synthetic tests ... No network") | No | None |
| 14 | SEC 8-K current feed (Atom) | `fam_dilution8k.py`: `parse_feed` | `test_fam_dilution8k.py` ("Synthetic data only, no network") | No | None |
| 15 | SEC daily form index and Form 4 XML | `fam_form4.py`: `has_index_header`, `parse_index`, `parse_form4`, `read_filings` | `test_fam_form4.py`, `test_sensor_v2.py` | No | `idx-signals/paper/catalysts_form4/FORM4-*.txt.gz` (4 files) hold accession, status and XML SHA-256 rows, **not** the XML |
| 16 | SEC submissions chunks and full filing text (Form 4 SHARP) | `fam_form4_sharp.py`: `owner_filings` | `test_sensor_v2.py` | No | None |
| 17 | SEC Schedule 13D cover page and items 4 and 5(c) | `fam_sec13d_v2.py`: `cover_page`, `strong_intent`, `item5c` | `test_sensor_v2.py` | No | None |
| 18 | SEC 8-K exhibit text | `guidance.py`: `exhibit_texts`, `plain_text` | `test_guidance.py` | No | None |
| 19 | Guidance sentences in release text | `guidance_v2.py`: `parse` | `test_guidance_v2.py` | No | None |
| 20 | SEC daily form index and filing acceptance time | `guidance_paper.py`: `releases_on`, `acceptance_ny` | `test_guidance_paper.py` | No | None |
| 21 | SEC full submission text (`<SEC-DOCUMENT>`) | `guidance_revision.py`: `submission` | `test_guidance_revision.py` (reads `protocol.json` only) | No | `idx-signals/research/GUIDANCE_REVISION_v1/fixtures/0000002488-21-000009.txt.gz` and `0000002488-21-000054.txt.gz` (AMD, with `bindings.json` hashes), read by that study's `run_first_decision.py`, not by tests |
| 22 | SEC submissions and XBRL frames; FINRA Reg SHO daily short volume (`cdn.finra.org`); split events in cached Yahoo chart payloads | `learner3.py`: `Context.filings`, `Context.shares`, `Context.short`, `_finra_day`, `_splits` | `test_learner3.py` ("Synthetic data, no network") | No | None |
| 23 | SEC full-text search (`efts.sec.gov`), `company_tickers.json`, filing documents, `companyconcept` | `us_actions.py`: `search`, `text_of`, `split_statements` | `test_e2_repair.py`, `test_split_verification.py`, `test_us_pipeline.py` | No | `idx-signals/data/archive/e2_us_sec_evidence_v1/sec_evidence_20261008.tar.xz`: every SEC response `us-actions` read on 2026-10-08 (Git LFS; only the pointer is checked out here, contents not inspected) |
| 24 | Sensors: Bluesky (`public.api.bsky.app`), StockTwits trending, SEC full-text search, CoinGecko trending, EmitenNews sitemap | `sensors.py`: `bluesky`, `stocktwits_trending`, `edgar_8k`, `coingecko_trending`, `emitennews_dilution` | `test_sensors.py`, `test_source_clock_and_blocks.py` | No (`test_sensors.py`: "No network"; inline `fake_fetch`) | `idx-signals/paper/sensors/raw/` (two captures, 2026-10-27): exact response bytes for each source except `edgar_8k`, whose file is `json.dumps` of its parsed result pages |
| 25 | IDX daily stock summary, GitHub mirror `wildangunawan/Dataset-Saham-IDX` | `sources/idx_mirror.py`: `fetch`, `_csv_summary`; `panel.py`: `load_mirror` | idx_mirror: `test_controls_quality.py`, `test_review_fixes.py` (both import only the `FIRST_SNAPSHOT` constant); panel: `test_corporate_actions.py` | No: no test names `fetch`, `_csv_summary` or `load_mirror` | None tracked (`data/raw/` is git-ignored) |
| 26 | IDX reference-price resets and primary-source corporate actions | `corporate_actions.py` (registry from the panel and `data/corporate_actions/manual.csv`) | `test_corporate_actions.py` ("Synthetic markets only"), `tests/support.py` | No | `manual.csv` rows are hand-entered with source URLs, not captured bytes |
| 27 | Yahoo chart API `query1.finance.yahoo.com` | `sources/yahoo.py`: `fetch_one`, `_summary`; `panel.py`: `_yahoo_frame`, `load_yahoo`; `global_panel.py`: `load_us` | yahoo: `test_source_resume_repair.py`; panel and global_panel as rows 25 and 4 | No | `idx-signals/data/archive/e2_us_inputs_v1/e2_us_raw_20261008.tar.xz`: 5,705 Yahoo chart payloads (Git LFS; pointer only here) |
| 28 | Nasdaq Trader symbol directories (`nasdaqlisted.txt`, `otherlisted.txt`) | `sources/us_universe.py`: `fetch`, `parse_dir` | **None** | No test at all | The two listing files are in the same LFS tarball as row 27 |
| 29 | RFC 3161 responses (FreeTSA, Sectigo) for runtime decision anchors | `runtime/time_anchor.py` (through `kod.timestamp`) | `test_time_anchor.py` | No: tokens are invented (`Stamp("fixture", b"signed:" + data)`, `b"not a valid RFC3161 token"`) | See row B6 |

## kod-machine/kod

| # | Source | Module: function | Test files | Real sample in tests | Real bytes elsewhere |
|---|---|---|---|---|---|
| B1 | SEC earnings-release exhibit HTML and filing index headers | `earnings.py`: `read_document` (`_Page`), `extract_table_facts`, `extract_guidance`, `headline_checks`, `sec_acceptance` | `tests/test_earnings.py`, `test_earnings_gate_a.py`, `test_earnings_reader_v2.py`, `test_earnings_repairs.py`, `test_earnings_review.py`; `workstation_tests/test_gate_b.py` | **Yes**: `tests/fixtures/releases_v2/` and `examples/earnings_demo/` | `evaluation/fixtures/txn/` (CI evaluation), `evaluation/holdout_v1/fixtures/` |
| B2 | Optional consensus JSON file passed to the analysis | `earnings.py`: `load_consensus` | No test names it | No | None |
| B3 | SEC `company_tickers_exchange.json` | `workstation/sources.py`: `SecClient.resolve` | `workstation/sources.py` is imported by `workstation_tests/test_gate_c.py`, `test_review.py`, `test_review_g.py`, `test_sources_demo.py`; `test_web.py` reaches `resolve` through the web app | No (`test_web.py` serves one inline row) | None |
| B4 | SEC submissions JSON (filing events) | `workstation/sources.py`: `normalize_submissions`, `acceptance_time` | as B3; `test_sources_demo.py` calls `normalize_submissions` | No (`test_sources_demo.py`: "Synthetic boundary fixture") | `examples/companyfacts/*/submissions.json.gz` (trimmed, real) reach `companyfacts.business_type` and `observation_rows` through `ResearchService.import_companyfacts`, not this function |
| B5 | SEC XBRL companyfacts JSON, with submissions for business type and acceptance times | `workstation/companyfacts.py`: `parse`, `observation_rows`, `business_type`, `acceptance_times`, `filing_chronology` | `workstation_tests/test_gate_c.py` directly; `test_gate_d.py`, `test_gate_e.py`, `test_gate_f.py`, `test_review_g.py` through `services.ResearchService.import_companyfacts` | **Yes, trimmed**: `examples/companyfacts/` | n/a |
| B6 | RFC 3161 responses from FreeTSA and Sectigo | `timestamp.py`: `RFC3161Timestamper`, `_parse_gen_time` (through OpenSSL) | `tests/test_timestamp.py` ("a throwaway OpenSSL timestamp authority served on localhost"), `tests/support.py`, `tests/test_review_fixes.py`; `idx-signals/tests/test_time_anchor.py` | No real-authority token in unit tests | 2 tokens in `kod-machine/registry/timestamps/case/` and 2,149 in `idx-signals/paper/timestamps/`. The `checks.yml` integrity step `python3 -m kod verify` checks the tokens the KOD ledger references; no workflow step names a check of the paper tokens |
| B7 | Daily price CSV supplied to the workstation | `workstation/prices.py`: `parse_csv` | `workstation_tests/test_gate_e.py` (inline bytes) | No | None |
| B8 | GitHub Actions API workflow runs (server-side commit receipts) | `remote.py`: `GitHubActionsClient`, `remote_status` | `tests/test_audit_v2.py` (local fake server), `tests/support.py` | No | No retained responses found. The `checks.yml` integrity step runs `python3 -m kod verify` with `GITHUB_TOKEN` to check GitHub receipts |

## Named sources with no parser in idxsig or kod

| Source | Where it is parsed | Tests |
|---|---|---|
| Wikimedia (and Wikidata) | Research only: `idx-signals/research/ATTENTION_LEAD_v1/fetch.py` (Wikidata SPARQL map, per-article pageviews), `fetch_slow.py`, `fetch_slow_v2.py`, `fetch_dump.py` (monthly pageview dumps) | Out of scope |
| DefiLlama | No code anywhere in the repository. Named only in `idx-signals/research/CATALYST_REGISTER_v1/protocol.json` and Markdown documents | n/a |
| alternative.me Fear and Greed | Research only: `idx-signals/research/HERMES_NOV3_REPRO_v1/lib.py`: `load_fng`, reading `hermes_fng_alternative_me.json` in that folder. Its `PROTOCOL.md` names alternative.me, 2018-02-01 to 2026-11-02; that origin was not independently checked here | Out of scope |
| Upbit notices | No code anywhere in the repository; Markdown documents only | n/a |
| Binance public archives (`data.binance.vision`) | Outside the two packages: `tools/collect_premove_crypto.py` (tested by `idx-signals/tests/test_premove_collector.py`) and research collectors (`research/E6/collect_hourly.py`, `E7/collect_perp.py`, `PRESSURE_v1/fetch.py`, `LIQ_REBOUND_v1/collect.py`, `CRYPTO_PUMP_HISTORY_v1/`, `BINANCE_ANN_1S/fetch_ticks.py`, `BINANCE_ANN_1M/feasibility.py`, `HERMES_NOV3_REPRO_v1/fetch.py`); also `handoff/fresh-eyes-2026-11-01/backtests/` | Out of scope; not surveyed further |
| EmitenNews articles | Also in research: `idx-signals/research/UMA_IDX_v1/collect.py` | Out of scope |

## Inputs not counted as outside-data parsers

- `idxsig/timing_context.py`: caller-prepared context packs (declared calendar events, catalysts, shadow
  quotes). They are validated as declarations; no single outside format is parsed.
- `idxsig/symbols.py`: a hand-entered rename map that cites a Binance announcement URL.
- `docs/research_sources/hermes_20261104/`, read by `test_timing_research.py`: research documents checked
  against recorded hashes, not parsed as data.
- `costs/etoro_crypto_2026.json`, read by `test_timing_context.py`: owner-reported cost assumptions.

## Sourceable now (real bytes exist, no new capture needed)

| Row | Real bytes | Note |
|---|---|---|
| 2 | Production commissioning bundle (outside the repository), the same bundle the chrony fixture came from | 8 retained responses covering all five intraday endpoints |
| 8, 24 | `idx-signals/paper/sensors/raw/` | Exact bytes for 5 of the 6 sources; `edgar_8k` is re-serialized |
| 12 | `idx-signals/paper/sensors/raw/*/emitennews_dilution.json.gz` | The sitemap document type `catalysts.dilution_tags` reads |
| 21 | `idx-signals/research/GUIDANCE_REVISION_v1/fixtures/` | Exactly the `<SEC-DOCUMENT>` input `guidance_revision.submission` checks |
| 23, 27, 28 | `idx-signals/data/archive/e2_us_sec_evidence_v1/`, `e2_us_inputs_v1/` | Git LFS: needs `git lfs pull` first |
| B4 | `kod-machine/examples/companyfacts/*/submissions.json.gz` | Trimmed real responses that keep `cik` and all six `filings.recent` fields `normalize_submissions` reads |
| 5 (re-serialized only) | `idx-signals/paper/microstructure/raw/` | Depth JSON re-serialized and bars converted: tests field shape only, not the exact bytes |

All other rows need a new real capture before they can meet the owner check.

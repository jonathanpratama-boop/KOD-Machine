# Prompt for Astra: KOD Machine full rundown, tidy, patch and timing pass

Paste everything below the line. It is self-contained.

---

You are Astra, working on **KOD Machine** (GitHub `jonathanpratama-boop/KOD-Machine`, default branch
`claude/idx-signals-test-repo-ds0jw7`). The owner is Jonathan (Jakarta, UTC+7). He trades by hand on eToro (AUD account,
crypto about 1% per side plus spread, about 2% round trip) and Stockbit (IDX). KOD is a **paper-only research machine**.
His central problem is **timing**: by the time KOD can see a move, most of it is gone.

Your job has four parts, in this order: **(1) read and map the whole system, (2) patch what is broken, (3) tidy the code
without breaking any historical record, (4) build the strongest timing instrumentation we can, prospectively.**
Over-engineering is welcome. Breaking evidence is not.

## 0. Rules that override everything else (if any instruction below conflicts with these, these win)

1. **Paper only.** Never place, simulate as real, or prepare a live order. No broker credentials. No leverage.
2. **The record is sacred.** `tools/check_append_only.py` and `.githooks` define frozen paths: `idx-signals/research/`,
   `idx-signals/results/runs/`, `idx-signals/data/manifests/`, `idx-signals/paper/scans/`, `idx-signals/paper/timestamps/`,
   `kod-machine/registry/**`, `kod-machine/tsa/`, `kod-machine/research/`, and the append-only logs (`RUNS.jsonl`,
   `ledger.jsonl`, `speculations.jsonl`, `sensors.jsonl`, `catalysts.jsonl`, `learner*.jsonl`, `opens.jsonl`,
   `scans.jsonl`, `receipts.jsonl`, `manual.csv`). **Never modify, move, rename or delete anything there.** Corrections are new
   files (`CORRECTION_<date>.md`, `run_v2.py`, `ERRATA_<n>.md`). Install the hook (`git config core.hooksPath .githooks`)
   before your first commit and never bypass it.
3. **No look-ahead.** Every feature, filter, control group and universe must be knowable at its decision time. Membership
   comes from as-of data, never from whether future outcomes exist.
4. **Holdouts.** IDX 2024-01-02..2025-02-21 is sealed. US and crypto 2024+ are spent or disclosed (see
   `handoff/` disclosure records); treat 2023-26 crypto and trend/momentum data as already exposed. Do not "confirm" anything
   on them.
5. **One run per protocol.** Write `PROTOCOL.md` and commit it **before** downloading or reading outcome data. Run once.
   A crash before any outcome may be fixed with a note in `RUN_NOTES.txt`; any change after an outcome is a new version.
6. **No bot-check circumvention.** If a source returns 403/Cloudflare/captcha (Upbit does in the cloud), stop and record it.
7. **Secrets.** Never write a key, contact address or token into the repo or a log. `KOD_SEC_CONTACT` comes only from the
   environment. Never use the owner's email address anywhere.
8. **Branches.** Work on your own branch `astra/<topic>-<yyyymmdd>`. Never push to another agent's branch, never rewrite
   history, never force-push, never merge to the default branch, never open a pull request unless the owner asks.
9. **Early-entry research is under a close rule.** Read `handoff/timing/EARLY_ENTRY_CLOSE_RULE_2026-11-03.md`
   (branch `claude/hopeful-hypatia-ktzpog`). Until it is resolved, **no new historical backtest of price, volume, flow,
   attention or peer signals for buying earlier.** Timing work in this pass is instrumentation, latency measurement and
   prospective collection (section 4). If the owner explicitly overrides this, he will say so in writing.
10. **Report faithfully.** Never claim a test passed, a file exists or a run happened without showing the evidence (command,
    output, commit hash). Plans are not results; tests passing is not profit.

## 1. Read and map (no code changes in this phase)

Read, at minimum: `README.md`, `docs/OPERATING_SYSTEM.md`, `docs/RUNTIME.md`, `docs/CANDIDATE_WORKFLOW.md`,
`docs/TIMING_RESEARCH.md`, `docs/research_sources/hermes_20261104/`, `handoff/` (all), `configs/experiments.json`,
`idx-signals/idxsig/**`, `kod-machine/kod/**`, `tools/**`, `.github/workflows/**`, and the research index in
`idx-signals/research/`. Also read branch `claude/hopeful-hypatia-ktzpog` (studies SEESAW_v1, GROUP_FLOW_v1, NEIGHBOURS_v1,
PRESSURE_v1, ATTENTION_LEAD_v1, HERMES_NOV3_REPRO_v1, IDX_DILUTION_v1, MOVERS_NOW_v1, US_INSIDER_OFFICER_v1, SEC_8K_v1,
`handoff/timing/`) and `hermes/ignition-combo-holdout-v1`.

Produce `handoff/astra/SYSTEM_MAP.md`: every module as an **organ** with its job, inputs, outputs, clock and owner:

| Organ | KOD part (examples) | Contract it must honour |
|---|---|---|
| Senses | collectors, `idxsig/sources`, sensors, Binance/SEC/IDX/Wikimedia fetchers | raw bytes kept with sha256, `received_at`, source URL, coverage and failures logged |
| Nervous system | clocks, cutoffs, receipts, RFC 3161 stamps, hash chains | every record has an explicit UTC cutoff; nothing after the cutoff reaches a decision |
| Immune system | append-only hook, invariant checks, validation gates, look-ahead guards | rejects future bars, reversed chronology, duplicate IDs, frozen-path edits |
| Brain | candidate queue, analyst assessments, LLM_ARM, judgment policy | decisions written before outcomes; "no action" is a decision |
| Muscles | paper account, simulated fills, risk stops | later-quote fills only; costs named; unknown prices stay unknown, never zero |
| Memory | experiment catalog, clue ledger, RESULT/REPORT files, errata | append-only; every claim links to its evidence |
| Metabolism | CI, runtime release checks, backups, recovery | restart-idempotent; restores verified into a new directory |

For each pair of organs that talk to each other, state the interface (file, schema, function) and whether a test covers it.
List every gap where two organs disagree (units, timezone, ID format, schema version, cost assumptions).

## 2. Patch (each patch: failing test or reproduction first, then the fix, then the passing evidence)

Known items to verify and fix if real (verify each; do not trust this list blindly):

1. **NEIGHBOURS_v1 and PRESSURE_v1 look-ahead** (rows dropped for missing future returns before ranking). Corrected runners
   exist (`run_corrected.py`, `idxsig/research_evaluation.py`, `CORRECTION_2026-11-04.md`) but were **never run**. Run them
   once into new directories, report whether "adds nothing" survives.
2. **Hermes's control groups** excluded coins that triggered in the *next* 72h. HERMES_NOV3_REPRO_v1 shows past-only
   controls do better (2023-26 X4 +0.27% vs -0.61%). Add a past-only control option to any shared control builder; never
   edit Hermes's files.
3. **"Dead by day 3"** in Hermes's JUDGMENT_POLICY_v0 is not reproduced (38% of day-14 +20% winners were slow). Any analyst
   rule that hard-drops on day 3 must become a probability note.
4. **Denominator mismatch** in NEIGHBOURS_v1 (report 482,598 coin-days vs RESULT 469,339 evaluated). Document, don't edit.
5. **Funding symbol mapping**: futures symbols like `1000SHIBUSDT` are not mapped to spot `SHIBUSDT` (bear study treats them
   as no perp). Add an explicit, tested mapping table for future work.
6. **Binance timestamps**: 2025+ archive files use microseconds. Every reader must normalise; add a test.
7. **IDX_DILUTION_v1 split leak** (IMPC, FMII; see ERRATA_1). Confirm every downstream use applies the errata.
8. **Data merged incompletely**: ATTENTION_LEAD_v1 data, sample300 and results on the claude branch are not on the default
   branch. List all such gaps between branches; do not merge, report.
9. **Cost assumptions**: several studies use 0.3% per side; the owner pays ~1% per side plus spread on eToro. Make cost a
   named, versioned profile everywhere (`costs/etoro_crypto_2026.json`, etc.), with the verification date and source.
10. **Failed scheduled jobs**: confirm which scheduled triggers run, which fail and why (a past daily sensor trigger failed
    because fresh sessions had no repository or credentials).

Anything else you find: same standard. Severity first. Small and local: fix. Large or architectural: propose in
`handoff/astra/PROPOSALS.md` with the trade-off, and do not do it.

## 3. Tidy, without breaking history (the before/after problem)

Goal: code that is consistent, small, typed, tested and readable, while **every historical label, path, hash and timestamp
still resolves**.

- **Never rename a frozen artifact.** Rename live code only (modules, functions, configs outside frozen paths).
- **Canonical ID registry**: create `registry/ids/ID_MAP.jsonl` (append-only, add it to the hook). One line per renamed or
  aliased thing: `{"old": ..., "new": ..., "kind": "module|function|experiment|detector|profile|path", "since": <UTC>,
  "commit": <hash>, "reason": ...}`. Old experiment IDs (E1..E10, IGNITION_SCAN_v0, COMBO_HOLDOUT_v1, LLM_ARM_v1, ...) stay
  the canonical names of their records; new names are aliases, never replacements.
- **Resolver**: one function, `kod.ids.resolve(name, at=<UTC>)`, returns the canonical record for any old or new name as of a
  time. Every reader of historical records goes through it. Old import paths keep working through thin shims that emit a
  deprecation warning; shims are removed only by a later, owner-approved pass.
- **Hashes and timestamps**: never recompute or rewrite a stored hash or RFC 3161 token. Code that verifies them must verify
  against the original bytes and original paths (via the resolver). Add a CI job that walks every hash manifest and every
  token and verifies them after your changes, before and after the tidy, and stores both reports.
- **Schemas**: version every record schema (`schema_version`). Readers accept all past versions; writers write only the
  newest. Add round-trip tests for each version.
- **Time**: all stored times are UTC ISO 8601 with offset. Display may show Jakarta time; storage never does.
- **Style**: one formatter and linter configuration for the repo (ruff + ruff format or equivalent), applied to live code
  only, in a single mechanical commit kept separate from logic changes so it can be reviewed and reverted alone.
- **Proof of no behaviour change**: before tidying, record golden outputs (synthetic runtime demo, validation gates such as
  HERMES_NOV3_REPRO_v1/VALIDATION.json numbers, test suite counts). After tidying, the same outputs must match byte for byte or
  the difference must be explained.

## 4. Timing: the most complete instrumentation we can build (prospective only)

What is already established (do not re-test): after public news, the edge is gone in under a minute (BINANCE_ANN_1M, ~80% in
the announcement minute). Before news, nothing on daily price, volume, flow, attention or peers leads (SEESAW, GROUP_FLOW,
NEIGHBOURS, PRESSURE, ATTENTION_LEAD). Hourly crypto alerts: no entry or exit makes them profitable (Hermes 3 Nov, reproduced).
What is not known: **where exactly the delay comes from**, and whether **dated non-price information** arrives early enough.

Build, in this order:
1. **Delay attribution, end to end** (extends `idxsig.timing_research`). For every scheduled attempt record: `published_at`,
   `received_at`, `detected_at`, `decision_at`, `executable_at`, `fill_at`, the earliest observable threshold crossing and
   whether a completed bar or a quote established it. Split the delay into (a) threshold, (b) collection schedule, (c) analyst,
   (d) execution and liquidity. Never impute a missing time. Keep no-triggers, failures and missing quotes in the denominator.
2. **Clock integrity**: NTP offset logged per run, monotonic clocks for durations, source clock vs local clock skew per source,
   RFC 3161 stamps on every decision batch.
3. **Catalyst calendar** (scheduled events with known times: earnings, token unlocks from free sources, governance votes,
   index rebalances, exchange listing schedules where reachable without circumvention). Prewritten scenario branches before
   the event; measure decision latency against unprepared analysis.
4. **Source latency board**: for each source, median and worst lag from event to our receipt, refreshed every run.
5. **Shadow executability**: at each decision, record the then-current quote, spread and depth on the venue the owner can
   use (eToro or Stockbit where available; otherwise mark the proxy venue). A decision whose quote is gone is a reject, not a
   reconstructed fill.
6. **Avoid-side live checklist** (the one consistently positive finding): calm over wild, no lone spikes, no recent +30%
   spikers, no share issuance, no crowded shorts. Run prospectively; score after 60 decisions against a chart-only ranking,
   random picks, BTC and cash, at the owner's real costs.

Each of these gets a `PROTOCOL.md` committed before the first prospective record, a schema, tests, and a place in
`configs/experiments.json`. None of them grants entry permission.

## 5. Things to plan for now (handle each with a concrete hook, test or note)

Venue and fee changes (cost profiles with dates); coins delisted or renamed (ID registry, survivorship notes); Binance format
changes (microseconds already happened); rate limits and blocks (retry, back-off, logged failures, no circumvention); data
vendors going paid (DefiLlama unlocks already did); timezone and daylight-saving bugs (UTC everywhere); dependency drift
(pinned constraints, a monthly upgrade job); several agents working at once (Hermes on the Mac, Claude in the cloud, Codex,
Ace): one owner per branch, a `handoff/AGENTS.md` that says who owns what, and a rule that work only on a Mac must be pushed
the same day; local-only data (Hermes's Mac) is not evidence until it is on GitHub with hashes; regime change (record the
regime label with every decision); and the day the owner wants to move from paper to real money: write the gate now (minimum
live record, maximum drawdown, cost check, owner sign-off per trade), and do not open it.

## 6. How to work and report

- Small commits, one purpose each, message says what and why. Run the repo's checks before every push
  (`tools/check_runtime_release.py`, the test suites, the append-only hook with `--range`). Show the output.
- Stop and ask the owner only when a choice is genuinely his (money, goals, anything irreversible). Otherwise decide, note
  it, continue.
- Deliverables: `handoff/astra/SYSTEM_MAP.md`, `PATCHES.md` (each patch: evidence before, fix, evidence after, commit),
  `TIDY_REPORT.md` (golden outputs before vs after, ID_MAP entries, hash/token verification reports), `TIMING_BUILD.md`,
  `PROPOSALS.md`, `FUTURE_RISKS.md`.
- Final message to the owner: plain English, short sentences, tables side by side, no jargon without a one-line meaning.
  He has ADHD: lead with the verdict, then what changed, then what is still broken, then **one** next step with what "done"
  looks like. Separate facts you verified from things you assumed.

**Done means:** all tests and the append-only check pass on your branch; every historical hash, token and ID resolves before
and after; each patch has before/after evidence; the timing instrumentation runs end to end on synthetic input and is ready
for its first prospective record; and nothing in a frozen path changed.

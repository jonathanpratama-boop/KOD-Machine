# KOD fix plan: closing the "expert human would beat KOD" gaps

Written 2026-11-04 for the owner and every agent (Claude, Ace, Astra, Codex, Hermes). Evidence was measured on the default
branch `claude/idx-signals-test-repo-ds0jw7` at `dbb27ea5c` unless stated. Each fix states what is wrong, the exact
change, how the owner can check it without reading code, and what must not be touched.

**Standing constraints for every fix:** paper only; frozen paths and append-only logs untouched (corrections are new
files); the running 30-slot cohort on 159.65.2.145 is not modified (its plan pins commit `dbb27ea5c` and checks 527 files);
fixes land on a branch and reach main only with the architect's approval (Fix 4).

---

## Fix 1: one author's blind spot in both code and tests

**Evidence.** `idx-signals/idxsig/runtime/timing.py:60` reads `fields[3]` of `chronyc -c tracking`. Real chrony output has
14 fields (`refid, ref name/IP, stratum, ref time, SYSTEM OFFSET, ...`), so field 3 is the reference *time*
(1793795343.59 on the server), not the offset (0.002434953 s). `idxsig/runtime/timing_evidence.py:~178` re-checks the
same wrong field, and `tests/test_timing_evidence.py:88` uses an invented 13-field sample. Code, verifier and test agree
with each other and disagree with reality.

**Change.**
1. New parser version `CHRONY_TRACKING_V2`: accept only 14 fields, read field 4, else `MEASUREMENT_FAILED` (never guess).
2. The verifier accepts both versions: records written by v1 keep their stored value and are reported as
   `OFFSET_FIELD_DEFECT_V1` with the true offset recomputed from the retained raw stdout; v2 records are checked against field 4.
   No stored record is rewritten.
3. Real-sample fixture: `idx-signals/tests/fixtures/real/chronyc_tracking_20261104T123000Z.txt` (the server's actual
   output from the commissioning bundle). Test asserts offset 0.002434953 and that the old 13-field shape is rejected.
4. **Real-sample rule (all parsers of outside data):** each gets at least one fixture captured from the real source.
   Inventory the parsers (chrony, Binance klines/book/depth/archives, SEC, IDX, EmitenNews, Wikimedia, DefiLlama,
   alternative.me, Upbit notices) and list which lack one in `handoff/REAL_SAMPLE_INVENTORY.md`; add the missing ones.
5. **Role split from now on:** for new code, a different agent writes the tests from the protocol/spec before seeing the
   implementation.

**Owner check.** The test log shows the real server sample giving 0.002434953 s. The inventory lists zero parsers without a real sample.
**Effort.** 1-2 hours (items 1-3); about a day (item 4). **Who.** Claude (repo only). The server keeps v1 until its cohort ends.

---

## Fix 2: look-ahead mistakes in study scripts

**Evidence.** The shared library is well guarded (46 test files exercise future-leak cases). The study scripts are not:
none of the 83 `idx-signals/research/*` folders has its own tests, and every look-ahead defect found so far was in study
code (NEIGHBOURS/PRESSURE dropped rows with missing future returns; Hermes's controls excluded coins that triggered in the
next 72h; the PATHS bucket order hid slow winners).

**Change.**
1. **Truncation test** (`tools/check_no_lookahead.py`), works on any study that writes dated decisions: run the study on
   full data, then again with all data cut off at a date T. Every decision dated on or before T must be identical in both
   runs. Repeat for several T. Any difference means a decision used data from after its own date.
2. **Scramble test** for studies that separate deciding from scoring (`idxsig/research_evaluation.py` pattern): replace
   every value after each decision time with noise; the frozen decision table must not change.
3. Prove the tool works: a deliberately leaky toy study must FAIL and a clean twin must PASS, as committed tests.
4. Make it part of every new protocol: "passes check_no_lookahead" is a required line before the run.
5. Run the already-written corrected runners once into new folders (they are corrections of existing studies, not new
   early-entry searches): `NEIGHBOURS_v1/run_corrected.py` and `PRESSURE_v1/run_corrected.py`. Inputs exist
   (`rows.csv.gz`, `taker.csv.gz`). Report whether "adds nothing" survives.
6. Old frozen studies are not edited; the experiment catalog marks each as `LOOKAHEAD_CHECKED` or `UNCHECKED`.

**Owner check.** The toy leaky study fails; every new study's report shows "look-ahead check: PASS"; the catalog shows a count of checked vs unchecked.
**Effort.** About a day (1-4); 1-2 hours (5). **Who.** Claude or Astra.

---

## Fix 3: sprawl

**Evidence.** 15 core files exceed 800 lines (largest `idxsig/paper.py` 2,323, `e5.py` 2,227, `cli.py` 2,045,
`catalysts.py` 2,044). 159 of 276 study scripts read raw files directly (153 also use shared `idxsig` code). 7 branches are
not merged into main: `claude/hopeful-hypatia-ktzpog`, `hermes/ignition-combo-holdout-v1`, `hermes/info-magnet-v0`,
`hermes/nov3-studies-v1`, `integrate/trend-account-20261101`, `data-archive`, `moonshot-tools`.

**Change.**
1. **Shared-data rule:** new studies load data only through shared, as-of-aware loaders (one per source, with timestamp-
   unit normalisation built in). A CI warning flags new study scripts that open raw files directly; old ones are exempt.
2. **Branch rule:** at most 5 open working branches; merge or archive within 7 days. Proposed now: merge the research
   folders of `claude/hopeful-hypatia-ktzpog` and the three Hermes branches (append-only additions); keep `data-archive`;
   `moonshot-tools` is untouched by owner instruction; review `integrate/trend-account-20261101`.
3. **Big files:** split only inside an architect-approved tidy that repeats Astra's equivalence proof (identical code
   structure and golden outputs). Byte-pinned files (`runtime/account.py` and the 10 others in `tools/live_code_style.json`)
   are never reformatted.

**Owner check.** Open-branch count is 5 or fewer; the CI warning appears on a test study that reads raw files.
**Effort.** Rule and warning half a day; merges 1-2 hours; splitting gradual. **Who.** The architect.

---

## Fix 4: no single architect

**Evidence.** Not in code; in history: five agents, one 558-file integration commit, all agents commit as the same
GitHub user, so GitHub reviews cannot tell them apart.

**Change.**
1. The owner names **one architect** (proposed: Astra, which wrote `handoff/astra/SYSTEM_MAP.md` and the equivalence-checked tidy).
2. Only the architect merges into main (daily paper bots excepted for their log paths). One builder works on main's code at a time.
3. Every merge into main adds `handoff/merges/<date>-<branch>.md` answering the six owner questions (below), and the merge
   commit message names the architect. A CI check fails a merge of code without that note.

**Owner check.** Each merge has a short note with six yes/no answers. **Effort.** 30 minutes plus the owner's decision.

---

## Fix 5: domain judgment

**Evidence.** 83 studies and about 70 counted trials to establish what a retail-trading professional would have said up
front: an eToro/Stockbit trader cannot win races measured in minutes.

**Change.**
1. **Feasibility gate**, a mandatory first section of every new protocol, answered before any data is touched:
   - *Executable?* Venue, round-trip cost (eToro crypto about 2%, owner estimate), speed needed vs speed available.
   - *Known answer?* Two or three published sources or prior KOD studies on the same question, with what they found.
   - *Decision value?* Which money decision changes, and which result would change it.
   Any "no" or "nothing" means NO-GO, recorded, not run.
2. **One independent human review** (quant developer, a few hours; cost estimate a few hundred US dollars, unverified):
   scope (a) the evidence system (locks, look-ahead guards, controls), (b) the main conclusion ("price/daily signals do not
   time entries for this owner; avoid filters repeat"), (c) the INFO_MAGNET result when it exists. Deliverable: a 1-2 page memo.

**Owner check.** Every new protocol opens with three short answers; the memo exists. **Effort.** Gate: 1 hour to add to the template.

---

## Fix 6: operations

**Evidence.** No alerting code anywhere in the repo. GitHub cron runs start up to 7 hours late. On the server, one failed
slot halts all later slots (`/var/lib/kod/schedule/HALTED.json`) and nobody is told. Ongoing backups are on the same server.

**Change (server; Ace, because Claude cannot reach it).**
1. **Dead-man's switch:** a separate timer, 12 minutes after each slot, runs `kod-status`. All due slots CAPTURED and not
   halted: ping a free monitor (for example healthchecks.io). Otherwise ping its fail URL. Missing ping (server down) also alerts.
   The monitor alerts the owner's phone. Does not modify the frozen plan, `observe.py` or `kod-observe.timer`.
2. **Daily line** to the owner (email or a Telegram bot): "KOD <date>: slots a-b CAPTURED, 0 failed, next <time> WIB".
3. **Off-server copy:** after each backup, copy the archive off the server (DigitalOcean backups, about 20% of the droplet
   price, or a push to a dedicated GitHub branch with a write-limited deploy key).
4. Time-sensitive jobs move from GitHub cron to the server timer after this cohort.

**Owner check.** A test alert reaches the phone; one daily line arrives; a backup exists somewhere other than the server.
**Effort.** About 1-2 hours. **Who.** Ace.

---

## The owner's six questions before any merge into main
1. Were the tests written by a different agent than the code?
2. Does every parser of outside data have a real-sample test?
3. Does every study pass the look-ahead check?
4. Did the architect approve it?
5. Could I actually trade this, and could the result change what I do?
6. Does it alert me when it breaks?

## Order
| # | Fix | Who | Effort | Why this order |
|---|---|---|---|---|
| 1 | Fix 6 dead-man's switch + daily line | Ace | 1-2 h | Protects the experiment running now |
| 2 | Fix 1 items 1-3 (clock parser v2, verifier, real sample) | Claude | 1-2 h | Next cohort correct from the start |
| 3 | Fix 2 items 1-5 (look-ahead tool, corrected runners) | Claude / Astra | ~1 day | Closes the most common research defect |
| 4 | Fix 4 architect + Fix 5 gate | Owner decides, then 1 h | — | Rules before more building |
| 5 | Fix 1 item 4, Fix 3 | Architect | gradual | Hygiene |

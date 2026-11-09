# IDX lower-limit (ARB) correction: before and after on the existing ledger

Date 2026-11-09. Branch `claude/idx-arb-oct2026-correction`, base `04927b3c4`. Paper trading only.
The ledger and the speculation register are byte-identical to the base commit (hashes in section 10); this report only replays them.

Two terms. **ARB** is the exchange's lower price limit, the largest fall allowed in one day. The simulator treats a close at or below it as a **locked** session: nobody could be assumed to buy, so a sale that day is not possible and the sale rolls to the next session. **ARA** is the upper limit.

## Bottom line

- **Verdict.** The October 2026 rule change alters **14 of the 93 scored hypothetical IDX outcomes**, flips no verdict, and will alter at least 3 more (ALKA, DFAM, BSWD) if the correction is not in place before the nightly job scores them. None of the 126 IDX decisions was a buy and none of the 93 outcomes was executed, so these records contain no executed loss, real or paper. The figures below describe hypothetical what-if trades.
- **Decision needed today.** The IDX scoring job runs about 10:20 UTC (17:20 Jakarta) on weekdays and pushes to `claude/idx-signals-test-repo-ds0jw7`. Today it is offered six decisions, four of them new (ALKA, KONI, MKNT, POLI; section 6). Merge before then, or pause the IDX scoring step (scans are unaffected by this change). An OUTCOME row is permanent unless the owner approves a revision (section 9).
- **What was wrong.** `idxsig/market.py` jumped from the 2026-09-28 rule (lower limit 15%) straight to a 2027 rule. It never learned that the exchange cut the lower limit to **7% on 2026-10-19** and, for reference prices Rp11 to Rp14, to **a nominal Rp1 on 2026-10-20**. Every lock at the lower limit since 2026-10-19 was judged against 15%.
- **How firm the 14 are.** They rest on two modelling choices that the exchange rules do not settle. First, a close at or below the lower limit counts as a day the holder could not sell. With a strict "below the limit" test, 1 of the 93 records changes (FLMC), not 14. Second, every name is held to the regular-board 7% limit; with a 10% limit for every name, none changes. In 13 of the 14 deciding bars the name traded higher earlier in the session and closed at the limit price; only TRON on 2026-10-19 traded at one price all day. Both choices predate this change.
- **What does not change.** Entry fills, the upper limit, position sizing, the frozen policy and every recorded row.
- **Other records that use the same lock test.** An independent sweep of the code found three persisted families that store lock-derived values: the ledger OUTCOME rows (above), the speculation register (1 of its 23 IDX rows would resolve differently) and the **catalyst register, where 9 of its 14 IDX rows change** (17 of 84 simulated sales roll one to three sessions later) and its published line moves from +1.16% and 64% to +1.35% and 71%. Neither register has a rescore path. The learner's forecasts move only through training labels (raw probabilities by at most 0.04, published calls unchanged). Section 6.
- **Not known.** The decree texts were not read (idx.co.id refused the download). Board membership of each stock is not in the data. Nothing is confirmed for 2027. See section 7.

## 1. What changed in the code

Only `idxsig/market.py` (plus the README schedule and tests). Lower limit by date, regular boards:

| From | Lower limit (ARB) | Rp1-10 | Rp11-14 |
|---|---|---|---|
| 2026-09-28 | 15% | -Rp1 | 15% |
| **2026-10-19** | **7%** | -Rp1 | 7% (the formula gives ARB = reference; the real limit that day is unknown, see section 7) |
| **2026-10-20** | **7%** | -Rp1 | **-Rp1** |
| after 2026-12-31 | **not confirmed**: the 2026-10-20 rule is carried forward and flagged | | |

The upper limit, the tick table, the Rp1 minimum price and every earlier regime are unchanged (a golden-master test pins the outputs for a grid of references on 40 dates that cover every regime from 2019-07-29 to 2026-10-18).
The announced 2027 symmetric lower limit is no longer executable. After 2026-12-31 `limits()` carries the last confirmed rule forward, emits `RulesUnconfirmedWarning`, and the carried-forward period is its own regime labelled `UNCONFIRMED`. It never raises, because US and crypto runs share the same code path. `execution.py` and `paper.py` are byte-pinned by frozen records and are not touched.

## 2. Populations, recounted from the ledger file

Ledger snapshot: 755 rows (SCAN 79, DECISION 400, OUTCOME 276), sha256 `c1a67890577f7495212d1d9b3abbc97922bf741a007fc422c8225f5a87cd4395`, head record hash `4ee35255de041da3b75af78fdee3062560918affb97e64aa4b699077655277e8`.

| Population | Count |
|---|---|
| IDX decisions (122 marked IDX, 4 with signal session 2026-10-07 and no market field, which the code treats as IDX) | 126 |
| IDX OUTCOME rows (one per scored decision, no duplicates, no revision rows, no repeated decision ids) | 93 |
| Decisions with signal on or after 2026-10-19 | **88** (57 scored, 31 pending) |
| Hypothetical trades inside that set | **27** |
| All scored records that carry a hypothetical trade | 40 |
| Scored records whose path touches 2026-10-19 or later | **82** (35 with a trade) |
| Pending decisions with no outcome yet | 33 (31 window still open, 2 complete but never scored) |

The figures "88 decisions" and "27 hypothetical records" are both correct for the definition "signal on or after 2026-10-19". They are not the exposed set: 82 records (35 trades) have a scored path that reaches 2026-10-19 or later, and 4 of the 14 changed records have signals before 2026-10-19.

## 3. The 14 records that change

Method: replay each record with the real scorer under the shipped rules and under the corrected rules on the same price data, and compare replay with replay. Net returns are after fees, in percent of the entry price; "pp" is percentage points, "sess" is sessions. The 16-digit values, both record hashes and the other 112 rows are in `impact_records.csv` (`source_decision_id`, `source_outcome_record_hash`, `source_decision_record_hash`).

| Decision id (after SCAN-) | Effect | Recorded in ledger | Replay, shipped rules | Replay, corrected rules | Change | Deciding bar |
|---|---|---|---|---|---|---|
| 2026-10-12-F1_ARA-ZONE | EXIT LATER | 10-19 invalidation -21.47% | 10-19 invalidation -21.47% | 10-20 invalidation -18.28% | +3.19 pp, +1 sess | at the 7% limit |
| 2026-10-14-F1_ARA-SONA | EXIT LATER | 10-19 invalidation -21.09% | 10-19 invalidation -21.09% | 10-20 invalidation -22.86% | -1.77 pp, +1 sess | at the 7% limit |
| 2026-10-14-F1_ARA-TRON | EXIT LATER | 10-19 invalidation -20.09% | 10-19 invalidation -20.09% | 10-20 invalidation -16.61% | +3.47 pp, +1 sess | at the 7% limit |
| 2026-10-16-F1_ARA-CBPE | EXIT LATER | 10-21 invalidation -13.06% | 10-21 invalidation -13.06% | 10-22 invalidation -16.27% | -3.21 pp, +1 sess | at the 7% limit |
| 2026-10-20-F1_ARA-HATM | EXIT LATER | 10-23 invalidation -13.25% | 10-23 invalidation -13.25% | 10-26 invalidation -17.27% | -4.02 pp, +1 sess | at the 7% limit |
| 2026-10-20-F1_ARA-PNSE | NO OUTCOME | 10-28 horizon -4.85% | 10-28 horizon -4.85% | no outcome (horizon 10-28 locked) | n/a | at the 7% limit |
| 2026-10-22-F1_ARA-BUKK | EXIT LATER | 10-26 invalidation -6.95% | 10-26 invalidation -6.95% | 10-30 invalidation -25.74% | -18.78 pp, +4 sess | at the 7% limit |
| 2026-10-22-F1_ARA-PNSE | EXIT LATER | 10-27 invalidation -13.32% | 10-27 invalidation -13.32% | 10-29 invalidation -22.45% | -9.12 pp, +2 sess | at the 7% limit |
| 2026-10-23-F1_ARA-ASLI | EXIT LATER | 10-28 invalidation -13.37% | 10-28 invalidation -13.37% | 11-02 invalidation -26.92% | -13.56 pp, +3 sess | at the 7% limit |
| 2026-10-23-F1_ARA-FLMC | EXIT LATER | 10-27 invalidation -9.57% | 10-27 invalidation -9.57% | 10-28 invalidation -6.30% | +3.28 pp, +1 sess | below the 7% limit (wider-limit name?) |
| 2026-10-23-F1_ARA-KONI | NO OUTCOME | 11-02 horizon +5.13% | 11-02 horizon +5.13% | no outcome (horizon 11-02 locked) | n/a | at the 7% limit |
| 2026-10-23-F1_ARA-PTSP | NO OUTCOME | 11-02 horizon +8.36% | 11-02 horizon +8.36% | no outcome (horizon 11-02 locked) | n/a | at the 7% limit |
| 2026-10-23-F1_ARA-TOBA | EXIT LATER | 10-29 invalidation -16.37% | 10-29 invalidation -16.37% | 11-02 invalidation -23.87% | -7.49 pp, +2 sess | at the 7% limit |
| 2026-10-29-F1_ARA-YPAS | EXIT LATER | 11-03 invalidation -13.04% | 11-03 invalidation -13.04% | 11-05 invalidation -22.14% | -9.10 pp, +2 sess | at the 7% limit |

Reading it: a name that falls about 6 to 9 percent a day sits locked at the 7% limit on each of those days (one to five days in these records), so a stop-out that the 15% rule filled on day one cannot be filled until the run ends. All 14 deciding bars closed 6.1 to 9.2 percent below the previous close, 13 of them exactly at the modelled 7% limit price. The 3 NO OUTCOME records have a locked fifth-session close; the legacy scorer never rolls past its horizon, so no OUTCOME would be written (two of the three were missed gains). The second October change, Rp1 for Rp11-14, adds no lock to any record. The whole effect is the 7% percentage. Each decree is applied to the whole session of its effective date; three of the 14 records (ZONE, SONA, TRON) turn on 2026-10-19 itself.

## 4. Unchanged cases

| Category | Records | Meaning |
|---|---|---|
| UNCHANGED | 68 | path reaches 2026-10-19 or later, replay identical: 47 had no trade (the lower-limit flag is never consulted), 8 traded across a newly locked session with no effect, 13 traded with no newly locked session |
| NOT AFFECTED | 11 | scored path ends before 2026-10-19 (5 trades, 6 without a trade) |

The correction only adds locks, so no record becomes scorable and none changes verdict.

## 5. Aggregates (hypothetical paper trades of rejected candidates)

| | Recorded | Shipped rules (replay) | Corrected rules (replay) |
|---|---|---|---|
| Hypothetical trades | 40 | 40 | 37 |
| Mean net return | -8.66% | -8.68% | -11.17% |
| Median net return | -9.47% | -9.70% | -10.21% |
| Same 37 trades in both, mean | | -9.62% | -11.17% |
| Correct rejections (of 93 decisions) | 88 | 88 | 87 |
| Missed gains | 5 | 5 | 3 (and 3 records without outcome) |

The corrected mean is partly survivorship: the 3 trades that drop out averaged +2.9% under the shipped rules, so dropping them lowers the mean on its own. Market-wide the correction turns 1,892 (ticker, session) cells from sellable to locked (2,858 to 4,750 locked cells), 349 of them on 2026-10-19. Nothing turns the other way and the upper-limit flags are identical.

## 6. Unresolved cases

**Pending decisions.** `paper.due()`, run on the committed ledger with today set to each date, offers six decisions to today's run: ARII and BIKE, which it offers every night and never scores, and the four with signal day 2026-10-30: ALKA, KONI, MKNT and POLI. ALKA and POLI already have their old-rule exits fixed (invalidation on 11-04 and 11-05), KONI (signal 10-30) depends on the 2026-11-09 bar, and MKNT has no hypothetical trade. Tomorrow's run adds the 2026-11-02 signals DFAM, AKPI, ROCK, BTEK and MKNT: DFAM's old-rule exit is fixed (11-05); AKPI and ROCK have locked sessions on their paths and no exit yet. On 2026-11-11 it adds the 2026-11-03 signals BSWD (old-rule exit fixed, 11-06), TMPO, FLMC, AIMS and MKNT. `due()` says a window can have ended, not that a row is written. Decisions with a flipped bar on the path so far (all closes exactly at the modelled 7% limit), and the two that are stuck for reasons unrelated to this change:

| Pending decision (after SCAN-) | Sessions that lock only under the corrected rule | State on the bars seen so far |
|---|---|---|
| 2026-10-08-F1_ARA-ARII | none | trade entered, no exit yet under either |
| 2026-10-14-F1_ARA-BIKE | none | trade entered, no exit yet under either |
| 2026-10-30-F1_ARA-ALKA | 11-02, 11-03, 11-04 | **already differs**: shipped rules would exit 11-04 invalidation; corrected rules have no exit yet |
| 2026-10-30-F1_ARA-KONI | 11-02, 11-03, 11-06 | trade entered, no exit yet under either |
| 2026-10-30-F1_ARA-POLI | 11-03 | same exit under both (11-05 invalidation) |
| 2026-11-02-F1_ARA-AKPI | 11-03 | trade entered, no exit yet under either |
| 2026-11-02-F1_ARA-DFAM | 11-03, 11-04, 11-05, 11-06 | **already differs**: shipped rules would exit 11-05 invalidation; corrected rules have no exit yet |
| 2026-11-02-F1_ARA-ROCK | 11-03, 11-04 | trade entered, no exit yet under either |
| 2026-11-03-F1_ARA-BSWD | 11-04, 11-05, 11-06 | **already differs**: shipped rules would exit 11-06 invalidation; corrected rules have no exit yet |
| 2026-11-04-F1_ARA-BOBA | 11-05, 11-06 | trade entered, no exit yet under either |
| 2026-11-05-F1_ARA-AGAR | 11-06 | trade entered, no exit yet under either |
| 2026-11-05-F1_ARA-BELL | 11-06 | trade entered, no exit yet under either |

ARII (signal 10-08) has a locked horizon bar under the old 15% limit and BIKE (signal 10-14) a suspended one, so the legacy scorer returns no outcome and `paper.due()` offers them again every night. That failure mode predates this change. 8 pending decisions (BIKE once, MKNT five times, TMPO twice) are on names with no 2026-11-06 bar in the final pull; none has a flip to miss, because BIKE is the suspended case above and MKNT and TMPO have no hypothetical entry.

**Speculation register.** `paper/speculations.jsonl` holds 23 IDX RESOLUTION rows. 21 use next-session returns only and cannot change. 2 BASE5 rows use the lock at their horizon day. One of them, ALKA BASE5 (`SPEC-SCAN-2026-10-29-F1_ARA-ALKA`), would not have resolved on 2026-11-06 under the corrected rules, because twins KDTN and WBSA closed locked exactly at the 7% limit on their horizon day. YPAS BASE5 is unchanged. The shipped-rules replay reproduces 22 of the 23 recorded rows; the miss is the TMPO NEXT1 row of 2026-11-04, a data-timing difference in a window that never reads the lock flags. The recorded rows were not touched.

**Catalyst register.** `paper/catalysts.jsonl` holds 14 IDX RESOLUTION rows (index run-up window, signal 2026-10-28: buy the 2026-10-29 close, sell the 2026-10-30 close; 84 simulated trades, 14 candidates and 70 twins). They use the same lower-limit test through `speculation.simulate`, and the first replay above did not cover them; a reviewer found the gap. A separate analyst replayed them, and the reviewer's scratch replay gives the same result. The shipped-rules replay reproduces all 14 recorded rows (differences only in the last floating-point bits, at most 3.3e-16). Under the corrected rules **9 of the 14 rows change** (CUAN, HEAL, ISAT, MIKA, PGEO, SCMA, SMGR, SMRA, TINS) and 5 do not (AALI, ELSA, PTBA, TKIM, UNVR). 17 of the 84 trades sell later, 14 of them by one session, 1 by two and 2 by three. Each of the 17 closed 6.3% to 7.0% below the previous close on 2026-10-30, except LUCY, which closed 10.0% down and is therefore a wider-limit name. Two candidate exits move: CUAN from -7.20% to -0.89% and ISAT from -7.20% to -2.44%. The register's published line (`paper/CATALYSTS.md`, RUNUP: paired 14, mean signed difference +1.16%, share with the flow 64%) would read +1.35% and 71%, and one graded statement flips (ISAT with the flow: no to yes). The register labels IDX_INDEX "never tested"; the shift is 0.19 percentage points against a standard error of 1.10, from 14 sets of one index review. The recorded rows were not touched. Row-by-row table: `other_families/report.md`.

**Derived forecasts and pending register work.** The learner (`paper/learner_v2.jsonl`) trains on graded register statements, so the changed catalyst labels would move the raw probabilities of 202 of its 238 forecasts (24 of 26 IDX) by at most 0.040; published probabilities and calls do not change. The speculation row for ALKA, pending under the corrected rules, would move the published probability of 3 IDX forecasts by at most 0.024. Sealed forecasts are facts and nothing here edits them. Work still pending is computed by whichever `market.py` is live when it resolves: 24 BASE5 sets in the speculation register and 14 POST20 windows in the catalyst register (not before 2026-11-27), the first rows to be written under whichever rules are in force.

**What-if (labelled, not part of any count).** If the scorer kept rolling past the horizon to the first sellable close: PNSE (signal 10-20) exits 10-29 at -9.29% (shipped -4.85%), KONI (signal 10-23) exits 11-04 at -0.11% (shipped +5.13%, a missed gain becomes a correct rejection), PTSP stays locked through 2026-11-06.

## 7. How sure the numbers are, and what is not known

- **Two separately written replays agree.** Two analysts wrote separate harnesses from the same inputs, without seeing each other's work. They match on all 126 records (category and exits identical, net returns within 1e-9). A third, earlier probe by a reviewer also found 14 changed trades and the same three records without outcome. For the catalyst register, a reviewer's scratch replay and a separate analyst's harness agree on the 9 changed rows and the published line. Both harnesses run the repository's own scorer on the same price pull, so this agreement checks the harness code and the bookkeeping, not the scorer or the rules. A from-scratch recomputation of the documented rules reproduced all 125,120 lock flags in both rule sets with no disagreement; that checks the code against the stated rules, not the rules against the exchange.
- **Baseline gate.** Replaying the shipped rules reproduces 90 of the 93 recorded outcomes field for field. The 3 differences are not rule effects: BTEK is a floating-point knife-edge on a discovery flag (0.2999999999999998 against 0.30000000000000004), and CARE and SOHO were scored from a price pull started at 08:13 UTC, before the 09:30 UTC time the code treats as the final bar, so their last bar was still moving. All 9 outcomes of signal day 2026-10-21 came from that pull. The ARB effect is always measured as corrected replay minus shipped replay, so these cannot leak into it. The replays ran on Python 3.13.17, numpy 2.5.3 and pandas 3.0.5, outside the repository's tested range (3.12, numpy 2.3.5, pandas 2.2.3); the gate (largest residual 8.9e-16) is the evidence that this does not move the results.
- **Final-bar replay.** Only one raw price pull survives (2026-11-06, 920 tickers, hashes verified). Every record is replayed on it, not on the pull that wrote it.
- **The rules rest on secondary sources.** The decree texts (Kep-00157, Kep-00158) were not read: idx.co.id returned HTTP 403, one retry with a browser-style header was refused by the session's policy and not pursued. The dates, 7% and the Rp11-14 reading come from the IDX trading-mechanism web page, IDX press releases as reposted by brokers, and press reports; the 2026-12-31 end date of the 7% rule is also stated in OJK press release SP 219/OJK/DKPU/XI/2026 (2026-11-05, read directly). The sources were re-read on 2026-11-09 at 05:43 to 06:05 UTC with no change (`spec_pack/RECHECK_20261109.md`); MSCI's index review of 2026-11-12 is the next date that could move BEI. The rounding rule (ARA floored and ARB ceiled to the tick of the limit price's own band) is inferred from 20 observed limit prices.
- **2026-10-19, references Rp11-14.** The formula gives ARB = reference, but BTEK and TAXI closed 25% below it that day (BTEK traded as low as Rp7 from Rp12) and PPRO traded from Rp14 down to Rp10, below every candidate limit. The real limit that day is unknown. No scored record has such a bar on its path.
- **Boards.** The October decisions cover the Main, Development and New Economy boards; the Acceleration and Special Monitoring boards keep 10%. The data has no board field, so every name gets the regular rule. 46 of 920 names show a traded close below their modelled 7% limit since 2026-10-19 (not counting BTEK and TAXI on 2026-10-19). All 168 such closes are within 10% of the previous close, which marks them as wider-limit names, not proof of a board. Of the 14 changed records only FLMC belongs to such a name; without it 13 change.
- **The lock convention carries most of the effect.** The scorer treats "close at or below the lower limit" as a session in which the holder could not sell, whatever the volume. A real close at the limit does not prove that nobody could sell. For references up to Rp14 one tick is the whole limit, so every down close counts as a lock: 12 of 12 down closes among 37 traded Rp11-14 bars since 2026-10-20 were flagged although the volumes were heavy. This convention predates this change and lives in the pinned `execution.py`. No scored record is affected by the Rp11-14 case.
- **After 2026-12-31 nothing is confirmed.** BEI called the symmetric 2027 plan conditional and replaced the decree twice in October. A third-party source says the symmetric limits return on their own unless BEI acts (not verified). The convention adopted here locks at least as many closes as any wider limit would, which is the cautious choice for whether a sale was possible. Its effect on scored returns has no determined sign, because the legacy scorer drops a decision whose horizon close is locked.

## 8. Separate findings (not fixed here)

1. **A price pull before the close.** On 2026-10-29 the scoring pull started at 08:13 UTC (15:13 Jakarta time), before the close, and finished windows on a bar that was still moving. 9 outcomes (all signal 2026-10-21) were scored that way; 2 of them (CARE, SOHO) differ from the final bars. `score_pending` and `due` do not check that the session is closed (only the scan does). Fixing it needs `paper.py`, which is pinned.
2. **The legacy scorer never rolls past a locked horizon bar.** It drops a trade whenever its fifth-session close sits at the lower limit, whatever the trade's return so far. Under the 7% limit that removes 3 of 40 trades: PTSP +8.36%, KONI +5.13% and PNSE -4.85% under the shipped rules (ranks 3, 4 and 10 of 40), so the mean of the remaining trades is lower. The plan text recorded in all 100 IDX PASS decisions says "a sale rolls while locked at ARB". The execution model (`execution.execute`) does roll. Whether the scorer should roll is an owner decision. Operator note: a decision with no outcome whose horizon close is between 7% and 10% below the previous close may not really have been locked.
3. **Hashed plan text still states the old limit.** Every IDX decision record carries `plan.gap_risk`: "...a gap through it makes the loss larger, up to 15% per session while locked at ARB" (`paper.py` line 1112). 97 records have it, 64 of them written for signals since 2026-10-19, and every scan that finds a candidate adds more. Since 2026-10-19 the lower limit is 7%, so the sentence misstates the exchange limit. The frozen policy parameter `max_stop_distance` (0.15, `paper.py` line 106) is commented in the code as the IDX lower-limit distance. Two other 15% sentences ("15% below the entry", `paper.py` lines 1108 and 1131) are in the execution-plan branch, which no recorded IDX decision has used. `paper.py` is pinned by frozen records, so none of this is changed here; the architect decides whether a text change is worth a new policy version.
4. **The warning repeats and reaches other markets.** `Market.build` computes the IDX limits before it discards them for markets without limits, so after 2026-12-31 every US and crypto build emits the IDX `RulesUnconfirmedWarning`, once per `Market.build` call under the default filter. Harmless unless a job escalates warnings; removing it needs `execution.py`. One existing test (`tests/test_sensor_v2.py`, through the US helper in `tests/test_catalysts.py`) already builds bars dated into 2027 and emits it.
5. **Stale pins.** `market.py` changes sha256. Three completed protocols pin the old hash `e9e9328a` (MSCI_DELETION_v1, MSCI_DELETION_OPT_v1, MSCI_DELETION_OOT_v1); their runners will now refuse to run again, but all three already have a completed run whose stored results are untouched. Seven other studies pin an older hash `b956576f` that was already stale (the two CATALYST_REGISTER_v1 kill tests, E9, IDX_INSIDER_NEWS_OOT, SLOW_10K, US_8K_ITEMS, US_INSIDER_BUY). `handoff/claude/LINT_CLEANUP_20261104.md` and `ruff.toml` still describe the `market.py` pin as intact.
6. **Panel QA after the next panel build.** `panel._limit_qa` will count closes 7 to 10 percent below the reference of wider-limit names as violations, and a real Rp11-14 violation is counted in the Rp50 bucket because the Rp50 floor check no longer applies. New panel manifests list the new regimes; old manifests are frozen files and are not recomputed.

## 9. Ways to correct the ledger (not done; needs the owner's approval)

- Leave the recorded rows as they are. They are a true record of what the code did on those dates.
- For the 11 shifted records, and for any pending decision scored under the old rule before the merge, write revision rows with `paper-score --rescore ID --reason ...`; the `revises` link keeps the original. Tried on a scratch copy of the corrected code, `--rescore` of the 14 changed records writes 11 revision rows.
- The 3 records without an outcome under the corrected rules (PNSE signal 2026-10-20, KONI and PTSP signal 2026-10-23) get no row from `--rescore`: `score()` returns None and `score_pending` skips it. An unscorable status needs a change to `paper.py`; until then the only record of them is this report.
- The speculation and catalyst registers have no rescore command: `speculation.due` and `catalysts.due` skip any (set, window) that already has a RESOLUTION, and no code writes a `revises` link for them. A corrected RESOLUTION (ALKA BASE5, and the 9 catalyst rows) needs new code and the architect's decision.
- If the scoring step is not paused and the correction is not merged first, today's run writes OUTCOME rows for ALKA, KONI and POLI under the old rule.

## 10. Inputs and reproduction

| Input | Value |
|---|---|
| Ledger snapshot | `idx-signals/paper/ledger.jsonl` at `04927b3c4`, sha256 `c1a67890577f7495212d1d9b3abbc97922bf741a007fc422c8225f5a87cd4395` |
| Speculation snapshot | `idx-signals/paper/speculations.jsonl` (277 rows), sha256 `0118f0c87d96e1a5fc6726d2668536d93e9c45ddc7e2a0dbdbaff47264542b04` |
| Price manifest | `yahoo_recent-20261106T101853Z.jsonl`, sha256 prefix `3a27d3445b3d`, 920 payloads, every payload hash verified |
| `market.py` before | sha256 `e9e9328af46a871d6a8bc929ab10889f071bcdbef4be6d85f6fe1d26bd2f9cbc` |

Files here: `impact_records.csv` (126 rows: 93 outcomes and 33 pending), `baseline_gate.csv` (93 comparisons with a diagnosis for each difference), `flipped_bars_on_paths.csv` (every flipped bar on the path of a scored record; for pending decisions see `flip_sessions_on_path` in `impact_records.csv`), `speculation_replay.csv` and `speculation_base5_trades.csv`, `other_families/` (the catalyst register and learner replay: `report.md` with the row-by-row table, `results.csv`, `trades.csv`, `baseline_gate.csv`, `family_census.csv`, `lock_cells_changed.csv` listing the 1,892 cells that flip, `code_callers.txt`, `harness.py`, and `consumer_map.md`, an independent map of every place that reads the lock), and `harness/impact_replay_a.py` and `harness/impact_replay_b.py`, the two independent harnesses for the ledger. One erratum: `other_families/report.md` says the changed catalyst trades closed 6.7% to 7.0% below the previous close; its own `trades.csv` shows 6.3% to 7.0%, plus LUCY at 10.0%, as stated in section 6. The harnesses were written in a scratch directory and carry its absolute paths; point `ARB2` / `FROZEN` (harness a) or the `ROOT` / `SCRATCH` derivation (harness b) at two copies of `idx-signals` that differ only in `idxsig/market.py` and at the frozen raw payloads. The raw payloads are not in git; the manifest holds their hashes. Also here: `DESIGN_NOTES.md` (what review changed), `spec_pack/` (market facts, interface contract, research passes, the re-check) and `DRAFT_MERGE_NOTE.md` (answers to the six merge questions and a waiver request for the architect).

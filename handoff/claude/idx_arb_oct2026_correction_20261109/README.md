# IDX lower-limit (ARB) correction: before and after on the existing ledger

Date 2026-11-09. Branch `claude/idx-arb-oct2026-correction`, base `04927b3c4`. Paper trading only: no real order was ever placed on these records.
The ledger, the published results and every frozen record are untouched. This report only replays them.

## Bottom line

- **What was wrong.** `idxsig/market.py` jumped from the 2026-09-28 rule (lower limit 15%) straight to a 2027 rule. It never learned that the exchange cut the lower limit to **7% on 2026-10-19** and, for reference prices Rp11 to Rp14, to **a nominal Rp1 on 2026-10-20**. Every lock at the lower limit since 2026-10-19 was judged against 15%.
- **What it changes.** Of the 93 scored IDX records, **14 change and 79 do not**. 11 hypothetical exits move 1 to 4 sessions later (8 worse, 3 better; mean change in net return -5.2 points). 3 hypothetical trades can no longer be scored, because their last session is locked. No verdict flips.
- **What it does not change.** Entry fills, the upper limit, position sizing and the frozen policy are unaffected. Nothing was executed: all 93 records are rejected candidates scored on paper. The defensible statement is "no executed loss established in the inspected records"; the hypothetical scores do move, as shown below.
- **Time-critical.** 33 decisions are still waiting for an outcome. Three of them (ALKA, DFAM, BSWD) are already certain to be scored differently. `paper.due()` shows that tonight's run (about 10:20 UTC) scores ALKA, KONI and POLI, tomorrow's scores DFAM, and BSWD follows on 2026-11-11. Until this change reaches the default branch the nightly job writes OUTCOME rows under the 15% rule, and an OUTCOME row is permanent unless the owner approves a revision.
- **Not known.** The decree texts were not read (idx.co.id refused the download). Board membership of each stock is not in the data. Nothing is confirmed for 2027. See section 7.

## 1. What changed in the code

Only `idxsig/market.py` (plus the README schedule and tests). Lower limit by date, regular boards:

| From | Lower limit (ARB) | Rp1-10 | Rp11-14 |
|---|---|---|---|
| 2026-09-28 | 15% | -Rp1 | 15% |
| **2026-10-19** | **7%** | -Rp1 | 7% (formula gives ARB = reference; real limit that day unknown, see section 7) |
| **2026-10-20** | **7%** | -Rp1 | **-Rp1** |
| after 2026-12-31 | **not confirmed**: the 2026-10-20 rule is carried forward and flagged | | |

The upper limit, the tick table, the Rp1 minimum price and every earlier regime are unchanged (a golden-master test pins 2019-07-29 to 2026-10-18).
The announced 2027 symmetric lower limit is no longer executable. After 2026-12-31 `limits()` carries the last confirmed rule forward, emits `RulesUnconfirmedWarning`, and the carried-forward period is its own regime labelled `UNCONFIRMED`. It never raises, because US and crypto runs share the same code path. `execution.py` and `paper.py` are byte-pinned by frozen records and are not touched.

## 2. Populations, recounted from the ledger file

Ledger snapshot: 755 rows (SCAN 79, DECISION 400, OUTCOME 276), sha256 `c1a67890577f7495212d1d9b3abbc97922bf741a007fc422c8225f5a87cd4395`, head record hash `4ee35255de041da3b75af78fdee3062560918affb97e64aa4b699077655277e8`.

| Population | Count |
|---|---|
| IDX decisions (122 marked IDX, 4 written 2026-10-07 without a market field, which the code treats as IDX) | 126 |
| IDX OUTCOME rows (one per decision, no duplicates, no revision rows, no repeated decision ids) | 93 |
| Decisions with signal on or after 2026-10-19 | **88** (57 scored, 31 pending) |
| Hypothetical trades inside that set | **27** |
| All scored records that carry a hypothetical trade | 40 |
| Scored records whose path touches 2026-10-19 or later | **82** (35 with a trade) |
| Pending decisions with no outcome yet | 33 (31 window still open, 2 complete but never scored) |

The figures "88 decisions" and "27 hypothetical records" are both correct for the definition "signal on or after 2026-10-19". They are not the exposed set: 82 records (35 trades) have a scored path that reaches 2026-10-19 or later, and 4 of the 14 changed records have signals before 2026-10-19.

## 3. The 14 records that change

Method: replay each record with the real scorer under the shipped rules and under the corrected rules on the same price data, and compare replay with replay. Full precision, both record hashes and the other 112 rows are in `impact_records.csv` (`source_decision_id`, `source_outcome_record_hash`, `source_decision_record_hash`).

| Record (decision id) | Effect | Recorded in ledger | Replay, shipped rules | Replay, corrected rules | Change | Deciding bar |
|---|---|---|---|---|---|---|
| 2026-10-12-F1_ARA-ZONE | SHIFTED | 10-19 invalidation -21.47% | 10-19 invalidation -21.47% | 10-20 invalidation -18.28% | +3.19 pp, +1 sess | at the 7% limit |
| 2026-10-14-F1_ARA-SONA | SHIFTED | 10-19 invalidation -21.09% | 10-19 invalidation -21.09% | 10-20 invalidation -22.86% | -1.77 pp, +1 sess | at the 7% limit |
| 2026-10-14-F1_ARA-TRON | SHIFTED | 10-19 invalidation -20.09% | 10-19 invalidation -20.09% | 10-20 invalidation -16.61% | +3.47 pp, +1 sess | at the 7% limit |
| 2026-10-16-F1_ARA-CBPE | SHIFTED | 10-21 invalidation -13.06% | 10-21 invalidation -13.06% | 10-22 invalidation -16.27% | -3.21 pp, +1 sess | at the 7% limit |
| 2026-10-20-F1_ARA-HATM | SHIFTED | 10-23 invalidation -13.25% | 10-23 invalidation -13.25% | 10-26 invalidation -17.27% | -4.02 pp, +1 sess | at the 7% limit |
| 2026-10-20-F1_ARA-PNSE | UNSCORABLE | 10-28 horizon -4.85% | 10-28 horizon -4.85% | no outcome (horizon 10-28 locked) | n/a | at the 7% limit |
| 2026-10-22-F1_ARA-BUKK | SHIFTED | 10-26 invalidation -6.95% | 10-26 invalidation -6.95% | 10-30 invalidation -25.74% | -18.78 pp, +4 sess | at the 7% limit |
| 2026-10-22-F1_ARA-PNSE | SHIFTED | 10-27 invalidation -13.32% | 10-27 invalidation -13.32% | 10-29 invalidation -22.45% | -9.12 pp, +2 sess | at the 7% limit |
| 2026-10-23-F1_ARA-ASLI | SHIFTED | 10-28 invalidation -13.37% | 10-28 invalidation -13.37% | 11-02 invalidation -26.92% | -13.56 pp, +3 sess | at the 7% limit |
| 2026-10-23-F1_ARA-FLMC | SHIFTED | 10-27 invalidation -9.57% | 10-27 invalidation -9.57% | 10-28 invalidation -6.30% | +3.28 pp, +1 sess | below the 7% limit (wider-limit name?) |
| 2026-10-23-F1_ARA-KONI | UNSCORABLE | 11-02 horizon +5.13% | 11-02 horizon +5.13% | no outcome (horizon 11-02 locked) | n/a | at the 7% limit |
| 2026-10-23-F1_ARA-PTSP | UNSCORABLE | 11-02 horizon +8.36% | 11-02 horizon +8.36% | no outcome (horizon 11-02 locked) | n/a | at the 7% limit |
| 2026-10-23-F1_ARA-TOBA | SHIFTED | 10-29 invalidation -16.37% | 10-29 invalidation -16.37% | 11-02 invalidation -23.87% | -7.49 pp, +2 sess | at the 7% limit |
| 2026-10-29-F1_ARA-YPAS | SHIFTED | 11-03 invalidation -13.04% | 11-03 invalidation -13.04% | 11-05 invalidation -22.14% | -9.10 pp, +2 sess | at the 7% limit |

Reading it: a name that falls about 6 to 9 percent a day for several days sits locked at the 7% limit on each of those days, so a stop-out that the 15% rule filled on day one cannot be filled until the run ends. All 14 deciding bars closed 6.1 to 9.2 percent below the previous close, 13 of them exactly at the modelled 7% limit price. The 3 UNSCORABLE records have a locked fifth-session close; the legacy scorer never rolls past its horizon, so no OUTCOME would be written (two of the three were missed gains). The second October change, Rp1 for Rp11-14, adds no lock to any record. The whole effect is the 7% percentage.

## 4. Unchanged cases

| Category | Records | Meaning |
|---|---|---|
| UNCHANGED | 68 | path reaches 2026-10-19 or later, replay identical: 47 had no trade (a lock is never consulted), 8 traded across a newly locked session with no effect, 13 traded with no newly locked session |
| NOT AFFECTED | 11 | scored path ends before 2026-10-19 (5 trades, 6 without a trade) |
| BECOMES SCORABLE, VERDICT CHANGED | 0 | the correction only adds locks |

## 5. Aggregates (hypothetical paper trades of rejected candidates)

| | Recorded | Shipped rules (replay) | Corrected rules (replay) |
|---|---|---|---|
| Hypothetical trades | 40 | 40 | 37 |
| Mean net return | -8.66% | -8.68% | -11.17% |
| Median net return | -9.47% | -9.70% | -10.21% |
| Same 37 trades in both, mean | | -9.62% | -11.17% |
| Correct rejections | 88 | 88 | 87 |
| Missed gains | 5 | 5 | 3 (and 3 records without outcome) |

The corrected mean is partly survivorship: the 3 trades that drop out averaged +2.9% under the shipped rules, so dropping them lowers the mean on its own. Market-wide the correction turns 1,892 (ticker, session) cells from sellable to locked (2,858 to 4,750 locked cells), 349 of them on 2026-10-19. Nothing turns the other way and the upper-limit flags are identical.

## 6. Unresolved cases

**Pending decisions.** Those with a flipped bar on the path so far (all closes exactly at the modelled 7% limit), plus the two that are stuck for reasons unrelated to this change:

| Pending decision | Sessions that lock only under the corrected rule | State on the bars seen so far |
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

ARII (signal 10-08) has a locked horizon bar under the old 15% limit and BIKE (signal 10-14) a suspended one, so the legacy scorer returns no outcome and `paper.due()` offers them again every night. That failure mode predates this change. 8 pending names have no 2026-11-06 bar in the final pull, so a flip cannot be seen for them yet.

**Speculation register.** `paper/speculations.jsonl` holds 23 IDX RESOLUTION rows. 21 use next-session returns only and cannot change. 2 BASE5 rows use the lock at their horizon day. One of them, ALKA BASE5 (`SPEC-SCAN-2026-10-29-F1_ARA-ALKA`), would not have resolved on 2026-11-06 under the corrected rules, because twins KDTN and WBSA closed locked exactly at the 7% limit on their horizon day. YPAS BASE5 is unchanged. The recorded rows were not touched.

**What-if (labelled, not part of any count).** If the scorer kept rolling past the horizon to the first sellable close: PNSE (signal 10-20) exits 10-29 at -9.29% (shipped -4.85%), KONI exits 11-04 at -0.11% (shipped +5.13%, a missed gain becomes a correct rejection), PTSP stays locked through 2026-11-06.

## 7. How sure the numbers are, and what is not known

- **Two independent replays agree exactly.** Two analysts wrote separate harnesses from the same inputs, without seeing each other's work. They match on all 126 records (category, exits and net returns to 1e-9). A third, earlier probe by a reviewer also found 14 changed trades and the same three unscorable names. A from-scratch recomputation of the documented rules reproduced all 125,120 lock flags in both rule sets with no disagreement; that checks the code against the stated rules, not the rules against the exchange.
- **Baseline gate.** Replaying the shipped rules reproduces 90 of the 93 recorded outcomes field for field. The 3 differences are not rule effects: BTEK is a floating-point knife-edge on a discovery flag (0.2999999999999998 against 0.30000000000000004), and CARE and SOHO were scored from a price pull started at 08:13 UTC, before the 09:30 UTC time the code treats as the final bar, so their last bar was still moving. All 9 outcomes of signal day 2026-10-21 came from that pull. The ARB effect is always measured as corrected replay minus shipped replay, so these cannot leak into it.
- **Final-bar replay.** Only one raw price pull survives (2026-11-06, 920 tickers, hashes verified). Every record is replayed on it, not on the pull that wrote it.
- **The rules rest on secondary sources.** The decree texts (Kep-00157, Kep-00158) were not read: idx.co.id returned HTTP 403 and the block was not circumvented. The dates, 7% and the Rp11-14 reading come from the IDX trading-mechanism web page, IDX press releases as reposted by brokers, and press reports. The rounding rule (ARA floored and ARB ceiled to the tick of the limit price's own band) is inferred from 20 observed limit prices.
- **2026-10-19, references Rp11-14.** The formula gives ARB = reference, but BTEK and TAXI closed 25% below it that day, below every candidate limit. The real limit that day is unknown. No scored record has such a bar on its path.
- **Boards.** The October decisions cover the Main, Development and New Economy boards; the Acceleration and Special Monitoring boards keep 10%. The data has no board field, so every name gets the regular rule. If the ARB were 10% instead of 7%, **0 records change**: the whole effect sits on closes between the 7% and 10% limits. 46 of 920 names show a close below their modelled 7% limit since 2026-10-19, which marks them as wider-limit names. Of the 14 changed records only FLMC belongs to such a name; without it 13 change.
- **A modelling convention carries most of the effect.** The scorer treats "close at or below the lower limit" as a session in which the holder could not sell, whatever the volume. 13 of the 14 changes rest on a close exactly at the limit price. A real close at the limit does not prove that nobody could sell. This convention predates this change and is unchanged.
- **After 2026-12-31 nothing is confirmed.** BEI called the symmetric 2027 plan conditional and replaced the decree twice in October. The convention adopted here is cautious for exits (a narrower lower limit locks more), and it is a convention.

## 8. Separate findings (not fixed here)

1. **A price pull before the close.** On 2026-10-29 the scoring pull started at 08:13 UTC (15:13 Jakarta time), before the close, and finished windows on a bar that was still moving. 9 outcomes (all signal 2026-10-21) were scored that way; 2 of them (CARE, SOHO) differ from the final bars. `score_pending` and `due` do not check that the session is closed. Fixing it needs `paper.py`, which is pinned.
2. **The legacy scorer never rolls past a locked horizon bar.** The omission is selective: it drops exactly the worst, or most profitable, locked trades. Under the 7% limit it hits 3 of 40 trades. The execution model (`execution.execute`) does roll. Whether the scorer should roll is an owner decision.
3. **Hashed plan text still says "15%".** `paper.py` writes "15% below the entry" into new decision records, and the frozen policy parameter `max_stop_distance` is 0.15. Both are pinned and describe the sizing assumption, not the exchange limit. Left alone on purpose.
4. **A spurious warning on non-IDX runs.** `Market.build` computes limits for every market before discarding them, so a US or crypto run after 2026-12-31 emits the IDX `RulesUnconfirmedWarning` once per process. Harmless; removing it needs `execution.py`.
5. **Stale pins.** `market.py` changes sha256. Three completed protocols pin the old hash (MSCI_DELETION_v1, MSCI_DELETION_OPT_v1, MSCI_DELETION_OOT_v1) and their runners will refuse to run again. Their stored results are untouched. E9 already pins an older hash.

## 9. Ways to correct the ledger (not done; needs the owner's approval)

- Leave the recorded rows as they are. They are a true record of what the code did on those dates.
- For the 14 changed records and for any pending decision scored under the old rule before the merge, write revision rows through the existing `--rescore` / `revises` mechanism, which never edits the original.
- The 3 unscorable records cannot get an "unscorable" status without editing `paper.py`. A note in the revision rows is the smallest way.
- The ALKA BASE5 resolution is a separate register; the architect decides.

## 10. Inputs and reproduction

| Input | Value |
|---|---|
| Ledger snapshot | `idx-signals/paper/ledger.jsonl` at `04927b3c4`, sha256 `c1a67890577f7495212d1d9b3abbc97922bf741a007fc422c8225f5a87cd4395` |
| Speculation snapshot | `idx-signals/paper/speculations.jsonl` (277 rows), sha256 `0118f0c87d96e1a5fc6726d2668536d93e9c45ddc7e2a0dbdbaff47264542b04` |
| Price manifest | `yahoo_recent-20261106T101853Z.jsonl`, sha256 prefix `3a27d3445b3d`, 920 payloads, every payload hash verified |
| `market.py` before / after | sha256 `e9e9328af46a871d6a8bc929ab10889f071bcdbef4be6d85f6fe1d26bd2f9cbc` / see the commit |

Files here: `impact_records.csv` (126 rows: 93 outcomes and 33 pending), `baseline_gate.csv` (93 comparisons with a diagnosis for each difference), `flipped_bars_on_paths.csv` (every flipped bar on a replayed path with its limit and board hint), `speculation_replay.csv` and `speculation_base5_trades.csv`, and `harness/impact_replay_a.py` and `harness/impact_replay_b.py`, the two independent harnesses. The harnesses were written in a scratch directory and carry its absolute paths; point `ARB2` / `FROZEN` (harness a) or the `ROOT` / `SCRATCH` derivation (harness b) at two copies of `idx-signals` that differ only in `idxsig/market.py` and at the frozen raw payloads. The raw payloads are not in git; the manifest holds their hashes.

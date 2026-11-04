# INFO_MAGNET primary gate: independent verification

Written 2026-11-04 by Claude. Subject: Codex's run on branch `codex/info-magnet-check-20261104`
(`handoff/astra/info-magnet-check-20261104/`, result commit `6abc9e68a`, freeze commit `e97a93e`), received as the
owner's package `KOD-INFO-MAGNET-REVIEW.zip`. Two independent checks were run: a recomputation from Claude's own,
separately downloaded Binance archives, and an adversarial design audit. **Verdict: PRIMARY_GATE_FAIL stands.**

## 1. Recomputation from independent data

Claude's Binance spot 1h archives were downloaded on 2026-11-03 for `HERMES_NOV3_REPRO_v1` (702 symbols, 2020-01 to
2026-10, sha256 per file in that study's `fetch_manifest.json`), before INFO_MAGNET existed. Codex's `EVENTS.json` was
read as data only. Script and output: `info-magnet-verification/verify.py` and `verify_out.json`.

| Check | Codex | Independent | Match |
|---|---:|---:|---|
| Events recomputed | 75 | 75 | all |
| Mean target gross return, 24 h | -7.800% | -7.800% | max abs difference 2.2e-16 |
| Control returns recomputed | 375 | 375 | 0 differ |
| Mean event net after 2% | -9.800% | -9.800% | yes |
| Paired excess after 2% (vs gross controls) | -8.546 pp | -8.546 pp | yes |
| 6 h and 72 h target returns | | | max abs difference 2.2e-16 and 1.8e-16 |
| Notice time, entry hour, exit bar, symbol mapping | | | all 75 consistent |

Every one of the 30 events Codex marked unmeasurable is also unmeasurable in the independent archive. Two reused
tickers (LIT, USDS) would have mapped to older, unrelated pairs, but both events are excluded for lack of a pre-notice
bar, so the result is unaffected. Five assets appear in two separate listing notices (10 events), a same-asset
dependence the run discloses and does not model.

## 2. Adversarial design audit

Second agent, instructed to refute the result. Scripts: `info-magnet-verification/recompute.py` and
`recompute_out.json` (all 75 events times six instruments recomputed from Codex's checksum-verified raw archives).

| Check | Rating | Evidence |
|---|---|---|
| Specification frozen before any price was read | SOUND | Branch created with `e97a93e` at 14:09:53Z; first Binance read 14:14:01Z; ADDENDUM and EXCLUSIONS hashes match FREEZE.json |
| Post-run repairs | MINOR ISSUE | Made after the first run's outputs were seen (disclosed). All three runs fail both outcome checks: paired excess -8.78 / -8.57 / -8.55 pp; only the unresolved count changed (17, 3, 0) |
| Publication time and entry | SOUND | Every first_listed_at carries +09:00; entry is floor(hour)+1h, always after publication |
| Controls | SOUND | Eligibility from a complete bar before the notice only; pool includes delisted names; seeded, never replaced |
| Cost asymmetry | SOUND | Trades already lose 7.8% before any cost; charging both sides gives the same verdict |
| Horizon choice | SOUND | Mean trade loses after costs at 6 h (-4.4%), 24 h (-9.8%) and 72 h (-14.9%); none could pass |
| Bootstrap | SOUND | Reproduced to 6 decimals; every clustering (date, week, month, notice, symbol, event) excludes zero |

## 3. What happened to the price (post-result, descriptive only; not a tested rule)

| Measure, 75 events | Median | Mean |
|---|---:|---:|
| Highest price in the notice hour vs the last close before it | **+46.8%** | +58.9% |
| Entry price (first full hour) vs the last close before the notice | **+23.0%** | +34.9% |
| Entry price vs the notice hour's high | -10.7% | -13.2% |
| Last close before the notice to the 24 h exit | +7.8% | +26.2% |
| Events with a 24 h loss after entry | 81% | |

Every one of the 75 coins had already risen before the first possible hourly entry (minimum +1.3%), and 71 of 75 traded
at least 10% higher during the notice hour. **The move exists, but it happens inside the hour of the notice; an entry at
the first full hour buys after the spike and then gives back.** This matches BINANCE_ANN_1M (about 80% of the move
inside the announcement minute). A seconds-level entry on brand-new listings was not tested and would need its own
protocol; it is outside the owner's manual eToro/Stockbit execution.

## 4. Consequence
The early-entry close rule (`handoff/timing/EARLY_ENTRY_CLOSE_RULE_2026-11-03.md`) is applied in
`handoff/decisions/2026-11-04_early_entry_closed.md`.

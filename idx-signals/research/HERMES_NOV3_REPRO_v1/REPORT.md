# HERMES_NOV3_REPRO_v1 report (run once, 2026-11-03)

**Verdict: Hermes's 3 November conclusions hold.** Rebuilt here from scratch, from its chat descriptions and its pushed
code, on freshly downloaded Binance data: 45 claims checked, **36 reproduced, 7 partly, 2 not reproduced**.
The two that failed matter for the judgment policy: **"winners show themselves by day 3" is wrong** under the plain
reading, and strength signs only look like a "worse typical result" if you measure from when the sign is visible.
Fixing Hermes's look-ahead in the random-coin comparison makes the alerts look **worse** against random coins, not better.

Everything here is exploratory on years Hermes already used. Nothing is a strategy. Paper only.

## Validation gate: PASS (same code, fresh data, Hermes's pushed numbers)
| | Hermes | Here |
|---|---|---|
| Alerts 2020-22 / controls | 5,267 / 26,321 | **5,267 / 26,321** |
| Reach +30% in 72h / net 72h | 17.5% / -4.1% | **17.5% / -4.1%** |
| 2023-26 alerts with X4 / mean | 6,971 / -2.95% | **6,974 / -2.96%** |
| COMBO A 2023-26 | 968 at +1.10% | **969 at +1.07%** |

## Claim by claim (mean per trade unless stated; periods 2020-21 / 2022 / 2023-26)

### Study 1, entry timing (same alerts, +50%-or-14-days exit)
| Claim | Hermes | Here | Verdict |
|---|---|---|---|
| Buy next hour | +3.5 / -5.0 / -3.0 | +3.5 / -5.2 / -3.0 | REPRODUCED |
| Limit 15% below; good moves skipped | +5.1 / 0.0 / -0.2; 73-83% | +5.1 / -0.3 / -0.2; 74-83% | REPRODUCED |
| First-day-high break; skipped | +7.3 / -4.3 / -0.4; 45-66% | +7.8 / -4.8 / -0.1; 40-57% | REPRODUCED |
| Earlier alarm (+5% in 1h); becomes full move | +4.6 / -4.3 / -1.8; ~55% | +4.7 / -4.3 / -1.8; 50-52% | REPRODUCED |
| Strong clues + first-day-high break | +15.9 / -20.6 / +1.4 | +15.2 / -17.8 (n=6) / +2.0 | REPRODUCED |
| Peak timing; typical later peak | ~78h vs 20-23h; +15% | 77h vs 18h / 22h; +15% | REPRODUCED |
| Winners' first pullback vs all | 7-10% vs 13% | 7-10% vs 13-14% | REPRODUCED |
| Typical (median) trade loses in 2022 and 2023-26 for every entry | yes | yes (all groups) | REPRODUCED |

### Study 2, crowd mood and funding (12,190 alerts)
| Claim | Hermes | Here | Verdict |
|---|---|---|---|
| Extreme Fear: peak / hours / reach +50% / mean | +15% / 18h / 16% / -4.8% | +16% / 17h / 16% / -4.4% | REPRODUCED |
| Fear; Neutral; Greed | 28h -3.7%; 21h -3.3%; 43h -1.2% | 23h -4.4%; 17h -4.2%; 43h -0.8% | REPRODUCED |
| Extreme Greed | +27% / 102h / 29% / +8.2% | +27% / 101h / 29% / +8.2% | REPRODUCED |
| 2023-26: Extreme Fear vs Extreme Greed peak | 8h vs 55h | 8h vs 52h | REPRODUCED |
| Crowded longs vs crowded shorts (alerts) | +5.3% vs -3.9% | +5.0% vs -3.8% | REPRODUCED |
| Spike shorts: crowded shorts hold most big losses | -7.4%; 26 of 37 worse than -50% | -3.2%; 32 of 46 (both 70%) | REPRODUCED |

Caveat found here: 295 of 421 spike shorts with funding data were in the crowded-shorts state, so "skip crowded
shorts" removes most spike shorts. Crowded longs (n=63) also lost (-3.8%).

### Study 3, price paths (11,972 alerts with 30 days of data)
| Claim | Hermes | Here | Verdict |
|---|---|---|---|
| P1 touched +10/20/30/50% (2020-21) | 75/57/42/26% | 75/57/42/26% | REPRODUCED |
| P1 same, 2023-26; of those negative at day 14 | 62/41/28/16%; 54/40/31/21% | 62/40/28/15%; 55/40/32/22% | REPRODUCED |
| P2 touched -10/20/30% (2023-26); recovered by day 14 | 83/49/21%; 19/7.6/2.7% | 83/49/21%; 18/7.1/2.4% | REPRODUCED |
| **P3 under 1 in 100 became a +20% day-14 winner without +20% by hour 72** | < 1% | **4.4% of all alerts (2023-26), 10.6% (2020-21); 38-48% of all day-14 +20% winners were slow** | **NOT REPRODUCED** |
| P4 hour-6 gain buckets: what happened next (median) | -8 / -14 / -25% | -8 / -14 / -25% | REPRODUCED |
| P4 kept-runner share by bucket | 12 / 25 / **31%** | 9 / 16 / 11% | PARTLY (the >+25% bucket does not hold the most runners) |
| P5 strength signs: more big runners, worse typical result | 23% vs 7%; -9% vs -5% | from entry: more runners, **better** median | **NOT REPRODUCED** as defined; see post-run check |
| P6 kept runners: Extreme Greed vs others; 2020-21 vs 2023-26 | 27% vs 9-14%; 22% vs 11% | 20% vs 6-10%; 16% vs 8% | REPRODUCED (same ratios, lower levels) |
| 30-day peak inside the first 24h | 41% (2023-26) vs 29% (2020-21) | 41% vs 29% | REPRODUCED |

**Post-run check (written after the run, descriptive only, `post_checks.py`):** measured from the moment each sign is
visible (hour 6 or 24) to day 14, strength signs **do** give a worse typical result: 2023-26 median -9.0% vs -6.6%
(new high by hour 6), -9.5% vs -5.1% (beat BTC over 24h). They lift the +50% runner rate 1.3-1.5x, not 3x. So Hermes's
P5 conclusion holds in the tradable sense, with a smaller runner effect.

### Study 4, quick exits (18 versions; Extreme Greed alerts get double target and 14 days)
| Claim | Hermes | Here | Verdict |
|---|---|---|---|
| Old exit (+50% / 14d); random 2023-26 | +3.5 / -5.0 / -3.0; -0.6 | +3.5 / -5.2 / -3.0; -0.6 | REPRODUCED |
| Hold 72h; random | -2.0 / -6.7 / -3.8; -0.9 | -2.0 / -6.9 / -3.9; -1.0 | REPRODUCED |
| Main: +15% / -10% / day 3; random | -0.9 / -2.7 / -2.0; -0.7 | -1.0 / -2.8 / -2.0; -0.7 | REPRODUCED |
| Best (2023-26): +10%, no stop | -0.4 / -2.2 / -1.7 | +1.5 / -2.3 / -1.6 | PARTLY (still positive in the boom) |
| Quick exits wipe out the boom profit | +3.5% -> about -0.5% | stopped versions -0.1 to -1.0%; no-stop versions +1.5 to +3.4% | PARTLY |
| Stops barely matter | -10/-15/none similar | true in 2023-26 (0.3-0.5 pt); in 2020-21 stops cost 2-3 pt | PARTLY |
| Extreme Greed running longer adds | ~0.2 pt | +0.2 pt (2020-21), ~0 later | REPRODUCED |
| Alerts worse than random coins under every quick exit | yes | 20 of 20 versions, vs both control sets | REPRODUCED |
| Main version negative in every year 2020-26 | yes | -0.9% to -2.8% every year | REPRODUCED |

### Study 5, bear market (BTC below its 200-day average, 2018-26)
| Claim | Hermes | Here | Verdict |
|---|---|---|---|
| Bear weeks | 214 | 214 | REPRODUCED |
| Hold BTC; worst drop | -13%; -67% | -13%; -67% | REPRODUCED |
| Short all alts (proxy; perp) | -93%; -84% | -94%; -90% | REPRODUCED |
| Buy dips in strong coins | -8.7% per trade | -0.6% (median -4.3%, 42% wins) | PARTLY (negative, much smaller) |
| Buy at capitulation | -1% | -0.9% | REPRODUCED |
| Short spikes (proxy): wins, median, worst; mean | 66%, +12%, -488%; +1.5% | 68%, +12.6%, -491%; +2.8% | REPRODUCED |
| Short spikes (perp, real funding) | -4.0% | -2.9% | REPRODUCED |
| Short faded spikes (proxy; perp) | -1.3%; -4.3% | -1.2%; -4.2% | REPRODUCED |
| Buy BTC at Fear & Greed <= 15, hold 20 days | +2.6%, 60% wins, 42 trades, positive in all 3 periods | +3.2%, 63% wins, **27 trades**, 2021-23 **-0.2%** (n=8) | PARTLY |
| Weekly short of recent spikers (perp, BTC rule) | -97% | -98% | REPRODUCED |
| Same, altcoin-breadth rule | +116%, all from 2024-26, -49% in 2021-23 | **-62%**; -69% in 2021-23, +47% in 2024-26 | PARTLY (same pattern, opposite total) |
| Long strong / short weak (perp) | -55% | -84% | REPRODUCED |
| Cash beats almost everything in BTC bear weeks | yes | every BTC-bear arm lost | REPRODUCED |

## Hermes's control flaw, corrected
Hermes's random coins excluded any coin that triggered in the **next** 72 hours (future information). With past-only
exclusion, random coins do better: 2023-26 X4 **+0.27%** vs Hermes's -0.61%. So the flaw made random coins look worse
and **flattered the alerts by about 0.9 points**. Corrected, alerts trail random coins by 3.2 points (X4) and by
1.8-2.0 points under the quick exits. No conclusion is rescued by the flaw; the alerts' disadvantage is larger.

## What changes for KOD
1. **Drop the "dead by day 3" rule** from JUDGMENT_POLICY / the analyst card. In 2023-26, 38% of alerts that ended day
   14 up 20%+ had not touched +20% in their first 72 hours (examples: LDO, FET, JASMY, January 2023). Not moving by day 3
   cuts the odds a lot (6% finish +20%, vs 27% for alerts that touched +20% by hour 72); it does not end them, and
   those slow winners are over a third of all winners. Hermes's direction is right; "almost never" is not.
2. Everything else Hermes concluded on 3 Nov stands: no entry or exit makes the alerts profitable; mood sets how long
   moves last; crowded shorts are where squeezes kill; in BTC bear weeks cash wins; the Fear & Greed <= 15 Bitcoin buy
   is a small lead (27-42 trades), not proof, and it was not positive in every period here.
3. The remaining lever is unchanged: choosing which alerts to take using evidence beyond price (Hermes's Test B,
   INFO_MAGNET_v0), which cannot run from this cloud environment (Upbit blocks it).

## Not reproduced here
INFO_MAGNET_v0 (not run by Hermes either; Upbit 403 here): `INFO_MAGNET_v0_NOT_RUN.md`. JUDGMENT_POLICY_v0: a policy,
transcribed in `JUDGMENT_POLICY_v0_TRANSCRIBED.md`. clue_mechanisms_v1: written, never run by Hermes.

## Files
PROTOCOL.md (locked before data) · fetch.py, fetch_manifest.json (76,961 Binance files, sha256) · lib.py, build.py,
VALIDATION.json · entry_timing.py, psych.py, paths.py, spike_default.py, bear.py (each run once) · out/RESULT_*.json and
per-trade CSVs · post_checks.py, out/POST_CHECK_strength_from_sign.json (post-run, descriptive) · LEDGER_LINES.md.
Definitions the chat did not give are marked [GAP] in PROTOCOL.md; those explain most of the PARTLY rows.

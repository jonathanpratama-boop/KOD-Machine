# LEAD_LADDER_INTL_v1 report (counted test 29)

Recorded run 2026-10-26 with `run_v2.py`, final verdict by `placebo_gate.py` (ADDENDUM_2), verified by `verify_v3.py`
(sampled event rows from the panels, every pooled lift and gate, 0 mismatches). Universe: 2,851 stocks eToro lists on
nine non-US exchanges with Yahoo history (of 3,161 requested; Stockholm 168 of 385 not found because eToro and Yahoo
write share classes differently). Discovery 2020-07..2022-12 only; survivor-only.

## Verdict: NOT_REPLICATED

| Cell | Pooled lift before rises | Placebo | Lift before falls | Failed gates |
|---|---|---|---|---|
| P1 beaten-down (ret20 bottom), fast moves, lead 3 | 2.50 (lower 2.29) | 1.11 | 2.34 | direction |
| P2 few recent up-days (up5 bottom), slow moves, lead 5 | 1.63 | 1.56 | 1.47 | size, direction, years, placebo |
| P3 young listing (age bottom), slow moves, lead 10 | 1.46 | 1.15 | 1.87 | size, direction, years, placebo |

P1 is real separation, in all nine markets (2.0 to 2.8 except Tokyo, 14 events), in every year, and as strong 20
sessions out as 3: beaten-down stocks are about 2.5 times as likely to jump 30% within a week, and about 2.3 times as
likely to fall 23%. It predicts a large move, not its direction. P2 and P3 do not reappear.

Secondary ladder: 0 of 256 cells pass; 27 are movement-only (volatility, drawdown, recent losses).

## Reading with test 28

Across 12 markets, the robust daily-bar finding is movement: names that are volatile and beaten down move more, both
ways. The directional cells of test 28 were either pool artifacts (LEAD_LADDER_v1/ERRATA_1.md), market-specific, or
survivorship: P1's direction gap in the US (3.17 vs 2.09) and crypto shrinks to 2.50 vs 2.34 here. No daily-bar
feature tested gives an early, directional warning of a moonshot in any market the owner can trade.

## Consequence (the reading rule)

NOT_REPLICATED: test 28's directional cells are read as market-specific or chance. No detector is built from them.

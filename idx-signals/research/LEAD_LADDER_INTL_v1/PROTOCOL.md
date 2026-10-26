# LEAD_LADDER_INTL_v1: do LEAD_LADDER_v1's directional cells appear in eToro's nine largest non-US stock markets?

Written 2026-10-26, before any price of these markets is fetched. Counted test 29 (the number LEAD_LADDER_v1's
consequence reserved for an IDX validation, which the owner declined:
`handoff/decisions/2026-10-26_markets_us_crypto_and_etoro_countries.md`).

## Question

LEAD_LADDER_v1 (test 28) found three directional, non-timing patterns: beaten-down names before fast up-moves
(US and crypto, lead 3), young listings and few recent up-days before slow up-moves (IDX). This test asks, on new
markets the owner can trade, whether they appear again. Separation only: no trade, no order.

## Markets and data

The stocks eToro lists (snapshot `etoro_instruments-20261016T190421Z`, sha256 `5c90ab53…`) on its nine non-US
exchanges with at least 200 stocks, mapped to Yahoo Finance symbols:

| Market | eToro exchange ids | eToro suffix -> Yahoo | Price-band edges (local units, about USD 1 / 5 / 20) |
|---|---|---|---|
| UK | 7, 42, 43, 44 | .L -> .L (pence) | 80 / 400 / 1,600 |
| DE | 6 | .DE -> .DE | 0.9 / 4.5 / 18 |
| FR | 9 | .PA -> .PA | 0.9 / 4.5 / 18 |
| AU | 31 | .ASX -> .AX | 1.5 / 7.5 / 30 |
| SE | 15 | .ST -> .ST | 10 / 50 / 200 |
| NO | 14 | .OL -> .OL | 10 / 50 / 200 |
| HK | 21 | .HK -> .HK | 8 / 40 / 160 |
| JP | 56 | .T -> .T | 150 / 750 / 3,000 |
| IT | 11 | .MI -> .MI | 0.9 / 4.5 / 18 |

Symbols with other suffixes or marked "-old" are skipped. Yahoo daily bars from 2019-01-01, split-adjusted by the
source; every request (not-found included) in a hashed manifest. Survivor-only and eToro-selected (names eToro
lists today, mostly larger companies). Survivorship inflates exactly the beaten-down-then-rebound pattern (crashed
names that died are absent), so **a pass here cannot confirm; it is a screen**. One panel per market (causal
close-time preprocessing, the current global panel format); a session needs at least 50 names trading.

Windows as E2: discovery 2020-07-01 .. 2022-12-31; the study market ends 2023-12-31 and only discovery is read;
2024 onward is sealed.

## Method

LEAD_LADDER_v1 unchanged (`idxsig/lead_ladder.py`, `research/LEAD_LADDER_v1/protocol.json`): the four episode kinds,
the void rule, leads 0..20, pools matched within each market on its own session (price band, liquidity quintile;
no market cap), E2's feature list, tail lifts, week-clustered bootstrap (2,000, seed 20261026). Events and their
pools are per market; the nine markets are **pooled** into one INTL result by summing observed and expected counts.
Per-market results are descriptive.

## Primary: three pre-specified cells (pooled INTL, void analysis)

| Cell | Kind | Feature, tail | Lead | Test 28 finding |
|---|---|---|---|---|
| P1 | FAST_UP | ret20, bottom | 3 | CRYPTO 2.11 (down 1.21), US 3.17 (down 2.09) |
| P2 | SLOW_UP | up5, bottom | 5 | IDX 2.21 (down 1.34) |
| P3 | SLOW_UP | age, bottom | 10 | IDX 2.10 (down 1.33) |

Bonferroni over 3 cells, one-sided 0.05/3: z = 2.13. Gates as test 28: G1 lift >= 2.0; G2 lower bound at z 2.13 above
1.0; G3 lift >= 1.5 x the matching down kind's lift; G4 lift >= 1.5 in each discovery year with >= 30 events (2020
counts from July); G5 >= 100 events and expected >= 10. Age is censored at the first Yahoo bar (2019-01-01 or later);
a listing before 2019 reads as old, so P3 asks about listings since 2019.

Reading rules, fixed now:

- **REPLICATED_SCREEN**: at least one primary cell passes. The pattern reappears on new markets (survivor-only).
  Next would be one frozen detector with a money test against matched entries, on survivorship-free data.
- **NOT_REPLICATED**: no primary cell passes. Test 28's directional cells are read as market-specific or chance.
- **NOT_TESTABLE**: a primary cell has fewer than 100 events (G5); it is reported as such, not as a fail.

## Secondary (gated, not the verdict)

The full ladder on pooled INTL: 2 up kinds x 4 gated leads x 32 feature-tails = 256 cells, z = 3.55 (0.05/256), same
gates; reported as passing / movement-only counts beside the verdict.

## Rehearsal and verification

Placebo first (random eligible names on the same sessions in place of the up episodes, seed 20261026): expected no
primary or secondary pass. `verify.py` recomputes every primary and secondary pooled lift and gate from the per-event
tables, and a seeded sample of 200 event rows from the panels with code that does not import the ladder module.
`PINS.json` before the run. The result enters the register whatever it is.

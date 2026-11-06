# KOD paper book (PAPER_BOOK_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-06T00:24:43.047001Z; latest US scan session: 2026-11-05.
- Latest compatible LEARNER v2.4 forecast: 2026-11-06T00:22:22Z (signal session 2026-11-05).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

Generated 2026-11-06T00:24:43Z. Paper only: no orders, no money. Protocol: `research/PAPER_BOOK_v1/protocol.json`.

## The three plain answers

- **What does it do?** For every US stock that just closed +30%, KOD says DONT_BUY when its dump-tomorrow probability is 0.46 or more, otherwise BUY_OK. The KOD book buys every BUY_OK at the next open and sells five sessions later; $1,000 a position, real costs.
- **Evidence so far?** 24 spikes planned, 0 trades closed. The verdict waits for the planned look at 300 closed trades; until then the numbers are a running tally.
- **What counts as success?** Two separate questions, each at the planned look: DONT_BUY works if the skipped spikes do worse than the bought ones (95% bound below zero); the KOD book makes money if its average trade is above zero (95% bound above zero).

## The books

| Book | What it holds | Positions | Open | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|---:|
| KOD | every BUY_OK | 15 | 15 | 0 | 0 | $+0 | - |
| ALL | every spike | 24 | 24 | 0 | 0 | $+0 | - |
| AVOIDED | every DONT_BUY (kept out) | 9 | 9 | 0 | 0 | $+0 | - |
| OWNER | spikes you confirmed BUY | 0 | 0 | 0 | 0 | $+0 | - |

## Every spike

| Signal | Ticker | Dump tomorrow | KOD | You | Status | Net |
|---|---|---:|---|---|---|---:|
| 2026-11-05 | ZNB | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-05 | XXII | 0.36 | BUY_OK | - | OPEN | - |
| 2026-11-05 | VXX | 0.11 | BUY_OK | - | OPEN | - |
| 2026-11-05 | PLCE | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-05 | LABT | 0.33 | BUY_OK | - | OPEN | - |
| 2026-11-05 | JDZG | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-05 | HTCR | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-05 | FLYE | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-05 | DNUT | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-05 | BDMD | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-05 | APP | 0.09 | BUY_OK | - | OPEN | - |
| 2026-11-05 | AMTX | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-05 | AEHL | 0.30 | BUY_OK | - | OPEN | - |
| 2026-10-30 | WHLR | 0.62 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | SLGB | 0.52 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | SGRX | 0.58 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | ONEG | 0.61 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | OMEX | 0.70 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | MASK | 0.63 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | GDYN | 0.47 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | FMC | 0.38 | BUY_OK | - | OPEN | - |
| 2026-10-30 | CHOW | 0.68 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | ATYR | 0.65 | DONT_BUY | - | OPEN | - |
| 2026-10-30 | ASUR | 0.43 | BUY_OK | - | OPEN | - |

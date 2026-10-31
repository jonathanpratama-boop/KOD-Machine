# KOD paper book (PAPER_BOOK_v1)

Generated 2026-10-31T08:46:01Z. Paper only: no orders, no money. Protocol: `research/PAPER_BOOK_v1/protocol.json`.

## The three plain answers

- **What does it do?** For every US stock that just closed +30%, KOD says DONT_BUY when its dump-tomorrow probability is 0.46 or more, otherwise BUY_OK. The KOD book buys every BUY_OK at the next open and sells five sessions later; $1,000 a position, real costs.
- **Evidence so far?** 11 spikes planned, 0 trades closed. The verdict waits for the planned look at 300 closed trades; until then the numbers are a running tally.
- **What counts as success?** Two separate questions, each at the planned look: DONT_BUY works if the skipped spikes do worse than the bought ones (95% bound below zero); the KOD book makes money if its average trade is above zero (95% bound above zero).

## The books

| Book | What it holds | Positions | Open | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|---:|
| KOD | every BUY_OK | 2 | 2 | 0 | 0 | $+0 | - |
| ALL | every spike | 11 | 11 | 0 | 0 | $+0 | - |
| AVOIDED | every DONT_BUY (kept out) | 9 | 9 | 0 | 0 | $+0 | - |
| OWNER | spikes you confirmed BUY | 0 | 0 | 0 | 0 | $+0 | - |

## Every spike

| Signal | Ticker | Dump tomorrow | KOD | You | Status | Net |
|---|---|---:|---|---|---|---:|
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

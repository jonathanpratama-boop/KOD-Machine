# KOD paper book (PAPER_BOOK_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-09T23:00:44.214968Z; latest US scan session: 2026-11-09.
- Latest compatible LEARNER v2.4 forecast: 2026-11-09T22:57:08Z (signal session 2026-11-09).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

Generated 2026-11-09T23:00:44Z. Paper only: no orders, no money. Protocol: `research/PAPER_BOOK_v1/protocol.json`.

## The three plain answers

- **What does it do?** For every US stock that just closed +30%, KOD says DONT_BUY when its dump-tomorrow probability is 0.46 or more, otherwise BUY_OK. The KOD book buys every BUY_OK at the next open and sells five sessions later; $1,000 a position, real costs.
- **Evidence so far?** 72 spikes planned, 11 trades closed. The verdict waits for the planned look at 300 closed trades; until then the numbers are a running tally.
- **What counts as success?** Two separate questions, each at the planned look: DONT_BUY works if the skipped spikes do worse than the bought ones (95% bound below zero); the KOD book makes money if its average trade is above zero (95% bound above zero).

## The books

| Book | What it holds | Positions | Open | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|---:|
| KOD | every BUY_OK | 61 | 59 | 2 | 1 | $-80 | -4.02% |
| ALL | every spike | 72 | 61 | 11 | 4 | $-1,140 | -10.37% |
| AVOIDED | every DONT_BUY (kept out) | 11 | 2 | 9 | 3 | $-1,060 | -11.78% |
| OWNER | spikes you confirmed BUY | 0 | 0 | 0 | 0 | $+0 | - |

## Every spike

| Signal | Ticker | Dump tomorrow | KOD | You | Status | Net |
|---|---|---:|---|---|---|---:|
| 2026-11-09 | XHLD | 0.34 | BUY_OK | - | OPEN | - |
| 2026-11-09 | WOK | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-09 | UG | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-09 | TVRD | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-09 | TOPS | 0.48 | DONT_BUY | - | OPEN | - |
| 2026-11-09 | TLS | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-09 | TANH | 0.36 | BUY_OK | - | OPEN | - |
| 2026-11-09 | OMH | 0.49 | DONT_BUY | - | OPEN | - |
| 2026-11-09 | NCPL | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-09 | MODD | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-09 | MF | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-09 | JZ | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-09 | INLF | 0.40 | BUY_OK | - | OPEN | - |
| 2026-11-09 | GPUS | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-09 | GFR | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-09 | FJET | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-09 | FISN | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-09 | ESLA | 0.36 | BUY_OK | - | OPEN | - |
| 2026-11-09 | DCTH | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-09 | CVKD | 0.27 | BUY_OK | - | OPEN | - |
| 2026-11-09 | CKX | 0.33 | BUY_OK | - | OPEN | - |
| 2026-11-09 | AKBA | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-06 | VSA | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-06 | VIVK | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-06 | VAI | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-06 | STAK | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-06 | SNT | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-06 | SMX | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-06 | SKIN | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-06 | SERV | 0.10 | BUY_OK | - | OPEN | - |
| 2026-11-06 | SDA | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-06 | RDGT | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-06 | RCT | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-06 | POM | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-06 | OPTU | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-06 | OBX | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-06 | MTVA | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-06 | KRMN | 0.09 | BUY_OK | - | OPEN | - |
| 2026-11-06 | KDK | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-06 | INDI | 0.11 | BUY_OK | - | OPEN | - |
| 2026-11-06 | HTCO | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-06 | HPAI | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-06 | GOGO | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-06 | GIBO | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-06 | FROG | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-06 | FLY | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-06 | CIIT | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-06 | CABR | 0.20 | BUY_OK | - | OPEN | - |
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
| 2026-10-30 | WHLR | 0.62 | DONT_BUY | - | TRADED | -60.01% |
| 2026-10-30 | SLGB | 0.52 | DONT_BUY | - | TRADED | -46.60% |
| 2026-10-30 | SGRX | 0.58 | DONT_BUY | - | TRADED | -28.30% |
| 2026-10-30 | ONEG | 0.61 | DONT_BUY | - | TRADED | -13.46% |
| 2026-10-30 | OMEX | 0.70 | DONT_BUY | - | TRADED | -4.73% |
| 2026-10-30 | MASK | 0.63 | DONT_BUY | - | TRADED | +9.12% |
| 2026-10-30 | GDYN | 0.47 | DONT_BUY | - | TRADED | +0.07% |
| 2026-10-30 | FMC | 0.38 | BUY_OK | - | TRADED | -11.72% |
| 2026-10-30 | CHOW | 0.68 | DONT_BUY | - | TRADED | -12.34% |
| 2026-10-30 | ATYR | 0.65 | DONT_BUY | - | TRADED | +50.24% |
| 2026-10-30 | ASUR | 0.43 | BUY_OK | - | TRADED | +3.69% |

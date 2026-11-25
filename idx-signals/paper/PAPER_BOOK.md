# KOD paper book (PAPER_BOOK_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-25T23:03:09.887809Z; latest US scan session: 2026-11-25.
- Latest compatible LEARNER v2.4 forecast: 2026-11-25T22:58:41Z (signal session 2026-11-25).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

Generated 2026-11-25T23:03:09Z. Paper only: no orders, no money. Protocol: `research/PAPER_BOOK_v1/protocol.json`.

## The three plain answers

- **What does it do?** For every US stock that just closed +30%, KOD says DONT_BUY when its dump-tomorrow probability is 0.46 or more, otherwise BUY_OK. The KOD book buys every BUY_OK at the next open and sells five sessions later; $1,000 a position, real costs.
- **Evidence so far?** 289 spikes planned, 141 trades closed. The verdict waits for the planned look at 300 closed trades; until then the numbers are a running tally.
- **What counts as success?** Two separate questions, each at the planned look: DONT_BUY works if the skipped spikes do worse than the bought ones (95% bound below zero); the KOD book makes money if its average trade is above zero (95% bound above zero).

## The books

| Book | What it holds | Positions | Open | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|---:|
| KOD | every BUY_OK | 265 | 114 | 127 | 31 | $-11,664 | -9.18% |
| ALL | every spike | 289 | 123 | 141 | 34 | $-15,023 | -10.65% |
| AVOIDED | every DONT_BUY (kept out) | 24 | 9 | 14 | 3 | $-3,358 | -23.99% |
| OWNER | spikes you confirmed BUY | 0 | 0 | 0 | 0 | $+0 | - |

## Every spike

| Signal | Ticker | Dump tomorrow | KOD | You | Status | Net |
|---|---|---:|---|---|---|---:|
| 2026-11-25 | TRAW | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-25 | TOPP | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-25 | TMCR | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-25 | SVRE | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-25 | SLSN | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-25 | RMTX | 0.43 | BUY_OK | - | OPEN | - |
| 2026-11-25 | RAYA | 0.38 | BUY_OK | - | OPEN | - |
| 2026-11-25 | RADX | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-25 | NXAT | 0.33 | BUY_OK | - | OPEN | - |
| 2026-11-25 | NRSN | 0.35 | BUY_OK | - | OPEN | - |
| 2026-11-25 | MWYN | 0.12 | BUY_OK | - | OPEN | - |
| 2026-11-25 | LONA | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-25 | KYNB | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-25 | JDZG | 0.61 | DONT_BUY | - | OPEN | - |
| 2026-11-25 | GLXG | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-25 | FNUC | 0.38 | BUY_OK | - | OPEN | - |
| 2026-11-25 | FCUV | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-25 | DKI | 0.53 | DONT_BUY | - | OPEN | - |
| 2026-11-25 | CURR | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-25 | CGTX | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-25 | BYAH | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-25 | BGLC | 0.30 | BUY_OK | - | OPEN | - |
| 2026-11-25 | BBCI | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-25 | ALGS | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-24 | TNYA | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-24 | SMXT | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-24 | RMSG | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-24 | RBNE | 0.34 | BUY_OK | - | OPEN | - |
| 2026-11-24 | PLAG | 0.30 | BUY_OK | - | OPEN | - |
| 2026-11-24 | PARA | 0.37 | BUY_OK | - | OPEN | - |
| 2026-11-24 | ONFO | 0.51 | DONT_BUY | - | OPEN | - |
| 2026-11-24 | MTR | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-24 | LVWR | 0.26 | BUY_OK | - | OPEN | - |
| 2026-11-24 | LGHL | 0.45 | BUY_OK | - | OPEN | - |
| 2026-11-24 | JAGX | 0.65 | DONT_BUY | - | OPEN | - |
| 2026-11-24 | ISPC | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-24 | IBIO | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-24 | GLXG | 0.27 | BUY_OK | - | OPEN | - |
| 2026-11-24 | GFAI | 0.26 | BUY_OK | - | OPEN | - |
| 2026-11-24 | FGL | 0.51 | DONT_BUY | - | OPEN | - |
| 2026-11-24 | EMBC | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-24 | CODX | 0.41 | BUY_OK | - | OPEN | - |
| 2026-11-24 | CD | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-24 | CCTG | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-24 | BENF | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-24 | BDRX | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-24 | APUS | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-24 | ALXO | 0.12 | BUY_OK | - | OPEN | - |
| 2026-11-24 | ALTG | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-24 | ALDX | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-24 | AKAN | 0.42 | BUY_OK | - | OPEN | - |
| 2026-11-23 | ZSQR | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-23 | XCH | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-23 | VIVS | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-23 | TOPP | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-23 | SRTM | 0.47 | DONT_BUY | - | OPEN | - |
| 2026-11-23 | SMTK | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-23 | SCWO | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-23 | SCAG | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-23 | RSSS | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-23 | RIME | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-23 | PTHS | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-23 | PRFX | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-23 | PARA | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-23 | PAAI | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-23 | OTLY | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-23 | NVDA | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-23 | MRM | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-23 | LSTA | 0.30 | BUY_OK | - | OPEN | - |
| 2026-11-23 | LINK | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-23 | KYMR | 0.11 | BUY_OK | - | OPEN | - |
| 2026-11-23 | ITP | 0.26 | BUY_OK | - | OPEN | - |
| 2026-11-23 | INTJ | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-23 | IMCC | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-23 | GRRR | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-23 | FFR | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-23 | DTSS | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-23 | DCGO | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-23 | CYAB | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-23 | CUE | 0.10 | BUY_OK | - | OPEN | - |
| 2026-11-23 | CELU | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-23 | BYSI | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-23 | BUUU | 0.11 | BUY_OK | - | OPEN | - |
| 2026-11-23 | BNAI | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-23 | AUUD | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-23 | ALZN | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-23 | AEON | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-20 | YOUL | 0.47 | DONT_BUY | - | OPEN | - |
| 2026-11-20 | RAYA | 0.41 | BUY_OK | - | OPEN | - |
| 2026-11-20 | NXAT | 0.40 | BUY_OK | - | OPEN | - |
| 2026-11-20 | NIXX | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-20 | MSS | 0.33 | BUY_OK | - | OPEN | - |
| 2026-11-20 | MEDS | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-20 | LVWR | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-20 | CIGL | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-20 | BNAI | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-20 | AMCI | 0.43 | BUY_OK | - | OPEN | - |
| 2026-11-19 | ZKIN | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-19 | VIVS | 0.42 | BUY_OK | - | OPEN | - |
| 2026-11-19 | SEAT | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-19 | RAYA | 0.30 | BUY_OK | - | OPEN | - |
| 2026-11-19 | POAS | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-19 | MRKR | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-19 | MPU | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-19 | LVWR | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-19 | HTCR | 0.27 | BUY_OK | - | OPEN | - |
| 2026-11-19 | ELOG | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-19 | BDMD | 0.52 | DONT_BUY | - | OPEN | - |
| 2026-11-19 | BAER | 0.26 | BUY_OK | - | OPEN | - |
| 2026-11-18 | VWAV | 0.51 | DONT_BUY | - | OPEN | - |
| 2026-11-18 | SVRE | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-18 | SKYA | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-18 | NUR | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-18 | MPU | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-18 | ICU | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-18 | HIHO | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-18 | CUE | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-18 | CLRO | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-18 | BTOC | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-18 | AZI | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-18 | ANPA | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-18 | AKAN | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-17 | VAI | 0.17 | BUY_OK | - | TRADED | -9.96% |
| 2026-11-17 | TGL | 0.23 | BUY_OK | - | TRADED | -31.72% |
| 2026-11-17 | SYPR | 0.10 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-17 | SMTK | 0.49 | DONT_BUY | - | UNRESOLVABLE | - |
| 2026-11-17 | SLS | 0.22 | BUY_OK | - | TRADED | -34.74% |
| 2026-11-17 | SGRX | 0.22 | BUY_OK | - | TRADED | -5.75% |
| 2026-11-17 | NCT | 0.61 | DONT_BUY | - | TRADED | -29.58% |
| 2026-11-17 | MPU | 0.23 | BUY_OK | - | TRADED | +100.70% |
| 2026-11-17 | KALA | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-17 | GP | 0.27 | BUY_OK | - | TRADED | -34.11% |
| 2026-11-17 | GLSI | 0.13 | BUY_OK | - | TRADED | +2.70% |
| 2026-11-17 | FRTT | 0.19 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-17 | DFSC | 0.25 | BUY_OK | - | TRADED | +0.01% |
| 2026-11-17 | CVKD | 0.16 | BUY_OK | - | TRADED | -20.91% |
| 2026-11-17 | AZI | 0.23 | BUY_OK | - | TRADED | -60.61% |
| 2026-11-17 | AYTU | 0.13 | BUY_OK | - | TRADED | +0.12% |
| 2026-11-16 | VIVK | 0.55 | DONT_BUY | - | TRADED | -39.73% |
| 2026-11-16 | TDTH | 0.28 | BUY_OK | - | TRADED | -65.38% |
| 2026-11-16 | HIHO | 0.22 | BUY_OK | - | TRADED | +7.32% |
| 2026-11-16 | GMM | 0.44 | BUY_OK | - | TRADED | +33.90% |
| 2026-11-16 | GDHG | 0.32 | BUY_OK | - | TRADED | -86.41% |
| 2026-11-16 | ETS | 0.13 | BUY_OK | - | TRADED | -15.85% |
| 2026-11-16 | CYAB | 0.29 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-16 | COSM | 0.26 | BUY_OK | - | TRADED | +1.00% |
| 2026-11-16 | CLRO | 0.31 | BUY_OK | - | TRADED | -4.31% |
| 2026-11-16 | BGIN | 0.18 | BUY_OK | - | TRADED | +7.87% |
| 2026-11-16 | AKAN | 0.31 | BUY_OK | - | TRADED | +170.48% |
| 2026-11-13 | ZBAO | 0.43 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-13 | VTSI | 0.13 | BUY_OK | - | TRADED | -0.77% |
| 2026-11-13 | TGHL | 0.16 | BUY_OK | - | TRADED | -54.80% |
| 2026-11-13 | SLSN | 0.15 | BUY_OK | - | TRADED | -3.50% |
| 2026-11-13 | SLND | 0.09 | BUY_OK | - | TRADED | -24.12% |
| 2026-11-13 | SHIM | 0.10 | BUY_OK | - | TRADED | -1.90% |
| 2026-11-13 | SHFS | 0.43 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-13 | SBC | 0.09 | BUY_OK | - | TRADED | -15.71% |
| 2026-11-13 | RAIN | 0.13 | BUY_OK | - | TRADED | -23.32% |
| 2026-11-13 | ONFO | 0.38 | BUY_OK | - | TRADED | -36.54% |
| 2026-11-13 | NMAX | 0.09 | BUY_OK | - | TRADED | -24.66% |
| 2026-11-13 | LFTO | 0.08 | BUY_OK | - | TRADED | -8.76% |
| 2026-11-13 | LFMD | 0.09 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-13 | FCUV | 0.34 | BUY_OK | - | TRADED | -33.90% |
| 2026-11-13 | FCDH | 0.14 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-13 | BKHA | 0.22 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-13 | BGIN | 0.14 | BUY_OK | - | TRADED | +40.95% |
| 2026-11-13 | AKAN | 0.28 | BUY_OK | - | TRADED | +33.03% |
| 2026-11-13 | AEI | 0.14 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-12 | XLAB | 0.28 | BUY_OK | - | TRADED | -42.50% |
| 2026-11-12 | TGHL | 0.17 | BUY_OK | - | TRADED | -49.70% |
| 2026-11-12 | TGEN | 0.14 | BUY_OK | - | TRADED | -30.38% |
| 2026-11-12 | RIME | 0.15 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-12 | POAS | 0.32 | BUY_OK | - | TRADED | -26.80% |
| 2026-11-12 | PLCE | 0.28 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-12 | PARA | 0.29 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-12 | ICMB | 0.16 | BUY_OK | - | TRADED | -15.37% |
| 2026-11-12 | GP | 0.25 | BUY_OK | - | TRADED | +176.28% |
| 2026-11-12 | DBGI | 0.35 | BUY_OK | - | TRADED | -8.01% |
| 2026-11-12 | BGIN | 0.16 | BUY_OK | - | TRADED | +88.22% |
| 2026-11-12 | ARAI | 0.33 | BUY_OK | - | TRADED | -46.99% |
| 2026-11-12 | AIMD | 0.22 | BUY_OK | - | TRADED | +27.11% |
| 2026-11-12 | ADXN | 0.19 | BUY_OK | - | TRADED | -27.68% |
| 2026-11-12 | ADVB | 0.17 | BUY_OK | - | TRADED | -48.63% |
| 2026-11-11 | WHLR | 0.41 | BUY_OK | - | TRADED | -39.23% |
| 2026-11-11 | TANH | 0.16 | BUY_OK | - | TRADED | +14.69% |
| 2026-11-11 | SLXN | 0.31 | BUY_OK | - | TRADED | -52.17% |
| 2026-11-11 | SHFS | 0.40 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-11 | SFWL | 0.14 | BUY_OK | - | TRADED | +6.37% |
| 2026-11-11 | SCKT | 0.17 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-11 | RKDA | 0.17 | BUY_OK | - | TRADED | -11.25% |
| 2026-11-11 | RETO | 0.37 | BUY_OK | - | TRADED | -26.17% |
| 2026-11-11 | REED | 0.08 | BUY_OK | - | TRADED | -18.70% |
| 2026-11-11 | OPTT | 0.25 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-11 | NWTG | 0.10 | BUY_OK | - | TRADED | -33.09% |
| 2026-11-11 | NCT | 0.25 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-11 | GOVX | 0.36 | BUY_OK | - | TRADED | -9.96% |
| 2026-11-11 | GEVO | 0.08 | BUY_OK | - | TRADED | -8.66% |
| 2026-11-11 | ELOG | 0.14 | BUY_OK | - | TRADED | +67.22% |
| 2026-11-11 | CANG | 0.14 | BUY_OK | - | TRADED | +7.53% |
| 2026-11-11 | BURU | 0.33 | BUY_OK | - | TRADED | -9.23% |
| 2026-11-11 | BSEM | 0.16 | BUY_OK | - | TRADED | -51.68% |
| 2026-11-11 | BGS | 0.08 | BUY_OK | - | TRADED | -9.36% |
| 2026-11-10 | ZIP | 0.11 | BUY_OK | - | TRADED | -1.54% |
| 2026-11-10 | TTEC | 0.15 | BUY_OK | - | TRADED | +27.35% |
| 2026-11-10 | TREO | 0.18 | BUY_OK | - | TRADED | -23.61% |
| 2026-11-10 | TANH | 0.30 | BUY_OK | - | TRADED | +27.59% |
| 2026-11-10 | SMX | 0.26 | BUY_OK | - | TRADED | -82.51% |
| 2026-11-10 | PXLW | 0.17 | BUY_OK | - | TRADED | -12.65% |
| 2026-11-10 | PEPG | 0.26 | BUY_OK | - | TRADED | -29.54% |
| 2026-11-10 | NNOX | 0.16 | BUY_OK | - | TRADED | -37.44% |
| 2026-11-10 | NCI | 0.33 | BUY_OK | - | TRADED | -34.08% |
| 2026-11-10 | MNDO | 0.16 | BUY_OK | - | TRADED | -0.21% |
| 2026-11-10 | MI | 0.31 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-10 | LGVN | 0.19 | BUY_OK | - | TRADED | -34.90% |
| 2026-11-10 | INLF | 0.49 | DONT_BUY | - | TRADED | -54.92% |
| 2026-11-10 | ESLA | 0.31 | BUY_OK | - | TRADED | -58.32% |
| 2026-11-10 | AACG | 0.18 | BUY_OK | - | TRADED | -28.22% |
| 2026-11-09 | XHLD | 0.34 | BUY_OK | - | TRADED | -15.06% |
| 2026-11-09 | WOK | 0.29 | BUY_OK | - | TRADED | -6.33% |
| 2026-11-09 | UG | 0.17 | BUY_OK | - | TRADED | -23.40% |
| 2026-11-09 | TVRD | 0.32 | BUY_OK | - | TRADED | -28.06% |
| 2026-11-09 | TOPS | 0.48 | DONT_BUY | - | TRADED | -22.03% |
| 2026-11-09 | TLS | 0.16 | BUY_OK | - | TRADED | -3.36% |
| 2026-11-09 | TANH | 0.36 | BUY_OK | - | TRADED | +152.51% |
| 2026-11-09 | OMH | 0.49 | DONT_BUY | - | TRADED | -83.56% |
| 2026-11-09 | NCPL | 0.21 | BUY_OK | - | TRADED | +29.63% |
| 2026-11-09 | MODD | 0.14 | BUY_OK | - | TRADED | -1.54% |
| 2026-11-09 | MF | 0.31 | BUY_OK | - | TRADED | +48.85% |
| 2026-11-09 | JZ | 0.32 | BUY_OK | - | TRADED | +4.39% |
| 2026-11-09 | INLF | 0.40 | BUY_OK | - | TRADED | +14.45% |
| 2026-11-09 | GPUS | 0.28 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-09 | GFR | 0.15 | BUY_OK | - | TRADED | -0.56% |
| 2026-11-09 | FJET | 0.23 | BUY_OK | - | TRADED | -27.91% |
| 2026-11-09 | FISN | 0.28 | BUY_OK | - | TRADED | -1.00% |
| 2026-11-09 | ESLA | 0.36 | BUY_OK | - | TRADED | -39.28% |
| 2026-11-09 | DCTH | 0.17 | BUY_OK | - | TRADED | -4.63% |
| 2026-11-09 | CVKD | 0.27 | BUY_OK | - | TRADED | +36.86% |
| 2026-11-09 | CKX | 0.33 | BUY_OK | - | TRADED | -18.63% |
| 2026-11-09 | AKBA | 0.22 | BUY_OK | - | TRADED | -27.24% |
| 2026-11-06 | VSA | 0.17 | BUY_OK | - | TRADED | -33.61% |
| 2026-11-06 | VIVK | 0.29 | BUY_OK | - | TRADED | -13.88% |
| 2026-11-06 | VAI | 0.15 | BUY_OK | - | TRADED | -2.33% |
| 2026-11-06 | STAK | 0.20 | BUY_OK | - | TRADED | -50.35% |
| 2026-11-06 | SNT | 0.16 | BUY_OK | - | TRADED | -2.06% |
| 2026-11-06 | SMX | 0.23 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-06 | SKIN | 0.15 | BUY_OK | - | TRADED | -7.55% |
| 2026-11-06 | SERV | 0.10 | BUY_OK | - | TRADED | -26.08% |
| 2026-11-06 | SDA | 0.20 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-06 | RDGT | 0.14 | BUY_OK | - | TRADED | -9.92% |
| 2026-11-06 | RCT | 0.25 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-06 | POM | 0.22 | BUY_OK | - | TRADED | -0.38% |
| 2026-11-06 | OPTU | 0.14 | BUY_OK | - | TRADED | -9.14% |
| 2026-11-06 | OBX | 0.16 | BUY_OK | - | TRADED | -7.63% |
| 2026-11-06 | MTVA | 0.14 | BUY_OK | - | TRADED | -16.58% |
| 2026-11-06 | KRMN | 0.09 | BUY_OK | - | TRADED | -18.08% |
| 2026-11-06 | KDK | 0.14 | BUY_OK | - | TRADED | -17.11% |
| 2026-11-06 | INDI | 0.11 | BUY_OK | - | TRADED | +6.66% |
| 2026-11-06 | HTCO | 0.19 | BUY_OK | - | TRADED | -7.62% |
| 2026-11-06 | HPAI | 0.23 | BUY_OK | - | TRADED | -33.71% |
| 2026-11-06 | GOGO | 0.18 | BUY_OK | - | TRADED | -17.84% |
| 2026-11-06 | GIBO | 0.14 | BUY_OK | - | TRADED | -51.75% |
| 2026-11-06 | FROG | 0.08 | BUY_OK | - | TRADED | +8.00% |
| 2026-11-06 | FLY | 0.14 | BUY_OK | - | TRADED | +5.49% |
| 2026-11-06 | CIIT | 0.16 | BUY_OK | - | TRADED | -20.71% |
| 2026-11-06 | CABR | 0.20 | BUY_OK | - | TRADED | -25.95% |
| 2026-11-05 | ZNB | 0.22 | BUY_OK | - | TRADED | -30.41% |
| 2026-11-05 | XXII | 0.36 | BUY_OK | - | TRADED | -56.37% |
| 2026-11-05 | VXX | 0.11 | BUY_OK | - | TRADED | -13.98% |
| 2026-11-05 | PLCE | 0.14 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-05 | LABT | 0.33 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-05 | JDZG | 0.15 | BUY_OK | - | TRADED | -47.37% |
| 2026-11-05 | HTCR | 0.13 | BUY_OK | - | TRADED | -14.94% |
| 2026-11-05 | FLYE | 0.15 | BUY_OK | - | TRADED | -14.89% |
| 2026-11-05 | DNUT | 0.13 | BUY_OK | - | TRADED | -12.59% |
| 2026-11-05 | BDMD | 0.15 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-05 | APP | 0.09 | BUY_OK | - | TRADED | +14.81% |
| 2026-11-05 | AMTX | 0.13 | BUY_OK | - | TRADED | -33.26% |
| 2026-11-05 | AEHL | 0.30 | BUY_OK | - | TRADED | -21.11% |
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


## Secondary view: split-unit assessments (display only, the frozen verdict above is unchanged)

29 of 289 planned spikes are split artifacts on current evidence (20 confirmed, 9 probable): a reverse split left the previous close in pre-split units, so the recorded +30% day did not happen. 3 are unresolved and stay in every view. 1 carried an artifact tag that current evidence does not support. Ledgers: `paper/split_flags.jsonl` (rule `SPLIT_ARTIFACT_V11`, the tag at the time) and `paper/split_assessments.jsonl` (rule `SPLIT_UNITS_V1`, research/SPLIT_REVISIONS_v1).

| Spike | Session | Tag at the time | Tag recorded before entry cutoff | Current assessment | Assessed |
|---|---|---|---|---|---|
| ATYR | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| MASK | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| OMEX | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_PROBABLE | 2026-11-13 |
| WHLR | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| XXII | 2026-11-05 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| TOPS | 2026-11-09 | ARTIFACT_V11 | no | ARTIFACT_PROBABLE | 2026-11-13 |
| SMX | 2026-11-10 | ARTIFACT_V11 | yes | REAL_MOVE_AFTER_SPLIT | 2026-11-13 |
| GOVX | 2026-11-11 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-13 |
| SLXN | 2026-11-11 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-13 |
| ARAI | 2026-11-12 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-13 |
| COSM | 2026-11-16 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-16 |
| DFSC | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| KALA | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| NCT | 2026-11-17 | INDETERMINATE | yes | REAL_MOVE_UNITS_UNVERIFIED | 2026-11-17 |
| SGRX | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| TGL | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| NIXX | 2026-11-20 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-23 |
| AUUD | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| CYAB | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| IMCC | 2026-11-23 | NOT_FLAGGED | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| ITP | 2026-11-23 | INDETERMINATE | yes | REAL_MOVE_UNITS_CONTAMINATED | 2026-11-24 |
| LSTA | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| PARA | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_PROBABLE | 2026-11-24 |
| RIME | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| SMTK | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| SRTM | 2026-11-23 | INDETERMINATE | yes | REAL_MOVE_UNITS_CONTAMINATED | 2026-11-24 |
| TOPP | 2026-11-23 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-24 |
| CCTG | 2026-11-24 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-25 |
| CODX | 2026-11-24 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-25 |
| GFAI | 2026-11-24 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-25 |
| ISPC | 2026-11-24 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-25 |
| JAGX | 2026-11-24 | INDETERMINATE | yes | REAL_MOVE_UNITS_CONTAMINATED | 2026-11-25 |
| PARA | 2026-11-24 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-24 |
| RBNE | 2026-11-24 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-25 |
| FNUC | 2026-11-25 | INDETERMINATE | yes | UNEXPLAINED_EXTREME_MOVE | 2026-11-25 |
| RMTX | 2026-11-25 | INDETERMINATE | yes | UNEXPLAINED_EXTREME_MOVE | 2026-11-25 |

The same books three ways. As frozen counts every planned spike. Known at the time leaves out only the spikes whose artifact tag was recorded before their entry cutoff: it is what a filter could have done on the day. Corrected leaves out the spikes that current evidence classes as artifacts: it uses evidence that arrived later and is not a filter that was available before the trade. This is a disclosure, not a second verdict: the planned look and the bounds above are computed on every planned spike, as frozen.

| Book | View | Positions | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|
| KOD | As frozen | 265 | 127 | 31 | $-11,664 | -9.18% |
| KOD | Known at the time | 257 | 121 | 29 | $-10,005 | -8.27% |
| KOD | Corrected | 241 | 119 | 29 | $-9,645 | -8.10% |
| ALL | As frozen | 289 | 141 | 34 | $-15,023 | -10.65% |
| ALL | Known at the time | 281 | 135 | 32 | $-13,363 | -9.90% |
| ALL | Corrected | 260 | 128 | 30 | $-12,729 | -9.94% |
| AVOIDED | As frozen | 24 | 14 | 3 | $-3,358 | -23.99% |
| AVOIDED | Known at the time | 24 | 14 | 3 | $-3,358 | -23.99% |
| AVOIDED | Corrected | 19 | 9 | 1 | $-3,084 | -34.27% |
| OWNER | As frozen | 0 | 0 | 0 | $+0 | - |
| OWNER | Known at the time | 0 | 0 | 0 | $+0 | - |
| OWNER | Corrected | 0 | 0 | 0 | $+0 | - |

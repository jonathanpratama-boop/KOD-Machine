# KOD paper account (PAPER_ACCOUNT_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-23T23:06:40.066467Z; latest US scan session: 2026-11-23.
- Latest compatible LEARNER v2.4 forecast: 2026-11-23T23:00:51Z (signal session 2026-11-23).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

As of the latest record (2026-11-23T23:05:02Z). Paper only: no orders, no money. Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`.

## The three plain answers

- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real execution rules with one shared $10,000 account per arm: 0.5% planned loss per position, 1.5% for everything at once, at most 3 new orders per session, no leverage. An order fills only at the next opening print inside its limit; stops and the five-session time exit come from the bars.
- **How to read the money:** cash is what the account holds; reserved is cash set aside for orders waiting for the next open (not spent, not lost, just unavailable to another order); available = cash minus reserved. Equity = cash plus open positions at their latest recorded price. Realized P&L counts only closed trades.
- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the stop 5% below the fill. Same candidates, costs and exits. Each arm is a separate simulated account.

## Accounts

| Arm | Cash | Reserved | Available | Open value | Equity | Realized | Unrealized | Pending | Filled | Rejected | Cancelled | Declined | Closed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | $10,105.51 | $2,618.83 | $7,486.68 | $0.00 | $10,105.51 | $105.51 | $0.00 | 3 | 1 | 14 | 0 | 201 | 1 |
| FIXED5 | $9,787.01 | $2,628.39 | $7,158.62 | $0.00 | $9,787.01 | -$212.99 | $0.00 | 3 | 8 | 0 | 0 | 208 | 8 |

## Open positions and valuation

- No open positions.

## Drawdown (from recorded nightly marks only)

- BASE: -0.32% across 17 mark(s), trough at the close of 2026-11-12
- FIXED5: -2.18% across 17 mark(s), trough at the close of 2026-11-18

## Every decision

| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |
|---|---|---|---|---|---|---|---:|
| 2026-10-30 | FMC | BASE | KOD | order 174 @ <= 5.42, reserved $944.49 | REJECTED_STOP_TOO_WIDE: open 6.11 is above the permitted entry 5.42: the stop at 5.15 would be 15.71% away, more than 5% | - | - |
| 2026-10-30 | ASUR | BASE | KOD | order 107 @ <= 8.89, reserved $952.66 | REJECTED_STOP_TOO_WIDE: open 9.98 is above the permitted entry 8.89: the stop at 8.45 would be 15.33% away, more than 5% | - | - |
| 2026-11-05 | APP | BASE | KOD | order 2 @ <= 356.71, reserved $713.78 | filled 2 @ 356 on 2026-11-06, stop 338.9 | TIME_EXIT_AT_CLOSE 2026-11-13 @ 409.1 | $105.51 |
| 2026-11-05 | VXX | BASE | KOD | order 51 @ <= 18.2, reserved $929.59 | REJECTED_STOP_TOO_WIDE: open 21.73 is above the permitted entry 18.2: the stop at 17.29 would be 20.43% away, more than 5% | - | - |
| 2026-11-05 | HTCR | BASE | KOD | order 694 @ <= 1.2, reserved $836.96 | REJECTED_STOP_TOO_WIDE: open 1.63 is above the permitted entry 1.2: the stop at 1.14 would be 30.06% away, more than 5% | - | - |
| 2026-11-05 | DNUT | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | AMTX | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | PLCE | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | FLYE | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | JDZG | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | BDMD | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | ZNB | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | AEHL | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | LABT | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-05 | XXII | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-06 | FROG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 47.97 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | KRMN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 49.33 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | SERV | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.32 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | INDI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.26 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | MTVA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.31 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | KDK | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.33 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | GIBO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 48.86 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | RDGT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.31 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | FLY | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 49.61 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | OPTU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.31 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | VAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.33 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | SKIN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.30 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | SNT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.30 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | CIIT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.27 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | OBX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.19 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | VSA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.34 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | GOGO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.28 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | HTCO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.29 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | CABR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.31 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | SDA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.34 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | STAK | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.26 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | POM | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.32 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | SMX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.34 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | HPAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.34 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | RCT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.35 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-06 | VIVK | BASE | KOD | declined: LIMIT_PLANNED_RISK: 105.04 + 50.32 would exceed 1.5% of equity 10070.18 | - | - | - |
| 2026-11-09 | MODD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.52 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | GFR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.52 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | TLS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.46 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | UG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.50 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | DCTH | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 49.77 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | NCPL | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.48 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | AKBA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.51 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | FJET | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.51 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | CVKD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.52 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | FISN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.44 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | GPUS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.53 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | WOK | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.48 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | MF | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.45 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | TVRD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.50 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | JZ | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.48 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | CKX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.28 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | XHLD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.51 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | TANH | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.00 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | ESLA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.52 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-09 | INLF | BASE | KOD | declined: LIMIT_PLANNED_RISK: 142.60 + 50.53 would exceed 1.5% of equity 10107.74 | - | - | - |
| 2026-11-10 | ZIP | BASE | KOD | declined: LIMIT_PLANNED_RISK: 113.62 + 50.19 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | TTEC | BASE | KOD | declined: LIMIT_PLANNED_RISK: 113.62 + 50.33 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | NNOX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 113.62 + 50.38 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | MNDO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 113.62 + 50.39 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | PXLW | BASE | KOD | declined: LIMIT_PLANNED_RISK: 113.62 + 50.34 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | TREO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 113.62 + 50.36 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | AACG | BASE | KOD | order 745 @ <= 0.5801, reserved $438.66 | REJECTED_STOP_TOO_WIDE: open 0.96 is above the permitted entry 0.5801: the stop at 0.5511 would be 42.59% away, more than 5% | - | - |
| 2026-11-10 | LGVN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 50.28 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | PEPG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 50.35 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | SMX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 49.98 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | TANH | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 50.29 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | ESLA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 50.38 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | MI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 50.38 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-10 | NCI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 148.20 + 50.22 would exceed 1.5% of equity 10078.76 | - | - | - |
| 2026-11-11 | REED | BASE | KOD | declined: LIMIT_PLANNED_RISK: 132.14 + 50.42 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | BGS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 132.14 + 50.33 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | GEVO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 132.14 + 50.46 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | NWTG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 132.14 + 50.49 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | ELOG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 132.14 + 50.46 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | SFWL | BASE | KOD | order 85 @ <= 3.7, reserved $316.07 | REJECTED_STOP_TOO_WIDE: open 4.67 is above the permitted entry 3.7: the stop at 3.52 would be 24.63% away, more than 5% | - | - |
| 2026-11-11 | CANG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.44 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | BSEM | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.44 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | TANH | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 49.44 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | RKDA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.48 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | SCKT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.48 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | NCT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.46 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | OPTT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.48 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | SLXN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.38 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | BURU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.47 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | GOVX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.46 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | RETO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.41 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | SHFS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.49 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-11 | WHLR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 150.59 + 50.47 would exceed 1.5% of equity 10097.28 | - | - | - |
| 2026-11-12 | TGEN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.32 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | RIME | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | ICMB | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | BGIN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.27 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | ADVB | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.23 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | TGHL | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | ADXN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | AIMD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.35 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | GP | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | PLCE | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | XLAB | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.35 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | PARA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.38 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | POAS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.32 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | ARAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.35 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-12 | DBGI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 109.96 + 50.37 would exceed 1.5% of equity 10075.10 | - | - | - |
| 2026-11-13 | LFTO | BASE | KOD | order 44 @ <= 22.3, reserved $981.69 | REJECTED_STOP_TOO_WIDE: open 24.93 is above the permitted entry 22.3: the stop at 21.19 would be 15.00% away, more than 5% | - | - |
| 2026-11-13 | SBC | BASE | KOD | order 153 @ <= 6.38, reserved $977.60 | REJECTED_STOP_TOO_WIDE: open 7.12 is above the permitted entry 6.38: the stop at 6.07 would be 14.75% away, more than 5% | - | - |
| 2026-11-13 | LFMD | BASE | KOD | order 461 @ <= 1.94, reserved $898.81 | pending: next open (before 2026-11-16T14:30:00Z) | - | - |
| 2026-11-13 | NMAX | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SLND | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SHIM | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | RAIN | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | VTSI | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | AEI | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | FCDH | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | BGIN | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SLSN | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | TGHL | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | BKHA | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | AKAN | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | FCUV | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | ONFO | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SHFS | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | ZBAO | BASE | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-16 | ETS | BASE | KOD | order 589 @ <= 1.57, reserved $929.35 | REJECTED_STOP_TOO_WIDE: open 2 is above the permitted entry 1.57: the stop at 1.5 would be 25.00% away, more than 5% | - | - |
| 2026-11-16 | BGIN | BASE | KOD | order 232 @ <= 3.72, reserved $867.36 | REJECTED_STOP_TOO_WIDE: open 4.78 is above the permitted entry 3.72: the stop at 3.54 would be 25.94% away, more than 5% | - | - |
| 2026-11-16 | HIHO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | COSM | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.47 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | TDTH | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | CYAB | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.53 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | AKAN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.49 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | CLRO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.41 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | GDHG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.49 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-16 | GMM | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.37 + 50.45 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | SYPR | BASE | KOD | order 699 @ <= 1.22, reserved $857.04 | pending: next open (before 2026-11-18T14:30:00Z) | - | - |
| 2026-11-17 | GLSI | BASE | KOD | order 58 @ <= 16.54, reserved $960.76 | REJECTED_STOP_TOO_WIDE: open 18.6 is above the permitted entry 16.54: the stop at 15.72 would be 15.48% away, more than 5% | - | - |
| 2026-11-17 | AYTU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | KALA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.35 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | CVKD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | VAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.44 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | FRTT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | SLS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 49.85 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | SGRX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.41 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | TGL | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.32 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | AZI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | MPU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 36.40 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | DFSC | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.44 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-17 | GP | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.41 + 50.49 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | CUE | BASE | KOD | order 247 @ <= 3.43, reserved $851.45 | REJECTED_STOP_TOO_WIDE: open 4.55 is above the permitted entry 3.43: the stop at 3.26 would be 28.35% away, more than 5% | - | - |
| 2026-11-18 | HIHO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | CLRO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | SKYA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.47 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | ANPA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.47 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | AZI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | MPU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.49 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | NUR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | ICU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | BTOC | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | SVRE | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-18 | AKAN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.38 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | ZKIN | BASE | KOD | order 535 @ <= 1.13, reserved $607.57 | REJECTED_STOP_TOO_WIDE: open 1.54 is above the permitted entry 1.13: the stop at 1.08 would be 29.87% away, more than 5% | - | - |
| 2026-11-19 | MRKR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | ELOG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | LVWR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | SEAT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | BAER | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | HTCR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | MPU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.42 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | RAYA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | POAS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.42 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-19 | VIVS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 133.76 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | LVWR | BASE | KOD | order 982 @ <= 0.6431, reserved $641.00 | REJECTED_STOP_TOO_WIDE: open 0.9801 is above the permitted entry 0.6431: the stop at 0.611 would be 37.66% away, more than 5% | - | - |
| 2026-11-20 | BNAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.39 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | CIGL | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.53 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | NIXX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.45 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | MEDS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.49 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | MSS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | NXAT | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | RAYA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.53 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-20 | AMCI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.44 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | RSSS | BASE | KOD | order 261 @ <= 3.29, reserved $862.98 | pending: next open (before 2026-11-24T14:30:00Z) | - | - |
| 2026-11-23 | NVDA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | CUE | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.38 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | BUUU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | KYMR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 43.78 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | GRRR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | SCWO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | PAAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | INTJ | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | FFR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | PRFX | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | OTLY | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.27 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | CELU | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | DCGO | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | PTHS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.42 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | DTSS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | MRM | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 47.03 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | BNAI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.40 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | XCH | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.40 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | ZSQR | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.43 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | AUUD | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | AEON | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.52 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | BYSI | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | RIME | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | LINK | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.41 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | IMCC | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.51 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | ALZN | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.47 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | SMTK | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | CYAB | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | SCAG | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.50 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | ITP | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | VIVS | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.53 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | TOPP | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.53 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | PARA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.49 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-11-23 | LSTA | BASE | KOD | declined: LIMIT_PLANNED_RISK: 151.32 + 50.48 would exceed 1.5% of equity 10105.51 | - | - | - |
| 2026-10-30 | FMC | FIXED5 | KOD | order 138 @ <= 6.8, reserved $939.81 | filled 138 @ 6.11 on 2026-11-02, stop 5.81 | STOP 2026-11-06 @ 5.81 | -$43.89 |
| 2026-10-30 | ASUR | FIXED5 | KOD | order 92 @ <= 10.34, reserved $952.71 | filled 92 @ 9.98 on 2026-11-02, stop 9.49 | STOP 2026-11-02 @ 9.49 | -$47.79 |
| 2026-11-05 | APP | FIXED5 | KOD | order 2 @ <= 391.7, reserved $783.79 | filled 2 @ 356 on 2026-11-06, stop 338.2 | TIME_EXIT_AT_CLOSE 2026-11-13 @ 409.1 | $105.51 |
| 2026-11-05 | VXX | FIXED5 | KOD | order 39 @ <= 24.41, reserved $952.47 | filled 39 @ 21.73 on 2026-11-06, stop 20.65 | STOP 2026-11-06 @ 20.65 | -$42.97 |
| 2026-11-05 | HTCR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.65 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | DNUT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.60 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | AMTX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.68 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | PLCE | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.70 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | FLYE | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.59 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | JDZG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.71 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | BDMD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.71 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | ZNB | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.68 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | AEHL | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.39 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | LABT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.69 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-05 | XXII | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 125.63 + 49.68 would exceed 1.5% of equity 9945.43 | - | - | - |
| 2026-11-06 | FROG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 45.31 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | KRMN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 48.48 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | SERV | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.50 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | INDI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.65 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | MTVA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.67 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | KDK | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.67 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | GIBO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.19 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | RDGT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.66 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | FLY | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 48.87 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | OPTU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.67 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | VAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.56 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | SKIN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.26 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | SNT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.63 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | CIIT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.57 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | OBX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.17 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | VSA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.56 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | GOGO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.53 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | HTCO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.66 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | CABR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.64 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | SDA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.66 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | STAK | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.60 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | POM | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.65 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | SMX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.60 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | HPAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.66 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | RCT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.67 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-06 | VIVK | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 106.48 + 49.64 would exceed 1.5% of equity 9935.53 | - | - | - |
| 2026-11-09 | MODD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.79 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | GFR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.47 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | TLS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.66 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | UG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.41 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | DCTH | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.85 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | NCPL | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.82 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | AKBA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.85 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | FJET | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.84 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | CVKD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.86 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | FISN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.80 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | GPUS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.86 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | WOK | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.85 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | MF | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.66 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | TVRD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.81 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | JZ | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.85 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | CKX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.64 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | XHLD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.82 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | TANH | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.77 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | ESLA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.82 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-09 | INLF | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 144.04 + 49.84 would exceed 1.5% of equity 9973.09 | - | - | - |
| 2026-11-10 | ZIP | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.65 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | TTEC | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.57 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | NNOX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.70 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | MNDO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.70 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | PXLW | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.63 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | TREO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.67 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | AACG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.71 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | LGVN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.65 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | PEPG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.61 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | SMX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.30 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | TANH | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 48.01 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | ESLA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.72 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | MI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.69 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-10 | NCI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 115.06 + 49.41 would exceed 1.5% of equity 9944.11 | - | - | - |
| 2026-11-11 | REED | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.80 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | BGS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.74 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | GEVO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.70 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | NWTG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.78 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | ELOG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.76 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | SFWL | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 24.36 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | CANG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.79 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | BSEM | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.75 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | TANH | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.39 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | RKDA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.81 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | SCKT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.77 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | NCT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.75 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | OPTT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.80 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | SLXN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.73 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | BURU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.80 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | GOVX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.72 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | RETO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.76 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | SHFS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.81 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-11 | WHLR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 133.58 + 49.79 would exceed 1.5% of equity 9962.63 | - | - | - |
| 2026-11-12 | TGEN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.66 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | RIME | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.69 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | ICMB | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.66 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | BGIN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.58 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | ADVB | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.56 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | TGHL | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.69 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | ADXN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.52 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | AIMD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.66 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | GP | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.64 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | PLCE | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.69 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | XLAB | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.69 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | PARA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.70 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | POAS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.62 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | ARAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.58 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-12 | DBGI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 111.40 + 49.69 would exceed 1.5% of equity 9940.45 | - | - | - |
| 2026-11-13 | LFTO | FIXED5 | KOD | order 36 @ <= 26.87, reserved $967.80 | filled 36 @ 24.93 on 2026-11-16, stop 23.69 | STOP 2026-11-17 @ 23.69 | -$45.54 |
| 2026-11-13 | SBC | FIXED5 | KOD | order 117 @ <= 8.07, reserved $945.61 | filled 117 @ 7.12 on 2026-11-16, stop 6.77 | STOP 2026-11-16 @ 6.77 | -$43.41 |
| 2026-11-13 | LFMD | FIXED5 | KOD | order 346 @ <= 2.4, reserved $834.55 | pending: next open (before 2026-11-16T14:30:00Z) | - | - |
| 2026-11-13 | NMAX | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SLND | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SHIM | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | RAIN | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | VTSI | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | AEI | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | FCDH | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | BGIN | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SLSN | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | TGHL | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | BKHA | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | AKAN | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | FCUV | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | ONFO | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | SHFS | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-13 | ZBAO | FIXED5 | KOD | declined: LIMIT_NEW_PER_SESSION: 3 orders already placed for this session | - | - | - |
| 2026-11-16 | ETS | FIXED5 | KOD | order 407 @ <= 2.15, reserved $879.43 | filled 407 @ 2 on 2026-11-17, stop 1.9 | STOP 2026-11-17 @ 1.9 | -$48.66 |
| 2026-11-16 | BGIN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.37 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | HIHO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.51 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | COSM | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.54 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | TDTH | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.53 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | CYAB | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.54 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | AKAN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.48 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | CLRO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.38 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | GDHG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.50 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-16 | GMM | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 127.49 + 49.52 would exceed 1.5% of equity 9910.08 | - | - | - |
| 2026-11-17 | SYPR | FIXED5 | KOD | order 576 @ <= 1.53, reserved $885.69 | pending: next open (before 2026-11-18T14:30:00Z) | - | - |
| 2026-11-17 | GLSI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.93 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | AYTU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 49.06 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | KALA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.98 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | CVKD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 49.07 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | VAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 49.06 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | FRTT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 49.13 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | SLS | FIXED5 | KOD | order 45 @ <= 21.05, reserved $947.72 | filled 45 @ 19.5 on 2026-11-18, stop 18.53 | STOP 2026-11-18 @ 18.53 | -$46.24 |
| 2026-11-17 | SGRX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 147.23 + 49.08 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | TGL | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 147.23 + 48.97 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | AZI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 147.23 + 49.12 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | MPU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 147.23 + 49.04 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | DFSC | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 147.23 + 48.97 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-17 | GP | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 147.23 + 49.11 would exceed 1.5% of equity 9833.25 | - | - | - |
| 2026-11-18 | CUE | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.82 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | HIHO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | CLRO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.73 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | SKYA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.84 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | ANPA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | AZI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.88 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | MPU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | NUR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.90 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | ICU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.88 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | BTOC | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.91 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | SVRE | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.90 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-18 | AKAN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.90 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | ZKIN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.84 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | MRKR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.89 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | ELOG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | LVWR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.90 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | SEAT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.89 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | BAER | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | HTCR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | MPU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.82 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | RAYA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | POAS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.74 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-19 | VIVS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | LVWR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.89 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | BNAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.80 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | CIGL | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | NIXX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.83 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | MEDS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | MSS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.91 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | NXAT | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | RAYA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.91 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-20 | AMCI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.91 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | RSSS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 99.01 + 48.85 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | NVDA | FIXED5 | KOD | order 5 @ <= 181.54, reserved $908.15 | pending: next open (before 2026-11-24T14:30:00Z) | - | - |
| 2026-11-23 | CUE | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.71 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | BUUU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.76 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | KYMR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 42.20 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | GRRR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.74 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | SCWO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.89 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | PAAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.88 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | INTJ | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.85 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | FFR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.89 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | PRFX | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | OTLY | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.62 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | CELU | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | DCGO | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | PTHS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.88 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | DTSS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | MRM | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | BNAI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.80 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | XCH | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.76 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | ZSQR | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.85 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | AUUD | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.88 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | AEON | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | BYSI | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | RIME | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.91 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | LINK | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | IMCC | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.87 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | ALZN | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.90 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | SMTK | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.92 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | CYAB | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.87 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | SCAG | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.91 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | ITP | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.86 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | VIVS | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.90 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | TOPP | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | PARA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.93 would exceed 1.5% of equity 9787.01 | - | - | - |
| 2026-11-23 | LSTA | FIXED5 | KOD | declined: LIMIT_PLANNED_RISK: 145.29 + 48.31 would exceed 1.5% of equity 9787.01 | - | - | - |

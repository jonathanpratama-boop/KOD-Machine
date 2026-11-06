# KOD paper account (PAPER_ACCOUNT_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-06T23:02:01.348379Z; latest US scan session: 2026-11-06.
- Latest compatible LEARNER v2.4 forecast: 2026-11-06T22:57:08Z (signal session 2026-11-06).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

As of the latest record (2026-11-06T23:00:33Z). Paper only: no orders, no money. Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`.

## The three plain answers

- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real execution rules with one shared $10,000 account per arm: 0.5% planned loss per position, 1.5% for everything at once, at most 3 new orders per session, no leverage. An order fills only at the next opening print inside its limit; stops and the five-session time exit come from the bars.
- **How to read the money:** cash is what the account holds; reserved is cash set aside for orders waiting for the next open (not spent, not lost, just unavailable to another order); available = cash minus reserved. Equity = cash plus open positions at their latest recorded price. Realized P&L counts only closed trades.
- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the stop 5% below the fill. Same candidates, costs and exits. Each arm is a separate simulated account.

## Accounts

| Arm | Cash | Reserved | Available | Open value | Equity | Realized | Unrealized | Pending | Filled | Rejected | Cancelled | Declined | Closed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | $9,287.74 | $0.00 | $9,287.74 | $782.44 | $10,070.18 | $0.00 | $69.77 | 0 | 1 | 4 | 0 | 36 | 0 |
| FIXED5 | $9,153.09 | $0.00 | $9,153.09 | $782.44 | $9,935.53 | -$134.65 | $69.77 | 0 | 4 | 0 | 0 | 37 | 3 |

## Open positions and valuation

- BASE APP: $782.44, valued at the close of 2026-11-06 (+9.91% since entry)
- FIXED5 APP: $782.44, valued at the close of 2026-11-06 (+9.91% since entry)

## Drawdown (from recorded nightly marks only)

- BASE: 0.00% across 6 mark(s)
- FIXED5: -0.69% across 6 mark(s), trough at the close of 2026-11-06

## Every decision

| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |
|---|---|---|---|---|---|---|---:|
| 2026-10-30 | FMC | BASE | KOD | order 174 @ <= 5.42, reserved $944.49 | REJECTED_STOP_TOO_WIDE: open 6.11 is above the permitted entry 5.42: the stop at 5.15 would be 15.71% away, more than 5% | - | - |
| 2026-10-30 | ASUR | BASE | KOD | order 107 @ <= 8.89, reserved $952.66 | REJECTED_STOP_TOO_WIDE: open 9.98 is above the permitted entry 8.89: the stop at 8.45 would be 15.33% away, more than 5% | - | - |
| 2026-11-05 | APP | BASE | KOD | order 2 @ <= 356.71, reserved $713.78 | filled 2 @ 356 on 2026-11-06, stop 338.9 | - | - |
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
| 2026-10-30 | FMC | FIXED5 | KOD | order 138 @ <= 6.8, reserved $939.81 | filled 138 @ 6.11 on 2026-11-02, stop 5.81 | STOP 2026-11-06 @ 5.81 | -$43.89 |
| 2026-10-30 | ASUR | FIXED5 | KOD | order 92 @ <= 10.34, reserved $952.71 | filled 92 @ 9.98 on 2026-11-02, stop 9.49 | STOP 2026-11-02 @ 9.49 | -$47.79 |
| 2026-11-05 | APP | FIXED5 | KOD | order 2 @ <= 391.7, reserved $783.79 | filled 2 @ 356 on 2026-11-06, stop 338.2 | - | - |
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

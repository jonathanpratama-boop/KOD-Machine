# KOD paper account (PAPER_ACCOUNT_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-06T00:25:52.853594Z; latest US scan session: 2026-11-05.
- Latest compatible LEARNER v2.4 forecast: 2026-11-06T00:22:22Z (signal session 2026-11-05).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

As of the latest record (2026-11-06T00:25:09Z). Paper only: no orders, no money. Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`.

## The three plain answers

- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real execution rules with one shared $10,000 account per arm: 0.5% planned loss per position, 1.5% for everything at once, at most 3 new orders per session, no leverage. An order fills only at the next opening print inside its limit; stops and the five-session time exit come from the bars.
- **How to read the money:** cash is what the account holds; reserved is cash set aside for orders waiting for the next open (not spent, not lost, just unavailable to another order); available = cash minus reserved. Equity = cash plus open positions at their latest recorded price. Realized P&L counts only closed trades.
- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the stop 5% below the fill. Same candidates, costs and exits. Each arm is a separate simulated account.

## Accounts

| Arm | Cash | Reserved | Available | Open value | Equity | Realized | Unrealized | Pending | Filled | Rejected | Cancelled | Declined | Closed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | $10,000.00 | $2,480.33 | $7,519.67 | $0.00 | $10,000.00 | $0.00 | $0.00 | 3 | 0 | 2 | 0 | 10 | 0 |
| FIXED5 | $9,107.77 | $1,736.26 | $7,371.51 | $837.66 | $9,945.43 | -$47.79 | -$8.06 | 2 | 2 | 0 | 0 | 11 | 1 |

## Open positions and valuation

- FIXED5 FMC: $837.66, valued at the close of 2026-11-05 (-0.65% since entry)

## Drawdown (from recorded nightly marks only)

- BASE: 0.00% across 5 mark(s)
- FIXED5: -0.59% across 5 mark(s), trough at the close of 2026-11-05

## Every decision

| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |
|---|---|---|---|---|---|---|---:|
| 2026-10-30 | FMC | BASE | KOD | order 174 @ <= 5.42, reserved $944.49 | REJECTED_STOP_TOO_WIDE: open 6.11 is above the permitted entry 5.42: the stop at 5.15 would be 15.71% away, more than 5% | - | - |
| 2026-10-30 | ASUR | BASE | KOD | order 107 @ <= 8.89, reserved $952.66 | REJECTED_STOP_TOO_WIDE: open 9.98 is above the permitted entry 8.89: the stop at 8.45 would be 15.33% away, more than 5% | - | - |
| 2026-11-05 | APP | BASE | KOD | order 2 @ <= 356.71, reserved $713.78 | pending: next open (before 2026-11-06T14:30:00Z) | - | - |
| 2026-11-05 | VXX | BASE | KOD | order 51 @ <= 18.2, reserved $929.59 | pending: next open (before 2026-11-06T14:30:00Z) | - | - |
| 2026-11-05 | HTCR | BASE | KOD | order 694 @ <= 1.2, reserved $836.96 | pending: next open (before 2026-11-06T14:30:00Z) | - | - |
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
| 2026-10-30 | FMC | FIXED5 | KOD | order 138 @ <= 6.8, reserved $939.81 | filled 138 @ 6.11 on 2026-11-02, stop 5.81 | - | - |
| 2026-10-30 | ASUR | FIXED5 | KOD | order 92 @ <= 10.34, reserved $952.71 | filled 92 @ 9.98 on 2026-11-02, stop 9.49 | STOP 2026-11-02 @ 9.49 | -$47.79 |
| 2026-11-05 | APP | FIXED5 | KOD | order 2 @ <= 391.7, reserved $783.79 | pending: next open (before 2026-11-06T14:30:00Z) | - | - |
| 2026-11-05 | VXX | FIXED5 | KOD | order 39 @ <= 24.41, reserved $952.47 | pending: next open (before 2026-11-06T14:30:00Z) | - | - |
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

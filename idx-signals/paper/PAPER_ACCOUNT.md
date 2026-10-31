# KOD paper account (PAPER_ACCOUNT_v1)

As of the latest record (2026-10-31T10:36:42Z). Paper only: no orders, no money. Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`.

## The three plain answers

- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real execution rules with one shared $10,000 account per arm: 0.5% planned loss per position, 1.5% for everything at once, at most 3 new orders per session, no leverage. An order fills only at the next opening print inside its limit; stops and the five-session time exit come from the bars.
- **How to read the money:** cash is what the account holds; reserved is cash set aside for orders waiting for the next open (not spent, not lost, just unavailable to another order); available = cash minus reserved. Equity = cash plus open positions at their latest recorded price. Realized P&L counts only closed trades.
- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the stop 5% below the fill. Same candidates, costs and exits. Each arm is a separate simulated account.

## Accounts

| Arm | Cash | Reserved | Available | Open value | Equity | Realized | Unrealized | Pending | Filled | Rejected | Cancelled | Declined | Closed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | $10,000.00 | $1,897.15 | $8,102.85 | $0.00 | $10,000.00 | $0.00 | $0.00 | 2 | 0 | 0 | 0 | 0 | 0 |
| FIXED5 | $10,000.00 | $1,892.52 | $8,107.48 | $0.00 | $10,000.00 | $0.00 | $0.00 | 2 | 0 | 0 | 0 | 0 | 0 |

## Open positions and valuation

- No open positions.

## Drawdown (from recorded nightly marks only)

- BASE: 0.00% across 1 mark(s)
- FIXED5: 0.00% across 1 mark(s)

## Every decision

| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |
|---|---|---|---|---|---|---|---:|
| 2026-10-30 | FMC | BASE | KOD | order 174 @ <= 5.42, reserved $944.49 | pending: next open (before 2026-11-02T14:30:00Z) | - | - |
| 2026-10-30 | ASUR | BASE | KOD | order 107 @ <= 8.89, reserved $952.66 | pending: next open (before 2026-11-02T14:30:00Z) | - | - |
| 2026-10-30 | FMC | FIXED5 | KOD | order 138 @ <= 6.8, reserved $939.81 | pending: next open (before 2026-11-02T14:30:00Z) | - | - |
| 2026-10-30 | ASUR | FIXED5 | KOD | order 92 @ <= 10.34, reserved $952.71 | pending: next open (before 2026-11-02T14:30:00Z) | - | - |

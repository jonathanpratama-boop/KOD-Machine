# KOD paper account (PAPER_ACCOUNT_v1)

Generated 2026-10-31T10:36:47Z. Paper only: no orders, no money. Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`.

## The three plain answers

- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real execution rules with one shared $10,000 account: 0.5% planned loss per position, 1.5% for everything at once, at most 3 new orders per session, no leverage. An order fills only at the next opening print inside its limit; stops and the five-session time exit are applied as the bars come in.
- **What counts as working?** First, plumbing: every decision has a sealed plan and a reason, cash and positions reconcile, realized gains only after an exit, open losses in equity. Profit is judged later, on many closed trades, never on a few.
- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the stop 5% below the fill. Same candidates, costs and exits.

## Accounts

| Arm | Equity | Cash | Reserved | Open value | Realized | Unrealized | Max drawdown | Orders | Filled | Rejected | Declined |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | $10,000.00 | $10,000.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 2 | 0 | 0 | 0 |
| FIXED5 | $10,000.00 | $10,000.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 2 | 0 | 0 | 0 |

## Every decision

| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |
|---|---|---|---|---|---|---|---:|
| 2026-10-30 | FMC | BASE | KOD | order 174 @ <= 5.42 | pending (next open) | - | - |
| 2026-10-30 | ASUR | BASE | KOD | order 107 @ <= 8.89 | pending (next open) | - | - |
| 2026-10-30 | FMC | FIXED5 | KOD | order 138 @ <= 6.8 | pending (next open) | - | - |
| 2026-10-30 | ASUR | FIXED5 | KOD | order 92 @ <= 10.34 | pending (next open) | - | - |

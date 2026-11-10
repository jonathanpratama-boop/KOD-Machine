# KOD crypto spot paper account (CRYPTO_ACCOUNT_v1, rules v1.4)

As of the latest record (2026-11-10T00:33:45Z). Paper only: no orders, no money. Protocol: `research/CRYPTO_ACCOUNT_v1/protocol_v1_4.json` (supersedes v1.3; see CORRECTION_4.md).

- **Rules:** 10,000 USDT; 0.5% planned loss per position, 1.5% in total, 3 new orders per UTC day, no leverage; buys only what the frozen crypto policy decides to buy; limit 1% above the policy's quote, valid 1:00:00; fills at a recorded ask, exits at a recorded bid; stop 5% below the fill; time exit after 5 days; fee 0.10% per side.

| Cash | Reserved | Available | Open value | Equity | Realized | Unrealized |
|---:|---:|---:|---:|---:|---:|---:|
| 10,000.00 | 0.00 | 10,000.00 | 0.00 | 10,000.00 | 0.00 | 0.00 |

## Open positions

- None.

## Quote fetch failures

- None.

## Every decision

| Decided | Coin | Policy | Account | Fill | Exit | Net P&L |
|---|---|---|---|---|---|---:|
| 2026-10-31T12:26:34Z | BEAMXUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-10-31T12:26:34Z | SOPHUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-11-08T13:55:06Z | SOXSBUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-11-08T13:55:06Z | UVXYBUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-11-08T13:55:06Z | ONEUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-11-09T00:25:50Z | GNSUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-11-10T00:33:40Z | INITUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |
| 2026-11-10T00:33:40Z | SOXLBUSDT | PASS | declined: POLICY_PASS: detection is validated (E30 precision 18.5% vs 4.0% for matched names), but the executable plan (buy at the next day's open, ho | - | - | - |

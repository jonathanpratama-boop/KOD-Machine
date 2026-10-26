# LEAD_LADDER_v1 erratum 1 (2026-10-26): two passing cells are partly a pool artifact

The recorded verdict (LEAD_FOUND, 6 of 808 cells) and every file in `results/` stand as produced. Its gates compare
each lift with 1.0. The rehearsal (`rehearsal/lifts.csv`: random eligible names in place of the up episodes, same
sessions) shows that for some features the null lift is above 1, because the matched pools exclude names with a
same-kind move in u..t. Read against the placebo, the passing cells are:

| Cell | Recorded lift | Placebo lift | Ratio |
|---|---|---|---|
| IDX SLOW_UP age bottom, lead 10 (rule-selected) | 2.10 | 0.88 | 2.39 |
| IDX SLOW_UP age bottom, lead 3 | 2.01 | 0.93 | 2.16 |
| IDX SLOW_UP up5 bottom, lead 5 | 2.21 | 1.80 | 1.23 |
| CRYPTO FAST_UP ret20 bottom, lead 3 | 2.11 | 1.44 | 1.46 |
| US FAST_UP ret20 bottom, lead 3 (survivor-only) | 3.17 | 1.08 | 2.95 |

So IDX up5 is not distinguishable from its own null, and the crypto beaten-down cell is weaker than its lift says.
The IDX listing-age cell and the US cell survive the placebo comparison. The movement-only finding (volatility and
drawdown predict both directions) is unaffected in kind. LEAD_LADDER_INTL_v1 adds this placebo gate (its ADDENDUM_2).

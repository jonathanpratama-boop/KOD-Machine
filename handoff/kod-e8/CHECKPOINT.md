# E8 checkpoint (replaceable view; the record is the E8 branch history)

Updated: 2026-10-16, stage 2 of 5 done.

Branch `claude/e8-peer-spillover` (local; based on published E6 head fa142ff). Its commits are
carried in `bundles/e8-peer-spillover.bundle`; restore with
`git fetch handoff/kod-e8/bundles/e8-peer-spillover.bundle claude/e8-peer-spillover:claude/e8-peer-spillover`.

| Stage | State | Commit |
|---|---|---|
| 1. Mechanism comparison + declared feasibility rule | done | b1d1f6d |
| 2. Feasibility v1 (GO; link defect found from composition) and amendment 1, feasibility v1.1 (GO) | done | a409810, 1b19dfb, bfcf099 |
| 3. Freeze protocol (outcomes, controls, plan, costs, gates) | next | |
| 4. Outcome code + synthetic tests | pending | |
| 5. One discovery run, report including a null | pending | |

Inputs: `data/manifests/binance_1h-20261015T182940Z.jsonl` (Binance spot 1h, 2020-04..2022-12 read;
2023+ never opened). G3/Mac untouched; snapshot verified offline only (24/24 guard tests on copies).

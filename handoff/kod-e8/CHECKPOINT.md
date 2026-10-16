# E8 checkpoint (replaceable view; the record is the E8 branch history)

Updated: 2026-10-16. **Complete: E8 discovery FAIL at frozen gates. E8 stops; nothing retuned.**

Branch `claude/e8-peer-spillover` (local, not pushed; based on published E6 head fa142ff). Its commits
are carried in `bundles/e8-peer-spillover.bundle`; restore with
`git fetch handoff/kod-e8/bundles/e8-peer-spillover.bundle claude/e8-peer-spillover:claude/e8-peer-spillover`.

| Stage | State | Commit |
|---|---|---|
| 1. Mechanism comparison + declared feasibility rule | done | b1d1f6d |
| 2. Feasibility v1 (GO; low-beta link defect found from composition), amendment 1, feasibility v1.1 (GO) | done | a409810, 1b19dfb, bfcf099 |
| 3. Protocol KOD-CRYPTO-E8-v1 frozen | done | 8ec2265 |
| 4. Outcome code + synthetic tests (253 repository tests pass) | done | f23e1f5 |
| 5. One discovery run: FAIL; independent raw-file check 25/25; rerun identical | done | 6c8fd1c |

Result (`idx-signals/research/E8/RESULT.md`): 1,206 warnings; 72h excess +0.44% (95% -0.28% to +1.16%,
p 0.114); U20 17.8% vs 15.9% (p 0.066); plan mean net +0.09% (p 0.436), win rate 41.1%, 2022 negative,
max drawdown -38.9% at 5% per trade.

Inputs: `data/manifests/binance_1h-20261015T182940Z.jsonl` (2020-04..2022-12 read; 2023+ never opened).
G3/Mac untouched; the handoff snapshot was verified offline only (232 hashes, 24/24 guard tests on copies).

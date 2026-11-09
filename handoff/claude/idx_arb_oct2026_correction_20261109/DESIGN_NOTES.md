# Design notes: what the plan was, what review changed, what was rejected

This is the short version for the architect. The first plan was reviewed by an independent critic before any code was written. Four blockers changed it.

## The four blockers and what was done

| # | Finding | Resolution |
|---|---|---|
| 1 | The first plan raised an error from `limits()` for any date after 2026-12-31. Reproduced: it would crash the crypto routine first (UTC day 2027-01-01), then US and IDX on Monday 2027-01-04, because `Market.build` calls `limits()` for every market and throws the result away when `price_limits=False`. A raise also stops the scan, which cannot be back-filled. The fix would have needed an edit to `execution.py`, which frozen records pin. | `limits()` never raises. After 2026-12-31 it carries the last confirmed rule forward, emits `RulesUnconfirmedWarning`, and the period is its own regime labelled `UNCONFIRMED`. The announced symmetric 2027 rule is gone from the executable schedule. Fail-closed is left as an option (see below). |
| 2 | The research spec said that on 2026-10-19 a reference of Rp11-14 has ARB = reference (no downside). Two real bars contradict it: BTEK and TAXI (previous close 12, open 8, close 9). Tests written from that spec would have codified it. | The spec was corrected (v2): nothing is asserted for that cell. The code keeps the plain 7% formula for that one day and documents it as unresolved. No scored record has such a bar on its path. |
| 3 | The plan said "minimal change in `market.py`" but the trace also recommended editing `execution.py` and the hashed text in `paper.py`. Both are byte-pinned by frozen records (`handoff/claude/LINT_CLEANUP_20261104.md`). | The PR touches `market.py`, the README and tests, nothing else. `market.py` itself is pinned by three completed MSCI protocols; that edit is the defect and needs the architect's waiver (see the PR). |
| 4 | Tests written "from the spec only" cannot cover a guard or the Market-level behaviour, because the spec has no interface, and the scratch directory held a working implementation. | A third party wrote an interface contract (`spec_pack/CONTRACT.md`). Two test authors worked in isolated workspaces holding only the unmodified code, the corrected spec and the contract. Their tests cover four layers: `limits()`, `Market.build`, `execute()` and `paper.score()`. |

Smaller findings that were folded in: the ledger replay is possible after all (the frozen 2026-11-06 pull survives), so the impact report replays every record, with a pre-declared list of three known differences; the report compares replay with replay, never replay with the recorded value; the affected set is every record whose path touches 2026-10-19 or later, not only decisions with a signal on or after that date; the 7% versus 10% bound and a board hint are reported because board membership is unknown.

## Evidence that the tests do not depend on one implementation

- A second implementation was written blind from the contract by a different agent. Both implementations pass all 167 tests. They agree on 9,210 random (reference, date) pairs including NaN, infinity, zero, negative and non-integer references, on 480 two-dimensional regime-edge cells, and on 5,747 pre-2026-10-19 pairs that must equal the unmodified module.
- Both test authors built independent exact-rational oracles from the spec. The oracle and the unmodified code agree for every valid reference from Rp1 to Rp600,000 under the 15% rule, which validates the oracle itself.
- On the unmodified code 27 of 82 and 32 of 85 new tests fail, each for the intended reason.

## Options left for the architect

1. **Fail-closed after 2026-12-31 instead of carry-forward.** It needs a waiver for `execution.py` (so that only the IDX lower-limit consumers raise, never the scan and never `price_limits=False`), an alert, and a runbook, in the same change. Not done here because the unconfirmed period may last months.
2. **A rules-epoch marker in OUTCOME rows.** None exists, and adding one touches pinned `paper.py`. The cut-over is provable from the merge commit and the first nightly run after it. Record both.
3. **A drift canary.** Since 2026-10-19 no close was more than 10% below the modelled 7% limit, except 2026-10-19 Rp11-14 bars. A nightly count of closes below that threshold would show a reversion to 15% or 35% at once. Not built (it is new functionality).
4. **Scorer change** so that a locked horizon bar rolls instead of leaving no outcome. Needs `paper.py`, a waiver and a scorer version bump.
5. **Open the decree.** The in-force Rule II-A PDF is listed in the IDX register at `https://www.idx.co.id/Media/stumk2gi/signed_peraturan_nomor_ii_a_tentang_perdagangan_efek_bersifat_ekuitas-261020.pdf`. The owner can open it in a browser. It would settle the rounding wording, the Rp11-14 reading, the board scope and any 2027 clause.

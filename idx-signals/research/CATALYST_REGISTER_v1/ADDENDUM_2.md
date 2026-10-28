# Addendum 2 (2026-10-28, before the first SEC13D set): a win-rate primary and pre-declared extended looks

The owner's instruction: "merge PR #16 and do 1, 2, 3, 4, 5" (decision record `handoff/decisions/2026-10-28c_proof_program.md`).
Items 1 and 2 are frozen in `prereg_2.json` in this folder. `protocol.json` is unchanged, because its sha256 is bound into
the sealed IDX_INDEX sets. Every SEC13D set sealed from now carries `prereg_2.json`'s sha256 under `preregistration`,
and `paper-verify` refuses a set whose recorded hash differs. No SEC13D set and no SEC13D outcome existed when it was
frozen; the first SEC13D outcome cannot exist before 2026-11-27 (20 sessions after the first entry).

**Why.** Statistical power. One sealed set's paired difference has a spread near 21% (US_INSIDER_BUY's 20-session
returns, paired against five twins). At the project's t >= 3, the smallest provable effects are:

| Sets | Smallest provable mean edge | Smallest provable win rate vs twins |
|---|---|---|
| 60 | 8.5% (10.7% at the first look's 3.75) | 69% |
| 240 | 4.3% | 60% |
| 960 | 2.1% | 55% |
| 1,920 | 1.5% | 53% |

The literature's 13D drift is 1-3% per event. As frozen, the protocol would have ended at 240 sets, and a real 2% edge
would have read "not proven".

**What changes for SEC13D.**
1. **A second primary, WIN_RATE.** Per FIRE set, a win is the plan's net above the twins' median net (the existing cone
   statement `BEATS_TWINS_20`). The test is the per-session share of wins, a one-sided t against 0.5. It is eligible only
   if the plan's mean net after costs is also above zero, so a high win rate with a losing average never passes. The
   exact binomial p is reported beside it, descriptively.
2. **Looks continue past 240.** The looks are 60, 120, 240 (unchanged, t at least 3.75, 3.0, 3.0), then 480, 960 and
   1,920 (t at least 3.0, from at least 30, 60 and 120 sessions). From the 240 look on, a primary whose estimate is at or
   below zero stops with FAIL (futility). A primary not eligible at 1,920 fails.
3. **Error control.** Each primary has at most six looks at t >= 3.0 or stricter, so a null primary is eligible with
   probability at most 0.81% (Bonferroni over the looks), and the family at most 1.62%. Every look of each primary is a
   counted trial file, so the register's Holm adjustment counts all of them.

**Test numbers** follow the order in which counted trial files are added. The protocol's line "the first is the project's
test 31" holds only if no other counted test lands first. The 13D kill test of item 4 (`KILL_TEST_2020_2022/`) runs
before the first look and takes the next number.

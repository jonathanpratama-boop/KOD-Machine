# Decision 2026-10-28c (owner): merge the Catalyst Register and run the five-point proof program

The session proposed five ways to get from "built" to "proven" (sample size, not bugs, is the limit). The owner answered:
"merge PR #16 and do 1, 2, 3, 4, 5".

0. **PR #16 merged** into the main branch (merge commit `036e6dd`, CI green on `04f027a`). From now on, the registers
   run from the main branch.
1. **Win-rate primary** for SEC13D, pre-registered before any SEC13D set: `research/CATALYST_REGISTER_v1/prereg_2.json`,
   `ADDENDUM_2.md`.
2. **Extended looks** 480, 960 and 1,920, with a futility stop from the 240 look, pre-declared in the same file.
3. **More families in parallel**, each with its own frozen protocol and its own counted looks: DILUTION_8K (8-K Item
   3.02, the avoid side: does the issuer underperform its twins?) and FORM4 (a prospective replication of
   US_INSIDER_BUY's frozen event definition). Shorting is still not run; the dilution family measures underperformance
   only, because borrow costs are not free data.
4. **One-shot 13D kill test** on 2020-2022, with survivor-only prices, so it can fail the family but cannot confirm it.
   This overrides, for this one test only, the protocol's "no backtest of any family". It is frozen in
   `research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022/` before any data is read, run once, and counted.
5. **Routines run the registers** without the session: the three scheduled routine prompts gain the speculate, catalyst
   and report steps. The SEC contact comes only from the environment setting or the session's declared contact, and is
   never written to a file.

Not changed: PAPER-POLICY-v4, `ledger.jsonl` and every earlier record, and every frozen protocol file.

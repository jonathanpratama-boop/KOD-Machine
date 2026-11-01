# Disclosure 2026-11-01: MOVERS_NOW_v1 computed outcomes inside sealed holdout windows (found by a scoping agent; verified)

Found on 2026-11-01 by a read-only scoping agent while it checked prior KOD exposure of the IDX archive fields. I
verified it directly in the repo. Nothing was changed in MOVERS_NOW_v1; this note only records the exposure.

## What was verified

- `idx-signals/research/MOVERS_NOW_v1/` was written and run on 2026-10-27 (commits 6bbc609 and 30eea9e).
- Its exploration "learn window" is **2025-01-02 .. 2026-03-31** (PROTOCOL.md line 5; `study.py` line 17:
  `t = t[t.date >= "2025-01-02"]`). For every tradable name-day it labels whether the close rose 30% or more, or fell
  23% or more, within the next 20 sessions. Features load from 2024-06-01 (`mv_lib.load`).
- **IDX.** The sealed IDX holdout is 2024-01-02 .. 2025-02-21 (BLUEPRINT "Sealed holdouts"). MOVERS_NOW_v1 computed
  forward outcomes for IDX name-days from 2025-01-02 through 2025-02-21. Its features also read rows from 2024-06-01.
  Its protocol does not mention the holdout. The rule results it reports (R1 momentum, R2 dilution news) used this
  window.
- **US and crypto.** BLUEPRINT puts the US/crypto holdout at 2024-01-01 .. 2026-12-31. MOVERS_NOW_v1's US and crypto
  learn window (2025-01-02 .. 2026-03-31) and its check window (2026-04-01 .. 2026-09-08) lie inside it. I found no
  owner decision authorising that use. The crypto holdout was already largely spent with owner permission
  (ADMISSION_HOLDOUT_v1, CRYPTO_TUNE_v1). For US I found no record either way.

## Consequences (stated now so later studies label their windows correctly)

1. The IDX holdout's last seven weeks (2025-01-02 .. 2025-02-21) have had forward 20-session outcomes computed. They are
   no longer clean for questions about large moves, momentum or dilution news. The 2024 part, including the four 2024
   MSCI reviews, was not touched by MOVERS_NOW_v1.
2. The US/crypto 2025-2026 period has been used for exploration by MOVERS_NOW_v1 (30% movers, momentum). Any future US or
   crypto study must treat 2025-01 .. 2026-09 as inspected for those questions.
3. Corrected record: decision `2026-11-01b` said the IDX archive's foreign-flow, closing-queue and negotiated fields were
   "never used as signals" and that "2019-07 .. 2023-12 is clean development data". Both are wrong.
   - Counted test 30 (`research/FLOW_IDX_v1`, 2026-10-26, verdict NO_FLOW_LEAD) used foreign buy/sell, bid/offer queue
     volumes and negotiated value on 2021-01-22 .. 2022-12-30.
   - Its rehearsal also computed 2023 lifts against real -30% falls.
   - Its pre-registered consequence was "stop this line", and `handoff/precatalyst-program/PROGRAM_v1.md` marks the
     "Tape" family Closed.
   - Decision `2026-10-26b`'s "no test has used them" was true when written, earlier the same day.

## For the owner

- Whether to treat MOVERS_NOW_v1's US/crypto use as sanctioned (exploration on a holdout already partly spent) or as a
  breach like `2026-10-31_holdout_breach_by_research_agent.md`.
- Re-opening the Tape family (foreign flow and related fields) needs your explicit decision. It was closed by test 30's
  pre-registered consequence.

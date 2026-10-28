# KOD-CATALYST-REGISTER-v1

Frozen 2026-10-28, before the first set was sealed. The machine-readable copy is `protocol.json` in this folder; every
sealed record carries its sha256, and `paper-verify` refuses a set whose protocol hash differs. Paper only: no order, no
change to `PAPER-POLICY-v4`, `paper/ledger.jsonl` or `paper/speculations.jsonl`, no new scheduled task.

**Why.** Thirty counted tests found no daily-tape feature that tells the direction of a move before it starts; the leads
that passed anything were events with an actor (`handoff/precatalyst-program/PROGRAM_v1.md`, sections 1 and 2). A high win
rate is a property of which events the machine agrees to speak on and when it abstains. This register measures that
prospectively, for event families whose direction is set by their mechanism, with the Speculation Register's machinery
(`idxsig/speculation.py`: sealing before the entry, matched twins, the frozen plan simulation, unit reconciliation,
per-session paired t). The owner approved it on 2026-10-28: "okay yeah just do all four i guess"
(`handoff/decisions/2026-10-28b_precatalyst_four_calls.md`).

## Records (`paper/catalysts.jsonl`, hash chain, RFC 3161 stamps, pushed)

| Record | When | What |
|---|---|---|
| `BATCH` | each read of a family's source | every new event seen with its status (`SEALED` or a `SKIP_*` reason), the source pages' and the ticker map's sha256, the feed's time span and a coverage-gap flag. A missed filing is a recorded gap, never backfilled. |
| `CATALYST_SET` | per event, before its entry cutoff | the event, the signal features (from the paper scan's frozen features file), the coverage class with every rule's input, the cone with its priors, the windows, the twins and every twin candidate checked |
| `TAG` | per new US or IDX Speculation Register set, before that set's cutoff | `DILUTION_RECENT` (true, false, or null when the source could not be read), with the evidence, bound to the set's record hash |
| `RESOLUTION` | per (set, window) once the bars cover it | the plan's trade for the name and each twin, the paired difference, every statement graded with its Brier term |

## SEC13D (counted)

- **Event**: an original Schedule 13D (`SCHEDULE 13D`, not `/A`, not 13G) accepted on or after 2026-10-28 00:00 New York,
  read from EDGAR's current-filings feed (entry `<updated>` = acceptance time).
- **Issuer**: a ticker of the subject CIK (SEC `company_tickers_exchange.json`) that is fresh and eligible in the US paper
  scan of the signal session; an operating issuer (a 10-K, 10-Q, 20-F or 40-F in the last 550 days and no fund report);
  no other original 13D on it in the previous 90 days. Otherwise `SKIP_NO_TICKER`, `SKIP_NOT_IN_UNIVERSE`,
  `SKIP_NOT_OPERATING` or `SKIP_REPEAT_90D`.
- **Timing**: entry at the open of the first NYSE session whose 09:15 New York is after sealing (weekdays without the
  2026-2027 NYSE holidays, copied from exchange_calendars XNYS into `catalysts.NYSE_HOLIDAYS`); the signal session is the
  NYSE session before; the set must be sealed before 09:15 New York of the entry session. A filing accepted at or before
  the close of the session before the signal session is `SKIP_LATE` (the register missed it). Every batch is recorded,
  also an empty one, so a coverage gap (the feed no longer reaching back to the previous batch) is always visible.
- **Plan `H20`**: buy the entry session's opening print, sell the close 20 sessions later; US fees and cost tiers as the
  Speculation Register; no stop. A yardstick, not a strategy.
- **Coverage**: `FIRE`, or `ABSTAIN` if any of `DILUTION_RECENT` (an `is_dilution` filing from the 19th weekday before the
  signal session to the sealing date: 424B, S-1, S-3, F-1, F-3 families, EFFECT, 8-K Item 3.02), `MOVED_ALREADY` (signal
  close at least 1.15 x the last close before acceptance), `MICROCAP` (latest `dei:EntityCommonStockSharesOutstanding` x
  signal close below USD 50 million; no fact = `MV_UNKNOWN`, which also abstains). All three are recorded for every set.
- **Twins**: `speculation.draw_twins` on the same features (band, liquidity, momentum, drawdown; excluding the batch's event
  names and the scan's candidates), taken in seeded order, keeping the first 5 operating issuers with no original 13D in the
  last 90 days (at most 15 checked).
- **Cone**: `GAIN0_20` (prior 0.55, declared and weak, from Brav, Jiang, Partnoy & Thomas 2008), `BEATS_TWINS_20` (0.5),
  `FADE10_20` and `RUN30_20` (the register's running base rate, 0.5 until 20 are graded). Item 4's intent words are a
  descriptive tag, never graded.
- **Decision rule**: on FIRE sets, one-sided t on per-session mean paired differences (plan net minus the twins' mean
  net), looks at 60, 120 and 240 pairs from at least 15 sessions; eligible at a look if t is at least 3.75, 3.0 and 3.0
  respectively (Lan-DeMets O'Brien-Fleming-type spending 3.750, 2.538, 1.645 with the project's floor of 3.0), p < 0.05
  and the plan's mean net after costs is above zero. Confirmed if eligible at the next look too; FAIL if not eligible at
  240. Each look adds a counted trial file `research/QUANT_GRADE/trials/CATALYST_REGISTER_v1_SEC13D_FIRE_n<look>.json`; the
  first is the project's test 31. ABSTAIN sets are scored the same way and reported beside it, descriptively: they grade
  the abstention rule.

## IDX_INDEX (descriptive, not counted)

A review's changes (IDX30, LQ45, IDX80) go into `events/IDX_INDEX_<effective>.json` before its first set, each with its
sources and a confidence (`CONFIRMED`: two independent sources, or one whose list the index's fixed size forces;
`SINGLE_SOURCE`). idx.co.id answers HTTP 403 to this container, so the sources are news articles or the owner's copy of the
announcement. Direction +1 for a name only added, -1 for a name only removed; a name both added and removed is not sealed.
`RUNUP`: buy the closing auction of the session after the signal session, sell the close of the last session before the
effective date (the funds' rebalancing close). `POST20`: buy that close, hold 20 sessions. Twins by `draw_twins` on the IDX
scan's features, excluding every name of the review. Statements `WITH_FLOW_RUNUP` and `REVERSAL_POST20` (0.5 each).
Reported, never tested.

## DILUTION_RECENT tags

For US Speculation Register sets: the SEC13D dilution rule on the set's ticker and signal session. For IDX sets: an
EmitenNews headline about new shares (`sensors.dilution_kinds`) naming the ticker, posted in the last 28 days. Crypto: not
applicable. Metadata only; the Speculation Register's frozen protocol and its sets are unchanged.

## Forbidden

A backtest of any family; reading a sealed holdout; changing any rule, prior, window, abstention rule or look after the
first SEC13D set (a change is a v2 protocol with its own trial files); backfilling a missed filing; any order; any change to
`PAPER-POLICY-v4`, `ledger.jsonl` or `speculations.jsonl`; any new scheduled task.

## Changes from the draft in `handoff/precatalyst-program/PROGRAM_v1.md` (made before the first seal)

1. The paired difference is the plan's net minus the twins' **mean** net, as in the Speculation Register; the median is
   graded in `BEATS_TWINS_20`.
2. `MOVED_ALREADY` compares the signal close with the last close before acceptance: the entry open is not known at sealing.
3. The draft's falsifier statement on Item 4 became a descriptive tag: Item 4 commonly lists every purpose the filer may
   pursue, so a keyword match cannot be graded as true or false.
4. Subjects and twins must be operating issuers. Found in the one pre-freeze dry run: before freezing, the batch code was
   run once against the real filings of 26 and 27 October with a test-only window start, to check the parsing end to end.
   Nothing was appended and no price after those filings was read. It drew a closed-end fund (GCV) as a twin because the
   fund had filed a 10-Q in 1995, hence the 550-day and fund-report rule.
5. The universe is the US paper scan's fresh and eligible names, in place of the draft's price and liquidity filters; a
   filing seen too late is `SKIP_LATE`; sessions follow the NYSE holiday list; the look boundaries are 3.75, 3.0 and 3.0.

## Operating it

The three paper routines are unchanged. Until the owner adds these steps to the routine prompts (or merges this branch),
the session runs them from this branch's worktree when the routines fire: after the US scan, `catalyst-seal --family
SEC13D`; after each `speculate`, `catalyst-tag`; after each `paper-score`, `catalyst-score`. EDGAR requests carry the
declared contact inline (`KOD_SEC_CONTACT`), never written to a file.

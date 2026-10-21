# IDX insider-purchase news (IDX_INSIDER_NEWS): protocol

Written 2026-10-21, after the labelling audit (`audit/AUDIT.json`) and a counts-only feasibility (`feasibility/FEASIBILITY.json`),
and committed before any price, return or control value of these events is read. Historical research only: never prospective
performance; no orders; the frozen paper cycle is untouched. The IDX holdout (2024-01-02 .. 2025-02-21) is never loaded.

## The question, in three stages
1. **Will the stock move?** Not scored. A report that insiders bought is public news, not a forecast.
2. **Can we capture it?** After an obtainable entry (the close on the publication day if the article was posted by 14:30 WIB on a
   session day, otherwise the next session's close), after IDX fees, lot sizes, auto-rejection locks and a decision-time capacity cap,
   is there return left that matched random entries did not earn? This is the stage every earlier stock test of this project failed.
3. **Can the account carry it?** Not tested here (a single-position notional of IDR 10 million per trade, as in every IDX run).

## Events (fixed before any price is read)
`events.csv` (sha256 `bb28119fa7653da8baf3523157fd9378ef9c8f7a40b61fef1822958fd301c9dd`), built by `build_events.py` from the audited
labels (`labels.csv`; procedure in `LABELING.md` and `INSTRUCTIONS.md`, committed before labelling):
- Candidates: of 38,707 EmitenNews headlines of 2021-2023 (`sitemap_index.csv.gz`), those whose slug has a purchase-like word and an IDX
  ticker code were fetched (`articles.csv.gz`: 2,112, of which 52 pages failed and were not labelled); 2,060 were labelled by model
  sessions that saw the title, the posting time and the first 700 characters of the body, and nothing about prices.
- Event = labelled `INSIDER_BUY` (a director, commissioner or controlling shareholder, or a person or company the article presents as
  belonging to or controlled by them, bought shares of the listed company named in the headline) with confidence high or medium,
  an issuer ticker, and posted 2021-02-15 .. 2023-11-30 (WIB). **689 events on 229 tickers** (2021: 91, 2022: 285, 2023: 313) out of
  742 `INSIDER_BUY` labels.
- Audit (two blind reviewers, 45 `INSIDER_BUY` items and 45 others drawn with seed 20261022): precision 97.8% for both reviewers
  (44 of 45, the same item wrong in both; GO needed 85%); 0 of the 45 other items called `INSIDER_BUY` by either reviewer; kappa
  with the labeller 0.94 and 0.95, between the reviewers 0.98.
- The article's posting time is the time the news site published, not the time the filing reached IDX and not the time of the
  transaction (articles usually say the purchase was a day to a week earlier).

## Trade (the harness, unchanged: `idxsig.execution`, via `idxsig.idx_events`)
- The harness's signal session s is the posting day's previous session if posted by 14:30 on a session day, else the posting day's
  session (or the last session before a non-session day); entry at the **close of s + 1**; exit at the close of the 20th session after
  entry (primary hold 20; 5 and 60 reported). A name that cannot be bought (no trade, locked at the upper limit, fewer shares than
  one lot, more than 10% of the median volume of the 20 sessions up to and including the signal session, or a share-unit change the registry
  cannot verify) is skipped and counted; an event while the same name is still held is skipped (`SKIP_OVERLAP`). An event whose exit would fall
  after 2023-12-29 is `INCOMPLETE` and not scored (decided by dates only).
- Notional IDR 10 million per trade; fees 0.15% buy and 0.25% sell; verified corporate actions scale the shares, unverified resets and
  rights issues are not scored (`ca_mode="registry"`, fill model C, `data_end_exit="last_close"`).
- Data: the IDX panel `panel-20261007T225823Z` (sha256 `9d3a0718c95f9e885c4f8310cf68bf5e75021c366c454f73389d7fae75c02877`) and its
  corporate-action registry `ca_registry-20261007T230210Z` (sha256 `659da375e4586deab958e22dc242d7be6966ebc226bfefe8ce7ce85eb51f1e6c`),
  the pair the E1 study ran on (the later 10-13 rebuild is not in this checkout); window 2021-01-22 .. 2023-12-29 (TIER_1: exchange data,
  survivorship-complete). The panel is cut at the window end before it is loaded into the market.
- Feasibility (counts only; no return, price or control value was printed or saved): all 689 events map to the panel; at hold 20 the
  statuses are EXITED 370, SKIP_OVERLAP 188, SKIP_LIQUIDITY 100, SKIP_CAPACITY_UNKNOWN 15, SKIP_ARA_LOCK 8, SKIP_NOT_TRADED 7,
  INCOMPLETE 1. The feasibility file counts 322 "scored with a control" because it used 5 control draws, which leaves some events
  without a scored draw; with the 200 draws used here a counts-only check found at least one scored control for every EXITED event
  (one of them with fewer than 20), so about 370 events are expected to be scored. The GO rule (at least 100 scored events) is met either way.

## Controls
For each event, 200 replacement draws of names that could have been bought the same session, in the same price band, liquidity,
market-cap, volatility, momentum, drawdown and listing-age buckets as the signalled name (`controls.py`, v2; relaxed from the last
feature when fewer than 10 names match), each executed with the same plan. Excess = the event's net return minus the mean net return of
its scored draws. Seed 20261007.

## Statistics
Cluster = the posting date. 10,000 bootstrap resamples of dates (seed 20261024 plus the position of the hold in (5, 20, 60), so
hold 20 uses 20261025); t = mean over the bootstrap standard error. Winsorised means clip at the 1st and 99th percentiles.

## Gates (PASS only if all four hold; hold 20)
- **G1** mean excess over matched controls > 0 with bootstrap t >= 3.0 (the project hurdle; this is counted test 23 in
  `research/QUANT_GRADE/trials`).
- **G2** mean net > 0 and the winsorised mean net > 0.
- **G3** mean excess > 0 in each calendar year that has at least 20 scored events.
- **G4** mean net > 0 after an extra 0.5% per side (1% round trip).

## Reported whatever the verdict (descriptive; 3 variants counted in the register)
Holds 5, 20 and 60: scored events, hit rate, mean and median net, mean excess, t. Status counts for every mapped event (how many
could be bought). Results by year. Mean control return.

## Single run, frozen inputs, independent check
`run_frozen.py` sets the three sha256 values above as the expected inputs of `run_v2.py` and calls it; `run_v2.py` refuses to run
twice. `verify_v2.py` then recomputes, with its own code and the panel file, the signal sessions, the entry and exit closes, every
scored trade's net return, the statistics and the gates (the matched-control means come from the harness, whose controls are
tested separately). `run.py` and `verify.py`, committed earlier, pinned a panel that is not in this checkout and were never run.

## How the result will be read (fixed now)
- **PASS**: purchases by insiders reported in the news left return after an obtainable close, fees and locks. Next step: a forward
  paper watch of the news feed with the same rule, and the official IDX disclosure feed (blocked from the cloud) to move the clock
  earlier; nothing real.
- **FAIL with mean excess > 0 and t < 3**: a lean without the power to say; recorded as such, no follow-up without new data.
- **FAIL otherwise**: by the time a news site reports an insider purchase and a buyer can act at a close, the matched stock has
  earned the same; this tests the news clock, not the official filing's clock.
No rerun after the result: any change is a new experiment with its own protocol.

## Limits (stated before the result)
- News time is later than filing time and filing time is later than the transaction; a null here does not test the filing's own
  reaction, and a positive here could be partly the transaction's own drift before the article.
- EmitenNews chooses what to write about. The labeller is a model; its precision is audited by two other model sessions, which share
  its family of errors. Recall is not measured beyond the 45 sampled "other" items (none was an insider purchase).
- 2021-2023 only, one source, about 370 events after liquidity, lock and overlap skips (of 689); IDX moves in lots and has daily price
  limits. Exits that fall after 2023-12-29 are not scored, so late-2023 events are under-represented at holds 20 and 60.
- 2021-2022 and 2023 are periods the earlier IDX detector studies also used (discovery and validation); no detector, parameter or
  event is shared with this test.
- Excess is measured against random entries of the same session and buckets; it is not a test of insider-purchase news against other
  news, and it does not adjust for dividends (price returns).

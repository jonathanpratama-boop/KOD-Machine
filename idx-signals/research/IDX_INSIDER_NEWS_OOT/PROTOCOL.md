# IDX insider-purchase news, out of time (IDX_INSIDER_NEWS_OOT): protocol

Written 2026-10-21 and committed before any 2025-2026 headline, article, price or return of this study is fetched or read. It is
historical research (the events happened before the run), never prospective performance; no orders; the frozen paper cycle is untouched.
The sealed IDX holdout (2024-01-02 .. 2025-02-21) and the sealed crypto holdout stay sealed.

## Why this test
`research/IDX_INSIDER_NEWS` (counted test 23, corrected run in `results_corrected/`) passed its four gates narrowly: +2.81% mean excess
per trade over matched random entries at a 20-session hold (t 3.07, 370 events, 2021-2023). Its excess is heavy-tailed (the top 5 events
give 45% of it), it shrank every year (+5.6%, +3.2%, +1.6%), its first run failed at t 2.78, and it does not clear the register's
all-variants bar. The test that decides whether it is real needs data nobody has looked at. The panel holds such a segment: **2025-02-24 ..
2026-10-06** (382 sessions, Yahoo daily bars, quality tier TIER_3). No hypothesis study in this repository has been run on it (the
studies' windows end on 2025-02-21 or earlier; the frozen paper cycle began in October 2026). This protocol replicates test 23 on it
with nothing re-tuned.

## The question, in three stages (unchanged)
1. Will the stock move? Not scored. 2. Can we capture it? After an obtainable close, fees, lots, auto-rejection locks and a capacity cap,
is there return left that matched random entries did not earn? 3. Can the account carry it? Not tested (IDR 10 million per trade).

## What is fixed (copied from test 23; nothing is re-tuned)
- **Events.** EmitenNews articles the model labeller calls `INSIDER_BUY` (a director, commissioner or controlling shareholder, or a person
  or company presented as belonging to them, bought shares of the listed company named in the headline) with confidence high or medium
  and an issuer ticker. Candidate rule, labeller and reviewer instructions
  (`research/IDX_INSIDER_NEWS/INSTRUCTIONS.md`, sha256 `179a4516079b2389b8ba25c45ac72f2f84667aec749a35a418e054f129a9aa9e`) and audit procedure
  (`research/IDX_INSIDER_NEWS/LABELING.md`, sha256 `ef4af98afb0302de9d833150923dbeda2c7898a653c3a9ae96b0f047fca67ec9`: 45 labelled-insider and 45 other items drawn with seed 20261022, two
  blind reviewers, GO only if the lower reviewer's precision is at least 85%) are the ones of test 23. LABELING.md's second GO condition
  (150 labelled events) is replaced by the scored-events GO below.
- **Trade.** The harness, unchanged (`idxsig.idx_events` over `idxsig.execution`, configuration `config()` of
  `research/IDX_INSIDER_NEWS/run_v2.py`): signal session s = the posting day's previous session if posted by 14:30 WIB on a session day, else
  that day's session (or the last session before a non-session day); entry at the close of s + 1; exit at the close of the 20th session after
  entry (primary hold 20; 5 and 60 reported); IDR 10 million per trade; fees 0.15% buy and 0.25% sell; whole 100-share lots; auto-rejection
  locks; shares at most 10% of the median volume of the 20 sessions up to the signal session (fill model C); an event while the same name is
  still held is skipped; an event whose exit falls after the panel ends is not scored; `ca_mode="registry"`.
- **Controls.** For each event 200 replacement draws of names that could have been bought the same session, matched on the harness's
  buckets (`controls.py` v2, relaxed from the last feature when fewer than 10 names match), each executed with the same plan; the control of
  an event is the mean net return of its scored draws; excess = net return - control. Seed 20261007.
- **Statistics.** Cluster = the posting date; 10,000 bootstrap resamples of dates (seed 20261024 plus the position of the hold in (5, 20, 60));
  t = mean over the bootstrap standard error; winsorised means clip at the 1st and 99th percentiles.
- **Code.** `idxsig/idx_events.py` sha256 `18498f1a31219fd2b954537d989d33851f990a856b7bacadddbdd01fd9197111`, `idxsig/execution.py` `8949da97745896cb9ccf305d3e4e76cec9b41ee1e05aad2729ac3b228ea9bb98`, `idxsig/controls.py` `5e3e8e7a1a26df43801b0b859d298f3f646bf01e09946130b625763f27d8d361`,
  `idxsig/market.py` `b956576fec19dbac3164bd8181e63f6b579d138aa42016d11af35103832c6d9f`, `run_v2.py` `dfb52523426dcb2cad740749c4bdae8ad8c8905979fe4c3cf94e9174b3ccfbdd`; the run refuses to start if any of them differs.

## What is different (forced by the data, not chosen)
1. **Window.** Articles posted **2025-03-03 .. 2026-09-07** (WIB). The first date is five sessions after the last holdout session (2025-02-21),
   the embargo E1 used at its boundaries; the last date is the date of the 22nd-last session of the panel, so that every event can complete
   a 20-session hold before the panel ends on 2026-10-06. Both follow from the calendar. The sitemap rows and articles dated before the
   first date are dropped when the index is built and never stored or read.
2. **Data tier.** TIER_3: Yahoo daily bars (95.5% of closes equal the exchange's in the 918,000-row overlap), survivor-only (60 names stop
   at the boundary and cannot be bought or drawn as controls), no share counts, corporate actions from Yahoo split events only (single source,
   never share-scaled: a trade held across such a reset is not scored, for events and controls alike). The market-cap bucket is therefore
   constant in the segment and controls match on price band, liquidity, volatility, momentum, drawdown and listing age.
3. **Candidates.** The same pinned ticker list as test 23 (the IDX mirror's `List Emiten/all.csv`); the 25 names listed after the boundary
   cannot be candidates.
4. **Market rules.** The harness applies the auto-rejection regimes in force (15% lower limit from 2025-04-08; floor Rp1 from 2026-09-28).
5. **Sealed prices.** Prices of the sealed holdout enter only as look-back history of the matching features and the 60-session eligibility
   count at the start of the segment; no event, entry or exit lies in it and nothing computed on it is read or printed.

## Gates (PASS only if all four hold; hold 20)
- **G1** mean excess over matched controls > 0 with day-cluster bootstrap t >= 1.65 (one-sided 5%). This replicates one pre-specified effect;
  it is not a new discovery, so the project's 3.0 hurdle for new tests is not applied. It is counted in the register (test 24).
- **G2** mean net > 0 and the winsorised mean net > 0.
- **G3** mean excess > 0 in each calendar year that has at least 20 scored events.
- **G4** mean net > 0 after an extra 0.5% per side.
**GO rule before the run:** at least 100 events with status EXITED at hold 20, counted from the harness's statuses without reading any
return. Fewer: the run is not made, the shortfall is reported, and there is no verdict.

## Power (stated now)
The discovery standard error was about 0.9% at 370 events. At n scored events it is about 0.9% x sqrt(370 / n), and G1 needs a mean excess of
1.65 times that. Approximate chance of passing G1 (normal approximation): if the true excess equals the discovery estimate (+2.8%) 48% at
n = 100, 62% at 150, 81% at 250; if it is half of it 20%, 25%, 35%; if there is none 5%. The discovery estimate is probably inflated (winner's
curse; its own decline by year), so a miss with a positive excess is not a refutation.

## Reported whatever the verdict
Holds 5, 20 and 60 (scored events, hit rate, mean and median net, mean excess, t); status counts; results by calendar year and by half-year;
the mean control return; the share of the excess given by the top 5 and top 20 events; the discovery's numbers beside; the inverse-variance
pooled excess of discovery and this segment (descriptive only). 3 variants are counted in the register.

## How the result will be read (fixed now)
- **PASS**: the lead persisted out of time. Next steps: a forward paper watch of the news feed (read-only), then the sealed IDX holdout as a
  single confirmation (owner authorisation). Still the news clock, not the filing's; still survivor-only data.
- **G1 holds but G4 fails**: the effect exists but is too small after realistic frictions.
- **G1 fails with mean excess > 0 and t >= 1.0**: a lean in the same direction without the power to confirm; no verdict.
- **Otherwise** (mean excess <= 0 or t < 1.0): no sign that it persisted; test 23 is read as a decayed effect or a false positive and gets
  no follow-up without new data.
No rerun after the result: any change is a new experiment with its own protocol.

## Limits (stated before the result)
- News posting time, not the filing's; EmitenNews chooses what it writes; the labeller is a model audited by two other model sessions of the
  same family; recall is not measured beyond the audit's sample of other items.
- TIER_3 data is survivor-only and single-source for corporate actions; control matching lacks the market-cap bucket. Survivor-only data
  flatters long positions for events and controls alike; names that were delisted or suspended after the boundary are absent from both, so
  the excess is less affected than the net return but not unaffected.
- One source, one market, 18 months, few events; IDX moves in lots and has daily price limits; the March-April 2025 crash and rebound sit at
  the start of the segment (controls share the same sessions, which cancels the market move but not event-type effects).
- A decaying effect (+5.6%, +3.2%, +1.6% in 2021-2023) predicts a small excess here; the gates were fixed knowing that.

# Binance futures-launch announcements at minute resolution (BINANCE_ANN_1M)

Written 2026-10-21 and committed before any minute bar or return for these events is fetched or read. Historical research
only: never prospective performance; no orders; the frozen paper cycle is untouched.

## Why this test
Every stock test KOD has run died at stage 2 of the three stages: public news is priced before an obtainable entry. With
daily bars the loss is a day wide, so "before an obtainable entry" could mean a minute or a morning. Crypto is the one
market where the clock is free: 1-minute bars of every pair, delisted ones included, and exact announcement times in
milliseconds. This test measures stage 2 in minutes for one concrete, repeatable event: a token's **first USDT-margined
perpetual launch on Binance Futures**, announced on Binance's own site, for a token that already trades against USDT on
Binance spot (so a spot buy is possible the moment the announcement appears).

## Events (fixed before any price is read)
`feasibility/events.csv`, rows with `eligible = True` (counts-only feasibility, `feasibility/FEASIBILITY.json`):
- an article in Binance's "New Cryptocurrency Listing" catalog (`announcements.csv.gz`, release time in ms) whose title is
  "Binance Futures Will Launch ... Perpetual ..." and names the token (index products excluded);
- the token's USDT-margined perpetual has its first archived trading day (data.binance.vision, futures/um, 1d) 0-7 days after
  the article's release date, which removes repeat launches (BUSD-, USDC-, coin-margined contracts of a token whose main
  contract exists) and mis-read titles by an external fact;
- the token has a spot `<TOKEN>USDT` pair (a `1000`-prefixed token maps to the unprefixed pair if the prefixed one does not
  exist) with at least 30 days of history and a median daily quote volume of at least USD 1,000,000 over the 30 sessions
  before the announcement day (from the existing daily panel, `data/raw/binance/20261008T001212Z`);
- announced 2020-02-01 .. 2023-12-31 (the panel starts 2020-01-01; **2024 onward is never loaded**).
Feasibility result: 115 events on 102 distinct days (2020: 35, 2021: 26, 2022: 14, 2023: 40); the rule was GO at 100 events.

## Time and price conventions
- T = the article's release time. b0 = the 1-minute bar (UTC) that contains T. `C[b0+m]` = the close of the bar m minutes after
  b0 (the price at the end of that minute). Minutes without a trade carry the last close forward; before a pair's first bar the
  close is missing.
- **Entry** at `C[b0+d]`. **Exit** at `C[b0+d+h]`. Primary: d = 0 (the close of the announcement minute: a reaction within
  the minute, i.e. an automated one), h = 60 minutes. Gross return = exit / entry - 1.
- Costs: 0.20% per side (the paper ledger's crypto assumption: Binance's 0.10% taker fee plus 0.10% assumed slippage), so net =
  gross - 0.40%. Sensitivity: 0.10% and 0.40% per side. These are assumptions; the microstructure side-car is now measuring
  the real book cost for the paper candidates.

## Controls
For each event, the pool is every USDT spot pair in the daily panel (delisted pairs included) with at least 30 days of
history, median 30-session quote volume >= USD 1,000,000 before the announcement day, daily bars through the day after
the announcement, other than the event's own pair, other than any pair with an eligible event within 1 day, and other than
stablecoin and fiat pairs and leveraged tokens (base asset in the list `STABLE_FIAT` of `fetch_minutes.py`, or a name ending
UP, DOWN, BULL or BEAR). Order the pool
by a permutation seeded with `sha256("20261022|<article_id>|<token>")`; fetch the first 16; keep the first 10 that traded in
at least 30 of the 60 minutes before b0 and in bar b0. Excess = the event's return minus the mean of its controls' returns at
the same offsets (a spec that needs entry at `b0+d` also needs each control to have traded in that bar).

## Event quality (deterministic, from the bars, before returns are looked at)
An event is **valid** if its own pair traded in bar b0 and in at least 30 of the 60 minutes before b0, and it has at least 5
usable controls. Invalid events are counted and dropped; nothing else is dropped.

## Statistics
Cluster = the UTC day of the announcement. Bootstrap: 10,000 resamples of days with replacement; t = mean over the bootstrap
standard error. Seed 20261022 plus the cell's position (0-19) in the grid below, d-major then h (so the primary cell, d = 0
and h = 60, uses 20261024); the G4 test uses 20261022 + 99. Winsorised means clip at the 1st and 99th percentiles.

## Gates (PASS only if all four hold)
- **G1** primary (d = 0, h = 60): mean excess over controls > 0 with bootstrap t >= 3.0 (the project hurdle, research/QUANT_GRADE,
  counted test 21).
- **G2** primary: mean net > 0 and the winsorised mean net > 0.
- **G3** primary: mean excess > 0 in each calendar year that has at least 20 valid events.
- **G4** delayed entry (d = 4, h = 60; the close of the fifth minute): mean excess > 0.

## Reported whatever the verdict (descriptive, not gates; 20 cells counted as variants in the register)
- The grid d in {0, 1, 4, 14} x h in {5, 15, 60, 240, 1440}: mean gross, excess and net, bootstrap t, share positive.
- The mean path of the event, the controls and the excess at m in {-60, -30, -15, -5, -1, 0, 1, 2, 3, 4, 5, 10, 15, 30, 60, 120,
  240, 480, 1440} relative to `C[b0-1]`: how much of the move had happened by the end of the announcement minute.
- Leak / clock check: the mean excess over m in [-60, -1] (before the announcement).
- Cost sensitivity at 0.10% and 0.40% per side; results by year; per-event table.

## How the result will be read (fixed now)
- **PASS**: the reaction to a futures-launch announcement is partly capturable after an obtainable (>= 5 minute) delay and costs.
  Next step: a forward paper watch of Binance's live announcement feed, recorded the way the paper ledger is; nothing real.
- **FAIL, with the excess already earned by the end of the announcement minute (excess at m = 0 at least half of the excess
  at m = 60, and that excess positive)**: the market prices the launch inside a minute; the stage-2 bottleneck is now measured:
  an obtainable entry is later than the move.
- **FAIL, with a positive pre-announcement excess at least as large as the post-announcement one**: the clock or a leak
  places the move before the published time; either way nothing obtainable. Recorded as such.
- **FAIL otherwise**: futures-launch announcements left nothing obtainable at minute resolution in 2020-2023.
If more than one FAIL reading applies, the pre-announcement (clock or leak) reading comes first.
No rerun after the result: any change is a new experiment with its own protocol.

## Limits (stated before the result)
- The catalog's release time is the page's publication time; its lag behind the true release cannot be checked. The
  pre-announcement check above is the only guard.
- A close-of-minute entry is the earliest honest entry these bars allow; sub-minute fills and the spread at announcement time
  are not observed, so costs are assumed. The owner cannot trade within a minute by hand: G4 is the human-latency line.
- Binance is the venue measured; whether the owner can trade it (or a broker's copy of it) is an open account question.
- One 4-year window with 2022 thin (14 events); events cluster in time (hence day clusters); tokens are those Binance chose
  to launch. Controls are liquid altcoins at the same minute, so common market moves cancel but event-type effects (e.g.
  launch-day volatility) do not.
- 2023 is used validation for the moonshot detectors; it is plain sample here because no detector is involved.

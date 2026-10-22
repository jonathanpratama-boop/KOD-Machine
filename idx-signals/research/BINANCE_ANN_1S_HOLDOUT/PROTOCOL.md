# Binance futures-launch announcements in seconds, out of time (BINANCE_ANN_1S_HOLDOUT): protocol

Written 2026-10-22 and committed before any crypto datum dated 2024-01-01 or later is read for this hypothesis. Authorised by the owner
in `AUTHORIZATION.md` (quoted verbatim). Historical research only: never prospective performance; no orders; the frozen paper cycle is untouched.

## Why this test
`research/BINANCE_ANN_1S` (counted test 22) found that buying Binance spot 2 seconds after the published time of a futures-perpetual launch
announcement and selling 5 minutes later netted +1.30% per event after a 0.2% round-trip fee (t 3.58, 103 fillable events of 2020-2023). It was
chosen after seeing the minute-level result on the same events, it measures trade prints rather than quotes, and it is the only lead in the
register that still stands (the IDX insider-buy lead failed out of time on 2026-10-21). This protocol applies **the same event rule, trade
definitions, cells, costs and statistics, unchanged**, to the launches announced from 2024-01-01 to 2026-09-30: events nobody has analysed.

## Events (the rule of `research/BINANCE_ANN_1M/feasibility.py`, applied to a new window)
From `research/BINANCE_ANN_1M/announcements.csv.gz` (sha256 `766da636a68e9301cdf5cca93e7e9963fd8f4cec2b3321d189694f969a784761`; the full catalog as served on 2026-10-21; its 2024+ rows were
stored but never read or analysed, the code cut the catalog at 2024-01-01), articles released 2024-01-01 00:00 UTC .. 2026-09-30 23:59:59 UTC whose title is
"Binance Futures Will Launch ... Perpetual" (no index products) and names a token such that: the token's USDT perpetual's first archived day (data.binance.vision,
futures/um, 1d klines) is 0-7 days after the article's release date; the token has a spot `<TOKEN>USDT` pair (a `1000`-prefixed token maps to the unprefixed pair if the
prefixed one does not exist) with at least 30 days of history and a median daily quote volume of at least USD 1,000,000 over the 30 sessions before the article day
(from the stored daily panel `data/raw/binance/20261008T001212Z`). Events after 2026-09-30 are left for a forward watch. One row per (article, token); the day cluster is the UTC day.
An event is **usable** if its pair has at least 3 trades in the 60 seconds before T. The **placebo** is the same pair 24 hours earlier.
The code that selects events and runs them is test 21/22's, loaded unchanged: `BINANCE_ANN_1M/feasibility.py` sha256 `66201a5e4d14bc891682d97cf326d57936f9424ca28aab9b6cfe2375e4142b3a`, `BINANCE_ANN_1M/run.py`
(`cluster_boot`, `winsor`, `p_one_sided`) `36581fd770c738db9a30309a0fea465cdffb1415d9f0577deafbd85f69ded212`, `BINANCE_ANN_1S/run.py` (`analyse`, `cell_stats`) `1c32253405c19e1a1a28e4376b50b120801de0f78147db4e2d45faaf54716cad`, `BINANCE_ANN_1S/fetch_ticks.py`
(`one`, `day_url`, `download`, `read_slice`) `aae6d7b524b683a79081ecc17d79a5bae21c071c95a3ba025d20dade646097bb`; `run.py` refuses to start if any of them differs.

## Data and what is opened
Binance's public daily aggregate-trade archives (spot/daily/aggTrades), the trades in [T-120 s, T+3900 s] for each event and each placebo, each archive's URL, size and sha256 in
`ticks/MANIFEST.json`. Opened for this test and nothing else of crypto 2024+: the daily quote-volume rows of candidate pairs for the 30 sessions before each article, the futures
archive's file names, and those trade windows. All other crypto data dated 2024-01-01 or later stays unopened. Definitions (T, P0, reaction R(s), latency L, entry at the first buyer-initiated
trade at or after T + L, exit at the first seller-initiated trade at or after entry + H, net = gross - 0.20%, conservative net = gross - 0.40%) are those of `research/BINANCE_ANN_1S/PROTOCOL.md`.

## Grid and statistics (unchanged)
L in {0.5, 1, 2, 5, 10, 30} s x H in {60, 300, 3600} s = 18 cells, all reported (18 variants counted in the register). Cluster = UTC day of T; 10,000 bootstrap resamples of days; seed 20261122 plus the
cell's position (0-17), L-major then H (the placebo uses the same); t = mean over the bootstrap standard error; winsorised means clip at the 1st and 99th percentiles.

## Gates (PASS only if all four hold)
- **G1** L = 2 s, H = 300 s: mean net > 0 with bootstrap t >= 1.65 (one-sided 5%). This replicates one pre-specified effect on new events, so the 3.0 hurdle for new discoveries is not applied;
  it is counted in the register (test 25).
- **G2** L = 5 s, H = 300 s: mean net > 0.
- **G3** L = 2 s, H = 300 s: the winsorised mean net > 0.
- **G4** (method check) the placebo's mean net at L = 2 s, H = 300 s has bootstrap t < 2.5.

## GO rules (counts only, fixed now)
1. After the events are selected (before any trade is fetched): at least 40 eligible events, else the run is not made and the shortfall is reported.
2. After the trades are fetched, before returns are read: at least 30 events that are usable and fillable at L = 2 s, H = 300 s, else the run is not made (the counts are reported; no verdict).

## Power (stated now)
The discovery standard error of the mean net at the gate cell was about 0.36% at 103 events; at n events it is about 0.36% x sqrt(103 / n) and G1 needs 1.65 times that. Approximate chance of passing G1 (normal approximation):
if the true mean net equals the discovery estimate (+1.30%): 61% at n = 30, 72% at 40, 86% at 60, 93% at 80; if it is half of it (+0.65%): 25%, 30%, 39%, 47%; if there is none: 5%. The discovery estimate
was chosen after a look and is probably inflated, so a miss with a positive mean is not a refutation.

## Reported whatever the verdict
The full 18-cell grid for events and placebo (gross, net, conservative net, unfillable counts); the mean and median reaction curve with day-cluster intervals; the speed of the move (half-move time,
share of events at half by 0.5, 1, 2, 5, 10, 30 s); the spread before and after T; the clock check (Pre and Total); results by calendar year; the discovery's numbers beside:
R(60 s) +3.35%, R(1 s) +1.33% (40% of R(60)), R(2 s) +2.18% (65%), median half-move 1.01 s, median spread 0.12% before T and 0.24% in the first 2 s, Pre/Total 3.5%, 103 fillable of 106 usable.

## How the result will be read (fixed now)
- **PASS** (all four gates): the seconds-level reaction and its capture at 2 s replicate on events nobody had analysed. Next step: a live measurement of feed lag and book depth (needs a process on the owner's
  side), then a search for a venue the owner can use, because Binance is restricted for the owner (`AUTHORIZATION.md`); nothing real.
- **G1 holds but another gate fails**: recorded as such; not a PASS.
- **G1 fails with mean net > 0 and t >= 1.0**: a lean in the same direction without the power to confirm; no verdict.
- **Otherwise**: no sign that it persisted. Then, in this order: if Total > 1% and Pre is at least a quarter of Total, "the move starts before the published time"; else if R(60) > 1% and
  R(1 s) is at least 80% of R(60), "the window has closed (the market got faster)"; else if R(60) <= 1%, "the reaction itself shrank"; else "no clear window". We stop chasing announcement reactions.
No rerun after the result: any change is a new experiment with its own protocol, and this holdout is spent for the hypothesis.

## Limits (stated before the result)
- Trade prints, not quotes; the first buyer-initiated trade approximates what a small marketable buy would have paid. The catalog's release time is the record's, not the time a poller could first see it.
- One venue and one event type; competing automated traders exist; Binance may have changed how announcements are published and how fast listings are priced since 2023; a result here
  is about the market's reaction, not about whether anyone can capture it, and the owner cannot trade on Binance.
- Multi-token launches give several rows with the same T (the day cluster handles it). Events are those of Binance's choosing.

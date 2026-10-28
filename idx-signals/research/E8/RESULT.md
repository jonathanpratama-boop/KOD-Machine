# E8 discovery result (KOD-CRYPTO-E8-v1): FAIL

Historical discovery on Binance spot data, July 2020 to December 2022. Not prospective
performance. 2023 and the 2024+ holdout were not read. The protocol was frozen at `8ec2265`, the
code at `f23e1f5`, and the run executed once (`discovery/summary.json`, `discovery/events.csv.gz`).
The regenerated warning list matched the committed feasibility v1.1 list exactly.

## Verdict

**Fail.** Four of six gates failed: information (G1), moonshot rate (G2), trading (G3) and
year consistency (G4). The sample gate (G0) and the busiest-weeks check (G5) held. No high-win-rate
label applies. Per the protocol, nothing is retuned and E8 stops here.

## Numbers (1,206 scored warnings, 116 weeks, 266 coins, 0 unscorable)

| Measure | Warned peers | Matched non-linked controls | Difference (95% week-bootstrap interval, one-sided p) |
|---|---:|---:|---|
| 72-hour gross return, mean | +0.56% | +0.12% | **+0.44%** (-0.28% to +1.16%, p 0.114) G1 fails |
| 72-hour gross return, median | -1.04% | | |
| High reached +20% within 72h (U20) | 17.8% | 15.9% | **+1.9 points** (-0.5 to +4.4, p 0.066) G2 fails |
| High reached +30% within 72h (U30, reported only) | 10.0% | 7.8% | +2.2 points (+0.1 to +4.4, p 0.017) not a gate |
| Excess in 2021 / 2022 / 2020 H2 | | | +1.00% / **-0.63%** / +3.2% (37 events) G4 fails |
| Excess without the two busiest weeks | | | +0.26% (1,150 events) G5 holds |
| Excess with one hour of extra latency | | | +0.30% (reported) |

Trading plan (buy next open; +20% take-profit, -10% stop, 72-hour limit; 0.4%-0.6% round-trip cost):

| | Value |
|---|---:|
| Mean net per trade | **+0.09%** (-0.88% to +1.10%, p 0.436) G3 fails |
| Same plan on controls | -0.40% |
| Median net | -2.13% |
| Win rate | **41.1%** (Wilson 95%: 38.4% to 43.9%) |
| Mean win / mean loss | +10.8% / -7.4% |
| Worst trade / worst 1% | -10.5% / -10.5% (the stop held; no gap below it) |
| Exits | 598 timeouts, 402 stops, 206 take-profits |
| Capital exposure | up to 17 positions at once; a position open in 70% of hours; mean hold 52 hours |
| At 5% of capital per trade | cumulative +5.5% over 1,206 trades, maximum drawdown **-38.9%** |
| Capacity | median $3,100 per trade at 1% of the coin's hourly volume (10th percentile $640) |

Link strength did not order the effect: excess +0.01% (low), +1.57% (middle), -0.27% (high tercile).

## What this establishes

- On this population and period, warned peers did not beat matched non-linked coins by enough to
  separate from noise. The interval excludes a 72-hour excess above about +1.2%.
- The costed plan was roughly break-even before uncertainty, lost in 2022, and won only 41% of
  trades. It is not a high-win-rate strategy, and its drawdown at modest sizing was severe.
- The point estimates lean positive (excess, moonshot rates, plan versus controls), but none clears
  a frozen gate, and 2022 reverses. The U30 difference has nominal p 0.017 as one of several
  reported secondary measures; it was not a gate, and no claim or retuning rests on it.

## What it cannot establish

- That spillover does not exist. It concerns this exact link (30-day partial correlation at hourly
  resolution), this leader definition, 72-hour horizon, plan, cost model and 2020-2022 Binance spot.
  It says nothing about IDX group rotation, other links (shared ownership, explicit sector lists) or
  faster execution.
- Fills: hourly OHLC cannot show order-book depth, so slippage is modelled, not measured.
- Any later period. A pass would have needed prospective confirmation; a fail needs nothing more.

## Process record

1. `b1d1f6d` mechanisms and feasibility rule, before any E8 data was read.
2. `a409810` feasibility v1 (GO, counts only); its peer list exposed a low-beta link defect.
3. `1b19dfb` amendment 1 (partial-correlation link, PAXG and BKRW excluded), before any outcome.
4. `bfcf099` feasibility v1.1 (GO: 1,206 events, 116 weeks, 266 coins).
5. `8ec2265` protocol frozen. `f23e1f5` outcome code and tests (253 pass). This run.

Reproduce (from `idx-signals/`, with the hourly archive files present):
`python3 research/E8/run_discovery.py data/manifests/binance_1h-20261015T182940Z.jsonl`
(refuses to overwrite `discovery/`; run it on a copy).

## Verification

- 20 E8 synthetic tests and the 253-test repository suite pass at `f23e1f5`.
- `verify_result.py` recomputes 25 randomly chosen events straight from the raw archive zips,
  without E8's outcome code: entry bar, 72-hour return, U20 label, plan exit reason and net return
  match in 25 of 25. It reproduces the mean excess and the bootstrap p (0.1137) from the saved rows.
- A second full in-memory run gives an identical report and the same FAIL decision.

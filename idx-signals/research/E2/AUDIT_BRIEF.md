# Audit brief: E2 US trading result

For an independent reviewer. It says what to reproduce and where each assumption lives. It is
not a self-audit: check the claims, not this file. Known problems the author found are in
[ERRATA.md](ERRATA.md); look for more.

## The claim

Detector G2_RET30 (a +30% day) on US common stocks, 2023: buying at the next session's open
and holding 5 sessions averaged **-3.65% net per trade (1,099 scored) vs -0.60% for matched
random entries** (`results/runs/20261008T060443Z_MOONSHOT_E2_US_D1_v1/`). The erratum puts it
at -4.47% with costs at the price actually traded. Question to settle: is the sign right?

## Provenance

| Item | Where | Hash / commit |
|---|---|---|
| Protocol, frozen before analysis | `research/E2/protocol.json` | commit `a155cf0` |
| Detector frozen before validation | `idxsig/rules/moonshot_g.py` (`SELECTED`) | commit `e5a1be2` |
| Code of the run | | commit `826ec76` |
| Panel | `data/manifests/panel_us-20261008T004105Z.json` | panel sha256 `e5b52674…` |
| Raw pull | `data/manifests/yahoo_us-20261008T001812Z.jsonl`, `us_universe-20261008T001213Z.jsonl` | per-file sha256 in the manifest |
| Every attempt | `results/runs/…/trades.csv.gz` | sha256 in `results/RUNS.jsonl` |

Raw files and panels are not in git (size). Re-pulling now will not match byte for byte: Yahoo
re-adjusts history at every new split. Compare returns (ratios), not price levels.

## Reproduce

```sh
cd idx-signals
pip install -r requirements.txt
python3 -m idxsig fetch-us --start 2020-01-01          # ~15 min; new manifests
python3 -m idxsig build-global-panel --market US --manifest data/manifests/yahoo_us-<stamp>.jsonl
python3 -m idxsig run --market US --rule MOONSHOT_E2_US_D1 --start 2023-01-01 --end 2023-12-31 \
    --panel data/manifests/panel_us-<stamp>.json --no-commit
python3 research/E2/diagnostics/us_reverse_splits.py   # needs the original raw files
```

A cheaper check that needs no rebuild: sample rows of `trades.csv.gz` and compare
`exit_price / entry_price` against an independent source (exchange or broker charts). Dates
are the signal close, the entry open and the exit close.

## What to check, and where

| Area | Question | Code |
|---|---|---|
| Timing | Signal at the close of d uses data through d only; entry is the open of d+1; exit the close of d+1+5 | `rules/moonshot_g.py`, `rules/__init__.py` (prefix-first evaluation), `execution.py` (entry/exit search) |
| Prices | Yahoo split-adjusted closes and opens; one-day reverting spikes dropped | `global_panel.py` (`load_us`, `_spikes`, `_finish`) |
| Corporate actions | Splits handled by the source's adjustment; dividends ignored; **price levels not point-in-time** (erratum 1) | `global_panel.py`, `ERRATA.md` |
| Fills | $5,000 notional, whole shares, at most 10% of the entry session's volume; a name already held is skipped | `execution.py` (`SKIP_LOT`, `SKIP_LIQUIDITY`, `SKIP_OVERLAP`) |
| Costs | Assumed per side by price: 1.5% < $1, 0.5% $1-5, 0.15% $5-20, 0.05% above, plus the SEC fee; no measured spreads | `profiles.py` (`US`) |
| Exit | No stop: held 5 sessions, sold at the first close a sale is possible (the paper plans add a stop; the harness test did not) | `execution.py` |
| Controls | Same session, same price band / liquidity quintile / volatility / momentum / drawdown / age; market cap unknown for every US name (matched trivially) | `controls.py`, `backtest.py` |
| Survivorship | Universe = names listed on 2026-10-08; delisted names absent | protocol, `us_universe.py` |

## Which errors could flip the sign

Most known issues push the true result lower, not higher: survivorship drops names that
pumped and then died; costs are assumed, and sub-$5 names after a +30% day usually trade on
wider spreads; point-in-time costs are higher (erratum 1). What could make the reported loss
too pessimistic: bad Yahoo opens on the entry day (an opening print far from tradeable prices),
mis-adjusted splits that create fake drops inside the holding window, or an off-by-one in the
entry/exit sessions. Those are where an audit can most change the conclusion.

# E8 feasibility amendment 1 (2026-10-16), after the first count and before any outcome

The first feasibility check (`feasibility/`, decision GO) is preserved unchanged. Its event list
exposed a construction defect in the **link**, found from signal composition alone. No forward
return, high, low or other outcome had been computed by any E8 code at this point.

## Defect

The most frequently named peers were PAXG, a gold-backed token (86 of 1,687 events), BTC (65),
TRX (30) and ETH (30). Subtracting the cross-sectional median return assumes every coin moves one
for one with the market. Low-beta assets then share a common residual (minus the market move), so
their residuals correlate with each other and with any low-beta leader without any narrative or
group relation. The link was measuring "low beta" instead of "same group".

## Changes (fixed now; every other definition and every threshold is unchanged)

1. **Link = partial correlation** of the leader's and the candidate's hourly log returns given the
   market's hourly return (the same cross-sectional median as before), over the same 720 bars
   t-743..t-24, using bars where both returns and the market return are valid (at least 600).
   This equals the correlation of market-model residuals with each coin's own beta, so a coin's
   sensitivity to the market no longer creates a link. The floor (0.20) and top 3 are unchanged.
2. **Asset-backed tokens excluded** from the universe as never-eligible, like stablecoins: PAXG (gold)
   and BKRW (a Korean-won stablecoin missing from the shared stablecoin list). They cannot carry a
   crypto narrative move, and both are removed on that ground, not on any outcome.

## Re-run

The same feasibility script, GO/NO-GO conditions and spec run again into `feasibility_v1.1/`.
If that run is NO-GO, E8 stops at feasibility. The protocol is frozen only after it.

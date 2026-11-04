# E8 implementation notes (signal side), written before the feasibility check ran

Each note fixes a detail that FEASIBILITY_SPEC.md leaves open. Cited in `idxsig/e8.py` as "note n".

1. **Loading.** Timestamp checks (unit, hour alignment, monotonic order within a monthly file,
   duplicate bars across files) are counted on the raw rows before de-duplication. Duplicates keep the
   first row. Files for months after 2022-12 are never opened; `build_hourly` drops any bar after
   2022-12-31 23:00 UTC.
2. **Liquidity.** Median daily quote volume over the complete days (all 24 bars present) among the 30
   calendar days before the decision hour's day; at least 20 such days are required.
3. **Cross-sectional medians.** The hourly market return and the 24-hour market return are medians
   over eligible coins with a valid value in that bar, and are undefined when fewer than 20 coins
   qualify. A residual return exists for every coin with a valid hourly return in a bar where the
   market median is defined.
4. **Relisting guard.** A coin is ineligible on day d when it had a run of more than 7 consecutive days
   without any bar that ended within days d-60..d-1.
5. **First crossing.** A leader trigger at t requires that the raw leader condition held in none of
   hours t-72..t-1. A coin meeting the raw leader condition anywhere in t-72..t is not a candidate peer.
6. **One open event per coin.** When a coin is named as a peer within 72 hours of its previous peer
   event, no new event is created and no replacement peer is drawn. When several leaders name the same
   coin in one hour, the event records the leader with the highest link and the number of leaders.
7. **Sanity days.** "No bad bar in the 37 days before t" uses whole days d-37..d-1 (E6's per-day flag:
   taker volume above total volume, or a non-positive close).
8. **Trailing volatility** for the power calculation: standard deviation of valid hourly log returns
   over the 720 bars ending at t (at least 600 valid), times sqrt(72). No bar after t is used.

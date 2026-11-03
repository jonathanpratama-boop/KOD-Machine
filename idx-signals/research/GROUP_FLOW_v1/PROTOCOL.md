# GROUP_FLOW_v1: does a jump that rides its group's flow keep its gains better than a jump that happens alone?

Written 2026-11-03, before any outcome is computed. Owner's idea: follow the money; explain why a stock rises even without
news. SEESAW_v1 found month-level flow does not lead the crypto tide. This tests the stock-level version: is a jump part of a
group flow (peers rising the same day) or a lone move?

## Data
US repair panel (panel_us_repair-20261008T114805Z), daily, survivor-only, 2020-01-02 .. 2023-12-29. The sealed US holdout
(2024+) is never loaded.

## Events
A one-day jump: close / previous close >= 1.30 on session s, for a stock with 20-session median traded value >= USD 1m and
close >= USD 1, s between 2020-07-01 and 2023-11-29. One event per stock per 20 sessions.

## The group (causal)
Peers = the 20 other liquid stocks whose daily returns over sessions s-120 .. s-1 correlate most with the stock's (at least
100 shared sessions). Group move = the median peer return on session s.
- WITH GROUP: group move >= +3%.
- ALONE: |group move| <= 1%.
- (in between: reported, not compared)

## Outcomes (from the jump-day close, which is when you would see it)
fwd5 and fwd20 returns; KEEPS = fwd20 > 0; FALLS = a close <= jump close / 1.30 within 20 sessions.

## Reading (fixed now)
- **Flow-backed jumps last**: WITH GROUP has a higher fwd20 median AND a higher KEEPS share than ALONE, in both 2020-21 and
  2022-23. Then the group check joins the analyst as the "why is it rising" sensor, and is logged live.
- **No difference** otherwise.
Statistics: means and medians with a week-clustered bootstrap for the WITH minus ALONE difference in fwd20. One counted
exploratory test on development years.

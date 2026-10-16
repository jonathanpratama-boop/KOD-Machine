# E8 implementation notes, outcome side (written after the freeze at 8ec2265, before the run)

Cited in `idxsig/e8.py` as "note O n". None of these changes a value fixed in `protocol.json`.

- **O1 Window.** For a decision at the close of hour t, the entry is the open of bar t+1 and the
  window is bars t+1..t+72 inclusive. Only those bars are read for outcomes. The latency
  sensitivity uses bars t+2..t+73; when bar t+73 lies beyond 2022-12-31 23:00 it is not computed.
- **O2 Plan order.** Bars are processed in time order. Within a bar: a gap (open at or below the
  stop) fills at the open; otherwise a low at or below the stop fills at the stop; otherwise a high at
  or above the take-profit fills at the take-profit. The entry bar is evaluated too, with its open
  equal to the entry price. Absent bars are skipped. A position still open after the last bar exits
  at the last present close in the window (TIMEOUT).
- **O3 Labels.** U20 and U30 use the highest high over present bars of the whole window, regardless
  of when the plan exits; they describe the warning, not the trade.
- **O4 Costs.** Slippage is chosen by the coin's liquidity at the decision hour (the eligibility
  liquidity, note 2). The same costs apply to every exit type.
- **O5 Quintiles.** Liquidity and volatility cut points (20/40/60/80th percentiles) are computed on
  the pool coins that have an entry bar. The event coin is placed by the same cut points. An
  undefined volatility (fewer than 600 valid bars) can only match at the "liquidity" or "pool" level.
- **O6 Controls.** The pool excludes the event coin and the event's leader. The leader recorded for
  an event (the highest link when several leaders named it) defines "not linked".
- **O7 Weeks.** ISO weeks of the decision hour in UTC. Ties for the busiest weeks (G5) go to the
  earlier week.
- **O8 Exposure.** A position occupies hours t+1 to t+bars. The drawdown is measured on the
  cumulative net at 5% of capital per trade, ordered by exit hour, without compounding.

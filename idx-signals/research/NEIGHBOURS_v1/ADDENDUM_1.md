# ADDENDUM_1 (2026-11-03, written before any model is fitted or forward return computed)

PROTOCOL.md says features are rank-normalised across coins each day. That is undefined for features that are identical for every
coin on a day (BTC 7-day return, breadth, and the station returns). Resolution:
- Coin-level features (own returns, volume ratio, distance from high, volatility, all peer features) are rank-normalised across
  eligible coins each day, to [-0.5, 0.5].
- Day-level features (BTC 7-day, breadth, each station's 1- and 3-day median return) are z-scored with the mean and standard
  deviation of the training window. Because the target is demeaned across coins each day, a day-level feature on its own cannot
  change any coin's ranking; in model A (BTC 7-day, breadth) they are therefore inert, and are kept only as written.
- In model C, each station return enters only multiplied by the coin's own-station indicator (5 own stations x 5 stations x 2
  horizons = 50 features), which is what lets "when station k moved, coins in station s do better or worse" affect rankings.
- Training rows for a refit on 1 January of year Y are days whose 5-day exit falls before Y (no label from inside Y).
Nothing else changes.

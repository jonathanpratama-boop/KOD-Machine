# Experiment E1: IDX five-session repricings (KOD-IDX-E1-v1)

Frozen before any analysis. The machine-readable protocol is `protocol.json`; every result
file records its SHA-256. Code: `idxsig/e1.py` (study), `idxsig/rules/moonshot_e1.py`
(detector family, shared with the backtest harness and the live paper scan).

**Question.** Using only what was known at a session's close, which signals distinguish IDX
names that reprice +30% / +50% / +100% within the next five sessions from similar names on
the same session?

**Event.** Decision cutoff = close of session t. R5max(t) = highest close over t+1..t+5,
measured on IDX's reference-price chain (so splits and rights issues do not create jumps),
relative to the close of t. Labels E30 / E50 / E100. An episode starts on the first
qualifying day with no qualifying day in the five sessions before it.

**Universe.** Every ticker-day in TIER_1 data where the name traded, has 20 sessions of
history and at least one later session; non-winners included; no price floor (bands reported).

**Periods.** Discovery 2021-01-22 .. 2022-12-30, validation 2023, holdout 2024-01-02 ..
2025-02-21. Five-session embargo at each boundary. The holdout is sealed: `e1.Study` ends its
market at the last validation session, so no holdout label can be formed until a detector
is frozen and validated, and then exactly once.

**First 100 events.** The first 100 E30 episodes of discovery in date order (ties by
ticker). No other selection.

**Matched controls.** Five per event: same session, other names, no E30, same price band,
liquidity quintile and market-cap quintile at the close of t (relaxed in that order when
fewer than five share all three). Volatility, momentum, drawdown and the day's behaviour are
deliberately not matched: they are candidate signals.

**Weak signals.** 20 pre-event measures (protocol.json lists definitions): returns over 1,
5, 20 sessions, market-relative return, volume, value and trade-count ratios, range
expansion, close location, volatility, drawdown, turnover, up days, untraded days, listing
age, size, ARA lock, 60-session breakout, and a daily analogue of ASTRA's IGNITION v1.
Reported as medians and matched-set AUC with bootstrap intervals.

**Detector.** One rule from the fixed family F1..F10, chosen on discovery only: admissible
if it flags at least 200 ticker-days and the Wilson lower bound of its E30 precision exceeds
the base rate; highest lift wins. It is written into `moonshot_e1.SELECTED` and committed
before any validation statistic exists. Validation then reports precision and lift against
the base rate and against matched random controls, recall and lead time, false alerts,
executability, and a trading run through the idxsig harness.

**Claims.** Historical research only. A 100-event pilot does not establish predictive power,
and nothing here is prospective performance.

# Pasted chart ideas, graded

Paste a TradingView idea (or any tip) in chat; it is written as a JSON spec here (never code: entry types are a fixed list
in `idxsig/idea_grader.py`) and graded with `python3 -m idxsig idea-grade research/IDEAS/<file>.json`:

1. against random entries with the same exit (does the signal beat the take-profit/stop geometry?);
2. against the search: the idea and its 160 near-identical neighbours, Hansen's SPA with a stationary bootstrap;
3. on a later period it was not chosen on (IDX: after the sealed 2024-01-02..2025-02-21 window; US and crypto: the last 30%
   of pre-2024 history, since 2024 on is sealed).

Verdicts: SURVIVES, IN-SAMPLE ONLY, NOT DISTINGUISHABLE FROM LUCK. Paper only. `example_bbca.json` is a demonstration (two
generic BBCA ideas, both NOT DISTINGUISHABLE FROM LUCK on 2026-10-29).

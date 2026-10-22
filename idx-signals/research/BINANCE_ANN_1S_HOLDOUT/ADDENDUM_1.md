# BINANCE_ANN_1S_HOLDOUT: addendum 1 (a title-format drift mis-parsed the tokens; the corrected selection)

Written 2026-10-22 and committed before the corrected selection is run. `PROTOCOL.md` governs everything not changed below.

## What happened
`events.py`, as committed, selected **9 eligible events** against the GO rule's 40 (`feasibility/`, committed as produced). Of the 338 token rows in the window, 46 matched a spot pair, all
in 2024; **none of the 228 rows of 2025-2026 matched one**, although the stored daily panel runs to 2026-10-08 and holds the 2025 listings (TRUMP, KAITO, BERA, PUMP, WLFI among them).
Reading only the titles and what the parser returned (no price, no trade): since 2024 Binance titles often name the **contract symbol** ("... USDⓈ-Margined NIGHTUSDT Perpetual Contract",
"... SLERFUSDT and SCRTUSDT Perpetual Contracts") instead of the base token ("... USDⓈ-M GLM Perpetual Contract"). Test 21's `tokens()` returned "NIGHTUSDT" and `pair_for` looked up
"NIGHTUSDTUSDT". The zero is an artifact of the parser, not a finding about Binance.

## The correction (and only this)
A parsed token of the form `<BASE>USDT` with a base of at least two characters is replaced by `<BASE>`. Nothing else changes: the window (2024-01-01 .. 2026-09-30), the rule (perpetual's first
archived day 0-7 days after the article, spot USDT pair of at least 30 days, median daily quote volume of at least USD 1,000,000 over the 30 sessions before), the GO thresholds (40 eligible events,
30 fillable at the gate cell), the 18 cells, the costs, the seeds, the gates, the reading rules. Known misses that stay missed: symbols longer than the 12-character token pattern
(1000000-prefixed contracts), contracts named in Chinese, "Multiple ... Perpetual Contracts" titles that name no symbol, and pre-market perpetuals of tokens with no spot pair yet (ineligible by the
age rule anyway).

## What is added
`events_v2.py` (the corrected selection, writing `feasibility_v2/`), and `fetch_ticks_v2.py`, `run_v2.py`, `verify_v2.py`: the committed scripts with their paths pointing at `feasibility_v2/`
(the committed files cannot be edited). The code hashes pinned in `PROTOCOL.md` (test 21/22's files) apply unchanged. The first-pass outputs in `feasibility/` stay as the record.

## Fixed now, before the corrected selection exists
- If the corrected selection still has fewer than 40 eligible events, the run is **not made** (GO rule 1 as written); the authorization is then spent only on counts and the shortfall is reported.
- If it has 40 or more, the rest of the protocol follows unchanged: ticks, GO rule 2, one run, the verifier, the register (counted test 25).

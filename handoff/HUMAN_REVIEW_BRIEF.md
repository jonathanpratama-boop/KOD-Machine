# Brief for one independent human review

For the owner to send to a freelance quantitative developer. Every finding in KOD so far has been checked only by AI
agents (Claude, Codex, Ace, Astra, Hermes), which can share blind spots. This review buys the one kind of evidence KOD
has never had.

## Scope (a few hours)
1. **Evidence system.** Are KOD's research controls sound? Pre-registered protocols committed before data, append-only
   records (`tools/check_append_only.py`), look-ahead guards (`docs/LOOKAHEAD_CHECK.md`), control-group construction,
   cost assumptions, and the timing journal (`docs/TIMING_RESEARCH.md`, `handoff/astra/`).
2. **Main conclusion.** For a retail trader using eToro and Stockbit (no API, manual orders, ~2% crypto round trip):
   price, volume, flow, attention, peer and exchange-listing signals on daily or hourly data do not make early entries
   profitable; detection of big movers works but buying them does not; "avoid" filters (lone spikes, recent +30%
   spikers, share issuance, crowded shorts) repeat across studies. Is that conclusion supported, overstated, or missing
   an obvious alternative?
3. **The last test.** INFO_MAGNET primary gate (Upbit KRW listings, 75 events, entry first full hour after notice, 24h
   hold): branch `codex/info-magnet-check-20261104`, folder `handoff/astra/info-magnet-check-20261104/`, and the
   independent check in `handoff/claude/INFO_MAGNET_VERIFICATION.md`.

## Deliverable
A memo of one to two pages: what is sound, what is wrong (with file and line), what they would test next or stop doing.

## Access
Read-only access to the GitHub repository `jonathanpratama-boop/KOD-Machine`. No server, broker or account access. No
credentials are shared.

## Who
A quantitative developer with crypto backtesting and market-microstructure experience (freelance platforms or
quant communities). Cost is the owner's decision; a few hours of freelance time is the expected size (not verified).

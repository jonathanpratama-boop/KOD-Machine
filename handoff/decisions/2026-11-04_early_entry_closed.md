# Decision 2026-11-04: early-entry research is CLOSED

**Owner's words (2026-11-03):** "Test, then close." The decision rule was fixed before the last test was run:
`handoff/timing/EARLY_ENTRY_CLOSE_RULE_2026-11-03.md` (commit `29fd09ee8`).

## The rule applied to the result

The lane stays open only if all three conditions hold. INFO_MAGNET primary gate, 24 h hold (Codex, branch
`codex/info-magnet-check-20261104`; independently verified in `handoff/claude/INFO_MAGNET_VERIFICATION.md`):

| Condition | Result | Holds? |
|---|---|---|
| 1. The locked plan's tradability test passes | `PRIMARY_GATE_FAIL` | **No** |
| 2. Mean minus random coins after a 2% round trip above zero, 95% lower bound above zero | -8.55 pp, 95% interval -13.95 to -2.01 pp | **No** |
| 3. At least 30 listing events | 75 | Yes |

Two of three fail. **Early-entry research is CLOSED as of 2026-11-04.** No prospective paper log is opened for listing
notices.

## What "closed" means
- No new study of entering earlier using price, volume, flow, attention, peers or exchange-listing notices. The closed
  record: E1-E3, ENTRY_TIMING (US and crypto), IGNITION and COMBO_HOLDOUT, BINANCE_ANN_1M, SEESAW, GROUP_FLOW, NEIGHBOURS
  and PRESSURE (originals and corrected runs, `idx-signals/research/RESEARCH_CORRECTIONS_20261104/`), ATTENTION_LEAD,
  Hermes's 3 November studies (reproduced in HERMES_NOV3_REPRO_v1) and INFO_MAGNET.
- **Reopening** requires a new kind of dated, non-price information that passes its own locked test opening with the
  feasibility gate (`docs/PROTOCOL_TEMPLATE.md`). New framings of the closed families do not qualify.
- New ideas go to `handoff/timing/IDEA_PARKING_LOT.md`, reviewed monthly (first review 2026-12-04).

## What continues
- TIMING_CAPTURE_v1 on the cloud server (operations evidence, not an entry test), 30 slots to 2026-11-09 16:00 WIB.
- LLM_ARM_v1 live calls toward 60.
- Avoid-side research, under its own protocols. The individual avoid findings come from different markets, horizons
  and controls and have not been validated as one combined rule (Astra's correction in
  `handoff/astra/PATCHES_RESEARCH.md`); a combined avoid checklist needs its own protocol before any paper run.
- Ace's economic-event register (on-chain buybacks and issuance) is a different information family and is not covered
  by this closure.

## The timing lesson in one line
The moves are real and they happen inside the minute or hour of the news; a manual retail trader enters after them
and then gives back. The owner's edge, if any, is on the avoid side and in preparation for scheduled events, not in
racing the news.

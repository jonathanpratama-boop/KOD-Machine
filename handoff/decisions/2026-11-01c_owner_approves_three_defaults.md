# Decision 2026-11-01c (owner): the three open decisions of 2026-11-01b are approved

**Owner's words (2026-11-01, 16:37 WIB):** "Im handing this to Ace. But, all three yes."

The three decisions, as put in `2026-11-01b_fresh_eyes_verdict_and_trend_core.md` and `handoff/fresh-eyes-2026-11-01/FRESH_EYES_VERDICT.md` section 8:

1. **Paper trial before any capital: approved.** TREND_CORE_PAPER_v1 (`handoff/fresh-eyes-2026-11-01/paper/PAPER_PROTOCOL.md`,
   sha256 `e48ddf92…16b8812`) runs for at least 90 consecutive logged days before any live allocation is proposed. The pass bar,
   risk layer and kill criterion are those in the protocol and are not changed. Earliest date a live proposal can be made:
   2027-01-29 (90 signal days from 2026-10-31), and only if the bar is met.
2. **Exchange rule-change event register as the one new research line: approved.** Scope: Binance announcements of spot and
   futures delistings, margin and leverage-tier changes, and collateral-ratio changes. The first step is a dated protocol,
   committed with its hash pinned before any announcement text or price is read, stating the event definition, the entry and
   exit, the matched controls, the costs (Binance spot 0.15% a side; perpetuals 0.10% a side plus funding), the development and
   validation periods, and the pass gate. LLM use is limited to parsing announcement text into a structured register; the
   parser is validated on a hand-labelled sample before any return is computed.
3. **Pause the Moonshot scheduled tasks: approved.** Applied on 2026-11-01 at 09:38 UTC: "Moonshot weekly review" is disabled.
   "Moonshot pre-open scan (v3)" and "Moonshot post-close log (v3)" could not be disabled from this session (the platform
   refused the change); the owner disables them in the scheduled-task settings. The Moonshot ledger and registry are left as
   they are, with no closing entry written; the pause is reversible.

**Not changed:** every frozen protocol and ledger; the daily crypto paper scan, the KOD daily sensor pull, the two decision-note
scoring reminders and the PREMOVE_SHADOW_v1 trial, which continue to their frozen ends.

**Handover:** the owner is handing the next stage to Ace. `handoff/fresh-eyes-2026-11-01/HANDOFF_TO_ACE.md` is the entry point.

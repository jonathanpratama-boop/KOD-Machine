# Guidance comparison on the cloud

The existing server runs a separate `kod-guidance-margin.timer`. One cycle collects the declared wire feed, reads new supported disclosures through the API, records source-only reviews, admits qualifying pairs, updates available daily paper prices, and writes `STATUS.json`. The existing dashboard publisher includes a summary on its single page. The R2 services and frozen protocol are separate.

- Code: `/opt/kod/guidance-margin`
- Private state, sources, API receipts and decision journal: `/var/lib/kod/guidance-margin`
- Private credential: `/etc/kod/guidance-margin.env`, mode 0600
- Status: `/var/lib/kod/guidance-margin/STATUS.json`
- Timer: `kod-guidance-margin.timer`, ten minutes after each completed cycle
- Public summary: `GUIDANCE_MARGIN_STATUS.json` alongside `DASHBOARD.html` in the existing backup branch

The protocol is `idx-signals/research/GUIDANCE_MARGIN_PAPER_v1/PROTOCOL.md`. First operational review: 20 November 2026. Early price observations appear after actual entries at sessions 1, 3 and 5; the primary horizon is 20 exchange sessions. A source arrival or a model call is not an eligible signal or a profitable trade.

API charges are estimates based on retained token usage. The reader reserves a conservative amount before calls, avoids automatic repeats of a paid intent, and stops paid calls before the promotional-credit expiry. The quote and scoring paths continue without paid calls. Unknown transport usage remains conservatively reserved. The allowance is for KOD calls only, not a live invoice balance or protection against unrelated account spending.

Only source-backed, reviewed facts are admitted. A second model read does not prove correctness; source coverage and agent review remain limitations of the pilot. Missing or contradictory facts are visible and excluded, rather than changed into zero. Daily opening prices are modeled fills. Splits or dividends reported during a holding period require review before valuation; the study shows that missing outcome instead of silently adjusting it.

`run.py --skip-feed` updates existing paper prices and status without model calls. Restarting the timer does not reset state or backfill missed admissions. Inspect `journalctl -u kod-guidance-margin.service` and `STATUS.json` for failures. Preserve original journal rows when making corrections.

# ATTENTION_LEAD_v1 report (run once, 2026-11-03)

**Locked reading: NO USABLE LEAD.** Attention surges on stocks that have not moved yet come before slightly more big moves
in *both* directions, with no excess return. In the descriptive view, attention arrives on the jump day, not before it.

Data: Wikimedia monthly pageview_complete user dumps (ADDENDUM_2), 1,884 of 1,952 articles found, 2,317,864 article-days.
Validation gate: dump vs API on 82 articles / 102,377 article-days, 100% exact match. Prices: repair panel 2020-07..2023-12.

| | Attention-surge events | Controls (same day, quiet attention) |
|---|---|---|
| Events | 1,473 (683 tickers) | 5+ per event day |
| +30% within 20 sessions | 3.80% | 2.41% (lift 1.58x) |
| -23% within 20 sessions | 3.80% | 2.82% (1.35x) |
| Mean fwd20 | +1.18% | +1.08% |
| Excess fwd20 | **+0.10%**, t 0.24, 95% range -0.65% .. +0.92% | |
| Median excess | -0.75% | |

Criteria: up30 >= 1.5x controls PASS; (up - down) above controls PASS (narrowly: 0.0 vs -0.4 pts); excess t >= 2 FAIL.
"Both ways" needs dn23 >= 1.5x controls: 1.35x, not met. So the locked code returns NO USABLE LEAD.

By year, excess: 2020 -0.68%, 2021 -0.06%, 2022 +0.01%, 2023 +0.79%. 2022's crash rate on events was 8.7%.

Jump profile (571 one-day +30% jumps, median views / normal): days -10..-2 about 0.97-1.12x (noise), day -1 **1.18x**,
day 0 **2.36x**, day +1 1.92x. The only pre-jump rise is the day before, and UTC day -1 includes US evening news and
after-hours trading, so it is at most hours of lead, not days.

300-ticker subset (ADDENDUM_1 sample, same code, `sample300/`): 238 events, up30 5.0% vs 2.0%, dn23 2.9% vs 1.9%,
excess +0.55% t 0.76, reading "ATTENTION LEADS, BOTH WAYS". Small sample (12 up-hits); the full universe is primary.

## Plain reading
A Wikipedia surge on a quiet stock means "something is about to happen", about 1.5x more often than normal, but it is
as likely to be a crash as a jump. It does not tell you which, and on average there is no extra return. Attention
does not arrive days early: it arrives with the price. This closes the last "before the crowd" door testable on daily data.

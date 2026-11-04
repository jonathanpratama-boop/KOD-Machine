# KOD decision policy: judgment instead of fixed trading rules (draft v0, 2026-11-03)

**Owner instruction (Jonathan, 2026-11-03):** remove the fixed rules we wrote. KOD's trading decisions no longer come from
one-size rules (buy every alert at the next hour, +50%/14-day exit, the same entry in every mood, summed chart clues).

## What is removed (decision rules)
| Old fixed rule | Replaced by |
|---|---|
| Buy every qualifying alert at the next hour | Case-by-case: preferred / watch / no action |
| Fixed +50% target, 14-day hold | Target and holding time argued per candidate from structure, catalyst and crowd mood (clue ledger #6, #7) |
| Same entry style in every market | Entry chosen per case (market, limit, confirmation), with the historical missed-winner cost stated (#9, #10) |
| Six chart clues added as a score | Separate evidence families weighed explicitly; overlapping chart clues counted once (#4) |
| A single sentiment gate (F&G ≥ 55) | Mood used as context for the clock, not a pass/fail switch (#6) |

The clue ledger becomes **guidance labelled passed / clue / failed**, not rules. Judgment may override a clue but must say why.

## What stays fixed (these are not trading rules; without them judgment cannot be told apart from luck)
1. **Record before outcome:** every decision, its reasoning, entry plan and the rejected candidates are written and
   timestamped before the result is known. "No action" is a recorded decision.
2. **Fixed scoring:** after costs, against the same candidates' chart-only ranking, a random pick, holding BTC and cash.
   First verdict at 60 decisions. The scoring method is not changed after seeing results.
3. **Paper only.** No real money without Jonathan's explicit approval of a specific trade.
4. **Evidence-backed limits:** no shorting into crowded shorts (#12); no leverage; costs and realistic fills counted.

## Not touched by this change
- Past frozen tests and their results (they are the evidence behind the clue ledger; never deleted).
- Live paper tests already running on GitHub (changing them mid-run voids them; scan shutdown is Jonathan's).

## Known risk
Judgment cannot be backtested (an AI may already know historical outcomes), so proof is live only and slow, and flexible
judgment is easier to fool ourselves with. The fixed record-and-score rules above exist to catch that.

## Correction C1 (2026-11-04)
"Drop anything that hasn't moved by about day 3" is removed as a hard rule wherever it appears in this policy or in the
analyst card. HERMES_NOV3_REPRO_v1 (branch claude/hopeful-hypatia-ktzpog) did not reproduce PATHS_v1's "under 1 in 100":
in 2023-26, 38% of alerts that ended day 14 up 20%+ had not touched +20% by hour 72 (4.4% of all alerts). Not moving by
day 3 lowers the odds (6% vs 27%) but does not end them. It stays only as a probability tilt the analyst may weigh.

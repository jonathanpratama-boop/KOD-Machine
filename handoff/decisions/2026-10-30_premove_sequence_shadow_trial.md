# Decision 2026-10-30: pre-move sequence stays a frozen challenger; one prospective shadow trial

Owner's decision (relaying Ace's review of PR #19): retain sequence as a frozen research challenger and keep summary
as the default research baseline. The benchmark is real progress in how KOD tests early detection, but it has not
shown that sequence features beat summary features: +0.88 percentage points, 95% interval -0.22 to +1.81.

Applied as research/PREMOVE_SHADOW_v1:
- three frozen arms rank the same crypto candidates daily: summary, sequence, and a control fitted with each
  row's 20-day window shuffled (each day's return, range and volume kept together);
- same eligibility, target and five-alert budget as PR #19; 12 months of decisions (2026-10-30..2027-10-29) plus
  five days for the last outcomes; no retuning, no performance-based stopping, no extension;
- primary: sequence-minus-summary early hit rate, paired calendar-block bootstrap; promotion only with at least
  +1 point, an interval above zero and more distinct episodes; order credited only if sequence also beats the
  shuffled control; an inconclusive end leaves summary as the default.

The control was fitted on a re-collected vintage whose panel is byte-identical to PR #19's input; refitting the
frozen summary and sequence models on it reproduces their coefficients exactly.

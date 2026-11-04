# Pre-capture correction 2 — endpoint-specific receipt policy

2026-11-01, saved BEFORE implementation of this correction or any public API
request. Parent review identified avoidable false blocking from treating cached
closed historical candles/product metadata as if each were an executable quote.
This changes the fixed policy before seeing outcomes, not after a failed capture.
The original specification and earlier review addendum remain preserved.

- Every response: UTC-aware local start/receipt, monotonic elapsed and wall elapsed
  must agree within0.25 seconds; explicit GMT HTTP Date required; nonnegative finite
  Age if supplied; HTTP Date cannot be more than5 seconds in the local future.
- Book: unchanged RTT≤2 seconds, Age exactly0, HTTP Date within5 seconds of receipt,
  source book time within0..5 seconds of receipt, fresh mark≤5 seconds at use.
- Product and closed-candle warm-up: RTT≤5 seconds, HTTP Date no older than300 seconds
  at receipt, Age≤300 seconds. This is a bounded operational cache tolerance, not
  a claim these responses were first published at their HTTP Date.
- Product at-use age is conservative: max(Age + measured response delay,
  receipt-minus-HTTP-Date,0) plus elapsed local receipt-to-use must remain≤300 seconds. Cached metadata does not receive
  a new300-second lifetime just because it was received locally again.
- Candles: additionally require the response HTTP Date at/after the end of the final
  selected daily bucket. This rejects an older cached pre-close snapshot even when
  the latest day has closed by local receipt. Still require exactly40 complete,
  contiguous, latest-day UTC buckets and actual receipt-time availability; absent
  first-publication time remains null. Returned out-of-window buckets are audited.

Books—not historical cache timestamps—provide the strict contemporaneous clock
check before a decision and fill. A cached warm-up is not a stale executable quote.
All source identity, post-intent timing, no-retry/no-fallback, managed routing and
simulation-only rules are unchanged. The old clearance is invalidated by these
source/policy changes; independent re-review is required before the first attempt.

Independent-review clarification before capture: effective source age uses
max(apparent Date age, Age + measured response delay), then adds local residence
at metadata use. Do not add Date age and Age together (double counting). If Age
is absent, no claim of zero cache age is made: use the available Date-derived age
and measured delay conservatively; first publication/cache history remains unknown.
Reject duplicate case-insensitive header names, malformed/nonfinite/negative Age,
and preserve header pairs in new raw receipts so duplicate headers cannot disappear
when converted to a dictionary. The same bounded300-second source-age gate applies
before accepting product/candle receipts; books retain the stricter unchanged gate.
Age syntax is ASCII integer delta-seconds only; signs, fractions, nonfinite values,
whitespace and duplicate-case representations reject rather than normalize. An
absent Age field is explicitly distinguishable from a supplied zero field in the
preserved receipt; the age lower-bound calculation never claims full cache history.

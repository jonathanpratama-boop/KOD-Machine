# Source census sampling correction — declared before roster construction

16 November 2026. One bounded source-only correction to Phase 1, not a new
strategy or an outcome-selected extension.

The first 20 ascending CIKs remain recorded. Their registration-age bias and
small sample do not support closing the wider availability question.

Take the distinct positive integer CIKs in E10 `filings.csv`, pinned Git blob
`caaf2108a2fae0e94467305dab0d88bc195f808b` at KOD commit
`c22b2e1682c0322fc65569e159a257d147a1f86f`. Exclude exactly the original 20 CIKs,
not inconvenient new cases. For each remaining CIK, compute SHA-256 of the
UTF-8 string `KOD_MARGIN_SOURCE_CENSUS_V2_20261116:<integer CIK>` (no leading
zeros). Sort ascending by the hexadecimal digest, then numeric CIK for a tie.
Select the first 40, without replacements. Use the lexicographically first
frozen ticker for display. The salt and sample size are fixed by this file
before the roster is constructed. They will not be searched or changed.

Window and fact definition remain exactly those of `source-census-selection.md`:
1 October–15 November 2026 inclusive; comparable full-year revenue plus
same-period, same-basis operating-profit or operating-margin guidance revision.
EPS, EBITDA, gross margin and FCF are not substitutes. Preserve failures,
unknowns, inaccessible sources, missing priors and accounting-definition changes.
Do not fetch market-price series, returns, holdouts or interim strategy results.

Report the 40 separately from the earlier 20 and targeted source examples.
The historical E10 issuer universe retains its survivor/liquidity and historical
coverage limitations. Hash order removes the explicit preference for low CIKs;
it does not make the parent universe representative of the whole US market.
Any already encountered issuers remain development observations. Missing event
enumeration is UNKNOWN, not confirmed absence. A source-positive event is not
yet an actionable or profitable signal.

This is the sole additional availability sample in this execution. Complete it
and make a bounded build/hold decision with the observed denominator and source
limitations. Do not keep extending the sample until a positive appears.

# Repairs between first execution and accepted execution

The first execution is preserved. No hypothesis, primary horizon, cost, control sampling seed, bootstrap method or decision threshold changed.

1. Target eligibility mistakenly used the filtered control pool. Fixed to check targets against the complete historical archive symbol directory. Control product exclusions still apply only to controls. An excluded stablecoin target is not falsely called an absent archive.
2. Older source notices express the ticker as Korean name plus a terminal uppercase token inside parentheses and sometimes express KRW as Korean `원화`. The initial parser missed six older ticker notices and four target tokens in the `원화` notice1882. Parsing now follows those unambiguous forms. Mixed swap/background annotations are retained as ignored diagnostics, not turned into new listings. Three unresolved BTC-only title formats remain rejected; they do not enter the KRW primary test.
3. The official, checksum-verified NEAR December2021 file contains an unrelated internal row ending1.334seconds short of a full hour. The first parser rejected the entire month. The corrected parser retains verified raw bytes and diagnostics, makes valid other hours available, and still raises an integrity error if the requested entry, eligibility or exit hour is incomplete. No price is interpolated, repaired or assumed.
4. Secondary-horizon data failures remain separate from the primary result. Missing outcome data never triggers replacement of an already-selected control.

The first Mac launch also encountered a missing Python certificate bundle. Execution used the existing system CA bundle via SSL_CERT_FILE=/etc/ssl/cert.pem; TLS verification was retained.

These implementation repairs were made after the first execution revealed defects. The first-run partial results are therefore retained as superseded implementation evidence; no claim is made that the corrected source was frozen before any outcomes were viewed. The economic specification was published in e97a93e before the first price read and remains byte-identical.

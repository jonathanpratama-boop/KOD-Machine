# Named cost assumptions

Each new cost profile has a version, explicit quote currency and effective interval,
source references and an account-applicability status. `valid_from` dates the use
of this research assumption; it is not a claim about when a broker changed fees.
The historical studies retain their original costs and outputs byte for byte.

`etoro_crypto_2026.json` keeps the owner's reported 1% per-side assumption. The
official public schedule was reviewed on 4 November 2026 and is tiered by account
level and volume. The owner's actual rate, product and FX costs remain unverified.
No authenticated account or current holdings were read. A named assumption does
not establish account access or prove that a proxy quote is executable there.

`hermes_legacy_crypto_003_v1.json` names a historical 0.3% per-side assumption for
comparison. It does not rerun or amend any frozen research result.

Existing runtime account profiles already pin `fee_rate` and `slippage` by hash.
`idxsig.timing_context.account_cost_profile` derives a named description without
altering the source profile, its identity, rounding rules, or journal. New fees
require a new explicitly selected profile; an existing paper account cannot be
silently migrated to another fee assumption.

Shadow price checks use ask for a hypothetical entry and bid for hypothetical
liquidation. Thus the market spread is already counted. The displayed full-spread
fraction is `(ask-bid)/mid`; it must not be charged again. Each commission and
slippage assumption is applied once to its corresponding leg. Missing slippage
or fees produces an unknown economic result. FX remains separately unknown unless
supplied; quote-currency arithmetic must not be presented as an AUD-account result.

These files are versioned inputs. Do not revise an already used assumption in
place; add a new profile and preserve the original profile hash in each observation.

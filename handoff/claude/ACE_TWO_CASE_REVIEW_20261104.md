# Review of Ace's two-case package (GMX buyback, SUSHI mint)

Written 2026-11-04 by Claude, as requested in the package's `CLAUDE-REVIEW.md`. Package: `KOD-TWO-CASE-REVIEW.zip`
(owner upload). Three independent reviewers worked from the retained raw evidence only, without network access: one
per case, one on package integrity. Each decoded token amounts directly from the raw RPC receipts (ERC-20 Transfer
logs, recorded decimals) and re-ran Ace's offline audit scripts on a fresh copy. Structured output:
`ace-two-case-review.json`.

## Verdicts

| Admission | Verdict |
|---|---|
| GMX 2024 as a **funded repurchase / payment-flow** record (not an enlarged fee share, not a burn, not a buy signal) | **UPHELD WITH CAVEATS** |
| SUSHI 2 April 2026 as an **actual mint observation**, kept separate from the unproven December 2025 policy implementation | **UPHELD WITH CAVEATS** |
| Package integrity | **UPHELD**: 241/241 package files, 97/97 GMX and 106/106 SUSHI raw files, and all 70 per-request receipts match their sha256; `audit_chain.py` and `audit_distribution.py` reproduce the retained reviews exactly apart from `reviewed_at` |

## GMX: confirmed
- FeeHandler `0x7EB417637a3E6d1C19E6d69158c47610b7a5d9B3` deployment and GMX token identity.
- 25 Oct 2024, tx `0xa25c3e5d…`: 25 GMX into the FeeHandler for 566.648207 USDC, paid from the fee-buyback bucket after
  the same multicall claimed 1,161.125376 USDC of fees.
- 30 Oct 2024: 7,408 GMX withdrawn; 13,922.419287 GMX sent to the distributor; an actual claim of
  0.000121571506507967 GMX from the official ExtendedGmxTracker, cleanly separated from 0.036485528840690004 vested GMX
  (the two sum exactly to the restake).
- **Fee share unchanged, checked on-chain**: every V1 claim splits exactly 30/70 and every V2 claim 0.7297/0.2703
  (about 27% of V2 fees).
- New corroboration the package did not report: the distributor's rate set at 01:25:44 equals the funding spread over one
  week, and the release in the claim equals that rate times 179 seconds, exactly.

## GMX: caveats for Ace to fix
1. **Undisclosed second buyback executor.** In the package's own log query, 276 of 285 BuybackFees events come from
   `0x7cc506c8d711c2a17b61a75bd082d2514160baad`, not the FeeHandler (9 events). Both draw on the same fee bucket, and the
   program's buybacks started on 24 Oct, so the 25 Oct transaction is not the first. Identify this address.
2. **The cited first disclosure proposed a larger fee share.** The 20 July 2024 forum post proposed 100% of V1 fees for
   buybacks. That was never implemented, but "the original 2024 policy kept 30%/27%" rests only on the November
   activation article; say so.
3. **Not an open-market purchase.** The "buyback" is a keeper selling a GMX batch to the FeeHandler at the oracle price
   plus a configured 1.5000% premium. Net market buying depends on how keepers source GMX, and the premium is a cost
   to stakers.
4. **ETH payouts continued.** The sample claim also paid 0.000479866762049327 WETH from the legacy tracker, worth about
   400 times the GMX reward at the time.
5. **Possible address poisoning.** The outflow file shows 0-value transfers to the lookalike
   `0x986b053c1ddc6fac59fe095c2cb468a529c943aa`. The abbreviated distributor address in the reports matches both; use
   full addresses (real distributor `0x986b4e5a…43aa`).
6. Wording and gaps: "constructor GMX address agrees with the chain receipt" has no chain support (deploy input and
   `eth_getCode` were not retained); the binding Tally vote (30 Jul to 4 Aug 2024) is missing from the timeline; the
   fee receiver `0x43ce…` is an externally owned keeper account, so the receiver-to-distributor step is a manual transfer.

## SUSHI: confirmed
- SUSHIPOWAH links to SUSHI `0x6B35…0fE2`; Signal public by 7 Dec 2025; Implementation vote 14-21 Dec 2025 passed (5.214M
  For against a 5M quorum), raising the annual emission rate from 1.5% to "up to 5%".
- Tx `0x64c3dd1c…`, block 24,789,496, 2026-04-02 04:21:23 UTC: `deposit(125, 0)` minted 348,944.41692 SUSHI to the
  developer Safe and 3,489,444.1692 to MasterChef (exactly 1:10), total 3,838,388.58612. No SUSHI went to the caller.
- The legacy MasterChef code explains the split; nothing in the transaction establishes the 5% policy. Failed historical
  state calls are retained, and current supply is never used as a before/after figure.

## SUSHI: new evidence that strengthens the separation
1. **The accrual predates the vote.** The reward amount implies at least 1,062,171 blocks (about 148 days) of accrual,
   starting at or before about 4 Nov 2025, more than a month before the December vote. So this mint mostly reflects
   rewards accrued under the old setting.
2. **It is the only real mint in about 11 months.** The retained `zero-mint-logs.raw` shows the 2 April pair as the only
   non-zero SUSHI mint from about 13 Dec 2025 to Nov 2026 (194 zero-value rows), roughly 1.3% of supply. Annualising it
   from the vote date (about 4.8%) would be misleading, because the accrual started before the vote.
3. Pool 125's LP token has changed since the mint, consistent with the January 2026 LP-migration proposal, and unminted
   accrual is building up again.

## SUSHI: caveats for Ace to fix
- `REPORT.md` says "a reward claim can crystallise previously accrued rewards", but the caller received nothing: it was a
  zero-amount deposit that triggered a pool update. "1.5% prior ceiling" should read "1.5% current rate".
- `SUSHI-CEILING-ARITHMETIC.json` sets `actual_minting_observed` to null although a mint was observed.
- Provenance: `snapshot-original-proposal.json` is a re-serialised extract, not the captured bytes its receipt names
  (sha `275e25f3…` is absent); its content matches the fresh Snapshot fetch, so nothing material depends on it.
- Some contracts are only "partially verified" on Blockscout; the token-owner read used `latest` rather than a pinned block.

## Server receipts in the package
`CLOUD-START.json` and `CLOUD-END.json` show active timers, no halt and 527 tracked files intact at `dbb27ea5c` at
16:17 and 16:28 UTC. They are self-reported summaries: they cannot by themselves prove that nothing on the server changed.

## What this means for KOD
Both admissions are sound as **history**: what happened, when and to whom. Neither is a price test or a signal. The
reviewers' findings tighten the records: GMX's buybacks were mostly executed by a second, unidentified controller at an
oracle-plus-premium price, and SUSHI's mint mostly accrued before the policy it might be mistaken for. Any later price
test on this event family needs its own protocol with the feasibility gate (`docs/PROTOCOL_TEMPLATE.md`), and one GMX
policy episode is one event, not many.

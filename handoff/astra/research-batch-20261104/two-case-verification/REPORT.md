# KOD: two historical cases verified in parallel

4 November 2026. **Result: a real GMX fee-funded repurchase and reward-payment path is verified. Actual SUSHI issuance is also verified, but its attribution to the new emissions ceiling is not established.** These are completed historical mechanism checks. No price-return result, current trade or profitable edge is claimed.

## GMX — genuine repurchase and payout, unchanged fee entitlement

The original 2024 policy switched staker payouts from ETH/AVAX into purchased GMX. It kept the staker fee shares unchanged: 30% of V1 fees and 27% of V2 fees. The economic change was the purchase/payment flow, not a higher share of protocol revenue. The governance vote and the operational implementation have different dates.

| Verified step | Actual result |
|---|---|
| 2024 policy disclosure | The retained forum version was posted 20 July 2024. It refers to an earlier 2023 idea; this is not proof of the first-ever discussion |
| Snapshot vote | 24–28 July 2024, winning option buy back/distribute GMX |
| Governance execution | 7 August 2024; an empty operational payload, so this transaction alone does not prove implementation |
| Operational repurchase | Successful 25 October 2024 transaction transferred 25 GMX into the official FeeHandler and 566.648207 USDC to the counterparty |
| Program withdrawal | Successful 30 October 2024 transaction transferred 7,408 GMX from FeeHandler to the fee receiver |
| Reward funding and claim | Separate transactions show fee-receiver funding of the reward distributor, distributor funding of the GMX reward tracker, and a reward claim to a staking account contract followed by restaking through the official router. The detailed case retains exact amounts, addresses, times and receipts |

The program deals in fungible pooled tokens. The sample claim is evidence that the program paid rewards; it is not a trace of the exact 25 individual tokens through the pool.

**Admission decision:** include this episode in a historical **funded repurchase/payment-flow** register. Exclude it from any arm requiring an increase in stakers' fee percentage. Do not label repurchases as permanent burns. An investor holding an exchange spot product is not automatically a recipient of the protocol's staking distributions.

This distinction matters numerically: out of 100 units of V2 fees, the historical staker allocation stayed 27 units. Changing their payment asset does not by itself add another 27 units of holder income. Whether new native-token purchase demand produces a remaining price effect is still an empirical question.

## SUSHI — real mint, policy implementation unproven

An earlier Signal proposal was public by 7 December 2025. The Implementation proposal was created on 14 December and voting ended on 21 December. It authorized an annual ceiling of **up to 5%**, describing the prior ceiling as 1.5%, with discretionary deployment. The complete earlier policy history was not independently recovered. At the proposal's illustrative 285 million token base, additional annual headroom is 9.975 million tokens. That is ceiling arithmetic, not observed annual issuance.

On **2 April 2026 at 04:21:23 UTC**, a successful Ethereum transaction minted:

| Recipient | Newly minted SUSHI |
|---|---:|
| Developer address | 348,944.41692 |
| Legacy MasterChef reward contract | 3,489,444.1692 |
| **Total** | **3,838,388.58612** |

The transaction called `deposit(125, 0)` on the old MasterChef contract. Its mint split matches the legacy developer/reward path. A reward claim can crystallize previously accrued rewards; the receipt does not establish when all those rewards economically accrued or that a December 2025 governance change caused the mint.

**Admission decision:** include this as a verified **actual mint observation**. Do not admit it as a verified implementation of the new 5% policy or as a fresh governance dilution surprise. The proposal also does not establish an implemented buyback program. Neither a 5% ceiling nor this mint determines a 5% price loss.

Historical state calls were unavailable on the tested free RPC routes. Current total supply is not substituted for a before/after historical comparison. Receipt decoding establishes the observed mint; policy attribution remains a distinct unresolved claim.

## What has moved forward

- The GMX episode now has an observed operational purchase/payout chain and can enter the appropriate historical source register.
- The SUSHI record now separates a verified mint from an unverified policy attribution. It cannot silently enter the same source-event sample as a newly executed issuance policy.
- The two findings and exclusions are recorded as structured evidence. No price test is launched from one qualifying policy episode; transaction counts from the same program are not independent policy events.
- The next eligible expansion must use the same source standard across successes and failures: identify the prior economic arrangement, the new decision, actual funds or supply changes, beneficiaries, and all relevant clocks. This pass did not install a new recurring research service.

## Verification and limits

Two investigators worked in parallel; a third reviewer independently assessed the economics and decoded the retained chain evidence. The parent independently recomputed the Sushi mint sum and transaction/block bindings. Raw requests, successful and failed responses, source-code/deployment files and SHA-256 receipts are retained. Later payout-chain evidence has its own additive review.

On-chain evidence is read from public RPC responses, not an independently synchronized local node. Attempts to obtain a second provider's corroboration failed and are disclosed. Token amounts use recorded decimals; unavailable historical metadata/state calls are not replaced with fictional values. Source statements, actual chain events, and causal attribution remain distinct.

The 2026 GMX reward conditions differ from the 2024 episode. Current documentation does not retroactively establish the old rules, and the old successful payout does not promise a currently obtainable yield.

The existing cloud collector was checked during the work. Its timer and safeguard timer were active, there was no halt, and all 527 frozen source files matched. The dated start/end receipts accompany this report. The cloud collection continues independently.

## Direct evidence links

- GMX operational purchase: https://arbiscan.io/tx/0xa25c3e5d32e359e28400ab58363a07ed111066d04ef6b168489656ee38de0d3a
- GMX program withdrawal: https://arbiscan.io/tx/0xbe3198e192ce2b3146a8014e8ea627e8d6665280db53248a428e5a8a7f0056ae
- GMX source activation article: https://gmxio.substack.com/p/the-distribution-of-protocol-rewards
- SUSHI mint transaction: https://etherscan.io/tx/0x64c3dd1cf19b0267080fae868ae63d8ac2a59038573c6c62791a9a24ce823751
- SUSHI original policy vote: https://snapshot.box/#/s:sushigov.eth/proposal/0x9c4dd678c47020b2d308bb6876a9140f17f120c1b324727025703cb92186362e

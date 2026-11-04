# Cashflow and dilution source checks — actual first result

Decision: NEEDS_EVENT_VERIFICATION for H1 and H2. Public discovery data are accessible; an honest performance sample is not yet assembled. No token price-return test has been run for these hypotheses.

## Work completed
Two independent source investigations ran alongside the exchange-delisting work. The public Snapshot GraphQL endpoint worked from the Mac and the Singapore server. Nine candidate space identifiers were returned; exact official control/contract mapping is still incomplete. A separate bounded query retrieved 1,000 latest closed proposals across seven requested spaces. That capped, uneven sample is not the whole governance universe: Balancer alone accounts for 533 rows. Counts of 11 cashflow, 24 emissions and 22 treasury keyword candidates overlap and are only a discovery screen, not qualified economic events.

Three proposal bodies were inspected. None supplied the complete verified execution/identity evidence needed for the proposed implemented-change test. This is zero qualified cases among the inspected examples, not proof that no qualifying events exist in the universe.

| Inspected case | Evidence found | Research decision |
|---|---|---|
| GMX buyback/distribution proposal | Approved policy candidate; changes how fees purchase/distribute tokens | WATCH: connect exact prior policy, first disclosure, deployment and actual payments; no immediate current trade claim |
| Sushi emissions proposal | Approved increase from a 1.5% ceiling to up to 5%; conditional future buybacks also discussed | H2 candidate requiring implementation proof; reject the misleading interpretation that the mention of buybacks establishes a current funded buyback |
| Balancer winddown proposal | Mixed future redemption/winddown, with first redemption window described for May 2027 | Exclude from currently implemented, pure cash-distribution cohort; preserve as future, mixed-policy case |

## Why the lifecycle check changes the analysis
Snapshot's closed vote status is not a canonical execution record. Protocol-specific contract execution, amount, beneficiary and activation time must be joined. The same applies to tokens already held in a treasury: distribution is not necessarily new minting; repurchase is not necessarily burning; project revenue is not automatically a holder's cash claim.

A follow-up primary-source check also shows why old governance cards need version history. GMX's July 2024 proposal preceded a project article published on 4 November 2024 reporting distributions beginning 30 October 2024. Publication and stated activation are different dates. Its current documentation describes a later reward-policy change in March 2026. Those dates cannot be collapsed into one 'new bullish buyback' event today. The page claims are source leads, not independently checked chain transactions; no price outcomes were consulted for this follow-up.

## Next substantive acceptance gate
For a bounded source-assembly follow-up, complete one end-to-end H1 case and one H2 case: authoritative identity, latest prior policy, incremental economic change, earliest public disclosure, governance authority, successful execution and beneficiary/supply movement. Retain failures and compound policies. Then assess whether enough distinct, comparable events exist to justify a locked return study. Stop a lane if the needed historical evidence cannot be reconstructed; do not replace it with keyword sentiment or silently select only easily verified winners.

No new recurring service, paid data purchase, portfolio position or automated entry policy was created. These source checks do not amend the failed early-entry/listing studies or the existing cloud collector.

## Primary references and evidence
- Snapshot API: https://docs.snapshot.box/tools/api
- Aave lifecycle documentation: https://aave.com/docs/ecosystem/governance
- GMX original discussion: https://gov.gmx.io/t/gmx-transition-from-buyback-eth-and-distribute-eth-to-buyback-gmx-and-distribute-gmx/3693
- GMX project activation announcement: https://gmxio.substack.com/p/the-distribution-of-protocol-rewards
- GMX current rewards documentation: https://docs.gmx.io/docs/tokenomics/rewards/

Raw proposal/query receipts, source bodies, contract-identity checks and limitations are retained in the companion governance-preflight and governance-access evidence directories. The original exploratory 1,000-row request was not archived; the exact same bounded query was reissued and its second response is retained with that limitation disclosed. The original response has not been reconstructed or falsely attributed to the second retrieval.

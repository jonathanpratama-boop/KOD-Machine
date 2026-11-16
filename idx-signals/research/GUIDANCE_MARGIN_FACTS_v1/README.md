# Guidance-margin facts: offline development

This is an offline fact validator, revision journal and a one-call development reader adapter. It is **not an autonomous reader, a trading strategy, a launched experiment or evidence of profit**. Live development API calls have now been evaluated: the repaired version passed five controls but failed both complete real-disclosure pairs. The unattended reader remains on hold. See [the 16 November development evaluation](DEVELOPMENT_EVAL_20261116.md). The existing cloud timing study continues separately.

A [two-call stronger-model follow-up](MODEL_COMPARISON_20261116.md) improved real-number extraction, but neither complete source comparison passed. It did not change the reader code, expected facts or HOLD decision.

## Why this work exists

E10 already tested revenue-guidance revisions with costs, delayed entry and a funded account; its published result failed. The distinct question is whether a comparable change in forecast operating margin adds information beyond a revenue revision. A higher revenue forecast can coexist with weaker operating profit. That observation does not establish that the market missed it or that KOD can earn money from it.

The corrected source-only census used a predeclared hash sample of 40 issuers from E10's retained universe. We read 32 earnings releases and retained eight incomplete issuer histories. Two explicit as-reported revenue/operating-profit pairs were found: KTOS and RBBN. KTOS has an intervening acquisition; RBBN's complete latest-prior history remains provisional. ADEA's comparison derived from complete operating expenses is recorded separately, outside the strict numerator. None is an admitted live signal.

The earlier oldest-CIK sample (17 releases, zero pairs) was biased and did not justify closing the idea. The dated review/addenda preserve that correction. The corrected sample establishes existence and useful rejection cases, not a reliable arrival-rate estimate. No stock-price outcome was queried or used to select the sample.

## What is implemented

`idxsig.guidance_margin_facts.qualify(pair)` validates the documented input contract, binds numerical values to character spans in retained source excerpts, checks identities, fiscal periods, accounting definitions, consolidation perimeters and clocks, and computes midpoint conventions deterministically. Missing evidence never passes. Output is `FACTS_READY`, `MISSING`, `INCOMPARABLE` or `UNVERIFIED`; malformed or contradictory evidence raises an error.

`record_revision(record, path)` uses KOD's existing paper-chain format, file lock and atomic publication. It preserves every prior observation, rejects duplicate IDs/stale revisions and requires correction-known time to advance. Concurrent revisions of one head cannot both succeed.

External source authenticity, semantic binding and prior-history attestations are **trusted inputs**, not facts this validator independently proves. A model must not create its own verification flags. Exact numerical matching does not prove it read the right row or the source is genuine.

The four fixtures demonstrate provisional RBBN evidence, the KTOS acquisition mismatch, Mattel's accounting recast and one explicitly synthetic ready case. Only the synthetic case is ready; no historical receipt time was invented.

## Reproduce locally

From the repository root, in a Python environment with the existing IDX requirements installed:

```sh
PYTHONPATH=idx-signals python3 -m unittest discover -s idx-signals/tests -p test_guidance_margin_facts_independent.py -v
PYTHONPATH=idx-signals python3 -m idxsig.guidance_margin_facts --fixtures idx-signals/research/GUIDANCE_MARGIN_FACTS_v1/fixtures.json --out /tmp/kod-margin-facts-new-run
```

Use a new output directory for each rehearsal; existing artifacts are not overwritten. The CLI produces a report and an append-only fact ledger, with source/implementation hashes and explicit zero provider calls/orders. It does not generate forecasts or returns. The retained rehearsal binds the implementation version it used; a later formatting-only revision has its own validation receipt.

## Work still required before an unattended study

1. Demonstrate the actual registered disclosure feed on the cloud, retain its coverage/errors and actual receipt clocks, and define a reliable latest-comparable-prior procedure. Unknown earlier-publication time must not be substituted with an earnings-call time. Historical missing receipt does not block a future receipt-based design.
2. The dedicated OpenAI credential is installed privately and actual development calls have run. Reliable real-source extraction is still unresolved: complete tables, losses, acquisitions, adjusted definitions and missing histories need source-level qualification. The small supervised development check is not independent validation. No credential belongs in this repository.
3. Fix eligibility, the mechanical and fact-rich decisions, comparison baseline, common clock, executable price/cost assumptions and finite-account policy before any outcome test. Reuse existing account code. A fact-rich arm beating a revenue-only arm would not itself prove LLM superiority over another reader with the same facts.
4. Choose the evidence/review schedule from demonstrated event arrivals and relevant variability. The 2/32 source-discovery fraction is not a certified admission rate. Keep an inconclusive result possible.
5. Freeze the prospective protocol, independently test the full capture-to-account path, then add the new comparison to the existing dashboard and start its isolated job. None of those deployment steps has been claimed complete here.

The fact contract is development-versioned. It is not an RFC3161-frozen trading protocol. There is no new account engine, recurring model charge, new collector shutdown quota or real-money order.

## Development OpenAI adapter

`idxsig.guidance_margin_reader` builds a strict structured extraction request from source text alone, binds quoted numbers locally and preserves the first response and actual usage. The model cannot provide verification flags or change trusted source clocks/identity. Partial source excerpts may correctly produce missing facts. The adapter has no default model, scheduler, retries, trades or automatic env-file loading. See [READER_CONTRACT.md](READER_CONTRACT.md).

Prepare a request without calling the API:

```sh
PYTHONPATH=idx-signals python3 -m idxsig.guidance_margin_reader --fixtures idx-signals/research/GUIDANCE_MARGIN_FACTS_v1/fixtures.json --fixture-id rbbn-provisional-source-pair --model MODEL_SNAPSHOT_ID --out /tmp/kod-reader-prepared
```

A deliberate `--live` invocation makes at most one attempt using the process's OPENAI_API_KEY; it requires a different new output directory. Keep these private artifacts outside the public repository. A rejected, incomplete or failed response is retained, never silently replaced. Known missing source headers must be collected from complete source material before an extraction-quality claim can be made.

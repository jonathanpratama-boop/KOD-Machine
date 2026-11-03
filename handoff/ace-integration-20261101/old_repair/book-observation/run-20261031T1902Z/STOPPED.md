# Collector terminated by runtime network policy

The first scheduled set succeeded with three public books. The process survived
the agent's turn ending and attempted BTCUSDT in set 2 at 19:04:20 UTC. That call
recorded a connection-close URLError. The runtime then terminated the execution.
On checking its session, the tool returned:

`Unified exec process failed: Network access to "https://data-api.binance.vision:443" was blocked by policy.`

No collector or timeout process remained at the 19:06:48 UTC process check.
The old RUNNING status was a stale mid-set status, preserved verbatim in
`status-before-reconciliation.json`. Reconciled status and summary now say STOPPED.

Final evidence: 4 admitted attempts, 3 successful raw books, 1 failed sample,
176 missing scheduled samples. No network resumption, alternate host, escalation,
historical backfill or deadline extension was attempted. Missing-samples metadata
does not contain invented market observations. The three raw response hashes
were reverified. This is **not** a completed two-hour observation campaign.

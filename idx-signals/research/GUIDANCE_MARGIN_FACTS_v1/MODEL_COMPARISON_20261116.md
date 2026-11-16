# Stronger-model follow-up, 16 November 2026

**The unattended-reader decision remains HOLD.** A stronger model recovered more of the real source facts, but neither complete comparison passed the existing checks. This is a follow-up to the [two mini-model development passes](DEVELOPMENT_EVAL_20261116.md), whose failures and scores remain unchanged.

After those failures, two additional calls were specified before execution: `gpt-5.4-2026-03-05`, one attempt on each complete real-disclosure pair, using the same reader code at `0bfe4e21`, source packets, low reasoning effort and expected facts. No prompt or scoring criteria changed. This was a development comparison selected after seeing failures, not independent validation or a general model benchmark.

| Case | GPT-5.4 mini, repaired version | GPT-5.4 follow-up |
| --- | --- | --- |
| Ribbon | Wrong spread, omitted operating profit, reconstructed quotes; rejected | Main annual figures correctly identified, but spread references were ambiguous/not valid numeric tokens; rejected |
| Mattel | Profit ranges found, quotes rewritten, prior definition missing; rejected | Numeric ranges, missing revenue-level handling and basis labels passed exact source matching; prior definition still missing, so comparison incomplete |

Mattel passed all eight predeclared numeric/null/basis checks. It failed the ninth requirement: identifying both accounting definitions and the change between them. The current explanation did identify the amortization recast; the model abstained on the prior definition. This is better evidence extraction, not evidence of a comparable profit increase. Its bound candidate remains MISSING and cannot generate a signal.

Ribbon's response identified revenue midpoints of $814m and $825m, spreads of $7m and $15m, and GAAP losses of $18.8m and $9.8m. However, its current spread quote contains the same amount twice, once for the quarter and once for the year, and the submitted spread token includes `+/-` and a scale suffix. The local validator correctly refuses to choose a source occurrence or silently rewrite the answer. No successful automated Ribbon comparison is claimed.

Complete-case score: **0/2 for both models**. The main improvement is that the stronger model reads the figures and current accounting caveat more accurately. The remaining work is to use explicit source cell references and identify comparable accounting definitions; relaxing the evidence check would conceal the problem. Source acquisition was supervised, and complete prior histories and unattended arrival coverage are still unproved.

The two extra calls used 95,042 input and 2,557 output tokens, estimated at $0.27596 using the [published model rates](https://developers.openai.com/api/docs/models/gpt-5.4). Total for all three development passes: **16 calls, approximately $0.4631**, excluding the earlier connection test. These are estimated list-price usage amounts, not invoice charges. No recurring job or new trading experiment was enabled.

[Machine-readable plan and result](MODEL_COMPARISON_20261116.json) retains the same expected-source hash, code hash, model, usage, response hashes and actual receipt times. Full requests, first responses and candidate remain in the owner's local evaluation directory. All code is unchanged from the 61-test repair; this follow-up adds evidence only.

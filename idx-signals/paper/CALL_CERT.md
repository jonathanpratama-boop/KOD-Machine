# Certified dump calls (shadow, beside LEARNER v2.4)

Generated 2026-11-12T23:01:21Z from paper/learner_v3.jsonl and the registers. Method and history check: `research/CALL_CERT_v1` (the certificate held on 2023: 44 calls, right 70.5%). This report changes nothing in v2.4.

## The three plain answers

- **What is predicted:** for a US stock that just closed +30% or more, that it closes at least 10% lower at the next session while most of its twins do not. A call is made only when the shadow score clears a bar certified by Learn then Test.
- **What counts as success:** the calls are wrong at most half the time (certified level 50%, confidence 95%); the realised losing rate stays at or under it.
- **Evidence so far:** 131 live forecasts, 18 calls, 5 wrong of 13 (38.5%); p that the true rate exceeds 50%: 0.867.

## The bar

- From history alone (2022 and 2023 scores of models that never saw those years, 2599 events): threshold 0.555.
- Each live forecast uses the bar certified from history plus every live outcome resolved before it was made; the bar moves as outcomes resolve (the history check found the 2022 bar fired 3.1% of 2023's events, not 1%).
- 2023 on its own does not certify (strictest 1%: 15 calls, 4 wrong, p 0.059 against 0.05); pooled with 2022 it does, at about the top 5% of spikes. Expect few calls.

## Live forecasts

| Signal session | Ticker | Shadow score | Bar | Call | v2.4 raw | Outcome |
|---|---|---|---|---|---|---|
| 2026-11-12 | XLAB | 0.536 | 0.557 | - | 0.279 | pending |
| 2026-11-12 | TGHL | 0.396 | 0.557 | - | 0.169 | pending |
| 2026-11-12 | TGEN | 0.369 | 0.557 | - | 0.136 | pending |
| 2026-11-12 | RIME | 0.394 | 0.557 | - | 0.150 | pending |
| 2026-11-12 | POAS | 0.645 | 0.557 | **DUMP** | 0.317 | pending |
| 2026-11-12 | PLCE | 0.445 | 0.557 | - | 0.278 | pending |
| 2026-11-12 | PARA | 0.433 | 0.557 | - | 0.287 | pending |
| 2026-11-12 | ICMB | 0.440 | 0.557 | - | 0.160 | pending |
| 2026-11-12 | GP | 0.505 | 0.557 | - | 0.246 | pending |
| 2026-11-12 | DBGI | 0.524 | 0.557 | - | 0.349 | pending |
| 2026-11-12 | BGIN | 0.477 | 0.557 | - | 0.161 | pending |
| 2026-11-12 | ARAI | 0.695 | 0.557 | **DUMP** | 0.329 | pending |
| 2026-11-12 | AIMD | 0.576 | 0.557 | **DUMP** | 0.223 | pending |
| 2026-11-12 | ADXN | 0.470 | 0.557 | - | 0.185 | pending |
| 2026-11-12 | ADVB | 0.407 | 0.557 | - | 0.168 | pending |
| 2026-11-11 | WHLR | 0.701 | 0.557 | **DUMP** | 0.410 | dumped |
| 2026-11-11 | TANH | 0.382 | 0.557 | - | 0.161 | did not dump |
| 2026-11-11 | SLXN | 0.665 | 0.557 | **DUMP** | 0.315 | dumped |
| 2026-11-11 | SHFS | 0.568 | 0.557 | **DUMP** | 0.405 | pending |
| 2026-11-11 | SFWL | 0.339 | 0.557 | - | 0.140 | did not dump |
| 2026-11-11 | SCKT | 0.440 | 0.557 | - | 0.175 | pending |
| 2026-11-11 | RKDA | 0.431 | 0.557 | - | 0.167 | did not dump |
| 2026-11-11 | RETO | 0.516 | 0.557 | - | 0.368 | did not dump |
| 2026-11-11 | REED | 0.294 | 0.557 | - | 0.077 | did not dump |
| 2026-11-11 | OPTT | 0.472 | 0.557 | - | 0.251 | pending |
| 2026-11-11 | NWTG | 0.301 | 0.557 | - | 0.101 | did not dump |
| 2026-11-11 | NCT | 0.412 | 0.557 | - | 0.246 | did not dump |
| 2026-11-11 | GOVX | 0.711 | 0.557 | **DUMP** | 0.361 | did not dump |
| 2026-11-11 | GEVO | 0.245 | 0.557 | - | 0.084 | did not dump |
| 2026-11-11 | ELOG | 0.389 | 0.557 | - | 0.136 | did not dump |
| 2026-11-11 | CANG | 0.375 | 0.557 | - | 0.144 | did not dump |
| 2026-11-11 | BURU | 0.575 | 0.557 | **DUMP** | 0.332 | dumped |
| 2026-11-11 | BSEM | 0.371 | 0.557 | - | 0.160 | dumped |
| 2026-11-11 | BGS | 0.268 | 0.557 | - | 0.078 | did not dump |
| 2026-11-10 | ZIP | 0.296 | 0.557 | - | 0.111 | dumped |
| 2026-11-10 | TTEC | 0.387 | 0.557 | - | 0.154 | did not dump |
| 2026-11-10 | TREO | 0.346 | 0.557 | - | 0.178 | did not dump |
| 2026-11-10 | TANH | 0.490 | 0.557 | - | 0.304 | did not dump |
| 2026-11-10 | SMX | 0.385 | 0.557 | - | 0.259 | dumped |
| 2026-11-10 | PXLW | 0.405 | 0.557 | - | 0.171 | dumped |
| 2026-11-10 | PEPG | 0.461 | 0.557 | - | 0.256 | did not dump |
| 2026-11-10 | NNOX | 0.304 | 0.557 | - | 0.158 | did not dump |
| 2026-11-10 | NCI | 0.430 | 0.557 | - | 0.327 | dumped |
| 2026-11-10 | MNDO | 0.378 | 0.557 | - | 0.160 | did not dump |
| 2026-11-10 | MI | 0.472 | 0.557 | - | 0.309 | pending |
| 2026-11-10 | LGVN | 0.365 | 0.557 | - | 0.189 | did not dump |
| 2026-11-10 | INLF | 0.642 | 0.557 | **DUMP** | 0.487 | did not dump |
| 2026-11-10 | ESLA | 0.531 | 0.557 | - | 0.306 | did not dump |
| 2026-11-10 | AACG | 0.398 | 0.557 | - | 0.180 | did not dump |
| 2026-11-09 | XHLD | 0.360 | 0.557 | - | 0.337 | did not dump |
| 2026-11-09 | WOK | 0.348 | 0.557 | - | 0.295 | did not dump |
| 2026-11-09 | UG | 0.233 | 0.557 | - | 0.165 | did not dump |
| 2026-11-09 | TVRD | 0.431 | 0.557 | - | 0.321 | did not dump |
| 2026-11-09 | TOPS | 0.611 | 0.557 | **DUMP** | 0.479 | did not dump |
| 2026-11-09 | TLS | 0.217 | 0.557 | - | 0.165 | did not dump |
| 2026-11-09 | TANH | 0.425 | 0.557 | - | 0.357 | did not dump |
| 2026-11-09 | OMH | 0.574 | 0.557 | **DUMP** | 0.494 | dumped |
| 2026-11-09 | NCPL | 0.250 | 0.557 | - | 0.212 | did not dump |
| 2026-11-09 | MODD | 0.147 | 0.557 | - | 0.143 | did not dump |
| 2026-11-09 | MF | 0.316 | 0.557 | - | 0.313 | did not dump |
| 2026-11-09 | JZ | 0.345 | 0.557 | - | 0.323 | did not dump |
| 2026-11-09 | INLF | 0.438 | 0.557 | - | 0.396 | did not dump |
| 2026-11-09 | GPUS | 0.304 | 0.557 | - | 0.285 | pending |
| 2026-11-09 | GFR | 0.160 | 0.557 | - | 0.151 | did not dump |
| 2026-11-09 | FJET | 0.245 | 0.557 | - | 0.227 | dumped |
| 2026-11-09 | FISN | 0.304 | 0.557 | - | 0.281 | dumped |
| 2026-11-09 | ESLA | 0.384 | 0.557 | - | 0.361 | did not dump |
| 2026-11-09 | DCTH | 0.243 | 0.557 | - | 0.170 | did not dump |
| 2026-11-09 | CVKD | 0.303 | 0.557 | - | 0.266 | did not dump |
| 2026-11-09 | CKX | 0.433 | 0.557 | - | 0.326 | did not dump |
| 2026-11-09 | AKBA | 0.244 | 0.557 | - | 0.218 | did not dump |
| 2026-11-06 | VSA | 0.349 | 0.557 | - | 0.168 | did not dump |
| 2026-11-06 | VIVK | 0.438 | 0.557 | - | 0.290 | dumped |
| 2026-11-06 | VAI | 0.291 | 0.557 | - | 0.145 | did not dump |
| 2026-11-06 | STAK | 0.383 | 0.557 | - | 0.202 | did not dump |
| 2026-11-06 | SNT | 0.326 | 0.557 | - | 0.158 | did not dump |
| 2026-11-06 | SMX | 0.395 | 0.557 | - | 0.228 | pending |
| 2026-11-06 | SKIN | 0.306 | 0.557 | - | 0.150 | did not dump |
| 2026-11-06 | SERV | 0.192 | 0.557 | - | 0.102 | did not dump |
| 2026-11-06 | SDA | 0.415 | 0.557 | - | 0.201 | pending |
| 2026-11-06 | RDGT | 0.318 | 0.557 | - | 0.142 | did not dump |
| 2026-11-06 | RCT | 0.448 | 0.557 | - | 0.253 | pending |
| 2026-11-06 | POM | 0.395 | 0.557 | - | 0.218 | dumped |
| 2026-11-06 | OPTU | 0.266 | 0.557 | - | 0.144 | did not dump |
| 2026-11-06 | OBX | 0.292 | 0.557 | - | 0.164 | did not dump |
| 2026-11-06 | MTVA | 0.285 | 0.557 | - | 0.137 | did not dump |
| 2026-11-06 | KRMN | 0.162 | 0.557 | - | 0.095 | did not dump |
| 2026-11-06 | KDK | 0.234 | 0.557 | - | 0.139 | did not dump |
| 2026-11-06 | INDI | 0.184 | 0.557 | - | 0.108 | did not dump |
| 2026-11-06 | HTCO | 0.362 | 0.557 | - | 0.188 | dumped |
| 2026-11-06 | HPAI | 0.459 | 0.557 | - | 0.228 | did not dump |
| 2026-11-06 | GOGO | 0.348 | 0.557 | - | 0.176 | did not dump |
| 2026-11-06 | GIBO | 0.265 | 0.557 | - | 0.139 | did not dump |
| 2026-11-06 | FROG | 0.150 | 0.557 | - | 0.083 | did not dump |
| 2026-11-06 | FLY | 0.269 | 0.557 | - | 0.144 | did not dump |
| 2026-11-06 | CIIT | 0.349 | 0.557 | - | 0.164 | did not dump |
| 2026-11-06 | CABR | 0.407 | 0.557 | - | 0.196 | did not dump |
| 2026-11-05 | ZNB | 0.505 | 0.557 | - | 0.221 | did not dump |
| 2026-11-05 | XXII | 0.675 | 0.557 | **DUMP** | 0.355 | dumped |
| 2026-11-05 | VXX | 0.329 | 0.557 | - | 0.112 | did not dump |
| 2026-11-05 | PLCE | 0.361 | 0.557 | - | 0.142 | pending |
| 2026-11-05 | LABT | 0.640 | 0.557 | **DUMP** | 0.333 | pending |
| 2026-11-05 | JDZG | 0.388 | 0.557 | - | 0.151 | dumped |
| 2026-11-05 | HTCR | 0.372 | 0.557 | - | 0.126 | dumped |
| 2026-11-05 | FLYE | 0.339 | 0.557 | - | 0.148 | did not dump |
| 2026-11-05 | DNUT | 0.363 | 0.557 | - | 0.130 | did not dump |
| 2026-11-05 | BDMD | 0.420 | 0.557 | - | 0.154 | pending |
| 2026-11-05 | APP | 0.256 | 0.557 | - | 0.087 | did not dump |
| 2026-11-05 | AMTX | 0.327 | 0.557 | - | 0.131 | did not dump |
| 2026-11-05 | AEHL | 0.655 | 0.557 | **DUMP** | 0.303 | dumped |
| 2026-10-30 | WHLR | 0.601 | 0.555 | **DUMP** | 0.623 | dumped |
| 2026-10-30 | SLGB | 0.378 | 0.555 | - | 0.519 | did not dump |
| 2026-10-30 | SGRX | 0.446 | 0.555 | - | 0.581 | did not dump |
| 2026-10-30 | ONEG | 0.516 | 0.555 | - | 0.609 | did not dump |
| 2026-10-30 | OMEX | 0.626 | 0.555 | **DUMP** | 0.700 | did not dump |
| 2026-10-30 | MASK | 0.521 | 0.555 | - | 0.631 | dumped |
| 2026-10-30 | GDYN | 0.333 | 0.555 | - | 0.466 | did not dump |
| 2026-10-30 | FMC | 0.255 | 0.555 | - | 0.382 | did not dump |
| 2026-10-30 | CHOW | 0.562 | 0.555 | **DUMP** | 0.681 | did not dump |
| 2026-10-30 | ATYR | 0.548 | 0.555 | - | 0.651 | did not dump |
| 2026-10-30 | ASUR | 0.301 | 0.555 | - | 0.430 | did not dump |
| 2026-10-29 | XCH | 0.336 | 0.555 | - | 0.507 | did not dump |
| 2026-10-29 | SGLY | 0.454 | 0.555 | - | 0.575 | pending |
| 2026-10-29 | PCLA | 0.479 | 0.555 | - | 0.599 | dumped |
| 2026-10-29 | NCPL | 0.303 | 0.555 | - | 0.423 | dumped |
| 2026-10-29 | KPLT | 0.336 | 0.555 | - | 0.498 | dumped |
| 2026-10-29 | JFIN | 0.342 | 0.555 | - | 0.499 | did not dump |
| 2026-10-29 | INLF | 0.740 | 0.555 | **DUMP** | 0.744 | dumped |
| 2026-10-29 | GKOS | 0.204 | 0.555 | - | 0.357 | did not dump |
| 2026-10-29 | BURU | 0.413 | 0.555 | - | 0.528 | dumped |
| 2026-10-29 | ADT | 0.177 | 0.555 | - | 0.384 | did not dump |

## Limits

- The bound treats events as independent; spikes cluster, so it is optimistic, and the realised rate is the check.
- History prices are survivor-only; the live record is the honest one.
- A shadow report: no order, no change to the frozen challenger.

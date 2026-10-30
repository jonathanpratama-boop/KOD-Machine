# RECENT_REPLAY_v1: result (one run, 2026-10-30)

Protocol `protocol.json` (frozen 2026-10-30T08:05:57Z), `PROTOCOL.md`. LEARNER v2.4 replayed session by session over the US +30% spikes of 2026-04-01..2026-10-28: 1718 events on 146 sessions, 3392 graded pairs. Every number is in `results/RESULT.json`; every forecast and outcome in `results/forecasts.csv.gz`.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not?

**What counts as success?** The registered bar of the live test: the forecasts rank the dumpers above the others with z >= 3.75 at the first look of 250 pairs (30 sessions), 3.0 at the later looks.

**What is the evidence?** 1718 next-session outcomes over 146 sessions: AUC 0.623 (benchmark 0.587), se 0.016, z 7.48, look 1000. **Verdict: SKILL at the n>=1000 look (z 7.48 >= 3.0).**

## Headline: the next-session dump

| | v2.4 raw | benchmark |
|---|---|---|
| AUC | 0.623 | 0.587 |
| Brier gain over the base rate | +0.0118 (se 0.0033, 146 blocks) | +0.0073 (se 0.0023, 146 blocks) |
| Brier gain of v2.4 over the benchmark | +0.0045 (se 0.0024, 146 blocks) | |

Base rate of the statement (own dump at the next session): 38.3% of 1718; raw next-session dump (any, twins aside): 38.3%.

### By month

| month | pairs | own-dump rate | AUC |
|---|---:|---:|---:|
| 2026-04 | 260 | 35.8% | 0.510 |
| 2026-05 | 312 | 32.4% | 0.593 |
| 2026-06 | 293 | 43.0% | 0.595 |
| 2026-07 | 197 | 46.2% | 0.616 |
| 2026-08 | 251 | 36.3% | 0.721 |
| 2026-09 | 211 | 41.7% | 0.647 |
| 2026-10 | 194 | 35.1% | 0.696 |

## Companion: the 5-session plan ends 10% down

1674 graded (ungraded 44: window still open or no entry); own-dump rate 46.7%; AUC 0.610 (benchmark 0.597); Brier gain over the base rate +0.0084 (se 0.0027, 30 blocks), over the benchmark +0.0033 (se 0.0022, 30 blocks).

## Certified next-day dump calls (idxsig.call_cert)

182 calls on 1718 events (10.6%), 182 graded: 83 wrong, losing rate 45.6% against the certified 50% (exact binomial p that a true losing rate of 50% or worse gives this few or fewer: 0.133).

| ticker | session | score | bar | dumped |
|---|---|---:|---:|---|
| KRSA | 2026-04-01 | 0.632 | 0.555 | no |
| AIXI | 2026-04-06 | 0.590 | 0.555 | no |
| HCAI | 2026-04-07 | 0.569 | 0.555 | no |
| AFJK | 2026-04-09 | 0.566 | 0.555 | yes |
| VSA | 2026-04-09 | 0.667 | 0.555 | yes |
| FUSE | 2026-04-10 | 0.567 | 0.555 | no |
| RECT | 2026-04-13 | 0.597 | 0.556 | yes |
| AXNX | 2026-04-14 | 0.629 | 0.556 | yes |
| SNAL | 2026-04-14 | 0.688 | 0.556 | yes |
| BIRD | 2026-04-15 | 0.643 | 0.556 | yes |
| QH | 2026-04-15 | 0.573 | 0.556 | no |
| MYSE | 2026-04-16 | 0.625 | 0.557 | no |
| PBM | 2026-04-16 | 0.615 | 0.557 | no |
| WNW | 2026-04-16 | 0.617 | 0.557 | no |
| EFOI | 2026-04-17 | 0.688 | 0.557 | yes |
| AKAN | 2026-04-22 | 0.664 | 0.558 | no |
| FIRY | 2026-04-23 | 0.611 | 0.558 | yes |
| QH | 2026-04-27 | 0.690 | 0.559 | no |
| YAAS | 2026-04-27 | 0.682 | 0.559 | yes |
| ATER | 2026-04-28 | 0.564 | 0.558 | no |
| CNSP | 2026-05-04 | 0.597 | 0.559 | no |
| RNTZ | 2026-05-04 | 0.762 | 0.559 | yes |
| EVC | 2026-05-06 | 0.564 | 0.559 | no |
| STFS | 2026-05-06 | 0.683 | 0.559 | no |
| AEHL | 2026-05-08 | 0.571 | 0.560 | no |
| ASBP | 2026-05-11 | 0.643 | 0.559 | no |
| JZXN | 2026-05-11 | 0.576 | 0.559 | yes |
| SMX | 2026-05-11 | 0.579 | 0.559 | yes |
| WOK | 2026-05-11 | 0.737 | 0.559 | no |
| AIIO | 2026-05-13 | 0.577 | 0.560 | no |
| FCHL | 2026-05-13 | 0.611 | 0.560 | no |
| QUCY | 2026-05-13 | 0.726 | 0.560 | no |
| TDIC | 2026-05-13 | 0.680 | 0.560 | yes |
| AIIO | 2026-05-14 | 0.629 | 0.560 | yes |
| FCHL | 2026-05-14 | 0.621 | 0.560 | yes |
| HCWB | 2026-05-15 | 0.600 | 0.562 | no |
| RNTZ | 2026-05-15 | 0.598 | 0.562 | no |
| TDIC | 2026-05-15 | 0.690 | 0.562 | yes |
| AIIO | 2026-05-18 | 0.626 | 0.563 | yes |
| GOVX | 2026-05-18 | 0.583 | 0.563 | no |
| GIPR | 2026-05-19 | 0.577 | 0.564 | no |
| INM | 2026-05-19 | 0.591 | 0.564 | no |
| NCPL | 2026-05-21 | 0.596 | 0.565 | no |
| QTEX | 2026-05-22 | 0.583 | 0.564 | no |
| AIMD | 2026-05-26 | 0.621 | 0.564 | yes |
| ASTC | 2026-05-27 | 0.716 | 0.564 | no |
| RKTO | 2026-05-27 | 0.566 | 0.564 | no |
| PRFX | 2026-05-29 | 0.629 | 0.565 | yes |
| ABTS | 2026-06-01 | 0.605 | 0.564 | no |
| AIM | 2026-06-01 | 0.581 | 0.564 | no |
| BDAI | 2026-06-01 | 0.704 | 0.564 | yes |
| TGHL | 2026-06-01 | 0.687 | 0.564 | yes |
| DXST | 2026-06-02 | 0.687 | 0.564 | no |
| LASE | 2026-06-02 | 0.620 | 0.564 | no |
| ATPC | 2026-06-03 | 0.575 | 0.565 | yes |
| SOAR | 2026-06-03 | 0.598 | 0.565 | yes |
| XOS | 2026-06-03 | 0.702 | 0.565 | yes |
| STI | 2026-06-04 | 0.749 | 0.566 | no |
| VERU | 2026-06-04 | 0.618 | 0.566 | yes |
| SPHL | 2026-06-05 | 0.703 | 0.567 | yes |
| BYAH | 2026-06-08 | 0.686 | 0.568 | yes |
| INHD | 2026-06-08 | 0.764 | 0.568 | no |
| ITOC | 2026-06-08 | 0.650 | 0.568 | yes |
| MTEN | 2026-06-08 | 0.696 | 0.568 | yes |
| NPT | 2026-06-08 | 0.782 | 0.568 | yes |
| SUNE | 2026-06-08 | 0.738 | 0.568 | yes |
| CCTG | 2026-06-09 | 0.698 | 0.568 | yes |
| CHAI | 2026-06-09 | 0.597 | 0.568 | yes |
| BDAI | 2026-06-10 | 0.693 | 0.545 | no |
| CHOW | 2026-06-10 | 0.584 | 0.545 | yes |
| CIIT | 2026-06-10 | 0.586 | 0.545 | no |
| CPOP | 2026-06-10 | 0.582 | 0.545 | yes |
| DSS | 2026-06-10 | 0.585 | 0.545 | yes |
| DSY | 2026-06-10 | 0.785 | 0.545 | yes |
| FCDH | 2026-06-10 | 0.640 | 0.545 | yes |
| STI | 2026-06-10 | 0.612 | 0.545 | no |
| YFOR | 2026-06-10 | 0.587 | 0.545 | yes |
| ESYN | 2026-06-11 | 0.553 | 0.545 | no |
| GELS | 2026-06-11 | 0.654 | 0.545 | yes |
| MTEN | 2026-06-11 | 0.633 | 0.545 | no |
| FCDH | 2026-06-12 | 0.562 | 0.547 | no |
| FCDH | 2026-06-15 | 0.577 | 0.547 | yes |
| MTEN | 2026-06-15 | 0.679 | 0.547 | no |
| PRFX | 2026-06-15 | 0.602 | 0.547 | yes |
| RGNT | 2026-06-15 | 0.666 | 0.547 | yes |
| AHMA | 2026-06-16 | 0.584 | 0.547 | no |
| CAST | 2026-06-17 | 0.554 | 0.549 | no |
| EHGO | 2026-06-17 | 0.608 | 0.549 | yes |
| EHGO | 2026-06-22 | 0.551 | 0.549 | no |
| BOLD | 2026-06-23 | 0.579 | 0.549 | no |
| AZI | 2026-06-29 | 0.574 | 0.549 | yes |
| CIRC | 2026-06-29 | 0.564 | 0.549 | yes |
| UPC | 2026-06-29 | 0.575 | 0.549 | yes |
| FXHO | 2026-07-01 | 0.565 | 0.549 | yes |
| LHAI | 2026-07-01 | 0.712 | 0.549 | yes |
| VEEE | 2026-07-13 | 0.691 | 0.547 | no |
| JTAI | 2026-07-15 | 0.691 | 0.548 | yes |
| ZYBT | 2026-07-20 | 0.669 | 0.547 | yes |
| CPHI | 2026-07-21 | 0.785 | 0.547 | yes |
| INLF | 2026-07-22 | 0.591 | 0.547 | no |
| PN | 2026-07-22 | 0.709 | 0.547 | no |
| ZCMD | 2026-07-22 | 0.595 | 0.547 | yes |
| ZYBT | 2026-07-23 | 0.633 | 0.548 | no |
| STAK | 2026-07-24 | 0.590 | 0.549 | yes |
| BIYA | 2026-07-28 | 0.553 | 0.549 | no |
| STKH | 2026-07-28 | 0.626 | 0.549 | yes |
| DFNS | 2026-07-29 | 0.580 | 0.549 | no |
| CYCU | 2026-07-30 | 0.689 | 0.549 | yes |
| DFNS | 2026-07-30 | 0.556 | 0.549 | yes |
| MF | 2026-07-30 | 0.557 | 0.549 | no |
| YAAS | 2026-07-30 | 0.705 | 0.549 | no |
| FCUV | 2026-07-31 | 0.789 | 0.549 | no |
| FMFC | 2026-07-31 | 0.711 | 0.549 | yes |
| DFNS | 2026-08-03 | 0.565 | 0.551 | yes |
| HYFM | 2026-08-03 | 0.721 | 0.551 | yes |
| AMIX | 2026-08-04 | 0.640 | 0.551 | yes |
| YXT | 2026-08-05 | 0.725 | 0.552 | yes |
| CELZ | 2026-08-06 | 0.571 | 0.552 | no |
| WYHG | 2026-08-06 | 0.580 | 0.552 | yes |
| XHLD | 2026-08-06 | 0.731 | 0.552 | yes |
| MB | 2026-08-07 | 0.624 | 0.552 | yes |
| YJ | 2026-08-07 | 0.741 | 0.552 | yes |
| JWEL | 2026-08-10 | 0.672 | 0.552 | no |
| SCKT | 2026-08-10 | 0.694 | 0.552 | yes |
| PLAG | 2026-08-11 | 0.791 | 0.553 | yes |
| BQ | 2026-08-12 | 0.599 | 0.553 | no |
| FGI | 2026-08-13 | 0.623 | 0.553 | yes |
| XHG | 2026-08-13 | 0.731 | 0.553 | no |
| MDXH | 2026-08-14 | 0.587 | 0.553 | no |
| SXTC | 2026-08-14 | 0.630 | 0.553 | yes |
| WETO | 2026-08-14 | 0.587 | 0.553 | no |
| IPST | 2026-08-17 | 0.751 | 0.553 | no |
| FFR | 2026-08-18 | 0.570 | 0.554 | no |
| IPST | 2026-08-18 | 0.590 | 0.554 | yes |
| PFSA | 2026-08-18 | 0.757 | 0.554 | yes |
| PSIG | 2026-08-18 | 0.567 | 0.554 | no |
| SXTC | 2026-08-18 | 0.660 | 0.554 | yes |
| WETO | 2026-08-18 | 0.556 | 0.554 | yes |
| IPDN | 2026-09-14 | 0.571 | 0.555 | no |
| MEDS | 2026-09-15 | 0.606 | 0.555 | no |
| RETO | 2026-09-15 | 0.730 | 0.555 | yes |
| VEEA | 2026-09-15 | 0.568 | 0.555 | no |
| DLXY | 2026-09-16 | 0.770 | 0.555 | yes |
| MEDS | 2026-09-16 | 0.593 | 0.555 | yes |
| AEMD | 2026-09-17 | 0.683 | 0.555 | no |
| DTSS | 2026-09-17 | 0.684 | 0.555 | yes |
| GIPR | 2026-09-18 | 0.596 | 0.556 | no |
| MRNO | 2026-09-18 | 0.576 | 0.556 | no |
| QNME | 2026-09-18 | 0.668 | 0.556 | no |
| REFR | 2026-09-18 | 0.581 | 0.556 | no |
| GLND | 2026-09-21 | 0.590 | 0.556 | yes |
| JAGX | 2026-09-22 | 0.704 | 0.557 | yes |
| BFRG | 2026-09-23 | 0.572 | 0.556 | yes |
| VSA | 2026-09-23 | 0.607 | 0.556 | yes |
| WHLR | 2026-09-23 | 0.558 | 0.556 | yes |
| PMAX | 2026-09-24 | 0.639 | 0.557 | no |
| WETO | 2026-09-24 | 0.561 | 0.557 | no |
| FFTT | 2026-09-25 | 0.664 | 0.557 | yes |
| INLF | 2026-09-25 | 0.568 | 0.557 | no |
| TDIC | 2026-09-25 | 0.574 | 0.557 | yes |
| WHLR | 2026-09-25 | 0.604 | 0.557 | yes |
| KNRX | 2026-09-28 | 0.759 | 0.557 | yes |
| FFTT | 2026-09-29 | 0.568 | 0.558 | no |
| TGE | 2026-09-30 | 0.654 | 0.558 | no |
| MI | 2026-10-05 | 0.666 | 0.558 | yes |
| OLB | 2026-10-06 | 0.612 | 0.558 | no |
| WFF | 2026-10-09 | 0.740 | 0.558 | no |
| LNKS | 2026-10-12 | 0.600 | 0.558 | yes |
| MNDR | 2026-10-12 | 0.599 | 0.558 | yes |
| WFF | 2026-10-12 | 0.582 | 0.558 | yes |
| FLYE | 2026-10-13 | 0.559 | 0.558 | no |
| JBDI | 2026-10-13 | 0.693 | 0.558 | yes |
| TCRT | 2026-10-13 | 0.579 | 0.558 | yes |
| NIVF | 2026-10-14 | 0.652 | 0.558 | yes |
| SXTC | 2026-10-19 | 0.743 | 0.559 | yes |
| POM | 2026-10-21 | 0.605 | 0.559 | yes |
| WHLR | 2026-10-21 | 0.742 | 0.559 | yes |
| XHLD | 2026-10-21 | 0.573 | 0.559 | yes |
| VIVK | 2026-10-22 | 0.561 | 0.559 | yes |
| CHOW | 2026-10-26 | 0.592 | 0.530 | no |
| NUWE | 2026-10-27 | 0.765 | 0.530 | no |
| PARA | 2026-10-28 | 0.663 | 0.530 | no |

## What it does not show

- A live record: the forecasts were replayed, not sealed that evening; the live ledger (paper/learner_v3.jsonl) stays the only prospective record and its registered looks stand.
- Names delisted between the range and 2026-10-30 are absent (survivorship); the twins and the breadth and market features come from this pull's frame (see PROTOCOL.md).
- Nothing here changes v2.4; a later version is tested on live data or on a period sealed from now on.

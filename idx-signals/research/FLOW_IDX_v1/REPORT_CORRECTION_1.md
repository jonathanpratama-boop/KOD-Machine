# FLOW_IDX_v1 report correction 1 (2026-10-26)

REPORT.md and every file in `stage1/` stand as produced; one sentence of the report was too strong.

REPORT.md says the cells with lift above 2 are all "block share in the bottom tail", at 2.1 to 4.0 times chance.
Exactly: 13 cells have lift >= 2 and a significant lower bound (G1 and G2). 12 are low block share (blk5, blk20, most for
fast rises); one is low foreign participation (fpart20 bottom, hot names, lead 5, lift 2.04). Lifts run from 2.04 to
4.63; the matching falls run from 0.88 to 3.57.

Two of the 13 look directional: IDX blk5 bottom at lead 3 (lift 4.04 against 0.88 for fast falls) and at lead 20 (3.27
against 1.09). Both pass G1, G2, G3, G4 and G6 and fail G5: the summed expectation is 3.2 and 4.3 (10 needed) and the
observed count is about 13 and 14 events. A "no block trading" state in a handful of events, not a result. The
verdict (NO_FLOW_LEAD) is unchanged.

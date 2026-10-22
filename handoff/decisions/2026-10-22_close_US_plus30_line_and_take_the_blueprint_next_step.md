# Decision 2026-10-22 (owner's instruction, applied): close the US "+30% day" buy line, and take the Blueprint's next step

Owner's words: "Look at the instruction and plan, whats the architect's next plan? Apply that."

Plan read: `handoff/BLUEPRINT.md`, "Open decisions and the next step" (2026-10-17): "close the +30% line, and archive the data inputs before anything else. Then either stop, or
test one US signal that may come before the move, frozen in advance like the others. My pick is insider buying reported to the SEC on Form 4." No document in the repository is
labelled "architect"; this is the plan of record, read together with its "For LLM agents" rules (paper only, append-only, sealed holdouts closed, the frozen paper cycle untouched).

Applied:

1. **The US "buy after a +30% day" entry is retired**, as the crypto entry was on 2026-10-17 (`handoff/decisions/2026-10-17_retire_G2_RET30_crypto_entry.md`). Evidence on record:
   E2 and its repairs (US trading negative against matched stocks, the sign unchanged by the repairs), E9 (documented +30% moves -1.07% a trade over 644 trades, undocumented -3.06% over
   1,337, negative in every year), and the 60-session breakout baseline (11,833 trades, no edge). Scope: no further buy-side variant of this entry is run, including the delayed entry
   (draft PR #5, E3 US retention, which stays open on GitHub and is not run) and a regime filter. Shorting the movers is not covered. The daily paper scans keep logging these
   detections as descriptive records; the frozen paper cycle, its rules and its ledger are unchanged.
2. **The data inputs are already archived**: branch `origin/data-archive` (2026-10-18, 218,736 files, 7.70 GB, manifest `archive-20261018T174417Z`). The Blueprint's statement that
   the inputs exist only in the build container is out of date. The backup counts as verified only after `tools/verify_archive.py` passes on a machine other than the build
   container (the command is in that branch's README). Nothing was archived or pushed to LFS today.
3. **The next test is the US insider-purchase study**, `idx-signals/research/US_INSIDER_BUY/` (protocol committed before any Form 4 record is fetched). It is counted test 26 in the
   register when it runs. The price panel is survivor-only, so a pass could not confirm an effect; a fail is informative.

Not changed: no real order, no sealed holdout, no change to the frozen paper cycle, no GitHub state (PRs stay as they are).

# Preserved retrospective run

Read [REPORT.md](REPORT.md) and the [engineering assessment](../../../../../docs/PREMOVE_DISCOVERY.md) together. Sequence ranking improved over simple volume/volatility, but its improvement over summary features was inconclusive. Probability quality and the false-alert burden do not support deployment.

This directory publishes the compact report, model parameters, summary, source provenance and complete bundle manifest. The three compressed CSVs listed in `MANIFEST.json` are preserved in the [complete result bundle](https://chatgpt.com/library?file_id=libfile_3f347ecfa61c81919c701299e7d015b1&account_id=personal), alongside these exact files, frozen protocol, implementation and regression tests. Personal artifact access requires the owner's account.

- Archive: `KOD-premove-results-20261030.tar.gz`
- Size: 14,735,005 bytes
- SHA-256: `cbdc58fd291377e0e72501da70f4cd21e99034e1f6e00a4afb03b59393f8df59`
- Forecasts: all 119,176 eligible 2023 decisions, including 1,805 unknown outcomes.
- `MANIFEST.json` describes the original seven-file output bundle. This explanatory README was added for repository navigation and is not part of that original bundle.

The run identifier is an arbitrary directory label; authoritative generation time is `2026-10-30T07:49:05Z` in `summary.json`. The frozen protocol was committed before evaluation in `7da767f94a6dd8b3cfbfa4222cf826ddae7590d2`. Source files match the hashes in `summary.json`; the implementation was published in `8c73b3adf902096f5b7d8a0f3ee58d2a0079ec66`.

For inputs, reproduction commands and data coverage limitations, see the engineering assessment above. Do not replace this run when reproducing; publish to a new directory.

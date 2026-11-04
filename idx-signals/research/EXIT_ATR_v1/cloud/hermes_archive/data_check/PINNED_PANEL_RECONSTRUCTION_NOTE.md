# Pinned-panel reconstruction: result (2026-10-17 WIB, before any return)

Attempts are preserved: `PINNED_PANEL_RECONSTRUCTION_attempt1_BUILD_FAILED.json` (my script omitted six empty
records that the builder's hash check requires) and `PINNED_PANEL_RECONSTRUCTION.json` (attempt 2).

## Method
- The 2026-10-13 REST rows, filtered to klines that closed before the pinned pull's `finished_at`
  (2026-10-08T00:33:37Z).
- Combined with the 2026-10-08 manifest header, records and statuses verbatim; only path and sha256 changed.
- Built with E2's unmodified builder (code a155cf0).

## Result: DIFFERS_FROM_PINNED (bytes). Content identity: NOT ESTABLISHED.

| Check | Pinned | Rebuilt |
|---|---|---|
| Panel sha256 (.csv.gz) | 3dc12749c7cc... | 636c832fc8de... |
| Rows / tickers / sessions | 773,512 / 683 / 2,472 | identical |
| First / last session, default start | | identical |
| delisted_in_universe (190), excluded_stable_or_leveraged | | identical |
| QA (spike rows dropped and examples, non-session dates) | | identical |
| Per-pair raw rows (715 pairs): pinned rows minus complete rows is 0 or 1 | | consistent for all |
| Zero-row legacy files (BCC, BCHABC, BCHSV, USDSB, VEN) | | byte-identical |

- Re-compressing the rebuilt content with the pinned file name in the gzip header (mtime 0, levels 9 and 6)
  does not reproduce 3dc12749... either.
- The rebuilt panel's decompressed CSV has sha256
  `f63ff85d77d4d298572fd7a634b10540c7c9f4435b370ea03bc704598daf9be0` (64,340,904 bytes).
- Environment here: Python 3.15.0, zlib 1.2.12. E2's environment is unknown.
- Possible causes, which cannot be separated here:
  - (a) a different deflate implementation or version;
  - (b) a content difference, for example a daily kline Binance revised between the 8 Oct and 13 Oct pulls.

## What is missing, exactly
Any ONE of these, from the environment that ran E2 and E5:
1. The sha256 of the DECOMPRESSED pinned panel, which needs no file transfer:
   `gunzip -c data/panel/panel_crypto-20261008T003354Z.csv.gz | sha256sum`
   - If it equals f63ff85d..., the content is identical and only compression differed.
2. The pinned panel itself: `data/panel/panel_crypto-20261008T003354Z.csv.gz` (sha256 3dc12749...).
3. The raw directory `data/raw/binance/20261008T001212Z/`. Its per-file sha256 values are in
   `data/manifests/binance-20261008T003333Z.jsonl`.

Until then: the faithful-reproduction claim is BLOCKED. The test may run only as "E2 configuration on a
reconstructed input whose build metadata matches the pinned panel exactly, with byte or content identity
unverified". That label must appear on every result.

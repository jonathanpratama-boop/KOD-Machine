# e2_us_sec_evidence_v1: SEC responses behind the US split schedule (2026-10-08)

| File | Bytes | SHA-256 | What |
|---|---:|---|---|
| `sec_evidence_20261008.tar.xz` | 149,805,232 | `3d53b51b0a92593826a2c56c6baf533f356744cd7f55c7a0c5b11c7495942779` | every SEC EDGAR response (full-text search results and filing documents, with each response's URL, status and time) read by `us-actions` and `us-coverage`: `data/raw/sec/20261008T091626Z/` |

Each response is listed with its hash in `data/manifests/sec_split_evidence-*.jsonl` and
`sec_split_coverage-*.jsonl`. With the archive extracted, the schedule and coverage files can
be re-derived without network:

```sh
git lfs pull --include="idx-signals/data/archive/e2_us_sec_evidence_v1/*" --exclude=""
tar -xJf data/archive/e2_us_sec_evidence_v1/sec_evidence_20261008.tar.xz        # into idx-signals/
python3 -m idxsig us-actions --raw-manifest data/manifests/yahoo_us-20261008T001812Z.jsonl \
    --effective-after 2023-01-03 --universe-end 2023-12-29 --user-agent offline \
    --cache-dir data/raw/sec/20261008T091626Z --offline
python3 -m idxsig us-actions ... --recheck data/corporate_actions/us_splits-<first pass>.json --offline ...
python3 -m idxsig us-coverage --raw-manifest data/manifests/yahoo_us-20261008T001812Z.jsonl \
    --start 2023-01-03 --end 2023-12-29 --user-agent offline --cache-dir data/raw/sec/20261008T091626Z --offline
```

Compare the `status` columns with the committed `data/corporate_actions/us_splits-*.csv`.

Access, as for every archive here: Git LFS in this private repository (see ../README.md).

# Archived original inputs

Exact bytes of inputs that are too large for git history. They are Git LFS objects in this
**private** repository, so the only way to them is repository access: whoever can clone the
repository can fetch them, nobody else. No credential is stored here. `.lfsconfig` excludes
this directory from automatic LFS downloads, so an ordinary clone stays small; fetch on purpose.

## e2_us_inputs_v1: the E2-US dataset (pulled 2026-10-08 00:12-00:24 UTC)

| File | Bytes | SHA-256 | What |
|---|---:|---|---|
| `e2_us_raw_20261008.tar.xz` | 108,011,700 | `4e6c2add81c532aca8e7ceef56480f3d2ea187370066580f9be67d258ef532e5` | the 5,705 Yahoo chart payloads (`data/raw/yahoo_us/20261008T001213Z/`) and the two Nasdaq Trader listing files (`data/raw/us_universe/20261008T001212Z/`), paths as in the frozen manifests |
| `panel_us-20261008T004105Z.csv.gz` | 200,358,031 | `e5b5267438667a136f4a4cb42c52d6bc98bc80cde6a88c02a27751a4902c9b92` | the compressed panel the original run used, byte for byte |

Each file inside the tarball is listed with its SHA-256 in the frozen manifests
`data/manifests/yahoo_us-20261008T001812Z.jsonl` and `us_universe-20261008T001213Z.jsonl`
(committed with the original work, before any repair). The tarball is deterministic
(`tar --sort=name --mtime='2026-10-08 00:00:00Z' --owner=0 --group=0 --numeric-owner`, xz -6);
its own hash matters less than the per-file hashes, which are the frozen evidence.

### Retrieve and verify

Requires git and git-lfs, and read access to the repository.

```sh
git clone https://github.com/jonathanpratama-boop/KOD-Machine.git
cd KOD-Machine
git checkout <the commit named in the handoff>
git lfs pull --include="idx-signals/data/archive/e2_us_inputs_v1/*" --exclude=""
cd idx-signals/data/archive/e2_us_inputs_v1 && sha256sum -c SHA256SUMS && cd ../../..
tar -xJf data/archive/e2_us_inputs_v1/e2_us_raw_20261008.tar.xz           # into idx-signals/
mkdir -p data/panel && cp data/archive/e2_us_inputs_v1/panel_us-20261008T004105Z.csv.gz data/panel/
python3 research/E2/repair/verify_inputs.py    # every payload, listing file, panel and run file vs frozen hashes
```

`verify_inputs.py` must print `ALL ORIGINAL INPUTS PRESENT AND MATCHING`.

Alternative to the archived panel: rebuild it from the payloads.
`python3 -m idxsig build-global-panel --market US --manifest data/manifests/yahoo_us-20261008T001812Z.jsonl`
writes a new file whose decompressed content must hash to
`8714fa1f98b5882a77a9095573775301f285ebef269c6108a9375ce8d52df988`
(`gzip -dc <file> | sha256sum`); the compressed file hash differs only because gzip stores
the output file name (research/E2/repair/reproduction_v1.json).

A fresh download from Yahoo is a different dataset (the provider re-adjusts history at every
new split), not a reproduction.

Terms: Yahoo Finance data for personal and research use; Nasdaq Trader symbol directory.
Do not redistribute outside the repository's collaborators.

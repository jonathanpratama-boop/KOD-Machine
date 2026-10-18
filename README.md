# KOD-Machine data archive (complete)

Data-only branch holding every untracked data file listed in the archive manifest (218,736 files, 7.70 GB):
the Yahoo pulls, IDX mirror, eToro snapshot, US universe, panels, SEC caches and filings, and Binance pulls.
Batches 1-3 are the inputs that cannot be fetched again exactly; batches 4-7 are SEC and Binance data.

Restore and verify (on the Mac, from a clone of the repository):

    git fetch origin data-archive
    git worktree add ../KOD-data data-archive
    sh ../KOD-data/reassemble.sh
    python3 ../KOD-data/tools/verify_archive.py \
        ../KOD-data/idx-signals/data/manifests/archive-20261018T174417Z.jsonl.gz ../KOD-data

Expect "full archive: verified 218736, missing 0, mismatched 0".
The backup counts as done only after that check passes on a machine other than the build container.

Not in the manifest: `idx-signals/data/raw/idx_mirror_git.tar` is the IDX mirror's own git history (a nested
repository, which git cannot store directly and the manifest does not list). Extract it into
`idx-signals/data/raw/idx_mirror/` if needed.

# KOD-Machine data archive (irreplaceable tier)

Data-only branch. It holds the untracked inputs that cannot be fetched again exactly: the Yahoo pulls (the
provider revises history), the IDX mirror, the eToro instrument snapshot, the US universe and the panels.
SEC and Binance data are not here: they can be downloaded again, and the manifest proves whether a re-download
matches byte for byte.

Restore and verify (on the Mac, from a clone of the repository):

    git fetch origin data-archive
    git worktree add ../KOD-data data-archive
    sh ../KOD-data/reassemble.sh
    python3 ../KOD-data/tools/verify_archive.py \
        ../KOD-data/idx-signals/data/manifests/archive-20261018T174417Z.jsonl.gz ../KOD-data \
        --only data/raw/yahoo data/raw/idx_mirror data/raw/etoro data/raw/us_universe data/panel

Expect "verified N, missing 0, mismatched 0". (`data/raw/yahoo` also matches the other yahoo_* folders.)
The backup counts as done only after that check passes on a machine other than the build container.

Not in the manifest: `idx-signals/data/raw/idx_mirror_git.tar` is the IDX mirror's own git history (a nested
repository, which git cannot store directly and the manifest does not list). Extract it into
`idx-signals/data/raw/idx_mirror/` if needed.

#!/bin/sh
# Rebuild the panels split for GitHub's 100 MB file limit, then remove the parts.
set -e
cd "$(dirname "$0")/idx-signals/data/panel"
for f in panel_us-20261008T004105Z.csv.gz panel_us_repair-20261008T095321Z.csv.gz panel_us_repair-20261008T114805Z.csv.gz; do
  cat "$f".part-* > "$f" && rm "$f".part-*
done
echo "panels rebuilt"

#!/usr/bin/env python3
"""Check an archive copy of idx-signals' untracked data against a committed manifest
(idx-signals/data/manifests/archive-<stamp>.jsonl.gz): every file present, same size, same sha256.

Usage: python3 tools/verify_archive.py <manifest.jsonl.gz> <root that contains idx-signals/>  [--only PREFIX ...]
Prints missing and mismatched files; exits non-zero if any.
"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("root")
    ap.add_argument("--only", nargs="*", default=[], help="check only paths starting with these prefixes")
    args = ap.parse_args()
    base = Path(args.root) / "idx-signals"
    ok = missing = bad = 0
    with gzip.open(args.manifest, "rt") as fh:
        for line in fh:
            rec = json.loads(line)
            if args.only and not rec["path"].startswith(tuple(args.only)):
                continue
            p = base / rec["path"]
            if not p.is_file():
                missing += 1
                print(f"MISSING {rec['path']}")
                continue
            h = hashlib.sha256()
            with p.open("rb") as r:
                for b in iter(lambda: r.read(1 << 20), b""):
                    h.update(b)
            if p.stat().st_size != rec["bytes"] or h.hexdigest() != rec["sha256"]:
                bad += 1
                print(f"MISMATCH {rec['path']}")
            else:
                ok += 1
    print(f"verified {ok}, missing {missing}, mismatched {bad}")
    return 1 if missing or bad else 0


if __name__ == "__main__":
    sys.exit(main())

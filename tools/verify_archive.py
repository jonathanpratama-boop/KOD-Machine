#!/usr/bin/env python3
"""Check an archive copy of idx-signals' untracked data against a committed manifest
(idx-signals/data/manifests/archive-<stamp>.jsonl.gz and its .summary.json): every file present, same size,
same sha256. Fails if no file was checked, if the manifest does not match its summary (file count, bytes,
sha256), or, for a full check, if fewer files were checked than the summary lists.

Usage: python3 tools/verify_archive.py <manifest.jsonl.gz> <root that contains idx-signals/>  [--only PREFIX ...]
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
    manifest = Path(args.manifest)
    summary_path = manifest.with_name(manifest.name.replace(".jsonl.gz", ".summary.json"))
    if not summary_path.is_file():
        print(f"FAIL no summary file {summary_path.name}: cannot tell a complete manifest from a partial one")
        return 1
    summary = json.loads(summary_path.read_text())
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != summary["manifest_sha256"]:
        print("FAIL manifest does not match the sha256 in its summary")
        return 1
    base = Path(args.root) / "idx-signals"
    listed = listed_bytes = ok = missing = bad = 0
    with gzip.open(manifest, "rt") as fh:
        for line in fh:
            rec = json.loads(line)
            listed += 1
            listed_bytes += rec["bytes"]
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
    problems = []
    if (listed, listed_bytes) != (summary["files"], summary["bytes"]):
        problems.append(f"manifest lists {listed} files / {listed_bytes} bytes, summary says "
                        f"{summary['files']} / {summary['bytes']}")
    if ok + missing + bad == 0:
        problems.append("no file was checked (empty manifest or no path matched --only)")
    if not args.only and ok + missing + bad != summary["files"]:
        problems.append(f"checked {ok + missing + bad} of {summary['files']} files")
    for p in problems:
        print(f"FAIL {p}")
    scope = f"prefixes {args.only}" if args.only else "full archive"
    print(f"{scope}: verified {ok}, missing {missing}, mismatched {bad} (manifest {summary['files']} files, "
          f"{summary['bytes'] / 1e9:.2f} GB)")
    return 1 if missing or bad or problems else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build the single-page KOD dashboard with its data embedded.

    python3 tools/status/dashboard/make_standalone.py --data /path/to/status-out \
        --out tools/status/dashboard/standalone.html

The generated file opens directly in a browser and needs no external libraries.
Run build_status.py first to refresh the source data.
"""

import argparse
import json
from pathlib import Path


DATASETS = [
    "experiments",
    "programs",
    "summary",
    "history",
    "runs",
    "run_days",
    "server",
    "server_history",
    "events",
    "gaps",
    "build",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    template_path = Path(__file__).with_name("one_page.html")
    template = template_path.read_text(encoding="utf-8")
    if template.count("__KOD_DATA__") != 1:
        raise SystemExit("one_page.html must contain exactly one __KOD_DATA__ marker")

    data = {}
    missing = []
    for name in DATASETS:
        path = args.data / f"{name}.json"
        if path.exists():
            data[name] = json.loads(path.read_text(encoding="utf-8"))
        else:
            missing.append(name)
    if missing:
        raise SystemExit(f"missing datasets in {args.data}: {', '.join(missing)}")

    # Keep embedded JSON inside its script element, even if a source includes HTML.
    embedded = (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    html = template.replace("__KOD_DATA__", embedded)
    args.out.write_text(html, encoding="utf-8")
    built_at = data["build"][0]["built_at"]
    print(f"wrote {args.out} ({len(html):,} characters) from {len(data)} datasets built {built_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

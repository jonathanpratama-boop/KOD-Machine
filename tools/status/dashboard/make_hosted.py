#!/usr/bin/env python3
"""Turn standalone.html into the form the artifact host wants (no doctype/html/head/body tags).

    python3 tools/status/dashboard/make_standalone.py --data DIR --out /tmp/kod-standalone.html
    python3 tools/status/dashboard/make_hosted.py --in /tmp/kod-standalone.html --out /tmp/kod-hosted.html

The host wraps the file in its own shell, so only the title, style, body markup and scripts are kept.
"""

import argparse
import re
from pathlib import Path

TITLE = "KOD Research Status"


def to_hosted(html: str) -> str:
    html = re.sub(r"^\s*<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", html, flags=re.I)
    html = re.sub(r'<meta charset="utf-8">\s*', "", html, count=1)
    html = re.sub(r'<meta name="viewport"[^>]*>\s*', "", html, count=1)
    html = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", html, count=1, flags=re.S)
    html = re.sub(r"</head>\s*<body>\s*", "", html, count=1)
    html = re.sub(r"\s*</body>\s*</html>\s*$", "\n", html)
    for tag in ("html", "head", "body"):
        if re.search(rf"<{tag}[\s>]", html, re.I):
            raise SystemExit(f"hosted page still has a <{tag}> tag")
    if not html.lstrip().startswith("<title>"):
        raise SystemExit("hosted page must start with its <title>")
    if "download" in re.findall(r'id="([^"]+)"', html) or "download-data" in html:
        raise SystemExit("the host blocks downloads; remove the download control")
    return html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    html = to_hosted(args.src.read_text(encoding="utf-8"))
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out} ({len(html):,} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

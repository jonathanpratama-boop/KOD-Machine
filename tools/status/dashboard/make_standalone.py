#!/usr/bin/env python3
"""Build standalone.html: the dashboard page with its data embedded, openable in any browser.

    python3 tools/status/dashboard/make_standalone.py --data /path/to/status-out \
        --out tools/status/dashboard/standalone.html

--data is the directory build_status.py wrote. The page needs d3 from cdnjs (one script tag);
everything else is in the file. It stands in for the dashboard runtime (dash.data/draw/params),
so what you see is the same page as the hosted dashboard, frozen at the time of the build.
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

TOKENS = """:root{--font-anthropic-sans:system-ui,-apple-system,"Segoe UI",sans-serif;--font-anthropic-serif:Georgia,serif;
--cds-font-size-caption:12px;--cds-font-size-body:14px;--cds-font-size-heading:16px;--cds-font-size-title:26px;
--cds-font-weight-medium:550;--cds-gap-xs:4px;--cds-gap-sm:8px;--cds-gap-md:12px;--cds-gap-lg:16px;--cds-gap-xl:28px;
--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:16px;--cds-radius:8px;--color-panel:#fff;
--color-border-line:#e5e3dc;--color-fg:#1f1e1c;--color-fg-muted:#6b6a65;--color-ok:#2e7d4f;--color-warn:#b7791f;
--color-bad:#c0392b;--cds-chart-grid:#eeece6;--cds-chart-muted:#a9a69c;--cds-chart-reference:#8a877d;
--cds-surface-popover:#fff;--cds-border:#ddd;--cds-text-secondary:#777;--cds-shadow-popover:0 2px 8px rgba(0,0,0,.12);
--cds-dur-slow:.2s}
body{background:#f7f6f2;margin:0;padding:24px;color:var(--color-fg);font-family:var(--font-anthropic-sans)}
#dash-root{max-width:1240px;margin:0 auto}"""

RUNTIME = """
window.__D = %DATA%;
const draws = {}; const datas = []; let params = {};
window.dash = {
  colors: ['#3b6fd4', '#d4823b', '#2e7d4f', '#8a5cc2'],
  data: (id) => (__D[id] ? { status: 'ok', data: __D[id], columns: Object.keys(__D[id][0] || {}) } : { status: 'loading' }),
  params: () => params,
  setParams: (p) => { params = { ...params, ...p }; run(); },
  setLink: () => run(),
  onData: (f) => { datas.push(f); f(); },
  draw: (n, fn) => { draws[n] = fn; },
};
function run() {
  datas.forEach((f) => f());
  for (const [n, fn] of Object.entries(draws)) {
    document.querySelectorAll('[data-draw="' + n + '"]').forEach((el) => { if (!el.closest('[hidden]')) fn(el); });
  }
}
window.addEventListener('load', run);
window.addEventListener('resize', run);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    here = Path(__file__).parent
    page = (here / "index.html").read_text()
    data = {}
    for name in DATASETS:
        path = args.data / f"{name}.json"
        if path.exists():
            data[name] = json.loads(path.read_text())
    missing = [n for n in DATASETS if n not in data]
    if missing:
        raise SystemExit(f"missing datasets in {args.data}: {', '.join(missing)}")
    runtime = RUNTIME.replace("%DATA%", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    built = data["build"][0]["built_at"]
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>KOD Status (snapshot)</title>"
        f"<style>{TOKENS}</style>"
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>'
        f"<script>{runtime}</script></head><body>"
        f'<p style="font-size:12px;color:#6b6a65;margin:0 0 12px">Snapshot built {built}. '
        "Regenerate with tools/status/dashboard/make_standalone.py.</p>"
        f'<div id="dash-root">{page}</div></body></html>'
    )
    args.out.write_text(html)
    print(f"wrote {args.out} ({len(html):,} bytes) from {len(data)} datasets built {built}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

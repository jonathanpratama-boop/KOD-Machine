"""Browser journey through the Company Decision Dossier, in a real browser against a real local server on a fresh offline demo workspace.

    python3 workstation_tests/browser_journey.py --out <directory for screenshots and the JSON report>

Needs the optional workstation dependencies and Playwright for Python with a Chromium build (not part of the unit tests). The journey:
inbox -> company -> dossier -> a supported change -> its calculation -> the source evidence -> archive search -> passage in context -> driver model
started from history -> saved scenario -> sensitivity cell (what-if) -> reverse valuation -> thesis with a scenario condition -> revised assumption ->
the condition now needs review, with the changed assumption in its trace -> recorded decision -> reopened packet reproduces -> Markdown/JSON exports.
Then the main pages again at a phone width. Console errors (including CSP violations), unlabeled form fields and page-level horizontal overflow fail.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UNLABELED = """() => [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
  .filter(e => !e.closest('label') && !e.getAttribute('aria-label') && !(e.id && document.querySelector(`label[for="${e.id}"]`)))
  .map(e => e.name || e.outerHTML.slice(0, 80))"""
OVERFLOW = "() => document.documentElement.scrollWidth - window.innerWidth"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(root, port):
    import uvicorn
    from kod.workstation.web import create_app

    config = uvicorn.Config(
        create_app(root, offline=True),
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return server
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--executable", help="Chromium executable, if Playwright's own lookup fails")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    from kod.workstation.demo import seed_demo
    from kod.workstation.services import ResearchService
    from kod.workstation.store import Store

    report = {
        "steps": [],
        "console_errors": [],
        "unlabeled_fields": {},
        "overflow_px": {},
        "failures": [],
    }
    with tempfile.TemporaryDirectory(prefix="kod-journey-") as tmp:
        root = Path(tmp) / "workspace"
        service = ResearchService(Store(root))
        seed_demo(service)
        port = free_port()
        server = serve(root, port)
        base = f"http://127.0.0.1:{port}"
        with sync_playwright() as p:
            browser = p.chromium.launch(
                **({"executable_path": args.executable} if args.executable else {})
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.set_default_timeout(10000)
            page.on(
                "console", lambda m: m.type == "error" and report["console_errors"].append(m.text)
            )
            page.on("pageerror", lambda e: report["console_errors"].append(str(e)))

            pending = []

            def act(fn, *a, **kw):
                """Run a browser action; a failure is kept and reported by the next step instead of aborting the journey."""
                try:
                    return fn(*a, **kw)
                except Exception as exc:
                    pending.append(
                        f"{fn.__name__}{a[:1]}: {type(exc).__name__}: {str(exc).splitlines()[0][:200]}"
                    )

            def step(name, check=None):
                started = time.monotonic()
                ok = True
                detail = None
                try:
                    if pending:
                        raise RuntimeError("; ".join(pending))
                    detail = check() if check else None
                except Exception as exc:  # a failed expectation is recorded, the journey stops at the end with a non-zero exit
                    ok, detail = False, f"{type(exc).__name__}: {exc}"[:400]
                    report["failures"].append(name)
                pending.clear()
                page.screenshot(
                    path=str(args.out / f"{len(report['steps']) + 1:02d}-{name}.png"),
                    full_page=True,
                )
                report["unlabeled_fields"][name] = page.evaluate(UNLABELED)
                report["overflow_px"][name] = page.evaluate(OVERFLOW)
                report["steps"].append(
                    {
                        "step": name,
                        "ok": ok,
                        "seconds": round(time.monotonic() - started, 2),
                        "url": page.url.replace(base, ""),
                        "detail": detail,
                    }
                )

            def expect_text(text):
                page.wait_for_selector(f"text={text}", timeout=10000)
                return text

            act(page.goto, base + "/")
            step("inbox", lambda: expect_text("Watchlist"))
            act(page.click, "nav.watchlist >> text=NVDA")
            step("company", lambda: expect_text("COMPANY WORKSPACE"))
            act(page.click, "text=Open dossier →")
            step("dossier", lambda: expect_text("Supported changes"))
            act(page.click, ".change-cards a >> nth=0")
            step("calculation", lambda: expect_text("CALCULATION LINEAGE"))
            act(page.click, "table >> a.cell-link >> nth=0")
            step(
                "evidence",
                lambda: expect_text("the preserved response holds this value at this pointer"),
            )
            act(page.goto, base + "/search")
            act(page.fill, "input[name=q]", "data center revenue")
            act(page.press, "input[name=q]", "Enter")
            step("search", lambda: expect_text("matching passage"))
            act(page.click, "text=Passage in context → >> nth=0")
            step("passage", lambda: expect_text("PASSAGE"))

            nvda = page.evaluate(
                "() => [...document.querySelectorAll('nav.watchlist a')].find(a => a.textContent.includes('NVDA')).getAttribute('href')"
            )
            act(page.goto, base + nvda + "/model?start=history")
            form = {
                "valuation_date": "2026-10-23",
                "revenue_growth": "40, 25, 15, 10, 8",
                "cash_tax_rate": "15",
                "capex_rate": "3",
                "nwc_rate": "15",
                "discount_rate": "10",
                "terminal_growth": "3",
                "terminal_roic": "30",
                "cash": "11000",
                "debt": "8500",
                "other_senior_claims": "0",
                "bridge_as_of": "2026-07-26",
                "share_count": "24300",
                "share_count_as_of": "2026-07-26",
                "share_count_basis": "browser journey: diluted shares, analyst-reviewed proxy",
                "rationale": "Browser journey: illustrative assumptions, not a view.",
            }
            for name, value in form.items():
                act(page.fill, f"[name={name}]", value)
            for name, value in (
                ("treatment_stock_compensation", "expensed_in_margin"),
                ("treatment_leases", "operating_cost_in_margin"),
                ("treatment_convertibles", "none_outstanding"),
                ("treatment_noncontrolling_interests", "none"),
                ("treatment_tax_losses", "none_material"),
            ):
                act(page.select_option, f"[name={name}]", value)
            step("model-form", lambda: expect_text("History as reference"))
            act(page.click, "text=Validate & save version →")
            step("scenario", lambda: expect_text("Value per share"))
            act(page.click, "table.dossier-table a.cell-link >> nth=0")
            step("what-if", lambda: expect_text("What-if, not saved"))
            act(page.select_option, "select[name=solve]", "operating_margin")
            act(page.fill, "input[name=target]", "100")
            act(page.click, 'button:has-text("Solve")')
            step("reverse", lambda: expect_text("required under this model and these assumptions"))

            act(page.goto, base + nvda + "/thesis")
            act(page.fill, "[name=title]", "Journey thesis")
            act(
                page.fill,
                "[name=statement]",
                "Demand stays strong and the base case stays above 100 per share.",
            )
            act(page.fill, "[name=c1_label]", "Review if the base case falls below 100 per share")
            act(page.select_option, "[name=c1_left]", "scenario:base:default:per_share")
            act(page.select_option, "[name=c1_op]", "<")
            act(page.fill, "[name=c1_value]", "100")
            act(page.select_option, "[name=c1_unit]", "currency/share")
            act(page.fill, "[name=c1_currency]", "USD")
            act(page.fill, "[name=rationale]", "Browser journey")
            act(page.click, "text=Validate & save version →")
            step(
                "thesis",
                lambda: expect_text(
                    "not triggered · Review if the base case falls below 100 per share"
                ),
            )

            act(page.goto, base + nvda + "/model")
            act(page.click, "table >> text=Open → >> nth=0")
            act(page.click, "text=Revise as new version")
            act(page.fill, "[name=operating_margin]", "40")
            act(page.fill, "[name=rationale]", "Browser journey: margin compression case.")
            act(page.click, "text=Validate & save version →")
            step("revised-scenario", lambda: expect_text("version 2 of 2"))
            act(page.goto, base + nvda + "/thesis")
            step(
                "thesis-review",
                lambda: (
                    expect_text("triggered · Review if the base case falls below 100 per share"),
                    expect_text("changed: operating_margin"),
                ),
            )
            act(page.goto, base + nvda + "/dossier")
            act(
                page.fill,
                "form[action$='/decisions'] [name=question]",
                "Does the margin compression case break the thesis?",
            )
            act(
                page.fill,
                "form[action$='/decisions'] [name=choice]",
                "Keep researching margins; no position change",
            )
            act(
                page.fill,
                "form[action$='/decisions'] [name=rationale]",
                "Browser journey decision.",
            )
            act(page.fill, "form[action$='/decisions'] [name=review_date]", "2027-01-31")
            act(page.click, "text=Record decision packet →")
            step("packet", lambda: expect_text("DECISION PACKET"))
            packet_url = page.url.split("?")[0]
            act(page.click, "text=Reproduce")
            step("reproduce", lambda: expect_text("Reproduced"))
            md, js = page.request.get(packet_url + ".md"), page.request.get(packet_url + ".json")
            report["exports"] = {
                "markdown_status": md.status,
                "json_status": js.status,
                "json_sha256": js.json().get("packet_sha256") if js.ok else None,
            }

            phone = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
            page = phone.new_page()
            page.on(
                "console", lambda m: m.type == "error" and report["console_errors"].append(m.text)
            )
            for name, path in (
                ("phone-dossier", nvda + "/dossier"),
                ("phone-model", nvda + "/model"),
                ("phone-thesis", nvda + "/thesis"),
                ("phone-packet", packet_url.replace(base, "")),
                ("phone-search", "/search?q=revenue"),
            ):
                act(page.goto, base + path)
                step(name)
            browser.close()
        server.should_exit = True
    problems = [k for k, v in report["unlabeled_fields"].items() if v] + [
        k for k, v in report["overflow_px"].items() if v > 1
    ]
    report["passed"] = (
        not report["failures"]
        and not report["console_errors"]
        and not problems
        and report.get("exports", {}).get("json_status") == 200
    )
    report["layout_problems"] = problems
    (args.out / "journey.json").write_text(json.dumps(report, indent=1))
    print(
        json.dumps(
            {
                k: report[k]
                for k in ("passed", "failures", "console_errors", "layout_problems", "exports")
            },
            indent=1,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

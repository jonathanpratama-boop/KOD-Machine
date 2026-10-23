"""Local, single-user research interface. Network access is explicit and optional."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import dossier as dossier_model
from . import search as archive
from .domain import timestamp
from .financials import FinancialRepository
from .policy import DAY_END, STRICT, AsOfPolicy, eligibility
from .services import ResearchService
from .store import Store

ASSETS = Path(__file__).resolve().parent
MAX_BODY = 10 * 1024 * 1024
MAX_UPLOAD = 8 * 1024 * 1024
COOKIE = "kod_workstation_csrf"
METRICS = {"revenue": "Revenue", "net_income": "Net income", "operating_income": "Operating income", "operating_expenses": "Operating expenses", "gross_margin": "Gross margin", "eps_diluted": "Diluted EPS"}


class _BodyTooLarge(Exception):
    pass


class LocalBoundary:
    """Limit streamed bodies and reject browser cross-origin mutations before parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        if scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}:
            host = headers.get("host", "").lower()
            origin = headers.get("origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != host:
                    return await PlainTextResponse("Cross-origin changes are refused.", 403)(scope, receive, send)
            if headers.get("sec-fetch-site") == "cross-site":
                return await PlainTextResponse("Cross-site changes are refused.", 403)(scope, receive, send)
        try:
            if int(headers.get("content-length", "0")) > MAX_BODY:
                return await PlainTextResponse("The request is too large (10 MiB maximum).", 413)(scope, receive, send)
        except ValueError:
            return await PlainTextResponse("Invalid Content-Length.", 400)(scope, receive, send)
        size = 0

        async def limited():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > MAX_BODY:
                raise _BodyTooLarge
            return message

        async def security_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (b"content-security-policy", b"default-src 'self'; style-src 'self'; img-src 'self' data:; script-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"),
                ])
            await send(message)

        try:
            await self.app(scope, limited, security_headers)
        except _BodyTooLarge:
            await PlainTextResponse("The request is too large (10 MiB maximum).", 413)(scope, receive, send)


def safe_url(value):
    """Citation links do not imply authentication; allow only ordinary public URL syntax."""
    try:
        p = urlsplit(str(value))
        if p.scheme in {"http", "https"} and p.hostname and not p.username and not p.password and not any(c in str(value) for c in "\r\n\x00"):
            return str(value)
    except ValueError:
        pass
    return None


def _text(value, maximum=4000):
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValueError(f"Text exceeds the {maximum:,}-character limit.")
    return text


def _error(exc):
    # A provider may include a contact in an upstream diagnostic; never echo it.
    return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted contact]", str(exc))[:600]


def _display_time(value):
    return str(value).replace("T", " ").replace("+00:00", " UTC").replace("Z", " UTC") if value else "Unknown"


def _number(value):
    if value is None:
        return "—"
    try:
        from decimal import Decimal
        v = Decimal(str(value))
        return f"{v:,.8f}".rstrip("0").rstrip(".") if "." in str(value) else f"{v:,.0f}"
    except Exception:
        return str(value)


def _available_key(row):
    """Sort/filter key: a precise publication time, else a date-only publication, else nothing."""
    return row.get("published_at") or (row.get("metadata") or {}).get("publication_date") or ""


def _available(row):
    if row.get("published_at"):
        return _display_time(row["published_at"])
    day = (row.get("metadata") or {}).get("publication_date")
    return f"{day} (date only)" if day else "Unknown"


def _unit(fact):
    unit = fact.get("unit", "unknown")
    cur = fact.get("currency")
    if unit == "percent":
        return "%"
    if unit == "per_share":
        return f"{cur or '?'} / share"
    return f"{cur or '?'} {unit}"


POLICIES = {"day-end": DAY_END, "strict": STRICT}


def _policy(clock, as_of="", mode="", policy=""):
    """The information-time policy from query parameters: cutoff (default now), observed/public mode (default observed), strict/day-end (default day-end,
    which admits date-only filing availability from the end of the filing day)."""
    try:
        cutoff = timestamp(as_of.strip() or clock())
        mode = mode or "observed"
        if mode not in ("observed", "public"):
            raise ValueError("Choose observed or public mode.")
        if (policy or "day-end") not in POLICIES:
            raise ValueError("Choose the strict or day-end availability policy.")
        return AsOfPolicy.parse(cutoff, mode, POLICIES[policy or "day-end"])
    except ValueError as exc:
        raise HTTPException(400, "Invalid information cutoff: " + _error(exc))


def _policy_query(policy):
    name = next(k for k, v in POLICIES.items() if v == policy.policy_version)
    return urlencode({"as_of": policy.as_dict()["cutoff"], "mode": policy.mode, "policy": name})


def create_app(data_dir, offline=False, service=None, *, testing=False):
    """Build an app with explicit runtime state; no import-time IO or collection."""
    app = FastAPI(title="KOD Workstation", docs_url=None, redoc_url=None)
    app.add_middleware(LocalBoundary)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"] + (["testserver"] if testing else []))
    app.state.service = service or ResearchService(Store(Path(data_dir)))
    app.state.store = app.state.service.store
    app.state.offline = bool(offline)
    signing_key = secrets.token_bytes(32)
    templates = Jinja2Templates(directory=str(ASSETS / "templates"))
    templates.env.filters.update(moment=_display_time, number=_number)
    templates.env.globals.update(show=dossier_model.display, metric_label=lambda m: dossier_model.LABELS.get(m, str(m).replace("_", " ")))
    templates.env.globals.update(available=_available, metric=lambda key: METRICS.get(key, str(key).replace("_", " ").title()), unit=_unit, safe_url=safe_url)
    markdown = MarkdownIt("commonmark", {"html": False, "linkify": False}).disable("image")
    app.mount("/static", StaticFiles(directory=str(ASSETS / "static")), name="static")

    def valid_token(token):
        try:
            value, signature = token.rsplit(".", 1)
            expected = hmac.new(signing_key, value.encode(), hashlib.sha256).hexdigest()
            return len(value) >= 32 and hmac.compare_digest(signature, expected)
        except (ValueError, AttributeError):
            return False

    def render(request, template, *, status_code=200, **context):
        token = request.cookies.get(COOKIE, "")
        if not valid_token(token):
            value = secrets.token_urlsafe(32)
            token = value + "." + hmac.new(signing_key, value.encode(), hashlib.sha256).hexdigest()
        common = {"request": request, "csrf": token, "offline": app.state.offline, "securities": app.state.store.securities(), "message": request.query_params.get("message", "")[:600]}
        response = templates.TemplateResponse(request=request, name=template, context={**common, **context}, status_code=status_code)
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=8 * 3600, path="/")
        response.headers["Cache-Control"] = "no-store"
        return response

    async def form(request):
        fields = await request.form(max_files=2, max_fields=20)
        cookie, token = request.cookies.get(COOKIE, ""), str(fields.get("csrf", ""))
        if not valid_token(cookie) or not hmac.compare_digest(cookie, token):
            raise HTTPException(403, "This form expired or could not be verified. Reload the page and try again.")
        return fields

    def redirect(path, message=None):
        return RedirectResponse(path + ("?" + urlencode({"message": message}) if message else ""), status_code=303)

    def security_or_404(security_id):
        try:
            return app.state.store.get_security(security_id)
        except (ValueError, KeyError):
            raise HTTPException(404, "Company not found.")

    def note_or_404(note_id):
        try:
            return app.state.store.note(note_id)
        except (ValueError, KeyError):
            raise HTTPException(404, "Research note not found.")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return render(request, "error.html", status_code=exc.status_code, title="Unable to complete this request", error=exc.detail, page="error")

    @app.get("/", response_class=HTMLResponse)
    def inbox(request: Request, security: str = "", category: str = "", status: str = "", q: str = "", after: str = "", before: str = ""):
        store = app.state.store
        securities = store.securities()
        by_id = {s["id"]: s for s in securities}
        events = store.events(security or None)
        referenced = {event.get("document_id") for event in events}
        rows = [{**event, "kind": event.get("form", "Filing"), "status": event.get("metadata", {}).get("extraction_status", "filing"), "company": by_id.get(event["security_id"])} for event in events]
        for doc in store.documents(security or None):
            if doc["id"] not in referenced and doc.get("role") != "metadata" and doc.get("provider") not in {"sec_submissions", "sec_mapping"}:
                rows.append({**doc, "kind": "RELEASE", "title": doc["filename"], "status": doc["extraction_status"], "company": by_id.get(doc["security_id"]), "document_id": doc["id"]})
        rows = [r for r in rows if (not category or r["kind"] == category) and (not status or r["status"] == status)
                and (not q or q.lower() in (r.get("title", "") + " " + str(r.get("company", {}))).lower())
                and (not after or _available_key(r)[:10] >= after)
                and (not before or bool(_available_key(r)) and _available_key(r)[:10] <= before)]
        rows.sort(key=lambda r: (_available_key(r), r.get("observed_at") or ""), reverse=True)
        return render(request, "inbox.html", page="inbox", rows=rows[:250], total=len(rows), notes=store.notes(), selected=security, category=category, selected_status=status, q=q[:200], after=after, before=before)

    @app.post("/watchlist")
    async def add_watchlist(request: Request):
        fields = await form(request)
        try:
            ticker = _text(fields.get("ticker"), 32).upper()
            name = _text(fields.get("name"), 180)
            cik = _text(fields.get("cik"), 10) or None
            venue = _text(fields.get("venue"), 24).upper() or "UNSPECIFIED"
            currency = _text(fields.get("currency"), 3).upper() or "USD"
            if not re.fullmatch(r"[A-Z0-9.^_-]{1,32}", ticker) or not name:
                raise ValueError("Provide a company name and a valid ticker.")
            if cik and not cik.isdigit():
                raise ValueError("CIK must contain digits only.")
            if not re.fullmatch(r"[A-Z]{3}", currency):
                raise ValueError("Use a three-letter currency code.")
            sec = app.state.store.upsert_security(ticker, name, cik=cik, venue=venue, currency=currency, association="user_asserted")
            return redirect("/company/" + sec["id"], "Company added. Identity is user asserted until verified from filing metadata.")
        except ValueError as exc:
            return redirect("/", _error(exc))

    @app.post("/watchlist/{security_id}/remove")
    async def remove_watchlist(security_id: str, request: Request):
        await form(request)
        security_or_404(security_id)
        app.state.store.remove_watchlist(security_id)
        return redirect("/", "Removed from the watchlist. Saved evidence and notes are retained.")

    @app.post("/watchlist/resolve")
    async def resolve_watchlist(request: Request):
        fields = await form(request)
        if app.state.offline:
            return redirect("/", "Offline mode: ticker lookup is disabled. Add an explicit company and CIK instead.")
        try:
            from .sources import SecClient
            client = SecClient()
            identity = await run_in_threadpool(client.resolve, _text(fields.get("ticker"), 32))
            raw = getattr(client, "last_mapping_raw", None)
            observed = getattr(client, "last_mapping_observed_at", None)
            if not isinstance(raw, bytes) or not raw or not isinstance(observed, str):
                raise ValueError("SEC identity lookup did not retain its source evidence. Add an explicit identity or retry.")
            sec = app.state.store.upsert_security(**identity)
            mapping_url = "https://www.sec.gov/files/company_tickers_exchange.json"
            app.state.store.save_document(
                sec["id"], raw, "company_tickers_exchange.json", mapping_url,
                observed_at=observed, role="metadata", provider="sec_mapping",
                association="verified_from_filing_metadata", external_id=mapping_url,
                extraction_status="metadata", published_basis="Publication time unknown; current SEC listing metadata observed at retrieval",
                metadata={"kind": "SEC current listing mapping", "selected_ticker": identity["ticker"],
                          "selected_cik": identity.get("cik"), "observed_basis": "fetched by this SEC ticker lookup",
                          "coverage_note": "Current listings only; not a historical security master"},
            )
            return redirect("/company/" + sec["id"], "Company identity resolved from current SEC listing metadata.")
        except (ValueError, RuntimeError) as exc:
            return redirect("/", _error(exc))

    @app.get("/company/{security_id}", response_class=HTMLResponse)
    def company(security_id: str, request: Request):
        sec = security_or_404(security_id)
        docs = app.state.store.documents(security_id)
        return render(request, "company.html", page="company", company=sec, documents=docs, parsed=[d for d in docs if d.get("extraction_status") in ("parsed", "needs_review")], events=app.state.store.events(security_id), notes=app.state.store.notes(security_id))

    @app.post("/company/{security_id}/upload")
    async def upload(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        try:
            document = fields.get("document")
            if not hasattr(document, "read"):
                raise ValueError("Select an HTML earnings release to upload.")
            filename = Path((document.filename or "release.html").replace("\\", "/")).name
            if Path(filename).suffix.lower() not in {".htm", ".html"}:
                raise ValueError("This version accepts .html or .htm earnings releases. PDF is not supported.")
            raw = await document.read(MAX_UPLOAD + 1)
            if len(raw) > MAX_UPLOAD:
                raise ValueError("The release exceeds the 8 MiB upload limit.")
            header = fields.get("sec_headers")
            headers = await header.read(1024 * 1024 + 1) if hasattr(header, "read") and header.filename else None
            if headers is not None and len(headers) > 1024 * 1024:
                raise ValueError("The SEC header file exceeds the 1 MiB limit.")
            url = _text(fields.get("source_url"), 2000) or "https://example.invalid/local-file/" + filename
            if not safe_url(url):
                raise ValueError("The citation must be a valid http or https URL.")
            role = _text(fields.get("role"), 20)
            if role not in {"current", "comparison"}:
                raise ValueError("Choose current or comparison release.")
            doc = app.state.service.ingest(security_id, raw, filename, url, published_at=_text(fields.get("published_at"), 80) or None, sec_headers=headers,
                                           role=role, association="user_asserted")
            message = {"parsed": "Source preserved and parsed. You can now generate a research note.",
                       "needs_review": "Source preserved and its figures were read, but the release does not establish which quarter it reports. Generate a note to see the columns, or record the reported period explicitly."}.get(
                doc["extraction_status"], "Source preserved, but this layout was not parsed. Supply a supported HTML summary table to extract figures.")
            return redirect("/company/" + security_id, message)
        except ValueError as exc:
            return redirect("/company/" + security_id, _error(exc))
        finally:
            await fields.close()

    @app.post("/company/{security_id}/import-url")
    async def import_source(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        if app.state.offline:
            return redirect("/company/" + security_id, "Offline mode: remote fetching is disabled. Upload a saved HTML release instead.")
        try:
            from .sources import import_url
            role = _text(fields.get("role"), 20) or "current"
            if role not in {"current", "comparison"}:
                raise ValueError("Choose current or comparison release.")
            await run_in_threadpool(import_url, app.state.service, security_id, _text(fields.get("source_url"), 2000), role=role, published_at=_text(fields.get("published_at"), 80) or None)
            return redirect("/company/" + security_id, "Source fetched and preserved. Check its extraction status below.")
        except (ValueError, RuntimeError) as exc:
            return redirect("/company/" + security_id, _error(exc))

    @app.post("/company/{security_id}/refresh")
    async def refresh(security_id: str, request: Request):
        await form(request)
        security_or_404(security_id)
        if app.state.offline:
            return redirect("/company/" + security_id, "Offline mode: SEC refresh is disabled. Saved sources remain available.")
        try:
            from .sources import refresh_security
            result = await run_in_threadpool(refresh_security, app.state.service, security_id)
            return redirect("/company/" + security_id, result.get("message", "Refresh finished. Inspect source health for details."))
        except (ValueError, RuntimeError) as exc:
            return redirect("/company/" + security_id, _error(exc))

    @app.post("/company/{security_id}/notes")
    async def generate(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        try:
            mode = _text(fields.get("mode"), 20)
            if mode not in {"observed", "public"}:
                raise ValueError("Choose observed or public reconstruction mode.")
            saved = app.state.service.generate_note(security_id, _text(fields.get("current_id"), 100), comparison_id=_text(fields.get("comparison_id"), 100) or None,
                                                   as_of=_text(fields.get("as_of"), 80) or None, mode=mode,
                                                   period=_text(fields.get("period"), 60) or None,
                                                   reporting_currency=_text(fields.get("reporting_currency"), 3).upper() or None)
            return redirect("/note/" + saved["id"], "Research note saved.")
        except ValueError as exc:
            return redirect("/company/" + security_id, _error(exc))

    @app.get("/note/{note_id}", response_class=HTMLResponse)
    def note(note_id: str, request: Request):
        saved = note_or_404(note_id)
        sec = security_or_404(saved["security_id"])
        result = saved["result"]
        from .. import earnings
        facts = result.get("facts", [])
        highlights = [f for f in facts if f.get("metric") in {"revenue", "eps_diluted", "net_income"} and f.get("basis") != "NON-GAAP"
                      and not any("CONFLICT" in flag for flag in f.get("flags", []))][:3]
        eligible = result.get("cutoff", {}).get("current_release_eligible", False)
        return render(request, "note.html", page="note", note=saved, company=sec, result=result, highlights=highlights, eligible=eligible,
                      annotations=app.state.store.annotations(note_id), full_note=markdown.render(saved["markdown"]),
                      questions=earnings.questions(result) if eligible else [])

    @app.post("/note/{note_id}/annotations")
    async def annotate(note_id: str, request: Request):
        fields = await form(request)
        note_or_404(note_id)
        try:
            thesis, invalidation, review = (_text(fields.get(k)) for k in ("thesis", "invalidation", "review_condition"))
            if not any((thesis, invalidation, review)):
                raise ValueError("Write a thesis, invalidation condition or review condition before saving.")
            app.state.store.annotate(note_id, thesis, invalidation, review)
            return redirect("/note/" + note_id, "Your annotation was saved as a new version.")
        except ValueError as exc:
            return redirect("/note/" + note_id, _error(exc))

    @app.get("/note/{note_id}/export.md")
    def export_markdown(note_id: str):
        saved = note_or_404(note_id)
        text = saved["markdown"]
        annotations = app.state.store.annotations(note_id)
        if annotations:
            latest = annotations[0]
            # Human annotations remain plain escaped text in a clearly separate section.
            text += "\n## User research annotation (not an extracted fact)\n\n"
            for label, key in (("Thesis", "thesis"), ("Invalidation", "invalidation"), ("Next review", "review_condition")):
                value = str(latest.get(key, "")).replace("\r", "").replace("\n", " ")
                text += f"- {label}: " + re.sub(r"([\\`*_[\]<>!|])", r"\\\1", value) + "\n"
        return Response(text, media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="kod-research-note.md"', "Cache-Control": "no-store"})

    @app.get("/note/{note_id}/export.json")
    def export_json(note_id: str):
        saved = note_or_404(note_id)
        data = {**saved, "annotations": app.state.store.annotations(note_id), "entry_permission": False}
        return Response(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="kod-research-note.json"', "Cache-Control": "no-store"})

    @app.get("/source/{document_id}")
    def source(document_id: str):
        try:
            app.state.store.document(document_id)
            raw = app.state.store.raw(document_id)
        except (ValueError, KeyError):
            raise HTTPException(404, "Source not found or its stored hash could not be verified.")
        return PlainTextResponse(raw.decode("utf-8", "replace"), headers={"Cache-Control": "no-store", "Content-Disposition": "inline"})

    def build_dossier(security_id, request, as_of="", mode="", policy="", view="", question=""):
        security_or_404(security_id)
        if view not in ("", "as_reported", "latest"):
            raise HTTPException(400, "Choose the as-reported or latest view.")
        chosen = _policy(app.state.service.clock, as_of, mode, policy)
        try:
            question = _text(question, 400) or None
        except ValueError as exc:
            raise HTTPException(400, _error(exc))
        return dossier_model.build(app.state.service, security_id, chosen, view or "as_reported", question), chosen

    @app.get("/company/{security_id}/dossier", response_class=HTMLResponse)
    def company_dossier(security_id: str, request: Request, as_of: str = "", mode: str = "", policy: str = "", view: str = "", question: str = ""):
        d, chosen = build_dossier(security_id, request, as_of, mode, policy, view, question)
        query = _policy_query(chosen) + "&" + urlencode({"view": d["view"]})
        return render(request, "dossier.html", page="dossier", company=app.state.store.get_security(security_id), d=d, query=query,
                      quarterly=dossier_model.history_table(d, "quarterly"), annual=dossier_model.history_table(d, "annual"),
                      balances=dossier_model.history_table(d, "instant"), changes={c["key"]: c for c in d["changes"]},
                      policy_name=next(k for k, v in POLICIES.items() if v == chosen.policy_version))

    @app.get("/company/{security_id}/dossier.json")
    def dossier_json(security_id: str, request: Request, as_of: str = "", mode: str = "", policy: str = "", view: str = "", question: str = ""):
        d, _ = build_dossier(security_id, request, as_of, mode, policy, view, question)
        return Response(json.dumps({**d, "entry_permission": False}, indent=2, ensure_ascii=False, allow_nan=False), media_type="application/json",
                        headers={"Content-Disposition": 'attachment; filename="kod-dossier.json"', "Cache-Control": "no-store"})

    @app.get("/company/{security_id}/dossier.md")
    def dossier_markdown(security_id: str, request: Request, as_of: str = "", mode: str = "", policy: str = "", view: str = "", question: str = ""):
        d, _ = build_dossier(security_id, request, as_of, mode, policy, view, question)
        return Response(dossier_model.render_markdown(d), media_type="text/markdown",
                        headers={"Content-Disposition": 'attachment; filename="kod-dossier.md"', "Cache-Control": "no-store"})

    @app.get("/company/{security_id}/dossier/calculation/{calc_id}", response_class=HTMLResponse)
    def calculation_page(security_id: str, calc_id: str, request: Request, as_of: str = "", mode: str = "", policy: str = "", view: str = ""):
        d, chosen = build_dossier(security_id, request, as_of, mode, policy, view)
        record = d["calculations"].get(calc_id)
        if record is None:
            raise HTTPException(404, "This calculation is not part of the dossier at the selected cutoff and view.")
        return render(request, "calculation.html", page="dossier", company=app.state.store.get_security(security_id), d=d, calc=record,
                      query=_policy_query(chosen) + "&" + urlencode({"view": d["view"]}))

    @app.get("/observation/{observation_id}", response_class=HTMLResponse)
    def observation_page(observation_id: str, request: Request, as_of: str = "", mode: str = "", policy: str = ""):
        found = FinancialRepository(app.state.store)._query("o.id=?", (observation_id,))
        if not found:
            raise HTTPException(404, "Observation not found.")
        o = found[0]
        chosen = _policy(app.state.service.clock, as_of, mode, policy) if as_of else None
        if chosen is not None and not eligibility(o.availability(), chosen)[0]:
            raise HTTPException(404, "This observation is not eligible at the selected cutoff.")
        security_id = o.security_id
        source_entry, check = None, None
        if o.provider == "sec_companyfacts" and o.source_document_id:
            try:
                from .companyfacts import resolve_pointer
                node = resolve_pointer(json.loads(app.state.store.raw(o.source_document_id), parse_float=Decimal, parse_int=Decimal), o.evidence["json_pointer"])
                source_entry = node
                check = Decimal(str(node.get("val"))) == o.value
            except (ValueError, KeyError, IndexError, TypeError, ArithmeticError):
                source_entry, check = None, False
        return render(request, "observation.html", page="dossier", o=o, company=app.state.store.get_security(security_id) if security_id else None,
                      source_entry=json.dumps(source_entry, indent=1, default=str) if source_entry is not None else None, pointer_check=check,
                      evidence=json.dumps(o.evidence, indent=1, ensure_ascii=False))

    @app.get("/search", response_class=HTMLResponse)
    def search_page(request: Request, q: str = "", company: str = "", period: str = "", source: str = "", as_of: str = "", mode: str = "", policy: str = ""):
        chosen = _policy(app.state.service.clock, as_of, mode, policy)
        if company:
            security_or_404(company)
        try:
            result = archive.search(app.state.store, app.state.service.archive, q[:archive.MAX_QUERY], chosen, [company] if company else None,
                                    period.strip()[:60] or None, [source] if source else None) if q.strip() else None
        except ValueError as exc:
            raise HTTPException(400, _error(exc))
        return render(request, "search.html", page="search", result=result, q=q[:archive.MAX_QUERY], selected=company, period=period[:60], source=source,
                      source_types=archive.SOURCE_TYPES, policy=chosen, policy_name=next(k for k, v in POLICIES.items() if v == chosen.policy_version),
                      query=_policy_query(chosen))

    @app.get("/source/{document_id}/passage/{index}", response_class=HTMLResponse)
    def passage_page(document_id: str, index: int, request: Request, as_of: str = "", mode: str = "", policy: str = ""):
        chosen = _policy(app.state.service.clock, as_of, mode, policy) if as_of else None
        try:
            context = archive.passage_context(app.state.store, app.state.service.archive, document_id, index, chosen)
        except (ValueError, KeyError) as exc:
            raise HTTPException(404, _error(exc))
        return render(request, "passage.html", page="search", ctx=context, company=app.state.store.get_security(context["document"]["security_id"]))

    @app.get("/health", response_class=HTMLResponse)
    def health(request: Request):
        return render(request, "health.html", page="health", health=app.state.store.health(), jobs=app.state.store.jobs()[:30], sec_configured=bool(os.environ.get("KOD_SEC_CONTACT")))

    return app

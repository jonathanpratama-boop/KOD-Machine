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
import sqlite3
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import decisions
from . import dossier as dossier_model
from . import model as fcff
from . import thesis as conditions
from . import prices as price_rules
from . import scenarios, companyfacts
from . import search as archive
from .domain import timestamp
from .financials import FinancialRepository
from .policy import DAY_END, STRICT, AsOfPolicy, eligibility
from .services import ResearchService
from .store import Store
from .forecasts import ForecastArchive, ForecastUnavailable
from .replay import ReplayArchive, ReplayUnavailable
from .research import ResearchArchive, ResearchUnavailable
from .operations import (
    OperationsArchive,
    OperationsUnavailable,
    TimingArchive,
    health_rows,
    brief,
    timing_timeline,
    timing_context_views,
)

ASSETS = Path(__file__).resolve().parent
MAX_BODY = 10 * 1024 * 1024
MAX_UPLOAD = 8 * 1024 * 1024
COOKIE = "kod_workstation_csrf"
METRICS = {
    "revenue": "Revenue",
    "net_income": "Net income",
    "operating_income": "Operating income",
    "operating_expenses": "Operating expenses",
    "gross_margin": "Gross margin",
    "eps_diluted": "Diluted EPS",
}


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
                    return await PlainTextResponse("Cross-origin changes are refused.", 403)(
                        scope, receive, send
                    )
            if headers.get("sec-fetch-site") == "cross-site":
                return await PlainTextResponse("Cross-site changes are refused.", 403)(
                    scope, receive, send
                )
        try:
            if int(headers.get("content-length", "0")) > MAX_BODY:
                return await PlainTextResponse("The request is too large (10 MiB maximum).", 413)(
                    scope, receive, send
                )
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
                message.setdefault("headers", []).extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        # 'same-origin', not 'no-referrer': under no-referrer a browser sends "Origin: null" on its own form posts, which the Origin check
                        # above (rightly) refuses. Cross-site requests still carry no referrer.
                        (b"referrer-policy", b"same-origin"),
                        (b"x-frame-options", b"DENY"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; style-src 'self'; img-src 'self' data:; script-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",
                        ),
                    ]
                )
            await send(message)

        try:
            await self.app(scope, limited, security_headers)
        except _BodyTooLarge:
            await PlainTextResponse("The request is too large (10 MiB maximum).", 413)(
                scope, receive, send
            )


def safe_url(value):
    """Citation links do not imply authentication; allow only ordinary public URL syntax."""
    try:
        p = urlsplit(str(value))
        if (
            p.scheme in {"http", "https"}
            and p.hostname
            and not p.username
            and not p.password
            and not any(c in str(value) for c in "\r\n\x00")
        ):
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
    return (
        str(value).replace("T", " ").replace("+00:00", " UTC").replace("Z", " UTC")
        if value
        else "Unknown"
    )


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
MILLION = Decimal(10) ** 6
PERCENT_FIELDS = (
    "revenue_growth",
    "operating_margin",
    "cash_tax_rate",
    "depreciation_rate",
    "capex_rate",
    "nwc_rate",
    "discount_rate",
    "terminal_growth",
    "terminal_roic",
)


def _plain(value: Decimal) -> str:
    """Exact fixed-point text without exponent or trailing zeros ('60922000000', '0.25', '-0.1')."""
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "") else text


def _percent_list(text, name):
    """'30, 25, 20' (percent) -> ['0.3', '0.25', '0.2'] exactly; one value means every year."""
    parts = [p.strip() for p in str(text or "").replace(";", ",").split(",") if p.strip()]
    if not parts:
        raise ValueError(f"{fcff.LABELS[name]} is required")
    out = []
    for part in parts:
        try:
            value = Decimal(part.rstrip("%"))
        except ArithmeticError:
            raise ValueError(f"{fcff.LABELS[name]}: {part!r} is not a number")
        if not value.is_finite():
            raise ValueError(f"{fcff.LABELS[name]} must be finite")
        out.append(_plain(value / 100))
    return out if len(out) > 1 or name in fcff.VECTOR else out[0]


def _millions(text, name, required=False):
    text = str(text or "").strip().replace(",", "")
    if not text:
        if required:
            raise ValueError(f"{name} is required")
        return None
    try:
        value = Decimal(text)
    except ArithmeticError:
        raise ValueError(f"{name}: {text!r} is not a number")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    return _plain(value * MILLION)


def assumptions_from_form(fields) -> dict:
    """The assumption record from the model form: rates in percent, amounts and share counts in millions; stored exactly in base units and fractions."""
    raw = {
        "horizon_years": int(_text(fields.get("horizon_years"), 3) or 0),
        "currency": _text(fields.get("currency"), 3).upper(),
        "valuation_date": _text(fields.get("valuation_date"), 10),
        "base": {
            "revenue": _millions(fields.get("base_revenue"), "Base revenue", True),
            "fiscal_year_end": _text(fields.get("base_fiscal_year_end"), 10),
        },
    }
    for name in PERCENT_FIELDS:
        value = _percent_list(fields.get(name), name)
        raw[name] = value[0] if isinstance(value, list) and len(value) == 1 else value
    raw["bridge"] = {k: _millions(fields.get(k), k.replace("_", " ")) for k in fcff.BRIDGE}
    raw["bridge"]["as_of"] = _text(fields.get("bridge_as_of"), 10) or None
    raw["shares"] = {
        "count": _millions(fields.get("share_count"), "share count"),
        "as_of": _text(fields.get("share_count_as_of"), 10) or None,
        "basis": _text(fields.get("share_count_basis"), 300) or None,
    }
    raw["treatments"] = {k: _text(fields.get("treatment_" + k), 40) for k in fcff.TREATMENTS}
    cited = [
        i
        for i in _text(fields.get("cited_observations"), 2000).split()
        if re.fullmatch(r"fob_[0-9a-f]{24}", i)
    ]
    if cited:
        raw["sources"] = {"base_revenue": {"observation_ids": cited}}
    return raw


def form_from_assumptions(raw: dict) -> dict:
    """Pre-fill values for the form from a stored version (the inverse of assumptions_from_form)."""

    def pct(v):
        return ", ".join(_plain(Decimal(x) * 100) for x in (v if isinstance(v, list) else [v]))

    def mil(v):
        return "" if v in (None, "") else _plain(Decimal(v) / MILLION)

    out = {
        "horizon_years": raw.get("horizon_years"),
        "currency": raw.get("currency"),
        "valuation_date": raw.get("valuation_date"),
        "base_revenue": mil((raw.get("base") or {}).get("revenue")),
        "base_fiscal_year_end": (raw.get("base") or {}).get("fiscal_year_end"),
    }
    out.update({name: pct(raw[name]) for name in PERCENT_FIELDS if raw.get(name) is not None})
    out.update({k: mil((raw.get("bridge") or {}).get(k)) for k in fcff.BRIDGE})
    out["bridge_as_of"] = (raw.get("bridge") or {}).get("as_of") or ""
    shares = raw.get("shares") or {}
    out.update(
        {
            "share_count": mil(shares.get("count")),
            "share_count_as_of": shares.get("as_of") or "",
            "share_count_basis": shares.get("basis") or "",
        }
    )
    out.update({"treatment_" + k: v for k, v in (raw.get("treatments") or {}).items()})
    out["cited_observations"] = " ".join(
        ((raw.get("sources") or {}).get("base_revenue") or {}).get("observation_ids", [])
    )
    return out


BUILDER_ROWS = 4


def conditions_from_form(fields) -> list:
    """Conditions from the builder rows (one comparison each) plus an optional JSON list for nested all/any/not expressions. Both are validated against the
    typed schema; JSON is parsed, never executed."""
    out = []
    for i in range(1, BUILDER_ROWS + 1):
        label, left = _text(fields.get(f"c{i}_label"), 300), _text(fields.get(f"c{i}_left"), 120)
        if not label and not left:
            continue
        op = _text(fields.get(f"c{i}_op"), 2)
        right_code = _text(fields.get(f"c{i}_right"), 120)
        right = (
            conditions.operand_from_code(right_code)
            if right_code != "constant"
            else {
                "kind": "constant",
                "value": _text(fields.get(f"c{i}_value"), 40),
                "unit": _text(fields.get(f"c{i}_unit"), 20),
            }
        )
        if right["kind"] == "constant" and right["unit"] in ("currency", "currency/share"):
            right["currency"] = _text(fields.get(f"c{i}_currency"), 3).upper()
        out.append(
            {
                "id": f"c{i}",
                "label": label,
                "expression": {
                    "op": op,
                    "left": conditions.operand_from_code(left),
                    "right": right,
                },
            }
        )
    advanced = _text(fields.get("advanced_conditions"), 20000)
    if advanced:
        for c in conditions.parse_conditions(advanced):
            if any(c["id"] == o["id"] for o in out):
                raise ValueError(f"condition id {c['id']} is used twice")
            out.append(c)
    return conditions.validate_conditions(out)


def _grid_values(text, center, step):
    """Grid axis values in percent ('8, 9, 10'), or five values around the saved level when empty."""
    if text.strip():
        values = [Decimal(p.strip().rstrip("%")) / 100 for p in text.split(",") if p.strip()]
    else:
        values = [center + step * k for k in (-2, -1, 0, 1, 2)]
    if not 1 <= len(values) <= 9 or not all(v.is_finite() for v in values):
        raise ValueError("each grid axis takes 1 to 9 finite values")
    return values


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
    except (ValueError, OverflowError) as exc:
        raise HTTPException(400, "Invalid information cutoff: " + _error(exc))


def _policy_query(policy):
    name = next(k for k, v in POLICIES.items() if v == policy.policy_version)
    return urlencode({"as_of": policy.as_dict()["cutoff"], "mode": policy.mode, "policy": name})


def create_app(
    data_dir,
    offline=False,
    service=None,
    *,
    testing=False,
    replay_db=None,
    forecast_dir=None,
    runtime_root=None,
):
    """Build an app with explicit runtime state; no import-time IO or collection."""
    app = FastAPI(title="KOD Workstation", docs_url=None, redoc_url=None)
    app.add_middleware(LocalBoundary)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost"] + (["testserver"] if testing else []),
    )
    app.state.service = service or ResearchService(Store(Path(data_dir)))
    app.state.store = app.state.service.store
    app.state.offline = bool(offline)
    app.state.replay_db = (
        Path(replay_db) if replay_db is not None else ASSETS.parents[1] / "var" / "kod.db"
    )
    app.state.forecast_dir = Path(forecast_dir) if forecast_dir is not None else None
    app.state.runtime_root = runtime_root
    signing_key = secrets.token_bytes(32)
    templates = Jinja2Templates(directory=str(ASSETS / "templates"))
    templates.env.filters.update(moment=_display_time, number=_number)

    def ops_percent(value):
        if value is None:
            return "—"
        try:
            number = Decimal(str(value))
            return f"{number * 100:,.1f}%" if number.is_finite() else "—"
        except Exception:
            return "—"

    templates.env.filters.update(
        ops_brief=brief,
        ops_percent=ops_percent,
        ops_pretty=lambda value: json.dumps(
            value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False
        ),
    )
    templates.env.globals.update(
        show=dossier_model.display,
        metric_label=lambda m: dossier_model.LABELS.get(m, str(m).replace("_", " ")),
    )
    templates.env.globals.update(
        available=_available,
        metric=lambda key: METRICS.get(key, str(key).replace("_", " ").title()),
        unit=_unit,
        safe_url=safe_url,
    )
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
        common = {
            "request": request,
            "csrf": token,
            "offline": app.state.offline,
            "securities": app.state.store.securities(),
            "message": request.query_params.get("message", "")[:600],
        }
        response = templates.TemplateResponse(
            request=request, name=template, context={**common, **context}, status_code=status_code
        )
        response.set_cookie(
            COOKIE, token, httponly=True, samesite="strict", max_age=8 * 3600, path="/"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    async def form(request, max_fields=20):
        fields = await request.form(max_files=2, max_fields=max_fields)
        cookie, token = request.cookies.get(COOKIE, ""), str(fields.get("csrf", ""))
        if not valid_token(cookie) or not hmac.compare_digest(cookie, token):
            raise HTTPException(
                403, "This form expired or could not be verified. Reload the page and try again."
            )
        return fields

    def redirect(path, message=None):
        joiner = "&" if "?" in path else "?"
        return RedirectResponse(
            path + (joiner + urlencode({"message": message}) if message else ""), status_code=303
        )

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
        return render(
            request,
            "error.html",
            status_code=exc.status_code,
            title="Unable to complete this request",
            error=exc.detail,
            page="error",
        )

    def operations_page(request, page, *, query="", state="", status="", candidate_id=None):
        """Render a verified runner projection. Reading never changes operational state."""
        titles = {
            "today": ("Today", "Review the latest recorded run, its coverage and the work ahead."),
            "candidates": (
                "Candidates",
                "Inspect detections, supporting evidence and unresolved blockers.",
            ),
            "candidate": (
                "Candidate detail",
                "Trace the recorded observation through context, blockers and plan.",
            ),
            "market_map": (
                "Market map",
                "See which groups participated in the recorded market move.",
            ),
            "paper_portfolio": (
                "Paper portfolio",
                "Inspect simulated cash, positions, orders and fills.",
            ),
            "experiments": (
                "Experiments",
                "Track research status without turning an experiment into a trading policy.",
            ),
        }
        title, description = titles[page]
        context = {
            "page": page,
            "ops_title": title,
            "ops_description": description,
            "ops_error": None,
            "query": query[:200].strip(),
            "selected_state": state,
            "selected_status": status,
        }
        try:
            snap = OperationsArchive(app.state.runtime_root).snapshot()
            payload = snap["payload"]
            run = payload["run"]
            candidates = payload["candidates"]
            experiments = payload["experiments"]
            pattern = context["query"].casefold()
            context.update(
                snapshot=snap,
                payload=payload,
                sources=health_rows(payload["health"]),
                synthetic=bool(run.get("synthetic"))
                or str(run.get("mode", "")).lower()
                in {"demo", "synthetic", "synthetic_demo", "fixture"},
                blocked_count=sum(bool(c.get("blockers")) for c in candidates),
                states=sorted({str(c.get("state", "UNKNOWN")) for c in candidates}),
                candidates=[
                    c
                    for c in candidates
                    if (not state or c.get("state") == state)
                    and (not pattern or pattern in brief(c).casefold())
                ],
                groups=payload["market_context"].get("groups", []),
                experiment_statuses=sorted({str(e.get("status", "UNKNOWN")) for e in experiments}),
                experiments=[
                    e
                    for e in experiments
                    if (not status or e.get("status") == status)
                    and (not pattern or pattern in brief(e).casefold())
                ],
            )
            if candidate_id is not None:
                candidate = next((c for c in candidates if c["id"] == candidate_id), None)
                if candidate is None:
                    raise HTTPException(
                        404, "Candidate not found in the recorded runtime snapshot."
                    )
                context["candidate"] = candidate
        except OperationsUnavailable as exc:
            context["ops_error"] = str(exc)
        return render(request, "operations.html", **context)

    @app.get("/today", response_class=HTMLResponse)
    def today(request: Request):
        return operations_page(request, "today")

    @app.get("/timing", response_class=HTMLResponse)
    def timing_page(request: Request):
        context = {"page": "timing", "timing_error": None}
        try:
            snapshot = TimingArchive(app.state.runtime_root).snapshot()
            payload = snapshot["payload"]
            candidate_ids, run_id = set(), None
            try:
                operations = OperationsArchive(app.state.runtime_root).snapshot()["payload"]
                candidate_ids = {row["id"] for row in operations["candidates"]}
                run_id = operations["run"].get("id")
            except OperationsUnavailable:
                pass
            details = {row["id"]: row for row in payload["summary"]["records"]}
            attempts = sorted(payload["attempts"], key=lambda row: row["recorded_at"], reverse=True)
            context.update(
                snapshot=snapshot,
                timing=payload,
                summary=payload["summary"],
                attempts=attempts[:100],
                retained_count=len(attempts),
                details=details,
                context_views=timing_context_views(payload),
                timeline=timing_timeline,
                owned_candidate_ids=candidate_ids,
                owned_run_id=run_id,
                synthetic=any(row["evidence_kind"] == "synthetic" for row in attempts),
            )
        except OperationsUnavailable as exc:
            context["timing_error"] = str(exc)
        return render(request, "timing.html", **context)

    @app.get("/candidates", response_class=HTMLResponse)
    def candidates_page(request: Request, q: str = "", state: str = ""):
        return operations_page(request, "candidates", query=q, state=state)

    @app.get("/candidate/{candidate_id:path}", response_class=HTMLResponse)
    def candidate_page(candidate_id: str, request: Request):
        return operations_page(request, "candidate", candidate_id=candidate_id)

    @app.get("/market-map", response_class=HTMLResponse)
    def market_map(request: Request):
        return operations_page(request, "market_map")

    @app.get("/paper-portfolio", response_class=HTMLResponse)
    def paper_portfolio(request: Request):
        return operations_page(request, "paper_portfolio")

    @app.get("/experiments", response_class=HTMLResponse)
    def experiments_page(request: Request, q: str = "", status: str = ""):
        return operations_page(request, "experiments", query=q, status=status)

    @app.get("/investigate", response_class=HTMLResponse)
    def investigate(request: Request, as_of: str = ""):
        """One explicit information cutoff across independent preserved evidence stores."""
        chosen = _policy(app.state.service.clock, as_of, "observed", "strict")
        cases, ledger_error = [], None
        try:
            cases = ReplayArchive(app.state.replay_db).cases()
        except (ReplayUnavailable, OSError, sqlite3.Error):
            ledger_error = (
                "The frozen case ledger is unavailable. Company evidence remains accessible."
            )
        population, population_error = [], None
        try:
            from .research import ResearchArchive

            population = ResearchArchive().studies()
        except ModuleNotFoundError as exc:
            if exc.name != "kod.workstation.research":
                raise
            population_error = "Preserved research adapter not connected."
        except (OSError, ValueError):
            population_error = (
                "Preserved research catalog is unavailable; no study results were substituted."
            )
        return render(
            request,
            "investigate.html",
            page="investigate",
            cutoff=chosen.as_dict()["cutoff"],
            query=_policy_query(chosen),
            cases=cases,
            ledger_error=ledger_error,
            workbench_query=lambda **params: urlencode(params),
            population=population,
            population_error=population_error,
        )

    @app.get("/research/{study_id}", response_class=HTMLResponse)
    def research_study(study_id: str, request: Request, as_of: str = ""):
        try:
            cutoff = timestamp(as_of.strip() or app.state.service.clock())
        except ValueError as exc:
            raise HTTPException(400, "Choose a timezone-qualified information cutoff.") from exc
        try:
            study = ResearchArchive().study(study_id, as_of=cutoff)
        except ResearchUnavailable as exc:
            raise HTTPException(404, str(exc)) from exc
        return render(
            request,
            "research.html",
            page="investigate",
            study=study,
            as_of=cutoff,
            research_now=app.state.service.clock(),
            research_query=lambda **params: urlencode(params),
        )

    @app.get("/replay", response_class=HTMLResponse)
    def event_replay(
        request: Request,
        case_id: str = "",
        as_of: str = "",
        minimum_grade: str = "D",
        reveal: str = "",
    ):
        """Read an immutable ledger snapshot; never collect or write research here."""
        cases, snapshot, selected, error = [], None, None, None
        try:
            replay = ReplayArchive(app.state.replay_db)
            cases = replay.cases()
            if cases:
                selected = next((c for c in cases if c["case_id"] == case_id), None)
                if case_id and selected is None:
                    raise HTTPException(404, "Replay event not found.")
                selected = selected or max(
                    (c for c in cases if c["call_type"] != "SIMULATED"),
                    key=lambda c: c["opened_at"],
                    default=cases[0],
                )
                cutoff = as_of.strip() or selected["decision_cutoff"]
                snapshot = replay.snapshot(
                    selected["case_id"],
                    cutoff,
                    reveal_outcome=reveal == "outcome",
                    minimum_grade=minimum_grade,
                )
        except ReplayUnavailable as exc:
            error = str(exc)
        except (ValueError, KeyError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except (OSError, sqlite3.Error):
            error = "The preserved ledger is unavailable. Replay reads the existing var/kod.db; it does not create a replacement or fetch live data."
        return render(
            request,
            "replay.html",
            page="replay",
            cases=cases,
            selected=selected,
            snapshot=snapshot,
            replay_error=error,
            minimum_grade=minimum_grade,
            outcome_requested=reveal == "outcome",
            replay_query=lambda **params: urlencode(params),
            replay_now=app.state.service.clock(),
        )

    @app.get("/forecasts", response_class=HTMLResponse)
    def forecast_replay(request: Request, set_id: str = "", as_of: str = "", reveal: str = ""):
        """Read a sealed market forecast at a chosen moment; never recompute, fetch or write."""
        forecasts, snap, error = [], None, None
        try:
            archive = ForecastArchive(app.state.forecast_dir)
            forecasts = archive.forecasts()
            if forecasts:
                chosen = next((f for f in forecasts if f["set_id"] == set_id), None)
                if set_id and chosen is None:
                    raise HTTPException(404, "Forecast not found.")
                chosen = chosen or forecasts[0]
                snap = archive.snapshot(
                    chosen["set_id"],
                    as_of.strip() or chosen["made_at"],
                    reveal_outcome=reveal == "outcome",
                )
        except ForecastUnavailable as exc:
            error = str(exc)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except OSError:
            error = "The forecast ledger is unavailable. This page reads idx-signals/paper; it creates nothing."
        return render(
            request,
            "forecasts.html",
            page="forecasts",
            forecast_list=forecasts,
            snap=snap,
            forecast_error=error,
            outcome_requested=reveal == "outcome",
            forecast_query=lambda **params: urlencode(params),
        )

    @app.get("/", response_class=HTMLResponse)
    def inbox(
        request: Request,
        security: str = "",
        category: str = "",
        status: str = "",
        q: str = "",
        after: str = "",
        before: str = "",
    ):
        store = app.state.store
        securities = store.securities()
        by_id = {s["id"]: s for s in securities}
        events = store.events(security or None)
        referenced = {event.get("document_id") for event in events}
        rows = [
            {
                **event,
                "kind": event.get("form", "Filing"),
                "status": event.get("metadata", {}).get("extraction_status", "filing"),
                "company": by_id.get(event["security_id"]),
            }
            for event in events
        ]
        for doc in store.documents(security or None):
            if (
                doc["id"] not in referenced
                and doc.get("role") != "metadata"
                and doc.get("provider") not in {"sec_submissions", "sec_mapping"}
            ):
                rows.append(
                    {
                        **doc,
                        "kind": "RELEASE",
                        "title": doc["filename"],
                        "status": doc["extraction_status"],
                        "company": by_id.get(doc["security_id"]),
                        "document_id": doc["id"],
                    }
                )
        rows = [
            r
            for r in rows
            if (not category or r["kind"] == category)
            and (not status or r["status"] == status)
            and (
                not q or q.lower() in (r.get("title", "") + " " + str(r.get("company", {}))).lower()
            )
            and (not after or _available_key(r)[:10] >= after)
            and (not before or bool(_available_key(r)) and _available_key(r)[:10] <= before)
        ]
        rows.sort(key=lambda r: (_available_key(r), r.get("observed_at") or ""), reverse=True)
        return render(
            request,
            "inbox.html",
            page="inbox",
            rows=rows[:250],
            total=len(rows),
            notes=store.notes(),
            selected=security,
            category=category,
            selected_status=status,
            q=q[:200],
            after=after,
            before=before,
        )

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
            sec = app.state.store.upsert_security(
                ticker, name, cik=cik, venue=venue, currency=currency, association="user_asserted"
            )
            return redirect(
                "/company/" + sec["id"],
                "Company added. Identity is user asserted until verified from filing metadata.",
            )
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
            return redirect(
                "/",
                "Offline mode: ticker lookup is disabled. Add an explicit company and CIK instead.",
            )
        try:
            from .sources import SecClient

            client = SecClient()
            identity = await run_in_threadpool(client.resolve, _text(fields.get("ticker"), 32))
            raw = getattr(client, "last_mapping_raw", None)
            observed = getattr(client, "last_mapping_observed_at", None)
            if not isinstance(raw, bytes) or not raw or not isinstance(observed, str):
                raise ValueError(
                    "SEC identity lookup did not retain its source evidence. Add an explicit identity or retry."
                )
            sec = app.state.store.upsert_security(**identity)
            mapping_url = "https://www.sec.gov/files/company_tickers_exchange.json"
            app.state.store.save_document(
                sec["id"],
                raw,
                "company_tickers_exchange.json",
                mapping_url,
                observed_at=observed,
                role="metadata",
                provider="sec_mapping",
                association="verified_from_filing_metadata",
                external_id=mapping_url,
                extraction_status="metadata",
                published_basis="Publication time unknown; current SEC listing metadata observed at retrieval",
                metadata={
                    "kind": "SEC current listing mapping",
                    "selected_ticker": identity["ticker"],
                    "selected_cik": identity.get("cik"),
                    "observed_basis": "fetched by this SEC ticker lookup",
                    "coverage_note": "Current listings only; not a historical security master",
                },
            )
            return redirect(
                "/company/" + sec["id"],
                "Company identity resolved from current SEC listing metadata.",
            )
        except (ValueError, RuntimeError) as exc:
            return redirect("/", _error(exc))

    @app.get("/company/{security_id}", response_class=HTMLResponse)
    def company(security_id: str, request: Request):
        sec = security_or_404(security_id)
        docs = app.state.store.documents(security_id)
        return render(
            request,
            "company.html",
            page="company",
            company=sec,
            documents=docs,
            parsed=[d for d in docs if d.get("extraction_status") in ("parsed", "needs_review")],
            events=app.state.store.events(security_id),
            notes=app.state.store.notes(security_id),
        )

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
                raise ValueError(
                    "This version accepts .html or .htm earnings releases. PDF is not supported."
                )
            raw = await document.read(MAX_UPLOAD + 1)
            if len(raw) > MAX_UPLOAD:
                raise ValueError("The release exceeds the 8 MiB upload limit.")
            header = fields.get("sec_headers")
            headers = (
                await header.read(1024 * 1024 + 1)
                if hasattr(header, "read") and header.filename
                else None
            )
            if headers is not None and len(headers) > 1024 * 1024:
                raise ValueError("The SEC header file exceeds the 1 MiB limit.")
            url = (
                _text(fields.get("source_url"), 2000)
                or "https://example.invalid/local-file/" + filename
            )
            if not safe_url(url):
                raise ValueError("The citation must be a valid http or https URL.")
            role = _text(fields.get("role"), 20)
            if role not in {"current", "comparison"}:
                raise ValueError("Choose current or comparison release.")
            doc = app.state.service.ingest(
                security_id,
                raw,
                filename,
                url,
                published_at=_text(fields.get("published_at"), 80) or None,
                sec_headers=headers,
                role=role,
                association="user_asserted",
            )
            message = {
                "parsed": "Source preserved and parsed. You can now generate a research note.",
                "needs_review": "Source preserved and its figures were read, but the release does not establish which quarter it reports. Generate a note to see the columns, or record the reported period explicitly.",
            }.get(
                doc["extraction_status"],
                "Source preserved, but this layout was not parsed. Supply a supported HTML summary table to extract figures.",
            )
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
            return redirect(
                "/company/" + security_id,
                "Offline mode: remote fetching is disabled. Upload a saved HTML release instead.",
            )
        try:
            from .sources import import_url

            role = _text(fields.get("role"), 20) or "current"
            if role not in {"current", "comparison"}:
                raise ValueError("Choose current or comparison release.")
            await run_in_threadpool(
                import_url,
                app.state.service,
                security_id,
                _text(fields.get("source_url"), 2000),
                role=role,
                published_at=_text(fields.get("published_at"), 80) or None,
            )
            return redirect(
                "/company/" + security_id,
                "Source fetched and preserved. Check its extraction status below.",
            )
        except (ValueError, RuntimeError) as exc:
            return redirect("/company/" + security_id, _error(exc))

    @app.post("/company/{security_id}/refresh")
    async def refresh(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        if app.state.offline:
            return redirect(
                "/company/" + security_id,
                "Offline mode: SEC refresh is disabled. Saved sources remain available.",
            )
        try:
            from .sources import SourceUnavailable, refresh_companyfacts, refresh_security

            if fields.get("what") == "filed_history":
                try:
                    result = await run_in_threadpool(
                        refresh_companyfacts, app.state.service, security_id
                    )
                except SourceUnavailable as exc:
                    return redirect(
                        "/company/" + security_id,
                        "Filed-history refresh failed: " + _error(exc)[:300],
                    )
            else:
                result = await run_in_threadpool(refresh_security, app.state.service, security_id)
            return redirect(
                "/company/" + security_id,
                result.get("message", "Refresh finished. Inspect source health for details."),
            )
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
            saved = app.state.service.generate_note(
                security_id,
                _text(fields.get("current_id"), 100),
                comparison_id=_text(fields.get("comparison_id"), 100) or None,
                as_of=_text(fields.get("as_of"), 80) or None,
                mode=mode,
                period=_text(fields.get("period"), 60) or None,
                reporting_currency=_text(fields.get("reporting_currency"), 3).upper() or None,
            )
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
        highlights = [
            f
            for f in facts
            if f.get("metric") in {"revenue", "eps_diluted", "net_income"}
            and f.get("basis") != "NON-GAAP"
            and not any("CONFLICT" in flag for flag in f.get("flags", []))
        ][:3]
        eligible = result.get("cutoff", {}).get("current_release_eligible", False)
        return render(
            request,
            "note.html",
            page="note",
            note=saved,
            company=sec,
            result=result,
            highlights=highlights,
            eligible=eligible,
            annotations=app.state.store.annotations(note_id),
            full_note=markdown.render(saved["markdown"]),
            questions=earnings.questions(result) if eligible else [],
        )

    @app.post("/note/{note_id}/annotations")
    async def annotate(note_id: str, request: Request):
        fields = await form(request)
        note_or_404(note_id)
        try:
            thesis, invalidation, review = (
                _text(fields.get(k)) for k in ("thesis", "invalidation", "review_condition")
            )
            if not any((thesis, invalidation, review)):
                raise ValueError(
                    "Write a thesis, invalidation condition or review condition before saving."
                )
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
            for label, key in (
                ("Thesis", "thesis"),
                ("Invalidation", "invalidation"),
                ("Next review", "review_condition"),
            ):
                value = str(latest.get(key, "")).replace("\r", "").replace("\n", " ")
                text += f"- {label}: " + re.sub(r"([\\`*_[\]<>!|])", r"\\\1", value) + "\n"
        return Response(
            text,
            media_type="text/markdown",
            headers={
                "Content-Disposition": 'attachment; filename="kod-research-note.md"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/note/{note_id}/export.json")
    def export_json(note_id: str):
        saved = note_or_404(note_id)
        data = {
            **saved,
            "annotations": app.state.store.annotations(note_id),
            "entry_permission": False,
        }
        return Response(
            json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="kod-research-note.json"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/source/{document_id}")
    def source(document_id: str):
        try:
            app.state.store.document(document_id)
            raw = app.state.store.raw(document_id)
        except (ValueError, KeyError):
            raise HTTPException(404, "Source not found or its stored hash could not be verified.")
        return PlainTextResponse(
            raw.decode("utf-8", "replace"),
            headers={"Cache-Control": "no-store", "Content-Disposition": "inline"},
        )

    def build_dossier(security_id, request, as_of="", mode="", policy="", view="", question=""):
        security_or_404(security_id)
        if view not in ("", "as_reported", "latest"):
            raise HTTPException(400, "Choose the as-reported or latest view.")
        chosen = _policy(app.state.service.clock, as_of, mode, policy)
        try:
            question = _text(question, 400) or None
        except ValueError as exc:
            raise HTTPException(400, _error(exc))
        return dossier_model.build(
            app.state.service, security_id, chosen, view or "as_reported", question
        ), chosen

    @app.get("/company/{security_id}/dossier", response_class=HTMLResponse)
    def company_dossier(
        security_id: str,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
        view: str = "",
        question: str = "",
    ):
        d, chosen = build_dossier(security_id, request, as_of, mode, policy, view, question)
        query = _policy_query(chosen) + "&" + urlencode({"view": d["view"]})
        review = decisions.review(app.state.service, security_id, chosen, d["view"], d)
        return render(
            request,
            "dossier.html",
            page="dossier",
            company=app.state.store.get_security(security_id),
            d=d,
            query=query,
            review=review,
            packets=decisions.packets(app.state.service, security_id)[:10],
            shown=conditions.shown,
            quarterly=dossier_model.history_table(d, "quarterly"),
            annual=dossier_model.history_table(d, "annual"),
            balances=dossier_model.history_table(d, "instant"),
            changes={c["key"]: c for c in d["changes"]},
            policy_name=next(k for k, v in POLICIES.items() if v == chosen.policy_version),
        )

    @app.get("/company/{security_id}/dossier.json")
    def dossier_json(
        security_id: str,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
        view: str = "",
        question: str = "",
    ):
        d, _ = build_dossier(security_id, request, as_of, mode, policy, view, question)
        return Response(
            json.dumps(
                {**d, "entry_permission": False}, indent=2, ensure_ascii=False, allow_nan=False
            ),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="kod-dossier.json"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/company/{security_id}/dossier.md")
    def dossier_markdown(
        security_id: str,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
        view: str = "",
        question: str = "",
    ):
        d, _ = build_dossier(security_id, request, as_of, mode, policy, view, question)
        return Response(
            dossier_model.render_markdown(d),
            media_type="text/markdown",
            headers={
                "Content-Disposition": 'attachment; filename="kod-dossier.md"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/company/{security_id}/dossier/calculation/{calc_id}", response_class=HTMLResponse)
    def calculation_page(
        security_id: str,
        calc_id: str,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
        view: str = "",
    ):
        d, chosen = build_dossier(security_id, request, as_of, mode, policy, view)
        record = d["calculations"].get(calc_id)
        if record is None:
            raise HTTPException(
                404, "This calculation is not part of the dossier at the selected cutoff and view."
            )
        change = next((c for c in d["changes"] if c.get("calculation_id") == calc_id), None)
        return render(
            request,
            "calculation.html",
            page="dossier",
            company=app.state.store.get_security(security_id),
            d=d,
            calc=record,
            change=change,
            query=_policy_query(chosen) + "&" + urlencode({"view": d["view"]}),
        )

    @app.get("/observation/{observation_id}", response_class=HTMLResponse)
    def observation_page(
        observation_id: str, request: Request, as_of: str = "", mode: str = "", policy: str = ""
    ):
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

                node = resolve_pointer(
                    json.loads(
                        app.state.store.raw(o.source_document_id),
                        parse_float=Decimal,
                        parse_int=Decimal,
                    ),
                    o.evidence["json_pointer"],
                )
                source_entry = node
                check = Decimal(str(node.get("val"))) == o.value
            except (ValueError, KeyError, IndexError, TypeError, ArithmeticError):
                source_entry, check = None, False
        evidence = dict(o.evidence)
        if chosen is not None:
            # The SEC assigns 'frame' from the latest filing in the snapshot (possibly after the cutoff): not shown in a cutoff-bound view.
            evidence.pop("frame", None)
            if isinstance(source_entry, dict):
                source_entry = {k: v for k, v in source_entry.items() if k != "frame"}
        return render(
            request,
            "observation.html",
            page="dossier",
            o=o,
            company=app.state.store.get_security(security_id) if security_id else None,
            source_entry=json.dumps(source_entry, indent=1, default=str)
            if source_entry is not None
            else None,
            pointer_check=check,
            evidence=json.dumps(evidence, indent=1, ensure_ascii=False),
        )

    @app.get("/search", response_class=HTMLResponse)
    def search_page(
        request: Request,
        q: str = "",
        company: str = "",
        period: str = "",
        source: str = "",
        as_of: str = "",
        mode: str = "",
        policy: str = "",
    ):
        chosen = _policy(app.state.service.clock, as_of, mode, policy)
        if company:
            security_or_404(company)
        try:
            result = (
                archive.search(
                    app.state.store,
                    app.state.service.archive,
                    q[: archive.MAX_QUERY],
                    chosen,
                    [company] if company else None,
                    period.strip()[:60] or None,
                    [source] if source else None,
                )
                if q.strip()
                else None
            )
        except ValueError as exc:
            raise HTTPException(400, _error(exc))
        return render(
            request,
            "search.html",
            page="search",
            result=result,
            q=q[: archive.MAX_QUERY],
            selected=company,
            period=period[:60],
            source=source,
            source_types=archive.SOURCE_TYPES,
            policy=chosen,
            policy_name=next(k for k, v in POLICIES.items() if v == chosen.policy_version),
            query=_policy_query(chosen),
        )

    @app.get("/source/{document_id}/passage/{index}", response_class=HTMLResponse)
    def passage_page(
        document_id: str,
        index: int,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
    ):
        chosen = _policy(app.state.service.clock, as_of, mode, policy) if as_of else None
        try:
            context = archive.passage_context(
                app.state.store, app.state.service.archive, document_id, index, chosen
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(404, _error(exc))
        return render(
            request,
            "passage.html",
            page="search",
            ctx=context,
            company=app.state.store.get_security(context["document"]["security_id"]),
        )

    def version_or_404(security_id, version_id):
        try:
            version = scenarios.assumption_version(app.state.service, version_id)
        except ValueError:
            raise HTTPException(404, "Assumption version not found.")
        if version["security_id"] != security_id:
            raise HTTPException(404, "Assumption version not found for this company.")
        return version

    @app.get("/company/{security_id}/model", response_class=HTMLResponse)
    def model_page(security_id: str, request: Request, start: str = "", from_version: str = ""):
        sec = security_or_404(security_id)
        service = app.state.service
        sets = scenarios.assumption_sets(service, security_id)
        chosen = _policy(service.clock)
        classification = service.submissions_context(security_id, chosen)
        results = {
            s["latest_id"]: scenarios.run_version(
                service, s["latest_id"], policy=chosen, context=classification
            )
            for s in sets
        }
        reference = fcff.suggest_from_history(
            dossier_model.build(service, security_id, chosen, context=classification)
        )
        prefill, scenario, name = {}, "base", "default"
        if from_version:
            v = version_or_404(security_id, from_version)
            prefill, scenario, name = (
                form_from_assumptions(v["assumptions"]),
                v["scenario"],
                v["name"],
            )
        elif start == "history":
            vals = reference["values"]
            if "base_revenue" in vals:
                prefill = {
                    "base_revenue": _plain(Decimal(vals["base_revenue"]["value"]) / MILLION),
                    "base_fiscal_year_end": vals["base_revenue"]["fiscal_year_end"],
                    "cited_observations": " ".join(vals["base_revenue"]["observation_ids"]),
                }
            for k in ("operating_margin", "capex_rate", "depreciation_rate"):
                if k in vals:
                    prefill[k] = _plain(Decimal(vals[k]["value"]) * 100)
        return render(
            request,
            "model.html",
            page="model",
            company=sec,
            sets=sets,
            results=results,
            reference=reference,
            prefill=prefill,
            scenario=scenario,
            set_name=name,
            business=companyfacts.business_type(classification["data"]),
            treatments=fcff.TREATMENTS,
            labels=fcff.LABELS,
            model_name=fcff.MODEL,
        )

    @app.post("/company/{security_id}/model/assumptions")
    async def save_assumptions(security_id: str, request: Request):
        fields = await form(request, max_fields=60)
        security_or_404(security_id)
        try:
            raw = assumptions_from_form(fields)
            version = scenarios.save_assumptions(
                app.state.service,
                security_id,
                _text(fields.get("scenario"), 10),
                raw,
                _text(fields.get("rationale")),
                _text(fields.get("name"), 80) or "default",
            )
            scenarios.run_version(app.state.service, version["id"])
            return redirect(
                f"/company/{security_id}/model/version/{version['id']}",
                f"Saved {version['scenario']} assumptions as version {version['version']}.",
            )
        except fcff.AssumptionError as exc:
            return redirect(
                f"/company/{security_id}/model", "Not saved. " + _error("; ".join(exc.problems))
            )
        except (ValueError, ArithmeticError) as exc:
            return redirect(f"/company/{security_id}/model", "Not saved. " + _error(exc))

    @app.get("/company/{security_id}/model/version/{version_id}", response_class=HTMLResponse)
    def scenario_page(
        security_id: str,
        version_id: str,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
        row: str = "discount_rate",
        row_values: str = "",
        column: str = "terminal_growth",
        column_values: str = "",
        solve: str = "",
        target: str = "",
        lo: str = "",
        hi: str = "",
        what_if_row: str = "",
        what_if_column: str = "",
    ):
        sec = security_or_404(security_id)
        service = app.state.service
        version = version_or_404(security_id, version_id)
        chosen = _policy(service.clock, as_of, mode, policy)
        classification = service.submissions_context(security_id, chosen)
        result = scenarios.run_version(service, version_id, policy=chosen, context=classification)
        a = fcff.validate(version["assumptions"])
        business = companyfacts.business_type(
            classification["data"]
        )  # the what-if grids read the page's own cutoff
        shown, what_if = result.valuation, None
        grid = reverse = None
        problems = []
        try:
            if row not in fcff.GRID_PARAMETERS or column not in fcff.GRID_PARAMETERS:
                raise ValueError("choose grid parameters from: " + ", ".join(fcff.GRID_PARAMETERS))
            centre = lambda name: a.value(name)[0] if name in fcff.VECTOR else a.value(name)  # noqa: E731
            r_values = _grid_values(row_values[:200], centre(row), Decimal("0.01"))
            c_values = _grid_values(
                column_values[:200],
                centre(column),
                Decimal("0.005") if column == "terminal_growth" else Decimal("0.01"),
            )
            grid = fcff.sensitivity(
                a,
                (row, r_values),
                (column, c_values),
                business,
                "per_share" if result.valuation.per_share is not None else "enterprise_value",
            )
            if what_if_row and what_if_column:
                overrides = {row: Decimal(what_if_row), column: Decimal(what_if_column)}
                if not fcff._check_pair(a, overrides):
                    shown, what_if = (
                        fcff.run(fcff.with_values(a, overrides), business),
                        {row: what_if_row, column: what_if_column},
                    )
        except (ValueError, ArithmeticError) as exc:
            problems.append(_error(exc))
        price_row = scenarios.price_at(service, security_id, chosen)
        context = scenarios.market_context(version, a, result.valuation, price_row)
        if solve:
            try:
                goal = (
                    Decimal(target)
                    if target.strip()
                    else (Decimal(context["price"]) if context.get("status") == "ok" else None)
                )
                if goal is None:
                    raise ValueError("no comparable eligible price; give a target value per share")
                bracket = (Decimal(lo), Decimal(hi)) if lo.strip() and hi.strip() else None
                reverse = fcff.reverse(a, goal, solve, bracket, business)
                reverse["target_source"] = (
                    "manual target"
                    if target.strip()
                    else f"price {context['price']} {context['currency']} on {context['price_date']} ({context['source']})"
                )
            except (ValueError, ArithmeticError) as exc:
                problems.append(_error(exc))
        with service.store._connection() as db:
            from .calculations import stale_reasons

            stale = stale_reasons(db, result.calculation_id)
        versions = scenarios.history(service, version["assumption_id"])
        diffs = {}
        for newer, older in zip(versions, versions[1:]):
            diffs[newer["id"]] = scenarios.changed_fields(
                older["assumptions"], newer["assumptions"]
            )
        return render(
            request,
            "scenario.html",
            page="model",
            company=sec,
            version=version,
            a=a,
            result=result,
            shown=shown,
            what_if=what_if,
            grid=grid,
            reverse=reverse,
            context=context,
            problems=problems,
            stale=stale,
            versions=versions,
            diffs=diffs,
            labels=fcff.LABELS,
            grid_parameters=fcff.GRID_PARAMETERS,
            reverse_parameters=list(fcff.REVERSE_BRACKETS),
            policy=chosen,
            solve=solve,
            target=target,
            row=row,
            column=column,
            row_values=row_values,
            column_values=column_values,
            policy_name=next(k for k, v in POLICIES.items() if v == chosen.policy_version),
            query=_policy_query(chosen),
        )

    @app.get("/company/{security_id}/prices", response_class=HTMLResponse)
    def prices_page(security_id: str, request: Request):
        sec = security_or_404(security_id)
        return render(
            request,
            "prices.html",
            page="model",
            company=sec,
            rows=scenarios.price_list(app.state.service, security_id),
            adjustments=price_rules.ADJUSTMENTS,
            sessions=price_rules.SESSIONS,
        )

    def price_meta(fields):
        return {
            k: _text(fields.get(k), 300)
            for k in ("currency", "timezone", "adjustment", "session", "source", "feed_coverage")
        }

    @app.post("/company/{security_id}/prices/manual")
    async def manual_price(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        try:
            done = scenarios.add_manual_price(
                app.state.service,
                security_id,
                _text(fields.get("date"), 10),
                _text(fields.get("close"), 40),
                price_meta(fields),
                _text(fields.get("at"), 40) or None,
            )
            return redirect(
                f"/company/{security_id}/prices",
                "Price recorded." if done["added"] else "This price was already recorded.",
            )
        except ValueError as exc:
            return redirect(f"/company/{security_id}/prices", "Not recorded. " + _error(exc))

    @app.post("/company/{security_id}/prices/import")
    async def import_prices(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        try:
            upload = fields.get("file")
            if not hasattr(upload, "read"):
                raise ValueError("Choose a CSV file.")
            raw = await upload.read(price_rules.MAX_BYTES + 1)
            done = scenarios.import_price_csv(
                app.state.service,
                security_id,
                raw,
                Path((upload.filename or "prices.csv").replace("\\", "/")).name[:120],
                price_meta(fields),
            )
            return redirect(
                f"/company/{security_id}/prices",
                f"Imported {done['rows']} rows ({done['added']} new); "
                f"{done['coverage'].get('weekdays_without_price', 0)} weekdays without a price.",
            )
        except ValueError as exc:
            return redirect(f"/company/{security_id}/prices", "Nothing imported. " + _error(exc))
        finally:
            await fields.close()

    @app.get("/company/{security_id}/thesis", response_class=HTMLResponse)
    def thesis_page(
        security_id: str,
        request: Request,
        as_of: str = "",
        mode: str = "",
        policy: str = "",
        view: str = "",
        revise: str = "",
    ):
        sec = security_or_404(security_id)
        service = app.state.service
        chosen = _policy(service.clock, as_of, mode, policy)
        if view not in ("", "as_reported", "latest"):
            raise HTTPException(400, "Choose the as-reported or latest view.")
        result = decisions.review(service, security_id, chosen, view or "as_reported")
        all_theses = decisions.theses(service, security_id)
        recorded = {
            t["version"]["id"]: decisions.recorded_reviews(service, t["version"]["id"])[:12]
            for t in result["theses"]
        }
        prefill = None
        if revise:
            try:
                prefill = decisions.thesis_version(service, revise)
            except ValueError:
                raise HTTPException(404, "Thesis version not found.")
            if prefill["security_id"] != security_id:
                raise HTTPException(404, "Thesis version not found for this company.")
        names = sorted(
            {s["name"] for s in scenarios.assumption_sets(service, security_id)} | {"default"}
        )
        return render(
            request,
            "thesis.html",
            page="thesis",
            company=sec,
            result=result,
            theses=all_theses,
            recorded=recorded,
            prefill=prefill,
            advanced=json.dumps(prefill["conditions"], indent=1) if prefill else "",
            options=conditions.operand_options(names),
            describe=conditions.describe,
            shown=conditions.shown,
            policy=chosen,
            view=view or "as_reported",
            rows=range(1, BUILDER_ROWS + 1),
            policy_name=next(k for k, v in POLICIES.items() if v == chosen.policy_version),
            query=_policy_query(chosen),
        )

    @app.post("/company/{security_id}/thesis")
    async def save_thesis(security_id: str, request: Request):
        fields = await form(request, max_fields=60)
        security_or_404(security_id)
        try:
            version = decisions.save_thesis(
                app.state.service,
                security_id,
                _text(fields.get("title"), 120),
                _text(fields.get("statement")),
                conditions_from_form(fields),
                _text(fields.get("rationale")),
            )
            return redirect(
                f"/company/{security_id}/thesis",
                f"Saved '{version['title']}' as version {version['version']}.",
            )
        except ValueError as exc:
            return redirect(f"/company/{security_id}/thesis", "Not saved. " + _error(exc))

    @app.post("/company/{security_id}/thesis/review")
    async def record_thesis_review(security_id: str, request: Request):
        fields = await form(request)
        security_or_404(security_id)
        chosen = _policy(
            app.state.service.clock,
            _text(fields.get("as_of"), 40),
            _text(fields.get("mode"), 20),
            _text(fields.get("policy"), 20),
        )
        view = _text(fields.get("view"), 20) or "as_reported"
        if view not in ("as_reported", "latest"):
            raise HTTPException(400, "Choose the as-reported or latest view.")
        rows = decisions.record_review(app.state.service, security_id, chosen, view)
        triggered = sum(1 for r in rows if r["status"] == "triggered")
        return redirect(
            f"/company/{security_id}/thesis?{_policy_query(chosen)}&view={view}",
            f"Recorded {len(rows)} condition evaluations; {triggered} need review.",
        )

    @app.post("/company/{security_id}/decisions")
    async def save_decision(security_id: str, request: Request):
        fields = await form(request, max_fields=30)
        security_or_404(security_id)
        chosen = _policy(
            app.state.service.clock,
            _text(fields.get("as_of"), 40),
            _text(fields.get("mode"), 20),
            _text(fields.get("policy"), 20),
        )
        view = _text(fields.get("view"), 20) or "as_reported"
        if view not in ("as_reported", "latest"):
            raise HTTPException(400, "Choose the as-reported or latest view.")
        try:
            saved = decisions.save_packet(
                app.state.service,
                security_id,
                chosen,
                view,
                _text(fields.get("question"), 400),
                _text(fields.get("choice"), 200),
                _text(fields.get("rationale"), 8000),
                _text(fields.get("thesis_version_id"), 100) or None,
                _text(fields.get("review_date"), 10) or None,
                _text(fields.get("review_condition"), 1000) or None,
                _text(fields.get("resolution_rule"), 2000) or None,
            )
            return redirect(
                "/packet/" + saved["id"],
                "Decision packet recorded. It cannot be changed; record a new decision to revise it.",
            )
        except ValueError as exc:
            return redirect(
                f"/company/{security_id}/dossier?{_policy_query(chosen)}&view={view}",
                "Not recorded. " + _error(exc),
            )

    def packet_or_404(packet_id):
        try:
            return decisions.packet(app.state.service, packet_id)
        except ValueError as exc:
            raise HTTPException(404, _error(exc))

    # The export routes are registered first: '/packet/{packet_id}' would otherwise also match 'pkt_….json'.
    @app.get("/packet/{packet_id}.md")
    def packet_markdown(packet_id: str):
        return Response(
            decisions.render_markdown(packet_or_404(packet_id)),
            media_type="text/markdown",
            headers={
                "Content-Disposition": 'attachment; filename="kod-decision-packet.md"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/packet/{packet_id}.json")
    def packet_json(packet_id: str):
        stored = packet_or_404(packet_id)
        data = {
            "id": stored["id"],
            "packet_sha256": stored["packet_sha256"],
            "created_at": stored["created_at"],
            "packet": stored["packet"],
            "entry_permission": False,
        }
        return Response(
            json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="kod-decision-packet.json"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/packet/{packet_id}", response_class=HTMLResponse)
    def packet_page(packet_id: str, request: Request, reproduce: str = ""):
        stored = packet_or_404(packet_id)
        check = decisions.reproduce(app.state.service, packet_id) if reproduce else None
        return render(
            request,
            "packet.html",
            page="dossier",
            company=app.state.store.get_security(stored["security_id"]),
            stored=stored,
            body=stored["packet"],
            check=check,
            describe=conditions.describe,
            shown=conditions.shown,
        )

    @app.get("/health", response_class=HTMLResponse)
    def health(request: Request):
        return render(
            request,
            "health.html",
            page="health",
            health=app.state.store.health(),
            jobs=app.state.store.jobs()[:30],
            sec_configured=bool(os.environ.get("KOD_SEC_CONTACT")),
        )

    return app

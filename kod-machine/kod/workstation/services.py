"""Research use cases over preserved sources; no network dependencies.

Provider code acquires bytes. This service records them and invokes the existing
deterministic financial engines. No uploaded URL is treated as authentication.
"""
from __future__ import annotations

import hashlib
import html
from pathlib import Path
import re
from urllib.parse import urlsplit

from .. import earnings
from ..hashing import utc_now
import json

from . import companyfacts, financials
from .search import ArchiveIndex
from .domain import APP_VERSION, MAX_DOCUMENT_BYTES, association as valid_association, publication, source_url as valid_url, timestamp
from .policy import DAY_END, AsOfPolicy
from .store import Store


class ResearchService:
    def __init__(self, store: Store, clock=utc_now):
        self.store = store
        self.clock = clock
        self.parser_sha256 = hashlib.sha256(Path(earnings.__file__).read_bytes()).hexdigest()
        self.archive = ArchiveIndex(store)

    @staticmethod
    def _validate_identity(security, url, headers=None):
        """Check the source's SEC identity (URL CIK, header CIKs, accession) against the selected company; returns the header link (see header_link)."""
        parts = urlsplit(url)
        url_cik = None
        if parts.hostname in ("www.sec.gov", "sec.gov", "data.sec.gov"):
            match = re.search(r"^/Archives/edgar/data/(\d+)/", parts.path)
            if match:
                url_cik = int(match.group(1))
        header_ciks = set()
        if headers:
            text = html.unescape(headers.decode("utf-8", "replace"))
            header_ciks = {int(c) for c in re.findall(r"CENTRAL INDEX KEY:\s*(\d+)", text, re.I) + re.findall(r"<CIK>\s*(\d+)", text, re.I)}
        if url_cik is not None and header_ciks and url_cik not in header_ciks:
            raise ValueError("SEC source URL and header CIK disagree")
        link = ResearchService.header_link(url, headers) if headers else None
        if security["cik"]:
            cik = int(security["cik"])
            if (url_cik is not None and url_cik != cik) or (header_ciks and cik not in header_ciks):
                raise ValueError("source CIK does not match the selected company")
        return link

    ACCESSION_STATEMENTS = (
        re.compile(r"ACCESSION[- ]NUMBER\s*[>:]\s*(\d{10}-\d{2}-\d{6})(?!\d)", re.I),
        re.compile(r"SEC EDGAR Submission\s+(\d{10}-\d{2}-\d{6})(?!\d)", re.I),
        re.compile(r"(?<!\d)(\d{10}-\d{2}-\d{6})(?:\.hdr\.sgml|-index(?:-headers)?\.html?|\.txt)\b", re.I),
    )

    @staticmethod
    def header_link(url, headers: bytes) -> dict:
        """How a supplied SEC filing header relates to this source. 'matched' only when every accession the header states (its ACCESSION lines, title and
        file names) is one and the same and is the accession folder of the SEC Archives source URL, and the header states one acceptance time; then (and only
        then) that acceptance time is the filing's. A header naming a different filing, or several, raises. Anything else is 'unestablished' with the reason:
        the header remains preserved as an assertion."""
        text = html.unescape(headers.decode("utf-8", "replace"))
        stated = set()
        for rx in ResearchService.ACCESSION_STATEMENTS:
            stated.update(rx.findall(text))
        parts = urlsplit(url)
        folder = re.search(r"^/Archives/edgar/data/\d+/(\d{10})(\d{2})(\d{6})/", parts.path) if parts.hostname in ("www.sec.gov", "sec.gov") else None
        accession = "-".join(folder.groups()) if folder else None
        if len(stated) > 1:
            raise ValueError("the SEC header states more than one accession number (" + ", ".join(sorted(stated)) + ")")
        if accession and stated and accession not in stated:
            raise ValueError("the SEC header belongs to a different filing (accession " + next(iter(stated)) + ") than the source URL")
        stamps = set(re.findall(r"ACCEPTANCE-DATETIME>\s*(\d{14})(?!\d)", text))
        if len(stamps) > 1:
            return {"status": "unestablished", "accession": next(iter(stated), None),
                    "reason": "the header states different acceptance times (" + ", ".join(sorted(stamps)) + ")"}
        if accession and stated:
            return {"status": "matched", "accession": accession, "reason": "the header's accession number is the source URL's filing folder"}
        if not stated:
            return {"status": "unestablished", "accession": None, "reason": "the header states no accession number"}
        return {"status": "unestablished", "accession": next(iter(stated)),
                "reason": "the source URL is not an SEC Archives filing folder, so the header's accession cannot be tied to this document"}

    def ingest(self, security_id, raw: bytes, filename, source_url, published_at=None, sec_headers: bytes | None = None,
               retrieved_at=None, role="current", association="user_asserted", provider="local", external_id=None):
        security = self.store.get_security(security_id)
        valid_url(source_url)
        valid_association(association)
        if role not in ("current", "comparison", "metadata", "other"):
            raise ValueError("unsupported source role")
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_DOCUMENT_BYTES:
            raise ValueError("document must contain 1 byte to 12 MiB")
        if sec_headers is not None and (not isinstance(sec_headers, bytes) or len(sec_headers) > MAX_DOCUMENT_BYTES):
            raise ValueError("SEC headers must be bytes smaller than 12 MiB")
        link = self._validate_identity(security, source_url, sec_headers)
        observed = timestamp(retrieved_at or self.clock())
        published, date_only = publication(published_at)
        basis = "publication timestamp supplied by the user" if published else "UNKNOWN: no precise publication timestamp supplied"
        asserted = None
        if sec_headers and published_at is None:
            acceptance = earnings.sec_acceptance(html.unescape(sec_headers.decode("utf-8", "replace")))
            if acceptance and link["status"] == "matched":
                published = acceptance
                basis = ("SEC filing acceptance from the filing's own header, whose accession number matches the source URL (New York clock converted to UTC); "
                         "not earliest issuer publication")
            elif acceptance:
                # A header that cannot be tied to this filing is kept as an assertion, never as the filing's acceptance time.
                asserted = acceptance
                basis = f"UNKNOWN: a supplied header asserts SEC acceptance at {acceptance}, but {link['reason']}; not used as this filing's acceptance time"
        if date_only:
            basis = "publication date supplied by the user; intraday availability unknown"
        if published and observed < published:
            raise ValueError("observation must not precede publication")
        metadata = {
            "parser_version": earnings.SCHEMA,
            "parser_sha256": self.parser_sha256,
            "publication_precision": "date" if date_only else "second" if published else "unknown",
            "observed_basis": "retrieval time supplied by the user" if retrieved_at else "document loaded by this run; earlier retrieval unknown",
            "source_family": "issuer-release" if role in ("current", "comparison") else "source-metadata",
            "usage_note": "Source supplied for private research; redistribution rights not established by ingestion.",
        }
        if date_only:
            metadata["publication_date"] = date_only
        if link:
            metadata["header_link"] = link
        if asserted:
            metadata["asserted_header_acceptance"] = asserted
        status, facts, resolution = "unsupported", [], None
        try:
            doc = earnings.read_document(raw, Path(str(filename).replace("\\", "/")).name)
            # Listing currency is not the issuer's reporting currency: only the
            # document's own statements, or an explicit analyst record, set it.
            facts, issues = earnings.extract_table_facts(doc)
            resolution = earnings.headline_checks(doc, facts)["resolution"]
            metadata["title"] = next((line[:240] for line in doc["lines"] if line.strip()), str(filename)[:240])
            metadata["period"] = resolution["period"]
            metadata["period_resolution"] = {k: resolution[k] for k in ("status", "basis", "reason", "candidates")}
            metadata["parser"] = earnings.PARSER_VERSION
            metadata["issue_codes"] = sorted({i["code"] for i in issues})
            if resolution["status"] == "RESOLVED":
                status = "parsed"
            elif resolution["candidates"]:
                # Figures were recognised but the release does not establish which quarter it reports: a note can be generated only as a withheld result, or after the
                # analyst records the period explicitly.
                status = "needs_review"
                metadata["review_reason"] = "reported period unresolved: " + resolution["reason"]
            else:
                metadata["extraction_error"] = "No supported earnings table found. Preserve this source and supply a supported HTML release to generate a note."
        except (earnings.EarningsError, ValueError, ArithmeticError) as exc:
            metadata["extraction_error"] = str(exc)[:1200]
            metadata["title"] = str(filename)[:240]
        # Headers are evidence too, not an unattached mutable assertion in the
        # database. They are saved only after all identity/time checks passed.
        if sec_headers:
            header_url = earnings.sec_headers_url(source_url) or source_url
            header_doc = self.store.save_document(
                security_id, sec_headers, "filing-headers.html", header_url,
                published_at=published, published_basis=basis, observed_at=observed,
                role="metadata", association=association, provider=provider,
                external_id=(str(external_id) + ":headers") if external_id else None,
                extraction_status="not_applicable", metadata={"kind": "SEC filing header", "parser_version": earnings.SCHEMA},
            )
            metadata["sec_headers_document_id"] = header_doc["id"]
        saved = self.store.save_document(
            security_id, raw, filename, source_url, published_at=published, published_basis=basis,
            observed_at=observed, role=role, association=association, provider=provider,
            external_id=external_id, extraction_status=status, metadata=metadata,
        )
        if status in ("parsed", "needs_review"):
            self._record_observations(saved, facts, resolution)
        return saved

    def _record_observations(self, document, facts, resolution):
        """Every figure the release yields becomes an immutable observation of this document (idempotent for the same bytes and parser version)."""
        issuer = (self.store.identity(document["security_id"]) or {}).get("issuer_id")
        header_id = document["metadata"].get("sec_headers_document_id")
        if header_id and "header_link" not in document["metadata"]:
            # Documents saved before v2 kept the header but not its relationship; establish it now from the preserved bytes.
            try:
                link = self.header_link(document["source_url"], self.store.raw(header_id))
            except ValueError:
                link = {"status": "unestablished", "accession": None, "reason": "the preserved header could not be tied to this source"}
            document = {**document, "metadata": {**document["metadata"], "header_link": link}}
        periods, rows = financials.release_rows(document, document["security_id"], issuer, facts, resolution, self.clock())
        return self.store.record_observations(periods, rows)

    def import_companyfacts(self, security_id, raw: bytes, source_url: str, observed_at=None, submissions: bytes | None = None,
                            submissions_url: str | None = None, provider="sec") -> dict:
        """Preserve an SEC companyfacts response (and optionally the submissions feed) and record its mapped facts as observations. The response must belong
        to the company's recorded CIK. Returns the coverage report: what was recorded, what is absent, what was not interpreted."""
        security = self.store.get_security(security_id)
        valid_url(source_url)
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_DOCUMENT_BYTES:
            raise ValueError("companyfacts response must contain 1 byte to 12 MiB")
        if not security["cik"]:
            raise ValueError("record the company's CIK before importing SEC companyfacts")
        data = companyfacts.parse(raw)
        if int(data["cik"]) != int(security["cik"]):
            raise ValueError(f"companyfacts belong to CIK {int(data['cik'])}, not the selected company's CIK {int(security['cik'])}")
        subs = None
        if submissions is not None:
            try:
                subs = json.loads(submissions)
            except ValueError as exc:
                raise ValueError("submissions response is not valid JSON") from exc
            if not isinstance(subs, dict) or str(subs.get("cik", "")).lstrip("0") != str(int(security["cik"])):
                raise ValueError("submissions response belongs to a different CIK")
            valid_url(submissions_url or "https://data.sec.gov/submissions/")
        observed = timestamp(observed_at or self.clock())
        meta = {"kind": "SEC companyfacts response", "entity": str(data.get("entityName"))[:240], "cik": str(int(data["cik"])), "reader": companyfacts.PARSER_VERSION,
                "usage_note": "Public SEC data preserved for private research."}
        doc = self.store.save_document(security_id, raw, "companyfacts.json", source_url, published_at=None,
                                       published_basis="API snapshot: each fact carries its own filing date; this response's own publication time is not established",
                                       observed_at=observed, role="other", association="verified_from_filing_metadata", provider=provider,
                                       external_id=f"companyfacts:{int(data['cik'])}", extraction_status="companyfacts", metadata=meta)
        if subs is not None:
            self.store.save_document(security_id, submissions, "submissions.json", submissions_url or "https://data.sec.gov/submissions/", published_at=None,
                                     published_basis="API snapshot of the filing list; filing dates are per filing", observed_at=observed, role="metadata",
                                     association="verified_from_filing_metadata", provider=provider, external_id=f"submissions:{int(data['cik'])}",
                                     extraction_status="metadata", metadata={"kind": "SEC submissions response", "cik": str(int(data["cik"])),
                                                                             "sic": subs.get("sic"), "sic_description": subs.get("sicDescription")})
        issuer = (self.store.identity(security_id) or {}).get("issuer_id")
        periods, rows, coverage = companyfacts.observation_rows(data, doc, security_id, issuer, self.clock(), subs)
        coverage["added"] = self.store.record_observations(periods, rows)
        coverage["document_id"] = doc["id"]
        coverage["business_type"] = companyfacts.business_type(subs)
        self.store.record_job("sec-companyfacts", security_id, "success",
                              f"Recorded {coverage['observations']} companyfacts observations ({coverage['added']} new). Absent catalog metrics: "
                              f"{', '.join(coverage['absent_metrics']) or 'none'}. Whole-entity standard-taxonomy facts only.",
                              started_at=observed, finished_at=self.clock(), new_count=coverage["added"])
        return coverage

    def submissions_context(self, security_id, policy, source=None, *, legacy=False):
        """Select and verify one classification source; public reconstruction is an explicit proxy."""
        documents = {d["id"]: d for d in self.store.documents(security_id) if d["metadata"].get("kind") == "SEC submissions response"}
        with self.store._connection() as db:
            events = db.execute("SELECT o.* FROM observations o JOIN documents d ON d.id=o.document_id WHERE d.security_id=?", (security_id,)).fetchall()
        # INTEGER PRIMARY KEY observation IDs preserve actual import order, including A -> B -> A re-observations.
        candidates = ([(d, d["observed_at"], None) for d in documents.values()] if legacy else
                      [(documents[e["document_id"]], e["observed_at"], e["id"]) for e in events if e["document_id"] in documents])
        candidates.sort(key=lambda item: (item[1], item[0]["id"] if legacy else item[2]))
        if source is not None:
            candidates = [item for item in candidates if item[0]["id"] == source.get("document_id") and item[2] == source.get("recording_seq")]
            if source.get("document_id") and not candidates:
                raise ValueError("frozen classification source is not available for this company")
        if policy.mode == "observed":
            candidates = [item for item in candidates if item[1] <= policy.as_dict()["cutoff"]][-1:]
        doc, observed, sequence = candidates[0] if candidates else (None, None, None)
        raw = json.loads(self.store.raw(doc["id"])) if doc else None
        result = {"data": raw, "source": {"document_id": doc["id"] if doc else None,
                "sha256": doc["sha256"] if doc else None, "observed_at": observed, "recording_seq": sequence,
                "policy": policy.as_dict(), "availability": "unknown" if doc is None else
                ("observed_snapshot" if policy.mode == "observed" else "public_reconstruction_proxy"),
                "limitation": "SIC classification unavailable at this cutoff" if doc is None else
                ("current metadata proxy; not evidence of historical classification" if policy.mode == "public" else None)}}
        if source is not None and source != result["source"]:
            raise ValueError("frozen classification source does not match its policy and preserved metadata")
        return result

    def submissions_at(self, security_id, policy):
        context = self.submissions_context(security_id, policy)
        return context["data"], context["source"]["observed_at"]

    def latest_submissions(self, security_id):
        """The snapshot held now: submissions_at with the clock as the cutoff (one rule, the live-page convenience)."""
        return self.submissions_at(security_id, AsOfPolicy.parse(timestamp(self.clock()), "observed", DAY_END))[0]

    def index_documents(self, security_id=None) -> dict:
        """Record observations for preserved releases that have none from this parser version (for example after an upgrade from v1). The stored bytes
        are re-read and integrity-checked; nothing is fetched and no document, note or earlier observation is changed."""
        done = {"documents": 0, "observations": 0, "skipped": []}
        for doc in self.store.documents(security_id):
            if doc["role"] not in ("current", "comparison") or doc["extraction_status"] not in ("parsed", "needs_review", "unsupported"):
                continue
            if self.store.observation_count(doc["id"], earnings.PARSER_VERSION):
                continue
            try:
                parsed = earnings.read_document(self.store.raw(doc["id"]), doc["filename"])
                facts, _ = earnings.extract_table_facts(parsed)
                resolution = earnings.headline_checks(parsed, facts)["resolution"]
            except (earnings.EarningsError, ValueError, ArithmeticError) as exc:
                done["skipped"].append({"document_id": doc["id"], "reason": str(exc)[:300]})
                continue
            done["observations"] += self._record_observations(doc, facts, resolution)
            done["documents"] += 1
        return done

    def _source(self, doc, link=None):
        parsed = earnings.read_document(self.store.raw(doc["id"]), doc["filename"])
        published, basis = doc["published_at"], doc["published_basis"]
        if published and "SEC filing acceptance" in basis and (link is None or link["status"] != "matched"):
            # Saved under an earlier rule: the acceptance time came from a header that is not tied to this filing. It stays an assertion, not availability.
            published = None
            basis = ("UNKNOWN: the stored acceptance time " + doc["published_at"] + " came from a header that is not tied to this filing ("
                     + (link["reason"] if link else "no header preserved") + "); re-checked when the note was generated")
        return {
            "document_id": doc["id"], "source_version_id": doc["id"],
            "doc": parsed, "source_url": doc["source_url"], "published_at": published,
            "published_basis": basis, "observed_at": doc["observed_at"],
            "observed_basis": doc["metadata"].get("observed_basis", "recorded source observation"),
            "title": doc["metadata"].get("title", doc["filename"]),
        }

    def generate_note(self, security_id, current_id, comparison_id=None, as_of=None, mode="observed", period=None, reporting_currency=None):
        """period / reporting_currency: the analyst's explicit records (see earnings.analyse); they are saved with the note's result."""
        security = self.store.get_security(security_id)
        current = self.store.document(current_id)
        comparison = self.store.document(comparison_id) if comparison_id else None
        links = {}
        for doc in (current, comparison):
            if doc is None:
                continue
            if doc["security_id"] != security_id:
                raise ValueError("document belongs to a different security")
            # A listing can acquire a verified CIK after a document was first
            # uploaded. Recheck stored source assertions against today's issuer
            # mapping before using either side of a financial comparison.
            header_id = doc["metadata"].get("sec_headers_document_id")
            headers = None
            if header_id:
                header_doc = self.store.document(header_id)
                if header_doc["security_id"] != security_id:
                    raise ValueError("stored filing header belongs to a different security")
                headers = self.store.raw(header_id)
            links[doc["id"]] = self._validate_identity(security, doc["source_url"], headers)
            if doc["extraction_status"] not in ("parsed", "needs_review"):
                raise ValueError("source layout is not supported for earnings extraction; inspect the preserved source or supply a supported HTML release")
        cutoff = timestamp(as_of or self.clock())
        if mode not in ("observed", "public"):
            raise ValueError("mode must be observed or public")
        recorded = {"recorded_by": "analyst (workstation)", "recorded_at": self.clock()}
        result = earnings.analyse(
            security["name"], security["ticker"], security["venue"], self._source(current, links.get(current["id"])),
            self._source(comparison, links.get(comparison["id"])) if comparison else None, cutoff, mode,
            currency_override={"currency": reporting_currency, **recorded} if reporting_currency else None,
            period_override={"period": period, **recorded} if period else None,
        )
        result["workstation"] = {
            "app_version": APP_VERSION, "parser_sha256": self.parser_sha256,
            "source_versions": [{"document_id": d["id"], "association": d["association"], "sha256": d["sha256"]}
                                for d in (current, comparison) if d],
        }
        markdown = earnings.render_note(result)
        association_text = "; ".join(f"{role}: {d['association']}" for role, d in (("current", current), ("comparison", comparison)) if d)
        markdown += "\nSource association: " + association_text + ". A user assertion is not authenticated issuer identity.\n"
        return self.store.save_note(security_id, current_id, comparison_id, result, markdown, cutoff, mode)

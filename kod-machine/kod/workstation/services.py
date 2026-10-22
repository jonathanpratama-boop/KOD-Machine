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
from .domain import APP_VERSION, MAX_DOCUMENT_BYTES, association as valid_association, publication, source_url as valid_url, timestamp
from .store import Store


class ResearchService:
    def __init__(self, store: Store, clock=utc_now):
        self.store = store
        self.clock = clock
        self.parser_sha256 = hashlib.sha256(Path(earnings.__file__).read_bytes()).hexdigest()

    @staticmethod
    def _validate_identity(security, url, headers=None):
        claimed = []
        parts = urlsplit(url)
        if parts.hostname in ("www.sec.gov", "sec.gov", "data.sec.gov"):
            match = re.search(r"^/Archives/edgar/data/(\d+)/", parts.path)
            if match:
                claimed.append(int(match.group(1)))
        if headers:
            text = html.unescape(headers.decode("utf-8", "replace"))
            match = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", text)
            if match:
                claimed.append(int(match.group(1)))
        if len(set(claimed)) > 1:
            raise ValueError("SEC source URL and header CIK disagree")
        if headers:
            folder = re.search(r"^/Archives/edgar/data/\d+/(\d{10})(\d{2})(\d{6})/", parts.path) if parts.hostname in ("www.sec.gov", "sec.gov") else None
            stated = re.search(r"ACCESSION-NUMBER>\s*(\d{10}-\d{2}-\d{6})", headers.decode("utf-8", "replace"))
            if folder and stated and "-".join(folder.groups()) != stated.group(1):
                raise ValueError("the SEC header belongs to a different filing (accession " + stated.group(1) + ") than the source URL")
        if security["cik"] and claimed and int(security["cik"]) != claimed[0]:
            raise ValueError("source CIK does not match the selected company")

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
        self._validate_identity(security, source_url, sec_headers)
        observed = timestamp(retrieved_at or self.clock())
        published, date_only = publication(published_at)
        basis = "publication timestamp supplied by the user" if published else "UNKNOWN: no precise publication timestamp supplied"
        if sec_headers and published_at is None:
            published = earnings.sec_acceptance(sec_headers.decode("utf-8", "replace"))
            if published:
                basis = "SEC filing acceptance from supplied header (New York clock converted to UTC); not earliest issuer publication"
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
        status = "unsupported"
        try:
            doc = earnings.read_document(raw, Path(str(filename).replace("\\", "/")).name)
            # Listing currency is not the issuer's reporting currency. Preserve
            # the parser's explicit dollar-sign assumption until the user can
            # supply a document-specific reporting-currency override.
            facts, issues = earnings.extract_table_facts(doc)
            head = earnings.headline_checks(doc, facts)
            period = earnings.choose_current(facts, head)
            metadata["title"] = next((line[:240] for line in doc["lines"] if line.strip()), str(filename)[:240])
            metadata["period"] = period
            metadata["issue_codes"] = sorted({i["code"] for i in issues})
            if period is None:
                metadata["extraction_error"] = "No supported earnings table found. Preserve this source and supply a supported HTML release to generate a note."
            else:
                status = "parsed"
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
        return self.store.save_document(
            security_id, raw, filename, source_url, published_at=published, published_basis=basis,
            observed_at=observed, role=role, association=association, provider=provider,
            external_id=external_id, extraction_status=status, metadata=metadata,
        )

    def _source(self, doc):
        parsed = earnings.read_document(self.store.raw(doc["id"]), doc["filename"])
        return {
            "document_id": doc["id"], "source_version_id": doc["id"],
            "doc": parsed, "source_url": doc["source_url"], "published_at": doc["published_at"],
            "published_basis": doc["published_basis"], "observed_at": doc["observed_at"],
            "observed_basis": doc["metadata"].get("observed_basis", "recorded source observation"),
            "title": doc["metadata"].get("title", doc["filename"]),
        }

    def generate_note(self, security_id, current_id, comparison_id=None, as_of=None, mode="observed"):
        security = self.store.get_security(security_id)
        current = self.store.document(current_id)
        comparison = self.store.document(comparison_id) if comparison_id else None
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
            self._validate_identity(security, doc["source_url"], headers)
            if doc["extraction_status"] != "parsed":
                raise ValueError("source layout is not supported for earnings extraction; inspect the preserved source or supply a supported HTML release")
        cutoff = timestamp(as_of or self.clock())
        if mode not in ("observed", "public"):
            raise ValueError("mode must be observed or public")
        result = earnings.analyse(
            security["name"], security["ticker"], security["venue"], self._source(current),
            self._source(comparison) if comparison else None, cutoff, mode,
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

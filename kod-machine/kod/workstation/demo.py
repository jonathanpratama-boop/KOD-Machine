"""Replay the repository's four real historical releases, without network access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[2] / "examples" / "earnings_demo"
COMPANIES = (
    ("NVDA", "NVIDIA Corporation", "1045810", "", "2024-11-20T22:00:00Z"),
    ("AMD", "Advanced Micro Devices, Inc.", "2488", "more/amd", "2024-10-29T22:00:00Z"),
    ("AAPL", "Apple Inc.", "320193", "more/aapl", "2024-10-31T22:00:00Z"),
    ("MSFT", "Microsoft Corporation", "789019", "more/msft", "2024-10-30T22:00:00Z"),
)


def seed_demo(service, examples_root=None) -> list[dict]:
    """Same ingestion/note path as uploads; only frozen source retrieval is replayed."""
    root = Path(examples_root or DEMO_ROOT)
    notes = []
    for ticker, name, cik, sub, cutoff in COMPANIES:
        folder = root / sub
        sources = json.loads((folder / "SOURCES.json").read_text(encoding="utf-8"))
        for item in sources:
            raw = (folder / item["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("Demo source SHA-256 differs from its preserved manifest: " + item["file"])
        sec = service.store.upsert_security(ticker, name, cik, "XNAS", "USD", "user_asserted")
        docs = {}
        for role, aliases in (("current", ("current", "cur")), ("comparison", ("prior", "pri"))):
            release = next(i for i in sources if i["role"] in aliases and
                           (i.get("kind") == "release" or "index-headers" not in i["file"]))
            header = next(i for i in sources if i["role"] in aliases and
                          (i.get("kind") == "headers" or "index-headers" in i["file"]))
            doc = service.ingest(
                sec["id"], (folder / release["file"]).read_bytes(), release["file"], release["url"],
                sec_headers=(folder / header["file"]).read_bytes(),
                retrieved_at=release.get("retrieved_at") or release["retrieved_at_utc_file_mtime"],
                role=role, provider="frozen_demo", external_id=release["url"],
                association="user_asserted",
            )
            docs[role] = doc
        current = docs["current"]
        service.store.save_event(
            sec["id"], "demo:" + current["id"], "8-K exhibit",
            f"Historical earnings example · {ticker}", current["source_url"],
            published_at=current["published_at"], published_basis=current["published_basis"],
            observed_at=current["observed_at"], document_id=current["id"],
            metadata={"demonstration": True, "coverage": "Preserved 2024 release; not a current-market feed"},
        )
        notes.append(service.generate_note(sec["id"], current["id"], docs["comparison"]["id"],
                                           as_of=cutoff, mode="public"))
    service.store.record_job("demo", "four-company replay", "success",
                             "Four preserved 2024 earnings releases replayed offline. These are historical examples, not current data.")
    return notes

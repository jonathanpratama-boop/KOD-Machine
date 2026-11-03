"""Load the explicit, source-backed experiment registry without inferring promotion.

This small registry replaces status guesses from a directory name, an old README,
or an open PR. A report is evidence of a reported result, not a successful rerun.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re

STATUSES = {"RESEARCH_CLOSED", "RESEARCH_CORRECTION_PENDING", "RESEARCH_COLLECTION",
            "PAPER_SIGNAL_LOG", "PAPER_TRIAL", "PLANNED"}
EVIDENCE_LEVELS = {"REPORTED_RETROSPECTIVE", "REPORTED_RETROSPECTIVE_WITH_DEFECT",
                   "DESCRIPTIVE_RETROSPECTIVE", "PROSPECTIVE_SIGNALS_ONLY",
                   "PROSPECTIVE_TRIAL", "PROTOCOL_ONLY", "OWNER_DECISION"}


def _safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("source path must be a relative repository path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("source path must remain inside the repository")
    return value


def load_catalog(repo_root) -> list[dict]:
    """Return validated records plus source availability; never fabricate missing data.

    Missing source files yield SOURCE_MISSING on that record, rather than a false
    validated result or an unavailable whole dashboard. Malformed declarations fail.
    """
    root = Path(repo_root).resolve()
    payload = json.loads((root / "configs" / "experiments.json").read_text())
    if payload.get("schema_version") != 1 or not isinstance(payload.get("experiments"), list):
        raise ValueError("unsupported experiment catalog schema")
    ids = set()
    result = []
    for raw in payload["experiments"]:
        item = dict(raw)
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError("experiment ids must be nonempty and unique")
        ids.add(identifier)
        if item.get("status") not in STATUSES or item.get("evidence_level") not in EVIDENCE_LEVELS:
            raise ValueError(f"invalid status/evidence level for {identifier}")
        if item.get("live_eligible") is not False:
            raise ValueError("this research catalog cannot grant live eligibility")
        if not isinstance(item.get("limitations"), list) or not isinstance(item.get("sources"), list) or not item["sources"]:
            raise ValueError("each record needs explicit sources and limitations")
        missing = []
        for source in item["sources"]:
            path = _safe_relative(source.get("path"))
            ref_type = source.get("ref_type", "git_commit")
            if ref_type == "git_commit":
                if not isinstance(source.get("ref"), str) or not re.fullmatch(r"[0-9a-f]{40}", source["ref"]):
                    raise ValueError("source ref must be an observed full git commit")
            elif ref_type == "working_tree":
                if source.get("ref") is not None:
                    raise ValueError("uncommitted sources cannot invent a commit ref")
            else:
                raise ValueError("unknown source ref type")
            candidate = (root / path).resolve()
            if not candidate.is_relative_to(root):
                raise ValueError("source symlink escapes repository")
            if not candidate.is_file():
                missing.append(path)
        item["source_status"] = "SOURCE_MISSING" if missing else "PRESENT_NOT_RERUN"
        item["missing_sources"] = missing
        result.append(item)
    return result

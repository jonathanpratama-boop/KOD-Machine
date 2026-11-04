"""Issuer, instrument and listing identity, kept apart from the v1 watchlist row.

A v1 `securities` row mixes three things: the reporting entity (CIK), the instrument (share class) and the tradable listing (ticker, venue, trading currency).
They are recorded separately here. The existing security ID stays the listing's ID, so every saved link keeps working; `security_identity` is the explicit,
versioned mapping. Identifier aliases record when KOD observed them and on what basis; their historical validity is unknown unless evidenced, so it is
never backdated.
"""

from __future__ import annotations

import json

from .domain import canonical, identity

CLASS_UNKNOWN = "share class not recorded"

# Canonical metric catalog, version 1. kind: flow (a period amount), instant (a balance on a date), per_share, ratio, count. Only additive flows may be
# summed across contiguous periods or differenced from year-to-date figures; per-share amounts, ratios and share counts never are.
METRIC_CATALOG_V1 = (
    (
        "revenue",
        "Revenue",
        "flow",
        1,
        "currency",
        "Total net revenue (net sales) of the consolidated entity for the period.",
    ),
    (
        "gross_margin",
        "Gross margin",
        "ratio",
        0,
        "percent",
        "Gross profit as a percentage of revenue, as printed.",
    ),
    (
        "operating_expenses",
        "Operating expenses",
        "flow",
        1,
        "currency",
        "Total operating expenses as printed by the issuer.",
    ),
    (
        "operating_income",
        "Operating income",
        "flow",
        1,
        "currency",
        "Operating income (loss) of the consolidated entity.",
    ),
    (
        "net_income",
        "Net income",
        "flow",
        1,
        "currency",
        "Net income (loss); attribution to the parent is as tagged or printed.",
    ),
    (
        "eps_diluted",
        "Diluted EPS",
        "per_share",
        0,
        "currency_per_share",
        "Diluted earnings per share. Not additive across periods.",
    ),
    (
        "diluted_shares",
        "Diluted weighted-average shares",
        "count",
        0,
        "shares",
        "Weighted-average diluted shares for the period. Not additive and not the same as period-end shares outstanding.",
    ),
    (
        "shares_outstanding",
        "Shares outstanding",
        "instant",
        0,
        "shares",
        "Shares outstanding on a stated date (cover page or balance sheet).",
    ),
    (
        "operating_cash_flow",
        "Cash from operations",
        "flow",
        1,
        "currency",
        "Net cash provided by (used in) operating activities.",
    ),
    (
        "capex",
        "Capital expenditures",
        "flow",
        1,
        "currency",
        "Payments for property and equipment, as a nonnegative investment amount; the provider's signed value is kept in raw_value.",
    ),
    (
        "depreciation_amortization",
        "Depreciation and amortization",
        "flow",
        1,
        "currency",
        "Depreciation and amortization from the cash-flow statement.",
    ),
    (
        "cash_and_equivalents",
        "Cash and equivalents",
        "instant",
        0,
        "currency",
        "Cash and cash equivalents at the period end.",
    ),
    ("total_assets", "Total assets", "instant", 0, "currency", "Total assets at the period end."),
    (
        "total_liabilities",
        "Total liabilities",
        "instant",
        0,
        "currency",
        "Total liabilities at the period end, where the issuer reports the total.",
    ),
    (
        "stockholders_equity",
        "Stockholders' equity",
        "instant",
        0,
        "currency",
        "Total stockholders' equity attributable to the parent at the period end.",
    ),
    (
        "long_term_debt",
        "Long-term debt (noncurrent)",
        "instant",
        0,
        "currency",
        "Noncurrent long-term debt as tagged (us-gaap LongTermDebtNoncurrent); current portions and other components are not combined.",
    ),
)
METRIC_VERSION = 1


def seed_metric_catalog(db):
    for metric, label, kind, additive, family, description in METRIC_CATALOG_V1:
        db.execute(
            "INSERT OR IGNORE INTO metric_definitions VALUES (?,?,?,?,?,?,?)",
            (metric, METRIC_VERSION, label, kind, additive, family, description),
        )


def _issuer_id(row):
    return (
        identity("iss", "cik", row["cik"]) if row["cik"] else identity("iss", "listing", row["id"])
    )


def ensure_identity(db, row, now, basis="watchlist record") -> dict:
    """Record (idempotently) the issuer, instrument, listing and aliases for one `securities` row, and map the security ID to them when the mapping changed."""
    issuer_id = _issuer_id(row)
    instrument_id = identity("ins", row["id"])
    db.execute(
        "INSERT OR IGNORE INTO issuers VALUES (?,?,?,?,?)",
        (
            issuer_id,
            row["name"],
            row["cik"],
            row["association"] if row["cik"] else "unresolved",
            row["created_at"],
        ),
    )
    db.execute(
        "INSERT OR IGNORE INTO instruments VALUES (?,?,?,?)",
        (instrument_id, issuer_id, CLASS_UNKNOWN, row["created_at"]),
    )
    db.execute(
        "INSERT OR IGNORE INTO listings VALUES (?,?,?,?,?)",
        (row["id"], instrument_id, row["venue"], row["currency"], row["created_at"]),
    )
    evidence = canonical(
        {"source": basis, "association": row["association"], "validity": "unknown; not backdated"}
    )
    db.execute(
        "INSERT OR IGNORE INTO identifier_aliases(subject_kind,subject_id,id_type,value,valid_from,valid_to,observed_at,evidence,recorded_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "listing",
            row["id"],
            "ticker",
            row["ticker"],
            None,
            None,
            row["created_at"],
            evidence,
            now,
        ),
    )
    if row["cik"]:
        db.execute(
            "INSERT OR IGNORE INTO identifier_aliases(subject_kind,subject_id,id_type,value,valid_from,valid_to,observed_at,evidence,recorded_at) VALUES (?,?,?,?,?,?,?,?,?)",
            ("issuer", issuer_id, "cik", row["cik"], None, None, row["created_at"], evidence, now),
        )
    latest = db.execute(
        "SELECT listing_id,instrument_id,issuer_id FROM security_identity WHERE security_id=? ORDER BY id DESC LIMIT 1",
        (row["id"],),
    ).fetchone()
    if latest is None or tuple(latest) != (row["id"], instrument_id, issuer_id):
        db.execute(
            "INSERT INTO security_identity(security_id,listing_id,instrument_id,issuer_id,basis,recorded_at) VALUES (?,?,?,?,?,?)",
            (row["id"], row["id"], instrument_id, issuer_id, basis, now),
        )
    return {
        "security_id": row["id"],
        "listing_id": row["id"],
        "instrument_id": instrument_id,
        "issuer_id": issuer_id,
    }


def backfill(db, now):
    for row in db.execute("SELECT * FROM securities ORDER BY created_at, id").fetchall():
        ensure_identity(db, row, now, basis="migrated from the v1 securities row")


def current(db, security_id, as_of: str | None = None) -> dict | None:
    """The latest identity mapping of a listing, or the latest recorded at or before `as_of`."""
    row = db.execute(
        """SELECT si.*, i.name AS issuer_name, i.cik, i.association AS issuer_association, l.venue, l.trading_currency
                        FROM security_identity si JOIN issuers i ON i.id=si.issuer_id JOIN listings l ON l.id=si.listing_id
                        WHERE si.security_id=? AND (? IS NULL OR si.recorded_at<=?) ORDER BY si.id DESC LIMIT 1""",
        (security_id, as_of, as_of),
    ).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["aliases"] = [
        dict(a, evidence=json.loads(a["evidence"]))
        for a in db.execute(
            "SELECT * FROM identifier_aliases WHERE (subject_kind='listing' AND subject_id=?) OR (subject_kind='issuer' AND subject_id=?) ORDER BY id",
            (security_id, out["issuer_id"]),
        )
    ]
    return out

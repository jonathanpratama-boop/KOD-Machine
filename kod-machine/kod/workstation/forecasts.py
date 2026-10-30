"""Read-only replay of KOD's sealed market forecasts (LEARNER v2.4, idx-signals/paper).

The forecast ledger and the Speculation Register are append-only hash chains written by idx-signals. This module
reads them with the standard library only: no idx-signals import, no network, no writes. Every read re-checks each
record's hash and its link to the previous record; a broken chain withholds the replay instead of showing it.

What a cutoff shows:
- the sealed set (the spike and its matched twins) once it was sealed,
- the forecast once it was made, with the numbers and inputs it recorded,
- the outcome only when the caller asks for it AND the register recorded it by the cutoff.
Nothing is recomputed here. Reproduction is idx-signals' `learner3-verify`; this view states which record it shows.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PAPER = Path(__file__).resolve().parents[3] / "idx-signals" / "paper"
FORECASTS = "learner_v3.jsonl"
REGISTER = "speculations.jsonl"
TOKENS = "timestamps"
FORECAST_TYPE = "LEARNER3_FORECAST"
HEADLINE = "NEXT_DUMP10_1"
STATEMENTS = {
    "NEXT_DUMP10_1": "closes at least 10% below the spike-day close at the next session, when most of its twins do not",
    "DUMP10_5": "its 5-session plan ends at least 10% down, when most of its twins do not",
}


class ForecastUnavailable(ValueError):
    """The ledger cannot support a trustworthy replay."""


def _canonical(obj) -> str:
    """The exact serialisation idx-signals hashes (idxsig.paper._canonical)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _known(cutoff: datetime, value: str | None) -> bool:
    moment = _time(value)
    return moment is not None and moment <= cutoff


def read_chain(path: Path) -> list[dict]:
    """Every record of an append-only ledger, after checking each hash and each link."""
    if not path.exists():
        raise ForecastUnavailable(f"{path.name} is not present; nothing was created or fetched.")
    records, previous = [], None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        body = {k: v for k, v in record.items() if k != "record_hash"}
        if hashlib.sha256(_canonical(body).encode()).hexdigest() != record.get("record_hash"):
            raise ForecastUnavailable(
                f"{path.name} line {number}: record hash mismatch; replay withheld."
            )
        if record.get("prev_hash") != previous:
            raise ForecastUnavailable(
                f"{path.name} line {number}: broken chain link; replay withheld."
            )
        previous = record["record_hash"]
        records.append(record)
    return records


class ForecastArchive:
    def __init__(self, paper_dir: Path | str | None = None):
        self.paper = Path(paper_dir) if paper_dir is not None else DEFAULT_PAPER

    def _ledgers(self) -> tuple[list[dict], list[dict]]:
        return read_chain(self.paper / FORECASTS), read_chain(self.paper / REGISTER)

    def forecasts(self) -> list[dict]:
        """Navigation only: which forecasts exist. No probabilities, calls or outcomes."""
        forecasts, _ = self._ledgers()
        rows = [
            {
                "set_id": f["set_id"],
                "ticker": f.get("ticker"),
                "signal_session": f["signal_session"],
                "made_at": f["made_at"],
            }
            for f in forecasts
            if f.get("type") == FORECAST_TYPE
        ]
        return sorted(rows, key=lambda r: (r["signal_session"], r["ticker"] or ""), reverse=True)

    def snapshot(self, set_id: str, as_of: str, *, reveal_outcome: bool = False) -> dict:
        cutoff = _time(as_of)
        if cutoff is None:
            raise ValueError(
                "Use a timezone-qualified timestamp, for example 2026-10-30T13:30:00Z."
            )
        forecasts, register = self._ledgers()
        forecast = next(
            (f for f in forecasts if f.get("type") == FORECAST_TYPE and f["set_id"] == set_id), None
        )
        if forecast is None:
            raise ForecastUnavailable("Unknown forecast.")
        sealed = next(
            (r for r in register if r.get("type") == "SPECULATION_SET" and r["set_id"] == set_id),
            None,
        )
        if sealed is None or sealed["record_hash"] != forecast.get("set_record_hash"):
            raise ForecastUnavailable(
                "The forecast does not point at the sealed set it names; replay withheld."
            )

        resolutions = [
            r for r in register if r.get("type") == "RESOLUTION" and r["set_id"] == set_id
        ]
        timeline = sorted(
            {sealed["sealed_at"], forecast["made_at"], forecast["entry_cutoff"]}
            | {r["resolved_at"] for r in resolutions},
            key=_time,
        )

        out = {
            "as_of": _stamp(cutoff),
            "set_id": set_id,
            "ticker": forecast.get("ticker"),
            "signal_session": forecast["signal_session"],
            "timeline": timeline,
            "set": None,
            "forecast": None,
            "outcome": None,
            "outcome_status": "",
            "integrity": {
                "forecast_record": forecast["record_hash"],
                "set_record": sealed["record_hash"],
                "chains": f"{FORECASTS} and {REGISTER}: every record hash and link checked on this read",
                "external_timestamps": sorted(
                    p.name.split(".")[1]
                    for p in (self.paper / TOKENS).glob(forecast["record_hash"] + ".*.tsr")
                ),
            },
        }

        if _known(cutoff, sealed["sealed_at"]):
            out["set"] = {
                "sealed_at": sealed["sealed_at"],
                "entry_cutoff": sealed["entry_cutoff"],
                "signal": sealed.get("signal", {}),
                "twins": [t.get("ticker") for t in sealed.get("twins", [])],
                "twins_match_level": sealed.get("twins_match_level"),
                "register": sealed.get("register"),
            }

        if _known(cutoff, forecast["made_at"]):
            statements = []
            for name, fc in forecast["forecasts"].items():
                statements.append(
                    {
                        "statement": name,
                        "headline": name == HEADLINE,
                        "meaning": STATEMENTS.get(name, name),
                        "raw": fc["raw"],
                        "anchor": fc["anchor"],
                        "bench": fc["bench"],
                        "published": fc["published"],
                        "call": fc.get("call") or {},
                        "why": fc.get("why") or [],
                    }
                )
            out["forecast"] = {
                "learner": forecast.get("learner"),
                "protocol": forecast.get("protocol", {}),
                "made_at": forecast["made_at"],
                "statements": sorted(statements, key=lambda s: not s["headline"]),
                "features": forecast.get("features", {}),
                "provenance": {
                    "price_pull": forecast.get("provenance", {}).get("manifest", {}),
                    "sources_read": len(forecast.get("provenance", {}).get("responses", {})),
                },
                "reproduce": "idx-signals: python3 -m idxsig learner3-report (verify rebuilds every sealed forecast)",
            }

        visible = [r for r in resolutions if _known(cutoff, r["resolved_at"])]
        if not reveal_outcome:
            out["outcome_status"] = (
                "Hidden. Reveal it separately; the forecast above never depends on it."
            )
        elif not visible:
            out["outcome_status"] = (
                "Not recorded by this cutoff. The register grades each window after it closes."
            )
        else:
            latest = {}
            for r in visible:  # ledger order: a later correction of the same window wins
                latest[r["window"]] = r
            graded = []
            for window, r in sorted(latest.items()):
                for c in r.get("cone", []):
                    if c.get("outcome") is not None:
                        graded.append(
                            {
                                "window": window,
                                "statement": c["id"],
                                "outcome": bool(c["outcome"]),
                                "twins_rate": c.get("twins_rate"),
                                "resolved_at": r["resolved_at"],
                            }
                        )
            out["outcome"] = graded
            out["outcome_status"] = f"Recorded by the register: {len(graded)} graded statement(s)."
        return out

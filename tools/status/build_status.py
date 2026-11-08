#!/usr/bin/env python3
"""Build the KOD status dashboard data (stdlib only, Python 3.12+).

    python3 tools/status/build_status.py --kod /home/user/KOD-Machine \
        --kod-ref origin/claude/idx-signals-test-repo-ds0jw7 \
        --backups /home/user/kod-timing-backups --out <dir> [--now 2026-11-06T05:30:00Z]

What it does
  * Reads ONLY through `git show` / `git ls-tree` / `git log` on the given refs, so the
    working tree of either repo never matters and nothing is ever written to them.
  * Reads the registry tools/status/experiments.json (next to this script, or --registry).
    Every entry names a reader function below. The reader returns counts, an as-of time and
    the record times behind its counts. A reader that throws gives an UNKNOWN row plus a
    gaps.json READ_ERROR row; the build never stops because of one experiment.
  * Writes experiments.json, programs.json, summary.json, history.json, runs.json,
    run_days.json, server.json, server_history.json, events.json, gaps.json and build.json
    into --out. programs.json and summary.json are the owner's view: registry programs (groups
    of live tests) and one row of headline numbers.

Rules it enforces
  * EVIDENCE COLLECTED (records made), SCORED (outcomes that can be evaluated) and NEEDED (what
    the frozen protocol needs) are separate numbers; fraction = scored / needed only.
  * as_of is the time of the newest underlying RECORD, not a commit or push time. (Closed rows
    use the commit time of their verdict record, which has no internal stamp.)
  * A live row whose as_of is older than stale_after_hours reads UNKNOWN, never green.
    STALLED and HALTED, which carry positive evidence of a problem, are kept.
  * projected_date only comes from the scoring rate of the last 14 days; no rate means null.
  * No interim win rates or returns are written for a study that has not reached its look.

Day buckets: history.json uses WIB (UTC+7) days, because the US nightly runs straddle UTC
midnight but not WIB midnight. run_days.json uses the market session date. All times written
are ISO UTC ("...Z").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
WIB_OFFSET = timedelta(hours=7)
SIZE_LIMIT = 190_000  # bytes per output file (the page budget is 200 KB)
HISTORY_DAYS = 120  # history.json keeps the last 120 WIB days per experiment
SERVER_DAYS = 30  # server_history.json keeps 30 days ...
SERVER_FULL_HOURS = 48  # ... every heartbeat for the last 48 h, older ones thinned ...
SERVER_THIN_HOURS = 6  # ... to one per study per 6 h (status changes are always kept)
EVENT_DAYS = 31  # events.json keeps the last 31 days
RUN_DAYS = 30  # run_days.json: last 30 session dates per job
PROJECTION_WINDOW = 14  # days of history behind projected_date ...
PROJECTION_MIN_DAYS = 7  # ... or the days since the first record, but never fewer than this
LIVE_STATES = ("RUNNING", "WAITING")
BAD_STATES = ("HALTED", "STALLED", "UNKNOWN")  # a row in one of these carries a plain `issue`
GAIN_DAYS = 7  # programs.json: scored_7d / collected_7d look back this many WIB days
OUTCOMES = ("worked", "didnt_work", "no_answer", "not_an_idea")  # registry `outcome` values
# Plain names for the catalyst filing feeds, used in a stalled feed's `issue` text. A registry
# entry's params.feed_plain overrides this.
FEED_PLAIN = {
    "SEC13D": "investor-stake filings",
    "SEC13D_V2": "investor-stake filings",
    "DILUTION_8K": "share-offering filings",
    "FORM4": "insider filings",
    "FORM4_SHARP": "insider filings",
}
# Word limits for the owner-facing registry text (over the limit: a build warning, not an error).
WORD_LIMITS = {
    "live": {"short": 4, "ceo_line": 14, "unit": 3},
    "closed": {"short": 5, "lesson": 18},
}


# ===================================================================================== time helpers
def parse_ts(text: str) -> datetime:
    """ISO-8601 -> aware UTC. Accepts 'Z', offsets, minute precision ('2026-11-02T22:10Z')."""
    value = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def norm_iso(text: str | None) -> str | None:
    """Any ISO stamp -> 'YYYY-MM-DDTHH:MM:SSZ' (so string comparison and max() work)."""
    return iso(parse_ts(text)) if text else None


def exact_iso(text: str | None) -> str | None:
    """Like norm_iso but keeps sub-second precision when the record carries it, so an
    as_of is the record's own stamp, not a truncated copy."""
    if not text:
        return None
    value = parse_ts(text)
    if value.microsecond:
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return iso(value)


def wib_day(text: str) -> str:
    return (parse_ts(text) + WIB_OFFSET).date().isoformat()


def day_range(first: str, last: str):
    current, end = date.fromisoformat(first), date.fromisoformat(last)
    while current <= end:
        yield current.isoformat()
        current += timedelta(days=1)


def at_utc(day: date, hhmm: str, plus_days: int = 0) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC) + timedelta(
        days=plus_days
    )


def newest(stamps) -> str | None:
    values = [norm_iso(s) for s in stamps if s]
    return max(values) if values else None


def plain_day(day: str, today: str) -> str:
    """'2026-11-04' -> 'Nov 4' (with the year when it is not `today`'s year)."""
    value = date.fromisoformat(day)
    text = f"{value:%b} {value.day}"
    return text if day[:4] == today[:4] else f"{text}, {value.year}"


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def days_since(stamp: str, now: datetime) -> int:
    """Whole days from a record time to the build time (at least 1)."""
    return max(1, int((now - parse_ts(stamp)).total_seconds() // 86400))


# ===================================================================================== git access
class SourceMissing(Exception):
    """A registry source does not exist at the ref (reported as SOURCE_MISSING)."""


class Repo:
    """Read-only access to one git repo through git show / ls-tree / log, with a small cache."""

    def __init__(self, path: str, ref: str | None, label: str):
        self.path, self.ref, self.label = path, ref, label
        self._text: dict = {}
        self._rows: dict = {}

    def git(self, *args: str) -> str | None:
        done = subprocess.run(["git", "-C", self.path, *args], capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else None

    def text(self, path: str, ref: str | None = None) -> str:
        key = (ref or self.ref, path)
        if key not in self._text:
            out = self.git("show", f"{key[0]}:{path}")
            if out is None:
                raise SourceMissing(f"{self.label}:{key[0]}:{path}")
            self._text[key] = out
        return self._text[key]

    def exists(self, path: str, ref: str | None = None) -> bool:
        return self.git("cat-file", "-e", f"{ref or self.ref}:{path}") is not None

    def json(self, path: str, ref: str | None = None):
        return json.loads(self.text(path, ref))

    def jsonl(self, path: str, optional: bool = False) -> list[dict]:
        """Rows of a JSON-lines file. A bad line raises (READ_ERROR). optional: a missing file is
        []."""
        if path not in self._rows:
            try:
                text = self.text(path)
            except SourceMissing:
                if optional:
                    return []
                raise
            rows = []
            for number, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{number}: not a JSON object")
                rows.append(row)
            self._rows[path] = rows
        return self._rows[path]

    def ls(self, directory: str, ref: str | None = None) -> list[str]:
        out = self.git("ls-tree", "--name-only", ref or self.ref, directory.rstrip("/") + "/")
        return out.split("\n")[:-1] if out else []

    def ls_recursive(self, prefix: str = "") -> list[str]:
        args = ["ls-tree", "-r", "--name-only", self.ref] + ([prefix] if prefix else [])
        out = self.git(*args)
        return out.split("\n")[:-1] if out else []

    def head(self, ref: str | None = None) -> str:
        return (self.git("rev-parse", ref or self.ref) or "").strip()

    def last_commit(self, path: str, ref: str | None = None) -> str | None:
        out = (self.git("log", "-1", "--format=%cI", ref or self.ref, "--", path) or "").strip()
        return norm_iso(out) if out else None

    def first_commit(self, path: str) -> str | None:
        out = (
            self.git("log", "--diff-filter=A", "--format=%cI", self.ref, "--", path) or ""
        ).split()
        return norm_iso(out[-1]) if out else None

    def commits(self, ref: str) -> list[tuple[str, str]]:
        out = self.git("log", "--reverse", "--format=%H %cI", ref) or ""
        return [tuple(line.split()) for line in out.splitlines() if line.strip()]

    def remote_branches(self) -> list[str]:
        out = self.git("branch", "-r", "--format=%(refname:short)") or ""
        names = [b[len("origin/") :] for b in out.split() if b.startswith("origin/")]
        return [b for b in names if b and b != "HEAD"]


# =================================================================================== build context
class Ctx:
    """Everything a reader may use: both repos, the registry calendars, the build time."""

    def __init__(self, kod: Repo, backups: Repo, registry: dict, now: datetime):
        self.kod, self.backups, self.registry, self.now = kod, backups, registry, now
        self.today_wib = (now + WIB_OFFSET).date().isoformat()
        self.calendars = registry.get("calendars", {})

    @property
    def now_iso(self) -> str:
        return iso(self.now)

    def trading_day(self, calendar: str, day: date) -> bool:
        cal = self.calendars.get(calendar, {})
        if cal.get("every_day"):
            return True
        return day.weekday() < 5 and day.isoformat() not in set(cal.get("holidays", []))

    def next_trading_day(self, calendar: str, day: date) -> date:
        day += timedelta(days=1)
        while not self.trading_day(calendar, day):
            day += timedelta(days=1)
        return day


def reading(**values) -> dict:
    """A reader's result: counts, as_of, record times, notes, optional events/server rows."""
    base = {
        "collected": None,
        "scored": None,
        "as_of": None,
        "state": None,
        "note": [],
        "collected_times": [],
        "scored_times": [],
        "events": [],
        "server": None,
        "server_history": [],
        "needed": "registry",
        "projected_fixed": None,
        "gaps": [],
        "issue": None,  # plain words (<= 10) when the reader sets STALLED or HALTED
    }
    base.update(values)
    return base


def event(at: str | None, kind: str, title: str, detail: str, source: str) -> dict:
    return {"at": norm_iso(at), "kind": kind, "title": title, "detail": detail, "source": source}


# ============================================================================= shared ledger logic
def latest_resolutions(rows: list[dict], before: str | None = None) -> dict:
    """(register namespace, set_id, window) -> the last RESOLUTION in file order (resolved before
    `before`)."""
    out = {}
    for row in rows:
        if row.get("type") != "RESOLUTION":
            continue
        if before is not None and (row.get("resolved_at") or "9") >= before:
            continue
        register = (row.get("register") or "").split("-v")[0]
        out[(register, row["set_id"], row.get("window"))] = row
    return out


def cone_outcomes(rows: list[dict], before: str) -> dict:
    """(set_id, statement) -> (outcome, resolved_at, twins_rate) for graded cone statements."""
    out = {}
    for res in latest_resolutions(rows, before).values():
        for cone in res.get("cone") or []:
            if cone.get("outcome") is not None:
                out[(res["set_id"], cone["id"])] = (
                    bool(cone["outcome"]),
                    res["resolved_at"],
                    cone.get("twins_rate"),
                )
    return out


def own_move(outcomes: dict, set_id: str, base: str):
    """The stock's own move: false if it did not happen; true if it did and fewer than half the
    twins did."""
    found = outcomes.get((set_id, base))
    if found is None:
        return None
    if not found[0]:
        return False, found[1]
    return None if found[2] is None else (found[2] < 0.5, found[1])


def all_sets(catalysts: list[dict], register: list[dict]) -> dict:
    sets = {r["set_id"]: r for r in catalysts if r.get("type") == "CATALYST_SET"}
    for row in register:
        if row.get("type") == "SPECULATION_SET":
            sets[row["set_id"]] = {**row, "family": "SPEC_" + row.get("market", "US")}
    return sets


def bound_forecasts(forecasts: list[dict], kind: str, sets: dict, now_iso: str):
    """First forecast per set, bound to the set's record_hash and made before its entry cutoff."""
    seen = set()
    for forecast in forecasts:
        if (
            forecast.get("type") != kind
            or forecast["made_at"] >= now_iso
            or forecast["set_id"] in seen
        ):
            continue
        the_set = sets.get(forecast["set_id"])
        if the_set is None or the_set.get("record_hash") != forecast.get("set_record_hash"):
            continue
        if forecast["made_at"] >= the_set["entry_cutoff"]:
            continue
        seen.add(forecast["set_id"])
        yield forecast


def norm_minute(text: str) -> str:
    """'2026-11-02T22:10Z' -> '2026-11-02T22:10:00Z' so it compares with second-precision stamps."""
    return text[:-1] + ":00Z" if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\dZ", text) else text


# ============================================================================== readers: forecasts
LLM_STATEMENTS = ("RUN30_5", "FADE10_5", "BEATS_TWINS_5")
CALLS_FILE = re.compile(r"/calls[^/]*\.jsonl$")


def unmerged_calls(ctx: Ctx, calls_dir: str) -> list[dict]:
    """Call rows in calls*.jsonl files that exist on another remote branch of the KOD repo but not
    on the data ref. They are never counted (the data ref is the record), only reported, so a call
    that was made in time but not merged is not described as 'never called'. Each row gets
    `_branch`, `_path` and `_commit` (the commit that added the file on that branch)."""
    if not hasattr(ctx, "_unmerged_calls"):
        ctx._unmerged_calls = {}
    if calls_dir in ctx._unmerged_calls:
        return ctx._unmerged_calls[calls_dir]
    on_ref = {f for f in ctx.kod.ls(calls_dir) if CALLS_FILE.search(f)}
    seen, out = set(), []
    for branch in sorted(ctx.kod.remote_branches()):
        ref = "origin/" + branch
        if ref == ctx.kod.ref:
            continue
        for path in ctx.kod.ls(calls_dir, ref):
            if not CALLS_FILE.search(path) or path in on_ref or path in seen:
                continue
            seen.add(path)
            commit = (
                ctx.kod.git("log", "--diff-filter=A", "-1", "--format=%h %cI", ref, "--", path)
                or ""
            ).split()
            for line in ctx.kod.text(path, ref).splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if isinstance(row, dict):
                    row.update(
                        _branch=branch,
                        _path=path,
                        _commit=" ".join(commit[:1]) or "?",
                    )
                    out.append(row)
    ctx._unmerged_calls[calls_dir] = out
    return out


def call_links(call: dict, the_set: dict) -> bool:
    """audit-v1 linkage of one call to its sealed set (not the uniqueness rules)."""
    if any(call.get(k) != the_set.get(k) for k in ("ticker", "market", "signal_session")):
        return False
    called = norm_minute(call.get("called_at", ""))
    if not the_set["sealed_at"] <= called < the_set["entry_cutoff"]:
        return False
    return call.get("call") in ("BACK", "AVOID", "ABSTAIN")


def read_llm_arm(ctx: Ctx, p: dict) -> dict:
    """LLM_ARM_v1. collected = call rows passing audit-v1's linkage rules; scored = calls whose set
    has one complete BASE5 resolution (RESOLVED, same protocol, after the call and cutoff, boolean
    outcomes and the sealed priors on RUN30_5, FADE10_5, BEATS_TWINS_5)."""
    files = [f for f in ctx.kod.ls(p["calls_dir"]) if re.search(r"/calls[^/]*\.jsonl$", f)]
    if not files:
        raise SourceMissing(f"KOD:{p['calls_dir']}/calls*.jsonl")
    calls = [row for f in sorted(files) for row in ctx.kod.jsonl(f)]
    register = ctx.kod.jsonl(p["register"])
    set_rows = defaultdict(list)
    for row in register:
        if row.get("type") == "SPECULATION_SET":
            set_rows[row["set_id"]].append(row)
    base5 = defaultdict(list)
    for row in register:
        if row.get("type") == "RESOLUTION" and row.get("window") == "BASE5":
            base5[row["set_id"]].append(row)
    ids = Counter(c.get("call_id") for c in calls)
    per_set = Counter(c.get("set") for c in calls)
    counted, scored = [], []
    for call in calls:
        if (
            ids[call.get("call_id")] > 1
            or per_set[call.get("set")] > 1
            or len(set_rows[call.get("set")]) != 1
        ):
            continue
        the_set = set_rows[call["set"]][0]
        called = norm_minute(call["called_at"])
        if not call_links(call, the_set):
            continue
        counted.append((call, the_set))
        resolutions = base5.get(call["set"], [])
        if len(resolutions) == 1 and llm_call_scored(called, the_set, resolutions[0]):
            scored.append(resolutions[0])
    first_call = min((norm_minute(c["called_at"]) for c, _ in counted), default=None)
    called_sets = {c["set"] for c, _ in counted}
    due = [
        s
        for rows in set_rows.values()
        for s in rows
        if first_call
        and first_call < s["entry_cutoff"]
        and (s["entry_cutoff"] <= ctx.now_iso or s["set_id"] in called_sets)
    ]
    missed = [s for s in due if s["set_id"] not in called_sets]
    elsewhere = {}  # set_id -> an in-time call found only on an unmerged branch
    for call in unmerged_calls(ctx, p["calls_dir"]):
        rows = set_rows.get(call.get("set"), [])
        if len(rows) == 1 and call["set"] not in called_sets and call_links(call, rows[0]):
            elsewhere.setdefault(call["set"], call)
    unmerged = [s for s in missed if s["set_id"] in elsewhere]
    missed = [s for s in missed if s["set_id"] not in elsewhere]
    actions = Counter(c["call"] for c, _ in counted)
    disagree = sum(1 for c, _ in counted if c.get("agrees_with_kod") is False)
    coverage = (
        f"coverage: {len(due) - len(missed) - len(unmerged)} of {len(due)} sealed sets have a "
        "call on the data branch made before their cutoff"
    )
    if unmerged:
        branches = sorted(
            {
                f"{elsewhere[s['set_id']]['_branch']} (commit {elsewhere[s['set_id']]['_commit']})"
                for s in unmerged
            }
        )
        coverage += (
            f"; {len(unmerged)} more call(s) were made before their cutoff but exist only on "
            f"branch {', '.join(branches)}, not merged into the data branch, so they are not "
            "counted in 'calls made' until merged"
        )
    coverage += f"; {len(missed)} set(s) got no call anywhere (these can never be called)"
    notes = [
        coverage,
        "calls: "
        + ", ".join(f"{a} {actions.get(a, 0)}" for a in ("BACK", "AVOID", "ABSTAIN"))
        + f"; disagreements with KOD {disagree}",
    ]
    events, gaps = [], []
    by_session = defaultdict(list)
    for s in missed:
        by_session[(s["market"], s["signal_session"])].append(s)
    for (market, session), rows in sorted(by_session.items()):
        cutoff = min(r["entry_cutoff"] for r in rows)
        tickers = ", ".join(sorted(r["ticker"] for r in rows))
        events.append(
            event(
                cutoff,
                "incident",
                f"LLM arm: {len(rows)} {market} set(s) of {session} got no call",
                f"Entry cutoff passed with no call for {tickers} on the data branch or any other "
                "branch; these can never be called.",
                f"KOD:{p['register']} (SPECULATION_SET entry_cutoff) vs "
                f"KOD:{p['calls_dir']}/calls*.jsonl",
            )
        )
    by_file = defaultdict(list)
    for s in unmerged:
        call = elsewhere[s["set_id"]]
        by_file[(call["_branch"], call["_path"], call["_commit"])].append((s, call))
    for (branch, path, commit), pairs in sorted(by_file.items()):
        made = max(norm_minute(c["called_at"]) for _, c in pairs)
        sessions = sorted({f"{s['market']} {s['signal_session']}" for s, _ in pairs})
        tickers = ", ".join(sorted(s["ticker"] for s, _ in pairs))
        events.append(
            event(
                made,
                "incident",
                f"LLM arm: {len(pairs)} call(s) for {', '.join(sessions)} not merged into the "
                "data branch",
                f"Calls for {tickers} were made at {made}, before their entry cutoffs, but "
                f"{path} exists only on branch {branch} (commit {commit}). They are not counted "
                "until merged into the data branch.",
                f"KOD:origin/{branch}:{path}",
            )
        )
        gaps.append(
            {
                "kind": "NOT_ON_DASHBOARD",
                "path": f"KOD:origin/{branch}:{path}",
                "detail": f"LLM_ARM_v1: {len(pairs)} in-time call(s) ({tickers}) on a branch not "
                "merged into the data ref; merge them so they count",
            }
        )
    return reading(
        collected=len(counted),
        scored=len(scored),
        as_of=newest(norm_minute(c["called_at"]) for c, _ in counted),
        collected_times=[norm_minute(c["called_at"]) for c, _ in counted],
        scored_times=[r["resolved_at"] for r in scored],
        note=notes,
        events=events,
        gaps=gaps,
    )


def llm_call_scored(called: str, the_set: dict, res: dict) -> bool:
    if res.get("status") != "RESOLVED" or res.get("protocol") != the_set.get("protocol"):
        return False
    if res["resolved_at"] < max(called, the_set["entry_cutoff"]):
        return False
    cone = {x["id"]: x for x in res.get("cone") or []}
    sealed = {x["id"]: x for x in the_set.get("cone") or []}
    return all(
        isinstance(cone.get(k, {}).get("outcome"), bool)
        and cone[k].get("prior") == sealed.get(k, {}).get("prior")
        for k in LLM_STATEMENTS
    )


def read_spec_register(ctx: Ctx, p: dict) -> dict:
    """Speculation Register, one market. collected = SPECULATION_SET rows; scored = latest BASE5
    RESOLUTION per set with status RESOLVED and a paired twin difference (the unit the look
    counts)."""
    market = p["market"]
    register = [r for r in ctx.kod.jsonl(p["register"]) if r.get("market") == market]
    sets = {r["set_id"]: r for r in register if r.get("type") == "SPECULATION_SET"}
    latest = latest_resolutions(register)
    paired = [
        r
        for (_, _, w), r in latest.items()
        if w == "BASE5" and r["status"] == "RESOLVED" and r.get("paired") is not None
    ]
    by_window = Counter(f"{w} {r['status']}" for (_, _, w), r in latest.items())
    sessions = {r["signal_session"] for r in paired}
    notes = [
        f"signal sessions among scored sets: {len(sessions)} of {p.get('min_sessions', 15)} needed "
        f"(sets sealed over {len({s['signal_session'] for s in sets.values()})} sessions)",
        "latest resolutions by window: "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_window.items())),
    ]
    events = []
    if paired:
        first = min(paired, key=lambda r: r["resolved_at"])
        events.append(
            event(
                first["resolved_at"],
                "milestone",
                f"Speculation Register {market}: first paired 5-day result",
                f"Set {first['set_id']} resolved BASE5 with a twin comparison.",
                f"KOD:{p['register']} (RESOLUTION window BASE5)",
            )
        )
    stamps = [s["sealed_at"] for s in sets.values()] + [r["resolved_at"] for r in latest.values()]
    return reading(
        collected=len(sets),
        scored=len(paired),
        as_of=newest(stamps),
        collected_times=[s["sealed_at"] for s in sets.values()],
        scored_times=[r["resolved_at"] for r in paired],
        note=notes,
        events=events,
    )


V22_SKILL_KINDS = ("RELATIVE", "MECHANISM", "TRIANGULATED", "PATH")
V22_TRIANGLES = {
    "SEC13D_V2": ("MECH_13DA_UP_60", "BEATS_TWINS_60"),
    "FORM4_SHARP": ("MECH_SECOND_BUY_20", "BEATS_TWINS_60"),
}
V22_BASE = {"PUMP30": "RUN30", "PUMP100": "DOUBLE", "DUMP10": "FADE10"}
V22_PATH = re.compile(r"^(PUMP30|PUMP100|DUMP10|PUMP_AND_DUMP)_(\d+)$")
BLOCK_EPOCH = date(2000, 1, 3)


def v22_outcome(outcomes: dict, set_id: str, family: str, statement: str):
    match = V22_PATH.match(statement)
    if statement == "TRIANGULATED":
        if family not in V22_TRIANGLES:
            return None
        first, second = (outcomes.get((set_id, x)) for x in V22_TRIANGLES[family])
    elif match and match[1] == "PUMP_AND_DUMP":
        first = own_move(outcomes, set_id, f"RUN30_{match[2]}")
        second = own_move(outcomes, set_id, f"FADE10_{match[2]}")
    elif match:
        return own_move(outcomes, set_id, f"{V22_BASE[match[1]]}_{match[2]}")
    else:
        found = outcomes.get((set_id, statement))
        return None if found is None else (found[0], found[1])
    if first is None or second is None:
        return None
    return first[0] and second[0], max(first[1], second[1])


def block_of(stamp: str) -> int:
    return (date.fromisoformat(stamp[:10]) - BLOCK_EPOCH).days // 28


def block_end(block: int) -> str:
    return (BLOCK_EPOCH + timedelta(days=28 * (block + 1))).isoformat() + "T00:00:00Z"


def read_learner_v22(ctx: Ctx, p: dict) -> dict:
    """LEARNER v2.2. collected = sealed forecasts. scored = FINISHED 4-week blocks holding claim
    pairs (the look needs 60 pairs AND 15 finished blocks; the block rule binds, so pairs would
    mislead a progress bar)."""
    forecasts = ctx.kod.jsonl(p["forecasts"])
    catalysts, register = ctx.kod.jsonl(p["catalysts"]), ctx.kod.jsonl(p["register"])
    sets = all_sets(catalysts, register)
    outcomes = cone_outcomes(catalysts + register, ctx.now_iso)
    pairs = []
    for forecast in bound_forecasts(forecasts, "LEARNER2_FORECAST", sets, ctx.now_iso):
        for statement, spec in forecast["forecasts"].items():
            if spec.get("kind") not in V22_SKILL_KINDS:
                continue
            found = v22_outcome(outcomes, forecast["set_id"], forecast.get("family"), statement)
            if found is not None and found[1] > forecast["made_at"]:
                pairs.append((forecast.get("event_key", forecast["set_id"]), statement, found[1]))
    first_pairs = {}
    for key, statement, stamp in sorted(pairs, key=lambda x: x[2]):
        first_pairs.setdefault((key, statement), stamp)
    blocks = Counter(
        block_of(s) for s in first_pairs.values() if block_end(block_of(s)) <= ctx.now_iso
    )
    own = [f for f in forecasts if f.get("type") == "LEARNER2_FORECAST"]
    notes = [
        f"{len(pairs)} forward-scored pairs so far ({sum(blocks.values())} in finished blocks); "
        f"the look needs {p.get('min_pairs', 60)} pairs and {p.get('min_blocks', 15)} "
        "finished blocks"
    ]
    if pairs:
        first_block = min(block_of(s) for _, _, s in pairs)
        earliest = (
            BLOCK_EPOCH + timedelta(days=28 * (first_block + p.get("min_blocks", 15)))
        ).isoformat()
        notes.append(
            f"current block ends {block_end(first_block)[:10]}; earliest possible first look "
            f"{earliest} (block rule, not a forecast)"
        )
    return reading(
        collected=len(own),
        scored=len(blocks),
        as_of=newest(f["made_at"] for f in own),
        collected_times=[f["made_at"] for f in own],
        scored_times=[block_end(b) for b in blocks],
        note=notes,
    )


V24_BASE = {"NEXT_DUMP10_1": "DOWN10_1", "DUMP10_5": "FADE10_5"}


def read_learner_v24(ctx: Ctx, p: dict) -> dict:
    """LEARNER v2.4. collected = sealed forecasts; scored = headline NEXT_DUMP10_1 outcomes resolved
    after the forecast. A look is official only as a frozen LEARNER3_EVALUATION row (missing file =
    none yet)."""
    forecasts = ctx.kod.jsonl(p["forecasts"])
    catalysts, register = ctx.kod.jsonl(p["catalysts"]), ctx.kod.jsonl(p["register"])
    evaluations = ctx.kod.jsonl(p["evaluations"], optional=True)
    sets = all_sets(catalysts, register)
    outcomes = cone_outcomes(catalysts + register, ctx.now_iso)
    headline = []
    for forecast in bound_forecasts(forecasts, "LEARNER3_FORECAST", sets, ctx.now_iso):
        found = own_move(outcomes, forecast["set_id"], V24_BASE["NEXT_DUMP10_1"])
        if (
            "NEXT_DUMP10_1" in forecast["forecasts"]
            and found is not None
            and found[1] > forecast["made_at"]
        ):
            headline.append((forecast["signal_session"], found[1]))
    own = [f for f in forecasts if f.get("type") == "LEARNER3_FORECAST"]
    forecast_sets = {f["set_id"] for f in own}
    missing = [
        s
        for s in sets.values()
        if s.get("family") == "SPEC_US"
        and (s.get("protocol") or {}).get("id") == p["set_protocol"]
        and s.get("sealed_at", "") >= p["first_set_sealed_at"]
        and s["entry_cutoff"] <= ctx.now_iso
        and s["set_id"] not in forecast_sets
    ]
    frozen = sum(1 for e in evaluations if e.get("type") == "LEARNER3_EVALUATION")
    notes = [
        f"signal sessions among scored outcomes: {len({s for s, _ in headline})} of "
        f"{p.get('min_sessions', 30)} needed",
        f"frozen evaluations: {frozen}",
        f"due US sets that never got a forecast: {len(missing)} (permanent)",
    ]
    events = []
    by_session = defaultdict(list)
    for s in missing:
        by_session[s["signal_session"]].append(s)
    for session, rows in sorted(by_session.items()):
        events.append(
            event(
                min(r["entry_cutoff"] for r in rows),
                "incident",
                f"LEARNER v2.4 sealed no forecast for {len(rows)} US set(s) of {session}",
                "Entry cutoff passed without a LEARNER3_FORECAST; the sets can never be forecast.",
                f"KOD:{p['forecasts']} vs KOD:{p['register']} (SPECULATION_SET entry_cutoff)",
            )
        )
    return reading(
        collected=len(own),
        scored=len(headline),
        as_of=newest(f["made_at"] for f in own),
        collected_times=[f["made_at"] for f in own],
        scored_times=[t for _, t in headline],
        note=notes,
        events=events,
    )


def read_call_cert_report(ctx: Ctx, p: dict) -> dict:
    """CALL_CERT shadow calls, parsed from the report the nightly writes (the calls come from a
    fitted model). A call is a '**DUMP**' row; scored when its outcome reads 'dumped' or 'did not
    dump'."""
    report = ctx.kod.text(p["report"])
    generated = re.search(r"^Generated (\S+Z) ", report, re.M)
    if not generated:
        raise ValueError(f"{p['report']}: no 'Generated <ISO>Z' line")
    rows = [
        [c.strip() for c in line.split("|")[1:-1]]
        for line in report.splitlines()
        if re.match(r"^\| \d{4}-\d\d-\d\d \|", line)
    ]
    if not rows:
        raise ValueError(f"{p['report']}: no forecast table rows")
    calls = [r for r in rows if r[4] == "**DUMP**"]
    resolved = [r for r in calls if r[6] in ("dumped", "did not dump")]
    forecasts = [f for f in ctx.kod.jsonl(p["forecasts"]) if f.get("type") == "LEARNER3_FORECAST"]
    register = ctx.kod.jsonl(p["register"])
    next1 = {
        r["set_id"]: r for r in latest_resolutions(register).values() if r.get("window") == "NEXT1"
    }
    made = {f["set_id"]: f["made_at"] for f in forecasts}

    def set_id(row):
        return p["set_id_pattern"].format(session=row[0], ticker=row[1])

    newest_record = newest(
        [f["made_at"] for f in forecasts]
        + [next1[f["set_id"]]["resolved_at"] for f in forecasts if f["set_id"] in next1]
    )
    notes = [
        f"{len(rows)} shadow forecasts, {len(calls)} calls, {len(calls) - len(resolved)} "
        "calls open; "
        "outcome rates are left to paper/CALL_CERT.md (no frozen live look)"
    ]
    stale_pending = [
        f"{r[1]} {r[0]}"
        for r in rows
        if r[6] == "pending" and next1.get(set_id(r), {}).get("status") == "UNRESOLVABLE"
    ]
    if stale_pending:
        notes.append(
            "shown 'pending' but UNRESOLVABLE in the register: " + ", ".join(stale_pending)
        )
    as_of = norm_iso(generated[1])
    if newest_record and newest_record > as_of:
        notes.append(f"report is BEHIND its ledger (newest record {newest_record})")
    return reading(
        collected=len(calls),
        scored=len(resolved),
        as_of=as_of,
        collected_times=[made[set_id(r)] for r in calls if set_id(r) in made],
        scored_times=[next1[set_id(r)]["resolved_at"] for r in resolved if set_id(r) in next1],
        note=notes,
    )


# ================================================================================== readers: books
def read_paper_book(ctx: Ctx, p: dict) -> dict:
    """PAPER_BOOK_v1. collected = one BOOK_PLAN per set; scored = latest BOOK_RESULT TRADED with a
    return. Also lists US spikes whose entry cutoff passed with no plan (they are permanently out of
    the book)."""
    book = ctx.kod.jsonl(p["ledger"])
    plans = {}
    for row in book:
        if row["type"] == "BOOK_PLAN":
            plans.setdefault(row["set_id"], row)
    results = {r["set_id"]: r for r in book if r["type"] == "BOOK_RESULT"}
    traded = [
        r
        for r in results.values()
        if r.get("status") == "TRADED" and r.get("net_return") is not None
    ]
    sets = [
        r
        for r in ctx.kod.jsonl(p["upstream_sets"])
        if r.get("type") == "SPECULATION_SET"
        and r.get("market") == "US"
        and r["signal_session"] >= p["first_signal"]
    ]
    missed = [s for s in sets if s["set_id"] not in plans and s["entry_cutoff"] <= ctx.now_iso]
    verdicts = Counter(r.get("verdict") for r in plans.values())
    notes = [
        f"KOD book (BUY_OK) {verdicts.get('BUY_OK', 0)}, AVOIDED (DONT_BUY) "
        f"{verdicts.get('DONT_BUY', 0)}",
        f"US spikes that passed their cutoff with no plan: {len(missed)} (permanent)",
    ]
    events = []
    by_session = defaultdict(list)
    for s in missed:
        by_session[s["signal_session"]].append(s)
    for session, rows in sorted(by_session.items()):
        events.append(
            event(
                min(r["entry_cutoff"] for r in rows),
                "incident",
                f"Paper book: {len(rows)} US spike(s) of {session} passed cutoff unplanned",
                "No compatible LEARNER v2.4 forecast before the entry cutoff; the spikes are out "
                "of the book for good.",
                f"KOD:{p['upstream_sets']} vs KOD:{p['ledger']} (no BOOK_PLAN)",
            )
        )
    stamps = [r.get("made_at") or r.get("resolved_at") for r in book]
    return reading(
        collected=len(plans),
        scored=len(traded),
        as_of=newest(stamps),
        collected_times=[r["made_at"] for r in plans.values()],
        scored_times=[r["resolved_at"] for r in traded],
        note=notes,
        events=events,
    )


def read_paper_account(ctx: Ctx, p: dict) -> dict:
    """PAPER_ACCOUNT_v1 for one arm. collected = decisions (ACCT_ORDER + ACCT_DECLINE); scored =
    ACCT_EXIT."""
    rows = [r for r in ctx.kod.jsonl(p["ledger"]) if r.get("arm") == p["arm"]]
    orders = {r["record_hash"]: r for r in rows if r["type"] == "ACCT_ORDER"}
    entries = {r["order_record_hash"]: r for r in rows if r["type"] == "ACCT_ENTRY"}
    exits = [r for r in rows if r["type"] == "ACCT_EXIT"]
    cancels = {r["order_record_hash"] for r in rows if r["type"] == "ACCT_CANCEL"}
    declines = [r for r in rows if r["type"] == "ACCT_DECLINE"]
    marks = [r for r in rows if r["type"] == "ACCT_MARK"]
    filled = sum(1 for e in entries.values() if e.get("status") == "FILLED")
    pending = sum(1 for h in orders if h not in entries and h not in cancels)
    notes = [
        f"orders {len(orders)} (filled {filled}, rejected {len(entries) - filled}, pending "
        f"{pending}, "
        f"cancelled {len(cancels)}), declines {len(declines)}, nightly marks {len(marks)}",
        "PAPER account (no real money); P&L is not shown before a registered evaluation",
    ]
    events = []
    if exits:
        first = min(exits, key=lambda r: r["recorded_at"])
        events.append(
            event(
                first["recorded_at"],
                "milestone",
                f"Paper account {p['arm']}: first closed paper trade",
                f"{first.get('ticker', first.get('symbol', ''))} exit "
                f"{first.get('exit_reason', '')}",
                f"KOD:{p['ledger']} (ACCT_EXIT)",
            )
        )
    stamps = [r.get("made_at") or r.get("recorded_at") for r in rows]
    return reading(
        collected=len(orders) + len(declines),
        scored=len(exits),
        as_of=newest(stamps),
        collected_times=[r["made_at"] for r in list(orders.values()) + declines],
        scored_times=[r["recorded_at"] for r in exits],
        note=notes,
        events=events,
    )


def read_crypto_account(ctx: Ctx, p: dict) -> dict:
    """CRYPTO_ACCOUNT_v1. collected = recorded policy decisions. STALLED when crypto policy
    decisions in the ledger are not recorded by the account and either the oldest one is past the
    grace period or the account itself has not written anything for `account_stale_hours`."""
    rows = ctx.kod.jsonl(p["ledger"])
    decided = {r["decision_id"]: r for r in rows if r["type"] in ("ACCT_ORDER", "ACCT_DECLINE")}
    exits = [r for r in rows if r["type"] == "ACCT_EXIT"]
    policy = [
        r
        for r in ctx.kod.jsonl(p["policy_ledger"])
        if r.get("market") == "CRYPTO"
        and r.get("type") == "DECISION"
        and r.get("signal_session", "") >= p["first_signal"]
    ]
    backlog = [r for r in policy if r["decision_id"] not in decided]
    stamps = [r.get("made_at") or r.get("observed_at") or r.get("recorded_at") for r in rows]
    # as_of = the newest record this check read: the account's own writes AND the crypto policy
    # rows it was checked against (no decision due means the account is correctly idle).
    checked = [norm_iso(r["decided_at"]) for r in policy] + [
        norm_iso(r["discovered_at"])
        for r in ctx.kod.jsonl(p["policy_ledger"])
        if r.get("type") == "SCAN"
        and scan_market(r) == "CRYPTO"
        and r.get("session", "") >= p["first_signal"]
    ]
    state, notes, events, issue = None, [], [], None
    last_write = newest(stamps)
    grace = timedelta(hours=p.get("backlog_grace_hours", 6))
    if backlog:
        oldest = min(norm_iso(r["decided_at"]) for r in backlog)
        account_age = ctx.now - parse_ts(last_write) if last_write else None
        late = ctx.now - parse_ts(oldest) > grace
        idle = account_age is None or account_age > timedelta(hours=p["account_stale_hours"])
        if late or idle:
            state = "STALLED"
            days = sorted({wib_day(r["decided_at"]) for r in backlog})
            issue = (
                f"{plural(len(backlog), 'crypto decision')} "
                f"{'from' if len(days) == 1 else 'since'} {plain_day(days[0], ctx.today_wib)} "
                "not recorded"
            )
            since = (
                iso(parse_ts(oldest) + grace)
                if late or not last_write
                else iso(parse_ts(last_write) + timedelta(hours=p["account_stale_hours"]))
            )
            notes.append(
                f"STALLED since {since}: {len(backlog)} crypto policy decision(s) decided "
                f"{oldest} not recorded by the account after the "
                f"{p.get('backlog_grace_hours', 6)} h grace"
            )
        else:
            notes.append(
                f"{len(backlog)} crypto policy decision(s) decided {oldest} not recorded yet "
                f"(within the {p.get('backlog_grace_hours', 6)} h grace)"
            )
        events.append(
            event(
                oldest,
                "incident",
                f"Crypto account did not record {len(backlog)} policy decision(s)",
                ", ".join(sorted(r["decision_id"] for r in backlog)),
                f"KOD:{p['policy_ledger']} DECISION vs KOD:{p['ledger']}",
            )
        )
    recorded_until = max(
        (norm_iso(r["decided_at"]) for r in policy if r["decision_id"] in decided), default=None
    )
    notes.append(
        f"last account write {last_write}; as_of is the newest record checked (account or crypto "
        "policy ledger)"
        + (f"; newest recorded decision was decided {recorded_until}" if recorded_until else "")
    )
    return reading(
        collected=len(decided),
        scored=len(exits),
        as_of=newest(stamps + checked),
        state=state,
        issue=issue,
        collected_times=[r["made_at"] for r in decided.values()],
        scored_times=[r.get("recorded_at") or r.get("made_at") for r in exits],
        note=notes,
        events=events,
    )


def read_premove_shadow(ctx: Ctx, p: dict) -> dict:
    """PREMOVE_SHADOW_v1. collected = sealed decision days; scored = resolved decision days; needed
    = every calendar day of the fixed trial. A day that was never sealed is lost for good."""
    rows = ctx.kod.jsonl(p["ledger"])
    sealed = {r["decision_date"]: r for r in rows if r["type"] == "PREMOVE_SHADOW_FORECAST"}
    resolved = {r["decision_date"]: r for r in rows if r["type"] == "PREMOVE_SHADOW_RESOLUTION"}
    yesterday = (ctx.now.date() - timedelta(days=1)).isoformat()
    expected = list(day_range(p["first"], min(yesterday, p["last"])))
    missing = [d for d in expected if d not in sealed]
    needed = (date.fromisoformat(p["last"]) - date.fromisoformat(p["first"])).days + 1
    notes = [
        f"days never sealed: {', '.join(missing) if missing else 'none'} (at most "
        f"{needed - len(missing)} "
        f"of {needed} can now be sealed); final outcomes due {p['final_due']}"
    ]
    events = [
        event(
            f"{(date.fromisoformat(d) + timedelta(days=2)).isoformat()}T00:00:00Z",
            "incident",
            f"Pre-move shadow day {d} was never sealed",
            "No PREMOVE_SHADOW_FORECAST for this decision day; a day can only be sealed before its "
            "outcome bars exist, so the gap is permanent.",
            f"KOD:{p['ledger']} (no decision_date {d})",
        )
        for d in missing
    ]
    if resolved:
        first = min(resolved.values(), key=lambda r: r["resolved_at"])
        events.append(
            event(
                first["resolved_at"],
                "milestone",
                "Pre-move shadow trial: first day resolved",
                f"Decision day {first['decision_date']} got its 5-day outcomes.",
                f"KOD:{p['ledger']} (PREMOVE_SHADOW_RESOLUTION)",
            )
        )
    stamps = [r.get("made_at") or r.get("resolved_at") for r in rows]
    return reading(
        collected=len(sealed),
        scored=len(resolved),
        needed=needed,
        as_of=newest(stamps),
        collected_times=[r["made_at"] for r in sealed.values()],
        scored_times=[r["resolved_at"] for r in resolved.values()],
        note=notes,
        events=events,
        projected_fixed=p["final_due"],
    )


def catalyst_batches(rows: list[dict], family: str) -> list[dict]:
    return [r for r in rows if r.get("type") == "BATCH" and r.get("family") == family]


def missed_batch_sessions(ctx: Ctx, batches: list[dict], calendar: str, due_hhmm: str) -> list[str]:
    """US sessions after the family's last batch whose batch was due (next day `due_hhmm` UTC) but
    is absent."""
    if not batches:
        return []
    last = date.fromisoformat(max(b["signal_session"] for b in batches))
    out, day = [], ctx.next_trading_day(calendar, last)
    while at_utc(day, due_hhmm, 1) < ctx.now:
        out.append(day.isoformat())
        day = ctx.next_trading_day(calendar, day)
    return out


def never_batched_sessions(
    ctx: Ctx, batches: list[dict], calendar: str, due_hhmm: str
) -> list[str]:
    """US sessions between the family's first and last batch that never got a batch (a later batch
    does not backfill them)."""
    if not batches:
        return []
    have = {b["signal_session"] for b in batches}
    first = date.fromisoformat(min(have))
    last = max(have)
    out, day = [], ctx.next_trading_day(calendar, first)
    while day.isoformat() < last:
        if day.isoformat() not in have and at_utc(day, due_hhmm, 1) < ctx.now:
            out.append(day.isoformat())
        day = ctx.next_trading_day(calendar, day)
    return out


def stalled_feed_issue(ctx: Ctx, p: dict, family: str, last_batch: str) -> str:
    """Plain `issue` for a stopped catalyst feed, e.g. 'No new insider filings batch for 7 days'."""
    feed = p.get("feed_plain") or FEED_PLAIN.get(family, "filings")
    return f"No new {feed} batch for {plural(days_since(last_batch, ctx.now), 'day')}"


def coverage_gap(batch: dict) -> bool:
    return (
        batch.get("coverage_gap") is True or (batch.get("feed") or {}).get("coverage_gap") is True
    )


def read_catalyst(ctx: Ctx, p: dict) -> dict:
    """One catalyst family. collected = sealed sets; scored = latest RESOLUTION in the decision
    window, RESOLVED with a paired difference (FIRE sets only when the protocol says so). STALLED
    when batches stop."""
    rows = ctx.kod.jsonl(p["ledger"])
    family, window = p["family"], p["window"]
    sets = {}
    for row in rows:
        if row.get("type") == "CATALYST_SET" and row.get("family") == family:
            sets.setdefault(row["set_id"], row)
    scored = [
        r
        for r in latest_resolutions(rows).values()
        if r.get("family") == family
        and r.get("window") == window
        and r.get("status") == "RESOLVED"
        and (r.get("paired") or {}).get("diff") is not None
        and (not p.get("fire_only") or r.get("coverage") == "FIRE")
    ]
    batches = catalyst_batches(rows, family)
    missed = missed_batch_sessions(
        ctx, batches, p.get("calendar", "NYSE"), p.get("batch_due_utc", "14:00")
    )
    classes = Counter((s.get("coverage") or {}).get("class") for s in sets.values())
    notes = [
        f"FIRE {classes.get('FIRE', 0)}, ABSTAIN {classes.get('ABSTAIN', 0)}; scored signal "
        "sessions "
        f"{len({r['signal_session'] for r in scored})} of {p.get('look_sessions', 15)} needed"
    ]
    state, issue = None, None
    if missed:
        notes.append(f"no batch for US session(s) {', '.join(missed)} since the last one")
        if len(missed) >= p.get("stall_after_missed", 2):
            state = "STALLED"
            issue = stalled_feed_issue(ctx, p, family, max(b["sealed_at"] for b in batches))
    holes = never_batched_sessions(
        ctx, batches, p.get("calendar", "NYSE"), p.get("batch_due_utc", "14:00")
    )
    if holes:
        notes.append(
            f"US session(s) never batched since the family started: {', '.join(holes)} "
            "(permanent: a later batch does not backfill them)"
        )
    own_sessions = {b["signal_session"] for b in batches}
    feed = catalyst_batches(rows, p["gap_from"]) if p.get("gap_from") else batches
    gap_notes = []
    for b in sorted(feed, key=lambda x: x["sealed_at"]):
        if b["signal_session"] not in own_sessions or not coverage_gap(b):
            continue
        later = [
            x["sealed_at"]
            for x in feed
            if x["signal_session"] == b["signal_session"]
            and x["sealed_at"] > b["sealed_at"]
            and not coverage_gap(x)
        ]
        gap_notes.append(
            f"signal {b['signal_session']} (batch sealed {b['sealed_at']}"
            + (f"; a later batch sealed {min(later)} reports no gap" if later else "")
            + ")"
        )
    if gap_notes:
        notes.append(
            "batch(es) with a feed coverage gap"
            + (f" in the source feed {p['gap_from']}" if p.get("gap_from") else "")
            + ": "
            + ", ".join(gap_notes)
        )
    events = [
        event(
            b["sealed_at"],
            "incident",
            f"Catalyst {family}: batch with a feed coverage gap",
            f"Batch for signal {b['signal_session']} could not read back far enough; "
            "filings in the gap "
            "are never backfilled.",
            f"KOD:{p['ledger']} (BATCH feed.coverage_gap)",
        )
        for b in batches
        if coverage_gap(b)
    ]
    stamps = [
        r.get("sealed_at") or r.get("resolved_at")
        for r in rows
        if r.get("family") == family and r.get("type") in ("BATCH", "CATALYST_SET", "RESOLUTION")
    ]
    return reading(
        collected=len(sets),
        scored=len(scored),
        as_of=newest(stamps),
        state=state,
        issue=issue,
        collected_times=[s["sealed_at"] for s in sets.values()],
        scored_times=[r["resolved_at"] for r in scored],
        note=notes,
        events=events,
    )


def read_catalyst_pooled(ctx: Ctx, p: dict) -> dict:
    """Pooled document-class test: FIRE parent sets of several families. Its as_of is the newest
    pooled record; a stopped feeding family is caught by the stall rule (STALLED) and named in the
    note with its own last batch, so one stopped feed cannot look green."""
    rows = ctx.kod.jsonl(p["ledger"])
    families = p["families"]
    sets = {}
    for row in rows:
        if (
            row.get("type") == "CATALYST_SET"
            and row.get("family") in families
            and not row.get("parent")
        ):
            sets.setdefault(row["set_id"], row)
    fire = {k: s for k, s in sets.items() if (s.get("coverage") or {}).get("class") == "FIRE"}
    scored = [
        r
        for r in latest_resolutions(rows).values()
        if r["set_id"] in fire
        and r.get("window") == p["window"]
        and r.get("status") == "RESOLVED"
        and r.get("coverage") == "FIRE"
        and (r.get("paired") or {}).get("diff") is not None
    ]
    last_batch, stalled = {}, []
    for family in families:
        batches = catalyst_batches(rows, family)
        last_batch[family] = newest(b["sealed_at"] for b in batches)
        if len(missed_batch_sessions(ctx, batches, "NYSE", "14:00")) >= p.get(
            "stall_after_missed", 2
        ):
            stalled.append(family)
    by_family = Counter(s["family"] for s in fire.values())
    notes = [
        "FIRE parents by family: " + ", ".join(f"{f} {by_family.get(f, 0)}" for f in families),
        "last batch by family: " + ", ".join(f"{f} {last_batch[f]}" for f in families),
    ]
    issue = None
    if stalled:
        notes.insert(
            0,
            "STALLED feeding famil(ies): "
            + ", ".join(f"{f} (last batch {last_batch[f]})" for f in stalled)
            + "; as_of is the newest pooled record, the other families are still feeding",
        )
        longest = min(stalled, key=lambda f: last_batch[f])
        if len(stalled) == 1:
            issue = stalled_feed_issue(ctx, {}, longest, last_batch[longest])
        else:
            issue = (
                f"{len(stalled)} filing feeds stopped; longest "
                f"{plural(days_since(last_batch[longest], ctx.now), 'day')}"
            )
    stamps = [
        r.get("sealed_at") or r.get("resolved_at")
        for r in rows
        if r.get("family") in families and r.get("type") in ("BATCH", "CATALYST_SET", "RESOLUTION")
    ]
    return reading(
        collected=len(fire),
        scored=len(scored),
        as_of=newest(stamps),
        state="STALLED" if stalled else None,
        issue=issue,
        collected_times=[s["sealed_at"] for s in fire.values()],
        scored_times=[r["resolved_at"] for r in scored],
        note=notes,
    )


def trend_core_days(ctx: Ctx, path: str):
    """TREND_CORE ledger -> ({signal_date: {symbol: first row}}, raw row count, hash-chain
    breaks)."""
    raw = ctx.kod.text(path)
    lines = [line for line in raw.split("\n") if line.strip()]
    previous, breaks, by_day = "0" * 64, 0, defaultdict(dict)
    for line in lines:
        row = json.loads(line)
        breaks += row.get("prev_sha256") != previous
        previous = hashlib.sha256(line.encode()).hexdigest()
        by_day[row["signal_date"]].setdefault(
            row["symbol"], row
        )  # dedup (symbol, signal_date), first wins
    return by_day, len(lines), breaks


def read_trend_core(ctx: Ctx, p: dict) -> dict:
    """TREND_CORE paper log. collected = signal days logged for every symbol (no MISSED row); scored
    = 0 until the pass-bar check after 90 consecutive logged days."""
    by_day, raw_rows, breaks = trend_core_days(ctx, p["ledger"])
    complete = {
        d: coins
        for d, coins in by_day.items()
        if all(coins.get(s, {}).get("action", "MISSED") != "MISSED" for s in p["symbols"])
    }
    missed = sorted(d for d, coins in by_day.items() if d not in complete)
    unique = sum(len(c) for c in by_day.values())
    notes = [
        f"{raw_rows} raw rows, {raw_rows - unique} duplicate(s) dropped on (symbol, signal_date); "
        f"hash-chain breaks {breaks}; MISSED days {', '.join(missed) if missed else 'none'}"
    ]
    logged = [
        max(c["logged_utc"] for c in coins.values() if "logged_utc" in c)
        for coins in complete.values()
    ]
    return reading(
        collected=len(complete), scored=0, as_of=newest(logged), collected_times=logged, note=notes
    )


# ================================================================================= readers: closed
def dig(obj, dotted: str):
    for key in dotted.split("."):
        obj = obj[key]
    return obj


def read_closed_record(ctx: Ctx, p: dict) -> dict:
    """A closed study: CLOSED only while its verdict record still exists and still says what the
    registry says (must_contain strings, optional JSON key == value checks). as_of = newest commit
    of those files. Optional "ref": read the record from that ref instead of the ledger ref (for a
    study whose record lives on a research branch)."""
    ref = p.get("ref")
    problems, paths = [], [p["record"]]
    text = ctx.kod.text(p["record"], ref)
    problems += [
        f"record no longer states {s!r}" for s in p.get("must_contain", []) if s not in text
    ]
    checks = p.get("json", [])
    for check in checks if isinstance(checks, list) else [checks]:
        if check["path"] not in paths:
            paths.append(check["path"])
        value = dig(ctx.kod.json(check["path"], ref), check["key"])
        if value != check["equals"]:
            problems.append(
                f"{check['path']} {check['key']}={value!r}, expected {check['equals']!r}"
            )
    if problems:
        raise ValueError("; ".join(problems))
    return reading(
        state="CLOSED",
        as_of=newest(ctx.kod.last_commit(x, ref) for x in paths),
        collected="registry",
        scored="registry",
    )


# ================================================================================= readers: server
def backups_ref(p: dict) -> str:
    return "origin/" + p["branch"]


def health_rows_over_history(ctx: Ctx, p: dict, summarize) -> list[dict]:
    """Walk a backup branch's commits; one row per distinct HEALTH heartbeat (code commits re-carry
    it)."""
    out, previous = [], None
    for sha, _ in ctx.backups.commits(backups_ref(p)):
        try:
            summary = summarize(ctx, p, sha)
        except (SourceMissing, KeyError, ValueError, TypeError):
            continue  # early commits predate HEALTH.json
        if summary["as_of"] == previous:
            continue
        previous = summary["as_of"]
        out.append(
            {
                "at": summary["as_of"],
                "study": p["study"],
                "status": summary["status"],
                "coverage": summary["coverage"],
                "captured": summary["captured"],
                "scored": summary["scored"],
                "commit": sha[:9],
            }
        )
    return out


def summarize_cohort(ctx: Ctx, p: dict, ref: str) -> dict:
    """main: 30-slot TIMING_CAPTURE cohort (HEALTH.json + COHORT-REPORT.json)."""
    health = ctx.backups.json("HEALTH.json", ref)
    try:
        report = ctx.backups.json("COHORT-REPORT.json", ref)
    except SourceMissing:
        report = {}
    as_of = parse_ts(health["as_of"])
    due = [s for s in health["slots"] if parse_ts(s["scheduled_at"]) <= as_of]
    issues = list(health.get("issues") or [])
    missed = list(report.get("noncaptured_terminal_slots", []))
    issues += [f"slot {s} not captured" for s in missed]
    if health.get("evidence_integrity_ok") is False:
        issues.append("evidence_integrity_ok false")
    status = (
        "CLOSED" if report.get("collection_closed") else ("RUNNING" if not issues else "STALLED")
    )
    captured = sum(1 for s in health["slots"] if s["status"] == "CAPTURED")
    return {
        "as_of": exact_iso(health["as_of"]),
        "status": status,
        "phase": report.get("outcome") or "UNKNOWN",
        "coverage": round(sum(s["status"] == "CAPTURED" for s in due) / len(due), 4)
        if due
        else None,
        "captured": captured,
        "planned": report.get("planned_slots", len(health["slots"])),
        "scored": report.get("terminal_slots"),
        "issues": issues,
        "missed": len(missed),
        "integrity_bad": health.get("evidence_integrity_ok") is False,
        "ends_at": norm_iso(report.get("last_scheduled_at")),
    }


def summarize_supplement(ctx: Ctx, p: dict, ref: str) -> dict:
    """supplement-30m-v1: only the SUPPLEMENT slots (ORIGINAL_REFERENCE rows mirror main)."""
    health = ctx.backups.json("HEALTH.json", ref)
    view = health["view"]
    as_of = parse_ts(view["as_of"])
    own = [s for s in view["slots"] if s["origin"] == "SUPPLEMENT"]
    due = [s for s in own if parse_ts(s["scheduled_at"]) <= as_of]
    bad = [s for s in due if s["status"] != "CAPTURED"]
    issues = list(health.get("issues") or []) + list(view.get("issues") or [])
    issues += [f"slot {s['slot']} {s['status']}" for s in bad]
    return {
        "as_of": exact_iso(health["as_of"]),
        "status": "RUNNING" if not issues else "STALLED",
        "phase": "COLLECTING",
        "coverage": round((len(due) - len(bad)) / len(due), 4) if due else None,
        "captured": sum(1 for s in own if s["status"] == "CAPTURED"),
        "planned": len(own),
        "scored": len(due),
        "issues": issues,
        "missed": len(bad),
        "ends_at": norm_iso(view.get("end_at")),
    }


def summarize_collector(ctx: Ctx, p: dict, ref: str) -> dict:
    """research-r2 / capacity-r2 HEALTH.json (minute-bar collector studies)."""
    health = ctx.backups.json("HEALTH.json", ref)
    collector = health.get("collector") or {}
    coverage = collector.get("coverage") or {}
    if health.get("phase") in ("HALTED", "PAUSED") or health.get("pause_latched"):
        status = "HALTED"
    else:
        status = {"OK": "RUNNING", "PRELIMINARY": "WAITING", "FAILED": "STALLED"}.get(
            health.get("status"), "UNKNOWN"
        )
    pooled = coverage.get("pooled_on_time_coverage")
    engine = health.get("research_engine") or {}
    events = engine.get("event_count")
    matured = None
    if p.get("scored_key"):
        scored = coverage.get(p["scored_key"])
    else:
        # scored = admitted events whose primary outcome (event + outcome_hours) has matured. HEALTH
        # carries no event times, so this is only known for certain while no event can be old
        # enough: every event is admitted at or after t0.
        hours = p.get("outcome_hours", 24)
        if events == 0:
            matured = 0
        elif events and engine.get("t0") and engine.get("as_of"):
            first_possible = parse_ts(engine["t0"]) + timedelta(hours=hours)
            if parse_ts(engine["as_of"]) < first_possible:
                matured = 0
        if matured is None and events:
            # Past the first possible maturity, count events from the engine's own OUTCOME records:
            # one per timing arm, so OUTCOME // arms-per-event. Later windows (72 h, 120 h) also
            # write OUTCOME records, so the count is only unambiguous while it cannot exceed one
            # primary outcome per arm per event; beyond that it stays unknown rather than guessed.
            counts = engine.get("ledger_counts") or {}
            outcomes, arms = counts.get("OUTCOME"), counts.get("ARM_DECISION")
            if outcomes is not None and arms and arms % events == 0:
                per_event = arms // events
                if outcomes <= arms and outcomes % per_event == 0:
                    matured = outcomes // per_event
        scored = matured
    return {
        "as_of": exact_iso(health.get("emitted_at") or collector.get("as_of")),
        "status": status,
        "phase": health.get("phase"),
        "coverage": round(pooled, 4) if pooled is not None else None,
        "captured": coverage.get("on_time_closed_total"),
        "planned": coverage.get(p.get("planned_key", "full_capture_expected_closed_total")),
        "scored": scored,
        "events": events,
        "issues": list(health.get("issues") or []),
        "ends_at": norm_iso(health.get("end_at")),
        "raw": health,
    }


SERVER_SUMMARIES = {
    "cohort": summarize_cohort,
    "supplement": summarize_supplement,
    "collector": summarize_collector,
}


def server_issue(status: str, summary: dict) -> str | None:
    """Plain `issue` for a server study that is HALTED, STALLED or UNKNOWN (else None)."""
    if status == "HALTED":
        paused = summary.get("phase") == "PAUSED" or "COLLECTOR_PAUSED" in summary["issues"]
        return "Server data collector is paused" if paused else "Server data collector has stopped"
    if status == "STALLED":
        if summary.get("missed"):
            return f"{plural(summary['missed'], 'scheduled capture')} missed"
        if summary.get("integrity_bad"):
            return "Saved server data failed its integrity check"
        return "Server reported a problem"
    if status == "UNKNOWN":
        return "Server status could not be read"
    return None


def r2_capacity_closure(ctx: Ctx, p: dict) -> dict | None:
    """The capacity-trial closure record carried inside the research-r2 HEALTH.json."""
    health = ctx.backups.json("HEALTH.json", "origin/" + p["closure_branch"])
    records = (health.get("predecessor_capacity") or {}).get("receipt_hashes_and_records") or {}
    closure = (records.get("CAPACITY_CLOSURE.json") or {}).get("record")
    ack = (records.get("PREDECESSOR_BACKUP_ACK.json") or {}).get("record") or {}
    if not closure:
        return None
    return {
        "closed_at": norm_iso(closure.get("capacity_closed_at")),
        "acceptance": closure.get("capacity_acceptance"),
        "status": (health.get("predecessor_capacity") or {}).get("status"),
        "ack_branch": ack.get("branch"),
        "ack_commit": ack.get("commit"),
    }


def read_server_study(ctx: Ctx, p: dict) -> dict:
    """A server study on a backup branch. Returns the experiment counts, one server.json row and its
    heartbeat history. A closed study needs its closure verified (record or registry `expect`)."""
    summarize = SERVER_SUMMARIES[p["kind"]]
    now_summary = summarize(ctx, p, backups_ref(p))
    history = health_rows_over_history(ctx, p, summarize)
    issues, status, notes, events = list(now_summary["issues"]), now_summary["status"], [], []
    if (
        p.get("coverage_bar") is not None
        and now_summary["coverage"] is not None
        and now_summary["coverage"] < p["coverage_bar"]
    ):
        issues.append(
            f"on-time coverage {now_summary['coverage']} below the protocol bar {p['coverage_bar']}"
        )
        notes.append(issues[-1])
    if p.get("coverage_reported") and now_summary["coverage"] is not None:
        text = f"on-time coverage {now_summary['coverage']} so far ({p['coverage_reported']})"
        issues.append(text)
        notes.append(text)
    if now_summary.get("events") is not None and not p.get("scored_key"):
        raw_engine = (now_summary.get("raw") or {}).get("research_engine") or {}
        hours = p.get("outcome_hours", 24)
        t0 = raw_engine.get("t0")
        earliest = iso(parse_ts(t0) + timedelta(hours=hours)) if t0 else "?"
        matured = now_summary["scored"]
        notes.append(
            f"{now_summary['events']} market event(s) admitted; "
            + (
                f"{matured} with a matured {hours} h primary outcome"
                if matured is not None
                else f"matured {hours} h outcomes not countable from HEALTH.json (no event times)"
            )
            + f"; the first outcome can mature at {earliest} at the earliest"
        )
    if p.get("closed_by") == "r2_closure":
        closure = r2_capacity_closure(ctx, p)
        head = ctx.backups.head(backups_ref(p))
        if not closure or closure["ack_branch"] != p["branch"] or closure["ack_commit"] != head:
            raise ValueError("closure record does not name this branch head")
        status, now_summary["ends_at"] = "CLOSED", closure["closed_at"]
        now_summary["phase"] = closure["status"]
        issues.append(f"closed {closure['closed_at']}: {closure['acceptance']}")
        events.append(
            event(
                closure["closed_at"],
                "decision",
                f"{p['study']} closed early, not passed",
                f"capacity_acceptance: {closure['acceptance']}",
                f"BACKUPS:{p['closure_branch']}:HEALTH.json#predecessor_capacity",
            )
        )
    elif p.get("closed_by") == "registry":
        raw = now_summary.get("raw") or {}
        for key, expected in p.get("expect", {}).items():
            if raw.get(key) != expected:
                raise ValueError(
                    f"HEALTH.json {key}={raw.get(key)!r}, registry expects {expected!r}"
                )
        status = "CLOSED"
    events += server_transition_events(p, history)
    server = {
        "study": p["study"],
        "name": p["name"],
        "status": status,
        "phase": now_summary["phase"],
        "coverage": now_summary["coverage"],
        "captured": now_summary["captured"],
        "planned": now_summary["planned"],
        "issues": "; ".join(issues),
        "as_of": now_summary["as_of"],
        "stale_after_hours": p.get("stale_after_hours"),
        "ends_at": now_summary["ends_at"],
        "source": f"BACKUPS:{p['branch']}:HEALTH.json",
    }
    by_day = {}
    for row in history:
        by_day[wib_day(row["at"])] = row
    return reading(
        collected=now_summary["captured"],
        scored=now_summary["scored"],
        as_of=now_summary["as_of"],
        state=status,
        issue=server_issue(status, now_summary),
        server=server,
        server_history=history,
        note=notes,
        events=events,
        history_rows=[(d, r["captured"], r["scored"]) for d, r in sorted(by_day.items())],
    )


def server_transition_events(p: dict, history: list[dict]) -> list[dict]:
    """Status changes along a branch's heartbeats: going bad is an incident, coming back a
    milestone."""
    out, previous, before = [], None, None
    for row in history:
        bad = row["status"] in ("HALTED", "STALLED", "UNKNOWN")
        if previous is not None and row["status"] != previous:
            title = f"{p['name']}: {previous} -> {row['status']} (seen at backup)"
            detail = (
                f"First seen in the backup at {row['at']}; the previous backup at {before['at']} "
                f"still read {previous}, so the change happened between the two (the time shown is "
                f"the backup, not the change). Coverage {row['coverage']}, captured "
                f"{row['captured']}"
                + (
                    " (unchanged since the previous backup)"
                    if row["captured"] == before["captured"]
                    else ""
                )
                + "."
            )
            out.append(
                event(
                    row["at"],
                    "incident" if bad else "milestone",
                    title,
                    detail,
                    f"BACKUPS:{p['branch']}@{row['commit']}:HEALTH.json",
                )
            )
        elif previous is None and bad:
            out.append(
                event(
                    row["at"],
                    "incident",
                    f"{p['name']}: {row['status']} at its first backup",
                    f"coverage {row['coverage']}",
                    f"BACKUPS:{p['branch']}@{row['commit']}:HEALTH.json",
                )
            )
        previous, before = row["status"], row
    return out


READERS = {
    "llm_arm": read_llm_arm,
    "spec_register": read_spec_register,
    "learner_v22": read_learner_v22,
    "learner_v24": read_learner_v24,
    "call_cert_report": read_call_cert_report,
    "paper_book": read_paper_book,
    "paper_account": read_paper_account,
    "crypto_account": read_crypto_account,
    "premove_shadow": read_premove_shadow,
    "catalyst": read_catalyst,
    "catalyst_pooled": read_catalyst_pooled,
    "trend_core": read_trend_core,
    "closed_record": read_closed_record,
    "server_study": read_server_study,
}


# ========================================================================== jobs (runs / run_days)
def judge_day(first: datetime | None, due: datetime, deadline: datetime, now: datetime) -> str:
    """ok if the record came by `due`; partial if late but before the decision's own deadline;
    missed after that; pending while the deadline has not passed (pending rows are not written)."""
    if first is not None and first <= due:
        return "ok"
    if first is not None and first <= deadline:
        return "partial"
    if first is not None or now > deadline:
        return "missed"
    return "pending"


def job_scan(ctx: Ctx, p: dict):
    """Nightly paper scan for one market: SCAN rows of ledger.jsonl keyed by session."""
    first, last, label = {}, None, None
    for row in ctx.kod.jsonl(p["ledger"]):
        if row.get("type") != "SCAN" or scan_market(row) != p["market"]:
            continue
        stamp = parse_ts(row["discovered_at"])
        day = date.fromisoformat(row["session"])
        first[day] = min(first.get(day, stamp), stamp)
        if last is None or stamp > last:
            last, label = stamp, f"{row['scan_id']}: {row.get('result', '')}"

    def status(day: date) -> str:
        due = at_utc(day, p["scheduled_utc"], p.get("run_day_offset", 0)) + timedelta(
            hours=p["ok_within_hours"]
        )
        deadline = at_utc(ctx.next_trading_day(p["calendar"], day), p["deadline_utc"])
        value = judge_day(first.get(day), due, deadline, ctx.now)
        if value == "partial":
            status.details[day.isoformat()] = (
                f"late, not incomplete: session {day} scan written {iso(first[day])}, "
                f"due by {iso(due)}"
            )
        return value

    status.details = {}
    status.partial_means = "late"
    return last, label, status


def scan_market(row: dict) -> str:
    """The first IDX scan predates the market field; classify by scan_id prefix."""
    if row.get("market"):
        return row["market"]
    scan_id = row.get("scan_id", "")
    return (
        "US"
        if scan_id.startswith("SCAN-US-")
        else "CRYPTO"
        if scan_id.startswith("SCAN-CRYPTO-")
        else "IDX"
    )


def job_llm_calls(ctx: Ctx, p: dict):
    """LLM calls for one market: every sealed set of a session needs a call before its entry
    cutoff."""
    roster = defaultdict(dict)
    for row in ctx.kod.jsonl(p["register"]):
        if row.get("type") == "SPECULATION_SET" and row.get("market") == p["market"]:
            roster[date.fromisoformat(row["signal_session"])][row["set_id"]] = parse_ts(
                row["entry_cutoff"]
            )
    calls, seen = {}, set()
    for path in sorted(
        f for f in ctx.kod.ls(p["calls_dir"]) if re.search(r"/calls[^/]*\.jsonl$", f)
    ):
        for row in ctx.kod.jsonl(path):
            if row.get("market") == p["market"] and row["call_id"] not in seen:
                seen.add(row["call_id"])
                calls[row["set"]] = (parse_ts(row["called_at"]), row["signal_session"])
    last = max((c for c in calls.values()), default=(None, None))
    label = f"call on a {last[1]} {p['market']} spike" if last[0] else None
    start = date.fromisoformat(p["start"])
    elsewhere = {}
    for row in unmerged_calls(ctx, p["calls_dir"]):
        if row.get("market") == p["market"] and row.get("set") not in calls:
            elsewhere[row["set"]] = row

    def status(day: date) -> str:
        sets = roster.get(day, {})
        if day < start or not sets:
            return "not_expected" if day < start or day < ctx.now.date() else "pending"
        on_time = sum(1 for s, cutoff in sets.items() if s in calls and calls[s][0] <= cutoff)
        if on_time == len(sets):
            return "ok"
        if ctx.now <= min(sets.values()):
            return "pending"
        found = [
            elsewhere[s]
            for s, cutoff in sets.items()
            if s in elsewhere and parse_ts(norm_minute(elsewhere[s]["called_at"])) <= cutoff
        ]
        if found:
            where = sorted({f"{r['_branch']} (commit {r['_commit']})" for r in found})
            status.details[day.isoformat()] = (
                f"judged from the data branch: {len(found)} in-time call(s) for this session "
                f"exist only on unmerged branch {', '.join(where)}"
            )
        return "partial" if on_time else "missed"

    status.details = {}
    return last[0], label, status


def job_trend_core(ctx: Ctx, p: dict):
    """TREND_CORE daily log: signal day D is ok if logged by (D+1) cron + ok_within_hours."""
    by_day, _, _ = trend_core_days(ctx, p["ledger"])
    logged = {}
    for d, coins in by_day.items():
        stamps = [
            parse_ts(c["logged_utc"])
            for c in coins.values()
            if c.get("action") != "MISSED" and "logged_utc" in c
        ]
        if len(stamps) == len(p["symbols"]):
            logged[date.fromisoformat(d)] = max(stamps)
    last_day = max(logged, default=None)

    start = date.fromisoformat(p["start"])

    def status(day: date) -> str:
        if day < start:
            return "not_expected"
        due = at_utc(day, p["scheduled_utc"], 1) + timedelta(hours=p["ok_within_hours"])
        return judge_day(logged.get(day), due, at_utc(day, p["scheduled_utc"], 2), ctx.now)

    return (
        (logged[last_day] if last_day else None),
        (f"signal day {last_day} logged" if last_day else None),
        status,
    )


def job_ledger_by_session(ctx: Ctx, p: dict):
    """Generic: rows of `type` in `ledger`, keyed by `session_field`, stamped by `time_field`. A
    session's record is due by (next trading day) `deadline_utc`; ok if it exists then, else
    missed. `only_if_type`: a session is expected only when the ledger holds a row of that type
    for it (a resolution is owed only for a day that was sealed)."""
    stamps = defaultdict(list)
    owed = {
        row[p["session_field"]][:10]
        for row in ctx.kod.jsonl(p["ledger"])
        if row.get("type") == p.get("only_if_type")
    }
    for row in ctx.kod.jsonl(p["ledger"]):
        if row.get("type") != p["type"] or any(
            row.get(k) != v for k, v in p.get("where", {}).items()
        ):
            continue
        stamps[date.fromisoformat(row[p["session_field"]][:10])].append(
            parse_ts(row[p["time_field"]])
        )
    last_day = max(stamps, default=None)
    start = date.fromisoformat(p["start"])
    offset = p.get("session_offset_days", 0)

    def status(day: date) -> str:
        key = day - timedelta(days=offset)
        if key < start or (p.get("only_if_type") and key.isoformat() not in owed):
            return "not_expected"
        deadline = at_utc(ctx.next_trading_day(p["calendar"], day), p["deadline_utc"])
        return judge_day(min(stamps[key]) if stamps.get(key) else None, deadline, deadline, ctx.now)

    last = max(stamps[last_day]) if last_day else None
    return last, (f"{p['type']} for {p['session_field']} {last_day}" if last_day else None), status


def job_catalyst_batch(ctx: Ctx, p: dict):
    """Catalyst batch for one family per US session; a batch with a feed coverage gap is partial."""
    rows = ctx.kod.jsonl(p["ledger"])
    batches = defaultdict(list)
    for b in catalyst_batches(rows, p["family"]):
        batches[date.fromisoformat(b["signal_session"])].append(b)
    parent = defaultdict(list)
    if p.get("gap_from"):
        for b in catalyst_batches(rows, p["gap_from"]):
            parent[date.fromisoformat(b["signal_session"])].append(b)
    last = max((parse_ts(b["sealed_at"]) for bs in batches.values() for b in bs), default=None)
    last_day = max(batches, default=None)
    start = date.fromisoformat(p["start"])

    def status(day: date) -> str:
        if day < start:
            return "not_expected"
        deadline = at_utc(day, p["deadline_utc"], 1)
        found = batches.get(day, [])
        state = judge_day(
            min(parse_ts(b["sealed_at"]) for b in found) if found else None,
            deadline,
            deadline,
            ctx.now,
        )
        if state == "ok" and any(coverage_gap(b) for b in found + parent.get(day, [])):
            return "partial"
        return state

    return last, (f"{p['family']} batch for signal {last_day}" if last_day else None), status


def job_crypto_account(ctx: Ctx, p: dict):
    """Crypto account sync: every crypto policy DECISION of a day must be recorded (none due =
    not_expected)."""
    recorded = {
        r["decision_id"]: parse_ts(r["made_at"])
        for r in ctx.kod.jsonl(p["ledger"])
        if r["type"] in ("ACCT_ORDER", "ACCT_DECLINE")
    }
    decisions = defaultdict(list)
    for row in ctx.kod.jsonl(p["policy_ledger"]):
        if row.get("market") == "CRYPTO" and row.get("type") == "DECISION":
            decisions[date.fromisoformat(row["signal_session"])].append(row["decision_id"])
    start = date.fromisoformat(p["start"])

    def status(day: date) -> str:
        ids = decisions.get(day, [])
        if day < start or not ids:
            return "not_expected" if day < ctx.now.date() else "pending"
        done = sum(1 for i in ids if i in recorded)
        if done == len(ids):
            return "ok"
        if ctx.now <= at_utc(day, p["deadline_utc"], 1):
            return "pending"
        return "partial" if done else "missed"

    last = max(recorded.values(), default=None)
    return last, (f"{len(recorded)} decision(s) recorded" if last else None), status


JOB_READERS = {
    "scan": job_scan,
    "llm_calls": job_llm_calls,
    "trend_core": job_trend_core,
    "ledger_by_session": job_ledger_by_session,
    "catalyst_batch": job_catalyst_batch,
    "crypto_account_sync": job_crypto_account,
}


def build_jobs(ctx: Ctx, gaps: list) -> tuple[list, list, list]:
    runs, days, events = [], [], []
    for job in ctx.registry.get("jobs", []):
        p = job["params"]
        try:
            last, label, status = JOB_READERS[job["reader"]](ctx, p)
        except Exception as exc:  # one broken job must not stop the build
            gaps.append(gap_for(exc, job["source"].split(" ")[0], f"job {job['job']}"))
            runs.append(run_row(job, None, f"READ_ERROR: {type(exc).__name__}"))
            continue
        runs.append(run_row(job, iso(last), label))
        calendar = p.get("calendar", "DAILY")
        job_days = []
        for back in range(RUN_DAYS - 1, -1, -1):
            day = ctx.now.date() - timedelta(days=back)
            value = status(day) if ctx.trading_day(calendar, day) else "not_expected"
            if value == "pending":
                continue  # the deadline has not passed yet; not written (schema has 4 statuses)
            job_days.append({"date": day.isoformat(), "job": job["job"], "status": value})
        days += job_days
        events += run_day_incidents(
            job,
            job_days,
            getattr(status, "details", {}),
            getattr(status, "partial_means", None),
        )
    return runs, days, events


def run_day_incidents(
    job: dict, job_days: list[dict], details: dict | None = None, partial_means: str | None = None
) -> list[dict]:
    """One incident per run of consecutive bad expected days (missed/partial), not one per day.
    `details` (date -> text) adds what the record shows for a day; `partial_means` names what
    'partial' means for this job (e.g. 'late' for a scan) so the title does not say 'partial'."""
    details = details or {}
    out, streak = [], []
    expected = [d for d in job_days if d["status"] != "not_expected"] + [{"status": "ok"}]
    for row in expected:
        if row["status"] in ("missed", "partial"):
            streak.append(row)
            continue
        if streak:
            first, last = streak[0]["date"], streak[-1]["date"]
            span = first if first == last else f"{first} to {last}"
            kinds = sorted({d["status"] for d in streak})
            if partial_means:
                kinds = [
                    f"{partial_means} (run_days status 'partial')" if k == "partial" else k
                    for k in kinds
                ]
            extra = "; ".join(details[d["date"]] for d in streak if d["date"] in details)
            out.append(
                event(
                    f"{last}T23:59:59Z",
                    "incident",
                    f"{job['name']}: {'/'.join(kinds)} for {span} ({len(streak)} expected day(s))",
                    "Judged from the records the job writes (no run log exists); dates are session "
                    "dates and the time is the end of the last one."
                    + (f" {extra}." if extra else ""),
                    job["source"],
                )
            )
            streak = []
    return out


def run_row(job: dict, last: str | None, label: str | None) -> dict:
    return {
        "job": job["job"],
        "market": job["market"],
        "last_success_at": last,
        "last_record": label,
        "expected_every_hours": job["expected_every_hours"],
        "grace_hours": job["grace_hours"],
        "source": job["source"],
    }


# ===================================================================================== experiments
def gap_for(exc: Exception, path: str, who: str) -> dict:
    if isinstance(exc, SourceMissing):
        return {
            "kind": "SOURCE_MISSING",
            "path": str(exc),
            "detail": f"{who}: source not found at the ref",
        }
    return {
        "kind": "READ_ERROR",
        "path": path,
        "detail": f"{who}: {type(exc).__name__}: {str(exc)[:240]}",
    }


def history_rows(entry: dict, result: dict, today: str) -> list[dict]:
    """Cumulative collected/scored per WIB day from the first record (or the registry `start`) to
    today."""
    if entry["group"] == "closed":
        if result.get("collected") is None and result.get("scored") is None:
            return []
        return [
            {
                "date": entry["closed_on"],
                "experiment": entry["id"],
                "collected": result.get("collected"),
                "scored": result.get("scored"),
            }
        ]
    if result.get("history_rows"):
        return [
            {"date": d, "experiment": entry["id"], "collected": c, "scored": s}
            for d, c, s in result["history_rows"]
        ]
    collected = Counter(wib_day(t) for t in result["collected_times"] if t)
    scored = Counter(wib_day(t) for t in result["scored_times"] if t)
    starts = list(collected) + list(scored) + ([entry["start"]] if entry.get("start") else [])
    if not starts:
        return []
    first = max(
        min(starts), (date.fromisoformat(today) - timedelta(days=HISTORY_DAYS - 1)).isoformat()
    )
    run_c = sum(n for d, n in collected.items() if d < first)
    run_s = sum(n for d, n in scored.items() if d < first)
    out = []
    for day in day_range(first, today):
        run_c += collected.get(day, 0)
        run_s += scored.get(day, 0)
        out.append({"date": day, "experiment": entry["id"], "collected": run_c, "scored": run_s})
    return out


def projection(
    history: list[dict],
    scored: int | None,
    needed: int | None,
    today: str,
    opts: dict | None = None,
):
    """(projected_date, note). The pace is the gain of the basis count (registry
    `projection.basis`: "scored", the default, or "collected" plus `lag_days` from a sealed
    record to its scored outcome) over the last PROJECTION_WINDOW days, or over the days since
    the first record when that is shorter (at least PROJECTION_MIN_DAYS), so a window that starts
    before anything was scored does not dilute the rate. A registry `projection.earliest_look` (a
    protocol floor such as a minimum number of sessions) is used when it is later than the pace,
    and the note says which one set the date. (None, why) without an estimate."""
    opts = opts or {}
    if scored is None or not needed:
        return None, None
    if scored >= needed:
        return today, "needed count reached"
    basis = opts.get("basis", "scored")
    lag = int(opts.get("lag_days", 0))
    by_day = {h["date"]: h[basis] for h in history if h.get(basis) is not None}
    if not by_day:
        return None, f"no estimate: no {basis} history"
    current = by_day[max(by_day)]
    started = [d for d, v in by_day.items() if v]
    if not started:
        return None, f"no estimate: nothing {basis} yet"
    since_first = (date.fromisoformat(today) - date.fromisoformat(min(started))).days + 1
    window = max(PROJECTION_MIN_DAYS, min(PROJECTION_WINDOW, since_first))
    back = (date.fromisoformat(today) - timedelta(days=window)).isoformat()
    base = by_day.get(back, 0 if back < min(by_day) else None)
    if base is None:
        return None, "no estimate: history incomplete"
    recent = current - base
    if recent <= 0:
        return None, f"no estimate: nothing {basis} in the last {window} days"
    day0 = date.fromisoformat(today)
    if basis == "collected" and current >= needed:
        reached = min(d for d, v in by_day.items() if v >= needed)
        pace = max(day0, date.fromisoformat(reached) + timedelta(days=lag))
        pace_note = (
            f"the {needed}th record was collected {reached}; plus the {lag}-day lag to its "
            f"outcome: about {pace}"
        )
    else:
        left = needed - current
        rate = recent / window
        pace = day0 + timedelta(days=math.ceil(left / rate) + lag)
        low = recent - 1.28 * math.sqrt(recent)
        high = recent + 1.28 * math.sqrt(recent)
        early = day0 + timedelta(days=math.ceil(left / (high / window)) + lag)
        late = day0 + timedelta(days=math.ceil(left / (low / window)) + lag) if low > 0 else None
        band = (
            f"likely {early} to {late}"
            if late
            else f"no earlier than about {early}; upper end open"
        )
        what = "scored" if basis == "scored" else f"{basis}, plus {lag} days to the outcome"
        pace_note = f"at the last {window} days' pace ({recent} {what}): about {pace}, {band}"
    floor = opts.get("earliest_look")
    reason = opts.get("earliest_look_reason", "the protocol's earliest look")
    if floor and floor > pace.isoformat():
        return floor, (
            f"projected_date {floor} is set by {reason} (the same date as next_milestone); "
            f"the pace alone would give: {pace_note}"
        )
    note = f"projected_date from pace: {pace_note}"
    if floor:
        note += f"; {reason} ({floor}) does not bind"
    return pace.isoformat(), note


def freshness(state: str, as_of: str | None, stale_hours, now: datetime) -> tuple[str, str | None]:
    """A live row older than its limit reads UNKNOWN (STALLED/HALTED/CLOSED are kept)."""
    if state not in LIVE_STATES:
        return state, None
    if as_of is None:
        return "UNKNOWN", "no as-of time"
    age = (now - parse_ts(as_of)).total_seconds() / 3600
    if stale_hours is not None and age > stale_hours:
        return "UNKNOWN", f"newest record is {age:.0f} h old, over the {stale_hours} h limit"
    return state, None


def check_sources(ctx: Ctx, entry: dict, gaps: list) -> None:
    """Every registry source must still exist (globs: at least one match). Optional ones may be
    absent. "KOD@<branch>:path" checks the file on origin/<branch> instead of the ledger ref."""
    for source in entry.get("sources", []):
        repo_name, _, rest = source.partition(":")
        rest = rest.split(" ")[0].split("#")[0]
        if repo_name.startswith("KOD@"):
            found = ctx.kod.exists(rest.rstrip("/"), "origin/" + repo_name[4:])
        elif repo_name == "KOD":
            if "*" in rest:
                folder, pattern = rest.rsplit("/", 1)
                regex = re.compile(re.escape(pattern).replace(r"\*", ".*") + "$")
                found = any(regex.match(f.rsplit("/", 1)[-1]) for f in ctx.kod.ls(folder))
            else:
                found = ctx.kod.exists(rest.rstrip("/"))
        elif repo_name == "BACKUPS":
            branch, _, path = rest.partition(":")
            found = ctx.backups.exists(path or "HEALTH.json", "origin/" + branch)
        else:
            found = True
        if not found:
            gaps.append(
                {
                    "kind": "SOURCE_MISSING",
                    "path": source,
                    "detail": f"{entry['id']}: listed source is not at the ref",
                }
            )


def check_protocol(ctx: Ctx, entry: dict) -> tuple[bool, str | None]:
    """The frozen protocol file must still hash to the registry's sha256."""
    lock = entry.get("protocol")
    if not lock:
        return True, None
    digest = hashlib.sha256(ctx.kod.text(lock["path"]).encode()).hexdigest()
    if digest != lock["sha256"]:
        return (
            False,
            f"PROTOCOL CHANGED: {lock['path']} sha256 {digest[:12]}, registry "
            f"{lock['sha256'][:12]}",
        )
    return True, f"protocol {lock['path']} unchanged (sha256 {digest[:12]})"


def build_experiment(ctx: Ctx, entry: dict, gaps: list) -> dict:
    """Run one registry entry's reader and assemble its experiments.json row (never raises)."""
    check_sources(ctx, entry, gaps)
    try:
        result = READERS[entry["reader"]](ctx, entry.get("params", {}))
        error = None
    except Exception as exc:  # one broken reader must not stop the build
        error = exc
        result = reading(state="UNKNOWN")
        first_source = (entry.get("sources") or [entry["id"]])[0]
        gaps.append(gap_for(exc, first_source, f"{entry['id']} reader {entry['reader']}"))
    gaps += result.get("gaps") or []
    for key in ("collected", "scored"):
        if result[key] == "registry":
            result[key] = entry.get(key)
    notes = list(result["note"])
    events = list(result["events"])
    state = result["state"] or "RUNNING"
    closed = entry["group"] == "closed"
    issue = result.get("issue")
    if error is not None:
        notes.insert(0, f"reader failed: {type(error).__name__}")
        if isinstance(error, SourceMissing):
            issue = (
                "Its written result is missing" if closed else "A record file it needs is missing"
            )
        else:
            issue = (
                "Its written result no longer matches"
                if closed
                else "Its records could not be read"
            )
    if error is None:
        try:
            unchanged, protocol_note = check_protocol(ctx, entry)
        except SourceMissing as exc:
            unchanged, protocol_note = False, f"protocol file missing: {exc}"
        if protocol_note:
            notes.append(protocol_note)
        if not unchanged:
            state = "UNKNOWN"
            issue = (
                "Its locked test rules file is missing"
                if protocol_note.startswith("protocol file missing")
                else "Its locked test rules were edited"
            )
            gaps.append(
                {
                    "kind": "READ_ERROR",
                    "path": "KOD:" + entry["protocol"]["path"],
                    "detail": f"{entry['id']}: {protocol_note}",
                }
            )
            events.append(
                event(
                    ctx.now_iso,
                    "incident",
                    f"{entry['name']}: frozen protocol changed",
                    protocol_note,
                    "KOD:" + entry["protocol"]["path"],
                )
            )
    state, stale_note = freshness(state, result["as_of"], entry.get("stale_after_hours"), ctx.now)
    if stale_note:
        notes.insert(0, "UNKNOWN: " + stale_note)
        issue = (
            f"No update since {plain_day(wib_day(result['as_of']), ctx.today_wib)}"
            if result["as_of"]
            else "No records yet"
        )
    if state not in BAD_STATES:
        issue = None
    elif not issue:
        issue = {
            "HALTED": "Paused",
            "STALLED": "Stopped making new records",
            "UNKNOWN": "Status could not be confirmed",
        }[state]
    needed = entry.get("needed") if result["needed"] == "registry" else result["needed"]
    history = history_rows(entry, result, ctx.today_wib) if error is None else []
    projected, projection_note = (None, None)
    verdict_date, verdict_basis = None, None
    if not closed and error is None:
        projected, projection_note = projection(
            history, result["scored"], needed, ctx.today_wib, entry.get("projection")
        )
        if projected:
            verdict_date, verdict_basis = projected, "estimate"
        server_end = (result["server"] or {}).get("ends_at")
        if entry["group"] == "server" and server_end:
            verdict_date, verdict_basis = wib_day(server_end), "scheduled"
        fixed_end = result["projected_fixed"] or entry.get("fixed_end")
        if fixed_end:
            projection_note = (
                f"fixed-calendar study: ends {fixed_end} by schedule (used as projected_date); "
                f"the pace-based estimate would be {projected or 'none'}"
            )
            projected = fixed_end
            verdict_date, verdict_basis = fixed_end, "scheduled"
    if state == "CLOSED" or entry.get("plumbing"):
        # a plumbing check (data collection that answers no question) has an end, not a verdict
        verdict_date, verdict_basis = None, None
    if projection_note:
        notes.append(projection_note)
    if entry.get("next_date") and entry["next_date"] < ctx.today_wib and entry["group"] != "closed":
        notes.append(
            f"registry next_date {entry['next_date']} has passed; next_milestone text needs "
            "a refresh"
        )
    if entry.get("note"):
        notes.append(entry["note"])
    if entry["group"] == "closed":
        notes.insert(0, f"closed {entry.get('closed_on')}; record {entry.get('record')}")
    scored = result["scored"]
    row = {
        "id": entry["id"],
        "name": entry["name"],
        "plain": entry["plain"],
        "group": entry["group"],
        "state": state,
        "collected": result["collected"],
        "collected_label": entry.get("collected_label", ""),
        "scored": scored,
        "scored_label": entry.get("scored_label", ""),
        "needed": needed,
        "needed_label": entry.get("needed_label", ""),
        "fraction": round(min(scored / needed, 1.0), 4) if scored is not None and needed else None,
        "as_of": result["as_of"],
        "stale_after_hours": entry.get("stale_after_hours"),
        "next_milestone": entry.get("next_milestone", ""),
        "next_date": entry.get("next_date"),
        "projected_date": projected,
        "verdict": entry.get("verdict") if state == "CLOSED" else None,
        "source": "; ".join(entry.get("sources", [])),
        "note": "; ".join(notes),
        # owner-facing view (registry text; null until the registry carries it)
        "program": entry.get("program"),
        "short": entry.get("short"),
        "ceo_line": entry.get("ceo_line"),
        "unit": entry.get("unit"),
        "outcome": entry.get("outcome"),
        "lesson": entry.get("lesson"),
        "issue": issue,
        "verdict_date": verdict_date,
        "verdict_basis": verdict_basis,
        "plumbing": bool(entry.get("plumbing")),
    }
    return {
        "row": row,
        "history": history,
        "events": events,
        "server": result["server"],
        "server_history": result["server_history"],
    }


# ================================================================================= events and gaps
def decision_events(ctx: Ctx) -> list[dict]:
    """Every handoff/decisions/*.md: at = the commit that added it; title = its first heading."""
    out = []
    for path in ctx.kod.ls("handoff/decisions"):
        if not path.endswith(".md"):
            continue
        text = ctx.kod.text(path)
        title = next(
            (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")),
            path.rsplit("/", 1)[-1],
        )
        kind = "incident" if re.match(r"(Incident|Disclosure)\b", title) else "decision"
        out.append(
            event(
                ctx.kod.first_commit(path),
                kind,
                title[:160],
                path.rsplit("/", 1)[-1],
                f"KOD:{path}",
            )
        )
    return out


def closed_verdict_events(ctx: Ctx, registry: list[dict], rows: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in rows}
    out = []
    for entry in registry:
        row = by_id.get(entry["id"])
        if entry["group"] == "closed" and row and row["state"] == "CLOSED" and row["as_of"]:
            source = (
                f"KOD:{entry['record']}" if entry["reader"] == "closed_record" else row["source"]
            )
            out.append(
                event(
                    row["as_of"],
                    "milestone",
                    f"{entry['name']}: verdict",
                    row["verdict"] or "",
                    source,
                )
            )
    return out


PROTOCOL_FILE = re.compile(
    r"(^|/)(PROTOCOL\.md|PROTOCOL_DRAFT\.md|protocol[^/]*\.json|prereg[^/]*\.json)$"
)
VERDICT_FILE = re.compile(r"(^|/)(REPORT|RESULT|RESULTS|OUTCOME)\.(md|json)$")


def covered(registry: dict) -> tuple[set, set]:
    """Ids and source paths the registry already shows (sources, `covers` aliases,
    reference_only)."""
    ids, paths = set(registry.get("reference_only", {})), set(registry.get("reference_only", {}))
    for entry in registry["experiments"]:
        ids.add(entry["id"])
        ids.update(entry.get("covers", []))
        for source in entry.get("sources", []) + entry.get("optional_sources", []):
            paths.add(source.split(" ")[0].split("#")[0])
        if entry.get("record"):
            paths.add("KOD:" + entry["record"])
    for job in registry.get("jobs", []):
        paths.add(job["source"].split(" ")[0])
    return ids, paths


def research_dirs_with_evidence(ctx: Ctx) -> dict:
    """research/<D>/ folders holding a protocol, a verdict record or a live .jsonl."""
    files = defaultdict(list)
    for path in ctx.kod.ls_recursive("idx-signals/research/"):
        parts = path.split("/")
        if len(parts) >= 4:
            files[parts[2]].append("/".join(parts[3:]))
    out = {}
    for folder, names in sorted(files.items()):
        marks = [
            label
            for label, hit in (
                ("protocol", any(PROTOCOL_FILE.search(n) for n in names)),
                ("verdict record", any(VERDICT_FILE.search(n) for n in names)),
                ("live .jsonl", any(n.endswith(".jsonl") for n in names)),
            )
            if hit
        ]
        if marks:
            out[folder] = marks
    return out


def gap_detector(ctx: Ctx) -> list[dict]:
    """Things that exist but are not on the dashboard: research folders, ledgers, server branches,
    catalog ids and closing decisions. Explicit exclusions live in the registry's reference_only
    map."""
    ids, paths = covered(ctx.registry)
    path_text = " ".join(paths)
    gaps = []
    for folder, marks in research_dirs_with_evidence(ctx).items():
        if folder in ids or f"idx-signals/research/{folder}/" in path_text:
            continue
        gaps.append(
            {
                "kind": "NOT_ON_DASHBOARD",
                "path": f"KOD:idx-signals/research/{folder}/",
                "detail": f"has {', '.join(marks)}; last commit "
                f"{ctx.kod.last_commit('idx-signals/research/' + folder)}",
            }
        )
    skip = tuple(ctx.registry.get("ledger_scan_skip", []))
    for path in ctx.kod.ls_recursive():
        if not path.endswith(".jsonl") or path.startswith(skip) or "/manifests/" in path:
            continue
        if (
            f"KOD:{path}" in paths
            or path in ids
            or any(f"KOD:{path}".startswith(p.rstrip("*")) and "*" in p for p in paths)
        ):
            continue
        gaps.append(
            {
                "kind": "NOT_ON_DASHBOARD",
                "path": f"KOD:{path}",
                "detail": f"JSON-lines ledger; last commit {ctx.kod.last_commit(path)}",
            }
        )
    for branch in ctx.backups.remote_branches():
        if branch in ids or any(p.startswith(f"BACKUPS:{branch}:") for p in paths):
            continue
        top = (ctx.backups.git("ls-tree", "--name-only", "origin/" + branch) or "").split()
        if "HEALTH.json" in top:
            kind = (
                "code/ops branch (has .github)"
                if ".github" in top
                else "server branch with HEALTH.json"
            )
            gaps.append({"kind": "NOT_ON_DASHBOARD", "path": f"BACKUPS:{branch}", "detail": kind})
    try:
        for item in ctx.kod.json("configs/experiments.json")["experiments"]:
            if item["id"] not in ids:
                gaps.append(
                    {
                        "kind": "NOT_ON_DASHBOARD",
                        "path": f"KOD:configs/experiments.json#{item['id']}",
                        "detail": f"catalog status {item.get('status')}",
                    }
                )
    except (SourceMissing, KeyError, ValueError) as exc:
        gaps.append(gap_for(exc, "KOD:configs/experiments.json", "catalog check"))
    for path in ctx.kod.ls("handoff/decisions"):
        heading = ctx.kod.text(path).split("\n", 1)[0]
        if re.search(r"\b(CLOSED|close|retire)\b", heading, re.I) and f"KOD:{path}" not in paths:
            gaps.append(
                {
                    "kind": "NOT_ON_DASHBOARD",
                    "path": f"KOD:{path}",
                    "detail": "closing decision not cited by any closed entry",
                }
            )
    return gaps


# ============================================================================ owner view: programs
def gain(points: list[dict], key: str, today: str, days: int = GAIN_DAYS) -> int | None:
    """How much a cumulative history count grew over the last `days` WIB days (None without
    history). The value on a day is the latest row on or before it, 0 before the first row."""
    series = sorted((h["date"], h[key]) for h in points if h.get(key) is not None)
    if not series:
        return None
    back = (date.fromisoformat(today) - timedelta(days=days)).isoformat()

    def value_on(day: str) -> int:
        return next((v for d, v in reversed(series) if d <= day), 0)

    return value_on(today) - value_on(back)


def program_lead(program: dict, members: list[dict]) -> dict | None:
    """Registry `lead` if set; else the member with the earliest verdict_date; else the highest
    fraction; else the first member (registry order breaks every tie)."""
    if not members:
        return None
    by_id = {m["id"]: m for m in members}
    if program.get("lead") in by_id:
        return by_id[program["lead"]]
    dated = [m for m in members if m["verdict_date"]]
    if dated:
        return min(dated, key=lambda m: m["verdict_date"])
    with_fraction = [m for m in members if m["fraction"] is not None]
    if with_fraction:
        return max(with_fraction, key=lambda m: m["fraction"])  # max keeps the first of a tie
    return members[0]


def soonest_stale(members: list[dict]) -> dict | None:
    """The member whose as_of + stale_after_hours comes first (no as_of: already stale; no limit:
    never), so the program is stale on the viewer's clock exactly when any member is. CLOSED
    members are never aged, so they only count when nothing else is left."""
    pool = [m for m in members if m["state"] != "CLOSED"] or members
    if not pool:
        return None

    def deadline(m: dict) -> datetime:
        if m["as_of"] is None:
            return datetime.min.replace(tzinfo=UTC)
        if m["stale_after_hours"] is None:
            return datetime.max.replace(tzinfo=UTC)
        return parse_ts(m["as_of"]) + timedelta(hours=m["stale_after_hours"])

    return min(pool, key=deadline)


def build_programs(registry: dict, rows: list[dict], history: list[dict], today: str) -> list[dict]:
    """programs.json: one row per registry program, summarised from its live/server members."""
    by_exp = defaultdict(list)
    for h in history:
        by_exp[h["experiment"]].append(h)
    out = []
    programs = registry.get("programs") or []
    for position, program in sorted(
        enumerate(programs), key=lambda item: (item[1].get("order", item[0]), item[0])
    ):
        members = [r for r in rows if r["program"] == program["id"] and r["group"] != "closed"]
        lead = program_lead(program, members)
        bad = [m for m in members if m["state"] in BAD_STATES]
        if bad:
            status = "issue"
        elif all(m["state"] == "WAITING" for m in members):
            status = "waiting"
        else:
            status = "running"
        lead_history = by_exp.get(lead["id"], []) if lead else []
        started = [h["date"] for m in members for h in by_exp.get(m["id"], [])]
        fresh = soonest_stale(members)
        upcoming = [m for m in members if m["verdict_date"] and m["verdict_date"] >= today]
        nxt = min(upcoming, key=lambda m: m["verdict_date"]) if upcoming else None
        out.append(
            {
                "id": program["id"],
                "name": program["name"],
                "question": program.get("question"),
                "order": program.get("order", position),
                "tests": len(members),
                "lead": lead["id"] if lead else None,
                "lead_short": lead["short"] if lead else None,
                "status": status,
                "issue": bad[0]["issue"] if bad else None,
                "scored": lead["scored"] if lead else None,
                "needed": lead["needed"] if lead else None,
                "progress": lead["fraction"] if lead else None,
                "unit": lead["unit"] if lead else None,
                "scored_7d": gain(lead_history, "scored", today) if lead else None,
                "collected": lead["collected"] if lead else None,
                "collected_7d": gain(lead_history, "collected", today) if lead else None,
                "verdict_date": lead["verdict_date"] if lead else None,
                "verdict_basis": lead["verdict_basis"] if lead else None,
                # the earliest verdict any member is due to reach (registry order breaks ties)
                "next_verdict_date": nxt["verdict_date"] if nxt else None,
                "next_verdict_basis": nxt["verdict_basis"] if nxt else None,
                "next_verdict_what": nxt["short"] if nxt else None,
                "started": min(started) if started else None,
                "as_of": fresh["as_of"] if fresh else None,
                "stale_after_hours": fresh["stale_after_hours"] if fresh else None,
            }
        )
    return out


def build_summary(
    rows: list[dict], programs: list[dict], history: list[dict], today: str, built_at: str
) -> dict:
    """summary.json's single row: the owner's headline numbers."""
    live = [r for r in rows if r["group"] in ("live", "server")]
    closed = [r for r in rows if r["group"] == "closed"]
    outcomes = Counter(r["outcome"] for r in closed)
    upcoming = [p for p in programs if p["next_verdict_date"] and p["next_verdict_date"] >= today]
    first = min(upcoming, key=lambda p: p["next_verdict_date"]) if upcoming else None
    return {
        "proven_live": sum(r["outcome"] == "worked" for r in live),
        "live_tests": len(live),
        "programs": len(programs),
        "ideas_tested": sum(r["outcome"] != "not_an_idea" for r in closed),
        "worked": outcomes["worked"],
        "didnt_work": outcomes["didnt_work"],
        "no_answer": outcomes["no_answer"],
        "checks": outcomes["not_an_idea"],
        "next_verdict_date": first["next_verdict_date"] if first else None,
        "next_verdict_program": first["name"] if first else None,
        "next_verdict_what": first["next_verdict_what"] if first else None,
        "next_verdict_basis": first["next_verdict_basis"] if first else None,
        "issues": sum(p["status"] == "issue" for p in programs),
        "first_record_date": min((h["date"] for h in history), default=None),
        "built_at": built_at,
    }


# ================================================================================= output trimming
def thin_server_history(rows: list[dict], now: datetime) -> list[dict]:
    """Keep 30 days; every heartbeat in the last 48 h, older ones one per study per 6 h; status
    changes always."""
    keep, last_status, seen_bucket = [], {}, set()
    for row in sorted(rows, key=lambda r: (r["study"], r["at"])):
        when = parse_ts(row["at"])
        if now - when > timedelta(days=SERVER_DAYS):
            last_status[row["study"]] = row["status"]
            continue
        changed = last_status.get(row["study"]) != row["status"]
        last_status[row["study"]] = row["status"]
        bucket = (row["study"], int(when.timestamp() // (SERVER_THIN_HOURS * 3600)))
        if changed or now - when <= timedelta(hours=SERVER_FULL_HOURS) or bucket not in seen_bucket:
            seen_bucket.add(bucket)
            keep.append({k: row[k] for k in ("at", "study", "status", "coverage", "captured")})
    return sorted(keep, key=lambda r: r["at"])


def fit_size(name: str, rows: list[dict], time_key: str | None) -> tuple[list[dict], int]:
    """Drop the oldest rows until the file is under SIZE_LIMIT (a safety net; normal trimming comes
    first)."""
    dropped = 0
    ordered = sorted(rows, key=lambda r: r.get(time_key) or "") if time_key else list(rows)
    while ordered and len(json.dumps(ordered, indent=1, ensure_ascii=False).encode()) > SIZE_LIMIT:
        cut = max(1, len(ordered) // 20)
        ordered, dropped = ordered[cut:], dropped + cut
    if dropped:
        print(f"WARNING: {name}: dropped {dropped} oldest row(s) to stay under {SIZE_LIMIT} bytes")
    return ordered, dropped


def write_json(out: Path, name: str, rows: list[dict]) -> int:
    data = json.dumps(rows, indent=1, ensure_ascii=False) + "\n"
    (out / name).write_text(data, encoding="utf-8")
    return len(data.encode())


# ===================================================================================== main
def load_registry(path: Path) -> dict:
    registry = json.loads(path.read_text(encoding="utf-8"))
    seen = Counter(e["id"] for e in registry["experiments"])
    duplicates = [k for k, n in seen.items() if n > 1]
    if duplicates:
        raise SystemExit(f"registry has duplicate ids: {duplicates}")
    unknown = [e["id"] for e in registry["experiments"] if e["reader"] not in READERS]
    if unknown:
        raise SystemExit(f"registry entries name unknown readers: {unknown}")
    programs = registry.get("programs") or []
    program_ids = Counter(p["id"] for p in programs)
    duplicates = [k for k, n in program_ids.items() if n > 1]
    if duplicates:
        raise SystemExit(f"registry has duplicate program ids: {duplicates}")
    members = defaultdict(set)
    for e in registry["experiments"]:
        if e.get("program") is not None:
            if e["program"] not in program_ids:
                raise SystemExit(f"registry entry {e['id']} names unknown program {e['program']}")
            members[e["program"]].add(e["id"])
        if e.get("outcome") is not None and e["outcome"] not in OUTCOMES:
            raise SystemExit(
                f"registry entry {e['id']} has outcome {e['outcome']!r}; use one of {OUTCOMES}"
            )
    for p in programs:
        if p.get("lead") is not None and p["lead"] not in members[p["id"]]:
            raise SystemExit(f"program {p['id']} lead {p['lead']} is not one of its entries")
    return registry


def registry_warnings(registry: dict) -> list[str]:
    """Owner-view text that is missing or over its word limit (the build still runs)."""
    out, unassigned, no_outcome = [], [], []
    for e in registry["experiments"]:
        kind = "closed" if e["group"] == "closed" else "live"
        if kind == "live" and e.get("program") is None:
            unassigned.append(e["id"])
        if kind == "closed" and e.get("outcome") is None:
            no_outcome.append(e["id"])
        for key, limit in WORD_LIMITS[kind].items():
            words = len(str(e.get(key) or "").split())
            if words > limit:
                out.append(f"{e['id']}.{key} has {words} words (limit {limit})")
    if unassigned:
        out.append(
            f"{len(unassigned)} live/server entries have no program: {', '.join(unassigned)}"
        )
    if no_outcome:
        out.append(f"{len(no_outcome)} closed entries have no outcome: {', '.join(no_outcome)}")
    return out


def build(args) -> dict:
    now = parse_ts(args.now) if args.now else datetime.now(UTC)
    registry = load_registry(Path(args.registry))
    kod = Repo(args.kod, args.kod_ref, "KOD")
    backups = Repo(args.backups, None, "BACKUPS")
    if not kod.head():
        raise SystemExit(f"cannot resolve {args.kod_ref} in {args.kod}")
    ctx = Ctx(kod, backups, registry, now)
    gaps, experiments, history, events, servers, server_history = [], [], [], [], [], []
    for entry in registry["experiments"]:
        built = build_experiment(ctx, entry, gaps)
        experiments.append(built["row"])
        history += built["history"]
        events += built["events"]
        if built["server"]:
            servers.append(built["server"])
        elif entry["reader"] == "server_study":
            p = entry["params"]
            servers.append(
                {
                    "study": p["study"],
                    "name": p["name"],
                    "status": "UNKNOWN",
                    "phase": None,
                    "coverage": None,
                    "captured": None,
                    "planned": None,
                    "issues": "reader failed",
                    "as_of": None,
                    "stale_after_hours": p.get("stale_after_hours"),
                    "ends_at": None,
                    "source": f"BACKUPS:{p['branch']}:HEALTH.json",
                }
            )
        server_history += built["server_history"]
    for server in servers:
        if server["status"] in LIVE_STATES or server["status"] == "STALLED":
            fresh, _ = freshness("RUNNING", server["as_of"], server["stale_after_hours"], now)
            if fresh == "UNKNOWN":
                server["status"] = "UNKNOWN"
    runs, run_days, job_events = build_jobs(ctx, gaps)
    events += job_events
    try:
        events += decision_events(ctx)
    except Exception as exc:  # events are optional decoration; report and continue
        gaps.append(gap_for(exc, "KOD:handoff/decisions/", "decision events"))
    events += closed_verdict_events(ctx, registry["experiments"], experiments)
    try:
        gaps += gap_detector(ctx)
    except Exception as exc:
        gaps.append(gap_for(exc, "registry", "gap detector"))
    since = iso(now - timedelta(days=EVENT_DAYS))
    unique = {}
    for item in events:
        if item["at"] and item["source"] and since <= item["at"] <= iso(now + timedelta(hours=1)):
            unique[(item["at"], item["title"])] = item
    events = sorted(unique.values(), key=lambda e: e["at"], reverse=True)
    backups_heads = "; ".join(
        f"{b}={backups.head('origin/' + b)[:12]}" for b in sorted(backups.remote_branches())
    )
    self_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    build_row = [
        {
            "built_at": iso(now),
            "kod_commit": kod.head(),
            "backups_commits": backups_heads,
            "builder": f"tools/status/build_status.py sha256:{self_hash} python "
            f"{sys.version.split()[0]}",
            "registry_entries": len(registry["experiments"]),
        }
    ]
    server_history = thin_server_history(server_history, now)
    programs = build_programs(registry, experiments, history, ctx.today_wib)
    summary = build_summary(experiments, programs, history, ctx.today_wib, iso(now))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    datasets = {
        "experiments.json": (experiments, None),
        "programs.json": (programs, None),
        "summary.json": ([summary], None),
        "history.json": (history, "date"),
        "runs.json": (runs, None),
        "run_days.json": (run_days, "date"),
        "server.json": (servers, None),
        "server_history.json": (server_history, "at"),
        "events.json": (events, None),
        "gaps.json": (gaps, None),
        "build.json": (build_row, None),
    }
    sizes = {}
    for name, (rows, key) in datasets.items():
        if key:
            rows, _ = fit_size(name, rows, key)
        sizes[name] = (len(rows), write_json(out, name, rows))
    return {
        "experiments": experiments,
        "programs": programs,
        "summary": summary,
        "warnings": registry_warnings(registry),
        "gaps": gaps,
        "events": events,
        "runs": runs,
        "run_days": run_days,
        "servers": servers,
        "sizes": sizes,
        "build": build_row[0],
    }


def print_summary(result: dict, out: str) -> None:
    print(
        f"built {result['build']['built_at']}  kod {result['build']['kod_commit'][:12]}  -> {out}"
    )
    for name, (count, size) in result["sizes"].items():
        print(f"  {name:22s} {count:5d} rows {size:8d} bytes")
    states = Counter(r["state"] for r in result["experiments"])
    print("experiment states: " + ", ".join(f"{k} {v}" for k, v in sorted(states.items())))
    for row in result["experiments"]:
        if row["group"] != "closed":
            print(
                f"  {row['id']:26s} {row['state']:8s} collected {row['collected']!s:>6} "
                f"scored {row['scored']!s:>5} needed {row['needed']!s:>5} as_of {row['as_of']}"
                + (f" issue: {row['issue']}" if row["issue"] else "")
            )
    closed = [r for r in result["experiments"] if r["group"] == "closed"]
    print(
        f"  closed rows: {len(closed)} ({sum(r['state'] == 'CLOSED' for r in closed)} "
        "verified CLOSED)"
    )
    for server in result["servers"]:
        print(
            f"  server {server['study']:22s} {server['status']:8s} coverage {server['coverage']} "
            f"captured {server['captured']} as_of {server['as_of']}"
        )
    for program in result["programs"]:
        print(
            f"  program {program['id']:20s} {program['status']:7s} tests {program['tests']} "
            f"lead {program['lead']} verdict {program['verdict_date']} ({program['verdict_basis']}) "
            f"next {program['next_verdict_date']} {program['next_verdict_what']}"
            + (f" issue: {program['issue']}" if program["issue"] else "")
        )
    summary = result["summary"]
    print(
        f"summary: {summary['live_tests']} live tests in {summary['programs']} programs, "
        f"{summary['ideas_tested']} ideas tested ({summary['worked']} worked, "
        f"{summary['didnt_work']} did not, {summary['no_answer']} no answer), "
        f"next verdict {summary['next_verdict_date']} ({summary['next_verdict_what']})"
    )
    for warning in result["warnings"]:
        print(f"  registry: {warning}")
    day_states = Counter(d["status"] for d in result["run_days"])
    print("run_days: " + ", ".join(f"{k} {v}" for k, v in sorted(day_states.items())))
    print(
        "events: "
        + ", ".join(
            f"{k} {v}" for k, v in sorted(Counter(e["kind"] for e in result["events"]).items())
        )
    )
    print(
        "gaps: "
        + ", ".join(
            f"{k} {v}" for k, v in sorted(Counter(g["kind"] for g in result["gaps"]).items())
        )
    )
    for item in result["gaps"]:
        if item["kind"] != "NOT_ON_DASHBOARD":
            print(f"  {item['kind']}: {item['path']} | {item['detail']}")


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--kod", required=True, help="path to the KOD-Machine repo")
    parser.add_argument(
        "--kod-ref",
        required=True,
        help="ref to read, e.g. origin/claude/idx-signals-test-repo-ds0jw7",
    )
    parser.add_argument("--backups", required=True, help="path to the kod-timing-backups repo")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--registry", default=str(here / "experiments.json"))
    parser.add_argument(
        "--now", help="ISO UTC build time (default: the clock); for reproducible builds"
    )
    args = parser.parse_args(argv)
    result = build(args)
    print_summary(result, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

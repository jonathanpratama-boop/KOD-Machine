"""Black-box tests for tools/status/build_status.py (KOD status dashboard generator).

Run:  cd /home/user/KOD-Machine && python3 -m unittest tools/status/test_build_status.py -v
      (or: python3 tools/status/test_build_status.py)

These tests were written WITHOUT reading build_status.py. They exercise it only
through its command line and the JSON files it writes.

ASSUMPTIONS (documented as required):
  * CLI: python3 tools/status/build_status.py --kod <repo> --kod-ref <ref>
         --backups <repo> --out <dir> [--registry <path>]
    `--registry <path>` points the builder at a registry file other than its
    default tools/status/experiments.json. It is used only by the fixture tests.
  * The builder exits 0 when it finishes, even if some sources are missing or
    unreadable (those become gaps.json rows, never a crash).
  * The registry file is JSON: either a list of entries or an object holding the
    list under "experiments" (or "entries"); each entry has an "id".
  * Experiment ids follow the cartographer specs (LLM_ARM_v1, SPEC_REGISTER_US,
    SPEC_REGISTER_IDX, SPEC_REGISTER_CRYPTO, LEARNER_v2_2, LEARNER_v2_4,
    PAPER_BOOK_v1, PREMOVE_SHADOW_v1, srv:research_r2, srv:timing_capture_30).
    Lookups fall back to name/source matching where noted.
  * run_days.json statuses are exactly the four documented ones.
  * fraction == min(1, scored/needed) (the schema says fraction is 0-1).
  * A non-CLOSED experiment (or server study) whose as_of is older than
    stale_after_hours at build.json.built_at must not read RUNNING/WAITING.
  * `--now <UTC ISO>` sets the build time (used once, by OwnerView, for a build
    "4 days later").

The owner's-view tests (OwnerView, and the owner_view checks on the other two
builds) were written by a second agent from the page's data contract (programs.json,
summary.json, the new experiments.json fields), also without reading
build_status.py. Contract readings they rely on: the build day and history days are
WIB (UTC+7) days; a 7-day gain is the newest cumulative value minus the value as of
build day - 7 (0 if the series starts later); "first member" and lead ties follow
registry order; worked / didnt_work / no_answer count closed rows; a server study's
end may be read as its UTC or its WIB day.

The next-verdict and plumbing tests (NextVerdict, and those checks in the shared
helpers) were written by a third agent from the changed contract, again without
reading the builder's code: a registry entry may carry "plumbing": true (a
data-collection check that answers no question); its row's `plumbing` is true
(false unless set) and its verdict_date / verdict_basis are null even with a fixed end
or projected_date. programs.json's next_verdict_date / _basis / _what are the earliest
member verdict_date on or after the build's WIB day, that member's basis and `short`
(registry order breaks ties; null when none); verdict_date / verdict_basis stay the
lead's. summary.json's next_verdict_* come from the program with the earliest
next_verdict_date (on or after the build day), using that program's next_verdict_*.
Ties between programs are not in the contract, so any tied program is accepted.

The real-data tests recompute every checked number from the raw default-branch
files (git show) with code in this file; nothing is hard-coded except the
protocol constant FIRST_LOOK = 60 and the paper-book look size 300.

Nothing here writes to either repository. The fixture is a fresh `git init`
repository under a temp dir that borrows KOD's objects through
objects/info/alternates and adds one synthetic commit on top of the default
branch head (one source deleted, one ledger line corrupted, one unregistered
research folder added).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from datetime import date, datetime, timedelta, timezone

KOD = os.environ.get("KOD_REPO", "/home/user/KOD-Machine")
BACKUPS = os.environ.get("KOD_BACKUPS_REPO", "/home/user/kod-timing-backups")
REF = "origin/claude/idx-signals-test-repo-ds0jw7"
BUILDER = os.path.join(KOD, "tools", "status", "build_status.py")
REGISTRY = os.path.join(KOD, "tools", "status", "experiments.json")
RUN_TIMEOUT = 110
MAX_FILE_BYTES = 256 * 1024

DATASETS = {
    "experiments.json": {
        "id": (str,), "name": (str,), "plain": (str,), "group": (str,), "state": (str,),
        "collected": (int, None), "collected_label": (str, None),
        "scored": (int, None), "scored_label": (str, None),
        "needed": (int, None), "needed_label": (str, None),
        "fraction": (float, int, None), "as_of": (str, None),
        "stale_after_hours": (int, float), "next_milestone": (str, None),
        "next_date": (str, None), "projected_date": (str, None), "verdict": (str, None),
        "source": (str,), "note": (str, None),
        # owner's view (data contract): registry text, then builder-derived fields
        "program": (str, None), "short": (str, None), "ceo_line": (str, None), "unit": (str, None),
        "outcome": (str, None), "lesson": (str, None), "issue": (str, None),
        "verdict_date": (str, None), "verdict_basis": (str, None), "plumbing": (bool,),
    },
    "programs.json": {
        "id": (str,), "name": (str,), "question": (str,), "order": (int, float), "tests": (int,),
        "lead": (str, None), "lead_short": (str, None), "status": (str,), "issue": (str, None),
        "scored": (int, None), "needed": (int, None), "progress": (float, int, None), "unit": (str, None),
        "scored_7d": (int, None), "collected": (int, None), "collected_7d": (int, None),
        "verdict_date": (str, None), "verdict_basis": (str, None), "started": (str, None),
        "next_verdict_date": (str, None), "next_verdict_basis": (str, None), "next_verdict_what": (str, None),
        "as_of": (str, None), "stale_after_hours": (int, float),
    },
    "summary.json": {
        "proven_live": (int,), "live_tests": (int,), "programs": (int,), "ideas_tested": (int,),
        "worked": (int,), "didnt_work": (int,), "no_answer": (int,), "checks": (int,),
        "next_verdict_date": (str, None), "next_verdict_program": (str, None),
        "next_verdict_what": (str, None), "next_verdict_basis": (str, None),
        "issues": (int,), "first_record_date": (str, None), "built_at": (str,),
    },
    "history.json": {"date": (str,), "experiment": (str,), "collected": (int, None), "scored": (int, None)},
    "runs.json": {"job": (str,), "market": (str,), "last_success_at": (str, None),
                  "last_record": (str, None), "expected_every_hours": (int, float),
                  "grace_hours": (int, float), "source": (str,)},
    "run_days.json": {"date": (str,), "job": (str,), "status": (str,)},
    "server.json": {"study": (str,), "name": (str,), "status": (str,), "phase": (str, None),
                    "coverage": (float, int, None), "captured": (int, None), "planned": (int, None),
                    "issues": (str,), "as_of": (str, None), "stale_after_hours": (int, float),
                    "ends_at": (str, None), "source": (str,)},
    "server_history.json": {"at": (str,), "study": (str,), "status": (str,),
                            "coverage": (float, int, None), "captured": (int, None)},
    "events.json": {"at": (str,), "kind": (str,), "title": (str,), "detail": (str,), "source": (str,)},
    "gaps.json": {"kind": (str,), "path": (str,), "detail": (str,)},
    "build.json": {"built_at": (str,), "kod_commit": (str,), "backups_commits": (str,),
                   "builder": (str,), "registry_entries": (int,)},
}
GROUPS = {"live", "server", "closed"}
STATES = {"RUNNING", "WAITING", "HALTED", "CLOSED", "STALLED", "UNKNOWN"}
GREEN = {"RUNNING", "WAITING"}
RUN_DAY_STATUSES = {"ok", "missed", "partial", "not_expected"}
EVENT_KINDS = {"incident", "decision", "milestone"}
GAP_KINDS = {"NOT_ON_DASHBOARD", "SOURCE_MISSING", "READ_ERROR"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BAD = {"HALTED", "STALLED", "UNKNOWN"}
OUTCOMES = {"worked", "didnt_work", "no_answer", "not_an_idea"}
BASES = {"scheduled", "estimate"}
PROGRAM_STATUSES = {"running", "issue", "waiting"}
REGISTRY_TEXT = ("program", "short", "ceo_line", "unit", "outcome", "lesson")
WIB = timedelta(hours=7)
GAIN_DAYS = 7
ISSUE_MAX_WORDS = 10
# Words the owner must never see in builder-written text (plain-language rules).
JARGON = re.compile(r"\b(BASE5|NEXT1|PATH20|brier|protocols?|holdouts?|pp|sha(256)?|sets?|registers?|"
                    r"twins|cohorts?|priors?|abstain|fire|G2_RET30|F1_ARA|ledgers?)\b", re.I)


# --------------------------------------------------------------------------- helpers
def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout if r.returncode == 0 else None


def show(path, repo=KOD, ref=REF):
    return git(repo, "show", f"{ref}:{path}", check=False)


def jsonl(path, repo=KOD, ref=REF):
    t = show(path, repo, ref)
    if t is None:
        return None
    return [json.loads(line) for line in t.splitlines() if line.strip()]


def parse_utc(s):
    """Parse an ISO timestamp; raise unless it carries a UTC offset of zero."""
    if not isinstance(s, str) or "T" not in s:
        raise ValueError(f"not an ISO datetime: {s!r}")
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    if re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d([+-]|$)", t):  # minute precision
        t = t[:16] + ":00" + t[16:]
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise ValueError(f"not UTC: {s!r}")
    return dt


def is_date(s):
    if not isinstance(s, str) or not DATE_RE.match(s):
        return False
    date.fromisoformat(s)
    return True


def run_builder(out, kod=KOD, ref=REF, registry=None, now=None):
    cmd = [sys.executable, BUILDER, "--kod", kod, "--kod-ref", ref, "--backups", BACKUPS, "--out", out]
    if registry:
        cmd += ["--registry", registry]
    if now:
        cmd += ["--now", now]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=RUN_TIMEOUT)


def load_out(out):
    data = {}
    for name in DATASETS:
        p = os.path.join(out, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data[name] = json.load(f)
    return data


def registry_entries(path=REGISTRY):
    with open(path, encoding="utf-8") as f:
        reg = json.load(f)
    if isinstance(reg, dict):
        reg = reg.get("experiments", reg.get("entries", []))
    return reg


def find_exp(rows, ids, name_pat=None):
    by = {r.get("id"): r for r in rows}
    for i in ids:
        if i in by:
            return by[i]
    if name_pat:
        hits = [r for r in rows if re.search(name_pat, (r.get("name") or "") + " " + (r.get("id") or ""), re.I)]
        if len(hits) == 1:
            return hits[0]
    return None


# ------------------------------------------------- owner's view: rules from the contract
def registry_doc(path=REGISTRY):
    """(entries in registry order, programs) from a registry file."""
    with open(path, encoding="utf-8") as f:
        reg = json.load(f)
    if isinstance(reg, list):
        return reg, []
    return reg.get("experiments", reg.get("entries", [])), reg.get("programs") or []


def wib_day(dt):
    """The Indonesian-time (UTC+7) calendar day of a UTC datetime, as YYYY-MM-DD."""
    return (dt + WIB).date().isoformat()


def build_day(data):
    return wib_day(parse_utc(data["build.json"][0]["built_at"]))


def program_members(program_id, entries, rows_by_id):
    """Live/server rows of one program, in registry order (closed rows never count)."""
    return [rows_by_id[e["id"]] for e in entries
            if e.get("program") == program_id and e["id"] in rows_by_id
            and rows_by_id[e["id"]]["group"] != "closed"]


def lead_rule(program, members):
    """(acceptable lead ids, rule used) per the contract: registry lead, else earliest non-null
    verdict_date, else highest fraction, else the first member. Ties allow any tied member."""
    if program.get("lead"):
        return {program["lead"]}, "override"
    dated = [m for m in members if m["verdict_date"] is not None]
    if dated:
        first = min(m["verdict_date"] for m in dated)
        return {m["id"] for m in dated if m["verdict_date"] == first}, "earliest"
    with_fraction = [m for m in members if m["fraction"] is not None]
    if with_fraction:
        top = max(m["fraction"] for m in with_fraction)
        return {m["id"] for m in with_fraction if m["fraction"] == top}, "fraction"
    return ({members[0]["id"]} if members else {None}), "first"


def gain_7d(history_rows, key, today):
    """Gain of a cumulative history count over the last 7 WIB days: the newest value up to
    today minus the value as of today - 7 (0 if the series starts later); None without history."""
    rows = sorted((r for r in history_rows if r["date"] <= today and r[key] is not None),
                  key=lambda r: r["date"])
    if not rows:
        return None
    base_day = (date.fromisoformat(today) - timedelta(days=GAIN_DAYS)).isoformat()
    before = [r[key] for r in rows if r["date"] <= base_day]
    return rows[-1][key] - (before[-1] if before else 0)


def stale_deadline(row):
    """as_of + stale_after_hours; a row with no as_of counts as already stale."""
    if row["as_of"] is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return parse_utc(row["as_of"]) + timedelta(hours=row["stale_after_hours"])


# ------------------------------------------------------- independent recomputation
def norm_called(ts):
    return ts[:-1] + ":00Z" if len(ts) == 17 else ts


def expected_llm():
    reg = jsonl("idx-signals/paper/speculations.jsonl")
    names = git(KOD, "ls-tree", "--name-only", f"{REF}:idx-signals/research/LLM_ARM_v1").split()
    calls = []
    for f in sorted(n for n in names if n.startswith("calls") and n.endswith(".jsonl")):
        calls += jsonl("idx-signals/research/LLM_ARM_v1/" + f)
    set_count = Counter(r["set_id"] for r in reg if r["type"] == "SPECULATION_SET")
    sets = {r["set_id"]: r for r in reg if r["type"] == "SPECULATION_SET"}
    base5 = {}
    for r in reg:
        if r["type"] == "RESOLUTION" and r["window"] == "BASE5":
            base5.setdefault(r["set_id"], []).append(r)
    ids = Counter(c.get("call_id") for c in calls)
    per_set = Counter(c.get("set") for c in calls)
    ok, scored = [], 0
    for c in calls:
        s = sets.get(c.get("set"))
        if s is None or ids[c.get("call_id")] > 1 or per_set[c["set"]] > 1 or set_count[c["set"]] != 1:
            continue
        if any(c.get(k) != s.get(k) for k in ("ticker", "market", "signal_session")):
            continue
        t = parse_utc(norm_called(c["called_at"]))
        if not (parse_utc(s["sealed_at"]) <= t < parse_utc(s["entry_cutoff"])):
            continue
        if c.get("call") not in ("BACK", "AVOID", "ABSTAIN"):
            continue
        ok.append(c)
        rs = base5.get(c["set"], [])
        if len(rs) == 1:
            r = rs[0]
            if (r["status"] == "RESOLVED" and r.get("protocol") == s.get("protocol")
                    and parse_utc(r["resolved_at"]) >= max(t, parse_utc(s["entry_cutoff"]))):
                cone = {x["id"]: x for x in r.get("cone") or []}
                orig = {x["id"]: x for x in s.get("cone") or []}
                if all(isinstance(cone.get(k, {}).get("outcome"), bool)
                       and cone[k].get("prior") == orig.get(k, {}).get("prior")
                       for k in ("RUN30_5", "FADE10_5", "BEATS_TWINS_5")):
                    scored += 1
    as_of = max(parse_utc(norm_called(c["called_at"])) for c in ok)
    return {"collected": len(ok), "scored": scored, "needed": 60, "as_of": as_of}


def expected_spec():
    reg = jsonl("idx-signals/paper/speculations.jsonl")
    out = {}
    for m in ("US", "IDX", "CRYPTO"):
        sets = {r["set_id"] for r in reg if r["type"] == "SPECULATION_SET" and r["market"] == m}
        latest = {}
        for r in reg:
            if r["type"] == "RESOLUTION" and r["market"] == m:
                latest[(r["set_id"], r["window"])] = r
        paired = [r for (_, w), r in latest.items()
                  if w == "BASE5" and r["status"] == "RESOLVED" and r.get("paired") is not None]
        out[m] = {"collected": len(sets), "scored": len(paired)}
    out["ALL"] = sum(v["collected"] for v in out.values())
    return out


def expected_learners():
    l2 = jsonl("idx-signals/paper/learner_v2.jsonl")
    l3 = jsonl("idx-signals/paper/learner_v3.jsonl")
    f2 = [r for r in l2 if r.get("type") == "LEARNER2_FORECAST"]
    f3 = [r for r in l3 if r.get("type") == "LEARNER3_FORECAST"]
    return {"v2_2": {"collected": len(f2), "as_of": max(parse_utc(r["made_at"]) for r in f2)},
            "v2_4": {"collected": len(f3), "as_of": max(parse_utc(r["made_at"]) for r in f3)}}


def expected_paper_book():
    book = jsonl("idx-signals/paper/paper_book.jsonl")
    plans = {}
    for r in book:
        if r["type"] == "BOOK_PLAN":
            plans.setdefault(r["set_id"], r)
    res = {r["set_id"]: r for r in book if r["type"] == "BOOK_RESULT"}
    traded = [r for r in res.values() if r.get("status") == "TRADED" and r.get("net_return") is not None]
    return {"collected": len(plans), "scored": len(traded), "needed": 300}


def expected_server():
    h = json.loads(show("HEALTH.json", BACKUPS, "origin/research-r2-20261105T181200Z"))
    cov = h["collector"]["coverage"]
    halted = h.get("phase") in ("HALTED", "PAUSED") or h.get("pause_latched")
    status = "HALTED" if halted else {"OK": "RUNNING", "PRELIMINARY": "WAITING", "FAILED": "STALLED"}.get(h["status"], "UNKNOWN")
    main = json.loads(show("HEALTH.json", BACKUPS, "origin/main"))
    return {"r2": {"status": status, "raw_status": h["status"], "coverage": cov["pooled_on_time_coverage"],
                   "captured": cov["on_time_closed_total"], "as_of": parse_utc(h["emitted_at"])},
            "cohort": {"captured": main["counts"].get("CAPTURED", 0),
                       "planned": len(main["slots"]), "as_of": parse_utc(main["as_of"])}}


# ------------------------------------------------------------------- shared checks
class OutputChecks:
    """Mixin: schema assertions shared by the real-data and fixture builds."""

    def check_schema(self, data, out, allow_null_as_of_when_unknown=False):
        for name, schema in DATASETS.items():
            with self.subTest(file=name):
                p = os.path.join(out, name)
                self.assertTrue(os.path.exists(p), f"{name} not written")
                self.assertLess(os.path.getsize(p), MAX_FILE_BYTES, f"{name} >= 256 KB")
                rows = data[name]
                self.assertIsInstance(rows, list, f"{name} is not a JSON array")
                for i, row in enumerate(rows):
                    self.assertIsInstance(row, dict, f"{name}[{i}] not an object")
                    self.assertEqual(set(row), set(schema), f"{name}[{i}] keys differ: {sorted(set(row) ^ set(schema))}")
                    for k, types in schema.items():
                        v = row[k]
                        self.assertNotIsInstance(v, (dict, list), f"{name}[{i}].{k} is nested (rows must be flat)")
                        if v is None:
                            self.assertIn(None, types, f"{name}[{i}].{k} is null")
                            continue
                        py = tuple(t for t in types if t is not None)
                        if bool not in py:  # a bool is an int in Python; only bool fields may hold one
                            self.assertFalse(isinstance(v, bool), f"{name}[{i}].{k} is a bool")
                        self.assertIsInstance(v, py, f"{name}[{i}].{k}={v!r} wrong type")

    def check_semantics(self, data, allow_null_as_of_when_unknown=False):
        exps = data["experiments.json"]
        build = data["build.json"]
        self.assertEqual(len(build), 1, "build.json must hold exactly one row")
        built_at = parse_utc(build[0]["built_at"])
        ids = [e["id"] for e in exps]
        self.assertEqual(len(ids), len(set(ids)), "duplicate experiment ids")
        for e in exps:
            with self.subTest(experiment=e["id"]):
                self.assertIn(e["group"], GROUPS)
                self.assertIn(e["state"], STATES)
                if e["as_of"] is None:
                    self.assertTrue(allow_null_as_of_when_unknown and e["state"] == "UNKNOWN",
                                    "as_of null on a row that is not UNKNOWN")
                else:
                    as_of = parse_utc(e["as_of"])
                    age_h = (built_at - as_of).total_seconds() / 3600
                    if e["state"] != "CLOSED" and age_h > e["stale_after_hours"]:
                        self.assertNotIn(e["state"], GREEN,
                                         f"as_of {age_h:.1f}h old > limit {e['stale_after_hours']}h but state {e['state']}")
                for k in ("next_date", "projected_date"):
                    if e[k] is not None:
                        self.assertTrue(is_date(e[k]), f"{k}={e[k]!r}")
                for k in ("collected", "scored", "needed"):
                    if e[k] is not None:
                        self.assertGreaterEqual(e[k], 0)
                if e["fraction"] is not None:
                    self.assertTrue(0 <= e["fraction"] <= 1, f"fraction {e['fraction']}")
                if e["scored"] is not None and e["needed"]:
                    self.assertIsNotNone(e["fraction"], "fraction missing though scored and needed are set")
                    self.assertAlmostEqual(e["fraction"], min(1.0, e["scored"] / e["needed"]), places=3)
                if e["needed"] is None or e["scored"] is None:
                    self.assertIsNone(e["fraction"], "fraction set without scored/needed")
                self.assertTrue(e["source"].strip(), "empty source")

        # history: cumulative, non-decreasing, one row per day, known experiments
        per = {}
        for h in data["history.json"]:
            self.assertTrue(is_date(h["date"]), h)
            self.assertIn(h["experiment"], ids, f"history for unknown experiment {h['experiment']}")
            per.setdefault(h["experiment"], []).append(h)
        by_id = {e["id"]: e for e in exps}
        for exp_id, rows in per.items():
            with self.subTest(history=exp_id):
                dates = [r["date"] for r in rows]
                self.assertEqual(len(dates), len(set(dates)), "duplicate history dates")
                rows = sorted(rows, key=lambda r: r["date"])
                for k in ("collected", "scored"):
                    vals = [r[k] for r in rows if r[k] is not None]
                    self.assertEqual(vals, sorted(vals), f"history {k} decreases")
                last = rows[-1]["collected"]
                if by_id[exp_id]["collected"] is not None and last is not None:
                    self.assertEqual(last, by_id[exp_id]["collected"], "last history collected != current collected")

        jobs = {r["job"] for r in data["runs.json"]}
        for r in data["runs.json"]:
            if r["last_success_at"] is not None:
                parse_utc(r["last_success_at"])
            self.assertGreater(r["expected_every_hours"], 0)
            self.assertGreaterEqual(r["grace_hours"], 0)
        seen = Counter()
        for d in data["run_days.json"]:
            self.assertTrue(is_date(d["date"]), d)
            self.assertIn(d["status"], RUN_DAY_STATUSES, d)
            self.assertIn(d["job"], jobs, f"run_days job {d['job']} missing from runs.json")
            seen[(d["job"], d["date"])] += 1
        self.assertFalse([k for k, n in seen.items() if n > 1], "duplicate (job, date) in run_days")
        for j in jobs:
            self.assertLessEqual(len({d for (jj, d) in seen if jj == j}), 31, f"{j}: more than 30 days")

        for s in data["server.json"]:
            with self.subTest(server=s["study"]):
                if s["coverage"] is not None:
                    self.assertTrue(0 <= s["coverage"] <= 1)
                if s["ends_at"] is not None:
                    parse_utc(s["ends_at"])
                if s["as_of"] is not None:
                    age_h = (built_at - parse_utc(s["as_of"])).total_seconds() / 3600
                    if age_h > s["stale_after_hours"] and s["status"] not in ("CLOSED",):
                        self.assertNotIn(s["status"], GREEN | {"OK"}, f"stale server study reads {s['status']}")
        for h in data["server_history.json"]:
            parse_utc(h["at"])
            if h["coverage"] is not None:
                self.assertTrue(0 <= h["coverage"] <= 1)
        for ev in data["events.json"]:
            parse_utc(ev["at"])
            self.assertIn(ev["kind"], EVENT_KINDS)
            self.assertTrue(ev["source"].strip(), f"event without a cited record: {ev['title']}")
        for g in data["gaps.json"]:
            self.assertIn(g["kind"], GAP_KINDS)
            self.assertTrue(g["path"].strip())

    # ---------------------------------------------------------- owner's view (contract)
    def check_registry_text(self, data, registry_path):
        """program/ceo_line/unit/outcome/lesson are the registry's values, null where not set;
        a set `short` is copied as is (the null default for `short` is its own test)."""
        entries, _ = registry_doc(registry_path)
        by_id = {e["id"]: e for e in data["experiments.json"]}
        for entry in entries:
            row = by_id.get(entry["id"])
            if row is None:
                continue
            with self.subTest(experiment=entry["id"]):
                for k in REGISTRY_TEXT:
                    if k == "short" and k not in entry:
                        continue
                    self.assertEqual(row[k], entry.get(k), f"{k}: row {row[k]!r} != registry {entry.get(k)!r}")
                if row["outcome"] is not None:
                    self.assertIn(row["outcome"], OUTCOMES)

    def check_short_default(self, data, registry_path):
        """Contract: `short` is null where the registry does not set it."""
        entries, _ = registry_doc(registry_path)
        by_id = {e["id"]: e for e in data["experiments.json"]}
        filled = sorted(e["id"] for e in entries
                        if "short" not in e and e["id"] in by_id and by_id[e["id"]]["short"] is not None)
        self.assertEqual(filled, [], "rows whose registry entry has no `short` but whose row has one "
                         "(contract: null where not set)")

    def check_issue_field(self, data):
        for e in data["experiments.json"]:
            with self.subTest(experiment=e["id"], state=e["state"]):
                if e["state"] in BAD:
                    self.assertIsInstance(e["issue"], str, "HALTED/STALLED/UNKNOWN row without an issue")
                    self.assertTrue(e["issue"].strip(), "empty issue text")
                    self.assertLessEqual(len(e["issue"].split()), ISSUE_MAX_WORDS, f"issue too long: {e['issue']!r}")
                    self.assertIsNone(JARGON.search(e["issue"]), f"jargon in issue: {e['issue']!r}")
                else:
                    self.assertIsNone(e["issue"], f"issue set on a {e['state']} row: {e['issue']!r}")

    def check_verdict_dates(self, data, registry_path):
        entries, _ = registry_doc(registry_path)
        reg = {e["id"]: e for e in entries}
        ends = {s["study"]: s["ends_at"] for s in data["server.json"]}
        for e in data["experiments.json"]:
            vd, basis = e["verdict_date"], e["verdict_basis"]
            plumbing = bool(reg.get(e["id"], {}).get("plumbing"))
            with self.subTest(experiment=e["id"], verdict_date=vd, basis=basis):
                self.assertIs(e["plumbing"], plumbing, "plumbing must be the registry flag (false unless set)")
                self.assertEqual(vd is None, basis is None, "verdict_date and verdict_basis must be null together")
                if plumbing:
                    # a data-collection check answers no question: it has an end, never a verdict
                    self.assertEqual((vd, basis), (None, None), "a plumbing row must have a null verdict_date/basis")
                    continue
                if vd is None:
                    self.assertTrue(e["group"] == "closed" or (e["projected_date"] is None
                                                             and not reg.get(e["id"], {}).get("fixed_end")
                                                             and not (e["group"] == "server" and ends.get(e["id"]))),
                                    "verdict_date null though a fixed end or projected_date exists (not plumbing)")
                    continue
                self.assertTrue(is_date(vd), f"verdict_date {vd!r} is not YYYY-MM-DD")
                self.assertIn(basis, BASES)
                self.assertNotEqual(e["group"], "closed", "a closed row has no verdict still to come")
                fixed_end = reg.get(e["id"], {}).get("fixed_end")
                if fixed_end:
                    self.assertEqual((vd, basis), (fixed_end, "scheduled"), "fixed end must be the verdict date")
                elif e["group"] == "server" and ends.get(e["id"]):
                    end = parse_utc(ends[e["id"]])
                    self.assertIn(vd, {end.date().isoformat(), wib_day(end)}, f"server end {ends[e['id']]}")
                    self.assertEqual(basis, "scheduled")
                elif e["projected_date"] is not None:
                    self.assertEqual(vd, e["projected_date"], "no fixed end: verdict_date must be projected_date")
                if basis == "estimate":
                    self.assertEqual(vd, e["projected_date"], "an estimate must come from projected_date")

    def expected_programs(self, data, registry_path):
        """Recompute every programs.json row from the contract, experiments.json and history.json."""
        entries, programs = registry_doc(registry_path)
        rows = {e["id"]: e for e in data["experiments.json"]}
        hist = {}
        for h in data["history.json"]:
            hist.setdefault(h["experiment"], []).append(h)
        today = build_day(data)
        out = {}
        for p in programs:
            members = program_members(p["id"], entries, rows)
            leads, rule = lead_rule(p, members)
            lead = next((m for m in members if m["id"] in leads), None)
            bad = [m for m in members if m["state"] in BAD]
            status = "issue" if bad else ("waiting" if members and all(m["state"] == "WAITING" for m in members)
                                          else "running")
            dates = [h["date"] for m in members for h in hist.get(m["id"], [])]
            soonest = min((stale_deadline(m) for m in members), default=None)
            upcoming = [m for m in members if m["verdict_date"] is not None and m["verdict_date"] >= today]
            first = min((m["verdict_date"] for m in upcoming), default=None)
            out[p["id"]] = {
                "registry": p, "members": members, "leads": leads, "rule": rule, "lead": lead,
                # the earliest member verdict on/after the build day; registry order breaks ties
                "next": next((m for m in upcoming if m["verdict_date"] == first), None),
                "status": status, "issue": bad[0]["issue"] if bad else None, "soonest": soonest,
                "pairs": {(m["as_of"], m["stale_after_hours"]) for m in members if stale_deadline(m) == soonest},
                "started": min(dates) if dates else None,
                "scored_7d": gain_7d(hist.get(lead["id"], []), "scored", today) if lead else None,
                "collected_7d": gain_7d(hist.get(lead["id"], []), "collected", today) if lead else None,
            }
        return out

    def check_programs(self, data, registry_path):
        want = self.expected_programs(data, registry_path)
        got = data["programs.json"]
        self.assertEqual(sorted(p["id"] for p in got), sorted(want), "programs.json ids != registry programs")
        for p in got:
            w = want[p["id"]]
            reg, lead = w["registry"], w["lead"]
            with self.subTest(program=p["id"]):
                for k in ("name", "question", "order"):
                    self.assertEqual(p[k], reg.get(k), f"{k} not copied from the registry")
                self.assertEqual(p["tests"], len(w["members"]), "tests != live/server members")
                self.assertIn(p["lead"], w["leads"], f"lead {p['lead']} breaks the '{w['rule']}' rule")
                self.assertIn(p["status"], PROGRAM_STATUSES)
                self.assertEqual(p["status"], w["status"], "status rule")
                self.assertEqual(p["issue"], w["issue"], "issue must be the first member issue (null otherwise)")
                self.assertEqual(p["started"], w["started"], "started = first history date of any member")
                nxt = w["next"]
                self.assertEqual((p["next_verdict_date"], p["next_verdict_basis"], p["next_verdict_what"]),
                                 (nxt["verdict_date"], nxt["verdict_basis"], nxt["short"]) if nxt else (None, None, None),
                                 "next_verdict_* = the earliest member verdict on/after the build day, its basis and "
                                 "short (registry order breaks ties; null when none)")
                if lead is None:
                    continue
                # with a tie, judge the lead-derived fields against the tied lead the build chose
                lead = next((m for m in w["members"] if m["id"] == p["lead"]), lead)
                self.assertEqual(p["lead_short"], lead["short"], "lead_short = the lead's short")
                for k in ("scored", "needed", "collected", "unit", "verdict_date", "verdict_basis"):
                    self.assertEqual(p[k], lead[k], f"{k} must be the lead's")
                if lead["scored"] is not None and lead["needed"]:
                    self.assertIsNotNone(p["progress"])
                    self.assertTrue(0 <= p["progress"] <= 1, f"progress {p['progress']} outside 0..1")
                    self.assertAlmostEqual(p["progress"], min(1.0, lead["scored"] / lead["needed"]), places=3)
                else:
                    self.assertIsNone(p["progress"], "progress set without the lead's scored/needed")
                hist = [h for h in data["history.json"] if h["experiment"] == lead["id"]]
                self.assertEqual(p["scored_7d"], gain_7d(hist, "scored", build_day(data)), "scored_7d")
                self.assertEqual(p["collected_7d"], gain_7d(hist, "collected", build_day(data)), "collected_7d")

    def check_program_freshness(self, data, registry_path):
        """as_of/stale_after_hours come from the member that goes stale first, so the page's
        stale(as_of, stale_after_hours) on the program is true exactly when any member is stale."""
        want = self.expected_programs(data, registry_path)
        built_at = parse_utc(data["build.json"][0]["built_at"])
        for p in data["programs.json"]:
            w = want[p["id"]]
            if not w["members"]:
                continue
            with self.subTest(program=p["id"]):
                self.assertIn((p["as_of"], p["stale_after_hours"]), w["pairs"],
                              "as_of/stale_after_hours not taken together from the soonest-stale member")
                deadline = stale_deadline(p)
                self.assertEqual(deadline, w["soonest"])
                probes = {built_at}
                for m in w["members"]:
                    if m["as_of"] is not None:
                        d = stale_deadline(m)
                        probes |= {d - timedelta(seconds=1), d + timedelta(seconds=1)}
                for t in sorted(probes):
                    any_member = any(t > stale_deadline(m) for m in w["members"])
                    self.assertEqual(t > deadline, any_member, f"at {t.isoformat()}: program stale != any member stale")

    def check_summary(self, data, registry_path):
        rows = data["experiments.json"]
        self.assertEqual(len(data["summary.json"]), 1, "summary.json must hold exactly one row")
        s = data["summary.json"][0]
        closed = [e for e in rows if e["group"] == "closed"]
        live = [e for e in rows if e["group"] in ("live", "server")]
        progs = data["programs.json"]
        self.assertEqual(s["proven_live"], sum(e["outcome"] == "worked" for e in live), "proven_live")
        self.assertEqual(s["live_tests"], len(live), "live_tests")
        self.assertEqual(s["programs"], len(progs), "programs")
        self.assertEqual(s["ideas_tested"], sum(e["outcome"] != "not_an_idea" for e in closed),
                         "ideas_tested = closed rows whose outcome is not not_an_idea")
        for k in ("worked", "didnt_work", "no_answer"):
            self.assertEqual(s[k], sum(e["outcome"] == k for e in closed), k)
        self.assertEqual(s["checks"], sum(e["outcome"] == "not_an_idea" for e in closed), "checks")
        self.assertEqual(s["issues"], sum(p["status"] == "issue" for p in progs), "issues")
        dates = [h["date"] for h in data["history.json"]]
        self.assertEqual(s["first_record_date"], min(dates) if dates else None, "first_record_date")
        self.assertEqual(s["built_at"], data["build.json"][0]["built_at"], "built_at")
        # the program with the earliest next_verdict_date (not its lead's verdict_date) on/after today
        today = build_day(data)
        ahead = [p for p in progs if p["next_verdict_date"] is not None and p["next_verdict_date"] >= today]
        if not ahead:
            for k in ("next_verdict_date", "next_verdict_program", "next_verdict_what", "next_verdict_basis"):
                self.assertIsNone(s[k], f"{k} set though no program has a next verdict on/after {today}")
            return
        first = min(p["next_verdict_date"] for p in ahead)
        self.assertEqual(s["next_verdict_date"], first,
                         f"next verdict must be the earliest program next_verdict_date on/after {today}")
        picks = {(p["name"], p["next_verdict_what"], p["next_verdict_basis"])
                 for p in ahead if p["next_verdict_date"] == first}
        self.assertIn((s["next_verdict_program"], s["next_verdict_what"], s["next_verdict_basis"]), picks,
                      "next_verdict_program/_what/_basis must be that program's name and next_verdict_what/_basis")


# ------------------------------------------------------------------ real-data build
class RealDataBuild(OutputChecks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(BUILDER):
            raise unittest.SkipTest(f"builder not present at {BUILDER}")
        cls.tmp = tempfile.mkdtemp(prefix="kod-status-real-")
        cls.out = os.path.join(cls.tmp, "out")
        os.makedirs(cls.out)
        cls.proc = run_builder(cls.out)
        cls.data = load_out(cls.out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.proc.returncode, 0, f"builder failed:\n{self.proc.stderr[-3000:]}")

    def exp(self, ids, name_pat=None):
        e = find_exp(self.data["experiments.json"], ids, name_pat)
        self.assertIsNotNone(e, f"no experiment row for {ids}")
        return e

    # (b) schema
    def test_schema_all_datasets(self):
        self.check_schema(self.data, self.out)

    def test_semantics_and_staleness(self):
        self.check_semantics(self.data)

    def test_real_as_of_never_null(self):
        for e in self.data["experiments.json"]:
            self.assertIsNotNone(e["as_of"], f"{e['id']} has no as_of on real data")

    def test_build_row(self):
        b = self.data["build.json"][0]
        self.assertEqual(b["kod_commit"], git(KOD, "rev-parse", REF).strip())
        pairs = dict(p.strip().split("=", 1) for p in b["backups_commits"].split(";") if p.strip())
        self.assertIn("main", {k.replace("origin/", "") for k in pairs})
        for br, sha in pairs.items():
            full = git(BACKUPS, "rev-parse", "origin/" + br.replace("origin/", "")).strip()
            self.assertTrue(full.startswith(sha) and len(sha) >= 7, f"{br}={sha} != {full}")
        if os.path.exists(REGISTRY):
            self.assertEqual(b["registry_entries"], len(registry_entries()))

    def test_every_registry_entry_has_a_row(self):
        if not os.path.exists(REGISTRY):
            self.skipTest("registry file not present")
        ids = {e["id"] for e in self.data["experiments.json"]}
        missing = [e["id"] for e in registry_entries() if e["id"] not in ids]
        self.assertEqual(missing, [], "registry entries without an experiments.json row")

    # (a) real data, recomputed independently
    def test_llm_arm_counts(self):
        want = expected_llm()
        e = self.exp(["LLM_ARM_v1"], r"LLM.*arm")
        self.assertEqual(e["collected"], want["collected"], "LLM calls made")
        self.assertEqual(e["scored"], want["scored"], "LLM BASE5-scored calls")
        self.assertEqual(e["needed"], want["needed"])
        self.assertLessEqual(abs((parse_utc(e["as_of"]) - want["as_of"]).total_seconds()), 120,
                             "LLM as_of should be the newest call (called_at)")

    def test_speculation_sets_sealed(self):
        want = expected_spec()
        rows = {m: find_exp(self.data["experiments.json"], [f"SPEC_REGISTER_{m}"]) for m in ("US", "IDX", "CRYPTO")}
        if all(rows.values()):
            for m, e in rows.items():
                with self.subTest(market=m):
                    self.assertEqual(e["collected"], want[m]["collected"], f"{m} sets sealed")
                    self.assertEqual(e["scored"], want[m]["scored"], f"{m} paired BASE5")
        else:  # a single pooled register row
            e = self.exp(["SPEC_REGISTER", "SPECULATION_REGISTER_v1"], r"speculation register")
            self.assertEqual(e["collected"], want["ALL"])

    def test_learner_v2_2_forecasts(self):
        want = expected_learners()["v2_2"]
        e = self.exp(["LEARNER_v2_2", "LEARNER_v2"], r"LEARNER v2\.2")
        self.assertEqual(e["collected"], want["collected"])
        self.assertEqual(parse_utc(e["as_of"]), want["as_of"])

    def test_learner_v2_4_forecasts(self):
        want = expected_learners()["v2_4"]
        e = self.exp(["LEARNER_v2_4"], r"LEARNER v2\.4")
        self.assertEqual(e["collected"], want["collected"])
        self.assertEqual(parse_utc(e["as_of"]), want["as_of"])

    def test_paper_book(self):
        want = expected_paper_book()
        e = self.exp(["PAPER_BOOK_v1"], r"paper book")
        self.assertEqual(e["collected"], want["collected"], "spikes planned")
        self.assertEqual(e["scored"], want["scored"], "trades closed")
        self.assertEqual(e["needed"], want["needed"])

    def _server_row(self, ids, pats):
        for s in self.data["server.json"]:
            if s["study"] in ids:
                return s
        for s in self.data["server.json"]:
            hay = f"{s['study']} {s['name']} {s['source']}".lower()
            if any(p in hay for p in pats):
                return s
        self.fail(f"no server.json row for {ids}")

    def test_research_r2_from_health(self):
        want = expected_server()["r2"]
        s = self._server_row({"srv:research_r2", "research-r2-20261105T181200Z"}, ["research-r2", "research_r2"])
        self.assertAlmostEqual(s["coverage"], want["coverage"], places=4)
        self.assertEqual(s["captured"], want["captured"])
        built_at = parse_utc(self.data["build.json"][0]["built_at"])
        age_h = (built_at - want["as_of"]).total_seconds() / 3600
        if age_h > s["stale_after_hours"]:
            self.assertEqual(s["status"], "UNKNOWN", "stale R2 must read UNKNOWN")
        else:
            self.assertIn(s["status"], {want["status"], want["raw_status"]})
        self.assertEqual(parse_utc(s["as_of"]), want["as_of"])

    def test_timing_cohort_captured(self):
        want = expected_server()["cohort"]
        s = self._server_row({"srv:timing_capture_30", "main"}, ["timing_capture", "main:health", "cohort"])
        self.assertEqual(s["captured"], want["captured"])
        self.assertEqual(s["planned"], want["planned"])
        e = find_exp(self.data["experiments.json"], ["srv:timing_capture_30"])
        if e is not None:
            self.assertEqual(e["collected"], want["captured"])
            self.assertEqual(e["needed"], want["planned"])

    def test_server_history_from_commits(self):
        rows = self.data["server_history.json"]
        self.assertTrue(rows, "server_history.json is empty")
        r2_commits = len(git(BACKUPS, "log", "--format=%H", "origin/research-r2-20261105T181200Z").split())
        r2_rows = [r for r in rows if "r2" in r["study"].lower() and "capacity" not in r["study"].lower()]
        self.assertTrue(0 < len(r2_rows) <= r2_commits, f"{len(r2_rows)} R2 history rows vs {r2_commits} commits")

    def test_events_cover_known_halt(self):
        evs = self.data["events.json"]
        self.assertTrue(any(e["kind"] == "incident" for e in evs), "no incident events at all")
        self.assertTrue(any(e["kind"] == "decision" and "early_entry_closed" in e["source"] for e in evs),
                        "decision handoff/decisions/2026-11-04_early_entry_closed.md not an event")

    # owner's view on the real registry
    def test_owner_view_experiment_fields(self):
        self.check_registry_text(self.data, REGISTRY)
        self.check_issue_field(self.data)
        self.check_verdict_dates(self.data, REGISTRY)

    def test_owner_view_programs_and_summary(self):
        self.check_programs(self.data, REGISTRY)
        self.check_program_freshness(self.data, REGISTRY)
        self.check_summary(self.data, REGISTRY)

    def test_plumbing_rows_have_no_verdict(self):
        entries, _ = registry_doc(REGISTRY)
        reg = {e["id"]: e for e in entries}
        flagged = {i for i, e in reg.items() if e.get("plumbing")}
        if not flagged:
            self.skipTest("the registry marks no entry as plumbing")
        rows = {e["id"]: e for e in self.data["experiments.json"]}
        for i in reg:
            with self.subTest(experiment=i):
                self.assertIs(rows[i]["plumbing"], i in flagged, "plumbing must be the registry flag")
                if i in flagged:
                    self.assertEqual((rows[i]["verdict_date"], rows[i]["verdict_basis"]), (None, None))
        # the rule bites: a plumbing row has an end that would otherwise be its verdict date
        dated = [i for i in flagged if rows[i]["projected_date"] or reg[i].get("fixed_end")]
        self.assertTrue(dated, "no plumbing row has a fixed end or projected_date, so nothing is exempted")

    def test_next_verdict_may_come_from_a_non_lead_member(self):
        """On today's data the next verdict (2026-11-25, "US spikes vs look-alikes") is a non-lead
        member of paper_trading; skips when data drift ends that."""
        today = build_day(self.data)
        rows = {e["id"]: e for e in self.data["experiments.json"]}
        cases = [p for p in self.data["programs.json"] if p["next_verdict_date"] is not None
                 and p["next_verdict_what"] != p["lead_short"]]
        if not cases:
            self.skipTest("no program's next verdict comes from a non-lead member on today's data")
        for p in cases:
            lead = rows[p["lead"]]
            with self.subTest(program=p["id"], lead=p["lead"]):
                self.assertEqual((p["verdict_date"], p["verdict_basis"]), (lead["verdict_date"], lead["verdict_basis"]),
                                 "verdict_date/_basis stay the lead's")
                self.assertTrue(lead["verdict_date"] is None or lead["verdict_date"] < today
                                or lead["verdict_date"] >= p["next_verdict_date"],  # equal: an earlier-listed tie
                                "a non-lead next verdict must not come after the lead's own upcoming verdict")
        self.check_summary(self.data, REGISTRY)

    def test_learner_v3_evaluations_absence_is_not_a_gap(self):
        bad = [g for g in self.data["gaps.json"] if g["kind"] in ("SOURCE_MISSING", "READ_ERROR")
               and g["path"].rstrip("/").endswith("learner_v3_evaluations.jsonl")]
        self.assertEqual(bad, [], "absent learner_v3_evaluations.jsonl means 0 frozen, not a gap")


# ------------------------------------------------------------ failure-mode fixture
MISSING = "idx-signals/paper/premove_shadow.jsonl"
CORRUPT = "idx-signals/paper/paper_account.jsonl"
NEWDIR = "idx-signals/research/ZZ_UNREGISTERED_TEST_v1"


def make_fixture(root):
    """git init a repo borrowing KOD objects; commit one synthetic change set."""
    repo = os.path.join(root, "kod-fixture")
    subprocess.run(["git", "init", "-q", repo], check=True)
    objects = git(KOD, "rev-parse", "--path-format=absolute", "--git-common-dir").strip() + "/objects"
    with open(os.path.join(repo, ".git", "objects", "info", "alternates"), "w") as f:
        f.write(objects + "\n")
    head = git(KOD, "rev-parse", REF).strip()
    env = dict(os.environ, GIT_INDEX_FILE=os.path.join(root, "fixture.index"),
               GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")

    def g(*a, inp=None):
        return subprocess.run(["git", "-C", repo, *a], input=inp, capture_output=True, check=True, env=env).stdout

    def blob(data):
        return g("hash-object", "-w", "--stdin", inp=data).decode().strip()

    g("read-tree", head)
    g("update-index", "--force-remove", MISSING)
    original = g("show", f"{head}:{CORRUPT}")
    corrupt = blob(original + b"{this line is not json\n")
    protocol = blob(b"# Synthetic fixture study\n\nNot in the registry on purpose.\n")
    g("update-index", "--cacheinfo", f"100644,{corrupt},{CORRUPT}")
    g("update-index", "--add", "--cacheinfo", f"100644,{protocol},{NEWDIR}/PROTOCOL.md")
    tree = g("write-tree").decode().strip()
    commit = g("commit-tree", tree, "-p", head, "-m", "fixture: missing source, corrupt line, unregistered study").decode().strip()
    g("update-ref", "refs/heads/fixture", commit)
    g("update-ref", f"refs/remotes/{REF}", commit)  # same name as the real default ref
    return repo


class FailureModes(OutputChecks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(BUILDER):
            raise unittest.SkipTest(f"builder not present at {BUILDER}")
        if not os.path.exists(REGISTRY):
            raise unittest.SkipTest(f"registry not present at {REGISTRY}")
        cls.tmp = tempfile.mkdtemp(prefix="kod-status-fixture-")
        cls.repo = make_fixture(cls.tmp)
        cls.registry = os.path.join(cls.tmp, "registry.json")
        shutil.copy(REGISTRY, cls.registry)
        cls.out = os.path.join(cls.tmp, "out")
        os.makedirs(cls.out)
        cls.proc = run_builder(cls.out, kod=cls.repo, ref=REF, registry=cls.registry)
        cls.data = load_out(cls.out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_no_crash_and_all_files(self):
        self.assertEqual(self.proc.returncode, 0, f"builder crashed:\n{self.proc.stderr[-3000:]}")
        self.check_schema(self.data, self.out)
        self.check_semantics(self.data, allow_null_as_of_when_unknown=True)

    def test_missing_source_gives_source_missing_and_unknown(self):
        gaps = [g for g in self.data["gaps.json"] if g["kind"] == "SOURCE_MISSING" and MISSING in g["path"]]
        self.assertTrue(gaps, f"no SOURCE_MISSING row for {MISSING}")
        hit = [e for e in self.data["experiments.json"] if MISSING in e["source"]]
        self.assertTrue(hit, f"no experiment cites {MISSING}")
        for e in hit:
            self.assertEqual(e["state"], "UNKNOWN", f"{e['id']} lost its source but reads {e['state']}")

    def test_rest_still_builds(self):
        ids = {e["id"] for e in self.data["experiments.json"]}
        missing = [e["id"] for e in registry_entries(self.registry) if e["id"] not in ids]
        self.assertEqual(missing, [], "registry entries dropped after one source vanished")
        e = find_exp(self.data["experiments.json"], ["LLM_ARM_v1"], r"LLM.*arm")
        self.assertIsNotNone(e)
        self.assertEqual(e["collected"], expected_llm()["collected"], "unrelated experiment changed")
        self.assertTrue(any(x["state"] != "UNKNOWN" for x in self.data["experiments.json"]))

    def test_corrupt_line_gives_read_error(self):
        gaps = [g for g in self.data["gaps.json"] if g["kind"] == "READ_ERROR" and CORRUPT in g["path"]]
        self.assertTrue(gaps, f"no READ_ERROR row for the corrupt line in {CORRUPT}")

    def test_unregistered_research_folder(self):
        gaps = [g for g in self.data["gaps.json"] if g["kind"] == "NOT_ON_DASHBOARD"
                and "ZZ_UNREGISTERED_TEST_v1" in g["path"]]
        self.assertTrue(gaps, "unregistered research folder not reported NOT_ON_DASHBOARD")

    def test_fixture_commit_reported(self):
        self.assertEqual(self.data["build.json"][0]["kod_commit"],
                         git(self.repo, "rev-parse", "refs/heads/fixture").strip())

    def test_broken_sources_give_plain_issues(self):
        hit = [e for e in self.data["experiments.json"] if MISSING in e["source"] or CORRUPT in e["source"]]
        self.assertTrue([e for e in hit if e["state"] in BAD], "no broken-source row turned bad")
        self.check_issue_field(self.data)
        self.check_verdict_dates(self.data, self.registry)
        self.check_summary(self.data, self.registry)


# ---------------------------------------------- owner's view fixture (programs, summary)
# A copy of the real registry plus programs and plain text, built against the real data.
# The groupings are chosen so that, on today's data, each lead rule decides at least one
# program and gives a different answer from the rules below it:
#   ai_judge        earliest verdict_date (not the first member, not the highest fraction)
#   paper_trading   highest fraction (no member has a verdict date; the first has no fraction)
#   accounts        first member (no verdict dates, no fractions); its 2nd member is the one
#                   with an issue, so the program's issue is not simply the first member's
#   insider_signals registry lead (the last member, where the rules would pick the first)
#   timing_lab      registry lead (its two capture members keep the real registry's
#                   "plumbing": true, so they have no verdict date and the override now
#                   agrees with the earliest-verdict rule)
# Every check recomputes from the build's own rows, so data drift cannot make a check wrong;
# test_fixture_exercises_each_rule says (as skips) when drift stops a rule being exercised.
OWNER_PROGRAMS = [
    {"id": "forecaster", "name": "Forecasters", "order": 1,
     "question": "Can our forecasts call next week's winners better than chance?"},
    {"id": "paper_trading", "name": "Paper trading", "order": 2,
     "question": "Would the trades we plan make money on paper?"},
    {"id": "ai_judge", "name": "AI judge", "order": 3,
     "question": "Does an AI pick the better trade more often than not?"},
    {"id": "insider_signals", "name": "Insider signals", "order": 4, "lead": "CATALYST_DOCUMENT_CLASS",
     "question": "Do company filings point to stocks that move?"},
    {"id": "timing_lab", "name": "Entry-timing lab", "order": 5, "lead": "srv:research_r2",
     "question": "Does buying at a better minute change the result?"},
    {"id": "accounts", "name": "Practice accounts", "order": 6,
     "question": "Do the practice accounts follow their own rules every day?"},
]
OWNER_MEMBERS = {
    "ai_judge": ["LLM_ARM_v1", "SPEC_REGISTER_IDX", "SPEC_REGISTER_CRYPTO"],
    "forecaster": ["SPEC_REGISTER_US", "LEARNER_v2_2", "LEARNER_v2_4", "PREMOVE_SHADOW_v1", "trend_core_paper"],
    "paper_trading": ["CALL_CERT", "PAPER_BOOK_v1", "PAPER_ACCOUNT_v1_BASE"],
    "accounts": ["PAPER_ACCOUNT_v1_FIXED5", "CRYPTO_ACCOUNT_v1"],
    "insider_signals": ["CATALYST_SEC13D", "CATALYST_SEC13D_V2", "CATALYST_DILUTION_8K", "CATALYST_FORM4",
                        "CATALYST_FORM4_SHARP", "CATALYST_DOCUMENT_CLASS"],
    "timing_lab": ["srv:timing_capture_30", "srv:supplement_30m", "srv:research_r2"],
}
NO_TEXT = "trend_core_paper"  # in a program, but no short/ceo_line/unit: those must read null
CLOSED_OUTCOMES = ["worked", "didnt_work", "didnt_work", "no_answer", "not_an_idea",
                   "didnt_work", "no_answer", "not_an_idea"]  # the rest of the closed rows get none
# The second build runs "4 days later" at 03:00 UTC (10:00 WIB, the same calendar day in both).
FUTURE_NOW = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%dT03:00:00Z")
LIVE_WORKED = "PAPER_BOOK_v1"  # the future build marks this live test as worked


def owner_registry(path, override_timing_lead=True, live_worked=None):
    with open(REGISTRY, encoding="utf-8") as f:
        reg = json.load(f)
    programs = [dict(p) for p in OWNER_PROGRAMS]
    if not override_timing_lead:
        for p in programs:
            if p["id"] == "timing_lab":
                p.pop("lead")
    reg["programs"] = programs
    where = {m: pid for pid, ms in OWNER_MEMBERS.items() for m in ms}
    closed_seen = 0
    for e in reg["experiments"]:
        for k in REGISTRY_TEXT:  # start from the real registry without its own owner's-view text
            e.pop(k, None)
        if e["group"] in ("live", "server"):
            e["program"] = where[e["id"]]
            if e["id"] != NO_TEXT:
                e["short"] = "Test " + str(len(e["id"]) % 7)
                e["ceo_line"] = "Tells us whether this idea earns more than it costs."
                e["unit"] = "results judged"
            if e["id"] == live_worked:
                e["outcome"] = "worked"
        elif closed_seen < len(CLOSED_OUTCOMES):
            e["outcome"] = CLOSED_OUTCOMES[closed_seen]
            e["short"] = "Old idea " + str(closed_seen)
            e["lesson"] = "It looked good on past data but not on data it had never seen."
            closed_seen += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
    return path


class OwnerView(OutputChecks, unittest.TestCase):
    """programs.json, summary.json and the new experiments.json fields, against the contract."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(BUILDER):
            raise unittest.SkipTest(f"builder not present at {BUILDER}")
        if not os.path.exists(REGISTRY):
            raise unittest.SkipTest(f"registry not present at {REGISTRY}")
        cls.tmp = tempfile.mkdtemp(prefix="kod-status-owner-")
        cls.registry = owner_registry(os.path.join(cls.tmp, "registry.json"))
        cls.out = os.path.join(cls.tmp, "out")
        os.makedirs(cls.out)
        cls.proc = run_builder(cls.out, registry=cls.registry)
        cls.data = load_out(cls.out)
        # a build "4 days later" with no timing-lab override (and one live test marked worked)
        cls.registry2 = owner_registry(os.path.join(cls.tmp, "registry2.json"),
                                       override_timing_lead=False, live_worked=LIVE_WORKED)
        cls.out2 = os.path.join(cls.tmp, "out2")
        os.makedirs(cls.out2)
        cls.proc2 = run_builder(cls.out2, registry=cls.registry2, now=FUTURE_NOW)
        cls.data2 = load_out(cls.out2)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.proc.returncode, 0, f"builder failed:\n{self.proc.stderr[-3000:]}")
        self.assertEqual(self.proc2.returncode, 0, f"builder (--now) failed:\n{self.proc2.stderr[-3000:]}")

    def program(self, data, pid):
        hits = [p for p in data["programs.json"] if p["id"] == pid]
        self.assertEqual(len(hits), 1, f"no single programs.json row for {pid}")
        return hits[0]

    def test_schema(self):
        self.check_schema(self.data, self.out)
        self.check_schema(self.data2, self.out2)

    # experiments.json: new fields
    def test_registry_text_copied_null_where_not_set(self):
        self.check_registry_text(self.data, self.registry)
        row = find_exp(self.data["experiments.json"], [NO_TEXT])
        self.assertEqual((row["program"], row["ceo_line"], row["unit"]), ("forecaster", None, None))
        closed = [e for e in self.data["experiments.json"] if e["group"] == "closed"]
        self.assertTrue([e for e in closed if e["outcome"] is None and e["lesson"] is None],
                        "fixture should leave some closed rows without an outcome")
        live = [e for e in self.data["experiments.json"] if e["group"] != "closed"]
        self.assertTrue(all(e["outcome"] is None and e["lesson"] is None for e in live))

    def test_short_null_where_not_set(self):
        self.check_short_default(self.data, self.registry)

    def test_issue_field(self):
        self.check_issue_field(self.data)
        self.check_issue_field(self.data2)

    def test_verdict_date_and_basis(self):
        self.check_verdict_dates(self.data, self.registry)
        self.check_verdict_dates(self.data2, self.registry2)
        rows = {e["id"]: e for e in self.data["experiments.json"]}
        cap = rows["srv:timing_capture_30"]
        entry = {e["id"]: e for e in registry_entries(self.registry)}["srv:timing_capture_30"]
        self.assertTrue(entry.get("fixed_end") and entry.get("plumbing"), "fixture: a plumbing check with a fixed end")
        self.assertIs(cap["plumbing"], True)
        self.assertEqual((cap["verdict_date"], cap["verdict_basis"]), (None, None),
                         "a plumbing check's fixed end is not a verdict date")

    # programs.json
    def test_program_rows(self):
        self.check_programs(self.data, self.registry)
        self.check_programs(self.data2, self.registry2)

    def test_lead_registry_override(self):
        for pid, lead in (("insider_signals", "CATALYST_DOCUMENT_CLASS"), ("timing_lab", "srv:research_r2")):
            with self.subTest(program=pid):
                self.assertEqual(self.program(self.data, pid)["lead"], lead)
        # without the override the timing lab follows the earliest-verdict rule instead
        want = self.expected_programs(self.data2, self.registry2)["timing_lab"]
        self.assertIn(self.program(self.data2, "timing_lab")["lead"], want["leads"])
        self.assertEqual(want["rule"], "earliest")

    def test_lead_automatic_rules(self):
        want = self.expected_programs(self.data, self.registry)
        for p in self.data["programs.json"]:
            w = want[p["id"]]
            with self.subTest(program=p["id"], rule=w["rule"]):
                self.assertIn(p["lead"], w["leads"])

    def test_fixture_exercises_each_rule(self):
        """Skips (does not fail) when data drift stops a rule from deciding a program by itself."""
        want = self.expected_programs(self.data, self.registry)

        def fallback(members, rule):
            rest = {"earliest": "fraction", "fraction": "first"}.get(rule)
            if rest == "fraction":
                f = [m for m in members if m["fraction"] is not None]
                if f:
                    top = max(m["fraction"] for m in f)
                    return {m["id"] for m in f if m["fraction"] == top}
            return {members[0]["id"]}

        cases = {"earliest": "ai_judge", "fraction": "paper_trading", "first": "accounts",
                 "override": "insider_signals"}
        for rule, pid in cases.items():
            with self.subTest(rule=rule, program=pid):
                w = want[pid]
                if w["rule"] != rule:
                    self.skipTest(f"{pid} is now decided by '{w['rule']}', not '{rule}'")
                if rule == "override":
                    auto = lead_rule({}, w["members"])[0]
                    first_auto = next(m["id"] for m in w["members"] if m["id"] in auto)  # registry order
                    if w["leads"] == {first_auto}:
                        self.skipTest("the override now equals the automatic lead")
                elif rule != "first" and w["leads"] <= fallback(w["members"], rule):
                    self.skipTest(f"'{rule}' now agrees with the lower rule")
                self.assertIn(self.program(self.data, pid)["lead"], w["leads"])
        states = {p["status"] for p in self.data["programs.json"]}
        for status in ("running", "issue"):
            with self.subTest(status=status):
                if status not in states:
                    self.skipTest(f"no program is '{status}' on today's data")
        accounts = want["accounts"]
        with self.subTest(case="issue from a non-first member"):
            if accounts["status"] != "issue" or accounts["members"][0]["state"] in BAD:
                self.skipTest("accounts no longer has an issue only on a later member")
            self.assertEqual(self.program(self.data, "accounts")["issue"], accounts["issue"])

    def test_program_progress_is_lead_scored_over_needed(self):
        rows = {e["id"]: e for e in self.data["experiments.json"]}
        checked = 0
        for p in self.data["programs.json"]:
            lead = rows[p["lead"]]
            with self.subTest(program=p["id"], lead=p["lead"]):
                if lead["scored"] is not None and lead["needed"]:
                    self.assertAlmostEqual(p["progress"], min(1.0, lead["scored"] / lead["needed"]), places=3)
                    checked += 1
                else:
                    self.assertIsNone(p["progress"])
        self.assertGreater(checked, 0, "no program lead has scored/needed")

    def test_program_status_rule(self):
        want = self.expected_programs(self.data, self.registry)
        for p in self.data["programs.json"]:
            with self.subTest(program=p["id"]):
                self.assertEqual((p["status"], p["issue"]), (want[p["id"]]["status"], want[p["id"]]["issue"]))
        # 4 days later every program has a member past its freshness limit (78 h or less)
        for p in self.data2["programs.json"]:
            with self.subTest(future=p["id"]):
                self.assertEqual(p["status"], "issue")
                self.assertTrue(p["issue"])

    def test_program_freshness_pairing(self):
        self.check_program_freshness(self.data, self.registry)
        self.check_program_freshness(self.data2, self.registry2)

    def test_program_7_day_gains(self):
        hist = self.data["history.json"]
        today = build_day(self.data)
        for p in self.data["programs.json"]:
            rows = [h for h in hist if h["experiment"] == p["lead"]]
            with self.subTest(program=p["id"], lead=p["lead"]):
                self.assertEqual(p["scored_7d"], gain_7d(rows, "scored", today))
                self.assertEqual(p["collected_7d"], gain_7d(rows, "collected", today))
                if p["scored_7d"] is not None:
                    self.assertGreaterEqual(p["scored_7d"], 0)

    # summary.json
    def test_summary_counts(self):
        self.check_summary(self.data, self.registry)
        s = self.data["summary.json"][0]
        closed = [e for e in self.data["experiments.json"] if e["group"] == "closed"]
        self.assertEqual(s["proven_live"], 0, "no live test is marked worked in this build")
        self.assertEqual(s["checks"], CLOSED_OUTCOMES.count("not_an_idea"))
        self.assertEqual(s["ideas_tested"], len(closed) - CLOSED_OUTCOMES.count("not_an_idea"),
                         "closed rows with no outcome yet still count as ideas tested")
        self.assertEqual((s["worked"], s["didnt_work"], s["no_answer"]),
                         tuple(CLOSED_OUTCOMES.count(k) for k in ("worked", "didnt_work", "no_answer")))
        self.assertEqual(s["programs"], len(OWNER_PROGRAMS))
        self.assertEqual(s["live_tests"], sum(len(m) for m in OWNER_MEMBERS.values()))

    def test_summary_proven_live_counts_live_worked(self):
        self.check_summary(self.data2, self.registry2)
        s = self.data2["summary.json"][0]
        self.assertEqual(s["proven_live"], 1, f"{LIVE_WORKED} is marked worked in this build")
        closed = [e for e in self.data2["experiments.json"] if e["group"] == "closed"]
        self.assertEqual(s["worked"], sum(e["outcome"] == "worked" for e in closed),
                         "a live 'worked' must not count as a closed idea that worked")

    def test_future_build_next_verdicts_not_before_build_day(self):
        """(Past dates on pinned days are NextVerdict's job; this guards the --now build.)"""
        today = build_day(self.data2)
        self.assertEqual(today, FUTURE_NOW[:10], "--now did not set the build day")
        for p in self.data2["programs.json"]:
            with self.subTest(program=p["id"]):
                if p["next_verdict_date"] is not None:
                    self.assertGreaterEqual(p["next_verdict_date"], today, "a passed member verdict was picked")
        s = self.data2["summary.json"][0]
        if s["next_verdict_date"] is not None:
            self.assertGreaterEqual(s["next_verdict_date"], today, "a passed verdict date was picked")
        self.check_summary(self.data2, self.registry2)


# ------------------------------------- next verdict and plumbing fixture (pinned dates)
# A copy of the real registry whose programs and member dates are all set here, so every
# expected value is known in advance. Each member gets a `fixed_end` (its verdict date unless
# it is plumbing) as a day offset from the build's WIB day, and the build runs with --now so
# that day is pinned. PREMOVE_SHADOW_v1 stays out (its reader supplies its own end date).
#   nv_decoy      lead (earliest member) at +15: the earliest *lead* verdict on/after the
#                 build day, i.e. what the old summary rule would pick
#   nv_past_only  members due yesterday and 5 days ago, plus a plumbing member at +3: no next
#   nv_lead_later registry lead at +30, a non-lead member at +10 (the summary's pick) and one
#                 at -3 (earlier, but past)
#   nv_tie        two members at +20; the lead is the later-listed one and sorts first by id,
#                 so only registry order picks the earlier-listed one
#   nv_plumbing   plumbing at +1 (as in the real registry) and +2 (flag added here to a test
#                 that is not plumbing for real), and a member at +40 whose flag is set false
# A second build runs exactly NV_LATER_DAYS later, when nv_lead_later's +10 member is due on
# the build day itself ("on or after" the build day).
NV_PROGRAMS = [
    {"id": "nv_decoy", "name": "Decoy", "order": 1, "question": "Is the lead's date the next verdict?"},
    {"id": "nv_past_only", "name": "Past only", "order": 2, "question": "Are passed dates skipped?"},
    {"id": "nv_lead_later", "name": "Lead later", "order": 3, "lead": "CATALYST_SEC13D",
     "question": "Can a non-lead member give the next verdict?"},
    {"id": "nv_tie", "name": "Tie", "order": 4, "lead": "LEARNER_v2_2",
     "question": "Does registry order break a tie?"},
    {"id": "nv_plumbing", "name": "Plumbing", "order": 5, "question": "Do plumbing checks stay out?"},
]
# id: (program, fixed_end in days from the build day, registry "plumbing" value or None for unset)
NV_MEMBERS = {
    "PAPER_BOOK_v1": ("nv_decoy", 15, None),
    "CALL_CERT": ("nv_decoy", 18, None),
    "PAPER_ACCOUNT_v1_BASE": ("nv_past_only", -1, None),
    "PAPER_ACCOUNT_v1_FIXED5": ("nv_past_only", -5, None),
    "CRYPTO_ACCOUNT_v1": ("nv_past_only", 3, True),
    "CATALYST_SEC13D": ("nv_lead_later", 30, None),
    "CATALYST_DILUTION_8K": ("nv_lead_later", -3, None),
    "CATALYST_FORM4": ("nv_lead_later", 10, None),
    "SPEC_REGISTER_US": ("nv_tie", 20, None),
    "LEARNER_v2_2": ("nv_tie", 20, None),
    "LEARNER_v2_4": ("nv_tie", 25, None),
    "srv:timing_capture_30": ("nv_plumbing", 1, True),
    "LLM_ARM_v1": ("nv_plumbing", 2, True),
    "srv:supplement_30m": ("nv_plumbing", 40, False),
}
NV_NOW = datetime.now(timezone.utc).replace(microsecond=0)
NV_LATER_DAYS = 10


def day_plus(day, days):
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def nv_short(exp_id):
    return "Test " + exp_id


def utc_text(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def next_verdict_registry(path, today):
    with open(REGISTRY, encoding="utf-8") as f:
        reg = json.load(f)
    reg["programs"] = [dict(p) for p in NV_PROGRAMS]
    for e in reg["experiments"]:
        for k in REGISTRY_TEXT + ("plumbing", "fixed_end"):  # every date and flag is set below
            e.pop(k, None)
        if e["group"] in ("live", "server"):
            e["short"] = nv_short(e["id"])
        if e["id"] in NV_MEMBERS:
            program, offset, plumbing = NV_MEMBERS[e["id"]]
            e["program"] = program
            e["fixed_end"] = day_plus(today, offset)
            if plumbing is not None:
                e["plumbing"] = plumbing
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
    return path


class NextVerdict(OutputChecks, unittest.TestCase):
    """plumbing rows, programs.json next_verdict_* and summary.json's next verdict, on pinned days."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(BUILDER):
            raise unittest.SkipTest(f"builder not present at {BUILDER}")
        if not os.path.exists(REGISTRY):
            raise unittest.SkipTest(f"registry not present at {REGISTRY}")
        missing = [i for i in NV_MEMBERS if i not in {e["id"] for e in registry_entries()}]
        if missing:
            raise unittest.SkipTest(f"fixture members no longer in the registry: {missing}")
        cls.tmp = tempfile.mkdtemp(prefix="kod-status-next-")
        cls.today = wib_day(NV_NOW)
        cls.registry = next_verdict_registry(os.path.join(cls.tmp, "registry.json"), cls.today)
        cls.out = os.path.join(cls.tmp, "out")
        os.makedirs(cls.out)
        cls.proc = run_builder(cls.out, registry=cls.registry, now=utc_text(NV_NOW))
        cls.data = load_out(cls.out)
        cls.out2 = os.path.join(cls.tmp, "out2")
        os.makedirs(cls.out2)
        cls.proc2 = run_builder(cls.out2, registry=cls.registry,
                                now=utc_text(NV_NOW + timedelta(days=NV_LATER_DAYS)))
        cls.data2 = load_out(cls.out2)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.proc.returncode, 0, f"builder failed:\n{self.proc.stderr[-3000:]}")
        self.assertEqual(self.proc2.returncode, 0, f"builder (later) failed:\n{self.proc2.stderr[-3000:]}")

    def day(self, offset):
        return day_plus(self.today, offset)

    def builds(self):
        return (("today", self.data), (f"+{NV_LATER_DAYS} days", self.data2))

    def program(self, data, pid):
        hits = [p for p in data["programs.json"] if p["id"] == pid]
        self.assertEqual(len(hits), 1, f"no single programs.json row for {pid}")
        return hits[0]

    def rows(self, data):
        return {e["id"]: e for e in data["experiments.json"]}

    @staticmethod
    def next_fields(p):
        return p["next_verdict_date"], p["next_verdict_basis"], p["next_verdict_what"]

    def test_build_days_pinned_and_schema(self):
        self.assertEqual(build_day(self.data), self.today, "--now did not set the build day")
        self.assertEqual(build_day(self.data2), self.day(NV_LATER_DAYS), "--now did not set the later build day")
        self.check_schema(self.data, self.out)
        self.check_schema(self.data2, self.out2)

    def test_shared_contract_checks(self):
        for label, data in self.builds():
            with self.subTest(build=label):
                self.check_verdict_dates(data, self.registry)
                self.check_programs(data, self.registry)
                self.check_summary(data, self.registry)

    def test_plumbing_rows_have_null_verdict(self):
        reg = {e["id"]: e for e in registry_entries(self.registry)}
        for label, data in self.builds():
            rows = self.rows(data)
            for eid in ("srv:timing_capture_30", "LLM_ARM_v1", "CRYPTO_ACCOUNT_v1"):
                with self.subTest(build=label, experiment=eid):
                    self.assertTrue(reg[eid]["fixed_end"])
                    self.assertIs(rows[eid]["plumbing"], True)
                    self.assertEqual((rows[eid]["verdict_date"], rows[eid]["verdict_basis"]), (None, None),
                                     "a plumbing check's fixed end is not a verdict date")
            # "plumbing": false set explicitly, and no key at all: both false, verdict = fixed end
            for eid, offset in (("srv:supplement_30m", 40), ("PAPER_BOOK_v1", 15)):
                with self.subTest(build=label, experiment=eid):
                    self.assertIs(rows[eid]["plumbing"], False)
                    self.assertEqual((rows[eid]["verdict_date"], rows[eid]["verdict_basis"]),
                                     (self.day(offset), "scheduled"))
            self.assertEqual(sorted(i for i, r in rows.items() if r["plumbing"]),
                             sorted(i for i, e in reg.items() if e.get("plumbing") is True))

    def test_program_next_verdict_from_non_lead_member(self):
        for label, data in self.builds():
            p = self.program(data, "nv_lead_later")
            with self.subTest(build=label):
                self.assertEqual(p["lead"], "CATALYST_SEC13D")
                self.assertEqual((p["verdict_date"], p["verdict_basis"]), (self.day(30), "scheduled"),
                                 "verdict_date/_basis stay the lead's")
                self.assertEqual(self.next_fields(p), (self.day(10), "scheduled", nv_short("CATALYST_FORM4")),
                                 "next verdict = the earlier non-lead member")
                self.assertNotEqual(p["next_verdict_what"], p["lead_short"])
            # where the lead is the earliest member, next and lead agree
            decoy = self.program(data, "nv_decoy")
            with self.subTest(build=label, program="nv_decoy"):
                self.assertEqual(decoy["lead"], "PAPER_BOOK_v1")
                self.assertEqual(self.next_fields(decoy), (self.day(15), "scheduled", decoy["lead_short"]))

    def test_program_next_verdict_ignores_past_dates(self):
        rows = self.rows(self.data)
        self.assertEqual(rows["CATALYST_DILUTION_8K"]["verdict_date"], self.day(-3), "fixture: a past member date")
        self.assertEqual(rows["PAPER_ACCOUNT_v1_BASE"]["verdict_date"], self.day(-1), "fixture: due yesterday")
        lead_later = self.program(self.data, "nv_lead_later")
        self.assertEqual(lead_later["next_verdict_date"], self.day(10), "a member due 3 days ago was picked")
        # only passed (and plumbing) dates: no next verdict, though the lead's own date is still shown
        past = self.program(self.data, "nv_past_only")
        self.assertEqual(self.next_fields(past), (None, None, None), "passed dates must leave next_verdict_* null")
        self.assertEqual(past["lead"], "PAPER_ACCOUNT_v1_FIXED5")
        self.assertEqual((past["verdict_date"], past["verdict_basis"]), (self.day(-5), "scheduled"))
        # 10 days later: the +10 member is due on the build day itself and still counts
        later = self.program(self.data2, "nv_lead_later")
        self.assertEqual(build_day(self.data2), self.day(10))
        self.assertEqual(self.next_fields(later), (self.day(10), "scheduled", nv_short("CATALYST_FORM4")),
                         "a member due on the build day is 'on or after' it")
        self.assertEqual(self.next_fields(self.program(self.data2, "nv_past_only")), (None, None, None))

    def test_program_next_verdict_tie_follows_registry_order(self):
        order = [e["id"] for e in registry_entries(self.registry)]
        first, second = "SPEC_REGISTER_US", "LEARNER_v2_2"
        self.assertLess(order.index(first), order.index(second), "fixture: tie members out of registry order")
        self.assertLess(second, first, "fixture: id order must disagree with registry order")
        for label, data in self.builds():
            p = self.program(data, "nv_tie")
            with self.subTest(build=label):
                self.assertEqual(p["lead"], second)
                rows = self.rows(data)
                self.assertEqual(rows[first]["verdict_date"], rows[second]["verdict_date"])
                self.assertEqual(self.next_fields(p), (self.day(20), "scheduled", nv_short(first)),
                                 "a tie goes to the member listed first in the registry")

    def test_summary_picks_earliest_program_next_verdict(self):
        s = self.data["summary.json"][0]
        self.assertEqual((s["next_verdict_date"], s["next_verdict_program"], s["next_verdict_what"],
                          s["next_verdict_basis"]),
                         (self.day(10), "Lead later", nv_short("CATALYST_FORM4"), "scheduled"))
        # the old rule (earliest lead verdict on/after today) would have picked nv_decoy instead
        leads_ahead = [p for p in self.data["programs.json"]
                       if p["verdict_date"] is not None and p["verdict_date"] >= self.today]
        self.assertEqual(min(leads_ahead, key=lambda p: p["verdict_date"])["id"], "nv_decoy",
                         "fixture no longer separates the old rule from the new one")
        # later build: the pick is due on the build day itself
        s2 = self.data2["summary.json"][0]
        self.assertEqual((s2["next_verdict_date"], s2["next_verdict_program"], s2["next_verdict_what"],
                          s2["next_verdict_basis"]),
                         (build_day(self.data2), "Lead later", nv_short("CATALYST_FORM4"), "scheduled"))


def expected_now():
    """Print the real-data values these tests expect right now."""
    llm, spec, lrn, pb, srv = expected_llm(), expected_spec(), expected_learners(), expected_paper_book(), expected_server()
    return {"LLM_ARM_v1": {**llm, "as_of": llm["as_of"].isoformat()},
            "speculation_sets": spec,
            "LEARNER_v2_2": {"collected": lrn["v2_2"]["collected"], "as_of": lrn["v2_2"]["as_of"].isoformat()},
            "LEARNER_v2_4": {"collected": lrn["v2_4"]["collected"], "as_of": lrn["v2_4"]["as_of"].isoformat()},
            "PAPER_BOOK_v1": pb,
            "research_r2": {**srv["r2"], "as_of": srv["r2"]["as_of"].isoformat()},
            "timing_cohort": {**srv["cohort"], "as_of": srv["cohort"]["as_of"].isoformat()}}


if __name__ == "__main__":
    if "--expected" in sys.argv:
        print(json.dumps(expected_now(), indent=1))
    else:
        unittest.main()

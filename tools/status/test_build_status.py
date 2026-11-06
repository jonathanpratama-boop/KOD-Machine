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
from datetime import date, datetime

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


def run_builder(out, kod=KOD, ref=REF, registry=None):
    cmd = [sys.executable, BUILDER, "--kod", kod, "--kod-ref", ref, "--backups", BACKUPS, "--out", out]
    if registry:
        cmd += ["--registry", registry]
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

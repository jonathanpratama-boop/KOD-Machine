"""Cross-consumer revision invariants and immutable planned evaluation decisions."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from idxsig import learner_evaluation as ev, paper, speculation, catalysts, learner2


def record(i, y=0, rev=None):
    return {"type": "RESOLUTION", "set_id": f"S{i}", "window": "W", "market": "US", "family": "F",
            "record_hash": f"r{i}", "resolved_at": "2026-01-01T00:00:00Z", "status": "RESOLVED",
            "cone": [{"id": "X", "outcome": y}], **({"revises": rev} if rev else {})}


class EffectiveOutcomes(unittest.TestCase):
    def test_all_consumers_and_asof(self):
        rows = [record(i) for i in range(20)]
        correction = {**rows[0], "record_hash": "fix", "revises": "r0", "resolved_at": "2026-02-01T00:00:00Z",
                      "cone": [{"id": "X", "outcome": True}]}
        rows.append(correction)
        self.assertEqual(speculation.running_prior("US", "X", rows), (0.05, 20))
        self.assertEqual(catalysts.running_prior("F", "X", rows), (0.05, 20))
        self.assertFalse(learner2.outcomes(rows, "2026-01-15T00:00:00Z")[("S0", "X")][0])
        self.assertTrue(learner2.outcomes(rows, "2026-03-01T00:00:00Z")[("S0", "X")][0])
        rows.append({**correction, "record_hash": "ungraded", "revises": "fix", "status": "UNRESOLVABLE",
                     "resolved_at": "2026-04-01T00:00:00Z", "cone": [{"id": "X", "outcome": True}]})
        self.assertEqual(speculation.running_prior("US", "X", rows)[1], 19)
        self.assertNotIn(("S0", "X"), learner2.outcomes(rows, "2026-05-01T00:00:00Z"))

    def test_namespaces_windows_ties_and_schema_revisions(self):
        one = {**record(0), "register": "spec-register-v1"}
        two = {**record(0), "register": "catalyst-register-v1", "record_hash": "other"}
        window = {**one, "window": "OTHER", "record_hash": "window"}
        fixed = {**one, "register": "spec-register-v1.1", "record_hash": "fixed", "revises": "r0",
                 "cone": [{"id": "X", "outcome": True}]}
        effective = paper.latest_resolutions([one, two, window, fixed])
        self.assertEqual(len(effective), 3)
        self.assertEqual(effective[paper.resolution_key(one)]["record_hash"], "fixed")
        self.assertEqual(effective[paper.resolution_key(two)]["record_hash"], "other")
        with self.assertRaisesRegex(ValueError, "ambiguous learner set id"):
            learner2.outcomes([one, two], ASOF)
        with self.assertRaises(ValueError):
            paper.latest_resolutions([one, {**two, "revises": "r0"}])

    def test_link_validation_and_idempotence(self):
        first = record(0)
        self.assertEqual(len(paper.latest_resolutions([first, dict(first)])), 1)
        for revision in [record(1, rev="r0"), {**first, "record_hash": "new"},
                         {**first, "record_hash": "new", "revises": "missing"},
                         {**first, "record_hash": "new", "revises": "r0", "market": "CRYPTO"}]:
            with self.assertRaises(ValueError):
                paper.latest_resolutions([first, revision])
        with self.assertRaises(ValueError):
            paper.latest_resolutions([{**first, "revises": "unknown"}])


# Small deterministic evaluator keeps these storage/invariant tests fast; the
# learner3 end-to-end test separately freezes and replays real bootstrap results.
PROTO = {"protocol_id": "test", "claim": {"looks": [2, 4], "z_min": [2, 2], "min_sessions": [2, 3]}}
ASOF = "2027-01-01T00:00:00Z"


def pairs(rows, forecasts, asof):
    effective = paper.latest_resolutions(rows, asof=asof)
    return [{"set_id": r["set_id"], "statement": "X", "session": r["session"], "resolved_at": r["resolved_at"],
             "y": r["cone"][0]["outcome"], "raw": 0.6, "bench": 0.5, "resolution_record_hash": r["record_hash"]}
            for r in effective.values() if r.get("cone")]


def score(ps, rule, seed=20261029):
    return {"n_pairs": len(ps), "n_sessions": len({p["session"] for p in ps}), "look": rule["looks"][0],
            "auc": 0.5, "auc_bench": 0.5, "se": 1.0, "z": 0.0, "verdict": "not shown (final)"}


def rows(n):
    return [{**record(i, i % 2), "session": f"day{i}", "resolved_at": f"2026-01-{i+1:02d}T00:00:00Z"} for i in range(n)]


class FrozenLooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "looks.jsonl"

    def freeze(self, rs):
        return ev.freeze(rs, [], ASOF, PROTO, "protohash", pairs, score, "X", path=self.path)

    def test_first_prefix_final_and_readonly_reporting(self):
        self.assertIsNone(ev.official(pairs(rows(5), [], ASOF), "protohash", ASOF, self.path, proto=PROTO, claim_fn=score)["look"])
        self.assertFalse(self.path.exists())
        saved = self.freeze(rows(5))
        self.assertEqual([x["result"]["n_pairs"] for x in saved], [2, 4])
        old = self.path.read_bytes()
        self.assertEqual(self.freeze(rows(8)), [])
        self.assertEqual(self.path.read_bytes(), old)
        st = ev.official(pairs(rows(8), [], ASOF), "protohash", ASOF, self.path, proto=PROTO, claim_fn=score)
        self.assertEqual(st["n_pairs"], 4)
        self.assertEqual(ev.verify(self.path, score, proto=PROTO, proto_sha="protohash"), [])

    def test_correction_links_review_without_replacing_original(self):
        rs = rows(4)
        saved = self.freeze(rs)
        original = self.path.read_bytes()
        changed = {**rs[0], "record_hash": "fix", "revises": "r0", "resolved_at": "2026-02-01T00:00:00Z",
                   "cone": [{"id": "X", "outcome": 1}]}
        reviews = self.freeze(rs + [changed])
        self.assertEqual(len(reviews), 2)
        self.assertTrue(all(r["type"] == ev.REVIEW for r in reviews))
        self.assertTrue(self.path.read_bytes().startswith(original))
        self.assertEqual(self.freeze(rs + [changed]), [])
        st = ev.official(pairs(rs+[changed], [], ASOF), "protohash", ASOF, self.path, proto=PROTO, claim_fn=score)
        self.assertIn("requires correction review", st["verdict"])
        self.assertEqual(st["evaluation_hash"], saved[-1]["record_hash"])
        self.assertEqual(ev.verify(self.path, score, proto=PROTO, proto_sha="protohash"), [])

    def test_official_rejects_hash_valid_protocol_verdict_and_prefix_forgery(self):
        import copy
        source = rows(5)
        event = self.freeze(source)[0]
        for kind in ("verdict", "rule", "later_prefix"):
            with self.subTest(kind=kind):
                body = copy.deepcopy({k: v for k, v in event.items() if k not in ("record_hash", "prev_hash")})
                if kind == "verdict":
                    body["result"]["verdict"] = "SKILL"
                elif kind == "rule":
                    body["rule"]["z_min"] = [0]
                else:
                    later = pairs(source[:3], [], ASOF)
                    body.update(pairs=later, pairs_sha256=ev.digest(later),
                                result=ev._result(later, PROTO, 0, score, 20261029),
                                source_prefix={"count": 3, "sha256": ev.digest(source[:3]),
                                               "registers": ev._source_manifest(source[:3])})
                forged = self.path.with_name(kind + ".jsonl")
                paper.append([body], path=forged)
                self.assertEqual(paper.verify_chain(forged), [])
                with self.assertRaisesRegex(ValueError, "invalid evaluation ledger"):
                    ev.official(pairs(source, [], ASOF), "protohash", ASOF, forged,
                                proto=PROTO, claim_fn=score, records=source, forecasts=[], pair_fn=pairs, headline="X")

    def test_source_prefix_replay_survives_growth_of_first_register(self):
        first = {"type": "CATALYST_SET", "register": "catalyst-register-v1", "set_id": "CAT-0"}
        rs = [{**r, "register": "spec-register-v1"} for r in rows(4)]
        source = [first, *rs]
        self.freeze(source)
        grown = [first, {**first, "set_id": "CAT-1"}, *rs]
        opts = dict(records=grown, forecasts=[], pair_fn=pairs, headline="X")
        self.assertEqual(ev.verify(self.path, score, proto=PROTO, proto_sha="protohash", **opts), [])
        grown[-1] = {**grown[-1], "cone": [{"id": "X", "outcome": 123}]}
        self.assertTrue(ev.verify(self.path, score, proto=PROTO, proto_sha="protohash", **opts))

    def test_first_freeze_records_a_later_correction_assessment(self):
        rs = rows(4)
        changed = {**rs[0], "record_hash": "fix", "revises": "r0", "resolved_at": "2026-02-01T00:00:00Z",
                   "cone": [{"id": "X", "outcome": 1}]}
        saved = self.freeze(rs + [changed])
        self.assertEqual([r["type"] for r in saved], [ev.TYPE, ev.TYPE, ev.REVIEW, ev.REVIEW])
        self.assertEqual(saved[-1]["changes"][0]["current"]["resolution_record_hash"], "fix")
        self.assertEqual(self.freeze(rs + [changed]), [])
        self.assertEqual(ev.verify(self.path, score, proto=PROTO, proto_sha="protohash"), [])

    def test_historical_cutoff_cannot_backdate_the_recording(self):
        cutoff = "2026-02-01T00:00:00Z"
        recorded = "2026-10-30T12:00:00Z"
        with patch.object(ev, "utc_stamp", return_value=recorded):
            saved = ev.freeze(rows(4), [], cutoff, PROTO, "protohash", pairs, score, "X", path=self.path)
        self.assertTrue(all(r["frozen_at"] == recorded and r["cutoff"] == cutoff for r in saved))
        self.assertIsNone(ev.official(pairs(rows(4), [], cutoff), "protohash", cutoff, self.path, proto=PROTO, claim_fn=score)["look"])

    def test_concurrent_freeze_is_exactly_once(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.freeze(rows(5)), range(4)))
        self.assertEqual(len(paper.ledger_lines(self.path)), 2)
        self.assertEqual(ev.verify(self.path, score, proto=PROTO, proto_sha="protohash"), [])

    def test_min_sessions_uses_first_eligible_prefix(self):
        rs = rows(5)
        rs[1]["session"] = rs[0]["session"]
        saved = self.freeze(rs)
        self.assertEqual(saved[0]["result"]["n_pairs"], 3)
        self.assertEqual(saved[0]["source_prefix"]["count"], 3)

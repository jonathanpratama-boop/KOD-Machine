"""Offline replay regressions against preserved records and disposable corruption copies.

No fixture is a new forecast. Corruption tests modify only temporary copies of the
repository ledger; the real immutable archive must remain byte-for-byte unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from kod.workstation.replay import ReplayArchive, ReplayUnavailable, _available

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'var' / 'kod.db'
ZEAL = 'KOD-R-ZEAL-20250312'
OPEN = '2026-10-08T12:44:07Z'
CLOSED = '2026-10-08T12:44:16Z'
HISTORICAL = '2025-03-11T16:00:00Z'


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.archive = ReplayArchive(DB)
        self.original_sha = hashlib.sha256(DB.read_bytes()).hexdigest()

    def tearDown(self):
        self.assertEqual(hashlib.sha256(DB.read_bytes()).hexdigest(), self.original_sha)

    def corrupt_copy(self, statement, params=()):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / 'synthetic-corruption.db'
        shutil.copyfile(DB, path)
        with sqlite3.connect(path) as db:
            for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
                db.execute('DROP TRIGGER "' + name.replace('"', '""') + '"')
            db.execute(statement, params)
        return ReplayArchive(path)

    def test_catalog_is_navigation_only(self):
        cases = self.archive.cases()
        self.assertEqual(len(cases), 4)
        for case in cases:
            self.assertEqual(set(case), {'case_id', 'symbol', 'call_type', 'decision_cutoff', 'opened_at'})
        self.assertNotIn('REPRICED', json.dumps(cases))

    def test_historical_cutoff_does_not_invent_knowledge_or_prediction(self):
        snapshot = self.archive.snapshot(ZEAL, HISTORICAL)
        self.assertEqual(snapshot['known_evidence'], [])
        self.assertEqual(snapshot['information_sets'], [])
        self.assertIsNone(snapshot['recorded_prediction'])
        self.assertIsNone(snapshot['outcome'])
        text = json.dumps(snapshot)
        for future_text in ('petrelintide', 'WATCH', 'REPRICED_UP', 'SELECTED-ON-OUTCOME'):
            self.assertNotIn(future_text, text)

    def test_recorded_reconstruction_is_not_a_historical_forecast(self):
        snapshot = self.archive.snapshot(ZEAL, OPEN)
        self.assertTrue(snapshot['known_evidence'])
        prediction = snapshot['recorded_prediction']
        self.assertIn('retrospective', prediction['label'])
        self.assertIn('not a historical forecast', prediction['label'])
        self.assertEqual(prediction['recorded_at'], OPEN)
        self.assertEqual(prediction['disposition'], 'WATCH')
        self.assertTrue(prediction['evaluations'])
        self.assertIsNone(snapshot['outcome'])

    def test_outcome_requires_separate_reveal_and_recorded_cutoff(self):
        hidden = self.archive.snapshot(ZEAL, CLOSED)
        self.assertIsNone(hidden['outcome'])
        self.assertNotIn('REPRICED_UP', json.dumps(hidden))
        early = self.archive.snapshot(ZEAL, OPEN, reveal_outcome=True)
        self.assertIsNone(early['outcome'])
        visible = self.archive.snapshot(ZEAL, CLOSED, reveal_outcome=True)
        self.assertEqual(visible['outcome']['outcome_label'], 'REPRICED_UP')
        again = self.archive.snapshot(ZEAL, HISTORICAL, reveal_outcome=True)
        self.assertIsNone(again['outcome'])
        self.assertIsNone(again['recorded_prediction'])
        self.assertEqual(again['known_evidence'], [])

    def test_threshold_and_reveal_do_not_change_original_snapshot(self):
        baseline = self.archive.snapshot(ZEAL, CLOSED)
        for grade in 'ABCD':
            result = self.archive.snapshot(ZEAL, CLOSED, minimum_grade=grade, reveal_outcome=True)
            self.assertEqual(result['snapshot_sha'], baseline['snapshot_sha'])
            for key in ('known_evidence', 'information_sets', 'recorded_prediction'):
                self.assertEqual(result[key], baseline[key])
            accepted = result['sandbox']['accepted_evidence_ids']
            self.assertEqual(len(accepted), result['sandbox']['accepted_count'])
            self.assertTrue(all(e['grade'] <= grade for e in result['known_evidence'] if e['evidence_id'] in accepted))
        self.assertEqual(self.archive.snapshot(ZEAL, CLOSED), baseline)

    def test_equivalent_timezone_has_same_snapshot(self):
        self.assertEqual(self.archive.snapshot(ZEAL, CLOSED),
                         self.archive.snapshot(ZEAL, '2026-10-08T14:44:16+02:00'))

    def test_legacy_hash_does_not_claim_unbound_calculations(self):
        result = self.archive.snapshot('KOD-R-NVDA-20230524', CLOSED)
        self.assertEqual(result['recorded_prediction']['evaluations'], [])
        self.assertTrue(all(not s['facts'] for s in result['information_sets']))

    def test_missing_or_malformed_chronology_fails_closed(self):
        cutoff = datetime(2026, 10, 30, tzinfo=timezone.utc)
        for missing in (None, '', '2025-03-11', 'bad timestamp'):
            self.assertFalse(_available(cutoff, missing))
        archive = self.corrupt_copy('UPDATE cases SET opened_at=? WHERE case_id=?', ('', ZEAL))
        with self.assertRaises(ReplayUnavailable):
            archive.snapshot(ZEAL, CLOSED)
        archive = self.corrupt_copy('UPDATE evidence_objects SET recorded_at=?', ('',))
        result = archive.snapshot(ZEAL, CLOSED)
        self.assertEqual(result['known_evidence'], [])
        self.assertTrue(all(not s['facts'] for s in result['information_sets']))

    def test_evidence_cannot_be_recorded_after_frozen_call_or_before_retrieval(self):
        for recorded_at in ('2027-01-01T00:00:00Z', '2000-01-01T00:00:00Z'):
            archive = self.corrupt_copy('UPDATE evidence_objects SET recorded_at=?', (recorded_at,))
            result = archive.snapshot(ZEAL, '2027-02-01T00:00:00Z')
            self.assertEqual(result['known_evidence'], [])
            self.assertTrue(all(not s['facts'] for s in result['information_sets']))

    def test_unknown_card_recipe_is_withheld_as_archive_error(self):
        archive = self.corrupt_copy('UPDATE cases SET card_hash_version=? WHERE case_id=?', ('UNKNOWN', ZEAL))
        with self.assertRaises(ReplayUnavailable):
            archive.snapshot(ZEAL, CLOSED)

    def test_tampered_card_is_withheld(self):
        archive = self.corrupt_copy('UPDATE cases SET disposition=? WHERE case_id=?', ('REJECT', ZEAL))
        with self.assertRaisesRegex(ReplayUnavailable, 'hash mismatch'):
            archive.snapshot(ZEAL, CLOSED)

    def test_tampered_evidence_is_withheld(self):
        archive = self.corrupt_copy("UPDATE evidence_objects SET object_json='{}'")
        with self.assertRaisesRegex(ReplayUnavailable, 'hash mismatch'):
            archive.snapshot(ZEAL, CLOSED)

    def test_later_component_recording_is_withheld(self):
        archive = self.corrupt_copy('UPDATE detector_evaluations SET recorded_at=? WHERE case_id=?', (CLOSED, ZEAL))
        with self.assertRaisesRegex(ReplayUnavailable, 'recording time'):
            archive.snapshot(ZEAL, CLOSED)

    def test_outcome_must_reference_original_card(self):
        archive = self.corrupt_copy('UPDATE outcomes SET card_sha_at_open=? WHERE case_id=?', ('0' * 64, ZEAL))
        self.assertIsNone(archive.snapshot(ZEAL, CLOSED)['outcome'])
        with self.assertRaises(ReplayUnavailable):
            archive.snapshot(ZEAL, CLOSED, reveal_outcome=True)

    def test_missing_archive_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'missing.db'
            with self.assertRaises(ReplayUnavailable):
                ReplayArchive(path).cases()
            self.assertFalse(path.exists())

    def test_invalid_inputs(self):
        for value in ('', '2026-10-30', '2026-10-30T12:00:00', 'not a date', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.archive.snapshot(ZEAL, value)
        for grade in ('', 'E', 'a', None):
            with self.subTest(grade=grade), self.assertRaises(ValueError):
                self.archive.snapshot(ZEAL, CLOSED, minimum_grade=grade)
        with self.assertRaises(ReplayUnavailable):
            self.archive.snapshot("' OR 1=1 --", CLOSED)


class ReplayWebTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from kod.workstation.web import create_app
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = create_app(self.root / 'workspace', offline=True, testing=True, replay_db=DB)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def get(self, **params):
        response = self.client.get('/replay', params={'case_id': ZEAL, 'as_of': CLOSED, **params})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response.text

    def test_default_is_historical_and_unrevealed(self):
        response = self.client.get('/replay')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('No recorded call at this cutoff', response.text)
        self.assertIn('No evidence available at this cutoff', response.text)
        self.assertNotIn('REPRICED UP', response.text)

    def test_explicit_reveal_then_backwards_hides_all_future_content(self):
        hidden = self.get()
        self.assertNotIn('REPRICED UP', hidden)
        self.assertIn('Recorded retrospective reconstruction', hidden)
        shown = self.get(reveal='outcome')
        self.assertIn('REPRICED UP', shown)
        early = self.get(as_of=HISTORICAL, reveal='outcome')
        self.assertNotIn('REPRICED UP', early)
        self.assertNotIn('petrelintide', early)
        self.assertIn('No recorded call at this cutoff', early)

    def test_navigation_and_experiment_forms_do_not_carry_reveal(self):
        from html.parser import HTMLParser
        class Forms(HTMLParser):
            def __init__(self):
                super().__init__()
                self.forms = []
                self.current = None
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'form':
                    self.current = []
                    self.forms.append(self.current)
                elif self.current is not None and tag in ('input', 'select', 'button'):
                    self.current.append(attrs)
            def handle_endtag(self, tag):
                if tag == 'form':
                    self.current = None
        parser = Forms()
        parser.feed(self.get(reveal='outcome'))
        self.assertGreaterEqual(len(parser.forms), 2)
        for form in parser.forms:
            self.assertNotIn('reveal', [field.get('name') for field in form])

    def test_invalid_request_is_safe_error(self):
        self.assertEqual(self.client.get('/replay', params={'as_of': '2026-10-30'}).status_code, 400)
        self.assertEqual(self.client.get('/replay', params={'minimum_grade': 'E'}).status_code, 400)
        self.assertEqual(self.client.get('/replay', params={'case_id': 'unknown'}).status_code, 404)

    def test_missing_ledger_is_honest_and_not_created(self):
        self.app.state.replay_db = self.root / 'missing.db'
        response = self.client.get('/replay')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('Replay unavailable', response.text)
        self.assertFalse(self.app.state.replay_db.exists())


if __name__ == '__main__':
    unittest.main()

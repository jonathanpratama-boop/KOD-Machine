"""Read-only integration of real preserved population studies and shared cutoff UI."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from kod.workstation.web import create_app

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'kod' / 'workstation' / 'research_evidence'
NOW = '2026-10-31T00:00:00Z'
BEFORE = '2026-10-30T17:59:21Z'
CAPTURED = '2026-10-30T17:59:22Z'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for name, value in attrs if name == 'href')


class ResearchWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = create_app(Path(self.tmp.name) / 'workspace', offline=True, testing=True)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.paths = [ROOT / 'var' / 'kod.db', *EVIDENCE.glob('*.json')]
        self.before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.paths}

    def tearDown(self):
        self.assertEqual(self.before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.paths})

    def study(self, name, cutoff=NOW):
        response = self.client.get('/research/' + name, params={'as_of': cutoff})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response.text

    def test_historical_views_withhold_metrics_and_exact_raw_fields(self):
        for study in ('sequence', 'e6', 'execution'):
            with self.subTest(study=study):
                html = self.study(study, BEFORE)
                self.assertIn('Research evidence withheld', html)
                self.assertNotIn('Exact preserved result fields', html)
                self.assertNotIn('Inspect pinned upstream artifact', html)
                self.assertIn(CAPTURED, html)
                self.assertNotIn('research-summary', html)
                for leaked in ('1722', '204867', '-1.50%', '67.6%', 'Failed', 'failed discovery', 'paired interval includes zero'):
                    self.assertNotIn(leaked, html)

    def test_capture_boundary_releases_frozen_results(self):
        for study in ('sequence', 'e6', 'execution'):
            with self.subTest(study=study):
                html = self.study(study, CAPTURED)
                self.assertIn('Exact preserved result fields', html)
                self.assertNotIn('Research evidence withheld', html)

    def test_sequence_displays_baselines_false_alerts_censoring_and_uncertainty(self):
        html = self.study('sequence')
        for expected in ('76 / 1825', '1722 known false alerts', '27 censored',
                         '46 / 911', 'Simple', 'Summary', 'Sequence',
                         'Paired interval includes zero', 'not an active policy',
                         'Censoring bounds below are not confidence intervals',
                         'Probability calibration', 'train base rate',
                         'not tested by this model comparison'):
            self.assertIn(expected, html)

    def test_e6_keeps_failed_gates_and_controls_visible(self):
        html = self.study('e6')
        for expected in ('204867', 'Failed', 'P1 pressure', 'P2 pressure then breakout',
                         'failed discovery; frozen, not reopened', 'minus PL placebo',
                         'runs only for an arm whose gate passed'):
            self.assertIn(expected, html)
        self.assertGreaterEqual(html.count('<b>Failed</b>'), 2)

    def test_execution_pairs_high_hit_rate_with_negative_mean_and_no_implied_link(self):
        html = self.study('execution')
        for expected in ('34 / 53', '-1.50%', '67.6%', 'Median 9.30%',
                         'mean is negative', 'not an execution test of the sequence model',
                         'assumed fills, costs and short-side access',
                         'actually borrowable or tradeable'):
            self.assertIn(expected, html)

    def test_provenance_and_raw_are_present_only_after_availability(self):
        html = self.study('sequence')
        for expected in ('Provenance and reproduction', 'Inspect pinned upstream artifact',
                         'Exact preserved result fields', 'sha256', 'commit', CAPTURED,
                         'No result here is automatically attached to a ledger case or company'):
            self.assertIn(expected, html)

    def test_shared_cutoff_preserved_in_all_workbench_destinations(self):
        company = self.app.state.store.upsert_security('TEST', 'Test Company', venue='XNAS', currency='USD')
        response = self.client.get('/investigate', params={'as_of': BEFORE})
        self.assertEqual(response.status_code, 200, response.text)
        parser = Links()
        parser.feed(response.text)
        targets = []
        for href in parser.hrefs:
            parts = urlsplit(href)
            if parts.path.startswith('/research/') or (parts.path == '/replay' and 'case_id=' in parts.query) or parts.path == f"/company/{company['id']}/dossier":
                query = parse_qs(parts.query)
                self.assertEqual(query.get('as_of'), [BEFORE])
                if '/dossier' in parts.path:
                    self.assertEqual(query.get('mode'), ['observed'])
                    self.assertEqual(query.get('policy'), ['strict'])
                targets.append(parts.path)
        self.assertEqual(sum(p.startswith('/research/') for p in targets), 3)
        self.assertEqual(targets.count('/replay'), 4)
        self.assertIn(f"/company/{company['id']}/dossier", targets)
        self.assertIn('No implied joins', response.text)
        self.assertNotIn('failed discovery', response.text)
        self.assertIn('not historical evidence', response.text)

    def test_invalid_timestamps_and_unknown_studies_are_safe_errors(self):
        for endpoint in ('/investigate', '/research/sequence'):
            for timestamp in ('2026-10-30', 'not a timestamp', '2026-10-30T10:00:00'):
                with self.subTest(endpoint=endpoint, timestamp=timestamp):
                    response = self.client.get(endpoint, params={'as_of': timestamp})
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertNotIn('Traceback', response.text)
        for name in ('unknown', '<script>', 'sequence.json'):
            response = self.client.get('/research/' + name, params={'as_of': NOW})
            self.assertEqual(response.status_code, 404, response.text)
            self.assertNotIn('Traceback', response.text)

    def test_repeated_reads_and_cutoff_changes_do_not_mutate_workstation(self):
        store = self.app.state.store
        before = (store.securities(), store.events(), store.notes())
        for cutoff in (BEFORE, NOW, BEFORE, NOW):
            self.client.get('/investigate', params={'as_of': cutoff})
            for study in ('sequence', 'e6', 'execution'):
                self.study(study, cutoff)
        self.assertEqual(before, (store.securities(), store.events(), store.notes()))


if __name__ == '__main__':
    unittest.main()

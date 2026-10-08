"""Regression cases for false SEC approvals and market-local split boundaries."""
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from idxsig import paper, us_actions as ua
from tests.test_e2_repair import FakeSec
from tests import test_paper_scorer_v2 as scorer_tests


class Verification(unittest.TestCase):
    day = date(2026, 10, 8)

    def verify(self, text, n=1, d=100):
        return ua.verify_event(FakeSec({'test.htm': text}), {'SYN': 1}, 'SYN',
                               self.day.isoformat(), n, d, 'SPLIT')

    def test_proposed_ranges_and_unrelated_dates_cannot_approve(self):
        texts = [
            'On October 8, 2026, shareholders authorized a reverse stock split at a ratio ranging '
            'from 1-for-10 to 1-for-100. The board has not chosen a ratio or effective date.',
            'On October 8, 2026 we filed this report. A 1-for-100 reverse stock split became '
            'effective on January 2, 2024.',
            'We completed a 1-for-100 reverse stock split in 2024 and published results on October 8, 2026.',
            'We propose a 1-for-100 reverse stock split effective on October 8, 2026.',
            'A 1-for-100 reverse stock split may become effective on October 8, 2026.',
            'The 1-for-100 reverse stock split will not become effective on October 8, 2026.',
            'We cancelled the 1-for-100 reverse stock split effective on October 8, 2026.',
            'If approved, a 1-for-100 reverse stock split will become effective on October 8, 2026.',
            'We completed a 1-for-100 reverse stock split on January 2, 2024. '
            'The 1-for-10 reverse stock split is effective on October 8, 2026.',
        ]
        for text in texts:
            with self.subTest(text=text):
                self.assertNotIn(self.verify(text)['status'], ua.ACCEPTED)

    def test_definite_event_retains_auditable_excerpt(self):
        text = 'The 1-for-100 reverse stock split will become effective on October 8, 2026.'
        out = self.verify(text)
        self.assertEqual(out['status'], 'VERIFIED')
        self.assertEqual(out['evidence'][0]['matched_statements'], [text])
        self.assertEqual(out['evidence'][0]['verifier_version'], ua.VERSION)

    def test_ratio_direction_cannot_be_inverted(self):
        self.assertNotIn(self.verify('A 100-for-1 reverse stock split is effective on October 8, 2026.')['status'], ua.ACCEPTED)
        self.assertNotIn(self.verify('A 1-for-100 reverse stock split is effective on October 8, 2026.', 100, 1)['status'], ua.ACCEPTED)
        self.assertEqual(self.verify('A 100-for-1 stock split is effective on October 8, 2026.', 100, 1)['status'], 'VERIFIED')

    def test_may_as_a_month_is_not_a_conditional(self):
        out = ua.judge("A 1-for-10 reverse stock split is effective on May 8, 2026.", 1, 10, date(2026, 5, 8))
        self.assertTrue(out["date_ok"])

    def test_undated_ratio_is_diagnostic_only(self):
        out = self.verify('We completed a 1-for-100 reverse stock split.')
        self.assertEqual(out['status'], 'RATIO_CONFIRMED')
        self.assertNotIn(out['status'], ua.ACCEPTED)

    def test_coverage_does_not_quarantine_a_proposal(self):
        import pandas as pd
        client = FakeSec({'a.htm': 'On October 8, 2026 shareholders authorized a 1-for-100 reverse stock split.'})
        out = ua.check_jump(client, {'SYN': 1}, pd.DataFrame(columns=['ticker', 'effective_session']),
                            'SYN', '2026-10-08', 100, False)
        self.assertEqual(out['status'], 'NO_SPLIT_EVIDENCE')


class EventTimezone(unittest.TestCase):
    def parse(self, market, day, zone):
        stamp = int(datetime.fromisoformat(day + 'T09:00:00').replace(tzinfo=ZoneInfo(zone)).timestamp())
        payload = {'chart': {'result': [{'events': {'splits': {'x': {
            'date': stamp, 'numerator': 1, 'denominator': 10, 'splitRatio': '1:10'}}}}]}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'payload.json'
            path.write_text(json.dumps(payload))
            with mock.patch.object(ua, 'PKG_ROOT', Path(d)), mock.patch.object(ua, 'read_manifest',
                    return_value=({}, [{'ticker': 'SYN', 'path': path.name, 'http_status': 200, 'sha256': 'x'}])):
                return ua.yahoo_events(Path('manifest'), market=market)

    def test_idx_open_keeps_jakarta_session(self):
        ev = self.parse('IDX', '2026-10-08', 'Asia/Jakarta').iloc[0]
        self.assertEqual(ev.effective_session, '2026-10-08')
        self.assertEqual(ev.local_time, '09:00')

    def test_us_keeps_new_york_session_in_both_dst_regimes(self):
        for day in ('2026-01-08', '2026-10-08'):
            with self.subTest(day=day):
                ev = self.parse('US', day, 'America/New_York').iloc[0]
                self.assertEqual(ev.effective_session, day)
                self.assertEqual(ev.local_time, '09:00')


class Scoring(unittest.TestCase):
    def test_ratio_only_evidence_cannot_score(self):
        case = scorer_tests.ScorerV2()
        case.setUp()
        split = case.reverse_split(case.ran, case.session_after)
        ev = scorer_tests.events(('T007', case.session_after, 1., 10., '1:10', 'SPLIT'))
        out, reason, _ = case.scored(split, ev, verify=lambda e: ('RATIO_CONFIRMED', []))
        self.assertIsNone(out)
        self.assertIn('not corroborated', reason)

    def test_score_pending_passes_market_to_event_parser(self):
        import pandas as pd
        decision = {'type': 'DECISION', 'market': 'IDX', 'decision_id': 'D'}
        with mock.patch.object(paper, 'ledger_lines', return_value=[decision]), \
             mock.patch.object(paper, 'load_recent', return_value=(pd.DataFrame(), {})), \
             mock.patch.object(paper, '_market'), mock.patch.object(paper, '_window_complete', return_value=False), \
             mock.patch.object(ua, 'yahoo_events', return_value=pd.DataFrame()) as parser:
            paper.score_pending(Path('manifest'), market='IDX')
        parser.assert_called_once_with(Path('manifest'), market='IDX')


class ScheduleUpgrade(unittest.TestCase):
    def test_older_approvals_are_rechecked(self):
        import hashlib
        import pandas as pd
        row = {'ticker': 'SYN', 'effective_session': '2026-10-08', 'numerator': 1.,
               'denominator': 100., 'provider_ratio': '1:100', 'kind': 'SPLIT',
               'status': 'VERIFIED', 'evidence': '[]'}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = root/'raw.jsonl'
            raw.write_text('frozen input')
            csv = root/'schedule.csv'
            pd.DataFrame([row]).to_csv(csv, index=False)
            meta = root/'old.json'
            meta.write_text(json.dumps({'version': 'us-actions-v1', 'schedule': csv.name,
                'schedule_sha256': hashlib.sha256(csv.read_bytes()).hexdigest(),
                'raw_manifest_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
                'effective_after': '2023-01-03', 'universe_end': '2023-12-29'}))
            downgraded = pd.DataFrame([{**row, 'status': 'MENTION_ONLY'}])
            with mock.patch.object(ua, 'PKG_ROOT', root), \
                 mock.patch.object(ua, 'yahoo_events', return_value=pd.DataFrame([row])), \
                 mock.patch.object(ua, 'read_manifest', return_value=({}, [{'ticker': 'SYN', 'first_date': '2020-01-01'}])), \
                 mock.patch.object(ua, 'verify_schedule', return_value=downgraded) as verify, \
                 mock.patch.object(ua, 'write_manifest', return_value=Path('sec.jsonl')), \
                 mock.patch.object(ua, 'rel', side_effect=lambda p: str(p.relative_to(root))):
                output = ua.build_schedule(raw, 'offline', '2023-01-03', '2023-12-29',
                                           offline=True, recheck=meta, log=lambda s: None)
            self.assertEqual(verify.call_args.args[0]['ticker'].tolist(), ['SYN'])
            manifest = json.loads(output.read_text())
            self.assertEqual(manifest['status_counts'], {'MENTION_ONLY': 1})
            self.assertEqual(manifest['accepted_statuses'], ['VERIFIED'])

    def test_repair_builder_refuses_old_schedule(self):
        from idxsig import global_panel
        with tempfile.TemporaryDirectory() as d:
            manifest = Path(d)/'v1.json'
            manifest.write_text(json.dumps({'version': 'us-actions-v1'}))
            with mock.patch.object(global_panel, 'check_files', return_value=[]):
                with self.assertRaisesRegex(ValueError, 'older verifier'):
                    global_panel.build_us_repair(Path('raw'), manifest, '2023-12-29')

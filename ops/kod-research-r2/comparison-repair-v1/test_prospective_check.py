import json
import sqlite3
import unittest
import zlib

import test_export_results as fixtures
import export_results as report


class ProspectiveCheckTests(unittest.TestCase):
    setUp = fixtures.ResultsExportTests.setUp
    tearDown = fixtures.ResultsExportTests.tearDown

    def activate(self, started=None):
        folder = self.root / 'comparison-inputs'; folder.mkdir(exist_ok=True)
        self.started = self.watermark - 72 * 3600 if started is None else started
        (folder / 'PROSPECTIVE_CHECK.json').write_text(json.dumps({
            'schema':'KOD_PROSPECTIVE_CHECK_V1', 'started_at':report.iso(self.started),
            'timing_arm_minutes':1, 'horizon_hours':24}))
        self.db.execute('CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY,id TEXT UNIQUE,kind TEXT,at REAL,payload BLOB)')
        self.db.commit()

    def add_signal(self, ident='new', reference=None, complete=True, controls=True,
                   net=.05, compressed=True, arms=(1,5,30,240)):
        reference = self.watermark - 25*3600 if reference is None else reference
        basket = [{'symbol':'C1USDT'}, {'symbol':'C2USDT'}] if controls else []
        payload = {'event_id':ident,'reference_at':report.iso(reference),'controls':basket,
                   'controls_status':'AVAILABLE' if controls else 'UNAVAILABLE_PRE_EVENT_FEATURES'}
        raw = json.dumps(payload)
        self.db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(ident,'TESTUSDT',reference-3600,reference,raw))
        encoded = zlib.compress(raw.encode()) if compressed else raw
        self.db.execute("INSERT INTO ledger(id,kind,at,payload) VALUES(?,?,?,?)",('event:'+ident,'EVENT',reference,encoded))
        for arm in arms:
            targets=[('TESTUSDT','EVENT',net)]+([('C1USDT','CONTROL',-.02),('C2USDT','CONTROL',0)] if controls else [])
            for symbol,role,value in targets:
                pid=f'{ident}:{arm}:{symbol}'
                self.db.execute('INSERT INTO positions VALUES(?,?,?,?,?,?,?,?)',
                    (pid,ident,arm,symbol,role,reference+60,'ENTERED',json.dumps({'received_at':report.iso(reference+61)})))
                outcome={'position_id':pid,'horizon_hours':24,'returns':{'modeled_net_token_return':value,'net_excess':value-.01}}
                self.db.execute('INSERT INTO endpoints VALUES(?,?,?,?,?)',
                    (pid,24,reference+86400,'COMPLETE' if complete else 'AWAIT_EXIT',json.dumps(outcome) if complete else None))
                if complete:
                    self.db.execute('INSERT INTO ledger(id,kind,at,payload) VALUES(?,?,?,?)',
                        ('outcome:'+pid+':24','OUTCOME',reference+86401,json.dumps(outcome)))
        self.db.commit()
        return payload

    def check(self):
        return report.export_results(self.root)['prospective_check']

    def test_no_registration_keeps_check_disabled(self):
        self.assertEqual(self.check(), {'enabled':False})

    def test_pre_activation_winner_is_not_counted(self):
        self.activate(started=self.watermark-3600)
        self.add_signal(net=.5)
        value=self.check()
        self.assertEqual(value['status'],'WAITING_FOR_SIGNALS')
        self.assertEqual(value['events'],[])
        self.assertEqual(value['total_signals'],0)
        self.assertIsNone(value['mean_excess'])

    def test_full_compressed_original_selection_scores_one_pair_not_four_arms(self):
        self.activate();self.add_signal()
        value=self.check();event=value['events'][0]
        self.assertEqual((value['total_signals'],value['completed_pairs'],value['beat_controls']),(1,1,1))
        self.assertEqual(value['status'],'RECORDING_COMPARISONS')
        self.assertEqual(event['controls'],['C1USDT','C2USDT'])
        self.assertTrue(event['selection_verified'])
        self.assertAlmostEqual(event['control_mean_net_return'],-.01)
        self.assertAlmostEqual(event['excess'],.06)
        self.assertAlmostEqual(value['mean_excess'],.06)

    def test_pending_comparisons_show_original_choices_before_returns_exist(self):
        self.activate();self.add_signal(reference=self.watermark-60,complete=False,compressed=False)
        value=self.check();event=value['events'][0]
        self.assertEqual(value['status'],'WAITING_FOR_RESULTS')
        self.assertEqual(value['pending_pairs'],1)
        self.assertTrue(event['selection_verified'])
        self.assertEqual(event['controls'],['C1USDT','C2USDT'])
        self.assertIsNone(event['net_return']);self.assertIsNone(event['excess'])

    def test_changed_basket_is_unavailable(self):
        self.activate();payload=self.add_signal()
        payload['controls'][1]['symbol']='OTHERUSDT'
        self.db.execute('UPDATE events SET payload=?',(json.dumps(payload),));self.db.commit()
        value=self.check()
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertFalse(value['events'][0]['selection_verified'])
        self.assertIsNone(value['mean_excess'])

    def test_future_selection_clock_is_rejected(self):
        self.activate();self.add_signal()
        self.db.execute("UPDATE ledger SET at=at+1 WHERE kind='EVENT'");self.db.commit()
        value=self.check()
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertFalse(value['events'][0]['selection_verified'])

    def test_selection_appended_after_an_outcome_is_rejected(self):
        self.activate();self.add_signal()
        self.db.execute("UPDATE ledger SET seq=10000 WHERE kind='EVENT'");self.db.commit()
        value=self.check()
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertFalse(value['events'][0]['selection_verified'])

    def test_missing_control_never_becomes_partial_or_zero_comparison(self):
        self.activate();self.add_signal()
        self.db.execute("UPDATE endpoints SET status='CENSORED',payload=NULL WHERE position_id='new:1:C2USDT'");self.db.commit()
        value=self.check()
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertIsNone(value['events'][0]['control_mean_net_return'])
        self.assertIsNone(value['events'][0]['excess'])
        self.assertIsNone(value['mean_excess'])

    def test_no_controls_remains_a_visible_unavailable_signal(self):
        self.activate();self.add_signal(controls=False)
        value=self.check()
        self.assertEqual(value['status'],'COMPARISONS_UNAVAILABLE')
        self.assertEqual(value['total_signals'],1)
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertEqual(value['events'][0]['controls'],[])

    def test_losses_ties_and_same_day_signals_are_counted(self):
        self.activate()
        self.add_signal('loss',net=-.05)
        self.add_signal('tie',net=-.01,reference=self.watermark-25*3600+1)
        value=self.check()
        self.assertEqual(value['completed_pairs'],2)
        self.assertEqual(value['behind_controls'],1)
        self.assertEqual(value['tied_controls'],1)
        self.assertEqual(value['beat_controls'],0)
        self.assertEqual(value['distinct_signal_dates'],1)
        self.assertAlmostEqual(value['mean_excess'],-.02)

    def test_incomplete_comparison_after_deadline_is_unavailable(self):
        self.activate();self.add_signal(complete=False)
        value=self.check()
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertEqual(value['pending_pairs'],0)

    def test_missing_original_selection_record_is_unavailable(self):
        self.activate();self.add_signal()
        self.db.execute("DELETE FROM ledger WHERE kind='EVENT'");self.db.commit()
        value=self.check()
        self.assertFalse(value['events'][0]['selection_verified'])
        self.assertEqual(value['unavailable_pairs'],1)

    def test_different_exit_deadline_cannot_be_scored(self):
        self.activate();self.add_signal()
        self.db.execute("UPDATE endpoints SET deadline=deadline+3600 WHERE position_id='new:1:C1USDT'");self.db.commit()
        value=self.check()
        self.assertEqual(value['unavailable_pairs'],1)
        self.assertIsNone(value['mean_excess'])


if __name__=='__main__':unittest.main()

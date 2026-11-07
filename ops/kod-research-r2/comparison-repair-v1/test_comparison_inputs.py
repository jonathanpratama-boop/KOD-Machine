import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from comparison_inputs import daily_items, input_loader_with_comparisons, open_input_queue, PREFIX
from broad_observer.store import BroadStore
from research_r2.engine import ResearchEngine, stamp, iso, rebuild_from_exports

T = stamp('2026-11-07T00:00:00Z')
CONFIG = {'t0': iso(T), 'study_id': 'fixture', 'primary': [{'symbol': 'AAAUSDT'}, {'symbol': 'BBBUSDT'}]}


def source_attempt(at=T+60):
    rows = []
    for index in range(30):
        opened = T - (30-index)*86400
        rows.append([int(opened*1000), '1', '1', '1', '1', '1', int((opened+86400)*1000)-1, str(100+index)])
    return {'symbol': 'AAAUSDT', 'status_code': 200, 'request_started_at': iso(at-.1),
        'received_at': iso(at), 'cutoff_exclusive': iso(T), 'body': json.dumps(rows).encode()}


class ComparisonInputsTests(unittest.TestCase):
    def test_daily_inputs_preserve_receipt_time_and_old_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state = root/'state'; state.mkdir()
            engine = ResearchEngine(state/'engine', CONFIG)
            store = BroadStore(state, clock=lambda: dt.datetime.fromtimestamp(T+60,dt.timezone.utc))
            receipt = store.append_batch('daily-fixture', iso(T+60), 'OK', [source_attempt()], {}, kind='comparison_daily')
            event = store.iter_batches(receipt['day'])[0]
            original = [tuple(r) for r in engine.db.execute('SELECT * FROM ledger ORDER BY seq')]
            queue = open_input_queue(state, CONFIG)
            try:
                items = daily_items(store, event)
                self.assertTrue(queue.enqueue(PREFIX+event['hash'], items))
                self.assertFalse(queue.enqueue(PREFIX+event['hash'], items))
                engine.process_until(T+59)
                self.assertEqual(engine.db.execute('SELECT count(*) FROM daily').fetchone()[0], 0)
                engine.process_until(T+90)
                self.assertEqual(engine.db.execute('SELECT count(*) FROM daily').fetchone()[0], 30)
                self.assertEqual(engine.db.execute('SELECT min(available) FROM daily').fetchone()[0], T+60)
                self.assertEqual([tuple(r) for r in engine.db.execute('SELECT * FROM ledger WHERE seq<=? ORDER BY seq',(len(original),))], original)
                engine.export_incremental(state/'engine/ledger')
                rebuilt = rebuild_from_exports(root/'restored',CONFIG,state/'engine/ledger',input_loader_with_comparisons(store,CONFIG))
                try:
                    self.assertEqual(rebuilt.verify_ledger(), engine.verify_ledger())
                    self.assertEqual(rebuilt.db.execute('SELECT count(*) FROM daily').fetchone()[0],30)
                finally:
                    rebuilt.close()
            finally:
                queue.close(); engine.close()

    def test_incomplete_or_nonfinite_source_never_becomes_a_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BroadStore(tmp, clock=lambda: dt.datetime.fromtimestamp(T+60,dt.timezone.utc))
            for case in ('missing', 'nan', 'current_day'):
                attempt=source_attempt(); rows=json.loads(attempt['body'])
                if case=='missing': rows.pop()
                if case=='nan': rows[0][7]='NaN'
                if case=='current_day': rows[-1][0]=int(T*1000)
                attempt['body']=json.dumps(rows).encode()
                receipt=store.append_batch(case,iso(T+60),'OK',[attempt],{},kind='comparison_daily')
                event=store.iter_batches(receipt['day'],after_seq=receipt['seq'],limit=1)[0]
                with self.assertRaises(ValueError): daily_items(store,event)

    def test_late_delivery_does_not_rewrite_old_availability(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp); engine=ResearchEngine(state/'engine',CONFIG)
            store=BroadStore(state,clock=lambda:dt.datetime.fromtimestamp(T+60,dt.timezone.utc))
            receipt=store.append_batch('late',iso(T+60),'OK',[source_attempt()],{},kind='comparison_daily')
            event=store.iter_batches(receipt['day'])[0]
            engine.process_until(T+90)
            queue=open_input_queue(state,CONFIG)
            try:
                queue.enqueue(PREFIX+event['hash'],daily_items(store,event))
                engine.process_until(T+120)
                self.assertEqual(engine.db.execute('SELECT count(*) FROM daily').fetchone()[0],0)
                self.assertEqual(engine.db.execute("SELECT count(*) FROM ledger WHERE kind='LATE_ARCHIVE_INPUT'").fetchone()[0],30)
            finally:queue.close();engine.close()


if __name__=='__main__':unittest.main()

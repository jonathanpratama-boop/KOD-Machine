"""Controlled interleavings of real cycle/CAS writes; fixtures, no network receipts."""
import ast
import fcntl
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from idxsig import crypto_account as ca, paper
from tests import test_crypto_account as fixtures


class Concurrency(fixtures.Base):
    def bounded(self):
        rows=ca.lines();state=ca.account(rows)
        orders=[r for r in rows if r['type']==ca.ORDER]
        decided=[r['decision_id'] for r in rows if r['type'] in (ca.ORDER,ca.DECLINE)]
        self.assertEqual(len(decided),len(set(decided)))
        self.assertLessEqual(len(orders),ca.MAX_NEW_PER_DAY)
        self.assertLessEqual(state['planned_risk'],ca.MAX_PLANNED_RISK*state['equity']+1e-8)
        self.assertGreaterEqual(state['free_cash'],0)
        self.assertGreaterEqual(state['reserved'],0)
        self.assertEqual(paper.verify_chain(self.ledger),[])
        self.assertEqual(ca.verify(),[])

    def overlap(self, duplicate):
        first=[fixtures._decision(t) for t in ('A','B','C')]
        second=first if duplicate else [fixtures._decision(t) for t in ('D','E','F')]
        for d in first+second:self.m.book[ca.symbol_of(d)]=(105,106)
        armed=True;conflicts=[]
        def append(recs,**kwargs):
            nonlocal armed
            if armed and any(r['type']==ca.ORDER for r in recs):
                armed=False
                ca.cycle(second,self.m.fetch,self.m.clock,append)
            before=self.ledger.read_bytes() if self.ledger.exists() else b''
            try:return self.append(recs,**kwargs)
            except RuntimeError as exc:
                if str(exc)==ca._STALE_HEAD_MESSAGE:
                    conflicts.append(kwargs['expected_head'])
                    self.assertEqual(self.ledger.read_bytes(),before)
                raise
        run=ca.cycle(first,self.m.fetch,self.m.clock,append)
        self.assertEqual(len(conflicts),1)
        self.assertEqual(len(self.of(ca.ORDER)),3)
        self.assertEqual(self.kinds(run),[] if duplicate else [(ca.DECLINE,'LIMIT_NEW_PER_DAY')]*3)
        self.assertEqual(run['mark']['reserved'],round(ca.account(ca.lines())['reserved'],2))
        self.bounded()

    def test_duplicate_candidates_recompute_to_empty_without_replayed_orders(self):
        self.overlap(True)

    def test_disjoint_candidates_cannot_double_daily_or_risk_budget(self):
        self.overlap(False)

    def test_one_remaining_slot_admits_only_one_concurrent_candidate(self):
        for t in ('A','B','C','D'):self.m.book[t+'USDT']=(105,106)
        self.run_cycle([fixtures._decision('A'),fixtures._decision('B')])
        armed=True
        def append(recs,**kwargs):
            nonlocal armed
            if armed and any(r['type']==ca.ORDER for r in recs):
                armed=False
                ca.cycle([fixtures._decision('D')],self.m.fetch,self.m.clock,append)
            return self.append(recs,**kwargs)
        run=ca.cycle([fixtures._decision('C')],self.m.fetch,self.m.clock,append)
        self.assertEqual(self.kinds(run),[(ca.DECLINE,'LIMIT_NEW_PER_DAY')])
        self.assertEqual(len(self.of(ca.ORDER)),3)
        self.bounded()

    def test_stale_settlement_does_not_duplicate_fill(self):
        d=fixtures._decision('A');self.m.book['AUSDT']=(105,106)
        self.run_cycle([d]);self.m.book['AUSDT']=(99,100)
        armed=True
        def append(recs,**kwargs):
            nonlocal armed
            if armed and any(r['type']==ca.ENTRY for r in recs):
                armed=False
                ca.cycle([d],self.m.fetch,self.m.clock,append)
            return self.append(recs,**kwargs)
        run=ca.cycle([d],self.m.fetch,self.m.clock,append)
        self.assertEqual(len(self.of(ca.ENTRY)),1)
        self.assertEqual(self.kinds(run),[])
        self.bounded()

    def test_stale_mark_recomputed_from_new_reservation(self):
        self.m.book['AUSDT']=(105,106);armed=True
        def append(recs,**kwargs):
            nonlocal armed
            if armed and any(r['type']==ca.MARK for r in recs):
                armed=False
                ca.cycle([fixtures._decision('A')],self.m.fetch,self.m.clock,append)
            return self.append(recs,**kwargs)
        run=ca.cycle([],self.m.fetch,self.m.clock,append)
        self.assertGreater(run['mark']['reserved'],0)
        self.assertEqual(run['mark']['reserved'],round(ca.account(ca.lines())['reserved'],2))
        self.bounded()

    def test_retry_exhaustion_never_commits_stale_proposals(self):
        self.m.book['AUSDT']=(105,106);attempts=[]
        def append(recs,**kwargs):
            if any(r['type']==ca.ORDER for r in recs):
                attempts.append(kwargs.get('expected_head'))
                self.append([fixtures._quote('NOISEUSDT',1,1,fixtures.T0+timedelta(seconds=len(attempts)))])
                before=self.ledger.read_bytes()
                try:return self.append(recs,**kwargs)
                finally:self.assertEqual(self.ledger.read_bytes(),before)
            return self.append(recs,**kwargs)
        with self.assertRaisesRegex(ca.StaleHeadConflict,'retry budget exhausted'):
            ca.cycle([fixtures._decision('A')],self.m.fetch,self.m.clock,append)
        self.assertEqual(len(attempts),ca.MAX_PHASE_ATTEMPTS)
        self.assertEqual(len(set(attempts)),len(attempts))
        self.assertEqual(self.of(ca.ORDER),[])
        self.assertEqual(ca.account(ca.lines())['reserved'],0)
        self.bounded()

    def test_receipt_pending_after_commit_is_success_not_business_retry(self):
        self.m.book['AUSDT']=(105,106);order_attempts=[]
        def append(recs,**kwargs):
            written=self.append(recs,**kwargs)
            if any(r['type']==ca.ORDER for r in recs):
                order_attempts.append(recs)
                raise paper.ReceiptPendingError(written,RuntimeError('fixture receipt unavailable'))
            return written
        run=ca.cycle([fixtures._decision('A')],self.m.fetch,self.m.clock,append)
        self.assertEqual(len(order_attempts),1)
        self.assertEqual(self.kinds(run),[(ca.ORDER,'')])
        self.assertEqual(len(run['receipt_warnings']),1)
        self.assertGreater(run['mark']['reserved'],0)
        self.bounded()

    def test_actual_receipt_failure_occurs_after_lock_release_and_does_not_retry(self):
        self.m.book['AUSDT']=(105,106);receipt_calls=[]
        def receipts(hashes,path,timestamper):
            # Nonblocking acquisition fails if the append critical section still
            # owns this lock; no actual receipt service is contacted.
            with path.with_name(path.name+'.lock').open('a') as lock:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
            receipt_calls.append(hashes)
            raise RuntimeError('offline receipt failure')
        def append(recs,**kwargs):
            return paper.append(recs,path=self.ledger,timestamper=object(),**kwargs)
        with mock.patch.object(paper,'retry_receipts',side_effect=receipts):
            run=ca.cycle([fixtures._decision('A')],self.m.fetch,self.m.clock,append)
        self.assertEqual(len(self.of(ca.ORDER)),1)
        self.assertEqual(len(receipt_calls),4)  # observation, order, observation, mark
        self.assertEqual(len(run['receipt_warnings']),4)
        self.bounded()

    def test_unrelated_runtime_errors_are_not_treated_as_conflicts(self):
        self.m.book['AUSDT']=(105,106);calls=[]
        def append(recs,**kwargs):
            if any(r['type']==ca.ORDER for r in recs):
                calls.append(1);raise RuntimeError('ledger chain broken')
            return self.append(recs,**kwargs)
        with self.assertRaisesRegex(RuntimeError,'ledger chain broken'):
            ca.cycle([fixtures._decision('A')],self.m.fetch,self.m.clock,append)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.of(ca.ORDER),[])

    def test_observations_unguarded_and_all_state_phases_guarded(self):
        self.m.book['AUSDT']=(99,100);calls=[]
        def append(recs,**kwargs):
            calls.append(([r['type'] for r in recs],kwargs))
            return self.append(recs,**kwargs)
        ca.cycle([fixtures._decision('A')],self.m.fetch,self.m.clock,append)
        for kinds,kwargs in calls:
            self.assertEqual('expected_head' in kwargs,any(k in (ca.ORDER,ca.DECLINE,ca.ENTRY,ca.EXIT,ca.MARK) for k in kinds))
        self.bounded()

    def test_cli_callback_forwards_expected_head_and_keeps_receipt_pending_separate(self):
        source=(Path(ca.__file__).parent/'cli.py').read_text()
        callbacks=[n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='append'
                   and 'ca.LEDGER' in ast.get_source_segment(source,n)]
        self.assertEqual(len(callbacks),1)
        callback=callbacks[0];wrapped=ast.Module(body=[callback],type_ignores=[])
        writer=mock.Mock(return_value=[{'committed':True}]);written=[]
        ns={'paper':mock.Mock(append=writer,ReceiptPendingError=paper.ReceiptPendingError),
            'ca':ca,'stamper':None,'written':written,'print':mock.Mock()}
        exec(compile(ast.fix_missing_locations(wrapped),'cli-callback','exec'),ns)
        ns['append']([{'fixture':True}],expected_head='expected-prefix')
        self.assertEqual(writer.call_args.kwargs['expected_head'],'expected-prefix')
        writer.side_effect=paper.ReceiptPendingError([{'record_hash':'committed-hash'}],RuntimeError('pending'))
        ns['append']([{'fixture':True}],expected_head='next-prefix')
        self.assertEqual(written[-1]['record_hash'],'committed-hash')
        self.assertEqual(writer.call_count,2)


if __name__=='__main__':unittest.main()

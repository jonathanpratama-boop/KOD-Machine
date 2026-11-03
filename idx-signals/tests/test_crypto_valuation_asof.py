"""Separate artificial future-row/stale-clock guard; no normal forward-data claim."""
from datetime import timedelta
from idxsig import crypto_account as ca
from tests import test_crypto_account as fixtures


class AsOf(fixtures.Base):
    def seed(self):
        self.m.book['AAAUSDT']=(99.9,100)
        self.run_cycle([fixtures._decision('AAA')])
        now=fixtures.T0+timedelta(minutes=1)
        self.append([fixtures._quote('BBBUSDT',99.9,100,now)])
        return now

    def test_future_quote_cannot_change_present_mark_or_decision(self):
        now=self.seed();candidate=fixtures._decision('BBB');before=ca.lines()
        expected_mark=ca.mark(before,now);expected_decision=ca.decide(before,[candidate],now)
        self.append([fixtures._quote('AAAUSDT',200,200.1,now+timedelta(days=6))])
        self.assertEqual(ca.mark(ca.lines(),now),expected_mark)
        self.assertEqual(ca.decide(ca.lines(),[candidate],now),expected_decision)
        self.assertEqual(expected_decision[0]['type'],ca.ORDER)
        self.assertLessEqual(expected_mark['open_positions'][0]['valued_at'],expected_mark['made_at'])
        # Existing full-ledger reporting semantics are not silently rewritten.
        self.assertGreater(ca.account(ca.lines())['equity'],expected_mark['equity'])

    def test_future_quote_becomes_eligible_at_its_actual_observation_time(self):
        now=self.seed();future=now+timedelta(days=6)
        self.append([fixtures._quote('AAAUSDT',200,200.1,future)])
        self.assertEqual(ca.mark(ca.lines(),future)['open_positions'][0]['valued_at'],ca._stamp(future))

    def test_future_business_events_fail_closed_not_partial_history(self):
        now=self.seed();rows=ca.lines();future=ca._stamp(now+timedelta(days=1))
        for kind,fields in ((ca.ORDER,('made_at',)),(ca.DECLINE,('made_at',)),(ca.CANCEL,('made_at',)),
                            (ca.ENTRY,('recorded_at','filled_at')),(ca.EXIT,('recorded_at','exited_at')),
                            (ca.MARK,('made_at',))):
            for field in fields:
                with self.subTest(kind=kind,field=field):
                    inconsistent=rows+[{'type':kind,field:future,'decision_id':'future-fixture'}]
                    with self.assertRaises(ca.FutureLedgerStateError):ca.mark(inconsistent,now)
                    with self.assertRaises(ca.FutureLedgerStateError):ca.decide(inconsistent,[fixtures._decision('BBB')],now)

    def test_future_deadlines_are_not_mistaken_for_future_business_events(self):
        now=self.seed()
        self.assertGreater(self.of(ca.ENTRY)[0]['deadline'],ca._stamp(now))
        self.assertEqual(len(ca.mark(ca.lines(),now)['open_positions']),1)

    def test_naive_asof_clock_fails_closed(self):
        now=self.seed()
        with self.assertRaisesRegex(ValueError,'timezone-aware'):
            ca.mark(ca.lines(),now.replace(tzinfo=None))

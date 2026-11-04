"""v1.3 quote-boundary regressions; injected feed and actual HTTP parser, offline."""
import io
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from idxsig import crypto_account as ca
from tests import test_crypto_account as fixtures

BAD_BOOKS = ((float('nan'), 100), (99, float('nan')),
             (float('inf'), float('inf')), (99, float('inf')),
             (float('-inf'), 100), (99, float('-inf')),
             (0, 1), (-1, 1), (1, 0), (1, -1), (101, 100),
             (True, 100), (99, True), (None, 100), (99, None),
             ('garbage', 100), (99, 'garbage'), ([], 100), (99, {}))


class InvalidQuotes(fixtures.Base):
    def test_invalid_injected_books_decline_without_quotes_orders_or_reservations(self):
        for bid, ask in BAD_BOOKS:
            with self.subTest(bid=bid, ask=ask), tempfile.TemporaryDirectory() as td, mock.patch.object(ca, 'LEDGER', Path(td)/'ledger.jsonl'):
                # append() follows Base.ledger, so bind it to the same per-case file.
                with mock.patch.object(self, 'ledger', ca.LEDGER):
                    self.m.book['AAAUSDT'] = (bid, ask)
                    run = self.run_cycle([fixtures._decision('AAA')])
                    self.assertEqual(self.kinds(run), [(ca.DECLINE, 'NO_FRESH_QUOTE')])
                    self.assertEqual((self.of(ca.QUOTE), self.of(ca.ORDER), self.of(ca.ENTRY)), ([], [], []))
                    self.assertEqual(len(self.of(ca.QUOTE_ERROR)), 1)
                    self.assertIn('ValueError', self.of(ca.QUOTE_ERROR)[0]['error'])
                    self.assertEqual((run['mark']['cash'], run['mark']['reserved']), (ca.START_CASH, 0.0))

    def test_http_parser_rejects_invalid_bid_ask_before_returning(self):
        for bid, ask in BAD_BOOKS:
            payload = json.dumps({'bidPrice':bid, 'askPrice':ask}).encode()
            with self.subTest(bid=bid, ask=ask), mock.patch.object(ca.urllib.request, 'urlopen', return_value=io.BytesIO(payload)):
                with self.assertRaises(ValueError):
                    ca.book_ticker('AAAUSDT')

    def test_http_infinity_becomes_recorded_error_not_order(self):
        payload = b'{"bidPrice":"Infinity","askPrice":"Infinity"}'
        with mock.patch.object(ca.urllib.request, 'urlopen', side_effect=lambda *a, **kw: io.BytesIO(payload)), mock.patch.object(ca, 'utc_stamp', return_value=ca._stamp(fixtures.T0)):
            run = ca.cycle([fixtures._decision('AAA')], ca.fetch_quotes,
                           lambda: fixtures.T0 + timedelta(seconds=1), self.append)
        self.assertEqual(self.kinds(run), [(ca.DECLINE, 'NO_FRESH_QUOTE')])
        self.assertEqual(self.of(ca.QUOTE), [])
        self.assertEqual(run['mark']['reserved'], 0)

    def test_invalid_current_quote_cannot_fall_back_to_valid_recent_cache(self):
        self.append([fixtures._quote('AAAUSDT',99,100,fixtures.T0-timedelta(minutes=1))])
        self.m.book['AAAUSDT'] = (float('inf'),float('inf'))
        run = self.run_cycle([fixtures._decision('AAA')])
        self.assertEqual(self.kinds(run), [(ca.DECLINE,'NO_FRESH_QUOTE')])
        self.assertEqual(len(self.of(ca.QUOTE)),1)
        self.assertEqual(run['mark']['reserved'],0)

    def test_invalid_quote_preserves_existing_position_and_does_not_crash_midcycle(self):
        self.m.book['AAAUSDT'] = (99,100)
        decision = fixtures._decision('AAA')
        self.run_cycle([decision])
        before = ca.account(ca.lines())
        quote_count = len(self.of(ca.QUOTE))
        self.m.book['AAAUSDT'] = (float('inf'),float('inf'))
        run = self.run_cycle([{**decision,'decision_id':'independent-next'}])
        self.assertEqual(self.kinds(run),[(ca.DECLINE,'NO_FRESH_QUOTE')])
        self.assertEqual(ca.account(ca.lines()),before)
        self.assertEqual(len(self.of(ca.QUOTE)),quote_count)
        self.assertEqual(self.of(ca.EXIT),[])
        self.assertEqual(ca.verify(),[])

    def test_valid_finite_and_locked_quote_still_work(self):
        self.m.book['AAAUSDT']=(100,100)
        run=self.run_cycle([fixtures._decision('AAA')])
        self.assertEqual(self.kinds(run),[(ca.ORDER,''),(ca.ENTRY,'FILLED')])

    def test_legitimate_numeric_strings_parse_in_http_and_injected_feed(self):
        payload = b'{"bidPrice":"99.00000000","askPrice":"1e2"}'
        with mock.patch.object(ca.urllib.request,'urlopen',return_value=io.BytesIO(payload)):
            bid,ask,_=ca.book_ticker('AAAUSDT')
        self.assertEqual((bid,ask),(99.0,100.0))
        self.m.book['AAAUSDT']=('99.00000000','1e2')
        self.assertEqual(self.kinds(self.run_cycle([fixtures._decision('AAA')])),[(ca.ORDER,''),(ca.ENTRY,'FILLED')])

    def test_invalid_position_quote_does_not_block_unrelated_valid_symbol(self):
        self.m.book['AAAUSDT']=(99,100)
        self.run_cycle([fixtures._decision('AAA')])
        before=ca.account(ca.lines())['open'][0]
        self.m.book['AAAUSDT']=(True,None)
        self.m.book['BBBUSDT']=(99,100)
        run=self.run_cycle([fixtures._decision('BBB')])
        self.assertEqual(self.kinds(run),[(ca.ORDER,''),(ca.ENTRY,'FILLED')])
        after=ca.account(ca.lines())
        self.assertEqual(next(p for p in after['open'] if p['symbol']=='AAAUSDT'),before)
        self.assertEqual(len(after['open']),2)
        self.assertEqual(self.of(ca.QUOTE_ERROR)[-1]['symbol'],'AAAUSDT')
        self.assertNotIn('nan',ca.render(ca.lines()).lower())
        self.assertEqual(ca.verify(),[])


if __name__ == '__main__':
    unittest.main()

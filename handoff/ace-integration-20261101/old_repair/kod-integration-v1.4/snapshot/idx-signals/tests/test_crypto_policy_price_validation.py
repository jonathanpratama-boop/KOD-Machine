"""Policy reference input boundary; no strategy threshold changes or network."""
import tempfile
from pathlib import Path
from unittest import mock

from idxsig import crypto_account as ca
from tests import test_crypto_account as fixtures


class PolicyPrice(fixtures.Base):
    def test_invalid_policy_quote_declines_and_unrelated_candidate_continues(self):
        bad=(float('inf'),float('-inf'),float('nan'),True,False,None,'garbage',0,-1,'NaN','Infinity',[],{})
        for quote in bad:
            with self.subTest(quote=quote),tempfile.TemporaryDirectory() as td, mock.patch.object(ca,'LEDGER',Path(td)/'ledger.jsonl'):
                with mock.patch.object(self,'ledger',ca.LEDGER):
                    self.m.book={'AAAUSDT':(99,100),'BBBUSDT':(99,100)}
                    run=self.run_cycle([fixtures._decision('AAA',quote=quote),fixtures._decision('BBB')])
                    self.assertEqual(self.kinds(run),[(ca.DECLINE,'NO_DECISION_PRICE'),(ca.ORDER,''),(ca.ENTRY,'FILLED')])
                    self.assertEqual([r['symbol'] for r in self.of(ca.ORDER)],['BBBUSDT'])
                    self.assertEqual(run['mark']['reserved'],0)
                    self.assertEqual(len(ca.account(ca.lines())['open']),1)
                    self.assertEqual(ca.verify(),[])

    def test_legitimate_numeric_string_policy_quote_is_retained(self):
        self.m.book['AAAUSDT']=(99,100)
        run=self.run_cycle([fixtures._decision('AAA',quote='1e2')])
        self.assertEqual(self.kinds(run),[(ca.ORDER,''),(ca.ENTRY,'FILLED')])
        self.assertEqual(self.of(ca.ORDER)[0]['limit'],101)

    def test_missing_or_malformed_verified_price_declines(self):
        self.m.book['AAAUSDT']=(99,100)
        d={**fixtures._decision('AAA'),'verified_price':'not-a-price-record'}
        run=self.run_cycle([d])
        self.assertEqual(self.kinds(run),[(ca.DECLINE,'NO_DECISION_PRICE')])
        self.assertEqual(self.of(ca.ORDER),[])
        self.assertEqual(run['mark']['reserved'],0)

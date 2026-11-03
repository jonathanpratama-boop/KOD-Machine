"""Separate bounded causal valuation fixture; no network or receipts."""
import json, sys, tempfile
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
ROOT=Path(__file__).parent/'source'/'idx-signals'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from idxsig import crypto_account as ca, paper
from test_crypto_account import Market, _decision, _quote, T0
with tempfile.TemporaryDirectory() as tmp:
    ledger=Path(tmp)/'ledger.jsonl'
    with patch.object(ca,'LEDGER',ledger):
        append=lambda rows:paper.append(rows,path=ledger)
        market=Market(); market.book['AAAUSDT']=(99.9,100.0)
        ca.cycle([_decision('AAA')],market.fetch,market.clock,append)
        now=T0+timedelta(minutes=1)
        append([_quote('BBBUSDT',99.9,100.0,now)])
        candidate=_decision('BBB')
        baseline=ca.lines(); before=ca.mark(baseline,now); before_decision=ca.decide(baseline,[candidate],now)[0]
        future=T0+timedelta(days=6)
        append([_quote('AAAUSDT',200.0,200.1,future)])
        rows=ca.lines(); after=ca.mark(rows,now); after_decision=ca.decide(rows,[candidate],now)[0]
        result={'as_of':ca._stamp(now),'future_quote_time':ca._stamp(future),
                'before_mark_equity':before['equity'],'after_mark_equity':after['equity'],
                'before_decision':before_decision['type'],'after_decision':after_decision['type'],
                'after_decision_reason':after_decision.get('reason'),
                'mark_position':after['open_positions'][0],
                'eligible_position_quote_at':ca.fresh_quote(rows,'AAAUSDT',now)[0]['observed_at'],
                'eligible_candidate_quote_at':ca.fresh_quote(rows,'BBBUSDT',now)[0]['observed_at'],
                'settlement_at_now':ca.settle(rows,now),
                'settlement_at_future_types':[r['type'] for r in ca.settle(rows,future)],
                'chain_problems':paper.verify_chain(ledger),'account_problems':ca.verify()}
        assert before_decision['type']==ca.ORDER and after_decision['type']==ca.DECLINE
        assert after['open_positions'][0]['valued_at']>after['made_at']
        assert ca.settle(rows,now)==[] and not result['chain_problems'] and not result['account_problems']
        print(json.dumps(result,sort_keys=True))

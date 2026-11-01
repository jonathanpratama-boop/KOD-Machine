"""Two bounded spawn-process CAS races, temp ledgers and fake receipt tokens only."""
import json, multiprocessing as mp, socket, sys, tempfile, traceback
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).parent/'fixed-source'/'idx-signals'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from idxsig import crypto_account as ca, paper
from test_crypto_account import Market, _decision, _quote, T0

class FakeTimestamper:
    authorities=('offline_fixture',)
    def stamp(self,payload):
        return [SimpleNamespace(authority='offline_fixture',token=b'NOT-RFC3161-TEST-ONLY:'+payload)]

def worker(path, ticker, role, conn):
    try:
        ca.LEDGER=Path(path); paper.TOKENS=ca.LEDGER.parent/'fake-receipts'
        released=False; conflicts=0; proposals=0
        def clock(): return T0+timedelta(seconds=30 if released else 11+role)
        def fetch(symbols):
            return [{**_quote(s,105.,106.,T0+timedelta(seconds=30 if released else 10)),
                     'source':f'offline-process-{role}'} for s in symbols]
        def append(recs,**kwargs):
            nonlocal released,conflicts,proposals
            if any(r['type']==ca.ORDER for r in recs):
                proposals+=1
                if not released:
                    conn.send({'ready':role,'head':kwargs['expected_head']})
                    if not conn.poll(10): raise TimeoutError('parent release timeout')
                    assert conn.recv()=='go';released=True
            try:return paper.append(recs,path=ca.LEDGER,timestamper=FakeTimestamper(),**kwargs)
            except RuntimeError as exc:
                if type(exc) is RuntimeError and str(exc)==ca._STALE_HEAD_MESSAGE:conflicts+=1
                raise
        with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')),patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')):
            run=ca.cycle([_decision(ticker)],fetch,clock,append)
        conn.send({'done':role,'conflicts':conflicts,'proposals':proposals,
                   'events':[r['type'] for r in run['events']],'receipt_warnings':run['receipt_warnings']})
    except ca.StaleHeadConflict as exc:
        conn.send({'done':role,'conflicts':conflicts,'proposals':proposals,
                   'fail_closed':str(exc),'events':None,'receipt_warnings':[]})
    except BaseException:
        conn.send({'error':traceback.format_exc()})
        raise
    finally:conn.close()

def case(duplicate):
    ctx=mp.get_context('spawn')
    with tempfile.TemporaryDirectory(prefix='crypto-multiprocess-') as tmp:
        ledger=Path(tmp)/'ledger.jsonl'; children=[]; pipes=[]
        with patch.object(ca,'LEDGER',ledger),patch.object(paper,'TOKENS',Path(tmp)/'fake-receipts'):
            market=Market();market.book={'AUSDT':(105,106),'BUSDT':(105,106)}
            ca.cycle([_decision('A'),_decision('B')],market.fetch,market.clock,
                     lambda recs,**kw:paper.append(recs,path=ledger,timestamper=FakeTimestamper(),**kw))
            try:
                for role,ticker in enumerate(('C','C' if duplicate else 'D')):
                    parent,child=ctx.Pipe();p=ctx.Process(target=worker,args=(str(ledger),ticker,role,child))
                    p.start();child.close();children.append(p);pipes.append(parent)
                ready=[]
                for conn in pipes:
                    if not conn.poll(15): raise TimeoutError('worker ready timeout')
                    msg=conn.recv();assert 'ready' in msg,msg;ready.append(msg)
                # Both workers have computed proposals before either can publish.
                for conn in pipes:conn.send('go')
                done=[]
                for conn in pipes:
                    if not conn.poll(15):raise TimeoutError('worker completion timeout')
                    msg=conn.recv();assert 'done' in msg,msg;done.append(msg)
                for p in children:
                    p.join(5);assert p.exitcode==0,('child exit',p.exitcode)
                rows=ca.lines();st=ca.account(rows);orders=[r for r in rows if r['type']==ca.ORDER]
                decisions=[r['decision_id'] for r in rows if r['type'] in (ca.ORDER,ca.DECLINE)]
                chain=paper.verify_chain(ledger);problems=ca.verify()
                assert len(orders)==3 and st['planned_risk']<=150+1e-8
                assert st['free_cash']>=0 and st['cash']>=0 and st['reserved']>=0
                assert len(decisions)==len(set(decisions)) and not chain and not problems
                assert sum(d['conflicts'] for d in done)>=1
                assert all(not d['receipt_warnings'] for d in done)
                receipts=list((Path(tmp)/'fake-receipts').glob('*.tsr'))
                assert len(receipts)==len(rows)
                return {'case':'duplicate final-slot candidates' if duplicate else 'disjoint final-slot candidates',
                        'orders':len(orders),'distinct_decisions':len(set(decisions)),
                        'planned_risk':st['planned_risk'],'risk_cap':150,'cash':st['cash'],
                        'reserved':st['reserved'],'free_cash':st['free_cash'],
                        'chain_problems':chain,'account_problems':problems,
                        'workers':done,'fake_receipts':len(receipts),'ledger_rows':len(rows),
                        'child_exitcodes':[p.exitcode for p in children]}
            finally:
                for p in children:
                    if p.is_alive():p.terminate()
                    p.join(5)
                    if p.is_alive():p.kill();p.join(5)
                for conn in pipes:conn.close()

if __name__=='__main__':
    for duplicate in (True,False):print(json.dumps(case(duplicate),sort_keys=True))

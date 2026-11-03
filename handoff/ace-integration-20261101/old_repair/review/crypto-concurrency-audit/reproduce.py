"""Offline stale-snapshot interleaving of real ca.cycle; no receipts or network."""
import json, sys, tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 'source' / 'idx-signals'))
from idxsig import crypto_account as ca, paper
T = datetime(2026,11,1,0,30,tzinfo=timezone.utc)
def candidate(t):
    return {'type':'DECISION','market':'CRYPTO','decision_id':'fixture-'+t,
            'decision':'BUY ON TRIGGER','instrument':{'ticker':t},
            'signal_session':'2026-10-31','decided_at':'2026-11-01T00:20:00Z',
            'verified_price':{'quote':100.0},'record_hash':'fixture-decision-'+t}
def run_case(duplicate):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'ledger.jsonl'
        cands_a=[candidate(t) for t in ['A','B','C']]
        cands_b=cands_a if duplicate else [candidate(t) for t in ['D','E','F']]
        def feed(now):
            return lambda syms: [{'type':ca.QUOTE,'account':ca.ACCOUNT_ID,'symbol':s,
                                  'bid':105.0,'ask':106.0,'observed_at':ca._stamp(now),
                                  'source':'offline-fixture'} for s in syms]
        armed=True
        def append(recs):
            nonlocal armed
            # A has already called decide(lines()). Pause before its append;
            # B now completes its entire cycle before A resumes.
            if armed and any(r['type']==ca.ORDER for r in recs):
                armed=False
                ca.cycle(cands_b,feed(T+timedelta(seconds=2)),
                         lambda:T+timedelta(seconds=2),append)
            return paper.append(recs,path=path)
        with patch.object(ca,'LEDGER',path):
            ca.cycle(cands_a,feed(T),lambda:T+timedelta(seconds=1),append)
            rows=ca.lines(); state=ca.account(rows)
            orders=[r for r in rows if r['type']==ca.ORDER]
            result={'case':'duplicate decisions' if duplicate else 'disjoint decisions',
                    'orders':len(orders),'distinct_decisions':len({r['decision_id'] for r in orders}),
                    'decision_times':sorted({r['made_at'] for r in orders}),
                    'risk':state['planned_risk'],'risk_cap':ca.MAX_PLANNED_RISK*state['equity'],
                    'reserved':state['reserved'],'daily_order_cap':ca.MAX_NEW_PER_DAY,
                    'chain_problems':paper.verify_chain(path),'account_problems':ca.verify()}
            assert len(orders)==6 and result['risk']>result['risk_cap']
            assert not result['chain_problems']
            if not duplicate: assert not result['account_problems']
            print(json.dumps(result,sort_keys=True))

def control():
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'ledger.jsonl'
        paper.append([{'type':'fixture','value':1}],path=p,expected_head=None)
        before=p.read_bytes()
        try: paper.append([{'type':'fixture','value':2}],path=p,expected_head=None)
        except RuntimeError as e:
            assert p.read_bytes()==before
            print(json.dumps({'expected_head_control':str(e),'bytes_unchanged':True}))
        else: raise AssertionError('stale head accepted')
run_case(True)
run_case(False)
control()

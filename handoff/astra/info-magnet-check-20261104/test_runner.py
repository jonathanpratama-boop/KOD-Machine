import datetime as dt
from decimal import Decimal
import unittest
from run import evaluate
from archive import DownloadError

UTC=dt.timezone.utc
ENTRY=dt.datetime(2024,1,2,2,tzinfo=UTC)
EVENT={'primary_krw':True,'notice_at':'2024-01-02T01:10:00Z','entry_at':ENTRY.isoformat(),'review_required':[],'symbol':'TARGETUSDT','event_id':'UPBIT:1:TARGET'}
SYMBOLS=['TARGETUSDT']+[f'C{i}USDT' for i in range(1,7)]
class Fake:
    def __init__(self,mode='ok'):self.mode=mode;self.calls=[]
    def bar(self,symbol,hour):
        self.calls.append((symbol,hour))
        if self.mode=='secondary_error' and hour==ENTRY+dt.timedelta(hours=71):raise DownloadError('secondary only')
        if self.mode=='missing_exit' and hour==ENTRY+dt.timedelta(hours=23):return None
        if self.mode=='no_prior' and hour<ENTRY:return None
        return {'open':Decimal('100'),'close':Decimal('104')}
class Runner(unittest.TestCase):
    def test_secondary_error_does_not_discard_primary(self):
        r=evaluate(EVENT,Fake('secondary_error'),SYMBOLS)
        self.assertEqual(r['status'],'SCORED');self.assertEqual(r['horizons']['72']['status'],'UNRESOLVED_DATA')
    def test_missing_primary_exit_is_unresolved(self):
        r=evaluate(EVENT,Fake('missing_exit'),SYMBOLS)
        self.assertEqual(r['status'],'UNRESOLVED_PRIMARY_OUTCOME');self.assertEqual(len(r['control_symbols']),5)
    def test_prior_hour_absence_not_zero_return(self):
        r=evaluate(EVENT,Fake('no_prior'),SYMBOLS)
        self.assertEqual(r['status'],'UNMEASURABLE_NO_PRE_NOTICE_HOUR');self.assertNotIn('event_gross_return',r)
    def test_deterministic_controls_and_proper_eligibility_hour(self):
        a=Fake();r=evaluate(EVENT,a,SYMBOLS);r2=evaluate(EVENT,Fake(),SYMBOLS)
        self.assertEqual(r['control_symbols'],r2['control_symbols']);self.assertNotIn('TARGETUSDT',r['control_symbols'])
        self.assertEqual(a.calls[0][1],dt.datetime(2024,1,2,0,tzinfo=UTC))
        self.assertEqual(r['status'],'SCORED')
if __name__=='__main__':unittest.main()

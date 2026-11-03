"""Independent endpoint-age amendment checks; all invented receipts, no network."""
import sys,unittest,copy
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent.parent/'coinbase_reference_adapter_20261101'),str(Path(__file__).resolve().parent.parent/'coinbase_reference_adapter_20261101'/'tests')]
from mock_fixtures import *
class Freshness(unittest.TestCase):
 def cached(self,age=120,lag=120,elapsed=3):
  r=receipt(product()['url'],a.checked_receipt(product())[2],elapsed=elapsed)
  r['headers']['Date']=format_datetime(BASE-timedelta(seconds=lag),usegmt=True)
  if age is not None:r['headers']['Age']=str(age)
  return r
 def test_age_transit_plus_residence_not_omitted_or_doubled(self):
  r=self.cached();a.product_rules(r,at(177))
  with self.assertRaises(ValueError):a.product_rules(r,at(177.001))
  with self.assertRaises(ValueError):a.checked_receipt(self.cached(299,299,5))
 def test_date_age_not_summed_and_absent_age_uses_date(self):
  a.product_rules(self.cached(100,200,3),at(100))
  with self.assertRaises(ValueError):a.product_rules(self.cached(100,200,3),at(100.001))
  a.product_rules(self.cached(None,299,.1),at(1))
  with self.assertRaises(ValueError):a.product_rules(self.cached(None,299,.1),at(1.001))
 def test_bad_or_ambiguous_age_date_headers_rejected(self):
  for age in ('nan','inf','-1','1.5','+1','unknown'):
   with self.subTest(age=age),self.assertRaises(ValueError):a.checked_receipt(self.cached(age))
  for name,value in [('age','0'),('date',format_datetime(BASE,usegmt=True))]:
   r=self.cached();r['headers'][name]=value
   with self.subTest(name=name),self.assertRaises(ValueError):a.checked_receipt(r)
 def test_preserved_header_pairs_cannot_hide_duplicate_or_mismatch(self):
  r=self.cached();r['header_pairs']=list(r['headers'].items())+[('Age','0')]
  with self.assertRaises(ValueError):a.checked_receipt(r)
  r=self.cached();r['header_pairs']=list(r['headers'].items());r['headers']['Age']='0'
  with self.assertRaises(ValueError):a.checked_receipt(r)
 def test_role_latency_bound_and_clock_jump(self):
  a.checked_receipt(self.cached(0,0,5))
  with self.assertRaises(ValueError):a.checked_receipt(self.cached(0,0,5.001))
  r=self.cached();r['monotonic_elapsed_seconds']=2
  with self.assertRaises(ValueError):a.checked_receipt(r)
  b=book();b['request_started_at']=at(-2);b['monotonic_elapsed_seconds']=3
  with self.assertRaises(ValueError):a.checked_receipt(b)
 def test_closed_at_receipt_but_http_date_preclose_rejected(self):
  midnight=BASE.replace(hour=0);rs=[]
  for symbol in a.PRODUCTS:
   r=candles(symbol);r['received_at']=a.stamp(midnight+timedelta(seconds=1));r['request_started_at']=a.stamp(midnight+timedelta(seconds=.9));r['headers']['Date']=format_datetime(midnight-timedelta(seconds=1),usegmt=True);rs.append(r)
  with self.assertRaises(ValueError):a.bars_payload(rs,'2026-10-31',a.stamp(midnight+timedelta(seconds=2)))
  for r in rs:r['headers']['Date']=format_datetime(midnight,usegmt=True)
  out,_=a.bars_payload(rs,'2026-10-31',a.stamp(midnight+timedelta(seconds=2)))
  self.assertEqual(len(out['BTC-USD']),40)
if __name__=='__main__':unittest.main()
